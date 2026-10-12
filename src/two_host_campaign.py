"""Additive, resumable encoding ablation; imports audited Notebook-16 evidence."""
from datetime import datetime, timezone
from copy import deepcopy
from functools import lru_cache
import csv
import hashlib
import json
from pathlib import Path
import shutil
from time import perf_counter
import zipfile
from . import benchmark_a_campaign as legacy
from .benchmark_a_campaign import (save_json, _read, _inside, _digest, _require, _lock, start_attempt)
from .independent_campaign import canonical_hash
from .two_host_encoding import ENCODING, build_two_host_qubo, compact_reference, certify_encoding
from .two_host_runner import run_compact_trial, probe_compact, audit_compact_report

SCOPE='phase4i_two_host_encoding_v1'


def _environment():
    return {**legacy._environment(),'encoding_source_sha256':{
        name:_digest(Path(__file__).parent/name) for name in
        ('two_host_encoding.py','two_host_runner.py','two_host_campaign.py')}}


@lru_cache(maxsize=4)
def _model(serialized):
    b=build_two_host_qubo(json.loads(serialized))
    return b,compact_reference(b)


def get_model(context,instance_id):
    return _model(json.dumps(context['instances'][instance_id],sort_keys=True))


def make_trials(context):
    return [{**t,'run_key':canonical_hash(dict(parent_run_key=t['run_key'],encoding=ENCODING))}
            for t in legacy.make_trials(context)]


def new_campaign(context,baseline_sha256):
    design=dict(benchmark=context,encoding=ENCODING,baseline_sha256=baseline_sha256,environment=_environment())
    return dict(schema_version=1,scope=SCOPE,campaign_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
        design=design,design_hash=canonical_hash(design),planned_runs=make_trials(context),
        preprocessing_sessions=[],attempts=[],active=None)


def _validate_result(r,attempt,context,environment):
    t=attempt['trial']
    _require(r['config']==t['config'] and r['instance_id']==t['instance_id'],'Attempt controls differ.')
    allowed=legacy.TERMINAL if attempt['kind']=='trial' else (legacy.TERMINAL-{'completed'})|{'passed','time_estimate_exceeds_budget'}
    _require(r['status'] in allowed,'Unknown compact attempt status.')
    if r['status']=='completed':
        _require(r['environment']==environment['core'],'Report runtime/source differs.')
        b,ref=get_model(context,t['instance_id']);audit_compact_report(b,r,t['config'],ref)
    if r['status']=='passed':
        _require(len(r['active_points'])==len(r['evaluation_seconds'])==3
            and all(len(x)==2*t['config']['reps'] and all(v!=0 for v in x) for x in r['active_points'])
            and r['estimated_solver_seconds']<=t['config']['max_seconds'],'Invalid probe evidence.')


def finish_attempt(folder,campaign,result,context):
    active=campaign['active'];_require(active is not None,'No active attempt.')
    _validate_result(result,active,context,campaign['design']['environment'])
    path=_inside(folder,active['report'])
    save_json(path,dict(schema_version=1,design_hash=campaign['design_hash'],campaign_id=campaign['campaign_id'],
        attempt=active,result=result))
    campaign['attempts'].append(dict(number=active['number'],kind=active['kind'],run_key=active['trial']['run_key'],
        instance_id=active['trial']['instance_id'],reps=active['trial']['config']['reps'],status=result['status'],
        report=active['report'],report_sha256=_digest(path)))
    campaign['active']=None;save_json(Path(folder)/'campaign.json',campaign)


def recover_active(folder,campaign,context):
    active=campaign['active']
    if active is None:return
    path=_inside(folder,active['report'])
    if path.is_file():
        e=_read(path)
        _require(e['attempt']==active and e['design_hash']==campaign['design_hash']
            and e['campaign_id']==campaign['campaign_id'],'Orphan report identity differs.')
        r=e['result']
    else:
        r=dict(status='interrupted',config=active['trial']['config'],instance_id=active['trial']['instance_id'],
            stop_reason='Previous kernel stopped before a terminal report was saved.',cost_function_evals=None,total_seconds=None)
    finish_attempt(folder,campaign,r,context)


