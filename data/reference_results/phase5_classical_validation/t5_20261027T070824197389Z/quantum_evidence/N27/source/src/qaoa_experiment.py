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

from .ising import build_ising, decode_samples, integer_to_bits, scale_ising, scaled_qaoa_point
from .qubo import decode_qubo, exact_qubo_reference
from .qaoa_optimizer import RecordingCOBYLA, sampling_seeds


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
        min_energy = objective + bundle["penalties"]["assignment"] * assignment_error
        conditional_mean = float(min_energy)
        multiplicity = 1
        for group, encoding_counts in zip(groups, encodings):
            h, r = group["host"], group["resource_index"]
            residual_without_slack = (
                decoded["usage"][h][r] - group["capacity"] * decoded["y"][h]
            )
            target = max(0, -residual_without_slack)
            multiplicity *= encoding_counts[target]
            min_energy += bundle["penalties"]["capacity"] * (residual_without_slack + target)**2
            weights = group["weights"]
            slack_mean = sum(weights) / 2
            slack_variance = sum(weight**2 for weight in weights) / 4
            conditional_mean += bundle["penalties"]["capacity"] * (
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
    sampling_seeds(config)
    initial_point = config.get("initial_point", [0.3] * config["reps"] + [0.7] * config["reps"])
    if len(initial_point) != 2 * config["reps"] or not np.isfinite(initial_point).all():
        raise ValueError("initial_point needs two finite angles per QAOA layer.")
    config["initial_point"] = [float(value) for value in initial_point]
    if config.get("hamiltonian_scaling", "none") not in ("none", "max_abs"):
        raise ValueError("hamiltonian_scaling must be 'none' or 'max_abs'.")
    radius = config.get("cobyla_rhobeg", 1.0)
    if isinstance(radius, (bool, np.bool_)) or not np.isfinite(radius) or radius <= 0:
        raise ValueError("cobyla_rhobeg must be positive and finite.")
    tolerance = config.get("cobyla_tol", 1e-4)
    if isinstance(tolerance, (bool, np.bool_)) or not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("cobyla_tol must be positive and finite.")
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
    raw_operator, _ = build_ising(bundle)
    operator, scaling = scale_ising(raw_operator, config.get("hamiltonian_scaling", "none"))
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
    result = {
        "instance_id": bundle["instance"]["instance_id"],
        "num_qubits": operator.num_qubits, "backend_options": options,
        "setup_seconds": setup_seconds, "sampling_seconds": sampling_seconds,
        "elapsed_seconds": perf_counter() - started,
        "rough_maxiter_plus_final_sampling_seconds": sampling_seconds * (config["maxiter"] + 1),
        "shots": sum(counts.values()), "observed_bitstrings": len(counts),
        "initial_sample_mean_qubo_energy": float(mean), "resources": memory.as_dict(),
    }
    if "hamiltonian_scaling" in config:
        result["hamiltonian_scaling"] = scaling
    return result


def experiment_environment():
    """Record the actual runtime and source bytes used by the current installation."""
    directory = Path(__file__).resolve().parent
    names = ("placement.py", "qubo.py", "ising.py", "qaoa_experiment.py",
             "penalty_analysis.py", "independent_campaign.py", "scaling_campaign.py", "depth_campaign.py",
             "qaoa_optimizer.py", "convergence_diagnostics.py", "convergence_campaign.py")
    return {
        "runtime": {
            "python_version": platform.python_version(), "platform": platform.platform(),
            "numpy_version": np.__version__, "scipy_version": scipy.__version__,
            "qiskit_version": qiskit.__version__,
            "qiskit_optimization_version": qiskit_optimization.__version__,
            "qiskit_aer_version": qiskit_aer.__version__,
        },
        "source_sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                          for name in names if (directory / name).is_file()},
    }


def qubo_fingerprint(bundle):
    """Bind a report to variable order and the actual objective coefficients."""
    objective = bundle["qubo"].objective
    value = {"variables": [v.name for v in bundle["qubo"].variables],
             "constant": objective.constant, "linear": objective.linear.to_array().tolist(),
             "quadratic": objective.quadratic.to_array().tolist()}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _new_report(bundle, config, reference, operator, offset, scaling):
    """Common model/provenance fields for both objective evaluation methods."""
    num_bits = bundle["qubo"].get_num_vars()
    canonical_input = json.dumps(bundle["instance"], sort_keys=True,
                                 ensure_ascii=False, separators=(",", ":"))
    report = {
        "schema_version": 3 if bundle["penalty_mode"] == "independent" else 2,
        "scope": ("phase4b_independent_penalty_pilot" if bundle["penalty_mode"] == "independent"
                  else "phase3_original_instances_single_seed_pilot"),
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
        "penalties": bundle["penalties"].copy(), "penalty_mode": bundle["penalty_mode"],
        "provenance": {"model_version": bundle["model_version"], "qubo": qubo_fingerprint(bundle)},
        "environment": experiment_environment(),
        "variable_names": [variable.name for variable in bundle["qubo"].variables],
        "config": config, "reference": reference,
        "optimization_history": [], "final_samples": None, "metrics": None,
        "sampling_protocol": "independent_final_v1", "sampling": sampling_seeds(config),
    }
    if "hamiltonian_scaling" in config:
        report["hamiltonian_scaling"] = scaling
    return report


def distribution_statistics(bundle, distribution, shots, seed):
    """Sample standard deviation and SE of a measured energy mean.

    This estimates noise at ONE fixed point. It is not an optimizer stopping
    certificate, and a training-selected point can still have selection bias.
    """
    energies = np.array([bundle["qubo"].objective.evaluate(
        integer_to_bits(key, bundle["qubo"].get_num_vars())) for key in distribution])
    probabilities = np.array(list(distribution.values()), dtype=float)
    mean = float(probabilities @ energies)
    variance = float(probabilities @ np.square(energies - mean))
    # Frequencies with denominator n: convert to unbiased sample variance.
    sample_std = float(np.sqrt(max(0., variance) * shots / (shots - 1))) if shots > 1 else None
    return {"mean_qubo_energy": mean, "energy_std": sample_std,
            "mean_standard_error": None if sample_std is None else sample_std / np.sqrt(shots),
            "shots": shots, "seed": seed, "variance_estimator": "unbiased_sample"}


def _measure_final(bundle, config, operator, point, manager=None, options=None):
    """Fresh measured circuit; no reused optimizer eigenstate or repaired bits."""
    seeds = sampling_seeds(config)
    if manager is None:
        _, _, manager, options = _aer_components(config)
    circuit = QAOAAnsatz(cost_operator=operator, reps=config["reps"])
    circuit.measure_all()
    compiled = manager.run(circuit)
    if compiled.layout is not None and compiled.layout.final_index_layout() != list(range(operator.num_qubits)):
        raise ValueError("Final measurement requires identity qubit layout.")
    sampler = SamplerV2(default_shots=seeds["evaluation_shots"], seed=seeds["evaluation_seed"],
                        options={"backend_options": options})
    counts = sampler.run([(compiled, point)]).result()[0].data.meas.get_counts()
    if sum(counts.values()) != seeds["evaluation_shots"]:
        raise AssertionError("Final shot count differs from the declared evaluation batch.")
    return {key: count / seeds["evaluation_shots"] for key, count in counts.items()}


def _complete_report(report, bundle, raw_operator, offset, scaling, point, estimate,
                     distribution, optimizer, reference, parameter_names):
    config = report["config"]
    samples = decode_samples(bundle, distribution, raw_operator, offset)
    report.update({
        "status": "completed", "cost_function_evals": optimizer.stop["nfev"],
        "optimizer_stop": optimizer.stop.copy(), "optimal_point": np.asarray(point).tolist(),
        "parameter_names": parameter_names,
        "optimizer_estimated_qubo_expectation": scaling["scale"] * float(estimate) + offset,
        "observed_final_bitstrings": len(samples), "metrics": summarize_samples(samples, reference),
        "final_samples": samples,
    })
    if optimizer.stop["nfev"] != len(report["optimization_history"]):
        raise AssertionError("Optimizer evaluation count differs from recorded history.")
    report.setdefault("sampling_statistics", {})["evaluation"] = distribution_statistics(
        bundle, distribution, report["sampling"]["evaluation_shots"], report["sampling"]["evaluation_seed"])
    if "hamiltonian_scaling" in config:
        report["optimizer_estimated_execution_expectation"] = float(estimate)
        report["optimal_point_raw_hamiltonian"] = scaled_qaoa_point(
            report["optimal_point"], config["reps"], 1 / scaling["scale"])


def run_qaoa_experiment(bundle, config, reference=None, progress=True):
    """Train with shots; score a fresh final batch with a separate fixed seed.

    The time guard is checked between expensive calls, not a hard interrupt.
    Only completed runs may be persisted by save_experiment_report().
    """
    config = _validated_config(bundle, config)
    limit = config["max_seconds"]
    reference = prepare_reference(bundle) if reference is None else reference
    raw_operator, offset = build_ising(bundle)
    operator, scaling = scale_ising(raw_operator, config.get("hamiltonian_scaling", "none"))
    report = _new_report(bundle, config, reference, operator, offset, scaling)
    started = perf_counter()

    def record_evaluation(eval_count, parameters, value, metadata):
        elapsed = perf_counter() - started
        executed_value = float(np.real(value))
        mean_energy = scaling["scale"] * executed_value + offset
        entry = {
            "evaluation": int(eval_count), "parameters": np.asarray(parameters).tolist(),
            "estimated_qubo_energy": mean_energy, "elapsed_seconds": elapsed,
        }
        if "hamiltonian_scaling" in config:
            entry["execution_hamiltonian_expectation"] = executed_value
        report["optimization_history"].append(entry)
        if progress and (eval_count == 1 or eval_count % 5 == 0):
            print(f"  evaluation {eval_count}: mean E={mean_energy:.6f}, "
                  f"elapsed={elapsed:.1f}s", flush=True)
        if elapsed >= limit:
            raise _EvaluationTimeLimit("Elapsed budget reached after an evaluation.")

    _, sampler, manager, options = _aer_components(config)
    report["backend_options"] = options
    optimizer = RecordingCOBYLA(config["maxiter"], config.get("cobyla_rhobeg", 1.0),
                                config.get("cobyla_tol", 1e-4))
    algorithm = QAOA(sampler=sampler, optimizer=optimizer,
                     reps=config["reps"], initial_point=config["initial_point"],
                     callback=record_evaluation, pass_manager=manager)
    try:
        with _MemoryMonitor() as memory:
            result = algorithm.compute_minimum_eigenvalue(operator)
            report["optimization_seconds"] = perf_counter() - started
            sample_started = perf_counter()
            distribution = _measure_final(bundle, config, operator, result.optimal_point, manager, options)
            report["evaluation_sampling_seconds"] = perf_counter() - sample_started
            if perf_counter() - started >= limit:
                raise _EvaluationTimeLimit("Elapsed budget reached after independent final sampling.")
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
    report.update({"elapsed_seconds": elapsed, "resources": memory.as_dict(),
        "sampling_statistics": {"training": distribution_statistics(
            bundle, result.eigenstate, config["shots"], config["seed"])}})
    _complete_report(report, bundle, raw_operator, offset, scaling, result.optimal_point,
                     float(np.real(result.eigenvalue)), distribution, optimizer, reference,
                     [str(parameter) for parameter in algorithm.ansatz.parameters])
    report["postprocessing_seconds"] = perf_counter() - decode_started
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
    if report.get("penalty_mode") == "independent":
        weights = report["penalties"]
        name = (f"{report['instance_id']}_a{weights['assignment']:g}_c{weights['capacity']:g}_"
                f"p{config['reps']}_seed{config['seed']}_{stamp}.json")
    folder = "phase4b_independent_runs" if report.get("penalty_mode") == "independent" else "phase3_runs"
    if report.get("scope") == "phase4c_hamiltonian_scaling":
        arm = report.get("experiment", {}).get("arm_id")
        if arm not in ("raw_original", "normalized_matched", "normalized_common"):
            raise ValueError("A scaling report requires a known experiment arm.")
        folder = "phase4c_scaling_runs"
        name = f"{report['instance_id']}_{arm}_p{config['reps']}_seed{config['seed']}_{stamp}.json"
    if report.get("scope") == "phase4d_depth_comparison":
        arm = report.get("experiment", {}).get("arm_id")
        if {"p1_control": 1, "p2_embedded": 2}.get(arm) != config["reps"]:
            raise ValueError("A depth report requires an arm matching its QAOA depth.")
        folder = "phase4d_depth_runs"
        name = f"{report['instance_id']}_{arm}_p{config['reps']}_seed{config['seed']}_{stamp}.json"
    if report.get("scope") == "phase4e_convergence_diagnostics":
        arm = report.get("experiment", {}).get("arm_id")
        if arm not in ("sampled_common", "exact_common", "sampled_alternative", "exact_alternative"):
            raise ValueError("A convergence report requires a known experiment arm.")
        folder = "phase4e_convergence_runs"
        name = f"{report['instance_id']}_{arm}_seed{config['seed']}_{stamp}.json"
    directory = Path(root) / "data" / "reference_results" / folder
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)
                    + "\n", encoding="utf-8")
    return path
