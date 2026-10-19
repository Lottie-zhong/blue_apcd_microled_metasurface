import csv
import hashlib
import json
from pathlib import Path

NP = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
COUPLING = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def csv_data(p, limit=None):
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
    return {"path": str(p), "sha256": sha(p), "fieldnames": r.fieldnames, "rows": rows[:limit] if limit else rows, "row_count": len(rows)}


def read_json(p):
    return {"path": str(p), "sha256": sha(p), "data": json.loads(p.read_text(encoding="utf-8"))}


def compact_row(row, fields):
    return {k: row.get(k) for k in fields if k in row}


def main():
    paths = {
        "hf22": NP / r"outputs\np_k6_m8a_primary2_closeout_v1\hf22_formal_development_484rows.csv",
        "m9_oof": NP / r"outputs\np_k6_m9_22g_forward_retraining_v1\oof_predictions_22g.csv",
        "m9_metrics": NP / r"outputs\np_k6_m9_22g_forward_retraining_v1\model_metrics_constrained.csv",
        "m9_rank": NP / r"outputs\np_k6_m9_22g_forward_retraining_v1\ranking_metrics.csv",
        "m7a_features": NP / r"outputs\np_k6_m7a_targeted_development_acquisition_design_v1\candidate_acquisition_features.csv",
        "m7a_pred": NP / r"outputs\np_k6_m7a_targeted_development_acquisition_design_v1\candidate_predictions_long.csv",
        "m8a_scores": NP / r"outputs\np_k6_m8a_final_targeted_acquisition_design_v1\candidate_selection_scores.csv",
        "m8a_backup": NP / r"outputs\np_k6_m8a_final_targeted_acquisition_design_v1\backup_ranking.csv",
        "m0f_registry": ML / r"outputs\coupling_ml\M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1\M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION\M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1\M0F_FINAL_RECONCILED_LEVEL1_NUMERICAL_REGISTRY_V1.csv",
        "m0f_eligibility": ML / r"outputs\coupling_ml\M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1\M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION\M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1\M0F_FINAL_RESIDUAL_ELIGIBILITY_AFTER_FULL_COMPONENT_SET_V1.csv",
    }
    out = {"files": {}, "unique_hf_geometry_rows": [], "m0f_rows": []}
    for name, p in paths.items():
        if p.exists():
            d = csv_data(p)
            out["files"][name] = {"path": d["path"], "sha256": d["sha256"], "fieldnames": d["fieldnames"], "row_count": d["row_count"]}
            if name == "hf22":
                rows = d["rows"]
                by = {}
                for row in rows:
                    gid = row.get("geometry_id") or row.get("candidate_id") or row.get("geometry") or row.get("case_id")
                    if gid not in by:
                        by[gid] = row
                out["unique_hf_geometry_rows"] = list(by.values())
            if name == "m0f_registry":
                fields = ["logical_case_id", "truth_domain", "candidate", "spacer_nm", "ux", "source_polarization", "provider_channel", "observable", "wavelength_grid_nm", "level2_authoritative_raw_path", "np_provider_freeze_path", "level1_reconciled_status", "residual_compatible", "reason", "physical_order_mapping"]
                out["m0f_rows"] = [compact_row(r, fields) for r in d["rows"]]
        else:
            out["files"][name] = {"path": str(p), "missing": True}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
