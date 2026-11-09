"""Three-host domain-wall QUBO, independent placement truth and exact controls."""
from collections import Counter
from itertools import product, combinations
import numpy as np
from qiskit_optimization import QuadraticProgram
from .placement import _arrays, evaluate_model, evaluate_placement
from .qubo import build_qubo, _binary_vector
from .qaoa_experiment import slack_encoding_counts

ENCODING='three_host_domain_wall_v2'
PENALTY=4


def build_three_host_qubo(instance):
    demand,capacity=_arrays(instance);n=len(demand)
    if len(capacity)!=3 or not 1<=n<=5:
        raise ValueError('Three hosts and one to five tasks are required.')
    old=build_qubo(instance,assignment_penalty=PENALTY,capacity_penalty=PENALTY)
    model=QuadraticProgram(name=instance['instance_id']+'_'+ENCODING)
    for i in range(n):
        model.binary_var(name=f'u_{i}');model.binary_var(name=f'v_{i}')
    for h in range(3):model.binary_var(name=f'y_{h}')
    groups=[]
    for g in old['slack_groups']:
        indices=[]
        for name in g['names']:
            indices.append(model.get_num_vars());model.binary_var(name=name)
        groups.append({**g,'indices':indices})
    size=model.get_num_vars();T=np.zeros((old['qubo'].get_num_vars(),size));c=np.zeros(len(T))
    for i in range(n):
        c[3*i]=1;T[3*i,2*i]=-1
        T[3*i+1,2*i]=1;T[3*i+1,2*i+1]=-1;T[3*i+2,2*i+1]=1
    T[3*n:,2*n:]=np.eye(size-2*n)
    objective=old['qubo'].objective;Q=objective.quadratic.to_array();l=objective.linear.to_array()
    quadratic=T.T@Q@T;linear=T.T@l+T.T@(Q+Q.T)@c
    for i in range(n):
        linear[2*i+1]+=PENALTY;quadratic[2*i,2*i+1]-=PENALTY
    model.minimize(constant=float(objective.constant+c@l+c@Q@c),linear=linear,quadratic=quadratic)
    return {**old,'qubo':model,'model':model,'model_version':ENCODING,'encoding':ENCODING,
        'base_count':2*n+3,'slack_groups':groups,'one_hot_bundle':old,'affine_map':T,'affine_offset':c}


def decode_three_host(bundle,bits):
    bits=_binary_vector(bits,bundle['qubo'].get_num_vars());n=bundle['n']
    uv=bits[:2*n].reshape(n,2);u,v=uv.T;y=bits[2*n:2*n+3]
    x=np.column_stack((1-u,u-v,v));valid=bool((u>=v).all())
    if not valid:
        demand,_=_arrays(bundle['instance'])
        return dict(domain_valid=False,feasible=False,objective=None,one_hot_ok=False,
            capacity_ok=False,x=x.tolist(),y=y.tolist(),usage=(x.T@demand).tolist(),placement=None)
    return dict(**evaluate_model(bundle['instance'],x,y),domain_valid=True,placement=(u+v).tolist())


def energy_formula(bundle,bits):
    bits=_binary_vector(bits,bundle['qubo'].get_num_vars());n=bundle['n'];demand,_=_arrays(bundle['instance'])
    u,v=bits[:2*n].reshape(n,2).T;x=np.column_stack((1-u,u-v,v));y=bits[2*n:2*n+3]
    usage=x.T@demand;energy=int(y.sum()+PENALTY*np.sum(v*(1-u)))
    for g in bundle['slack_groups']:
        slack=sum(int(bits[j])*w for j,w in zip(g['indices'],g['weights']))
        residual=int(usage[g['host'],g['resource_index']])-g['capacity']*int(y[g['host']])+slack
        energy+=PENALTY*residual**2
    return float(energy)


def placement_reference(instance):
    demand,capacity=_arrays(instance);n=len(demand)
    if len(capacity)!=3 or n>5:raise ValueError('Reference is limited to three hosts/five tasks.')
    histogram=Counter()
    for assignment in product(range(3),repeat=n):
        d=evaluate_placement(instance,assignment)
        if d['feasible']:histogram[d['objective']]+=1
    optimum=min(histogram) if histogram else None;total=3**n
    return dict(assignments=total,histogram={str(k):int(v) for k,v in sorted(histogram.items())},
        optimum=optimum,feasible_probability=sum(histogram.values())/total,
        optimal_probability=histogram[optimum]/total if optimum is not None else None,
        method='exact host-assignment enumeration; y inferred; no overload repair')


