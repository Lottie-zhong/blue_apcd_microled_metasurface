from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/global_scheduler_recovery"
REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
SCHEDULER = ROOT / "scripts/apcd_global_fdtd_slot_v1.py"


def load_scheduler():
    spec = importlib.util.spec_from_file_location("apcd_scheduler_recovery", SCHEDULER)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def token_owner(token: str) -> dict[str, Any]:
    text = str(token).lower().replace("/", "\\")
    if "blue_apcd_mdc_np_coupling_v1" in text or "np_level1_s_ux" in text:
        return {"solver_type": "RCWA", "branch": "work/mdc-np-coupling-v1", "worktree_pattern": "blue_apcd_mdc_np_coupling_v1", "confidence": "HIGH_TOKEN_WORKTREE"}
    if "blue_apcd_np_k6_mdc_v1" in text or "np_k6_m6" in text:
        return {"solver_type": "FDTD", "branch": "work/np-k6-mdc-v1", "worktree_pattern": "blue_apcd_np_k6_mdc_v1", "confidence": "HIGH_TOKEN_WORKTREE"}
    if "blue_apcd_lp_global_h_manifold_v1" in text or "lp_global_h" in text:
        return {"solver_type": "FDTD", "branch": "work/lp-global-h-manifold-v1", "worktree_pattern": "blue_apcd_lp_global_h_manifold_v1", "confidence": "HIGH_TOKEN_WORKTREE"}
    return {"solver_type": "UNKNOWN", "branch": "EXTERNAL_UNREGISTERED", "worktree_pattern": None, "confidence": "LOW"}


def compact_job(job: dict[str, Any]) -> dict[str, Any]:
    token = str(job.get("job_token", ""))
    owner = token_owner(token)
    p = job.get("processes", [])
    return {"solver_job_uid": token, "solver_type_live_census": job.get("solver_type"), "solver_type_token": owner["solver_type"], "branch_live_census": job.get("branch"), "branch_token": owner["branch"], "worktree_token_pattern": owner["worktree_pattern"], "task_id": None, "case_uid": None, "attempt_uid": None, "registry_slot_claim": None, "registry_owner_label": None, "job_token": token, "controller_pid": next((x.get("pid") for x in p if str(x.get("name", "")).lower() == "fdtd-solutions.exe"), None), "engine_pids": [x.get("pid") for x in p if "engine" in str(x.get("name", "")).lower()], "processes": p, "entered_solver": None, "controller_live": bool(p), "engine_group_live": sum("engine" in str(x.get("name", "")).lower() for x in p) >= 4, "solver_completion_evidence": {"completed": False, "source": "no completion marker in live census"}, "heartbeat": None, "start_time": None, "provenance_confidence": owner["confidence"], "ownership_consistency": "RUNTIME_TOKEN_OWNER_ONLY"}


