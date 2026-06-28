from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/stage_r1c2_rcled_c2_focused_refinement.py"
OUT = ROOT / "outputs/r1c2_rcled_c2_focused_refinement"


def test_r1c2_scope_and_candidates():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "R1C2_RCLED_C2_focused_refinement" in text
    for cid in ["C2_base", "C2_cav210", "C2_cav230", "C2_TiO2_40", "C2_TiO2_60"]:
        assert cid in text
    assert "WAVELENGTHS = [450.0, 453.0, 456.0]" in text
    assert '"bottom_pair_count": 0' in text


def test_no_forbidden_integration_builders():
    text = SCRIPT.read_text(encoding="utf-8")
    for token in ["Stage11", "Stage12", "addpoly"]:
        assert token not in text
    assert "fdtd.set(\"dimension\", \"2D\")" in text
    assert "fdtd.set(\"theta\", 90)" in text and "fdtd.set(\"phi\", 0)" in text
    assert "No forbidden integration" not in text
    assert "RCLED_bottom_reflector_group" in text


def test_outputs_if_present():
    result = OUT / "r1c2_refinement_results.csv"
    if not result.exists():
        return
    rows = list(csv.DictReader(result.open(newline="", encoding="utf-8")))
    assert len(rows) == 15
    assert {r["candidate_id"] for r in rows} == {"C2_base", "C2_cav210", "C2_cav230", "C2_TiO2_40", "C2_TiO2_60"}
    assert {r["wavelength_nm"] for r in rows} == {"450.0", "453.0", "456.0"}
    for r in rows:
        assert r["status"] in {"ok", "reused"}
        assert "eta20" in r and "peak_abs_angle_deg" in r and "dominant_zone" in r
        assert float(r["peak_abs_angle_deg"]) >= 0.0
