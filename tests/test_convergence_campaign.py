"""Campaign resume must reject changed evidence, not merely trust the table."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from src.qubo import build_qubo
from src.qaoa_experiment import prepare_reference, run_qaoa_experiment
from src.convergence_diagnostics import ExactQAOAOracle, run_exact_qaoa
from src.convergence_campaign import make_design, make_trials, new_campaign, record_trial, verify_campaign, save_campaign


class ConvergenceCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instance = {'schema_version':1,'instance_id':'campaign_test','objective':'min_active_hosts',
            'tasks':[{'id':'T0','cpu':1,'ram':1}], 'hosts':[{'id':'H0','cpu':1,'ram':1}]}
        cls.bundle = build_qubo(cls.instance,assignment_penalty=3,capacity_penalty=3)
        cls.reference = prepare_reference(cls.bundle)
        cls.base = dict(shots=32,evaluation_shots=64,maxiter=6,max_qubits=4,max_seconds=300.,
            aer_threads=1,aer_memory_mb=256,min_available_gib=.01,hamiltonian_scaling='max_abs',
            cobyla_rhobeg=1.,cobyla_tol=1e-4)

    def test_matrix_has_three_sampled_seeds_but_one_exact_trial_per_start(self):
        design=make_design(self.instance,self.bundle,[60,61,62],self.base)
        trials=make_trials(design)
        self.assertEqual(len(trials),8)
        self.assertEqual(sum(t['objective_mode']=='exact' for t in trials),2)
        self.assertEqual(len({t['run_key'] for t in trials}),8)
        for t in trials:
            self.assertNotEqual(t['config']['seed'],t['config']['evaluation_seed'])
            self.assertEqual(t['config']['evaluation_shots'],64)
            self.assertEqual(t['config']['reps'],1)

    def test_real_reports_resume_and_mutated_samples_stop_or_config_are_rejected(self):
        design=make_design(self.instance,self.bundle,[60],self.base)
        campaign=new_campaign(design)
        trials=make_trials(design)
        oracle=ExactQAOAOracle(self.bundle,trials[0]['config'],self.reference)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); manifest=root/'manifest.json'
            for t in trials:
                if t['objective_mode']=='exact':
                    report=run_exact_qaoa(self.bundle,t['config'],self.reference,oracle,progress=False)
                else:
                    report=run_qaoa_experiment(self.bundle,t['config'],self.reference,progress=False)
                path=record_trial(root,campaign,t,report,self.bundle,oracle)
                save_campaign(manifest,campaign)
            self.assertEqual(len(verify_campaign(root,campaign,design,self.bundle,self.reference)),4)
            loaded=json.loads(manifest.read_text())
            self.assertEqual(loaded['remaining_run_keys'],[])
            self.assertEqual(len(verify_campaign(root,loaded,design,self.bundle,self.reference)),4)
            path=root/campaign['completed_runs'][0]['report']
            original=json.loads(path.read_text())
            for kind in ('counts','stop','config','identity','energy'):
                altered=deepcopy(original)
                if kind=='counts': altered['final_samples'][0]['probability']+=1/64
                elif kind=='stop': altered['optimizer_stop']['nfev']+=1
                elif kind=='config': altered['config']['evaluation_seed']=60
                elif kind=='identity': altered['exact_diagnostics_point_sha256']='wrong'
                else: altered['final_samples'][0]['energy']+=1
                path.write_text(json.dumps(altered))
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    verify_campaign(root,campaign,design,self.bundle,self.reference)
            path.write_text(json.dumps(original))
            altered=deepcopy(campaign); altered['completed_runs'].append(altered['completed_runs'][0])
            with self.assertRaises(ValueError): verify_campaign(root,altered,design,self.bundle,self.reference)

    def test_design_rejects_unmatched_or_invalid_controls(self):
        for changes in ({'seed':60},{'hamiltonian_scaling':'none'},{'cobyla_tol':0},{'maxiter':3}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                make_design(self.instance,self.bundle,[60,61,62],{**self.base,**changes})
        with self.assertRaises(ValueError):
            make_design(self.instance,self.bundle,[60,60],self.base)

    def test_exact_only_budget_keeps_starts_and_has_two_trials(self):
        design=make_design(self.instance,self.bundle,[60,61,62],
                           {**self.base, 'maxiter':200}, objective_modes=('exact',))
        trials=make_trials(design)
        self.assertEqual(len(trials),2)
        self.assertEqual({t['initial_point_id'] for t in trials},{'common','alternative'})
        self.assertTrue(all(t['objective_mode']=='exact' and t['config']['maxiter']==200 for t in trials))
        for modes in ((), ('unknown',), ('exact','exact')):
            with self.subTest(modes=modes), self.assertRaises(ValueError):
                make_design(self.instance,self.bundle,[60],self.base,objective_modes=modes)

    def test_historical_read_is_explicit_and_resume_still_checks_environment(self):
        from unittest.mock import patch
        design=make_design(self.instance,self.bundle,[60],self.base)
        campaign=new_campaign(design)
        with tempfile.TemporaryDirectory() as d:
            save_campaign(Path(d)/'manifest.json',campaign)
            with patch('src.convergence_campaign.experiment_environment',return_value={'changed':True}):
                with self.assertRaises(ValueError):
                    verify_campaign(d,campaign,design,self.bundle,self.reference)
                self.assertEqual(verify_campaign(d,campaign,design,self.bundle,self.reference,
                                                require_current_environment=False),[])
                changed=deepcopy(campaign); changed['design_hash']='wrong'
                with self.assertRaises(ValueError):
                    verify_campaign(d,changed,design,self.bundle,self.reference,
                                    require_current_environment=False)

    def test_exact_report_cannot_be_recorded_as_a_sampled_trial(self):
        design=make_design(self.instance,self.bundle,[60],self.base)
        campaign=new_campaign(design)
        sampled=campaign['planned_runs'][0]
        oracle=ExactQAOAOracle(self.bundle,sampled['config'],self.reference)
        report=run_exact_qaoa(self.bundle,sampled['config'],self.reference,oracle,progress=False)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                record_trial(d,campaign,sampled,report,self.bundle,oracle)
            self.assertEqual(campaign['completed_runs'],[])
            self.assertEqual(list(Path(d).iterdir()),[])


if __name__=='__main__': unittest.main()
