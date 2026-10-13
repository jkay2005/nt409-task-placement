"""Notebook 18: exact controls, measured classical solvers and read-only evidence."""
from itertools import product
from math import expm1, log1p
from random import Random
from statistics import median, mean, stdev
from time import perf_counter
from .placement import _arrays


def _problem(instance):
    demand,capacity=_arrays(instance)
    if len(capacity)!=2 or len(demand)>16:
        raise ValueError('This control is limited to two hosts and at most 16 tasks.')
    return demand.tolist(),capacity.tolist()


def _objective(demand,capacity,assignment):
    usage=[[0,0],[0,0]];used=set()
    for (cpu,ram),host in zip(demand,assignment):
        usage[host][0]+=cpu;usage[host][1]+=ram;used.add(host)
    return len(used) if all(usage[h][r]<=capacity[h][r] for h in range(2) for r in range(2)) else None


def structured_reference(instance):
    demand,capacity=_problem(instance)
    values=[_objective(demand,capacity,a) for a in product((0,1),repeat=len(demand))]
    valid=[v for v in values if v is not None];optimum=min(valid) if valid else None
    count=valid.count(optimum) if valid else 0
    return dict(instance_id=instance['instance_id'],assignments=len(values),feasible_count=len(valid),
        optimal_count=count,optimum=optimum,feasible_probability=len(valid)/len(values),
        optimal_probability=count/len(values) if valid else None,
        method='exact enumeration of task-to-host choices; y inferred; overload is failure')


def batch_success(probability,shots):
    if type(shots) is not int or shots<=0:raise ValueError('shots must be a positive integer.')
    if probability is None:return None
    if not 0<=probability<=1:raise ValueError('Probability outside [0,1].')
    return 1. if probability==1 else -expm1(shots*log1p(-probability))


def solve_classical(instance,method,shots=1024,seed=180000):
    """One solve, including input validation and output construction; no optimum input."""
    demand,capacity=_problem(instance);n=len(demand)
    if method=='exact_enumeration':assignments=product((0,1),repeat=n)
    elif method=='random_assignment':
        if type(shots) is not int or shots<=0:raise ValueError('Invalid random draw budget.')
        rng=Random(seed);assignments=(tuple(rng.randrange(2) for _ in range(n)) for _ in range(shots))
    else:raise ValueError('Unknown classical method.')
    best=None;placement=None;feasible=0;count=0
    for assignment in assignments:
        count+=1;objective=_objective(demand,capacity,assignment)
        if objective is not None:
            feasible+=1
            if best is None or objective<best:best=objective;placement=list(assignment)
    return dict(best_objective=best,best_placement=placement,evaluations=count,feasible_draws=feasible)


def measure_classical(instance,blocks=7,target_seconds=.02,max_calls=4096,shots=1024):
    """Warm process microbenchmark. Calibration is excluded, no empty-loop subtraction."""
    if type(blocks) is not int or blocks<3 or target_seconds<=0 or max_calls<1:
        raise ValueError('Invalid timing configuration.')
    reference=structured_reference(instance);rows=[]
    for method in ('exact_enumeration','random_assignment'):
        def run_block(calls,index):
            started=perf_counter();success=0
            for j in range(calls):
                result=solve_classical(instance,method,shots,180000+index*max_calls+j)
                success+=int(reference['optimum'] is not None and result['best_objective']==reference['optimum'])
            return perf_counter()-started,success
        calibration=perf_counter();calls=1
        while True:
            duration,_=run_block(calls,0)
            if duration>=target_seconds or calls>=max_calls:break
            calls=min(2*calls,max_calls)
        calibration=perf_counter()-calibration
        measured=[run_block(calls,k+1) for k in range(blocks)]
        times=[x[0] for x in measured]
        rows.append(dict(instance_id=instance['instance_id'],method=method,shots=shots if method=='random_assignment' else None,
            calls_per_block=calls,block_seconds=times,seconds_median=median(times)/calls,
            seconds_min=min(times)/calls,seconds_max=max(times)/calls,calibration_seconds=calibration,
            reference_optimum=reference['optimum'],successful_calls=sum(x[1] for x in measured),
            total_calls=calls*blocks,target_block_seconds=target_seconds,
            measurement='warm process; per-solve validation, RNG, candidate checking, output and success bookkeeping; excludes imports, calibration, ground-truth preparation'))
    return rows


