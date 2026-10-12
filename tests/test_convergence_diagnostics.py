"""Independent exact-state and held-out-sampling checks on tiny QAOA models.

The expected energies below are calculated from the placement equations, not
from the implementation's diagonal, matrix, or report summarization helpers.
"""

from math import sqrt
import unittest
from unittest.mock import patch

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2

from src.convergence_diagnostics import (
    ExactQAOAOracle,
    full_energy_diagonal,
    run_exact_qaoa,
)
from src.ising import build_ising, scale_ising
from src.qaoa_experiment import prepare_reference, run_qaoa_experiment
from src.qubo import build_qubo


def tiny_bundle(demand=1, assignment_penalty=7, capacity_penalty=3):
    """One task/one host: x, y, CPU slack, RAM slack = four qubits."""
    return build_qubo(
        {"schema_version": 1, "instance_id": "convergence_test",
         "objective": "min_active_hosts",
         "tasks": [{"id": "T0", "cpu": demand, "ram": demand}],
         "hosts": [{"id": "H0", "cpu": 1, "ram": 1}]},
        assignment_penalty=assignment_penalty,
        capacity_penalty=capacity_penalty,
    )


def small_config(**changes):
    return {
        "seed": 60, "shots": 64, "evaluation_seed": 1060,
        "evaluation_shots": 64, "reps": 1, "maxiter": 8,
        "max_qubits": 4, "max_seconds": 300,
        "aer_threads": 1, "aer_memory_mb": 256,
        "min_available_gib": 0.01, "initial_point": [0.3, 0.7],
        "hamiltonian_scaling": "max_abs", "cobyla_rhobeg": 1.,
        "cobyla_tol": 1e-4, **changes,
    }


def independent_basis_reference(bundle):
    """Evaluate every tiny basis state from x/y/resource/slack definitions."""
    n, m = bundle["n"], bundle["m"]
    size, base_count = bundle["qubo"].get_num_vars(), bundle["base_count"]
    demand = np.array([[t["cpu"], t["ram"]] for t in bundle["instance"]["tasks"]])
    capacity = np.array([[h["cpu"], h["ram"]] for h in bundle["instance"]["hosts"]])
    energies, feasible, objective, assignment_error, onehot = [], [], [], [], []
    for value in range(2**size):
        bits = np.array([(value >> k) & 1 for k in range(size)], dtype=int)
        x, y = bits[:n*m].reshape(n, m), bits[n*m:base_count]
        usage = x.T @ demand
        error = int(np.square(x.sum(axis=1) - 1).sum())
        capacity_error = 0
        for group in bundle["slack_groups"]:
            slack = sum(bits[index] * weight for index, weight in
                        zip(group["indices"], group["weights"]))
            h, r = group["host"], group["resource_index"]
            capacity_error += (usage[h, r] + slack - capacity[h, r]*y[h])**2
        energies.append(float(y.sum() + bundle["penalties"]["assignment"]*error
                              + bundle["penalties"]["capacity"]*capacity_error))
        feasible.append(error == 0 and bool((usage <= capacity*y[:, None]).all()))
        objective.append(int(y.sum()))
        assignment_error.append(error)
        onehot.append(error == 0)
    feasible = np.array(feasible, dtype=bool)
    objective = np.array(objective)
    optimum = int(objective[feasible].min()) if feasible.any() else None
    optimal = feasible & (objective == optimum) if optimum is not None else np.zeros_like(feasible)
    return {
        "energies": np.array(energies, dtype=float), "feasible": feasible,
        "optimal": optimal, "onehot": np.array(onehot, dtype=bool),
        "assignment_error": np.array(assignment_error), "base_count": base_count,
    }


