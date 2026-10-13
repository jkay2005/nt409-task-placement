"""Measured QAOA for the frozen branch-A benchmark; historical runners unchanged."""
from time import perf_counter
import traceback
import numpy as np
import psutil
from qiskit.circuit.library import QAOAAnsatz
from qiskit_optimization.minimum_eigensolvers import QAOA
from .ising import build_ising, scale_ising, decode_samples
from .penalty_analysis import penalty_diagnostics
from .qaoa_optimizer import RecordingCOBYLA
from .qaoa_experiment import (_validated_config, _new_report, _aer_components,
    _measure_final, _complete_report, _MemoryMonitor, _EvaluationTimeLimit,
    prepare_reference, distribution_statistics)


class ResourceStop(RuntimeError):
    pass


def memory_snapshot():
    return dict(available_gib=psutil.virtual_memory().available/2**30,
                rss_gib=psutil.Process().memory_info().rss/2**30)


class ResourceGuard:
    """Boundary monitoring, not an OS hard cap or a native-call interrupt."""
    def __init__(self, policy, snapshot=None):
        self.policy=policy
        self.snapshot=snapshot or memory_snapshot
        self.observations=[]

    def check(self, stage, start=False):
        value=dict(stage=stage,**self.snapshot())
        self.observations.append(value)
        minimum=self.policy['start_available_min_gib'] if start else self.policy['remaining_available_min_gib']
        if value['available_gib']<minimum or value['rss_gib']>self.policy['process_rss_stop_gib']:
            raise ResourceStop(f"{stage}: available={value['available_gib']:.3f} GiB, "
                               f"RSS={value['rss_gib']:.3f} GiB; resource policy exceeded.")
        return value

    def summary(self):
        return dict(policy=self.policy,measurement='evaluation_boundary_samples_not_native_allocation_peak',
            minimum_available_gib=min((x['available_gib'] for x in self.observations),default=None),
            maximum_observed_rss_gib=max((x['rss_gib'] for x in self.observations),default=None),
            observations=self.observations)


def select_output(samples, shots, optimum):
    """Use objective, frequency, then variable-order bits; never repair a bit."""
    valid=[s for s in samples if s['decoded']['feasible']]
    chosen=min(valid,key=lambda s:(s['decoded']['objective'],-s['probability'],tuple(s['bits']))) if valid else None
    highest=max(s['probability'] for s in samples)
    modes=sorted([s for s in samples if abs(s['probability']-highest)<1e-12],key=lambda s:s['bits'])
    return dict(rule='best_valid_no_bit_repair',selected=chosen,found_valid=chosen is not None,
        selected_objective=None if chosen is None else chosen['decoded']['objective'],
        optimality_gap=None if chosen is None or optimum is None else chosen['decoded']['objective']-optimum,
        found_optimal=None if optimum is None else bool(chosen and chosen['decoded']['objective']==optimum),
        mode_count=round(highest*shots),mode_tie_count=len(modes),
        mode_bits=[s['bits'] for s in modes],mode_valid_count=sum(s['decoded']['feasible'] for s in modes),
        unique_mode_valid=modes[0]['decoded']['feasible'] if len(modes)==1 else None)


def _failure(report, error, setup_done):
    if isinstance(error,ResourceStop):status='resource_stopped' if setup_done else 'resource_blocked'
    elif isinstance(error,_EvaluationTimeLimit):status='time_budget_exceeded'
    elif isinstance(error,KeyboardInterrupt):status='interrupted'
    elif isinstance(error,MemoryError):status='memory_error'
    else:status='error'
    report.update(status=status,stop_reason=str(error) or type(error).__name__,
                  error_type=type(error).__name__,traceback=traceback.format_exc(limit=12))
    # Partial diagnostic samples are not a completed experiment.
    report.pop('benchmark_output',None)