def verify_campaign(folder,campaign,context):
    expected=dict(benchmark=context,encoding=ENCODING,baseline_sha256=campaign['design']['baseline_sha256'],environment=_environment())
    _require(campaign['schema_version']==1 and campaign['scope']==SCOPE and campaign['design']==expected
        and campaign['design_hash']==canonical_hash(expected),'Input/source/runtime changed; resume refused.')
    if expected['baseline_sha256'] is not None:
        _require(_digest(Path(folder)/'baseline_notebook16.zip')==expected['baseline_sha256'],'Baseline archive changed.')
    planned=make_trials(context);_require(campaign['planned_runs']==planned,'Planned matrix changed.')
    lookup={t['run_key']:t for t in planned};seen=set();completed=[]
    for number,row in enumerate(campaign['attempts'],1):
        _require(row['number']==number and row['run_key'] in lookup,'Unknown ledger row.')
        path=_inside(folder,row['report']);_require(_digest(path)==row['report_sha256'],'Report digest differs.')
        e=_read(path);a=e['attempt'];r=e['result'];trial=lookup[row['run_key']]
        _require(e['campaign_id']==campaign['campaign_id'] and e['design_hash']==campaign['design_hash']
            and a['trial']==trial and a['number']==number and a['kind']==row['kind'] and a['report']==row['report']
            and r['status']==row['status'] and row['instance_id']==trial['instance_id']
            and row['reps']==trial['config']['reps'],'Ledger identity differs.')
        _validate_result(r,a,context,expected['environment'])
        if r['status'] in ('completed','passed'):
            key=(row['kind'],row['run_key']);_require(key not in seen,'Duplicate successful attempt.');seen.add(key)
            if row['kind']=='trial':completed.append(row)
    if campaign['active'] is not None:
        a=campaign['active'];_require(a['number']==len(campaign['attempts'])+1 and a['trial'] in planned
            and a['kind'] in ('trial','probe'),'Invalid active attempt.');_inside(folder,a['report'])
    return completed


def prepare_models(folder,context):
    with _lock(folder):
        campaign=_read(Path(folder)/'campaign.json');verify_campaign(folder,campaign,context)
        _require(campaign['active'] is None,'Recover active attempt before preprocessing.')
        rows=[]
        for item in context['manifest']['instances']:
            t=perf_counter();b,r=get_model(context,item['instance_id']);certificate=certify_encoding(b)
            rows.append(dict(instance_id=item['instance_id'],role=item['role'],certificate=certificate,
                reference=r,model_reference_certificate_seconds=perf_counter()-t))
        campaign['preprocessing_sessions'].append(dict(rows=rows,at_utc=datetime.now(timezone.utc).isoformat()))
        save_json(Path(folder)/'campaign.json',campaign)
    return rows


def run_preflights(folder,context,instance_ids=None,retry_failed=False):
    selected=legacy._selected(context,instance_ids)
    with _lock(folder):
        campaign=_read(Path(folder)/'campaign.json');verify_campaign(folder,campaign,context);recover_active(folder,campaign,context)
        for instance in selected:
            b,r=get_model(context,instance)
            for p in context['protocol']['qaoa']['depths']:
                trial=next(t for t in campaign['planned_runs'] if t['instance_id']==instance and t['config']['reps']==p)
                rows=[a for a in campaign['attempts'] if a['kind']=='probe' and a['run_key']==trial['run_key']]
                if rows and (rows[-1]['status']=='passed' or (rows[-1]['status']!='interrupted' and not retry_failed)):continue
                start_attempt(folder,campaign,trial,'probe');print(f'Compact probe {instance} p={p}',flush=True)
                result=probe_compact(b,trial['config'],context['protocol']['resource_policy'],r)
                finish_attempt(folder,campaign,result,context);print(result['status'],flush=True)
                if result['status']!='passed':return campaign
    return campaign


def run_campaign(folder,context,instance_ids=None,retry_failed=False,progress=True):
    selected=legacy._selected(context,instance_ids)
    with _lock(folder):
        campaign=_read(Path(folder)/'campaign.json');verify_campaign(folder,campaign,context);recover_active(folder,campaign,context)
        passed={(a['instance_id'],a['reps']) for a in campaign['attempts'] if a['kind']=='probe' and a['status']=='passed'}
        _require({(i,p) for i in selected for p in context['protocol']['qaoa']['depths']}<=passed,'Run selected preflights first.')
        for trial in sorted(campaign['planned_runs'],key=lambda t:t['role']!='negative_control'):
            if trial['role']=='benchmark' and trial['instance_id'] not in selected:continue
            rows=[a for a in campaign['attempts'] if a['kind']=='trial' and a['run_key']==trial['run_key']]
            if rows and (rows[-1]['status']=='completed' or (rows[-1]['status']!='interrupted' and not retry_failed)):continue
            b,r=get_model(context,trial['instance_id']);start_attempt(folder,campaign,trial,'trial')
            print(f"Compact {trial['instance_id']} p={trial['config']['reps']} seed={trial['config']['seed']}",flush=True)
            result=run_compact_trial(b,trial['config'],context['protocol']['resource_policy'],r,progress)
            finish_attempt(folder,campaign,result,context);print(result['status'],flush=True)
            if result['status']!='completed':break
        verify_campaign(folder,campaign,context)
    return campaign


