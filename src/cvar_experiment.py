"""Exact lower-tail CVaR control; original QUBO and measured scoring unchanged."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter
import numpy as np

from .convergence_diagnostics import ExactQAOAOracle
from .convergence_campaign import make_design as diagnostic_design
from .independent_campaign import canonical_hash, save_campaign, report_row as placement_row
from .ising import build_ising, scaled_qaoa_point
from .penalty_analysis import penalty_diagnostics
from .qaoa_optimizer import RecordingCOBYLA, sampling_seeds
from .qaoa_experiment import (_validated_config, _new_report, _MemoryMonitor,
    _EvaluationTimeLimit, _measure_final, _complete_report, prepare_reference,
    experiment_environment, qubo_fingerprint, summarize_samples, distribution_statistics)

SCOPE = 'phase4f_exact_cvar'
METHOD = 'QAOA_AerExactCVaR_CPU_statevector_COBYLA'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _alpha(alpha):
    _require(not isinstance(alpha, (bool, np.bool_)) and np.isfinite(alpha) and 0 < alpha <= 1,
             'CVaR alpha must be finite and in (0,1].')
    return float(alpha)


def lower_tail_cvar(energies, probabilities, alpha):
    """Average the lowest alpha probability mass, splitting the boundary atom.

    Zero-mass states and ties are allowed. Near-unit normalization drift is
    removed; invalid distributions are rejected rather than silently repaired.
    """
    alpha = _alpha(alpha)
    e, p = np.asarray(energies, dtype=float), np.asarray(probabilities, dtype=float)
    _require(e.ndim == p.ndim == 1 and e.shape == p.shape and e.size > 0
             and np.isfinite(e).all() and np.isfinite(p).all() and (p >= 0).all()
             and np.isclose(p.sum(), 1., atol=1e-9, rtol=0), 'Invalid energy distribution.')
    order = np.argsort(e, kind='stable')
    e, p = e[order], p[order] / p.sum()
    mass_before = np.cumsum(p) - p
    weights = np.minimum(p, np.maximum(0., alpha - mass_before))
    _require(np.isclose(weights.sum(), alpha, atol=1e-10, rtol=0), 'CVaR tail mass differs.')
    return float(weights @ e / alpha)


class ExactCVaROracle(ExactQAOAOracle):
    """Reuse the existing circuit/diagonal; aggregate equal energies once."""

    def __init__(self, bundle, config, reference=None):
        super().__init__(bundle, config, reference)
        self.levels, self.level_index = np.unique(self.energies, return_inverse=True)
        self._cvar_cache = {}

    def cvar(self, point, alpha):
        alpha = _alpha(alpha)
        point = np.asarray(point, dtype=float)
        _require(point.shape == (2*self.config['reps'],) and np.isfinite(point).all(),
                 'Invalid QAOA angles.')
        # Exact alpha=1 control preserves the old mean evaluator's arithmetic.
        if alpha == 1.:
            return self.evaluate(point)['exact_mean_qubo_energy']
        key = (alpha, *point)
        if key not in self._cvar_cache:
            result = self.backend.run(self.circuit.assign_parameters(point), shots=1).result()
            _require(result.success, 'Aer exact CVaR evaluation failed.')
            p = np.asarray(result.data(0)['probabilities'], dtype=float)
            _require(p.shape == self.energies.shape, 'Probability register differs.')
            mass = np.bincount(self.level_index, weights=p, minlength=len(self.levels))
            self._cvar_cache[key] = lower_tail_cvar(self.levels, mass, alpha)
        return self._cvar_cache[key]


def run_cvar_qaoa(bundle, config, alpha=.1, reference=None, oracle=None, progress=True):
    alpha = _alpha(alpha)
    config = _validated_config(bundle, config)
    reference = prepare_reference(bundle) if reference is None else reference
    started = perf_counter()
    oracle = ExactCVaROracle(bundle, config, reference) if oracle is None else oracle
    oracle.check_compatible(bundle, config, reference)
    raw, offset = build_ising(bundle)
    scale = oracle.scaling['scale']
    report = _new_report(bundle, config, reference, oracle.operator, offset, oracle.scaling)
    report.update(method=METHOD, scope=SCOPE,
        objective={'kind':'lower_tail_cvar', 'alpha':alpha, 'source':'ideal_statevector',
                   'boundary_rule':'fractional_probability_mass'},
        implementation_sha256=implementation_hash(), backend_options=oracle.options.copy())
    optimizer = RecordingCOBYLA(config['maxiter'], config.get('cobyla_rhobeg',1.), config.get('cobyla_tol',1e-4))

    def objective(point):
        if perf_counter()-started >= config['max_seconds']:
            raise _EvaluationTimeLimit('Time guard before CVaR evaluation.')
        value = oracle.cvar(point, alpha)
        executed = (value-offset)/scale
        entry = dict(evaluation=len(report['optimization_history'])+1,
            parameters=np.asarray(point).tolist(), cvar_qubo_energy=value,
            cvar_execution_energy=executed, objective_source='ideal_statevector_cvar',
            elapsed_seconds=perf_counter()-started)
        report['optimization_history'].append(entry)
        if progress and (entry['evaluation']==1 or entry['evaluation']%10==0):
            print(f"  CVaR evaluation {entry['evaluation']}: value={value:.8f}, elapsed={entry['elapsed_seconds']:.1f}s", flush=True)
        if entry['elapsed_seconds'] >= config['max_seconds']:
            raise _EvaluationTimeLimit('Time guard after CVaR evaluation.')
        return executed

    try:
        with _MemoryMonitor() as memory:
            result = optimizer(objective, config['initial_point'])
            report['optimization_seconds'] = perf_counter()-started
            audit_started = perf_counter()
            exact = oracle.evaluate(result.x)
            final_cvar = oracle.cvar(result.x, alpha)
            report['exact_audit_seconds'] = perf_counter()-audit_started
            sample_started = perf_counter()
            distribution = _measure_final(bundle, config, oracle.operator, result.x, oracle.manager, oracle.options)
            report['evaluation_sampling_seconds'] = perf_counter()-sample_started
            if perf_counter()-started >= config['max_seconds']:
                raise _EvaluationTimeLimit('Time guard after CVaR evaluation sampling.')
    except _EvaluationTimeLimit:
        report.update(status='time_budget_exceeded', elapsed_seconds=perf_counter()-started,
                      cost_function_evals=len(report['optimization_history']), resources=memory.as_dict())
        return report
    report.update(elapsed_seconds=perf_counter()-started, resources=memory.as_dict(), exact_diagnostics=exact)
    decode_started = perf_counter()
    # Reuse measured-sample decoding; pass the actual mean, never label CVaR as mean.
    _complete_report(report, bundle, raw, offset, oracle.scaling, result.x,
        (exact['exact_mean_qubo_energy']-offset)/scale, distribution, optimizer, reference, oracle.parameter_names)
    report.pop('optimizer_estimated_qubo_expectation')
    report.pop('optimizer_estimated_execution_expectation', None)
    report.update(optimizer_objective_value=final_cvar,
                  optimizer_objective_execution_value=float(result.fun),
                  postprocessing_seconds=perf_counter()-decode_started)
    report['penalty_analysis'] = penalty_diagnostics(bundle, report)
    report['penalty_analysis_seconds'] = perf_counter()-decode_started-report['postprocessing_seconds']
    return report


def implementation_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def make_design(instance, bundle, base_config, starts, seed, alpha, baseline):
    alpha = _alpha(alpha)
    design = diagnostic_design(instance, bundle, [seed], base_config, starts, objective_modes=('exact',))
    design['objective'] = {'kind':'lower_tail_cvar', 'alpha':alpha, 'source':'ideal_statevector',
                           'boundary_rule':'fractional_probability_mass'}
    design['implementation_sha256'] = implementation_hash()
    design['study'].update(stage='exact_mean_vs_cvar', baseline=baseline,
        primary_diagnostic='ideal_optimal_placement_probability_with_mean_and_cvar_reported_separately',
        budget_rule='same_original_starts_max_evaluations_and_final_shots')
    return design


def make_trials(design):
    trials=[]
    for start, point in design['starts'].items():
        config={**design['base_config'], 'seed':design['seeds'][0], 'reps':1, 'initial_point':list(point)}
        config['evaluation_seed']=sampling_seeds(config)['evaluation_seed']
        t=dict(instance_id=design['instance_id'], pair_id='common_P3', initial_point_id=start,
               objective_mode='exact_cvar', arm_id=f'cvar_{start}', seed=config['seed'], config=config)
        t['run_key']=canonical_hash({'design_hash':canonical_hash(design), **t})
        trials.append(t)
    return trials


def new_campaign(design):
    return dict(schema_version=1, scope=SCOPE,
        campaign_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
        design=design, design_hash=canonical_hash(design), planned_runs=make_trials(design), completed_runs=[])


def _validate_report(r, trial, design, bundle, reference):
    _require(r.get('status')=='completed' and r.get('method')==METHOD and r.get('scope')==SCOPE
             and r.get('objective')==design['objective'], 'Report method/objective differs.')
    _require(r['config']==trial['config'] and r['environment']==design['environment']
             and r['implementation_sha256']==design['implementation_sha256'], 'Configuration/implementation differs.')
    _require(r['instance']==bundle['instance'] and r['reference']==reference
             and r['penalties']==design['penalties'] and r['penalty_mode']=='independent'
             and r['provenance']=={'model_version':bundle['model_version'],'qubo':qubo_fingerprint(bundle)}
             and r['variable_names']==[v.name for v in bundle['qubo'].variables], 'Model/reference differs.')
    raw, offset = build_ising(bundle)
    _require(r['hamiltonian_scaling']==design['normalization'] and r['ising_offset']==offset
             and r['num_qubits']==raw.num_qubits and r['parameter_names']==['β[0]','γ[0]'], 'Execution model differs.')
    _require(len(r['optimal_point'])==2 and np.isfinite(r['optimal_point']).all()
             and np.allclose(r['optimal_point_raw_hamiltonian'],
                 scaled_qaoa_point(r['optimal_point'],1,1/design['normalization']['scale']),atol=1e-10,rtol=0),
             'Final angles differ.')
    h, stop = r['optimization_history'], r['optimizer_stop']
    _require(0<len(h)==r['cost_function_evals']==stop['nfev']<=trial['config']['maxiter']
             and isinstance(stop['success'],bool) and type(stop['status']) is int and bool(stop['message'])
             and h[0]['parameters']==trial['config']['initial_point']
             and [x['evaluation'] for x in h]==list(range(1,len(h)+1)), 'Optimizer history differs.')
    scale=design['normalization']['scale']
    _require(all(x['objective_source']=='ideal_statevector_cvar' and len(x['parameters'])==2
             and np.isfinite(x['parameters']).all() and np.isclose(x['cvar_qubo_energy'],
                scale*x['cvar_execution_energy']+offset,atol=1e-7,rtol=0) for x in h), 'CVaR history units differ.')
    value=r['optimizer_objective_value'];exact=r['exact_diagnostics']
    _require(np.isfinite(value) and reference['minimum_energy']-1e-7<=value<=exact['exact_mean_qubo_energy']+1e-7
             and np.isclose(value,scale*r['optimizer_objective_execution_value']+offset,atol=1e-7,rtol=0)
             and any(np.allclose(x['parameters'],r['optimal_point'],atol=1e-12,rtol=0)
                and np.isclose(x['cvar_qubo_energy'],value,atol=1e-7,rtol=0) for x in h)
             and 'optimizer_estimated_qubo_expectation' not in r, 'CVaR confused with mean or selected point differs.')
    _require(all(np.isfinite(exact[k]) and 0<=exact[k]<=1+1e-9 for k in
        ('exact_feasible_probability','exact_optimal_probability','exact_ground_probability','exact_onehot_probability')),
        'Invalid ideal probabilities.')
    _require(exact['exact_optimal_probability']<=exact['exact_feasible_probability']+1e-9
             and np.isfinite(exact['exact_mean_qubo_energy']), 'Invalid ideal mean/placement probabilities.')
    _require(r['sampling']==sampling_seeds(trial['config']) and r['sampling_protocol']=='independent_final_v1',
             'Final sampling differs.')
    samples=r['final_samples'];shots=r['sampling']['evaluation_shots']
    bits=np.array([s['bits'] for s in samples]);p=np.array([s['probability'] for s in samples]);counts=np.rint(p*shots)
    _require(bits.shape==(len(samples),raw.num_qubits) and np.isin(bits,[0,1]).all()
             and len({tuple(v) for v in bits})==len(samples)==r['observed_final_bitstrings']
             and np.isfinite(p).all() and (counts>0).all() and counts.sum()==shots
             and np.allclose(p,counts/shots,atol=1e-12,rtol=0), 'Measured bits/counts differ.')
    _require(penalty_diagnostics(bundle,r)==r['penalty_analysis'] and summarize_samples(samples,reference)==r['metrics'],
             'Measured metrics differ.')
    distribution={sum(int(v)<<k for k,v in enumerate(s['bits'])):s['probability'] for s in samples}
    _require(distribution_statistics(bundle,distribution,shots,r['sampling']['evaluation_seed'])==r['sampling_statistics']['evaluation'],
             'Measured statistics differ.')


def report_row(root, path, report, trial):
    return {**placement_row(root,path,report,trial), 'arm_id':trial['arm_id'], 'objective_mode':'exact_cvar',
        'alpha':report['objective']['alpha'], 'optimizer_objective_value':report['optimizer_objective_value'],
        **report['exact_diagnostics'], 'optimizer_stop':report['optimizer_stop'],
        'optimal_point':report['optimal_point'], 'sampling':report['sampling'],
        'report_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def record_trial(root, campaign, trial, report, bundle, reference):
    _require(trial in campaign['planned_runs'] and trial['run_key'] not in {r['run_key'] for r in campaign['completed_runs']},
             'Unplanned or already completed trial.')
    _validate_report(report,trial,campaign['design'],bundle,reference)
    report['experiment']={k:campaign[k] for k in ('campaign_id','design_hash')}
    report['experiment'].update(run_key=trial['run_key'],arm_id=trial['arm_id'])
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path=Path(root)/'data/reference_results/phase4f_cvar_runs'/f"{trial['instance_id']}_{trial['arm_id']}_{stamp}.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    campaign['completed_runs'].append(report_row(root,path,report,trial))
    return path


def verify_campaign(root, campaign, design, bundle, reference):
    _require(campaign['scope']==SCOPE and campaign['schema_version']==1
             and campaign['design']==design and campaign['design_hash']==canonical_hash(design), 'CVaR design differs.')
    _require(design['environment']==experiment_environment() and design['implementation_sha256']==implementation_hash(),
             'Runtime/code changed; start a new campaign.')
    _require(design['instance_sha256']==canonical_hash(bundle['instance']) and design['qubo_sha256']==qubo_fingerprint(bundle),
             'Input/QUBO differs.')
    planned=make_trials(design);rows=campaign['completed_runs'];keys=[r['run_key'] for r in rows]
    _require(campaign['planned_runs']==planned and len(keys)==len(set(keys))
             and set(keys)<={t['run_key'] for t in planned}, 'Planned/completed trials differ.')
    _require(campaign['planned_run_count']==len(planned) and campaign['completed_run_count']==len(rows)
             and campaign['remaining_run_keys']==[t['run_key'] for t in planned if t['run_key'] not in keys], 'Counts differ.')
    root=Path(root).resolve();lookup={t['run_key']:t for t in planned}
    for row in rows:
        path=(root/row['report']).resolve()
        _require(path.is_relative_to(root), 'Report must stay inside repository.')
        r=json.loads(path.read_text(encoding='utf-8'));trial=lookup[row['run_key']]
        _require(r['experiment']==dict(campaign_id=campaign['campaign_id'],design_hash=campaign['design_hash'],
                   run_key=trial['run_key'],arm_id=trial['arm_id']), 'Report identity differs.')
        _validate_report(r,trial,design,bundle,reference)
        _require(report_row(root,path,r,trial)==row, 'Report digest or manifest row differs.')
    return rows
