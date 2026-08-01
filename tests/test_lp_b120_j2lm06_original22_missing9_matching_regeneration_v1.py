import csv,json
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML=ROOT/"outputs/lp_ml_dataset_v1"
def test_missing9_plan_and_exact18():
 d=json.loads((ML/"plans/b120_j2lm06_original22_missing9_matching_regeneration_plan_v1.json").read_text()); assert len(d["candidates"])==9; assert d["subrun_count"]==18; assert d["wavelength_nm"]==[450.0]
def test_regenerated_complete_jones_and_no_bounded6_fit():
 st=ML/"staging/b120_j2lm06_original22_missing9_matching_regeneration_v1"; assert len(list(st.glob("subruns/*/*/checkpoint.json")))==18; assert len(list(st.glob("candidates/*.json")))==9
 m=json.loads((ML/"analysis/b120_j2lm06_original22_full_jones_model_after_matching_regeneration_v1.json").read_text()); assert m["bounded6_fit_used"] is False
def test_replay_label_and_no_d9():
 r=json.loads((ML/"analysis/b120_j2lm06_bounded6_full_jones_retrospective_holdout_replay_v1.json").read_text()); assert r["label"]=="LEAKAGE_CONTROLLED_RETROSPECTIVE_EXTERNAL_REPLAY"; route=json.loads((ML/"analysis/b120_j2lm06_full_jones_diagnostic_and_d9_readiness_v1.json").read_text()); assert route["no_d9_generated"] is True
