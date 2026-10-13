"""A bounded p=1 study of execution units and starts, with common (3,3) penalties."""

from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np

from .independent_campaign import canonical_hash, save_campaign, report_row as placement_report_row
from .ising import build_ising, scale_ising, scaled_qaoa_point
from .penalty_analysis import penalty_diagnostics
from .qaoa_experiment import experiment_environment, qubo_fingerprint, summarize_samples

SCOPE = "phase4c_hamiltonian_scaling"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def make_design(instance, bundle, seeds, base_config, raw_start, common_start=(0.3, 1.0)):
    _require(instance == bundle['instance'] and bundle['penalties'] == {'assignment':3.,'capacity':3.},
             "This study fixes the original input and common penalties (3,3).")
    _require(base_config.get('reps') == 1, "Probe scaling at p=1 before the depth study.")
    _require(bool(seeds) and len(set(seeds)) == len(seeds)
             and all(type(s) is int and s >= 0 for s in seeds), "Distinct integer seeds are required.")
    _require(not set(base_config) & {'seed','initial_point','hamiltonian_scaling'},
             "Seeds, starts and scaling are set by the arms, not the base config.")
    for name in ('shots','maxiter','max_qubits','aer_threads','aer_memory_mb'):
        _require(type(base_config.get(name)) is int and base_config[name] > 0, f"Invalid {name}.")
    for name in ('max_seconds','min_available_gib','cobyla_rhobeg'):
        value = base_config.get(name)
        _require(value is not None and not isinstance(value,(bool,np.bool_))
                 and np.isfinite(value) and value > 0, f"Invalid {name}.")
    raw, _ = build_ising(bundle)
    _, normalization = scale_ising(raw,'max_abs')
    raw_start = scaled_qaoa_point(raw_start,1,1)
    common_start = scaled_qaoa_point(common_start,1,1)
    return {
        'instance_id':instance['instance_id'], 'instance_sha256':canonical_hash(instance),
        'penalties':bundle['penalties'].copy(), 'model_version':bundle['model_version'],
        'qubo_sha256':qubo_fingerprint(bundle), 'normalization':normalization,
        'base_config':dict(base_config), 'seeds':list(seeds), 'environment':experiment_environment(),
        'arms': {
            'raw_original':{'hamiltonian_scaling':'none','initial_point':raw_start},
            'normalized_matched':{'hamiltonian_scaling':'max_abs',
                'initial_point':scaled_qaoa_point(raw_start,1,normalization['scale'])},
            'normalized_common':{'hamiltonian_scaling':'max_abs','initial_point':common_start},
        },
        'study': {'stage':'common_penalty_scaling_diagnostic','protocol_version':1,
            'primary_metric':'optimal_placement_probability', 'common_penalties':[3.,3.],
            'role':'exploratory_before_depth',
            'search_rule':'same_COBYLA_rhobeg_in_execution_coordinates',
            'output_rule':'measured_best_valid_with_frequency_ties_disclosed'},
    }


def make_trials(design):
    trials = []
    design_hash = canonical_hash(design)
    for arm_id, arm in design['arms'].items():
        for seed in design['seeds']:
            row = {'instance_id':design['instance_id'],'arm_id':arm_id,'pair_id':'common_P3',
                   'initial_point_id':arm_id,'seed':seed,
                   'config':{**design['base_config'],**arm,'seed':seed}}
            row['run_key'] = canonical_hash({'design_hash':design_hash,**row})
            trials.append(row)
    return trials


def new_campaign(design):
    return {'schema_version':1,'scope':SCOPE,
            'campaign_id':datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
            'design':design,'design_hash':canonical_hash(design),
            'planned_runs':make_trials(design),'completed_runs':[]}


def report_row(root, path, report, trial):
    return {**placement_report_row(root,path,report,trial),
            'arm_id':trial['arm_id'],'hamiltonian_scaling':report['hamiltonian_scaling']['method'],
            'execution_scale':report['hamiltonian_scaling']['scale'],
            'beta_initial':trial['config']['initial_point'][0],
            'gamma_initial':trial['config']['initial_point'][1],
            'gamma_initial_raw':trial['config']['initial_point'][1]/report['hamiltonian_scaling']['scale'],
            'beta_optimal':report['optimal_point'][0],'gamma_optimal':report['optimal_point'][1],
            'gamma_optimal_raw':report['optimal_point_raw_hamiltonian'][1]}


