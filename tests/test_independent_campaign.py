"""Campaign persistence and corruption checks using a real short Aer report."""

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.qubo import build_qubo
from src.qaoa_experiment import prepare_reference, run_qaoa_experiment, save_experiment_report
from src.penalty_analysis import penalty_diagnostics
from src.independent_campaign import (
    make_design, make_trials, new_campaign, save_campaign, report_row, verify_campaign,
)


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.instance = json.loads((root / "data/instances/p3_demo.json").read_text())
        cls.config = dict(shots=64, reps=1, maxiter=4, max_qubits=23,
                          max_seconds=300, aer_threads=2, aer_memory_mb=2048,
                          min_available_gib=2.0)
        cls.design = make_design({"p3_demo": cls.instance}, {"a12_c3": [12, 3]},
                                 {"old": [0.3, 0.7]}, [42], cls.config)
        cls.trial = make_trials(cls.design)[0]
        cls.bundle = build_qubo(cls.instance, assignment_penalty=12, capacity_penalty=3)
        cls.reference = prepare_reference(cls.bundle)
        cls.report = run_qaoa_experiment(cls.bundle, cls.trial["config"],
                                        cls.reference, progress=False)
        cls.report["penalty_analysis"] = penalty_diagnostics(cls.bundle, cls.report)
        cls.report["penalty_analysis_seconds"] = 0.0

    def campaign_with_report(self, root):
        campaign = new_campaign(self.design)
        report = copy.deepcopy(self.report)
        report["experiment"] = {"campaign_id": campaign["campaign_id"],
            "design_hash": campaign["design_hash"], "run_key": self.trial["run_key"],
            "pair_id": self.trial["pair_id"], "initial_point_id": self.trial["initial_point_id"],
            "purpose": "controlled_independent_penalty_pilot"}
        path = save_experiment_report(root, report)
        campaign["completed_runs"].append(report_row(root, path, report, self.trial))
        manifest = path.parent / f"campaign_{campaign['campaign_id']}.json"
        save_campaign(manifest, campaign)
        return campaign, path, manifest

    def test_completed_campaign_roundtrip_and_resume(self):
        with TemporaryDirectory() as root:
            campaign, _, manifest = self.campaign_with_report(root)
            loaded = json.loads(manifest.read_text())
            self.assertEqual(loaded, campaign)
            self.assertEqual(loaded["remaining_run_keys"], [])
            rows = verify_campaign(root, loaded, self.design,
                {("p3_demo", "a12_c3"): self.bundle}, {("p3_demo", "a12_c3"): self.reference})
            self.assertEqual(rows, campaign["completed_runs"])

    def test_changed_source_or_penalty_design_cannot_resume(self):
        with TemporaryDirectory() as root:
            campaign, _, _ = self.campaign_with_report(root)
            for key in ("environment", "penalty_pairs"):
                altered = copy.deepcopy(self.design)
                altered[key] = {}
                with self.assertRaises(ValueError):
                    verify_campaign(root, campaign, altered, {}, {})

    def test_corrupt_samples_or_manifest_rows_are_rejected(self):
        with TemporaryDirectory() as root:
            campaign, path, _ = self.campaign_with_report(root)
            corrupted = json.loads(path.read_text())
            corrupted["final_samples"][0]["energy"] += 1
            path.write_text(json.dumps(corrupted))
            with self.assertRaises(ValueError):
                verify_campaign(root, campaign, self.design,
                    {("p3_demo", "a12_c3"): self.bundle}, {("p3_demo", "a12_c3"): self.reference})
        with TemporaryDirectory() as root:
            campaign, _, _ = self.campaign_with_report(root)
            campaign["completed_runs"][0]["feasible_probability"] += 0.25
            with self.assertRaises(ValueError):
                verify_campaign(root, campaign, self.design,
                    {("p3_demo", "a12_c3"): self.bundle}, {("p3_demo", "a12_c3"): self.reference})

    def test_duplicate_design_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            make_design({"p3_demo": self.instance}, {"same": [3, 3], "again": [3, 3]},
                        {"old": [0.3, 0.7]}, [42], self.config)
        with self.assertRaises(ValueError):
            make_design({"p3_demo": self.instance}, {"same": [3, 3]},
                        {"old": [0.3, 0.7]}, [42, 42], self.config)


if __name__ == "__main__":
    unittest.main()
