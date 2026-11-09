from copy import deepcopy
import unittest
from src.three_host_encoding import build_three_host_qubo,three_host_reference
from src.three_host_runner import run_three_host_trial,probe_three_host,audit_three_host_report
from test_three_host_encoding import instance


def config():
    return dict(shots=32,evaluation_shots=32,reps=1,seed=190,evaluation_seed=100190,
        maxiter=12,max_seconds=60.,max_qubits=25,aer_threads=1,aer_memory_mb=2048,
        min_available_gib=.1,hamiltonian_scaling='max_abs',cobyla_rhobeg=1.,cobyla_tol=1e-4,
        initial_point=[.3,1.])


POLICY=dict(start_available_min_gib=.1,remaining_available_min_gib=.1,process_rss_stop_gib=4.)


class ThreeHostRunnerTests(unittest.TestCase):
    def test_measured_trial_counts_independent_final_and_semantic_tamper(self):
        b=build_three_host_qubo(instance());ref=three_host_reference(b);c=config()
        r=run_three_host_trial(b,c,POLICY,ref,progress=False)
        self.assertEqual(r['status'],'completed',r.get('stop_reason'))
        audit_three_host_report(b,r,c,ref)
        self.assertEqual(sum(r['final_counts'].values()),32)
        self.assertEqual(r['total_algorithm_shots'],sum(r['algorithm_sampler_batches'])+32)
        self.assertGreaterEqual(len(r['algorithm_sampler_batches']),r['cost_function_evals']+1)
        self.assertEqual(r['sampling']['evaluation_seed'],100190)
        for field in ['metrics','benchmark_output','parameter_names']:
            bad=deepcopy(r)
            if field=='metrics':bad[field]['invalid_domain_probability']+=.1
            elif field=='benchmark_output':bad[field]['found_valid']=not bad[field]['found_valid']
            else:bad[field]=['gamma','beta']
            with self.assertRaises(ValueError):audit_three_host_report(b,bad,c,ref)

    def test_probe_and_resource_block_preserve_failure_status(self):
        b=build_three_host_qubo(instance());ref=three_host_reference(b);c=config()
        p=probe_three_host(b,c,POLICY,ref)
        self.assertEqual(p['status'],'passed',p.get('stop_reason'))
        self.assertEqual(len(p['evaluation_seconds']),3)
        self.assertTrue(all(v!=0 for x in p['active_points'] for v in x))
        blocked=run_three_host_trial(b,c,{**POLICY,'start_available_min_gib':1e9},ref,progress=False)
        self.assertEqual(blocked['status'],'resource_blocked')
        self.assertNotIn('benchmark_output',blocked)
