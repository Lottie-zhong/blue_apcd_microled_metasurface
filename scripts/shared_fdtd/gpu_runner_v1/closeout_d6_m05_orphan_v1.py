from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import sqlite3
import subprocess
import urllib.parse
import uuid

try:
    import runner as _runner
except ImportError:
    from . import runner as _runner

CASE_ID = "K6LDA1_DEV_D6_M05"
ATTEMPT_ID = "attempt_001"
RUN_ID = "K6V2_D6M05_20261005T182728Z_92041df6"
SCHEMA = "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1"
PRODUCTION_ROOT = pathlib.Path(r"D:\apcd_runtime\gpu_production_runner_v1")
CONTROL_DB = pathlib.Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
COUPLING_LEDGER = pathlib.Path(
    r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\QUEUE_EXECUTION_LEDGER_V1.json"
)
CLOSEOUT_DIRNAME = "postentry_closeout_v1"


class CloseoutBlocked(RuntimeError):
    pass


class InjectedCloseoutCrash(RuntimeError):
    pass


def _now():
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _sha(path):
    return _sha_bytes(pathlib.Path(path).read_bytes())


def _read_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise CloseoutBlocked("JSON_READ_FAILED:" + str(path)) from exc


def _write_json(path, value):
    _runner.atomic_json(pathlib.Path(path), value)


