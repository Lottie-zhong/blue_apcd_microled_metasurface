from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b2e_0283_local_refinement_scout01.py"
PLAN = ROOT / "outputs" / "lp_ml1b2d_0283_refinement" / "lp_ml1b2d_0283_local_refinement_plan.csv"


def load_module():
    spec = importlib.util.spec_from_file_location("b2e", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_scout_selection_exactly_8_and_required_families():
    m = load_module()
    rows = m.select_scout_rows(PLAN)
    assert len(rows) == 8
    assert all(r["geometry_valid"].lower() == "true" for r in rows)
    families = [r["refinement_family"] for r in rows]
    assert families.count("reassigned_B120_cleanup") == 5
    assert families.count("phase_tuning_scout") == 1
    assert families.count("fabrication_friendly_H_check") == 2
    assert {r["H_nm"] for r in rows if r["refinement_family"] == "fabrication_friendly_H_check"} == {"600.000000", "500.000000"}


def test_rank_results_classifies_projector_seed():
    m = load_module()
    selected = m.select_scout_rows(PLAN)
    keep = [selected[0], next(r for r in selected if r["candidate_id"] == "LPML1B2D_B2D_0283_C02")]
    rows, runtime = [], []
    for meta in keep:
        for wl in m.WAVELENGTHS:
            rows.append({"candidate_id": meta["candidate_id"], "wavelength_nm": wl, "status": "ok", "selected_Tx": "0.90", "conversion_to_leakage_ratio": "12.0", "matrix_error": "0.20", "phase_error_deg": "10.0" if wl == 452 else "12.0", "nearest_bin_deg": "120"})
            runtime.append({"candidate_id": meta["candidate_id"], "runtime_sec": "1.0"})
    ranked = m.rank_results(rows, runtime, keep)
    assert {r["b2c_style_class"] for r in ranked} == {"strong_B120_refined_seed"}
