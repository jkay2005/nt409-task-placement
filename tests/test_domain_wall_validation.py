"""N28 budget/data isolation; simulation doubles never change the 5x3 instances."""
import copy
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments import domain_wall_validation as n28
from src.domain_wall_training import identity as development_identity
from src.shot_noise_campaign import load_json, save_json
from src.validation5x3 import DATA, load_dataset
from test_domain_wall_training import CheapEvaluator

ROOT=Path(__file__).resolve().parents[1]


class ValidationLedgerTests(unittest.TestCase):
    def test_three_fixed_cases_have_separate_paid_dependencies_and_budget(self):
        plan=n28.make_plan(False)
        self.assertEqual(len(plan),18)
        self.assertEqual(sum(s['cap'] for s in plan),1800)
        self.assertEqual(sum(s['cap'] for s in n28.make_plan(True)),108)
        for k,case in enumerate(('v5x3_1','v5x3_2','v5x3_3')):
            rows=[s for s in plan if s['instance_id']==case]
            self.assertEqual(len(rows),6)
            self.assertEqual(sum(s['cap'] for s in rows),600)
            self.assertEqual({s['final_seed'] for s in rows},{20261025+k})
            for s in rows:
                if s['p']==2:
                    self.assertEqual(s['depends_on'],f"{case}__{s['variant']}_p1")
        with self.assertRaises(ValueError): n28.make_plan(1)

    def test_case_snapshots_and_protocol_are_frozen(self):
        with TemporaryDirectory() as tmp:
            out=n28.create_campaign(ROOT,Path(tmp)/'qa',software_validation=True)
            c=n28.checked_campaign(ROOT,out)
            self.assertEqual([x['input'] for x in c['identity']['cases']],load_dataset(ROOT)['validation_instances'])
            self.assertEqual([x['optimum'] for x in c['identity']['cases']],[2,3,3])
            self.assertTrue(all(x['qubits']==25 for x in c['identity']['cases']))
            self.assertEqual(out,n28.create_campaign(ROOT,out,software_validation=True))
            p=out/'inputs/v5x3_2.json';value=load_json(p);value['tasks'][0]['cpu']+=1;save_json(p,value)
            with self.assertRaises(ValueError):n28.checked_campaign(ROOT,out)

    def test_new_experiment_does_not_change_n27_identity(self):
        before=development_identity(ROOT,False)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);shutil.copytree(ROOT/'src',root/'src',ignore=shutil.ignore_patterns('__pycache__'))
            p=root/DATA;p.parent.mkdir(parents=True);shutil.copy2(ROOT/DATA,p)
            self.assertEqual(before,development_identity(root,False))
            (root/'experiments').mkdir();shutil.copy2(ROOT/n28.MODULE,root/n28.MODULE)
            with self.assertRaises(FileNotFoundError):n28.create_campaign(root,root/'primary')
            self.assertFalse((root/'primary').exists())


