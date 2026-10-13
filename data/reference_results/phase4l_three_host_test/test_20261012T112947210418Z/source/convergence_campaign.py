"""A small predeclared shot-noise/initialization diagnostic with verified resume."""
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
import numpy as np

from .independent_campaign import canonical_hash, save_campaign, report_row as placement_row
from .ising import build_ising, scale_ising, scaled_qaoa_point
from .penalty_analysis import penalty_diagnostics
from .qaoa_experiment import (
    _validated_config, experiment_environment, qubo_fingerprint, summarize_samples,
    save_experiment_report, distribution_statistics,
)
from .qaoa_optimizer import sampling_seeds

SCOPE = "phase4e_convergence_diagnostics"
METHODS = {"sampled": "QAOA_AerSamplerV2_CPU_statevector_COBYLA",
           "exact": "QAOA_AerExactExpectation_CPU_statevector_COBYLA"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def make_design(instance, bundle, seeds, base_config, starts=None, *, objective_modes=("sampled", "exact")):
    """One deterministic exact optimization per start; sampled seeds vary."""
    _require(instance == bundle["instance"] and bundle["penalty_mode"] == "independent"
             and bundle["penalties"] == {"assignment": 3., "capacity": 3.},
             "Notebook 12 fixes the instance and independent penalties (3,3).")
    _require(bool(seeds) and len(set(seeds)) == len(seeds)
             and all(type(s) is int and 0 <= s < 2**32 for s in seeds), "Distinct 32-bit seeds required.")
    _require(not set(base_config) & {"seed", "evaluation_seed", "reps", "initial_point"}
             and base_config.get("hamiltonian_scaling") == "max_abs",
             "Seeds/depth/starts are set by the normalized experiment arms.")
    starts = {"common": [0.3, 1.0], "alternative": [0.8, 1.2]} if starts is None else starts
    _require(set(starts) == {"common", "alternative"}, "Two named starts are required.")
    normalized_starts = {}
    for name, point in starts.items():
        _require(len(point) == 2 and all(not isinstance(v, (bool, np.bool_)) for v in point)
                 and np.isfinite(point).all(), "Two finite p=1 angles are required.")
        normalized_starts[name] = [float(v) for v in point]
    config = _validated_config(bundle, {**base_config, "seed": seeds[0], "reps": 1,
                                       "initial_point": normalized_starts["common"]})
    _require(config["maxiter"] >= 4, "p=1 COBYLA needs at least four evaluations.")
    for name in ("seed", "reps", "initial_point"):
        config.pop(name)
    raw, _ = build_ising(bundle)
    _, scaling = scale_ising(raw, "max_abs")
    modes = tuple(objective_modes)
    _require(bool(modes) and len(set(modes)) == len(modes) and set(modes) <= set(METHODS),
             "Select distinct known objective modes.")
    design = {"instance_id": instance["instance_id"], "instance_sha256": canonical_hash(instance),
            "model_version": bundle["model_version"], "qubo_sha256": qubo_fingerprint(bundle),
            "penalties": bundle["penalties"].copy(), "normalization": scaling,
            "base_config": config, "seeds": list(seeds), "starts": normalized_starts,
            "environment": experiment_environment(),
            "study": {"stage": "shot_noise_and_initialization_diagnostic", "protocol_version": 1,
                "depth": 1, "sampling_protocol": "independent_final_v1",
                "primary_diagnostic": "optimizer_estimate_vs_independent_measurement_vs_ideal_expectation",
                "quality_metric": "measured_optimal_placement_probability",
                "budget_rule": "same_max_function_evaluations_and_final_shots; runtime_reported_separately",
                "exact_repetition_rule": "one_deterministic_optimization_per_start_no_seed_pseudoreplication",
                "output_rule": "observed_bits_only_with_frequency_ties_disclosed"}}
    # Preserve the historical Notebook 12 design/hash when using both modes.
    if modes != ("sampled", "exact"):
        design["objective_modes"] = list(modes)
    return design


def make_trials(design):
    trials = []
    for init_id, point in design["starts"].items():
        for mode in design.get("objective_modes", ("sampled", "exact")):
            seeds = design["seeds"] if mode == "sampled" else design["seeds"][:1]
            for seed in seeds:
                config = {**design["base_config"], "seed": seed, "reps": 1, "initial_point": list(point)}
                config["evaluation_seed"] = sampling_seeds(config)["evaluation_seed"]
                row = {"instance_id": design["instance_id"], "pair_id": "common_P3",
                       "initial_point_id": init_id, "objective_mode": mode,
                       "arm_id": f"{mode}_{init_id}", "seed": seed, "config": config}
                row["run_key"] = canonical_hash({"design_hash": canonical_hash(design), **row})
                trials.append(row)
    return trials


def new_campaign(design):
    return {"schema_version": 1, "scope": SCOPE,
            "campaign_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
            "design": design, "design_hash": canonical_hash(design),
            "planned_runs": make_trials(design), "completed_runs": []}


def _identity(campaign, trial):
    return {"campaign_id": campaign["campaign_id"], "design_hash": campaign["design_hash"],
            "run_key": trial["run_key"], "arm_id": trial["arm_id"],
            "objective_mode": trial["objective_mode"], "purpose": campaign["design"]["study"]["stage"]}


def _point_hash(report):
    return canonical_hash({"qubo": report["provenance"]["qubo"],
                           "point": report["optimal_point"], "config": report["config"]})


def report_row(root, path, report, trial):
    exact = report["exact_diagnostics"]
    observed = report["metrics"]["final_sample_mean_qubo_energy"]
    estimate = report["optimizer_estimated_qubo_expectation"]
    evaluation_shots = report["sampling"]["evaluation_shots"]
    return {**placement_row(root, path, report, trial),
        "arm_id": trial["arm_id"], "objective_mode": trial["objective_mode"],
        "evaluation_seed": report["sampling"]["evaluation_seed"], "evaluation_shots": evaluation_shots,
        "optimizer_success": report["optimizer_stop"]["success"],
        "optimizer_status": report["optimizer_stop"]["status"], "optimizer_message": report["optimizer_stop"]["message"],
        "optimizer_estimated_energy": estimate, **exact,
        "training_minus_exact_energy": estimate - exact["exact_mean_qubo_energy"],
        "evaluation_minus_exact_energy": observed - exact["exact_mean_qubo_energy"],
        "evaluation_standard_error_exact": exact["exact_energy_std"] / np.sqrt(evaluation_shots),
        "evaluation_standard_error_sample": report["sampling_statistics"]["evaluation"]["mean_standard_error"],
        "optimization_seconds": report["optimization_seconds"],
        "evaluation_sampling_seconds": report["evaluation_sampling_seconds"],
        "exact_audit_seconds": report["exact_audit_seconds"], "optimal_point": report["optimal_point"],
        "initial_point": trial["config"]["initial_point"]}


def record_trial(root, campaign, trial, report, bundle, oracle):
    """Audit the final point once and persist a completed, measured trial."""
    _require(report.get("status") == "completed", "Only completed trials may be recorded.")
    _require(report.get("method") == METHODS[trial["objective_mode"]],
             "The report evaluation method does not match this experiment arm.")
    _require(trial in campaign["planned_runs"] and report["config"] == trial["config"]
             and trial["run_key"] not in {r["run_key"] for r in campaign["completed_runs"]},
             "Trial/config differs or already completed.")
    oracle.check_compatible(bundle, report["config"], report["reference"])
    started = perf_counter()
    report["exact_diagnostics"] = oracle.evaluate(report["optimal_point"])
    report["exact_audit_seconds"] = perf_counter() - started
    report["exact_diagnostics_point_sha256"] = _point_hash(report)
    report["scope"], report["experiment"], report["study"] = SCOPE, _identity(campaign, trial), campaign["design"]["study"]
    started = perf_counter()
    report["penalty_analysis"] = penalty_diagnostics(bundle, report)
    report["penalty_analysis_seconds"] = perf_counter() - started
    path = save_experiment_report(root, report)
    campaign["completed_runs"].append(report_row(root, path, report, trial))
    return path


def verify_campaign(root, campaign, design, bundle, reference, *, require_current_environment=True):
    """Recompute measured metrics from source bits before resuming or reporting."""
    _require(campaign["scope"] == SCOPE and campaign["schema_version"] == 1, "Use a notebook 12 manifest.")
    _require(campaign["design"] == design and campaign["design_hash"] == canonical_hash(design),
             "Design changed; create a new campaign.")
    # False is for reading archived evidence only, never for resuming a run.
    _require(not require_current_environment or experiment_environment() == design["environment"],
             "Code/runtime changed; create a new campaign.")
    _require(canonical_hash(bundle["instance"]) == design["instance_sha256"]
             and qubo_fingerprint(bundle) == design["qubo_sha256"] and bundle["penalties"] == design["penalties"],
             "Input/model differs.")
    planned = make_trials(design)
    _require(campaign["planned_runs"] == planned, "Planned trials differ.")
    lookup = {t["run_key"]: t for t in planned}
    rows, root = campaign["completed_runs"], Path(root).resolve()
    keys = [r["run_key"] for r in rows]
    _require(len(keys) == len(set(keys)) and set(keys) <= set(lookup), "Duplicate/unplanned completed trials.")
    _require(campaign["planned_run_count"] == len(planned) and campaign["completed_run_count"] == len(rows)
             and campaign["remaining_run_keys"] == [t["run_key"] for t in planned if t["run_key"] not in keys],
             "Manifest counts differ.")
    raw, offset = build_ising(bundle)
    _, scaling = scale_ising(raw, "max_abs")
    _require(scaling == design["normalization"], "Design normalization differs.")
    for row in rows:
        trial = lookup[row["run_key"]]
        path = (root / row["report"]).resolve()
        _require(path.is_relative_to(root), "Report path must stay inside the repository.")
        r = json.loads(path.read_text(encoding="utf-8"))
        _require(r["status"] == "completed" and r["scope"] == SCOPE and r["schema_version"] == 3
                 and r["method"] == METHODS[trial["objective_mode"]]
                 and r["experiment"] == _identity(campaign, trial) and r["study"] == design["study"], "Report identity differs.")
        _require(r["config"] == trial["config"] and r["penalties"] == design["penalties"]
                 and r["penalty_mode"] == "independent" and r["penalty"] == 3., "Controls differ.")
        _require(r["instance"] == bundle["instance"] and r["instance_id"] == design["instance_id"]
                 and r["instance_sha256"] == design["instance_sha256"]
                 and r["provenance"] == {"model_version": bundle["model_version"], "qubo": qubo_fingerprint(bundle)}
                 and r["environment"] == design["environment"] and r["reference"] == reference
                 and r["variable_names"] == [v.name for v in bundle["qubo"].variables]
                 and r["num_qubits"] == raw.num_qubits and r["ising_offset"] == offset and r["pauli_terms"] == len(raw),
                 "Model/reference/runtime differs.")
        _require(r["hamiltonian_scaling"] == scaling and r["parameter_names"] == ["β[0]", "γ[0]"]
                 and len(r["optimal_point"]) == 2 and np.isfinite(r["optimal_point"]).all()
                 and np.allclose(r["optimal_point_raw_hamiltonian"],
                     scaled_qaoa_point(r["optimal_point"], 1, 1/scaling["scale"]), rtol=0, atol=1e-10), "Angle units differ.")
        history, stop = r["optimization_history"], r["optimizer_stop"]
        _require(0 < len(history) == r["cost_function_evals"] == stop["nfev"] <= trial["config"]["maxiter"]
                 and type(stop["status"]) is int and type(stop["success"]) is bool
                 and isinstance(stop["message"], str) and bool(stop["message"].strip())
                 and [h["evaluation"] for h in history] == list(range(1, len(history)+1))
                 and history[0]["parameters"] == trial["config"]["initial_point"]
                 and all(len(h["parameters"]) == 2 and np.isfinite(h["parameters"]).all() for h in history),
                 "Optimizer history/termination differs.")
        _require(all(np.isclose(h["estimated_qubo_energy"], scaling["scale"]*h["execution_hamiltonian_expectation"]+offset,
                               rtol=0, atol=1e-7) for h in history)
                 and np.isclose(r["optimizer_estimated_qubo_expectation"],
                     scaling["scale"]*r["optimizer_estimated_execution_expectation"]+offset, rtol=0, atol=1e-7), "Energy units differ.")
        _require(r["sampling_protocol"] == "independent_final_v1" and r["sampling"] == sampling_seeds(trial["config"]),
                 "Final measurement seed/shots differs.")
        samples, shots = r["final_samples"], r["sampling"]["evaluation_shots"]
        bits = np.array([s["bits"] for s in samples]); probs = np.array([s["probability"] for s in samples])
        _require(bits.shape == (len(samples), raw.num_qubits) and np.isin(bits, [0, 1]).all()
                 and np.isfinite(probs).all() and (probs > 0).all(), "Invalid samples.")
        counts = np.rint(probs*shots)
        _require(len({tuple(b) for b in bits}) == len(samples) == r["observed_final_bitstrings"]
                 and counts.sum() == shots and (counts > 0).all() and (probs[:-1] >= probs[1:]).all()
                 and np.allclose(probs, counts/shots, rtol=0, atol=1e-12), "Final counts differ.")
        _require(penalty_diagnostics(bundle, r) == r["penalty_analysis"]
                 and summarize_samples(samples, reference) == r["metrics"], "Metrics differ from raw bits.")
        distribution = {sum(int(v) << k for k, v in enumerate(s["bits"])): s["probability"] for s in samples}
        expected_stats = distribution_statistics(bundle, distribution, shots, r["sampling"]["evaluation_seed"])
        _require(r["sampling_statistics"]["evaluation"] == expected_stats, "Evaluation statistics differ.")
        exact = r["exact_diagnostics"]
        _require(r["exact_diagnostics_point_sha256"] == _point_hash(r), "Exact diagnostic point/model differs.")
        _require(all(np.isfinite(exact[k]) and 0 <= exact[k] <= 1+1e-9 for k in (
                     "exact_feasible_probability", "exact_optimal_probability", "exact_ground_probability", "exact_onehot_probability"))
                 and exact["exact_optimal_probability"] <= exact["exact_feasible_probability"]+1e-9
                 and np.isfinite(exact["exact_mean_qubo_energy"]) and exact["exact_mean_qubo_energy"] >= reference["minimum_energy"]-1e-7
                 and np.isfinite(exact["exact_energy_std"]) and exact["exact_energy_std"] >= 0
                 and np.isclose(exact["standard_error_at_training_shots"], exact["exact_energy_std"]/np.sqrt(trial["config"]["shots"]),
                                rtol=0, atol=1e-10), "Invalid ideal diagnostics.")
        if trial["objective_mode"] == "exact":
            _require(np.isclose(r["optimizer_estimated_qubo_expectation"], exact["exact_mean_qubo_energy"], rtol=0, atol=1e-7)
                     and all(h.get("objective_source") == "ideal_statevector_expectation" for h in history), "Exact objective differs.")
        else:
            training = r["sampling_statistics"]["training"]
            _require(training["seed"] == trial["seed"] and training["shots"] == trial["config"]["shots"]
                     and np.isclose(training["mean_qubo_energy"], r["optimizer_estimated_qubo_expectation"], rtol=0, atol=1e-7)
                     and all(h.get("objective_source") != "ideal_statevector_expectation" for h in history),
                     "Sampled objective differs.")
        _require(report_row(root, path, r, trial) == row, "Manifest row differs from source report.")
    return rows
