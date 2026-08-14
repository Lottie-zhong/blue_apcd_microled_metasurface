import csv,json
from pathlib import Path
ROOT=Path(__file__).parents[1]
OUT=ROOT/"outputs/np_k6_m7_16g_forward_retraining_v1"
def test_authority_exact():
    rows=list(csv.DictReader((ROOT/"outputs/np_k6_m6_formal_development_merge_v1/formal_development_hf_observations_352rows.csv").open(encoding="utf-8")))
    assert len(rows)==352 and len({r["geometry_id"] for r in rows})==16
    assert len({(r["geometry_id"],r["polarization"]) for r in rows})==32
def test_g01_quarantine_only():
    rows=list(csv.DictReader((ROOT/"outputs/np_k6_m6_formal_development_merge_v1/formal_development_hf_observations_352rows.csv").open(encoding="utf-8")))
    assert not any("NP_K6_M6_PRIMARY4_G01" in r["case_id"] for r in rows)
def test_lf_and_oof():
    lf=json.loads((OUT/"lf_authority_completion.json").read_text())
    assert lf["coverage_complete"] and lf["geometry_count"]==16 and lf["rows"]==352
    assert len(lf["geometry_indices"])==16
    oof=list(csv.DictReader((OUT/"oof_predictions_16g.csv").open(encoding="utf-8")))
    assert len(oof)==9*352
def test_prereg_and_solver_zero():
    m=json.loads((OUT/"m7_training_run_manifest.json").read_text())
    s=json.loads((OUT/"solver_zero_audit.json").read_text())
    assert m["fit_started_after_preregistration"] is True
    assert all(int(s.get(k,0))==0 for k in ("fdtd_run_calls","lumapi_solver_run_calls","new_hf_acquisition","external_hf_calls","sealed_hf_target_reads","inverse_design"))
    assert int(s.get("checkpoint_count",0))==0
def test_external_metadata_only():
    e=json.loads((OUT/"external_set_readiness.json").read_text())
    assert e["metadata_only"] is True and e["external_target_reads"]==0 and e["sealed_target_reads"]==0
