"""Measured compact QAOA with fresh final samples and audited decoding."""
from time import perf_counter
import numpy as np
import psutil
from qiskit.circuit.library import QAOAAnsatz
from qiskit.primitives import BaseSamplerV2
from qiskit.primitives.containers import SamplerPub
from qiskit_optimization.minimum_eigensolvers import QAOA
from .two_host_encoding import ENCODING, decode_compact
from .ising import build_ising, scale_ising, scaled_qaoa_point, integer_to_bits, ising_energy
from .qaoa_experiment import (_validated_config, _aer_components, _measure_final,
    _new_report, _MemoryMonitor, _EvaluationTimeLimit, summarize_samples,
    distribution_statistics, qubo_fingerprint)
from .qaoa_optimizer import RecordingCOBYLA, sampling_seeds
from .benchmark_a_runner import ResourceGuard, select_output, _failure


def memory_snapshot():
    # /proc/self on Linux also works when PID namespaces differ from procfs.
    rss,_=_MemoryMonitor()._memory_info()
    return dict(available_gib=psutil.virtual_memory().available/2**30,rss_gib=rss/2**30)


class CountedSampler(BaseSamplerV2):
    """Count submitted shots, including Qiskit's extra optimal-state sampling."""
    def __init__(self,sampler,default_shots):
        self.sampler=sampler;self.default_shots=default_shots;self.batches=[]

    def run(self,pubs,*,shots=None):
        pubs=[SamplerPub.coerce(p,shots if shots is not None else self.default_shots) for p in pubs]
        self.batches.append(sum(int(np.prod(p.shape))*p.shots for p in pubs))
        return self.sampler.run(pubs,shots=shots)


def decode_distribution(bundle,distribution,raw,offset):
    samples=[]
    for key,probability in distribution.items():
        bits=integer_to_bits(key,raw.num_qubits)
        energy=float(bundle['qubo'].objective.evaluate(bits))
        if not np.isclose(energy,ising_energy(raw,offset,bits),rtol=0,atol=1e-7):
            raise ValueError('Compact Ising energy/bit order differs.')
        samples.append(dict(bits=bits.tolist(),probability=float(probability),
            energy=energy,decoded=decode_compact(bundle,bits)))
    return sorted(samples,key=lambda s:s['probability'],reverse=True)


