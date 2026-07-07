from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b2c_selectivity_first_ranker.py"
OUT = ROOT / "outputs" / "lp_ml1b2c_selectivity_first_ranking"
RANKING = OUT / "batch_01" / "lp_ml1b2c_batch01_selectivity_first_ranking.csv"
SUMMARY = OUT / "batch_01" / "lp_ml1b2c_batch01_summary.json"
THRESHOLDS = OUT / "lp_ml1b2c_thresholds.json"
NEXT = OUT / "lp_ml1b2c_next_action_recommendation.json"
REPORT = ROOT / "reports" / "lp_ml1b2c_selectivity_first_ranking.md"


def run_ranker():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_threshold_file_and_no_fdtd_flags():
    run_ranker()
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    assert thresholds["selected_Tx_min"] == 0.45
    assert thresholds["ratio_median_min"] == 6.0
    assert thresholds["phase_err_at_452nm_max_deg"] == 15.0
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["no_fdtd_run"] is True
    assert summary["strong_or_usable_count"] == 0


def test_batch01_class_assignment_no_strong_or_usable():
    run_ranker()
    rows = list(csv.DictReader(RANKING.open(newline="", encoding="utf-8")))
    assert len(rows) == 6
    classes = {r["b2c_class"] for r in rows}
    assert "strong_projector_phase_good" not in classes
    assert "usable_projector_phase_good" not in classes
    assert "high_Tx_but_nonselective" in classes
    assert "phase_near_but_nonselective" in classes
    assert all(r["extraction_schema_gate"] == "pass" for r in rows)


def test_next_action_and_report_boundary():
    run_ranker()
    rec = json.loads(NEXT.read_text(encoding="utf-8"))
    assert rec["recommended_next_batch_id"] == "LPML1B2A_BATCH_04"
    assert rec["do_not_declare_k6_readiness"] is True
    text = REPORT.read_text(encoding="utf-8")
    assert "Hierarchy implemented" in text
    assert "No FDTD was run" in text


def test_ranker_can_emit_batch04_names_after_results_exist():
    batch04 = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_04"
    if not (batch04 / "lp_ml1b2b_batch04_results.csv").exists():
        return
    report = ROOT / "reports" / "lp_ml1b2c_batch04_selectivity_first_ranking.md"
    subprocess.run([sys.executable, str(SCRIPT), "--batch-dir", str(batch04), "--batch-name", "batch_04", "--report", str(report)], cwd=ROOT, check=True)
    assert (OUT / "batch_04" / "lp_ml1b2c_batch04_selectivity_first_ranking.csv").exists()
    assert (OUT / "batch_04" / "lp_ml1b2c_batch04_summary.json").exists()
    assert report.exists()