def independent_exact_statistics(bundle, config, point):
    raw_operator, _ = build_ising(bundle)
    operator, _ = scale_ising(raw_operator, config["hamiltonian_scaling"])
    circuit = QAOAAnsatz(cost_operator=operator, reps=config["reps"])
    probabilities = Statevector(circuit.assign_parameters(point)).probabilities()
    truth = independent_basis_reference(bundle)
    energy = truth["energies"]
    mean = float(probabilities @ energy)
    variance = float(probabilities @ np.square(energy - mean))
    return {
        "exact_mean_qubo_energy": mean,
        "exact_feasible_probability": float(probabilities @ truth["feasible"]),
        "exact_optimal_probability": (float(probabilities @ truth["optimal"])
                                      if truth["feasible"].any() else None),
        "exact_ground_probability": float(probabilities @ np.isclose(
            energy, energy.min(), rtol=0, atol=1e-8)),
        "exact_energy_std": sqrt(variance),
        "standard_error_at_training_shots": sqrt(variance/config["shots"]),
    }


def independent_final_counts(bundle, config, point):
    """Use the public Aer/Qiskit APIs to reconstruct a held-out measurement."""
    raw_operator, _ = build_ising(bundle)
    operator, _ = scale_ising(raw_operator, config["hamiltonian_scaling"])
    options = {
        "method": "statevector", "device": "CPU", "precision": "double",
        "max_parallel_threads": config["aer_threads"],
        "max_parallel_experiments": 1, "max_parallel_shots": 1,
        "max_memory_mb": config["aer_memory_mb"],
    }
    backend = AerSimulator(**options)
    manager = generate_preset_pass_manager(
        optimization_level=1, backend=backend, seed_transpiler=config["seed"])
    circuit = QAOAAnsatz(cost_operator=operator, reps=config["reps"])
    circuit.measure_all()
    compiled = manager.run(circuit)
    sampler = SamplerV2(default_shots=config["evaluation_shots"],
                        seed=config["evaluation_seed"],
                        options={"backend_options": options})
    counts = sampler.run([(compiled, point)]).result()[0].data.meas.get_counts()
    return {int(label.replace(" ", ""), 2): count for label, count in counts.items()}


def report_counts(report):
    shots = report["config"]["evaluation_shots"]
    counts = {}
    for sample in report["final_samples"]:
        value = sum(int(bit) << k for k, bit in enumerate(sample["bits"]))
        count = sample["probability"] * shots
        if abs(count - round(count)) > 1e-8:
            raise AssertionError("Final probabilities must be frequencies of evaluation_shots.")
        if value in counts:
            raise AssertionError("A measured bitstring occurs twice in final_samples.")
        counts[value] = round(count)
    return counts


class EnergyDiagonalTests(unittest.TestCase):
    def test_diagonal_matches_equations_in_little_endian_order(self):
        for assignment, capacity in ((3, 3), (7, 3), (0.5, 2.5)):
            with self.subTest(penalties=(assignment, capacity)):
                bundle = tiny_bundle(assignment_penalty=assignment,
                                     capacity_penalty=capacity)
                expected = independent_basis_reference(bundle)
                actual = full_energy_diagonal(bundle, max_qubits=4)
                self.assertEqual(actual["base_count"], 2)
                self.assertEqual(actual["energies"].shape, (16,))
                self.assertTrue(np.issubdtype(actual["energies"].dtype, np.floating))
                np.testing.assert_allclose(actual["energies"], expected["energies"], atol=1e-10, rtol=0)
                for target, source in (("feasible_base", "feasible"),
                                       ("optimal_base", "optimal"),
                                       ("onehot_base", "onehot"),
                                       ("assignment_error_base", "assignment_error")):
                    np.testing.assert_array_equal(actual[target], expected[source][:4])
                # x=y=1 is optimal irrespective of slack, while wrong slack costs energy.
                self.assertTrue(actual["optimal_base"][3])
                self.assertEqual(actual["energies"][3], 1)
                self.assertEqual(actual["energies"][7], 1 + capacity)
                self.assertEqual(actual["energies"][1], 2*capacity)

    def test_infeasible_model_has_no_optimal_or_feasible_base_state(self):
        bundle = tiny_bundle(demand=2)
        actual = full_energy_diagonal(bundle, max_qubits=4)
        expected = independent_basis_reference(bundle)
        self.assertFalse(np.any(actual["feasible_base"]))
        self.assertFalse(np.any(actual["optimal_base"]))
        np.testing.assert_allclose(actual["energies"], expected["energies"], rtol=0, atol=1e-10)

    def test_qubit_guard_runs_before_any_exponential_allocation(self):
        class OversizeQubo:
            def get_num_vars(self):
                return 24

        # Intentionally omit instance/slack data: limit rejection must happen first.
        with patch.object(np, "arange", side_effect=AssertionError("Allocation before limit check")):
            with self.assertRaises(ValueError):
                full_energy_diagonal({"qubo": OversizeQubo()}, max_qubits=23)


