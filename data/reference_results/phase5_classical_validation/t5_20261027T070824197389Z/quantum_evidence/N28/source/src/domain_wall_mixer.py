"""State preparation and ordered domain-wall mixer for the frozen 5x3 study.

Only assignment-domain validity is preserved. Capacity and slack are still
handled by the unchanged QUBO. The mixer is a product, not exp[-i beta(A+B)].
"""
import hashlib
import json
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

INPUT_HASH = 'e6d3ac93ed2d5a831f5d7393750e9a1995b46fbe20d077058a629c7797996278'
VARIANTS = ('standard_x', 'valid_x', 'valid_dw')


def validate_fixed_instance(instance):
    canonical = json.dumps(instance, sort_keys=True, ensure_ascii=False,
                           separators=(',', ':'), allow_nan=False).encode()
    if (len(instance['tasks']) != 5 or len(instance['hosts']) != 3
            or hashlib.sha256(canonical).hexdigest() != INPUT_HASH):
        raise ValueError('Expected the exact frozen a3_dev_n5 input: 5 tasks, 3 hosts.')


def initial_state(valid=True):
    """Uniform legal assignment codes; H on the same 15 auxiliary bits as control."""
    circuit = QuantumCircuit(25, name='initial_domain' if valid else 'initial_plus')
    if valid:
        for u in range(0,10,2):
            circuit.ry(2*np.arccos(1/np.sqrt(3)), u)
            circuit.cry(np.pi/2, u, u+1)
        circuit.h(range(10,25))
    else:
        circuit.h(range(25))
    return circuit


def mix_pair(circuit, u, v, beta):
    """A: flip u if v=0; then B: flip v if u=1. Rx(2 beta)=exp(-i beta X)."""
    circuit.x(v)
    circuit.crx(2*beta, v, u)
    circuit.x(v)
    circuit.crx(2*beta, u, v)


def domain_mixer():
    beta = Parameter('beta_domain')
    circuit = QuantumCircuit(25, name='domain_AB')
    for u in range(0,10,2):
        mix_pair(circuit, u, u+1, beta)
    circuit.rx(2*beta, range(10,25))
    return circuit


def circuit_components(variant):
    if variant not in VARIANTS:
        raise ValueError(f'Unknown variant: {variant}')
    if variant == 'standard_x':
        return None, None
    return initial_state(), domain_mixer() if variant == 'valid_dw' else None


def domain_support():
    """Mask for the 10 least-significant assignment bits, independent of y/slack."""
    indices = np.arange(1024, dtype=np.uint16)
    mask = np.ones(1024, dtype=bool)
    for u in range(0,10,2):
        mask &= ((indices >> u) & 1) >= ((indices >> (u+1)) & 1)
    return mask


def domain_probability(probabilities):
    probabilities = np.asarray(probabilities)
    if probabilities.shape != (2**25,):
        raise ValueError('Expected the full 25-qubit probability vector.')
    marginal = probabilities.reshape(-1,1024).sum(axis=0)
    return float(marginal[domain_support()].sum())


def make_evaluator(bundle, reps, variant, threads=4, min_available_gib=4.):
    from .shot_noise_diagnostic import ThreeHostEvaluator
    validate_fixed_instance(bundle['instance'])
    if bundle['qubo'].get_num_vars() != 25 or bundle.get('encoding') != 'three_host_domain_wall_v2':
        raise ValueError('Expected the frozen 25-qubit domain-wall model.')
    state, mixer = circuit_components(variant)
    return ThreeHostEvaluator(bundle, reps, threads=threads,
        min_available_gib=min_available_gib, initial_state=state, mixer_operator=mixer)
