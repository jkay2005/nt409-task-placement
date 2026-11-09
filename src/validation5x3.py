"""Prospective, conditioned 5x3 validation data; no QAOA-based selection."""
from datetime import datetime, timezone
from itertools import combinations, combinations_with_replacement, product
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
from random import Random

import numpy as np

from .placement import _arrays, evaluate_placement
from .independent_campaign import canonical_hash
from .three_host_benchmark import signature, _instance
from .three_host_encoding import (build_three_host_qubo, certify_three_host,
    three_host_reference)
from .ising import build_ising, ising_energy, scale_ising
from .qaoa_experiment import qubo_fingerprint
from .shot_noise_campaign import save_json
from .classical_baselines import solve_heuristic

DATA = 'data/benchmarks/nt409_validation5x3_v1/dataset.json'
SEED = 20261025
DATA_HASH = '19bcd132aa4e240220611111dd81190fa21c84842f3c5f2bfb29de036c290758'
ASSIGNMENTS = np.asarray(list(product(range(3), repeat=5)), dtype=int)
HOT = np.eye(3, dtype=int)[ASSIGNMENTS]
USED = np.asarray([len(set(a)) for a in ASSIGNMENTS])


def assignment_audit(instance):
    demand, capacity = _arrays(instance)
    if demand.shape != (5,2) or capacity.shape != (3,2):
        raise ValueError('Exactly five tasks and three hosts are required.')
    usage = np.einsum('anh,nr->ahr', HOT, demand)
    cpu, ram = [(usage[:,:,r] <= capacity[:,r]).all(axis=1) for r in range(2)]
    feasible = cpu & ram
    histogram = {str(k): int((feasible & (USED==k)).sum()) for k in (1,2,3)}
    optimum = next((k for k in (1,2,3) if histogram[str(k)]), None)
    def witness(mask):
        return ASSIGNMENTS[np.flatnonzero(mask)[0]].tolist() if mask.any() else None
    return dict(assignments=243, histogram=histogram, optimum=optimum,
        feasible_assignments=int(feasible.sum()),
        optimal_assignments=histogram[str(optimum)] if optimum else 0,
        cpu_pass_ram_fail=int((cpu & ~ram).sum()),
        ram_pass_cpu_fail=int((ram & ~cpu).sum()),
        cpu_pass_ram_fail_witness=witness(cpu & ~ram),
        ram_pass_cpu_fail_witness=witness(ram & ~cpu),
        optimal_witness=witness(feasible & (USED==optimum)))


def select_cases(excluded_signatures):
    """Enumerate the finite multiset pool; rank each stratum by seeded SHA256."""
    hosts = list(combinations_with_replacement(list(product((2,3),repeat=2)),3))
    capacities = np.asarray(hosts)
    unique = {}; feasible_count = independent_count = 0
    excluded = set(excluded_signatures)
    demands = list(combinations_with_replacement(list(product((1,2,3),repeat=2)),5))
    for tasks in demands:
        usage = np.einsum('anh,nr->ahr', HOT, np.asarray(tasks))
        cpu, ram = [(usage[None,:,:,r] <= capacities[:,None,:,r]).all(axis=2) for r in range(2)]
        valid = cpu & ram
        has_solution = valid.any(axis=1)
        feasible_count += int(has_solution.sum())
        independent = has_solution & (cpu & ~ram).any(axis=1) & (ram & ~cpu).any(axis=1)
        for h in np.flatnonzero(independent):
            if len(set(tasks))<2 or len(set(hosts[h]))<2: continue
            independent_count += 1
            sig = signature(tasks, hosts[h])
            if sig in excluded or sig in unique: continue
            optimum = int(USED[valid[h]].min())
            unique[sig] = dict(tasks=tasks, hosts=hosts[h], signature=sig,
                               optimum=optimum, feasible=int(valid[h].sum()))
    twos = [r for r in unique.values() if r['optimum']==2]
    threes = sorted((r for r in unique.values() if r['optimum']==3),
                    key=lambda r:(r['feasible'],r['signature']))
    midpoint = len(threes)//2
    strata = [twos, threes[:midpoint], threes[midpoint:]]
    if not all(strata): raise ValueError('Selection strata must all be nonempty.')
    cases = []
    for k, pool in enumerate(strata):
        chosen = min(pool, key=lambda r:canonical_hash(dict(seed=SEED, signature=r['signature'])))
        tasks, host_rows = list(chosen['tasks']), list(chosen['hosts'])
        rng = Random(SEED+k); rng.shuffle(tasks); rng.shuffle(host_rows)
        cases.append(_instance(f'v5x3_{k+1}', tasks, host_rows))
    stats = dict(raw_multiset_candidates=len(demands)*len(hosts),
        feasible_multiset_candidates=feasible_count,
        independent_heterogeneous_candidates=independent_count,
        unique_eligible_after_exclusions=len(unique), excluded_signature_count=len(excluded),
        strata_sizes=[len(p) for p in strata], selection_seed=SEED)
    return cases, stats


