import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_h650_b300_escape_hatch_plan_stage11_4a16.py"
REPORTS = ROOT / "reports"


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_manifest_is_h650_only_and_bounded():
    run_script()
    manifest = json.loads((REPORTS / "stage11_4a16_h650_b300_escape_hatch_manifest.json").read_text(encoding="utf-8"))
    assert manifest["planning_only"] is True
    assert manifest["no_fdtd"] is True
    assert manifest["height_nm"] == 650
    assert manifest["target_bin_deg"] == 300
    assert manifest["total_future_cases"] == 18
    assert manifest["total_future_cases"] <= manifest["max_future_cases"]
    assert manifest["exclude_h600_b60_donor_forcing"] is True


def test_candidate_space_groups_are_expected():
    run_script()
    rows = list(csv.DictReader((REPORTS / "stage11_4a16_h650_b300_escape_hatch_candidate_space.csv").open(encoding="utf-8")))
    assert [row["group_id"] for row in rows] == ["S11_4A16_G1_H650_B300_DIRECT_ESCAPE", "S11_4A16_G2_H650_B300_MINI_REPAIR"]
    assert [int(row["future_case_count"]) for row in rows] == [12, 6]
    assert {int(row["height_nm"]) for row in rows} == {650}


def test_plan_excludes_forbidden_routes_and_heavy_outputs():
    run_script()
    manifest = json.loads((REPORTS / "stage11_4a16_h650_b300_escape_hatch_manifest.json").read_text(encoding="utf-8"))
    assert "coverage" in manifest["do_not_run"]
    assert "H600 rerun" in manifest["do_not_run"]
    assert "K=6" in manifest["do_not_run"]
    text = (REPORTS / "stage11_4a16_h650_b300_escape_hatch_plan.md").read_text(encoding="utf-8")
    for token in ["outputs/", ".fsp", ".ldf", "monitor", "farfield"]:
        assert token not in text
