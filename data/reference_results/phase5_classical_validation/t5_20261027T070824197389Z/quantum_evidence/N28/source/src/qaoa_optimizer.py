"""Small shared controls for sampled and exact QAOA experiments."""

import numpy as np
from scipy.optimize import minimize
from qiskit_optimization.optimizers import OptimizerResult


def sampling_seeds(config):
    """Keep the final measurement reproducible and separate from training."""
    seed = config.get("seed")
    final_seed = config.get("evaluation_seed", (seed + 100000) % 2**32
                            if type(seed) is int else None)
    for value in (seed, final_seed):
        if type(value) is not int or not 0 <= value < 2**32:
            raise ValueError("Sampling seeds must be integers in [0, 2**32).")
    if final_seed == seed:
        raise ValueError("evaluation_seed must differ from the optimization seed.")
    final_shots = config.get("evaluation_shots", config.get("shots"))
    if type(final_shots) is not int or final_shots < 1:
        raise ValueError("evaluation_shots must be a positive integer.")
    return {"optimization_seed": seed, "evaluation_seed": final_seed,
            "evaluation_shots": final_shots}


class RecordingCOBYLA:
    """The Qiskit callable interface, with SciPy's actual termination result.

    As with Qiskit's COBYLA wrapper, angle bounds are ignored. QAOA angles
    are periodic; changing this behavior would change the historical control.
    maxiter is a cap on function evaluations, not on outer iterations.
    """

    def __init__(self, maxiter, rhobeg=1., tol=1e-4):
        if type(maxiter) is not int or maxiter < 1:
            raise ValueError("maxiter must be a positive evaluation cap.")
        for value in (rhobeg, tol):
            if isinstance(value, (bool, np.bool_)) or not np.isfinite(value) or value <= 0:
                raise ValueError("COBYLA radius and tolerance must be positive and finite.")
        self.options = {"maxiter": maxiter, "rhobeg": float(rhobeg), "tol": float(tol)}
        self.stop = None

    def __call__(self, fun, x0, jac=None, bounds=None):
        # scipy's exceptions (including the experiment's time guard) propagate.
        result = minimize(fun, x0, method="COBYLA", options=self.options)
        self.stop = {"status": int(result.status), "success": bool(result.success),
                     "message": str(result.message), "nfev": int(result.nfev)}
        output = OptimizerResult()
        output.x, output.fun = np.asarray(result.x), float(result.fun)
        output.nfev = int(result.nfev)
        if "nit" in result:
            output.nit = int(result.nit)
        return output
