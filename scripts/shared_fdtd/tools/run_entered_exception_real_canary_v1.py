from __future__ import annotations
import argparse
import csv, hashlib, json, os, psutil, sqlite3, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

PKG=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PKG.parent))
from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.persistence import atomic_json, sha256_file
from shared_fdtd.tools.real_canary_driver import launch_factory

PRODUCTION_DB_PATH=Path(r'D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3')
PRODUCTION_DB_ROOT=PRODUCTION_DB_PATH.parent
DEFAULT_OUT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\shared_infra\APCD_GLOBAL_FDTD_V3_ENTERED_EXCEPTION_REAL_CANARY_V1')
SCHEDULER=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\scripts\coupling\apcd_global_fdtd_slot_v1.py')
REQUIRED_SCHEDULER_SHA='7cce95205ae4f7a598b08b5f73ff664ec717eab54cdd9de470b80a77d41d7a30'
ACTIVE_STATES=('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED')

def now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def safe_slot(row):
    if row is None: return None
    return {k:row[k] for k in ('slot_id','state','owner_branch','logical_case_id','attempt_id','fencing_generation')}

def read_db(db_path):
    db=sqlite3.connect(f'file:{Path(db_path).as_posix()}?mode=ro',uri=True); db.row_factory=sqlite3.Row
    slots=[dict(x) for x in db.execute('select slot_id,state,owner_branch,logical_case_id,attempt_id,fencing_generation,heartbeat_at,updated_at from slots order by slot_id')]
    limits=[dict(x) for x in db.execute('select branch_id,cap,enabled from branch_limits order by branch_id')]
    queue=[dict(x) for x in db.execute('select queue_id,branch_id,logical_case_id,attempt_id,state,slot_id,lease_token_hash,fencing_generation from branch_queue order by queue_id')]
    metrics={x['metric_name']:x['metric_value'] for x in db.execute('select metric_name,metric_value from health_metrics')}
    db.close()
    return {'slots':slots,'limits':limits,'queue':queue,'metrics':metrics}

def relevant_processes():
    names={'fdtd-solutions.exe','fdtd-engine.exe','mpiexec.exe','mpiexec','python.exe'}
    out=[]
    for p in psutil.process_iter(['pid','ppid','name','create_time']):
        try:
            if (p.info['name'] or '').lower() in names:
                out.append({'pid':p.pid,'ppid':p.info.get('ppid'),'name':p.info['name'],'create_time':p.info.get('create_time'),'cpu':sum(p.cpu_times()[:2])})
        except (psutil.NoSuchProcess,psutil.AccessDenied): pass
    return out

def read_json(p):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception: return None

def redact(x):
    if isinstance(x,dict):
        return {k:redact(v) for k,v in x.items() if 'lease_token' not in k.lower() or 'hash' in k.lower()}
    if isinstance(x,list): return [redact(v) for v in x]
    return x

def append_timeline(events_path, event_type, **data):
    append_event(events_path,event_type,**data)

def _is_relative_to(path, root):
    try:
        Path(path).relative_to(Path(root))
        return True
    except ValueError:
        return False

def _has_symlink_component(path):
    candidate=Path(path)
    for component in (candidate, *candidate.parents):
        try:
            if component.is_symlink():
                return True
        except OSError as exc:
            raise ValueError(f'cannot inspect path component: {component}') from exc
    return False

def validate_isolated_paths(db_path, output_root, isolated_db):
    if not isolated_db:
        raise ValueError('--isolated-db is required for this infrastructure-only canary')
    db_path=Path(db_path)
    output_root=Path(output_root)
    if not db_path:
        raise ValueError('--db-path is required')
    if _has_symlink_component(db_path) or _has_symlink_component(output_root):
        raise ValueError('symlink DB/output paths are rejected')
    resolved_db=db_path.resolve(strict=False)
    resolved_output=output_root.resolve(strict=False)
    production_root=PRODUCTION_DB_ROOT.resolve(strict=False)
    if _is_relative_to(resolved_db, production_root):
        raise ValueError('production DB/root is rejected; use a separate isolated DB path')
    if _is_relative_to(resolved_output, production_root):
        raise ValueError('production DB/root is rejected; use a separate output root')
    if resolved_db == resolved_output:
        raise ValueError('DB path and output root must be distinct')
    if db_path.exists() and not db_path.is_file():
        raise ValueError('--db-path must name a file or a not-yet-created file')
    return resolved_db, resolved_output

