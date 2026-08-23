from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any


ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
AUTH = ROOT / "paper_a_broadband/authority"
REPORT = ROOT / "paper_a_broadband/reports/lp_anisotropy_balanced_conditional_truth_v1"
INITIAL_REPORT = ROOT / "paper_a_broadband/reports/lp_anisotropy_balanced_truth_v1"
RUNTIME = ROOT / "paper_a_broadband/runtime/search_anisotropy_balanced_truth_v1"
SELECTION_REPORT = ROOT / "paper_a_broadband/reports/lp_anisotropy_feasible_space_v2_balanced_selection"
INITIAL_RUNNER = ROOT / "paper_a_broadband/scripts/lp_anisotropy_balanced_truth_runner_v1.py"
SELECTION_SCRIPT = ROOT / "paper_a_broadband/scripts/lp_anisotropy_balanced_selection_v2.py"
INITIAL = ["BF01", "BF02", "BF03", "BF04"]
CONDITIONAL = ["BF05", "BF06", "BF07", "BF08"]
ALL = INITIAL + CONDITIONAL
CONDITIONAL_CASES = [f"{gid}_{pol}" for gid in CONDITIONAL for pol in ("x", "y")]
TASK_ID = "PAPER_A_LP_ANISOTROPY_BALANCED_CONDITIONAL_TRUTH_V1"
INITIAL_ENTERED = 8
CONDITIONAL_BUDGET = 8
TOTAL_STAGE_BUDGET = 16
MAX_ACTIVE = 2
MONITOR_INTERVAL_S = 600.0

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INIT = load_module(INITIAL_RUNNER, "balanced_initial_truth_for_conditional")
SEL = load_module(SELECTION_SCRIPT, "balanced_selection_for_conditional")
INIT.REPORT = REPORT
INIT.TASK_ID = TASK_ID
INIT.MAX_PHYSICS_JOBS = TOTAL_STAGE_BUDGET
INIT.BASE.REPORT = REPORT
INIT.BASE.TASK_ID = TASK_ID
INIT.BASE.PREV.REPORT = REPORT
INIT.BASE.PREV.TASK_ID = TASK_ID


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sha_obj(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["status"])
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)


def selected() -> dict[str, dict[str, Any]]:
    rows = INIT.selected_rows()
    return {row["geometry_id"]: row for row in rows}


def initial_summaries() -> list[dict[str, Any]]:
    output = []
    for gid in INITIAL:
        path = INITIAL_REPORT / f"{gid}_metrics.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        output.append(data["summary"])
    return output


def directional_rows(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in summaries
        if row.get("MDC_weighted", {}).get("DoLP", 0.0) >= 0.40
        or row.get("MDC_FWHM_psi_span_deg", 999.0) <= 45.0
    ]


