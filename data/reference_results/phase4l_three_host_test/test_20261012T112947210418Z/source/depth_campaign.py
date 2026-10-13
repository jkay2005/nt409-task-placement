"""A paired p=1/p=2 experiment with common penalties and equal evaluation caps."""
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np

from .independent_campaign import canonical_hash, save_campaign, report_row as placement_report_row
from .ising import build_ising, scale_ising, scaled_qaoa_point
from .penalty_analysis import penalty_diagnostics
from .qaoa_experiment import experiment_environment, qubo_fingerprint, summarize_samples

SCOPE = 'phase4d_depth_comparison'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def embed_p1_start(point):
    """Append an identity layer, in Qiskit's beta-then-gamma parameter order."""
    _require(len(point)==2 and all(not isinstance(v,(bool,np.bool_)) for v in point)
             and np.isfinite(point).all(), 'Two finite p=1 angles are required.')
    return [float(point[0]),0.,float(point[1]),0.]


def make_design(instance, bundle, seeds, base_config, p1_start=(0.3,1.0)):
    _require(instance==bundle['instance'] and bundle['penalties']=={'assignment':3.,'capacity':3.},
             'The depth study fixes the input and common penalties (3,3).')
    _require(bool(seeds) and len(set(seeds))==len(seeds)
             and all(type(s) is int and s>=0 for s in seeds), 'Distinct nonnegative integer seeds required.')
    _require(not set(base_config)&{'seed','reps','initial_point'}
             and base_config.get('hamiltonian_scaling')=='max_abs', 'Depth/starts are set by the normalized arms.')
    for name in ('shots','maxiter','max_qubits','aer_threads','aer_memory_mb'):
        _require(type(base_config.get(name)) is int and base_config[name]>0, f'Invalid {name}.')
    _require(base_config['maxiter']>=6, 'p=2 COBYLA needs at least six function evaluations.')
    for name in ('max_seconds','min_available_gib','cobyla_rhobeg'):
        value=base_config.get(name)
        _require(value is not None and not isinstance(value,(bool,np.bool_))
                 and np.isfinite(value) and value>0, f'Invalid {name}.')
    embedded=embed_p1_start(p1_start)
    raw,_=build_ising(bundle)
    _,normalization=scale_ising(raw,'max_abs')
    return {'instance_id':instance['instance_id'],'instance_sha256':canonical_hash(instance),
        'penalties':bundle['penalties'].copy(),'model_version':bundle['model_version'],
        'qubo_sha256':qubo_fingerprint(bundle),'normalization':normalization,
        'base_config':dict(base_config),'seeds':list(seeds),'environment':experiment_environment(),
        'arms':{'p1_control':{'reps':1,'initial_point':[embedded[0],embedded[2]]},
                'p2_embedded':{'reps':2,'initial_point':embedded}},
        'study':{'stage':'matched_budget_depth_comparison','protocol_version':1,
            'primary_metric':'optimal_placement_probability','common_penalties':[3.,3.],
            'depths':[1,2],'role':'exploratory_depth_comparison',
            'initialization_rule':'fixed_p1_start_plus_zero_final_layer',
            'budget_rule':'same_max_function_evaluations_and_shots_per_trial',
            'output_rule':'measured_best_valid_with_frequency_ties_disclosed'}}


def make_trials(design):
    trials=[]
    design_hash=canonical_hash(design)
    for seed in design['seeds']:
        for arm_id,arm in design['arms'].items():
            row={'instance_id':design['instance_id'],'arm_id':arm_id,'pair_id':'common_P3',
                 'initial_point_id':arm_id,'seed':seed,'config':{**design['base_config'],**arm,'seed':seed}}
            row['run_key']=canonical_hash({'design_hash':design_hash,**row})
            trials.append(row)
    return trials


def new_campaign(design):
    return {'schema_version':1,'scope':SCOPE,
            'campaign_id':datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
            'design':design,'design_hash':canonical_hash(design),
            'planned_runs':make_trials(design),'completed_runs':[]}


def report_row(root, path, report, trial):
    return {**placement_report_row(root,path,report,trial),'arm_id':trial['arm_id'],
            'execution_scale':report['hamiltonian_scaling']['scale'],
            'parameter_names':report['parameter_names'],'initial_point':trial['config']['initial_point'],
            'optimal_point':report['optimal_point'],'optimal_point_raw_hamiltonian':report['optimal_point_raw_hamiltonian']}