def aggregate_rows(rows,references):
    """Formal runs only. SD is across seeds; batch success is observed, not a plug-in IID estimate."""
    groups={};seen=set()
    for row in rows:
        if row['role']!='benchmark':continue
        key=(row['encoding'],row['instance_id'],row['p']);identity=key+(row['seed'],)
        if identity in seen:raise ValueError('Duplicate encoding/instance/p/seed.')
        seen.add(identity)
        if row['status']!='completed':raise ValueError('Incomplete quantum evidence.')
        groups.setdefault(key,[]).append(row)
    result=[]
    for (encoding,instance,p),rs in groups.items():
        shots=sum(r['evaluation_shots'] for r in rs)
        def count(field):return sum(round(r[field]*r['evaluation_shots']) for r in rs)
        opt=count('optimal_probability');feasible=count('feasible_probability');prob=opt/shots
        u=rs[0]['uniform_optimal_probability'];random=references[instance]['optimal_probability']
        result.append(dict(encoding=encoding,instance_id=instance,p=p,runs=len(rs),num_qubits=rs[0]['num_qubits'],
            final_shots=shots,optimal_count=opt,feasible_count=feasible,optimal_probability=prob,
            feasible_probability=feasible/shots,ground_probability=count('ground_probability')/shots,
            optimal_probability_sd=stdev(r['optimal_probability'] for r in rs) if len(rs)>1 else None,
            found_optimal_runs=sum(r['found_optimal'] for r in rs),found_valid_runs=sum(r['found_valid'] for r in rs),
            observed_run_success=sum(r['found_optimal'] for r in rs)/len(rs),uniform_optimal_probability=u,
            structured_random_optimal_probability=random,lift_own_uniform=prob/u if u else None,
            lift_structured_random=prob/random if random else None,
            total_seconds=sum(r['total_seconds'] for r in rs),seconds_mean=mean(r['total_seconds'] for r in rs),
            seconds_median=median(r['total_seconds'] for r in rs),total_nfev=sum(r['nfev'] for r in rs),
            total_algorithm_shots=sum(r['total_algorithm_shots'] for r in rs),
            sample_mean_energy=mean(r['sample_mean_energy'] for r in rs)))
    return result


def control_rows(evidence,references):
    controls=[];seen=set()
    for row in evidence['rows']:
        key=(row['encoding'],row['instance_id'])
        if key in seen:continue
        seen.add(key)
        controls.append(dict(instance_id=row['instance_id'],role=row['role'],method='uniform_'+row['encoding'],
            feasible_probability=row['uniform_feasible_probability'],optimal_probability=row['uniform_optimal_probability'],
            optimal_batch_1024_probability=batch_success(row['uniform_optimal_probability'],1024),
            source='analytic uniform on encoded bits; decoded placement quality'))
    for instance,r in references.items():
        role=next(x['role'] for x in evidence['rows'] if x['instance_id']==instance)
        controls.append(dict(instance_id=instance,role=role,method='random_assignment_y_inferred',
            feasible_probability=r['feasible_probability'],optimal_probability=r['optimal_probability'],
            optimal_batch_1024_probability=batch_success(r['optimal_probability'],1024),
            source='exact enumeration of host choices, no repair of overloaded assignments'))
    return controls


