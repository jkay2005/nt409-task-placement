import unittest
from unittest.mock import patch
from test_two_host_encoding import tiny_instance
from src.two_host_encoding import build_two_host_qubo, compact_reference
from src.two_host_runner import run_compact_trial, probe_compact, audit_compact_report


class TwoHostRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=build_two_host_qubo(tiny_instance());cls.reference=compact_reference(cls.bundle)
        cls.config=dict(shots=64,evaluation_shots=64,maxiter=8,max_seconds=120.,max_qubits=23,
            aer_threads=1,aer_memory_mb=2048,min_available_gib=.01,hamiltonian_scaling='max_abs',
            cobyla_rhobeg=1.,cobyla_tol=1e-4,seed=70,evaluation_seed=100070,reps=1,initial_point=[.3,1.])
        cls.policy=dict(start_available_min_gib=.01,remaining_available_min_gib=.01,process_rss_stop_gib=4.)

    def test_real_final_counts_decoder_and_audit(self):
        r=run_compact_trial(self.bundle,self.config,self.policy,self.reference,progress=False)
        self.assertEqual(r['status'],'completed',r.get('stop_reason'))
        audit_compact_report(self.bundle,r,self.config,self.reference)
        self.assertEqual(sum(round(s['probability']*64) for s in r['final_samples']),64)
        self.assertTrue(all(s['decoded']['one_hot_ok'] for s in r['final_samples']))
        self.assertEqual(r['algorithm_sampler_shots'],(r['cost_function_evals']+1)*64)
        self.assertEqual(r['total_algorithm_shots'],r['algorithm_sampler_shots']+64)
        r['metrics']['feasible_probability']+=1/64
        with self.assertRaises(ValueError):audit_compact_report(self.bundle,r,self.config,self.reference)

    def test_resource_stop_precedes_backend_and_preserves_failure(self):
        with patch('src.two_host_runner._aer_components',side_effect=AssertionError('backend called')):
            r=run_compact_trial(self.bundle,self.config,{**self.policy,'start_available_min_gib':1e9},self.reference,False)
        self.assertEqual(r['status'],'resource_blocked')
        self.assertNotIn('benchmark_output',r)

    def test_probe_uses_all_layers_and_measures_final_batch(self):
        c={**self.config,'reps':3,'initial_point':[.3,0.,0.,1.,0.,0.]}
        r=probe_compact(self.bundle,c,self.policy,self.reference)
        self.assertEqual(r['status'],'passed',r)
        self.assertEqual(len(r['active_points']),3)
        self.assertTrue(all(all(v!=0 for v in point) for point in r['active_points']))


if __name__=='__main__':unittest.main()
