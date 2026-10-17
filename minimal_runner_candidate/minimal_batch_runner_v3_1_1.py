"""Generic APCD Runner 3.1.1. Shared CPU/GPU server admission.

The shared file mutex coordinates participating V3.1.1 processes only.
It does not fence V2.1, manual GUI launches, or other users' solvers.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import shared_resource_gate
from datetime import datetime, timezone

VERSION = '3.1.1-shared-server'
DEFAULT_ROOT = Path(__file__).resolve().parent
DEFAULT_LOCK = Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\gpu_runner_v31_shared.lock')
POLICY_PATH = DEFAULT_LOCK.parent / 'shared_resource_policy.json'
IDENTITY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:/@+\-]{0,199}$')
SHA = re.compile(r'^[0-9a-fA-F]{64}$')
log = logging.getLogger('apcd.runner.v31')


class ResourceGateError(RuntimeError):
    pass


class NoReplayError(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class MinimalBatchRunner:
    def __init__(self, db_path=None, output_dir=None, lock_path=None):
        self.db_path = str(Path(db_path or DEFAULT_ROOT / 'data/runner_v31.db').resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.output_dir = Path(output_dir or Path(self.db_path).parent / 'outputs' / Path(self.db_path).stem).resolve()
        self.gpu_lock_file = Path(lock_path or DEFAULT_LOCK).resolve()
        self.gpu_lock_handle = None
        self.last_hold = False
        self._init_db()

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        try:
            with con:
                yield con
        finally:
            con.close()

    def _init_db(self):
        with self._connect() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute('CREATE TABLE IF NOT EXISTS batches(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,description TEXT,status TEXT DEFAULT \'PENDING\',created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            con.execute('CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,batch_id INTEGER NOT NULL,input_fsp_path TEXT NOT NULL,input_fsp_sha256 TEXT NOT NULL,status TEXT DEFAULT \'PENDING\',created_at TEXT DEFAULT CURRENT_TIMESTAMP,started_at TEXT,completed_at TEXT,output_fsp_path TEXT,error_message TEXT,FOREIGN KEY(batch_id) REFERENCES batches(id))')
            con.execute('CREATE TABLE IF NOT EXISTS solver_entries(id INTEGER PRIMARY KEY,job_id INTEGER NOT NULL UNIQUE,attempt_id TEXT NOT NULL,entered_at TEXT NOT NULL,FOREIGN KEY(job_id) REFERENCES jobs(id))')
            additions = {
                'jobs': {'external_execution_id': 'TEXT', 'external_job_id': 'TEXT', 'attempt_id': 'TEXT', 'case_id': 'TEXT', 'physical_contract_sha256': 'TEXT', 'log_path': 'TEXT', 'output_sha256': 'TEXT', 'execution_mode': 'TEXT', 'resource_requirements': 'TEXT', 'manifest_json': 'TEXT'},
                'solver_entries': {'external_execution_id': 'TEXT', 'solver_entered': 'INTEGER', 'pre_fsp_sha256': 'TEXT', 'physical_contract_sha256': 'TEXT', 'case_id': 'TEXT', 'execution_mode': 'TEXT'}
            }
            for table, columns in additions.items():
                existing = {r['name'] for r in con.execute('PRAGMA table_info(' + table + ')')}
                for key, kind in columns.items():
                    if key not in existing:
                        con.execute('ALTER TABLE ' + table + ' ADD COLUMN ' + key + ' ' + kind)
            # No source-FSP hash uniqueness: different execution identities may share input.
            con.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_execution_registration ON jobs(external_execution_id) WHERE external_execution_id IS NOT NULL')
            con.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_execution_entry ON solver_entries(external_execution_id) WHERE external_execution_id IS NOT NULL')

    def _acquire_gpu_lock(self, timeout=0):
        if self.gpu_lock_handle is not None:
            raise ResourceGateError('Resource gate HOLD: this instance already holds the mutex')
        handle = None
        try:
            import msvcrt
            self.gpu_lock_file.parent.mkdir(parents=True, exist_ok=True)
            handle = open(self.gpu_lock_file, 'a+b')
            if self.gpu_lock_file.stat().st_size == 0:
                handle.write(b'\0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            self.gpu_lock_handle = handle
            return True
        except Exception as exc:
            if handle is not None:
                handle.close()
            raise ResourceGateError('Resource gate HOLD: shared file mutex unavailable or occupied: ' + str(exc)) from exc

    def _release_gpu_lock(self):
        handle, self.gpu_lock_handle = self.gpu_lock_handle, None
        if handle is not None:
            try:
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                handle.close()

    def _require_live_exclusion(self, job=None):
        try:
            if self.gpu_lock_handle is None or job is None:
                raise ValueError('Real admission requires the APCD shared mutex and registered job')
            policy = json.loads(POLICY_PATH.read_text(encoding='utf-8'))
            if Path(self.db_path) != Path(policy['canonical_db']).resolve() or self.gpu_lock_file != DEFAULT_LOCK.resolve():
                raise ValueError('Real admission requires canonical APCD database and mutex')
            if Path(__file__).resolve() != Path(policy['installed_runner']).resolve():
                raise ValueError('Real admission requires the installed APCD entry point')
            if not job['external_execution_id'] or not job['case_id'] or not job['physical_contract_sha256']:
                raise ValueError('Real admission requires execution identity, case and physical contract hash')
            requirements = json.loads(job['resource_requirements'] or '{}')
            evidence = shared_resource_gate.check(requirements, self.output_dir, policy)
            folder = self.output_dir / ('batch_' + str(job['batch_id'])) / ('job_' + str(job['id']))
            folder.mkdir(parents=True, exist_ok=True)
            (folder/'resource_snapshot.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
            if evidence['hold_reasons']:
                raise ValueError('; '.join(evidence['hold_reasons']))
            return policy
        except Exception as exc:
            raise ResourceGateError('Resource gate HOLD: ' + str(exc)) from exc

    def submit_batch(self, manifest_path):
        try:
            manifest_path = Path(manifest_path).resolve()
            manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
            name = manifest['batch_name']
            if not isinstance(name, str) or not name.strip():
                raise ValueError('batch_name must be nonempty text')
            items = manifest['jobs']
            if not isinstance(items, list) or not items:
                raise ValueError('jobs must be a nonempty list')
            rows = []
            for item in items:
                source = Path(item['input_fsp'])
                source = (manifest_path.parent / source).resolve() if not source.is_absolute() else source.resolve()
                if not source.is_file() or source.suffix.lower() != '.fsp':
                    raise ValueError('input_fsp must be an existing .fsp file')
                actual_sha = sha256(source)
                declared = item.get('source_fsp_sha256', item.get('sha256'))
                if declared is not None and (not isinstance(declared, str) or not SHA.fullmatch(declared) or declared.lower() != actual_sha):
                    raise ValueError('source FSP SHA256 mismatch or malformed hash')
                if 'sha256' in item and 'source_fsp_sha256' in item and item['sha256'].lower() != item['source_fsp_sha256'].lower():
                    raise ValueError('Conflicting source hash aliases')
                execution = item.get('external_execution_id', item.get('external_job_id', item.get('job_id')))
                external_job = item.get('external_job_id', item.get('job_id', execution))
                for label, value in [('external_execution_id', execution), ('external_job_id', external_job)]:
                    if value is not None and (not isinstance(value, str) or not IDENTITY.fullmatch(value)):
                        raise ValueError(label + ' must be generic ASCII text of 1..200 characters')
                attempt = item.get('attempt_id', 'attempt_001')
                if not isinstance(attempt, str) or not IDENTITY.fullmatch(attempt):
                    raise ValueError('Invalid attempt_id')
                contract = item.get('physical_contract_sha256')
                if contract is not None and (not isinstance(contract, str) or not SHA.fullmatch(contract)):
                    raise ValueError('Malformed physical_contract_sha256')
                requirements = item.get('resource_requirements')
                if requirements is not None and not isinstance(requirements, dict):
                    raise ValueError('resource_requirements must be an object')
                rows.append((str(source), actual_sha, execution, external_job, attempt, item.get('case_id'), contract, json.dumps(requirements), json.dumps(manifest)))
            with self._connect() as con:
                con.execute('BEGIN IMMEDIATE')
                batch_id = con.execute('INSERT INTO batches(name,description) VALUES(?,?)', (name, manifest.get('description', ''))).lastrowid
                for row in rows:
                    con.execute('INSERT INTO jobs(batch_id,input_fsp_path,input_fsp_sha256,external_execution_id,external_job_id,attempt_id,case_id,physical_contract_sha256,resource_requirements,manifest_json) VALUES(?,?,?,?,?,?,?,?,?,?)', (batch_id,) + row)
            return True, None
        except Exception as exc:
            return False, str(exc)

    def _record_solver_entry(self, job_id, attempt_id, fake_solver=False):
        if fake_solver and Path(self.db_path) == (DEFAULT_LOCK.parent/'data/runner_v31.db').resolve():
            raise ResourceGateError('Resource gate HOLD: Fake acceptance requires an isolated database')
        with self._connect() as con:
            con.execute('BEGIN IMMEDIATE')
            job = con.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if job is None or job['status'] != 'PENDING':
                raise NoReplayError('No Replay: job is missing or no longer PENDING')
            if con.execute('SELECT 1 FROM solver_entries WHERE job_id=? OR (external_execution_id IS NOT NULL AND external_execution_id=?)', (job_id, job['external_execution_id'])).fetchone():
                raise NoReplayError('No Replay: job/external execution already reserved')
            if attempt_id != job['attempt_id'] and job['attempt_id'] is not None:
                raise RuntimeError('Attempt identity differs from registered identity')
            if not fake_solver:
                self._require_live_exclusion(job)
            timestamp = now()
            con.execute('INSERT INTO solver_entries(job_id,attempt_id,entered_at,external_execution_id,solver_entered,pre_fsp_sha256,physical_contract_sha256,case_id,execution_mode) VALUES(?,?,?,?,?,?,?,?,?)', (job_id,attempt_id,timestamp,job['external_execution_id'],int(not fake_solver),job['input_fsp_sha256'],job['physical_contract_sha256'],job['case_id'],'FAKE' if fake_solver else 'REAL'))
            con.execute('UPDATE jobs SET status=\'RUNNING\',started_at=?,execution_mode=? WHERE id=?', (timestamp,'FAKE' if fake_solver else 'REAL',job_id))

    def _check_no_replay(self, job_id):
        with self._connect() as con:
            row = con.execute('SELECT 1 FROM solver_entries WHERE job_id=?', (job_id,)).fetchone()
        return (False, 'No Replay: existing attempt reservation') if row else (True, None)

    def run_job(self, job_id, input_fsp=None, output_fsp=None, fake_solver=False):
        self.last_hold = False
        with self._connect() as con:
            row = con.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None:
            return False, 'Job not found'
        job = dict(row)
        if job['status'] != 'PENDING':
            return False, 'No Replay: job is ' + job['status']
        folder = self.output_dir / ('batch_' + str(job['batch_id'])) / ('job_' + str(job_id))
        folder.mkdir(parents=True, exist_ok=True)
        final = Path(output_fsp).resolve() if output_fsp else folder / 'output.fsp'
        partial = final.with_name(final.stem + '.partial.fsp')
        staged = folder / 'input.fsp'
        logfile = folder / 'runner.log'
        acquired = False
        fdtd = None
        with logfile.open('a', encoding='utf-8') as evidence:
            def event(message):
                evidence.write(now() + ' ' + message + '\n'); evidence.flush(); os.fsync(evidence.fileno())
            try:
                event(json.dumps({'job_id':job_id,'external_execution_id':job['external_execution_id'],'attempt_id':job['attempt_id'],'mode':'FAKE' if fake_solver else 'REAL'}))
                with self._connect() as con:
                    con.execute('UPDATE jobs SET log_path=? WHERE id=?', (str(logfile),job_id))
                source = Path(job['input_fsp_path'])
                if input_fsp and Path(input_fsp).resolve() != source:
                    raise ValueError('Input path differs from registration')
                if sha256(source) != job['input_fsp_sha256']:
                    raise ValueError('Input SHA256 changed after submit')
                self._acquire_gpu_lock(); acquired = True
                (folder/'manifest.json').write_text(job['manifest_json'] or '{}',encoding='utf-8')
                shutil.copyfile(source, staged)
                if sha256(staged) != job['input_fsp_sha256']:
                    raise ValueError('Staged input SHA256 mismatch')
                final.parent.mkdir(parents=True, exist_ok=True)
                if final.exists() or partial.exists():
                    raise RuntimeError('Output already exists; preserve evidence and do not overwrite')
                self._record_solver_entry(job_id, job['attempt_id'] or 'attempt_001', fake_solver=fake_solver)
                event('Attempt reservation committed before backend call; solver_entered=' + str(not fake_solver))
                if fake_solver:
                    shutil.copyfile(staged, partial)
                else:
                    policy = json.loads(POLICY_PATH.read_text(encoding='utf-8'))
                    sys.path.insert(0, policy['lumapi_path'])
                    import lumapi
                    fdtd = lumapi.FDTD()
                    fdtd.load(str(staged))
                    fdtd.run('FDTD', 'GPU')
                    fdtd.save(str(partial))
                    fdtd.close(); fdtd = None
                if not partial.is_file() or partial.stat().st_size == 0:
                    raise RuntimeError('Native output missing or empty')
                output_hash = sha256(partial)
                os.replace(str(partial), str(final))
                with self._connect() as con:
                    con.execute('UPDATE jobs SET status=\'COMPLETED\',completed_at=?,output_fsp_path=?,output_sha256=?,error_message=NULL WHERE id=?', (now(),str(final),output_hash,job_id))
                event('COMPLETED output=' + str(final) + ' sha256=' + output_hash)
                return True, None
            except NoReplayError as exc:
                event(str(exc))
                return False, str(exc)
            except ResourceGateError as exc:
                self.last_hold = True
                event(str(exc))
                with self._connect() as con:
                    con.execute('UPDATE jobs SET error_message=? WHERE id=?', (str(exc),job_id))
                return False, str(exc)
            except Exception as exc:
                event('FAILED ' + repr(exc))
                with self._connect() as con:
                    con.execute('UPDATE jobs SET status=\'FAILED\',completed_at=?,error_message=?,output_fsp_path=? WHERE id=?', (now(),str(exc),str(partial) if partial.exists() else None,job_id))
                return False, str(exc)
            finally:
                if fdtd is not None:
                    try:
                        fdtd.close()
                    except Exception as exc:
                        event('CLOSE_ERROR ' + repr(exc))
                if acquired:
                    try:
                        self._release_gpu_lock()
                    except Exception as exc:
                        event('LOCK_RELEASE_ERROR ' + repr(exc))

    def run_batch(self, batch_name, fake_solver=False):
        self.last_hold = False
        with self._connect() as con:
            batch = con.execute('SELECT id FROM batches WHERE name=?', (batch_name,)).fetchone()
            if batch is None:
                return 0, 1
            jobs = con.execute('SELECT id FROM jobs WHERE batch_id=? AND status=\'PENDING\' ORDER BY id', (batch['id'],)).fetchall()
        completed = failed = 0
        for job in jobs:
            ok, message = self.run_job(job['id'], fake_solver=fake_solver)
            if self.last_hold:
                break
            completed += int(ok); failed += int(not ok)
        return completed, failed

    def status_batch(self, batch_name):
        with self._connect() as con:
            batch = con.execute('SELECT * FROM batches WHERE name=?', (batch_name,)).fetchone()
            if batch is None:
                return {}
            jobs = [dict(r) for r in con.execute('SELECT * FROM jobs WHERE batch_id=? ORDER BY id', (batch['id'],))]
            for job in jobs:
                job['internal_job_id'] = job['id']
                entry = con.execute('SELECT * FROM solver_entries WHERE job_id=?', (job['id'],)).fetchone()
                job['attempt'] = dict(entry) if entry else None
        result = {'batch_id':batch['id'],'batch_name':batch_name,'total':len(jobs),'jobs':jobs}
        for key in ['COMPLETED','PENDING','RUNNING','FAILED']:
            result[key.lower()] = sum(j['status'] == key for j in jobs)
        result['recovery_rule'] = 'Any existing attempt reservation forbids automatic replay, including stale RUNNING and FAKE attempts.'
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='APCD GPU Runner ' + VERSION)
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('command',choices=['submit','run','status'])
    parser.add_argument('batch_name')
    parser.add_argument('--manifest')
    parser.add_argument('--fake-solver',action='store_true')
    parser.add_argument('--db')
    parser.add_argument('--output-dir')
    args = parser.parse_args(argv)
    runner = MinimalBatchRunner(args.db, args.output_dir)
    if args.command == 'submit':
        if not args.manifest:
            print('--manifest required',file=sys.stderr); return 1
        try:
            data = json.loads(Path(args.manifest).read_text(encoding='utf-8-sig'))
            if data.get('batch_name') != args.batch_name:
                raise ValueError('CLI batch name differs from Manifest')
        except Exception as exc:
            print(str(exc),file=sys.stderr); return 1
        ok, message = runner.submit_batch(args.manifest)
        print('Submitted' if ok else 'Submit failed: ' + str(message))
        return 0 if ok else 1
    if args.command == 'run':
        completed, failed = runner.run_batch(args.batch_name,args.fake_solver)
        print(json.dumps({'completed':completed,'failed':failed,'hold':runner.last_hold}))
        status = runner.status_batch(args.batch_name)
        if runner.last_hold or status.get('running', 0):
            return 2
        return 1 if failed or status.get('failed', 0) or not status else 0
    status = runner.status_batch(args.batch_name)
    print(json.dumps(status,indent=2))
    return 0 if status else 1


if __name__ == '__main__':
    sys.exit(main())