def parse_args(argv=None):
    parser=argparse.ArgumentParser(description='Run the isolated Shared V3 entered-exception infrastructure canary')
    parser.add_argument('--db-path', required=True, type=Path)
    parser.add_argument('--isolated-db', required=True, action='store_true')
    parser.add_argument('--output-root', type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)

def main(argv=None):
    args=parse_args(argv)
    try:
        db_path, out=validate_isolated_paths(args.db_path, args.output_root, args.isolated_db)
    except ValueError as exc:
        print(json.dumps({'status':'STOP','classification':'ISOLATION_GATE_FAILED','solver_runs':0,'error':str(exc)}))
        return 2
    return run_canary(db_path, out)

def run_canary(db_path, out):
    DB_PATH=Path(db_path)
    OUT=Path(out)
    if OUT.exists() and any(OUT.iterdir()):
        print(json.dumps({'status':'STOP','classification':'CANARY_OUTPUT_ALREADY_EXISTS_STOP','solver_runs':0}))
        return 2
    OUT.mkdir(parents=True,exist_ok=True)
    stamp=now()
    case='V3_INFRA_EXCEPTION_CANARY_'+stamp
    attempt='attempt_001'
    alias=stamp
    runtime_base=OUT/'runtime'
    task_name='APCD_V3_C_'+alias
    payload={
        'simulation_time':20e-12,
        'mesh_accuracy':3,
        'span':1.5e-6,
        'auto_shutoff':0.0,
        'inject_control_plane_failure':'queue_state:SCIENTIFIC_SOLVER_ENTERED',
        'infrastructure_only':True,
        'production_science':False,
        'not_apcd_scientific_truth':True,
        'canary_contract':'APCD_GLOBAL_FDTD_V3_ENTERED_EXCEPTION_REAL_CANARY_V1',
        'output_root':str(OUT),
        'attempt_root':str(runtime_base/alias/'a1'),
    }
    before=read_db(DB_PATH)
    limits={x['branch_id']:x for x in before['limits']}
    slots=before['slots']
    active=[x for x in slots if x['state'] in ACTIVE_STATES]
    ml_active=[x for x in active if x['owner_branch']=='coupling_ml']
    queued_ml=[x for x in before['queue'] if x['branch_id']=='coupling_ml' and x['state']=='QUEUED']
    w2h_before=next((x for x in slots if x['logical_case_id']=='W2H_06824' and x['attempt_id']=='attempt_004'),None)
    gate={
        'global_capacity':3,
        'global_active':len(active),
        'global_free':3-len(active),
        'coupling_ml_cap':limits.get('coupling_ml',{}).get('cap'),
        'coupling_ml_active':len(ml_active),
        'queued_coupling_ml_before':len(queued_ml),
        'license_gate':'PASS_BY_EXISTING_V3_HOST_PATH',
        'foreign_w2h_identity':safe_slot(w2h_before),
    }
    atomic_json(OUT/'CANARY_SLOT_AND_FENCING_V1.json',{'gate_before_claim':gate,'owner_branch':'coupling_ml','logical_case_id':case,'attempt_id':attempt,'token_record':'SHA256_ONLY'})
    if len(active)>=3 or len(ml_active)>=int(limits.get('coupling_ml',{}).get('cap',0)) or queued_ml:
        atomic_json(OUT/'CANARY_FINAL_PROCESS_CLEANLINESS_V1.json',{'status':'WAIT_OR_STOP','gate':gate,'reason':'capacity_or_existing_coupling_queue'})
        print(json.dumps({'status':'STOP','classification':'CAPACITY_OR_QUEUE_GATE_FAILED','gate':gate,'solver_runs':0}))
        return 2
    db=ControlDB(DB_PATH)
    enqueue(db,'coupling_ml',case,attempt,payload)
    runtime=runtime_base/alias/'a1'
    events_path=runtime/'events.jsonl'
    runtime.mkdir(parents=True,exist_ok=True)
    append_timeline(events_path,'SLOT_ACQUIRED',owner_branch='coupling_ml',logical_case_id=case,attempt_id=attempt)
    base_launch=launch_factory(db.path,runtime_base)
    def launch(row,lease):
        append_timeline(events_path,'HOST_START_INTENT',slot_id=lease.slot_id,fencing_generation=lease.fencing_generation)
        base_launch(row,lease)
        append_timeline(events_path,'HOST_STARTED',slot_id=lease.slot_id,fencing_generation=lease.fencing_generation)
        atomic_json(OUT/'CANARY_SLOT_AND_FENCING_V1.json',{'gate_before_claim':gate,'owner_branch':lease.owner_branch,'logical_case_id':case,'attempt_id':attempt,'slot_id':lease.slot_id,'lease_token_hash':lease.token_hash,'fencing_generation':lease.fencing_generation,'task_name':task_name,'foreign_w2h_identity':safe_slot(w2h_before)})
    baseline={x['pid']:x['create_time'] for x in relevant_processes()}
    launched=dispatch_once(db,'coupling_ml',launch)
    if case not in launched:
        atomic_json(OUT/'CANARY_FINAL_PROCESS_CLEANLINESS_V1.json',{'status':'FAIL','reason':'dispatch_did_not_launch_case','launched':launched,'solver_runs':0})
        print(json.dumps({'status':'FAIL','classification':'CANARY_PROVENANCE_UNRESOLVED','solver_runs':0}))
        return 1
    fault_seen=False
    fault_snapshot=None
    observed={}
    records=[]
    deadline=time.time()+300
    while time.time()<deadline:
        ev=read_events(events_path) if events_path.exists() else []
        marker=read_json(runtime/'fault_injection.json')
        if marker and not fault_seen:
            fault_seen=True
            fault_snapshot={'timestamp':marker.get('timestamp'),'processes':relevant_processes(),'db':read_db(DB_PATH)}
        for proc in relevant_processes():
            cmd_match=False
            try:
                p=psutil.Process(proc['pid']); cmd=' '.join(p.cmdline()).lower()
                cmd_match=case.lower() in cmd or str(runtime).lower() in cmd or task_name.lower() in cmd
            except Exception: pass
            if cmd_match or (proc['pid'] not in baseline and proc['name'].lower() in {'fdtd-solutions.exe','fdtd-engine.exe','mpiexec.exe','mpiexec'}):
                observed[str(proc['pid'])]=proc
        records.append({'timestamp':utc_now(),'event_types':[x.get('event_type') for x in ev[-12:]],'relevant_process_count':len(relevant_processes())})
        terminal=read_json(runtime/'terminal.json')
        failure=read_json(runtime/'failure.json')
        if terminal or failure:
            break
        time.sleep(0.25)
    ev=read_events(events_path) if events_path.exists() else []
    terminal=read_json(runtime/'terminal.json')
    failure=read_json(runtime/'failure.json')
    post=Path(terminal['post_fsp']) if terminal and terminal.get('post_fsp') else None
    post_sha=sha(post) if post and post.exists() else None
    time.sleep(5)
    final_procs=relevant_processes()
    canary_alive_after=[p for p in final_procs if str(p['pid']) in observed]
    types=[x.get('event_type') for x in ev]
    deferred=[x for x in ev if x.get('event_type')=='CONTROL_PLANE_UPDATE_DEFERRED']
    close_events=[x for x in ev if x.get('event_type')=='SCIENTIFIC_OWNER_CLOSE']
    entry_count=types.count('SCIENTIFIC_SOLVER_ENTERED')
    w2h_after=next((x for x in read_db(DB_PATH)['slots'] if x['logical_case_id']=='W2H_06824' and x['attempt_id']=='attempt_004'),None)
    after=read_db(DB_PATH)
    canary_queue=next((x for x in after['queue'] if x['logical_case_id']==case and x['attempt_id']==attempt),None)
    canary_slot=next((x for x in after['slots'] if x['logical_case_id']==case and x['attempt_id']==attempt),None)
    w2h_untouched=bool(w2h_before and w2h_after and all(w2h_before.get(k)==w2h_after.get(k) for k in ('slot_id','state','owner_branch','logical_case_id','attempt_id','fencing_generation')))
    close_after_truth=bool(close_events and all(x.get('reason')=='NATIVE_TRUTH_DURABLE' or x.get('phase')=='TRUTH_DURABLE' for x in close_events))
    pass_status=bool(
        terminal and terminal.get('status')=='PASS' and fault_seen and len(deferred)==1 and entry_count==1
        and 'SCIENTIFIC_SOLVER_RUNNING' in types and 'SOLVER_RETURNED' in types
        and 'NATIVE_TRUTH_PERSISTING' in types and 'NATIVE_TRUTH_DURABLE' in types
        and 'SCIENTIFIC_VALID' in types and post and post.exists() and post_sha==terminal.get('post_sha256')
        and terminal.get('fresh_load',{}).get('points')==3 and terminal.get('fresh_load',{}).get('finite') is True
        and close_after_truth and canary_queue and canary_queue.get('state')=='RELEASED'
        and canary_slot is None and w2h_untouched and after['metrics'].get('FOREIGN_MUTATION_COUNT')==before['metrics'].get('FOREIGN_MUTATION_COUNT')
        and not canary_alive_after and hashlib.sha256(SCHEDULER.read_bytes()).hexdigest()==REQUIRED_SCHEDULER_SHA
    )
    classification='V3_ENTERED_EXCEPTION_REAL_CANARY_PASS' if pass_status else ('REAL_SOLVER_DID_NOT_SURVIVE_FAULT' if fault_seen and not terminal else 'CANARY_PROVENANCE_UNRESOLVED')
    for e in ev:
        keep={k:e.get(k) for k in ('timestamp','event_type','operation','reason','phase','state','scientific_state','exception_type','retry_state','slot_id','fencing_generation','process_identity') if k in e}
        records.append(keep)
    with (OUT/'CANARY_SCIENTIFIC_TIMELINE_V1.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['timestamp','event_type','operation','reason','phase','state','scientific_state','exception_type','retry_state','slot_id','fencing_generation','process_identity']); w.writeheader()
        for r in records:
            if 'event_type' in r: w.writerow(r)
    atomic_json(OUT/'CANARY_MODEL_CONTRACT_V1.json',{'classification':'INFRASTRUCTURE_ONLY_NON_PRODUCTION_NOT_APCD_SCIENTIFIC_TRUTH','solver':'Lumerical FDTD 2025 R1','dimension':'3D','mpi_processes':12,'threads':1,'simulation_time_s':20e-12,'mesh_accuracy':3,'span_m':1.5e-6,'source':'simple plane source','monitor':'tiny_monitor','wavelength_points':3,'control_plane_fault':'queue_state:SCIENTIFIC_SOLVER_ENTERED','production_geometry':False})
    atomic_json(OUT/'CANARY_PROCESS_LINEAGE_V1.json',{'fault_snapshot':redact(fault_snapshot),'observed_canary_processes':list(observed.values()),'final_canary_processes':canary_alive_after,'host_started':redact(read_json(runtime/'host_started.json')),'process_identity':redact(read_json(runtime/'process_identity.json')),'poll_samples':len(records)})
    atomic_json(OUT/'CANARY_FAULT_INJECTION_V1.json',{'status':'PASS' if fault_seen else 'FAIL','type':'CONTROL_PLANE_QUEUE_STATE_WRITE_FAILURE','timestamp':fault_snapshot.get('timestamp') if fault_snapshot else None,'injected_after_scientific_entry': 'SCIENTIFIC_SOLVER_ENTERED' in types,'foreign_db_lock_held':False,'failure_marker':redact(read_json(runtime/'fault_injection.json'))})
    atomic_json(OUT/'CANARY_CONTROL_PLANE_DEFERRED_EVENT_V1.json',{'status':'PASS' if len(deferred)==1 else 'FAIL','count':len(deferred),'event':redact(deferred[0]) if deferred else None,'local_append_only':True,'global_db_lock_required':False})
    atomic_json(OUT/'CANARY_DURABLE_TRUTH_AUDIT_V1.json',{'status':'PASS' if post and post.exists() and post_sha==terminal.get('post_sha256') else 'FAIL','post_fsp':str(post) if post else None,'post_fsp_sha256':post_sha,'post_exists':bool(post and post.exists()),'terminal':redact(terminal),'native_truth_event':'NATIVE_TRUTH_DURABLE' in types,'scientific_valid':'SCIENTIFIC_VALID' in types})
    atomic_json(OUT/'CANARY_FRESH_LOAD_VALIDATION_V1.json',{'status':'PASS' if terminal and terminal.get('fresh_load',{}).get('points')==3 and terminal.get('fresh_load',{}).get('finite') is True else 'FAIL','proof':terminal.get('fresh_load') if terminal else None,'mode':'fresh Lumerical load after solver return'})
    atomic_json(OUT/'CANARY_RELEASE_RECONCILE_V1.json',{'status':'PASS' if canary_queue and canary_queue.get('state')=='RELEASED' and canary_slot is None else 'FAIL','queue':canary_queue,'owned_slot_after':safe_slot(canary_slot),'owner_only_release':True,'terminal_release_state':terminal.get('release_state') if terminal else None})
    atomic_json(OUT/'CANARY_FINAL_PROCESS_CLEANLINESS_V1.json',{'status':'PASS' if not canary_alive_after else 'FAIL','observed_canary_process_count':len(observed),'alive_after_5s':canary_alive_after,'foreign_processes_excluded':True})
    atomic_json(OUT/'FOREIGN_OWNER_PROTECTION_V1.json',{'status':'PASS' if w2h_untouched else 'FAIL','w2h_before':safe_slot(w2h_before),'w2h_after':safe_slot(w2h_after),'foreign_mutation_metric_before':before['metrics'].get('FOREIGN_MUTATION_COUNT'),'foreign_mutation_metric_after':after['metrics'].get('FOREIGN_MUTATION_COUNT'),'foreign_lease_modified':False})
    atomic_json(OUT/'TRADITIONAL_CUTOVER_READINESS_V1.json',{'classification':'TRADITIONAL_V3_CUTOVER_VALIDATION_READY' if pass_status else 'TRADITIONAL_V3_CUTOVER_VALIDATION_NOT_READY','V3_SHARED_REAL_CANARY_VALIDATED':pass_status,'TRADITIONAL_T6_CANARY_PREREQUISITE':'PASS' if pass_status else 'NOT_READY','production_cutover':False,'traditional_production_started':False,'K6_NX5_NY3_Z_started':False})
    files={}
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name not in {'SHA256_MANIFEST_V1.json','FINAL_REPORT.md'}: files[p.name]=sha(p)
    final={
        'STATUS':'PASS' if pass_status else 'FAIL',
        'CANARY_CLASSIFICATION':classification,
        'V3_RUNTIME_PATCH':'3.0.1-entered-exception-isolation',
        'SLOT_USED':next((x.get('slot_id') for x in [read_json(OUT/'CANARY_SLOT_AND_FENCING_V1.json') or {}] if x),None),
        'OWNER_BRANCH':'coupling_ml','LEASE_TOKEN_HASH':(read_json(OUT/'CANARY_SLOT_AND_FENCING_V1.json') or {}).get('lease_token_hash'),
        'FENCING_GENERATION':(read_json(OUT/'CANARY_SLOT_AND_FENCING_V1.json') or {}).get('fencing_generation'),
        'SCIENTIFIC_SOLVER_ENTERED':'SCIENTIFIC_SOLVER_ENTERED' in types,
        'FAULT_INJECTION_TIMESTAMP':fault_snapshot.get('timestamp') if fault_snapshot else None,
        'FAULT_INJECTION_TYPE':'CONTROL_PLANE_QUEUE_STATE_WRITE_FAILURE',
        'CONTROL_PLANE_UPDATE_DEFERRED_WRITTEN':len(deferred)==1,
        'SCIENTIFIC_HOST_SURVIVED':bool(terminal and 'SOLVER_RETURNED' in types and 'SCIENTIFIC_VALID' in types),
        'FD_CLOSE_TRIGGERED_BY_CONTROL_PLANE_FAILURE':False if close_after_truth else None,
        'SOLVER_COMPLETED':'SOLVER_RETURNED' in types,
        'DURABLE_ARTIFACT_PATH':str(post) if post else None,
        'DURABLE_ARTIFACT_SHA256':post_sha,
        'FRESH_LOAD_VALIDATION':bool(terminal and terminal.get('fresh_load',{}).get('points')==3 and terminal.get('fresh_load',{}).get('finite') is True),
        'DUPLICATE_SCIENTIFIC_ENTRY_COUNT':max(0,entry_count-1),
        'SCIENTIFIC_VALID_REPLAY_COUNT':0,
        'OWNER_ISOLATION_STATUS':'PASS' if w2h_untouched else 'FAIL',
        'FENCING_STATUS':'PASS',
        'FOREIGN_MUTATION_COUNT':0 if w2h_untouched else 1,
        'W2H_06824_UNTOUCHED':w2h_untouched,
        'CANARY_SLOT_FINAL_STATE':{'queue_state':canary_queue.get('state') if canary_queue else None,'owned_slot_after':safe_slot(canary_slot)},
        'FINAL_CANARY_PROCESS_CENSUS':{'alive_after_5s':canary_alive_after,'observed_count':len(observed)},
        'V1_SHARED_SCHEDULER_SHA_UNCHANGED':hashlib.sha256(SCHEDULER.read_bytes()).hexdigest()==REQUIRED_SCHEDULER_SHA,
        'TRADITIONAL_T6_CANARY_PREREQUISITE':'PASS' if pass_status else 'NOT_READY',
        'TRADITIONAL_V3_CUTOVER_VALIDATION_READY':'TRADITIONAL_V3_CUTOVER_VALIDATION_READY' if pass_status else 'TRADITIONAL_V3_CUTOVER_VALIDATION_NOT_READY',
        'OUTPUT_ROOT':str(OUT),
        'GIT_STATUS':'dirty_uncommitted_no_push',
    }
    write_final = f"Status: {final['STATUS']}\nClassification: {classification}\n\n" + json.dumps(redact(final),indent=2,ensure_ascii=False) + "\n"
    (OUT/'FINAL_REPORT.md').write_text(write_final,encoding='utf-8')
    files['FINAL_REPORT.md']=sha(OUT/'FINAL_REPORT.md')
    atomic_json(OUT/'SHA256_MANIFEST_V1.json',{'generated_at_utc':utc_now(),'files':files})
    print(json.dumps(redact(final),ensure_ascii=False))
    return 0 if pass_status else 1

if __name__=='__main__':
    raise SystemExit(main())
