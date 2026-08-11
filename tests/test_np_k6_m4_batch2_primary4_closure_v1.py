import csv
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1"


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_batch2_closure_report_passes():
    report = json.loads((OUT / "batch2_independent_validator_report.json").read_text(encoding="utf-8-sig"))
    assert report["status"] == "PASS"
    assert all(report["checks"].values())


def test_batch2_and_merged_row_counts():
    assert len(_rows(OUT / "batch2_hf_observations_long.csv")) == 88
    assert len(_rows(OUT / "merged_development_hf_observations_long.csv")) == 286


def test_no_unauthorized_solver_or_sealed_read():
    ledger = json.loads((OUT / "batch2_execution_ledger.json").read_text(encoding="utf-8-sig"))
    state = json.loads((OUT / "batch2_supervisor_state.json").read_text(encoding="utf-8-sig"))
    assert ledger["solver_run_invocations_total"] == 8
    assert ledger["accepted_case_count"] == 8
    assert ledger["sealed_target_reads"] == 0
    assert state["first6_first8_entered"] is False
    assert state["m5_training_started"] is False