class ExactOracleTests(unittest.TestCase):
    def test_exact_statistics_match_independent_qiskit_states_at_p1_and_p2(self):
        bundle = tiny_bundle()
        for reps, point in ((1, [0.27, 0.91]), (2, [0.27, -0.19, 0.91, 0.43])):
            for scaling in ("none", "max_abs"):
                with self.subTest(reps=reps, scaling=scaling):
                    config = small_config(reps=reps, initial_point=point,
                                          hamiltonian_scaling=scaling)
                    expected = independent_exact_statistics(bundle, config, point)
                    with patch.object(SparsePauliOp, "to_matrix", side_effect=AssertionError("Dense matrix")), \
                         patch.object(Statevector, "probabilities_dict", side_effect=AssertionError("All labels")), \
                         patch.object(Statevector, "sample_memory", side_effect=AssertionError("All labels")):
                        oracle = ExactQAOAOracle(bundle, config, prepare_reference(bundle))
                        actual = oracle.evaluate(point)
                    for key, value in expected.items():
                        self.assertAlmostEqual(actual[key], value, places=9, msg=key)

    def test_gamma_normalization_preserves_physical_statistics(self):
        bundle = tiny_bundle()
        raw, _ = build_ising(bundle)
        _, scaling = scale_ising(raw, "max_abs")
        self.assertGreater(scaling["scale"], 1)
        point = [0.21, -0.13, 0.32, -0.28]
        converted = point[:2] + [gamma*scaling["scale"] for gamma in point[2:]]
        unscaled = ExactQAOAOracle(bundle, small_config(
            reps=2, initial_point=point, hamiltonian_scaling="none")).evaluate(point)
        normalized = ExactQAOAOracle(bundle, small_config(
            reps=2, initial_point=converted)).evaluate(converted)
        for key in ("exact_mean_qubo_energy", "exact_feasible_probability",
                    "exact_optimal_probability", "exact_ground_probability", "exact_energy_std"):
            self.assertAlmostEqual(unscaled[key], normalized[key], places=9, msg=key)

    def test_bad_points_and_qubit_limit_are_rejected(self):
        bundle = tiny_bundle()
        oracle = ExactQAOAOracle(bundle, small_config())
        for point in ([0.3], [0.3, float("nan")], [0.3, float("inf")]):
            with self.subTest(point=point), self.assertRaises(ValueError):
                oracle.evaluate(point)
        with self.assertRaises(ValueError):
            ExactQAOAOracle(bundle, small_config(max_qubits=3))


