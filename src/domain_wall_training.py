"""N27: fixed development-only T4b; durable budgets and no outcome-based tuning."""
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
from time import perf_counter
import traceback
import zipfile

import numpy as np
import psutil

from .domain_wall_mixer import (VARIANTS, validate_fixed_instance,
    circuit_components, domain_probability)
from .shot_noise_diagnostic import ThreeHostEvaluator
from .initialization_campaign import interp_p1_to_p2
from .qaoa_experiment import experiment_environment, qubo_fingerprint
from .qaoa_optimizer import RecordingCOBYLA
from .shot_noise_campaign import load_json, save_json, digest, file_hash
from .three_host_encoding import build_three_host_qubo
from .validation5x3 import load_dataset, DATA_HASH


def make_plan(software_validation=False):
    if type(software_validation) is not bool:
        raise ValueError('software_validation must be boolean.')
    return [dict(id=f'{v}_p{p}',variant=v,p=p,cap=6 if software_validation else 100,
        depends_on=f'{v}_p1' if p==2 else None) for v in VARIANTS for p in (1,2)]


def _source_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def identity(root, software_validation):
    root=Path(root);data=load_dataset(root);instance=data['development_instance']
    bundle=build_three_host_qubo(instance)
    if bundle['qubo'].get_num_vars()!=25:
        raise ValueError('N27 requires the frozen 5x3/25-qubit development instance.')
    return dict(study='nt409_domainwall_t4b_v1',software_validation=software_validation,
        dataset_sha256=DATA_HASH,input=instance,input_sha256=digest(instance),
        qubo_sha256=qubo_fingerprint(bundle),qubits=25,
        protocol=data['planned_training'],
        source_sha256={p.name:_source_hash(p) for p in sorted((root/'src').glob('*.py'))},
        runtime=experiment_environment()['runtime'])


def create_campaign(root, output=None, software_validation=False):
    root=Path(root).resolve();plan=make_plan(software_validation)
    ident=identity(root,software_validation)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=Path(output).resolve() if output else root/'data/reference_results/phase5_domainwall_training'/f't4b_{stamp}'
    if folder.exists():
        c=checked_campaign(root,folder)
        if c['identity']!=ident: raise ValueError('Cannot change scope or runtime on resume.')
        return folder
    folder.mkdir(parents=True)
    for name in ident['source_sha256']:
        target=folder/'source/src'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/'src'/name,target)
    save_json(folder/'input.json',ident['input'])
    save_json(folder/'dataset.json',load_dataset(root))
    save_json(folder/'campaign.json',dict(schema_version=1,created_utc=stamp,
        identity=ident,identity_sha256=digest(ident),plan=plan,stages={}))
    return folder


def checked_campaign(root, folder):
    folder=Path(folder);c=load_json(folder/'campaign.json');ident=c['identity']
    if digest(ident)!=c['identity_sha256'] or ident!=identity(root,ident['software_validation']):
        raise ValueError('Dataset, input, protocol, source, model or runtime changed.')
    if c['plan']!=make_plan(ident['software_validation']):
        raise ValueError('Frozen stage plan changed.')
    if load_json(folder/'input.json')!=ident['input'] or load_json(folder/'dataset.json')!=load_dataset(root):
        raise ValueError('Input/dataset snapshot changed.')
    for name,h in ident['source_sha256'].items():
        if _source_hash(folder/'source/src'/name)!=h: raise ValueError('Source snapshot changed.')
    if set(c['stages'])-{s['id'] for s in c['plan']}:
        raise ValueError('Unknown stage in ledger.')
    for key,entry in c['stages'].items():
        expected=f'raw/{key}.json'
        if entry['path']!=expected or file_hash(folder/expected)!=entry['sha256']:
            raise ValueError('Stage report hash/path changed.')
        report=load_json(folder/expected)
        if report['status']!=entry['status']:
            raise ValueError('Stage report status differs from ledger.')
    return c


class TrainingEvaluator(ThreeHostEvaluator):
    """Score domain and placement in one extra simulation after optimization."""
    def exact(self, point):
        probabilities=self._probabilities(point);d=self.diagonal
        return dict(mean_energy=float(probabilities@d['energies']),
            p_domain=domain_probability(probabilities),
            p_valid=float(probabilities[d['feasible']].sum()),
            p_opt=float(probabilities[d['optimal']].sum()),
            p_ground=float(probabilities[d['ground']].sum()))


def build_evaluator(bundle, p, variant):
    validate_fixed_instance(bundle['instance'])
    if bundle['qubo'].get_num_vars()!=25:
        raise ValueError('Expected the full 25-qubit register.')
    state,mixer=circuit_components(variant)
    return TrainingEvaluator(bundle,p,threads=4,min_available_gib=4.,
                             initial_state=state,mixer_operator=mixer)


def _record(folder, campaign, stage, report):
    path=f"raw/{stage['id']}.json";save_json(folder/path,report)
    campaign['stages'][stage['id']]=dict(path=path,sha256=file_hash(folder/path),status=report['status'])
    save_json(folder/'campaign.json',campaign)


