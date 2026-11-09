"""Notebook 24: exact mean versus lower-tail CVaR with charged INTERP.

Persisted Notebook 22/23 code stays immutable so old campaigns remain resumable.
The original CVaR boundary rule is reused; only the 25-qubit evaluator is new.
"""
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
from time import perf_counter
import traceback
import zipfile

import numpy as np
import psutil

from .shot_noise_campaign import (load_json, save_json, digest, file_hash,
    identity as model_identity, SOURCES as MODEL_SOURCES)
from .initialization_campaign import record_trial, resolved_config
from .shot_noise_diagnostic import ThreeHostEvaluator, calibrate
from .cvar_experiment import lower_tail_cvar
from .three_host_encoding import build_three_host_qubo
from .qaoa_experiment import qubo_fingerprint
from .qaoa_optimizer import RecordingCOBYLA
from .ising import build_ising, scale_ising

PROTOCOL = 'data/benchmarks/nt409_cvar_v1/protocol.json'
SOURCES = MODEL_SOURCES + ['initialization_campaign.py', 'cvar_experiment.py',
    'convergence_diagnostics.py', 'convergence_campaign.py', 'independent_campaign.py',
    'penalty_analysis.py', 'cvar_campaign.py']
ALPHAS = [1., .25, .1]
GROUPS = ['p2__mean', 'p2__cvar_025', 'p2__cvar_010']


def make_plan(protocol):
    total, local = protocol['total_budget'], protocol['local_budget']
    if (type(total) is not int or type(local) is not int or total != 2*local
            or local < 6 or protocol['alphas'] != ALPHAS
            or any(type(a) not in (int,float) for a in protocol['alphas'])):
        raise ValueError('Use fixed alphas [1,.25,.1] and total=2*local >=12.')
    plan=[]
    for group,alpha in zip(GROUPS,ALPHAS):
        parent=None
        for p,a in [(1,1.),(2,alpha)]:
            config={k:protocol[k] for k in ['shots','final_shots','rhobeg','tol',
                                           'max_seconds','min_available_gib']}
            config.update(maxiter=local,initial_point=[.3,1.] if p==1 else None,
                          seed=0,final_seed=60000000+len(plan))
            item=dict(id=f'{group}__stage{p}',group=group,p=p,alpha=a,
                target_alpha=alpha,instance_id=protocol['instances'][0]['instance_id'],
                start='anchor' if p==1 else 'interp',depends_on=parent,config=config)
            plan.append(item);parent=item['id']
    return plan


