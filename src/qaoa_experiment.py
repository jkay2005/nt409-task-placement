"""Small-instance references and reproducible QAOA experiments for Phase 3.

Reuse the Phase 1/2 model. Exact references enumerate x,y, not all slack bits.
QAOA outcomes are always evaluated from the observed final samples.
"""

from collections import Counter
from datetime import datetime, timezone
from itertools import product
import hashlib
import json
from pathlib import Path
import platform
from time import perf_counter

import numpy as np
import scipy
import qiskit
import qiskit_optimization
import qiskit_aer
import psutil
from qiskit.circuit.library import QAOAAnsatz
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2
from qiskit_optimization.minimum_eigensolvers import QAOA
from qiskit_optimization.optimizers import COBYLA

from .ising import build_ising, decode_samples, integer_to_bits
from .qubo import decode_qubo, exact_qubo_reference


def slack_encoding_counts(weights):
    """Count every binary encoding of each slack value, including duplicates."""
    counts = Counter({0: 1})
    for weight in weights:
        updated = counts.copy()
        for value, count in counts.items():
            updated[value + weight] += count
        counts = updated
    return counts


def exact_uniform_baseline(bundle, truth=None, max_base_variables=16):
    """Exact uniform full-bit baseline without enumerating 2**num_qubits.

    Feasibility depends only on x,y. Slack encoding multiplicities count QUBO
    ground states. Conditional means use E[s]=sum(w)/2 and Var(s)=sum(w*w)/4.
    The base enumeration limit is deliberate: this is a tiny-fixture reference.
    """
    size = bundle["base_count"]
    if size > max_base_variables:
        raise ValueError("Exact references are limited to tiny x,y registers.")
    if truth is None:
        truth = exact_qubo_reference(bundle, max_base_variables=max_base_variables)
    minimum = float(truth["minimum_energy"])
    num_bits = bundle["qubo"].get_num_vars()
    groups = bundle["slack_groups"]
    encodings = [slack_encoding_counts(group["weights"]) for group in groups]
    feasible_by_objective = Counter()
    ground_count = 0
    mean_energy_sum = 0.0
    observed_minimum = float("inf")
    bits = np.zeros(num_bits, dtype=int)

    for base in product((0, 1), repeat=size):
        bits[:size] = base
        decoded = decode_qubo(bundle, bits)
        x = np.asarray(decoded["x"], dtype=int)
        assignment_error = int(np.square(x.sum(axis=1) - 1).sum())
        objective = sum(decoded["y"])
        min_energy = objective + bundle["penalty"] * assignment_error
        conditional_mean = float(min_energy)
        multiplicity = 1
        for group, encoding_counts in zip(groups, encodings):
            h, r = group["host"], group["resource_index"]
            residual_without_slack = (
                decoded["usage"][h][r] - group["capacity"] * decoded["y"][h]
            )
            target = max(0, -residual_without_slack)
            multiplicity *= encoding_counts[target]
            min_energy += bundle["penalty"] * (residual_without_slack + target)**2
            weights = group["weights"]
            slack_mean = sum(weights) / 2
            slack_variance = sum(weight**2 for weight in weights) / 4
            conditional_mean += bundle["penalty"] * (
                (residual_without_slack + slack_mean)**2 + slack_variance
            )
        observed_minimum = min(observed_minimum, min_energy)
        mean_energy_sum += conditional_mean
        if decoded["feasible"]:
            feasible_by_objective[decoded["objective"]] += 1
        if np.isclose(min_energy, minimum, rtol=0, atol=1e-7):
            ground_count += multiplicity

    if not np.isclose(observed_minimum, minimum, rtol=0, atol=1e-7):
        raise AssertionError("The QUBO reference does not match this instance.")
    best_objective = min(feasible_by_objective) if feasible_by_objective else None
    base_states = 2**size
    return {
        "method": "exact_xy_enumeration_and_slack_encoding_counts",
        "checked_base_vectors": base_states,
        "total_bitstrings": 2**num_bits,
        "original_best_objective": best_objective,
        "feasible_xy_count": sum(feasible_by_objective.values()),
        "optimal_placement_xy_count": (
            feasible_by_objective[best_objective] if best_objective is not None else None
        ),
        "qubo_ground_state_bitstring_count": ground_count,
        "feasible_probability": sum(feasible_by_objective.values()) / base_states,
        "optimal_placement_probability": (
            feasible_by_objective[best_objective] / base_states
            if best_objective is not None else None
        ),
        "ground_state_probability": ground_count / 2**num_bits,
        "mean_qubo_energy": mean_energy_sum / base_states,
    }


