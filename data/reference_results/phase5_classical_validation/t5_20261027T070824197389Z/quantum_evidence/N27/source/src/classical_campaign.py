"""Notebook 21: frozen classical benchmark and auditable exports, no QAOA rerun."""
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import itertools
import json
import platform
from pathlib import Path
import shutil
import statistics
import sys
from time import perf_counter
import zipfile

from .classical_baselines import ALGORITHMS, solve_heuristic, solve_milp
from .placement import evaluate_model, evaluate_placement

PROTOCOL_PATH = 'data/benchmarks/nt409_classical_b_v1_1/protocol.json'
PROTOCOL_HASH = '40f2a27293c3377112429e57de4f06532d2ee7e0034aae7d9868f9d06d92b626'
SOURCE_PATHS = ('src/placement.py', 'src/classical_baselines.py', 'src/classical_campaign.py',
                'requirements-branch-b.txt', 'notebooks/21_classical_baselines_b.ipynb')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    temp.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    return list(csv.DictReader(io.StringIO(Path(path).read_text(encoding='utf-8-sig'))))


def write_csv(path, rows):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def exact_reference(instance):
    histogram = {}
    for placement in itertools.product(range(len(instance['hosts'])), repeat=len(instance['tasks'])):
        checked = evaluate_placement(instance, placement)
        if checked['feasible']:
            key = str(checked['objective'])
            histogram[key] = histogram.get(key, 0) + 1
    return dict(optimum=min(map(int, histogram), default=None), objective_histogram=histogram,
                total_assignments=len(instance['hosts'])**len(instance['tasks']),
                feasible_assignments=sum(histogram.values()))


def load_context(root):
    root = Path(root)
    protocol = read_json(root/PROTOCOL_PATH)
    require(digest(protocol) == PROTOCOL_HASH, 'Protocol changed; create a new version.')
    require(hashlib.sha256((root/'src/placement.py').read_text(encoding='utf-8-sig').encode()).hexdigest() == protocol['validator_normalized_sha256'], 'Shared validator changed.')
    instances = {}
    for row in protocol['instances']:
        item = read_json(root/row['input_path'])
        require(digest(item) == row['input_canonical_sha256'], f"Input changed: {row['instance_id']}")
        instances[row['instance_id']] = item
    groups_text = (root/protocol['a_group_path']).read_text(encoding='utf-8-sig')
    require(hashlib.sha256(groups_text.encode()).hexdigest() == protocol['a_group_normalized_sha256'],
            'A group evidence changed.')
    return dict(protocol=protocol, instances=instances,
                a_groups=list(csv.DictReader(io.StringIO(groups_text))))


def _check_report(instance, report, reference):
    allowed = ('optimal', 'feasible_not_proven', 'infeasible', 'unbounded', 'abnormal', 'model_invalid', 'no_incumbent', 'unknown') if report['algorithm'] == 'MILP' else ('feasible', 'no_placement_found')
    require(report['status'] in allowed, 'Invalid status.')
    require(report['found_valid'] == (report['status'] in ('optimal', 'feasible_not_proven', 'feasible')), 'Status/validity mismatch.')
    require(report['solver_certified_optimal'] == (report['status'] == 'optimal'), 'Optimal certificate/status mismatch.')
    require(report['solver_certified_infeasible'] == (report['status'] == 'infeasible'), 'Infeasible certificate/status mismatch.')
    if report['found_valid']:
        checked = evaluate_model(instance, report['x'], report['y'])
        require(checked['feasible'] and checked['objective'] == report['objective'], 'Invalid solver result.')
        require(report['placement'] == [r.index(1) for r in checked['x']], 'Placement/x mismatch.')
        require(reference['optimum'] is not None and report['objective'] >= reference['optimum'], 'Reference mismatch.')
    else:
        require(report['objective'] is None and report['placement'] is None, 'Failure has an objective.')
    if report['solver_certified_optimal']:
        require(report['status'] == 'optimal' and report['objective'] == reference['optimum'], 'False optimal claim.')
    if report['solver_certified_infeasible']:
        require(report['status'] == 'infeasible' and reference['optimum'] is None, 'False infeasible claim.')
    if report['algorithm'] != 'MILP':
        require(not report['solver_certified_optimal'] and not report['solver_certified_infeasible'], 'Heuristic proof claim.')
    for key in ('build_seconds', 'solve_seconds', 'check_seconds', 'total_seconds'):
        require(report[key] >= 0, 'Negative timing.')


