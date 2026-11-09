"""Notebook 22: isolate finite-shot noise on the frozen three-host QAOA model.

Both modes share a compiled ideal Aer circuit. Only the training energy
estimator changes. Ground truth is used for scoring, never to select angles.
"""
from time import perf_counter
import traceback

import numpy as np
import psutil
from qiskit.circuit.library import QAOAAnsatz
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

from .ising import build_ising, scale_ising
from .three_host_encoding import three_host_reference, decode_three_host
from .qaoa_optimizer import RecordingCOBYLA


def three_host_diagonal(bundle, max_qubits=25, chunk_size=2**18):
    """Bounded polynomial diagonal; never materialize q full bit arrays."""
    q = bundle['qubo'].get_num_vars()
    if not 1 <= q <= max_qubits <= 25:
        raise ValueError('Notebook 22 exact diagnostics support at most 25 qubits.')
    if type(chunk_size) is not int or chunk_size < 1:
        raise ValueError('chunk_size must be positive.')
    count = 2**q
    energies = np.empty(count, dtype=np.float64)
    feasible = np.empty(count, dtype=bool)
    objectives = np.empty(count, dtype=np.uint8)
    optimal = np.empty(count, dtype=bool)
    base_count = bundle['base_count']
    decoded = [decode_three_host(bundle, [(k >> j) & 1 for j in range(q)])
               for k in range(2**base_count)]
    feasible_base = np.array([d['feasible'] for d in decoded], dtype=bool)
    objective_base = np.array([sum(d['y']) for d in decoded], dtype=np.uint8)
    reference = three_host_reference(bundle)
    optimum = reference['original_best_objective']
    objective = bundle['qubo'].objective
    linear = objective.linear.to_dict()
    quadratic = objective.quadratic.to_dict()
    for start in range(0, count, chunk_size):
        stop = min(start+chunk_size, count)
        integers = np.arange(start, stop, dtype=np.uint32)
        bits = [(integers >> j) & 1 for j in range(q)]
        values = np.full(stop-start, objective.constant, dtype=np.float64)
        for i, coefficient in linear.items():
            values += coefficient*bits[i]
        for (i, j), coefficient in quadratic.items():
            values += coefficient*bits[i]*bits[j]
        base = integers % 2**base_count
        energies[start:stop] = values
        feasible[start:stop] = feasible_base[base]
        objectives[start:stop] = objective_base[base]
        optimal[start:stop] = feasible_base[base] & (objective_base[base] == optimum)
    minimum = float(energies.min())
    if not np.isclose(minimum, reference['minimum_energy'], atol=1e-8, rtol=0):
        raise ValueError('Polynomial diagonal and analytic slack reference disagree.')
    return dict(energies=energies, feasible=feasible, objectives=objectives,
                optimal=optimal, optimum=optimum,
                ground=np.isclose(energies, minimum, atol=1e-8, rtol=0))


