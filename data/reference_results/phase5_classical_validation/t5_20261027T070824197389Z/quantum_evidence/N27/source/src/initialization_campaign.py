"""Notebook 23: bounded initialization strategies on the fixed reference."""
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import traceback
import zipfile

import numpy as np

from .shot_noise_campaign import (load_json, save_json, digest, file_hash,
    identity as model_identity, SOURCES as MODEL_SOURCES, build_evaluator)
from .shot_noise_diagnostic import train, calibrate
from .three_host_encoding import build_three_host_qubo
from .qaoa_experiment import qubo_fingerprint
from .ising import build_ising, scale_ising

PROTOCOL = 'data/benchmarks/nt409_initialization_v1/protocol.json'
SOURCES = MODEL_SOURCES + ['initialization_campaign.py']


def interp_p1_to_p2(point):
    """Zhou et al., PRX 10 021067, Eq B1 at p=1; beta before gamma."""
    point = np.asarray(point, dtype=float)
    if point.shape != (2,) or not np.isfinite(point).all():
        raise ValueError('INTERP requires a finite p=1 point [beta,gamma].')
    return [float(point[0])]*2 + [float(point[1])]*2


def make_plan(protocol, scale):
    total, local = protocol['total_budget'], protocol['local_budget']
    if (type(total) is not int or type(local) is not int or total != 2*local
            or local < 6 or not np.isfinite(scale) or scale <= 0):
        raise ValueError('Use total=2*local, with at least six evaluations per stage.')
    plan = []

    def add(strategy, depth, seed, stages):
        group = f'p{depth}__{strategy}' + (f'_{seed}' if seed is not None else '')
        dependency = None
        for stage, (p, start, point, cap) in enumerate(stages):
            config = {k: protocol[k] for k in ['shots', 'final_shots', 'rhobeg', 'tol',
                                               'max_seconds', 'min_available_gib']}
            config.update(maxiter=cap, initial_point=point, seed=0,
                          final_seed=50000000+len(plan))
            item = dict(id=f'{group}__stage{stage+1}', group=group,
                strategy=strategy, target_depth=depth, init_seed=seed, p=p,
                start=start, instance_id=protocol['instances'][0]['instance_id'],
                depends_on=dependency if start=='interp' else None, config=config)
            plan.append(item)
            dependency = item['id']

    for p in protocol['depths']:
        anchor = [.3]+[0.]*(p-1)+[1.]+[0.]*(p-1)
        add('single', p, None, [(p, 'anchor', anchor, total)])
        for seed in protocol['seeds']:
            rng = np.random.default_rng(seed+10000*p)
            point = np.r_[rng.uniform(0, np.pi, p),
                          rng.uniform(0, 2*np.pi*scale, p)].tolist()
            add('multistart', p, seed, [(p, 'anchor', anchor, local),
                                       (p, 'random', point, local)])
        if p == 2:
            add('interp', 2, None, [(1, 'anchor', [.3,1.], local),
                                   (2, 'interp', None, local)])
    return plan


def identity(root, protocol):
    if type(protocol['software_validation']) is not bool:
        raise ValueError('software_validation must be boolean.')
    if protocol['maxiter'] != protocol['total_budget']:
        raise ValueError('maxiter must equal the total strategy cap.')
    if protocol['study_id'] != 'nt409_initialization_v1' or protocol['noise_batches'] != 1:
        raise ValueError('Use the Notebook23 protocol with one profiling batch.')
    ident = model_identity(root, protocol)
    bundle = build_three_host_qubo(next(iter(ident['inputs'].values())))
    if qubo_fingerprint(bundle) != protocol['instances'][0]['qubo_sha256']:
        raise ValueError('Frozen QUBO differs.')
    _, scaling = scale_ising(build_ising(bundle)[0], 'max_abs')
    ident['model'] = dict(qubits=bundle['qubo'].get_num_vars(), scale=scaling['scale'])
    path = Path(root)/'src/initialization_campaign.py'
    ident['source_sha256'][path.name] = hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    make_plan(protocol, scaling['scale'])
    return ident


