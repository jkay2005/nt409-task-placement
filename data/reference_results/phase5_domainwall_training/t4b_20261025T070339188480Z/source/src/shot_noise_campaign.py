"""Persist, resume, audit and export the bounded Notebook 22 diagnostic."""
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import traceback
import zipfile

import numpy as np

from .qaoa_experiment import experiment_environment, qubo_fingerprint
from .shot_noise_diagnostic import ThreeHostEvaluator, calibrate, train
from .three_host_encoding import build_three_host_qubo

PROTOCOL = 'data/benchmarks/nt409_shot_noise_v2/protocol.json'
SOURCES = ['placement.py', 'qubo.py', 'ising.py', 'qaoa_experiment.py',
           'qaoa_optimizer.py', 'three_host_encoding.py',
           'shot_noise_diagnostic.py', 'shot_noise_campaign.py']


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def identity(root, protocol):
    root = Path(root)
    if (protocol['encoding'] != 'three_host_domain_wall_v2'
            or protocol['capacity_penalty'] != 4 or protocol['domain_penalty'] != 4):
        raise ValueError('This study requires the frozen three-host domain-wall model.')
    if len(protocol['instances']) != 1:
        raise ValueError('Notebook 22 uses exactly one reference instance.')
    if not protocol['software_validation']:
        item = protocol['instances'][0]
        if (item['instance_id'] != 'a3_dev_n5'
                or item['input_sha256'] != 'e6d3ac93ed2d5a831f5d7393750e9a1995b46fbe20d077058a629c7797996278'
                or item['qubo_sha256'] != '8fa77f91e277724277e5aaf4c1a29b5cec345e91e3660f13a6a166efc44fc515'):
            raise ValueError('The scientific input is fixed to a3_dev_n5.')
    if protocol['mixer'] != 'X' or protocol['scaling'] != 'max_abs':
        raise ValueError('This study requires the X mixer and max_abs scaling.')
    if (not protocol['depths'] or len(set(protocol['depths'])) != len(protocol['depths'])
            or any(type(p) is not int or p not in (1, 2) for p in protocol['depths'])
            or not protocol['seeds'] or len(set(protocol['seeds'])) != len(protocol['seeds'])
            or any(type(s) is not int or not 1 <= s < 1000 for s in protocol['seeds'])):
        raise ValueError('Invalid depths or training seeds.')
    if (type(protocol['maxiter']) is not int
            or not 2*max(protocol['depths'])+2 <= protocol['maxiter'] < 10000):
        raise ValueError('Evaluation cap must accommodate COBYLA initialization.')
    for key in ['rhobeg', 'tol', 'max_seconds', 'min_available_gib']:
        value = protocol[key]
        if type(value) not in (int, float) or not np.isfinite(value) or value <= 0:
            raise ValueError(f'{key} must be positive and finite.')
    for key in ['shots', 'final_shots', 'noise_batches', 'threads']:
        if type(protocol[key]) is not int or protocol[key] <= 0:
            raise ValueError(f'Invalid {key}.')
    if protocol['noise_batches'] >= 100:
        raise ValueError('Calibration seed blocks support fewer than 100 batches.')
    inputs = {}
    for item in protocol['instances']:
        value = load_json(root/item['path'])
        if value['instance_id'] != item['instance_id'] or digest(value) != item['input_sha256']:
            raise ValueError('Frozen input differs: '+item['instance_id'])
        inputs[item['instance_id']] = value
    if len(inputs) != len(protocol['instances']) or not inputs:
        raise ValueError('Instance IDs must be unique and nonempty.')
    source = {name: hashlib.sha256((root/'src'/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
              for name in SOURCES}
    return dict(protocol=protocol, inputs=inputs, source_sha256=source,
                runtime=experiment_environment()['runtime'])


def make_plan(protocol):
    plan = []
    for instance in protocol['instances']:
        for p in protocol['depths']:
            group_index = len(plan)//(len(protocol['seeds'])+1)
            group = f"{instance['instance_id']}__p{p}"
            for slot, seed in enumerate([None]+protocol['seeds']):
                mode = 'exact' if seed is None else 'shots'
                config = {k: protocol[k] for k in ['shots', 'final_shots', 'maxiter',
                    'rhobeg', 'tol', 'max_seconds', 'min_available_gib']}
                config.update(initial_point=[.3]+[0.]*(p-1)+[1.]+[0.]*(p-1),
                    seed=0 if seed is None else seed,
                    final_seed=40000000+100*group_index+slot)
                plan.append(dict(id=f'{group}__{mode}_{slot}', group=group,
                    instance_id=instance['instance_id'], p=p, mode=mode, config=config,
                    calibration_seed_base=20000000+group_index*100))
    return plan


def create_campaign(root, output=None, protocol=None):
    root = Path(root).resolve()
    protocol = load_json(root/PROTOCOL) if protocol is None else protocol
    ident = identity(root, protocol)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = Path(output) if output is not None else root/'data/reference_results/phase4n_shot_noise'/f'noise_{stamp}'
    folder = folder.resolve()
    if (folder/'campaign.json').exists():
        old = load_json(folder/'campaign.json')
        if old['identity'] != ident or old['plan'] != make_plan(protocol):
            raise ValueError('Cannot resume with changed inputs, protocol, source or runtime.')
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
        identity=ident, identity_sha256=digest(ident), plan=make_plan(protocol),
        attempts=[], calibrations={}))
    return folder


