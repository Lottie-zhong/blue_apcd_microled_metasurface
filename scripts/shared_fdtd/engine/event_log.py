from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from shared_fdtd.control_v3.db import utc_now

def _semantic_key(event_type, payload):
    explicit=payload.get('semantic_event_key')
    if explicit: return str(explicit)
    launch_id=payload.get('launch_id') or (payload.get('launch_identity') or {}).get('launch_id')
    identity=(payload.get('case_id') or payload.get('logical_case_id'),payload.get('attempt_id'),launch_id)
    if event_type in {'SCIENTIFIC_SOLVER_ENTERED','SCIENTIFIC_LAUNCH_CLAIMED','SCIENTIFIC_PROCESS_BOUND','GPU_ENGINE_ENTRY_CONFIRMED'} and all(identity):
        return hashlib.sha256(json.dumps([event_type,*identity],separators=(',',':'),sort_keys=True).encode()).hexdigest()
    return None

def _lock_file(path):
    lock=path.with_name(path.name+'.lock').open('a+b')
    if os.name=='nt':
        import msvcrt
        lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
    else:
        import fcntl
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
    return lock

def _unlock(lock):
    try:
        if os.name=='nt':
            import msvcrt
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
    finally: lock.close()

def append_event(path,event_type,**payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    row={'timestamp':utc_now(),'event_type':event_type,**payload};key=_semantic_key(event_type,row)
    if key: row['semantic_event_key']=key
    lock=_lock_file(path)
    try:
        if key and path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                if not line.strip(): continue
                try: old=json.loads(line)
                except json.JSONDecodeError: continue
                if old.get('event_type')==event_type and old.get('semantic_event_key')==key: return old
        with path.open('a',encoding='utf-8') as handle:
            handle.write(json.dumps(row,sort_keys=True,default=str)+'\n');handle.flush();os.fsync(handle.fileno())
        return row
    finally: _unlock(lock)

def read_events(path):
    p=Path(path)
    if not p.exists(): return []
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