def create_campaign(root, output=None, protocol=None):
    root = Path(root).resolve()
    protocol = load_json(root/PROTOCOL) if protocol is None else protocol
    ident = identity(root, protocol)
    plan = make_plan(protocol, ident['model']['scale'])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = Path(output).resolve() if output else root/'data/reference_results/phase4o_initialization'/f'init_{stamp}'
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
    if c['plan'] != make_plan(c['identity']['protocol'],c['identity']['model']['scale']):
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


def resolved_config(campaign, item, folder):
    config = dict(item['config'])
    dependency_hash = None
    if item['depends_on']:
        entry = campaign['trials'][item['depends_on']]
        parent = load_json(Path(folder)/entry['path'])
        if parent['status'] != 'completed':
            raise ValueError('INTERP requires a completed preparatory trial.')
        config['initial_point'] = interp_p1_to_p2(parent['point'])
        dependency_hash = entry['sha256']
    return config, dependency_hash


def record_trial(folder, campaign, item, report):
    path = f"raw/{item['id']}.json"
    save_json(Path(folder)/path, report)
    campaign['trials'][item['id']] = dict(path=path, sha256=file_hash(Path(folder)/path),
                                         status=report['status'])
    save_json(Path(folder)/'campaign.json', campaign)


def run_campaign(root, folder, max_new_trials=None, groups=None, progress=True):
    if max_new_trials is not None and (type(max_new_trials) is not int or max_new_trials < 1):
        raise ValueError('max_new_trials must be positive or None.')
    folder = Path(folder)
    with writer(root, folder) as c:
        all_groups = {t['group'] for t in c['plan']}
        if groups is not None and (not groups or len(set(groups))!=len(groups) or set(groups)-all_groups):
            raise ValueError('groups must be a nonempty subset of planned group IDs.')
        evaluators = {}
        count = 0
        for item in c['plan']:
            if groups is not None and item['group'] not in groups:
                continue
            old = c['trials'].get(item['id'])
            if old and old['status'] == 'completed':
                continue
            if old:
                if progress: print('Incomplete trial retained; budget cannot be reset:', item['id'])
                break
            if max_new_trials is not None and count >= max_new_trials:
                break
            config, dependency_hash = resolved_config(c, item, folder)
            metadata = dict(id=item['id'], plan=item, dependency_sha256=dependency_hash)
            # Reserve before native work: a killed process cannot silently reset its budget.
            record_trial(folder, c, item, dict(**metadata, mode='exact', config=config,
                         status='running', nfev=None, history=[]))
            if progress: print('Run', item['id'], '| cap', config['maxiter'], flush=True)
            try:
                if item['p'] not in evaluators:
                    evaluators[item['p']] = build_evaluator(c, item)
                report = train(evaluators[item['p']], config, 'exact', progress)
            except (Exception, KeyboardInterrupt) as error:
                report = dict(mode='exact', config=config, status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                    nfev=0, history=[], error=str(error), error_type=type(error).__name__,
                    traceback=traceback.format_exc(limit=8))
            report.update(metadata)
            record_trial(folder, c, item, report)
            count += 1
            if report['status'] != 'completed':
                break
    return summarize(folder)


def choose_result(reports, target_depth):
    candidates = [r for r in reports if r['plan']['p']==target_depth]
    return min(candidates, key=lambda r:r['optimizer_value'])


