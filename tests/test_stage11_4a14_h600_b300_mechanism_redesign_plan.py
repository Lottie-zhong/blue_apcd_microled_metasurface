import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_h600_b300_mechanism_redesign_plan_stage11_4a14.py"
REPORTS = ROOT / "reports"


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_manifest_has_bounded_distinct_plan():
    run_script()
    manifest = json.loads((REPORTS / "stage11_4a14_h600_b300_mechanism_manifest.json").read_text(encoding="utf-8"))
    assert manifest["planning_only"] is True
    assert manifest["no_fdtd"] is True
    assert manifest["height_nm"] == 600
    assert manifest["target_bin_deg"] == 300
    assert manifest["total_future_cases"] == 24
    assert manifest["total_future_cases"] <= manifest["max_future_cases"]


def test_candidate_space_groups_are_expected_and_distinct():
    run_script()
    rows = list(csv.DictReader((REPORTS / "stage11_4a14_h600_b300_mechanism_candidate_space.csv").open(encoding="utf-8")))
    assert [int(r["future_case_count"]) for r in rows] == [12, 6, 6]
    assert sum(int(r["future_case_count"]) for r in rows) == 24
    assert all("A10" in r["distinct_from_prior"] or "A11" in r["distinct_from_prior"] or "A12" in r["distinct_from_prior"] or "A8" in r["distinct_from_prior"] for r in rows)


def test_a8_b60_family_is_excluded_and_heavy_outputs_absent():
    run_script()
    manifest = json.loads((REPORTS / "stage11_4a14_h600_b300_mechanism_manifest.json").read_text(encoding="utf-8"))
    assert "B300_x_pair_swap_G80_O-40" in manifest["excluded_b60_donor_families"]
    text = (REPORTS / "stage11_4a14_h600_b300_mechanism_redesign_plan.md").read_text(encoding="utf-8")
    for token in ["outputs/", ".fsp", ".ldf", "monitor", "farfield"]:
        assert token not in text
