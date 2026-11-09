"""Frozen branch-A input, append-only attempts, audited recovery and CSV export."""
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import zipfile
from time import perf_counter
import numpy as np
from .independent_campaign import canonical_hash
from .qubo import build_qubo
from .ising import build_ising, scale_ising, scaled_qaoa_point, decode_samples
from .qaoa_optimizer import sampling_seeds
from .qaoa_experiment import (experiment_environment, qubo_fingerprint, prepare_reference,
                             summarize_samples, distribution_statistics)
from .penalty_analysis import penalty_diagnostics
from .benchmark_a_runner import run_trial, probe_depth, select_output

SCOPE='phase4h_branch_a_unified_v1_1'
# v1.1 changes only the QAOA time guard; the v1 inputs and rules are inherited.
FROZEN_DESIGN='c7b30d1044cbd9b68c858d1f40e6414aeee388bb2d7114c0ea06b475e5e4d92f'
TERMINAL={'completed','resource_blocked','resource_stopped','time_budget_exceeded','interrupted','memory_error','error'}


def _require(condition,message):
    if not condition:raise ValueError(message)


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(path)


def _inside(root,name):
    root=Path(root).resolve();path=(root/name).resolve()
    _require(path.is_relative_to(root),'Path leaves repository/campaign.')
    return path


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_benchmark(root):
    root=Path(root).resolve()
    manifest=_read(root/'data/benchmarks/nt409_benchmark_v1_1/manifest.json')
    body={k:v for k,v in manifest.items() if k!='design_sha256'}
    _require(manifest['design_sha256']==canonical_hash(body)==FROZEN_DESIGN,
             'Frozen benchmark manifest changed. Restore the delivered v1.1 files.')
    protocol=_read(_inside(root,manifest['protocol_path']))
    _require(canonical_hash(protocol)==manifest['protocol_canonical_sha256'],'Protocol changed.')
    spec=_inside(root,manifest['specification_path']).read_bytes().replace(b'\r\n',b'\n')
    _require(hashlib.sha256(spec).hexdigest()==manifest['specification_sha256_lf_utf8'],'Frozen specification changed.')
    parent=_inside(root,manifest['parent_specification_path']).read_bytes().replace(b'\r\n',b'\n')
    _require(hashlib.sha256(parent).hexdigest()==manifest['parent_specification_sha256_lf_utf8'],
             'Inherited v1 specification changed.')
    instances={}
    for row in manifest['instances']:
        instance=_read(_inside(root,row['path']))
        _require(instance['instance_id']==row['instance_id'] and canonical_hash(instance)==row['canonical_sha256'],
                 f"Input changed: {row['instance_id']}")
        instances[row['instance_id']]=instance
    return dict(manifest=manifest,protocol=protocol,instances=instances)


def _environment():
    directory=Path(__file__).parent
    return dict(core=experiment_environment(),branch_a_source_sha256={name:_digest(directory/name)
        for name in ('benchmark_a_runner.py','benchmark_a_campaign.py')})


def _config(protocol,p,seed,final_seed):
    q=protocol['qaoa'];r=protocol['resource_policy']
    return dict(shots=q['shots'],evaluation_shots=q['evaluation_shots'],maxiter=q['maxiter'],
        max_seconds=q['max_seconds'],max_qubits=r['max_qubits'],aer_threads=r['aer_threads'],
        aer_memory_mb=r['aer_memory_mb'],min_available_gib=r['start_available_min_gib'],
        hamiltonian_scaling=q['hamiltonian_scaling'],cobyla_rhobeg=q['cobyla_rhobeg'],
        cobyla_tol=q['cobyla_tol'],seed=seed,evaluation_seed=final_seed,reps=p,
        initial_point=q['initial_points_beta_then_gamma'][str(p)].copy())


def make_trials(context):
    protocol=context['protocol'];q=protocol['qaoa'];trials=[]
    for row in context['manifest']['instances']:
        if row['role']!='benchmark':continue
        for p in q['depths']:
            for seed,final in zip(q['optimization_seeds'],q['evaluation_seeds']):
                trials.append(dict(instance_id=row['instance_id'],role='benchmark',config=_config(protocol,p,seed,final)))
    negative=protocol.get('negative_control')
    if negative:
        smoke=negative['qaoa_smoke']
        config=_config(protocol,smoke['reps'],smoke['seed'],smoke['evaluation_seed']);config.update(smoke)
        trials.append(dict(instance_id=negative['instance_id'],role='negative_control',config=config))
    for t in trials:
        t['run_key']=canonical_hash(dict(benchmark=canonical_hash(context),**t))
    return trials


