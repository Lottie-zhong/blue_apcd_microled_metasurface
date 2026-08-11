import csv, json, re
from pathlib import Path

ROOT=Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs"/"np_k6_m5b_forward_formulation_repair_v1"

def test_m5b_validator_passed():
    report=json.loads((OUT/"m5b_validator_report.json").read_text(encoding="utf-8"))
    assert report["status"]=="PASS"
    assert report["solver_calls"]==0

def test_eta_plus1_schema_is_symbolic():
    s=json.loads((OUT/"NP_K6_AUTHORITATIVE_OUTPUT_SCHEMA_V1.json").read_text(encoding="utf-8"))
    assert s["eta_plus1_symbolic_key"]=="eta_m+1"
    assert s["primary_vector"].index("eta_m+1")==5

def test_residual_reconstruction_contract():
    a=json.loads((OUT/"m5b_residual_reconstruction_audit.json").read_text(encoding="utf-8"))
    assert a["corrected_formula"]=="eta_hat=LF_eta+delta_hat"
    assert a["no_refit_reconstruction_performed"] is True

def test_oof_pairing_and_variants():
    rows=list(csv.DictReader((OUT/"m5b_refit_candidate_oof.csv").open(encoding="utf-8-sig",newline="")))
    assert len({(r["case_id"],r["wavelength_nm"]) for r in rows})==286
    assert {r["variant"] for r in rows}=={"raw","constrained"}
    assert "corrected_residual_mlp" in {r["model"] for r in rows}

def test_active_pipeline_has_no_literal_eta_index():
    src=(ROOT/"scripts"/"np_k6_m5b_refit_v1.py").read_text(encoding="utf-8")
    assert not re.search(r"a\[ix,\s*[45]\]",src)
    assert "eta_plus_idx" in src
