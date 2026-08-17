from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "np_k6_m9a_normal_incidence_plateau_reassessment_v1"
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def test_m9a_prereg_precedes_derived_outputs():
 p=OUT/"NP_K6_M9A_PLATEAU_REASSESSMENT_PREREG_V1.json"
 assert sha(p)==json.loads((OUT/"preregistration_sha256.json").read_text())["sha256"]
def test_exact_hf22_authority():
 with (ROOT/"outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv").open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
 assert len(rows)==484 and len({r["geometry_id"] for r in rows})==22 and len({(r["geometry_id"],r["polarization"]) for r in rows})==44
 assert sorted({int(float(r["wavelength_nm"])) for r in rows})==list(range(445,456))
 assert all(r["quality_gate_pass"]=="true" and r["diagnostic_only"]=="false" and r["bulk_mdc_compatible"]=="false" and r["accepted_execution"] in ("true", "") for r in rows)
def test_solver_external_sealed_zero():
 z=json.loads((OUT/"solver_zero_audit.json").read_text())
 assert all(z[k]==0 for k in ["fdtd_run_calls","rcwa_run_calls","lumapi_solver_run_calls","new_development_hf","external_hf","sealed_hf_target_reads","inverse_design"])
def test_capability_and_angular_scope():
 d=json.loads((OUT/"capability_matrix.json").read_text())
 assert len(d["rows"])==99
 assert all(r["status"]=="NOT_SUPPORTED" for r in d["rows"] if r["dimension"]=="K_angular_generalization")
 assert json.loads((OUT/"decision.json").read_text())["status"]=="NP_K6_M9A_NORMAL_INCIDENCE_SCREENING_FROZEN_WAIT_COUPLING_ANGULAR_HANDOFF"
def test_external_hold_and_historical_plateau():
 e=json.loads((OUT/"external_hf_disposition.json").read_text()); p=json.loads((OUT/"provenance_audit.json").read_text())
 assert e["status"]=="HOLD" and e["target_reads"]==0
 assert p["historical_m9_status_preserved"]=="NP_K6_M9_22G_FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED"