def verify_campaign(root, campaign, design, bundle, reference):
    """Verify only referenced reports, one at a time; never merge whole folders."""
    _require(campaign['scope']==SCOPE and campaign['schema_version']==1, "Use a notebook 10 manifest.")
    _require(campaign['design']==design and campaign['design_hash']==canonical_hash(design),
             "Design/input/code/runtime changed; start a new campaign.")
    _require(experiment_environment()==design['environment'], "Source/runtime changed during this campaign.")
    _require(canonical_hash(bundle['instance'])==design['instance_sha256']
             and qubo_fingerprint(bundle)==design['qubo_sha256'] and bundle['penalties']==design['penalties'],
             "Input or QUBO does not match the design.")
    planned=make_trials(design)
    _require(campaign['planned_runs']==planned, "Planned trials differ.")
    lookup={t['run_key']:t for t in planned}
    rows=campaign['completed_runs']
    keys=[r['run_key'] for r in rows]
    _require(len(keys)==len(set(keys)) and set(keys)<=set(lookup), "Duplicate or unplanned completed keys.")
    _require(campaign['planned_run_count']==len(planned) and campaign['completed_run_count']==len(rows)
             and campaign['remaining_run_keys']==[t['run_key'] for t in planned if t['run_key'] not in keys],
             "Manifest counts or remaining keys differ.")
    root=Path(root).resolve()
    raw,offset=build_ising(bundle)
    for row in rows:
        trial=lookup[row['run_key']]
        path=(root/row['report']).resolve()
        _require(path.is_relative_to(root), "Source report must stay inside the repository.")
        report=json.loads(path.read_text(encoding='utf-8'))
        expected={'campaign_id':campaign['campaign_id'],'design_hash':campaign['design_hash'],
                  'run_key':trial['run_key'],'arm_id':trial['arm_id'],'purpose':'common_penalty_scaling_diagnostic'}
        _require(report['scope']==SCOPE and report['status']=='completed' and report['schema_version']==3
                 and report['experiment']==expected and report['study']==design['study'], "Report identity differs.")
        _require(report['config']==trial['config'] and report['penalties']==design['penalties']
                 and report['penalty']==3 and report['penalty_mode']=='independent', "Configuration or penalties differ.")
        _require(report['instance']==bundle['instance'] and report['instance_id']==design['instance_id']
                 and report['instance_sha256']==design['instance_sha256'], "Input differs.")
        _require(report['environment']==design['environment']
                 and report['provenance']=={'model_version':bundle['model_version'],'qubo':qubo_fingerprint(bundle)}
                 and report['variable_names']==[v.name for v in bundle['qubo'].variables]
                 and report['reference']==reference and report['num_qubits']==raw.num_qubits
                 and report['ising_offset']==offset and report['pauli_terms']==len(raw), "Model/reference differs.")
        _,scaling=scale_ising(raw,trial['config']['hamiltonian_scaling'])
        _require(report['hamiltonian_scaling']==scaling and report['parameter_names']==['β[0]','γ[0]'],
                 "Hamiltonian scale or parameter order differs.")
        _require(np.allclose(report['optimal_point_raw_hamiltonian'],scaled_qaoa_point(report['optimal_point'],1,1/scaling['scale']),rtol=0,atol=1e-10),
                 "Gamma conversion differs.")
        history=report['optimization_history']
        _require(len(history)==report['cost_function_evals'] and len(history)<=trial['config']['maxiter']
                 and [h['evaluation'] for h in history]==list(range(1,len(history)+1))
                 and history[0]['parameters']==trial['config']['initial_point'], "Optimizer history differs.")
        _require(all(np.isclose(h['estimated_qubo_energy'],scaling['scale']*h['execution_hamiltonian_expectation']+offset,rtol=0,atol=1e-7) for h in history)
                 and np.isclose(report['optimizer_estimated_qubo_expectation'],scaling['scale']*report['optimizer_estimated_execution_expectation']+offset,rtol=0,atol=1e-7),
                 "Raw/execution energy conversion differs.")
        samples=report['final_samples']
        probs=np.array([s['probability'] for s in samples])
        shots=report['config']['shots']
        counts=np.rint(probs*shots)
        _require(len({tuple(s['bits']) for s in samples})==len(samples)==report['observed_final_bitstrings']
                 and (counts>0).all() and counts.sum()==shots and (probs[:-1]>=probs[1:]).all()
                 and np.allclose(probs,counts/shots,rtol=0,atol=1e-12), "Samples/counts differ.")
        _require(penalty_diagnostics(bundle,report)==report['penalty_analysis']
                 and summarize_samples(samples,reference)==report['metrics'], "Metrics differ from raw bits.")
        _require(report_row(root,path,report,trial)==row, "Manifest row differs from report.")
    return rows