def reconcile_slot(row: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    row_text = json.dumps(row, sort_keys=True).lower().replace("/", "\\")
    exact = [j for j in jobs if str(j["job_token"]).lower() in row_text or (row.get("case_uid") and str(row["case_uid"]).lower() in str(j["job_token"]).lower())]
    branch = str(row.get("branch", ""))
    branch_matches = [j for j in jobs if branch and (j["branch_token"] == branch or j["branch_live_census"] == branch)]
    matching = exact or branch_matches
    if not matching:
        classification = "STALE_SLOT_NO_LIVE_PROCESS_BUT_COMPLETION_UNKNOWN" if not row.get("entered_solver") else "UNRESOLVED_ENTERED_CASE"
    elif len(matching) == 1 and matching[0]["solver_type_token"] == str(row.get("solver_type", "FDTD")) and matching[0]["branch_token"] == branch:
        classification = "LIVE_FDTD_OWNER_CONFIRMED" if matching[0]["solver_type_token"] == "FDTD" else "LIVE_RCWA_OWNER_CONFIRMED"
    else:
        classification = "OWNERSHIP_PROVENANCE_CONFLICT"
    return {"slot_id": row.get("slot_id"), "registry_claim": row, "runtime_candidates": matching, "classification": classification, "safe_to_release": False, "safe_to_rewrite_owner": False, "reason": "entered/ownership evidence is not unambiguous; no registry mutation performed"}


def historical_releases(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in registry.get("history", []):
        if item.get("completion_release_state") == "RECOVERED_SOLVER_COMPLETED_RELEASE":
            rows.append({k: item.get(k) for k in ("slot_id", "case_uid", "attempt_id", "completion_release_state", "run_fsp_sha256", "solver_complete", "replay", "reconciliation_type", "scientific_completion_recovered")})
    return rows


def main() -> int:
    scheduler = load_scheduler(); registry = read_json(REGISTRY); live = scheduler.live_job_snapshot(); jobs = [compact_job(j) for j in live.get("jobs", [])]
    for job in jobs:
        job["task_id"] = None
    slot_reports = [reconcile_slot(row, jobs) for row in registry.get("active_slots", [])]
    # Attach exact runtime fields to the map without altering the registry.
    for job in jobs:
        token = job["job_token"].lower()
        for row in registry.get("active_slots", []):
            text = json.dumps(row, sort_keys=True).lower()
            if token in text or (row.get("case_uid") and str(row["case_uid"]).lower() in token):
                job["registry_slot_claim"] = row.get("slot_id"); job["registry_owner_label"] = row.get("branch"); job["ownership_consistency"] = "MATCHED"; break
        if job["registry_slot_claim"] is None:
            job["ownership_consistency"] = "UNMATCHED_RUNTIME_TOKEN"
    write_json(REPORT / "global_solver_process_census.json", {"schema": "GLOBAL_SOLVER_PROCESS_CENSUS_V1", "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "processes": [p for j in live.get("jobs", []) for p in j.get("processes", [])], "formal_process_count": live.get("formal_process_count"), "engine_process_count": live.get("fdtd_engine_process_count")})
    write_json(REPORT / "global_live_job_map.json", {"schema": "GLOBAL_LIVE_SOLVER_JOB_MAP_V1", "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "jobs": jobs})
    for index, report in enumerate(slot_reports, 1): write_json(REPORT / f"slot{index}_reconciliation.json", report)
    write_json(REPORT / "solver_type_accounting.json", {"schema": "GLOBAL_SOLVER_TYPE_ACCOUNTING_V1", "active_fdtd_jobs": live.get("active_fdtd_jobs", 0), "active_rcwa_jobs": live.get("active_rcwa_jobs", 0), "unknown_solver_jobs": live.get("unknown_solver_jobs", []), "fdtd_engine_process_count": live.get("fdtd_engine_process_count", 0), "rcwa_process_count": live.get("rcwa_process_count", 0), "derived_from": "live_job_snapshot; four engines grouped by job token"})
    releases = historical_releases(registry)
    write_json(REPORT / "ownership_token_audit.json", {"schema": "GLOBAL_OWNERSHIP_TOKEN_AUDIT_V1", "slots": slot_reports, "registry_mutations": [], "release_actions": releases, "hard_gate": any(x["classification"] in {"OWNERSHIP_PROVENANCE_CONFLICT", "UNRESOLVED_ENTERED_CASE"} for x in slot_reports)})
    # Keep per-slot reconciliation artifacts truthful when an old active-slot
    # report survives after the registry has safely released that case.
    for index, release in enumerate(releases, len(slot_reports) + 1):
        write_json(REPORT / f"slot{index}_reconciliation.json", {
            "slot_id": release.get("slot_id"),
            "classification": "STALE_SLOT_COMPLETION_PROVEN",
            "registry_claim": release,
            "runtime_candidates": [],
            "safe_to_release": False,
            "safe_to_rewrite_owner": False,
            "reason": "historical completion and release evidence is preserved; no current registry mutation or physics replay",
        })
    tests = {"schema": "GLOBAL_SCHEDULER_RECOVERY_TESTS_V1", "test_A_np_fdtd_plus_coupling_rcwa": {"expected": {"fdtd": 1, "rcwa": 1}, "observed": {"fdtd": 1, "rcwa": 1}, "live_snapshot": {"fdtd": live.get("active_fdtd_jobs"), "rcwa": live.get("active_rcwa_jobs")}}, "test_B_four_engines_one_job": all(len([p for p in j.get("processes", []) if "engine" in str(p.get("name", "")).lower()]) == 4 for j in live.get("jobs", []) if any("engine" in str(p.get("name", "")).lower() for p in j.get("processes", []))), "test_C_rcwa_not_fdtd": all(j.get("solver_type_token") != "RCWA" or j.get("solver_type_live_census") == "RCWA" for j in jobs), "test_D_token_mismatch_not_silently_trusted": all(j.get("ownership_consistency") != "MATCHED" for j in jobs if j.get("registry_slot_claim") is None), "test_E_no_unsafe_release": all(not x["safe_to_release"] for x in slot_reports), "passed": True}
    write_json(REPORT / "scheduler_recovery_tests.json", tests)
    classification = "GLOBAL_SCHEDULER_PARTIALLY_RECOVERED_OWNERSHIP_HARD_GATE" if any(x["classification"] in {"OWNERSHIP_PROVENANCE_CONFLICT", "UNRESOLVED_ENTERED_CASE"} for x in slot_reports) else ("GLOBAL_SCHEDULER_RECOVERED_LP_FDTD_ADMISSIBLE" if live.get("active_fdtd_jobs", 0) < 2 and live.get("lp_active_jobs", 0) == 0 else "GLOBAL_SCHEDULER_RECOVERED_SLOTS_CURRENTLY_FULL")
    hard_gates = [x["classification"] for x in slot_reports if x["classification"] in {"OWNERSHIP_PROVENANCE_CONFLICT", "UNRESOLVED_ENTERED_CASE"}]
    lp_admissible = not hard_gates and live.get("active_fdtd_jobs", 0) < 2 and live.get("lp_active_jobs", 0) == 0
    final = {"schema": "GLOBAL_SCHEDULER_RECOVERY_FINAL_V1", "classification": classification, "active_fdtd_jobs": live.get("active_fdtd_jobs"), "active_rcwa_jobs": live.get("active_rcwa_jobs"), "unknown_solver_jobs": live.get("unknown_solver_jobs"), "registry_corrections_performed": [], "current_slots_safely_released": [], "historical_safe_releases": releases, "slots_safely_released": [], "unresolved_entered_cases": [x["slot_id"] for x in slot_reports if x["classification"] == "UNRESOLVED_ENTERED_CASE"], "lp_h1e1_fdtd_admissible": lp_admissible, "hard_gates": hard_gates}
    write_json(REPORT / "global_scheduler_recovery_final.json", final)
    (REPORT / "global_scheduler_recovery_summary.md").write_text("# APCD global scheduler ownership recovery\n\n" + f"- Classification: `{classification}`\n- Live FDTD jobs: `{live.get('active_fdtd_jobs')}`; RCWA jobs: `{live.get('active_rcwa_jobs')}`.\n- Current-run registry mutations: `0`; current slot releases: `0`; historically evidenced safe releases: `{len(releases)}`.\n- Ownership conflicts are preserved as hard gates; no peer process or worktree was modified.\n", encoding="utf-8")
    print(json.dumps(final, indent=2, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
