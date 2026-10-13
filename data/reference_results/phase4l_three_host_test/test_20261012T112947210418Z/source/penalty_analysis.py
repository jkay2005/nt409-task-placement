"""Observed-sample diagnostics for common or independent penalties and tied modes."""

import numpy as np

from .qubo import energy_parts, decode_qubo


def penalty_diagnostics(bundle, report):
    """Use observed samples without repairing slack or placement bits.

    Squared equation errors are comparable across P for the same instance.
    They include incorrect slack, not just original capacity violations.
    A tied frequency maximum has no unique mode; report its validity as None.
    """
    if report.get("status") != "completed":
        raise ValueError("Diagnostics require a completed sampling report.")
    weights = report.get("penalties")
    if weights is None and report.get("penalty") is not None:
        weights = {"assignment": report["penalty"], "capacity": report["penalty"]}
    if weights != bundle["penalties"]:
        raise ValueError("Report and QUBO penalties differ.")
    samples = report["final_samples"]
    if not samples:
        raise ValueError("No observed samples.")
    probs = np.asarray([s["probability"] for s in samples], dtype=float)
    if (not np.isfinite(probs).all() or (probs <= 0).any()
            or not np.isclose(probs.sum(), 1, rtol=0, atol=1e-8)):
        raise ValueError("Observed probabilities must be positive and sum to one.")
    averages = {key: 0.0 for key in ("active_hosts", "assignment_error", "capacity_error", "energy")}
    valid = []
    one_hot_probability = 0.0
    for sample in samples:
        parts = energy_parts(bundle, sample["bits"])
        decoded = decode_qubo(bundle, sample["bits"])
        if decoded != sample["decoded"] or not np.isclose(
                parts["energy"], sample["energy"], rtol=0, atol=1e-7):
            raise ValueError("Observed bits disagree with decoded data or energy.")
        for key in averages:
            averages[key] += sample["probability"] * parts[key]
        valid.append(decoded["feasible"])
        if decoded["one_hot_ok"]:
            one_hot_probability += sample["probability"]
    if not np.isclose(averages["energy"],
                      report["metrics"]["final_sample_mean_qubo_energy"], rtol=0, atol=1e-7):
        raise ValueError("Observed samples disagree with the reported mean energy.")
    top = np.isclose(probs, probs.max(), rtol=0, atol=1e-12)
    dominant = int(top.sum())
    dominant_valid = int(sum(flag for flag, selected in zip(valid, top) if selected))
    result = {
        "mean_active_hosts": averages["active_hosts"],
        "mean_assignment_error": averages["assignment_error"],
        "mean_capacity_equation_error": averages["capacity_error"],
        "mean_total_squared_error": averages["assignment_error"] + averages["capacity_error"],
        "reconstructed_mean_energy": averages["energy"],
        "dominant_bitstring_count": dominant,
        "dominant_valid_bitstring_count": dominant_valid,
        "unique_mode_valid": bool(dominant_valid) if dominant == 1 else None,
    }
    if bundle["penalty_mode"] == "independent":
        result["one_hot_probability"] = one_hot_probability
    return result
