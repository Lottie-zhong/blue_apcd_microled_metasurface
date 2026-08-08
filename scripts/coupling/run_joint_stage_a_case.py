from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from apcd_coupling.joint_case_schema import canonical_hash

CASE_ID = "STAGE_A_450NM_X_UX0_TEXTRA0"
OUTPUT = ROOT / "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1"
MDC_COMMIT = "489b54e43bbf2c08ce030a945b9d4b70ee7550f2"
NP_COMMIT = "7a8588f6b5a1c96d88813f60406d418b488135fd"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    out = args.output_dir
    setup = read_json(out / "setup_manifest.json")
    gate = read_json(out / "setup_gate.json")
    if not gate.get("pass"):
        raise RuntimeError("setup gate is not PASS")
    ledger = out / "runtime" / "attempt_001" / "entered_ledger.json"
    if ledger.exists():
        raise RuntimeError("STAGE_A_CASE_ENTERED_REPLAY_REQUIRES_AUTHORIZATION")
    prefsp = Path(setup["pre_fsp_path"])
    if sha256(prefsp) != setup["pre_fsp_sha256"]:
        raise RuntimeError("pre-FSP hash mismatch before solver entry")
    stage_contract_path = ROOT / "contracts/coupling/stage_a_direct_fullwave_contract_v1.json"
    stage_contract = read_json(stage_contract_path)
    case = read_json(out / "joint_case.json")
    physical_contract_hash = canonical_hash({"case": case, "stage_contract": stage_contract})
    commit = git_head()
    budget_path = ROOT / "registries/coupling/solver_budget_registry.json"
    budget = read_json(budget_path)
    if budget.get("entered_runs", 0) != 0 or budget.get("budgets", {}).get("FDTD", 0) != 0:
        raise RuntimeError("solver budget is not in the authorized zero-entered state")
    stage_contract.update({
        "status": "AUTHORIZED_TO_ENTER_STAGE_A_SINGLE_CASE",
        "solver_authorized": True,
        "authorized_case_id": CASE_ID,
        "authorized_at": now(),
        "t_extra_policy": {**stage_contract["t_extra_policy"], "run_now": True},
        "required_authorization_action": "AUTHORIZED_BY_CURRENT_TASK",
    })
    write_atomic(stage_contract_path, stage_contract)
    budget.update({
        "status": "STAGE_A_SINGLE_CASE_AUTHORIZED",
        "budgets": {**budget["budgets"], "FDTD": 1},
        "authorized_case_id": CASE_ID,
        "authorized_at": now(),
        "entered_runs": 0,
        "source_worktree_writes": 0,
    })
    write_atomic(budget_path, budget)
    attempt_dir = ledger.parent
    attempt_dir.mkdir(parents=True, exist_ok=True)
    entered = {
        "schema_version": "solver_entered_ledger_v1",
        "case_id": CASE_ID,
        "attempt_id": "attempt_001",
        "solver_entered": True,
        "entered_timestamp": now(),
        "pre_fsp_path": str(prefsp),
        "pre_fsp_sha256": setup["pre_fsp_sha256"],
        "physical_contract_hash": physical_contract_hash,
        "joint_geometry_hash": case["joint_geometry_hash"],
        "source_commits": {"mdc": MDC_COMMIT, "np": NP_COMMIT},
        "coupling_commit": commit,
        "automatic_replay_forbidden": True,
    }
    write_atomic(ledger, entered)
    budget.update({"entered_runs": 1, "entered_case_id": CASE_ID, "entered_attempt_id": "attempt_001", "entered_timestamp": entered["entered_timestamp"], "pre_fsp_sha256": setup["pre_fsp_sha256"], "physical_contract_hash": physical_contract_hash})
    write_atomic(budget_path, budget)
    setup["solver_entered"] = True
    setup["solver_entered_timestamp"] = entered["entered_timestamp"]
    setup["entered_ledger_path"] = str(ledger)
    write_atomic(out / "setup_manifest.json", setup)
    log = attempt_dir / "solver_controller.log"
    log.write_text(f"{entered['entered_timestamp']} solver_entered=true case_id={CASE_ID} pre_fsp_sha256={setup['pre_fsp_sha256']}\n", encoding="utf-8")
    post = attempt_dir / f"{CASE_ID}_attempt_001_post.fsp"
    runtime = {"case_id": CASE_ID, "attempt_id": "attempt_001", "pre_fsp_path": str(prefsp), "pre_fsp_sha256": setup["pre_fsp_sha256"], "post_fsp_path": str(post), "solver_entered": True, "solver_completed": False, "physical_contract_hash": physical_contract_hash, "source_commits": {"mdc": MDC_COMMIT, "np": NP_COMMIT}, "coupling_commit": commit}
    try:
        import lumapi
        fdtd = lumapi.FDTD(str(prefsp), hide=True)
        try:
            started = time.time()
            log.write_text(log.read_text(encoding="utf-8") + f"{now()} lifecycle=load_complete run_start=true\n", encoding="utf-8")
            fdtd.run()
            elapsed = time.time() - started
            fdtd.save(str(post))
            log.write_text(log.read_text(encoding="utf-8") + f"{now()} lifecycle=run_complete post_save=true elapsed_s={elapsed:.3f}\n", encoding="utf-8")
        finally:
            fdtd.close()
        post_sha = sha256(post)
        runtime.update({"solver_completed": True, "post_fsp_sha256": post_sha, "completed_timestamp": now()})
        write_atomic(attempt_dir / "run_state.json", runtime)
        setup["solver_completed"] = True
        setup["post_fsp_path"] = str(post)
        setup["post_fsp_sha256"] = post_sha
        write_atomic(out / "setup_manifest.json", setup)
        budget.update({"status": "STAGE_A_SINGLE_CASE_COMPLETED", "engine_completed": 1, "controller_returned": 1, "post_saved": 1, "post_fsp_sha256": post_sha})
        write_atomic(budget_path, budget)
        print(json.dumps(runtime, indent=2))
    except Exception as exc:
        runtime.update({"failure_timestamp": now(), "failure_type": type(exc).__name__, "failure_text": str(exc), "automatic_replay_forbidden": True})
        write_atomic(attempt_dir / "run_failure.json", runtime)
        budget.update({"status": "STAGE_A_SINGLE_CASE_ENTERED_FAILURE_REPLAY_FORBIDDEN", "engine_completed": 0, "controller_returned": 0, "post_saved": 0})
        write_atomic(budget_path, budget)
        raise

if __name__ == "__main__":
    main()
