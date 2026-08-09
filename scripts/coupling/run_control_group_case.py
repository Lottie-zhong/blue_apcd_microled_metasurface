from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
import sys
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from apcd_coupling.joint_case_schema import canonical_hash


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    case = read(out / "joint_case.json")
    setup = read(out / "setup_manifest.json")
    group = case["control_group"]
    case_id = case["case_id"]
    pre = Path(setup["pre_fsp_path"])
    if not pre.is_absolute():
        pre = (ROOT / pre).resolve()
    entry_sha = setup["pre_fsp_sha256"]

    budget_path = ROOT / "registries/coupling/solver_budget_registry.json"
    budget = read(budget_path)
    authorized = (budget.get("authorized_control_cases", []) + budget.get("authorized_spacer_cases", []) + budget.get("authorized_broadband_cases", []) + budget.get("authorized_incident_state_case_ids", []))
    if group in {"NB_T0", "NB_T79", "NB_T237"} and budget.get("status") in {"BROADBAND_RECONCILIATION_POLICY_FROZEN_DIAGNOSTIC_ONLY", "FINAL_SPACER_FREEZE_FOR_STAGE_A_XPOL_NORMAL", "NO_ROBUST_BROADBAND_WINNER"}:
        raise RuntimeError("broadband solver execution is locked after spacer freeze; new authorization required")
    if group == "POL_ANGLE_MATRIX" and budget.get("status") != "AUTHORIZED_POLARIZATION_ANGLE_450NM_MATRIX":
        raise RuntimeError("polarization-angle solver execution is locked after matrix validation; new authorization required")
    if not setup["setup_gate"]["pass"]:
        raise RuntimeError("setup gate not PASS")
    if sha(pre) != entry_sha:
        raise RuntimeError("pre-FSP hash mismatch before solver entry")
    if case_id not in authorized:
        raise RuntimeError(f"case not authorized: {case_id}")
    if int(budget.get("entered_runs", 0)) >= int(budget.get("budgets", {}).get("FDTD", 0)):
        raise RuntimeError("FDTD budget exhausted")

    completed = set(budget.get("completed_case_ids", []))
    incident_completed = set(budget.get("incident_state_completed_case_ids", []))
    incident_order = budget.get("authorized_incident_state_case_order", [])
    incident_entered = budget.get("incident_state_entered_case_ids", [])
    if group == "POL_ANGLE_MATRIX":
        if case_id not in incident_order:
            raise RuntimeError(f"incident-state case not authorized: {case_id}")
        expected_index = incident_order.index(case_id)
        if incident_entered != incident_order[:len(incident_entered)] or len(incident_entered) != expected_index:
            expected = incident_order[len(incident_entered)] if len(incident_entered) < len(incident_order) else None
            raise RuntimeError(f"incident-state case order violation: expected {expected}, got {case_id}")
    if group == "NB_T0" and "STAGE_A_NB_T237_445_455NM_X_UX0" not in completed:
        raise RuntimeError("NB_T237 must complete before NB_T0")
    if case_id in completed or case_id in incident_completed:
        raise RuntimeError("case already completed; replay forbidden")

    stage = read(ROOT / "contracts/coupling/stage_a_direct_fullwave_contract_v1.json")
    physical_hash = canonical_hash({"case": case, "stage_contract": stage})
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    attempt = "attempt_001"
    runtime_dir = out / "runtime" / attempt
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = runtime_dir / "entered_ledger.json"
    post = (runtime_dir / f"{case_id}_{attempt}_post.fsp").resolve()
    log = runtime_dir / "solver_controller.log"
    entered = {
        "schema_version": "solver_entered_ledger_v1",
        "case_id": case_id,
        "control_group": group,
        "attempt_id": attempt,
        "solver_entered": True,
        "entered_timestamp": now(),
        "pre_fsp_path": str(pre),
        "pre_fsp_entry_sha256": entry_sha,
        "physical_contract_hash": physical_hash,
        "joint_geometry_hash": case["joint_geometry_hash"],
        "source_commits": setup["source_commits"],
        "coupling_commit": commit,
        "automatic_replay_forbidden": True,
    }
    atomic(ledger_path, entered)
    log.write_text(f"{entered['entered_timestamp']} solver_entered=true control_group={group} case_id={case_id} pre_fsp_entry_sha256={entry_sha}\n", encoding="utf-8")
    budget["entered_runs"] = int(budget.get("entered_runs", 0)) + 1
    budget["entered_attempts"] = budget.get("entered_attempts", []) + [{"case_id": case_id, "attempt_id": attempt, "entered_timestamp": entered["entered_timestamp"], "pre_fsp_entry_sha256": entry_sha}]
    if group == "POL_ANGLE_MATRIX":
        budget["new_physical_cases_entered"] = int(budget.get("new_physical_cases_entered", 0)) + 1
        budget["incident_state_entered_case_ids"] = budget.get("incident_state_entered_case_ids", []) + [case_id]
    else:
        budget["entered_case_ids"] = budget.get("entered_case_ids", []) + [case_id]
    budget["status"] = "STAGE_A_CONTROL_GROUPS_RUNNING"
    atomic(budget_path, budget)
    setup["solver_entered"] = True
    setup["solver_entered_timestamp"] = entered["entered_timestamp"]
    setup["entered_ledger_path"] = str(ledger_path)
    atomic(out / "setup_manifest.json", setup)

    try:
        import lumapi
        fdtd = lumapi.FDTD(str(pre), hide=True)
        try:
            log.write_text(log.read_text(encoding="utf-8") + f"{now()} lifecycle=load_complete run_start=true\n", encoding="utf-8")
            start = time.time()
            fdtd.run()
            elapsed = time.time() - start
            fdtd.save(str(post))
            log.write_text(log.read_text(encoding="utf-8") + f"{now()} lifecycle=run_complete post_save=true elapsed_s={elapsed:.3f}\n", encoding="utf-8")
        finally:
            fdtd.close()
        post_sha = sha(post)
        current_sha = sha(pre)
        mutation = {"detected": current_sha != entry_sha, "entry_sha256": entry_sha, "current_path_sha256": current_sha, "evidence": "Lumerical setup-side mutation observed after solver lifecycle; entry-time identity remains immutable in entered_ledger.json.", "replay_policy": "No replay; each control case has one entered attempt."}
        runtime = {"schema_version": "control_group_run_state_v1", "case_id": case_id, "control_group": group, "attempt_id": attempt, "pre_fsp_path": str(pre), "pre_fsp_entry_sha256": entry_sha, "pre_fsp_current_sha256": current_sha, "pre_fsp_post_entry_mutation": mutation, "post_fsp_path": str(post), "post_fsp_sha256": post_sha, "solver_entered": True, "solver_completed": True, "physical_contract_hash": physical_hash, "source_commits": setup["source_commits"], "coupling_commit": commit, "completed_timestamp": now()}
        atomic(runtime_dir / "run_state.json", runtime)
        setup.update({"solver_completed": True, "post_fsp_path": str(post), "post_fsp_sha256": post_sha, "pre_fsp_current_sha256": current_sha, "pre_fsp_post_entry_mutation": mutation})
        atomic(out / "setup_manifest.json", setup)
        budget["engine_completed"] = int(budget.get("engine_completed", 0)) + 1
        budget["controller_returned"] = int(budget.get("controller_returned", 0)) + 1
        budget["post_saved"] = int(budget.get("post_saved", 0)) + 1
        budget["completed_attempts"] = budget.get("completed_attempts", []) + [{"case_id": case_id, "attempt_id": attempt, "post_fsp_sha256": post_sha, "completed_timestamp": runtime["completed_timestamp"]}]
        if group == "POL_ANGLE_MATRIX":
            budget["new_physical_cases_completed"] = int(budget.get("new_physical_cases_completed", 0)) + 1
            budget["incident_state_completed_case_ids"] = budget.get("incident_state_completed_case_ids", []) + [case_id]
        else:
            budget["completed_case_ids"] = budget.get("completed_case_ids", []) + [case_id]
        budget["status"] = "STAGE_A_CONTROL_GROUPS_RUNNING" if budget["entered_runs"] < budget["budgets"]["FDTD"] else "STAGE_A_CONTROL_GROUPS_ALL_COMPLETED"
        atomic(budget_path, budget)
        print(json.dumps(runtime, indent=2))
    except Exception as exc:
        failure = {"case_id": case_id, "control_group": group, "attempt_id": attempt, "solver_entered": True, "failure_type": type(exc).__name__, "failure_text": str(exc), "automatic_replay_forbidden": True}
        atomic(runtime_dir / "run_failure.json", failure)
        budget["status"] = "STAGE_A_CONTROL_GROUPS_ENTERED_FAILURE_REPLAY_FORBIDDEN"
        atomic(budget_path, budget)
        raise


if __name__ == "__main__":
    main()
