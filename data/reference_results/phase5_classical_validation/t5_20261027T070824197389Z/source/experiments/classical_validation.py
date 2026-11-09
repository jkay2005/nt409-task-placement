"""N29: frozen four-case classical quality comparison; no quantum retraining."""
import importlib.metadata
import math
from pathlib import Path
import platform
from datetime import datetime,timezone
import shutil

from src.classical_baselines import (ALGORITHMS, ORTOOLS_VERSION, SCIP_OPTIONS,
                                     solve_heuristic, solve_milp)
from src.placement import evaluate_model
from src.validation5x3 import load_dataset, assignment_audit, DATA_HASH
from src.three_host_encoding import build_three_host_qubo, three_host_reference
from src.domain_wall_training import _source_hash
from src.shot_noise_campaign import load_json,save_json,digest,file_hash

CASE_IDS=('a3_dev_n5','v5x3_1','v5x3_2','v5x3_3')
MODULE='experiments/classical_validation.py'
PROTOCOL=dict(algorithms=list(ALGORITHMS),milp_time_limit_seconds=600,
              milp_threads=1,scip_options=SCIP_OPTIONS,solves_per_algorithm_case=1,
              timing_purpose='descriptive_only_not_a_speed_benchmark',quantum_depth=2)


def case_inputs(root):
    data=load_dataset(root)
    cases=[data['development_instance'],*data['validation_instances']]
    if tuple(x['instance_id'] for x in cases)!=CASE_IDS:
        raise ValueError('Frozen four-case order changed.')
    if any(len(x['tasks'])!=5 or len(x['hosts'])!=3 for x in cases):
        raise ValueError('Every input must remain five tasks and three hosts.')
    return cases


def reference(instance):
    truth=assignment_audit(instance)
    encoded=three_host_reference(build_three_host_qubo(instance))
    return dict(**truth,uniform_encoded=encoded['uniform_baseline'],
                random_host_inferred_y=encoded['structured_random'])


def assess_result(instance,result,truth):
    """Keep explicit y and distinguish oracle agreement from solver proof."""
    r=dict(result);found=r['found_valid'];gap=None
    if r['algorithm'] not in ALGORITHMS:
        raise ValueError('Unknown classical algorithm.')
    if r['solver_certified_infeasible']:
        raise ValueError('A solver claimed infeasibility for a known feasible input.')
    if found:
        checked=evaluate_model(instance,r['x'],r['y'])
        if not checked['feasible'] or checked['objective']!=r['objective']:
            raise ValueError('Returned x/y do not validate without repair.')
        if r['placement']!=[row.index(1) for row in checked['x']]:
            raise ValueError('Placement differs from explicit x.')
        gap=r['objective']-truth['optimum']
        if gap<0:raise ValueError('Result contradicts exact enumeration.')
    elif any(r[k] is not None for k in ('objective','placement','x','y')):
        raise ValueError('A missing incumbent must not contain a placement.')
    if r['solver_certified_optimal'] and (not found or gap!=0 or r['algorithm']!='MILP' or r['status']!='optimal'):
        raise ValueError('Invalid optimality certificate.')
    if r['algorithm']=='MILP' and (r['status']=='optimal')!=r['solver_certified_optimal']:
        raise ValueError('MILP status and optimality certificate differ.')
    if r['solver_certified_optimal'] and (r['solver_bound'] is None or r['solver_gap'] is None
            or not math.isclose(r['solver_bound'],r['objective'],rel_tol=0,abs_tol=1e-6)
            or not math.isfinite(r['solver_gap']) or abs(r['solver_gap'])>1e-6):
        raise ValueError('An optimal certificate needs a matching finite bound and zero gap.')
    if r['algorithm']=='MILP' and found:
        bound=r['solver_bound']
        if bound is not None:
            if not math.isfinite(bound) or bound>truth['optimum']+1e-6:
                raise ValueError('Solver lower bound contradicts the oracle.')
            expected=max(0.,r['objective']-bound)/max(1.,abs(r['objective']))
            if r['solver_gap'] is None or not math.isfinite(r['solver_gap']) or abs(expected-r['solver_gap'])>1e-8:
                raise ValueError('Solver gap differs from objective/bound.')
    return dict(**r,matches_oracle=bool(found and gap==0),oracle_objective_gap=gap)


