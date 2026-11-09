"""Independent checks for the paired ideal/shot QAOA diagnostic."""
import json
from pathlib import Path
import unittest

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import Statevector

from src.three_host_encoding import build_three_host_qubo, decode_three_host, energy_formula, three_host_reference
from src.shot_noise_diagnostic import ThreeHostEvaluator, three_host_diagonal, train, calibrate

ROOT = Path(__file__).resolve().parents[1]
TINY = dict(schema_version=1, instance_id='noise_unit', objective='min_active_hosts',
            tasks=[dict(id='T0', cpu=1, ram=1)],
            hosts=[dict(id='H0', cpu=1, ram=1), dict(id='H1', cpu=1, ram=1), dict(id='H2', cpu=1, ram=1)])


class NoiseOracleTests(unittest.TestCase):
    def test_all_tiny_bits_match_original_qubo_and_decoder(self):
        bundle = build_three_host_qubo(TINY)
        data = three_host_diagonal(bundle, chunk_size=127)
        for k, energy in enumerate(data['energies']):
            bits = [(k >> j) & 1 for j in range(bundle['qubo'].get_num_vars())]
            decoded = decode_three_host(bundle, bits)
            self.assertAlmostEqual(energy, bundle['qubo'].objective.evaluate(bits))
            self.assertAlmostEqual(energy, energy_formula(bundle, bits))
            self.assertEqual(bool(data['feasible'][k]), decoded['feasible'])
        self.assertEqual(data['optimum'], 1)

    def test_exact_agrees_with_independent_qiskit_statevector(self):
        evaluator = ThreeHostEvaluator(build_three_host_qubo(TINY), reps=2, threads=1)
        point = [.23, -.11, .7, 1.2]
        circuit = QAOAAnsatz(evaluator.operator, reps=2).assign_parameters(point)
        probabilities = Statevector.from_instruction(circuit.decompose(reps=5)).probabilities()
        expected = probabilities @ evaluator.diagonal['energies']
        self.assertAlmostEqual(evaluator.exact(point)['mean_energy'], expected, places=9)

    def test_sampled_counts_reproduce_energy_and_approach_exact(self):
        evaluator = ThreeHostEvaluator(build_three_host_qubo(TINY), reps=1, threads=1)
        point = [.3, 1.]
        counts = evaluator.sample(point, shots=65536, seed=91)
        stats = evaluator.score_counts(counts)
        exact = evaluator.exact(point)
        self.assertEqual(sum(counts.values()), 65536)
        self.assertLess(abs(stats['mean_energy'] - exact['mean_energy']),
                        6 * exact['energy_std'] / np.sqrt(65536))
        self.assertEqual(counts, evaluator.sample(point, shots=65536, seed=91))

    def test_rejects_bad_angles_counts_and_size(self):
        bundle = build_three_host_qubo(TINY)
        with self.assertRaises(ValueError): three_host_diagonal(bundle, max_qubits=1)
        e = ThreeHostEvaluator(bundle, reps=1, threads=1)
        for point in [[.3], [float('nan'), 1.]]:
            with self.assertRaises(ValueError): e.exact(point)
        for counts in [{}, {'1': 0}, {'10x': 1}, {'1' * (e.size + 1): 1}]:
            with self.assertRaises(ValueError): e.score_counts(counts)

    def test_frozen_reference_has_five_tasks_three_hosts_and_real_objective_choice(self):
        from src.shot_noise_campaign import PROTOCOL, load_json
        from src.qaoa_experiment import qubo_fingerprint
        p = load_json(ROOT/PROTOCOL)
        self.assertEqual(len(p['instances']), 1)
        item = p['instances'][0]
        instance = load_json(ROOT/item['path'])
        self.assertEqual((len(instance['tasks']),len(instance['hosts'])), (5,3))
        bundle = build_three_host_qubo(instance)
        self.assertEqual(bundle['qubo'].get_num_vars(), 25)
        self.assertEqual(qubo_fingerprint(bundle), item['qubo_sha256'])
        truth = three_host_reference(bundle)
        self.assertEqual(truth['original_best_objective'], 2)
        self.assertGreater(truth['placement_histogram']['2'], 0)
        self.assertGreater(truth['placement_histogram']['3'], 0)

    def test_training_runs_both_modes_with_independent_final_counts(self):
        e = ThreeHostEvaluator(build_three_host_qubo(TINY), reps=1, threads=1)
        config = dict(initial_point=[.3, 1.], maxiter=8, shots=64, final_shots=128,
            seed=300, final_seed=40000000, rhobeg=1., tol=1e-4,
            max_seconds=60., min_available_gib=.001)
        for mode in ['exact', 'shots']:
            report = train(e, config, mode, progress=False)
            self.assertEqual(report['status'], 'completed', report.get('error'))
            self.assertLessEqual(report['nfev'], config['maxiter'])
            self.assertEqual(report['history'][0]['point'], config['initial_point'])
            self.assertEqual(sum(report['final_counts'].values()), 128)
            self.assertEqual(report['final_measured'], e.score_counts(report['final_counts']))
            for key, value in e.exact(report['point']).items():
                self.assertAlmostEqual(report['final_exact'][key], value, places=9)
            expected_shots = report['nfev']*64 if mode == 'shots' else 0
            self.assertEqual(report['training_shots'], expected_shots)
            if mode == 'shots':
                for row in report['history']:
                    self.assertNotEqual(row['seed'], config['final_seed'])
                    hist = row['energy_counts']
                    self.assertEqual(sum(c for _, c in hist), 64)
                    self.assertAlmostEqual(sum(v*c for v, c in hist)/64, row['mean_energy'])

    def test_resource_failure_preserves_failed_status(self):
        e = ThreeHostEvaluator(build_three_host_qubo(TINY), reps=1, threads=1)
        config = dict(initial_point=[.3, 1.], maxiter=8, shots=64, final_shots=64,
            seed=300, final_seed=40000000, rhobeg=1., tol=1e-4,
            max_seconds=60., min_available_gib=1e20)
        report = train(e, config, 'shots', progress=False)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['nfev'], 0)
        self.assertNotIn('final_exact', report)

    def test_calibration_uses_fixed_point_and_separate_batches(self):
        e = ThreeHostEvaluator(build_three_host_qubo(TINY), reps=1, threads=1)
        c = calibrate(e, [.3, 1.], shots=128, batches=4, seed_base=20000000)
        self.assertEqual(len(c['batches']), 4)
        self.assertEqual(len({b['seed'] for b in c['batches']}), 4)
        self.assertAlmostEqual(c['theoretical_se'], c['exact']['energy_std']/np.sqrt(128))


if __name__ == '__main__':
    unittest.main()
