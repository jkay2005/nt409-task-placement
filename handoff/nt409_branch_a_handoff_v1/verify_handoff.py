"""Verify the frozen handoff with Python's standard library; no QAOA runs."""
from collections import Counter
from itertools import product
from pathlib import Path, PurePosixPath
from statistics import mean, median
import csv
import hashlib
import json
import math
import zipfile

ROOT = Path(__file__).resolve().parent

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def read_csv(name):
    with (ROOT / 'tables' / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def check():
    files = read_json(ROOT / 'SHA256.json')['files_sha256']
    for name, expected in files.items():
        path = ROOT / name
        require(path.is_file(), f'Missing file: {name}')
        require(digest(path.read_bytes()) == expected, f'File changed: {name}')

    registry = read_csv('instance_registry.csv')
    require(len(registry) == 14, 'Expected 14 frozen instances')
    require(sum(row['include_in_main_comparison'] == 'True' for row in registry) == 9,
            'Expected 9 main comparison instances')
    for row in registry:
        instance = read_json(ROOT / row['input_path'])
        encoded = json.dumps(instance, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')
        require(digest(encoded) == row['input_canonical_sha256'], 'Input canonical hash differs')
        require(instance['instance_id'] == row['instance_id'], 'Instance ID differs')
        histogram = Counter()
        tasks, hosts = instance['tasks'], instance['hosts']
        for assignment in product(range(len(hosts)), repeat=len(tasks)):
            fits = all(sum(task[r] for task, h in zip(tasks, assignment) if h == j) <= host[r]
                       for j, host in enumerate(hosts) for r in ('cpu', 'ram'))
            if fits:
                histogram[len(set(assignment))] += 1
        optimum = min(histogram, default=None)
        require(str(optimum) == row['optimum_active_hosts'] if optimum is not None
                else row['optimum_active_hosts'] == '', 'Reference optimum differs')
        require(sum(histogram.values()) == int(row['feasible_assignments']), 'Feasible count differs')
        require(histogram[optimum] == int(row['optimal_assignments']), 'Optimal count differs')

    archives = read_csv('archive_registry.csv')
    for row in archives:
        with zipfile.ZipFile(ROOT / row['archive_path']) as z:
            names = z.namelist()
            require(len(names) == len(set(names)), 'Duplicate archive members')
            for name in names:
                p = PurePosixPath(name)
                require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,
                        f'Unsafe archive member: {name}')
            require(z.testzip() is None, 'Archive CRC differs')
            if 'sha256.json' in names:
                hashes = json.loads(z.read('sha256.json'))
                require(set(hashes) == set(names) - {'sha256.json'}, 'Archive checksum coverage differs')
                for name, expected in hashes.items():
                    require(digest(z.read(name)) == expected, f'Archive payload differs: {name}')

    runs = read_csv('a_runs.csv')
    groups = read_csv('a_groups.csv')
    require(len(runs) == 196 and len(groups) == 42, 'Run/group coverage differs')
    require(len({(r['study_id'], r['run_key']) for r in runs}) == 196, 'Duplicate run keys')
    for nb, expected in [(16, (45, 29, 24)), (17, (45, 45, 45)),
                         (19, (12, 12, 8)), (20, (90, 90, 63))]:
        selected = [r for r in runs if r['source_notebook'] == str(nb)
                    and r['role'] in ('benchmark', 'test', 'development')]
        observed = (len(selected), sum(r['found_valid'] == 'True' for r in selected),
                    sum(r['found_optimal'] == 'True' for r in selected))
        require(observed == expected, f'Notebook {nb} quality totals differ')
    for group in groups:
        selected = [r for r in runs if all(r[k] == group[k] for k in
                    ('source_notebook', 'instance_id', 'p'))]
        require(len(selected) == int(group['runs']), 'Group size differs')
        require(sum(r['found_optimal'] == 'True' for r in selected) == int(group['optimal_batches']),
                'Group success count differs')
        require(math.isclose(mean(float(r['optimal_probability']) for r in selected),
                             float(group['optimal_probability_mean']), abs_tol=1e-12), 'Group P_opt differs')
        require(math.isclose(median(float(r['total_seconds']) for r in selected),
                             float(group['median_trial_seconds']), abs_tol=1e-9), 'Group timing differs')
    for archive_path in sorted({r['source_archive_path'] for r in runs}):
        with zipfile.ZipFile(ROOT / archive_path) as z:
            for row in (r for r in runs if r['source_archive_path'] == archive_path):
                require(row['raw_report_member'] in z.namelist(), 'Missing raw report')
    print(f'PASS: {len(files)} file hashes; 14 inputs; {len(archives)} archives; '
          '196 run records; 42 groups; campaign totals consistent. No QAOA retraining.')

if __name__ == '__main__':
    check()
