"""Check comparable penalty errors and frequency ties on real QUBO vectors."""

import unittest
from pathlib import Path
import json

from src.qubo import build_qubo, decode_qubo
from src.qaoa_experiment import prepare_reference
from src.penalty_analysis import penalty_diagnostics


class PenaltyAnalysisTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.instance = json.loads((root / "data/instances/p3_demo.json").read_text())

    def report(self, bundle, vectors):
        samples = [{"bits": bits, "probability": 1 / len(vectors),
                    "energy": float(bundle["qubo"].objective.evaluate(bits)),
                    "decoded": decode_qubo(bundle, bits)} for bits in vectors]
        return {"status": "completed", "penalty": bundle["penalty"],
                **({"penalties": bundle["penalties"]} if bundle["penalty_mode"] == "independent" else {}),
                "metrics": {"final_sample_mean_qubo_energy":
                            sum(s["probability"] * s["energy"] for s in samples)},
                "final_samples": samples}

    def test_tied_modes_are_order_independent(self):
        bundle = build_qubo(self.instance)
        valid = prepare_reference(bundle)["example_minimizer_bits"]
        report = self.report(bundle, [valid, [0] * len(valid)])
        result = penalty_diagnostics(bundle, report)
        self.assertEqual(result["dominant_bitstring_count"], 2)
        self.assertEqual(result["dominant_valid_bitstring_count"], 1)
        self.assertIsNone(result["unique_mode_valid"])
        report["final_samples"].reverse()
        self.assertEqual(penalty_diagnostics(bundle, report), result)

    def test_fixed_vectors_have_same_error_across_penalties(self):
        first = build_qubo(self.instance, penalty=1)
        bits = prepare_reference(build_qubo(self.instance))["example_minimizer_bits"]
        bits[first["slack_groups"][0]["indices"][0]] ^= 1
        results = []
        for penalty in (1, 3, 8):
            bundle = build_qubo(self.instance, penalty=penalty)
            result = penalty_diagnostics(bundle, self.report(bundle, [bits]))
            self.assertTrue(result["unique_mode_valid"])
            self.assertEqual(result["mean_assignment_error"], 0)
            self.assertGreater(result["mean_capacity_equation_error"], 0)
            self.assertAlmostEqual(result["reconstructed_mean_energy"],
                                   1 + penalty * result["mean_total_squared_error"])
            results.append(result["mean_total_squared_error"])
        self.assertEqual(results, [1, 1, 1])

    def test_corrupt_energy_is_rejected(self):
        bundle = build_qubo(self.instance)
        report = self.report(bundle, [prepare_reference(bundle)["example_minimizer_bits"]])
        report["final_samples"][0]["energy"] += 1
        with self.assertRaises(ValueError):
            penalty_diagnostics(bundle, report)

    def test_independent_weights_reconstruct_mean_and_record_onehot(self):
        bundle = build_qubo(self.instance, assignment_penalty=12, capacity_penalty=3)
        bits = prepare_reference(bundle)["example_minimizer_bits"]
        result = penalty_diagnostics(bundle, self.report(bundle, [bits, [0]*len(bits)]))
        self.assertEqual(result["one_hot_probability"], 0.5)
        self.assertAlmostEqual(result["reconstructed_mean_energy"],
            result["mean_active_hosts"] + 12*result["mean_assignment_error"]
            + 3*result["mean_capacity_equation_error"])

    def test_different_independent_weights_are_rejected_even_when_scalar_is_null(self):
        bundle = build_qubo(self.instance, assignment_penalty=12, capacity_penalty=3)
        report = self.report(bundle, [[0]*bundle["qubo"].get_num_vars()])
        report["penalties"] = {"assignment": 3, "capacity": 12}
        with self.assertRaises(ValueError):
            penalty_diagnostics(bundle, report)


if __name__ == "__main__":
    unittest.main()
