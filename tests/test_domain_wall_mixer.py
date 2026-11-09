"""Local 4x4 gate proofs are blocks of the fixed 25-qubit problem, not new instances."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy.linalg import expm
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector

from src.domain_wall_mixer import (validate_fixed_instance, initial_state,
    mix_pair, domain_mixer, domain_support, circuit_components)


class DomainWallMixerTests(unittest.TestCase):
    def test_scope_rejects_changed_size_values_and_order(self):
        root = Path(__file__).resolve().parents[1]
        instance = json.loads((root/'data/benchmarks/nt409_shot_noise_v2/instance.json').read_text())
        validate_fixed_instance(instance)
        for mutation in ('task', 'host', 'demand', 'order'):
            item = copy.deepcopy(instance)
            if mutation == 'task': item['tasks'].pop()
            elif mutation == 'host': item['hosts'].pop()
            elif mutation == 'demand': item['tasks'][0]['ram'] += 1
            else: item['tasks'].reverse()
            with self.assertRaises(ValueError): validate_fixed_instance(item)

    def test_initial_pair_uniform_over_legal_codes_auxiliaries_stay_h(self):
        circuit = initial_state(True)
        self.assertEqual(circuit.num_qubits, 25)
        for i in range(5):
            block = QuantumCircuit(2)
            for item in circuit.data:
                indices = [circuit.find_bit(q).index for q in item.qubits]
                if indices and set(indices) <= {2*i, 2*i+1}:
                    block.append(item.operation, [j-2*i for j in indices])
            np.testing.assert_allclose(Statevector.from_instruction(block).data,
                                       [1/np.sqrt(3), 1/np.sqrt(3), 0, 1/np.sqrt(3)], atol=1e-14)
        auxiliary_h = [circuit.find_bit(op.qubits[0]).index for op in circuit.data
                       if op.operation.name == 'h']
        self.assertEqual(auxiliary_h, list(range(10, 25)))
        self.assertEqual(initial_state(False).count_ops(), {'h': 25})

    def test_pair_matches_ordered_exponentials_and_never_leaks(self):
        # Qiskit |v u> ordering: legal labels (u,v)=(00,10,11) have indices 0,1,3.
        a = np.zeros((4,4)); a[0,1] = a[1,0] = 1
        b = np.zeros((4,4)); b[1,3] = b[3,1] = 1
        for beta in [0., .37, -.81, np.pi/2, np.pi]:
            qc = QuantumCircuit(2); mix_pair(qc, 0, 1, beta)
            unitary = Operator(qc).data
            np.testing.assert_allclose(unitary, expm(-1j*beta*b) @ expm(-1j*beta*a), atol=1e-13)
            np.testing.assert_allclose(unitary.conj().T @ unitary, np.eye(4), atol=1e-13)
            np.testing.assert_allclose(unitary[2, [0,1,3]], 0., atol=1e-14)
            np.testing.assert_allclose(unitary[[0,1,3], 2], 0., atol=1e-14)
        # A and B do not commute: the chosen product must not be mislabeled exp[-i beta(A+B)].
        self.assertGreater(np.linalg.norm(a@b-b@a), 1.)

    def test_legal_transition_graph_is_connected(self):
        qc = QuantumCircuit(2); mix_pair(qc, 0, 1, .37)
        u = Operator(qc).data; reached={0}
        for _ in range(3):
            reached |= {j for i in reached for j in [0,1,3] if abs(u[j,i])+abs(u[i,j])>1e-10}
        self.assertEqual(reached, {0,1,3})

    def test_full_mixer_retains_auxiliary_x_and_single_shared_parameter(self):
        circuit = domain_mixer()
        self.assertEqual(circuit.num_qubits, 25)
        self.assertEqual(len(circuit.parameters), 1)
        aux = [circuit.find_bit(item.qubits[0]).index for item in circuit.data
               if item.operation.name == 'rx']
        self.assertEqual(aux, list(range(10,25)))
        self.assertEqual(circuit.count_ops()['crx'], 10)

    def test_domain_support_has_exactly_three_to_the_fifth_codes(self):
        mask = domain_support()
        self.assertEqual(mask.shape, (1024,))
        self.assertEqual(int(mask.sum()), 243)
        for k, valid in enumerate(mask):
            self.assertEqual(bool(valid), all(((k>>(2*i))&1)>=((k>>(2*i+1))&1) for i in range(5)))

    def test_variants_change_only_the_intended_components(self):
        a,b = circuit_components('standard_x'); self.assertIsNone(a); self.assertIsNone(b)
        a,b = circuit_components('valid_x'); self.assertEqual(a.num_qubits,25); self.assertIsNone(b)
        a,b = circuit_components('valid_dw'); self.assertEqual(a.num_qubits,25); self.assertEqual(b.num_qubits,25)
        with self.assertRaises(ValueError): circuit_components('typo')

    def test_optional_rss_does_not_discard_a_valid_quantum_result(self):
        import psutil
        from src.domain_wall_probe import optional_rss_mib
        with patch('src.domain_wall_probe.psutil.Process', side_effect=psutil.NoSuchProcess(2)):
            self.assertIsNone(optional_rss_mib())


if __name__ == '__main__': unittest.main()
