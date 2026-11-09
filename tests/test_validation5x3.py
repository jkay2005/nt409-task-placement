import copy
import json
from pathlib import Path
import unittest

from src.validation5x3 import assignment_audit, select_cases, load_dataset, run_audit

ROOT = Path(__file__).resolve().parents[1]


class Validation5x3Tests(unittest.TestCase):
    def test_original_case_has_redundant_cpu_and_exact_known_truth(self):
        instance = json.loads((ROOT/'data/benchmarks/nt409_shot_noise_v2/instance.json').read_text())
        a = assignment_audit(instance)
        self.assertEqual(a['feasible_assignments'], 90)
        self.assertEqual(a['optimal_assignments'], 8)
        self.assertEqual(a['cpu_pass_ram_fail'], 80)
        self.assertEqual(a['ram_pass_cpu_fail'], 0)
        for key in ('tasks', 'hosts'):
            bad = copy.deepcopy(instance); bad[key].pop()
            with self.assertRaises(ValueError): assignment_audit(bad)

    def test_frozen_selection_reproduces_and_resources_are_independent(self):
        data = load_dataset(ROOT)
        cases, stats = select_cases(data['excluded_signatures'])
        self.assertEqual(cases, data['validation_instances'])
        self.assertEqual(stats, data['pool_statistics'])
        for instance in cases:
            a = assignment_audit(instance)
            self.assertGreater(a['cpu_pass_ram_fail'], 0)
            self.assertGreater(a['ram_pass_cpu_fail'], 0)
            self.assertGreater(a['feasible_assignments'], 0)
        self.assertEqual([assignment_audit(i)['optimum'] for i in cases], [2,3,3])

    def test_audit_agrees_with_independent_oracles_and_writes_fresh_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'audit'
            r = run_audit(ROOT, out, progress=False)
            self.assertEqual(r['status'], 'PASS')
            self.assertEqual(len(r['cases']), 4)
            self.assertEqual(r['training_evaluations'], 0)
            self.assertTrue(all(c['qubits']==25 for c in r['cases']))
            self.assertTrue(all(c['max_ising_error']<1e-8 for c in r['cases']))
            with self.assertRaises(FileExistsError): run_audit(ROOT, out, progress=False)


if __name__ == '__main__': unittest.main()
