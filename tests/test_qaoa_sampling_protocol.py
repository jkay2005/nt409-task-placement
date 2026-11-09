"""Regression: final scoring uses a fresh seed and exposes numeric stopping."""
import json
from pathlib import Path
import unittest
import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit_aer.primitives import SamplerV2
from src.qubo import build_qubo
from src.ising import build_ising
from src.qaoa_experiment import run_qaoa_experiment, _aer_components


class SamplingProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=build_qubo({'schema_version':1,'instance_id':'sampling_regression',
            'objective':'min_active_hosts','tasks':[{'id':'T0','cpu':1,'ram':1}],
            'hosts':[{'id':'H0','cpu':1,'ram':1}]})
        cls.config=dict(seed=60,evaluation_seed=100060,shots=64,evaluation_shots=128,
            reps=1,maxiter=6,max_qubits=23,max_seconds=300,aer_threads=2,aer_memory_mb=2048)

    def test_final_counts_are_from_declared_independent_seed(self):
        r=run_qaoa_experiment(self.bundle,self.config,progress=False)
        self.assertEqual(r['sampling_protocol'],'independent_final_v1')
        self.assertEqual(r['sampling']['evaluation_seed'],100060)
        self.assertEqual(r['sampling']['evaluation_shots'],128)
        op,_=build_ising(self.bundle)
        _,_,manager,options=_aer_components(self.config)
        circuit=QAOAAnsatz(cost_operator=op,reps=1);circuit.measure_all()
        circuit=manager.run(circuit)
        sampler=SamplerV2(default_shots=128,seed=100060,options={'backend_options':options})
        counts=sampler.run([(circuit,r['optimal_point'])]).result()[0].data.meas.get_counts()
        actual={''.join(str(b) for b in s['bits'][::-1]):round(s['probability']*128) for s in r['final_samples']}
        self.assertEqual(actual,counts)
        self.assertEqual(r['optimizer_stop']['nfev'],r['cost_function_evals'])
        self.assertIsInstance(r['optimizer_stop']['success'],bool)
        self.assertTrue(r['optimizer_stop']['message'])
        self.assertGreaterEqual(r['sampling_statistics']['evaluation']['mean_standard_error'],0)
        self.assertEqual(r['sampling_statistics']['evaluation']['shots'],128)

    def test_same_seed_for_training_and_evaluation_is_rejected(self):
        with self.assertRaises(ValueError):
            run_qaoa_experiment(self.bundle,{**self.config,'evaluation_seed':60},progress=False)

    def test_default_evaluation_seed_is_distinct_and_reproducible(self):
        cfg={k:v for k,v in self.config.items() if k not in ('evaluation_seed','evaluation_shots')}
        a=run_qaoa_experiment(self.bundle,cfg,progress=False)
        b=run_qaoa_experiment(self.bundle,cfg,progress=False)
        self.assertNotEqual(a['sampling']['evaluation_seed'],cfg['seed'])
        self.assertEqual(a['sampling'],b['sampling'])
        self.assertEqual(a['final_samples'],b['final_samples'])


if __name__=='__main__':unittest.main()