def summarize(folder):
    folder = Path(folder)
    c = load_json(folder/'campaign.json')
    rows = []
    for group in dict.fromkeys(t['group'] for t in c['plan']):
        items = [t for t in c['plan'] if t['group']==group]
        reports = [load_json(folder/c['trials'][t['id']]['path']) for t in items if t['id'] in c['trials']]
        complete = len(reports)==len(items) and all(r['status']=='completed' for r in reports)
        row = dict(group=group, strategy=items[0]['strategy'], target_depth=items[0]['target_depth'],
            init_seed=items[0]['init_seed'], trials=len(items), trials_completed=sum(r['status']=='completed' for r in reports),
            status='completed' if complete else ('failed' if any(r['status']!='completed' for r in reports) else 'pending'),
            budget_cap=sum(t['config']['maxiter'] for t in items),
            nfev=None if any(r['nfev'] is None for r in reports) else sum(r['nfev'] for r in reports),
            diagnostic_exact_calls=sum('final_exact' in r for r in reports),
            final_measurement_shots=sum(sum(r.get('final_counts',{}).values()) for r in reports))
        if complete:
            best = choose_result(reports, row['target_depth'])
            row.update(selected_trial=best['id'], mean_energy=best['final_exact']['mean_energy'],
                p_opt=best['final_exact']['p_opt'], p_valid=best['final_exact']['p_valid'],
                p_ground=best['final_exact']['p_ground'], seconds=sum(r['elapsed_seconds'] for r in reports),
                selected_point=best['point'], optimal_count=best['final_measured']['optimal_count'])
        rows.append(row)
    comparisons = []
    for p in c['identity']['protocol']['depths']:
        for strategy in dict.fromkeys(r['strategy'] for r in rows if r['target_depth']==p):
            all_rows = [r for r in rows if r['target_depth']==p and r['strategy']==strategy]
            done = [r for r in all_rows if r['status']=='completed']
            comparison = dict(p=p, strategy=strategy, completed=len(done), planned=len(all_rows))
            if done:
                comparison.update(p_opt_mean=float(np.mean([r['p_opt'] for r in done])),
                    p_opt_min=min(r['p_opt'] for r in done), p_opt_max=max(r['p_opt'] for r in done),
                    p_valid_mean=float(np.mean([r['p_valid'] for r in done])),
                    energy_mean=float(np.mean([r['mean_energy'] for r in done])),
                    nfev_mean=float(np.mean([r['nfev'] for r in done])))
            comparisons.append(comparison)
    coverage = dict(planned=len(rows), completed=sum(r['status']=='completed' for r in rows),
                    failed=sum(r['status']=='failed' for r in rows), pending=sum(r['status']=='pending' for r in rows))
    return dict(status='complete' if coverage['completed']==coverage['planned'] else 'partial',
        software_validation=c['identity']['protocol']['software_validation'], coverage=coverage,
        optimizer_trials_planned=len(c['plan']), rows=rows, comparisons=comparisons)


def prepare_campaign(root, folder, progress=True):
    folder = Path(folder)
    profiles = []
    with writer(root, folder) as c:
        protocol = c['identity']['protocol']
        for p in sorted({t['p'] for t in c['plan']}):
            key = str(p)
            if key not in c['profiles']:
                item = next(t for t in c['plan'] if t['p']==p)
                if progress: print('Profile depth',p,flush=True)
                evaluator = build_evaluator(c,item)
                point = [.3]+[0.]*(p-1)+[1.]+[0.]*(p-1)
                profile = calibrate(evaluator,point,protocol['final_shots'],1,55000000+p,progress)
                profile.update(p=p,qubits=evaluator.size)
                path = f'profiles/p{p}.json'
                save_json(folder/path,profile)
                c['profiles'][key] = dict(path=path,sha256=file_hash(folder/path))
                save_json(folder/'campaign.json',c)
                del evaluator
            profile = load_json(folder/c['profiles'][key]['path'])
            profiles.append(dict(p=p,qubits=profile['qubits'],exact_seconds=profile['exact_seconds'],
                                 measurement_seconds=profile['batches'][0]['seconds']))
        costs = {r['p']:r['exact_seconds'] for r in profiles}
        strategies = [dict(group=g,cap=sum(t['config']['maxiter'] for t in c['plan'] if t['group']==g),
            training_cap_hours=sum(t['config']['maxiter']*costs[t['p']] for t in c['plan'] if t['group']==g)/3600)
            for g in dict.fromkeys(t['group'] for t in c['plan'])]
    return dict(profiles=profiles,strategies=strategies)


