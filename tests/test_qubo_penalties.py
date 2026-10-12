"""Weighted penalties checked against explicit constraints, including all tiny bits."""

from itertools import product
import json
from pathlib import Path
import unittest

import numpy as np
from qiskit_optimization.converters import LinearEqualityToPenalty

from src.qubo import build_qubo, decode_qubo, energy_parts, exact_qubo_reference
from src.ising import build_ising


ROOT = Path(__file__).resolve().parents[1]
TINY = {
    "schema_version": 1, "instance_id": "weighted_tiny",
    "objective": "min_active_hosts",
    "tasks": [{"id": "T1", "cpu": 1, "ram": 1}],
    "hosts": [{"id": "H0", "cpu": 2, "ram": 2}],
}


class WeightedQuboTests(unittest.TestCase):
    def test_equal_weights_preserve_common_converter_coefficients(self):
        for name in ("p0_reference", "p1_choice", "p1_tight", "p1_infeasible"):
            instance = json.loads((ROOT / f"data/instances/{name}.json").read_text())
            for penalty in (1, 3, 8):
                old = build_qubo(instance, penalty=penalty)
                new = build_qubo(instance, assignment_penalty=penalty,
                                 capacity_penalty=penalty)
                expected = LinearEqualityToPenalty(penalty).convert(old["model"])
                self.assertEqual([v.name for v in old["qubo"].variables],
                                 [v.name for v in new["qubo"].variables])
                self.assertEqual(expected.objective.constant, new["qubo"].objective.constant)
                np.testing.assert_array_equal(expected.objective.linear.to_array(),
                                              new["qubo"].objective.linear.to_array())
                np.testing.assert_array_equal(expected.objective.quadratic.to_array(),
                                              new["qubo"].objective.quadratic.to_array())

    def test_all_tiny_bits_match_weighted_formula_and_ising(self):
        for a, c in ((12, 3), (3, 12), (0.5, 2.5)):
            bundle = build_qubo(TINY, assignment_penalty=a, capacity_penalty=c)
            operator, offset = build_ising(bundle)
            for vector in product((0, 1), repeat=bundle["qubo"].get_num_vars()):
                bits = np.asarray(vector)
                # Directly evaluate the original equality constraints, not energy_parts.
                expected = int(bits[1])
                for constraint in bundle["model"].linear_constraints:
                    weight = a if constraint.name.startswith("assign_") else c
                    expected += weight * (constraint.linear.evaluate(bits) - constraint.rhs)**2
                self.assertAlmostEqual(expected, bundle["qubo"].objective.evaluate(bits))
                self.assertAlmostEqual(expected, energy_parts(bundle, bits)["energy"])
                parity = operator.paulis.z.astype(int) @ bits % 2
                actual = np.dot(np.real(operator.coeffs), (-1.)**parity) + offset
                self.assertAlmostEqual(expected, actual)
            truth = exact_qubo_reference(bundle)
            brute = min(bundle["qubo"].objective.evaluate(np.asarray(bits)) for bits in
                        product((0, 1), repeat=bundle["qubo"].get_num_vars()))
            self.assertAlmostEqual(truth["minimum_energy"], brute)

    def test_strong_weights_keep_fixture_minima_feasible(self):
        for name, hosts in (("p0_reference", 2), ("p1_choice", 1), ("p1_tight", 2)):
            instance = json.loads((ROOT / f"data/instances/{name}.json").read_text())
            for a, c in ((3, 3), (12, 3), (30, 3), (3, 6), (3, 12)):
                truth = exact_qubo_reference(build_qubo(
                    instance, assignment_penalty=a, capacity_penalty=c))
                self.assertEqual(truth["minimum_energy"], hosts)
                self.assertTrue(all(item["decoded"]["feasible"] for item in truth["minimizers"]))

    def test_rejects_ambiguous_partial_or_invalid_weights(self):
        for kwargs in ({"assignment_penalty": 3}, {"capacity_penalty": 3},
                       {"penalty": 3, "assignment_penalty": 3, "capacity_penalty": 3}):
            with self.assertRaises(ValueError):
                build_qubo(TINY, **kwargs)
        for value in (0, -1, float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                build_qubo(TINY, assignment_penalty=value, capacity_penalty=3)


if __name__ == "__main__":
    unittest.main()
