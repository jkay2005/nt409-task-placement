"""CVaR uses lower-tail probability mass, not a fraction of basis states."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from src.qubo import build_qubo
from src.qaoa_experiment import prepare_reference
from src.convergence_diagnostics import ExactQAOAOracle, run_exact_qaoa
from src.cvar_experiment import (lower_tail_cvar, ExactCVaROracle, run_cvar_qaoa,
    make_design, new_campaign, record_trial, verify_campaign, save_campaign)


class CVaRMathTests(unittest.TestCase):
    def test_fractional_boundary_and_unsorted_energies(self):
        self.assertAlmostEqual(lower_tail_cvar([10,0,2],[.75,.05,.20],.1),1.)
        self.assertAlmostEqual(lower_tail_cvar([0,2,10],[.05,.20,.75],.2),1.5)

    def test_alpha_one_is_mean_and_positive_affine_scaling_commutes(self):
        e=np.array([-2.,3.,9.]);p=np.array([.15,.25,.6])
        self.assertAlmostEqual(lower_tail_cvar(e,p,1.),p@e)
        self.assertAlmostEqual(lower_tail_cvar(7*e+13,p,.3),7*lower_tail_cvar(e,p,.3)+13)

    def test_ties_zero_mass_and_tail_within_ground_mass(self):
        self.assertAlmostEqual(lower_tail_cvar([0,2,2,10],[0,.05,.15,.8],.1),2.)
        self.assertAlmostEqual(lower_tail_cvar([1,7],[.2,.8],.1),1.)
        self.assertAlmostEqual(lower_tail_cvar([1,7],[1.,0.],1.),1.)

    def test_invalid_inputs_are_rejected(self):
        for alpha in (0,-.1,1.1,float('nan'),True):
            with self.subTest(alpha=alpha),self.assertRaises(ValueError):lower_tail_cvar([0,1],[.5,.5],alpha)
        for e,p in (([],[]),([0,1],[.2,.2]),([0,1],[-.1,1.1]),([0],[1,0]),([0,float('inf')],[.5,.5])):
            with self.subTest(e=e,p=p),self.assertRaises(ValueError):lower_tail_cvar(e,p,.1)


class CVaRRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instance={'schema_version':1,'instance_id':'cvar_test','objective':'min_active_hosts',
            'tasks':[{'id':'T0','cpu':1,'ram':1}],'hosts':[{'id':'H0','cpu':1,'ram':1}]}
        cls.bundle=build_qubo(cls.instance,assignment_penalty=3,capacity_penalty=3)
        cls.reference=prepare_reference(cls.bundle)
        cls.base=dict(shots=64,evaluation_shots=64,maxiter=12,max_seconds=300.,max_qubits=4,
            aer_threads=1,aer_memory_mb=256,min_available_gib=.01,
            hamiltonian_scaling='max_abs',cobyla_rhobeg=1.,cobyla_tol=1e-4)
        cls.design=make_design(cls.instance,cls.bundle,cls.base,
            {'common':[.3,1.],'alternative':[.8,1.2]},60,.1,{'test_baseline':'fixed'})
        cls.trial=new_campaign(cls.design)['planned_runs'][0]

    def test_oracle_matches_independent_statevector_and_alpha_one(self):
        from qiskit.circuit.library import QAOAAnsatz
        from qiskit.quantum_info import Statevector
        from src.ising import build_ising,scale_ising
        config=self.trial['config'];oracle=ExactCVaROracle(self.bundle,config,self.reference)
        operator,_=build_ising(self.bundle);operator,_=scale_ising(operator,'max_abs')
        point=[.41,1.13]
        probabilities=Statevector(QAOAAnsatz(operator,reps=1).assign_parameters(point)).probabilities()
        expected=lower_tail_cvar(oracle.energies,probabilities,.1)
        self.assertAlmostEqual(oracle.cvar(point,.1),expected,places=10)
        self.assertAlmostEqual(oracle.cvar(point,1.),oracle.evaluate(point)['exact_mean_qubo_energy'],places=10)

    def test_alpha_one_reproduces_existing_mean_runner(self):
        config=self.trial['config'];oracle=ExactCVaROracle(self.bundle,config,self.reference)
        cvar=run_cvar_qaoa(self.bundle,config,1.,self.reference,oracle,progress=False)
        mean=run_exact_qaoa(self.bundle,config,self.reference,oracle,progress=False)
        np.testing.assert_allclose(cvar['optimal_point'],mean['optimal_point'],atol=1e-8,rtol=0)
        self.assertAlmostEqual(cvar['optimizer_objective_value'],mean['exact_diagnostics']['exact_mean_qubo_energy'],places=8)
        self.assertEqual(cvar['final_samples'],mean['final_samples'])
        self.assertNotIn('optimizer_estimated_qubo_expectation',cvar)
        self.assertTrue(all(h['objective_source']=='ideal_statevector_cvar' for h in cvar['optimization_history']))

    def test_two_real_trials_resume_and_reject_modified_evidence(self):
        campaign=new_campaign(self.design)
        oracle=ExactCVaROracle(self.bundle,self.trial['config'],self.reference)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest=root/'manifest.json'
            for trial in campaign['planned_runs']:
                report=run_cvar_qaoa(self.bundle,trial['config'],.1,self.reference,oracle,progress=False)
                record_trial(root,campaign,trial,report,self.bundle,self.reference)
                save_campaign(manifest,campaign)
            loaded=json.loads(manifest.read_text(encoding='utf-8'))
            self.assertEqual(len(verify_campaign(root,loaded,self.design,self.bundle,self.reference)),2)
            self.assertEqual(loaded['remaining_run_keys'],[])
            path=root/loaded['completed_runs'][0]['report'];raw=path.read_bytes()
            r=json.loads(raw);r['objective']['alpha']=.2
            path.write_text(json.dumps(r),encoding='utf-8')
            with self.assertRaises(ValueError):verify_campaign(root,loaded,self.design,self.bundle,self.reference)
            path.write_bytes(raw)
            altered=copy.deepcopy(loaded);altered['completed_runs'][0]['exact_optimal_probability']+=.1
            with self.assertRaises(ValueError):verify_campaign(root,altered,self.design,self.bundle,self.reference)
            altered=copy.deepcopy(loaded);altered['planned_runs'][0]['config']['maxiter']+=1
            with self.assertRaises(ValueError):verify_campaign(root,altered,self.design,self.bundle,self.reference)

    def test_mean_report_cannot_be_recorded_as_cvar(self):
        campaign=new_campaign(self.design)
        report=run_exact_qaoa(self.bundle,self.trial['config'],self.reference,progress=False)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):record_trial(root,campaign,self.trial,report,self.bundle,self.reference)
            self.assertEqual(list(Path(root).rglob('*.json')),[])


if __name__=='__main__':unittest.main()