def three_host_reference(bundle):
    n=bundle['n'];size=bundle['base_count'];truth=placement_reference(bundle['instance'])
    # Only base bits are enumerated. Slack minimization/multiplicity is exact.
    base=np.asarray(list(product((0,1),repeat=size)),dtype=int);u=base[:,:2*n:2];v=base[:,1:2*n:2]
    x=np.stack((1-u,u-v,v),axis=2);y=base[:,2*n:];demand,_=_arrays(bundle['instance'])
    usage=np.einsum('bnh,nr->bhr',x,demand);domain=(u>=v).all(axis=1)
    minimum=y.sum(axis=1).astype(float)+PENALTY*np.sum(v*(1-u),axis=1)
    conditional=minimum.copy();multiplicity=np.ones(len(base),dtype=np.int64);capacity_ok=np.ones(len(base),dtype=bool)
    targets=[]
    for g in bundle['slack_groups']:
        residual=usage[:,g['host'],g['resource_index']]-g['capacity']*y[:,g['host']]
        target=np.clip(-residual,0,g['capacity']);targets.append(target)
        counts=slack_encoding_counts(g['weights']);multiplicity*=np.array([counts[int(t)] for t in target])
        minimum+=PENALTY*(residual+target)**2
        conditional+=PENALTY*((residual+sum(g['weights'])/2)**2+sum(w*w for w in g['weights'])/4)
        capacity_ok&=residual<=0
    feasible=domain&capacity_ok;objective=y.sum(axis=1);optimum=truth['optimum']
    low=float(minimum.min());minima=minimum==low;index=int(np.flatnonzero(minima)[0])
    bits=np.zeros(bundle['qubo'].get_num_vars(),dtype=int);bits[:size]=base[index]
    for g,target in zip(bundle['slack_groups'],targets):
        encoding=next(a for a in product((0,1),repeat=len(g['weights'])) if sum(b*w for b,w in zip(a,g['weights']))==target[index])
        bits[g['indices']]=encoding
    if not np.isclose(bundle['qubo'].objective.evaluate(bits),low,rtol=0,atol=1e-8):
        raise AssertionError('Slack minimum differs from QUBO.')
    all_ground_valid=bool(feasible[minima].all())
    if optimum is not None and (low!=optimum or not all_ground_valid or not (objective[minima]==optimum).all()):
        raise AssertionError('Ground states do not encode the exact placement optimum.')
    uniform=dict(method='exact_domain_wall_y_enumeration_slack_marginal',checked_base_vectors=len(base),
        total_bitstrings=2**len(bits),original_best_objective=optimum,
        feasible_probability=float(feasible.mean()),
        optimal_placement_probability=float((feasible&(objective==optimum)).mean()) if optimum is not None else None,
        invalid_domain_probability=float((~domain).mean()),
        ground_state_probability=int(multiplicity[minima].sum())/2**len(bits),mean_qubo_energy=float(conditional.mean()))
    return dict(minimum_energy=low,original_best_objective=optimum,instance_feasible=optimum is not None,
        all_qubo_minimizers_feasible=all_ground_valid,example_minimizer_bits=bits.tolist(),
        minimizer_base_count=int(minima.sum()),uniform_baseline=uniform,structured_random=truth,
        placement_histogram=truth['histogram'])


def certify_three_host(bundle):
    size=bundle['qubo'].get_num_vars();eye=np.eye(size,dtype=int);checked=0
    vectors=[np.zeros(size,dtype=int),*eye]
    vectors.extend(eye[i]+eye[j] for i,j in combinations(range(size),2))
    for bits in vectors:
        q=float(bundle['qubo'].objective.evaluate(bits));extended=bundle['affine_map']@bits+bundle['affine_offset']
        domain=PENALTY*sum(int(bits[2*i+1])*(1-int(bits[2*i])) for i in range(bundle['n']))
        old=float(bundle['one_hot_bundle']['qubo'].objective.evaluate(extended))+domain
        if not np.isclose(q,energy_formula(bundle,bits),rtol=0,atol=1e-8) or not np.isclose(q,old,rtol=0,atol=1e-8):
            raise AssertionError('Domain-wall polynomial identity differs.')
        checked+=1
    return dict(polynomial_identity=True,degree_two_basis_vectors=checked,
        method='complete binary degree-two basis; old affine energy plus domain penalty',
        num_qubits=size,domain_and_capacity_penalty=PENALTY)
