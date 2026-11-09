"""N28: the three frozen 5x3 cases; separate from N27's frozen src snapshot."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import gc
import os
import traceback
import zipfile
from time import perf_counter
import numpy as np
import psutil
from src.initialization_campaign import interp_p1_to_p2
from src.qaoa_optimizer import RecordingCOBYLA

from src import domain_wall_training as development
from src.domain_wall_mixer import VARIANTS, circuit_components
from src.qaoa_experiment import experiment_environment, qubo_fingerprint
from src.shot_noise_campaign import load_json, save_json, digest, file_hash
from src.three_host_encoding import build_three_host_qubo
from src.validation5x3 import load_dataset, DATA_HASH, assignment_audit

CASE_IDS=('v5x3_1','v5x3_2','v5x3_3')
MODULE='experiments/domain_wall_validation.py'


def make_plan(software_validation=False):
    stages=[]
    for k,case in enumerate(CASE_IDS):
        for s in development.make_plan(software_validation):
            stages.append({**s,'id':f"{case}__{s['id']}",'instance_id':case,
                'depends_on':f"{case}__{s['depends_on']}" if s['depends_on'] else None,
                'final_seed':20261025+k})
    return stages


def development_receipt(root):
    root=Path(root).resolve()
    pointer=root/'data/reference_results/phase5_domainwall_training/N27_ACTIVE.json'
    folder=(root/load_json(pointer)['relative_folder']).resolve()
    if not folder.is_relative_to(root):raise ValueError('N27 pointer is outside the repository.')
    c=development.checked_campaign(root,folder);s=development.summarize(root,folder)
    if s['software_validation'] or not s['complete'] or s['objective_cap']!=600:
        raise ValueError('Finish and review the primary N27 campaign before N28.')
    return dict(relative_folder=folder.relative_to(root).as_posix(),
        campaign_sha256=file_hash(folder/'campaign.json'),identity_sha256=c['identity_sha256'],
        completed_stages=len(c['stages']),objective_calls=s['objective_calls_reserved'])


def identity(root, software_validation):
    root=Path(root);data=load_dataset(root);cases=data['validation_instances'];records=[]
    if tuple(x['instance_id'] for x in cases)!=CASE_IDS:raise ValueError('Frozen case order changed.')
    for instance in cases:
        truth=assignment_audit(instance);b=build_three_host_qubo(instance)
        if b['qubo'].get_num_vars()!=25:raise ValueError('Every case must remain 5x3/25 qubits.')
        records.append(dict(input=instance,input_sha256=digest(instance),qubits=25,
            qubo_sha256=qubo_fingerprint(b),optimum=truth['optimum'],
            feasible_assignments=truth['feasible_assignments'],optimal_assignments=truth['optimal_assignments']))
    sources=[p.relative_to(root).as_posix() for p in sorted((root/'src').glob('*.py'))]+[MODULE]
    return dict(study='nt409_domainwall_t4c_v1',software_validation=software_validation,
        dataset_sha256=DATA_HASH,cases=records,protocol=data['planned_training'],
        predecessor=None if software_validation else development_receipt(root),
        source_sha256={name:development._source_hash(root/name) for name in sources},
        runtime=experiment_environment()['runtime'])


def create_campaign(root, output=None, software_validation=False):
    root=Path(root).resolve();plan=make_plan(software_validation);ident=identity(root,software_validation)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=Path(output).resolve() if output else root/'data/reference_results/phase5_domainwall_validation'/f't4c_{stamp}'
    if folder.exists():
        if checked_campaign(root,folder)['identity']!=ident:raise ValueError('Cannot change the campaign mode.')
        return folder
    folder.mkdir(parents=True)
    for name in ident['source_sha256']:
        target=folder/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,target)
    for case in ident['cases']:save_json(folder/'inputs'/f"{case['input']['instance_id']}.json",case['input'])
    save_json(folder/'dataset.json',load_dataset(root))
    save_json(folder/'campaign.json',dict(schema_version=1,created_utc=stamp,identity=ident,
        identity_sha256=digest(ident),plan=plan,stages={}))
    return folder


def checked_campaign(root, folder):
    folder=Path(folder);c=load_json(folder/'campaign.json');ident=c['identity']
    if digest(ident)!=c['identity_sha256'] or ident!=identity(root,ident['software_validation']):
        raise ValueError('Data, protocol, source, runtime or N27 evidence changed.')
    if c['plan']!=make_plan(ident['software_validation']):raise ValueError('Stage plan changed.')
    if load_json(folder/'dataset.json')!=load_dataset(root):raise ValueError('Dataset snapshot changed.')
    for case in ident['cases']:
        if load_json(folder/'inputs'/f"{case['input']['instance_id']}.json")!=case['input']:
            raise ValueError('Input snapshot changed.')
    for name,h in ident['source_sha256'].items():
        if development._source_hash(folder/'source'/name)!=h:raise ValueError('Source snapshot changed.')
    plan={s['id']:s for s in c['plan']}
    if set(c['stages'])-set(plan):raise ValueError('Unknown stage.')
    for key,entry in c['stages'].items():
        path=f'raw/{key}.json'
        if entry['path']!=path or file_hash(folder/path)!=entry['sha256']:raise ValueError('Raw stage hash/path changed.')
        report=load_json(folder/path)
        if report['stage']!=plan[key] or report['status']!=entry['status']:raise ValueError('Raw stage identity/status differs.')
    return c


def build_evaluator(bundle, p, variant, root):
    cases=load_dataset(root)['validation_instances']
    if bundle['instance'] not in cases or bundle['qubo'].get_num_vars()!=25:
        raise ValueError('N28 accepts only the three exact frozen 5x3/25-qubit validation inputs.')
    state,mixer=circuit_components(variant)
    return development.TrainingEvaluator(bundle,p,threads=4,min_available_gib=4.,
        initial_state=state,mixer_operator=mixer)


# Versioned N27 stage loop: only the case source, evaluator guard and seed differ.
# Keep N27 source bytes unchanged so its completed campaign remains verifiable.
def _run_stage(root, folder, c, stage, progress):
    started=perf_counter();p=c['identity']['protocol']
    case=next(x for x in c['identity']['cases'] if x['input']['instance_id']==stage['instance_id'])
    dependency=c['stages'].get(stage['depends_on'])
    point=list(p['initial_p1']) if not stage['depends_on'] else interp_p1_to_p2(
        load_json(folder/dependency['path'])['point'])
    r=dict(stage=stage,status='running',phase='setup',initial_point=point,history=[],
        dependency_sha256=dependency['sha256'] if dependency else None,
        calls=dict(objective=0,final_exact=0,final_sampling=0),
        selection='lowest observed mean energy only; no placement metric in optimizer')
    def save():
        r['elapsed_seconds']=perf_counter()-started;development._record(folder,c,stage,r)
    def guard():
        if psutil.virtual_memory().available/2**30 < p['min_available_gib']:
            raise MemoryError('Available RAM below 4 GiB; keep this stage for review.')
        if perf_counter()-started > p['max_seconds_per_stage']:
            raise TimeoutError('Stage time guard reached between native calls.')
    save();evaluator=None
    try:
        guard();bundle=build_three_host_qubo(case['input'])
        evaluator=build_evaluator(bundle,stage['p'],stage['variant'],root)
        r.update(setup_seconds=perf_counter()-started,phase='optimization',
                 compiled_depth=evaluator.compiled_depth,compiled_ops=evaluator.compiled_ops,
                 offset=evaluator.offset,scale=evaluator.scaling['scale'])
        save()
        def objective(point):
            guard()
            if r['calls']['objective']>=stage['cap']:
                raise RuntimeError('Objective evaluation cap would be exceeded.')
            row=dict(evaluation=len(r['history'])+1,point=np.asarray(point).tolist(),status='in_flight')
            r['history'].append(row);r['calls']['objective']+=1;save()
            call_started=perf_counter();mean=evaluator.mean_energy(point)
            value=(mean-evaluator.offset)/evaluator.scaling['scale']
            if not np.isfinite(mean) or not np.isfinite(value): raise ValueError('Nonfinite energy.')
            row.update(status='completed',mean_energy=mean,optimizer_value=value,
                       evaluation_seconds=perf_counter()-call_started)
            save()
            if progress and (row['evaluation']==1 or row['evaluation']%10==0):
                print(f"  eval {row['evaluation']}/{stage['cap']} | E={mean:.6f}",flush=True)
            guard();return value
        optimizer=RecordingCOBYLA(stage['cap'],p['rhobeg'],p['tol'])
        optimization_started=perf_counter();answer=optimizer(objective,point)
        if optimizer.stop['nfev']!=len(r['history']):
            raise AssertionError('Optimizer and durable ledger evaluation counts differ.')
        best=min(r['history'],key=lambda row:row['mean_energy'])
        r.update(point=best['point'],optimizer_returned_point=answer.x.tolist(),
            optimizer_stop=optimizer.stop,best_mean_energy=best['mean_energy'],
            optimization_seconds=perf_counter()-optimization_started,phase='final_scoring')
        guard();r['calls']['final_exact']+=1;save()
        r['final_exact']=evaluator.exact(r['point']);m=r['final_exact']
        if abs(m['mean_energy']-r['best_mean_energy'])>1e-7:
            raise AssertionError('Final replay differs from the selected training energy.')
        if not (-1e-10<=m['p_ground']<=m['p_opt']+1e-10<=m['p_valid']+2e-10
                <=m['p_domain']+3e-10<=1.+4e-10):
            raise AssertionError('Probability event inclusion failed.')
        if stage['variant']=='valid_dw' and abs(m['p_domain']-1)>1e-10:
            raise AssertionError('The AB circuit leaked outside the assignment domain.')
        if stage['p']==2:
            guard();r['calls']['final_sampling']+=1;save()
            r.update(final_seed=stage['final_seed'],final_shots=p['final_shots'])
            r['final_counts']=evaluator.sample(r['point'],p['final_shots'],stage['final_seed'])
            r['final_measured']=evaluator.score_counts(r['final_counts'])
        guard();r.update(status='completed',phase='done')
    except (Exception,KeyboardInterrupt) as error:
        r.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                 error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(limit=8))
    finally:
        r['completed_objective_calls']=sum(row['status']=='completed' for row in r['history'])
        save();del evaluator;gc.collect()
    return r


def run_campaign(root, folder, max_new_stages=None, instance_id=None, variant=None, progress=True):
    if max_new_stages is not None and (type(max_new_stages) is not int or max_new_stages<1):
        raise ValueError('max_new_stages must be positive or None.')
    if instance_id is not None and instance_id not in CASE_IDS:raise ValueError('Unknown validation instance.')
    if variant is not None and variant not in VARIANTS:raise ValueError('Unknown variant.')
    folder=Path(folder);lock=folder/'RUNNING.lock'
    with lock.open('x',encoding='utf-8') as f:f.write(f'pid={os.getpid()}\n')
    try:
        c=checked_campaign(root,folder)
        if any(e['status']!='completed' for e in c['stages'].values()):
            raise RuntimeError('Incomplete stage retained. Export for review; do not reset its budget.')
        count=0
        for i,stage in enumerate(c['plan']):
            if stage['id'] in c['stages']:continue
            if instance_id and stage['instance_id']!=instance_id:continue
            if variant and stage['variant']!=variant:continue
            if max_new_stages is not None and count>=max_new_stages:break
            if any(previous['id'] not in c['stages'] for previous in c['plan'][:i]):
                raise ValueError('Run the preceding planned case/variant first; do not skip difficult stages.')
            if progress:print('Run',stage['id'],'| 25 qubits | cap',stage['cap'],flush=True)
            result=_run_stage(root,folder,c,stage,progress);count+=1
            if result['status']!='completed':
                if progress:print('STOP:',result.get('error'),flush=True)
                break
        return summarize(root,folder)
    finally:lock.unlink()


def summarize(root, folder):
    folder=Path(folder);c=checked_campaign(root,folder);rows=[]
    for stage in c['plan']:
        row={k:stage[k] for k in ('id','instance_id','variant','p','cap','final_seed')}
        entry=c['stages'].get(stage['id']);row['status']='pending'
        if entry:
            r=load_json(folder/entry['path'])
            row.update(status=r['status'],objective_calls_reserved=r['calls']['objective'],
                objective_calls_completed=r.get('completed_objective_calls',sum(h['status']=='completed' for h in r['history'])),simulation_calls_reserved=sum(r['calls'].values()),
                elapsed_seconds=r['elapsed_seconds'],compiled_depth=r.get('compiled_depth'),
                optimizer_stop=r.get('optimizer_stop'),**r.get('final_exact',{}))
        rows.append(row)
    def totals(selected):
        return dict(complete=all(r['status']=='completed' for r in selected),
            completed_stages=sum(r['status']=='completed' for r in selected),
            objective_cap=sum(r['cap'] for r in selected),
            objective_calls_reserved=sum(r.get('objective_calls_reserved',0) for r in selected),
            objective_calls_completed=sum(r.get('objective_calls_completed',0) for r in selected),
            simulation_calls_reserved=sum(r.get('simulation_calls_reserved',0) for r in selected),
            elapsed_stage_seconds=sum(r.get('elapsed_seconds',0) for r in selected))
    return dict(software_validation=c['identity']['software_validation'],qubits_per_case=25,
        primary_depth=2,rows=rows,**totals(rows),cases=[dict(instance_id=case,**totals([r for r in rows if r['instance_id']==case])) for case in CASE_IDS],
        warning='p2 includes its own p1 cost; cap exhaustion is not convergence; three validation instances only.')


def export_campaign(root, folder):
    folder=Path(folder)
    if (folder/'RUNNING.lock').exists():raise RuntimeError('Wait for the active writer before export.')
    save_json(folder/'summary.json',summarize(root,folder))
    files=sorted(p for p in folder.rglob('*') if p.is_file() and p.name!='SHA256.json')
    save_json(folder/'SHA256.json',{p.relative_to(folder).as_posix():file_hash(p) for p in files})
    archive=folder.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(folder).as_posix())
    return archive


def open_campaign(root):
    """One primary campaign per notebook; completed stages never receive fresh budgets."""
    root=Path(root).resolve();pointer=root/'data/reference_results/phase5_domainwall_validation/N28_ACTIVE.json'
    if pointer.exists():
        folder=(root/load_json(pointer)['relative_folder']).resolve()
        if not folder.is_relative_to(root):raise ValueError('N28 pointer is outside the repository.')
        c=checked_campaign(root,folder)
        if c['identity']['software_validation']:raise ValueError('N28 cannot resume software-validation evidence as a primary run.')
        return folder
    folder=create_campaign(root)
    save_json(pointer,dict(relative_folder=folder.relative_to(root).as_posix()))
    return folder