def checked_campaign(root, folder):
    folder = Path(folder)
    c = load_json(folder/'campaign.json')
    if c['identity_sha256'] != digest(c['identity']):
        raise ValueError('Campaign identity checksum differs.')
    if c['identity'] != identity(root, c['identity']['protocol']):
        raise ValueError('Source, runtime or input changed; resume requires the original environment.')
    if c['plan'] != make_plan(c['identity']['protocol']):
        raise ValueError('Planned trials differ.')
    if load_json(folder/'protocol.json') != c['identity']['protocol']:
        raise ValueError('Protocol snapshot differs.')
    for name, value in c['identity']['inputs'].items():
        if load_json(folder/'inputs'/f'{name}.json') != value:
            raise ValueError('Input snapshot differs.')
    for name, value in c['identity']['source_sha256'].items():
        source = (folder/'source/src'/name).read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(source).hexdigest() != value:
            raise ValueError('Source snapshot differs.')
    for entry in c['attempts']+list(c['calibrations'].values()):
        path = folder/entry['path']
        if file_hash(path) != entry['sha256']:
            raise ValueError('Report checksum differs: '+entry['path'])
    return c


def build_evaluator(campaign, item):
    protocol = campaign['identity']['protocol']
    bundle = build_three_host_qubo(campaign['identity']['inputs'][item['instance_id']])
    expected = next(i for i in protocol['instances'] if i['instance_id'] == item['instance_id'])
    if qubo_fingerprint(bundle) != expected['qubo_sha256']:
        raise ValueError('QUBO coefficients differ from the frozen three-host reference.')
    return ThreeHostEvaluator(bundle, item['p'], protocol['threads'], protocol['min_available_gib'])


def ensure_calibration(c, evaluator, item, folder, progress):
    if item['group'] in c['calibrations']:
        return
    protocol = c['identity']['protocol']
    noise = calibrate(evaluator, item['config']['initial_point'], protocol['shots'],
                      protocol['noise_batches'], item['calibration_seed_base'], progress)
    noise.update(group=item['group'], qubits=evaluator.size, scaling=evaluator.scaling,
                 offset=evaluator.offset, compiled_depth=evaluator.compiled_depth,
                 compiled_ops=evaluator.compiled_ops)
    path = f"calibration/{item['group']}.json"
    save_json(folder/path, noise)
    c['calibrations'][item['group']] = dict(path=path, sha256=file_hash(folder/path))
    save_json(folder/'campaign.json', c)


def prepare_campaign(root, folder, progress=True):
    """Persist fixed-point calibration before committing to long training runs."""
    folder = Path(folder)
    c = checked_campaign(root, folder)
    lock = folder/'RUNNING.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(f'pid={os.getpid()}\n')
    rows = []
    try:
        for group in dict.fromkeys(p['group'] for p in c['plan']):
            item = next(p for p in c['plan'] if p['group'] == group)
            if group not in c['calibrations']:
                if progress: print('Calibrate:', group, flush=True)
                evaluator = build_evaluator(c, item)
                ensure_calibration(c, evaluator, item, folder, progress)
                del evaluator
            noise = load_json(folder/c['calibrations'][group]['path'])
            shot_seconds = float(np.median([b['seconds'] for b in noise['batches']]))
            cap = item['config']['maxiter']
            seeds = len(c['identity']['protocol']['seeds'])
            rows.append(dict(group=group, qubits=noise['qubits'],
                exact_seconds=noise['exact_seconds'], shot_seconds=shot_seconds,
                training_cap_hours=cap*(noise['exact_seconds']+seeds*shot_seconds)/3600))
        return rows
    finally:
        lock.unlink()