def prepare_reference(bundle):
    """Compute independent original-problem and QUBO references for one fixture."""
    truth = exact_qubo_reference(bundle)
    uniform = exact_uniform_baseline(bundle, truth)
    return {
        "minimum_energy": truth["minimum_energy"],
        "original_best_objective": uniform["original_best_objective"],
        "instance_feasible": uniform["original_best_objective"] is not None,
        "minimizer_xy_count": len(truth["minimizers"]),
        "all_qubo_minimizers_feasible": all(
            item["decoded"]["feasible"] for item in truth["minimizers"]
        ),
        "example_minimizer_bits": truth["minimizers"][0]["bits"],
        "uniform_baseline": uniform,
    }


def summarize_samples(samples, reference):
    """Keep placement feasibility, original optimality, and QUBO minimum separate."""
    if not samples:
        raise ValueError("The final sampling batch is empty.")
    probabilities = np.array([sample["probability"] for sample in samples])
    if (not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or not np.isclose(probabilities.sum(), 1, rtol=0, atol=1e-6)):
        raise ValueError("Final sample probabilities must sum to one.")
    feasible = [sample for sample in samples if sample["decoded"]["feasible"]]
    optimum = reference["original_best_objective"]
    if optimum is None and feasible:
        raise AssertionError("A feasible sample contradicts the exact reference.")
    best = min(feasible, key=lambda sample: (
        sample["decoded"]["objective"], sample["energy"], -sample["probability"]
    )) if feasible else None
    return {
        "feasible_probability": sum(sample["probability"] for sample in feasible),
        "optimal_placement_probability": (
            sum(sample["probability"] for sample in feasible
                if sample["decoded"]["objective"] == optimum)
            if optimum is not None else None
        ),
        "qubo_ground_state_probability": sum(
            sample["probability"] for sample in samples
            if np.isclose(sample["energy"], reference["minimum_energy"],
                          rtol=0, atol=1e-7)
        ),
        "final_sample_mean_qubo_energy": sum(
            sample["probability"] * sample["energy"] for sample in samples
        ),
        "most_frequent_valid": samples[0]["decoded"]["feasible"],
        "best_observed_valid": None if best is None else {
            "bits": best["bits"], "energy": best["energy"],
            "probability": best["probability"], **best["decoded"],
        },
    }


class _EvaluationTimeLimit(RuntimeError):
    pass


class _MemoryMonitor:
    """Use the OS peak, which also captures allocations inside native Aer code.

    The peak covers the entire Python process lifetime, including earlier cells.
    Restart the notebook kernel for a clean measurement of this workflow.
    """

    def _memory_info(self):
        if platform.system() == "Linux":
            fields = dict(line.split(":", 1) for line in
                          Path("/proc/self/status").read_text().splitlines() if ":" in line)
            return tuple(int(fields[key].split()[0]) * 1024 for key in ("VmRSS", "VmHWM"))
        info = psutil.Process().memory_info()
        return info.rss, getattr(info, "peak_wset", None)

    def __enter__(self):
        self.start_rss, _ = self._memory_info()
        self.start_available = psutil.virtual_memory().available
        return self

    def __exit__(self, *exc):
        self.end_rss, self.peak_rss = self._memory_info()
        self.end_available = psutil.virtual_memory().available

    def as_dict(self):
        return {
            "measurement": "OS_process_lifetime_peak_RSS_includes_earlier_kernel_activity",
            "process_start_rss_mib": self.start_rss / 2**20,
            "process_end_rss_mib": self.end_rss / 2**20,
            "process_peak_rss_mib": None if self.peak_rss is None else self.peak_rss / 2**20,
            "system_available_before_gib": self.start_available / 2**30,
            "system_available_after_gib": self.end_available / 2**30,
        }