def _result_row(meta, report, timings, reference):
    optimum = reference['optimum']
    obj = report['objective']
    return dict(instance_id=meta['instance_id'], role=meta['role'],
                include_in_main_comparison=meta['include_in_main_comparison'],
                input_canonical_sha256=meta['input_canonical_sha256'],
                algorithm=report['algorithm'], status=report['status'], found_valid=report['found_valid'],
                objective=obj, reference_optimum=optimum,
                found_optimal=(obj is not None and obj == optimum),
                optimality_gap=None if obj is None or optimum is None else (obj-optimum)/optimum,
                placement_json=json.dumps(report['placement']), y_json=json.dumps(report['y']),
                solver_certified_optimal=report['solver_certified_optimal'],
                solver_certified_infeasible=report['solver_certified_infeasible'],
                solver_bound=report['solver_bound'], solver_gap=report['solver_gap'],
                solver_version=report['solver_version'], quality_total_seconds=report['total_seconds'],
                timing_repetitions=len(timings),
                solve_seconds_median=statistics.median(r['solve_seconds'] for r in timings) if timings else None,
                total_seconds_median=statistics.median(r['total_seconds'] for r in timings) if timings else None,
                raw_report_path=f"raw/{meta['instance_id']}__{report['algorithm']}.json")


def _comparison(context, rows):
    results = {(r['instance_id'], r['algorithm']): r for r in rows}
    metas = {r['instance_id']: r for r in context['protocol']['instances']}
    output = []
    for group in context['a_groups']:
        if int(group['source_notebook']) not in context['protocol']['a_comparison_notebooks']:
            continue
        meta = metas[group['instance_id']]
        require(group['input_canonical_sha256'] == meta['input_canonical_sha256'], 'A/B input mismatch.')
        row = {k: group[k] for k in ('source_notebook', 'instance_id', 'input_canonical_sha256', 'p',
               'runs', 'valid_batches', 'optimal_batches', 'mean_selected_objective_valid_only',
               'reference_optimum', 'median_trial_seconds', 'timing_note')}
        for algorithm in ALGORITHMS:
            result = results[(group['instance_id'], algorithm)]
            for key in ('status', 'found_valid', 'objective', 'found_optimal', 'total_seconds_median'):
                row[f'{algorithm}_{key}'] = result[key]
        row['comparison_caveat'] = 'A: Windows historical trial; B: current runtime. Different timing scopes; A20 sleep. No speedup inference.'
        output.append(row)
    require(len(output) == 27, 'Expected 27 A instance/depth groups.')
    return output


def _summary(rows):
    summary = {}
    for algorithm in ALGORITHMS:
        main = [r for r in rows if r['include_in_main_comparison'] and r['algorithm'] == algorithm]
        summary[algorithm] = dict(instances=len(main), valid=sum(r['found_valid'] for r in main),
                                  optimal=sum(r['found_optimal'] for r in main),
                                  no_placement=sum(not r['found_valid'] for r in main))
    return summary


