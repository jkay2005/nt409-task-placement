"""Preserve physical states and raw QUBO scoring when rescaling the cost."""

from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp, Statevector

from src.ising import build_ising, ising_energy, scale_ising, scaled_qaoa_point
from src.qubo import build_qubo, energy_parts
from src.qaoa_experiment import run_qaoa_experiment, save_experiment_report


def tiny_bundle():
    return build_qubo({"schema_version": 1, "instance_id": "scaling_test",
        "objective": "min_active_hosts", "tasks": [{"id": "T0", "cpu": 1, "ram": 1}],
        "hosts": [{"id": "H0", "cpu": 1, "ram": 1}]},
        assignment_penalty=3, capacity_penalty=3)


class ScalingTests(unittest.TestCase):
    def test_all_basis_energies_and_ground_states_preserved(self):
        bundle = tiny_bundle()
        raw, offset = build_ising(bundle)
        scaled, info = scale_ising(raw, "max_abs")
        self.assertGreater(info["scale"], 1)
        original, normalized = [], []
        for bits in product((0, 1), repeat=raw.num_qubits):
            expected = energy_parts(bundle, bits)["energy"]
            executed = ising_energy(scaled, 0, bits)
            self.assertAlmostEqual(expected, info["scale"] * executed + offset)
            original.append(expected)
            normalized.append(executed)
        self.assertEqual(np.flatnonzero(np.isclose(original, min(original))).tolist(),
                         np.flatnonzero(np.isclose(normalized, min(normalized))).tolist())

    def test_matched_gamma_preserves_state_at_depth_one_and_two(self):
        raw, _ = build_ising(tiny_bundle())
        scaled, info = scale_ising(raw, "max_abs")
        for reps in (1, 2):
            point = [0.3] * reps + [0.7] * reps
            converted = scaled_qaoa_point(point, reps, info["scale"])
            before = Statevector(QAOAAnsatz(cost_operator=raw, reps=reps).assign_parameters(point))
            after = Statevector(QAOAAnsatz(cost_operator=scaled, reps=reps).assign_parameters(converted))
            self.assertTrue(before.equiv(after, rtol=0, atol=1e-10))
            np.testing.assert_allclose(scaled_qaoa_point(converted, reps, 1/info["scale"]), point)

    def test_constant_terms_do_not_set_scale_and_zero_scale_is_safe(self):
        raw = SparsePauliOp(["I", "Z"], coeffs=[1000, 2])
        _, info = scale_ising(raw, "max_abs")
        self.assertEqual(info["scale"], 2)
        _, info = scale_ising(SparsePauliOp("I", coeffs=[0]), "max_abs")
        self.assertEqual(info["scale"], 1)

    def test_invalid_scaling_or_angles_are_rejected(self):
        raw, _ = build_ising(tiny_bundle())
        with self.assertRaises(ValueError): scale_ising(raw, "unknown")
        for point, reps, scale in [([0.3], 1, 2), ([0.3, float('nan')], 1, 2),
                                    ([0.3, 0.7], 1, 0), ([0.3, 0.7], 1, True)]:
            with self.assertRaises(ValueError): scaled_qaoa_point(point, reps, scale)


class ScalingRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = tiny_bundle()
        cls.config = dict(seed=50, shots=64, reps=1, maxiter=4, max_qubits=23,
                          max_seconds=300, aer_threads=2, aer_memory_mb=2048,
                          min_available_gib=2.0, initial_point=[0.3, 0.7])

    def test_explicit_none_matches_legacy_samples_and_metrics(self):
        old = run_qaoa_experiment(self.bundle, self.config, progress=False)
        new = run_qaoa_experiment(self.bundle,
              {**self.config, "hamiltonian_scaling": "none", "cobyla_rhobeg": 1.0}, progress=False)
        self.assertEqual(old["final_samples"], new["final_samples"])
        self.assertEqual(old["metrics"], new["metrics"])
        self.assertEqual(old["optimal_point"], new["optimal_point"])
        self.assertNotIn("hamiltonian_scaling", old)
        self.assertEqual(new["hamiltonian_scaling"]["scale"], 1)

    def test_scaled_runner_scores_original_energy_and_initial_state(self):
        raw, _ = build_ising(self.bundle)
        _, info = scale_ising(raw, "max_abs")
        converted = scaled_qaoa_point(self.config["initial_point"], 1, info["scale"])
        original = run_qaoa_experiment(self.bundle, self.config, progress=False)
        scaled = run_qaoa_experiment(self.bundle,
             {**self.config, "hamiltonian_scaling": "max_abs", "initial_point": converted}, progress=False)
        self.assertEqual(scaled["hamiltonian_scaling"], info)
        self.assertAlmostEqual(original["optimization_history"][0]["estimated_qubo_energy"],
                               scaled["optimization_history"][0]["estimated_qubo_energy"], places=8)
        for sample in scaled["final_samples"]:
            self.assertAlmostEqual(sample["energy"], energy_parts(self.bundle, sample["bits"])["energy"])
        np.testing.assert_allclose(scaled["optimal_point_raw_hamiltonian"],
            scaled_qaoa_point(scaled["optimal_point"], 1, 1/info["scale"]))
        self.assertAlmostEqual(scaled["optimizer_estimated_qubo_expectation"],
            info["scale"]*scaled["optimizer_estimated_execution_expectation"]+scaled["ising_offset"])
        for entry in scaled["optimization_history"]:
            self.assertAlmostEqual(entry["estimated_qubo_energy"],
                info["scale"]*entry["execution_hamiltonian_expectation"]+scaled["ising_offset"])
        scaled["scope"] = "phase4c_hamiltonian_scaling"
        scaled["experiment"] = {"arm_id": "normalized_matched"}
        with TemporaryDirectory() as root:
            path = save_experiment_report(root, scaled)
            self.assertEqual(path.parent.name, "phase4c_scaling_runs")
            self.assertIn("normalized_matched", path.name)
            self.assertEqual(json.loads(path.read_text())["hamiltonian_scaling"], info)

    def test_invalid_runner_scaling_and_search_radius_rejected(self):
        for changes in [{"hamiltonian_scaling": "unknown"}, {"cobyla_rhobeg": 0}, {"cobyla_rhobeg": True}]:
            with self.assertRaises(ValueError):
                run_qaoa_experiment(self.bundle, {**self.config, **changes}, progress=False)


if __name__ == "__main__":
    unittest.main()
