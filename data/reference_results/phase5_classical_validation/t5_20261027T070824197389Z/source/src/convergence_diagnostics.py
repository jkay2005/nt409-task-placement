"""Bounded exact-state controls for tiny QAOA fixtures (Notebook 12).

Exact expectations remove measurement noise from the optimization objective.
Placement quality is still scored from an independent measured final batch.
No dense Hamiltonian matrix or dictionary of all 2**N labels is constructed.
"""

from time import perf_counter
import numpy as np
from qiskit.circuit.library import QAOAAnsatz

from .ising import build_ising, scale_ising
from .qaoa_optimizer import RecordingCOBYLA
from .qaoa_experiment import (
    _validated_config, _aer_components, _MemoryMonitor, _EvaluationTimeLimit,
    _new_report, _measure_final, _complete_report, prepare_reference, qubo_fingerprint,
)


def full_energy_diagonal(bundle, max_qubits=23):
    """E[k] follows Qiskit's little-endian order: low x/y, then slack bits.

    Enumerate the small x/y register and broadcast slack residuals. The
    floating point vector supports independent, fractional penalty weights.
    """
    size = bundle["qubo"].get_num_vars()
    if type(max_qubits) is not int or not 1 <= max_qubits <= 23 or size > max_qubits:
        raise ValueError("Exact diagnostics are limited to at most 23 qubits.")
    base_count, n, m = bundle["base_count"], bundle["n"], bundle["m"]
    if base_count > 16:
        raise ValueError("Exact diagnostics require a tiny x/y register (at most 16 bits).")
    bases = np.arange(2**base_count, dtype=np.uint32)
    bits = ((bases[:, None] >> np.arange(base_count)) & 1).astype(np.int64)
    x, y = bits[:, :n*m].reshape(-1, n, m), bits[:, n*m:]
    assignment_error = np.square(x.sum(axis=2) - 1).sum(axis=1)
    demand = np.array([[t["cpu"], t["ram"]] for t in bundle["instance"]["tasks"]])
    capacity = np.array([[h["cpu"], h["ram"]] for h in bundle["instance"]["hosts"]])
    usage = np.einsum("bih,ir->bhr", x, demand)
    onehot = assignment_error == 0
    feasible = onehot & (usage <= capacity[None, :, :] * y[:, :, None]).all(axis=(1, 2))
    objective = y.sum(axis=1)
    best = int(objective[feasible].min()) if feasible.any() else None
    optimal = feasible & (objective == best) if best is not None else np.zeros(len(bases), dtype=bool)
    energies = np.tile((objective + bundle["penalties"]["assignment"] * assignment_error
                        ).astype(float), (2**(size - base_count), 1))
    slack_register = np.arange(2**(size - base_count), dtype=np.uint32)
    for group in bundle["slack_groups"]:
        slack = sum(weight * ((slack_register >> (index - base_count)) & 1).astype(np.int64)
                    for index, weight in zip(group["indices"], group["weights"]))
        residual = (usage[None, :, group["host"], group["resource_index"]] + slack[:, None]
                    - group["capacity"] * y[None, :, group["host"]])
        energies += bundle["penalties"]["capacity"] * np.square(residual)
    return {"energies": energies.ravel(), "feasible_base": feasible, "optimal_base": optimal,
            "onehot_base": onehot, "assignment_error_base": assignment_error,
            "base_count": base_count}


class ExactQAOAOracle:
    """One Aer CPU circuit and compact numeric vectors reused across trials.

    Only scalar statistics are cached. Large probability vectors are discarded
    after each evaluation. This is an ideal simulator control, not a QPU oracle.
    """

    def __init__(self, bundle, config, reference=None):
        started = perf_counter()
        self.bundle = bundle
        self.config = _validated_config(bundle, config)
        self.fingerprint = qubo_fingerprint(bundle)
        self.reference = prepare_reference(bundle) if reference is None else reference
        self.diagonal = full_energy_diagonal(bundle, self.config["max_qubits"])
        self.energies = self.diagonal["energies"]
        if not np.isclose(self.energies.min(), self.reference["minimum_energy"], rtol=0, atol=1e-7):
            raise AssertionError("Energy diagonal differs from the QUBO reference.")
        self.energy_square = np.square(self.energies)
        self.ground_mask = np.isclose(self.energies, self.reference["minimum_energy"], rtol=0, atol=1e-7)
        raw, self.offset = build_ising(bundle)
        self.operator, self.scaling = scale_ising(raw, self.config.get("hamiltonian_scaling", "none"))
        self.backend, _, self.manager, self.options = _aer_components(self.config)
        circuit = QAOAAnsatz(cost_operator=self.operator, reps=self.config["reps"])
        self.parameter_names = [str(p) for p in circuit.parameters]
        self.circuit = self.manager.run(circuit)
        if self.circuit.layout is not None and self.circuit.layout.final_index_layout() != list(range(raw.num_qubits)):
            raise ValueError("Exact probabilities require identity qubit layout.")
        if [str(p) for p in self.circuit.parameters] != self.parameter_names:
            raise ValueError("Compiled QAOA parameter order changed.")
        self.circuit.save_probabilities(label="probabilities")
        self._cache = {}
        self.setup_seconds = perf_counter() - started

    def evaluate(self, point):
        point = np.asarray(point, dtype=float)
        if point.shape != (2*self.config["reps"],) or not np.isfinite(point).all():
            raise ValueError("Expected two finite angles per QAOA layer.")
        key = tuple(point)
        if key in self._cache:
            return self._cache[key].copy()
        started = perf_counter()
        result = self.backend.run(self.circuit.assign_parameters(point), shots=1).result()
        if not result.success:
            raise RuntimeError("Aer exact-state evaluation failed: " + str(result.status))
        probabilities = np.asarray(result.data(0)["probabilities"], dtype=float)
        if probabilities.shape != self.energies.shape or not np.isclose(probabilities.sum(), 1, atol=1e-9, rtol=0):
            raise AssertionError("Exact probabilities have the wrong register or normalization.")
        base_probabilities = probabilities.reshape(-1, 2**self.diagonal["base_count"]).sum(axis=0)
        mean = float(probabilities @ self.energies)
        std = float(np.sqrt(max(0., probabilities @ self.energy_square - mean**2)))
        answer = {
            "exact_mean_qubo_energy": mean,
            "exact_feasible_probability": float(base_probabilities[self.diagonal["feasible_base"]].sum()),
            "exact_optimal_probability": (float(base_probabilities[self.diagonal["optimal_base"]].sum())
                                          if self.reference["instance_feasible"] else None),
            "exact_ground_probability": float(probabilities[self.ground_mask].sum()),
            "exact_onehot_probability": float(base_probabilities[self.diagonal["onehot_base"]].sum()),
            "exact_mean_assignment_error": float(base_probabilities @ self.diagonal["assignment_error_base"]),
            "exact_energy_std": std,
            "standard_error_at_training_shots": std / np.sqrt(self.config["shots"]),
            "simulation_seconds": perf_counter() - started,
        }
        self._cache[key] = answer
        return answer.copy()

    def check_compatible(self, bundle, config, reference):
        keys = ("reps", "shots", "hamiltonian_scaling", "aer_threads", "aer_memory_mb", "max_qubits")
        if (qubo_fingerprint(bundle) != self.fingerprint or reference != self.reference
                or any(config.get(k) != self.config.get(k) for k in keys)):
            raise ValueError("The shared exact oracle does not match this model/configuration.")