def run_campaign(root, output_dir, machine_label, timing_note='', progress=True):
    root, out = Path(root), Path(output_dir)
    require(bool(machine_label.strip()), 'Provide a machine label.')
    context = load_context(root)
    protocol = context['protocol']
    import ortools
    from ortools.linear_solver import pywraplp
    require(ortools.__version__ == protocol['ortools_version'], 'Wrong OR-Tools version.')
    solver = pywraplp.Solver.CreateSolver(protocol['solver'])
    require(solver is not None, 'SCIP unavailable.')
    runtime = dict(machine_label=machine_label, timing_note=timing_note,
                   platform=platform.platform(), machine=platform.machine(), processor=platform.processor(),
                   python=sys.version, executable=sys.executable, solver_version=solver.SolverVersion(),
                   packages={p: importlib.metadata.version(p) for p in ('numpy', 'ortools', 'protobuf', 'pandas')})
    del solver
    out.mkdir(parents=True, exist_ok=False)
    start = perf_counter()
    campaign = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
                    protocol_sha256=PROTOCOL_HASH, runtime=runtime, completed_records=0)
    save_json(out/'campaign.json', campaign)
    save_json(out/'protocol.json', protocol)
    save_json(out/'a_groups.json', context['a_groups'])
    for path in SOURCE_PATHS:
        destination = out/'source'/path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root/path, destination)
    campaign['source_sha256'] = {path: hashlib.sha256((out/'source'/path).read_bytes()).hexdigest() for path in SOURCE_PATHS}
    save_json(out/'campaign.json', campaign)
    references, rows = {}, []
    try:
        for meta in protocol['instances']:
            name = meta['instance_id']
            instance = context['instances'][name]
            save_json(out/'inputs'/f'{name}.json', instance)
            references[name] = exact_reference(instance)
            for algorithm in ALGORITHMS:
                solve = (lambda: solve_milp(instance, protocol['time_limit_seconds'])) if algorithm == 'MILP' else (lambda: solve_heuristic(instance, algorithm))
                quality = solve()
                _check_report(instance, quality, references[name])
                timings, warmup = [], None
                terminal = quality['status'] in ('feasible', 'no_placement_found', 'optimal', 'infeasible')
                if terminal and quality['total_seconds'] < protocol['repeat_only_if_quality_total_below_seconds']:
                    warmup = solve()
                    _check_report(instance, warmup, references[name])
                    for _ in range(protocol['timing_repetitions']):
                        measurement = solve()
                        _check_report(instance, measurement, references[name])
                        require((measurement['status'], measurement['objective']) == (quality['status'], quality['objective']),
                                'Quality changed during timing; inspect results instead of selecting the best.')
                        timings.append(measurement)
                payload = dict(instance_id=name, input_canonical_sha256=meta['input_canonical_sha256'],
                               quality=quality, warmup=warmup, timings=timings)
                save_json(out/'raw'/f'{name}__{algorithm}.json', payload)
                rows.append(_result_row(meta, quality, timings, references[name]))
                campaign['completed_records'] = len(rows)
                save_json(out/'campaign.json', campaign)
                if progress:
                    print(f"{len(rows):02d}/36 {name:18} {algorithm:8} {quality['status']:20} objective={quality['objective']}", flush=True)
        save_json(out/'references.json', references)
        save_json(out/'results.json', rows)
        write_csv(out/'classical_results.csv', rows)
        comparison = _comparison(context, rows)
        write_csv(out/'comparison_a_b.csv', comparison)
        summary = _summary(rows)
        save_json(out/'summary.json', summary)
        campaign.update(status='completed', finished_utc=datetime.now(timezone.utc).isoformat(),
                        campaign_wall_seconds=perf_counter()-start,
                        timing_scope=protocol['timing_scope'], limitations=protocol['limitations'])
        save_json(out/'campaign.json', campaign)
    except Exception as exc:
        campaign.update(status='failed', error=f'{type(exc).__name__}: {exc}',
                        finished_utc=datetime.now(timezone.utc).isoformat())
        save_json(out/'campaign.json', campaign)
        raise
    audit = verify_campaign(out)
    save_json(out/'audit.json', audit)
    return out


