import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parents[1] / "outputs/mdc_hf_surrogate_v2_oof_model_selection_v1/20260804T_oof_model_selection_08915e7"

def test_oof_contract_counts_and_roles():
    auth=json.loads((ROOT/"oof_model_training_authorization.json").read_text())
    assert auth["expected_unique_neural_fits"] == 45
    ledger=pd.read_csv(ROOT/"oof_training_fit_ledger.csv")
    assert len(ledger)==45 and ledger.fit_id.nunique()==45
    assert set(ledger.architecture)=={"M1","M2","M3"}

def test_oof_membership_and_fresh_replay():
    m=json.loads((ROOT/"oof_training_membership_audit.json").read_text())
    assert m["geometry_count"]==96 and m["case_count"]==576 and m["all_six_cases_together"]
    r=json.loads((ROOT/"oof_inference_replay_audit.json").read_text())
    assert r["status"]=="PASS" and r["winner_match"]

def test_safety_guards_and_predictions():
    s=json.loads((ROOT/"oof_safety_audit.json").read_text())
    assert all(s[k]==0 for k in ["HF15_formal_label_reads","HF15_diagnostics_reads","sealed_test_reads","test40_reads","FDTD_calls","RCWA_calls","NP_solver_calls"])
    for a in ["m1","m2","m3"]:
        assert len(pd.read_parquet(ROOT/f"oof_case_predictions_{a}.parquet"))==576*3
        assert len(pd.read_parquet(ROOT/f"oof_geometry_predictions_{a}.parquet"))==96