def runtime_preflight():
    """Check dependencies without installing or changing the environment."""
    from packaging.requirements import Requirement
    for name in ('ortools','numpy','pandas','absl-py','protobuf','typing-extensions','immutabledict'):
        try:importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError('N29 dependency missing: '+name+'. Read N29_README_FIRST.md.') from error
    version=importlib.metadata.version('ortools')
    if version!=ORTOOLS_VERSION:raise RuntimeError('N29 requires ortools=='+ORTOOLS_VERSION)
    for text in importlib.metadata.requires('ortools') or []:
        req=Requirement(text)
        if (req.marker is None or req.marker.evaluate()) and importlib.metadata.version(req.name) not in req.specifier:
            raise RuntimeError('Unsatisfied OR-Tools dependency: '+text)
    from ortools.linear_solver import pywraplp
    solver=pywraplp.Solver.CreateSolver('SCIP')
    if solver is None or not solver.SetNumThreads(1) or not solver.SetSolverSpecificParametersAsString(SCIP_OPTIONS):
        raise RuntimeError('SCIP unavailable or frozen settings rejected.')
    return dict(python=platform.python_version(),platform=platform.platform(),
                packages={n:importlib.metadata.version(n) for n in ('ortools','numpy','pandas','absl-py','protobuf','typing-extensions','immutabledict')},
                solver=solver.SolverVersion(),threads=1)


def _inside(root,name):
    root=Path(root).resolve();path=(root/name).resolve()
    if not path.is_relative_to(root):raise ValueError('Evidence path escapes its root.')
    return path


def quantum_evidence(root):
    """Read archived evidence; current classical runtime need not equal its runtime."""
    from src import domain_wall_training as n27
    from experiments import domain_wall_validation as n28
    root=Path(root);receipts={};rows=[]
    specs=[('N27','phase5_domainwall_training',n27.make_plan(False)),
           ('N28','phase5_domainwall_validation',n28.make_plan(False))]
    for label,parent,plan in specs:
        pointer=load_json(root/'data/reference_results'/parent/(label+'_ACTIVE.json'))
        folder=_inside(root,pointer['relative_folder'])
        if (folder/'RUNNING.lock').exists():raise RuntimeError(label+' has an active/stale writer lock.')
        c=load_json(folder/'campaign.json');ident=c['identity'];data=load_dataset(root)
        if digest(ident)!=c['identity_sha256'] or ident['software_validation'] or c['plan']!=plan:
            raise ValueError(label+' is not the unchanged primary protocol.')
        if ident['dataset_sha256']!=DATA_HASH or load_json(folder/'dataset.json')!=data or ident['protocol']!=data['planned_training']:
            raise ValueError(label+' dataset/protocol differs.')
        expected=case_inputs(root)[:1] if label=='N27' else case_inputs(root)[1:]
        cases=[dict(input=ident['input'],qubits=ident['qubits'])] if label=='N27' else ident['cases']
        if [x['input'] for x in cases]!=expected or any(x['qubits']!=25 for x in cases):
            raise ValueError(label+' input scope differs.')
        manifest=load_json(folder/'SHA256.json')
        if not all(file_hash(_inside(folder,n))==h for n,h in manifest.items()):
            raise ValueError(label+' exported evidence checksum differs.')
        for name,h in ident['source_sha256'].items():
            rel='src/'+name if label=='N27' else name
            if n27._source_hash(_inside(folder/'source',rel))!=h:
                raise ValueError(label+' source snapshot differs.')
            if (root/rel).exists() and n27._source_hash(root/rel)!=h:
                raise ValueError(label+' source differs from the current shared implementation.')
        if set(c['stages'])!={s['id'] for s in plan}:raise ValueError(label+' is incomplete.')
        reports={}
        for st in plan:
            entry=c['stages'][st['id']];path='raw/'+st['id']+'.json'
            r=load_json(folder/path);reports[st['id']]=r
            if entry['path']!=path or file_hash(folder/path)!=entry['sha256'] or r['stage']!=st or r['status']!=entry['status'] or r['status']!='completed':
                raise ValueError(label+' raw stage differs or is incomplete.')
            if len(r['history'])!=r['calls']['objective'] or r['calls']['objective']>st['cap']:
                raise ValueError(label+' stage budget differs.')
        for st in plan:
            if st['p']!=2:continue
            r=reports[st['id']];prev=reports[st['depends_on']];point=prev['point']
            if r['initial_point']!=[point[0],point[0],point[1],point[1]] or r['dependency_sha256']!=c['stages'][st['depends_on']]['sha256']:
                raise ValueError(label+' p2 dependency differs.')
            rows.append(dict(instance_id=st.get('instance_id','a3_dev_n5'),variant=st['variant'],p=2,
                **r['final_exact'],final_measured=r['final_measured'],
                training_objective_calls=prev['calls']['objective']+r['calls']['objective'],
                training_cap=200,elapsed_stage_seconds=prev['elapsed_seconds']+r['elapsed_seconds'],
                source_campaign=label,source_stage=st['id'],source_raw_sha256=c['stages'][st['id']]['sha256'],
                original_runtime=ident['runtime']))
        receipts[label]=dict(relative_folder=pointer['relative_folder'],campaign_sha256=file_hash(folder/'campaign.json'),
            manifest_sha256=file_hash(folder/'SHA256.json'),identity_sha256=c['identity_sha256'],
            completed_stages=len(reports),objective_calls=sum(r['calls']['objective'] for r in reports.values()))
        if label=='N28':
            pre=ident['predecessor'];previous=receipts['N27']
            if any(pre[k]!=previous[k] for k in pre):raise ValueError('N28 refers to a different N27.')
    return dict(receipts=receipts,rows=rows)