def run_compact_trial(bundle,config,policy,reference,progress=True):
    whole=perf_counter();guard=ResourceGuard(policy,snapshot=memory_snapshot);setup_done=False
    report=dict(config=dict(config),instance_id=bundle['instance']['instance_id'],
        encoding=ENCODING,optimization_history=[],final_samples=None,metrics=None)
    with _MemoryMonitor() as memory:
        try:
            guard.check('before_setup',start=True);config=_validated_config(bundle,config)
            raw,offset=build_ising(bundle);op,scaling=scale_ising(raw,config['hamiltonian_scaling'])
            report=_new_report(bundle,config,reference,op,offset,scaling)
            report.update(scope='phase4i_two_host_encoding',encoding=ENCODING)
            started=perf_counter();setup_done=True
            def boundary(stage):
                guard.check(stage)
                if perf_counter()-started>=config['max_seconds']:raise _EvaluationTimeLimit(f'Time guard at {stage}.')
            def callback(count,parameters,value,metadata):
                value=float(np.real(value));elapsed=perf_counter()-started
                report['optimization_history'].append(dict(evaluation=int(count),parameters=np.asarray(parameters).tolist(),
                    estimated_qubo_energy=scaling['scale']*value+offset,execution_hamiltonian_expectation=value,
                    elapsed_seconds=elapsed,objective_source='sampled_mean'))
                if progress and (count==1 or count%10==0):print(f'  eval {count}: E={scaling["scale"]*value+offset:.6f}, {elapsed:.1f}s',flush=True)
                boundary('optimizer_evaluation')
            boundary('before_backend');_,sampler,manager,options=_aer_components(config)
            sampler=CountedSampler(sampler,config['shots'])
            report['backend_options']=options
            optimizer=RecordingCOBYLA(config['maxiter'],config['cobyla_rhobeg'],config['cobyla_tol'])
            algorithm=QAOA(sampler=sampler,optimizer=optimizer,reps=config['reps'],
                initial_point=config['initial_point'],callback=callback,pass_manager=manager)
            result=algorithm.compute_minimum_eigenvalue(op)
            report['optimization_seconds']=perf_counter()-started
            boundary('before_final_sampling');t=perf_counter()
            distribution=_measure_final(bundle,config,op,result.optimal_point,manager,options)
            report['evaluation_sampling_seconds']=perf_counter()-t;boundary('after_final_sampling');t=perf_counter()
            samples=decode_distribution(bundle,distribution,raw,offset)
            names=[str(x) for x in algorithm.ansatz.parameters];p=config['reps']
            if names!=[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)]:raise ValueError('Parameter order differs.')
            if optimizer.stop['nfev']!=len(report['optimization_history']):raise ValueError('Evaluation count differs.')
            estimate=float(np.real(result.eigenvalue))
            report.update(status='completed',optimizer_stop=optimizer.stop.copy(),optimal_point=result.optimal_point.tolist(),
                optimal_point_raw_hamiltonian=scaled_qaoa_point(result.optimal_point,p,1/scaling['scale']),
                parameter_names=names,optimizer_estimated_execution_expectation=estimate,
                optimizer_estimated_qubo_expectation=scaling['scale']*estimate+offset,
                final_samples=samples,observed_final_bitstrings=len(samples),metrics=summarize_samples(samples,reference),
                algorithm_sampler_batches=sampler.batches,algorithm_sampler_shots=sum(sampler.batches),
                benchmark_output=select_output(samples,config['evaluation_shots'],reference['original_best_objective']),
                sampling_statistics=dict(training=distribution_statistics(bundle,result.eigenstate,config['shots'],config['seed']),
                    evaluation=distribution_statistics(bundle,distribution,config['evaluation_shots'],config['evaluation_seed'])))
            report['postprocessing_seconds']=perf_counter()-t;boundary('after_postprocessing')
        except (Exception,KeyboardInterrupt) as error:_failure(report,error,setup_done)
    nfev=len(report['optimization_history'])
    report.update(resources=memory.as_dict(),resource_guard=guard.summary(),total_seconds=perf_counter()-whole,
        cost_function_evals=nfev,total_algorithm_shots=(report['algorithm_sampler_shots']+config['evaluation_shots'])
        if report['status']=='completed' else None)
    return report


def probe_compact(bundle,config,policy,reference):
    whole=perf_counter();guard=ResourceGuard(policy,snapshot=memory_snapshot);setup_done=False
    report=dict(config=dict(config),instance_id=bundle['instance']['instance_id'],encoding=ENCODING)
    with _MemoryMonitor() as memory:
        try:
            guard.check('before_probe',start=True);config=_validated_config(bundle,config)
            raw,offset=build_ising(bundle);op,_=scale_ising(raw,config['hamiltonian_scaling'])
            _,sampler,manager,options=_aer_components(config);p=config['reps']
            circuit=QAOAAnsatz(op,reps=p)
            if [str(x) for x in circuit.parameters]!=[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)]:
                raise ValueError('Probe parameter order differs.')
            circuit.measure_all();compiled=manager.run(circuit)
            if compiled.layout is not None and compiled.layout.final_index_layout()!=list(range(raw.num_qubits)):
                raise ValueError('Probe measurement layout differs.')
            setup_done=True;setup=perf_counter()-whole;times=[]
            points=[[.31+.03*j+.02*i for i in range(p)]+[.9+.05*j+.07*i for i in range(p)] for j in range(3)]
            for point in points:
                guard.check('before_probe_evaluation');t=perf_counter()
                counts=sampler.run([(compiled,point)]).result()[0].data.meas.get_counts()
                if sum(counts.values())!=config['shots']:raise ValueError('Probe count differs.')
                times.append(perf_counter()-t);guard.check('after_probe_evaluation')
            t=perf_counter();distribution=_measure_final(bundle,config,op,points[-1],manager,options)
            final=perf_counter()-t;t=perf_counter();samples=decode_distribution(bundle,distribution,raw,offset)
            post=perf_counter()-t;guard.check('after_probe_decode')
            estimate=1.5*(setup+max(times)*config['maxiter']+final+post)
            report.update(status='passed' if estimate<=config['max_seconds'] else 'time_estimate_exceeds_budget',
                active_points=points,evaluation_seconds=times,setup_seconds=setup,final_sampling_seconds=final,
                postprocessing_seconds=post,estimated_solver_seconds=estimate,num_qubits=raw.num_qubits,
                compiled_depth=compiled.depth(),compiled_ops=dict(compiled.count_ops()),
                probe_final_output=select_output(samples,config['evaluation_shots'],reference['original_best_objective']))
        except (Exception,KeyboardInterrupt) as error:_failure(report,error,setup_done)
    report.update(resources=memory.as_dict(),resource_guard=guard.summary(),total_seconds=perf_counter()-whole)
    return report