def run_exact_qaoa(bundle, config, reference=None, oracle=None, progress=True):
    """Same COBYLA/budget/ansatz; replace shot objective by ideal expectation.

    success describes numerical termination only. Report metrics use the
    independent evaluation_shots, never the ideal probabilities.
    """
    config = _validated_config(bundle, config)
    reference = prepare_reference(bundle) if reference is None else reference
    started = perf_counter()
    oracle = ExactQAOAOracle(bundle, config, reference) if oracle is None else oracle
    oracle.check_compatible(bundle, config, reference)
    raw, offset = build_ising(bundle)
    report = _new_report(bundle, config, reference, oracle.operator, offset, oracle.scaling)
    report["method"] = "QAOA_AerExactExpectation_CPU_statevector_COBYLA"
    report["backend_options"] = oracle.options.copy()
    report["oracle_setup_seconds"] = oracle.setup_seconds
    optimizer = RecordingCOBYLA(config["maxiter"], config.get("cobyla_rhobeg", 1.), config.get("cobyla_tol", 1e-4))

    def objective(point):
        if perf_counter() - started >= config["max_seconds"]:
            raise _EvaluationTimeLimit("Elapsed budget reached before exact evaluation.")
        stats = oracle.evaluate(point)
        executed = (stats["exact_mean_qubo_energy"] - offset) / oracle.scaling["scale"]
        entry = {"evaluation": len(report["optimization_history"]) + 1,
                 "parameters": np.asarray(point).tolist(),
                 "estimated_qubo_energy": stats["exact_mean_qubo_energy"],
                 "execution_hamiltonian_expectation": executed,
                 "objective_source": "ideal_statevector_expectation",
                 "elapsed_seconds": perf_counter() - started}
        report["optimization_history"].append(entry)
        if progress and (entry["evaluation"] == 1 or entry["evaluation"] % 5 == 0):
            print(f"  exact evaluation {entry['evaluation']}: E={entry['estimated_qubo_energy']:.6f}, "
                  f"elapsed={entry['elapsed_seconds']:.1f}s", flush=True)
        if entry["elapsed_seconds"] >= config["max_seconds"]:
            raise _EvaluationTimeLimit("Elapsed budget reached after exact evaluation.")
        return executed

    try:
        with _MemoryMonitor() as memory:
            result = optimizer(objective, config["initial_point"])
            final_exact = oracle.evaluate(result.x)
            report["optimization_seconds"] = perf_counter() - started
            sample_started = perf_counter()
            distribution = _measure_final(bundle, config, oracle.operator, result.x, oracle.manager, oracle.options)
            report["evaluation_sampling_seconds"] = perf_counter() - sample_started
            if perf_counter() - started >= config["max_seconds"]:
                raise _EvaluationTimeLimit("Elapsed budget reached after independent final sampling.")
    except _EvaluationTimeLimit:
        report.update({"status": "time_budget_exceeded", "elapsed_seconds": perf_counter() - started,
                       "cost_function_evals": len(report["optimization_history"]),
                       "stop_reason": "Time guard checked between expensive calls.", "resources": memory.as_dict()})
        return report
    report.update({"elapsed_seconds": perf_counter() - started, "resources": memory.as_dict(),
                   "exact_diagnostics": final_exact})
    decode_started = perf_counter()
    _complete_report(report, bundle, raw, offset, oracle.scaling, result.x, result.fun,
                     distribution, optimizer, reference, oracle.parameter_names)
    report["postprocessing_seconds"] = perf_counter() - decode_started
    return report
