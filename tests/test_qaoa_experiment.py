"""Independent exhaustive checks on tiny instances and original fixture references."""

from itertools import product
import json
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import Statevector

from src.qubo import build_qubo, decode_qubo, exact_qubo_reference
from src.qaoa_experiment import (
    exact_uniform_baseline, prepare_reference, summarize_samples,
    run_qaoa_experiment, save_experiment_report, _aer_components,
)
from src.ising import build_ising


ROOT = Path(__file__).resolve().parents[1]


def read_bundle(name):
    instance = json.loads((ROOT / "data" / "instances" / f"{name}.json").read_text(encoding="utf-8"))
    return build_qubo(instance)


def brute_uniform(bundle):
    """Enumerate full bits, independently of the factorized reference method."""
    rows = []
    for bits in product((0, 1), repeat=bundle["qubo"].get_num_vars()):
        bits = np.array(bits, dtype=int)
        rows.append((float(bundle["qubo"].objective.evaluate(bits)), decode_qubo(bundle, bits)))
    energies = [row[0] for row in rows]
    minimum = min(energies)
    objectives = [row[1]["objective"] for row in rows if row[1]["feasible"]]
    optimum = min(objectives) if objectives else None
    return {
        "original_best_objective": optimum,
        "feasible_probability": sum(decoded["feasible"] for _, decoded in rows) / len(rows),
        "optimal_placement_probability": (
            sum(decoded["feasible"] and decoded["objective"] == optimum
                for _, decoded in rows) / len(rows) if optimum is not None else None
        ),
        "qubo_ground_state_bitstring_count": sum(energy == minimum for energy in energies),
        "mean_qubo_energy": np.mean(energies),
    }


class ReferenceTests(unittest.TestCase):
    def compare_with_brute(self, bundle):
        factored = exact_uniform_baseline(bundle)
        brute = brute_uniform(bundle)
        for key, value in brute.items():
            if value is None:
                self.assertIsNone(factored[key], key)
            else:
                self.assertAlmostEqual(factored[key], value, places=10, msg=key)
        self.assertAlmostEqual(factored["ground_state_probability"],
                               brute["qubo_ground_state_bitstring_count"]
                               / 2**bundle["qubo"].get_num_vars())

    def test_demo_uniform_matches_full_enumeration(self):
        self.compare_with_brute(read_bundle("p3_demo"))

    def test_duplicate_slack_encodings_are_all_counted(self):
        for capacity, demand in [(5, 3), (6, 3)]:
            with self.subTest(capacity=capacity):
                instance = {
                    "schema_version": 1, "instance_id": "duplicate_slack",
                    "objective": "min_active_hosts",
                    "tasks": [{"id": "T0", "cpu": demand, "ram": demand}],
                    "hosts": [{"id": "H0", "cpu": capacity, "ram": capacity}],
                }
                bundle = build_qubo(instance)
                self.compare_with_brute(bundle)
                self.assertEqual(exact_uniform_baseline(bundle)["qubo_ground_state_bitstring_count"], 4)

    def test_original_references_match_phase2(self):
        expected = {
            "p0_reference": (2, 2, 1), "p1_choice": (1, 1, 1),
            "p1_tight": (2, 2, 4), "p1_infeasible": (5, None, 12),
        }
        for name, (energy, hosts, ground_count) in expected.items():
            with self.subTest(instance=name):
                ref = prepare_reference(read_bundle(name))
                self.assertEqual(ref["minimum_energy"], energy)
                self.assertEqual(ref["original_best_objective"], hosts)
                self.assertEqual(ref["uniform_baseline"]["qubo_ground_state_bitstring_count"], ground_count)

    def test_infeasible_qubo_ground_is_not_a_feasible_placement(self):
        bundle = read_bundle("p1_infeasible")
        ref = prepare_reference(bundle)
        truth = exact_qubo_reference(bundle)
        item = truth["minimizers"][0]
        metrics = summarize_samples([{**item, "probability": 1.0}], ref)
        self.assertEqual(metrics["feasible_probability"], 0)
        self.assertIsNone(metrics["optimal_placement_probability"])
        self.assertIsNone(metrics["best_observed_valid"])
        self.assertEqual(metrics["qubo_ground_state_probability"], 1)

    def test_optimal_placement_can_have_wrong_slack(self):
        bundle = read_bundle("p3_demo")
        ref = prepare_reference(bundle)
        bits = np.array(ref["example_minimizer_bits"])
        altered = bits.copy()
        altered[bundle["slack_groups"][0]["indices"][0]] ^= 1
        samples = [{
            "bits": vector.tolist(), "energy": float(bundle["qubo"].objective.evaluate(vector)),
            "decoded": decode_qubo(bundle, vector), "probability": 0.5,
        } for vector in [bits, altered]]
        metrics = summarize_samples(samples, ref)
        self.assertEqual(metrics["feasible_probability"], 1)
        self.assertEqual(metrics["optimal_placement_probability"], 1)
        self.assertEqual(metrics["qubo_ground_state_probability"], 0.5)


class AerRegressionTests(unittest.TestCase):
    def test_transpilation_preserves_qaoa_state_and_bit_order(self):
        tiny = build_qubo({
            "schema_version": 1, "instance_id": "aer_equivalence_test",
            "objective": "min_active_hosts",
            "tasks": [{"id": "T0", "cpu": 1, "ram": 1}],
            "hosts": [{"id": "H0", "cpu": 1, "ram": 1}],
        })
        operator, _ = build_ising(tiny)
        config = dict(shots=1024, seed=42, aer_threads=2, aer_memory_mb=2048)
        backend, _, manager, _ = _aer_components(config)
        for reps in (1, 2):
            with self.subTest(reps=reps):
                circuit = QAOAAnsatz(cost_operator=operator, reps=reps)
                angles = [0.3] * reps + [0.7] * reps
                expected = Statevector(circuit.assign_parameters(angles))
                compiled = manager.run(circuit).assign_parameters(angles)
                compiled.save_statevector()
                actual = backend.run(compiled).result().get_statevector()
                self.assertTrue(expected.equiv(actual, rtol=0, atol=1e-10))

    def test_aer_run_avoids_full_outcome_labels_and_saves_completed(self):
        bundle = read_bundle("p3_demo")
        config = dict(seed=42, shots=128, reps=1, maxiter=4,
                      max_qubits=23, max_seconds=300)
        with patch.object(Statevector, "sample_memory",
                          side_effect=AssertionError("Full outcome labels must not be built")):
            report = run_qaoa_experiment(bundle, config, progress=False)
        self.assertEqual(report["status"], "completed")
        self.assertAlmostEqual(sum(s["probability"] for s in report["final_samples"]), 1)
        self.assertGreater(report["resources"]["process_peak_rss_mib"], 0)
        with TemporaryDirectory() as root:
            path = save_experiment_report(root, report)
            self.assertEqual(json.loads(path.read_text())["status"], "completed")

    def test_timeout_report_cannot_be_saved(self):
        with TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                save_experiment_report(root, {"status": "time_budget_exceeded"})
            self.assertEqual(list(Path(root).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
