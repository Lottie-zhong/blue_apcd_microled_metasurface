import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).parents[1]/"outputs/mdc_hf_surrogate_v2_m1_final_5seed_ensemble_v1/20260804T_final_m1_5seed_067c76b"

def test_final_authorization_membership_and_epoch():
 a=json.loads((ROOT/"final_m1_ensemble_training_authorization.json").read_text()); assert a["final_training_authorized"] and a["authorized_unique_final_fits"]==5 and a["training_geometry_count"]==96 and a["training_case_count"]==576
 m=json.loads((ROOT/"final_training_membership_audit.json").read_text()); assert m["status"]=="PASS" and m["geometry_count"]==96 and m["case_count"]==576 and m["cases_per_geometry"]==6
 e=json.loads((ROOT/"final_epoch_policy.json").read_text()); assert e["m1_oof_fit_count"]==15 and 1<=e["final_epoch_count"]<=400 and e["same_epoch_all_final_seeds"]

def test_exactly_five_fits_and_contract():
 l=pd.read_csv(ROOT/"final_training_fit_ledger.csv"); assert len(l)==5 and l.final_fit_id.nunique()==5 and set(l.seed)=={20260804,20260805,20260806,20260807,20260808}; assert set(l.final_epoch_count)=={3}
 c=json.loads((ROOT/"final_m1_architecture_contract.json").read_text()); assert c["inputs"]["direct_tmm_features"] is False and c["heads"]["latent"]["activation"]=="linear"

def test_replay_and_safety():
 r=json.loads((ROOT/"final_inference_reproducibility_audit.json").read_text()); assert r["status"]=="PASS" and r["all_compared_keys_equal"]
 s=json.loads((ROOT/"final_ensemble_safety_audit.json").read_text()); assert s["M1_unique_final_fits"]==5 and s["M2_unique_final_fits"]==0 and s["M3_unique_final_fits"]==0 and s["test40_reads"]==0 and s["sealed_test_reads"]==0 and s["FDTD_calls"]==0
 t=json.loads((ROOT/"test40_evaluation_readiness_metadata_audit.json").read_text()); assert t["status"]=="PASS_METADATA_ONLY" and t["metadata_reads"]==0 and t["value_reads"]==0