def identity(root):
    root=Path(root);cases=case_inputs(root);runtime=runtime_preflight();quantum=quantum_evidence(root)
    sources=[p.relative_to(root).as_posix() for p in sorted((root/'src').glob('*.py'))]+[MODULE]
    return dict(study='nt409_classical_t5_v1',dataset_sha256=DATA_HASH,protocol=PROTOCOL,
        cases=[dict(input=x,input_sha256=digest(x)) for x in cases],runtime=runtime,
        quantum=quantum,source_sha256={n:_source_hash(root/n) for n in sources})


def create_campaign(root,output=None):
    root=Path(root).resolve();ident=identity(root)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=Path(output).resolve() if output else root/'data/reference_results/phase5_classical_validation'/('t5_'+stamp)
    if folder.exists():
        checked_campaign(root,folder);return folder
    folder.mkdir(parents=True)
    for name in ident['source_sha256']:
        target=folder/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,target)
    for case in ident['cases']:save_json(folder/'inputs'/(case['input']['instance_id']+'.json'),case['input'])
    save_json(folder/'dataset.json',load_dataset(root))
    for label,receipt in ident['quantum']['receipts'].items():
        shutil.copytree(_inside(root,receipt['relative_folder']),folder/'quantum_evidence'/label)
    save_json(folder/'campaign.json',dict(schema_version=1,created_utc=stamp,identity=ident,
        identity_sha256=digest(ident),cases={}))
    return folder


