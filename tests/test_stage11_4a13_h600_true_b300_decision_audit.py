import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_h600_true_b300_decision_audit_stage11_4a13.py"
REPORTS = ROOT / "reports"


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_decision_audit_outputs_expected_evidence():
    run_script()
    rows = list(csv.DictReader((REPORTS / "stage11_4a13_h600_true_b300_evidence_table.csv").open(encoding="utf-8")))
    assert len(rows) == 5
    by_id = {row["evidence_id"]: row for row in rows}
    assert by_id["A8_B60_DONOR"]["pass_level"] == "strict"
    assert by_id["A5_B240_LOOSE"]["pass_level"] == "loose"
    assert by_id["A12_G3_B300_FAIL"]["decision_use"] == "stop_H600_true_B300_blind_search"


def test_summary_blocks_coverage_and_k6():
    run_script()
    summary = json.loads((REPORTS / "stage11_4a13_h600_true_b300_summary.json").read_text(encoding="utf-8"))
    assert "do not run H600 coverage" in summary["decision"]
    assert "K=6" in summary["do_not_run"]
    assert summary["true_b300_failed_groups"] == ["A10 G1", "A11 G2", "A12 G3"]


def test_reports_do_not_reference_heavy_outputs():
    run_script()
    text = "\n".join(p.read_text(encoding="utf-8") for p in [REPORTS / "stage11_4a13_h600_true_b300_decision_audit.md", REPORTS / "stage11_4a13_h600_true_b300_recommended_next.md"])
    for token in ["outputs/", ".fsp", ".ldf", "monitor", "farfield"]:
        assert token not in text
