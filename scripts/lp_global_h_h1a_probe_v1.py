from __future__ import annotations

import argparse
import atexit
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ANCHOR_MANIFEST = ROOT / "reports/stage_h0_global_h/anchor_manifest.json"
SOURCE_CSV = ROOT / "outputs/lp_ml_dataset_v1/clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv"
FORMAL_CONTRACT = ROOT / "outputs/lp_ml_dataset_v1/contracts/lp_linear_x_projector_target_matrix_v1.json"
OUT = ROOT / "outputs/lp_global_h_h1a"
REPORT = ROOT / "reports/stage_h1a_global_h"
RUNTIME = OUT / "runtime"
NEW_HEIGHTS_NM = (400.0, 450.0, 550.0, 600.0)
ALL_HEIGHTS_NM = (400.0, 450.0, 500.0, 550.0, 600.0)
POLARIZATIONS = ("x", "y")
FORMAL_PERIOD_NM = 432.0
FORMAL_SOURCE_Z_NM = -250.0
FORMAL_MONITOR_Z_NM = 1000.0
MATERIAL_CONTRACT = "APCD_TIO2_NATIVE_M1"
EXTRACTION_CONVENTION = "transmission_side_full_period_coordinate_weighted_complex_G0_endpoint_dedup_periodic_reclosure_sqrtT_over_norm_arg_txx"
BUILDER_VERSION = "lp_ml_inverse_stage1_fdt_validation_runner_v1.unified_h_geometry_contract"
H500_DEDICATED_REFERENCE_DEG = 18.557501177497556
H500_HISTORICAL_QUANTILE_REFERENCE_DEG = 27.845019017638
MAX_NEW_SUBRUNS = 48
RUNNER_GUARD_FILENAME = "active_runner_guard.json"
READINESS_FILENAME = "license_readiness.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


RUNNER = load_module(ROOT / "scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py", "lp_h1a_formal_runner")
H0 = load_module(ROOT / "scripts/lp_global_h_h0_audit_v1.py", "lp_h1a_h0_audit")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_obj(value: object) -> str:
    return sha256_bytes(canonical_bytes(value))


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def h1a_run_identity(branch: str) -> str:
    payload = {
        "stage": "H1A",
        "branch": branch,
        "anchor_manifest_sha256": sha256_file(ANCHOR_MANIFEST),
        "source_csv_sha256": sha256_file(SOURCE_CSV),
        "formal_contract_sha256": sha256_file(FORMAL_CONTRACT),
    }
    return f"H1A-{sha256_obj(payload)[:20]}"


def runner_guard_path() -> Path:
    return OUT / RUNNER_GUARD_FILENAME


def _pid_exists(pid: object) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def acquire_runner_guard(run_identity: str, branch: str, mode: str, head: str = "") -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    path = runner_guard_path()
    owner = {
        "schema": "LP_GLOBAL_H_H1A_ACTIVE_RUNNER_GUARD_V1",
        "stage": "H1A",
        "run_identity": run_identity,
        "owner_pid": os.getpid(),
        "start_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "worktree": str(ROOT),
        "branch": branch,
        "head": head,
        "mode": mode,
        "manifest_provenance": str(OUT / "run_manifest.json"),
    }
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                existing = read_json(path)
            except Exception as exc:
                raise RuntimeError("HARD_GATE_STALE_H1A_RUNNER_GUARD_UNKNOWN_OWNERSHIP") from exc
            if _pid_exists(existing.get("owner_pid")):
                raise RuntimeError("ACTIVE_H1A_RUNNER_ALREADY_EXISTS")
            known = (
                existing.get("run_identity") == run_identity
                and existing.get("worktree") == str(ROOT)
                and existing.get("branch") == branch
                and existing.get("stage") == "H1A"
            )
            if not known:
                raise RuntimeError("HARD_GATE_STALE_H1A_RUNNER_GUARD_UNKNOWN_OWNERSHIP")
            try:
                path.unlink()
            except FileNotFoundError:
                continue
        else:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(owner, handle, indent=2, sort_keys=True, ensure_ascii=False)
                handle.write("\n")
            return {"path": str(path), **owner}


def release_runner_guard(guard: dict | None) -> None:
    if not guard:
        return
    path = Path(guard["path"])
    try:
        current = read_json(path)
        if current.get("owner_pid") == guard.get("owner_pid") and current.get("run_identity") == guard.get("run_identity"):
            path.unlink(missing_ok=True)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        pass


def readiness_error_verdict(error: object) -> str:
    text = str(error).lower()
    license_error = any(marker in text for marker in ("license", "licence", "checkout"))
    messaging_error = any(marker in text for marker in ("messaging", "message", "appopen", "app open", "handshake", "interop"))
    if license_error and messaging_error:
        return "LICENSE_OR_MESSAGING_UNAVAILABLE"
    if license_error:
        return "LICENSE_UNAVAILABLE"
    if messaging_error:
        return "MESSAGING_HANDSHAKE_FAILURE"
    return "READINESS_PROBE_ERROR"


