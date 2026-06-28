from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage11_lp_hnew_height_wavelength_inventory_stage11_4a0.py"
spec = importlib.util.spec_from_file_location("stage11_4a0", SCRIPT)
stage11_4a0 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(stage11_4a0)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_manifest_fixed_height_rules(tmp_path: Path) -> None:
    paths = stage11_4a0.write_reports(tmp_path)
    data = json.loads(paths["manifest"].read_text(encoding="utf-8"))

    assert data["no_fdtd_run_in_stage11_4a0"] is True
    assert data["mixed_height_tuple_allowed"] is False
    assert data["primary_heights"] == [600, 650]
    assert data["deferred_heights"] == [550, 750]


def test_h700_only_priority_bins(tmp_path: Path) -> None:
    paths = stage11_4a0.write_reports(tmp_path)
    rows = read_csv(paths["candidate_space"])
    h700 = [row for row in rows if row["height_nm"] == "700"]

    assert {row["phase_bin_hint_deg"] for row in h700} == {"240", "300"}
    assert all(row["planned_status"] == "included" for row in h700)


def test_planned_cases_are_exact_groups(tmp_path: Path) -> None:
    paths = stage11_4a0.write_reports(tmp_path)
    rows = read_csv(paths["planned_cases"])

    assert [row["case_group_id"] for row in rows] == [
        "S11_4A1_H600_ALL",
        "S11_4A1_H650_ALL",
        "S11_4A1_H700_240_300",
        "DEFER_H550",
        "DEFER_H750",
    ]


def test_reports_avoid_heavy_file_terms(tmp_path: Path) -> None:
    paths = stage11_4a0.write_reports(tmp_path)
    forbidden = ["outputs/", ".fsp", ".ldf", ".log", "monitor", "farfield"]

    for path in paths.values():
        text = path.read_text(encoding="utf-8").lower()
        assert not any(term in text for term in forbidden), path
