from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = r"N:\anaconda_envs\RCP_LCP\python.exe"
SCRIPT = ROOT / "scripts" / "lp_ml0" / "lp_ml0_existing_data_audit.py"
OUT = ROOT / "outputs" / "lp_ml0_existing_data_audit"


def run_script() -> None:
    subprocess.run([PY, str(SCRIPT)], cwd=ROOT, check=True)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_lp_ml0_audit_outputs_and_required_columns():
    run_script()
    rows = read_csv(OUT / "lp_hnew_all_candidates_unified.csv")
    required = {
        "candidate_id", "H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg",
        "gap_or_dx_nm", "target_bin_deg", "nearest_bin_deg", "selected_phase_deg", "phase_error_deg",
        "Tx", "leakage", "conversion_to_leakage_ratio", "matrix_error", "strict_or_loose_or_fail",
        "source_stage", "source_file", "result_csv",
    }
    assert rows
    assert required.issubset(rows[0].keys())


def test_h500_seed_rows_are_not_robust_or_direct_k6():
    run_script()
    rows = read_csv(OUT / "lp_h500_450nm_single_point_seed_library.csv")
    assert {r["target_bin_deg"] for r in rows} == {"0", "60", "120", "180", "240", "300"}
    assert all(r["library_role"] == "450nm_single_point_seed_only" for r in rows)
    assert all(r["robust_451_453_ready"] == "false" for r in rows)
    assert all(r["direct_k6_ready"] == "false" for r in rows)


def test_b240_b300_diagnosis_and_summary_exist():
    run_script()
    diag = read_csv(OUT / "lp_hnew_b240_b300_diagnosis.csv")
    assert diag
    assert any(r["diagnosis_bucket"].startswith("b240_candidates") for r in diag)
    assert any(r["diagnosis_bucket"].startswith("b300_candidates") for r in diag)
    summary = json.loads((OUT / "lp_ml0_audit_summary.json").read_text(encoding="utf-8"))
    assert summary["no_fdtd_run"] is True


def test_report_and_schema_boundary_text():
    run_script()
    report = (ROOT / "reports" / "lp_ml0_existing_data_audit.md").read_text(encoding="utf-8")
    schema = (ROOT / "reports" / "lp_ml0_schema_draft.yaml").read_text(encoding="utf-8")
    assert "No FDTD was run" in report
    assert "Re/Im Jones encoding" in schema
    assert "circular_phase_loss" in schema
