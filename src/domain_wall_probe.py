"""T3 qualification and one-evaluation timing; never optimize or rank variants."""
from datetime import datetime, timezone
import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
from time import perf_counter
import traceback

import numpy as np
import psutil
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from scipy.linalg import expm

from .domain_wall_mixer import (VARIANTS, INPUT_HASH, validate_fixed_instance,
    mix_pair, make_evaluator, domain_probability)
from .qaoa_experiment import qubo_fingerprint
from .shot_noise_campaign import save_json
from .three_host_encoding import build_three_host_qubo, three_host_reference

QUBO_HASH = '8fa77f91e277724277e5aaf4c1a29b5cec345e91e3660f13a6a166efc44fc515'


def optional_rss_mib():
    """Missing process telemetry is unknown, never fabricated as zero RAM."""
    try:
        return psutil.Process().memory_info().rss/2**20
    except (psutil.Error, OSError):
        return None


def certify_pair():
    """A local gate-block proof, not a different/smaller placement instance."""
    a = np.zeros((4,4)); a[0,1] = a[1,0] = 1
    b = np.zeros((4,4)); b[1,3] = b[3,1] = 1
    errors=[]; leakage=[]
    for beta in [0., .37, -.81, np.pi/2, np.pi]:
        qc=QuantumCircuit(2); mix_pair(qc,0,1,beta)
        unitary=Operator(qc).data
        errors.append(float(np.max(np.abs(unitary-expm(-1j*beta*b)@expm(-1j*beta*a)))))
        leakage.append(float(np.max(np.abs(unitary[2,[0,1,3]])**2)))
        if not np.allclose(unitary.conj().T@unitary,np.eye(4),atol=1e-12,rtol=0):
            raise AssertionError('Pair is not unitary.')
    qc=QuantumCircuit(2);mix_pair(qc,0,1,.37);u=Operator(qc).data
    reached={0}
    for _ in range(3):
        reached |= {j for i in reached for j in [0,1,3] if abs(u[j,i])+abs(u[i,j])>1e-10}
    if max(errors)>1e-12 or max(leakage)>1e-12 or reached!={0,1,3}:
        raise AssertionError('Pair proof failed.')
    return dict(max_matrix_error=max(errors),max_leakage=max(leakage),connected=True,
                circuit_order='A then B; U=B(beta)A(beta)',
                warning='Product of exponentials, not a single exponential of A+B.')


def _metrics(evaluator, probabilities):
    d=evaluator.diagonal
    return dict(p_domain=domain_probability(probabilities),
        p_valid=float(probabilities[d['feasible']].sum()),
        p_opt=float(probabilities[d['optimal']].sum()),
        p_ground=float(probabilities[d['ground']].sum()),
        mean_energy=float(probabilities@d['energies']),probability_sum=float(probabilities.sum()))