def new_campaign(context):
    design=dict(benchmark=context,environment=_environment())
    return dict(schema_version=1,scope=SCOPE,campaign_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
        design=design,design_hash=canonical_hash(design),planned_runs=make_trials(context),
        preprocessing_sessions=[],attempts=[],active=None)


@lru_cache(maxsize=4)
def _model(instance_json):
    instance=json.loads(instance_json)
    bundle=build_qubo(instance,assignment_penalty=3,capacity_penalty=3)
    return bundle,prepare_reference(bundle)


def model(context,instance_id):
    return _model(json.dumps(context['instances'][instance_id],sort_keys=True))


def prepare_models(folder,context):
    """Record model/reference preparation once per call, including cache reuse."""
    with _lock(folder):
        campaign=_read(Path(folder)/'campaign.json');verify_campaign(folder,campaign,context)
        _require(campaign['active'] is None,'Recover the active attempt before preparing models.')
        rows=[]
        for item in context['manifest']['instances']:
            before=_model.cache_info().hits;started=perf_counter()
            bundle,reference=model(context,item['instance_id']);elapsed=perf_counter()-started
            rows.append(dict(instance_id=item['instance_id'],role=item['role'],
                qubits=bundle['qubo'].get_num_vars(),optimal_hosts=reference['original_best_objective'],
                qubo_min=reference['minimum_energy'],model_reference_seconds=elapsed,
                cache_hit=_model.cache_info().hits>before))
        session=dict(started_at_utc=datetime.now(timezone.utc).isoformat(),rows=rows)
        campaign['preprocessing_sessions'].append(session)
        save_json(Path(folder)/'campaign.json',campaign)
    return rows


def _validate_completed(r,trial,context):
    bundle,reference=model(context,trial['instance_id']);config=trial['config'];p=config['reps']
    raw,offset=build_ising(bundle);_,scaling=scale_ising(raw,'max_abs')
    _require(r['status']=='completed' and r['method']=='QAOA_AerSamplerV2_CPU_statevector_COBYLA'
             and r['config']==config and r['instance']==bundle['instance'] and r['reference']==reference,
             'Completed report method/config/input/reference differs.')
    _require(r['instance_sha256']==canonical_hash(bundle['instance'])
        and r['provenance']==dict(model_version=bundle['model_version'],qubo=qubo_fingerprint(bundle))
        and r['variable_names']==[v.name for v in bundle['qubo'].variables]
        and r['num_qubits']==raw.num_qubits and r['ising_offset']==offset
        and r['penalties']==bundle['penalties'] and r['penalty_mode']=='independent', 'QUBO metadata differs.')
    _require(r['hamiltonian_scaling']==scaling and r['parameter_names']==
        [f'β[{i}]' for i in range(p)]+[f'γ[{i}]' for i in range(p)],'Scale/parameter order differs.')
    _require(len(r['optimal_point'])==2*p and np.isfinite(r['optimal_point']).all()
        and np.allclose(r['optimal_point_raw_hamiltonian'],scaled_qaoa_point(r['optimal_point'],p,1/scaling['scale']),rtol=0,atol=1e-10),
        'Final parameter units differ.')
    history=r['optimization_history'];stop=r['optimizer_stop']
    _require(0<len(history)==stop['nfev']==r['cost_function_evals']<=config['maxiter']
        and type(stop['success']) is bool and type(stop['status']) is int and bool(stop['message'])
        and [h['evaluation'] for h in history]==list(range(1,len(history)+1))
        and history[0]['parameters']==config['initial_point'],'Optimizer history/stop differs.')
    _require(all(len(h['parameters'])==2*p and np.isfinite(h['parameters']).all()
        and h['objective_source']=='sampled_mean'
        and np.isclose(h['estimated_qubo_energy'],scaling['scale']*h['execution_hamiltonian_expectation']+offset,rtol=0,atol=1e-7)
        for h in history),'History parameters or energy units differ.')
    _require(np.isclose(r['optimizer_estimated_qubo_expectation'],
        scaling['scale']*r['optimizer_estimated_execution_expectation']+offset,rtol=0,atol=1e-7),'Final energy units differ.')
    _require(r['sampling_protocol']=='independent_final_v1' and r['sampling']==sampling_seeds(config),'Sampling seeds differ.')
    samples=r['final_samples'];shots=config['evaluation_shots']
    bits=np.asarray([s['bits'] for s in samples]);prob=np.asarray([s['probability'] for s in samples]);counts=np.rint(prob*shots)
    _require(bits.shape==(len(samples),raw.num_qubits) and np.isin(bits,[0,1]).all()
        and len({tuple(x) for x in bits})==len(samples)==r['observed_final_bitstrings']
        and np.isfinite(prob).all() and (counts>0).all() and counts.sum()==shots
        and (prob[:-1]>=prob[1:]).all() and np.allclose(prob,counts/shots,rtol=0,atol=1e-12),'Invalid sample counts.')
    distribution={sum(int(v)<<i for i,v in enumerate(s['bits'])):s['probability'] for s in samples}
    _require(decode_samples(bundle,distribution,raw,offset)==samples,'Bits/decoded/energy differ.')
    _require(summarize_samples(samples,reference)==r['metrics'] and penalty_diagnostics(bundle,r)==r['penalty_analysis'],
             'Metrics differ from observed bits.')
    _require(select_output(samples,shots,reference['original_best_objective'])==r['benchmark_output'],'Benchmark output rule differs.')
    _require(distribution_statistics(bundle,distribution,shots,config['evaluation_seed'])==r['sampling_statistics']['evaluation'],
             'Final statistics differ.')
    training=r['sampling_statistics']['training']
    _require(training['shots']==config['shots'] and training['seed']==config['seed']
        and np.isclose(training['mean_qubo_energy'],r['optimizer_estimated_qubo_expectation'],rtol=0,atol=1e-7),
        'Training statistics differ.')


