"""Measured three-host QAOA with invalid-label accounting and fresh final shots."""
from time import perf_counter
import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit_optimization.minimum_eigensolvers import QAOA
from .three_host_encoding import ENCODING,decode_three_host
from .ising import build_ising,scale_ising,integer_to_bits,scaled_qaoa_point
from .qaoa_experiment import (_validated_config,_aer_components,_measure_final,_new_report,
    _MemoryMonitor,_EvaluationTimeLimit,summarize_samples,distribution_statistics,qubo_fingerprint)
from .qaoa_optimizer import RecordingCOBYLA,sampling_seeds
from .benchmark_a_runner import ResourceGuard,select_output,_failure
from .two_host_runner import CountedSampler,memory_snapshot


def decode_distribution(bundle,distribution,raw,offset):
    if not distribution:raise ValueError('Empty final distribution.')
    keys=list(distribution);bits=np.asarray([integer_to_bits(k,raw.num_qubits) for k in keys]);z=1-2*bits
    objective=bundle['qubo'].objective
    energy=objective.constant+bits@objective.linear.to_array()+np.sum((bits@objective.quadratic.to_array())*bits,axis=1)
    check=np.full(len(bits),offset,dtype=float)
    for label,coefficient in raw.to_list():
        if set(label)-{'I','Z'}:raise ValueError('Non-diagonal cost.')
        indices=[i for i in range(raw.num_qubits) if label[-1-i]=='Z']
        check+=float(np.real(coefficient))*np.prod(z[:,indices],axis=1)
    if not np.allclose(energy,check,rtol=0,atol=1e-7):raise ValueError('Ising energy or bit order differs.')
    samples=[dict(bits=b.tolist(),probability=float(distribution[k]),energy=float(e),
        decoded=decode_three_host(bundle,b)) for k,b,e in zip(keys,bits,energy)]
    return sorted(samples,key=lambda s:s['probability'],reverse=True)


def sample_metrics(samples,reference):
    m=summarize_samples(samples,reference);p=m['optimal_placement_probability'];f=m['feasible_probability']
    u=reference['uniform_baseline'];r=reference['structured_random']
    return {**m,'invalid_domain_probability':sum(s['probability'] for s in samples if not s['decoded']['domain_valid']),
        'optimal_lift_encoded':p/u['optimal_placement_probability'] if p is not None and u['optimal_placement_probability'] else None,
        'optimal_lift_structured_random':p/r['optimal_probability'] if p is not None and r['optimal_probability'] else None,
        'feasible_lift_encoded':f/u['feasible_probability'] if u['feasible_probability'] else None}


def _counts(distribution,qubits,shots):
    return {format(int(sum(int(x)<<i for i,x in enumerate(integer_to_bits(k,qubits)))),f'0{qubits}b'):
            round(float(p)*shots) for k,p in distribution.items()}