def _run_stage(folder, c, stage, progress):
    started=perf_counter();p=c['identity']['protocol']
    dependency=c['stages'].get(stage['depends_on'])
    point=list(p['initial_p1']) if not stage['depends_on'] else interp_p1_to_p2(
        load_json(folder/dependency['path'])['point'])
    r=dict(stage=stage,status='running',phase='setup',initial_point=point,history=[],
        dependency_sha256=dependency['sha256'] if dependency else None,
        calls=dict(objective=0,final_exact=0,final_sampling=0),
        selection='lowest observed mean energy only; no placement metric in optimizer')
    def save():
        r['elapsed_seconds']=perf_counter()-started;_record(folder,c,stage,r)
    def guard():
        if psutil.virtual_memory().available/2**30 < p['min_available_gib']:
            raise MemoryError('Available RAM below 4 GiB; keep this stage for review.')
        if perf_counter()-started > p['max_seconds_per_stage']:
            raise TimeoutError('Stage time guard reached between native calls.')
    save();evaluator=None
    try:
        guard();bundle=build_three_host_qubo(c['identity']['input'])
        evaluator=build_evaluator(bundle,stage['p'],stage['variant'])
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
            r.update(final_seed=p['final_seed_base'],final_shots=p['final_shots'])
            r['final_counts']=evaluator.sample(r['point'],p['final_shots'],p['final_seed_base'])
            r['final_measured']=evaluator.score_counts(r['final_counts'])
        guard();r.update(status='completed',phase='done')
    except (Exception,KeyboardInterrupt) as error:
        r.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                 error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(limit=8))
    finally:
        r['completed_objective_calls']=sum(row['status']=='completed' for row in r['history'])
        save();del evaluator;gc.collect()
    return r


def run_campaign(root, folder, max_new_stages=None, variant=None, progress=True):
    if max_new_stages is not None and (type(max_new_stages) is not int or max_new_stages<1):
        raise ValueError('max_new_stages must be positive or None.')
    if variant is not None and variant not in VARIANTS: raise ValueError('Unknown variant.')
    folder=Path(folder);lock=folder/'RUNNING.lock'
    with lock.open('x',encoding='utf-8') as f: f.write(f'pid={os.getpid()}\n')
    try:
        c=checked_campaign(root,folder)
        if any(e['status']!='completed' for e in c['stages'].values()):
            raise RuntimeError('Incomplete stage retained. Export for review; do not reset its budget.')
        count=0
        for stage in c['plan']:
            if stage['id'] in c['stages'] or (variant and stage['variant']!=variant): continue
            if max_new_stages is not None and count>=max_new_stages: break
            if stage['depends_on'] and stage['depends_on'] not in c['stages']:
                raise ValueError('Missing preparatory p1 stage.')
            if progress: print('Run',stage['id'],'| 25 qubits | cap',stage['cap'],flush=True)
            result=_run_stage(folder,c,stage,progress);count+=1
            if result['status']!='completed':
                if progress: print('STOP:',result.get('error'),flush=True)
                break
        return summarize(root,folder)
    finally: lock.unlink()


def summarize(root, folder):
    folder=Path(folder);c=checked_campaign(root,folder);rows=[]
    for stage in c['plan']:
        entry=c['stages'].get(stage['id'])
        if not entry:
            rows.append(dict(id=stage['id'],variant=stage['variant'],p=stage['p'],status='pending'))
            continue
        r=load_json(folder/entry['path'])
        rows.append(dict(id=stage['id'],variant=stage['variant'],p=stage['p'],status=r['status'],
            cap=stage['cap'],objective_calls_reserved=r['calls']['objective'],
            objective_calls_completed=r.get('completed_objective_calls',sum(h['status']=='completed' for h in r['history'])),
            simulation_calls_reserved=sum(r['calls'].values()),
            elapsed_seconds=r['elapsed_seconds'],compiled_depth=r.get('compiled_depth'),
            optimizer_stop=r.get('optimizer_stop'),**r.get('final_exact',{})))
    return dict(software_validation=c['identity']['software_validation'],
        instance_id=c['identity']['input']['instance_id'],qubits=25,
        complete=all(r['status']=='completed' for r in rows),
        objective_cap=sum(s['cap'] for s in c['plan']),
        objective_calls_reserved=sum(r.get('objective_calls_reserved',0) for r in rows),
        simulation_calls_reserved=sum(r.get('simulation_calls_reserved',0) for r in rows),
        elapsed_stage_seconds=sum(r.get('elapsed_seconds',0) for r in rows),rows=rows,
        primary_depth=2,warning='p2 includes its own p1 cost; cap exhaustion is not convergence.')


def open_campaign(root):
    """Notebook re-execution reuses one primary campaign, including completed ones."""
    root=Path(root).resolve();pointer=root/'data/reference_results/phase5_domainwall_training/N27_ACTIVE.json'
    if pointer.exists():
        relative=load_json(pointer)['relative_folder'];folder=(root/relative).resolve()
        if not folder.is_relative_to(root): raise ValueError('Campaign pointer is outside the repo.')
        c=checked_campaign(root,folder)
        if c['identity']['software_validation']: raise ValueError('N27 cannot resume a software-validation campaign.')
        return folder
    folder=create_campaign(root)
    save_json(pointer,dict(relative_folder=folder.relative_to(root).as_posix()))
    return folder


def export_campaign(root, folder):
    folder=Path(folder)
    if (folder/'RUNNING.lock').exists(): raise RuntimeError('Wait for the writer to finish before export.')
    save_json(folder/'summary.json',summarize(root,folder))
    files=sorted(p for p in folder.rglob('*') if p.is_file() and p.name!='SHA256.json')
    save_json(folder/'SHA256.json',{p.relative_to(folder).as_posix():file_hash(p) for p in files})
    archive=folder.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(folder).as_posix())
    return archive