def checked_campaign(root,folder):
    folder=Path(folder);c=load_json(folder/'campaign.json');ident=c['identity']
    if digest(ident)!=c['identity_sha256'] or ident!=identity(root):
        raise ValueError('N29 data, source, runtime or quantum evidence changed.')
    if load_json(folder/'dataset.json')!=load_dataset(root):raise ValueError('Dataset snapshot changed.')
    for name,h in ident['source_sha256'].items():
        if _source_hash(folder/'source'/name)!=h:raise ValueError('Source snapshot changed.')
    for case in ident['cases']:
        if load_json(folder/'inputs'/(case['input']['instance_id']+'.json'))!=case['input']:
            raise ValueError('Input snapshot changed.')
    for label,receipt in ident['quantum']['receipts'].items():
        q=folder/'quantum_evidence'/label
        if file_hash(q/'campaign.json')!=receipt['campaign_sha256'] or file_hash(q/'SHA256.json')!=receipt['manifest_sha256']:
            raise ValueError('Quantum evidence snapshot changed.')
        if not all(file_hash(_inside(q,n))==h for n,h in load_json(q/'SHA256.json').items()):
            raise ValueError('Quantum snapshot checksum differs.')
    if set(c['cases'])-set(CASE_IDS):raise ValueError('Unknown case in ledger.')
    for cid,entry in c['cases'].items():
        path='raw/'+cid+'.json';r=load_json(folder/path)
        if entry['path']!=path or file_hash(folder/path)!=entry['sha256'] or r['status']!=entry['status'] or r['instance_id']!=cid:
            raise ValueError('Raw case and ledger differ.')
        for result in r['results']:
            if 'model_lp_file' in result and file_hash(_inside(folder,result['model_lp_file']))!=result['model_lp_sha256']:
                raise ValueError('Exported MILP model changed.')
    return c


def open_campaign(root):
    root=Path(root).resolve();pointer=root/'data/reference_results/phase5_classical_validation/N29_ACTIVE.json'
    if pointer.exists():
        folder=_inside(root,load_json(pointer)['relative_folder']);checked_campaign(root,folder);return folder
    folder=create_campaign(root)
    save_json(pointer,dict(relative_folder=folder.relative_to(root).as_posix()))
    return folder


def _record_case(folder,c,r):
    path='raw/'+r['instance_id']+'.json';save_json(folder/path,r)
    c['cases'][r['instance_id']]=dict(path=path,sha256=file_hash(folder/path),status=r['status'])
    save_json(folder/'campaign.json',c)


def run_campaign(root,folder,instance_id=None,progress=True):
    """One recorded attempt per algorithm/case; interrupted attempts require review."""
    from time import perf_counter
    import traceback
    folder=Path(folder);lock=folder/'RUNNING.lock'
    if instance_id is not None and instance_id not in CASE_IDS:raise ValueError('Unknown case.')
    with lock.open('x',encoding='utf-8') as stream:stream.write(datetime.now(timezone.utc).isoformat())
    try:
        c=checked_campaign(root,folder)
        if any(e['status']!='completed' for e in c['cases'].values()):
            raise RuntimeError('An unfinished attempt exists. Export evidence for review; do not reset or retry.')
        for case in c['identity']['cases']:
            inp=case['input'];cid=inp['instance_id']
            if instance_id is not None and cid!=instance_id:continue
            if cid in c['cases']:
                if progress:print(cid+': already completed; no solver rerun.',flush=True)
                continue
            if any(k not in c['cases'] for k in CASE_IDS[:CASE_IDS.index(cid)]):
                raise ValueError('Run the four cases in their frozen order.')
            start=perf_counter()
            r=dict(instance_id=cid,input_sha256=case['input_sha256'],status='running',
                   reference=reference(inp),results=[],attempts=[])
            _record_case(folder,c,r)
            try:
                for algorithm in ALGORITHMS:
                    attempt=dict(algorithm=algorithm,status='in_flight');r['attempts'].append(attempt)
                    _record_case(folder,c,r)
                    if progress:print(cid+' / '+algorithm+': solving...',flush=True)
                    result=(solve_milp(inp,time_limit_seconds=PROTOCOL['milp_time_limit_seconds'])
                            if algorithm=='MILP' else solve_heuristic(inp,algorithm))
                    r['results'].append(result);_record_case(folder,c,r)
                    if result['algorithm']!=algorithm:raise ValueError('Solver returned a different algorithm.')
                    if 'model_lp' in result:
                        path='models/'+cid+'.lp';target=folder/path;target.parent.mkdir(exist_ok=True)
                        target.write_text(result.pop('model_lp'),encoding='utf-8')
                        result.update(model_lp_file=path,model_lp_sha256=file_hash(target))
                    r['results'][-1]=assess_result(inp,result,r['reference'])
                    attempt['status']='completed';_record_case(folder,c,r)
                    if progress:print('  '+result['status']+'; objective='+str(result['objective']),flush=True)
                r.update(status='completed',case_wall_seconds=perf_counter()-start)
            except (Exception,KeyboardInterrupt) as error:
                status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed'
                r.update(status=status,error_type=type(error).__name__,error=str(error),
                         traceback=traceback.format_exc(),case_wall_seconds=perf_counter()-start)
                if r['attempts']:r['attempts'][-1]['status']=status
                _record_case(folder,c,r)
                raise
            _record_case(folder,c,r)
        return c
    finally:
        lock.unlink()