def run_three_host_trial(bundle,config,policy,reference,progress=True):
    whole=perf_counter();guard=ResourceGuard(policy,snapshot=memory_snapshot);setup_done=False
    report=dict(config=dict(config),instance_id=bundle['instance']['instance_id'],encoding=ENCODING,
        optimization_history=[],final_samples=None,metrics=None)
    with _MemoryMonitor() as memory:
        try:
            guard.check('before_setup',start=True);config=_validated_config(bundle,config)
            raw,offset=build_ising(bundle);op,scaling=scale_ising(raw,config['hamiltonian_scaling'])
            report=_new_report(bundle,config,reference,op,offset,scaling)
            report.update(scope='phase4k_three_host_pilot_v2',encoding=ENCODING)
            setup_done=True
            def boundary(stage):
                guard.check(stage)
                if perf_counter()-whole>=config['max_seconds']:raise _EvaluationTimeLimit(f'Time guard at {stage}.')
            def callback(count,parameters,value,metadata):
                value=float(np.real(value));elapsed=perf_counter()-whole
                report['optimization_history'].append(dict(evaluation=int(count),parameters=np.asarray(parameters).tolist(),
                    estimated_qubo_energy=scaling['scale']*value+offset,execution_hamiltonian_expectation=value,
                    elapsed_seconds=elapsed,objective_source='sampled_mean'))
                if progress and (count==1 or count%10==0):print(f'  eval {count}: E={scaling["scale"]*value+offset:.6f}, {elapsed:.1f}s',flush=True)
                boundary('optimizer_evaluation')
            boundary('before_backend');t=perf_counter();_,sampler,manager,options=_aer_components(config)
            sampler=CountedSampler(sampler,config['shots']);report['backend_options']=options
            report['algorithm_sampler_batches']=sampler.batches
            optimizer=RecordingCOBYLA(config['maxiter'],config['cobyla_rhobeg'],config['cobyla_tol'])
            algorithm=QAOA(sampler=sampler,optimizer=optimizer,reps=config['reps'],
                initial_point=config['initial_point'],callback=callback,pass_manager=manager)
            result=algorithm.compute_minimum_eigenvalue(op);report['optimization_seconds']=perf_counter()-t
            boundary('before_final_sampling');t=perf_counter()
            distribution=_measure_final(bundle,config,op,result.optimal_point,manager,options)
            report['evaluation_sampling_seconds']=perf_counter()-t;boundary('after_final_sampling');t=perf_counter()
            samples=decode_distribution(bundle,distribution,raw,offset);p=config['reps'];names=[str(x) for x in algorithm.ansatz.parameters]
            if names!=[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)]:raise ValueError('Parameter order differs.')
            if optimizer.stop['nfev']!=len(report['optimization_history']):raise ValueError('Evaluation count differs.')
            estimate=float(np.real(result.eigenvalue))
            report.update(status='completed',optimizer_stop=optimizer.stop.copy(),optimal_point=result.optimal_point.tolist(),
                optimal_point_raw_hamiltonian=scaled_qaoa_point(result.optimal_point,p,1/scaling['scale']),parameter_names=names,
                optimizer_estimated_execution_expectation=estimate,optimizer_estimated_qubo_expectation=scaling['scale']*estimate+offset,
                final_counts=_counts(distribution,raw.num_qubits,config['evaluation_shots']),final_samples=samples,
                observed_final_bitstrings=len(samples),metrics=sample_metrics(samples,reference),
                algorithm_sampler_batches=sampler.batches,algorithm_sampler_shots=sum(sampler.batches),
                benchmark_output=select_output(samples,config['evaluation_shots'],reference['original_best_objective']),
                sampling_statistics=dict(training=distribution_statistics(bundle,result.eigenstate,config['shots'],config['seed']),
                    evaluation=distribution_statistics(bundle,distribution,config['evaluation_shots'],config['evaluation_seed'])))
            report['postprocessing_seconds']=perf_counter()-t;boundary('after_postprocessing')
        except (Exception,KeyboardInterrupt) as error:_failure(report,error,setup_done)
    report['algorithm_sampler_shots']=sum(report.get('algorithm_sampler_batches',[]))
    report.update(resources=memory.as_dict(),resource_guard=guard.summary(),total_seconds=perf_counter()-whole,
        cost_function_evals=len(report['optimization_history']),
        total_algorithm_shots=(report['algorithm_sampler_shots']+config['evaluation_shots']) if report['status']=='completed' else None)
    return report


def probe_three_host(bundle,config,policy,reference):
    whole=perf_counter();guard=ResourceGuard(policy,snapshot=memory_snapshot);setup_done=False
    report=dict(config=dict(config),instance_id=bundle['instance']['instance_id'],encoding=ENCODING)
    with _MemoryMonitor() as memory:
        try:
            guard.check('before_probe',start=True);config=_validated_config(bundle,config)
            raw,offset=build_ising(bundle);op,_=scale_ising(raw,config['hamiltonian_scaling'])
            _,sampler,manager,options=_aer_components(config);p=config['reps'];circuit=QAOAAnsatz(op,reps=p)
            if [str(x) for x in circuit.parameters]!=[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)]:raise ValueError('Probe parameter order differs.')
            circuit.measure_all();compiled=manager.run(circuit)
            if compiled.layout is not None and compiled.layout.final_index_layout()!=list(range(raw.num_qubits)):raise ValueError('Probe layout differs.')
            setup_done=True;setup=perf_counter()-whole;times=[]
            points=[[.31+.03*j+.02*i for i in range(p)]+[.9+.05*j+.07*i for i in range(p)] for j in range(3)]
            def boundary(stage):
                guard.check(stage)
                if perf_counter()-whole>=config['max_seconds']:raise _EvaluationTimeLimit(f'Probe time guard at {stage}.')
            for point in points:
                boundary('before_probe_evaluation');t=perf_counter()
                counts=sampler.run([(compiled,point)]).result()[0].data.meas.get_counts()
                if sum(counts.values())!=config['shots']:raise ValueError('Probe shot count differs.')
                times.append(perf_counter()-t);boundary('after_probe_evaluation')
            t=perf_counter();distribution=_measure_final(bundle,config,op,points[-1],manager,options)
            final=perf_counter()-t;boundary('after_probe_final');t=perf_counter()
            samples=decode_distribution(bundle,distribution,raw,offset);post=perf_counter()-t;boundary('after_probe_decode')
            estimate=1.5*(setup+max(times)*(config['maxiter']+1)+final+post)
            report.update(status='passed',active_points=points,evaluation_seconds=times,setup_seconds=setup,
                final_sampling_seconds=final,postprocessing_seconds=post,maxiter_seconds_estimate=estimate,
                estimate_within_per_trial_limit=estimate<=config['max_seconds'],num_qubits=raw.num_qubits,
                compiled_depth=compiled.depth(),compiled_ops=dict(compiled.count_ops()),
                probe_final_counts=_counts(distribution,raw.num_qubits,config['evaluation_shots']),
                probe_final_output=select_output(samples,config['evaluation_shots'],reference['original_best_objective']),
                note='Passed means executed probe passed resource checks; maxiter projection is not a whole-trial guarantee.')
        except (Exception,KeyboardInterrupt) as error:_failure(report,error,setup_done)
    report.update(resources=memory.as_dict(),resource_guard=guard.summary(),total_seconds=perf_counter()-whole)
    return report


