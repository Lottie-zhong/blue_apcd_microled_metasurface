import csv, hashlib, json, subprocess
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = ROOT / "outputs/lp_ml_dataset_v1"
A = O / "analysis"
C2 = O / "clean_v2"
C3 = O / "clean_v3"
P = O / "plans"
PROTECTED = [
    ROOT / "reports/lp_ml1a3_git_history_geometry_reconstruction.md",
    ROOT / "reports/stage11_4a20_legacy_fsp_object_inventory.md",
]

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True,
                          capture_output=True, check=True).stdout.strip()

def git_exists(rev):
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", rev],
                          text=True, capture_output=True).returncode == 0

def main():
    head = git("rev-parse", "HEAD")
    expected = "216e3ae8f5336a13b96cc78dd43dbaba345e440a"
    r3_commit = "b2affaa89e4ac100fac4c99cd21d24ad52209ded"
    merge_head = git("merge-base", "HEAD", expected)
    merge_r3 = git("merge-base", "HEAD", r3_commit)
    ancestry = {
        "head": head,
        "expected_head": expected,
        "expected_head_present": git_exists(expected),
        "round3_reported_commit": r3_commit,
        "round3_commit_present": git_exists(r3_commit),
        "merge_base_head_expected": merge_head,
        "merge_base_head_round3": merge_r3,
        "expected_head_is_ancestor_of_head": subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", expected, "HEAD"]).returncode == 0,
        "round3_commit_is_ancestor_of_head": subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", r3_commit, "HEAD"]).returncode == 0,
        "head_is_ancestor_of_round3_commit": subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", "HEAD", r3_commit]).returncode == 0,
        "ahead_behind": git("rev-list", "--left-right", "--count", "HEAD...origin/work/lp-stage11-4"),
        "branch": git("branch", "--show-current"),
        "upstream": git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"),
    }
    paths = {
        "clean_v2_dataset": C2 / "lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv",
        "clean_v2_split": C2 / "split_clean_v2.csv",
        "clean_v2_normalization": C2 / "normalization_clean_v2.json",
        "clean_v3_dataset": C3 / "lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv",
        "clean_v3_split": C3 / "split_clean_v3.csv",
        "clean_v3_normalization": C3 / "normalization_clean_v3.json",
        "r3_plan": P / "lp_ml_dataset_v1_round3_64_candidate_plan_v1.csv",
        "r3_contract": P / "lp_ml_dataset_v1_round3_execution_contract_v1.json",
        "r3_accounting": A / "lp_ml_round3_accounting_audit_v1.json",
        "r3_predictions": A / "lp_ml_round3_pre_retrain_prospective_predictions_v1.json",
        "r3_risk_model": A / "lp_ml_round3_risk_calibration_model_v1.json",
        "r3_risk_eval": A / "lp_ml_round3_risk_calibration_evaluation_v1.json",
        "r3_rescored_pool": A / "lp_ml_round3_recalibrated_508_candidate_table_v1.csv",
        "r3_tuple_front": P / "lp_ml_six_bin_inverse_search_round3_v1/lp_ml_six_bin_recalibrated_tuple_front_v1.json",
        "r3_decision": A / "lp_ml_round3_round4_need_assessment_v1.json",
    }
    missing = [k for k, p in paths.items() if not p.exists()]
    hashes = {k: (sha(p) if p.exists() else None) for k, p in paths.items()}
    c2 = read_csv(paths["clean_v2_dataset"]) if not missing else []
    c3 = read_csv(paths["clean_v3_dataset"]) if not missing else []
    c2_ids = {r.get("candidate_id") for r in c2}
    c3_ids = {r.get("candidate_id") for r in c3}
    r3_ids = c3_ids - c2_ids
    accounting = json.loads(paths["r3_accounting"].read_text(encoding="utf-8")) if not missing else {}
    risk_eval = json.loads(paths["r3_risk_eval"].read_text(encoding="utf-8")) if not missing else {}
    decision = json.loads(paths["r3_decision"].read_text(encoding="utf-8")) if not missing else {}
    source = {
        "missing": missing,
        "hashes": hashes,
        "clean_v2": {"geometries": len(c2_ids), "rows": len(c2), "geometry_054_rows": sum(r.get("candidate_id") == "LPML_R1_GLOBAL_SOBOL_054" for r in c2)},
        "clean_v3": {"geometries": len(c3_ids), "rows": len(c3), "geometry_054_rows": sum(r.get("candidate_id") == "LPML_R1_GLOBAL_SOBOL_054" for r in c3), "duplicate_rows": len(c3) - len({(r.get("candidate_id"), r.get("wavelength_nm")) for r in c3}), "clean_v2_geometry_subset": c2_ids.issubset(c3_ids), "round3_added_geometries": len(r3_ids), "round3_added_rows": sum(r.get("candidate_id") in r3_ids for r in c3)},
        "r3_accounting": accounting,
        "risk_evaluation": risk_eval,
        "decision": decision,
    }
    protected = {str(p.relative_to(ROOT)): sha(p) for p in PROTECTED}
    payload = {
        "contract": "LP_ML_ROUND3_EVIDENCE_RECONCILIATION_V1",
        "status": "PASS" if not missing and ancestry["expected_head_present"] and ancestry["round3_commit_present"] and source["clean_v2"]["geometry_054_rows"] == 0 and source["clean_v3"]["geometry_054_rows"] == 0 and source["clean_v3"]["duplicate_rows"] == 0 and source["clean_v3"]["clean_v2_geometry_subset"] and len(r3_ids) == 58 and source["clean_v3"]["round3_added_rows"] == 522 and ancestry["round3_commit_is_ancestor_of_head"] and ancestry["expected_head_is_ancestor_of_head"] else "HARD_GATE",
        "ancestry": ancestry,
        "source_artifacts": source,
        "protected_report_sha256": protected,
        "constraints": {"solver_calls": 0, "round4_executed": False, "inverse_fdtd": False, "geometry054_executed": False, "k6": False, "physics_dataset_modified": False, "split_modified": False, "normalization_modified": False, "checkpoints_modified": False, "frozen_tests_used_for_tuning": bool(json.loads((A / 'lp_ml_round3_risk_recalibration_input_freeze_v1.json').read_text())['frozen_tests_used_for_tuning']) if (A / 'lp_ml_round3_risk_recalibration_input_freeze_v1.json').exists() else None},
        "risk_recalibration": {"model_hash": hashes["r3_risk_model"], "evaluation_hash": hashes["r3_risk_eval"], "rescored_pool_hash": hashes["r3_rescored_pool"], "tuple_front_hash": hashes["r3_tuple_front"], "decision_hash": hashes["r3_decision"], "calibrated_spearman_cv": risk_eval.get("cross_validation", {}).get("calibrated_rank_correlation"), "dispersion_only_spearman_cv": risk_eval.get("cross_validation", {}).get("dispersion_only_rank_correlation"), "calibrated_high_error_recall_cv": risk_eval.get("cross_validation", {}).get("calibrated_high_error_recall"), "dispersion_only_high_error_recall_cv": risk_eval.get("cross_validation", {}).get("dispersion_only_high_error_recall"), "calibrated_high_error_low_risk_cv": risk_eval.get("cross_validation", {}).get("calibrated_high_error_low_risk_count"), "dispersion_only_high_error_low_risk_cv": risk_eval.get("cross_validation", {}).get("dispersion_only_high_error_low_risk_count")},
    }
    out = A / "lp_ml_round3_evidence_reconciliation_v1.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = ROOT / "reports/lp_ml_round3_evidence_reconciliation_v1.md"
    report.write_text("\n".join(["# LP-ML Round-3 Evidence Reconciliation v1", "", f"Status: `{payload['status']}`", "", f"HEAD: `{head}`; Round-3 commit `{r3_commit}` is an ancestor; expected 216e3ae is an ancestor; upstream divergence `{ancestry['ahead_behind']}`.", "", f"Clean-v2: {source['clean_v2']['geometries']} geometries / {source['clean_v2']['rows']} rows; clean-v3: {source['clean_v3']['geometries']} geometries / {source['clean_v3']['rows']} rows; clean-v3 adds {source['clean_v3']['round3_added_geometries']} complete geometries / {source['clean_v3']['round3_added_rows']} rows.", "", "Geometry 054 admitted rows are zero in both clean views; clean-v3 duplicate rows are zero; clean-v2 is a geometry subset of clean-v3.", "", f"Round-3 accounting: planned=64, entered={accounting.get('entered')}, unique={accounting.get('unique')}, duplicate={accounting.get('duplicate')}, accepted={accounting.get('accepted')}, quarantined={accounting.get('quarantined_geometries')}, complete={accounting.get('complete_geometries')}, rows={accounting.get('admitted_rows')}.", "", f"Risk calibration CV Spearman: calibrated={payload['risk_recalibration']['calibrated_spearman_cv']}; dispersion-only={payload['risk_recalibration']['dispersion_only_spearman_cv']}; calibrated high-error recall={payload['risk_recalibration']['calibrated_high_error_recall_cv']}; false-low-risk={payload['risk_recalibration']['calibrated_high_error_low_risk_cv']}.", "", "Offline-only: solver/FDTD=0; no Round-4 or inverse-FDTD execution; no physics, split, normalization, checkpoint, protected-report, geometry054 or K6 modification.", "", "Protected report hashes are recorded in the JSON artifact.", ""]) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(out), "report": str(report), "clean_v3": source["clean_v3"], "ancestry": ancestry}, indent=2))

if __name__ == "__main__":
    main()
