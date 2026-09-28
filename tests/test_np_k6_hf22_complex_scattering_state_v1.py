import json, csv, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/np_k6_hf22_complex_scattering_state_extraction_v1"

def test_complex_manifest_zero_solver_and_counts():
    m=json.loads((OUT/"complex_extraction_manifest.json").read_text(encoding="utf-8"))
    assert m["solver_run_calls"]==0
    assert m["save_calls"]==0
    assert m["case_count"]==44
    assert m["spectral_rows"]==484
    assert m["load_only"] is True

def test_complex_availability_complete():
    a=json.loads((OUT/"complex_availability_matrix.json").read_text(encoding="utf-8"))["availability"]
    assert len(a)==44
    assert all(x["load_ok"] and x["complex_eh_complete"] and x["gratingvector_ok"] and x["wavelength_count"]==11 for x in a)

def test_modal_closure_and_order_schema():
    with (OUT/"complex_power_closure_long.csv").open(encoding="utf-8-sig",newline="") as f: c=list(csv.DictReader(f))
    with (OUT/"complex_scattering_state_long.csv").open(encoding="utf-8-sig",newline="") as f: s=list(csv.DictReader(f))
    assert len(c)==968
    assert len(s)>=44*11*7
    assert max(abs(float(r["modal_minus_formal"])) for r in c)<1e-6
    assert all(math.isfinite(float(r["absolute_efficiency"])) for r in s)
    assert all(int(r["order_m"]) in range(-5,6) for r in s)