def audit_three_host_report(bundle,r,config,reference):
    def require(ok,message):
        if not ok:raise ValueError(message)
    raw,offset=build_ising(bundle);_,scaling=scale_ising(raw,config['hamiltonian_scaling']);p=config['reps']
    require(r['status']=='completed' and r['encoding']==ENCODING and r['config']==config and
        r['instance']==bundle['instance'] and r['reference']==reference,'Three-host identity differs.')
    require(r['num_qubits']==raw.num_qubits and r['ising_offset']==offset and r['hamiltonian_scaling']==scaling and
        r['provenance']==dict(model_version=ENCODING,qubo=qubo_fingerprint(bundle)) and
        r['variable_names']==[v.name for v in bundle['qubo'].variables],'QUBO metadata differs.')
    require(r['sampling']==sampling_seeds(config) and r['sampling_protocol']=='independent_final_v1','Sampling differs.')
    require(r['parameter_names']==[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)],'Parameters differ.')
    require(len(r['optimal_point'])==2*p and np.isfinite(r['optimal_point']).all() and
        np.allclose(r['optimal_point_raw_hamiltonian'],scaled_qaoa_point(r['optimal_point'],p,1/scaling['scale']),rtol=0,atol=1e-10),'Angles differ.')
    h=r['optimization_history'];nfev=len(h);shots=config['evaluation_shots']
    require(0<nfev==r['optimizer_stop']['nfev']==r['cost_function_evals']<=config['maxiter'] and
        h[0]['parameters']==config['initial_point'] and [x['evaluation'] for x in h]==list(range(1,nfev+1)),'Optimizer history differs.')
    require(all(len(x['parameters'])==2*p and np.isfinite(x['parameters']).all() and x['objective_source']=='sampled_mean' and
        np.isclose(x['estimated_qubo_energy'],scaling['scale']*x['execution_hamiltonian_expectation']+offset,rtol=0,atol=1e-7) for x in h),'History energy differs.')
    counts=r['final_counts'];require(counts and all(len(k)==raw.num_qubits and set(k)<={'0','1'} and type(v) is int and v>0 for k,v in counts.items()) and sum(counts.values())==shots,'Counts differ.')
    distribution={k:v/shots for k,v in counts.items()};samples=decode_distribution(bundle,distribution,raw,offset)
    require(samples==r['final_samples'] and len(samples)==r['observed_final_bitstrings'],'Decoded samples differ.')
    require(sample_metrics(samples,reference)==r['metrics'] and select_output(samples,shots,reference['original_best_objective'])==r['benchmark_output'],'Metrics differ.')
    require(distribution_statistics(bundle,distribution,shots,config['evaluation_seed'])==r['sampling_statistics']['evaluation'],'Evaluation statistics differ.')
    batches=r['algorithm_sampler_batches']
    require(len(batches)>=nfev+1 and all(type(b) is int and b>0 for b in batches) and
        sum(batches)==r['algorithm_sampler_shots'] and r['total_algorithm_shots']==sum(batches)+shots,'Shot accounting differs.')
    require(np.isclose(r['optimizer_estimated_qubo_expectation'],scaling['scale']*r['optimizer_estimated_execution_expectation']+offset,rtol=0,atol=1e-7) and
        np.isclose(r['sampling_statistics']['training']['mean_qubo_energy'],r['optimizer_estimated_qubo_expectation'],rtol=0,atol=1e-7),'Training energy differs.')
    require(all(np.isfinite(r[k]) and r[k]>=0 for k in ['total_seconds','optimization_seconds','evaluation_sampling_seconds','postprocessing_seconds']),'Timing differs.')
