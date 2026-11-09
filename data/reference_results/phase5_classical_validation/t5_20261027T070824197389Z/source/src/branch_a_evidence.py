"""Read-only cross-platform semantic audit of frozen Notebook 16/17 ZIPs."""
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from time import perf_counter
import zipfile
from . import benchmark_a_campaign as old
from . import two_host_campaign as compact
from .independent_campaign import canonical_hash


def digest(data):return hashlib.sha256(data).hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def read_verified_zip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist()
        require(len(names)==len(set(names)),'Duplicate archive member.')
        require(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts
                    and '\\' not in n and ':' not in n and not n.endswith('/') for n in names),'Unsafe archive name.')
        require(sum(i.file_size for i in z.infolist())<=512*2**20,'Archive exceeds review size limit.')
        payload={n:z.read(n) for n in names}
    checks=json.loads(payload['sha256.json'])
    require(set(checks)==set(payload)-{'sha256.json'},'Checksum coverage differs.')
    for name,expected in checks.items():require(digest(payload[name])==expected,f'Checksum differs: {name}')
    return payload


def compare_csv(data,rows):
    actual=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
    expected=[{k:'' if v is None else str(v) for k,v in row.items()} for row in rows]
    require(actual==expected,'Exported CSV differs from independently audited report rows.')


def _sources(environment):
    groups=[environment['core']['source_sha256'],environment['branch_a_source_sha256']]
    if 'encoding_source_sha256' in environment:groups.append(environment['encoding_source_sha256'])
    current=compact._environment()
    expected=[current['core']['source_sha256'],current['branch_a_source_sha256']]
    if len(groups)==3:expected.append(current['encoding_source_sha256'])
    results={}
    for recorded,local in zip(groups,expected):
        require(set(recorded)==set(local),'Recorded source module set differs.')
        for name,checksum in recorded.items():
            data=(Path(__file__).parent/name).read_bytes();lf=data.replace(b'\r\n',b'\n')
            require(checksum in {digest(data),digest(lf),digest(lf.replace(b'\n',b'\r\n'))},f'Source changed: {name}')
            results[name]='exact' if digest(data)==checksum else 'LF_CRLF_only'
    return results


def _audit_campaign(payload,context,is_compact,progress):
    module=compact if is_compact else old
    campaign=json.loads(payload['campaign.json']);design=campaign['design'];env=design['environment']
    require(campaign['schema_version']==1 and campaign['scope']==module.SCOPE
        and design['benchmark']==context and campaign['design_hash']==canonical_hash(design)
        and campaign['planned_runs']==module.make_trials(context) and campaign['active'] is None,'Campaign design or matrix differs.')
    source_check=_sources(env)
    if is_compact:
        require(design['encoding']==compact.ENCODING and
            digest(payload['baseline_notebook16.zip'])==design['baseline_sha256'],'Baseline identity differs.')
    trials={t['run_key']:t for t in campaign['planned_runs']};seen=set();successful={};probes=set()
    for number,row in enumerate(campaign['attempts'],1):
        if progress and (number==1 or number%5==0):print(f"Audit Notebook {'17' if is_compact else '16'}: {number}/{len(campaign['attempts'])}",flush=True)
        require(row['run_key'] in trials and row['number']==number,'Unknown ledger identity.')
        envelope=json.loads(payload[row['report']]);a=envelope['attempt'];r=envelope['result'];t=trials[row['run_key']]
        require(envelope['campaign_id']==campaign['campaign_id'] and envelope['design_hash']==campaign['design_hash']
            and a['number']==number and a['trial']==t and a['kind']==row['kind'] and a['report']==row['report']
            and row['report_sha256']==digest(payload[row['report']]) and r['status']==row['status']
            and row['instance_id']==t['instance_id'] and row['reps']==t['config']['reps'],'Ledger/report mismatch.')
        module._validate_result(r,a,context,env)
        if r['status']=='completed':
            require(all(r[k]==v for k,v in env['core']['runtime'].items()),'Runtime metadata differs.')
        if r['status'] in ('completed','passed'):
            key=(row['kind'],row['run_key']);require(key not in seen,'Duplicate success.');seen.add(key)
            if row['kind']=='trial':successful[row['run_key']]=r
            else:probes.add((t['instance_id'],t['config']['reps']))
    require(set(successful)==set(trials),'Incomplete campaign; all formal and negative trials required.')
    expected={(t['instance_id'],t['config']['reps']) for t in trials.values() if t['role']=='benchmark'}
    require(probes==expected,'Missing or unexpected successful probes.')
    rows=[]
    for t in campaign['planned_runs']:
        attempts=[a for a in campaign['attempts'] if a['kind']=='trial' and a['run_key']==t['run_key']]
        require(attempts[-1]['status']=='completed','Later failed attempt found.')
        r=successful[t['run_key']];row=compact._baseline_row(t,r,attempts)
        if is_compact:row.update(encoding=compact.ENCODING,total_algorithm_shots=r['total_algorithm_shots'],
            shot_accounting='counted_sampler_submissions_plus_independent_final')
        row['evaluation_shots']=t['config']['evaluation_shots']
        rows.append(row)
    return rows,dict(campaign_id=campaign['campaign_id'],environment=env,source_check=source_check,
        statuses=dict(Counter(a['kind']+':'+a['status'] for a in campaign['attempts'])),
        preprocessing_seconds=sum(row.get('model_reference_certificate_seconds',row.get('model_reference_seconds',0))
            for session in campaign['preprocessing_sessions'] for row in session['rows']))


def audit_archives(archive_path,context,progress=True):
    """No QAOA calls, no archive extraction, no edits to input archives."""
    started=perf_counter();data=Path(archive_path).read_bytes();new=read_verified_zip(data)
    baseline_bytes=new['baseline_notebook16.zip'];baseline=read_verified_zip(baseline_bytes)
    old_rows,old_meta=_audit_campaign(baseline,context,False,progress)
    new_rows,new_meta=_audit_campaign(new,context,True,progress)
    # The legacy Notebook16 CSV lacks encoding fields; the imported table in 17 is checked here.
    without_extra=lambda rs:[{k:v for k,v in r.items() if k!='evaluation_shots'} for r in rs]
    compare_csv(new['compact_results.csv'],without_extra(new_rows))
    compare_csv(new['encoding_comparison.csv'],without_extra(old_rows+new_rows))
    old_csv=list(csv.DictReader(io.StringIO(baseline['branch_a_results.csv'].decode('utf-8-sig'))))
    require(bool(old_csv),'Missing old CSV rows.')
    compare_csv(baseline['branch_a_results.csv'],[{k:r[k] for k in old_csv[0]} for r in old_rows])
    return dict(rows=old_rows+new_rows,archive_sha256=digest(data),baseline_sha256=digest(baseline_bytes),
        sources={'notebook16':old_meta,'notebook17':new_meta},audit_seconds=perf_counter()-started,
        interpretation='Semantic consistency audit, not independent attestation of the original machine.')
