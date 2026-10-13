"""Reproducible conditional pool, frozen split and honest placement controls."""
from itertools import product, combinations_with_replacement
from math import expm1, log1p
from random import Random
from statistics import median
from pathlib import Path
from time import perf_counter
import json
import numpy as np
from .placement import _arrays
from .independent_campaign import canonical_hash
from .benchmark_a_campaign import save_json, _inside
from .branch_a_summary import batch_success

FROZEN_DESIGN='0df7ad1f683eb2ae696422d15833e55a73ff5a552e47cf6b33f965bd9fdb8aad'
SELECTION_SEED=190019


def signature(tasks,hosts):
    variants=[dict(tasks=sorted(tasks),hosts=sorted(hosts)),
        dict(tasks=sorted((r,c) for c,r in tasks),hosts=sorted((r,c) for c,r in hosts))]
    return min(canonical_hash(v) for v in variants)


def candidate_pool(n):
    if n not in (4,5):raise ValueError('Pool uses four or five tasks.')
    pairs=list(product(range(1,4),repeat=2));hosts=list(combinations_with_replacement(pairs,3));capacity=np.array(hosts)
    assignments=np.array(list(product(range(3),repeat=n)));hot=np.eye(3,dtype=int)[assignments]
    used=(hot.sum(axis=1)>0).sum(axis=1);rows=[]
    for tasks in combinations_with_replacement(pairs,n):
        demand=np.array(tasks)
        if np.any(demand.sum(axis=0)>6):continue
        usage=np.einsum('anh,nr->ahr',hot,demand)
        feasible=(usage[None,:,:,:]<=capacity[:,None,:,:]).all(axis=(2,3))
        counts={k:feasible[:,used==k].sum(axis=1) for k in (1,2,3)}
        for j in np.flatnonzero((counts[1]==0)&(counts[2]>0)&(counts[3]>0)):
            S=sum(c.bit_length() for h in hosts[j] for c in h);optimal=int(counts[2][j]);three=int(counts[3][j])
            q=optimal/(4**n*8)
            rows.append(dict(tasks=tasks,hosts=hosts[j],num_qubits=2*n+3+S,optimal_assignments=optimal,
                three_host_assignments=three,uniform_optimal_probability=q,
                uniform_feasible_probability=(2*optimal+three)/(4**n*8),
                uniform_batch_success=batch_success(q,1024),structural_signature=signature(tasks,hosts[j])))
    return rows


def _instance(name,tasks,hosts):
    return dict(schema_version=1,instance_id=name,objective='min_active_hosts',
        tasks=[dict(id=f't{i}',cpu=c,ram=r) for i,(c,r) in enumerate(tasks)],
        hosts=[dict(id=f'h{i}',cpu=c,ram=r) for i,(c,r) in enumerate(hosts)])


def freeze_benchmark(folder):
    folder=Path(folder);rng=Random(SELECTION_SEED);selected=[];stats={}
    for n in (4,5):
        pool=candidate_pool(n);eligible=[r for r in pool if .2<=r['uniform_batch_success']<=.7 and len(set(r['hosts']))>1]
        unique={}
        for r in eligible:unique.setdefault(r['structural_signature'],r)
        eligible=list(unique.values());rng.shuffle(eligible)
        stats[str(n)]=dict(raw_candidates=len(pool),informative_candidates=sum(.2<=r['uniform_batch_success']<=.7 for r in pool),
            informative_heterogeneous_cpu_ram_swap_unique=len(eligible))
        dev=max(eligible,key=lambda r:r['num_qubits']);eligible.remove(dev)
        selected.append((f'a3_dev_n{n}','development',dev))
        eligible.sort(key=lambda r:(r['uniform_batch_success'],r['uniform_feasible_probability'],r['structural_signature']))
        for k,part in enumerate(np.array_split(np.arange(len(eligible)),3),1):
            selected.append((f'a3_test_n{n}_{k}','test',eligible[rng.choice(part.tolist())]))
    controls=[('a3_one_host',[(1,1)]*4,[(5,5),(1,1),(1,1)]),
              ('a3_infeasible',[(3,3)]*4,[(3,3)]*3)]
    from .three_host_encoding import placement_reference
    for name,tasks,hosts in controls:
        selected.append((name,'functional_control',dict(tasks=tasks,hosts=hosts,
            num_qubits=2*len(tasks)+3+sum(c.bit_length() for h in hosts for c in h),
            structural_signature=signature(tasks,hosts))))
    rows=[]
    for name,role,r in selected:
        i=_instance(name,r['tasks'],r['hosts']);ref=placement_reference(i);path=f'instances/{name}.json'
        save_json(folder/path,i)
        rows.append(dict(instance_id=name,role=role,path=path,canonical_sha256=canonical_hash(i),
            structural_signature=r['structural_signature'],num_tasks=len(i['tasks']),num_qubits=r['num_qubits'],
            optimum=ref['optimum'],uniform_batch_success=r.get('uniform_batch_success'),
            uniform_optimal_probability=r.get('uniform_optimal_probability')))
    protocol=dict(scope='phase4k_three_host_pilot_v2',selection_seed=SELECTION_SEED,
        qaoa=dict(depths=[1,2,3],optimization_seeds=[190,191],evaluation_seeds=[100190,100191],
            shots=1024,evaluation_shots=1024,maxiter=200,max_seconds=2400,hamiltonian_scaling='max_abs',
            cobyla_rhobeg=1.,cobyla_tol=1e-4,initial_points_beta_then_gamma={str(p):[.3]+[0.]*(p-1)+[1.]+[0.]*(p-1) for p in (1,2,3)}),
        functional_smoke=dict(reps=1,seed=192,evaluation_seed=100192,maxiter=35),
        resource_policy=dict(max_qubits=25,aer_threads=4,aer_memory_mb=2048,start_available_min_gib=8.,
            remaining_available_min_gib=4.,process_rss_stop_gib=4.),
        analysis=dict(depth_selection='none; p1/p2/p3 reported equally',absolute_success_threshold=None,
            controls=['uniform_encoded_domain_wall_y','random_assignment_y_inferred','exact_enumeration'],
            unit='instance; seeds nested; no IID plug-in for pooled quantum P_opt',
            test_runs_draft=90,test_campaign_started=False))
    save_json(folder/'protocol.json',protocol)
    body=dict(schema_version=1,scope='nt409_three_host_benchmark_v2',protocol_path='protocol.json',
        protocol_canonical_sha256=canonical_hash(protocol),pool_statistics=stats,instances=rows,
        selection='seeded heterogeneous informative pool; CPU/RAM swap and task/host permutations excluded; three strata by baseline probability',
        capacity_domain='pool 1..3; functional optimum1 includes capacity5; model regression verifies capacity4')
    manifest={**body,'design_sha256':canonical_hash(body)};save_json(folder/'manifest.json',manifest)
    return manifest


