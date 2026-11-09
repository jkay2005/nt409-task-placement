import numpy as np

RESOURCES = ("cpu", "ram")


def _arrays(instance):
    if instance["schema_version"] != 1:
        raise ValueError("Unsupported schema version.")

    if instance["objective"] != "min_active_hosts":
        raise ValueError("Unsupported objective.")

    for group in ("tasks", "hosts"):
        rows = instance[group]

        if not rows:
            raise ValueError(f"{group} must not be empty.")

        ids = [row["id"] for row in rows]

        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate IDs in {group}.")

        for row in rows:
            for resource in RESOURCES:
                value = row[resource]

                if type(value) is not int or value <= 0:
                    raise ValueError(
                        f"{group}: {resource} must be a positive integer."
                    )

    demand = np.array([
        [task[r] for r in RESOURCES]
        for task in instance["tasks"]
    ])

    capacity = np.array([
        [host[r] for r in RESOURCES]
        for host in instance["hosts"]
    ])

    return demand, capacity


def evaluate_model(instance, x, y):
    demand, capacity = _arrays(instance)
    n, m = len(demand), len(capacity)

    x, y = np.asarray(x), np.asarray(y)

    if x.shape != (n, m) or y.shape != (m,):
        raise ValueError("Incorrect x or y shape.")

    if not np.isin(x, [0, 1]).all() or not np.isin(y, [0, 1]).all():
        raise ValueError("x and y must be binary.")

    x, y = x.astype(int), y.astype(int)

    usage = x.T @ demand

    one_hot_ok = bool((x.sum(axis=1) == 1).all())
    capacity_ok = bool(
        (usage <= capacity * y[:, None]).all()
    )

    feasible = one_hot_ok and capacity_ok

    return {
        "feasible": feasible,
        "objective": int(y.sum()) if feasible else None,
        "one_hot_ok": one_hot_ok,
        "capacity_ok": capacity_ok,
        "x": x.tolist(),
        "y": y.tolist(),
        "usage": usage.tolist(),
    }


def evaluate_placement(instance, placement):
    n = len(instance["tasks"])
    m = len(instance["hosts"])

    p = np.asarray(placement)

    if p.shape != (n,) or p.dtype.kind not in "iu":
        raise ValueError(
            "placement must contain one integer host index per task."
        )

    if ((p < 0) | (p >= m)).any():
        raise ValueError("Host index out of range.")

    x = np.eye(m, dtype=int)[p]
    y = (x.sum(axis=0) > 0).astype(int)

    result = evaluate_model(instance, x, y)
    result["placement"] = p.tolist()

    return result