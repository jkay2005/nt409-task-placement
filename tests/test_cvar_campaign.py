import copy
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from src.cvar_campaign import (PROTOCOL, SOURCES, load_json, save_json, digest,
    make_plan, CVaREvaluator, create_campaign, run_campaign, summarize,
    prepare_campaign, audit_campaign, export_campaign, train)
from src.cvar_experiment import lower_tail_cvar
from src.three_host_encoding import build_three_host_qubo
from src.qaoa_experiment import qubo_fingerprint

ROOT=Path(__file__).resolve().parents[1]

class CVaRPlanTests(unittest.TestCase):
    def test_equal_caps_fresh_mean_preparation_for_every_objective(self):
        p=load_json(ROOT/PROTOCOL);plan=make_plan(p)
        self.assertEqual(len(plan),6)
        self.assertEqual([t['alpha'] for t in plan],[1.,1.,1.,.25,1.,.1])
        self.assertEqual(len({t['config']['final_seed'] for t in plan}),6)
        for group in {t['group'] for t in plan}:
            stages=[t for t in plan if t['group']==group]
            self.assertEqual([t['p'] for t in stages],[1,2])
            self.assertEqual(stages[1]['depends_on'],stages[0]['id'])
            self.assertEqual(sum(t['config']['maxiter'] for t in stages),200)
            self.assertEqual(stages[0]['config']['initial_point'],[.3,1.])
            self.assertIsNone(stages[1]['config']['initial_point'])
        p['local_budget']=99
        with self.assertRaises(ValueError):make_plan(p)

    def test_boundary_atom_ties_zero_mass_and_alpha_one(self):
        energy=[9,1,1,4];prob=[.5,.1,0,.4]
        self.assertAlmostEqual(lower_tail_cvar(energy,prob,.25),2.8)
        self.assertAlmostEqual(lower_tail_cvar(energy,prob,1),6.2)
        for a in [True,0,-.1,1.1,float('nan')]:
            with self.assertRaises(ValueError):lower_tail_cvar(energy,prob,a)

class CVaRCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'root'
        for name in SOURCES:
            target=self.root/'src'/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/'src'/name,target)
        instance=dict(schema_version=1,instance_id='cvar_qa',objective='min_active_hosts',
            tasks=[dict(id='t',cpu=1,ram=1)],hosts=[dict(id=f'h{i}',cpu=1,ram=1) for i in range(3)])
        save_json(self.root/'data/tiny.json',instance)
        self.bundle=build_three_host_qubo(instance)
        self.protocol=load_json(ROOT/PROTOCOL)
        self.protocol.update(software_validation=True,total_budget=12,local_budget=6,maxiter=12,
            threads=1,min_available_gib=.001,shots=32,final_shots=64)
        self.protocol['instances']=[dict(instance_id=instance['instance_id'],path='data/tiny.json',
            input_sha256=digest(instance),qubo_sha256=qubo_fingerprint(self.bundle))]

    def test_histogram_objective_matches_independent_statewise_cvar(self):
        e=CVaREvaluator(self.bundle,2,1,.001);point=[.3,.4,.7,.9]
        probabilities=e._probabilities(point)
        values=e.objectives(point,[1.,.25,.1])
        self.assertEqual(values['1.0'],float(probabilities@e.diagonal['energies']))
        for a in [.25,.1]:
            self.assertAlmostEqual(values[str(a)],lower_tail_cvar(e.diagonal['energies'],probabilities,a),places=10)
        self.assertLessEqual(values['0.1'],values['0.25'])
        self.assertLessEqual(values['0.25'],values['1.0'])

    def test_complete_resume_charged_parent_and_cross_objective_audit(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'run',self.protocol)
        run_campaign(self.root,folder,max_new_trials=1,progress=False)
        self.assertEqual(summarize(folder)['coverage']['completed'],0)
        run_campaign(self.root,folder,progress=False)
        c=load_json(folder/'campaign.json');s=summarize(folder)
        self.assertEqual(len(c['trials']),6)
        self.assertEqual(s['coverage'],dict(planned=3,completed=3,failed=0,pending=0))
        self.assertTrue(all(r['nfev']<=12 and r['trials_completed']==2 for r in s['rows']))
        starts=[]
        for group in {t['group'] for t in c['plan']}:
            prep,target=[t for t in c['plan'] if t['group']==group]
            r1=load_json(folder/c['trials'][prep['id']]['path']);r2=load_json(folder/c['trials'][target['id']]['path'])
            self.assertEqual(r2['config']['initial_point'],[r1['point'][0]]*2+[r1['point'][1]]*2)
            self.assertEqual(r2['dependency_sha256'],c['trials'][prep['id']]['sha256'])
            self.assertEqual(r2['objective_alpha'],target['alpha'])
            self.assertAlmostEqual(r2['final_objectives']['1.0'],r2['final_exact']['mean_energy'])
            starts.append(r2['config']['initial_point'])
        self.assertEqual(starts[0],starts[1]);self.assertEqual(starts[1],starts[2])
        before=load_json(folder/'campaign.json');run_campaign(self.root,folder,progress=False)
        self.assertEqual(before,load_json(folder/'campaign.json'))
        self.assertTrue(audit_campaign(self.root,folder)['complete'])
        self.assertTrue(export_campaign(self.root,folder).is_file())
        # Re-hash a forged CVaR value: semantic audit must still reject it.
        item=next(t for t in c['plan'] if t['alpha']==.25)
        entry=c['trials'][item['id']];path=folder/entry['path'];raw=load_json(path)
        raw['final_objectives']['0.25']+=1;save_json(path,raw)
        import hashlib
        c['trials'][item['id']]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();save_json(folder/'campaign.json',c)
        with self.assertRaises(ValueError):audit_campaign(self.root,folder)

    def test_mean_control_matches_existing_train_and_failure_keeps_history(self):
        from src.shot_noise_diagnostic import train as old_train
        e=CVaREvaluator(self.bundle,1,1,.001)
        config=make_plan(self.protocol)[0]['config']
        before=old_train(e,config,'exact',False);after=train(e,config,1.,False)
        self.assertEqual(before['point'],after['point'])
        self.assertEqual(before['optimizer_value'],after['optimizer_value'])
        self.assertEqual(before['final_exact'],after['final_exact'])
        self.assertEqual(before['final_counts'],after['final_counts'])
        real=e.objectives;calls=0
        def fail_second(*args):
            nonlocal calls
            calls+=1
            if calls==2:raise MemoryError('QA failure during training')
            return real(*args)
        with patch.object(e,'objectives',side_effect=fail_second):
            failed=train(e,config,1.,False)
        self.assertEqual(failed['status'],'failed');self.assertEqual(failed['nfev'],1)
        self.assertEqual(len(failed['history']),1)

    def test_profiles_are_outside_training_and_resume(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'profile',self.protocol)
        a=prepare_campaign(self.root,folder,progress=False)
        self.assertEqual(a,prepare_campaign(self.root,folder,progress=False))
        self.assertEqual(len(a['strategies']),3)
        self.assertFalse(load_json(folder/'campaign.json')['trials'])
        self.assertFalse(audit_campaign(self.root,folder)['complete'])

    def test_failed_trial_is_retained_and_other_group_can_run(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'failed',self.protocol)
        def fail(*args):
            reservation=load_json(folder/'campaign.json')['trials']
            first=load_json(folder/next(iter(reservation.values()))['path'])
            self.assertEqual(first['status'],'running');self.assertIsNone(first['nfev'])
            raise RuntimeError('QA failure')
        with patch('src.cvar_campaign.train',side_effect=fail):
            run_campaign(self.root,folder,progress=False)
        before=load_json(folder/'campaign.json');run_campaign(self.root,folder,progress=False)
        self.assertEqual(before,load_json(folder/'campaign.json'))
        self.assertEqual(summarize(folder)['coverage']['failed'],1)
        run_campaign(self.root,folder,groups=['p2__cvar_025'],progress=False)
        self.assertEqual(summarize(folder)['coverage']['completed'],1)
        self.assertFalse(audit_campaign(self.root,folder)['complete'])
        with self.assertRaises(ValueError):run_campaign(self.root,folder,groups=['unknown'],progress=False)

    def test_changed_protocol_and_source_are_rejected(self):
        folder=create_campaign(self.root,Path(self.temp.name)/'change',self.protocol)
        p=copy.deepcopy(self.protocol);p['tol']=.01
        with self.assertRaises(ValueError):create_campaign(self.root,folder,p)
        with (self.root/'src/cvar_campaign.py').open('a') as f:f.write('\n# changed\n')
        with self.assertRaises(ValueError):run_campaign(self.root,folder,progress=False)

if __name__=='__main__':unittest.main()
