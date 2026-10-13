"""Append-only development pilot; test instances are never submitted to QAOA."""
from datetime import datetime,timezone
from functools import lru_cache
from pathlib import Path
from statistics import median
from time import perf_counter
import csv,json,zipfile
import numpy as np
from .benchmark_a_campaign import (save_json,_read,_inside,_digest,_require,_lock,start_attempt,
    _config,result_rows as legacy_rows,TERMINAL)
from .independent_campaign import canonical_hash
from .qaoa_experiment import experiment_environment
from .three_host_encoding import build_three_host_qubo,three_host_reference,certify_three_host
from .three_host_runner import run_three_host_trial,probe_three_host,audit_three_host_report,decode_distribution
from .ising import build_ising
from .benchmark_a_runner import select_output
from .three_host_benchmark import required_lift
from .branch_a_summary import batch_success

SCOPE='phase4k_three_host_pilot_v2'


def environment():
    return dict(core=experiment_environment(),pilot_source_sha256={n:_digest(Path(__file__).parent/n) for n in
        ('three_host_encoding.py','three_host_benchmark.py','three_host_runner.py','three_host_pilot.py',
         'two_host_runner.py','benchmark_a_runner.py','benchmark_a_campaign.py','branch_a_summary.py')})


@lru_cache(maxsize=16)
def _model(serialized):
    b=build_three_host_qubo(json.loads(serialized));return b,three_host_reference(b)


def get_model(context,name):return _model(json.dumps(context['instances'][name],sort_keys=True))


def make_pilot_trials(context):
    q=context['protocol']['qaoa'];trials=[]
    for row in context['manifest']['instances']:
        if row['role']=='development':
            for p in q['depths']:
                for seed,final in zip(q['optimization_seeds'],q['evaluation_seeds']):
                    trials.append(dict(instance_id=row['instance_id'],role=row['role'],config=_config(context['protocol'],p,seed,final)))
        elif row['role']=='functional_control':
            smoke=context['protocol']['functional_smoke'];config=_config(context['protocol'],smoke['reps'],smoke['seed'],smoke['evaluation_seed'])
            config.update(smoke);trials.append(dict(instance_id=row['instance_id'],role=row['role'],config=config))
    for t in trials:t['run_key']=canonical_hash(dict(benchmark=canonical_hash(context),**t))
    return trials


def open_pilot(root,context,resume_dir=None):
    root=Path(root).resolve()
    if resume_dir is None:
        design=dict(benchmark=context,environment=environment())
        campaign=dict(schema_version=1,scope=SCOPE,campaign_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
            design=design,design_hash=canonical_hash(design),planned_runs=make_pilot_trials(context),
            preprocessing_sessions=[],attempts=[],active=None)
        folder=root/'data/reference_results/phase4k_three_host_pilot'/f"pilot_{campaign['campaign_id']}"
        folder.mkdir(parents=True,exist_ok=False);save_json(folder/'campaign.json',campaign)
    else:folder=_inside(root,resume_dir)
    with _lock(folder):
        campaign=_read(folder/'campaign.json');verify_pilot(folder,campaign,context);recover_active(folder,campaign,context)
    return folder,campaign


def _validate(r,active,context,env):
    t=active['trial'];allowed=TERMINAL if active['kind']=='trial' else (TERMINAL-{'completed'})|{'passed'}
    _require(r['config']==t['config'] and r['instance_id']==t['instance_id'] and r['status'] in allowed,'Pilot controls/status differ.')
    if r['status']=='completed':
        _require(r['environment']==env['core'],'Pilot runtime/source differs.')
        b,ref=get_model(context,t['instance_id']);audit_three_host_report(b,r,t['config'],ref)
    if r['status']=='passed':
        _require(len(r['active_points'])==len(r['evaluation_seconds'])==3 and
            all(len(x)==2*t['config']['reps'] and np.isfinite(x).all() and all(v!=0 for v in x) for x in r['active_points']) and
            all(np.isfinite(x) and x>=0 for x in r['evaluation_seconds']),'Probe evidence differs.')
        b,ref=get_model(context,t['instance_id']);raw,offset=build_ising(b);shots=t['config']['evaluation_shots']
        counts=r['probe_final_counts']
        _require(r['num_qubits']==raw.num_qubits and type(r['compiled_depth']) is int and r['compiled_depth']>0 and
            all(len(k)==raw.num_qubits and set(k)<={'0','1'} and type(v) is int and v>0 for k,v in counts.items()) and
            sum(counts.values())==shots,'Probe counts/layout differ.')
        samples=decode_distribution(b,{k:v/shots for k,v in counts.items()},raw,offset)
        _require(select_output(samples,shots,ref['original_best_objective'])==r['probe_final_output'],'Probe output differs.')
        estimate=1.5*(r['setup_seconds']+max(r['evaluation_seconds'])*(t['config']['maxiter']+1)+r['final_sampling_seconds']+r['postprocessing_seconds'])
        _require(np.isclose(estimate,r['maxiter_seconds_estimate'],rtol=0,atol=1e-8) and
            r['estimate_within_per_trial_limit']==(estimate<=t['config']['max_seconds']),'Probe projection differs.')