def audit_compact_report(bundle,r,config,reference):
    def require(ok,message):
        if not ok:raise ValueError(message)
    raw,offset=build_ising(bundle);_,scaling=scale_ising(raw,config['hamiltonian_scaling']);p=config['reps']
    require(r['status']=='completed' and r['encoding']==ENCODING and r['config']==config
        and r['instance']==bundle['instance'] and r['reference']==reference,'Compact identity differs.')
    require(r['num_qubits']==raw.num_qubits and r['ising_offset']==offset and r['hamiltonian_scaling']==scaling
        and r['variable_names']==[v.name for v in bundle['qubo'].variables]
        and r['provenance']==dict(model_version=ENCODING,qubo=qubo_fingerprint(bundle)),'Compact QUBO metadata differs.')
    require(r['sampling']==sampling_seeds(config) and r['sampling_protocol']=='independent_final_v1','Sampling protocol differs.')
    require(r['parameter_names']==[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)],'Parameter order differs.')
    require(len(r['optimal_point'])==2*p and np.isfinite(r['optimal_point']).all()
        and np.allclose(r['optimal_point_raw_hamiltonian'],scaled_qaoa_point(r['optimal_point'],p,1/scaling['scale']),rtol=0,atol=1e-10),
        'Final angles differ.')
    history=r['optimization_history'];nfev=len(history);shots=config['evaluation_shots']
    require(0<nfev==r['cost_function_evals']==r['optimizer_stop']['nfev']<=config['maxiter']
        and history[0]['parameters']==config['initial_point']
        and [h['evaluation'] for h in history]==list(range(1,nfev+1)),'Optimizer count/initial point differs.')
    require(all(len(h['parameters'])==2*p and np.isfinite(h['parameters']).all()
        and h['objective_source']=='sampled_mean' and np.isclose(h['estimated_qubo_energy'],
        scaling['scale']*h['execution_hamiltonian_expectation']+offset,rtol=0,atol=1e-7) for h in history),'History energy differs.')
    require(len(r['algorithm_sampler_batches'])>=nfev and all(type(x) is int and x>0 for x in r['algorithm_sampler_batches'])
        and r['algorithm_sampler_shots']==sum(r['algorithm_sampler_batches'])
        and r['total_algorithm_shots']==r['algorithm_sampler_shots']+shots,'Shot accounting differs.')
    samples=r['final_samples'];prob=np.asarray([s['probability'] for s in samples]);counts=np.rint(prob*shots)
    bits=np.asarray([s['bits'] for s in samples])
    require(bits.shape==(len(samples),raw.num_qubits) and np.isin(bits,[0,1]).all()
        and len({tuple(x) for x in bits})==len(samples)==r['observed_final_bitstrings']
        and np.isfinite(prob).all() and (counts>0).all() and counts.sum()==shots
        and np.allclose(prob,counts/shots,rtol=0,atol=1e-12),'Final counts differ.')
    dist={sum(int(v)<<i for i,v in enumerate(s['bits'])):s['probability'] for s in samples}
    require(decode_distribution(bundle,dist,raw,offset)==samples,'Compact samples differ.')
    require(summarize_samples(samples,reference)==r['metrics']
        and select_output(samples,shots,reference['original_best_objective'])==r['benchmark_output'],'Compact metrics differ.')
    require(distribution_statistics(bundle,dist,shots,config['evaluation_seed'])==r['sampling_statistics']['evaluation'],
        'Final statistics differ.')
    require(np.isclose(r['optimizer_estimated_qubo_expectation'],scaling['scale']*r['optimizer_estimated_execution_expectation']+offset,
        rtol=0,atol=1e-7) and np.isclose(r['sampling_statistics']['training']['mean_qubo_energy'],
        r['optimizer_estimated_qubo_expectation'],rtol=0,atol=1e-7),'Optimizer energy differs.')
