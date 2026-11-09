"""N29 quality checks use the four locked 5x3 cases, never resized fixtures."""
import copy
from pathlib import Path
import unittest
from experiments import classical_validation as n29
from src.classical_baselines import solve_heuristic
from src.placement import evaluate_placement

ROOT=Path(__file__).resolve().parents[1]

class ClassicalQualityTests(unittest.TestCase):
    def test_frozen_scope_and_independent_truth(self):
        cases=n29.case_inputs(ROOT)
        self.assertEqual([x['instance_id'] for x in cases],list(n29.CASE_IDS))
        self.assertTrue(all(len(x['tasks'])==5 and len(x['hosts'])==3 for x in cases))
        refs=[n29.reference(x) for x in cases]
        self.assertEqual([r['optimum'] for r in refs],[2,2,3,3])
        self.assertEqual([r['feasible_assignments'] for r in refs],[90,78,1,14])

    def test_heuristic_failure_is_not_an_infeasibility_certificate(self):
        inp=n29.case_inputs(ROOT)[2]
        for alg in ('FirstFit','BFD'):
            r=solve_heuristic(inp,alg);scored=n29.assess_result(inp,r,n29.reference(inp))
            self.assertFalse(scored['found_valid'])
            self.assertEqual(scored['status'],'no_placement_found')
            self.assertFalse(scored['solver_certified_infeasible'])
            self.assertIsNone(scored['oracle_objective_gap'])

    def test_oracle_match_does_not_upgrade_solver_certificate(self):
        inp=n29.case_inputs(ROOT)[1]
        r=solve_heuristic(inp,'FirstFit');checked=evaluate_placement(inp,[0,2,2,0,2])
        r.update(algorithm='MILP',status='feasible_not_proven',found_valid=True,
                 placement=checked['placement'],x=checked['x'],y=checked['y'],objective=2,
                 solver_bound=1.,solver_gap=.5)
        s=n29.assess_result(inp,r,n29.reference(inp))
        self.assertTrue(s['matches_oracle']);self.assertFalse(s['solver_certified_optimal'])
        self.assertEqual(s['oracle_objective_gap'],0)
        self.assertEqual(s['solver_gap'],.5)

    def test_invalid_explicit_y_and_false_certificate_are_rejected(self):
        inp=n29.case_inputs(ROOT)[1];r=solve_heuristic(inp,'FirstFit')
        broken=copy.deepcopy(r);broken['y']=[0,0,0]
        with self.assertRaises(ValueError):n29.assess_result(inp,broken,n29.reference(inp))
        broken=copy.deepcopy(r);broken.update(algorithm='MILP',status='optimal',solver_certified_optimal=True,solver_bound=3.,solver_gap=0.)
        with self.assertRaises(ValueError):n29.assess_result(inp,broken,n29.reference(inp))
        broken=copy.deepcopy(r);broken['placement'][0]=(broken['placement'][0]+1)%3
        with self.assertRaises(ValueError):n29.assess_result(inp,broken,n29.reference(inp))

    def test_optimal_certificate_requires_a_matching_finite_bound(self):
        inp=n29.case_inputs(ROOT)[3];r=solve_heuristic(inp,'FirstFit')
        r.update(algorithm='MILP',status='optimal',solver_certified_optimal=True,solver_bound=2.,solver_gap=1/3)
        with self.assertRaises(ValueError):n29.assess_result(inp,r,n29.reference(inp))
        r.update(solver_bound=None,solver_gap=None)
        with self.assertRaises(ValueError):n29.assess_result(inp,r,n29.reference(inp))

class QuantumEvidenceTests(unittest.TestCase):
    def test_missing_predecessor_and_outside_pointer_are_rejected(self):
        from tempfile import TemporaryDirectory
        from src.shot_noise_campaign import save_json
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(FileNotFoundError):n29.quantum_evidence(root)
            p=root/'data/reference_results/phase5_domainwall_training/N27_ACTIVE.json'
            save_json(p,{'relative_folder':'../../outside'})
            with self.assertRaises(ValueError):n29.quantum_evidence(root)

from tempfile import TemporaryDirectory
import shutil
from unittest.mock import patch
from src.shot_noise_campaign import load_json,save_json

class ClassicalCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'repo';self.root.mkdir()
        shutil.copytree(ROOT/'src',self.root/'src',ignore=shutil.ignore_patterns('__pycache__'))
        p=self.root/'data/benchmarks/nt409_validation5x3_v1/dataset.json';p.parent.mkdir(parents=True);shutil.copy2(ROOT/p.relative_to(self.root),p)
        (self.root/'experiments').mkdir();shutil.copy2(ROOT/n29.MODULE,self.root/n29.MODULE)
        self.runtime=patch.object(n29,'runtime_preflight',return_value={'test_only':True});self.runtime.start();self.addCleanup(self.runtime.stop)
        self.evidence=patch.object(n29,'quantum_evidence',return_value={'receipts':{},'rows':[]});self.evidence.start();self.addCleanup(self.evidence.stop)

    def test_pointer_reopens_same_campaign_and_snapshots_all_four_inputs(self):
        folder=n29.open_campaign(self.root)
        self.assertEqual(folder,n29.open_campaign(self.root))
        c=n29.checked_campaign(self.root,folder)
        self.assertEqual(len(c['identity']['cases']),4)
        self.assertEqual(len(list((folder/'inputs').glob('*.json'))),4)
        self.assertEqual(c['cases'],{})

    def test_changed_source_runtime_input_snapshot_are_rejected(self):
        folder=n29.open_campaign(self.root)
        with patch.object(n29,'runtime_preflight',return_value={'test_only':'changed'}):
            with self.assertRaises(ValueError):n29.checked_campaign(self.root,folder)
        p=folder/'inputs/v5x3_1.json';value=load_json(p);original=copy.deepcopy(value);value['tasks'][0]['cpu']+=1;save_json(p,value)
        with self.assertRaises(ValueError):n29.checked_campaign(self.root,folder)
        save_json(p,original)
        (folder/'source'/n29.MODULE).write_text('changed')
        with self.assertRaises(ValueError):n29.checked_campaign(self.root,folder)

    def test_completed_case_reopens_without_spending_another_solve(self):
        folder=n29.open_campaign(self.root)
        # This test double only exercises the ledger, not MILP correctness.
        def fixture(inp,**kwargs):
            r=solve_heuristic(inp,'FirstFit')
            r.update(algorithm='MILP',status='feasible_not_proven',model_lp='test fixture')
            return r
        with patch.object(n29,'solve_milp',side_effect=fixture) as solver:
            n29.run_campaign(self.root,folder,'a3_dev_n5',progress=False)
            n29.run_campaign(self.root,folder,'a3_dev_n5',progress=False)
            self.assertEqual(solver.call_count,1)
        r=load_json(folder/'raw/a3_dev_n5.json')
        self.assertEqual(r['status'],'completed');self.assertEqual(len(r['attempts']),3)
        self.assertFalse(r['results'][-1]['solver_certified_optimal'])
        (folder/r['results'][-1]['model_lp_file']).write_text('changed')
        with self.assertRaises(ValueError):n29.checked_campaign(self.root,folder)

    def test_interrupted_solver_is_recorded_and_cannot_be_silently_retried(self):
        folder=n29.open_campaign(self.root)
        with patch.object(n29,'solve_milp',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):n29.run_campaign(self.root,folder,'a3_dev_n5',progress=False)
        r=load_json(folder/'raw/a3_dev_n5.json')
        self.assertEqual(r['status'],'interrupted');self.assertEqual(len(r['attempts']),3)
        self.assertEqual(len(r['results']),2);self.assertEqual(r['attempts'][-1]['status'],'interrupted')
        self.assertFalse((folder/'RUNNING.lock').exists())
        with patch.object(n29,'solve_milp') as solver:
            with self.assertRaises(RuntimeError):n29.run_campaign(self.root,folder,'a3_dev_n5',progress=False)
            solver.assert_not_called()

    def test_case_order_and_exclusive_lock_are_enforced(self):
        folder=n29.open_campaign(self.root)
        with self.assertRaises(ValueError):n29.run_campaign(self.root,folder,'v5x3_1',progress=False)
        with self.assertRaises(ValueError):n29.run_campaign(self.root,folder,'unknown',progress=False)
        (folder/'RUNNING.lock').write_text('test lock')
        with self.assertRaises(FileExistsError):n29.run_campaign(self.root,folder,'a3_dev_n5',progress=False)

    def test_partial_summary_exports_failure_without_inventing_results(self):
        import zipfile
        folder=n29.open_campaign(self.root)
        with patch.object(n29,'solve_milp',side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):n29.run_campaign(self.root,folder,'a3_dev_n5',progress=False)
        s=n29.summarize(self.root,folder)
        self.assertEqual(s['completed_cases'],0);self.assertEqual(s['solver_attempts'],3)
        self.assertFalse(s['all_milp_certified']);self.assertEqual(len(s['classical_rows']),2)
        self.assertEqual([r['status'] for r in s['cases']],['failed','pending','pending','pending'])
        archive=n29.export_campaign(self.root,folder)
        with zipfile.ZipFile(archive) as z:
            self.assertIsNone(z.testzip())
            self.assertIn('raw/a3_dev_n5.json',z.namelist())
        manifest=load_json(folder/'SHA256.json')
        self.assertEqual(set(manifest),{p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p!=folder/'SHA256.json'})
        self.assertTrue(all(n29.file_hash(folder/p)==h for p,h in manifest.items()))
        (folder/'RUNNING.lock').write_text('test lock')
        with self.assertRaises(RuntimeError):n29.export_campaign(self.root,folder)