def run_readiness_probe(open_session, snapshot_fn=None) -> dict:
    if snapshot_fn is None:
        snapshot_fn = solver_isolation_snapshot
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / READINESS_FILENAME
    previous = read_json(path) if path.exists() else {}
    attempt = int(previous.get("license_readiness_probe_attempts", 0)) + 1
    entry = {
        "attempt": attempt,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "solver_entered": False,
        "physics_attempt": False,
        "fsp_created": False,
        "before_snapshot": snapshot_fn(),
    }
    session = None
    try:
        session = open_session()
        entry["verdict"] = "LUMERICAL_READY"
    except Exception as exc:
        entry["verdict"] = readiness_error_verdict(exc)
        entry["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if session is not None:
            try:
                session.close()
                entry["session_closed"] = True
            except Exception as exc:
                entry["session_closed"] = False
                entry["close_error"] = f"{type(exc).__name__}: {exc}"
    entry["after_snapshot"] = snapshot_fn()
    entry["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    attempts = list(previous.get("attempts", []))
    attempts.append(entry)
    payload = {
        "schema": "LP_GLOBAL_H_H1A_LICENSE_READINESS_V1",
        "license_readiness_probe_attempts": attempt,
        "latest_verdict": entry["verdict"],
        "solver_entered": False,
        "physics_attempt": False,
        "fsp_created": False,
        "attempts": attempts,
    }
    atomic_json(path, payload)
    return payload


def lumerical_readiness(runtime) -> dict:
    return run_readiness_probe(lambda: runtime.lumapi.FDTD(hide=getattr(runtime, "hide_gui", True)))


def next_attempt_artifacts(case_dir: Path, case_id: str) -> tuple[str, Path, Path]:
    paths = sorted(case_dir.glob("attempt_provenance*.json"))
    indices = []
    for path in paths:
        match = re.search(r"_attempt_(\d{3})\.json$", path.name)
        indices.append(int(match.group(1)) if match else 1)
    index = max(indices, default=0) + 1
    attempt_id = f"{case_id}_attempt_{index:03d}"
    provenance = case_dir / "attempt_provenance.json" if index == 1 else case_dir / f"attempt_provenance_attempt_{index:03d}.json"
    pre_fsp = case_dir / f"{case_id}_attempt_{index:03d}_pre.fsp"
    return attempt_id, provenance, pre_fsp


def is_global_infrastructure_error(error: object) -> bool:
    text = str(error).lower()
    return any(marker in text for marker in ("appopen", "app open", "messaging", "license", "licence", "lumapi", "interop", "handshake"))


def ordered_case_plan(anchors: list[dict]) -> list[tuple[dict, float, str]]:
    return [(anchor, height, pol) for anchor in anchors for height in NEW_HEIGHTS_NM for pol in POLARIZATIONS]


def schedule_case_results(anchors: list[dict], run_one) -> list[dict]:
    scheduled = []
    for anchor, height, pol in ordered_case_plan(anchors):
        result = run_one(anchor, height, pol)
        scheduled.append({"anchor": anchor, "height_nm": height, "polarization": pol, "result": result})
        if result.get("failure_scope") == "GLOBAL_INFRASTRUCTURE":
            break
    return scheduled


def number(value: object) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def bool_value(value: object) -> bool:
    return str(value).strip().upper() in {"1", "TRUE", "YES", "PASS", "ACCEPTED", "COMPLETE"}


def wrap_deg(value: float) -> float:
    return float(value) % 360.0


def circ_diff(value: float, reference: float) -> float:
    return float((float(value) - float(reference) + 180.0) % 360.0 - 180.0)


def circular_phase_span(values: list[float]) -> dict:
    return H0.circular_phase_span([float(value) for value in values])


def circular_central(values: list[float]) -> float:
    values = [wrap_deg(value) for value in values]
    if not values:
        raise ValueError("circular_central requires values")
    vector = np.mean(np.exp(1j * np.radians(values)))
    if abs(vector) > 1e-12:
        return float(np.degrees(np.angle(vector)) % 360.0)
    return float(min(values, key=lambda candidate: sum(abs(circ_diff(value, candidate)) for value in values)))


def circular_residuals(values: list[float], central: float) -> list[float]:
    return [circ_diff(value, central) for value in values]


def local_sensitivity(phi_by_height: dict[float, float], height_nm: float) -> float | None:
    """Circular finite-difference dphi/dH using the nearest frozen grid points."""
    if height_nm == 400.0:
        left, right = 400.0, 450.0
    elif height_nm == 600.0:
        left, right = 550.0, 600.0
    else:
        left, right = height_nm - 50.0, height_nm + 50.0
    if left not in phi_by_height or right not in phi_by_height:
        return None
    denominator = right - left
    return circ_diff(phi_by_height[right], phi_by_height[left]) / denominator


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def current_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def physical_contract(head: str) -> dict:
    return {"material_contract": MATERIAL_CONTRACT, "period_x_nm": FORMAL_PERIOD_NM, "period_y_nm": FORMAL_PERIOD_NM, "bottom_plane_nm": 0.0, "source_z_nm": FORMAL_SOURCE_Z_NM, "monitor_z_nm": FORMAL_MONITOR_Z_NM, "wavelength_nm": 450.0, "phase_reference": "arg(txx)", "projector": [[1, 0], [0, 0]], "observable": "coordinate_weighted_full_period_complex_G0", "endpoint_convention": "deduplicate_periodic_endpoints_and_reclose_period", "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)", "builder_version": BUILDER_VERSION, "builder_commit": head, "probe_script_sha256": sha256_file(Path(__file__))}


def load_anchors() -> tuple[list[dict], list[dict]]:
    anchors = list(read_json(ANCHOR_MANIFEST).get("anchors", []))
    hashes = [str(anchor["exact_geometry_hash_sha256"]) for anchor in anchors]
    if len(anchors) > 6:
        raise RuntimeError(f"HARD_GATE_ANCHOR_COUNT_GT6:{len(anchors)}")
    if not anchors or len(set(hashes)) != len(hashes):
        raise RuntimeError("HARD_GATE_ANCHOR_MANIFEST_UNIQUE_HASH")
    source_rows = read_csv(SOURCE_CSV)
    by_hash = {}
    for row in source_rows:
        key = str(row.get("exact_geometry_hash_sha256") or row.get("geometry_hash_sha256") or "")
        by_hash.setdefault(key, []).append(row)
    resolved, h500 = [], []
    for anchor in anchors:
        key = str(anchor["exact_geometry_hash_sha256"])
        matches = [row for row in by_hash.get(key, []) if number(row.get("wavelength_nm")) == 450.0]
        if len(matches) != 1:
            raise RuntimeError(f"HARD_GATE_H500_SOURCE_MATCH:{key}:{len(matches)}")
        source = dict(matches[0])
        if not bool_value(source.get("Jones_complete")) or str(source.get("material")) != MATERIAL_CONTRACT:
            raise RuntimeError(f"HARD_GATE_H500_SOURCE_NOT_AUTHORITATIVE:{key}")
        if number(source.get("H_nm")) != 500.0 or number(source.get("period_x_nm")) != FORMAL_PERIOD_NM or number(source.get("period_y_nm")) != FORMAL_PERIOD_NM:
            raise RuntimeError(f"HARD_GATE_H500_CONTRACT:{key}")
        row = dict(source)
        row.update(anchor)
        row.update({"anchor_role": anchor["role"], "authoritative_id": anchor["authoritative_id"], "exact_geometry_hash_sha256": key})
        resolved.append(row)
        h500.append(source)
    return resolved, h500


def planned_cases(anchors: list[dict]) -> list[dict]:
    return [{"authoritative_id": anchor["authoritative_id"], "role": anchor["anchor_role"], "exact_geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height, "polarization": pol} for anchor in anchors for height in NEW_HEIGHTS_NM for pol in POLARIZATIONS]


def case_identity(anchor: dict, height_nm: float, pol: str, head: str) -> dict:
    return {"anchor_authoritative_id": anchor["authoritative_id"], "anchor_role": anchor["anchor_role"], "exact_geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": float(height_nm), "polarization": pol, "material_contract": MATERIAL_CONTRACT, "period_nm": [FORMAL_PERIOD_NM, FORMAL_PERIOD_NM], "builder_version": BUILDER_VERSION, "builder_commit": head, "probe_script_sha256": sha256_file(Path(__file__)), "formal_extraction_convention": EXTRACTION_CONVENTION}


def case_name(identity: dict) -> str:
    return f"H1A_{identity['anchor_authoritative_id']}_{identity['exact_geometry_hash_sha256'][:12]}_H{int(identity['H_global_nm'])}_P{identity['polarization']}"


def solver_isolation_snapshot() -> dict:
    script = r'''$ErrorActionPreference = 'SilentlyContinue'
Get-Process -Name fdtd-engine-msmpi,mpiexec,fdtd-solutions -ErrorAction SilentlyContinue | ForEach-Object {
  $path = ''
  try { $path = $_.Path } catch {}
  "{0}|{1}|{2}|{3}" -f $_.Id,$_.Name,$_.StartTime,$path
}'''
    result = subprocess.run(["powershell", "-NoProfile", "-Command", script], text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
    processes = []
    for line in result.stdout.splitlines():
        if line.strip():
            parts = line.strip().split("|", 3)
            processes.append({"pid": parts[0], "name": parts[1] if len(parts) > 1 else "", "start": parts[2] if len(parts) > 2 else "", "path": parts[3] if len(parts) > 3 else ""})
    active = [item for item in processes if item["name"].lower() in {"fdtd-engine-msmpi", "mpiexec", "fdtd-solutions"}]
    return {"status": "PASS" if not active else "BLOCKED_ACTIVE_FDTD", "command_returncode": result.returncode, "processes": processes, "active_engine_or_mpi": active, "policy": "no kill/suspend/restart; no new solver entries while engine_or_mpiexec is active"}


def read_entered() -> list[dict]:
    path = OUT / "entered_accounting_v1.json"
    return list(read_json(path).get("solver_entries", [])) if path.exists() else []


def write_entered(entries: list[dict]) -> None:
    atomic_json(OUT / "entered_accounting_v1.json", {"schema": "LP_GLOBAL_H_H1A_ENTERED_ACCOUNTING_V1", "solver_entries": entries, "solver_subruns_entered": len(entries), "solver_budget_planned": MAX_NEW_SUBRUNS, "H500_scheduled": False})


def setup_gate(fdtd, row: dict, pol: str, height_nm: float) -> dict:
    base = RUNNER.build_gate(fdtd, row, pol)
    expected = RUNNER.unified_h_geometry_contract(height_nm)
    checks = dict(base.get("checks", {}))
    fields = {"FDTD_z_min": ("FDTD", "z min", 1e9), "FDTD_z_max": ("FDTD", "z max", 1e9), "source_z": ("source", "z", 1e9), "monitor_z": ("field_monitor", "z", 1e9), "T_z": ("T", "z", 1e9), "J1_z_min": ("pillar_1", "z min", 1e9), "J1_z_max": ("pillar_1", "z max", 1e9), "J2_z_min": ("pillar_2", "z min", 1e9), "J2_z_max": ("pillar_2", "z max", 1e9), "FDTD_x_span": ("FDTD", "x span", 1e9), "FDTD_y_span": ("FDTD", "y span", 1e9)}
    for name, (obj, key, scale) in fields.items():
        value = RUNNER.safe_get(fdtd, obj, key)
        checks[name] = value * scale if isinstance(value, (int, float)) else value
    expected_checks = {"FDTD_z_min": expected["fdtd_z_min_nm"], "FDTD_z_max": expected["fdtd_z_max_nm"], "source_z": expected["source_z_nm"], "monitor_z": expected["monitor_z_nm"], "T_z": expected["monitor_z_nm"], "J1_z_min": 0.0, "J2_z_min": 0.0, "J1_z_max": height_nm, "J2_z_max": height_nm, "FDTD_x_span": FORMAL_PERIOD_NM, "FDTD_y_span": FORMAL_PERIOD_NM}
    def close(value: object, target: float) -> bool:
        try:
            return abs(float(value) - target) < 1e-7
        except (TypeError, ValueError):
            return False
    readback_pass = all(close(checks.get(key), target) for key, target in expected_checks.items())
    return {"pass": bool(base.get("pass") and readback_pass), "base_gate": base, "checks": checks, "expected": expected, "readback_pass": readback_pass, "formal_convention": EXTRACTION_CONVENTION}


def checkpoint_result(case_dir: Path, identity: dict) -> dict | None:
    path = case_dir / "checkpoint.json"
    if not path.exists():
        return None
    payload = read_json(path)
    if payload.get("status") != "ACCEPTED" or payload.get("case_identity_sha256") != sha256_obj(identity):
        return None
    return {"status": "ACCEPTED", "solver_entered": True, "case_id": payload["case_id"], "identity": identity, "identity_sha256": payload["case_identity_sha256"], "polarization": identity["polarization"], "H_global_nm": identity["H_global_nm"], "rows": payload["rows"], "grid_audit": payload.get("grid_audit"), "checkpoint_path": str(path), "checkpoint_sha256": sha256_file(path), "recovered_from_checkpoint": True, "geometry_hash_sha256": identity["exact_geometry_hash_sha256"]}


def run_case(runtime, anchor: dict, height_nm: float, pol: str, head: str, contract: dict, entered: list[dict]) -> dict:
    identity = case_identity(anchor, height_nm, pol, head)
    identity_hash = sha256_obj(identity)
    case_id = case_name(identity)
    case_dir = RUNTIME / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    recovered = checkpoint_result(case_dir, identity)
    if recovered:
        return recovered
    if any(entry.get("solver_entered") is True and entry.get("case_identity_sha256") == identity_hash for entry in entered):
        return {"status": "QUARANTINED_ENTERED_NO_RECOVERY", "solver_entered": True, "case_id": case_id, "identity": identity, "identity_sha256": identity_hash, "polarization": pol, "H_global_nm": height_nm, "geometry_hash_sha256": identity["exact_geometry_hash_sha256"], "error": "entered=true exact case has no accepted checkpoint; rerun forbidden"}
    attempt_id, provenance_path, pre_fsp = next_attempt_artifacts(case_dir, case_id)
    record = {"case_id": case_id, "attempt_id": attempt_id, "case_identity": identity, "case_identity_sha256": identity_hash, "status": "PREFLIGHT", "solver_entered": False, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "geometry_hash_sha256": identity["exact_geometry_hash_sha256"], "physical_contract_sha256": sha256_obj(contract), "pre_fsp_path": str(pre_fsp)}
    f = None
    start = time.time()
    try:
        f = runtime.lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        setup = RUNNER.build(f, anchor, pol, height_nm=height_nm)
        f.save(str(pre_fsp))
        record["setup"] = setup
        record["pre_fsp_sha256"] = sha256_file(pre_fsp)
        f.close()
        f = None
        f = runtime.lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        f.load(str(pre_fsp))
        gate = setup_gate(f, anchor, pol, height_nm)
        record["configuration_gate"] = gate
        atomic_json(provenance_path, record)
        if not gate["pass"]:
            record.update({"status": "QUARANTINED_PREFLIGHT_GATE", "error": "configuration gate failed"})
            return record
        record.update({"status": "ENTERED", "solver_entered": True, "entered_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
        entered.append({"case_id": case_id, "attempt_id": record["attempt_id"], "solver_entered": True, "entered_utc": record["entered_utc"], "pre_fsp_sha256": record["pre_fsp_sha256"], "physical_contract_sha256": record["physical_contract_sha256"], "case_identity_sha256": identity_hash, "geometry_hash_sha256": identity["exact_geometry_hash_sha256"], "H_global_nm": height_nm, "polarization": pol})
        if len(entered) > MAX_NEW_SUBRUNS:
            raise RuntimeError("HARD_GATE_SOLVER_BUDGET_EXCEEDED")
        write_entered(entered)
        atomic_json(provenance_path, record)
        f.run()
        rows, grid = RUNNER.extract_broadband(f)
        atomic_json(case_dir / "checkpoint.json", {"schema": "LP_GLOBAL_H_H1A_CHECKPOINT_V1", "status": "ACCEPTED", "case_id": case_id, "case_identity": identity, "case_identity_sha256": identity_hash, "geometry": anchor, "H_global_nm": height_nm, "polarization": pol, "physical_contract": contract, "physical_contract_sha256": sha256_obj(contract), "setup": setup, "configuration_gate": gate, "rows": rows, "grid_audit": grid})
        record.update({"status": "ACCEPTED", "rows": rows, "grid_audit": grid, "checkpoint_path": str(case_dir / "checkpoint.json"), "checkpoint_sha256": sha256_file(case_dir / "checkpoint.json")})
        return record
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(), "retained_data_status": "attempt_and_entered_evidence_preserved", "failure_scope": "GLOBAL_INFRASTRUCTURE" if not record.get("solver_entered") and is_global_infrastructure_error(exc) else "CASE_OR_PHYSICS"})
        return record
    finally:
        if f is not None:
            try:
                f.close()
            except Exception:
                pass
        record["runtime_seconds"] = time.time() - start
        atomic_json(provenance_path, record)


def full_jones_row(anchor: dict, height_nm: float, x: dict, y: dict, source: str) -> dict:
    def c(row: dict, real: str, imag: str) -> complex:
        return complex(float(row[real]), float(row[imag]))
    J = np.array([[c(x["rows"][0], "weighted_Ex_real", "weighted_Ex_imag"), c(y["rows"][0], "weighted_Ex_real", "weighted_Ex_imag")], [c(x["rows"][0], "weighted_Ey_real", "weighted_Ey_imag"), c(y["rows"][0], "weighted_Ey_real", "weighted_Ey_imag")]])
    return {"authoritative_id": anchor["authoritative_id"], "anchor_role": anchor["anchor_role"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height_nm, "wavelength_nm": 450.0, "source": source, "physics_scope": "FULL_JONES_H1A_PHYSICS", "Jones_complete": True, **RUNNER.metrics(J), "x_case_id": x.get("case_id"), "y_case_id": y.get("case_id"), "x_checkpoint_sha256": x.get("checkpoint_sha256"), "y_checkpoint_sha256": y.get("checkpoint_sha256")}


def phase_only_row(anchor: dict, height_nm: float, x: dict, source: str) -> dict:
    row = x["rows"][0]
    txx = complex(float(row["weighted_Ex_real"]), float(row["weighted_Ex_imag"]))
    return {"authoritative_id": anchor["authoritative_id"], "anchor_role": anchor["anchor_role"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height_nm, "wavelength_nm": 450.0, "source": source, "physics_scope": "PHASE_ONLY_H1A_PHYSICS", "Jones_complete": False, "txx_real": txx.real, "txx_imag": txx.imag, "phase_wrapped_deg": float(np.degrees(np.angle(txx)) % 360.0), "Txx": abs(txx) ** 2, "selected_throughput_Txx": abs(txx) ** 2, "projector_eligible": False, "case_id": x.get("case_id"), "checkpoint_sha256": x.get("checkpoint_sha256")}


def h500_rows(anchor: dict, source: dict) -> tuple[dict, dict]:
    full = dict(source)
    full.update({"authoritative_id": anchor["authoritative_id"], "anchor_role": anchor["anchor_role"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": 500.0, "source": "H0_AUTHORITATIVE_ACCEPTED_PHYSICS", "physics_scope": "FULL_JONES_H1A_PHYSICS", "Jones_complete": True, "projector_eligible": True})
    phase = {"authoritative_id": anchor["authoritative_id"], "anchor_role": anchor["anchor_role"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": 500.0, "wavelength_nm": 450.0, "source": "H0_AUTHORITATIVE_ACCEPTED_PHYSICS", "physics_scope": "PHASE_ONLY_H1A_PHYSICS", "Jones_complete": False, "txx_real": source.get("txx_real"), "txx_imag": source.get("txx_imag"), "phase_wrapped_deg": source.get("phase_wrapped_deg"), "Txx": source.get("Txx"), "selected_throughput_Txx": source.get("Txx"), "projector_eligible": False}
    return full, phase


def make_tables(anchors: list[dict], h500_source: list[dict], results: dict[tuple[str, float, str], dict]) -> tuple[list[dict], list[dict], list[dict]]:
    full, phase = [], []
    for anchor, source in zip(anchors, h500_source):
        f500, p500 = h500_rows(anchor, source)
        full.append(f500)
        phase.append(p500)
        for height in NEW_HEIGHTS_NM:
            x = results[(anchor["exact_geometry_hash_sha256"], height, "x")]
            y = results[(anchor["exact_geometry_hash_sha256"], height, "y")]
            if x.get("status") == "ACCEPTED":
                phase.append(phase_only_row(anchor, height, x, "H1A_NEW_SOLVER_X_FORMAL"))
            if x.get("status") == "ACCEPTED" and y.get("status") == "ACCEPTED":
                full.append(full_jones_row(anchor, height, x, y, "H1A_NEW_SOLVER_XY_FORMAL"))
    phi = []
    for anchor in anchors:
        rows = {float(row["H_global_nm"]): row for row in phase if row["geometry_hash_sha256"] == anchor["exact_geometry_hash_sha256"]}
        phi500 = float(rows[500.0]["phase_wrapped_deg"])
        phi_by_height = {height: float(row["phase_wrapped_deg"]) for height, row in rows.items() if row.get("phase_wrapped_deg") is not None}
        for height in ALL_HEIGHTS_NM:
            row = rows.get(height)
            value = float(row["phase_wrapped_deg"]) if row else None
            delta = circ_diff(value, phi500) if value is not None else None
            phi.append({"authoritative_id": anchor["authoritative_id"], "anchor_role": anchor["anchor_role"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height, "phi_arg_txx_deg": value, "phi_H500_deg": phi500, "delta_phi_vs_H500_deg": delta, "delta_magnitude_deg": abs(delta) if delta is not None else None, "local_circular_sensitivity_deg_per_nm": local_sensitivity(phi_by_height, height), "selected_throughput_Txx": row.get("selected_throughput_Txx") if row else None, "projector_error_apcd_v1": row.get("projection_error_apcd_v1") if row else None, "physics_scope": row.get("physics_scope") if row else "MISSING"})
    return full, phase, phi


def interaction_tables(phi: list[dict], full: list[dict], anchor_count: int) -> tuple[list[dict], list[dict]]:
    interactions, spans = [], []
    for height in ALL_HEIGHTS_NM:
        values = [row for row in phi if float(row["H_global_nm"]) == height and row.get("delta_phi_vs_H500_deg") is not None]
        deltas = [float(row["delta_phi_vs_H500_deg"]) for row in values]
        central = circular_central(deltas) if deltas else None
        residuals = circular_residuals(deltas, central) if deltas and central is not None else []
        interactions.append({"H_global_nm": height, "anchor_count": len(values), "common_shift_C_deg": central, "rms_residual_deg": float(math.sqrt(sum(value * value for value in residuals) / len(residuals))) if residuals else None, "max_abs_residual_deg": max((abs(value) for value in residuals), default=None), "anchor_residuals_deg": {row["authoritative_id"]: residual for row, residual in zip(values, residuals)}, "delta_definition": "circ_diff(phi_i(H),phi_i(500))", "residual_definition": "circ_diff(delta_i(H),C(H))"})
        fixed = [row for row in full if float(row["H_global_nm"]) == height and bool_value(row.get("Jones_complete"))]
        all_span = circular_phase_span([float(row["phase_wrapped_deg"]) for row in fixed]) if fixed else {"circular_coverage_deg": 0.0}
        ranked = sorted(fixed, key=lambda row: float(row["projection_error_apcd_v1"]))
        compatible = ranked[: max(1, math.ceil(len(ranked) * 0.5))] if ranked else []
        compatible_span = circular_phase_span([float(row["phase_wrapped_deg"]) for row in compatible]) if compatible else {"circular_coverage_deg": 0.0}
        separations = [abs(circ_diff(float(left["phase_wrapped_deg"]), float(right["phase_wrapped_deg"]))) for index, left in enumerate(compatible) for right in compatible[index + 1:]]
        spans.append({"H_global_nm": height, "full_jones_count": len(fixed), "phase_only_count": sum(float(row["H_global_nm"]) == height for row in phi), "anchor_phase_span_deg": all_span.get("circular_coverage_deg", 0.0), "projector_compatible_semantics": "best_50_percent_by_projector_error_among_this_H1A_anchor_slice; no new absolute threshold", "projector_compatible_count": len(compatible), "projector_compatible_phase_span_deg": compatible_span.get("circular_coverage_deg", 0.0), "projector_compatible_anchor_ids": [row["authoritative_id"] for row in compatible], "projector_compatible_pair_separations_deg": separations, "throughput_selected_channel_Txx_mean": float(np.mean([float(row["Txx"]) for row in fixed])) if fixed else None})
    return interactions, spans


def decide_verdict(interactions: list[dict], spans: list[dict], anchor_count: int) -> tuple[str, dict]:
    if any(row["full_jones_count"] < anchor_count for row in spans):
        return "H1A_INCONCLUSIVE", {"reason": "complete symmetric grid is missing full-Jones pairs", "rule": "all six anchors must be complete at every H"}
    expansion = any(row["H_global_nm"] != 500.0 and row["projector_compatible_phase_span_deg"] > H500_DEDICATED_REFERENCE_DEG for row in spans)
    residual_max = max((float(row["max_abs_residual_deg"]) for row in interactions if row["max_abs_residual_deg"] is not None), default=0.0)
    if expansion and residual_max >= 15.0:
        return "H1A_GEOMETRY_DEPENDENT_H_RESPONSE_OBSERVED", {"rule": "complete grid + projector-compatible span above H500 dedicated reference + max residual >= 15 deg", "max_abs_residual_deg": residual_max, "span_expansion": True}
    if not expansion and residual_max < 15.0:
        return "H1A_COMMON_TRANSLATION_DOMINATED", {"rule": "complete grid + no projector-compatible span above H500 dedicated reference + max residual < 15 deg", "max_abs_residual_deg": residual_max, "span_expansion": False}
    return "H1A_INCONCLUSIVE", {"rule": "conservative joint interpretation did not separate translation from interaction", "max_abs_residual_deg": residual_max, "span_expansion": expansion}


def write_outputs(manifest: dict, full: list[dict], phase: list[dict], phi: list[dict], spans: list[dict], interactions: list[dict], quarantine: list[dict], verdict: str, detail: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "complete_jones_table.csv", full)
    write_csv(OUT / "phase_only_table.csv", phase)
    write_csv(OUT / "per_anchor_phi_vs_H.csv", phi)
    write_csv(OUT / "fixed_H_span_summary.csv", spans)
    write_csv(OUT / "H_geometry_interaction_summary.csv", interactions)
    write_csv(OUT / "quarantine_rejection_table.csv", quarantine)
    flags = {"FLAG_60_SECTOR": any(max(row.get("projector_compatible_pair_separations_deg", [0.0])) >= 60.0 for row in spans), "FLAG_120_ML_RESTART": any(float(row.get("projector_compatible_phase_span_deg", 0.0)) >= 120.0 for row in spans)}
    manifest.update({"status": "COMPLETE_ANALYSIS", "verdict": verdict, "verdict_detail": detail, "flags": flags, "projector_collapse_observed": any(row["full_jones_count"] < manifest["unique_anchor_count"] for row in spans), "artifacts": {name: str((OUT / filename).relative_to(ROOT)) for name, filename in {"complete_jones_table": "complete_jones_table.csv", "phase_only_table": "phase_only_table.csv", "per_anchor_phi_vs_H": "per_anchor_phi_vs_H.csv", "fixed_H_span_summary": "fixed_H_span_summary.csv", "H_geometry_interaction_summary": "H_geometry_interaction_summary.csv", "quarantine_rejection_table": "quarantine_rejection_table.csv"}.items()}})
    atomic_json(OUT / "final_audit.json", manifest)
    lines = ["# Stage H1A — Repeated-Anchor Global-H Sensitivity Probe", "", f"- Status: `{manifest['status']}`", f"- Verdict: `{verdict}`", f"- Branch / HEAD: `{manifest['branch']}` / `{manifest['head']}`", f"- Unique anchors: `{manifest['unique_anchor_count']}`", f"- Solver budget planned / entered / accepted / quarantined: `{manifest['solver_budget_planned']}` / `{manifest['solver_subruns_entered']}` / `{manifest['solver_subruns_accepted']}` / `{manifest['solver_subruns_quarantined']}`", "", "## Frozen contract", "", "- H grid: `400, 450, 500, 550, 600 nm`; only 400/450/550/600 were scheduled.", "- H500 reuses H0 authoritative data and is never rerun.", "- J1_H = J2_H = H_global; bottom z=0 nm; source z=-250 nm; monitor z=1000 nm; period=432 nm; material=APCD_TIO2_NATIVE_M1.", "", "## Fixed-H summary", ""]
    lines += [f"- H={row['H_global_nm']:.0f} nm: full-Jones={row['full_jones_count']}, phase-only={row['phase_only_count']}, all-anchor span={row['anchor_phase_span_deg']:.6f} deg, projector-compatible span={row['projector_compatible_phase_span_deg']:.6f} deg" for row in spans]
    lines += ["", "## Common-translation residuals", ""]
    lines += [f"- H={row['H_global_nm']:.0f} nm: C(H)={row['common_shift_C_deg']}, RMS={row['rms_residual_deg']}, max|r|={row['max_abs_residual_deg']}" for row in interactions]
    lines += ["", "## Flags", "", f"- FLAG_60_SECTOR: `{flags['FLAG_60_SECTOR']}`", f"- FLAG_120_ML_RESTART: `{flags['FLAG_120_ML_RESTART']}`; not an automatic ML start.", f"- Projector collapse observed: `{manifest['projector_collapse_observed']}`", "", "## Scope-separated references", "", f"- H500 dedicated-probe reference: `{H500_DEDICATED_REFERENCE_DEG}` deg.", f"- H500 historical quantile/reference slice: `{H500_HISTORICAL_QUANTILE_REFERENCE_DEG}` deg.", "", "## Artifacts", ""]
    lines += [f"- {key}: `{value}`" for key, value in manifest["artifacts"].items()]
    (REPORT / "stage_h1a_global_h_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    atomic_json(REPORT / "stage_h1a_global_h_final.json", manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--readiness-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if sum(bool(value) for value in (args.preflight_only, args.readiness_only, args.execute)) != 1:
        raise SystemExit("select exactly one mode")
    anchors, h500_source = load_anchors()
    head = current_head()
    branch = current_branch()
    run_identity = h1a_run_identity(branch)
    contract = physical_contract(head)
    planned = planned_cases(anchors)
    if len(planned) > MAX_NEW_SUBRUNS:
        raise SystemExit("HARD_GATE_PLANNED_BUDGET")
    snapshot = solver_isolation_snapshot()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "LP_GLOBAL_H_H1A_RUN_MANIFEST_V1", "stage": "H1A", "branch": branch, "head": head, "run_identity": run_identity, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "H_grid_nm": list(ALL_HEIGHTS_NM), "new_solver_heights_nm": list(NEW_HEIGHTS_NM), "H500_scheduled": False, "unique_anchor_count": len(anchors), "anchor_ids": [anchor["authoritative_id"] for anchor in anchors], "anchor_exact_hashes": [anchor["exact_geometry_hash_sha256"] for anchor in anchors], "solver_budget_planned": MAX_NEW_SUBRUNS, "solver_subruns_entered": len(read_entered()), "solver_isolation_snapshot": snapshot, "physical_contract": contract, "physical_contract_sha256": sha256_obj(contract), "source_csv": str(SOURCE_CSV.relative_to(ROOT)), "source_csv_sha256": sha256_file(SOURCE_CSV), "formal_contract": str(FORMAL_CONTRACT.relative_to(ROOT)), "formal_contract_sha256": sha256_file(FORMAL_CONTRACT), "planned_case_count": len(planned), "planned_cases": planned}
    atomic_json(OUT / "run_manifest.json", manifest)
    if args.preflight_only:
        manifest["status"] = "READY" if snapshot["status"] == "PASS" else snapshot["status"]
        atomic_json(OUT / "run_manifest.json", manifest)
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0 if snapshot["status"] == "PASS" else 2
    if snapshot["status"] != "PASS":
        manifest["status"] = snapshot["status"]
        atomic_json(OUT / "run_manifest.json", manifest)
        raise SystemExit("HARD_GATE_ACTIVE_SOLVER")

    mode = "readiness-only" if args.readiness_only else "execute"
    guard = acquire_runner_guard(run_identity, branch, mode, head)
    atexit.register(release_runner_guard, guard)
    runtime_config = RUNNER.load_runtime_config(str(ROOT / "configs" / "runtime.yaml"))
    lumapi = RUNNER.import_lumapi(runtime_config)
    runtime = type("RuntimeProxy", (), {"lumapi": lumapi, "hide_gui": getattr(runtime_config, "hide_gui", True)})()
    readiness = lumerical_readiness(runtime)
    manifest.update({"readiness_verdict": readiness["latest_verdict"], "license_readiness_probe_attempts": readiness["license_readiness_probe_attempts"]})
    if args.readiness_only:
        manifest["status"] = readiness["latest_verdict"]
        atomic_json(OUT / "run_manifest.json", manifest)
        print(json.dumps({"status": manifest["status"], "license_readiness_probe_attempts": readiness["license_readiness_probe_attempts"]}, indent=2))
        release_runner_guard(guard)
        return 0 if readiness["latest_verdict"] == "LUMERICAL_READY" else 2
    if readiness["latest_verdict"] != "LUMERICAL_READY":
        manifest["status"] = "H1A_RUNTIME_HARDENED_WAITING_LICENSE_OR_MESSAGING"
        atomic_json(OUT / "run_manifest.json", manifest)
        print(json.dumps({"status": manifest["status"], "readiness_verdict": readiness["latest_verdict"], "license_readiness_probe_attempts": readiness["license_readiness_probe_attempts"]}, indent=2))
        release_runner_guard(guard)
        return 2

    entered = read_entered()
    if len(entered) > MAX_NEW_SUBRUNS:
        raise SystemExit("HARD_GATE_ENTERED_BUDGET")
    results, quarantine = {}, []
    scheduled = schedule_case_results(anchors, lambda anchor, height, pol: run_case(runtime, anchor, height, pol, head, contract, entered))
    for item in scheduled:
        anchor = item["anchor"]
        height = item["height_nm"]
        pol = item["polarization"]
        result = item["result"]
        results[(anchor["exact_geometry_hash_sha256"], height, pol)] = result
        if result.get("status") != "ACCEPTED":
            quarantine.append({"case_id": result.get("case_id"), "authoritative_id": anchor["authoritative_id"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height, "polarization": pol, "status": result.get("status"), "solver_entered": result.get("solver_entered", False), "error": result.get("error", ""), "failure_scope": result.get("failure_scope")})
    global_failures = [item["result"] for item in scheduled if item["result"].get("failure_scope") == "GLOBAL_INFRASTRUCTURE"]
    if global_failures:
        manifest.update({"status": "H1A_RUNTIME_INFRASTRUCTURE_FAIL_FAST", "solver_subruns_entered": len(entered), "solver_subruns_accepted": 0, "solver_subruns_quarantined": len(quarantine), "fail_fast_case_id": global_failures[0].get("case_id"), "fail_fast_error": global_failures[0].get("error")})
        atomic_json(OUT / "run_manifest.json", manifest)
        print(json.dumps({"status": manifest["status"], "case_id": manifest["fail_fast_case_id"], "solver_subruns_entered": len(entered)}, indent=2))
        release_runner_guard(guard)
        return 2

    full, phase, phi = make_tables(anchors, h500_source, results)
    interactions, spans = interaction_tables(phi, full, len(anchors))
    verdict, detail = decide_verdict(interactions, spans, len(anchors))
    accepted = sum(result.get("status") == "ACCEPTED" for result in results.values())
    manifest.update({"solver_subruns_entered": len(entered), "solver_subruns_accepted": accepted, "solver_subruns_quarantined": len(quarantine), "solver_subruns_failed_recoverable": sum(item.get("solver_entered") is True for item in quarantine), "phase_only_rows": len(phase), "full_jones_rows": len(full)})
    write_outputs(manifest, full, phase, phi, spans, interactions, quarantine, verdict, detail)
    atomic_json(OUT / "run_manifest.json", manifest)
    print(json.dumps({"verdict": verdict, "solver_subruns_entered": len(entered), "solver_subruns_accepted": accepted, "solver_subruns_quarantined": len(quarantine), "flags": manifest.get("flags")}, indent=2))
    release_runner_guard(guard)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