def _validated_config(bundle, config):
    config = dict(config)
    config.setdefault("aer_threads", 4)
    config.setdefault("aer_memory_mb", 2048)
    config.setdefault("min_available_gib", 2.0)
    for key in ("shots", "reps", "maxiter", "max_qubits"):
        if type(config.get(key)) is not int or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer.")
    if type(config.get("seed")) is not int or config["seed"] < 0:
        raise ValueError("seed must be a nonnegative integer.")
    initial_point = config.get("initial_point", [0.3] * config["reps"] + [0.7] * config["reps"])
    if len(initial_point) != 2 * config["reps"] or not np.isfinite(initial_point).all():
        raise ValueError("initial_point needs two finite angles per QAOA layer.")
    config["initial_point"] = [float(value) for value in initial_point]
    limit = config.get("max_seconds", 300)
    if not np.isfinite(limit) or limit <= 0:
        raise ValueError("max_seconds must be positive and finite.")
    config["max_seconds"] = float(limit)
    num_bits = bundle["qubo"].get_num_vars()
    if num_bits > config["max_qubits"]:
        raise ValueError("Instance exceeds the configured qubit limit.")
    for key in ("aer_threads", "aer_memory_mb"):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer.")
    if not np.isfinite(config["min_available_gib"]) or config["min_available_gib"] <= 0:
        raise ValueError("min_available_gib must be positive and finite.")
    if 16 * 2**num_bits / 2**20 > config["aer_memory_mb"]:
        raise ValueError("One statevector alone exceeds aer_memory_mb.")
    available = psutil.virtual_memory().available / 2**30
    if available < config["min_available_gib"]:
        raise MemoryError(f"Only {available:.2f} GiB RAM available. Restart the kernel "
                          "and close other busy kernels/apps before running again.")
    return config


def _aer_components(config):
    """Compile once; run circuits and shots without parallel statevector copies."""
    options = {
        "method": "statevector", "device": "CPU", "precision": "double",
        "max_parallel_threads": config["aer_threads"],
        "max_parallel_experiments": 1, "max_parallel_shots": 1,
        # Aer limits quantum-state storage here, NOT the whole Python process.
        "max_memory_mb": config["aer_memory_mb"],
    }
    backend = AerSimulator(**options)
    sampler = SamplerV2(default_shots=config["shots"], seed=config["seed"],
                        options={"backend_options": options})
    manager = generate_preset_pass_manager(optimization_level=1, backend=backend,
                                            seed_transpiler=config["seed"])
    return backend, sampler, manager, options


def probe_qaoa_resources(bundle, config):
    """One initial-angle circuit evaluation before committing to optimization.

    This diagnostic is returned in memory only, never saved as a QAOA result.
    Its rough total estimate excludes decoding and is not a runtime guarantee.
    """
    config = _validated_config(bundle, config)
    operator, _ = build_ising(bundle)
    started = perf_counter()
    with _MemoryMonitor() as memory:
        _, sampler, manager, options = _aer_components(config)
        circuit = QAOAAnsatz(cost_operator=operator, reps=config["reps"])
        circuit.measure_all()
        compiled = manager.run(circuit)
        setup_seconds = perf_counter() - started
        sample_started = perf_counter()
        result = sampler.run([(compiled, config["initial_point"])]).result()[0]
        counts = result.data.meas.get_counts()
        sampling_seconds = perf_counter() - sample_started
        mean = sum(count * bundle["qubo"].objective.evaluate(
            integer_to_bits(key, operator.num_qubits)) for key, count in counts.items()
        ) / config["shots"]
    return {
        "instance_id": bundle["instance"]["instance_id"],
        "num_qubits": operator.num_qubits, "backend_options": options,
        "setup_seconds": setup_seconds, "sampling_seconds": sampling_seconds,
        "elapsed_seconds": perf_counter() - started,
        "rough_maxiter_plus_final_sampling_seconds": sampling_seconds * (config["maxiter"] + 1),
        "shots": sum(counts.values()), "observed_bitstrings": len(counts),
        "initial_sample_mean_qubo_energy": float(mean), "resources": memory.as_dict(),
    }