def verify_campaign(root, campaign, design, bundle, reference):
    """Verify a manifest against its source reports before resuming or summarizing."""
    _require(campaign['scope']==SCOPE and campaign['schema_version']==1, 'Use a notebook 11 manifest.')
    _require(campaign['design']==design and campaign['design_hash']==canonical_hash(design)
             and experiment_environment()==design['environment'], 'Design/code/runtime changed; start a new campaign.')
    _require(canonical_hash(bundle['instance'])==design['instance_sha256']
             and qubo_fingerprint(bundle)==design['qubo_sha256'] and bundle['penalties']==design['penalties'],
             'Input or QUBO differs.')
    planned=make_trials(design)
    _require(campaign['planned_runs']==planned, 'Planned trials differ.')
    lookup={t['run_key']:t for t in planned}
    rows=campaign['completed_runs']
    keys=[r['run_key'] for r in rows]
    _require(len(keys)==len(set(keys)) and set(keys)<=set(lookup), 'Duplicate/unplanned completed trials.')
    _require(campaign['planned_run_count']==len(planned) and campaign['completed_run_count']==len(rows)
             and campaign['remaining_run_keys']==[t['run_key'] for t in planned if t['run_key'] not in keys],
             'Manifest counts differ.')
    root=Path(root).resolve()
    raw,offset=build_ising(bundle)
    _,scaling=scale_ising(raw,'max_abs')
    _require(scaling==design['normalization'], 'Design scale differs.')
    for row in rows:
        trial=lookup[row['run_key']]
        path=(root/row['report']).resolve()
        _require(path.is_relative_to(root), 'Report path must stay inside the repository.')
        report=json.loads(path.read_text(encoding='utf-8'))
        expected={'campaign_id':campaign['campaign_id'],'design_hash':campaign['design_hash'],
                  'run_key':trial['run_key'],'arm_id':trial['arm_id'],'purpose':'matched_budget_depth_comparison'}
        _require(report['scope']==SCOPE and report['status']=='completed' and report['schema_version']==3
                 and report['experiment']==expected and report['study']==design['study'], 'Report identity differs.')
        _require(report['config']==trial['config'] and report['penalties']==design['penalties']
                 and report['penalty']==3 and report['penalty_mode']=='independent', 'Budget/depth/penalties differ.')
        _require(report['instance']==bundle['instance'] and report['instance_id']==design['instance_id']
                 and report['instance_sha256']==design['instance_sha256'], 'Input differs.')
        _require(report['environment']==design['environment']
                 and report['provenance']=={'model_version':bundle['model_version'],'qubo':qubo_fingerprint(bundle)}
                 and report['variable_names']==[v.name for v in bundle['qubo'].variables]
                 and report['reference']==reference and report['num_qubits']==raw.num_qubits
                 and report['ising_offset']==offset and report['pauli_terms']==len(raw), 'Model/reference differs.')
        p=trial['config']['reps']
        names=[f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)]
        _require(report['hamiltonian_scaling']==scaling and report['parameter_names']==names,
                 'Scale or parameter order differs.')
        _require(len(report['optimal_point'])==2*p and np.isfinite(report['optimal_point']).all()
                 and np.allclose(report['optimal_point_raw_hamiltonian'],
                     scaled_qaoa_point(report['optimal_point'],p,1/scaling['scale']),rtol=0,atol=1e-10),
                 'Angle conversion differs.')
        history=report['optimization_history']
        _require(0<len(history)==report['cost_function_evals']<=trial['config']['maxiter']
                 and [h['evaluation'] for h in history]==list(range(1,len(history)+1))
                 and history[0]['parameters']==trial['config']['initial_point']
                 and all(len(h['parameters'])==2*p and np.isfinite(h['parameters']).all() for h in history),
                 'Optimizer history differs.')
        _require(all(np.isclose(h['estimated_qubo_energy'],scaling['scale']*h['execution_hamiltonian_expectation']+offset,
                               rtol=0,atol=1e-7) for h in history)
                 and np.isclose(report['optimizer_estimated_qubo_expectation'],
                     scaling['scale']*report['optimizer_estimated_execution_expectation']+offset,rtol=0,atol=1e-7),
                 'Energy units differ.')
        samples=report['final_samples']
        bits=np.array([s['bits'] for s in samples])
        probs=np.array([s['probability'] for s in samples])
        _require(bits.shape==(len(samples),raw.num_qubits) and np.isin(bits,[0,1]).all()
                 and np.isfinite(probs).all() and (probs>0).all(), 'Invalid sample bits/probabilities.')
        shots=trial['config']['shots']
        counts=np.rint(probs*shots)
        _require(len({tuple(b) for b in bits})==len(samples)==report['observed_final_bitstrings']
                 and counts.sum()==shots and (counts>0).all() and (probs[:-1]>=probs[1:]).all()
                 and np.allclose(probs,counts/shots,rtol=0,atol=1e-12), 'Samples/counts differ.')
        _require(penalty_diagnostics(bundle,report)==report['penalty_analysis']
                 and summarize_samples(samples,reference)==report['metrics'], 'Metrics differ from raw samples.')
        _require(report_row(root,path,report,trial)==row, 'Manifest row differs.')
    return rows