def run_campaign(root, folder, max_new_runs=None, retry_failed=False, progress=True):
    folder = Path(folder)
    c = checked_campaign(root, folder)
    if max_new_runs is not None and (type(max_new_runs) is not int or max_new_runs < 1):
        raise ValueError('max_new_runs must be positive or None.')
    lock = folder/'RUNNING.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(f'pid={os.getpid()}\n')
    try:
        evaluators = {}
        new = 0
        for item in c['plan']:
            previous = [r for r in c['attempts'] if r['id'] == item['id']]
            if previous and previous[-1]['status'] == 'completed':
                continue
            if previous and not retry_failed:
                if progress: print('Stopped at failed run; inspect it before explicit retry:', item['id'])
                break
            if max_new_runs is not None and new >= max_new_runs:
                break
            if progress: print(f"[{new+1}] {item['id']}", flush=True)
            try:
                if item['group'] not in evaluators:
                    evaluators[item['group']] = build_evaluator(c, item)
                e = evaluators[item['group']]
                ensure_calibration(c, e, item, folder, progress)
                report = train(e, item['config'], item['mode'], progress=progress)
            except (Exception, KeyboardInterrupt) as error:
                report = dict(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                    mode=item['mode'], config=item['config'], history=[], nfev=0,
                    error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(limit=8))
            report.update(id=item['id'], group=item['group'])
            path = f"raw/{len(c['attempts'])+1:04d}_{item['id']}.json"
            save_json(folder/path, report)
            c['attempts'].append(dict(id=item['id'], path=path,
                                     sha256=file_hash(folder/path), status=report['status']))
            save_json(folder/'campaign.json', c)
            new += 1
            if report['status'] != 'completed':
                if progress: print('Saved incomplete run:', report.get('error'))
                break
        return summarize(folder)
    finally:
        lock.unlink()


def summarize(folder):
    folder = Path(folder)
    c = load_json(folder/'campaign.json')
    latest = {a['id']: a for a in c['attempts']}
    rows = []
    for item in c['plan']:
        row = dict(id=item['id'], group=item['group'], instance_id=item['instance_id'],
                   p=item['p'], mode=item['mode'], seed=item['config']['seed'], status='pending')
        if item['id'] in latest:
            r = load_json(folder/latest[item['id']]['path'])
            row.update(status=r['status'], nfev=r['nfev'])
            if r['status'] == 'completed':
                row.update(r['final_exact'])
                row.update(r['final_measured'])
                # Keep ideal mean separate from measured mean.
                row['mean_energy_exact'] = r['final_exact']['mean_energy']
                row['mean_energy_sampled'] = r['final_measured']['mean_energy']
                row.pop('mean_energy')
                row.update(seconds=r['elapsed_seconds'], optimizer_success=r['optimizer_stop']['success'])
        rows.append(row)
    comparisons = []
    for group in dict.fromkeys(r['group'] for r in rows):
        values = [r for r in rows if r['group'] == group]
        exact = next((r for r in values if r['mode'] == 'exact' and r['status'] == 'completed'), None)
        sampled = [r for r in values if r['mode'] == 'shots' and r['status'] == 'completed']
        if exact is None or not sampled:
            continue
        mean_opt = float(np.mean([r['p_opt'] for r in sampled]))
        comparisons.append(dict(group=group, sampled_completed=len(sampled),
            sampled_planned=len(c['identity']['protocol']['seeds']), exact_p_opt=exact['p_opt'],
            shots_p_opt_mean=mean_opt, shots_p_opt_min=min(r['p_opt'] for r in sampled),
            shots_p_opt_max=max(r['p_opt'] for r in sampled),
            delta_p_opt_pp=100*(exact['p_opt']-mean_opt),
            exact_p_valid=exact['p_valid'], shots_p_valid_mean=float(np.mean([r['p_valid'] for r in sampled])),
            exact_mean_energy=exact['mean_energy_exact'],
            shots_mean_energy_exact=float(np.mean([r['mean_energy_exact'] for r in sampled]))))
    coverage = dict(planned=len(rows), completed=sum(r['status']=='completed' for r in rows),
                    pending=sum(r['status']=='pending' for r in rows),
                    failed=sum(r['status'] not in ('pending', 'completed') for r in rows))
    return dict(status='complete' if coverage['completed']==coverage['planned'] else 'partial',
                software_validation=c['identity']['protocol']['software_validation'],
                coverage=coverage, rows=rows, comparisons=comparisons)