def run_probe(root, output_dir, threads=4, min_available_gib=4., progress=True):
    root,out=Path(root).resolve(),Path(output_dir).resolve()
    if out.exists():
        raise FileExistsError('Use a fresh output directory; T3 does not overwrite a previous probe.')
    instance=json.loads((root/'data/benchmarks/nt409_shot_noise_v2/instance.json').read_text(encoding='utf-8'))
    validate_fixed_instance(instance)
    if type(threads) is not int or threads<1 or not np.isfinite(min_available_gib) or min_available_gib<=0:
        raise ValueError('Positive thread count and available-RAM guard required.')
    bundle=build_three_host_qubo(instance)
    if qubo_fingerprint(bundle)!=QUBO_HASH:
        raise ValueError('QUBO coefficients/order changed.')
    reference=three_host_reference(bundle)
    sources=('domain_wall_mixer.py','domain_wall_probe.py','shot_noise_diagnostic.py',
             'three_host_encoding.py','ising.py','qubo.py','placement.py','qaoa_experiment.py',
             'qaoa_optimizer.py','shot_noise_campaign.py')
    source_hash={name:hashlib.sha256((root/'src'/name).read_bytes()).hexdigest() for name in sources}
    result=dict(schema_version=1,stage='T3 qualification, not T4 training',status='running',
        created_utc=datetime.now(timezone.utc).isoformat(),shape=[5,3],qubits=25,
        input_sha256=INPUT_HASH,qubo_sha256=QUBO_HASH,source_sha256=source_hash,
        training_evaluations=0,threads=threads,min_available_gib=min_available_gib,
        runtime=dict(platform=platform.platform(),processor=platform.processor(),
            packages={name:importlib.metadata.version(name) for name in ['numpy','scipy','qiskit','qiskit-aer','qiskit-optimization','psutil']}),
        pair_certificate=certify_pair(),initial_checks=[],records=[],
        limitations=['Fixed untrained angles: no ranking or improvement conclusion.',
            'One timed evaluation per circuit; not a matched runtime benchmark.',
            'RSS is measured after evaluation, not peak; null means unavailable.',
            'Available-RAM guard is checked between native calls; not an interrupt.',
            'Preserves domain-wall codes only; capacity/slack may still be invalid.'])
    out.mkdir(parents=True)
    save_json(out/'instance.json',instance)
    save_json(out/'probe.json',result)
    try:
        for reps in (1,2):
            # Predeclared points, unrelated to the optimum or previously learned angles.
            point=[.3,1.] if reps==1 else [.3,.2,1.,.5]
            for variant in VARIANTS:
                if progress:print(f'T3 p={reps} {variant}: build frozen 25-qubit circuit',flush=True)
                started=perf_counter()
                evaluator=make_evaluator(bundle,reps,variant,threads,min_available_gib)
                setup_seconds=perf_counter()-started
                if reps==1:
                    probabilities=evaluator._probabilities([0.,0.])
                    initial=_metrics(evaluator,probabilities);del probabilities
                    expected_domain=(3/4)**5 if variant=='standard_x' else 1.
                    factor=1. if variant=='standard_x' else (4/3)**5
                    if abs(initial['p_domain']-expected_domain)>1e-10:
                        raise AssertionError('Initial domain probability differs.')
                    for metric,key in [('p_valid','feasible_probability'),('p_opt','optimal_placement_probability')]:
                        if abs(initial[metric]-factor*reference['uniform_baseline'][key])>1e-10:
                            raise AssertionError('Initial distribution is not uniform as specified.')
                    result['initial_checks'].append(dict(variant=variant,**initial))
                started=perf_counter()
                probabilities=evaluator._probabilities(point)
                evaluation_seconds=perf_counter()-started
                metrics=_metrics(evaluator,probabilities);del probabilities
                if not (metrics['p_ground']<=metrics['p_opt']+1e-12<=metrics['p_valid']+2e-12
                        <=metrics['p_domain']+3e-12):
                    raise AssertionError('Probability event inclusion failed.')
                if variant=='valid_dw' and abs(1-metrics['p_domain'])>1e-10:
                    raise AssertionError('Full 25-qubit circuit leaked out of the domain.')
                result['records'].append(dict(variant=variant,p=reps,point=point,
                    setup_seconds=setup_seconds,evaluation_seconds=evaluation_seconds,
                    rss_after_evaluation_mib=optional_rss_mib(),
                    compiled_depth=evaluator.compiled_depth,compiled_ops=evaluator.compiled_ops,**metrics))
                if progress:print(f"  PASS: P_domain={metrics['p_domain']:.12f}; one eval={evaluation_seconds:.3f}s",flush=True)
                save_json(out/'probe.json',result)
                del evaluator;gc.collect()
        result['status']='PASS'
    except Exception:
        result['status']='FAILED';result['error']=traceback.format_exc()
        save_json(out/'probe.json',result)
        raise
    save_json(out/'probe.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--threads',type=int,default=4)
    args=parser.parse_args()
    run_probe(args.root,args.output,args.threads)