def export_summary(folder,archive_path,evidence,references,controls,groups,timings,timing_config):
    """Export derived data plus the unchanged input archive; never overwrite evidence sources."""
    from pathlib import Path
    import csv,json,platform,os,zipfile
    from datetime import datetime,timezone
    from .branch_a_evidence import digest,require
    from .benchmark_a_campaign import save_json
    folder=Path(folder);source=Path(archive_path).resolve();data=source.read_bytes()
    require(digest(data)==evidence['archive_sha256'],'Input archive changed since audit.')
    require(source!= (folder/'notebook17_results.zip').resolve(),'Output must differ from source archive.')
    folder.mkdir(parents=True,exist_ok=True)
    from .two_host_campaign import _environment
    metadata=dict(schema_version=1,scope='phase4j_branch_a_summary_v1',created_at_utc=datetime.now(timezone.utc).isoformat(),
        input_sha256=evidence['archive_sha256'],baseline_sha256=evidence['baseline_sha256'],
        audit_seconds=evidence['audit_seconds'],source_campaigns=evidence['sources'],current_environment=_environment(),
        summary_source_sha256={name:digest((Path(__file__).parent/name).read_bytes()) for name in
            ('branch_a_summary.py','branch_a_evidence.py')},
        processor=platform.processor(),logical_cpus=os.cpu_count(),timing_config=timing_config,
        timing_scope='Warm process timings; historical QAOA trial totals, not matched fresh end-to-end reruns. Preprocessing is reported separately. No quantum jobs run in Notebook18.',
        batch_success_scope='Exact IID probability only for analytical uniform/random controls; QAOA batch success is observed across training seeds.',
        notes=['No FF/BFD/MILP implemented. No quantum advantage claim.',
               'Timing repeated calls are microbenchmark repetitions, not independent QAOA training trials.',
               'System load/CPU equivalence across historical and current sessions is not established.',
               'No synthetic TTS extrapolation from pooled QAOA samples.'])
    save_json(folder/'summary.json',dict(metadata=metadata,references=references,groups=groups,controls=controls,timings=timings))
    save_json(folder/'audit.json',evidence)
    tables={'quantum_runs.csv':evidence['rows'],'quantum_groups.csv':groups,'controls.csv':controls,
        'classical_timings.csv':[{k:(json.dumps(v) if isinstance(v,list) else v) for k,v in r.items()} for r in timings]}
    paths=[folder/'summary.json',folder/'audit.json']
    for name,rows in tables.items():
        path=folder/name
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        paths.append(path)
    (folder/'notebook17_results.zip').write_bytes(data);paths.append(folder/'notebook17_results.zip')
    report=folder/'interpretation.md'
    report.write_text('# Notebook 18 — hướng dẫn diễn giải\n\n'
        '- quantum_groups.csv: tỷ lệ mẫu tối ưu/khả thi; SD giữa các seed; số lượt tìm thấy nghiệm.\n'
        '- controls.csv: xác suất chính xác của uniform và random task-to-host; cột batch dùng 1024 lần lấy mẫu IID.\n'
        '- classical_timings.csv: median/min/max từ các block đo trong phiên hiện tại. Đọc block_seconds/calls_per_block.\n'
        '- summary.json: protocol timing, môi trường mới, nguồn QAOA cũ, preprocessing và giới hạn so sánh.\n'
        '- Quantum total_seconds không phải toàn thời gian notebook; timing cổ điển không bao gồm import/calibration/exact reference.\n'
        '- Chỉ đủ bằng chứng cho so sánh mô tả với các triển khai này; không phải so sánh với mọi solver cổ điển.\n'
        '- Trường hợp vô nghiệm: P_opt không xác định (ô trống/null), P_feasible=0.\n'
        '- Notebook18 chỉ audit và đo classical. Giữ nguyên mọi kết quả QAOA16/17.\n',encoding='utf-8');paths.append(report)
    for name in ('summary_quality.png','cost_comparison.csv'):
        if (folder/name).is_file():paths.append(folder/name)
    save_json(folder/'sha256.json',{p.name:digest(p.read_bytes()) for p in paths});paths.append(folder/'sha256.json')
    archive=folder/f'{folder.name}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in paths:z.write(path,path.name)
    return archive