def summarize(root,folder):
    folder=Path(folder);c=checked_campaign(root,folder);cases=[];classical=[];controls=[];attempts=0
    for case in c['identity']['cases']:
        cid=case['input']['instance_id'];entry=c['cases'].get(cid)
        cases.append(dict(instance_id=cid,status=entry['status'] if entry else 'pending'))
        if entry is None:continue
        r=load_json(folder/entry['path']);attempts+=len(r['attempts'])
        truth=r['reference']
        for result in r['results']:
            # Unchecked solver returns remain in raw evidence, not comparison tables.
            if 'matches_oracle' not in result:continue
            classical.append(dict(instance_id=cid,oracle_optimum=truth['optimum'],**result))
        for name,key in (('uniform_encoded','optimal_placement_probability'),('random_host_inferred_y','optimal_probability')):
            control=truth[name]
            controls.append(dict(instance_id=cid,method=name,p_valid=control['feasible_probability'],p_opt=control[key]))
    complete=sum(x['status']=='completed' for x in cases)
    milp=[r for r in classical if r['algorithm']=='MILP']
    return dict(study=c['identity']['study'],cases=cases,completed_cases=complete,
        complete=complete==4,solver_attempts=attempts,expected_solver_attempts=12,
        all_milp_certified=len(milp)==4 and all(r['solver_certified_optimal'] for r in milp),
        classical_rows=classical,quantum_rows=c['identity']['quantum']['rows'],control_rows=controls,
        warning='Four fixed 5x3 inputs: one development and three conditioned validation cases. '
                'One classical solve per algorithm/case; timings are descriptive, not a speed benchmark. '
                'QAOA probabilities describe samples, not classical solver certificates. '
                'Random-host control infers y; uniform-encoded control does not. '
                'QAOA p2 is primary and its training cost includes p1. No quantum retraining.')


def export_campaign(root,folder):
    import csv
    import zipfile
    folder=Path(folder)
    if (folder/'RUNNING.lock').exists():raise RuntimeError('Wait for the writer before export.')
    summary=summarize(root,folder);save_json(folder/'summary.json',summary)
    tables={
        'classical':('instance_id','algorithm','status','found_valid','objective','oracle_optimum',
                     'oracle_objective_gap','matches_oracle','solver_certified_optimal','solver_bound',
                     'solver_gap','build_seconds','solve_seconds','check_seconds','total_seconds'),
        'quantum':('instance_id','variant','p','mean_energy','p_domain','p_valid','p_opt','p_ground',
                   'training_objective_calls','training_cap','elapsed_stage_seconds','source_campaign','source_raw_sha256'),
        'control':('instance_id','method','p_valid','p_opt')}
    for name,columns in tables.items():
        with (folder/(name+'_comparison.csv')).open('w',newline='',encoding='utf-8-sig') as stream:
            writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore')
            writer.writeheader();writer.writerows(summary[name+'_rows'])
    manifest=folder/'SHA256.json'
    files=sorted(p for p in folder.rglob('*') if p.is_file() and p!=manifest)
    save_json(manifest,{p.relative_to(folder).as_posix():file_hash(p) for p in files})
    archive=folder.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(folder).as_posix())
    return archive