def authorize() -> dict[str, Any]:
    REPORT.mkdir(parents=True, exist_ok=True)
    summaries = initial_summaries()
    final = [row for row in summaries if row.get("final_pass")]
    promising = [row for row in summaries if row.get("promising")]
    directional = directional_rows(summaries)
    if not directional:
        raise RuntimeError("HARD_GATE_NO_PREREGISTERED_DIRECTIONAL_TREND")
    old_midpoint = INITIAL_REPORT / "midpoint_physics_audit.json"
    old_midpoint_data = json.loads(old_midpoint.read_text(encoding="utf-8"))
    override = {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_MIDPOINT_AUTHORITY_OVERRIDE_V1",
        "timestamp_utc": now(),
        "status": "PASS",
        "supersedes_admission_rule_only": old_midpoint_data.get("conditional_admission_rule"),
        "preserves_initial_physics": True,
        "initial_midpoint_artifact": str(old_midpoint),
        "initial_midpoint_sha256": sha_file(old_midpoint),
        "revised_conditional_admission_rule": "final_pass_count > 0 or promising_count > 0 or directional_diagnostic_count > 0",
        "final_pass_count": len(final),
        "promising_count": len(promising),
        "directional_diagnostic_count": len(directional),
        "directional_geometry_ids": [row["geometry_id"] for row in directional],
        "BF04_evidence": {
            "MDC_weighted_DoLP": next(row for row in summaries if row["geometry_id"] == "BF04")["MDC_weighted"]["DoLP"],
            "MDC_FWHM_psi_span_deg": next(row for row in summaries if row["geometry_id"] == "BF04")["MDC_FWHM_psi_span_deg"],
        },
        "conditional_batch_eligible": True,
        "conditional_batch_authorized": True,
        "authorization": "USER_EXPLICIT_MIDPOINT_AUTHORITY_MODIFICATION_AND_SOLVER_CONTINUATION_2026_08_23",
        "authorized_geometry_ids": CONDITIONAL,
        "authorized_case_ids": CONDITIONAL_CASES,
        "conditional_physics_job_budget": CONDITIONAL_BUDGET,
        "total_stage_physics_job_budget": TOTAL_STAGE_BUDGET,
        "paper_a_max_active_fdtd": MAX_ACTIVE,
        "entered_true_no_auto_replay": True,
        "no_new_geometry": True,
        "no_rcwa": True,
        "no_ml": True,
    }
    write_json(AUTH / "paper_a_lp_anisotropy_balanced_midpoint_override_v1.json", override)
    write_json(REPORT / "midpoint_authority_override.json", override)
    md = [
        "# Paper A LP balanced midpoint authority override v1",
        "",
        "Status: `PASS`",
        "",
        "The initial BF01-BF04 optical evidence is unchanged. Only the conditional-admission rule is superseded.",
        "",
        "Revised rule: final pass, promising, or a preregistered directional diagnostic may authorize BF05-BF08.",
        "",
        f"BF04 provides the directional diagnostic: MDC-weighted DoLP={override['BF04_evidence']['MDC_weighted_DoLP']:.6f}; MDC-FWHM psi span={override['BF04_evidence']['MDC_FWHM_psi_span_deg']:.3f} deg.",
        "",
        "Conditional truth authority: BF05-BF08 x/y, maximum 8 additional FDTD jobs, maximum active Paper A FDTD=2.",
        "",
    ]
    (AUTH / "paper_a_lp_anisotropy_balanced_midpoint_override_v1.md").write_text("\n".join(md), encoding="utf-8")

    truth_path = AUTH / "paper_a_lp_anisotropy_balanced_initial_truth_v1.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth.update(
        {
            "status": "CONDITIONAL_TRUTH_BATCH_AUTHORIZED_PENDING_SETUP_ONLY_GATE",
            "conditional_batch_authorized": True,
            "conditional_batch_eligible": True,
            "conditional_authorized_case_ids": CONDITIONAL_CASES,
            "maximum_initial_physics_jobs": INITIAL_ENTERED,
            "maximum_conditional_physics_jobs": CONDITIONAL_BUDGET,
            "maximum_total_stage_physics_jobs": TOTAL_STAGE_BUDGET,
            "remaining_authorized_solver_budget": CONDITIONAL_BUDGET,
            "midpoint_authority_override": str(AUTH / "paper_a_lp_anisotropy_balanced_midpoint_override_v1.json"),
            "next_authority": "CONDITIONAL_TRUTH_BATCH_READY_AFTER_SETUP_ONLY_AND_RESOURCE_GATE",
        }
    )
    write_json(truth_path, truth)
    (AUTH / "paper_a_lp_anisotropy_balanced_initial_truth_v1.md").write_text(
        "# Paper A LP anisotropy balanced truth authority\n\n"
        "Status: `CONDITIONAL_TRUTH_BATCH_AUTHORIZED_PENDING_SETUP_ONLY_GATE`\n\n"
        "BF01-BF04 completed 8/8 x/y FDTD jobs. The midpoint admission rule is superseded by "
        "`paper_a_lp_anisotropy_balanced_midpoint_override_v1.json`. BF05-BF08 are authorized for at most "
        "8 additional x/y FDTD jobs, with at most two concurrent Paper A jobs and entered=true meaning no replay.\n",
        encoding="utf-8",
    )

    selection_path = AUTH / "paper_a_lp_anisotropy_balanced_selection_v2.json"
    selection_auth = json.loads(selection_path.read_text(encoding="utf-8"))
    selection_auth.update(
        {
            "solver_authority": "CONDITIONAL_TRUTH_BATCH_USER_AUTHORIZED_2026_08_23",
            "maximum_initial_physics_jobs": INITIAL_ENTERED,
            "maximum_conditional_physics_jobs": CONDITIONAL_BUDGET,
            "maximum_total_stage_physics_jobs": TOTAL_STAGE_BUDGET,
            "authorized_case_ids": [f"{gid}_{pol}" for gid in ALL for pol in ("x", "y")],
            "conditional_batch_authorized": True,
            "conditional_batch_eligible": True,
            "midpoint_override": str(AUTH / "paper_a_lp_anisotropy_balanced_midpoint_override_v1.json"),
            "remaining_authorized_solver_budget": CONDITIONAL_BUDGET,
        }
    )
    write_json(selection_path, selection_auth)

    scope_path = AUTH / "paper_a_lp_cp_broadband_scope_v1.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    scope.update(
        {
            "candidate_selection": "BALANCED_MECHANISM_STRATIFIED_SELECTION_PASS",
            "scientific_readiness": "CONDITIONAL_TRUTH_CANDIDATES_BF05_BF08_AUTHORIZED",
            "truth_plan": "BF01_BF04_COMPLETE_THEN_BF05_BF08_CONDITIONAL_TRUTH",
            "conditional_plan": "BF05_BF08_AUTHORIZED_BY_DIRECTIONAL_MIDPOINT_OVERRIDE",
            "solver_state": "WAIT_SETUP_ONLY_AND_RESOURCE_GATE",
            "midpoint_authority_override": str(AUTH / "paper_a_lp_anisotropy_balanced_midpoint_override_v1.json"),
        }
    )
    write_json(scope_path, scope)
    return override