def _augment(row,reference,encoding,config,qubits,total_shots=None,accounting=None):
    u=reference['uniform_baseline'];popt=row['optimal_probability'];pfeas=row['feasible_probability']
    return {**row,'encoding':encoding,'num_qubits':qubits,
        'uniform_feasible_probability':u['feasible_probability'],
        'uniform_optimal_probability':u['optimal_placement_probability'],
        'feasible_lift':pfeas/u['feasible_probability'] if pfeas is not None and u['feasible_probability'] else None,
        'optimal_lift':popt/u['optimal_placement_probability'] if popt is not None and u['optimal_placement_probability'] else None,
        'total_algorithm_shots':total_shots,'shot_accounting':accounting}


def result_rows(folder,campaign):
    rows=legacy.result_rows(folder,campaign);context=campaign['design']['benchmark']
    result=[]
    for row,t in zip(rows,campaign['planned_runs']):
        b,r=get_model(context,t['instance_id'])
        report=_read(Path(folder)/row['report'])['result'] if row['report'] else {}
        result.append(_augment(row,r,ENCODING,t['config'],b['qubo'].get_num_vars(),
            report.get('total_algorithm_shots'),'counted_sampler_submissions_plus_independent_final'))
    return result


def _baseline_row(t,r,attempts):
    o=r['benchmark_output'];m=r['metrics'];stop=r['optimizer_stop']
    row=dict(instance_id=t['instance_id'],role=t['role'],p=t['config']['reps'],seed=t['config']['seed'],
        run_key=t['run_key'],status=r['status'],attempt_count=len(attempts),found_valid=o['found_valid'],
        found_optimal=o['found_optimal'],selected_objective=o['selected_objective'],optimality_gap=o['optimality_gap'],
        feasible_probability=m['feasible_probability'],optimal_probability=m['optimal_placement_probability'],
        ground_probability=m['qubo_ground_state_probability'],sample_mean_energy=m['final_sample_mean_qubo_energy'],
        nfev=r['cost_function_evals'],optimizer_success=stop['success'],stop_reason=stop['message'],
        total_seconds=r['total_seconds'],optimization_seconds=r['optimization_seconds'],
        sampling_seconds=r['evaluation_sampling_seconds'],postprocessing_seconds=r['postprocessing_seconds'],
        peak_rss_mib=r['resources']['process_peak_rss_mib'],mode_tie_count=o['mode_tie_count'],
        unique_mode_valid=o['unique_mode_valid'],report=attempts[-1]['report'])
    known=r['qiskit_optimization_version']=='0.7.0'
    total=(r['cost_function_evals']+1)*t['config']['shots']+t['config']['evaluation_shots'] if known else None
    return _augment(row,r['reference'],'one_hot_slack_v1_1',t['config'],r['num_qubits'],total,
        'reconstructed_qiskit_optimization_0.7.0_including_eigenstate_batch' if known else 'unknown_version_not_inferred')


_baseline_cache={}


def import_baseline(path,context):
    digest=_digest(path);key=(digest,canonical_hash(context),canonical_hash(_environment()))
    if key not in _baseline_cache:
        summary=_audit_baseline(path,context)
        _require(summary['sha256']==digest,'Archive changed during audit.')
        _baseline_cache[key]=summary
    return deepcopy(_baseline_cache[key])


