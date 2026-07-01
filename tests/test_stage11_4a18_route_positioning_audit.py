import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_route_positioning_audit_stage11_4a18.py"
REPORTS = ROOT / "reports"


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_route_positioning_decision_blocks_lp_k6_and_coverage():
    run_script()
    summary = json.loads((REPORTS / "stage11_4a18_lp_route_positioning_summary.json").read_text(encoding="utf-8"))
    assert "Stop LP-Hnew six-bin" in summary["decision"]
    assert "LP K=6" in summary["do_not_enter"]
    assert "coverage" in summary["do_not_enter"]
    assert summary["recommended_next_project_priority"] == "CP/RCLED mainline"


def test_evidence_table_keeps_partial_evidence_and_failures():
    run_script()
    rows = list(csv.DictReader((REPORTS / "stage11_4a18_lp_route_positioning_evidence_table.csv").open(encoding="utf-8")))
    assert len(rows) == 4
    by_id = {r["evidence_id"]: r for r in rows}
    assert by_id["A8_B60_DONOR"]["pass_level"] == "strict"
    assert by_id["A5_B240_LOOSE"]["pass_level"] == "loose"
    assert by_id["A15_H600_B300_FAIL"]["nearest_actual_bins"] == "0;60"
    assert by_id["A17_H650_B300_FAIL"]["decision_use"] == "stop_LP_Hnew_sixbin_attempt"


def test_reports_do_not_reference_heavy_outputs():
    run_script()
    text = (REPORTS / "stage11_4a18_lp_route_positioning_audit.md").read_text(encoding="utf-8")
    for token in ["outputs/", ".fsp", ".ldf", "monitor", "farfield"]:
        assert token not in text
