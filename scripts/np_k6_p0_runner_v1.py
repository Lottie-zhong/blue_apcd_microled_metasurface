import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi

ROOT = Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
STAGE = ROOT / 'outputs/np_k6_hf_p0_label_generator_recovery_v1'

def now():
    return datetime.now(timezone.utc).isoformat()

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def atomic(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str), encoding='utf-8')
    tmp.replace(path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True)
    ap.add_argument('--task-name', default='')
    args = ap.parse_args()
    case = args.case
    cdir = STAGE / 'cases' / case
    contract = json.loads((cdir / 'setup_contract.json').read_text(encoding='utf-8-sig'))
    ledger_path = cdir / 'attempt_ledger.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8-sig'))
    run_dir = STAGE / 'runtime_runs' / case / 'attempt_001'
    run_dir.mkdir(parents=True, exist_ok=True)
    run_copy = run_dir / f'{case}_attempt_001_run.fsp'
    post = run_dir / f'{case}_attempt_001_post.fsp'
    status_path = run_dir / 'controller_status.json'
    events_path = run_dir / 'controller_events.jsonl'
    source = Path(contract['source_prefsp_path'])
    if ledger.get('entered') or ledger.get('run_invocation_count', 0) != 0 or post.exists():
        raise RuntimeError('refusing repeat attempt')
    if sha256(source) != contract['setup_sha256']:
        raise RuntimeError('setup SHA mismatch')
    def event(state, **extra):
        item = {'state': state, 'timestamp_utc': now(), 'pid': os.getpid(), 'case_id': case, 'attempt_id': 'attempt_001'}
        item.update(extra)
        atomic(status_path, item)
        with events_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(item, sort_keys=True) + '\n')
        return item
    shutil.copy2(source, run_copy)
    if sha256(run_copy) != contract['setup_sha256']:
        raise RuntimeError('run-copy SHA mismatch')
    event('controller_started', source_prefsp_sha256=sha256(source), run_copy_sha256=sha256(run_copy), task_name=args.task_name or None)
    ledger.update({'entered': True, 'run_invocation_count': 1, 'solver_entered_timestamp_utc': now(), 'controller_started': True, 'scheduler_task_name': args.task_name or None})
    atomic(ledger_path, ledger)
    run_ledger_path = run_dir / 'entered_ledger.json'
    atomic(run_ledger_path, ledger)
    fdtd = None
    try:
        fdtd = lumapi.FDTD(str(run_copy), hide=True)
        ledger['prefsp_opened'] = True
        atomic(ledger_path, ledger); atomic(run_ledger_path, ledger)
        event('prefsp_opened')
        fdtd.run()
        ledger['engine_completed'] = True
        atomic(ledger_path, ledger); atomic(run_ledger_path, ledger)
        event('engine_completed')
        fdtd.save(str(post))
        stable = False
        last = -1
        for _ in range(120):
            if post.exists() and post.stat().st_size > 0:
                size = post.stat().st_size
                if size == last:
                    stable = True
                    break
                last = size
            time.sleep(1)
        if not stable:
            raise RuntimeError('post-FSP did not stabilize')
        post_sha = sha256(post)
        ledger.update({'post_saved': True, 'post_fsp_path': str(post), 'post_fsp_sha256': post_sha})
        atomic(ledger_path, ledger); atomic(run_ledger_path, ledger)
        event('post_fsp_saved', post_fsp_sha256=post_sha, post_fsp_size_bytes=post.stat().st_size)
    except Exception as exc:
        ledger.update({'failure': repr(exc), 'failure_timestamp_utc': now()})
        atomic(ledger_path, ledger); atomic(run_ledger_path, ledger)
        event('controller_failed', error=repr(exc))
        raise
    finally:
        if fdtd is not None:
            fdtd.close()
    ledger['controller_returned'] = True
    atomic(ledger_path, ledger); atomic(run_ledger_path, ledger)
    event('controller_returned')
    print(json.dumps(ledger, indent=2, sort_keys=True))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
