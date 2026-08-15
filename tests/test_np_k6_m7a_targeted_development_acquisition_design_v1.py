import csv,json
from pathlib import Path
ROOT=Path(__file__).parents[1]
OUT=ROOT/"outputs/np_k6_m7a_targeted_development_acquisition_design_v1"
def test_prereg_hash_and_order():
    p=json.loads((OUT/"preregistration_sha256.json").read_text()); assert p["sha256"]==__import__("hashlib").sha256((OUT/"NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1.json").read_bytes()).hexdigest(); assert p["solver_calls"]==0
def test_universe_and_roles():
    s=json.loads((OUT/"selection_manifest.json").read_text()); assert s["candidate_universe_size"]==31; assert len(s["Primary4"])==4; assert {x["acquisition_role"] for x in s["Primary4"]}=={"RESIDUAL-TAIL","RANKING-CHAMPION-STRESS","POLARIZATION-STRESS","COVERAGE-CONTROL"}; assert len(s["backups"])>=8
def test_boundaries_and_order():
    rows=list(csv.DictReader((OUT/"candidate_acquisition_features.csv").open(encoding="utf-8"))); assert not any(r["geometry_id"]=="K6X_D110_D125_D130_D135_D140_D175" for r in rows); assert all(all(float(r[f"D{i}"])<=float(r[f"D{i+1}"]) for i in range(1,6)) for r in rows)
def test_prediction_and_audits():
    rows=list(csv.DictReader((OUT/"candidate_acquisition_features.csv").open(encoding="utf-8"))); assert len(rows)==31; assert all(k in rows[0] for k in ("calibrated_eta_plus1","ridge_eta_plus1","residual_mlp_eta_plus1","cnn_eta_plus1","ranking_ambiguity_score")); assert len(list(csv.DictReader((OUT/"candidate_predictions_long.csv").open(encoding="utf-8"))))==31*22
def test_zero_solver_and_decision():
    z=json.loads((OUT/"solver_zero_audit.json").read_text()); d=json.loads((OUT/"m7a_decision.json").read_text()); assert all(z[k]==0 for k in ("fdtd_run_calls","lumapi_solver_run_calls","new_hf_acquisition","external_hf_calls","sealed_hf_target_reads","inverse_design","checkpoint_count")); assert d["external_HF_authorized"] is False
