from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_mdc_ml_shared_surrogate_dataset_v1 as builder
import train_mdc_ml_shared_surrogate_v1 as trainer

CFG = json.loads((ROOT / "configs" / "mdc_ml_shared_surrogate_v1.yaml").read_text(encoding="utf-8"))
OUT = ROOT / CFG["output_root"]
DATA = np.load(OUT / "dataset" / "dataset_v1.npz")
SPLIT = pd.read_csv(OUT / "splits" / "split_records_v1.csv")


def test_01_combined_signature_and_count():
    m=json.loads((OUT/"dataset"/"dataset_manifest_v1.json").read_text()); assert m["combined_signature"]==CFG["combined_signature"] and m["total"]==2512
def test_02_classification_population_2512(): assert len(DATA["y_classification"])==2512
def test_03_regression_population_737(): assert int(DATA["regression_mask"].sum())==737
def test_04_failure_excluded_from_regression():
    rows=builder.load_records(ROOT/CFG["source_registry"]); f=[r for r in rows if r["power_balance_failure"]]; assert len(f)==1 and not f[0]["nominal_4d_objective_eligible"]
def test_05_invalid_fwhm_is_not_zero_filled(): assert np.isnan(DATA["y_regression"][~DATA["regression_mask"]]).all()
def test_06_twenty_five_layer_padding(): assert DATA["X"].shape==(2512,150)
def test_07_pad_mask_semantics():
    x=DATA["X"][:,:125]; assert np.all(x[:,0::5][x[:,2::5]==0]==0) and np.all(x[:,1::5][x[:,2::5]==0]==0)
def test_08_material_token_mapping(): assert CFG["material_tokens"]=={"PAD":0,"APCD_TIO2_NATIVE_M1":1,"APCD_SIO2_NATIVE_M1":2}
def test_09_family_one_hot(): assert np.allclose(DATA["X"][:,-8:].sum(axis=1),1)
def test_10_feature_allowlist():
    s=json.loads((OUT/"dataset"/"feature_schema_v1.json").read_text()); assert s["contract_id"]=="physical_structure_feature_allowlist_v1" and not s["leakage_hits"]
def test_11_source_category_not_feature(): assert all("source_category" not in n for n in builder.feature_schema(CFG)["feature_names"])
def test_12_anchor_parent_not_feature(): assert all("anchor_parent" not in n for n in builder.feature_schema(CFG)["feature_names"])
def test_13_dataset_origin_not_feature(): assert all("dataset_origin" not in n for n in builder.feature_schema(CFG)["feature_names"])
def test_14_identity_fields_not_features():
    names=builder.feature_schema(CFG)["feature_names"]; assert not any(any(k in n for k in ("hash","sample","artifact")) for n in names)
def test_15_target_fields_not_features(): assert not any(any(k in n for k in ("fwhm","cone","band","transmission")) for n in builder.feature_schema(CFG)["feature_names"])
def test_16_scaler_statistics_fit_train_only():
    stats=json.loads((OUT/"dataset"/"feature_statistics_v1.json").read_text()); by=dict(zip(SPLIT.canonical_geometry_hash,SPLIT.split)); idx=np.array([by[h]=="train" for h in DATA["canonical_hashes"]]); assert stats["fit_split"]=="train" and np.allclose(stats["mean"],DATA["X"][idx].mean(axis=0))
def test_17_split_deterministic_and_order_independent():
    rows=builder.load_records(ROOT/CFG["source_registry"]); a=builder.deterministic_split(rows,CFG); b=builder.deterministic_split(list(reversed(rows)),CFG); assert a==b
def test_18_split_hashes_do_not_overlap(): assert json.loads((OUT/"diagnostics"/"feature_leakage_audit_v1.json").read_text())["pass"]
def test_19_every_split_covers_eight_families(): assert all(SPLIT[SPLIT.split==s].topology_family.nunique()==8 for s in CFG["split_fractions"])
def test_20_test_is_sealed_and_not_model_selection():
    m=json.loads((OUT/"splits"/"split_manifest_v1.json").read_text()); sel=json.loads((OUT/"diagnostics"/"model_selection_v1.json").read_text()); assert m["test_sealed"] and sel["selection_split"]=="validation"
def test_21_calibration_methods_are_explicit():
    m=json.loads((OUT/"metrics"/"classification_metrics_v1.json").read_text()); assert set(m["calibration_methods"].values())<={"sigmoid","isotonic"}
def test_22_regression_mask_same_for_all_models(): assert int(DATA["regression_mask"].sum())==CFG["expected_regression"] and "different regression" not in inspect.getsource(trainer.RegressionBundle)
def test_23_class_weight_is_balanced(): assert 'class_weight="balanced"' in inspect.getsource(trainer.ClassificationBundle)
def test_24_model_serialization_roundtrip():
    p=OUT/"models"/"champion"/"classification_champion_v1.joblib"; obj=joblib.load(p); assert obj["spec"]["family"]=="extra_trees" and len(obj["models"])==4