def finish_attempt(folder,campaign,r,context):
    active=campaign['active'];_require(active is not None,'No active pilot attempt.')
    _validate(r,active,context,campaign['design']['environment']);path=_inside(folder,active['report'])
    save_json(path,dict(campaign_id=campaign['campaign_id'],design_hash=campaign['design_hash'],attempt=active,result=r))
    campaign['attempts'].append(dict(number=active['number'],kind=active['kind'],run_key=active['trial']['run_key'],
        instance_id=active['trial']['instance_id'],reps=active['trial']['config']['reps'],status=r['status'],
        report=active['report'],report_sha256=_digest(path)))
    campaign['active']=None;save_json(Path(folder)/'campaign.json',campaign)


def recover_active(folder,campaign,context):
    active=campaign['active']
    if active is None:return
    path=_inside(folder,active['report'])
    if path.exists():
        e=_read(path);_require(e['attempt']==active and e['campaign_id']==campaign['campaign_id'] and e['design_hash']==campaign['design_hash'],'Orphan differs.')
        result=e['result']
    else:result=dict(status='interrupted',config=active['trial']['config'],instance_id=active['trial']['instance_id'],
        stop_reason='Kernel stopped before a terminal report was saved.',total_seconds=None,cost_function_evals=None)
    finish_attempt(folder,campaign,result,context)


def verify_pilot(folder,campaign,context):
    expected=dict(benchmark=context,environment=environment());planned=make_pilot_trials(context)
    _require(campaign['scope']==SCOPE and campaign['schema_version']==1 and campaign['design']==expected and
        campaign['design_hash']==canonical_hash(expected) and campaign['planned_runs']==planned,'Pilot input/protocol/source/runtime changed; resume refused.')
    lookup={t['run_key']:t for t in planned};seen=set();completed=[]
    for number,row in enumerate(campaign['attempts'],1):
        _require(row['number']==number and row['run_key'] in lookup,'Unknown pilot ledger row.')
        path=_inside(folder,row['report']);_require(_digest(path)==row['report_sha256'],'Pilot report checksum differs.')
        e=_read(path);a=e['attempt'];r=e['result'];t=lookup[row['run_key']]
        _require(e['campaign_id']==campaign['campaign_id'] and e['design_hash']==campaign['design_hash'] and
            a['trial']==t and a['number']==number and a['kind']==row['kind'] and a['report']==row['report'] and
            row['instance_id']==t['instance_id'] and row['reps']==t['config']['reps'] and r['status']==row['status'],'Pilot ledger/report differs.')
        _validate(r,a,context,expected['environment'])
        if r['status'] in ('completed','passed'):
            key=(row['kind'],row['run_key']);_require(key not in seen,'Duplicate successful pilot.');seen.add(key)
            if row['kind']=='trial':completed.append(row)
    if campaign['active'] is not None:
        a=campaign['active'];_require(a['number']==len(campaign['attempts'])+1 and a['trial'] in planned and a['kind'] in ('trial','probe'),'Invalid active pilot.')
        _inside(folder,a['report'])
    return completed


def prepare_models(folder,context):
    with _lock(folder):
        campaign=_read(Path(folder)/'campaign.json');verify_pilot(folder,campaign,context);recover_active(folder,campaign,context);rows=[]
        for row in context['manifest']['instances']:
            t=perf_counter();b,r=get_model(context,row['instance_id']);certificate=certify_three_host(b)
            rows.append(dict(instance_id=row['instance_id'],role=row['role'],num_qubits=b['qubo'].get_num_vars(),
                certificate=certificate,reference=r,model_reference_certificate_seconds=perf_counter()-t))
        campaign['preprocessing_sessions'].append(dict(rows=rows,at_utc=datetime.now(timezone.utc).isoformat()))
        save_json(Path(folder)/'campaign.json',campaign)
    return rows


