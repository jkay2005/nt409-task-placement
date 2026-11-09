"""Depth comparison with equal budgets, identical starts and strict provenance."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import Statevector

from src.qubo import build_qubo, energy_parts
from src.ising import build_ising, scale_ising
from src.qaoa_experiment import prepare_reference, run_qaoa_experiment, save_experiment_report
from src.penalty_analysis import penalty_diagnostics
from src.depth_campaign import (embed_p1_start, make_design, make_trials, new_campaign,
                                save_campaign, report_row, verify_campaign)


class DepthCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instance = {'schema_version':1,'instance_id':'depth_test','objective':'min_active_hosts',
            'tasks':[{'id':'T0','cpu':1,'ram':1}],'hosts':[{'id':'H0','cpu':1,'ram':1}]}
        cls.bundle = build_qubo(cls.instance,assignment_penalty=3,capacity_penalty=3)
        cls.reference = prepare_reference(cls.bundle)
        cls.base = dict(shots=64,maxiter=8,max_qubits=23,max_seconds=300,aer_threads=2,
                        aer_memory_mb=2048,min_available_gib=2.,cobyla_rhobeg=1.,hamiltonian_scaling='max_abs')
        cls.design = make_design(cls.instance,cls.bundle,[55,56,57,58,59],cls.base,[0.3,1.])
        cls.trial = make_trials(cls.design)[1]
        cls.report = run_qaoa_experiment(cls.bundle,cls.trial['config'],cls.reference,progress=False)
        cls.report['penalty_analysis'] = penalty_diagnostics(cls.bundle,cls.report)
        cls.report['penalty_analysis_seconds'] = 0.

    def persisted(self,root):
        campaign = new_campaign(self.design)
        report = copy.deepcopy(self.report)
        report['scope'] = campaign['scope']
        report['study'] = self.design['study']
        report['experiment'] = {'campaign_id':campaign['campaign_id'],'design_hash':campaign['design_hash'],
            'run_key':self.trial['run_key'],'arm_id':self.trial['arm_id'],'purpose':'matched_budget_depth_comparison'}
        path = save_experiment_report(root,report)
        campaign['completed_runs'].append(report_row(root,path,report,self.trial))
        manifest = path.parent/f"depth_{campaign['campaign_id']}.json"
        save_campaign(manifest,campaign)
        return campaign,path,manifest

    def test_zero_final_layer_preserves_p1_state_and_energy(self):
        op,_ = build_ising(self.bundle)
        op,_ = scale_ising(op,'max_abs')
        for point in ([0.3,1.],[-0.4,2.1],[1.2,-0.7]):
            embedded = embed_p1_start(point)
            self.assertEqual(embedded,[point[0],0.,point[1],0.])
            before = Statevector(QAOAAnsatz(cost_operator=op,reps=1).assign_parameters(point))
            circuit = QAOAAnsatz(cost_operator=op,reps=2)
            self.assertEqual([str(p) for p in circuit.parameters],['β[0]','β[1]','γ[0]','γ[1]'])
            after = Statevector(circuit.assign_parameters(embedded))
            self.assertTrue(before.equiv(after,rtol=0,atol=1e-10))
            self.assertAlmostEqual(before.expectation_value(op).real,after.expectation_value(op).real)

    def test_ten_unique_trials_share_budget_and_pair_seeds(self):
        trials = make_trials(self.design)
        self.assertEqual(len(trials),10)
        self.assertEqual(len({t['run_key'] for t in trials}),10)
        self.assertEqual([t['seed'] for t in trials],[55,55,56,56,57,57,58,58,59,59])
        for p1,p2 in zip(trials[::2],trials[1::2]):
            self.assertEqual(p1['config']['reps'],1)
            self.assertEqual(p2['config']['reps'],2)
            self.assertEqual(p2['config']['initial_point'],embed_p1_start(p1['config']['initial_point']))
            self.assertEqual({k:v for k,v in p1['config'].items() if k not in ('reps','initial_point')},
                             {k:v for k,v in p2['config'].items() if k not in ('reps','initial_point')})

    def test_actual_p2_report_has_four_angles_and_raw_energy_units(self):
        report = self.report
        self.assertEqual(report['status'],'completed')
        self.assertEqual(report['parameter_names'],['β[0]','β[1]','γ[0]','γ[1]'])
        self.assertEqual(report['optimization_history'][0]['parameters'],[0.3,0.,1.,0.])
        self.assertTrue(all(len(h['parameters'])==4 for h in report['optimization_history']))
        self.assertLessEqual(report['cost_function_evals'],8)
        self.assertEqual(report['optimal_point_raw_hamiltonian'][:2],report['optimal_point'][:2])
        scale = report['hamiltonian_scaling']['scale']
        np.testing.assert_allclose(report['optimal_point_raw_hamiltonian'][2:],
                                  np.array(report['optimal_point'][2:])/scale)
        for sample in report['final_samples']:
            self.assertAlmostEqual(sample['energy'],energy_parts(self.bundle,sample['bits'])['energy'])

    def test_partial_resume_tracks_nine_remaining_trials(self):
        with TemporaryDirectory() as root:
            campaign,path,manifest = self.persisted(root)
            self.assertEqual(path.parent.name,'phase4d_depth_runs')
            self.assertIn('p2_embedded_p2_seed55',path.name)
            loaded = json.loads(manifest.read_text(encoding='utf-8'))
            self.assertEqual(loaded['completed_run_count'],1)
            self.assertEqual(len(loaded['remaining_run_keys']),9)
            self.assertEqual(verify_campaign(root,loaded,self.design,self.bundle,self.reference),campaign['completed_runs'])

    def test_partial_resume_with_non_utf8_default_encoding(self):
        """Reproduce Windows locale decoding even on a UTF-8 Linux runner."""
        original_read_text = Path.read_text

        def locale_read_text(path, encoding=None, errors=None):
            return original_read_text(path, encoding=encoding or 'cp1252', errors=errors)

        with patch.object(Path, 'read_text', locale_read_text):
            self.test_partial_resume_tracks_nine_remaining_trials()

    def test_altered_depth_angles_samples_or_scale_rejected(self):
        changes = [lambda r:r['config'].update(reps=1),
                   lambda r:r['optimal_point_raw_hamiltonian'].__setitem__(2,999.),
                   lambda r:r['parameter_names'].__setitem__(1,'γ[0]'),
                   lambda r:r['final_samples'][0]['bits'].__setitem__(0,2),
                   lambda r:r['hamiltonian_scaling'].update(scale=999.)]
        with TemporaryDirectory() as root:
            campaign,path,_ = self.persisted(root)
            original = path.read_text(encoding='utf-8')
            for change in changes:
                report = json.loads(original)
                change(report)
                path.write_text(json.dumps(report), encoding='utf-8')
                with self.assertRaises(ValueError):
                    verify_campaign(root,campaign,self.design,self.bundle,self.reference)

    def test_changed_budget_or_input_cannot_resume(self):
        with TemporaryDirectory() as root:
            campaign,_,_ = self.persisted(root)
            altered = copy.deepcopy(self.design)
            altered['base_config']['maxiter'] += 1
            with self.assertRaises(ValueError):verify_campaign(root,campaign,altered,self.bundle,self.reference)
            changed_instance = copy.deepcopy(self.instance)
            changed_instance['instance_id'] = 'another_input'
            wrong = build_qubo(changed_instance,assignment_penalty=3,capacity_penalty=3)
            with self.assertRaises(ValueError):verify_campaign(root,campaign,self.design,wrong,prepare_reference(wrong))

    def test_depth_saver_rejects_unknown_or_mismatched_arm(self):
        with TemporaryDirectory() as root:
            for arm in ('unknown','p1_control'):
                report = copy.deepcopy(self.report)
                report['scope'] = 'phase4d_depth_comparison'
                report['experiment'] = {'arm_id':arm}
                with self.assertRaises(ValueError):save_experiment_report(root,report)
            self.assertEqual(list(Path(root).rglob('*.json')),[])

    def test_invalid_start_penalties_or_depth_override_rejected(self):
        for point in ([0.3],[0.3,float('nan')],[True,1.]):
            with self.assertRaises(ValueError):embed_p1_start(point)
        for seeds,base in [([55,55],self.base),([True],self.base),
                           ([55],{**self.base,'reps':2}),([55],{**self.base,'hamiltonian_scaling':'none'})]:
            with self.assertRaises(ValueError):make_design(self.instance,self.bundle,seeds,base,[0.3,1.])
        wrong = build_qubo(self.instance,assignment_penalty=1,capacity_penalty=1)
        with self.assertRaises(ValueError):make_design(self.instance,wrong,[55],self.base,[0.3,1.])


if __name__=='__main__':unittest.main()
