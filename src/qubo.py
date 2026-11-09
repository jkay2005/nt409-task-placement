"""Phase 2: explicit binary slack + squared equality penalties.

The exact reference routine is for tiny fixtures, not a benchmark solver.
Bit vectors always follow `bundle['qubo'].variables` order.
"""

from itertools import product

import numpy as np
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import LinearEqualityToPenalty

from .placement import RESOURCES, _arrays, evaluate_model


def slack_weights(capacity):
    """Binary weights whose subset sums cover exactly 0..capacity.

    Example: capacity=5 -> [1, 2, 2], capacity=8 -> [1, 2, 4, 1].
    Different bit strings may encode the same slack value.
    """
    if type(capacity) is not int or capacity < 1:
        raise ValueError("capacity must be a positive integer.")
    size = capacity.bit_length()
    return [2**k for k in range(size - 1)] + [
        capacity - (2 ** (size - 1) - 1)
    ]


def build_qubo(instance, penalty=None, *, assignment_penalty=None, capacity_penalty=None):
    """Build binary equalities with either a shared P or two explicit weights.

    Both explicit weights are required; mixing them with `penalty` is ambiguous.
    Equal weights reproduce the original converter coefficients exactly.
    """
    demand, capacity = _arrays(instance)
    n, m = len(demand), len(capacity)
    independent = assignment_penalty is not None or capacity_penalty is not None
    if independent:
        if penalty is not None or assignment_penalty is None or capacity_penalty is None:
            raise ValueError("Provide both explicit weights, without a shared penalty.")
    else:
        assignment_penalty = capacity_penalty = m + 1 if penalty is None else penalty
    penalties = {}
    for name, value in (("assignment", assignment_penalty), ("capacity", capacity_penalty)):
        if isinstance(value, (bool, np.bool_)):
            raise ValueError(f"{name} penalty must be positive and finite.")
        value = float(value)
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} penalty must be positive and finite.")
        penalties[name] = value
    penalty = penalties["assignment"] if penalties["assignment"] == penalties["capacity"] else None

    model = QuadraticProgram(name=instance["instance_id"])
    for i in range(n):
        for h in range(m):
            model.binary_var(name=f"x_{i}_{h}")
    for h in range(m):
        model.binary_var(name=f"y_{h}")

    base_count = n * m + m
    slack_groups = []
    for h in range(m):
        for r, resource in enumerate(RESOURCES):
            weights = slack_weights(int(capacity[h, r]))
            names = [f"s_{h}_{resource}_{k}" for k in range(len(weights))]
            indices = []
            for name in names:
                indices.append(model.get_num_vars())
                model.binary_var(name=name)
            slack_groups.append({
                "host": h,
                "resource": resource,
                "resource_index": r,
                "capacity": int(capacity[h, r]),
                "weights": weights,
                "names": names,
                "indices": indices,
            })

    model.minimize(linear={f"y_{h}": 1 for h in range(m)})
    for i in range(n):
        model.linear_constraint(
            linear={f"x_{i}_{h}": 1 for h in range(m)},
            sense="==", rhs=1, name=f"assign_{i}",
        )
    for group in slack_groups:
        h, r = group["host"], group["resource_index"]
        linear = {f"x_{i}_{h}": int(demand[i, r]) for i in range(n)}
        linear[f"y_{h}"] = -group["capacity"]
        linear.update(dict(zip(group["names"], group["weights"])))
        model.linear_constraint(
            linear=linear, sense="==", rhs=0,
            name=f"capacity_{h}_{group['resource']}",
        )

    # Qiskit Optimization 0.7 uses a single multiplier for all equalities:
    # https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.converters.LinearEqualityToPenalty.html
    converter = LinearEqualityToPenalty(penalty=penalties["capacity"])
    qubo = converter.convert(model)
    delta = penalties["assignment"] - penalties["capacity"]
    if delta:
        constant = qubo.objective.constant
        linear = qubo.objective.linear.to_array()
        quadratic = qubo.objective.quadratic.to_array()
        for constraint in model.linear_constraints[:n]:
            row = constraint.linear.to_array()
            constant += delta * constraint.rhs**2
            linear -= 2 * delta * constraint.rhs * row
            quadratic += delta * np.outer(row, row)
        # Arrays are a documented objective input; off-diagonal terms are combined.
        # https://qiskit-community.github.io/qiskit-optimization/stubs/qiskit_optimization.QuadraticProgram.html#qiskit_optimization.QuadraticProgram.minimize
        qubo.minimize(constant=constant, linear=linear, quadratic=quadratic)
    assert [v.name for v in model.variables] == [v.name for v in qubo.variables]
    assert qubo.get_num_vars() == qubo.get_num_binary_vars()
    assert qubo.get_num_linear_constraints() == 0
    assert qubo.get_num_quadratic_constraints() == 0

    return {
        "instance": instance,
        "model": model,
        "qubo": qubo,
        "penalty": penalty,
        "penalties": penalties,
        "penalty_mode": "independent" if independent else "common",
        "model_version": "weighted_equalities_v2",
        "n": n,
        "m": m,
        "base_count": base_count,
        "slack_groups": slack_groups,
    }


