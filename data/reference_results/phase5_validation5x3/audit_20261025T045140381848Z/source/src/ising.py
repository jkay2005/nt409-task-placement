"""Phase 3: read a QUBO as an Ising Hamiltonian and decode QAOA samples."""

from numbers import Integral

import numpy as np

from .qubo import decode_qubo


def build_ising(bundle):
    """Return H and its constant offset, so E_qubo(bits) = <bits|H|bits> + offset."""
    operator, offset = bundle["qubo"].to_ising()
    assert operator.num_qubits == bundle["qubo"].get_num_vars()
    return operator, float(offset)


def scale_ising(operator, method="none"):
    """Change execution units only; raw QUBO coefficients remain unchanged.

    Identity coefficients contribute a global phase and do not set the scale.
    A zero/constant Hamiltonian uses scale 1 rather than dividing by zero.
    """
    if method not in ("none", "max_abs"):
        raise ValueError("hamiltonian_scaling must be 'none' or 'max_abs'.")
    coefficients = [abs(complex(c)) for label, c in operator.to_list() if set(label) != {"I"}]
    maximum = float(max(coefficients, default=0))
    if not np.isfinite(maximum):
        raise ValueError("Hamiltonian coefficients must be finite.")
    scale = maximum if method == "max_abs" and maximum > 0 else 1.0
    return operator / scale, {
        "method": method, "scale": scale,
        "raw_max_abs_coefficient": maximum,
        "execution_max_abs_coefficient": maximum / scale,
    }


def scaled_qaoa_point(point, reps, scale):
    """Map gamma_raw to gamma_execution=scale*gamma_raw, preserving beta.

    Qiskit parameter order is beta[0..p-1], gamma[0..p-1]. Use 1/scale
    for the inverse mapping. No optimizer bounds or steps are transformed.
    """
    point = np.asarray(point, dtype=float)
    if (type(reps) is not int or reps < 1 or point.shape != (2 * reps,)
            or not np.isfinite(point).all() or isinstance(scale, (bool, np.bool_))
            or not np.isfinite(scale) or scale <= 0):
        raise ValueError("Expected 2*p finite angles and a positive finite scale.")
    result = point.copy()
    result[reps:] *= scale
    if not np.isfinite(result).all():
        raise ValueError("Scaled angles must remain finite.")
    return result.tolist()


def integer_to_bits(value, num_bits):
    """Qiskit qubit k corresponds to QUBO variable k (least-significant bit)."""
    if isinstance(value, str):
        value = int(value.replace(" ", ""), 2)
    if not isinstance(value, Integral) or not 0 <= value < 2**num_bits:
        raise ValueError("Sample index is outside the bit register.")
    return np.array([(int(value) >> k) & 1 for k in range(num_bits)], dtype=int)


def ising_energy(operator, offset, bits):
    """Evaluate diagonal I/Z Hamiltonian directly; no 2**n statevector allocation."""
    bits = np.asarray(bits)
    if bits.shape != (operator.num_qubits,) or not np.isin(bits, [0, 1]).all():
        raise ValueError("Incorrect binary vector size or values.")
    total = complex(offset)
    for label, coefficient in operator.to_list():
        if any(letter not in "IZ" for letter in label):
            raise ValueError("The cost Hamiltonian should contain I and Z only.")
        eigenvalue = 1
        for qubit_index, bit in enumerate(bits):
            if label[-1 - qubit_index] == "Z" and bit:
                eigenvalue *= -1
        total += coefficient * eigenvalue
    if abs(total.imag) > 1e-8:
        raise ValueError("The cost energy should be real.")
    return float(total.real)


def decode_samples(bundle, eigenstate, operator, offset):
    """Preserve all observed samples; validate x,y and full QUBO energy separately."""
    num_bits = bundle["qubo"].get_num_vars()
    samples = []
    for key, probability in eigenstate.items():
        bits = integer_to_bits(key, num_bits)
        qubo_energy = float(bundle["qubo"].objective.evaluate(bits))
        ising_value = ising_energy(operator, offset, bits)
        if not np.isclose(qubo_energy, ising_value, rtol=0, atol=1e-7):
            raise AssertionError("Bit order or Ising offset is inconsistent.")
        samples.append({
            "bits": bits.tolist(),
            "probability": float(probability),
            "energy": qubo_energy,
            "decoded": decode_qubo(bundle, bits),
        })
    return sorted(samples, key=lambda sample: sample["probability"], reverse=True)