class ValidationExecutionTests(unittest.TestCase):
    def test_paid_case_specific_interp_resume_and_counts(self):
        with TemporaryDirectory() as tmp,patch.object(n28,'build_evaluator',return_value=CheapEvaluator()):
            out=n28.create_campaign(ROOT,Path(tmp)/'qa',software_validation=True)
            n28.run_campaign(ROOT,out,max_new_stages=1,progress=False)
            c=n28.checked_campaign(ROOT,out);first=copy.deepcopy(c['stages'])
            n28.run_campaign(ROOT,out,progress=False)
            c=n28.checked_campaign(ROOT,out);s=n28.summarize(ROOT,out)
            self.assertTrue(s['complete']);self.assertEqual(s['objective_calls_reserved'],108)
            self.assertEqual(s['simulation_calls_reserved'],135)
            self.assertEqual([x['objective_calls_reserved'] for x in s['cases']],[36,36,36])
            self.assertEqual(c['stages']['v5x3_1__standard_x_p1'],first['v5x3_1__standard_x_p1'])
            for stage in c['plan']:
                if stage['p']!=2:continue
                r=load_json(out/c['stages'][stage['id']]['path']);previous=load_json(out/c['stages'][stage['depends_on']]['path'])
                self.assertEqual(r['initial_point'],[previous['point'][0]]*2+[previous['point'][1]]*2)
                self.assertEqual(r['dependency_sha256'],c['stages'][stage['depends_on']]['sha256'])
                self.assertEqual(r['final_seed'],stage['final_seed'])
            before=load_json(out/'campaign.json');n28.run_campaign(ROOT,out,progress=False)
            self.assertEqual(before,load_json(out/'campaign.json'))
            archive=n28.export_campaign(ROOT,out)
            self.assertTrue(archive.is_file())

    def test_failure_reserves_budget_blocks_retries_and_exports_partial_evidence(self):
        with TemporaryDirectory() as tmp,patch.object(n28,'build_evaluator',return_value=CheapEvaluator()),patch.object(CheapEvaluator,'mean_energy',side_effect=MemoryError('simulation failed')):
            out=n28.create_campaign(ROOT,Path(tmp)/'qa',software_validation=True)
            n28.run_campaign(ROOT,out,progress=False)
            s=n28.summarize(ROOT,out);self.assertFalse(s['complete']);self.assertEqual(s['objective_calls_reserved'],1)
            with self.assertRaises(RuntimeError):n28.run_campaign(ROOT,out,progress=False)
            self.assertTrue(n28.export_campaign(ROOT,out).is_file())

    def test_filters_cannot_skip_a_planned_case_or_variant(self):
        with TemporaryDirectory() as tmp:
            out=n28.create_campaign(ROOT,Path(tmp)/'qa',software_validation=True)
            with self.assertRaises(ValueError):n28.run_campaign(ROOT,out,instance_id='v5x3_2',progress=False)
            with self.assertRaises(ValueError):n28.run_campaign(ROOT,out,variant='valid_dw',progress=False)
            with self.assertRaises(ValueError):n28.run_campaign(ROOT,out,instance_id='a3_dev_n5',progress=False)
            (out/'RUNNING.lock').write_text('other writer')
            with self.assertRaises(FileExistsError):n28.run_campaign(ROOT,out,progress=False)
            with self.assertRaises(RuntimeError):n28.export_campaign(ROOT,out)

    def test_builder_rejects_development_and_mutated_validation(self):
        from src.three_host_encoding import build_three_host_qubo
        data=load_dataset(ROOT)
        with self.assertRaises(ValueError):n28.build_evaluator(build_three_host_qubo(data['development_instance']),1,'valid_dw',ROOT)
        changed=copy.deepcopy(data['validation_instances'][0]);changed['tasks'][0]['ram']+=1
        with self.assertRaises(ValueError):n28.build_evaluator(build_three_host_qubo(changed),1,'standard_x',ROOT)

    def test_primary_pointer_requires_completed_n27_then_resumes_without_recreation(self):
        from src import domain_wall_training as n27
        with TemporaryDirectory() as tmp,patch.object(n27,'build_evaluator',return_value=CheapEvaluator()):
            root=Path(tmp);shutil.copytree(ROOT/'src',root/'src',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'experiments').mkdir();shutil.copy2(ROOT/n28.MODULE,root/n28.MODULE)
            p=root/DATA;p.parent.mkdir(parents=True);shutil.copy2(ROOT/DATA,p)
            previous=n27.open_campaign(root)
            with self.assertRaises(ValueError):n28.open_campaign(root)
            n27.run_campaign(root,previous,progress=False)
            before=load_json(previous/'campaign.json')
            first=n28.open_campaign(root)
            self.assertEqual(first,n28.open_campaign(root))
            self.assertEqual(before,load_json(previous/'campaign.json'))
            self.assertFalse(n28.checked_campaign(root,first)['identity']['software_validation'])
            self.assertEqual(n28.summarize(root,first)['objective_cap'],1800)
            self.assertEqual(len(list(first.parent.glob('t4c_*'))),1)

    def test_source_runtime_raw_tampering_and_interrupted_stage_are_retained(self):
        from src.shot_noise_campaign import file_hash
        with TemporaryDirectory() as tmp,patch.object(n28,'build_evaluator',return_value=CheapEvaluator()):
            out=n28.create_campaign(ROOT,Path(tmp)/'qa',software_validation=True)
            n28.run_campaign(ROOT,out,max_new_stages=1,progress=False)
            c=n28.checked_campaign(ROOT,out);key=c['plan'][0]['id'];path=out/c['stages'][key]['path']
            r=load_json(path);r['status']='running';del r['completed_objective_calls'];save_json(path,r)
            c['stages'][key].update(status='running',sha256=file_hash(path));save_json(out/'campaign.json',c)
            self.assertFalse(n28.summarize(ROOT,out)['complete'])
            self.assertTrue(n28.export_campaign(ROOT,out).exists())
            with self.assertRaises(RuntimeError):n28.run_campaign(ROOT,out,progress=False)
            r['point'][0]+=1;save_json(path,r)
            with self.assertRaises(ValueError):n28.checked_campaign(ROOT,out)
        with TemporaryDirectory() as tmp:
            out=n28.create_campaign(ROOT,Path(tmp)/'qa',software_validation=True)
            env=n28.experiment_environment();env['runtime']['python_version']='changed'
            with patch.object(n28,'experiment_environment',return_value=env):
                with self.assertRaises(ValueError):n28.checked_campaign(ROOT,out)
            (out/'source'/n28.MODULE).write_text('changed')
            with self.assertRaises(ValueError):n28.checked_campaign(ROOT,out)


if __name__=='__main__':unittest.main()