def load_three_host_benchmark(folder,expected_hash=None):
    folder=Path(folder);manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    body={k:v for k,v in manifest.items() if k!='design_sha256'}
    expected=FROZEN_DESIGN if expected_hash is None else expected_hash
    if canonical_hash(body)!=manifest['design_sha256'] or manifest['design_sha256']!=expected:
        raise ValueError('Frozen three-host manifest changed.')
    protocol=json.loads(_inside(folder,manifest['protocol_path']).read_text(encoding='utf-8'))
    if canonical_hash(protocol)!=manifest['protocol_canonical_sha256']:raise ValueError('Pilot protocol changed.')
    instances={}
    for row in manifest['instances']:
        i=json.loads(_inside(folder,row['path']).read_text(encoding='utf-8'));_arrays(i)
        if canonical_hash(i)!=row['canonical_sha256'] or i['instance_id']!=row['instance_id']:
            raise ValueError('Three-host input changed.')
        instances[row['instance_id']]=i
    return dict(manifest=manifest,protocol=protocol,instances=instances)


def required_lift(q,target=.8,shots=1024):
    if q is None or q==0:return None
    if not 0<q<=1 or not 0<target<1 or type(shots) is not int or shots<1:raise ValueError('Invalid lift inputs.')
    return -expm1(log1p(-target)/shots)/q


def solve_assignment(instance,method='exact_enumeration',draws=1024,seed=190000):
    demand,capacity=_arrays(instance);demand=demand.tolist();capacity=capacity.tolist();n=len(demand);m=len(capacity)
    if m!=3 or n>5:raise ValueError('Solver is limited to the small three-host study.')
    if method=='exact_enumeration':assignments=product(range(m),repeat=n)
    elif method=='random_assignment':
        if type(draws) is not int or draws<1:raise ValueError('Invalid draw count.')
        rng=Random(seed);assignments=(tuple(rng.randrange(m) for _ in demand) for _ in range(draws))
    else:raise ValueError('Unknown placement solver.')
    best=None;placement=None;count=0
    for a in assignments:
        count+=1;usage=[[0,0] for _ in capacity]
        for (c,r),h in zip(demand,a):usage[h][0]+=c;usage[h][1]+=r
        if any(usage[h][r]>capacity[h][r] for h in range(m) for r in range(2)):continue
        objective=len(set(a))
        if best is None or objective<best:best=objective;placement=list(a)
    return dict(best_objective=best,best_placement=placement,evaluations=count)


def measure_assignment(instance,blocks=7,target_seconds=.02,max_calls=4096):
    if type(blocks) is not int or blocks<3 or target_seconds<=0 or max_calls<1:raise ValueError('Invalid timing configuration.')
    rows=[]
    for method in ('exact_enumeration','random_assignment'):
        def block(calls,index):
            t=perf_counter()
            for j in range(calls):solve_assignment(instance,method,seed=190000+index*max_calls+j)
            return perf_counter()-t
        calibration=perf_counter();calls=1
        while block(calls,0)<target_seconds and calls<max_calls:calls=min(calls*2,max_calls)
        calibration=perf_counter()-calibration;times=[block(calls,k+1) for k in range(blocks)]
        rows.append(dict(instance_id=instance['instance_id'],method=method,calls_per_block=calls,
            block_seconds=times,seconds_median=median(times)/calls,seconds_min=min(times)/calls,
            seconds_max=max(times)/calls,calibration_seconds=calibration,
            measurement='warm process; validation, RNG, checks and output included; imports/calibration/reference preparation excluded'))
    return rows