def _binary_vector(values, size):
    vector = np.asarray(values)
    if vector.shape != (size,) or not np.isin(vector, [0, 1]).all():
        raise ValueError(f"Expected a binary vector of length {size}.")
    return vector.astype(int)


def decode_qubo(bundle, bits):
    """Check the original placement constraints, including the supplied y."""
    bits = _binary_vector(bits, bundle["qubo"].get_num_vars())
    n, m = bundle["n"], bundle["m"]
    x = bits[:n * m].reshape(n, m)
    y = bits[n * m:bundle["base_count"]]
    return evaluate_model(bundle["instance"], x, y)


def energy_parts(bundle, bits):
    """Independent evaluation of the unexpanded squared-penalty formula."""
    bits = _binary_vector(bits, bundle["qubo"].get_num_vars())
    result = decode_qubo(bundle, bits)
    x = np.asarray(result["x"])
    assignment_error = int(np.square(x.sum(axis=1) - 1).sum())
    capacity_error = 0
    for group in bundle["slack_groups"]:
        h, r = group["host"], group["resource_index"]
        slack = sum(int(bits[j]) * w for j, w in zip(
            group["indices"], group["weights"]
        ))
        residual = (
            result["usage"][h][r] + slack
            - group["capacity"] * result["y"][h]
        )
        capacity_error += residual**2
    active_hosts = sum(result["y"])
    return {
        "active_hosts": active_hosts,
        "assignment_error": assignment_error,
        "capacity_error": capacity_error,
        "energy": active_hosts + bundle["penalties"]["assignment"] * assignment_error
        + bundle["penalties"]["capacity"] * capacity_error,
    }


def complete_with_best_slack(bundle, base_bits):
    """Minimize energy over slack bits for one fixed (x,y) vector.

    With nonnegative demands, optimal slack is max(0, C*y - usage).
    It always lies in 0..C. This statement also holds for invalid x,y.
    """
    base = _binary_vector(base_bits, bundle["base_count"])
    bits = np.zeros(bundle["qubo"].get_num_vars(), dtype=int)
    bits[:bundle["base_count"]] = base
    result = decode_qubo(bundle, bits)
    for group in bundle["slack_groups"]:
        h, r = group["host"], group["resource_index"]
        remaining = max(
            0, group["capacity"] * result["y"][h] - result["usage"][h][r]
        )
        for j, weight in reversed(list(zip(group["indices"], group["weights"]))):
            if weight <= remaining:
                bits[j] = 1
                remaining -= weight
        assert remaining == 0
    return bits


def exact_qubo_reference(bundle, max_base_variables=16):
    """Exact global minimum: enumerate (x,y), minimize slack analytically.

    Includes zero/multiple assignments and arbitrary host activation.
    Counts minimizers by original (x,y), not by slack encodings.
    """
    size = bundle["base_count"]
    if size > max_base_variables:
        raise ValueError("This reference routine is only for tiny instances.")
    best = float("inf")
    minimizers = []
    for base in product((0, 1), repeat=size):
        bits = complete_with_best_slack(bundle, base)
        energy = float(bundle["qubo"].objective.evaluate(bits))
        parts = energy_parts(bundle, bits)
        assert np.isclose(energy, parts["energy"], rtol=0, atol=1e-8)
        item = {
            "bits": bits.tolist(),
            "energy": energy,
            "decoded": decode_qubo(bundle, bits),
        }
        if energy < best - 1e-8:
            best, minimizers = energy, [item]
        elif abs(energy - best) <= 1e-8:
            minimizers.append(item)
    return {
        "minimum_energy": best,
        "checked_base_vectors": 2**size,
        "minimizers": minimizers,
    }