def audit_campaign(root, folder, replay=True):
    folder = Path(folder)
    c = checked_campaign(root,folder)
    evaluators = {}
    def evaluator(item):
        if item['p'] not in evaluators:
            evaluators[item['p']] = build_evaluator(c,item)
        return evaluators[item['p']]
    def replay_exact(e,point,saved):
        if replay:
            actual = e.exact(point)
            if actual.keys()!=saved.keys() or any(not np.isclose(actual[k],v,atol=1e-8,rtol=1e-9) for k,v in saved.items()):
                raise ValueError('Exact endpoint replay differs.')
    for key, entry in c['profiles'].items():
        item = next(t for t in c['plan'] if str(t['p'])==key)
        e = evaluator(item)
        r = load_json(folder/entry['path'])
        point = [.3]+[0.]*(item['p']-1)+[1.]+[0.]*(item['p']-1)
        batch = r['batches'][0]
        if (r['point']!=point or len(r['batches'])!=1 or r['p']!=item['p'] or r['qubits']!=e.size
                or r['shots']!=c['identity']['protocol']['final_shots']
                or batch['seed']!=55000000+item['p'] or sum(batch['counts'].values())!=r['shots']
                or e.score_counts(batch['counts'])['mean_energy']!=batch['mean_energy']):
            raise ValueError('Profile design or counts differ.')
        replay_exact(e,point,r['exact'])
    checked = 0
    for item in c['plan']:
        if item['id'] not in c['trials']:
            continue
        entry = c['trials'][item['id']]
        r = load_json(folder/entry['path'])
        config, dependency_hash = resolved_config(c,item,folder)
        if (r['plan']!=item or r['config']!=config or r['dependency_sha256']!=dependency_hash
                or r['id']!=item['id'] or r['mode']!='exact' or r['status']!=entry['status']):
            raise ValueError('Trial identity, start or INTERP dependency differs.')
        if r['nfev'] is not None and (type(r['nfev']) is not int or not 0<=r['nfev']==len(r['history'])<=config['maxiter']):
            raise ValueError('Trial exceeded its local evaluation budget.')
        if r['status']!='completed':
            continue
        e = evaluator(item)
        if not r['history'] or r['history'][0]['point']!=config['initial_point'] or r['optimizer_stop']['nfev']!=r['nfev']:
            raise ValueError('Initial point or optimizer call count differs.')
        for j,h in enumerate(r['history']):
            e._point(h['point'])
            if h['evaluation']!=j+1 or h['seed'] is not None or h['energy_counts'] is not None or not np.isclose(
                    h['optimizer_value'],(h['mean_energy']-e.offset)/e.scaling['scale'],atol=1e-10,rtol=0):
                raise ValueError('Exact training history differs.')
        if not any(h['point']==r['point'] and np.isclose(h['optimizer_value'],r['optimizer_value'],atol=1e-9,rtol=0) for h in r['history']):
            raise ValueError('Returned point is missing from training history.')
        if (r['training_shots']!=0 or sum(r['final_counts'].values())!=config['final_shots']
                or e.score_counts(r['final_counts'])!=r['final_measured']
                or not np.isclose(r['optimizer_value'],(r['final_exact']['mean_energy']-e.offset)/e.scaling['scale'],atol=1e-8,rtol=0)):
            raise ValueError('Endpoint scoring or shot accounting differs.')
        replay_exact(e,r['point'],r['final_exact'])
        checked += 1
    summary = summarize(folder)
    if any(r['budget_cap']!=c['identity']['protocol']['total_budget'] or
           (r['nfev'] is not None and r['nfev']>r['budget_cap']) for r in summary['rows']):
        raise ValueError('Strategy exceeded its total evaluation cap.')
    return dict(status='PASS',complete=summary['status']=='complete',coverage=summary['coverage'],
        completed_trials_checked=checked,endpoint_replay=replay,
        meaning='Consistency and budget checks; not evidence of QAOA improvement.')


def export_campaign(root, folder):
    folder = Path(folder)
    with writer(root,folder):
        audit = audit_campaign(root,folder)
        summary = summarize(folder)
        save_json(folder/'audit.json',audit)
        save_json(folder/'summary.json',summary)
        for name,rows in [('strategies',summary['rows']),('comparison',summary['comparisons'])]:
            with (folder/f'{name}.csv').open('w',encoding='utf-8',newline='') as handle:
                columns = list(dict.fromkeys(k for row in rows for k in row))
                output = csv.DictWriter(handle,fieldnames=columns)
                output.writeheader();output.writerows(rows)
        paths = sorted(p for p in folder.rglob('*') if p.is_file() and p.name not in ['SHA256.json','RUNNING.lock'] and not p.name.endswith('.tmp'))
        save_json(folder/'SHA256.json',{p.relative_to(folder).as_posix():file_hash(p) for p in paths})
        archive = folder.parent/(folder.name+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for path in paths+[folder/'SHA256.json']:
                z.write(path,path.relative_to(folder).as_posix())
    return archive
