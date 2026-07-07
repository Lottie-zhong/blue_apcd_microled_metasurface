from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b2d_0283_reassignment_plan.py"
OUT = ROOT / "outputs" / "lp_ml1b2d_0283_refinement"
METRICS = OUT / "lp_ml1b2d_0283_reassignment_metrics.csv"
PLAN = OUT / "lp_ml1b2d_0283_local_refinement_plan.csv"
SUMMARY = OUT / "lp_ml1b2d_0283_summary.json"
REPORT = ROOT / "reports" / "lp_ml1b2d_0283_reassignment_and_refinement_plan.md"


def test_0283_reassignment_and_plan_outputs():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    assert METRICS.exists()
    assert PLAN.exists()
    assert SUMMARY.exists()
    assert REPORT.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["candidate_id"] == "LPML1A4_0283_B240_exploration_B240_H650"
    assert summary["reassignment_label"] == "strong_B120_reassigned_seed"
    assert summary["reassigned_bin"] == 120
    assert summary["nearest_bin_stability_count"] == 1
    assert summary["no_fdtd_run"] is True

    metric_rows = list(csv.DictReader(METRICS.open(newline="", encoding="utf-8")))
    assert len(metric_rows) == 9
    assert {row["nearest_bin_deg"] for row in metric_rows} == {"120"}

    plan_rows = list(csv.DictReader(PLAN.open(newline="", encoding="utf-8")))
    assert 12 <= len(plan_rows) <= 18
    assert all(row["geometry_valid"] == "true" for row in plan_rows)
    assert all(row["intended_reassigned_bin"] == "120" for row in plan_rows)

    text = REPORT.read_text(encoding="utf-8")
    assert "not a B240 success" in text
    assert "No FDTD" in text
