from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage11_lp_hnew_fixed_height_scout_stage11_4a1.py"
spec = importlib.util.spec_from_file_location("stage11_4a1", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def synthetic_templates() -> dict[str, dict[str, str]]:
    return {
        cid: {
            "dimer_case_id": cid,
            "candidate_id": cid,
            "p_x_nm": "431.907786",
            "p_y_nm": "432.000000",
            "geometry_legal": "true",
        }
        for cid in mod.TEMPLATE_BY_BIN.values()
    }


def test_planned_case_count_and_scope(monkeypatch):
    monkeypatch.setattr(mod, "load_template_rows", synthetic_templates)
    rows = mod.planned_case_rows()
    assert len(rows) == 42
    assert {int(float(r["height_nm"])) for r in rows} == {600, 650, 700}
    assert {int(float(r["wavelength_nm"])) for r in rows} == {451, 452, 453}
    assert {int(r["phase_bin_deg"]) for r in rows if int(float(r["height_nm"])) == 700} == {240, 300}


def test_pass_level_gates():
    assert mod.pass_level(6.0, 0.45, 0.50, 25.0) == "strict"
    assert mod.pass_level(3.0, 0.10, 1.00, 35.0) == "loose"
    assert mod.pass_level(2.9, 0.50, 0.20, 5.0) == "fail"


def test_result_fields_are_required_columns():
    for key in ["case_id", "height_nm", "wavelength_nm", "phase_bin_deg", "candidate_id", "target_Tx", "y_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg", "matrix_error", "pass_level", "result_csv", "status"]:
        assert key in mod.RESULT_FIELDS