def verify_campaign(output_dir):
    out = Path(output_dir)
    protocol = read_json(out/'protocol.json')
    require(digest(protocol) == PROTOCOL_HASH, 'Protocol checksum differs.')
    campaign = read_json(out/'campaign.json')
    require(campaign['status'] == 'completed' and campaign['completed_records'] == 36, 'Incomplete campaign.')
    for path, checksum in campaign['source_sha256'].items():
        require(hashlib.sha256((out/'source'/path).read_bytes()).hexdigest() == checksum, 'Source snapshot checksum differs.')
    references = read_json(out/'references.json')
    expected, timing_count = [], 0
    for meta in protocol['instances']:
        name = meta['instance_id']
        instance = read_json(out/'inputs'/f'{name}.json')
        require(digest(instance) == meta['input_canonical_sha256'], 'Input checksum differs.')
        require(exact_reference(instance) == references[name], 'Exact reference differs.')
        for algorithm in ALGORITHMS:
            payload = read_json(out/'raw'/f'{name}__{algorithm}.json')
            require(payload['instance_id'] == name and payload['input_canonical_sha256'] == meta['input_canonical_sha256'], 'Raw input linkage differs.')
            require(payload['quality']['algorithm'] == algorithm, 'Wrong algorithm.')
            quality = payload['quality']
            repeat = quality['status'] in ('feasible', 'no_placement_found', 'optimal', 'infeasible') and quality['total_seconds'] < protocol['repeat_only_if_quality_total_below_seconds']
            require(len(payload['timings']) == (protocol['timing_repetitions'] if repeat else 0), 'Timing count differs.')
            require((payload['warmup'] is not None) == repeat, 'Warmup count differs.')
            records = [payload['quality']] + payload['timings'] + ([payload['warmup']] if payload['warmup'] else [])
            for report in records:
                _check_report(instance, report, references[name])
                require(report['algorithm'] == algorithm, 'Wrong timing algorithm.')
                require((report['status'], report['objective']) == (quality['status'], quality['objective']), 'Timing result changed.')
            expected.append(_result_row(meta, payload['quality'], payload['timings'], references[name]))
            timing_count += len(payload['timings'])
    require(expected == read_json(out/'results.json'), 'Results differ from raw reports.')
    # Roundtrip through CSV to verify serialization of booleans/None and every field.
    def csv_rows(rows):
        text = io.StringIO(newline='')
        writer = csv.DictWriter(text, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
        return list(csv.DictReader(io.StringIO(text.getvalue())))
    require(read_csv(out/'classical_results.csv') == csv_rows(expected), 'CSV differs from raw reports.')
    groups = read_json(out/'a_groups.json')
    require(digest(groups) == protocol['a_groups_canonical_sha256'], 'A evidence checksum differs.')
    context = dict(protocol=protocol, a_groups=groups)
    comparison = _comparison(context, expected)
    require(read_csv(out/'comparison_a_b.csv') == csv_rows(comparison), 'A/B comparison differs.')
    require(_summary(expected) == read_json(out/'summary.json'), 'Summary differs.')
    return dict(status='PASS', quality_records=len(expected),
                main_records=sum(r['include_in_main_comparison'] for r in expected),
                timing_records=timing_count, a_comparison_rows=len(comparison),
                milp_certificates_complete=all(r['solver_certified_optimal'] or r['solver_certified_infeasible'] for r in expected if r['algorithm'] == 'MILP'))


def export_campaign(output_dir):
    out = Path(output_dir)
    verify_campaign(out)
    files = sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'SHA256.json')
    save_json(out/'SHA256.json', {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    archive = out.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in files + [out/'SHA256.json']:
            z.write(path, path.relative_to(out).as_posix())
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None, 'Archive CRC error.')
        for name, expected in read_json(out/'SHA256.json').items():
            require(hashlib.sha256(z.read(name)).hexdigest() == expected, 'Archive checksum error.')
    return archive
