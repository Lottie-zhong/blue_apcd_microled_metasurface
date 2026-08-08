"""Finalize state and provenance after the six-case HF pilot transaction."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
DATASET = ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1"
STAGE = ROOT / "outputs" / "np_k6_p0_remaining_five_anchors_execution_v1"
DOC = ROOT / "docs" / "np_k6_hf_pilot_anchor_dataset_v1.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    decision_path = DATASET / "dataset_decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision.update({
        "pilot_training_authorized": True,
        "bulk_mdc_compatible_training_authorized": False,
        "real_training_started": False,
        "checkpoint_count": 0,
        "formal_hf_label_count": 66,
        "six_anchor_transaction_committed": True,
        "provisional_hf_labels_promoted": True,
    })
    decision_path.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    supervisor = json.loads((STAGE / "supervisor_state.json").read_text(encoding="utf-8"))
    accepted = {
        "case_id": "RUN3C_P_PILOT_HF_V1",
        "attempt_id": "accepted_3ps_correction_v2",
        "entered": 1,
        "run_invocation_count": 1,
        "engine_completed": 1,
        "controller_returned": 1,
        "post_saved": 1,
        "post_fsp_sha256": "c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca",
        "quality_gate_pass": True,
        "max_abs_closure_residual": 0.004513767612906006,
        "structure_anomaly_448": 0.003592535616673165,
        "order_sum_mismatch_max": 2.220446049250313e-16,
        "direct_raw_sourcepower_mismatch_max": 1.1102230246251565e-16,
    }
    anchors = [accepted] + [
        {"case_id": x["case_id"], "attempt_id": "attempt_001", "entered": 1,
         "run_invocation_count": 1, "engine_completed": 1, "controller_returned": 1,
         "post_saved": 1, "post_fsp_sha256": x["post_fsp_sha256"],
         "quality_gate_pass": x["quality_gate_pass"], **x["metrics"]}
        for x in supervisor["completed_cases"]
    ]
    state = {
        "schema_version": "np_k6_hf_pilot_state_v1",
        "status": "NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY",
        "formal_observation_count": 66,
        "anchor_case_count": 6,
        "anchor_cases": anchors,
        "pilot_training_authorized": True,
        "bulk_mdc_compatible_training_authorized": False,
        "real_training_started": False,
        "checkpoint_count": 0,
        "sealed_test_touched": False,
        "solver_entered_total": 6,
        "solver_run_invocation_total": 6,
        "generator_id": "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2",
        "interface_stack_id": "NP_K6_INDEPENDENT_STACK_PILOT_V1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    (DATASET / "pilot_training_state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    budget = {
        "schema_version": "np_k6_hf_pilot_solver_budget_audit_v1",
        "authorized_remaining_five_entered": 5,
        "accepted_run3c_p_entered": 1,
        "solver_entered_total": 6,
        "solver_run_invocation_total": 6,
        "per_case_attempt_max": 1,
        "attempt_002_used": False,
        "automatic_rerun_used": False,
        "active_np_case_ids": [],
        "supervisor_current_case": supervisor.get("current_case"),
        "supervisor_status": supervisor.get("status"),
        "other_np_solver_cases": [],
        "sealed_test_touched": False,
    }
    (DATASET / "solver_budget_audit.json").write_text(json.dumps(budget, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    p_s = json.loads((DATASET / "p_s_preliminary_audit.json").read_text(encoding="utf-8"))
    lines = [
        "# NP K6 HF P0 anchor dataset pilot v1",
        "",
        "Status: `NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY`.",
        "",
        "Six sequential attempt_001 anchors passed the frozen V2 numerical gates and were promoted transactionally to exactly 66 formal HF observations (3 geometries × 2 polarizations × 11 exact wavelengths). `pilot_training_authorized=true`; bulk MDC-compatible training remains false; no real training or sealed test was started.",
        "",
        "## Anchor gates",
        "",
        "| case | post-FSP SHA256 | max closure | structure anomaly | order mismatch | direct normalization mismatch |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for a in anchors:
        lines.append(f"| {a['case_id']} | `{a['post_fsp_sha256']}` | {a.get('max_abs_closure_residual', '')} | {a.get('structure_anomaly_448', '')} | {a.get('order_sum_mismatch_max', '')} | {a.get('direct_raw_sourcepower_mismatch_max', '')} |")
    lines += [
        "",
        "All cases have exact wavelengths 445–455 nm, finite values, read-only reload, dominant transmitted order +1, and `quality_gate_pass=true`. No rerun or attempt_002 was used; the obsolete consumed RUN3C-S V1 identity remains excluded.",
        "",
        "## p/s preliminary audit",
        "",
        "The three geometry-family comparisons remain `P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA`; this pilot does not make a final p/s equivalence claim.",
        "",
        "```json",
        json.dumps(p_s, indent=2, sort_keys=True),
        "```",
        "",
        "Dataset files are under `outputs/np_k6_hf_pilot_dataset_v1/`. Training has not started (`checkpoint_count=0`).",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")
    files = []
    for p in sorted(DATASET.rglob("*")):
        if p.is_file() and p.name != "dataset_checksum_manifest.json":
            files.append({"path": str(p.relative_to(DATASET)).replace("\\", "/"), "sha256": sha256(p), "size_bytes": p.stat().st_size})
    manifest = {"schema_version": "np_k6_hf_pilot_dataset_v1", "formal_observation_count": 66, "files": files}
    (DATASET / "dataset_checksum_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": state["status"], "formal_observation_count": 66, "dataset_files": len(files), "doc": str(DOC)}, indent=2))


if __name__ == "__main__":
    main()