class ExactRunnerTests(unittest.TestCase):
    def test_real_optimization_records_stop_and_held_out_measured_samples(self):
        bundle = tiny_bundle()
        config = small_config(maxiter=8, evaluation_shots=128)
        report = run_exact_qaoa(bundle, config, progress=False)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["sampling_protocol"], "independent_final_v1")
        self.assertNotEqual(report["config"]["seed"], report["config"]["evaluation_seed"])
        self.assertEqual(report["config"]["evaluation_shots"], 128)
        self.assertEqual(report["parameter_names"], ["β[0]", "γ[0]"])
        self.assertEqual(len(report["optimal_point"]), 2)
        stop = report["optimizer_stop"]
        self.assertIsInstance(stop["success"], (bool, np.bool_))
        self.assertTrue(np.isfinite(stop["status"]))
        self.assertIsInstance(stop["message"], str)
        self.assertTrue(stop["message"].strip())
        self.assertEqual(stop["nfev"], report["cost_function_evals"])
        self.assertEqual(stop["nfev"], len(report["optimization_history"]))
        self.assertGreater(stop["nfev"], 0)
        self.assertLessEqual(stop["nfev"], config["maxiter"])
        for row in report["optimization_history"]:
            expected = independent_exact_statistics(bundle, config, row["parameters"])
            self.assertAlmostEqual(row["estimated_qubo_energy"],
                                   expected["exact_mean_qubo_energy"], places=9)
        counts = report_counts(report)
        self.assertEqual(sum(counts.values()), 128)
        self.assertEqual(counts, independent_final_counts(bundle, config, report["optimal_point"]))
        truth = independent_basis_reference(bundle)
        for sample in report["final_samples"]:
            value = sum(int(bit) << k for k, bit in enumerate(sample["bits"]))
            self.assertAlmostEqual(sample["energy"], truth["energies"][value], places=9)
            self.assertEqual(sample["decoded"]["feasible"], bool(truth["feasible"][value]))
        self.assertAlmostEqual(report["metrics"]["final_sample_mean_qubo_energy"],
                               sum(count*truth["energies"][value] for value, count in counts.items())/128)
        self.assertAlmostEqual(report["metrics"]["feasible_probability"],
                               sum(count for value, count in counts.items() if truth["feasible"][value])/128)
        self.assertAlmostEqual(report["metrics"]["optimal_placement_probability"],
                               sum(count for value, count in counts.items() if truth["optimal"][value])/128)

    def test_changing_final_seed_leaves_exact_training_unchanged(self):
        bundle = tiny_bundle()
        config = small_config(maxiter=6)
        first = run_exact_qaoa(bundle, config, progress=False)
        second = run_exact_qaoa(bundle, {**config, "evaluation_seed": 2060}, progress=False)
        np.testing.assert_allclose(first["optimal_point"], second["optimal_point"], rtol=0, atol=1e-12)
        self.assertEqual([row["estimated_qubo_energy"] for row in first["optimization_history"]],
                         [row["estimated_qubo_energy"] for row in second["optimization_history"]])
        first_counts, second_counts = report_counts(first), report_counts(second)
        self.assertNotEqual(first_counts, second_counts)
        self.assertEqual(first_counts, independent_final_counts(bundle, first["config"], first["optimal_point"]))
        self.assertEqual(second_counts, independent_final_counts(bundle, second["config"], second["optimal_point"]))

    def test_same_training_and_final_seed_is_rejected(self):
        with self.assertRaises(ValueError):
            run_exact_qaoa(tiny_bundle(), small_config(evaluation_seed=60), progress=False)


class SampledRunnerRegressionTests(unittest.TestCase):
    def test_sampled_optimizer_uses_held_out_final_counts_and_records_actual_stop(self):
        bundle = tiny_bundle()
        config = small_config(maxiter=6, evaluation_shots=128)
        report = run_qaoa_experiment(bundle, config, progress=False)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["sampling_protocol"], "independent_final_v1")
        counts = report_counts(report)
        self.assertEqual(sum(counts.values()), 128)
        self.assertEqual(counts, independent_final_counts(bundle, config, report["optimal_point"]))
        stop = report["optimizer_stop"]
        self.assertTrue(np.isfinite(stop["status"]))
        self.assertIsInstance(stop["success"], (bool, np.bool_))
        self.assertTrue(stop["message"].strip())
        self.assertEqual(stop["nfev"], report["cost_function_evals"])
        self.assertEqual(stop["nfev"], len(report["optimization_history"]))


if __name__ == "__main__":
    unittest.main()