def expected_readback(g: dict[str, Any], pol: str) -> dict[str, Any]:
    return {
        "source_start_nm": SEL.SOURCE_START,
        "source_stop_nm": SEL.SOURCE_STOP,
        "source_polarization_angle_deg": 0.0 if pol == "x" else 90.0,
        "T_frequency_points": 41.0,
        "field_frequency_points": 41.0,
        "materials": [SEL.MATERIAL, SEL.MATERIAL],
        "j1_center_x_nm": g["j1_center_x_nm"],
        "j1_center_y_nm": g["j1_center_y_nm"],
        "j1_x_span_nm": g["L1_nm"],
        "j1_y_span_nm": g["W1_nm"],
        "j2_center_x_nm": g["j2_center_x_nm"],
        "j2_center_y_nm": g["j2_center_y_nm"],
        "j2_x_span_nm": g["L2_nm"],
        "j2_y_span_nm": g["W2_nm"],
        "j1_rotation_deg": g["theta1_deg"],
        "j2_rotation_deg": g["theta2_deg"],
    }


def readback(f) -> dict[str, Any]:
    return {
        "source_start_nm": float(f.getnamed("source", "wavelength start")) * 1e9,
        "source_stop_nm": float(f.getnamed("source", "wavelength stop")) * 1e9,
        "source_polarization_angle_deg": float(f.getnamed("source", "polarization angle")),
        "T_frequency_points": float(f.getnamed("T", "frequency points")),
        "field_frequency_points": float(f.getnamed("field_monitor", "frequency points")),
        "materials": [str(f.getnamed("pillar_1", "material")), str(f.getnamed("pillar_2", "material"))],
        "j1_center_x_nm": float(f.getnamed("pillar_1", "x")) * 1e9,
        "j1_center_y_nm": float(f.getnamed("pillar_1", "y")) * 1e9,
        "j1_x_span_nm": float(f.getnamed("pillar_1", "x span")) * 1e9,
        "j1_y_span_nm": float(f.getnamed("pillar_1", "y span")) * 1e9,
        "j2_center_x_nm": float(f.getnamed("pillar_2", "x")) * 1e9,
        "j2_center_y_nm": float(f.getnamed("pillar_2", "y")) * 1e9,
        "j2_x_span_nm": float(f.getnamed("pillar_2", "x span")) * 1e9,
        "j2_y_span_nm": float(f.getnamed("pillar_2", "y span")) * 1e9,
        "j1_rotation_deg": float(f.getnamed("pillar_1", "rotation 1")),
        "j2_rotation_deg": float(f.getnamed("pillar_2", "rotation 1")),
    }


def readback_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, expected_value in expected.items():
        actual_value = actual[key]
        if isinstance(expected_value, list):
            if actual_value != expected_value:
                return False
        elif abs(float(actual_value) - float(expected_value)) >= 1e-6:
            return False
    return True