def _validate_result(result,attempt,context,environment):
    trial=attempt['trial']
    _require(result['config']==trial['config'] and result['instance_id']==trial['instance_id'],'Attempt controls differ.')
    allowed=TERMINAL if attempt['kind']=='trial' else (TERMINAL-{'completed'})|{'passed','time_estimate_exceeds_budget'}
    _require(result['status'] in allowed,'Unknown attempt status.')
    if result['status']=='completed':
        _require(result['environment']==environment['core'],'Report runtime/source changed.')
        _validate_completed(result,trial,context)
    if result['status']=='passed':
        _require(len(result['active_points'])==len(result['evaluation_seconds'])==3
            and all(len(point)==2*trial['config']['reps'] and np.isfinite(point).all() and all(v!=0 for v in point)
                    for point in result['active_points'])
            and result['estimated_solver_seconds']<=trial['config']['max_seconds'],'Invalid probe evidence.')


def start_attempt(folder,campaign,trial,kind):
    _require(campaign['active'] is None and trial in campaign['planned_runs'] and kind in ('trial','probe'),
             'Unknown or concurrent attempt.')
    _require(not any(a['kind']==kind and a['run_key']==trial['run_key'] and a['status'] in ('completed','passed')
                     for a in campaign['attempts']),'Attempt already completed.')
    number=len(campaign['attempts'])+1
    active=dict(number=number,kind=kind,trial=trial,
        started_at_utc=datetime.now(timezone.utc).isoformat(),report=f'attempts/{number:04d}_{kind}_{trial["run_key"][:12]}.json')
    campaign['active']=active;save_json(Path(folder)/'campaign.json',campaign)
    return active


def finish_attempt(folder,campaign,result,context):
    active=campaign['active'];_require(active is not None,'No active attempt.')
    _validate_result(result,active,context,campaign['design']['environment'])
    envelope=dict(schema_version=1,design_hash=campaign['design_hash'],campaign_id=campaign['campaign_id'],attempt=active,result=result)
    path=_inside(folder,active['report']);save_json(path,envelope)
    row=dict(number=active['number'],kind=active['kind'],run_key=active['trial']['run_key'],
        instance_id=active['trial']['instance_id'],reps=active['trial']['config']['reps'],status=result['status'],
        report=active['report'],report_sha256=_digest(path))
    campaign['attempts'].append(row);campaign['active']=None
    save_json(Path(folder)/'campaign.json',campaign)
    return row


def recover_active(folder,campaign,context):
    """Called under the OS lock: recover a final file or record a crashed attempt."""
    active=campaign['active']
    if active is None:return
    path=_inside(folder,active['report'])
    if path.exists():
        envelope=_read(path)
        _require(envelope['attempt']==active and envelope['campaign_id']==campaign['campaign_id']
            and envelope['design_hash']==campaign['design_hash'],'Orphan report identity differs.')
        result=envelope['result']
    else:
        result=dict(status='interrupted',config=active['trial']['config'],instance_id=active['trial']['instance_id'],
            stop_reason='Previous process ended before a terminal result was saved; partial counts are unavailable.',
            cost_function_evals=None,total_seconds=None)
    finish_attempt(folder,campaign,result,context)