def run_phase(folder,context,kind,instance_ids=None,retry_failed=False,progress=True):
    _require(kind in ('probe','trial'),'Unknown pilot phase.')
    allowed={t['instance_id'] for t in make_pilot_trials(context)}
    selected=allowed if instance_ids is None else set(instance_ids)
    _require(selected and selected<=allowed,'Test/unknown instances cannot run in Notebook19.')
    with _lock(folder):
        campaign=_read(Path(folder)/'campaign.json');verify_pilot(folder,campaign,context);recover_active(folder,campaign,context)
        prepared={r['instance_id'] for s in campaign['preprocessing_sessions'] for r in s['rows'] if r['certificate']['polynomial_identity']}
        _require(selected<=prepared,'Prepare and certify models first.')
        passed={(a['instance_id'],a['reps']) for a in campaign['attempts'] if a['kind']=='probe' and a['status']=='passed'}
        if kind=='trial':_require({(t['instance_id'],t['config']['reps']) for t in campaign['planned_runs'] if t['instance_id'] in selected}<=passed,'Run selected preflights first.')
        seen=set()
        for t in campaign['planned_runs']:
            group=(t['instance_id'],t['config']['reps'])
            if t['instance_id'] not in selected or (kind=='probe' and group in seen):continue
            seen.add(group);attempts=[a for a in campaign['attempts'] if a['kind']==kind and a['run_key']==t['run_key']]
            if attempts and (attempts[-1]['status'] in ('completed','passed') or (attempts[-1]['status']!='interrupted' and not retry_failed)):continue
            b,ref=get_model(context,t['instance_id']);start_attempt(folder,campaign,t,kind)
            print(f"{kind}: {t['instance_id']} p={t['config']['reps']} seed={t['config']['seed']}",flush=True)
            result=(probe_three_host(b,t['config'],context['protocol']['resource_policy'],ref) if kind=='probe' else
                run_three_host_trial(b,t['config'],context['protocol']['resource_policy'],ref,progress))
            finish_attempt(folder,campaign,result,context);print(result['status'],flush=True)
            if result['status'] not in ('completed','passed'):break
        verify_pilot(folder,campaign,context)
    return campaign


def result_rows(folder,campaign,context):
    rows=legacy_rows(folder,campaign)
    for row in rows:
        _,ref=get_model(context,row['instance_id']);q=ref['uniform_baseline']['optimal_placement_probability'];random=ref['structured_random']['optimal_probability']
        r=_read(Path(folder)/row['report'])['result'] if row['report'] else {};m=r.get('metrics') or {}
        row.update(num_qubits=get_model(context,row['instance_id'])[0]['qubo'].get_num_vars(),
            invalid_domain_probability=m.get('invalid_domain_probability'),optimal_lift_encoded=m.get('optimal_lift_encoded'),
            optimal_lift_structured_random=m.get('optimal_lift_structured_random'),uniform_optimal_probability=q,
            uniform_batch_success=batch_success(q,1024),structured_random_optimal_probability=random,
            structured_random_batch_success=batch_success(random,1024),total_algorithm_shots=r.get('total_algorithm_shots'))
    return rows


def budget_assessment(rows,campaign):
    groups={}
    for row in rows:
        if row['role']=='development' and row['status']=='completed':groups.setdefault((row['instance_id'],row['p']),[]).append(row['total_seconds'])
    full=all(row['status']=='completed' for row in rows)
    projection=15*sum(median(v) for v in groups.values()) if full else None
    return dict(status='pilot_complete' if full else 'pilot_partial',completed=sum(r['status']=='completed' for r in rows),planned=len(rows),
        projected_90_trial_seconds=projection,within_six_hours_by_projection=None if projection is None else projection<=21600,
        projection_scope='15 test trials per size/p times development median; excludes future preparation and failures; cost structure may differ; not a runtime guarantee',
        depth_selection='none',test_campaign_started=False)


def export_pilot(folder,context):
    folder=Path(folder)
    with _lock(folder):
        campaign=_read(folder/'campaign.json');verify_pilot(folder,campaign,context)
        _require(campaign['active'] is None,'Recover active attempt before export.')
        rows=result_rows(folder,campaign,context);assessment=budget_assessment(rows,campaign)
        save_json(folder/'assessment.json',assessment)
        table=folder/'pilot_results.csv'
        with table.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        paths=[folder/'campaign.json',table,folder/'assessment.json']+[folder/a['report'] for a in campaign['attempts']]
        for name in ('model_validation.json','controls.json','classical_timings.json','pilot_quality.png'):
            if (folder/name).exists():paths.append(folder/name)
        save_json(folder/'sha256.json',{p.relative_to(folder).as_posix():_digest(p) for p in paths});paths.append(folder/'sha256.json')
        archive=folder/f'{folder.name}.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for p in paths:z.write(p,p.relative_to(folder).as_posix())
    return archive,rows,assessment


def control_rows(context):
    rows=[]
    for item in context['manifest']['instances']:
        _,r=get_model(context,item['instance_id'])
        for name,f,q in [('uniform_encoded_domain_wall_y',r['uniform_baseline']['feasible_probability'],r['uniform_baseline']['optimal_placement_probability']),
                         ('random_assignment_y_inferred',r['structured_random']['feasible_probability'],r['structured_random']['optimal_probability'])]:
            rows.append(dict(instance_id=item['instance_id'],role=item['role'],method=name,feasible_probability=f,
                optimal_probability=q,optimal_batch_1024_probability=batch_success(q,1024),
                required_lift_for_80pct_batch=required_lift(q),note='IID analytical control; lift target is diagnostic, not an acceptance threshold'))
    return rows
