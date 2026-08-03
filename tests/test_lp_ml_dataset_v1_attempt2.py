from pathlib import Path
import csv,json,hashlib
R=Path(__file__).resolve().parents[1]; P=R/"outputs/lp_ml_dataset_v1/plans"; A=R/"outputs/lp_ml_dataset_v1/analysis"; S=R/"outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_smoke_attempt2_v1"
def rows(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def test_attempt2_preflight_sampling_gate():
    d=json.loads((A/"lp_ml_dataset_v1_round1_smoke_attempt2_preflight_sampling_gate_v1.json").read_text())
    assert d["preflight_reload_gate"]["pass"] is True
    c=d["preflight_reload_gate"]["checks"]
    assert c["T_frequency_points"]==9 and c["field_frequency_points"]==9
    assert c["T_use_wavelength_spacing"]==1 and c["field_use_wavelength_spacing"]==1
    assert c["T_use_source_limits"]==1 and c["field_use_source_limits"]==1
    assert d["wavelengths_nm"]==[450.0,450.5,451.0,451.5,452.0,452.5,453.0,453.5,454.0]
def test_attempt2_full_accounting_and_rows():
    s=json.loads((S/"final_sentinel_v1.json").read_text()); q=json.loads((S/"quality_audit_v1.json").read_text())
    assert s["outcome"]=="LP_ML_PIPELINE_SMOKE_PASS_READY_FOR_ROUND1_PRODUCTION"
    assert (s["planned_geometries"],s["entered_subruns"],s["accepted_subruns"],s["complete_jones_geometries"],s["spectral_rows"])==(16,32,32,16,144)
    assert s["duplicate_physics_rows"]==0 and s["model_filled_rows"]==0
    assert q["missing_subruns"]==0 and q["failed_subruns"]==0
    assert len(rows(S/"candidate_wavelength_jones_v1.csv"))==144
    assert len(rows(S/"geometry_records_v1.csv"))==16 and len(rows(S/"subrun_records_v1.csv"))==32
def test_attempt2_supersession_and_no_old_ingestion():
    d=json.loads((A/"lp_ml_dataset_v1_attempt_supersession_ledger_v1.json").read_text()); old=d["old_attempt"]; new=d["new_attempt"]
    assert old["entered"]==1 and old["accepted"]==0 and old["returned_frequency_count"]==5 and old["admitted_physics_rows"]==0
    assert old["ingestion_status"]=="EXCLUDED_NO_FORMAL_PHYSICS" and new["new_accounting_separate"] is True and new["no_overwrite"] is True
def test_attempt2_checksums_and_no_heavy():
    m=json.loads((S/"checksums_v1.json").read_text())
    for rel,h in m["files"].items(): assert hashlib.sha256((S/rel).read_bytes()).hexdigest()==h
    assert not [p for p in S.rglob("*") if p.suffix.lower() in {".fsp",".fspx",".ldf",".log",".h5",".mat",".npy",".npz"}]
