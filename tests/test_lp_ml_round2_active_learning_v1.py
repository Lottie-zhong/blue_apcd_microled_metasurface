from pathlib import Path
import csv,json
R=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
def j(p):return json.loads((R/p).read_text())
def c(p):
 with (R/p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def test_round2_execution_and_merge_contract():
 s=j("outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round2_active_learning_attempt1_v1/final_sentinel_v1.json");assert s["entered"]==128 and s["accepted"]==128 and s["quarantined_count"]==0
 p=c("outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv");assert len(p)==64
 from collections import Counter
 assert Counter(x["category"] for x in p)==Counter({"HIGH_UNCERTAINTY":20,"LOW_PHASE_AND_SIX_BIN_COVERAGE":16,"PROJECTOR_FAVORABLE_TRADEOFF":12,"BOUNDARY_AND_HIGH_GRADIENT":8,"DIVERSITY_CONTROLS":8})
 m=c("outputs/lp_ml_dataset_v1/lp_ml_dataset_v1_round2_complete_319_geometry_2871_rows.csv");assert len(m)==2871 and len({x["candidate_id"] for x in m})==319 and "LPML_R1_GLOBAL_SOBOL_054" not in {x["candidate_id"] for x in m}
 assert sorted({float(x["wavelength_nm"]) for x in m if x["round_origin"].startswith("ROUND2")})==[450+i*.5 for i in range(9)]
def test_round2_model_and_no_future_solver():
 q=j("outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_quality_audit_v1.json");assert q["complete_jones"] and q["duplicate_rows"]==0 and q["duplicate_geometry_hashes"]==0 and q["model_filled_rows"]==0 and not q["round3_solver_authorized"] and not q["inverse_design_fdt_authorized"]
 o=j("outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_outcome_v1.json");assert o["prospective_evaluation_before_retraining"] and o["outcome"].startswith("LP_ML_ROUND2_")
 f=j("outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_fresh_models_and_metrics_v1.json");assert f["from_scratch"] and not f["warm_start"] and all(k in f["models"] for k in ["ExtraTrees","HistGradientBoosting","SimpleMLP","residual_mlp_5seed"])
 cs=j("outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_checksums_v1.json");assert len(cs)==7