def verify_campaign(folder,campaign,context):
    expected=dict(benchmark=context,environment=_environment())
    _require(campaign['scope']==SCOPE and campaign['schema_version']==1 and campaign['design']==expected
        and campaign['design_hash']==canonical_hash(expected),'Input, implementation or runtime changed; resume refused.')
    planned=make_trials(context);_require(campaign['planned_runs']==planned,'Planned matrix changed.')
    lookup={t['run_key']:t for t in planned};completed=[];seen=set()
    for index,row in enumerate(campaign['attempts'],1):
        _require(row['number']==index and row['run_key'] in lookup,'Invalid/unknown ledger row.')
        path=_inside(folder,row['report']);_require(_digest(path)==row['report_sha256'],'Report digest differs.')
        envelope=_read(path);attempt=envelope['attempt'];r=envelope['result'];trial=lookup[row['run_key']]
        _require(envelope['design_hash']==campaign['design_hash'] and envelope['campaign_id']==campaign['campaign_id']
            and attempt['number']==index and attempt['trial']==trial and attempt['report']==row['report']
            and attempt['kind']==row['kind'] and r['status']==row['status']
            and row['instance_id']==trial['instance_id'] and row['reps']==trial['config']['reps'],'Ledger identity differs.')
        _validate_result(r,attempt,context,campaign['design']['environment'])
        if r['status'] in ('completed','passed'):
            key=(row['kind'],row['run_key']);_require(key not in seen,'Duplicate successful attempt.');seen.add(key)
            if row['kind']=='trial':completed.append(row)
    if campaign['active'] is not None:
        active=campaign['active']
        _require(active['number']==len(campaign['attempts'])+1 and active['trial'] in planned
            and active['kind'] in ('trial','probe'),'Invalid active attempt.')
        _inside(folder,active['report'])
    return completed


@contextmanager
def _lock(folder):
    """Cross-platform advisory lock; automatically released if a kernel dies."""
    path=Path(folder)/'campaign.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        f.seek(0,2)
        if f.tell()==0:f.write(b'0');f.flush()
        f.seek(0)
        if os.name=='nt':
            import msvcrt
            try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as e:raise RuntimeError('Another kernel is using this campaign.') from e
            try:yield
            finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as e:raise RuntimeError('Another kernel is using this campaign.') from e
            try:yield
            finally:fcntl.flock(f,fcntl.LOCK_UN)


def open_campaign(root,context,resume_dir=None):
    root=Path(root).resolve()
    if resume_dir is None:
        campaign=new_campaign(context)
        folder=root/'data/reference_results/phase4h_benchmark_a'/f"benchmark_a_{campaign['campaign_id']}"
        folder.mkdir(parents=True,exist_ok=False);save_json(folder/'campaign.json',campaign)
    else:
        folder=_inside(root,resume_dir);_require((folder/'campaign.json').is_file(),'Missing campaign.json in RESUME_DIR.')
    with _lock(folder):
        campaign=_read(folder/'campaign.json');verify_campaign(folder,campaign,context)
        recover_active(folder,campaign,context)
    return folder,campaign


def _selected(context,instance_ids):
    valid=[r['instance_id'] for r in context['manifest']['instances'] if r['role']=='benchmark']
    selected=valid if instance_ids is None else list(instance_ids)
    _require(bool(selected) and len(set(selected))==len(selected) and set(selected)<=set(valid),'Invalid selected instances.')
    return selected


def run_preflights(folder,context,instance_ids=None,retry_failed=False):
    selected=_selected(context,instance_ids)
    with _lock(folder):
        campaign=_read(Path(folder)/'campaign.json');verify_campaign(folder,campaign,context);recover_active(folder,campaign,context)
        for instance_id in selected:
            bundle,reference=model(context,instance_id)
            for p in context['protocol']['qaoa']['depths']:
                trial=next(t for t in campaign['planned_runs'] if t['instance_id']==instance_id and t['config']['reps']==p)
                rows=[a for a in campaign['attempts'] if a['kind']=='probe' and a['run_key']==trial['run_key']]
                if rows and rows[-1]['status']=='passed':continue
                if rows and rows[-1]['status']!='interrupted' and not retry_failed:continue
                start_attempt(folder,campaign,trial,'probe');print(f'Probe {instance_id} p={p}',flush=True)
                result=probe_depth(bundle,trial['config'],context['protocol']['resource_policy'],reference)
                finish_attempt(folder,campaign,result,context);print(result['status'],result.get('estimated_solver_seconds'),flush=True)
                if result['status']!='passed':return campaign
            gc.collect()
    return campaign