def load_dataset(root):
    data = json.loads((Path(root)/DATA).read_text(encoding='utf-8'))
    if canonical_hash(data) != DATA_HASH:
        raise ValueError('Frozen dataset, protocol or exclusions changed.')
    for instance in [data['development_instance'], *data['validation_instances']]:
        assignment_audit(instance)
    return data


def run_audit(root, output_dir, progress=True):
    root, out = Path(root).resolve(), Path(output_dir).resolve()
    if out.exists(): raise FileExistsError('Use a fresh audit directory.')
    data = load_dataset(root)
    selected, stats = select_cases(data['excluded_signatures'])
    if selected != data['validation_instances'] or stats != data['pool_statistics']:
        raise AssertionError('Frozen selection cannot be reproduced.')
    names = ('validation5x3.py','classical_baselines.py','three_host_encoding.py',
             'three_host_benchmark.py','independent_campaign.py','placement.py',
             'qubo.py','ising.py','qaoa_experiment.py','shot_noise_campaign.py')
    result = dict(status='running', created_utc=datetime.now(timezone.utc).isoformat(),
        dataset_sha256=DATA_HASH, selection_reproduced=True, training_evaluations=0,
        runtime=dict(platform=platform.platform(),packages={n:importlib.metadata.version(n)
            for n in ('numpy','qiskit','qiskit-optimization')}),
        source_sha256={n:hashlib.sha256((root/'src'/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                       for n in names}, cases=[],
        limitations=['Three conditioned synthetic validation cases, not a population sample.',
            'No QAOA optimizer, statevector simulation, new MILP run or timing benchmark.',
            'Heuristics use frozen task/host order; no permutation robustness claim.'])
    out.mkdir(parents=True); save_json(out/'dataset.json',data); save_json(out/'audit.json',result)
    try:
        for k, instance in enumerate([data['development_instance'], *selected]):
            if progress: print('Audit',instance['instance_id'],'| 5 tasks x 3 hosts',flush=True)
            truth = assignment_audit(instance)
            # Independent scalar validator checks every assignment against vectorized truth.
            scalar = {str(h):0 for h in (1,2,3)}
            for a in ASSIGNMENTS:
                checked = evaluate_placement(instance,a)
                if checked['feasible']: scalar[str(checked['objective'])] += 1
            if scalar != truth['histogram']: raise AssertionError('Placement oracles differ.')
            bundle = build_three_host_qubo(instance)
            certificate = certify_three_host(bundle)
            reference = three_host_reference(bundle)
            q = bundle['qubo'].get_num_vars()
            if q!=25 or reference['original_best_objective']!=truth['optimum']:
                raise AssertionError('Model size or optimum differs.')
            if {a:b for a,b in truth['histogram'].items() if b} != reference['placement_histogram']:
                raise AssertionError('QUBO reference placement histogram differs.')
            operator, offset = build_ising(bundle); _, scaling = scale_ising(operator,'max_abs')
            eye = np.eye(q,dtype=int)
            basis = [np.zeros(q,dtype=int),*eye]
            basis.extend(eye[i]+eye[j] for i,j in combinations(range(q),2))
            error = max(abs(bundle['qubo'].objective.evaluate(b)-ising_energy(operator,offset,b)) for b in basis)
            if error>1e-8: raise AssertionError('Ising polynomial identity differs.')
            heuristics = []
            for method in ('FirstFit','BFD'):
                h = solve_heuristic(instance,method)
                if h['found_valid'] and (not evaluate_placement(instance,h['placement'])['feasible']
                        or h['objective']<truth['optimum']):
                    raise AssertionError('Heuristic output differs from truth.')
                heuristics.append(h)
            result['cases'].append(dict(instance_id=instance['instance_id'],
                role='development' if k==0 else 'prospective_validation',
                input_sha256=canonical_hash(instance), structural_signature=signature(
                    [(t['cpu'],t['ram']) for t in instance['tasks']],
                    [(h['cpu'],h['ram']) for h in instance['hosts']]),
                qubo_sha256=qubo_fingerprint(bundle), qubits=q, truth=truth,
                certificate=certificate,max_ising_error=float(error),offset=offset,
                scale=scaling['scale'],reference=reference,heuristics=heuristics))
            save_json(out/'audit.json',result)
        result['status']='PASS'
    except (Exception, KeyboardInterrupt) as error:
        result.update(status='FAILED',error=f'{type(error).__name__}: {error}')
        save_json(out/'audit.json',result); raise
    save_json(out/'audit.json',result)
    return result