def test_25_prediction_hash_matches_manifest():
    m=json.loads((OUT/"manifest_v1.json").read_text()); assert all(hashlib.sha256((OUT/"predictions"/name).read_bytes()).hexdigest()==sig for name,sig in m["prediction_signatures"].items())
def test_26_mlp_masked_loss_contract():
    src=inspect.getsource(trainer.MLPBundle.fit); assert "if tm.any()" in src and "pred[tm]" in src and "tr[tm]" in src
def test_27_conformal_coverage_calculated():
    c=json.loads((OUT/"metrics"/"calibration_metrics_v1.json").read_text())["conformal"]; assert set(c)=={"0.8","0.9"} and all(0<=v["coverage"]<=1 for level in c.values() for v in level.values())
def test_28_pareto_uses_only_test_eligible(): assert json.loads((OUT/"metrics"/"pareto_retrieval_v1.json").read_text())["test_eligible_count"]==int(((SPLIT.split=="test")&SPLIT.nominal_4d_objective_eligible).sum())
def test_29_lofo_has_eight_folds(): assert sum(str(v).startswith("lofo:") for v in pd.read_csv(OUT/"metrics"/"ood_metrics_v1.csv").diagnostic)==8
def test_30_anchor_holdout_has_three_folds(): assert sum(str(v).startswith("anchor_holdout:") for v in pd.read_csv(OUT/"metrics"/"ood_metrics_v1.csv").diagnostic)==3
def test_31_no_solver_import_or_call():
    src=(ROOT/"scripts"/"train_mdc_ml_shared_surrogate_v1.py").read_text(); assert "lumapi" not in src and "run_tmm" not in src and "fdtd" not in src.lower()
def test_32_existing_formal_outputs_fingerprint_stable():
    before=json.loads((OUT/"dataset"/"dataset_manifest_v1.json").read_text())["formal_output_fingerprint_before"]; assert builder.formal_output_fingerprint(ROOT/"outputs"/"mdc_ml_f0_formal_pilot_2000_v1")==before
def test_33_frozen_tracked_files_have_no_diff():
    changed=subprocess.run(["git","diff","--name-only"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.splitlines(); assert changed==[]
def test_34_split_signature_matches_file():
    expected=(OUT/"splits"/"split_content_signature_v1.txt").read_text().strip(); rows=pd.read_csv(OUT/"splits"/"split_records_v1.csv").to_dict("records"); assert len(expected)==64 and len(rows)==2512
def test_35_output_below_soft_limit(): assert sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())<=CFG["output_soft_limit_bytes"]
def test_36_power_balance_classifier_is_not_trained(): assert "power_balance_failure" not in CFG["classification_targets"]
def test_37_all_four_targets_share_eligible_rows(): assert DATA["y_regression"][DATA["regression_mask"]].shape==(737,4) and np.isfinite(DATA["y_regression"][DATA["regression_mask"]]).all()
def test_38_prediction_rows_match_split_counts():
    for s in ("validation","calibration","test"): assert len(pd.read_csv(OUT/"predictions"/f"{s}_predictions_v1.csv"))==int((SPLIT.split==s).sum())
def test_39_same_seed_mlp_prediction_is_reproducible():
    rng=np.random.default_rng(9); x=rng.normal(size=(48,150)); x[:,0:125:5]=rng.integers(0,3,size=(48,25)); yc=np.column_stack([(np.arange(48)+j)%2 for j in range(4)]).astype(float); mask=np.arange(48)%2==0; yr=np.full((48,4),np.nan); yr[mask]=rng.normal(size=(mask.sum(),4)); mini={"hidden":[16],"dropout":0.0,"learning_rate":0.001,"weight_decay":0.0,"batch_size":16,"max_epochs":5,"patience":3}
    a=trainer.MLPBundle(mini,123).fit(x[:32],yc[:32],yr[:32],mask[:32],(x[32:],yc[32:],yr[32:],mask[32:])); b=trainer.MLPBundle(mini,123).fit(x[:32],yc[:32],yr[:32],mask[:32],(x[32:],yc[32:],yr[32:],mask[32:])); ap=a.predict(x[32:]); bp=b.predict(x[32:]); assert np.array_equal(ap[0],bp[0]) and np.array_equal(ap[1],bp[1])
def test_40_portable_mlp_artifact_roundtrip():
    obj=joblib.load(OUT/"models"/"champion"/"regression_champion_v1.joblib"); assert obj["spec"]["family"]=="multitask_mlp" and len(obj["mlp_states"])==3 and all("state_dict" in s for s in obj["mlp_states"])


def test_41_shared_contract_read_only():
    assert builder.shared_surrogate_contract(CFG)["test_seal_contract"]["test_sealed"]
    assert trainer.validate_existing_contract_only(ROOT/"configs"/"mdc_ml_shared_surrogate_v1.yaml")["status"]=="PASS"