def run_trial(bundle, config, policy, reference=None, progress=True):
    """Return complete or failed evidence. The campaign persists either status."""
    whole_started=perf_counter();guard=ResourceGuard(policy);setup_done=False
    report=dict(config=dict(config),instance_id=bundle['instance']['instance_id'],
                optimization_history=[],final_samples=None,metrics=None)
    with _MemoryMonitor() as memory:
        try:
            guard.check('before_setup',start=True)
            config=_validated_config(bundle,config)
            reference=prepare_reference(bundle) if reference is None else reference
            raw,offset=build_ising(bundle);operator,scaling=scale_ising(raw,config['hamiltonian_scaling'])
            report=_new_report(bundle,config,reference,operator,offset,scaling)
            started=perf_counter();setup_done=True

            def boundary(stage):
                guard.check(stage)
                if perf_counter()-started>=config['max_seconds']:
                    raise _EvaluationTimeLimit(f'Time guard at {stage}.')

            def callback(count,parameters,value,metadata):
                value=float(np.real(value));elapsed=perf_counter()-started
                report['optimization_history'].append(dict(evaluation=int(count),parameters=np.asarray(parameters).tolist(),
                    estimated_qubo_energy=scaling['scale']*value+offset,
                    execution_hamiltonian_expectation=value,elapsed_seconds=elapsed,objective_source='sampled_mean'))
                if progress and (count==1 or count%10==0):
                    print(f"  eval {count}: E={scaling['scale']*value+offset:.6f}, {elapsed:.1f}s",flush=True)
                boundary('optimizer_evaluation')

            boundary('before_backend')
            _,sampler,manager,options=_aer_components(config)
            report['backend_options']=options
            optimizer=RecordingCOBYLA(config['maxiter'],config['cobyla_rhobeg'],config['cobyla_tol'])
            algorithm=QAOA(sampler=sampler,optimizer=optimizer,reps=config['reps'],
                initial_point=config['initial_point'],callback=callback,pass_manager=manager)
            result=algorithm.compute_minimum_eigenvalue(operator)
            report['optimization_seconds']=perf_counter()-started
            boundary('before_final_sampling');sample_started=perf_counter()
            distribution=_measure_final(bundle,config,operator,result.optimal_point,manager,options)
            report['evaluation_sampling_seconds']=perf_counter()-sample_started
            boundary('after_final_sampling')
            report['elapsed_seconds']=perf_counter()-started
            decoded_started=perf_counter()
            report['sampling_statistics']={'training':distribution_statistics(bundle,result.eigenstate,config['shots'],config['seed'])}
            names=[str(p) for p in algorithm.ansatz.parameters]
            expected=[f'β[{i}]' for i in range(config['reps'])]+[f'γ[{i}]' for i in range(config['reps'])]
            if names!=expected:raise ValueError('Unexpected QAOA parameter order.')
            _complete_report(report,bundle,raw,offset,scaling,result.optimal_point,
                float(np.real(result.eigenvalue)),distribution,optimizer,reference,names)
            report['benchmark_output']=select_output(report['final_samples'],config['evaluation_shots'],reference['original_best_objective'])
            report['postprocessing_seconds']=perf_counter()-decoded_started
            t=perf_counter();report['penalty_analysis']=penalty_diagnostics(bundle,report)
            report['penalty_analysis_seconds']=perf_counter()-t
            guard.check('after_postprocessing')
        except (Exception,KeyboardInterrupt) as error:
            _failure(report,error,setup_done)
    report.update(resources=memory.as_dict(),resource_guard=guard.summary(),
        total_seconds=perf_counter()-whole_started,cost_function_evals=len(report['optimization_history']))
    return report


def probe_depth(bundle, config, policy, reference=None):
    """Three nonzero active-layer circuits, fresh final sampling and decoding."""
    whole=perf_counter();guard=ResourceGuard(policy);setup_done=False
    report=dict(config=dict(config),instance_id=bundle['instance']['instance_id'])
    with _MemoryMonitor() as memory:
        try:
            guard.check('before_probe',start=True)
            config=_validated_config(bundle,config)
            reference=prepare_reference(bundle) if reference is None else reference
            raw,offset=build_ising(bundle);op,scaling=scale_ising(raw,config['hamiltonian_scaling'])
            _,sampler,manager,options=_aer_components(config)
            p=config['reps'];circuit=QAOAAnsatz(op,reps=p);names=[str(x) for x in circuit.parameters]
            if names!=[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)]:
                raise ValueError('Unexpected QAOA parameter order.')
            circuit.measure_all();compiled=manager.run(circuit)
            if compiled.layout is not None and compiled.layout.final_index_layout()!=list(range(raw.num_qubits)):
                raise ValueError('Nonidentity measurement layout.')
            setup_done=True;setup=perf_counter()-whole
            points=[[.31+.03*j+.02*i for i in range(p)]+[.9+.05*j+.07*i for i in range(p)] for j in range(3)]
            times=[]
            for point in points:
                guard.check('before_probe_evaluation');t=perf_counter()
                counts=sampler.run([(compiled,point)]).result()[0].data.meas.get_counts()
                if sum(counts.values())!=config['shots']:raise ValueError('Probe shot count differs.')
                distribution_statistics(bundle,{int(k,2):v/config['shots'] for k,v in counts.items()},config['shots'],config['seed'])
                times.append(perf_counter()-t);guard.check('after_probe_evaluation')
            t=perf_counter();distribution=_measure_final(bundle,config,op,points[-1],manager,options)
            final_seconds=perf_counter()-t;guard.check('after_probe_final')
            t=perf_counter();samples=decode_samples(bundle,distribution,raw,offset)
            output=select_output(samples,config['evaluation_shots'],reference['original_best_objective'])
            post_seconds=perf_counter()-t;guard.check('after_probe_decode')
            estimate=1.5*(setup+max(times)*config['maxiter']+final_seconds)
            report.update(status='passed' if estimate<=config['max_seconds'] else 'time_estimate_exceeds_budget',
                setup_seconds=setup,active_points=points,evaluation_seconds=times,final_sampling_seconds=final_seconds,
                postprocessing_seconds=post_seconds,estimated_solver_seconds=estimate,
                estimated_total_seconds=estimate+1.5*post_seconds,num_qubits=raw.num_qubits,
                compiled_depth=compiled.depth(),compiled_ops=dict(compiled.count_ops()),
                parameter_names=names,probe_final_output=output,
                stop_reason='Probe estimate includes a 1.5 safety factor; this is not a guaranteed runtime.')
        except (Exception,KeyboardInterrupt) as error:
            _failure(report,error,setup_done)
    report.update(resources=memory.as_dict(),resource_guard=guard.summary(),total_seconds=perf_counter()-whole)
    return report