def run_campaign(folder,context,instance_ids=None,retry_failed=False,progress=True):
    selected=_selected(context,instance_ids)
    with _lock(folder):
        campaign=_read(Path(folder)/'campaign.json');verify_campaign(folder,campaign,context);recover_active(folder,campaign,context)
        passed={(a['instance_id'],a['reps']) for a in campaign['attempts'] if a['kind']=='probe' and a['status']=='passed'}
        required={(i,p) for i in selected for p in context['protocol']['qaoa']['depths']}
        _require(required<=passed,'Run all selected preflights successfully before formal optimization.')
        trials=sorted(campaign['planned_runs'],key=lambda t:t['role']!='negative_control')
        for trial in trials:
            if trial['role']=='benchmark' and trial['instance_id'] not in selected:continue
            rows=[a for a in campaign['attempts'] if a['kind']=='trial' and a['run_key']==trial['run_key']]
            if rows and rows[-1]['status']=='completed':continue
            if rows and rows[-1]['status']!='interrupted' and not retry_failed:continue
            bundle,reference=model(context,trial['instance_id'])
            start_attempt(folder,campaign,trial,'trial')
            print(f"Run {trial['instance_id']} p={trial['config']['reps']} seed={trial['config']['seed']} ({trial['role']})",flush=True)
            result=run_trial(bundle,trial['config'],context['protocol']['resource_policy'],reference,progress)
            finish_attempt(folder,campaign,result,context)
            print(result['status'],result.get('optimizer_stop',result.get('stop_reason')),flush=True)
            if result['status']!='completed':break
            gc.collect()
        verify_campaign(folder,campaign,context)
    return campaign


def result_rows(folder,campaign):
    """One row per planned trial, including pending and terminal failures."""
    rows=[]
    for t in campaign['planned_runs']:
        attempts=[a for a in campaign['attempts'] if a['kind']=='trial' and a['run_key']==t['run_key']]
        r=_read(Path(folder)/attempts[-1]['report'])['result'] if attempts else {}
        complete=r.get('status')=='completed'
        o=r.get('benchmark_output',{}) if complete else {}
        metrics=(r.get('metrics') or {}) if complete else {};stop=r.get('optimizer_stop') or {}
        rows.append(dict(instance_id=t['instance_id'],role=t['role'],p=t['config']['reps'],seed=t['config']['seed'],
            run_key=t['run_key'],status=r.get('status','pending'),attempt_count=len(attempts),
            found_valid=o.get('found_valid'),found_optimal=o.get('found_optimal'),
            selected_objective=o.get('selected_objective'),optimality_gap=o.get('optimality_gap'),
            feasible_probability=metrics.get('feasible_probability'),optimal_probability=metrics.get('optimal_placement_probability'),
            ground_probability=metrics.get('qubo_ground_state_probability'),sample_mean_energy=metrics.get('final_sample_mean_qubo_energy'),
            nfev=r.get('cost_function_evals'),optimizer_success=stop.get('success'),stop_reason=stop.get('message',r.get('stop_reason')),
            total_seconds=r.get('total_seconds'),optimization_seconds=r.get('optimization_seconds'),
            sampling_seconds=r.get('evaluation_sampling_seconds'),postprocessing_seconds=r.get('postprocessing_seconds'),
            peak_rss_mib=r.get('resources',{}).get('process_peak_rss_mib'),mode_tie_count=o.get('mode_tie_count'),
            unique_mode_valid=o.get('unique_mode_valid'),report=attempts[-1]['report'] if attempts else None))
    return rows


def export_campaign(folder,context):
    folder=Path(folder)
    with _lock(folder):
        campaign=_read(folder/'campaign.json');verify_campaign(folder,campaign,context)
        _require(campaign['active'] is None,'An active attempt must be recovered before exporting.')
        rows=result_rows(folder,campaign)
        table=folder/'branch_a_results.csv'
        with table.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        paths=[folder/'campaign.json',table]+[folder/a['report'] for a in campaign['attempts']]
        plot=folder/'branch_a_quality.png'
        if plot.is_file():paths.append(plot)
        checksums={p.relative_to(folder).as_posix():_digest(p) for p in paths}
        checksum_path=folder/'sha256.json';save_json(checksum_path,checksums)
        path=folder/f'{folder.name}.zip'
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            for p in paths+[checksum_path]:z.write(p,p.relative_to(folder).as_posix())
    return path,rows