def _audit_baseline(path,context):
    """Read the archive in memory; hash and semantically audit all attempts, no extraction."""
    with zipfile.ZipFile(path) as z:
        names=z.namelist();_require(len(names)==len(set(names)),'Duplicate archive entries.')
        checksums=json.loads(z.read('sha256.json'));payload={}
        for name,digest in checksums.items():
            data=z.read(name);_require(hashlib.sha256(data).hexdigest()==digest,'Baseline checksum differs.')
            if name.endswith('.json'):payload[name]=json.loads(data)
    campaign=payload['campaign.json'];design=campaign['design']
    _require(campaign['scope']==legacy.SCOPE and campaign['schema_version']==1
        and design['benchmark']==context and campaign['design_hash']==canonical_hash(design)
        and campaign['planned_runs']==legacy.make_trials(context) and campaign['active'] is None,
        'Notebook-16 baseline design/incomplete active attempt differs.')
    planned={t['run_key']:t for t in campaign['planned_runs']};success={};seen=set()
    for number,row in enumerate(campaign['attempts'],1):
        if number==1 or number%10==0:print(f"Audit Notebook16: {number}/{len(campaign['attempts'])} attempts",flush=True)
        _require(row['number']==number and row['run_key'] in planned,'Unknown baseline trial.')
        e=payload[row['report']];a=e['attempt'];r=e['result'];t=planned[row['run_key']]
        _require(checksums[row['report']]==row['report_sha256'] and e['campaign_id']==campaign['campaign_id']
            and e['design_hash']==campaign['design_hash'] and a['number']==number and a['trial']==t
            and a['kind']==row['kind'] and a['report']==row['report'] and r['status']==row['status']
            and row['instance_id']==t['instance_id'] and row['reps']==t['config']['reps'],'Baseline ledger differs.')
        legacy._validate_result(r,a,context,design['environment'])
        if r['status'] in ('completed','passed'):
            key=(row['kind'],row['run_key']);_require(key not in seen,'Duplicate baseline success.');seen.add(key)
            if row['kind']=='trial':success[row['run_key']]=r
    _require(set(success)==set(planned),'Baseline must contain all formal runs and the negative control.')
    rows=[]
    for t in campaign['planned_runs']:
        attempts=[a for a in campaign['attempts'] if a['kind']=='trial' and a['run_key']==t['run_key']]
        _require(attempts[-1]['status']=='completed','Baseline has a later failed attempt.')
        rows.append(_baseline_row(t,success[t['run_key']],attempts))
    return dict(sha256=_digest(path),campaign_id=campaign['campaign_id'],rows=rows,
        environment=design['environment'],runtime_matches_current=
        design['environment']['core']['runtime']==_environment()['core']['runtime'])


def open_campaign(root,context,baseline_zip,resume_dir=None):
    root=Path(root).resolve()
    if resume_dir is None:
        # Verify before creating a campaign; retain the exact imported bytes.
        baseline=import_baseline(baseline_zip,context)
        campaign=new_campaign(context,baseline['sha256'])
        folder=root/'data/reference_results/phase4i_encoding'/f"encoding_{campaign['campaign_id']}"
        folder.mkdir(parents=True,exist_ok=False)
        shutil.copyfile(baseline_zip,folder/'baseline_notebook16.zip');save_json(folder/'campaign.json',campaign)
    else:
        folder=_inside(root,resume_dir);campaign=_read(folder/'campaign.json')
        if baseline_zip is not None:
            _require(_digest(baseline_zip)==campaign['design']['baseline_sha256'],'Another baseline was selected on resume.')
        import_baseline(folder/'baseline_notebook16.zip',context)
    with _lock(folder):
        campaign=_read(folder/'campaign.json');verify_campaign(folder,campaign,context);recover_active(folder,campaign,context)
    return folder,campaign


def export_campaign(folder,context):
    folder=Path(folder)
    with _lock(folder):
        campaign=_read(folder/'campaign.json');verify_campaign(folder,campaign,context)
        _require(campaign['active'] is None,'Recover active attempt before export.')
        rows=result_rows(folder,campaign);paths=[folder/'campaign.json']+[folder/a['report'] for a in campaign['attempts']]
        tables={'compact_results.csv':rows}
        if campaign['design']['baseline_sha256'] is not None:
            baseline=import_baseline(folder/'baseline_notebook16.zip',context)
            tables['encoding_comparison.csv']=baseline['rows']+rows;paths.append(folder/'baseline_notebook16.zip')
        for name,table in tables.items():
            path=folder/name
            with path.open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
            paths.append(path)
        plot=folder/'encoding_quality.png'
        if plot.is_file():paths.append(plot)
        digest=folder/'sha256.json';save_json(digest,{p.relative_to(folder).as_posix():_digest(p) for p in paths})
        archive=folder/f'{folder.name}.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for path in paths+[digest]:z.write(path,path.relative_to(folder).as_posix())
    return archive,rows
