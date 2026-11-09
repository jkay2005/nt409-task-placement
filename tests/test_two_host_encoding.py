"""Verify the reduced encoding against independent placements and old energies."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import json
import unittest
import numpy as np
from src.qubo import build_qubo, decode_qubo, energy_parts
from src.ising import build_ising, ising_energy
from src.qaoa_experiment import prepare_reference
from src.two_host_encoding import (build_two_host_qubo, expand_bits, compact_bits,
    decode_compact, compact_reference, certify_encoding)

ROOT = Path(__file__).resolve().parents[1]


def tiny_instance():
    return dict(schema_version=1, instance_id='two_host_test', objective='min_active_hosts',
        tasks=[dict(id='t0', cpu=1, ram=1)],
        hosts=[dict(id='a', cpu=1, ram=1), dict(id='b', cpu=1, ram=1)])


class TwoHostEncodingTests(unittest.TestCase):
    def test_all_tiny_bits_preserve_energy_and_decoder_without_repair(self):
        b = build_two_host_qubo(tiny_instance()); old = b['one_hot_bundle']
        op, offset = build_ising(b)
        for values in product((0, 1), repeat=b['qubo'].get_num_vars()):
            bits = np.asarray(values); expanded = expand_bits(b, bits)
            self.assertEqual(compact_bits(b, expanded).tolist(), list(values))
            self.assertEqual(decode_compact(b, bits), decode_qubo(old, expanded))
            self.assertEqual(b['qubo'].objective.evaluate(bits), energy_parts(old, expanded)['energy'])
            self.assertAlmostEqual(ising_energy(op, offset, bits), b['qubo'].objective.evaluate(bits))
        # Both hosts off is still invalid: the encoding must not repair y/capacity.
        self.assertFalse(decode_compact(b, np.zeros(b['qubo'].get_num_vars(), dtype=int))['feasible'])

    def test_uniform_reference_matches_full_tiny_enumeration(self):
        b = build_two_host_qubo(tiny_instance()); r = compact_reference(b)
        samples = [(b['qubo'].objective.evaluate(list(bits)), decode_compact(b, bits))
                   for bits in product((0, 1), repeat=b['qubo'].get_num_vars())]
        minimum = min(e for e, d in samples); total = len(samples)
        u = r['uniform_baseline']
        self.assertEqual(r['minimum_energy'], minimum)
        self.assertEqual(u['ground_state_probability'], sum(e == minimum for e, d in samples)/total)
        self.assertEqual(u['feasible_probability'], sum(d['feasible'] for e, d in samples)/total)
        self.assertEqual(u['mean_qubo_energy'], sum(e for e, d in samples)/total)

    def test_frozen_instances_keep_optima_and_have_their_own_uniform(self):
        for name, qubits, optimum in [('p1_choice',16,1),('p1_tight',14,2),('p0_reference',19,2),('p1_infeasible',16,None)]:
            with self.subTest(instance=name):
                instance=json.loads((ROOT/'data/instances'/f'{name}.json').read_text())
                b=build_two_host_qubo(instance); r=compact_reference(b)
                old=prepare_reference(b['one_hot_bundle'])
                self.assertEqual(b['qubo'].get_num_vars(),qubits)
                self.assertEqual(r['original_best_objective'],optimum)
                if optimum is not None:
                    self.assertEqual(r['minimum_energy'],old['minimum_energy'])
                    self.assertAlmostEqual(r['uniform_baseline']['optimal_placement_probability'],
                        16*old['uniform_baseline']['optimal_placement_probability'])
                certificate=certify_encoding(b)
                self.assertTrue(certificate['polynomial_identity'])
                self.assertEqual(certificate['checked_base_vectors'],64)

    def test_reject_wrong_host_count_and_non_onehot_reverse_mapping(self):
        instance=tiny_instance(); instance['hosts'].append(dict(id='c',cpu=1,ram=1))
        with self.assertRaises(ValueError):build_two_host_qubo(instance)
        b=build_two_host_qubo(tiny_instance())
        with self.assertRaises(ValueError):compact_bits(b,np.zeros(b['one_hot_bundle']['qubo'].get_num_vars()))
        with self.assertRaises(ValueError):expand_bits(b,[0,1])


if __name__=='__main__':unittest.main()