def audit_campaign(root, folder, replay=True):
    folder = Path(folder)
    c = checked_campaign(root, folder)
    by_id = {p['id']: p for p in c['plan']}
    evaluators = {}
    count = 0
    for group, entry in c['calibrations'].items():
        item = next(p for p in c['plan'] if p['group'] == group)
        e = build_evaluator(c, item)
        evaluators[group] = e
        calibration = load_json(folder/entry['path'])
        protocol = c['identity']['protocol']
        if (calibration['point'] != item['config']['initial_point']
                or calibration['group'] != group or calibration['shots'] != protocol['shots']
                or len(calibration['batches']) != protocol['noise_batches']):
            raise ValueError('Calibration design differs.')
        for j, b in enumerate(calibration['batches']):
            if (b['seed'] != item['calibration_seed_base']+j
                    or sum(b['counts'].values()) != protocol['shots']
                    or not np.isclose(e.score_counts(b['counts'])['mean_energy'], b['mean_energy'],
                                      atol=1e-9, rtol=0)):
                raise ValueError('Calibration samples differ.')
        means = np.array([b['mean_energy'] for b in calibration['batches']])
        se = calibration['exact']['energy_std']/np.sqrt(protocol['shots'])
        if (not np.isclose(se, calibration['theoretical_se'], atol=1e-9, rtol=0)
                or not np.isclose(means.mean()-calibration['exact']['mean_energy'],
                                  calibration['observed_mean_error'], atol=1e-9, rtol=0)
                or (len(means)>1 and not np.isclose(means.std(ddof=1),
                    calibration['observed_batch_sd'], atol=1e-9, rtol=0))):
            raise ValueError('Calibration summary differs.')
        if replay:
            actual = e.exact(calibration['point'])
            if actual.keys() != calibration['exact'].keys() or any(
                not np.isclose(actual[k], v, atol=1e-8, rtol=1e-9)
                for k, v in calibration['exact'].items()):
                raise ValueError('Calibration exact replay differs.')
    for attempt in c['attempts']:
        item = by_id[attempt['id']]
        r = load_json(folder/attempt['path'])
        if r['id'] != item['id'] or r['group'] != item['group'] or r['config'] != item['config'] or r['mode'] != item['mode'] or r['status'] != attempt['status']:
            raise ValueError('Report identity differs.')
        if r['status'] != 'completed':
            continue
        if item['group'] not in c['calibrations']:
            raise ValueError('Completed trial is missing calibration.')
        if item['group'] not in evaluators:
            evaluators[item['group']] = build_evaluator(c, item)
        e = evaluators[item['group']]
        history = r['history']
        if not 0 < len(history) == r['nfev'] == r['optimizer_stop']['nfev'] <= item['config']['maxiter']:
            raise ValueError('Evaluation count differs.')
        if history[0]['point'] != item['config']['initial_point']:
            raise ValueError('Initial point differs.')
        for j, h in enumerate(history):
            e._point(h['point'])
            if h['evaluation'] != j+1 or not np.isclose(h['optimizer_value'],
                (h['mean_energy']-e.offset)/e.scaling['scale'], atol=1e-10, rtol=0):
                raise ValueError('History energy/index differs.')
            if r['mode'] == 'shots':
                hist = h['energy_counts']
                if (h['seed'] != item['config']['seed']*10000+j
                        or sum(n for _, n in hist) != item['config']['shots']
                        or any(type(n) is not int or n <= 0 for _, n in hist)
                        or not np.isclose(sum(v*n for v, n in hist)/item['config']['shots'],
                                          h['mean_energy'], atol=1e-9, rtol=0)):
                    raise ValueError('Training sample evidence differs.')
        matches = [h for h in history if h['point'] == r['point']
                   and np.isclose(h['optimizer_value'], r['optimizer_value'], atol=1e-9, rtol=0)]
        if not matches:
            raise ValueError('Returned optimum not found in training history.')
        if (sum(r['final_counts'].values()) != item['config']['final_shots']
                or e.score_counts(r['final_counts']) != r['final_measured']
                or r['training_shots'] != (r['nfev']*item['config']['shots'] if r['mode']=='shots' else 0)):
            raise ValueError('Final samples or shot accounting differ.')
        if replay:
            actual = e.exact(r['point'])
            if actual.keys() != r['final_exact'].keys() or any(not np.isclose(actual[k], v, atol=1e-8, rtol=1e-9) for k, v in r['final_exact'].items()):
                raise ValueError('Exact endpoint replay differs.')
        count += 1
    summary = summarize(folder)
    return dict(status='PASS', complete=summary['status']=='complete', checked_completed_attempts=count,
                endpoint_replay=replay, coverage=summary['coverage'],
                meaning='Consistency checks only; not evidence that exact improves QAOA.')


def export_campaign(root, folder):
    folder = Path(folder)
    if (folder/'RUNNING.lock').exists():
        raise RuntimeError('Cannot export while a campaign writer is running.')
    audit = audit_campaign(root, folder)
    summary = summarize(folder)
    save_json(folder/'audit.json', audit)
    save_json(folder/'summary.json', summary)
    for name, rows in [('results', summary['rows']), ('comparison', summary['comparisons'])]:
        with (folder/f'{name}.csv').open('w', encoding='utf-8', newline='') as handle:
            columns = list(dict.fromkeys(k for row in rows for k in row))
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    paths = sorted(p for p in folder.rglob('*') if p.is_file() and p.name != 'SHA256.json')
    save_json(folder/'SHA256.json', {p.relative_to(folder).as_posix(): file_hash(p) for p in paths})
    archive = folder.parent/(folder.name+'.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths+[folder/'SHA256.json']:
            z.write(p, p.relative_to(folder).as_posix())
    return archive
