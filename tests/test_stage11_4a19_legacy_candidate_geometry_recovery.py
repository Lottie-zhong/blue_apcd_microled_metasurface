import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_legacy_candidate_geometry_recovery_stage11_4a19.py"


def test_parse_suffix():
    ns = {"__file__": str(SCRIPT)}
    exec(SCRIPT.read_text(encoding="utf-8-sig"), ns)
    parsed = ns["parse_suffix"]("H500DIMER12D_004_B300_x_pair_swap_G80_O-40")
    assert parsed["target_bin"] == "B300"
    assert parsed["axis"] == "x"
    assert parsed["pair_swap"] == "true"
    assert parsed["G_nm"] == "80"
    assert parsed["O_nm"] == "-40"


def test_recovery_outputs_have_required_columns():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    table = ROOT / "reports" / "stage11_4a19_legacy_candidate_geometry_recovery_table.csv"
    with table.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    required = {"candidate_id", "base_candidate_id", "H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "gap_or_dx_nm", "pair_swap", "axis", "G_nm", "O_nm", "transform_rule", "evidence_file", "evidence_type", "confidence", "status"}
    assert rows
    assert required.issubset(rows[0])
    assert any(r["candidate_id"] == "H500DIMER2D_006_B240_x_pair_swap_G80_O-30" for r in rows)


def test_summary_and_reports_exist():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    summary = ROOT / "reports" / "stage11_4a19_legacy_candidate_geometry_summary.json"
    report = ROOT / "reports" / "stage11_4a19_legacy_candidate_geometry_report.md"
    next_file = ROOT / "reports" / "stage11_4a19_legacy_candidate_geometry_recommended_next.md"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert "recovered_count" in data
    assert "h500_six_seed_recovery" in data
    assert data["no_fdtd_lumerical_run"] is True
    assert "No FDTD or Lumerical" in report.read_text(encoding="utf-8")
    assert next_file.exists()


