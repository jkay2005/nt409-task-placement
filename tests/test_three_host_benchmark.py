import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from src.three_host_benchmark import (candidate_pool, freeze_benchmark, load_three_host_benchmark,
    required_lift, solve_assignment, measure_assignment)
from src.three_host_encoding import placement_reference
from src.branch_a_summary import batch_success


class ThreeHostBenchmarkTests(unittest.TestCase):
    def test_pool_counts_and_information_band_are_reproduced(self):
        for n,total,info in [(4,508,146),(5,82,47)]:
            p=candidate_pool(n)
            self.assertEqual(len(p),total)
            self.assertEqual(sum(.2<=r['uniform_batch_success']<=.7 for r in p),info)

    def test_frozen_split_replays_and_loader_rejects_mutation(self):
        with TemporaryDirectory() as a,TemporaryDirectory() as b:
            ma=freeze_benchmark(a);mb=freeze_benchmark(b)
            self.assertEqual(ma,mb)
            c=load_three_host_benchmark(a,expected_hash=ma['design_sha256'])
            roles=[r['role'] for r in ma['instances']]
            self.assertEqual(roles.count('development'),2);self.assertEqual(roles.count('test'),6)
            self.assertEqual(roles.count('functional_control'),2)
            signatures=[r['structural_signature'] for r in ma['instances']]
            self.assertEqual(len(signatures),len(set(signatures)))
            for row in ma['instances']:
                self.assertLessEqual(row['num_qubits'],25)
                if row['role']!='functional_control':
                    self.assertEqual(row['optimum'],2)
                    self.assertTrue(.2<=row['uniform_batch_success']<=.7)
                    self.assertGreater(placement_reference(c['instances'][row['instance_id']])['histogram']['3'],0)
            path=Path(a)/ma['instances'][0]['path'];i=json.loads(path.read_text());i['tasks'][0]['cpu']+=1
            path.write_text(json.dumps(i))
            with self.assertRaises(ValueError):load_three_host_benchmark(a,expected_hash=ma['design_sha256'])

    def test_lift_exact_formula_and_classical_result_without_oracle(self):
        q=6/8192;lift=required_lift(q,.8,1024)
        self.assertAlmostEqual(batch_success(lift*q,1024),.8)
        with TemporaryDirectory() as root:
            m=freeze_benchmark(root);c=load_three_host_benchmark(root,expected_hash=m['design_sha256'])
            for i in c['instances'].values():
                result=solve_assignment(i,'exact_enumeration')
                ref=placement_reference(i)
                self.assertEqual(result['best_objective'],ref['optimum'])
                self.assertEqual(result['evaluations'],ref['assignments'])
            i=c['instances']['a3_dev_n4']
            r=solve_assignment(i,'random_assignment',draws=13,seed=1)
            self.assertEqual(r,solve_assignment(i,'random_assignment',draws=13,seed=1))
            timings=measure_assignment(i,blocks=3,target_seconds=.001)
            self.assertTrue(all(len(t['block_seconds'])==3 and t['seconds_median']>0 for t in timings))