def prepare() -> dict[str, Any]:
    import lumapi

    REPORT.mkdir(parents=True, exist_ok=True)
    geometries = selected()
    results = []
    parent_hash = sha_file(SEL.PARENT_FSP)
    for gid in CONDITIONAL:
        g = geometries[gid]
        for pol in ("x", "y"):
            case_id = f"{gid}_{pol}"
            out = RUNTIME / "cases" / case_id
            out.mkdir(parents=True, exist_ok=True)
            state_path = out / "state.json"
            if state_path.exists() and json.loads(state_path.read_text(encoding="utf-8")).get("solver_entered"):
                raise RuntimeError(f"HARD_GATE_ENTERED_CASE_SETUP_MUTATION:{case_id}")
            pre = out / f"{case_id}_pre.fsp"
            setup_path = out / "setup_only.json"
            expected = expected_readback(g, pol)
            existing = json.loads(setup_path.read_text(encoding="utf-8")) if setup_path.exists() else None
            if existing and existing.get("status") == "PASS" and pre.exists() and existing.get("pre_fsp_sha256") == sha_file(pre):
                results.append(existing)
                continue
            f = lumapi.FDTD(hide=True)
            try:
                f.load(str(SEL.PARENT_FSP))
                f.switchtolayout()
                nm = 1e-9
                objects = [
                    ("pillar_1", g["j1_center_x_nm"], g["j1_center_y_nm"], g["L1_nm"], g["W1_nm"], g["theta1_deg"]),
                    ("pillar_2", g["j2_center_x_nm"], g["j2_center_y_nm"], g["L2_nm"], g["W2_nm"], g["theta2_deg"]),
                ]
                for obj, cx, cy, length, width, rotation in objects:
                    for key, value in (("x", cx), ("y", cy), ("x span", length), ("y span", width), ("z", SEL.H / 2), ("z span", SEL.H)):
                        f.setnamed(obj, key, float(value) * nm)
                    f.setnamed(obj, "rotation 1", float(rotation))
                    f.setnamed(obj, "material", SEL.MATERIAL)
                f.setnamed("source", "polarization angle", 0.0 if pol == "x" else 90.0)
                f.setnamed("source", "wavelength start", SEL.SOURCE_START * nm)
                f.setnamed("source", "wavelength stop", SEL.SOURCE_STOP * nm)
                for name in ("T", "field_monitor"):
                    f.setnamed(name, "use source limits", True)
                    f.setnamed(name, "use wavelength spacing", True)
                    f.setnamed(name, "frequency points", 41)
                f.setglobalmonitor("use source limits", True)
                f.setglobalmonitor("use wavelength spacing", True)
                f.setglobalmonitor("frequency points", 41)
                f.save(str(pre))
            finally:
                try:
                    f.close()
                except Exception:
                    pass
            f = lumapi.FDTD(hide=True)
            try:
                f.load(str(pre))
                actual = readback(f)
            finally:
                try:
                    f.close()
                except Exception:
                    pass
            result = {
                "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_CONDITIONAL_SETUP_ONLY_V1",
                "case_id": case_id,
                "geometry_id": gid,
                "polarization": pol,
                "status": "PASS" if readback_matches(actual, expected) else "HARD_GATE",
                "solver_run_called": False,
                "solver_entered": False,
                "pre_fsp_path": str(pre),
                "pre_fsp_sha256": sha_file(pre),
                "parent_fsp_sha256": parent_hash,
                "geometry_hash": g["geometry_hash_sha256"],
                "readback": actual,
                "expected": expected,
                "mesh_boundary_unchanged": True,
                "normalization_renormalized": False,
            }
            write_json(setup_path, result)
            results.append(result)
    output = {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_CONDITIONAL_PREPARED_FSP_PROVENANCE_V1",
        "timestamp_utc": now(),
        "status": "PASS" if len(results) == CONDITIONAL_BUDGET and all(row["status"] == "PASS" for row in results) else "HARD_GATE",
        "cases": results,
        "solver_run_called": False,
        "solver_entered": 0,
    }
    write_json(REPORT / "conditional_prepared_fsp_provenance.json", output)
    return output


