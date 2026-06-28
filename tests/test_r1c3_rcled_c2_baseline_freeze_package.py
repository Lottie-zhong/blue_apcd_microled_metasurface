from pathlib import Path
import csv, json
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/stage_r1c3_rcled_c2_baseline_freeze_package.py"
OUT = ROOT / "outputs/r1c3_rcled_c2_baseline_freeze_package"
INDEX = ROOT / "reports/rcled_mdc_workspace_index.md"

def test_script_scope():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "R1C3_RCLED_C2_baseline_freeze_package" in text
    assert "R1C2_C2_cav230" in text
    assert "R1C2_C2_base" in text
    assert "not yet run" in text

def test_outputs_if_present():
    path = OUT / "r1c3_frozen_baseline.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    p = data["primary_frozen_baseline"]
    assert p["candidate_id"] == "R1C2_C2_cav230"
    assert p["top_pair_count"] == 6
    assert p["bottom_pair_count"] == 0
    assert p["cavity_span_nm"] == 230
    assert p["termination"] == "TiO2_50nm"
    assert data["backup_candidate"]["candidate_id"] == "R1C2_C2_base"
    assert data["apcd_integration"] == "not yet run"

def test_csv_and_index_if_present():
    path = OUT / "r1c3_frozen_baseline.csv"
    if path.exists():
        rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
        assert rows[0]["candidate_id"] == "R1C2_C2_cav230"
    if INDEX.exists():
        text = INDEX.read_text(encoding="utf-8")
        assert "R1C2_C2_cav230" in text
        assert "R1C3 freeze status" in text
