import copy
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.initialization_campaign import (PROTOCOL, SOURCES, load_json, save_json, digest,
    make_plan, interp_p1_to_p2, create_campaign, run_campaign, summarize, choose_result)
from src.initialization_campaign import prepare_campaign, audit_campaign, export_campaign
from src.three_host_encoding import build_three_host_qubo
from src.qaoa_experiment import qubo_fingerprint

ROOT = Path(__file__).resolve().parents[1]


class InitializationPlanTests(unittest.TestCase):
    def test_interp_preserves_beta_gamma_order_and_repeats_both(self):
        self.assertEqual(interp_p1_to_p2([.3, 1.]), [.3, .3, 1., 1.])
        for point in [[.3], [.3, float('nan')], [.1, .2, .3, .4]]:
            with self.assertRaises(ValueError): interp_p1_to_p2(point)

    def test_plan_charges_all_stages_and_reproduces_random_points(self):
        p = load_json(ROOT/PROTOCOL)
        plan = make_plan(p, 65.5)
        self.assertEqual(plan, make_plan(p, 65.5))
        self.assertEqual(len(plan), 24)
        groups = set(t['group'] for t in plan)
        self.assertEqual(len(groups), 13)
        for group in groups:
            self.assertEqual(sum(t['config']['maxiter'] for t in plan if t['group']==group), 200)
        interp = [t for t in plan if t['strategy']=='interp']
        self.assertEqual([t['p'] for t in interp], [1,2])
        self.assertEqual(interp[1]['depends_on'], interp[0]['id'])
        self.assertIsNone(interp[1]['config']['initial_point'])
        self.assertEqual(len({t['config']['final_seed'] for t in plan}), 24)
        random = [t for t in plan if t['start']=='random']
        self.assertEqual(len(random), 10)
        for t in random:
            point=t['config']['initial_point']; depth=t['p']
            self.assertTrue(all(0<=x<3.141593 for x in point[:depth]))
            self.assertTrue(all(0<=x<2*3.141593*65.5 for x in point[depth:]))

    def test_rejects_unequal_budgets(self):
        p=load_json(ROOT/PROTOCOL); p['local_budget']=99
        with self.assertRaises(ValueError): make_plan(p,65.5)

    def test_winner_uses_energy_and_excludes_preparatory_depth(self):
        candidates = [dict(id='prep',plan={'p':1},optimizer_value=-100,p_opt=.99),
                      dict(id='low_energy',plan={'p':2},optimizer_value=-2,p_opt=.01),
                      dict(id='high_popt',plan={'p':2},optimizer_value=1,p_opt=.9)]
        self.assertEqual(choose_result(candidates,2)['id'],'low_energy')


class InitializationCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'root'
        for name in SOURCES:
            target=self.root/'src'/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/'src'/name,target)
        instance=dict(schema_version=1,instance_id='initialization_qa',objective='min_active_hosts',
            tasks=[dict(id='t',cpu=1,ram=1)],
            hosts=[dict(id=f'h{i}',cpu=1,ram=1) for i in range(3)])
        save_json(self.root/'data/tiny.json',instance)
        self.protocol=load_json(ROOT/PROTOCOL)
        self.protocol.update(software_validation=True,total_budget=12,local_budget=6,maxiter=12,
            seeds=[400],threads=1,min_available_gib=.001,shots=32,final_shots=64)
        self.protocol['instances']=[dict(instance_id=instance['instance_id'],path='data/tiny.json',
            input_sha256=digest(instance),qubo_sha256=qubo_fingerprint(build_three_host_qubo(instance)))]

    def test_run_resume_and_charged_interpolation(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'run',self.protocol)
        run_campaign(self.root,folder,max_new_trials=2,progress=False)
        self.assertEqual(len(load_json(folder/'campaign.json')['trials']),2)
        run_campaign(self.root,folder,progress=False)
        c=load_json(folder/'campaign.json')
        self.assertEqual(len(c['trials']),8)
        s=summarize(folder)
        self.assertEqual(s['coverage']['completed'],5)
        self.assertTrue(all(r['nfev']<=12 for r in s['rows']))
        interp=next(r for r in s['rows'] if r['strategy']=='interp')
        self.assertEqual(interp['target_depth'],2)
        self.assertEqual(interp['trials'],2)
        plan=[t for t in c['plan'] if t['strategy']=='interp']
        prep=load_json(folder/c['trials'][plan[0]['id']]['path'])
        target=load_json(folder/c['trials'][plan[1]['id']]['path'])
        self.assertEqual(target['config']['initial_point'],interp_p1_to_p2(prep['point']))
        self.assertEqual(target['dependency_sha256'],c['trials'][plan[0]['id']]['sha256'])
        run_campaign(self.root,folder,progress=False)
        self.assertEqual(c,load_json(folder/'campaign.json'))
        self.assertTrue(audit_campaign(self.root,folder)['complete'])
        self.assertTrue(export_campaign(self.root,folder).is_file())
        path=folder/c['trials'][next(iter(c['trials']))]['path']
        saved=load_json(path);saved['final_exact']['p_opt']=.999
        save_json(path,saved)
        with self.assertRaises(ValueError): audit_campaign(self.root,folder)

    def test_can_schedule_interp_without_free_external_pretraining(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'selected',self.protocol)
        run_campaign(self.root,folder,groups=['p2__interp'],progress=False)
        c=load_json(folder/'campaign.json')
        self.assertEqual(len(c['trials']),2)
        self.assertTrue(all('interp' in key for key in c['trials']))
        self.assertEqual(summarize(folder)['coverage']['completed'],1)
        with self.assertRaises(ValueError):
            run_campaign(self.root,folder,groups=['unknown'],progress=False)

    def test_profiles_resume_without_new_optimization_calls(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'profile',self.protocol)
        before=prepare_campaign(self.root,folder,progress=False)
        self.assertEqual(before,prepare_campaign(self.root,folder,progress=False))
        self.assertEqual(summarize(folder)['coverage']['completed'],0)
        self.assertEqual(len(before['profiles']),2)
        self.assertEqual(len(before['strategies']),5)
        self.assertFalse(audit_campaign(self.root,folder)['complete'])

    def test_failed_trial_does_not_reset_budget_on_resume(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'failure',self.protocol)
        def fail(evaluator,config,*args):
            return dict(status='failed',mode='exact',config=config,nfev=0,history=[],error='QA failure')
        with patch('src.initialization_campaign.train',side_effect=fail):
            run_campaign(self.root,folder,progress=False)
        before=load_json(folder/'campaign.json')
        run_campaign(self.root,folder,progress=False)
        self.assertEqual(before,load_json(folder/'campaign.json'))
        self.assertEqual(summarize(folder)['coverage']['failed'],1)

    def test_changed_protocol_is_rejected(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'change',self.protocol)
        changed=copy.deepcopy(self.protocol);changed['tol']=.01
        with self.assertRaises(ValueError): create_campaign(self.root,folder,changed)


if __name__=='__main__': unittest.main()
