"""Read-only DIAG2 science binding checks. No solver or database mutation."""
from pathlib import Path
import sqlite3

def validate_manifest(ledger, manifest, executor):
    if Path(executor).resolve() != Path(ledger['sole_supported_executor']).resolve():
        raise ValueError('UNSUPPORTED_LEGACY_EXECUTOR')
    if len(manifest.get('jobs', [])) != 1:
        raise ValueError('SINGLE_CASE_TRUTH_BEFORE_NEXT_REQUIRED')
    job=manifest['jobs'][0]
    matches=[x for x in ledger['cases'] if x['external_execution_id']==job.get('external_execution_id')]
    if len(matches)!=1: raise ValueError('UNBOUND_EXECUTION_ID')
    b=matches[0]
    for key in ['case_id','attempt_id','external_job_id','physical_contract_sha256','source_fsp_sha256','resource_requirements']:
        if job.get(key)!=b[key]: raise ValueError('SCIENCE_BINDING_MISMATCH:'+key)
    if Path(job['input_fsp']).resolve()!=Path(b['source_fsp']).resolve():
        raise ValueError('SCIENCE_BINDING_MISMATCH:source_fsp')
    if manifest['batch_name']!=b['runner_batch_name'] or manifest['science_batch_id']!=b['science_batch_id']:
        raise ValueError('SCIENCE_BATCH_MISMATCH')
    if manifest['science_dataset_id']!=b['dataset_id'] or manifest['science_case_request_sha256']!=b['case_request_sha256']:
        raise ValueError('SCIENCE_REQUEST_MISMATCH')
    return b

def reconcile(ledger):
    db=Path(ledger['sole_entry_evidence_db'])
    con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    con.row_factory=sqlite3.Row
    try:
        result=[]
        for b in ledger['cases']:
            jobs=con.execute('SELECT * FROM jobs WHERE external_execution_id=?',(b['external_execution_id'],)).fetchall()
            if len(jobs)!=1: raise ValueError('JOB_BINDING_CARDINALITY')
            j=dict(jobs[0])
            for k in ['case_id','attempt_id','external_job_id','physical_contract_sha256']:
                if j[k]!=b[k]: raise ValueError('REGISTERED_SCIENCE_MISMATCH:'+k)
            if j['id']!=b['runner_job_id'] or j['batch_id']!=b['runner_batch_id'] or j['input_fsp_sha256']!=b['source_fsp_sha256']:
                raise ValueError('JOB_ID_OR_SOURCE_MISMATCH')
            entries=[dict(x) for x in con.execute('SELECT * FROM solver_entries WHERE job_id=? OR external_execution_id=?',(j['id'],b['external_execution_id']))]
            if len(entries)>1: raise ValueError('ENTRY_CARDINALITY')
            for e in entries:
                if e['execution_mode']!='REAL' or e['solver_entered']!=1: raise ValueError('NON_SCIENCE_RESERVATION_IN_PRODUCTION')
                if e['case_id']!=b['case_id'] or e['attempt_id']!=b['attempt_id'] or e['pre_fsp_sha256']!=b['source_fsp_sha256'] or e['physical_contract_sha256']!=b['physical_contract_sha256']:
                    raise ValueError('ENTRY_SCIENCE_MISMATCH')
            result.append(dict(case_id=b['case_id'],entered_count=len(entries),entry=entries[0] if entries else None,status=j['status']))
        total=sum(x['entered_count'] for x in result)
        if total>ledger['inherited_total_limit']: raise ValueError('BUDGET_EXCEEDED')
        return dict(entered_total=total,cases=result,rule='REAL reservation consumes even FAILED; never Runner COMPLETED => labels-valid')
    finally:con.close()
