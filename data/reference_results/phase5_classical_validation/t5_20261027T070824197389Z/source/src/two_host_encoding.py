"""Exact one-hot subspace encoding for two hosts; historical modules unchanged."""
from collections import Counter
from itertools import product
import numpy as np
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import LinearEqualityToPenalty
from .placement import _arrays, evaluate_model
from .qubo import build_qubo, _binary_vector, complete_with_best_slack
from .qaoa_experiment import slack_encoding_counts

ENCODING = 'two_host_binary_v1'


def build_two_host_qubo(instance):
    demand, capacity = _arrays(instance)
    if len(capacity) != 2:
        raise ValueError('This encoding requires exactly two hosts.')
    old = build_qubo(instance, assignment_penalty=3, capacity_penalty=3)
    n = old['n']; model = QuadraticProgram(name=instance['instance_id']+'_'+ENCODING)
    for i in range(n):model.binary_var(name=f'z_{i}')
    for h in range(2):model.binary_var(name=f'y_{h}')
    groups=[]
    for group in old['slack_groups']:
        indices=[]
        for name in group['names']:
            indices.append(model.get_num_vars());model.binary_var(name=name)
        groups.append({**group,'indices':indices})
    model.minimize(linear={'y_0':1,'y_1':1})
    for group in groups:
        h,r=group['host'],group['resource_index']
        linear={f'z_{i}':int(demand[i,r])*(1 if h else -1) for i in range(n)}
        linear[f'y_{h}']=-group['capacity']
        linear.update(zip(group['names'],group['weights']))
        model.linear_constraint(linear=linear,sense='==',
            rhs=0 if h else -int(demand[:,r].sum()),name=f"capacity_{h}_{group['resource']}")
    qubo=LinearEqualityToPenalty(penalty=3).convert(model)
    return {**old,'model':model,'qubo':qubo,'base_count':n+2,'slack_groups':groups,
            'model_version':ENCODING,'encoding':ENCODING,'one_hot_bundle':old}


def expand_bits(bundle,bits):
    bits=_binary_vector(bits,bundle['qubo'].get_num_vars());n=bundle['n']
    x=np.column_stack((1-bits[:n],bits[:n])).reshape(-1)
    return np.concatenate((x,bits[n:]))


def compact_bits(bundle,bits):
    bits=_binary_vector(bits,bundle['one_hot_bundle']['qubo'].get_num_vars());n=bundle['n']
    x=bits[:2*n].reshape(n,2)
    if not (x.sum(axis=1)==1).all():raise ValueError('Only one-hot vectors have a compact representation.')
    return np.concatenate((x[:,1],bits[2*n:]))


def decode_compact(bundle,bits):
    bits=_binary_vector(bits,bundle['qubo'].get_num_vars());n=bundle['n']
    return evaluate_model(bundle['instance'],np.column_stack((1-bits[:n],bits[:n])),bits[n:n+2])


def _base_rows(bundle):
    if bundle['base_count']>16:raise ValueError('Exact reference is limited to tiny fixtures.')
    for base in product((0,1),repeat=bundle['base_count']):
        bits=np.zeros(bundle['qubo'].get_num_vars(),dtype=int);bits[:len(base)]=base
        yield bits,decode_compact(bundle,bits)


def compact_reference(bundle):
    """Enumerate z/y; account analytically for every slack encoding, including duplicates."""
    groups=bundle['slack_groups'];encodings=[slack_encoding_counts(g['weights']) for g in groups]
    histogram=Counter();records=[];mean=0.;minimum=float('inf')
    for bits,d in _base_rows(bundle):
        energy=float(sum(d['y']));conditional=energy;multiplicity=1
        for g,counts in zip(groups,encodings):
            residual=d['usage'][g['host']][g['resource_index']]-g['capacity']*d['y'][g['host']]
            target=max(0,-residual);multiplicity*=counts[target]
            energy+=3*(residual+target)**2
            conditional+=3*((residual+sum(g['weights'])/2)**2+sum(w*w for w in g['weights'])/4)
        best_old=complete_with_best_slack(bundle['one_hot_bundle'],expand_bits(bundle,bits)[:bundle['one_hot_bundle']['base_count']])
        best=compact_bits(bundle,best_old)
        if not np.isclose(bundle['qubo'].objective.evaluate(best),energy,rtol=0,atol=1e-8):
            raise AssertionError('Analytic slack minimum differs from reduced QUBO.')
        records.append((energy,multiplicity,d,best.tolist()));minimum=min(minimum,energy);mean+=conditional
        if d['feasible']:histogram[d['objective']]+=1
    optimum=min(histogram) if histogram else None
    minima=[x for x in records if x[0]==minimum];base_states=len(records);total=2**bundle['qubo'].get_num_vars()
    uniform=dict(method='exact_zy_enumeration_and_slack_encoding_counts',checked_base_vectors=base_states,
        total_bitstrings=total,original_best_objective=optimum,feasible_base_count=sum(histogram.values()),
        optimal_placement_base_count=histogram[optimum] if optimum is not None else None,
        qubo_ground_state_bitstring_count=sum(x[1] for x in minima),
        feasible_probability=sum(histogram.values())/base_states,
        optimal_placement_probability=histogram[optimum]/base_states if optimum is not None else None,
        ground_state_probability=sum(x[1] for x in minima)/total,mean_qubo_energy=mean/base_states)
    return dict(minimum_energy=minimum,original_best_objective=optimum,instance_feasible=optimum is not None,
        minimizer_base_count=len(minima),all_qubo_minimizers_feasible=all(x[2]['feasible'] for x in minima),
        example_minimizer_bits=minima[0][3],uniform_baseline=uniform)


def certify_encoding(bundle):
    """Prove equality of binary quadratic polynomials via their complete degree-2 basis."""
    size=bundle['qubo'].get_num_vars();old=bundle['one_hot_bundle'];checked=0
    vectors=[np.zeros(size,dtype=int)]+[np.eye(size,dtype=int)[i] for i in range(size)]
    vectors.extend(np.eye(size,dtype=int)[i]+np.eye(size,dtype=int)[j]
                   for i in range(size) for j in range(i+1,size))
    for bits in vectors:
        if not np.isclose(bundle['qubo'].objective.evaluate(bits),
                          old['qubo'].objective.evaluate(expand_bits(bundle,bits)),rtol=0,atol=1e-8):
            raise AssertionError('Reduced polynomial differs on its degree-2 basis.')
        checked+=1
    feasible=set();onehot=set()
    for bits,d in _base_rows(bundle):
        if d['feasible']:feasible.add(tuple(expand_bits(bundle,bits)[:old['base_count']]))
        onehot.add(tuple(expand_bits(bundle,bits)[:old['base_count']]))
    # Independent enumeration in the old x/y space verifies surjectivity too.
    from .qubo import decode_qubo
    old_feasible=set();old_onehot=set()
    for base in product((0,1),repeat=old['base_count']):
        full=np.zeros(old['qubo'].get_num_vars(),dtype=int);full[:len(base)]=base
        d=decode_qubo(old,full)
        if d['one_hot_ok']:old_onehot.add(base)
        if d['feasible']:old_feasible.add(base)
    if feasible!=old_feasible or onehot!=old_onehot:raise AssertionError('Placement sets differ.')
    return dict(polynomial_identity=True,polynomial_basis_vectors=checked,
        checked_base_vectors=2**bundle['base_count'],feasible_base_vectors=len(feasible),
        old_qubits=old['qubo'].get_num_vars(),new_qubits=size,
        method='binary_degree_2_basis_and_exhaustive_base_set_bijection')
