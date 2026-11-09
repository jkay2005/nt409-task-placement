"""Campaign control tests use a cheap evaluator double, never a smaller instance."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import shutil
import numpy as np

from src.domain_wall_training import create_campaign, checked_campaign, make_plan
from src.shot_noise_campaign import load_json, save_json
from src.domain_wall_training import run_campaign, summarize, export_campaign, open_campaign

ROOT = Path(__file__).resolve().parents[1]


class DomainWallTrainingLedgerTests(unittest.TestCase):
    def test_scientific_budget_and_separate_software_validation(self):
        plan=make_plan(False)
        self.assertEqual(len(plan),6)
        self.assertEqual(sum(s['cap'] for s in plan),600)
        self.assertEqual([s['p'] for s in plan],[1,2,1,2,1,2])
        self.assertEqual(sum(s['cap'] for s in make_plan(True)),36)
        with self.assertRaises(ValueError): make_plan(1)

    def test_create_resume_and_reject_changed_ledger(self):
        with TemporaryDirectory() as tmp:
            out=create_campaign(ROOT,Path(tmp)/'run')
            c=checked_campaign(ROOT,out)
            self.assertEqual(c['identity']['input']['instance_id'],'a3_dev_n5')
            self.assertEqual(c['identity']['qubits'],25)
            self.assertEqual(out,create_campaign(ROOT,out))
            with self.assertRaises(ValueError): create_campaign(ROOT,out,software_validation=True)
            c['plan'][0]['cap']=101;save_json(out/'campaign.json',c)
            with self.assertRaises(ValueError): checked_campaign(ROOT,out)


class CheapEvaluator:
    """Simulation boundary double, not a smaller scientific placement problem."""
    size=25;offset=248.5;scaling={'scale':65.5};compiled_depth=39;compiled_ops={'crx':10}
    def mean_energy(self,point): return 100.+float(np.square(point).sum())
    def exact(self,point):
        return dict(mean_energy=self.mean_energy(point),p_domain=1.,p_valid=.02,p_opt=.001,p_ground=.000001)
    def sample(self,point,shots,seed): return {'0'*25:shots}
    def score_counts(self,counts): return {'valid_count':0,'optimal_count':0,'ground_count':0}


class DomainWallTrainingExecutionTests(unittest.TestCase):
    def test_resume_charges_interp_and_preserves_completed_stages(self):
        with TemporaryDirectory() as tmp, patch('src.domain_wall_training.build_evaluator',return_value=CheapEvaluator()):
            out=create_campaign(ROOT,Path(tmp)/'run',software_validation=True)
            run_campaign(ROOT,out,max_new_stages=1,progress=False)
            c=checked_campaign(ROOT,out);entry=copy.deepcopy(c['stages']['standard_x_p1'])
            run_campaign(ROOT,out,progress=False)
            c=checked_campaign(ROOT,out)
            self.assertEqual(c['stages']['standard_x_p1'],entry)
            a=load_json(out/'raw/standard_x_p1.json');b=load_json(out/'raw/standard_x_p2.json')
            self.assertEqual(b['initial_point'],[a['point'][0]]*2+[a['point'][1]]*2)
            self.assertEqual(b['dependency_sha256'],entry['sha256'])
            self.assertEqual(a['point'],min(a['history'],key=lambda r:r['mean_energy'])['point'])
            self.assertEqual(a['calls']['final_sampling'],0)
            self.assertEqual(b['calls']['final_sampling'],1)
            self.assertLessEqual(summarize(ROOT,out)['objective_calls_reserved'],36)
            self.assertTrue(summarize(ROOT,out)['complete'])
            before=load_json(out/'campaign.json');run_campaign(ROOT,out,progress=False)
            self.assertEqual(before,load_json(out/'campaign.json'))
            self.assertTrue(export_campaign(ROOT,out).is_file())
            r=load_json(out/'raw/standard_x_p1.json');r['point'][0]=999;save_json(out/'raw/standard_x_p1.json',r)
            with self.assertRaises(ValueError): checked_campaign(ROOT,out)

    def test_failed_evaluation_is_reserved_and_cannot_get_fresh_budget(self):
        with TemporaryDirectory() as tmp, patch('src.domain_wall_training.build_evaluator',return_value=CheapEvaluator()), patch.object(CheapEvaluator,'mean_energy',side_effect=MemoryError('test boundary failure')):
            out=create_campaign(ROOT,Path(tmp)/'run',software_validation=True)
            run_campaign(ROOT,out,progress=False)
            r=load_json(out/'raw/standard_x_p1.json')
            self.assertEqual(r['status'],'failed');self.assertEqual(r['calls']['objective'],1)
            self.assertEqual(r['history'][0]['status'],'in_flight')
            before=load_json(out/'campaign.json')
            with self.assertRaises(RuntimeError): run_campaign(ROOT,out,progress=False)
            self.assertEqual(before,load_json(out/'campaign.json'))
            self.assertFalse(summarize(ROOT,out)['complete'])

    def test_writer_lock_prevents_second_runner(self):
        with TemporaryDirectory() as tmp:
            out=create_campaign(ROOT,Path(tmp)/'run',software_validation=True)
            (out/'RUNNING.lock').write_text('other process')
            with self.assertRaises(FileExistsError): run_campaign(ROOT,out,progress=False)

    def test_notebook_pointer_survives_reexecution_without_creating_another_campaign(self):
        from src.validation5x3 import DATA
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copytree(ROOT/'src',root/'src',ignore=shutil.ignore_patterns('__pycache__'))
            p=root/DATA;p.parent.mkdir(parents=True);shutil.copy2(ROOT/DATA,p)
            first=open_campaign(root)
            self.assertEqual(first,open_campaign(root))
            self.assertFalse(checked_campaign(root,first)['identity']['software_validation'])
            self.assertEqual(len(list(first.parent.glob('t4b_*'))),1)

    def test_runtime_change_prevents_cross_machine_resume(self):
        from src.domain_wall_training import experiment_environment
        with TemporaryDirectory() as tmp:
            out=create_campaign(ROOT,Path(tmp)/'run')
            env=experiment_environment();env['runtime']['python_version']='changed'
            with patch('src.domain_wall_training.experiment_environment',return_value=env):
                with self.assertRaises(ValueError): checked_campaign(ROOT,out)

    def test_snapshot_and_raw_report_tampering_are_detected(self):
        with TemporaryDirectory() as tmp:
            out=create_campaign(ROOT,Path(tmp)/'run')
            p=out/'input.json';value=load_json(p);value['tasks'][0]['cpu']=2;save_json(p,value)
            with self.assertRaises(ValueError): checked_campaign(ROOT,out)


if __name__=='__main__': unittest.main()
