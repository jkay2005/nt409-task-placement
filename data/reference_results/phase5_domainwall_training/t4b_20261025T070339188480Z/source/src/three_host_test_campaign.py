"""Frozen test campaign using the unchanged Notebook 19 model and runner."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import math
import zipfile

from .benchmark_a_campaign import (_read, _inside, _digest, _require, _lock, _config, save_json)
from .independent_campaign import canonical_hash
from .three_host_benchmark import load_three_host_benchmark, measure_assignment
from .three_host_encoding import certify_three_host
from .three_host_pilot import (environment as pilot_environment, get_model,
    make_pilot_trials, _validate, result_rows, control_rows)
from .three_host_runner import run_three_host_trial, probe_three_host

SCOPE = 'phase4l_three_host_test_v1'
PROTOCOL_HASH = 'ba470c6e96a8b8c560eaaa92463b27b36a22de8ac29ba76d615c5e03433c9266'


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_test_context(root):
    root = Path(root)
    parent = load_three_host_benchmark(root/'data/benchmarks/nt409_three_host_v2')
    protocol = _read(root/'data/benchmarks/nt409_three_host_test_v1/protocol.json')
    _require(canonical_hash(protocol) == PROTOCOL_HASH and
             protocol['parent_design'] == parent['manifest']['design_sha256'], 'Frozen test protocol changed.')
    return dict(**parent, test_protocol=protocol)


def make_test_trials(context):
    items = sorted((r for r in context['manifest']['instances'] if r['role'] == 'test'),
                   key=lambda r: (r['num_tasks'], r['instance_id']))
    _require(items, 'No test instances.')
    sizes = sorted({r['num_tasks'] for r in items})
    # Fixed pairing; the six official inputs alternate n4/n5.
    by_size = [[r for r in items if r['num_tasks'] == n] for n in sizes]
    order = [group[j] for j in range(max(map(len, by_size))) for group in by_size if j < len(group)]
    p = context['test_protocol']; q = p['qaoa']; depths = q['depths']; trials = []
    _require(len(q['optimization_seeds']) == len(q['evaluation_seeds']), 'Seed counts differ.')
    for seed_index, (seed, final) in enumerate(zip(q['optimization_seeds'], q['evaluation_seeds'])):
        for round_index in range(len(depths)):
            for j, item in enumerate(order):
                depth = depths[(round_index+j//len(sizes)+seed_index) % len(depths)]
                trial = dict(instance_id=item['instance_id'], role='test', config=_config(p, depth, seed, final))
                trial['run_key'] = canonical_hash(dict(benchmark=canonical_hash(context), **trial))
                trials.append(trial)
    _require(len({t['run_key'] for t in trials}) == len(trials), 'Duplicate planned trials.')
    return trials


class BudgetClock:
    """Active monotonic time; durable checkpoints. Idle between calls is excluded."""
    def __init__(self, state, label, save=None, tick=perf_counter, utc=utc_now):
        self.state, self.save, self.tick, self.utc = state, save, tick, utc
        _require(all(s['closed'] for s in state['sessions']), 'Recover the unclosed budget session first.')
        self.last = tick()
        self.session = dict(label=label, started_at_utc=utc(), last_checkpoint_at_utc=utc(),
                            seconds=0., closed=False, recovered=False, unconfirmed_wall_seconds=0.)
        state['sessions'].append(self.session)
        self._save()

    def _save(self):
        if self.save is not None: self.save()

    def remaining(self):
        return self.state['limit_seconds']-self.state['charged_seconds']-max(0., self.tick()-self.last)

    def checkpoint(self):
        now = self.tick(); seconds = max(0., now-self.last); self.last = now
        self.state['charged_seconds'] += seconds; self.session['seconds'] += seconds
        self.session['last_checkpoint_at_utc'] = self.utc(); self._save()

    def close(self):
        if not self.session['closed']:
            self.checkpoint(); self.session['closed'] = True; self._save()


def recover_budget(state, now=None):
    now = utc_now() if now is None else now
    for session in state['sessions']:
        if session['closed']: continue
        gap = (datetime.fromisoformat(now)-datetime.fromisoformat(session['last_checkpoint_at_utc'])).total_seconds()
        # After abrupt death the stop time is unknown. Never grant free budget.
        if gap < 0: gap = max(0., state['limit_seconds']-state['charged_seconds'])
        session.update(closed=True, recovered=True, unconfirmed_wall_seconds=gap,
                       recovery_at_utc=now, seconds=session['seconds']+gap)
        state['charged_seconds'] += gap


def environment():
    return dict(**pilot_environment(), test_source_sha256={name: _digest(Path(__file__).parent/name)
        for name in ('three_host_test_campaign.py', 'three_host_test_analysis.py')})


def audit_pilot_archive(root, archive, context):
    """Portable C2 audit: saved Windows runtime, current source modulo newlines."""
    import hashlib
    import json
    _require(canonical_hash(context['test_protocol']) == PROTOCOL_HASH, 'Test protocol changed before C2 audit.')
    parent = {k: v for k, v in context.items() if k != 'test_protocol'}
    archive = _inside(root, archive)
    with zipfile.ZipFile(archive) as z:
        _require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate pilot ZIP members.')
        hashes = json.loads(z.read('sha256.json'))
        _require(set(hashes) == set(z.namelist())-{'sha256.json'}, 'Pilot ZIP manifest incomplete.')
        for name, value in hashes.items():
            _require(hashlib.sha256(z.read(name)).hexdigest() == value, 'Pilot ZIP checksum differs.')
        m = json.loads(z.read('campaign.json')); planned = make_pilot_trials(parent)
        _require(m['scope'] == 'phase4k_three_host_pilot_v2' and m['active'] is None and
                 m['design']['benchmark'] == parent and m['planned_runs'] == planned and
                 canonical_hash(m['design']) == m['design_hash'], 'Pilot identity differs.')
        env = m['design']['environment']
        current = pilot_environment()
        for section, expected in ((env['core']['source_sha256'],current['core']['source_sha256']),
                                  (env['pilot_source_sha256'],current['pilot_source_sha256'])):
            _require(set(section) == set(expected), 'Pilot source inventory differs.')
            for name, value in section.items():
                b = (Path(__file__).parent/name).read_bytes().replace(b'\r\n', b'\n')
                _require(value in [hashlib.sha256(b).hexdigest(), hashlib.sha256(b.replace(b'\n', b'\r\n')).hexdigest()],
                         f'Pilot source differs: {name}')
        lookup = {t['run_key']: t for t in planned}; successes = set(); probe_pairs = set(); complete = probes = 0
        for number, a in enumerate(m['attempts'], 1):
            e = json.loads(z.read(a['report'])); active = e['attempt']; result = e['result']
            _require(a['number'] == number and a['run_key'] in lookup and active['trial'] == lookup[a['run_key']] and
                     active['number'] == number and active['kind'] == a['kind'] and active['report'] == a['report'] and
                     e['design_hash'] == m['design_hash'] and e['campaign_id'] == m['campaign_id'] and
                     result['status'] == a['status'] and hashes[a['report']] == a['report_sha256'] and
                     a['instance_id']==active['trial']['instance_id'] and a['reps']==active['trial']['config']['reps'], 'Pilot ledger differs.')
            _validate(result, active, parent, env)
            if result['status'] in ('completed', 'passed'):
                key = (a['kind'], a['run_key']); _require(key not in successes, 'Pilot success repeated.'); successes.add(key)
                complete += a['kind'] == 'trial'; probes += a['kind'] == 'probe'
                if a['kind']=='probe':probe_pairs.add((a['instance_id'],a['reps']))
        _require(complete == len(planned) == 14 and probes == 8 and
                 probe_pairs == {(t['instance_id'],t['config']['reps']) for t in planned}, 'Notebook 19 pilot is incomplete.')
    return dict(validated=True, archive_sha256=_digest(archive), campaign_id=m['campaign_id'],
                design_hash=m['design_hash'], completed_trials=complete, passed_probes=probes,
                audit='raw counts, semantic reports, ledger, sources modulo LF/CRLF; no quantum rerun')


def _audit_attempt(e, row, campaign, context):
    active = e['attempt']; trial = active['trial']; config = active['execution_config']
    remaining = active['budget_remaining_before_attempt']; reserve = context['test_protocol']['budget']['export_reserve_seconds']
    expected = dict(trial['config'], max_seconds=min(trial['config']['max_seconds'], remaining-reserve))
    _require(config == expected and config['max_seconds'] > 0, 'Execution guard differs from frozen budget rule.')
    _require(e['campaign_id'] == campaign['campaign_id'] and e['design_hash'] == campaign['design_hash'] and
             active['number'] == row['number'] and active['kind'] == row['kind'] and active['report'] == row['report'] and
             trial['run_key'] == row['run_key'] and e['result']['status'] == row['status'] and
             row['instance_id'] == trial['instance_id'] and row['reps'] == trial['config']['reps'], 'Test ledger/report differs.')
    shadow = dict(active, trial=dict(trial, config=config))
    _validate(e['result'], shadow, context, campaign['design']['environment'])


def verify_test_campaign(folder, campaign, context):
    expected = dict(benchmark=context, environment=environment())
    _require(campaign['scope'] == SCOPE and campaign['schema_version'] == 1 and campaign['design'] == expected and
             campaign['design_hash'] == canonical_hash(expected) and campaign['planned_runs'] == make_test_trials(context),
             'Test source/runtime/input/protocol changed; resume refused.')
    _require(campaign['pilot_evidence'].get('validated') is True, 'C2 pilot evidence missing.')
    budget = campaign['budget']; policy = context['test_protocol']['budget']
    _require(budget['limit_seconds'] == policy['limit_seconds'] and math.isfinite(budget['charged_seconds']) and
             budget['charged_seconds'] >= 0 and all(math.isfinite(s['seconds']) and s['seconds'] >= 0 for s in budget['sessions']) and
             abs(sum(s['seconds'] for s in budget['sessions'])-budget['charged_seconds']) < 1e-6 and
             sum(not s['closed'] for s in budget['sessions']) <= 1, 'Budget ledger differs.')
    lookup = {t['run_key']: t for t in campaign['planned_runs']}; seen = set(); completed = []
    for number, row in enumerate(campaign['attempts'], 1):
        _require(row['number'] == number and row['run_key'] in lookup, 'Unknown test attempt.')
        path = _inside(folder, row['report']); _require(_digest(path) == row['report_sha256'], 'Test report checksum differs.')
        e = _read(path); _require(e['attempt']['trial'] == lookup[row['run_key']], 'Planned trial differs.')
        _audit_attempt(e, row, campaign, context)
        if row['status'] in ('completed', 'passed'):
            key = (row['kind'], row['run_key']); _require(key not in seen, 'Completed test attempt repeated.'); seen.add(key)
            if row['kind'] == 'trial': completed.append(row)
    if campaign['active'] is not None:
        a = campaign['active']; _require(a['number'] == len(campaign['attempts'])+1 and a['trial'] in campaign['planned_runs'] and
            a['kind'] in ('trial', 'probe'), 'Invalid active test attempt.'); _inside(folder, a['report'])
    return completed


def _finish(folder, campaign, result, context):
    active = campaign['active']; trial = active['trial']; path = _inside(folder, active['report'])
    e = dict(campaign_id=campaign['campaign_id'], design_hash=campaign['design_hash'], attempt=active, result=result)
    row = dict(number=active['number'], kind=active['kind'], run_key=trial['run_key'], instance_id=trial['instance_id'],
               reps=trial['config']['reps'], status=result['status'], report=active['report'])
    _audit_attempt(e, row, campaign, context); save_json(path, e)
    row['report_sha256'] = _digest(path); campaign['attempts'].append(row); campaign['active'] = None
    save_json(Path(folder)/'campaign.json', campaign)


def _start_test_attempt(folder, campaign, trial, kind, remaining, reserve):
    _require(campaign['active'] is None and trial in campaign['planned_runs'], 'Unknown/concurrent test attempt.')
    _require(not any(a['kind']==kind and a['run_key']==trial['run_key'] and a['status'] in ('completed','passed')
                     for a in campaign['attempts']), 'Attempt already completed.')
    number=len(campaign['attempts'])+1
    campaign['active']=dict(number=number,kind=kind,trial=trial,started_at_utc=utc_now(),
        report=f'attempts/{number:04d}_{kind}_{trial["run_key"][:12]}.json',
        execution_config=dict(trial['config'],max_seconds=min(trial['config']['max_seconds'],remaining-reserve)),
        budget_remaining_before_attempt=remaining)
    # All recovery metadata enters the same atomic write.
    save_json(Path(folder)/'campaign.json',campaign)
    return campaign['active']


def _recover_attempt(folder, campaign, context):
    active = campaign['active']
    if active is None: return
    path = _inside(folder, active['report'])
    if path.exists():
        e = _read(path); _require(e['attempt'] == active and e['campaign_id']==campaign['campaign_id'] and
            e['design_hash']==campaign['design_hash'], 'Orphan attempt differs.'); result = e['result']
    else:
        result = dict(status='interrupted', config=active['execution_config'], instance_id=active['trial']['instance_id'],
                      stop_reason='Kernel stopped before terminal report; budget recovery is conservative.', total_seconds=None)
    _finish(folder, campaign, result, context)


@contextmanager
def _stage(folder, context, label):
    folder = Path(folder)
    with _lock(folder):
        campaign = _read(folder/'campaign.json'); recover_budget(campaign['budget'])
        clock = BudgetClock(campaign['budget'], label, save=lambda: save_json(folder/'campaign.json', campaign))
        try:
            verify_test_campaign(folder, campaign, context); _recover_attempt(folder, campaign, context)
            yield campaign, clock
        finally:
            clock.close()


def open_test_campaign(root, context, pilot_archive=None, resume_dir=None, bootstrap_seconds=0.):
    root = Path(root).resolve()
    _require(math.isfinite(bootstrap_seconds) and bootstrap_seconds >= 0, 'Invalid startup time.')
    started = perf_counter()
    if resume_dir is None:
        evidence = audit_pilot_archive(root, pilot_archive, context)
        design = dict(benchmark=context, environment=environment()); now = utc_now()
        campaign = dict(schema_version=1, scope=SCOPE, campaign_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
            design=design, design_hash=canonical_hash(design), pilot_evidence=evidence, planned_runs=make_test_trials(context),
            preprocessing_sessions=[], attempts=[], active=None, halt=None,
            budget=dict(limit_seconds=context['test_protocol']['budget']['limit_seconds'], charged_seconds=0., sessions=[]))
        folder = root/'data/reference_results/phase4l_three_host_test'/f"test_{campaign['campaign_id']}"
        folder.mkdir(parents=True, exist_ok=False)
        save_json(folder/'campaign.json', campaign)
    else:
        folder = _inside(root, resume_dir); _require((folder/'campaign.json').is_file(), 'Missing resume campaign.')
    seconds = bootstrap_seconds+(perf_counter()-started)
    with _stage(folder, context, 'open') as (campaign, clock):
        # Pre-stage imports, loading and C2 audit are charged once per open call.
        clock.state['charged_seconds'] += seconds; clock.session['seconds'] += seconds
    return folder, _read(folder/'campaign.json')


def prepare_test_models(folder, context):
    with _stage(folder, context, 'prepare') as (campaign, clock):
        rows = []; timings = []
        for item in context['manifest']['instances']:
            if item['role'] != 'test': continue
            if clock.remaining() <= context['test_protocol']['budget']['export_reserve_seconds']: break
            start = perf_counter(); bundle, ref = get_model(context, item['instance_id']); cert = certify_three_host(bundle)
            rows.append(dict(instance_id=item['instance_id'], role='test', num_qubits=bundle['qubo'].get_num_vars(),
                             certificate=cert, reference=ref, preparation_seconds=perf_counter()-start))
            timings.extend(measure_assignment(context['instances'][item['instance_id']]))
            clock.checkpoint()
        if rows:
            campaign['preprocessing_sessions'].append(dict(at_utc=utc_now(), rows=rows))
            save_json(Path(folder)/'model_validation.json', rows); save_json(Path(folder)/'classical_timings.json', timings)
        controls = [r for r in control_rows(context) if r['role'] == 'test']
        save_json(Path(folder)/'controls.json', controls)
    return rows


def run_test_phase(folder, context, kind, retry_failed=False, max_new_trials=None, progress=True):
    _require(kind in ('probe', 'trial'), 'Unknown test phase.')
    _require(max_new_trials is None or type(max_new_trials) is int and max_new_trials > 0, 'Invalid session trial count.')
    policy = context['test_protocol']; reserve = policy['budget']['export_reserve_seconds']
    with _stage(folder, context, kind) as (campaign, clock):
        prepared = {r['instance_id'] for s in campaign['preprocessing_sessions'] for r in s['rows'] if r['certificate']['polynomial_identity']}
        _require({t['instance_id'] for t in campaign['planned_runs']} <= prepared or
                 clock.remaining() <= reserve, 'Prepare all test models before QAOA.')
        passed = {(a['instance_id'], a['reps']): a for a in campaign['attempts'] if a['kind'] == 'probe' and a['status'] == 'passed'}
        required = {(t['instance_id'], t['config']['reps']) for t in campaign['planned_runs']}
        if kind == 'trial' and clock.remaining() > reserve: _require(required <= set(passed), 'All test preflights must pass before training.')
        seen = set(); count = 0; campaign['halt'] = None
        for trial in campaign['planned_runs']:
            pair = (trial['instance_id'], trial['config']['reps'])
            if kind == 'probe' and pair in seen: continue
            seen.add(pair)
            attempts = [a for a in campaign['attempts'] if a['kind'] == kind and a['run_key'] == trial['run_key']]
            if attempts and (attempts[-1]['status'] in ('completed','passed') or (attempts[-1]['status'] != 'interrupted' and not retry_failed)):
                continue
            if kind == 'probe': estimate = policy['budget']['probe_admission_seconds']
            else:
                report = _read(Path(folder)/passed[pair]['report'])['result']
                estimate = min(trial['config']['max_seconds'], report['maxiter_seconds_estimate'])
            clock.checkpoint()
            if clock.remaining() < reserve+estimate:
                campaign['halt'] = dict(reason='budget_admission_stopped', kind=kind, run_key=trial['run_key'],
                    required_seconds=reserve+estimate, remaining_seconds=max(0.,clock.remaining()), at_utc=utc_now())
                break
            bundle, ref = get_model(context, trial['instance_id']); clock.checkpoint()
            remaining = clock.remaining()
            if remaining < reserve+estimate:
                campaign['halt']=dict(reason='budget_admission_stopped',kind=kind,run_key=trial['run_key'],
                    required_seconds=reserve+estimate,remaining_seconds=max(0.,remaining),at_utc=utc_now())
                break
            execution = dict(trial['config'], max_seconds=min(trial['config']['max_seconds'], remaining-reserve))
            _start_test_attempt(folder,campaign,trial,kind,remaining,reserve)
            print(f"{kind}: {trial['instance_id']} p={trial['config']['reps']} seed={trial['config']['seed']}; remaining={remaining/3600:.2f}h", flush=True)
            result = (probe_three_host(bundle, execution, policy['resource_policy'], ref) if kind == 'probe' else
                      run_three_host_trial(bundle, execution, policy['resource_policy'], ref, progress))
            _finish(folder, campaign, result, context); clock.checkpoint(); count += 1
            print(result['status'], flush=True)
            if result['status'] not in ('completed','passed'):
                campaign['halt'] = dict(reason='attempt_failed', kind=kind, run_key=trial['run_key'], status=result['status'], at_utc=utc_now()); break
            if kind == 'trial' and max_new_trials is not None and count >= max_new_trials:
                campaign['halt'] = dict(reason='session_trial_limit', at_utc=utc_now()); break
    return _read(Path(folder)/'campaign.json')


def export_test_campaign(folder, context):
    from .three_host_test_analysis import summarize_test
    import csv
    folder = Path(folder)
    with _stage(folder, context, 'export') as (campaign, clock):
        rows = result_rows(folder, campaign, context); summary = summarize_test(rows, campaign)
        with (folder/'test_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        save_json(folder/'frozen_context.json', context)
        names = set(campaign['design']['environment']['core']['source_sha256'])
        names.update(campaign['design']['environment']['pilot_source_sha256'])
        names.update(campaign['design']['environment']['test_source_sha256'])
        for name in names:
            dest=folder/'source'/name;dest.parent.mkdir(exist_ok=True);dest.write_bytes((Path(__file__).parent/name).read_bytes())
        payload = ['test_results.csv','frozen_context.json'] + [a['report'] for a in campaign['attempts']]
        payload += [f'source/{name}' for name in sorted(names)]
        payload += [name for name in ('model_validation.json','controls.json','classical_timings.json','test_quality.png') if (folder/name).exists()]
        archive = folder/f'{folder.name}.zip'
        # Compress bulk evidence under the clock. Only the small final receipt
        # writes happen after closing, avoiding an unmetered second compression.
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name in payload: z.write(folder/name,name)
            clock.close()
            summary = summarize_test(rows,campaign); save_json(folder/'summary.json',summary)
            payload += ['campaign.json','summary.json']
            save_json(folder/'sha256.json',{name:_digest(folder/name) for name in payload})
            for name in ['campaign.json','summary.json','sha256.json']:z.write(folder/name,name)
    return archive, rows, summary


def analyse_test_campaign(folder, context):
    from .three_host_test_analysis import summarize_test, plot_test_quality
    with _stage(folder, context, 'analysis') as (campaign, clock):
        rows=result_rows(folder,campaign,context)
        summary=summarize_test(rows,campaign)
        plot_test_quality(summary,Path(folder)/'test_quality.png')
    return rows,summarize_test(rows,_read(Path(folder)/'campaign.json'))
