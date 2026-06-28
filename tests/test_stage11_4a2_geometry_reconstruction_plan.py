from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage11_lp_fixed_height_geometry_reconstruction_plan_stage11_4a2.py"
spec = importlib.util.spec_from_file_location("stage11_4a2", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_plan_stays_under_case_budget():
    rows = mod.plan_rows()
    assert mod.total_cases(rows) == 96
    assert mod.total_cases(rows) <= 96


def test_plan_scope_excludes_h500_and_h700_full_sweep():
    rows = mod.plan_rows()
    heights = {int(r["height_nm"]) for r in rows}
    assert 500 not in heights
    assert 700 not in heights
    assert heights == {600, 650}
    h650_rows = [r for r in rows if int(r["height_nm"]) == 650]
    assert len(h650_rows) == 1
    assert h650_rows[0]["phase_bin_deg"] == "240;300"


def test_priority_order_and_triggers():
    rows = mod.plan_rows()
    assert rows[0]["phase_bin_deg"] == "240"
    assert rows[0]["priority"] == "primary"
    assert rows[1]["phase_bin_deg"] == "300"
    assert "if H600" in rows[-1]["trigger"]


def test_manifest_declares_planning_boundaries():
    rows = mod.plan_rows()
    manifest = mod.build_manifest(rows, {"stage11_4a1_facts": "synthetic"})
    assert manifest["planning_only"] is True
    assert manifest["no_fdtd_run"] is True
    assert manifest["no_lumerical_run"] is True
    assert manifest["no_k6_metagrating"] is True
    assert manifest["primary_height_nm"] == 600
    assert manifest["secondary_optional_height_nm"] == 650
    assert manifest["excluded_heights_nm"] == [500, 700]


def test_generated_reports_have_expected_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(mod, "PLAN_MD", tmp_path / "plan.md")
    monkeypatch.setattr(mod, "CANDIDATE_SPACE_CSV", tmp_path / "space.csv")
    monkeypatch.setattr(mod, "MANIFEST_JSON", tmp_path / "manifest.json")
    monkeypatch.setattr(mod, "SUMMARY_JSON", tmp_path / "summary.json")
    rows = mod.plan_rows()
    manifest = mod.build_manifest(rows, {"ok": True})
    mod.write_csv(mod.CANDIDATE_SPACE_CSV, rows)
    mod.MANIFEST_JSON.write_text(json.dumps(manifest), encoding="utf-8")
    mod.write_md(rows, manifest)
    with mod.CANDIDATE_SPACE_CSV.open("r", encoding="utf-8", newline="") as handle:
        loaded = list(csv.DictReader(handle))
    assert len(loaded) == 4
    assert "K=6 remains blocked" in mod.PLAN_MD.read_text(encoding="utf-8")
