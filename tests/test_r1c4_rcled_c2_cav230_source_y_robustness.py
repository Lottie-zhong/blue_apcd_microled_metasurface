from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/stage_r1c4_rcled_c2_cav230_source_y_robustness.py"
OUT = ROOT / "outputs/r1c4_rcled_c2_cav230_source_y_robustness"


def test_r1c4_scope_and_matrix():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "R1C4_RCLED_C2_cav230_source_y_robustness" in text
    assert "ROOT = Path(r\"D:\\project\\worktrees\\blue_apcd_rcled_mdc\")" in text
    assert "SOURCE_Y_OFFSETS_NM = [-40.0, -20.0, 0.0, 20.0, 40.0]" in text
    assert "WAVELENGTHS = [450.0, 453.0, 456.0]" in text
    assert "CAVITY_SPAN_NM = 230.0" in text
    assert "TERMINATION = \"TiO2_50nm\"" in text


def test_no_forbidden_integration_builders():
    text = SCRIPT.read_text(encoding="utf-8")
    for token in ["Stage11", "Stage12", "B4INT", "addpoly"]:
        assert token not in text
    assert "fdtd.set(\"dimension\", \"2D\")" in text
    assert "fdtd.set(\"theta\", 90)" in text and "fdtd.set(\"phi\", 0)" in text
    assert "BOTTOM_PAIR_COUNT = 0" in text


def test_outputs_if_present():
    result = OUT / "r1c4_source_y_results.csv"
    if not result.exists():
        return
    rows = list(csv.DictReader(result.open(newline="", encoding="utf-8")))
    assert len(rows) == 15
    assert {r["source_y_offset_nm"] for r in rows} == {"-40.0", "-20.0", "0.0", "20.0", "40.0"}
    assert {r["wavelength_nm"] for r in rows} == {"450.0", "453.0", "456.0"}
    for r in rows:
        assert r["status"] in {"ok", "reused"}
        assert "eta20" in r and "peak_abs_angle_deg" in r and "dominant_zone" in r