def identity(root,protocol):
    if (type(protocol['software_validation']) is not bool
            or protocol['study_id']!='nt409_cvar_v1'
            or protocol['maxiter']!=protocol['total_budget']
            or protocol['depths']!=[1,2] or protocol['seeds']!=[400]
            or protocol['noise_batches']!=1):
        raise ValueError('Use the frozen Notebook24 protocol.')
    make_plan(protocol)
    ident=model_identity(root,protocol)
    bundle=build_three_host_qubo(next(iter(ident['inputs'].values())))
    if qubo_fingerprint(bundle)!=protocol['instances'][0]['qubo_sha256']:
        raise ValueError('Frozen QUBO differs.')
    _,scaling=scale_ising(build_ising(bundle)[0],'max_abs')
    ident['model']=dict(qubits=bundle['qubo'].get_num_vars(),scale=scaling['scale'])
    for name in SOURCES:
        ident['source_sha256'][name]=hashlib.sha256((Path(root)/'src'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    return ident


class CVaREvaluator(ThreeHostEvaluator):
    """Aggregate fixed integer QUBO energies; never sort 2**25 states per call."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        energy=self.diagonal['energies']
        if energy.min()<0 or energy.max()>100000 or not np.equal(energy,np.rint(energy)).all():
            raise ValueError('The frozen integer-energy histogram model is required.')
        self.energy_index=energy.astype(np.int32)
        self.levels=np.arange(int(self.energy_index.max())+1,dtype=float)

    def objectives(self,point,alphas):
        # Validate even alpha=1 (bool is not an alpha).
        if any(type(a) not in (int,float) or not np.isfinite(a) or not 0<a<=1 for a in alphas):
            raise ValueError('CVaR alpha must be finite in (0,1].')
        probabilities=self._probabilities(point)
        mean=float(probabilities@self.diagonal['energies'])
        values={'1.0':mean}
        if any(a!=1 for a in alphas):
            mass=np.bincount(self.energy_index,weights=probabilities,minlength=len(self.levels))
            values.update({str(float(a)):lower_tail_cvar(self.levels,mass,a) for a in alphas if a!=1})
        return values


def build_evaluator(campaign,item):
    bundle=build_three_host_qubo(campaign['identity']['inputs'][item['instance_id']])
    expected=campaign['identity']['protocol']['instances'][0]
    if qubo_fingerprint(bundle)!=expected['qubo_sha256']:
        raise ValueError('Frozen QUBO differs.')
    p=campaign['identity']['protocol']
    return CVaREvaluator(bundle,item['p'],p['threads'],p['min_available_gib'])



def create_campaign(root, output=None, protocol=None):
    root = Path(root).resolve()
    protocol = load_json(root/PROTOCOL) if protocol is None else protocol
    ident = identity(root, protocol)
    plan = make_plan(protocol)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = Path(output).resolve() if output else root/'data/reference_results/phase4p_cvar'/f'cvar_{stamp}'
    if (folder/'campaign.json').exists():
        old = checked_campaign(root, folder)
        if old['identity'] != ident or old['plan'] != plan:
            raise ValueError('Changed protocol cannot resume this campaign.')
        return folder
    folder.mkdir(parents=True, exist_ok=False)
    for name in SOURCES:
        target = folder/'source/src'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root/'src'/name, target)
    save_json(folder/'protocol.json', protocol)
    for name, value in ident['inputs'].items():
        save_json(folder/'inputs'/f'{name}.json', value)
    save_json(folder/'campaign.json', dict(schema_version=1, created_utc=stamp,
        identity=ident, identity_sha256=digest(ident), plan=plan, trials={}, profiles={}))
    return folder


def checked_campaign(root, folder):
    folder = Path(folder)
    c = load_json(folder/'campaign.json')
    if c['identity_sha256'] != digest(c['identity']) or c['identity'] != identity(root,c['identity']['protocol']):
        raise ValueError('Source, runtime, input or protocol changed.')
    if c['plan'] != make_plan(c['identity']['protocol']):
        raise ValueError('Resolved plan differs.')
    if load_json(folder/'protocol.json') != c['identity']['protocol']:
        raise ValueError('Protocol snapshot differs.')
    for name, value in c['identity']['inputs'].items():
        if load_json(folder/'inputs'/f'{name}.json') != value:
            raise ValueError('Input snapshot differs.')
    for name, value in c['identity']['source_sha256'].items():
        if hashlib.sha256((folder/'source/src'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() != value:
            raise ValueError('Source snapshot differs.')
    if set(c['trials']) - {t['id'] for t in c['plan']}:
        raise ValueError('Unknown trials in ledger.')
    for entry in list(c['trials'].values()) + list(c['profiles'].values()):
        if file_hash(folder/entry['path']) != entry['sha256']:
            raise ValueError('Report checksum differs: '+entry['path'])
    return c


@contextmanager
def writer(root, folder):
    lock = Path(folder)/'RUNNING.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(f'pid={os.getpid()}\n')
    try:
        yield checked_campaign(root, folder)
    finally:
        lock.unlink()


def train(evaluator,config,alpha,progress=True):
    """Optimize only the declared objective; placement labels are post-training."""
    started=perf_counter()
    report=dict(mode='exact_objective',objective_alpha=alpha,config=dict(config),history=[],status='running')
    def guard():
        if psutil.virtual_memory().available/2**30<config['min_available_gib']:
            raise MemoryError('Available RAM is below the diagnostic minimum.')
        if perf_counter()-started>config['max_seconds']:
            raise TimeoutError('Per-run time guard reached between native calls.')
    def objective(point):
        guard()
        values=evaluator.objectives(point,[alpha]);raw=values[str(float(alpha))]
        normalized=(raw-evaluator.offset)/evaluator.scaling['scale']
        row=dict(evaluation=len(report['history'])+1,point=np.asarray(point).tolist(),
            mean_energy=values['1.0'],raw_objective=raw,optimizer_value=normalized,
            seconds=perf_counter()-started)
        report['history'].append(row)
        if progress and (row['evaluation']==1 or row['evaluation']%25==0):
            print(f"  alpha={alpha:g} eval {row['evaluation']}: objective={raw:.6f}; E={values['1.0']:.6f}",flush=True)
        guard()
        return normalized
    try:
        guard()
        optimizer=RecordingCOBYLA(config['maxiter'],config['rhobeg'],config['tol'])
        result=optimizer(objective,config['initial_point'])
        report.update(point=result.x.tolist(),optimizer_value=float(result.fun),
            optimizer_stop=optimizer.stop,optimization_seconds=perf_counter()-started)
        if len(report['history'])!=optimizer.stop['nfev']:
            raise ValueError('Optimizer and recorded evaluation counts differ.')
        guard();report['final_exact']=evaluator.exact(result.x)
        guard();report['final_objectives']=evaluator.objectives(result.x,ALPHAS)
        guard();counts=evaluator.sample(result.x,config['final_shots'],config['final_seed'])
        report.update(final_counts=counts,final_measured=evaluator.score_counts(counts))
        guard();report['status']='completed'
    except (Exception,KeyboardInterrupt) as error:
        report.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
            error=str(error),error_type=type(error).__name__,traceback=traceback.format_exc(limit=8))
    report.update(nfev=len(report['history']),elapsed_seconds=perf_counter()-started,training_shots=0)
    return report


def run_campaign(root,folder,max_new_trials=None,groups=None,progress=True):
    if max_new_trials is not None and (type(max_new_trials) is not int or max_new_trials<1):
        raise ValueError('max_new_trials must be positive or None.')
    folder=Path(folder)
    with writer(root,folder) as c:
        if groups is not None and (not groups or len(set(groups))!=len(groups) or set(groups)-set(GROUPS)):
            raise ValueError('groups must be a nonempty subset of planned group IDs.')
        evaluators={};count=0
        for item in c['plan']:
            if groups is not None and item['group'] not in groups:continue
            old=c['trials'].get(item['id'])
            if old and old['status']=='completed':continue
            if old:
                if progress:print('Incomplete trial retained; budget cannot be reset:',item['id'])
                break
            if max_new_trials is not None and count>=max_new_trials:break
            config,dependency_hash=resolved_config(c,item,folder)
            metadata=dict(id=item['id'],plan=item,dependency_sha256=dependency_hash)
            record_trial(folder,c,item,dict(**metadata,mode='exact_objective',objective_alpha=item['alpha'],
                config=config,status='running',nfev=None,history=[]))
            if progress:print('Run',item['id'],'| alpha',item['alpha'],'| cap',config['maxiter'],flush=True)
            try:
                if item['p'] not in evaluators:evaluators[item['p']]=build_evaluator(c,item)
                report=train(evaluators[item['p']],config,item['alpha'],progress)
            except (Exception,KeyboardInterrupt) as error:
                report=dict(mode='exact_objective',objective_alpha=item['alpha'],config=config,
                    status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                    nfev=None,history=[],error=str(error),error_type=type(error).__name__,
                    traceback=traceback.format_exc(limit=8))
            report.update(metadata);record_trial(folder,c,item,report);count+=1
            if report['status']!='completed':break
    return summarize(folder)


def summarize(folder):
    folder=Path(folder);c=load_json(folder/'campaign.json');rows=[]
    for group in GROUPS:
        items=[t for t in c['plan'] if t['group']==group]
        reports=[load_json(folder/c['trials'][t['id']]['path']) for t in items if t['id'] in c['trials']]
        complete=len(reports)==2 and all(r['status']=='completed' for r in reports)
        row=dict(group=group,objective_alpha=items[-1]['alpha'],trials_completed=sum(r['status']=='completed' for r in reports),
            status='completed' if complete else ('failed' if any(r['status']!='completed' for r in reports) else 'pending'),
            budget_cap=sum(t['config']['maxiter'] for t in items),
            nfev=None if any(r['nfev'] is None for r in reports) else sum(r['nfev'] for r in reports),
            diagnostic_exact_calls=sum(('final_exact' in r)+('final_objectives' in r) for r in reports),
            final_measurement_shots=sum(sum(r.get('final_counts',{}).values()) for r in reports))
        if complete:
            final=reports[-1];v=final['final_objectives'];m=final['final_exact']
            row.update(selected_trial=final['id'],selected_point=final['point'],
                mean_energy=m['mean_energy'],cvar_025=v['0.25'],cvar_010=v['0.1'],
                raw_objective=v[str(float(items[-1]['alpha']))],p_opt=m['p_opt'],p_valid=m['p_valid'],
                p_ground=m['p_ground'],optimal_count=final['final_measured']['optimal_count'],
                seconds=sum(r['elapsed_seconds'] for r in reports))
        rows.append(row)
    coverage=dict(planned=3,completed=sum(r['status']=='completed' for r in rows),
        failed=sum(r['status']=='failed' for r in rows),pending=sum(r['status']=='pending' for r in rows))
    return dict(status='complete' if coverage['completed']==3 else 'partial',
        software_validation=c['identity']['protocol']['software_validation'],coverage=coverage,
        optimizer_trials_planned=6,rows=rows)


def prepare_campaign(root,folder,progress=True):
    folder=Path(folder);rows=[]
    with writer(root,folder) as c:
        protocol=c['identity']['protocol']
        for p in [1,2]:
            key=str(p)
            if key not in c['profiles']:
                if progress:print('Profile depth',p,flush=True)
                e=build_evaluator(c,next(t for t in c['plan'] if t['p']==p))
                point=[.3]+[0.]*(p-1)+[1.]+[0.]*(p-1)
                profile=calibrate(e,point,protocol['final_shots'],1,65000000+p,progress)
                profile.update(p=p,qubits=e.size,objective_seconds={},objective_values={})
                for a in ([1.] if p==1 else ALPHAS):
                    started=perf_counter();v=e.objectives(point,[a])
                    profile['objective_seconds'][str(a)]=perf_counter()-started
                    profile['objective_values'][str(a)]=v[str(a)]
                path=f'profiles/p{p}.json';save_json(folder/path,profile)
                c['profiles'][key]=dict(path=path,sha256=file_hash(folder/path))
                save_json(folder/'campaign.json',c);del e
            profile=load_json(folder/c['profiles'][key]['path'])
            rows.append(dict(p=p,qubits=profile['qubits'],objective_seconds=profile['objective_seconds'],
                measurement_seconds=profile['batches'][0]['seconds']))
        costs={r['p']:r['objective_seconds'] for r in rows}
        strategies=[dict(group=g,cap=protocol['total_budget'],training_cap_hours=sum(
            t['config']['maxiter']*costs[t['p']][str(t['alpha'])] for t in c['plan'] if t['group']==g)/3600) for g in GROUPS]
    return dict(profiles=rows,strategies=strategies)


def audit_campaign(root,folder,replay=True):
    folder=Path(folder);c=checked_campaign(root,folder);evaluators={}
    def evaluator(item):
        if item['p'] not in evaluators:evaluators[item['p']]=build_evaluator(c,item)
        return evaluators[item['p']]
    def equal(actual,saved):
        if actual.keys()!=saved.keys() or any(not np.isclose(actual[k],v,atol=1e-8,rtol=1e-9) for k,v in saved.items()):
            raise ValueError('Exact endpoint or CVaR replay differs.')
    for key,entry in c['profiles'].items():
        item=next(t for t in c['plan'] if str(t['p'])==key);e=evaluator(item)
        r=load_json(folder/entry['path']);point=[.3]+[0.]*(item['p']-1)+[1.]+[0.]*(item['p']-1)
        if (r['point']!=point or len(r['batches'])!=1 or r['p']!=item['p'] or r['qubits']!=e.size
                or r['shots']!=c['identity']['protocol']['final_shots']):
            raise ValueError('Profile design differs.')
        batch=r['batches'][0];alphas=[1.] if item['p']==1 else ALPHAS
        if (batch['seed']!=65000000+item['p'] or sum(batch['counts'].values())!=r['shots']
                or e.score_counts(batch['counts'])['mean_energy']!=batch['mean_energy']
                or set(r['objective_seconds'])!={str(a) for a in alphas}
                or any(not np.isfinite(v) or v<=0 for v in r['objective_seconds'].values())):
            raise ValueError('Profile counts or objective costs differ.')
        if replay:
            equal(e.exact(point),r['exact']);equal(e.objectives(point,alphas),r['objective_values'])
    checked=0;starts=[]
    for item in c['plan']:
        if item['id'] not in c['trials']:continue
        entry=c['trials'][item['id']];r=load_json(folder/entry['path'])
        config,dependency_hash=resolved_config(c,item,folder)
        if (r['plan']!=item or r['config']!=config or r['dependency_sha256']!=dependency_hash
                or r['id']!=item['id'] or r['mode']!='exact_objective'
                or r['objective_alpha']!=item['alpha'] or r['status']!=entry['status']):
            raise ValueError('Trial identity, objective or INTERP dependency differs.')
        if r['nfev'] is not None and (type(r['nfev']) is not int or not 0<=r['nfev']==len(r['history'])<=config['maxiter']):
            raise ValueError('Trial exceeded its local evaluation budget.')
        if r['status']!='completed':continue
        e=evaluator(item);minimum=float(e.diagonal['energies'].min())
        if not r['history'] or r['history'][0]['point']!=config['initial_point'] or r['optimizer_stop']['nfev']!=r['nfev']:
            raise ValueError('Initial point or optimizer evaluation count differs.')
        for j,h in enumerate(r['history']):
            e._point(h['point'])
            if (h['evaluation']!=j+1 or not np.isfinite([h['raw_objective'],h['mean_energy'],h['optimizer_value']]).all()
                    or h['raw_objective']>h['mean_energy']+1e-8
                    or h['raw_objective']<minimum-1e-8
                    or (item['alpha']==1 and h['raw_objective']!=h['mean_energy'])
                    or not np.isclose(h['optimizer_value'],(h['raw_objective']-e.offset)/e.scaling['scale'],atol=1e-10,rtol=0)):
                raise ValueError('Objective history or energy units differ.')
        if not any(h['point']==r['point'] and np.isclose(h['optimizer_value'],r['optimizer_value'],atol=1e-9,rtol=0) for h in r['history']):
            raise ValueError('Returned point is missing from training history.')
        v=r['final_objectives'];m=r['final_exact']
        if (set(v)!={str(a) for a in ALPHAS} or not np.isfinite(list(v.values())).all()
                or not minimum-1e-8<=v['0.1']<=v['0.25']+1e-8<=v['1.0']+2e-8
                or not np.isclose(v['1.0'],m['mean_energy'],atol=1e-8,rtol=0)
                or r['training_shots']!=0 or sum(r['final_counts'].values())!=config['final_shots']
                or e.score_counts(r['final_counts'])!=r['final_measured']
                or not np.isclose(r['optimizer_value'],(v[str(item['alpha'])]-e.offset)/e.scaling['scale'],atol=1e-8,rtol=0)):
            raise ValueError('Endpoint objective, mean or counts differ.')
        if replay:
            equal(e.exact(r['point']),m);equal(e.objectives(r['point'],ALPHAS),v)
        if item['p']==2:starts.append(config['initial_point'])
        checked+=1
    common_start=all(np.allclose(start,starts[0],atol=1e-10,rtol=0) for start in starts) if starts else None
    if common_start is False:raise ValueError('Objective controls did not use the same INTERP start.')
    summary=summarize(folder)
    if any(r['budget_cap']!=c['identity']['protocol']['total_budget'] or (r['nfev'] is not None and r['nfev']>r['budget_cap']) for r in summary['rows']):
        raise ValueError('Strategy exceeded its total evaluation cap.')
    return dict(status='PASS',complete=summary['status']=='complete',coverage=summary['coverage'],
        completed_trials_checked=checked,endpoint_replay=replay,common_p2_start=common_start,
        meaning='Consistency, objective and budget checks; not proof of QAOA improvement.')


def export_campaign(root,folder):
    folder=Path(folder)
    with writer(root,folder):
        audit=audit_campaign(root,folder);summary=summarize(folder)
        save_json(folder/'audit.json',audit);save_json(folder/'summary.json',summary)
        rows=summary['rows']
        with (folder/'strategies.csv').open('w',encoding='utf-8',newline='') as handle:
            columns=list(dict.fromkeys(k for row in rows for k in row))
            output=csv.DictWriter(handle,fieldnames=columns);output.writeheader();output.writerows(rows)
        paths=sorted(p for p in folder.rglob('*') if p.is_file() and p.name not in ['SHA256.json','RUNNING.lock'] and not p.name.endswith('.tmp'))
        save_json(folder/'SHA256.json',{p.relative_to(folder).as_posix():file_hash(p) for p in paths})
        archive=folder.parent/(folder.name+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for path in paths+[folder/'SHA256.json']:z.write(path,path.relative_to(folder).as_posix())
    return archive
