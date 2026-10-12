"""Small, sequential pilot campaigns with reproducible inputs and verified resume."""

from datetime import datetime, timezone
from itertools import product
import hashlib
import json
from pathlib import Path

import numpy as np

from .penalty_analysis import penalty_diagnostics
from .qaoa_experiment import experiment_environment, qubo_fingerprint, summarize_samples

SCOPE = "phase4b_independent_penalty_pilot"


def canonical_hash(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def make_design(instances, pairs, initial_points, seeds, base_config):
    _require(bool(instances) and all(v["instance_id"] == k for k, v in instances.items()),
             "Instance identifiers must match the design.")
    _require(bool(pairs), "At least one penalty pair is required.")
    normalized = {}
    for name, values in pairs.items():
        _require(len(values) == 2 and all(not isinstance(v, (bool, np.bool_)) for v in values),
                 "Each pair requires two numerical weights.")
        values = [float(v) for v in values]
        _require(np.isfinite(values).all() and min(values) > 0, "Weights must be positive and finite.")
        normalized[name] = values
    _require(len({tuple(v) for v in normalized.values()}) == len(normalized), "Duplicate penalty pairs.")
    _require(bool(seeds) and len(set(seeds)) == len(seeds)
             and all(type(s) is int and s >= 0 for s in seeds), "Seeds must be distinct nonnegative integers.")
    _require(base_config.get("reps") == 1, "This pilot holds depth p=1 fixed.")
    _require(bool(initial_points) and all(len(v) == 2 and np.isfinite(v).all()
                                        for v in initial_points.values()), "Two finite angles are required.")
    return {
        "instance_ids": list(instances), "instance_sha256": {k: canonical_hash(v) for k, v in instances.items()},
        "penalty_pairs": normalized, "initial_points": initial_points,
        "seeds": list(seeds), "base_config": dict(base_config),
        "diagnostics_version": 2, "model_version": "weighted_equalities_v2",
        "environment": experiment_environment(),
    }


def make_trials(design):
    trials = []
    design_hash = canonical_hash(design)
    for name, pair_id, init_id, seed in product(design["instance_ids"], design["penalty_pairs"],
                                              design["initial_points"], design["seeds"]):
        config = {**design["base_config"], "seed": seed,
                  "initial_point": list(design["initial_points"][init_id])}
        row = {"instance_id": name, "pair_id": pair_id, "initial_point_id": init_id,
               "seed": seed, "config": config}
        row["run_key"] = canonical_hash({"design_hash": design_hash, **row})
        trials.append(row)
    return trials


def new_campaign(design):
    return {"schema_version": 1, "scope": SCOPE,
            "campaign_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
            "design": design, "design_hash": canonical_hash(design),
            "planned_runs": make_trials(design), "completed_runs": []}


def save_campaign(path, campaign):
    planned = {r["run_key"] for r in campaign["planned_runs"]}
    completed = [r["run_key"] for r in campaign["completed_runs"]]
    _require(len(set(completed)) == len(completed) and set(completed) <= planned,
             "Completed run keys must be unique and planned.")
    campaign.update(updated_at_utc=datetime.now(timezone.utc).isoformat(),
                    planned_run_count=len(planned), completed_run_count=len(completed),
                    remaining_run_keys=[r["run_key"] for r in campaign["planned_runs"]
                                        if r["run_key"] not in set(completed)])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(campaign, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def report_row(root, path, report, trial):
    metrics = report["metrics"]
    best = metrics["best_observed_valid"]
    optimum = report["reference"]["original_best_objective"]
    probability = metrics["optimal_placement_probability"]
    return {
        **{k: trial[k] for k in ("run_key", "instance_id", "pair_id", "initial_point_id", "seed")},
        "report": Path(path).resolve().relative_to(Path(root).resolve()).as_posix(),
        "assignment_penalty": report["penalties"]["assignment"],
        "capacity_penalty": report["penalties"]["capacity"],
        "num_qubits": report["num_qubits"],
        **{k: report["config"][k] for k in ("shots", "reps", "maxiter")},
        "original_best_objective": optimum,
        "observed_best_objective": None if best is None else best["objective"],
        "optimality_gap": None if best is None or optimum is None else best["objective"] - optimum,
        "found_valid": metrics["feasible_probability"] > 0,
        "found_optimal": None if probability is None else probability > 0,
        **{k: metrics[k] for k in ("feasible_probability", "optimal_placement_probability",
                                  "qubo_ground_state_probability", "final_sample_mean_qubo_energy")},
        **report["penalty_analysis"],
        **{k: report[k] for k in ("elapsed_seconds", "postprocessing_seconds",
                                "penalty_analysis_seconds", "cost_function_evals")},
        "process_peak_rss_mib": report["resources"]["process_peak_rss_mib"],
    }


def verify_campaign(root, campaign, design, bundles, references):
    """Read one source report at a time; reject changed designs or altered samples."""
    _require(campaign["scope"] == SCOPE and campaign["schema_version"] == 1,
             "Use a notebook 08 campaign, not a notebook 06/07 manifest.")
    _require(campaign["design"] == design and campaign["design_hash"] == canonical_hash(design),
             "Input, weights, configuration, runtime or source changed. Start a new campaign.")
    _require(experiment_environment() == design["environment"], "Runtime or source changed during the campaign.")
    planned = make_trials(design)
    _require(campaign["planned_runs"] == planned, "Planned trials differ from the design.")
    lookup = {t["run_key"]: t for t in planned}
    rows = campaign["completed_runs"]
    keys = [r["run_key"] for r in rows]
    _require(len(set(keys)) == len(keys) and set(keys) <= set(lookup), "Duplicate or unplanned completed trials.")
    _require(campaign["planned_run_count"] == len(planned)
             and campaign["completed_run_count"] == len(rows)
             and campaign["remaining_run_keys"] == [t["run_key"] for t in planned if t["run_key"] not in keys],
             "Manifest counts or remaining run keys are inconsistent.")
    root = Path(root).resolve()
    for row in rows:
        trial = lookup[row["run_key"]]
        bundle = bundles[trial["instance_id"], trial["pair_id"]]
        path = (root / row["report"]).resolve()
        _require(path.is_relative_to(root), "Source report must stay inside the repository.")
        report = json.loads(path.read_text(encoding="utf-8"))
        expected_experiment = {"campaign_id": campaign["campaign_id"], "design_hash": campaign["design_hash"],
            "run_key": trial["run_key"], "pair_id": trial["pair_id"],
            "initial_point_id": trial["initial_point_id"], "purpose": "controlled_independent_penalty_pilot"}
        _require(report["status"] == "completed" and report["schema_version"] == 3
                 and report["experiment"] == expected_experiment, "Report identity or status differs.")
        _require(report["config"] == trial["config"] and report["penalties"] == bundle["penalties"]
                 and report["penalty"] == bundle["penalty"] and report["penalty_mode"] == "independent",
                 "Report configuration or weights differ.")
        _require(report["instance_id"] == trial["instance_id"] and report["instance"] == bundle["instance"]
                 and report["instance_sha256"] == canonical_hash(bundle["instance"]), "Report input differs.")
        _require(report["environment"] == design["environment"]
                 and report["provenance"] == {"model_version": bundle["model_version"], "qubo": qubo_fingerprint(bundle)}
                 and report["variable_names"] == [v.name for v in bundle["qubo"].variables]
                 and report["num_qubits"] == bundle["qubo"].get_num_vars(), "Report model or provenance differs.")
        reference = references[trial["instance_id"], trial["pair_id"]]
        _require(report["reference"] == reference, "Exact reference differs.")
        samples = report["final_samples"]
        probs = np.array([s["probability"] for s in samples])
        shots = report["config"]["shots"]
        counts = np.rint(probs * shots)
        _require(len({tuple(s["bits"]) for s in samples}) == len(samples) == report["observed_final_bitstrings"]
                 and np.all(counts > 0) and counts.sum() == shots
                 and np.allclose(probs, counts / shots, rtol=0, atol=1e-12)
                 and np.all(probs[:-1] >= probs[1:]), "Observed probabilities or sample counts differ.")
        _require(penalty_diagnostics(bundle, report) == report["penalty_analysis"], "Diagnostics differ from samples.")
        _require(summarize_samples(samples, reference) == report["metrics"], "Metrics differ from samples.")
        _require(report_row(root, path, report, trial) == row, "Manifest row differs from source report.")
    return rows
