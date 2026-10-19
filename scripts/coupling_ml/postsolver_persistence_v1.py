"""Small, durable post-solver lifecycle gate for Coupling-ML FDTD workers."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class LifecycleState(str, Enum):
    APP_OPEN_REQUESTED = "APP_OPEN_REQUESTED"
    APP_OPEN_CONNECTED = "APP_OPEN_CONNECTED"
    MANIFEST_FINALIZED = "MANIFEST_FINALIZED"
    RUN_CALLED = "RUN_CALLED"
    SCIENTIFIC_SOLVER_ENTERED = "SCIENTIFIC_SOLVER_ENTERED"
    SOLVER_RETURNED = "SOLVER_RETURNED"
    POST_FSP_SAVE_REQUESTED = "POST_FSP_SAVE_REQUESTED"
    POST_FSP_FILE_OPENED = "POST_FSP_FILE_OPENED"
    SAVE_PROGRESS = "SAVE_PROGRESS"
    POST_FSP_SAVE_COMPLETED = "POST_FSP_SAVE_COMPLETED"
    POST_FSP_SHA_VERIFIED = "POST_FSP_SHA_VERIFIED"
    POST_FSP_LOAD_ONLY_VALIDATED = "POST_FSP_LOAD_ONLY_VALIDATED"
    RAW_EXTRACTION_COMPLETED = "RAW_EXTRACTION_COMPLETED"
    RAW_SHA_VERIFIED = "RAW_SHA_VERIFIED"
    DERIVED_PROCESSING_COMPLETED = "DERIVED_PROCESSING_COMPLETED"
    AUDIT_COMPLETED = "AUDIT_COMPLETED"
    COMPLETED = "COMPLETED"
    SLOT_RELEASED = "SLOT_RELEASED"
    FAILED_AFTER_ENTRY = "FAILED_AFTER_ENTRY"
    FAILED_BEFORE_ENTRY = "FAILED_BEFORE_ENTRY"


FAILURE_CLASSES = {
    "SCIENTIFIC_SOLVER_FAILURE", "APP_SESSION_FAILURE", "PERSISTENCE_FAILURE",
    "POST_SAVE_VALIDATION_FAILURE", "RAW_EXTRACTION_FAILURE", "PARSER_FAILURE",
    "PROJECTION_FAILURE", "AUDIT_FAILURE", "CONTROLLER_FAILURE",
}

_TRANSITIONS = {
    None: {LifecycleState.APP_OPEN_REQUESTED},
    LifecycleState.APP_OPEN_REQUESTED: {LifecycleState.APP_OPEN_CONNECTED, LifecycleState.FAILED_BEFORE_ENTRY},
    LifecycleState.APP_OPEN_CONNECTED: {LifecycleState.MANIFEST_FINALIZED, LifecycleState.FAILED_BEFORE_ENTRY},
    LifecycleState.MANIFEST_FINALIZED: {LifecycleState.RUN_CALLED, LifecycleState.FAILED_BEFORE_ENTRY},
    LifecycleState.RUN_CALLED: {LifecycleState.SCIENTIFIC_SOLVER_ENTERED, LifecycleState.FAILED_BEFORE_ENTRY},
    LifecycleState.SCIENTIFIC_SOLVER_ENTERED: {LifecycleState.SOLVER_RETURNED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.SOLVER_RETURNED: {LifecycleState.POST_FSP_SAVE_REQUESTED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.POST_FSP_SAVE_REQUESTED: {LifecycleState.POST_FSP_FILE_OPENED, LifecycleState.SAVE_PROGRESS, LifecycleState.POST_FSP_SAVE_COMPLETED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.POST_FSP_FILE_OPENED: {LifecycleState.SAVE_PROGRESS, LifecycleState.POST_FSP_SAVE_COMPLETED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.SAVE_PROGRESS: {LifecycleState.POST_FSP_SAVE_COMPLETED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.POST_FSP_SAVE_COMPLETED: {LifecycleState.POST_FSP_SHA_VERIFIED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.POST_FSP_SHA_VERIFIED: {LifecycleState.POST_FSP_LOAD_ONLY_VALIDATED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.POST_FSP_LOAD_ONLY_VALIDATED: {LifecycleState.RAW_EXTRACTION_COMPLETED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.RAW_EXTRACTION_COMPLETED: {LifecycleState.RAW_SHA_VERIFIED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.RAW_SHA_VERIFIED: {LifecycleState.DERIVED_PROCESSING_COMPLETED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.DERIVED_PROCESSING_COMPLETED: {LifecycleState.AUDIT_COMPLETED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.AUDIT_COMPLETED: {LifecycleState.COMPLETED, LifecycleState.FAILED_AFTER_ENTRY},
    LifecycleState.COMPLETED: {LifecycleState.SLOT_RELEASED},
    LifecycleState.FAILED_AFTER_ENTRY: {LifecycleState.SLOT_RELEASED},
    LifecycleState.FAILED_BEFORE_ENTRY: {LifecycleState.SLOT_RELEASED},
}


class LifecycleError(RuntimeError):
    pass


class PreservationRequired(LifecycleError):
    """Caller must retain this controller, keep its process alive, and retain its slot."""
    pass


_PRESERVED_OWNERS = []


class SaveTimeout(TimeoutError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_default(value):
    # Keep durable lifecycle artifacts serializable for NumPy scalar values from adapters.
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=_json_default)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def durable_event(path, *, job_id, attempt_id, state, worker_pid=None, controller_pid=None,
                  session_id=None, artifact_path=None, artifact_sha256=None,
                  error_class=None, error=None, recovery_action=None, extra=None):
    record = {"timestamp": utc_now(), "job_id": job_id, "attempt_id": attempt_id,
              "worker_pid": worker_pid or os.getpid(), "controller_pid": controller_pid or os.getppid(),
              "session_id": session_id, "state": state, "artifact_path": str(artifact_path) if artifact_path else None,
              "artifact_sha256": artifact_sha256, "error_class": error_class,
              "error": error, "recovery_action": recovery_action}
    if extra:
        record.update(extra)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


class ArtifactRoles:
    """Keep frozen pre, mutable runtime, canonical post and rescue post separate."""

    def __init__(self, frozen_pre, runtime_fsp, canonical_post, recovery_post):
        self.frozen_pre = Path(frozen_pre)
        self.runtime_fsp = Path(runtime_fsp)
        self.canonical_post = Path(canonical_post)
        self.recovery_post = Path(recovery_post)

    def distinct(self):
        paths = [self.frozen_pre, self.runtime_fsp, self.canonical_post, self.recovery_post]
        return len({str(p.resolve()) for p in paths}) == 4

    def prepare(self, source_pre):
        if not self.distinct():
            raise LifecycleError("artifact roles are not distinct")
        source_pre = Path(source_pre)
        if not source_pre.is_file() or source_pre.stat().st_size == 0:
            raise LifecycleError("setup pre-FSP is missing")
        self.frozen_pre.parent.mkdir(parents=True, exist_ok=True)
        if any(p.exists() for p in [self.frozen_pre,self.runtime_fsp,self.canonical_post,self.recovery_post]):
            raise LifecycleError("materialized artifact role: replay/overwrite forbidden")
        if source_pre.resolve() in [p.resolve() for p in [self.frozen_pre,self.runtime_fsp,self.canonical_post,self.recovery_post]]:
            raise LifecycleError("setup and execution artifact roles must be distinct")
        with source_pre.open('rb') as source, self.frozen_pre.open('xb') as target:
            shutil.copyfileobj(source,target)
            target.flush();os.fsync(target.fileno())
        self.frozen_pre.chmod(stat.S_IREAD)
        shutil.copyfile(self.frozen_pre, self.runtime_fsp)
        self.runtime_fsp.chmod(stat.S_IREAD | stat.S_IWRITE)
        return {"frozen_pre_sha256": sha256_file(self.frozen_pre), "runtime_fsp_sha256": sha256_file(self.runtime_fsp)}

    def event_order(self, event_path):
        rows = [json.loads(line) for line in Path(event_path).read_text(encoding="utf-8").splitlines() if line.strip()]
        return [row["state"] for row in rows]


class LifecycleController:
    def __init__(self, *, job_id, attempt_id, roles, events_path, completion_path,
                 raw_path, release_slot, on_solver_entered=None, save_timeout_s=30):
        self.job_id, self.attempt_id = job_id, attempt_id
        self.roles, self.events_path = roles, Path(events_path)
        self.completion_path, self.raw_path = Path(completion_path), Path(raw_path)
        self.release_slot = release_slot
        self.on_solver_entered = on_solver_entered or (lambda: None)
        self.save_timeout_s = save_timeout_s
        self.state = None
        self.handle = None
        self.session_id = None
        self.persisted_artifact = None
        self.persisted_sha256 = None
        self.run_invocation_count = 0
        self.solver_entered = False
        self.solver_returned = False
        self.validated = False
        self.phase = 'APP_SESSION_FAILURE'
        self.released = False
        self.slot_release_pending = False
        self.owner_thread = threading.get_ident()
        if self.events_path.exists() or self.completion_path.exists():
            raise LifecycleError('existing durable state: no execution replay')

    def transition(self, state, **kwargs):
        state = LifecycleState(state)
        if state not in _TRANSITIONS.get(self.state, set()):
            raise LifecycleError(f"illegal transition {self.state} -> {state}")
        durable_event(self.events_path, job_id=self.job_id, attempt_id=self.attempt_id,
                      state=state.value, session_id=self.session_id,
                      artifact_path=kwargs.get("artifact_path"), artifact_sha256=kwargs.get("artifact_sha256"),
                      error_class=kwargs.get("error_class"), error=kwargs.get("error"),
                      recovery_action=kwargs.get("recovery_action"))
        self.state = state

    def _save_with_timeout(self, save):
        if threading.get_ident() != self.owner_thread:
            raise LifecycleError('session call from non-owner thread')
        # A watchdog may observe the filesystem, but must never call or close lumapi.
        expired = threading.Event()
        def report_timeout():
            expired.set()
            durable_event(self.events_path, job_id=self.job_id,attempt_id=self.attempt_id,
                          state='SAVE_TIMEOUT_RECOVERY_REQUIRED',session_id=self.session_id,
                          error_class='PERSISTENCE_FAILURE',recovery_action='retain live owner and slot; no concurrent API calls')
        watchdog = threading.Timer(self.save_timeout_s, report_timeout)
        watchdog.daemon = True
        watchdog.start()
        try:
            return save()
        finally:
            watchdog.cancel();watchdog.join()
            if expired.is_set():
                durable_event(self.events_path,job_id=self.job_id,attempt_id=self.attempt_id,
                              state='TIMED_OUT_SAVE_CALL_RETURNED',session_id=self.session_id)

    def _save_artifact(self, adapter, handle, path, *, recovery=False):
        if Path(path).exists():
            raise LifecycleError('post target already exists; overwrite forbidden')
        self._save_with_timeout(lambda: adapter.save(handle, str(path)))
        if not Path(path).is_file() or Path(path).stat().st_size == 0:
            raise LifecycleError("post-FSP save returned without a durable file")
        self.transition(LifecycleState.POST_FSP_SAVE_COMPLETED, artifact_path=path)
        digest = sha256_file(path)
        self.transition(LifecycleState.POST_FSP_SHA_VERIFIED, artifact_path=path, artifact_sha256=digest)
        self.persisted_artifact, self.persisted_sha256 = Path(path), digest

    def persist_post(self, adapter):
        self.transition(LifecycleState.POST_FSP_SAVE_REQUESTED, artifact_path=self.roles.canonical_post)
        try:
            self._save_artifact(adapter, self.handle, self.roles.canonical_post)
        except BaseException as first_error:
            durable_event(self.events_path, job_id=self.job_id, attempt_id=self.attempt_id,
                          state="PERSISTENCE_FAILURE", session_id=self.session_id,
                          artifact_path=self.roles.canonical_post, error_class="PERSISTENCE_FAILURE",
                          error=repr(first_error), recovery_action="inspect_live_session_and_rescue")
            rescue = getattr(adapter, "rescue_save", None)
            if rescue is None or not adapter.live_results_available(self.handle):
                raise LifecycleError(f"canonical post save failed and live rescue unavailable: {first_error}") from first_error
            durable_event(self.events_path, job_id=self.job_id, attempt_id=self.attempt_id,
                          state="RECOVERY_POST_FSP_SAVE_REQUESTED", session_id=self.session_id,
                          artifact_path=self.roles.recovery_post, recovery_action="resave_live_result")
            class RescueAdapter:
                def save(_, handle, path):
                    return rescue(handle, path)
            self._save_artifact(RescueAdapter(), self.handle, self.roles.recovery_post, recovery=True)

    def execute(self, adapter, manifest, extract_raw, derive, audit):
        try:
            self.transition(LifecycleState.APP_OPEN_REQUESTED)
            hashes=self.roles.prepare(manifest["setup_pre_fsp"])
            self.handle = adapter.open(str(self.roles.runtime_fsp))
            self.session_id = getattr(adapter, "session_id", None)
            self.transition(LifecycleState.APP_OPEN_CONNECTED)
            frozen_manifest=dict(manifest, **hashes)
            manifest_path=self.events_path.with_name(self.events_path.stem+'.manifest.json')
            atomic_json(manifest_path,frozen_manifest)
            self.transition(LifecycleState.MANIFEST_FINALIZED,artifact_path=manifest_path,artifact_sha256=sha256_file(manifest_path))
            durable_event(self.events_path, job_id=self.job_id, attempt_id=self.attempt_id,
                          state="FROZEN_PRE_AUTHORITY", session_id=self.session_id,
                          artifact_path=self.roles.frozen_pre,
                          artifact_sha256=sha256_file(self.roles.frozen_pre), extra={"manifest": manifest})
            self.transition(LifecycleState.RUN_CALLED)
            entered_path=self.events_path.with_name(self.events_path.stem+'.entered.json')
            physical_hash=manifest.get('physical_contract_sha256') or hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
            with entered_path.open('x',encoding='utf-8') as entered_file:
                json.dump(dict(job_id=self.job_id,attempt_id=self.attempt_id,solver_entered=True,timestamp=utc_now(),pre_fsp_sha256=hashes['frozen_pre_sha256'],physical_contract_sha256=physical_hash),entered_file)
                entered_file.flush();os.fsync(entered_file.fileno())
            self.run_invocation_count += 1
            self.solver_entered = True
            self.transition(LifecycleState.SCIENTIFIC_SOLVER_ENTERED)
            durable_event(self.events_path,job_id=self.job_id,attempt_id=self.attempt_id,
                          state='ENTERED_AUTHORITY',session_id=self.session_id,artifact_sha256=hashes['frozen_pre_sha256'],
                          extra={'solver_entered':True,'physical_contract_sha256':physical_hash})
            self.on_solver_entered()
            self.phase='SCIENTIFIC_SOLVER_FAILURE'
            adapter.run(self.handle)
            self.solver_returned = True
            self.transition(LifecycleState.SOLVER_RETURNED)
            self.phase='PERSISTENCE_FAILURE'
            self.persist_post(adapter)
            self.phase='POST_SAVE_VALIDATION_FAILURE'
            validation = dict(adapter.load_only(str(self.persisted_artifact), manifest))
            required=['ok','identity_pass','arrays_pass','shape_pass','sanity_pass']
            if not all(validation.get(key) is True for key in required) or validation.get("run_called") is not False or validation.get('session_id')==self.session_id:
                raise LifecycleError("independent LOAD-only validation failed")
            if sha256_file(self.persisted_artifact)!=self.persisted_sha256:
                raise LifecycleError('post SHA changed during independent load')
            atomic_json(self.events_path.with_name(self.events_path.stem+'.load_only.json'),validation)
            self.validated=True
            self.transition(LifecycleState.POST_FSP_LOAD_ONLY_VALIDATED, artifact_path=self.persisted_artifact,
                            artifact_sha256=self.persisted_sha256)
            durable_event(self.events_path,job_id=self.job_id,attempt_id=self.attempt_id,state='POST_FSP_VALIDATED',session_id=self.session_id,artifact_path=self.persisted_artifact,artifact_sha256=self.persisted_sha256)
            self.phase='RAW_EXTRACTION_FAILURE'
            extract_raw(self.handle, self.persisted_artifact, self.raw_path)
            if not self.raw_path.is_file() or self.raw_path.stat().st_size == 0:
                raise LifecycleError("raw artifact missing")
            raw_sha = sha256_file(self.raw_path)
            self.transition(LifecycleState.RAW_EXTRACTION_COMPLETED, artifact_path=self.raw_path)
            self.transition(LifecycleState.RAW_SHA_VERIFIED, artifact_path=self.raw_path, artifact_sha256=raw_sha)
            self.phase='PARSER_FAILURE'
            derived = dict(derive(self.raw_path))
            self.transition(LifecycleState.DERIVED_PROCESSING_COMPLETED)
            self.phase='AUDIT_FAILURE'
            audit_result = dict(audit(derived, self.persisted_artifact, self.raw_path))
            if audit_result.get("pass") is not True:
                raise LifecycleError("completion audit failed")
            if sha256_file(self.roles.frozen_pre)!=hashes['frozen_pre_sha256'] or sha256_file(self.persisted_artifact)!=self.persisted_sha256 or sha256_file(self.raw_path)!=raw_sha:
                raise LifecycleError('final immutable artifact SHA audit failed')
            self.transition(LifecycleState.AUDIT_COMPLETED)
            self.phase='CONTROLLER_FAILURE'
            adapter.close(self.handle)
            self.handle = None
            durable_event(self.events_path,job_id=self.job_id,attempt_id=self.attempt_id,state='APP_CLOSED',session_id=self.session_id)
            self.transition(LifecycleState.COMPLETED, artifact_path=self.persisted_artifact, artifact_sha256=self.persisted_sha256)
            result = {"status": "COMPLETED", "state": self.state.value, "job_id": self.job_id,
                      "attempt_id": self.attempt_id, "solver_entered": True, "solver_returned": True,
                      "run_invocation_count": self.run_invocation_count, "solver_rerun": False,
                      "post_fsp": str(self.persisted_artifact), "post_fsp_sha256": self.persisted_sha256,
                      "raw": str(self.raw_path), "raw_sha256": raw_sha, "load_only_validation": validation,
                      "derived": derived, "audit": audit_result, "completed_utc": utc_now()}
            atomic_json(self.completion_path, result)
            try:
                self.release_slot("COMPLETED")
            except BaseException as release_error:
                self.slot_release_pending = True
                result["slot_release_pending"] = True
                result["slot_release_state"] = "RECONCILE_REQUIRED"
                atomic_json(self.completion_path, result)
                durable_event(self.events_path, job_id=self.job_id, attempt_id=self.attempt_id,
                              state="SLOT_RELEASE_PENDING", error_class="CONTROLLER_FAILURE",
                              error=repr(release_error), recovery_action="retry canonical scheduler release or reconcile with durable completion evidence")
                raise
            self.released=True
            self.transition(LifecycleState.SLOT_RELEASED)
            result["state"] = self.state.value
            atomic_json(self.completion_path, result)
            return result
        except BaseException as exc:
            if self.state in {LifecycleState.COMPLETED,LifecycleState.SLOT_RELEASED}:
                durable_event(self.events_path,job_id=self.job_id,attempt_id=self.attempt_id,state='CONTROLLER_FAILURE',error_class='CONTROLLER_FAILURE',error=repr(exc),recovery_action='reconcile completion/slot; never rerun solver')
                raise
            entered = self.solver_entered
            error_class = getattr(exc,'error_class',self.phase)
            self.phase = error_class
            target = LifecycleState.FAILED_AFTER_ENTRY if entered else LifecycleState.FAILED_BEFORE_ENTRY
            durable_event(self.events_path,job_id=self.job_id,attempt_id=self.attempt_id,state=target.value,error_class=error_class,error=repr(exc))
            if entered and not self.validated:
                _PRESERVED_OWNERS.append(self)
                durable_event(self.events_path,job_id=self.job_id,attempt_id=self.attempt_id,state='PRESERVATION_REQUIRED',error_class=error_class,recovery_action='retain session and slot; worker must remain alive')
                raise PreservationRequired(str(exc)) from exc
            if self.handle is not None:
                try:
                    adapter.close(self.handle)
                except Exception:
                    pass
                self.handle = None
            self.release_slot(target.value)
            durable_event(self.events_path,job_id=self.job_id,attempt_id=self.attempt_id,state='FAILED_JOB_SLOT_RELEASED',error_class=error_class)
            result = {"status": target.value, "state": self.state.value, "job_id": self.job_id,
                      "attempt_id": self.attempt_id, "solver_entered": entered,
                      "solver_returned": self.solver_returned, "run_invocation_count": self.run_invocation_count,
                      "solver_rerun": False, "error_class": error_class, "error": repr(exc),
                      "post_fsp": str(self.persisted_artifact) if self.persisted_artifact else None,
                      "post_fsp_sha256": self.persisted_sha256}
            atomic_json(self.completion_path, result)
            raise


def zero_solver_recover(*, job_id, attempt_id, events_path, post_fsp, raw_path,
                        completion_path, adapter, manifest, extract_raw, derive, audit, expected_post_sha256,
                        original_solver_returned):
    if type(original_solver_returned) is not bool:
        raise LifecycleError('original solver return evidence must be explicit')
    post_fsp, raw_path = Path(post_fsp), Path(raw_path)
    if sha256_file(post_fsp)!=expected_post_sha256:
        raise LifecycleError('zero-solver recovery post SHA authority mismatch')
    if raw_path.exists() or Path(completion_path).exists():
        raise LifecycleError('recovery outputs exist: overwrite forbidden')
    durable_event(events_path, job_id=job_id, attempt_id=attempt_id, state="ZERO_SOLVER_RECOVERY_STARTED", artifact_path=post_fsp,
                  recovery_action="reuse_persisted_post_fsp")
    validation = dict(adapter.load_only(str(post_fsp), manifest))
    if not all(validation.get(k) is True for k in ['ok','identity_pass','arrays_pass','shape_pass','sanity_pass']) or validation.get("run_called") is not False:
        raise LifecycleError("zero-solver recovery LOAD-only validation failed")
    adapter.extract_raw_from_post(str(post_fsp), str(raw_path))
    if not raw_path.is_file() or raw_path.stat().st_size == 0:
        raise LifecycleError("zero-solver recovery raw artifact missing")
    raw_sha = sha256_file(raw_path)
    derived = dict(derive(raw_path))
    audit_result = dict(audit(derived, post_fsp, raw_path))
    if audit_result.get("pass") is not True:
        raise LifecycleError("zero-solver recovery audit failed")
    if sha256_file(post_fsp)!=expected_post_sha256:
        raise LifecycleError('post mutated during recovery')
    result = {"status": "COMPLETED", "state": "COMPLETED", "job_id": job_id, "attempt_id": attempt_id,
              "solver_entered": True, "solver_returned": original_solver_returned, "run_invocation_count": 0, "solver_rerun": False,
              "recovered_from_post_fsp": True, "post_fsp": str(post_fsp), "post_fsp_sha256": sha256_file(post_fsp),
              "raw": str(raw_path), "raw_sha256": raw_sha, "load_only_validation": validation,
              "derived": derived, "audit": audit_result, "completed_utc": utc_now()}
    atomic_json(completion_path, result)
    durable_event(events_path, job_id=job_id, attempt_id=attempt_id, state="COMPLETED", artifact_path=post_fsp,
                  artifact_sha256=result["post_fsp_sha256"], recovery_action="zero_solver_recovery")
    return result


def inspect_durable_state(events_path, worker_alive=False, engine_completed=False):
    """Crash/restart audit; a process exit is never evidence of persistence."""
    rows=[]
    try:
        for line in Path(events_path).read_text(encoding='utf-8').splitlines():
            rows.append(json.loads(line))
    except (ValueError,OSError):
        return {'complete':False,'classification':'CONTROLLER_FAILURE_INCOMPLETE_LEDGER'}
    states=[r['state'] for r in rows]
    valid='POST_FSP_VALIDATED' in states
    complete=valid and 'COMPLETED' in states and 'SLOT_RELEASED' in states
    if complete:classification='COMPLETED'
    elif valid:classification='ZERO_SOLVER_RECOVERY_AVAILABLE'
    elif 'SAVE_TIMEOUT_RECOVERY_REQUIRED' in states:classification='PERSISTENCE_FAILURE_SAVE_TIMEOUT'
    elif 'SCIENTIFIC_SOLVER_ENTERED' in states and not worker_alive:classification='FAILED_AFTER_ENTRY_WITHOUT_VALIDATED_PERSISTENCE'
    elif 'SOLVER_RETURNED' in states:classification='PERSISTENCE_PENDING'
    elif engine_completed and 'SCIENTIFIC_SOLVER_ENTERED' in states:classification='ENGINE_COMPLETED_NATIVE_RETURN_PENDING'
    else:classification='RUNNING' if worker_alive else 'FAILED_BEFORE_ENTRY'
    return dict(complete=complete,classification=classification,validated=valid,last_durable_state=states[-1] if states else None,
                solver_entered_count=states.count('SCIENTIFIC_SOLVER_ENTERED'))


def validated_completion(events_path,completion_path):
    snapshot=inspect_durable_state(events_path)
    if not snapshot['complete']:
        raise LifecycleError('controller cannot accept '+snapshot['classification'])
    result=json.loads(Path(completion_path).read_text(encoding='utf-8'))
    if result.get('status')!='COMPLETED' or result.get('load_only_validation',{}).get('ok') is not True:
        raise LifecycleError('completion gate metadata missing')
    for key in ['post_fsp','raw']:
        if sha256_file(result[key])!=result[key+'_sha256']:
            raise LifecycleError('controller detected '+key+' SHA mismatch')
    return result


def compatible_process_snapshot(slot_module):
    """Operational telemetry only. Missing private APIs never invalidate persisted truth."""
    try:
        provider=getattr(slot_module,'_ps_snapshot',None)
        if provider is not None:
            rows=provider()
            rows=[{k:r.get(k) for k in ['pid','ppid','name','path']} for r in rows]
            return {'quality':'AVAILABLE','provider':'scheduler','processes':rows}
        import psutil
        rows=[]
        for p in psutil.process_iter(['pid','ppid','name','exe']):
            if (p.info['name'] or '').lower() in ['fdtd-solutions.exe','fdtd-engine-msmpi.exe','fdtd-engine.exe']:
                rows.append(dict(pid=p.pid,ppid=p.info['ppid'],name=p.info['name'],path=p.info['exe']))
        return {'quality':'AVAILABLE_COMPATIBILITY_FALLBACK','provider':'psutil_read_only','processes':rows}
    except Exception as exc:
        return {'quality':'DEGRADED_TELEMETRY','provider':'unavailable','error':repr(exc),'processes':[]}