def run_qaoa_experiment(bundle, config, reference=None, progress=True):
    """QAOA with Aer CPU sampling and a single transpilation per optimization.

    The time budget is checked after evaluations, not a hard interrupt. Only
    completed runs may be persisted by save_experiment_report().
    """
    config = _validated_config(bundle, config)
    num_bits = bundle["qubo"].get_num_vars()
    limit = config["max_seconds"]
    if reference is None:
        reference = prepare_reference(bundle)
    operator, offset = build_ising(bundle)
    canonical_input = json.dumps(bundle["instance"], sort_keys=True,
                                 ensure_ascii=False, separators=(",", ":"))
    report = {
        "schema_version": 2,
        "scope": "phase3_original_instances_single_seed_pilot",
        "method": "QAOA_AerSamplerV2_CPU_statevector_COBYLA",
        "instance_id": bundle["instance"]["instance_id"],
        "instance": bundle["instance"],
        "instance_sha256": hashlib.sha256(canonical_input.encode("utf-8")).hexdigest(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(), "platform": platform.platform(),
        "numpy_version": np.__version__, "scipy_version": scipy.__version__,
        "qiskit_version": qiskit.__version__,
        "qiskit_optimization_version": qiskit_optimization.__version__,
        "qiskit_aer_version": qiskit_aer.__version__,
        "num_qubits": num_bits,
        "statevector_array_mib": 16 * 2**num_bits / 2**20,
        "pauli_terms": len(operator), "ising_offset": offset,
        "penalty": bundle["penalty"],
        "variable_names": [variable.name for variable in bundle["qubo"].variables],
        "config": config, "reference": reference,
        "optimization_history": [], "final_samples": None, "metrics": None,
    }
    started = perf_counter()

    def record_evaluation(eval_count, parameters, value, metadata):
        elapsed = perf_counter() - started
        mean_energy = float(np.real(value)) + offset
        report["optimization_history"].append({
            "evaluation": int(eval_count), "parameters": np.asarray(parameters).tolist(),
            "estimated_qubo_energy": mean_energy, "elapsed_seconds": elapsed,
        })
        if progress and (eval_count == 1 or eval_count % 5 == 0):
            print(f"  evaluation {eval_count}: mean E={mean_energy:.6f}, "
                  f"elapsed={elapsed:.1f}s", flush=True)
        if elapsed >= limit:
            raise _EvaluationTimeLimit("Elapsed budget reached after an evaluation.")

    _, sampler, manager, options = _aer_components(config)
    report["backend_options"] = options
    algorithm = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=config["maxiter"]),
                     reps=config["reps"], initial_point=config["initial_point"],
                     callback=record_evaluation, pass_manager=manager)
    try:
        with _MemoryMonitor() as memory:
            result = algorithm.compute_minimum_eigenvalue(operator)
    except _EvaluationTimeLimit:
        report.update({
            "status": "time_budget_exceeded",
            "elapsed_seconds": perf_counter() - started,
            "cost_function_evals": len(report["optimization_history"]),
            "stop_reason": "Time budget checked between optimizer evaluations.",
            "resources": memory.as_dict(),
        })
        return report

    # Separate solver timing from classical decoding/postprocessing timing.
    elapsed = perf_counter() - started
    decode_started = perf_counter()
    samples = decode_samples(bundle, result.eigenstate, operator, offset)
    report.update({
        "status": "completed", "elapsed_seconds": elapsed,
        "resources": memory.as_dict(),
        "cost_function_evals": int(result.cost_function_evals),
        "optimal_point": np.asarray(result.optimal_point).tolist(),
        "parameter_names": [str(parameter) for parameter in algorithm.ansatz.parameters],
        "optimizer_estimated_qubo_expectation": float(np.real(result.eigenvalue)) + offset,
        "observed_final_bitstrings": len(samples),
        "metrics": summarize_samples(samples, reference),
        "final_samples": [{
            "bits": sample["bits"], "probability": sample["probability"],
            "energy": sample["energy"], "decoded": sample["decoded"],
        } for sample in samples],
        "postprocessing_seconds": perf_counter() - decode_started,
    })
    return report


def save_experiment_report(root, report):
    """Save completed runs only; interrupted runs never produce result JSONs."""
    if report.get("status") != "completed":
        raise ValueError("Only completed QAOA runs are saved; no file was written.")
    if report.get("metrics") is None or not report.get("final_samples"):
        raise ValueError("A completed report must contain final samples and metrics.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    config = report["config"]
    name = (f"{report['instance_id']}_p{config['reps']}_"
            f"seed{config['seed']}_{stamp}.json")
    directory = Path(root) / "data" / "reference_results" / "phase3_runs"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)
                    + "\n", encoding="utf-8")
    return path