class ThreeHostEvaluator:
    """Reuse one compiled circuit; exact and sampled calls execute it anew."""
    def __init__(self, bundle, reps, threads=4, min_available_gib=4.):
        if type(reps) is not int or reps < 1:
            raise ValueError('reps must be a positive integer.')
        self.min_available_gib = min_available_gib
        self._memory_guard()
        self.bundle, self.reps = bundle, reps
        self.diagonal = three_host_diagonal(bundle)
        self.size = bundle['qubo'].get_num_vars()
        raw, self.offset = build_ising(bundle)
        self.operator, self.scaling = scale_ising(raw, 'max_abs')
        self.backend = AerSimulator(method='statevector', device='CPU', precision='double',
            max_parallel_threads=threads, max_parallel_experiments=1,
            max_parallel_shots=1, max_memory_mb=8192)
        ansatz = QAOAAnsatz(self.operator, reps=reps)
        self.names = [str(p) for p in ansatz.parameters]
        expected = [f'β[{i}]' for i in range(reps)] + [f'γ[{i}]' for i in range(reps)]
        if self.names != expected:
            raise ValueError('Unexpected QAOA parameter order.')
        manager = generate_preset_pass_manager(optimization_level=1,
                                               backend=self.backend, seed_transpiler=2200)
        compiled = manager.run(ansatz)
        if (compiled.layout is not None
                and compiled.layout.final_index_layout() != list(range(self.size))):
            raise ValueError('This diagnostic requires identity qubit layout.')
        if [str(p) for p in compiled.parameters] != self.names:
            raise ValueError('Transpilation changed parameter order.')
        self.compiled_depth = compiled.depth()
        self.compiled_ops = dict(compiled.count_ops())
        self.exact_circuit = compiled.copy()
        self.exact_circuit.save_probabilities(label='probabilities')
        self.measured_circuit = compiled.copy()
        self.measured_circuit.measure_all()

    def _memory_guard(self):
        if psutil.virtual_memory().available/2**30 < self.min_available_gib:
            raise MemoryError('Available RAM is below the diagnostic minimum.')

    def _point(self, point):
        point = np.asarray(point, dtype=float)
        if point.shape != (2*self.reps,) or not np.isfinite(point).all():
            raise ValueError('Expected beta then gamma: two finite angles per layer.')
        return point

    def _probabilities(self, point):
        self._memory_guard()
        result = self.backend.run(self.exact_circuit.assign_parameters(self._point(point)),
                                  shots=1).result()
        if not result.success:
            raise RuntimeError(str(result.status))
        probabilities = np.asarray(result.data(0)['probabilities'], dtype=float)
        if (probabilities.shape != (2**self.size,)
                or not np.isfinite(probabilities).all() or probabilities.min() < -1e-12
                or not np.isclose(probabilities.sum(), 1., atol=1e-9, rtol=0)):
            raise ValueError('Invalid ideal probability vector.')
        return probabilities

    def mean_energy(self, point):
        return float(self._probabilities(point) @ self.diagonal['energies'])

    def exact(self, point):
        probabilities = self._probabilities(point)
        d = self.diagonal
        mean = float(probabilities @ d['energies'])
        # Centering is more stable than E[E^2] - E[E]^2.
        std = float(np.sqrt(probabilities @ np.square(d['energies'] - mean)))
        return dict(mean_energy=mean, energy_std=std,
            p_valid=float(probabilities[d['feasible']].sum()),
            p_opt=float(probabilities[d['optimal']].sum()) if d['optimum'] is not None else None,
            p_ground=float(probabilities[d['ground']].sum()))

    def sample(self, point, shots, seed):
        self._memory_guard()
        if type(shots) is not int or shots < 1 or type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError('Invalid shots or seed.')
        result = self.backend.run(self.measured_circuit.assign_parameters(self._point(point)),
                                  shots=shots, seed_simulator=seed).result()
        if not result.success:
            raise RuntimeError(str(result.status))
        counts = dict(result.get_counts())
        if sum(counts.values()) != shots:
            raise ValueError('Aer returned an unexpected shot count.')
        return counts

    def score_counts(self, counts):
        if not counts or any(type(c) is not int or c <= 0 for c in counts.values()):
            raise ValueError('Counts must be positive integers.')
        if any(not k or len(k) > self.size or set(k) - {'0', '1'} for k in counts):
            raise ValueError('Counts contain invalid bitstrings.')
        indices = np.array([int(k, 2) for k in counts])
        weights = np.array(list(counts.values()), dtype=float)
        d = self.diagonal
        valid = d['feasible'][indices]
        return dict(mean_energy=float(weights @ d['energies'][indices] / weights.sum()),
            valid_count=int(weights[valid].sum()),
            optimal_count=int(weights[d['optimal'][indices]].sum()) if d['optimum'] is not None else None,
            ground_count=int(weights[d['ground'][indices]].sum()),
            best_valid_objective=int(d['objectives'][indices[valid]].min()) if valid.any() else None)


