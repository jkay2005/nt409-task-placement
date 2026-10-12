import json
from pathlib import Path
import unittest
import tempfile

from src.branch_a_summary import (structured_reference, solve_classical,
    batch_success, measure_classical, aggregate_rows, export_summary)
from src.placement import evaluate_placement

ROOT = Path(__file__).resolve().parents[1]


class SummaryControlsTests(unittest.TestCase):
    def instance(self, name):
        return json.loads((ROOT/'data/instances'/f'{name}.json').read_text())

    def test_exact_controls_and_solutions_match_original_validator(self):
        for name, feasible, optimal, optimum in [('p1_choice',11,1,1),
                ('p1_tight',4,4,2),('p0_reference',1,1,2),('p1_infeasible',0,0,None)]:
            instance=self.instance(name);r=structured_reference(instance)
            self.assertEqual((r['assignments'],r['feasible_count'],r['optimal_count'],r['optimum']),
                             (16,feasible,optimal,optimum))
            result=solve_classical(instance,'exact_enumeration')
            self.assertEqual(result['best_objective'],optimum)
            self.assertEqual(result['evaluations'],16)
            if optimum is not None:
                decoded=evaluate_placement(instance,result['best_placement'])
                self.assertTrue(decoded['feasible']);self.assertEqual(decoded['objective'],optimum)

    def test_random_samples_without_repair_and_fixed_draw_budget(self):
        instance=self.instance('p1_choice')
        a=solve_classical(instance,'random_assignment',shots=1024,seed=123)
        self.assertEqual(a,solve_classical(instance,'random_assignment',shots=1024,seed=123))
        self.assertEqual(a['evaluations'],1024)
        self.assertLess(a['feasible_draws'],1024)
        self.assertEqual(evaluate_placement(instance,a['best_placement'])['objective'],a['best_objective'])
        r=solve_classical(self.instance('p1_infeasible'),'random_assignment',shots=32)
        self.assertIsNone(r['best_objective']);self.assertEqual(r['feasible_draws'],0)

    def test_batch_probability_and_infeasible_are_not_conflated(self):
        self.assertIsNone(batch_success(None,1024))
        self.assertEqual(batch_success(0,1024),0)
        self.assertEqual(batch_success(1,1024),1)
        self.assertAlmostEqual(batch_success(.25,2),.4375)
        with self.assertRaises(ValueError):batch_success(.1,0)

    def test_timing_records_real_blocks_without_asserting_machine_speed(self):
        r=measure_classical(self.instance('p1_choice'),blocks=3,target_seconds=.001,max_calls=8,shots=16)
        self.assertEqual({x['method'] for x in r},{'exact_enumeration','random_assignment'})
        for x in r:
            self.assertEqual(len(x['block_seconds']),3)
            self.assertGreater(x['seconds_median'],0)
            self.assertGreaterEqual(x['calls_per_block'],1)
            self.assertEqual(x['reference_optimum'],1)

    def test_aggregation_distinguishes_shot_quality_and_run_success(self):
        base=dict(instance_id='p1_choice',role='benchmark',status='completed',encoding='two_host_binary_v1',p=1,
            evaluation_shots=1024,feasible_probability=.25,ground_probability=0,
            uniform_optimal_probability=.015625,found_valid=True,nfev=30,total_algorithm_shots=32768,
            total_seconds=2.,sample_mean_energy=5.,num_qubits=16)
        rows=[dict(base,seed=s,optimal_probability=v,found_optimal=v>0) for s,v in [(70,0.),(71,.125)]]
        r=aggregate_rows(rows,{'p1_choice':structured_reference(self.instance('p1_choice'))})[0]
        self.assertEqual(r['optimal_probability'],.0625)
        self.assertEqual(r['observed_run_success'],.5)
        self.assertEqual(r['optimal_count'],128)
        self.assertEqual(r['lift_structured_random'],1.)
        self.assertEqual(r['total_seconds'],4.)
        self.assertEqual(r['optimal_probability_sd'],2**.5/16)
        with self.assertRaises(ValueError):aggregate_rows(rows+[rows[0]],{'p1_choice':structured_reference(self.instance('p1_choice'))})

    def test_export_binds_unchanged_source_and_complete_checksums(self):
        from src.branch_a_evidence import digest,read_verified_zip
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'input.zip';source.write_bytes(b'fixed source fixture')
            evidence=dict(rows=[dict(instance_id='fixture')],archive_sha256=digest(source.read_bytes()),
                baseline_sha256='fixture',audit_seconds=0.,sources={})
            out=export_summary(root/'summary',source,evidence,{},[{'method':'control'}],
                [{'p':1}],[{'method':'exact','block_seconds':[.01,.02,.03]}],{'blocks':3})
            content=read_verified_zip(out.read_bytes())
            self.assertEqual(content['notebook17_results.zip'],source.read_bytes())
            self.assertEqual(json.loads(content['summary.json'])['metadata']['input_sha256'],evidence['archive_sha256'])
            source.write_bytes(b'changed')
            with self.assertRaises(ValueError):export_summary(root/'summary',source,evidence,{},[],[],[],{})


if __name__=='__main__':unittest.main()
