from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from shared_fdtd.control_v3.allocator import Allocator, Lease, OwnershipMismatch, ControlPlaneDeferred
from shared_fdtd.control_v3.db import ControlDB, utc_now
from shared_fdtd.engine.attempt_state import read_durable_attempt_state, RUNTIME_PATCH_VERSION
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.persistence import atomic_json, sha256_file

TERMINAL_LOG_RE = re.compile(
    r"(simulation\s+(?:finished|complete|completed)|"
    r"autoshutoff|simulation time reached|solver returned|"
    r"iterations?\s*[:=]\s*\d+)",
    re.IGNORECASE,
)


class FinisherHardGate(RuntimeError):
    pass


class DurablePostSolverFinisher:
    """Owner-scoped, restartable, zero-solver completion path.

    The finisher only consumes durable state and evidence. It never calls
    FDTD.run(), never creates a new scientific attempt, and never replays.
    """

    def __init__(
        self,
        *,
        db: ControlDB,
        attempt_root: str | Path,
        invoking_branch: str,
        adapter: Any,
        process_probe: Callable[[Mapping[str, Any]], list[Mapping[str, Any]]] | None = None,
        stability_observations: int = 2,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.db = db
        self.root = Path(attempt_root)
        self.invoking_branch = invoking_branch
        self.adapter = adapter
        self.process_probe = process_probe or (lambda state: [])
        self.stability_observations = max(1, int(stability_observations))
        self.sleep_fn = sleep_fn

    @property
    def state_path(self) -> Path:
        return self.root / "attempt_state.json"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    def _read_state(self) -> dict[str, Any]:
        return read_durable_attempt_state(self.state_path)

    def _append_once(self, event_type: str, **payload: Any) -> None:
        if any(row.get("event_type") == event_type for row in read_events(self.events_path)):
            return
        append_event(self.events_path, event_type, **payload)

    def _owned_lease(self, state: Mapping[str, Any]) -> Lease | None:
        with self.db.connect(readonly=True) as con:
            row = con.execute("SELECT * FROM slots WHERE slot_id=?", (state["slot_id"],)).fetchone()
        if row is None:
            raise OwnershipMismatch("missing slot: " + str(state["slot_id"]))
        if row["state"] == "FREE":
            return None
        expected = (
            row["owner_branch"] == state["owner_branch"] == self.invoking_branch
            and row["logical_case_id"] == state["logical_case_id"]
            and row["attempt_id"] == state["attempt_id"]
            and row["lease_token"] is not None
            and __import__("hashlib").sha256(row["lease_token"].encode()).hexdigest() == state["lease_token_hash"]
            and int(row["fencing_generation"]) == int(state["fencing_generation"])
        )
        if not expected:
            raise OwnershipMismatch(
                f"ownership mismatch branch={self.invoking_branch} slot={state['slot_id']} "
                f"case={state['logical_case_id']} attempt={state['attempt_id']}"
            )
        return Lease(
            row["slot_id"], row["owner_branch"], row["logical_case_id"],
            row["attempt_id"], row["lease_token"], int(row["fencing_generation"]),
        )

    def _advance_queue(self, state: Mapping[str, Any], new_state: str) -> None:
        with self.db.immediate() as con:
            row = con.execute(
                "SELECT state FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                (state["owner_branch"], state["logical_case_id"], state["attempt_id"]),
            ).fetchone()
            if row is None or row["state"] == new_state:
                return
            con.execute(
                "UPDATE branch_queue SET state=?,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                (new_state, utc_now(), state["owner_branch"], state["logical_case_id"], state["attempt_id"]),
            )
        self._append_once("QUEUE_STATE_ADVANCED", state=new_state)

    def _mark_stale_control_plane(self, state: Mapping[str, Any]) -> None:
        with self.db.connect(readonly=True) as con:
            row = con.execute(
                "SELECT state FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                (state["owner_branch"], state["logical_case_id"], state["attempt_id"]),
            ).fetchone()
        if row and row["state"] == "SCIENTIFIC_SOLVER_RUNNING":
            self._advance_queue(state, "STALE_CONTROL_PLANE_STATE")
            self._append_once("STALE_CONTROL_PLANE_STATE", prior_state="SCIENTIFIC_SOLVER_RUNNING")

    def _matching_processes(self, state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        expected = state.get("expected_process_identity") or {}
        expected_pids = {int(x) for x in expected.get("solver_pids", []) if str(x).isdigit()}
        rows = []
        for row in self.process_probe(state) or []:
            try:
                pid = int(row.get("ProcessId", row.get("pid")))
            except (TypeError, ValueError):
                continue
            if pid not in expected_pids:
                continue
            expected_start = str(expected.get("solver_creation_time_utc", ""))
            observed_start = str(row.get("CreationDate", row.get("creation_time_utc", "")))
            if expected_start and observed_start and expected_start not in observed_start and observed_start not in expected_start:
                continue
            cmd = str(row.get("CommandLine", row.get("command_line", "")) or "").lower()
            if state["logical_case_id"].lower() not in cmd and state["attempt_id"].lower() not in cmd:
                continue
            rows.append(row)
        return rows

    def _fsp_signature(self, path: Path) -> dict[str, Any] | None:
        if not path.is_file() or path.stat().st_size <= 0:
            return None
        st = path.stat()
        return {"path": str(path), "size_bytes": st.st_size, "mtime_ns": st.st_mtime_ns, "sha256": sha256_file(path)}

    def _stable_fsp(self, path: Path) -> tuple[bool, dict[str, Any] | None]:
        sig = self._fsp_signature(path)
        if sig is None:
            return False, None
        marker = self.root / ".finisher_fsp_observation.json"
        previous = {}
        if marker.is_file():
            try:
                previous = json.loads(marker.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        atomic_json(marker, sig)
        return bool(previous == sig), sig

    def _log_terminal(self, state: Mapping[str, Any]) -> bool:
        paths = [Path(x) for x in state.get("logs", [])]
        for path in paths:
            if path.is_file():
                try:
                    if TERMINAL_LOG_RE.search(path.read_text(errors="replace")):
                        return True
                except OSError:
                    pass
        return False

    def _evidence(self, state: Mapping[str, Any]) -> dict[str, Any]:
        events = read_events(self.events_path)
        runtime_fsp = Path(state.get("runtime_fsp") or "")
        explicit_return = any(row.get("event_type") == "SOLVER_RETURNED" for row in events)
        expected = state.get("expected_process_identity") or {}
        expected_pids = {int(x) for x in expected.get("solver_pids", []) if str(x).isdigit()}
        if not explicit_return and not expected_pids:
            return {
                "classification": "SCIENTIFIC_OUTCOME_UNRESOLVED",
                "exact_live_writer_count": None,
                "explicit_solver_return_event": False,
                "terminal_log_evidence": False,
                "runtime_fsp_stable": False,
                "runtime_fsp_signature": None,
                "process_identity_guard": "EXACT_SOLVER_LINEAGE_REQUIRED",
            }
        try:
            stable, signature = self._stable_fsp(runtime_fsp)
        except (OSError, IOError, PermissionError) as exc:
            return {
                "classification": "SCIENTIFIC_OUTCOME_UNRESOLVED",
                "exact_live_writer_count": None,
                "explicit_solver_return_event": any(row.get("event_type") == "SOLVER_RETURNED" for row in events),
                "terminal_log_evidence": False,
                "runtime_fsp_stable": False,
                "runtime_fsp_signature": None,
                "retryable_evidence_error": repr(exc),
            }
        try:
            live = self._matching_processes(state)
        except Exception as exc:
            return {
                "classification": "SCIENTIFIC_OUTCOME_UNRESOLVED",
                "exact_live_writer_count": None,
                "explicit_solver_return_event": any(row.get("event_type") == "SOLVER_RETURNED" for row in events),
                "terminal_log_evidence": False,
                "runtime_fsp_stable": stable,
                "runtime_fsp_signature": signature,
                "retryable_process_probe_error": repr(exc),
            }
        log_return = self._log_terminal(state)
        safe = stable and not live and (explicit_return or log_return)
        if safe:
            classification = "SOLVER_RETURNED_PROVEN" if explicit_return else "SOLVER_RETURNED_HIGH_CONFIDENCE"
        elif live:
            classification = "SOLVER_STILL_RUNNING"
        else:
            classification = "SCIENTIFIC_OUTCOME_UNRESOLVED"
        return {
            "classification": classification,
            "exact_live_writer_count": len(live),
            "explicit_solver_return_event": explicit_return,
            "terminal_log_evidence": log_return,
            "runtime_fsp_stable": stable,
            "runtime_fsp_signature": signature,
        }

    def _copy_native(self, source: Path, destination: Path) -> dict[str, Any]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_file() and destination.stat().st_size > 0:
            return {"status": "ALREADY_DURABLE", "path": str(destination), "sha256": sha256_file(destination)}
        tmp = destination.with_name(destination.name + ".finisher.tmp")
        shutil.copyfile(source, tmp)
        tmp.replace(destination)
        return {"status": "DURABLE", "path": str(destination), "sha256": sha256_file(destination)}

    def _release(self, state: Mapping[str, Any], lease: Lease | None) -> dict[str, Any]:
        if lease is None:
            self._append_once("RELEASE_ALREADY_COMPLETE")
            return {"status": "ALREADY_FREE", "duplicate_side_effects": 0}
        allocator = Allocator(self.db)
        try:
            allocator.release_pending(lease, "FINISHER_TRUTH_BEFORE_RELEASE")
        except Exception as exc:
            self._append_once("RELEASE_PENDING", retry_state="PENDING_RECONCILE", error=repr(exc))
            return {"status": "PENDING_RECONCILE", "error": repr(exc), "duplicate_side_effects": 0}
        try:
            result = allocator.release_owned_idempotent(lease, scientific_terminal="SCIENTIFIC_VALID")
        except Exception as exc:
            self._append_once("RELEASE_PENDING", retry_state="PENDING_RECONCILE", error=repr(exc))
            return {"status": "PENDING_RECONCILE", "error": repr(exc), "duplicate_side_effects": 0}
        try:
            self._advance_queue(state, "RELEASED")
        except Exception as exc:
            self._append_once("RELEASE_RECONCILE_PENDING", error=repr(exc))
            result = {**result, "queue_state": "PENDING_RECONCILE", "queue_error": repr(exc)}
        self._append_once("RELEASED", release_status=result["status"])
        return result

    def run_once(self) -> dict[str, Any]:
        state = self._read_state()
        if state.get("owner_branch") != self.invoking_branch:
            return {"status": "OWNERSHIP_MISMATCH", "mutation_count": 0, "replay": 0}
        try:
            lease = self._owned_lease(state)
        except OwnershipMismatch as exc:
            return {"status": "OWNERSHIP_MISMATCH", "mutation_count": 0, "replay": 0, "error": repr(exc)}

        if state.get("provenance_ambiguous") or not state.get("scientific_contract_hash"):
            return {"status": "PROVENANCE_AMBIGUOUS", "mutation_count": 0, "replay": 0}

        terminal_path = self.root / "terminal.json"
        if terminal_path.is_file():
            terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
            if terminal.get("status") == "HF_TRUTH_VALID":
                release = self._release(state, lease) if terminal.get("release_state") != "RELEASED" else {"status": "ALREADY_COMPLETE", "duplicate_side_effects": 0}
                if release.get("status") in {"RELEASED", "ALREADY_FREE"}:
                    terminal["release_state"] = "RELEASED"
                    atomic_json(terminal_path, terminal)
                return {"status": "ALREADY_TRUTH_DURABLE", "release": release, "replay": 0}

        evidence = self._evidence(state)
        if evidence["classification"] == "SOLVER_STILL_RUNNING":
            return {"status": "SOLVER_STILL_RUNNING", "evidence": evidence, "replay": 0}
        if evidence["classification"] == "SCIENTIFIC_OUTCOME_UNRESOLVED":
            return {"status": "SCIENTIFIC_OUTCOME_UNRESOLVED", "evidence": evidence, "replay": 0}

        self._mark_stale_control_plane(state)
        runtime_fsp = Path(state["runtime_fsp"])
        native_target = Path(state["native_target"])
        post_target = Path(state["post_target"])
        raw_target = Path(state["raw_target"])
        self._advance_queue(state, "SOLVER_RETURNED")
        self._append_once("SOLVER_RETURNED", evidence=evidence)

        native = self._copy_native(runtime_fsp, native_target)
        self._append_once("NATIVE_TRUTH_DURABLE", artifact=native)
        try:
            fresh = self.adapter.fresh_load_validate(native_target, state)
        except Exception as exc:
            self._append_once("FRESH_LOAD_DEFERRED", error=repr(exc), retry_state="PENDING_RECONCILE")
            return {"status": "FRESH_LOAD_DEFERRED", "error": repr(exc), "replay": 0}
        if not fresh.get("passed", False):
            return {"status": "FRESH_LOAD_FAILED", "fresh_load": fresh, "replay": 0}
        self._append_once("POST_FSP_VALID", fresh_load=fresh)

        try:
            post = self.adapter.postprocess(self.root, native_target, post_target, raw_target, state)
            self._append_once("RAW_VALID", postprocess=post)
            truth = self.adapter.validate_truth(self.root, state)
        except Exception as exc:
            self._append_once("POSTSOLVER_FINISH_DEFERRED", error=repr(exc), retry_state="PENDING_RECONCILE")
            return {"status": "POSTSOLVER_FINISH_DEFERRED", "error": repr(exc), "replay": 0}
        if not truth.get("passed", False):
            return {"status": "SCIENTIFIC_VALIDATION_FAILED", "truth": truth, "replay": 0}

        self._advance_queue(state, "SCIENTIFIC_VALID")
        self._append_once("SCIENTIFIC_VALID", truth=truth)
        self._append_once("HF_ARCHIVED", adapter=state.get("adapter_identity"))
        terminal = {
            "state": "COMPLETED",
            "status": "HF_TRUTH_VALID",
            "case_id": state["logical_case_id"],
            "attempt_id": state["attempt_id"],
            "solver_entered": True,
            "solver_runs": int(state.get("scientific_invocation_count", 1)),
            "replay": 0,
            "runtime_fsp": str(runtime_fsp),
            "runtime_fsp_sha256": sha256_file(runtime_fsp),
            "native_target": str(native_target),
            "native_sha256": sha256_file(native_target),
            "post_fsp": str(post_target),
            "raw_result": str(raw_target),
            "fresh_load": fresh,
            "postprocess": post,
            "truth": truth,
            "release_state": "PENDING_RECONCILE",
            "completed_timestamp_utc": utc_now(),
            "runtime_patch_version": RUNTIME_PATCH_VERSION,
        }
        atomic_json(terminal_path, terminal)
        release = self._release(state, lease)
        terminal["release_state"] = "RELEASED" if release["status"] in {"RELEASED", "ALREADY_FREE"} else "PENDING_RECONCILE"
        terminal["release"] = release
        atomic_json(terminal_path, terminal)
        return {"status": "HF_TRUTH_VALID", "terminal": terminal, "release": release, "replay": 0}
