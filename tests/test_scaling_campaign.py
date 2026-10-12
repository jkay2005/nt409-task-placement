"""Arm identity, raw/normalized search designs, and safe campaign resume."""

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.qubo import build_qubo
from src.qaoa_experiment import prepare_reference, run_qaoa_experiment, save_experiment_report
from src.penalty_analysis import penalty_diagnostics
from src.scaling_campaign import make_design, make_trials, new_campaign, save_campaign, report_row, verify_campaign


class ScalingCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instance = json.loads((Path(__file__).resolve().parents[1]/'data/instances/p3_demo.json').read_text())
        cls.bundle = build_qubo(cls.instance, assignment_penalty=3, capacity_penalty=3)
        cls.reference = prepare_reference(cls.bundle)
        cls.base = dict(shots=64, reps=1, maxiter=4, max_qubits=23, max_seconds=300,
                        aer_threads=2, aer_memory_mb=2048, min_available_gib=2.0, cobyla_rhobeg=1.0)
        cls.design = make_design(cls.instance, cls.bundle, [50,51,52,53,54], cls.base, [0.3,0.05])
        cls.trial = next(t for t in make_trials(cls.design) if t['arm_id']=='normalized_common')
        cls.report = run_qaoa_experiment(cls.bundle, cls.trial['config'], cls.reference, progress=False)
        cls.report['penalty_analysis'] = penalty_diagnostics(cls.bundle, cls.report)
        cls.report['penalty_analysis_seconds'] = 0.0

    def persisted(self, root):
        campaign = new_campaign(self.design)
        report = copy.deepcopy(self.report)
        report['scope'] = campaign['scope']
        report['study'] = self.design['study']
        report['experiment'] = {'campaign_id':campaign['campaign_id'], 'design_hash':campaign['design_hash'],
            'run_key':self.trial['run_key'], 'arm_id':self.trial['arm_id'],
            'purpose':'common_penalty_scaling_diagnostic'}
        path = save_experiment_report(root, report)
        campaign['completed_runs'].append(report_row(root,path,report,self.trial))
        manifest = path.parent/f"scaling_{campaign['campaign_id']}.json"
        save_campaign(manifest,campaign)
        return campaign,path,manifest

    def test_matrix_has_fifteen_unique_runs_and_matched_physical_start(self):
        trials = make_trials(self.design)
        self.assertEqual(len(trials),15)
        self.assertEqual(len({t['run_key'] for t in trials}),15)
        arms=self.design['arms']
        k=self.design['normalization']['scale']
        self.assertEqual(arms['normalized_matched']['initial_point'][0],arms['raw_original']['initial_point'][0])
        self.assertAlmostEqual(arms['normalized_matched']['initial_point'][1]/k,arms['raw_original']['initial_point'][1])
        self.assertEqual(arms['normalized_common']['initial_point'],[0.3,1.0])
        self.assertEqual({t['config']['hamiltonian_scaling'] for t in trials},{'none','max_abs'})

    def test_partial_campaign_roundtrip_and_remaining_keys(self):
        with TemporaryDirectory() as root:
            campaign,_,manifest=self.persisted(root)
            loaded=json.loads(manifest.read_text())
            self.assertEqual(loaded['completed_run_count'],1)
            self.assertEqual(len(loaded['remaining_run_keys']),14)
            self.assertEqual(verify_campaign(root,loaded,self.design,self.bundle,self.reference),campaign['completed_runs'])

    def test_changed_design_scope_or_scale_rejected(self):
        with TemporaryDirectory() as root:
            campaign,path,_=self.persisted(root)
            altered=copy.deepcopy(self.design)
            altered['arms']['normalized_common']['initial_point'][1]=0.5
            with self.assertRaises(ValueError):verify_campaign(root,campaign,altered,self.bundle,self.reference)
            changed=copy.deepcopy(campaign)
            changed['scope']='phase4b_independent_penalty_pilot'
            with self.assertRaises(ValueError):verify_campaign(root,changed,self.design,self.bundle,self.reference)
            report=json.loads(path.read_text())
            report['hamiltonian_scaling']['scale']+=1
            path.write_text(json.dumps(report))
            with self.assertRaises(ValueError):verify_campaign(root,campaign,self.design,self.bundle,self.reference)

    def test_invalid_penalties_seeds_or_depth_rejected(self):
        for seeds,base in [([50,50],self.base),([True],self.base),([50],{**self.base,'reps':2})]:
            with self.assertRaises(ValueError):make_design(self.instance,self.bundle,seeds,base,[0.3,0.05])
        wrong=build_qubo(self.instance,assignment_penalty=1,capacity_penalty=1)
        with self.assertRaises(ValueError):make_design(self.instance,wrong,[50],self.base,[0.3,0.05])


if __name__=='__main__':unittest.main()