def case_state(case_id: str) -> dict[str, Any] | None:
    path = RUNTIME / "cases" / case_id / "state.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def preflight() -> dict[str, Any]:
    override_path = AUTH / "paper_a_lp_anisotropy_balanced_midpoint_override_v1.json"
    prepared_path = REPORT / "conditional_prepared_fsp_provenance.json"
    override = json.loads(override_path.read_text(encoding="utf-8"))
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    initial_checkpoints = [RUNTIME / "cases" / f"{gid}_{pol}" / "checkpoint.json" for gid in INITIAL for pol in ("x", "y")]
    initial_ok = all(path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ACCEPTED" for path in initial_checkpoints)
    conditional_states = {case_id: case_state(case_id) for case_id in CONDITIONAL_CASES}
    entered_conditional = [case_id for case_id, state in conditional_states.items() if state and state.get("solver_entered")]
    scheduler = INIT.scheduler_snapshot()
    queued = INIT.registry_queue_demands()
    material = INIT.BASE.PREV.material_audit()
    setup_hashes_ok = prepared.get("status") == "PASS" and all(
        Path(row["pre_fsp_path"]).exists() and sha_file(Path(row["pre_fsp_path"])) == row["pre_fsp_sha256"]
        for row in prepared.get("cases", [])
    )
    checks = {
        "override_pass": override.get("status") == "PASS" and override.get("conditional_batch_authorized") is True,
        "directional_evidence_present": override.get("directional_diagnostic_count", 0) > 0,
        "initial_8_checkpoints_accepted": initial_ok,
        "conditional_8_setup_only_pass": setup_hashes_ok and len(prepared.get("cases", [])) == CONDITIONAL_BUDGET,
        "conditional_solver_entered_zero": not entered_conditional,
        "active_fdtd_zero": scheduler.get("active_fdtd_jobs") == 0,
        "unknown_solver_zero": not scheduler.get("unknown_solver_jobs"),
        "high_priority_queue_zero": not queued,
        "native_material_valid": bool(material.get("pass")),
    }
    result = {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_CONDITIONAL_PREFLIGHT_V1",
        "timestamp_utc": now(),
        "status": "PASS" if all(checks.values()) else "HARD_GATE",
        "checks": checks,
        "entered_conditional_cases": entered_conditional,
        "scheduler_snapshot": scheduler,
        "explicit_high_priority_registry_demand": queued,
        "material_validity": material,
        "solver_policy": {
            "conditional_budget": CONDITIONAL_BUDGET,
            "total_stage_budget": TOTAL_STAGE_BUDGET,
            "paper_a_max_active_fdtd": MAX_ACTIVE,
            "global_cap_unchanged": 3,
            "mpi_processes": 4,
            "threads": 1,
            "entered_true_no_auto_replay": True,
        },
    }
    write_json(REPORT / "preflight.json", result)
    return result


def run_case(case_id: str) -> dict[str, Any]:
    if case_id not in CONDITIONAL_CASES:
        raise RuntimeError(f"CASE_NOT_AUTHORIZED:{case_id}")
    return INIT.run_case(case_id)


def run_wave(gid: str) -> dict[str, Any]:
    processes = []
    handles = []
    for pol in ("x", "y"):
        case_id = f"{gid}_{pol}"
        log_path = RUNTIME / "cases" / case_id / "controller.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handle = log_path.open("a", encoding="utf-8")
        handles.append(handle)
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run-case", "--case-id", case_id], stdout=handle, stderr=handle)
        processes.append((case_id, process))
    while any(process.poll() is None for _, process in processes):
        time.sleep(5.0)
    results = []
    for case_id, process in processes:
        state = case_state(case_id)
        results.append({"case_id": case_id, "returncode": process.returncode, "state": state})
    for handle in handles:
        handle.close()
    if any(row["returncode"] != 0 or not row["state"] or row["state"].get("status") != "COMPLETED" for row in results):
        return {"geometry_id": gid, "status": "FAILED", "cases": results}
    return {"geometry_id": gid, "status": "COMPLETED", "cases": results, "summary": INIT.postprocess_geometry(gid)}


def monitor_sample() -> dict[str, Any]:
    states = INIT.case_states()
    scheduler = INIT.scheduler_snapshot()
    return {
        "timestamp": now(),
        "task": TASK_ID,
        "stage": "BALANCED_CONDITIONAL_TRUTH",
        "completed": sum(state.get("status") == "COMPLETED" for state in states),
        "total": TOTAL_STAGE_BUDGET,
        "running": sum(state.get("status") == "RUNNING" for state in states),
        "entered_unresolved": [state.get("case_id") for state in states if state.get("solver_entered") and state.get("status") in {"FAILED", "RUNNING", "RETURNED"}],
        "controller": {"pid": os.getpid(), "status": "RUNNING"},
        "global_fdtd_slots": scheduler,
        "explicit_high_priority_registry_demand": INIT.registry_queue_demands(),
        "progress": None,
    }


def monitor_loop(stop: threading.Event) -> None:
    monitor = RUNTIME / "monitor_conditional"
    monitor.mkdir(parents=True, exist_ok=True)
    lock = monitor / "paper_a_lp_conditional_truth_monitor.lock"
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("DUPLICATE_MONITOR_GUARD") from exc
    os.write(descriptor, canonical({"pid": os.getpid(), "task": TASK_ID, "created_utc": now()}))
    os.close(descriptor)
    try:
        while True:
            record = monitor_sample()
            append_jsonl(monitor / "paper_a_lp_conditional_truth_progress.jsonl", record)
            write_json(monitor / "paper_a_lp_conditional_truth_monitor_state.json", record)
            if stop.wait(MONITOR_INTERVAL_S):
                break
    finally:
        lock.unlink(missing_ok=True)


def all_summaries() -> list[dict[str, Any]]:
    return [INIT.postprocess_geometry(gid) for gid in ALL]


def rank_summaries(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        summaries,
        key=lambda row: (
            bool(row.get("final_pass")),
            bool(row.get("promising")),
            row.get("MDC_weighted", {}).get("DoLP", -1.0),
            -row.get("MDC_FWHM_psi_span_deg", 999.0),
            row.get("MDC_weighted", {}).get("P_LP_axisfree", -1.0),
        ),
        reverse=True,
    )


def closeout(reason: str) -> dict[str, Any]:
    summaries = all_summaries()
    ranked = rank_summaries(summaries)
    final_rows = [row for row in ranked if row.get("final_pass")]
    promising_rows = [row for row in ranked if row.get("promising")]
    if final_rows:
        verdict = "PAPER_A_LP_ANISOTROPY_BALANCED_FULL_TRUTH_PASS_STABLE_BASIN_FOUND"
    elif promising_rows:
        verdict = "PAPER_A_LP_ANISOTROPY_BALANCED_FULL_TRUTH_PROMISING_ONLY"
    else:
        verdict = "PAPER_A_LP_ANISOTROPY_BALANCED_FULL_TRUTH_STOPPED_NO_STABLE_BASIN"
    states = {case_id: case_state(case_id) for case_id in [f"{gid}_{pol}" for gid in ALL for pol in ("x", "y")]}
    entered = sum(bool(state and state.get("solver_entered")) for state in states.values())
    completed = sum(bool(state and state.get("status") == "COMPLETED") for state in states.values())
    decision = {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_FULL_TRUTH_DECISION_V1",
        "timestamp_utc": now(),
        "status": "PASS",
        "verdict": verdict,
        "reason": reason,
        "geometry_count": len(summaries),
        "solver_budget_max_cases": TOTAL_STAGE_BUDGET,
        "solver_entered_cases": entered,
        "solver_completed_cases": completed,
        "final_pass_count": len(final_rows),
        "promising_count": len(promising_rows),
        "ranked_geometry_ids": [row["geometry_id"] for row in ranked],
        "primary": final_rows[0]["geometry_id"] if final_rows else None,
        "best_diagnostic_only": None if final_rows else ranked[0]["geometry_id"],
        "no_rcwa": True,
        "no_ml": True,
        "summaries": summaries,
        "scheduler_snapshot": INIT.scheduler_snapshot(),
    }
    write_json(REPORT / "terminal_success.json", decision)
    rows = [
        {
            "geometry_id": row["geometry_id"],
            "MDC_weighted_DoLP": row["MDC_weighted"]["DoLP"],
            "MDC_weighted_P_LP_axisfree": row["MDC_weighted"]["P_LP_axisfree"],
            "MDC_FWHM_psi_span_deg": row["MDC_FWHM_psi_span_deg"],
            "MDC_FWHM_DoLP_worst": row["MDC_FWHM_DoLP_worst"],
            "formal_DoLP_worst": row["formal_DoLP_worst"],
            "formal_P_LP_axisfree_worst": row["formal_P_LP_axisfree_worst"],
            "final_pass": row["final_pass"],
            "promising": row["promising"],
        }
        for row in ranked
    ]
    write_csv(REPORT / "all_candidate_comparison.csv", rows)
    report = [
        "# Paper A LP anisotropy balanced full truth v1",
        "",
        f"Verdict: `{verdict}`",
        "",
        "Current Native-M1; source/monitor 430-470 nm; formal 435-465 nm at 1 nm; order-(0,0) J_xy from independent x/y inputs; axis-free coherency/Stokes qualification; phase/K6 excluded.",
        "",
        f"Solver entered/completed: {entered}/{completed} of {TOTAL_STAGE_BUDGET}. RCWA=0; ML=0.",
        "",
        "| geometry | weighted DoLP | weighted P_LP | FWHM psi span | formal worst DoLP | final pass | promising |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for row in ranked:
        report.append(
            f"| {row['geometry_id']} | {row['MDC_weighted']['DoLP']:.6f} | {row['MDC_weighted']['P_LP_axisfree']:.6f} | "
            f"{row['MDC_FWHM_psi_span_deg']:.3f} | {row['formal_DoLP_worst']:.6f} | {row['final_pass']} | {row['promising']} |"
        )
    (REPORT / "final_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    truth_path = AUTH / "paper_a_lp_anisotropy_balanced_initial_truth_v1.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth.update(
        {
            "status": "FULL_BALANCED_TRUTH_COMPLETE",
            "conditional_batch_authorized": True,
            "conditional_batch_eligible": True,
            "solver_entered_cases": entered,
            "solver_completed_cases": completed,
            "remaining_authorized_solver_budget": 0,
            "full_truth_verdict": verdict,
            "full_truth_result_artifact": str(REPORT / "terminal_success.json"),
            "champion_frozen": bool(final_rows),
            "primary": final_rows[0]["geometry_id"] if final_rows else None,
        }
    )
    write_json(truth_path, truth)
    return decision


def run_conditional() -> dict[str, Any]:
    pre = preflight()
    if pre["status"] != "PASS":
        write_json(REPORT / "terminal_failure.json", {"schema": "PAPER_A_LP_ANISOTROPY_BALANCED_CONDITIONAL_FAILURE_V1", "timestamp_utc": now(), "status": "HARD_GATE_PREFLIGHT", "preflight": pre})
        return {"status": "HARD_GATE_PREFLIGHT", "preflight": pre}
    controller_path = RUNTIME / "conditional_controller_state.json"
    controller = {"schema": "PAPER_A_LP_BALANCED_CONDITIONAL_CONTROLLER_STATE_V1", "task": TASK_ID, "pid": os.getpid(), "status": "RUNNING", "timestamp_utc": now()}
    write_json(controller_path, controller)
    stop = threading.Event()
    monitor = threading.Thread(target=monitor_loop, args=(stop,), name="balanced-conditional-monitor", daemon=True)
    monitor.start()
    waves = []
    try:
        for gid in CONDITIONAL:
            boundary = INIT.boundary_check()
            if not boundary["allow_next_wave"]:
                controller.update({"status": "LOW_PRIORITY_BACKGROUND_WAIT", "timestamp_utc": now(), "next_geometry_id": gid})
                write_json(controller_path, controller)
                return {"status": "LOW_PRIORITY_BACKGROUND_WAIT", "completed_waves": waves, "boundary": boundary}
            append_jsonl(REPORT / "visible_events.jsonl", {"timestamp_utc": now(), "event": "WAVE_ENTERING", "geometry_id": gid, "case_ids": [f"{gid}_x", f"{gid}_y"]})
            print(json.dumps({"event": "WAVE_ENTERING", "geometry_id": gid, "case_ids": [f"{gid}_x", f"{gid}_y"]}), flush=True)
            wave = run_wave(gid)
            waves.append(wave)
            if wave["status"] != "COMPLETED":
                controller.update({"status": "HARD_GATE_CASE_FAILURE", "timestamp_utc": now(), "geometry_id": gid})
                write_json(controller_path, controller)
                write_json(REPORT / "terminal_failure.json", {"schema": "PAPER_A_LP_ANISOTROPY_BALANCED_CONDITIONAL_FAILURE_V1", "timestamp_utc": now(), "status": "HARD_GATE_CASE_FAILURE", "wave": wave})
                return {"status": "HARD_GATE_CASE_FAILURE", "wave": wave}
            append_jsonl(REPORT / "visible_events.jsonl", {"timestamp_utc": now(), "event": "WAVE_COMPLETED", "geometry_id": gid})
            print(json.dumps({"event": "WAVE_COMPLETED", "geometry_id": gid}), flush=True)
        controller.update({"status": "COMPLETED", "timestamp_utc": now(), "solver_entered_cases": TOTAL_STAGE_BUDGET})
        write_json(controller_path, controller)
        return closeout("BF05_BF08_CONDITIONAL_TRUTH_COMPLETE")
    finally:
        stop.set()
        monitor.join(timeout=10)


def audit() -> dict[str, Any]:
    case_ids = [f"{gid}_{pol}" for gid in ALL for pol in ("x", "y")]
    cases = []
    for case_id in case_ids:
        state = case_state(case_id)
        checkpoint_path = RUNTIME / "cases" / case_id / "checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.exists() else None
        rows = checkpoint.get("rows", []) if checkpoint else []
        cases.append(
            {
                "case_id": case_id,
                "state": state.get("status") if state else None,
                "entered": bool(state and state.get("solver_entered")),
                "checkpoint_status": checkpoint.get("status") if checkpoint else None,
                "row_count": len(rows),
                "formal_grid_ok": [float(row["wavelength_nm"]) for row in rows] == INIT.GRID,
                "checkpoint_hash_ok": bool(state and checkpoint_path.exists() and state.get("checkpoint_sha256") == sha_file(checkpoint_path)),
                "run_fsp_exists": bool(state and state.get("run_fsp_sha256") and (RUNTIME / "cases" / case_id / f"{case_id}_run.fsp").exists()),
            }
        )
    spectra_path = REPORT / "full_jones_order_0_0_spectra.csv"
    with spectra_path.open(encoding="utf-8", newline="") as handle:
        spectra_rows = list(csv.DictReader(handle))
    scheduler = INIT.scheduler_snapshot()
    monitor_lock = RUNTIME / "monitor_conditional/paper_a_lp_conditional_truth_monitor.lock"
    checks = {
        "cases_16_all_complete": len(cases) == TOTAL_STAGE_BUDGET and all(row["state"] == "COMPLETED" for row in cases),
        "entered_exact_16": sum(row["entered"] for row in cases) == TOTAL_STAGE_BUDGET,
        "checkpoints_31_point_accepted": all(row["checkpoint_status"] == "ACCEPTED" and row["row_count"] == 31 and row["formal_grid_ok"] for row in cases),
        "checkpoint_hashes_match": all(row["checkpoint_hash_ok"] for row in cases),
        "run_fsp_all_exist": all(row["run_fsp_exists"] for row in cases),
        "full_jones_248_rows": len(spectra_rows) == 248 and len({(row["geometry_id"], row["wavelength_nm"]) for row in spectra_rows}) == 248,
        "scheduler_active_slots_zero": scheduler.get("active_fdtd_jobs") == 0 and not scheduler.get("unknown_solver_jobs"),
        "monitor_lock_released": not monitor_lock.exists(),
        "no_rcwa_ml": True,
    }
    result = {
        "schema": "PAPER_A_LP_ANISOTROPY_BALANCED_FULL_TRUTH_FINAL_AUDIT_V1",
        "timestamp_utc": now(),
        "status": "PASS" if all(checks.values()) else "HARD_GATE",
        "checks": checks,
        "cases": cases,
        "scheduler_snapshot": scheduler,
        "solver_accounting": {"authorized": TOTAL_STAGE_BUDGET, "entered": sum(row["entered"] for row in cases), "completed": sum(row["state"] == "COMPLETED" for row in cases), "remaining": 0, "rcwa": 0, "ml": 0},
    }
    write_json(REPORT / "final_audit.json", result)
    return result


def tests() -> dict[str, Any]:
    override = json.loads((AUTH / "paper_a_lp_anisotropy_balanced_midpoint_override_v1.json").read_text(encoding="utf-8"))
    prepared_path = REPORT / "conditional_prepared_fsp_provenance.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8")) if prepared_path.exists() else None
    checks = {
        "selection_identity": list(selected()) == ALL,
        "directional_rule_reproducible": [row["geometry_id"] for row in directional_rows(initial_summaries())] == override.get("directional_geometry_ids"),
        "conditional_ids_exact": override.get("authorized_geometry_ids") == CONDITIONAL,
        "conditional_cases_exact": override.get("authorized_case_ids") == CONDITIONAL_CASES,
        "budget_exact": override.get("conditional_physics_job_budget") == CONDITIONAL_BUDGET and override.get("total_stage_physics_job_budget") == TOTAL_STAGE_BUDGET,
        "prepared_eight_pass": bool(prepared and prepared.get("status") == "PASS" and len(prepared.get("cases", [])) == CONDITIONAL_BUDGET),
        "no_rcwa_ml": override.get("no_rcwa") is True and override.get("no_ml") is True,
    }
    result = {"schema": "PAPER_A_LP_ANISOTROPY_BALANCED_CONDITIONAL_TEST_V1", "timestamp_utc": now(), "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    write_json(REPORT / "test_report.json", result)
    return result


def status() -> dict[str, Any]:
    return {
        "controller": json.loads((RUNTIME / "conditional_controller_state.json").read_text(encoding="utf-8")) if (RUNTIME / "conditional_controller_state.json").exists() else None,
        "terminal_success": json.loads((REPORT / "terminal_success.json").read_text(encoding="utf-8")) if (REPORT / "terminal_success.json").exists() else None,
        "terminal_failure": json.loads((REPORT / "terminal_failure.json").read_text(encoding="utf-8")) if (REPORT / "terminal_failure.json").exists() else None,
        "conditional_states": {case_id: case_state(case_id) for case_id in CONDITIONAL_CASES},
        "scheduler": INIT.scheduler_snapshot(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["authorize", "prepare", "preflight", "run-case", "run-conditional", "audit", "tests", "status", "closeout"])
    parser.add_argument("--case-id")
    args = parser.parse_args()
    if args.mode == "authorize":
        output = authorize()
    elif args.mode == "prepare":
        output = prepare()
    elif args.mode == "preflight":
        output = preflight()
    elif args.mode == "run-case":
        if not args.case_id:
            raise RuntimeError("CASE_ID_REQUIRED")
        output = run_case(args.case_id)
    elif args.mode == "run-conditional":
        output = run_conditional()
    elif args.mode == "audit":
        output = audit()
    elif args.mode == "tests":
        output = tests()
    elif args.mode == "closeout":
        output = closeout("ZERO_SOLVER_RECLOSEOUT")
    else:
        output = status()
    print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
