from __future__ import annotations

import csv
import hashlib
import json
import pickle
from pathlib import Path

import numpy as np


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1"
DATASET = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1" / "V1_TRAINVAL_DATASET.csv"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    required = [
        "DATASET_INTEGRITY_AUDIT.json", "BLIND_LEAKAGE_AUDIT.json", "LABEL_SANITY_AUDIT.json",
        "TRAIN_ONLY_PREPROCESSOR.json", "ANGULAR_PCA_RANK_AUDIT.json", "ANGULAR_PCA_MODEL.npz",
        "PCA_RECONSTRUCTION_METRICS.csv", "PRIOR_FEATURE_VALIDITY_AUDIT.json", "GROUPED_CV_SPLIT_MANIFEST.json",
        "TRAIN_CV_MODEL_CANDIDATE_FREEZE.json", "RIDGE_ABLATION_RESULTS.csv", "GP_ABLATION_RESULTS.csv",
        "MLP_ABLATION_RESULTS.csv", "PRIOR_ABLATION_SUMMARY.csv", "VALIDATION_METRICS_SCALAR.csv",
        "VALIDATION_METRICS_PROFILE.csv", "VALIDATION_METRICS_DECISION.csv", "MODEL_PARETO_ANALYSIS.json",
        "FINAL_MODEL_RECOMMENDATION.json", "REPORT.md", "REPORT.json",
    ]
    missing = [n for n in required if not (OUT / n).is_file()]
    dataset = list(csv.DictReader(DATASET.open(newline="", encoding="utf-8-sig")))
    train = [r for r in dataset if r["split"] == "TRAIN"]
    train_ids = sorted({r["geometry_id"] for r in train})
    pca = np.load(OUT / "ANGULAR_PCA_MODEL.npz", allow_pickle=False)
    sqrt_w = np.sqrt(pca["weights_du"])
    components = pca["components_weighted"]
    mean_w = pca["mean_profile"] * sqrt_w
    profile_path = Path(train[0]["angular_profile_ref"])
    z = np.load(profile_path, allow_pickle=False)
    idx = int(np.argmin(np.abs(z["wavelengths_nm"] - float(train[0]["lambda_nm"]))))
    profile = z["f_up"][:, idx]
    coef = (profile * sqrt_w - mean_w) @ components.T
    recon_w = mean_w + coef @ components
    coef_roundtrip = (recon_w - mean_w) @ components.T
    pca_roundtrip_error = float(np.max(np.abs(coef - coef_roundtrip)))
    loaded_models = []
    model_errors = []
    for path in sorted((OUT / "models").glob("*.pkl")):
        try:
            with path.open("rb") as f:
                payload = pickle.load(f)
            if "models" in payload:
                assert len(payload["models"]) == 5
            else:
                assert "payload" in payload and hasattr(payload["payload"]["model"], "predict")
            loaded_models.append(path.name)
        except Exception as exc:
            model_errors.append({"path": str(path), "error": repr(exc)})
    grouped = read_json(OUT / "GROUPED_CV_SPLIT_MANIFEST.json")
    fold_leakage = []
    for fold in grouped["folds"]:
        if set(fold["train_geometry_ids"]) & set(fold["test_geometry_ids"]):
            fold_leakage.append(fold["fold"])
    freeze = read_json(OUT / "TRAIN_CV_MODEL_CANDIDATE_FREEZE.json")
    recommendation = read_json(OUT / "FINAL_MODEL_RECOMMENDATION.json")
    pareto = read_json(OUT / "MODEL_PARETO_ANALYSIS.json")
    candidates = list(pareto.get("candidate_metrics", []))
    cv_profile_best = min(candidates, key=lambda x: x["metrics"].get("cv_profile_l1", 1e99))
    validation_profile_best = min(candidates, key=lambda x: x["metrics"].get("val_profile_l1", 1e99))
    finalists = []
    for item in (cv_profile_best, validation_profile_best):
        if item["candidate"] not in finalists:
            finalists.append(item["candidate"])
    pareto["hierarchy_finalists"] = finalists
    pareto["hierarchy_finalist_rule"] = "best TRAIN grouped-CV profile and best one-shot VALIDATION profile; no weighted total"
    write_json(OUT / "MODEL_PARETO_ANALYSIS.json", pareto)
    recommendation["recommendation"] = "CHAMPION_READY_FOR_BLIND_PROSPECTIVE" if len(finalists) == 1 else "TWO_FINALISTS_REQUIRE_CHART_DECISION"
    recommendation["champion"] = finalists[0] if len(finalists) == 1 else None
    recommendation["finalists"] = finalists
    recommendation["production_blind_acquisition_authorized"] = len(finalists) == 1
    write_json(OUT / "FINAL_MODEL_RECOMMENDATION.json", recommendation)
    audit = {
        "schema_version": "ZERO_SOLVER_TEST_AUDIT_V1",
        "solver_entries": 0,
        "blind_truth_acquired": 0,
        "required_outputs_missing": missing,
        "dataset_rows": len(dataset),
        "train_geometry_count": len(train_ids),
        "grouped_cv_leakage_folds": fold_leakage,
        "pca_forward_inverse_coeff_max_abs_error": pca_roundtrip_error,
        "pca_forward_inverse_pass": bool(pca_roundtrip_error < 1e-10),
        "model_files_loaded": loaded_models,
        "model_load_errors": model_errors,
        "model_save_load_pass": not model_errors and len(loaded_models) > 0,
        "validation_one_shot_freeze": bool(freeze.get("created_before_validation") and recommendation.get("validation_one_shot")),
        "status": "PASS" if not missing and not fold_leakage and pca_roundtrip_error < 1e-10 and not model_errors else "FAIL",
    }
    write_json(OUT / "ZERO_SOLVER_TEST_AUDIT.json", audit)
    report_path = OUT / "REPORT.json"
    report = read_json(report_path)
    report["zero_solver_test_audit"] = str(OUT / "ZERO_SOLVER_TEST_AUDIT.json")
    report["zero_solver_test_status"] = audit["status"]
    write_json(report_path, report)
    report_md = OUT / "REPORT.md"
    report_md.write_text("# APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_SURROGATE_ABLATION_V1\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in report.items()), encoding="utf-8")
    files = [p for p in OUT.rglob("*") if p.is_file() and p.name != "FINAL_SHA256_MANIFEST.json"]
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "files": [{"path": str(p.relative_to(OUT)), "sha256": sha(p), "size": p.stat().st_size} for p in sorted(files)]})
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