def calibrate(evaluator, point, shots, batches, seed_base, progress=False):
    """Measure estimator variability at one fixed point, without optimizing it."""
    started = perf_counter()
    exact = evaluator.exact(point)
    exact_seconds = perf_counter()-started
    rows = []
    for i in range(batches):
        seed = seed_base + i
        started = perf_counter()
        counts = evaluator.sample(point, shots, seed)
        seconds = perf_counter()-started
        if progress and (i == 0 or (i+1) % 5 == 0):
            print(f"  calibration {i+1}/{batches}: {seconds:.2f}s", flush=True)
        rows.append(dict(seed=seed, counts=counts, seconds=seconds,
                         mean_energy=evaluator.score_counts(counts)['mean_energy']))
    means = np.array([r['mean_energy'] for r in rows])
    return dict(point=list(point), shots=shots, exact=exact, exact_seconds=exact_seconds, batches=rows,
                theoretical_se=exact['energy_std']/np.sqrt(shots),
                observed_batch_sd=float(means.std(ddof=1)) if batches > 1 else None,
                observed_mean_error=float(means.mean()-exact['mean_energy']))


def train(evaluator, config, mode, progress=True):
    """Same COBYLA and circuit in both modes; never select angles using P_opt.

    Energy histograms retain every sampled training mean for audit. Exact
    endpoint scoring and final measured counts are post-training diagnostics.
    Time/RAM guards operate between native calls, not as hard interrupts.
    """
    if mode not in ('exact', 'shots'):
        raise ValueError('mode must be exact or shots.')
    started = perf_counter()
    report = dict(mode=mode, config=dict(config), history=[], status='running')
    def guard():
        if psutil.virtual_memory().available/2**30 < config['min_available_gib']:
            raise MemoryError('Available RAM is below the diagnostic minimum.')
        if perf_counter()-started > config['max_seconds']:
            raise TimeoutError('Per-run time guard reached between native calls.')

    def objective(point):
        guard()
        index = len(report['history'])
        row = dict(evaluation=index+1, point=np.asarray(point).tolist())
        if mode == 'exact':
            mean = evaluator.mean_energy(point)
            row.update(seed=None, energy_counts=None)
        else:
            seed = config['seed']*10000 + index
            if seed == config['final_seed']:
                raise ValueError('Final measurement seed overlaps training.')
            counts = evaluator.sample(point, config['shots'], seed)
            energies = evaluator.diagonal['energies']
            histogram = {}
            for bits, count in counts.items():
                value = float(energies[int(bits, 2)])
                histogram[value] = histogram.get(value, 0) + count
            mean = sum(value*count for value, count in histogram.items())/config['shots']
            row.update(seed=seed, energy_counts=sorted(histogram.items()))
        normalized = (mean-evaluator.offset)/evaluator.scaling['scale']
        row.update(mean_energy=mean, optimizer_value=normalized,
                   seconds=perf_counter()-started)
        report['history'].append(row)
        if progress and (index == 0 or (index+1) % 25 == 0):
            print(f"  {mode} eval {index+1}: E={mean:.6f}", flush=True)
        guard()
        return normalized

    try:
        guard()
        optimizer = RecordingCOBYLA(config['maxiter'], config['rhobeg'], config['tol'])
        result = optimizer(objective, config['initial_point'])
        report.update(point=result.x.tolist(), optimizer_value=float(result.fun),
                      optimizer_stop=optimizer.stop, optimization_seconds=perf_counter()-started)
        if len(report['history']) != optimizer.stop['nfev']:
            raise ValueError('Optimizer and recorded evaluation counts differ.')
        guard()
        report['final_exact'] = evaluator.exact(result.x)
        guard()
        counts = evaluator.sample(result.x, config['final_shots'], config['final_seed'])
        report.update(final_counts=counts, final_measured=evaluator.score_counts(counts))
        guard()
        report['status'] = 'completed'
    except (Exception, KeyboardInterrupt) as error:
        report.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                      error_type=type(error).__name__, error=str(error),
                      traceback=traceback.format_exc(limit=8))
    report.update(nfev=len(report['history']), elapsed_seconds=perf_counter()-started,
                  training_shots=len(report['history'])*config['shots'] if mode == 'shots' else 0)
    return report