def _create_exclusive_json(path, value):
    """Publish a complete new fence atomically without replacing another claimant."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    data = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        with open(tmp, "xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(str(tmp), str(path))
            return True
        except FileExistsError:
            return False
        except OSError as exc:
            raise CloseoutBlocked("ATOMIC_RECOVERY_FENCE_CREATE_UNAVAILABLE") from exc
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _run_dir(root):
    return pathlib.Path(root) / "runs" / CASE_ID / ATTEMPT_ID / RUN_ID


def _closeout_dir(root):
    return _run_dir(root) / CLOSEOUT_DIRNAME


def _paths(root):
    rd = _run_dir(root)
    return {
        "lock": pathlib.Path(root) / ".runner.lock",
        "active": pathlib.Path(root) / "active_run.json",
        "registry": pathlib.Path(root) / "registry.json",
        "status": rd / "status.json",
        "manifest": rd / "manifest.json",
    }


def _run_inventory(run_dir):
    inventory = {}
    for path in sorted(pathlib.Path(run_dir).rglob("*")):
        if path.is_file() and path.relative_to(run_dir).parts[0] != CLOSEOUT_DIRNAME:
            inventory[str(path.relative_to(run_dir)).replace("\\", "/")] = _sha(path)
    return inventory


def _control_files(path):
    result = {}
    for candidate in (pathlib.Path(path), pathlib.Path(str(path) + "-wal")):
        result[candidate.name] = (
            {"size": candidate.stat().st_size, "sha256": _sha(candidate)} if candidate.exists() else None
        )
    return result


def _hold_probe(path):
    path = pathlib.Path(path)
    before = _control_files(path)
    uri = "file:///" + urllib.parse.quote(path.as_posix(), safe="/:") + "?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=5)
        con.execute("PRAGMA query_only=ON")
        con.execute("BEGIN")
        row = con.execute(
            "SELECT new_entry_hold,health_status,control_generation FROM admission_control WHERE control_id=1"
        ).fetchone()
        holds = con.execute(
            "SELECT hold_id FROM hold_lifecycle WHERE status='ACTIVE' ORDER BY hold_id"
        ).fetchall()
        con.rollback()
        con.close()
    except Exception as exc:
        raise CloseoutBlocked("GLOBAL_CONTROL_READ_FAILED") from exc
    after = _control_files(path)
    if before != after:
        raise CloseoutBlocked("GLOBAL_CONTROL_CHANGED_DURING_READ")
    if row is None:
        raise CloseoutBlocked("GLOBAL_CONTROL_ROW_MISSING")
    return {
        "path": str(path), "files": after, "new_entry_hold": int(row[0]),
        "health_status": str(row[1]), "control_generation": int(row[2]),
        "active_hold_ids": [str(r[0]) for r in holds], "active_hold_count": len(holds),
    }


def _process_probe(status, lock, active, run_dir):
    ps = (
        "$ErrorActionPreference='Stop'; "
        "@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine) "
        "| ConvertTo-Json -Compress -Depth 3"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            text=True, capture_output=True, timeout=30, check=False,
        )
        if proc.returncode:
            raise CloseoutBlocked("PROCESS_CENSUS_FAILED")
        rows = json.loads(proc.stdout or "[]")
        if rows is None:
            rows = []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise CloseoutBlocked("PROCESS_CENSUS_INVALID")
    except CloseoutBlocked:
        raise
    except Exception as exc:
        raise CloseoutBlocked("PROCESS_CENSUS_FAILED") from exc

    lineage = status.get("solver_process_lineage") or {}
    tracked = {int(x) for x in (lock.get("pid"), active.get("pid"), lineage.get("child_pid")) if str(x).isdigit()}
    for item in lineage.get("processes", []) if isinstance(lineage.get("processes"), list) else []:
        if isinstance(item, dict) and str(item.get("pid", "")).isdigit():
            tracked.add(int(item["pid"]))
    terms = (CASE_ID.lower(), RUN_ID.lower(), str(run_dir).replace("/", "\\").lower())
    engines = ("fdtd-engine", "fdtd-solutions", "mpiexec", "smpd")
    children = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        try:
            pid = int(item.get("ProcessId"))
        except (TypeError, ValueError):
            continue
        try:
            parent = int(item.get("ParentProcessId"))
        except (TypeError, ValueError):
            parent = None
        if parent is not None:
            children.setdefault(parent, []).append(pid)
    related_tree = set(tracked)
    frontier = list(tracked)
    while frontier:
        parent_pid = frontier.pop()
        for child_pid in children.get(parent_pid, []):
            if child_pid not in related_tree:
                related_tree.add(child_pid)
                frontier.append(child_pid)
    live = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        try:
            pid = int(item.get("ProcessId"))
        except (TypeError, ValueError):
            continue
        parent = item.get("ParentProcessId")
        try:
            parent = int(parent)
        except (TypeError, ValueError):
            parent = None
        name = str(item.get("Name") or "").lower()
        cmd = str(item.get("CommandLine") or "").replace("/", "\\").lower()
        exact = any(term in cmd for term in terms)
        descendant_engine = pid in (related_tree - tracked) and (
            any(n in name for n in engines) or name in {"python.exe", "powershell.exe", "cmd.exe"} or exact
        )
        if exact or pid in tracked or descendant_engine:
            live.append({
                "pid": pid, "parent_pid": parent, "name": item.get("Name"),
                "creation_date": item.get("CreationDate"),
                "reason": "RUN_ID_OR_PATH" if exact else "RECORDED_PID" if pid in tracked else "RECORDED_DESCENDANT_ENGINE",
            })
    return {
        "available": True, "live_related": live, "census_count": len(rows),
        "tracked_pids": sorted(tracked), "tracked_descendant_pids": sorted(related_tree - tracked),
    }


def _truth_probe(run_dir, ledger_path):
    run_dir = pathlib.Path(run_dir)
    ledger_raw = pathlib.Path(ledger_path).read_bytes()
    ledger = json.loads(ledger_raw.decode("utf-8-sig"))
    records = ledger.get("case_records")
    if isinstance(records, dict):
        row = records.get(CASE_ID, {})
        if row and row.get("case_id", CASE_ID) != CASE_ID:
            raise CloseoutBlocked("COUPLING_LEDGER_CASE_RECORD_IDENTITY_MISMATCH")
    elif isinstance(records, list):
        matches = [r for r in records if isinstance(r, dict) and r.get("case_id") == CASE_ID]
        if len(matches) != 1:
            raise CloseoutBlocked("COUPLING_LEDGER_CASE_RECORD_NOT_UNIQUE")
        row = matches[0]
    else:
        raise CloseoutBlocked("COUPLING_LEDGER_CASE_RECORD_SCHEMA_INVALID")
    current = ledger.get("current_case") or {}
    truth_member = CASE_ID in ledger.get("truth_valid_case_ids", [])
    label_member = CASE_ID in ledger.get("labels_valid_case_ids", [])
    if current.get("case_id") != CASE_ID or current.get("run_id") != RUN_ID:
        raise CloseoutBlocked("COUPLING_LEDGER_TARGET_CHANGED")
    if row.get("run_id") != RUN_ID or row.get("phase") != "RUN_ONE_IN_PROGRESS":
        raise CloseoutBlocked("COUPLING_LEDGER_RUN_STATE_MISMATCH")
    if ledger.get("entered_count") != 11 or ledger.get("automatic_replay_count") != 0:
        raise CloseoutBlocked("COUPLING_ENTRY_OR_REPLAY_COUNT_MISMATCH")
    if truth_member or label_member:
        raise CloseoutBlocked("COUPLING_TARGET_ALREADY_HAS_VALID_TRUTH")
    if any(row.get(k) for k in ("ingest_truth_path", "truth_path", "ingest_result_path", "label_path")):
        raise CloseoutBlocked("COUPLING_TARGET_HAS_INGEST_ARTIFACT")
    validation = _read_json(run_dir / "validation.json")
    hashes = _read_json(run_dir / "hashes.json")
    if validation != {"state": "PENDING"} or hashes != {"state": "PENDING"}:
        raise CloseoutBlocked("RUN_VALIDATION_OR_HASHES_NOT_PENDING")
    h5_path = run_dir / "run" / "run_output.h5"
    try:
        import h5py
        with h5py.File(h5_path, "r") as h5:
            datasets = []
            h5.visititems(lambda name, obj: datasets.append(name) if isinstance(obj, h5py.Dataset) else None)
    except Exception as exc:
        raise CloseoutBlocked("POSTENTRY_H5_TRUTH_INSPECTION_FAILED") from exc
    noncoords = [p for p in datasets if p.rsplit("/", 1)[-1].lower() not in {"x", "y", "z"}]
    if noncoords:
        raise CloseoutBlocked("POSTENTRY_H5_CONTAINS_NON_COORDINATE_RESULTS")
    candidates = []
    for path in run_dir.rglob("*"):
        if not path.is_file() or path.relative_to(run_dir).parts[0] == CLOSEOUT_DIRNAME:
            continue
        lower = path.name.lower()
        if path == h5_path or path.suffix.lower() == ".fsp":
            continue
        if "truth" in lower or "scientific_valid" in lower or path.suffix.lower() == ".npz":
            candidates.append(str(path.relative_to(run_dir)))
    if candidates:
        raise CloseoutBlocked("POSTENTRY_TRUTH_CANDIDATE_ARTIFACT_PRESENT")
    return {
        "truth_available": False,
        "reason": "VALIDATION_AND_HASHES_PENDING;H5_COORDINATES_ONLY;COUPLING_EXCLUDES_TARGET",
        "validation_state": "PENDING", "hashes_state": "PENDING",
        "h5_path": str(h5_path), "h5_sha256": _sha(h5_path),
        "h5_dataset_paths": sorted(datasets), "non_coordinate_dataset_paths": noncoords,
        "coupling_ledger_sha256": _sha_bytes(ledger_raw),
        "truth_valid_case": False, "labels_valid_case": False, "candidate_truth_artifacts": candidates,
    }


def _validate_hold(hold):
    if hold.get("health_status") != "PASS" or hold.get("new_entry_hold") != 0:
        raise CloseoutBlocked("ACTIVE_OR_UNHEALTHY_GLOBAL_HOLD")
    if hold.get("active_hold_count") != 0 or hold.get("active_hold_ids"):
        raise CloseoutBlocked("ACTIVE_GLOBAL_HOLD_LIFECYCLE")


def _validate_identity(root):
    paths = _paths(root)
    if any(not paths[k].is_file() for k in paths):
        raise CloseoutBlocked("REQUIRED_IDENTITY_FILE_MISSING")
    lock, active, registry, status, manifest = (_read_json(paths[k]) for k in ("lock", "active", "registry", "status", "manifest"))
    expected = {"case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID}
    for name, value in (("lock", lock), ("active", active), ("status", status), ("manifest", manifest)):
        if any(value.get(k) != v for k, v in expected.items()):
            raise CloseoutBlocked("IDENTITY_MISMATCH:" + name)
    if lock.get("pid") != active.get("pid") or active.get("state") != "SOLVER_ENTERED":
        raise CloseoutBlocked("LOCK_ACTIVE_IDENTITY_MISMATCH")
    if status.get("state") != "SOLVER_ENTERED" or status.get("solver_entered") is not True or status.get("solver_invocations") != 1:
        raise CloseoutBlocked("ENTRY_STATUS_NOT_EXACTLY_ONE")
    rows = [r for r in registry.get("runs", []) if isinstance(r, dict) and r.get("run_id") == RUN_ID]
    same = [r for r in registry.get("runs", []) if isinstance(r, dict) and r.get("case_id") == CASE_ID and r.get("attempt_id") == ATTEMPT_ID]
    if registry.get("schema") != "APCD_GPU_RUNNER_REGISTRY_V1" or len(rows) != 1 or len(same) != 1:
        raise CloseoutBlocked("REGISTRY_TARGET_NOT_UNIQUE")
    if rows[0].get("state") != "SOLVER_ENTERED" or rows[0].get("run_dir") != str(_run_dir(root)):
        raise CloseoutBlocked("REGISTRY_TARGET_STATE_OR_PATH_MISMATCH")
    proof_path = _run_dir(root) / "pre_entry_revalidation.json"
    proof = _read_json(proof_path)
    if status.get("pre_entry_revalidation_sha256") != _sha(proof_path):
        raise CloseoutBlocked("PRE_ENTRY_PROOF_HASH_MISMATCH")
    if proof.get("run_id") != RUN_ID or proof.get("result") != "PASS":
        raise CloseoutBlocked("PRE_ENTRY_PROOF_IDENTITY_OR_RESULT_MISMATCH")
    proof_generation = proof.get("global_entry_control", {}).get("control_generation")
    status_generation = status.get("global_entry_control_generation", proof_generation)
    if proof_generation != 27 or status_generation != proof_generation:
        raise CloseoutBlocked("ENTRY_CONTROL_GENERATION_MISMATCH")
    expected_fsp_sha = manifest.get("pre_fsp_sha256")
    source_fsp_path = manifest.get("pre_fsp_path")
    if not expected_fsp_sha or not source_fsp_path:
        raise CloseoutBlocked("MANIFEST_PRE_FSP_IDENTITY_MISSING")
    if not pathlib.Path(source_fsp_path).is_file() or _sha(source_fsp_path) != expected_fsp_sha:
        raise CloseoutBlocked("SOURCE_PRE_FSP_HASH_MISMATCH")
    if not (_run_dir(root) / "run.fsp").is_file():
        raise CloseoutBlocked("POST_RUN_FSP_MISSING")
    if any(k in status and status.get(k) != expected_fsp_sha for k in ("pre_fsp_sha256", "source_pre_fsp_sha256", "staged_pre_fsp_sha256")):
        raise CloseoutBlocked("STATUS_FSP_HASH_MISMATCH")
    if proof.get("physical_contract_sha256") != manifest.get("physical_contract_sha256"):
        raise CloseoutBlocked("MANIFEST_CONTRACT_HASH_MISMATCH")
    if proof.get("source_fsp_sha256") != expected_fsp_sha or proof.get("staged_fsp_sha256") != expected_fsp_sha:
        raise CloseoutBlocked("PRE_ENTRY_FSP_HASH_MISMATCH")
    setup_path = _run_dir(root) / "setup_validation.json"
    if status.get("setup_validation_sha256") != _sha(setup_path):
        raise CloseoutBlocked("SETUP_VALIDATION_HASH_MISMATCH")
    return {
        "paths": paths, "lock": lock, "active": active, "registry": registry,
        "status": status, "manifest": manifest,
    }


def _initial_hashes(root):
    paths = _paths(root)
    return {
        "markers": {"lock": _sha(paths["lock"]), "active": _sha(paths["active"])},
        "registry": _sha(paths["registry"]), "status": _sha(paths["status"]),
        "manifest": _sha(paths["manifest"]), "run_inventory": _run_inventory(_run_dir(root)),
    }


def _fresh_evidence(root, control_path, ledger_path, process_probe, hold_probe, truth_probe, identity):
    hold = hold_probe(control_path)
    _validate_hold(hold)
    process = process_probe(identity["status"], identity["lock"], identity["active"], _run_dir(root))
    if process.get("available") is not True or process.get("live_related"):
        raise CloseoutBlocked("RELATED_CONTROLLER_OR_ENGINE_LIVE_OR_UNKNOWN")
    truth = truth_probe(_run_dir(root), ledger_path)
    if truth.get("truth_available") is not False or truth.get("truth_valid_case") is not False or truth.get("labels_valid_case") is not False:
        raise CloseoutBlocked("TRUTH_STATE_CHANGED_OR_UNVERIFIED")
    if not truth.get("coupling_ledger_sha256"):
        raise CloseoutBlocked("COUPLING_LEDGER_TRUTH_EVIDENCE_MISSING")
    return {"hold": hold, "process": process, "truth": truth}


def _claim_body(root, hashes, identity, live):
    return {
        "schema": SCHEMA + "_RECOVERY_FENCE",
        "target": {"case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID},
        "recovery_fence_id": uuid.uuid4().hex,
        "created_utc": _now(),
        "runner_root": str(root),
        "input_hashes": hashes,
        "initial_marker_values": {"lock": identity["lock"], "active": identity["active"]},
        "initial_control": live["hold"],
        "initial_process_probe": live["process"],
        "initial_truth_probe": live["truth"],
        "authority_reference": "PROJECT_OWNER_APPROVED_RECOVERY;D6_M05_FIXED_RUN_ZERO_SOLVER_CLOSEOUT",
    }


def _seal_claim(body):
    return dict(body, claim_sha256=_sha_bytes(_canonical(body)))


def _verify_claim(claim):
    if not isinstance(claim, dict) or claim.get("schema") != SCHEMA + "_RECOVERY_FENCE":
        raise CloseoutBlocked("RECOVERY_CLAIM_SCHEMA_INVALID")
    if claim.get("target") != {"case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID}:
        raise CloseoutBlocked("RECOVERY_CLAIM_IDENTITY_MISMATCH")
    body = dict(claim)
    saved = body.pop("claim_sha256", None)
    if saved != _sha_bytes(_canonical(body)):
        raise CloseoutBlocked("RECOVERY_CLAIM_HASH_MISMATCH")


def _journal_read(path, claim):
    if not path.exists():
        return {"schema": SCHEMA + "_HASH_CHAIN", "claim_sha256": claim["claim_sha256"], "records": [], "chain_head_sha256": None}
    journal = _read_json(path)
    if journal.get("schema") != SCHEMA + "_HASH_CHAIN" or journal.get("claim_sha256") != claim.get("claim_sha256"):
        raise CloseoutBlocked("CLOSEOUT_JOURNAL_IDENTITY_MISMATCH")
    records = journal.get("records")
    if not isinstance(records, list):
        raise CloseoutBlocked("CLOSEOUT_JOURNAL_INVALID")
    previous = None
    for index, record in enumerate(records, 1):
        body = dict(record)
        saved = body.pop("record_sha256", None)
        if record.get("sequence") != index or record.get("previous_record_sha256") != previous:
            raise CloseoutBlocked("CLOSEOUT_JOURNAL_CHAIN_ORDER_INVALID")
        if saved != _sha_bytes(_canonical(body)):
            raise CloseoutBlocked("CLOSEOUT_JOURNAL_CHAIN_HASH_INVALID")
        previous = saved
    if journal.get("chain_head_sha256") != previous:
        raise CloseoutBlocked("CLOSEOUT_JOURNAL_HEAD_INVALID")
    return journal


def _event(journal, name):
    found = [r for r in journal["records"] if r.get("event") == name]
    if len(found) > 1:
        raise CloseoutBlocked("CLOSEOUT_JOURNAL_DUPLICATE_EVENT:" + name)
    return found[0] if found else None


def _append(path, journal, name, payload):
    if _event(journal, name):
        return journal
    body = {
        "sequence": len(journal["records"]) + 1, "event": name, "recorded_utc": _now(),
        "previous_record_sha256": journal.get("chain_head_sha256"), "payload": payload,
    }
    record = dict(body, record_sha256=_sha_bytes(_canonical(body)))
    updated = dict(journal)
    updated["records"] = list(journal["records"]) + [record]
    updated["chain_head_sha256"] = record["record_sha256"]
    _write_json(path, updated)
    return updated


def _event_payload(journal, name):
    entry = _event(journal, name)
    return entry.get("payload") if entry else None


def _validate_terminal_status(status, claim):
    ref = status.get("postentry_closeout_v1") or {}
    if (
        status.get("state") != "FAILED_POSTENTRY"
        or status.get("solver_entered") is not True
        or status.get("solver_invocations") != 1
        or ref.get("recovery_fence_id") != claim.get("recovery_fence_id")
        or ref.get("entry_consumed") is not True
        or ref.get("truth_available") is not False
        or ref.get("exit_reason") != "UNKNOWN"
        or ref.get("automatic_replay_count") != 0
        or not ref.get("disposition_sha256")
    ):
        raise CloseoutBlocked("TERMINAL_STATUS_NOT_OWNED_BY_RECOVERY_FENCE")


def _validate_terminal_registry(registry, claim):
    rows = [r for r in registry.get("runs", []) if isinstance(r, dict) and r.get("run_id") == RUN_ID]
    same = [r for r in registry.get("runs", []) if isinstance(r, dict) and r.get("case_id") == CASE_ID and r.get("attempt_id") == ATTEMPT_ID]
    if len(rows) != 1 or len(same) != 1:
        raise CloseoutBlocked("TERMINAL_REGISTRY_TARGET_NOT_UNIQUE")
    row = rows[0]
    if (
        row.get("state") != "FAILED_POSTENTRY"
        or row.get("postentry_closeout_fence_id") != claim.get("recovery_fence_id")
        or not row.get("postentry_disposition_sha256")
        or row.get("solver_invocations") != 1
        or row.get("automatic_replay_count") != 0
    ):
        raise CloseoutBlocked("TERMINAL_REGISTRY_NOT_OWNED_BY_RECOVERY_FENCE")
    return row


def _assert_markers_original(root, claim):
    paths = _paths(root)
    for name in ("lock", "active"):
        if not paths[name].exists() or _sha(paths[name]) != claim["input_hashes"]["markers"][name]:
            raise CloseoutBlocked("ORPHAN_MARKER_HASH_MISMATCH:" + name)
    _validate_identity(root)


def _assert_run_inventory(root, claim, journal):
    expected = dict(claim["input_hashes"]["run_inventory"])
    current = _run_inventory(_run_dir(root))
    status_event = _event(journal, "STATUS_TERMINALIZED")
    if status_event:
        expected["status.json"] = status_event["payload"]["status_sha256"]
    if current != expected:
        raise CloseoutBlocked("RUN_ARTIFACT_INVENTORY_HASH_MISMATCH")


def _assert_initial_unchanged(root, claim):
    paths = _paths(root)
    if _sha(paths["lock"]) != claim["input_hashes"]["markers"]["lock"]:
        raise CloseoutBlocked("LOCK_HASH_CHANGED_FROM_FRESH_CLAIM")
    if _sha(paths["active"]) != claim["input_hashes"]["markers"]["active"]:
        raise CloseoutBlocked("ACTIVE_HASH_CHANGED_FROM_FRESH_CLAIM")
    if _sha(paths["registry"]) != claim["input_hashes"]["registry"]:
        raise CloseoutBlocked("REGISTRY_HASH_CHANGED_FROM_FRESH_CLAIM")
    if _sha(paths["status"]) != claim["input_hashes"]["status"]:
        raise CloseoutBlocked("STATUS_HASH_CHANGED_FROM_FRESH_CLAIM")
    if _sha(paths["manifest"]) != claim["input_hashes"]["manifest"]:
        raise CloseoutBlocked("MANIFEST_HASH_CHANGED_FROM_FRESH_CLAIM")
    if _run_inventory(_run_dir(root)) != claim["input_hashes"]["run_inventory"]:
        raise CloseoutBlocked("RUN_INVENTORY_CHANGED_FROM_FRESH_CLAIM")


def _terminal_hashes(root, claim, journal):
    status_path = _paths(root)["status"]
    registry_path = _paths(root)["registry"]
    status = _read_json(status_path)
    _validate_terminal_status(status, claim)
    status_sha = _sha(status_path)
    disposition_event = _event_payload(journal, "DISPOSITION_WRITTEN")
    if not disposition_event or status["postentry_closeout_v1"]["disposition_sha256"] != disposition_event.get("disposition_sha256"):
        raise CloseoutBlocked("TERMINAL_STATUS_DISPOSITION_CHAIN_MISMATCH")
    se = _event(journal, "STATUS_TERMINALIZED")
    if se and se["payload"].get("status_sha256") != status_sha:
        raise CloseoutBlocked("TERMINAL_STATUS_HASH_MISMATCH")
    registry = _read_json(registry_path)
    row = _validate_terminal_registry(registry, claim)
    registry_sha = _sha(registry_path)
    revent = _event(journal, "REGISTRY_TERMINALIZED")
    if revent and revent["payload"].get("registry_sha256") != registry_sha:
        raise CloseoutBlocked("TERMINAL_REGISTRY_HASH_MISMATCH")
    if row.get("postentry_disposition_sha256") != status["postentry_closeout_v1"]["disposition_sha256"]:
        raise CloseoutBlocked("STATUS_REGISTRY_DISPOSITION_MISMATCH")
    return status_sha, registry_sha, status, registry


def _fresh_safety(root, control_path, ledger_path, claim, process_probe, hold_probe, truth_probe):
    hold = hold_probe(control_path)
    _validate_hold(hold)
    if hold != claim["initial_control"]:
        raise CloseoutBlocked("GLOBAL_CONTROL_FENCE_CHANGED")
    if _sha(ledger_path) != claim["initial_truth_probe"]["coupling_ledger_sha256"]:
        raise CloseoutBlocked("COUPLING_LEDGER_CHANGED_DURING_CLOSEOUT")
    status = _read_json(_paths(root)["status"])
    lock_path = _paths(root)["lock"]
    active_path = _paths(root)["active"]
    lock = _read_json(lock_path) if lock_path.exists() else claim["initial_marker_values"]["lock"]
    active = _read_json(active_path) if active_path.exists() else claim["initial_marker_values"]["active"]
    proc = process_probe(status, lock, active, _run_dir(root))
    if proc.get("available") is not True or proc.get("live_related"):
        raise CloseoutBlocked("RELATED_CONTROLLER_OR_ENGINE_LIVE_OR_UNKNOWN")
    truth = truth_probe(_run_dir(root), ledger_path)
    if truth.get("truth_available") is not False or truth.get("truth_valid_case") is not False or truth.get("labels_valid_case") is not False:
        raise CloseoutBlocked("TRUTH_STATE_CHANGED_OR_UNVERIFIED")
    if truth.get("coupling_ledger_sha256") != _sha(ledger_path):
        raise CloseoutBlocked("COUPLING_LEDGER_CHANGED_DURING_TRUTH_PROBE")
    return {"hold": hold, "process": proc, "truth": truth}


def _disposition(claim):
    return {
        "schema": SCHEMA + "_DISPOSITION",
        "case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID,
        "recovery_fence_id": claim["recovery_fence_id"], "claim_sha256": claim["claim_sha256"],
        "disposition": "FAILED_POSTENTRY_NO_TRUTH",
        "entry_consumed": True, "solver_invocations": 1, "automatic_replay_count": 0,
        "solver_return_observed": False, "exit_reason": "UNKNOWN", "truth_available": False,
        "truth_disposition": "UNRECOVERABLE_FROM_AVAILABLE_DURABLE_ARTIFACTS",
        "training_admitted": False, "scientific_valid": False, "quarantine": True,
        "quarantine_reason": "POSTENTRY_TRUTH_UNAVAILABLE;DO_NOT_TRAIN_OR_HANDOFF",
        "created_utc": claim["created_utc"], "input_hashes": claim["input_hashes"],
        "truth_evidence": claim["initial_truth_probe"], "control_evidence": claim["initial_control"],
        "process_evidence": claim["initial_process_probe"], "authority_reference": claim["authority_reference"],
    }


def _fault(fault_after, phase):
    if fault_after == phase:
        raise InjectedCloseoutCrash("INJECTED_PARTIAL_CLOSEOUT_AFTER:" + phase)


def _archive_marker(src, dst, expected_sha, expected_value):
    if dst.exists():
        if _sha(dst) != expected_sha:
            raise CloseoutBlocked("RELEASED_MARKER_ARCHIVE_HASH_MISMATCH:" + dst.name)
        if src.exists():
            raise CloseoutBlocked("BOTH_ORIGINAL_AND_ARCHIVED_MARKERS_PRESENT:" + src.name)
        return "ALREADY_ARCHIVED"
    if not src.exists() or _sha(src) != expected_sha or _read_json(src) != expected_value:
        raise CloseoutBlocked("MARKER_COMPARE_AND_SWAP_FAILED:" + src.name)
    src.rename(dst)
    if _sha(dst) != expected_sha:
        raise CloseoutBlocked("MARKER_ARCHIVE_VERIFY_FAILED:" + dst.name)
    return "ARCHIVED"


def _closeout_one_run(root, control_path, ledger_path, *, process_probe, hold_probe, truth_probe, fault_after=None, authority_reference="PROJECT_OWNER_APPROVED_RECOVERY;D6_M05_FIXED_RUN_ZERO_SOLVER_CLOSEOUT"):
    root = pathlib.Path(root).resolve()
    rd = _run_dir(root)
    cd = _closeout_dir(root)
    claim_path, journal_path, disposition_path = cd / "claim.json", cd / "journal.json", cd / "disposition.json"
    archive_active, archive_lock = cd / "released_active_run.json", cd / "released_runner.lock"

    if not claim_path.exists():
        if cd.exists() and any(cd.iterdir()):
            raise CloseoutBlocked("UNCLAIMED_CLOSEOUT_DIRECTORY_NOT_EMPTY")
        identity = _validate_identity(root)
        live = _fresh_evidence(root, control_path, ledger_path, process_probe, hold_probe, truth_probe, identity)
        hashes = _initial_hashes(root)
        body = {
            "schema": SCHEMA + "_RECOVERY_FENCE",
            "target": {"case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID},
            "recovery_fence_id": uuid.uuid4().hex,
            "created_utc": _now(),
            "runner_root": str(root),
            "input_hashes": hashes,
            "initial_marker_values": {"lock": identity["lock"], "active": identity["active"]},
            "initial_control": live["hold"],
            "initial_process_probe": live["process"],
            "initial_truth_probe": live["truth"],
            "authority_reference": authority_reference,
        }
        claim = dict(body, claim_sha256=_sha_bytes(_canonical(body)))
        cd.mkdir(parents=True, exist_ok=True)
        if not _create_exclusive_json(claim_path, claim):
            claim = _read_json(claim_path)
    else:
        claim = _read_json(claim_path)
    _verify_claim(claim)
    if claim.get("runner_root") != str(root):
        raise CloseoutBlocked("RECOVERY_CLAIM_ROOT_MISMATCH")
    journal = _journal_read(journal_path, claim)
    if not journal["records"]:
        live = _fresh_safety(root, control_path, ledger_path, claim, process_probe, hold_probe, truth_probe)
        _assert_initial_unchanged(root, claim)
        _assert_markers_original(root, claim)
        journal = _append(journal_path, journal, "PREPARED", {
            "claim_sha256": claim["claim_sha256"],
            "initial_hashes": claim["input_hashes"],
            "recovery_fence_id": claim["recovery_fence_id"],
        })

    if _event(journal, "LOCK_RELEASED"):
        if not archive_active.exists() or _sha(archive_active) != claim["input_hashes"]["markers"]["active"]:
            raise CloseoutBlocked("CLOSED_ACTIVE_MARKER_ARCHIVE_INVALID")
        if not archive_lock.exists() or _sha(archive_lock) != claim["input_hashes"]["markers"]["lock"]:
            raise CloseoutBlocked("CLOSED_LOCK_ARCHIVE_INVALID")
        disposition_event = _event_payload(journal, "DISPOSITION_WRITTEN")
        disposition_path = cd / "disposition.json"
        if (not disposition_event or not disposition_path.exists()
                or _sha(disposition_path) != disposition_event.get("disposition_sha256")):
            raise CloseoutBlocked("CLOSED_DISPOSITION_ARCHIVE_INVALID")
        status_sha, registry_sha, status, registry = _terminal_hashes(root, claim, journal)
        return {
            "result": "ALREADY_CLOSED", "solver_entry_count": 1, "automatic_replay_count": 0,
            "recovery_fence_id": claim["recovery_fence_id"],
            "status_sha256": status_sha, "registry_sha256": registry_sha,
            "journal_sha256": _sha(journal_path),
        }

    live = _fresh_safety(root, control_path, ledger_path, claim, process_probe, hold_probe, truth_probe)
    if not _event(journal, "DISPOSITION_WRITTEN"):
        expected_disposition = _disposition(claim)
        if disposition_path.exists():
            if _read_json(disposition_path) != expected_disposition:
                raise CloseoutBlocked("DISPOSITION_FILE_CONFLICT")
        else:
            _assert_initial_unchanged(root, claim)
            _assert_markers_original(root, claim)
            if _sha(_paths(root)["status"]) != claim["input_hashes"]["status"] or _sha(_paths(root)["registry"]) != claim["input_hashes"]["registry"]:
                raise CloseoutBlocked("STATE_CHANGED_BEFORE_DISPOSITION")
            _write_json(disposition_path, expected_disposition)
            _fault(fault_after, "after_disposition_write")
        disposition_sha = _sha(disposition_path)
        journal = _append(journal_path, journal, "DISPOSITION_WRITTEN", {
            "disposition_sha256": disposition_sha, "recovery_fence_id": claim["recovery_fence_id"],
        })
    else:
        disposition_sha = _event_payload(journal, "DISPOSITION_WRITTEN")["disposition_sha256"]
        if not disposition_path.exists() or _sha(disposition_path) != disposition_sha:
            raise CloseoutBlocked("DISPOSITION_HASH_MISMATCH")

    status_path = _paths(root)["status"]
    status = _read_json(status_path)
    if not _event(journal, "STATUS_TERMINALIZED"):
        if not _event(journal, "STATUS_TERMINALIZATION_INTENT"):
            journal = _append(journal_path, journal, "STATUS_TERMINALIZATION_INTENT", {
                "from": "SOLVER_ENTERED", "to": "FAILED_POSTENTRY",
                "disposition_sha256": disposition_sha, "recovery_fence_id": claim["recovery_fence_id"],
            })
        if status.get("state") == "SOLVER_ENTERED":
            if _sha(status_path) != claim["input_hashes"]["status"]:
                raise CloseoutBlocked("STATUS_HASH_MISMATCH_BEFORE_TERMINALIZATION")
            _fresh_safety(root, control_path, ledger_path, claim, process_probe, hold_probe, truth_probe)
            _assert_markers_original(root, claim)
            _assert_initial_unchanged(root, claim)
            if _sha(status_path) != claim["input_hashes"]["status"]:
                raise CloseoutBlocked("STATUS_CHANGED_DURING_TERMINALIZATION_REVALIDATION")
            _runner._transition(
                rd, status, "FAILED_POSTENTRY",
                failure="ORPHAN_POSTENTRY_NO_TRUTH_EXIT_REASON_UNKNOWN",
                failed_unix=__import__("time").time(),
                postentry_closeout_v1={
                    "schema": SCHEMA,
                    "recovery_fence_id": claim["recovery_fence_id"],
                    "disposition_sha256": disposition_sha,
                    "entry_consumed": True,
                    "truth_available": False,
                    "exit_reason": "UNKNOWN",
                    "automatic_replay_count": 0,
                },
            )
            _fault(fault_after, "after_status_write")
        status = _read_json(status_path)
        _validate_terminal_status(status, claim)
        if status["postentry_closeout_v1"]["disposition_sha256"] != disposition_sha:
            raise CloseoutBlocked("STATUS_DISPOSITION_HASH_MISMATCH")
        status_sha = _sha(status_path)
        journal = _append(journal_path, journal, "STATUS_TERMINALIZED", {
            "status_sha256": status_sha, "disposition_sha256": disposition_sha,
            "solver_invocations": 1, "automatic_replay_count": 0,
        })
    else:
        status_sha = _event_payload(journal, "STATUS_TERMINALIZED")["status_sha256"]
        if _sha(status_path) != status_sha:
            raise CloseoutBlocked("TERMINAL_STATUS_HASH_MISMATCH")

    registry_path = _paths(root)["registry"]
    registry = _read_json(registry_path)
    if not _event(journal, "REGISTRY_TERMINALIZED"):
        if not _event(journal, "REGISTRY_TERMINALIZATION_INTENT"):
            journal = _append(journal_path, journal, "REGISTRY_TERMINALIZATION_INTENT", {
                "disposition_sha256": disposition_sha, "status_sha256": status_sha,
                "recovery_fence_id": claim["recovery_fence_id"],
            })
        if _sha(registry_path) == claim["input_hashes"]["registry"]:
            _fresh_safety(root, control_path, ledger_path, claim, process_probe, hold_probe, truth_probe)
            status = _read_json(status_path)
            _validate_terminal_status(status, claim)
            _assert_run_inventory(root, claim, journal)
            if _sha(registry_path) != claim["input_hashes"]["registry"]:
                raise CloseoutBlocked("REGISTRY_CHANGED_DURING_TERMINALIZATION_REVALIDATION")
            registry = _read_json(registry_path)
            rows = [r for r in registry.get("runs", []) if isinstance(r, dict) and r.get("run_id") == RUN_ID]
            if len(rows) != 1 or rows[0].get("state") != "SOLVER_ENTERED":
                raise CloseoutBlocked("REGISTRY_TARGET_CHANGED_BEFORE_TERMINALIZATION")
            rows[0].update(
                state="FAILED_POSTENTRY",
                postentry_closeout_fence_id=claim["recovery_fence_id"],
                postentry_disposition_sha256=disposition_sha,
                solver_invocations=1,
                automatic_replay_count=0,
            )
            _write_json(registry_path, registry)
            _fault(fault_after, "after_registry_write")
        registry = _read_json(registry_path)
        row = _validate_terminal_registry(registry, claim)
        if row["postentry_disposition_sha256"] != disposition_sha:
            raise CloseoutBlocked("REGISTRY_DISPOSITION_HASH_MISMATCH")
        registry_sha = _sha(registry_path)
        journal = _append(journal_path, journal, "REGISTRY_TERMINALIZED", {
            "registry_sha256": registry_sha, "disposition_sha256": disposition_sha,
            "solver_invocations": 1, "automatic_replay_count": 0,
        })
    else:
        registry_sha = _event_payload(journal, "REGISTRY_TERMINALIZED")["registry_sha256"]
        if _sha(registry_path) != registry_sha:
            raise CloseoutBlocked("TERMINAL_REGISTRY_HASH_MISMATCH")

    status_sha, registry_sha, status, registry = _terminal_hashes(root, claim, journal)
    live = _fresh_safety(root, control_path, ledger_path, claim, process_probe, hold_probe, truth_probe)
    status_sha, registry_sha, status, registry = _terminal_hashes(root, claim, journal)
    if not disposition_path.exists() or _sha(disposition_path) != disposition_sha:
        raise CloseoutBlocked("DISPOSITION_HASH_CHANGED_BEFORE_RELEASE_AUDIT")
    _assert_run_inventory(root, claim, journal)
    # RELEASE_READY is written before marker removal. A crash can occur after
    # the active marker is atomically renamed but before ACTIVE_MARKER_RELEASED
    # reaches the journal, so accept exactly one of the original marker or its
    # byte-identical archive here.
    active_marker = _paths(root)["active"]
    expected_active_sha = claim["input_hashes"]["markers"]["active"]
    if archive_active.exists():
        if _sha(archive_active) != expected_active_sha or active_marker.exists():
            raise CloseoutBlocked("ACTIVE_MARKER_ARCHIVE_CHANGED_BEFORE_LOCK_RELEASE")
    elif not active_marker.exists() or _sha(active_marker) != expected_active_sha:
        raise CloseoutBlocked("ACTIVE_MARKER_ARCHIVE_CHANGED_BEFORE_LOCK_RELEASE")
    paths = _paths(root)
    if not _event(journal, "RELEASE_READY"):
        for name in ("lock", "active"):
            if not paths[name].exists() or _sha(paths[name]) != claim["input_hashes"]["markers"][name]:
                raise CloseoutBlocked("MARKER_HASH_MISMATCH_BEFORE_RELEASE_AUDIT:" + name)
        release_payload = {
            "identity": {"case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID},
            "recovery_fence_id": claim["recovery_fence_id"],
            "original_hashes": claim["input_hashes"],
            "terminal_hashes": {
                "disposition_sha256": disposition_sha,
                "status_sha256": status_sha,
                "registry_sha256": registry_sha,
            },
            "control_snapshot": live["hold"],
            "process_snapshot": live["process"],
            "truth_snapshot": live["truth"],
            "solver_entry_count": 1,
            "automatic_replay_count": 0,
        }
        journal = _append(journal_path, journal, "RELEASE_READY", release_payload)
        journal = _journal_read(journal_path, claim)
        if not _event(journal, "RELEASE_READY") or not journal.get("chain_head_sha256"):
            raise CloseoutBlocked("RELEASE_AUDIT_NOT_DURABLE")

    _fresh_safety(root, control_path, ledger_path, claim, process_probe, hold_probe, truth_probe)
    status_sha, registry_sha, status, registry = _terminal_hashes(root, claim, journal)
    _assert_run_inventory(root, claim, journal)
    active_result = _archive_marker(
        paths["active"], archive_active, claim["input_hashes"]["markers"]["active"],
        claim["initial_marker_values"]["active"],
    )
    _fault(fault_after, "after_active_marker_archive")
    if not _event(journal, "ACTIVE_MARKER_RELEASED"):
        journal = _append(journal_path, journal, "ACTIVE_MARKER_RELEASED", {
            "marker": "active_run.json", "archive_sha256": _sha(archive_active), "result": active_result,
        })

    # The lock remains the single-slot barrier until every preceding closeout record is durable.
    live = _fresh_safety(root, control_path, ledger_path, claim, process_probe, hold_probe, truth_probe)
    status_sha, registry_sha, status, registry = _terminal_hashes(root, claim, journal)
    if not disposition_path.exists() or _sha(disposition_path) != disposition_sha:
        raise CloseoutBlocked("DISPOSITION_HASH_CHANGED_BEFORE_LOCK_RELEASE")
    _assert_run_inventory(root, claim, journal)
    if not _event(journal, "LOCK_RELEASE_INTENT"):
        ready = _event(journal, "RELEASE_READY")
        if ready is None:
            raise CloseoutBlocked("RELEASE_READY_AUDIT_MISSING")
        journal = _append(journal_path, journal, "LOCK_RELEASE_INTENT", {
            "release_ready_record_sha256": ready["record_sha256"],
            "lock_sha256": claim["input_hashes"]["markers"]["lock"],
            "active_archive_sha256": _sha(archive_active),
            "status_sha256": status_sha,
            "registry_sha256": registry_sha,
            "control_snapshot": live["hold"],
            "process_snapshot": live["process"],
            "truth_snapshot": live["truth"],
        })
    _fault(fault_after, "before_lock_marker_archive")
    lock_result = _archive_marker(
        paths["lock"], archive_lock, claim["input_hashes"]["markers"]["lock"],
        claim["initial_marker_values"]["lock"],
    )
    _fault(fault_after, "after_lock_marker_archive")
    if not _event(journal, "LOCK_RELEASED"):
        journal = _append(journal_path, journal, "LOCK_RELEASED", {
            "marker": ".runner.lock", "archive_sha256": _sha(archive_lock), "result": lock_result,
            "status_sha256": _sha(paths["status"]),
            "registry_target_state": "FAILED_POSTENTRY", "solver_entry_count": 1,
            "automatic_replay_count": 0,
        })
    return {
        "result": "CLOSED", "case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID,
        "state": "FAILED_POSTENTRY", "truth_available": False, "exit_reason": "UNKNOWN",
        "solver_entry_count": 1, "automatic_replay_count": 0,
        "recovery_fence_id": claim["recovery_fence_id"],
        "disposition_sha256": _sha(disposition_path), "journal_sha256": _sha(journal_path),
        "released_active_marker_sha256": _sha(archive_active),
        "released_lock_sha256": _sha(archive_lock),
    }


def closeout_d6_m05_production():
    """Fixed identity entry point; no caller-supplied case, attempt, or run path."""
    root = PRODUCTION_ROOT.resolve()
    if root != pathlib.Path(_runner.PRODUCTION_RUNNER_ROOT).resolve():
        raise CloseoutBlocked("PINNED_RUNNER_ROOT_MISMATCH")
    return _closeout_one_run(
        root, CONTROL_DB, COUPLING_LEDGER,
        process_probe=_process_probe, hold_probe=_hold_probe, truth_probe=_truth_probe,
    )


if __name__ == "__main__":
    try:
        print(json.dumps(closeout_d6_m05_production(), sort_keys=True))
    except CloseoutBlocked as exc:
        print(json.dumps({"result": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        raise SystemExit(2)
