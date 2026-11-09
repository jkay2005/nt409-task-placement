import itertools
import json
import unittest
from pathlib import Path

from src.placement import evaluate_placement
from src.classical_baselines import solve_heuristic, solve_milp, binary_values, solver_status

ROOT = Path(__file__).resolve().parents[1]


def fixture(tasks, hosts):
    return {'schema_version': 1, 'objective': 'min_active_hosts',
            'tasks': [dict(id=f't{i}', cpu=c, ram=r) for i, (c, r) in enumerate(tasks)],
            'hosts': [dict(id=f'h{i}', cpu=c, ram=r) for i, (c, r) in enumerate(hosts)]}


class ClassicalTests(unittest.TestCase):
    def test_bfd_differs_from_first_fit(self):
        inst = fixture([(2, 2), (4, 4)], [(6, 6), (4, 4)])
        self.assertEqual(solve_heuristic(inst, 'FirstFit')['placement'], [0, 0])
        self.assertEqual(solve_heuristic(inst, 'BFD')['placement'], [0, 1])

    def test_bfd_restores_source_order_and_ff_failure_is_not_infeasibility(self):
        inst = fixture([(2, 2), (4, 4), (4, 4)], [(4, 4), (6, 6)])
        ff = solve_heuristic(inst, 'FirstFit')
        self.assertEqual(ff['status'], 'no_placement_found')
        self.assertIsNone(ff['objective'])
        self.assertFalse(ff['solver_certified_infeasible'])
        self.assertEqual(solve_heuristic(inst, 'BFD')['placement'], [1, 0, 1])
        self.assertEqual(solve_milp(inst)['objective'], 2)

    def test_both_resources_and_active_host_priority(self):
        inst = fixture([(2, 4), (1, 1)], [(8, 8), (3, 3)])
        for name in ('FirstFit', 'BFD'):
            self.assertEqual(solve_heuristic(inst, name)['placement'], [0, 0])

    def test_equal_scores_keep_host_order(self):
        inst = fixture([(2, 1), (1, 2)], [(3, 3), (3, 3)])
        for name in ('FirstFit', 'BFD'):
            self.assertEqual(solve_heuristic(inst, name)['placement'], [0, 0])

    def test_binary_tolerance_does_not_repair_fractional_solution(self):
        self.assertEqual(binary_values([1e-8, 1-1e-8]), [0, 1])
        for values in ([0.5], [float('nan')], [1.1]):
            with self.assertRaises(ValueError):
                binary_values(values)

    def test_solver_status_distinguishes_limits_from_proofs(self):
        from ortools.linear_solver import pywraplp
        self.assertEqual(solver_status(pywraplp.Solver.FEASIBLE), 'feasible_not_proven')
        self.assertEqual(solver_status(pywraplp.Solver.NOT_SOLVED), 'no_incumbent')
        self.assertEqual(solver_status(pywraplp.Solver.INFEASIBLE), 'infeasible')

    def test_frozen_instances_milp_matches_independent_enumeration(self):
        import csv
        registry = ROOT / 'handoff/nt409_branch_a_handoff_v1/tables/instance_registry.csv'
        for row in csv.DictReader(registry.read_text(encoding='utf-8-sig').splitlines()):
            if row['role'] == 'development':
                continue
            with self.subTest(instance=row['instance_id']):
                inst = json.loads((ROOT / row['input_path']).read_text(encoding='utf-8'))
                objectives = [r['objective'] for p in itertools.product(range(len(inst['hosts'])), repeat=len(inst['tasks']))
                              if (r := evaluate_placement(inst, p))['feasible']]
                optimum = min(objectives, default=None)
                report = solve_milp(inst)
                self.assertEqual(report['objective'], optimum)
                self.assertEqual(report['solver_certified_infeasible'], optimum is None)
                self.assertEqual(report['solver_certified_optimal'], optimum is not None)
                for name in ('FirstFit', 'BFD'):
                    heuristic = solve_heuristic(inst, name)
                    if heuristic['found_valid']:
                        self.assertTrue(evaluate_placement(inst, heuristic['placement'])['feasible'])
                        self.assertGreaterEqual(heuristic['objective'], optimum)

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            solve_heuristic(fixture([(0, 1)], [(2, 2)]), 'FirstFit')
        with self.assertRaises(ValueError):
            solve_heuristic(fixture([(1, 1)], [(2, 2)]), 'unknown')


if __name__ == '__main__':
    unittest.main()
