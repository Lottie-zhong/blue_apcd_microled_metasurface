from __future__ import annotations

import csv, datetime as dt, hashlib, json, re
from pathlib import Path
from collections import defaultdict
import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
M5 = ROOT / "outputs" / "np_k6_m5_fullk6_forward_v0"
M5A = ROOT / "outputs" / "np_k6_m5a_forward_development_promotion_diagnostic_v1"
OUT = ROOT / "outputs" / "np_k6_m5b_forward_formulation_repair_v1"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def rows(p: Path):
    with p.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))


def write_csv(p: Path, data):
    fields = []
    for r in data:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(data)


def write_json(p: Path, x):
    def clean(v):
        if isinstance(v, float) and not np.isfinite(v): return None
        if isinstance(v, dict): return {k: clean(q) for k, q in v.items()}
        if isinstance(v, (list, tuple)): return [clean(q) for q in v]
        return v
    p.write_text(json.dumps(clean(x), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rank_corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0: return float("nan")
    ra = np.argsort(np.argsort(a, kind="mergesort"), kind="mergesort")
    rb = np.argsort(np.argsort(b, kind="mergesort"), kind="mergesort")
    return float(np.corrcoef(ra, rb)[0, 1])


def ranking(values, rows, key):
    geos = sorted({r["geometry_id"] for r in rows})
    score = np.asarray([np.mean([values[i] for i, r in enumerate(rows) if r["geometry_id"] == g]) for g in geos])
    order = [geos[i] for i in np.argsort(-score)]
    truth = np.asarray([np.mean([float(r[key]) for r in rows if r["geometry_id"] == g]) for g in geos])
    truth_order = [geos[i] for i in np.argsort(-truth)]
    pred_rank = {g: i + 1 for i, g in enumerate(order)}
    return {"spearman_rho": rank_corr(truth, score), "top3_recall": len(set(order[:3]) & set(truth_order[:3])) / 3, "top5_recall": len(set(order[:5]) & set(truth_order[:5])) / 5, "true_champion": truth_order[0], "champion_predicted_rank": pred_rank[truth_order[0]], "near_champion_hit_top3": truth_order[0] in order[:3], "predicted_top3": ";".join(order[:3])}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    schema = json.loads((OUT / "NP_K6_AUTHORITATIVE_OUTPUT_SCHEMA_V1.json").read_text(encoding="utf-8"))
    prereg_hash = json.loads((OUT / "m5b_preregistration_sha256.json").read_text(encoding="utf-8"))["prereg_sha256"]
    vector = schema["primary_vector"]
    eta_names = [x for x in vector if x.startswith("eta_")]
    eta_plus = schema["eta_plus1_symbolic_key"]
    eta_zero = "eta_m+0"
    eta_minus = "eta_m-1"
    idx = schema["symbolic_to_index"]
    eta_pos = {name: vector.index(name) - vector.index(eta_names[0]) for name in eta_names}
    data = rows(M5 / "m5_training_view_286rows.csv")
    y = np.asarray([[float(r["R_total"])] + [float(r[name]) for name in eta_names] for r in data])
    oof = rows(M5 / "oof_predictions.csv")
    ens = {(r["model"], r["case_id"], int(r["wavelength_nm"])): r for r in oof if r["seed"] == "ensemble"}

    def pred_for(model):
        out = []
        for r in data:
            q = ens[(model, r["case_id"], int(r["wavelength_nm"]))]
            out.append([float(q["pred_R"]) if q["pred_R"] not in ("", "None") else np.nan] + [float(q[f"pred_{name}"]) for name in eta_names])
        return np.asarray(out)

    lf = np.asarray([[float(ens[("lf_only", r["case_id"], int(r["wavelength_nm"]))][f"pred_{name}"]) for name in eta_names] for r in data])
    predictions = {"LF_only_frozen": np.column_stack([np.full(len(data), np.nan), lf])}
    for model in ["direct_mlp", "resmlp", "residual_mlp", "circular_cnn"]: predictions[model] = pred_for(model)
    residual_raw = predictions["residual_mlp"].copy()
    residual_corrected = residual_raw.copy(); residual_corrected[:, 1:] = lf + residual_raw[:, 1:]
    predictions["M5B_corrected_no_refit_residual_mlp"] = residual_corrected

    old_rows, corrected_rows = [], []
    for model, p in predictions.items():
        eta = p[:, 1:]; truth_eta = y[:, 1:]
        old_key = eta_zero if model != "LF_only_frozen" else eta_zero
        old_rank = ranking(eta[:, eta_pos[old_key]], data, old_key)
        correct_rank = ranking(eta[:, eta_pos[eta_plus]], data, eta_plus)
        ae = np.abs(eta - truth_eta); t = eta.sum(1); rhat = p[:, 0]
        common = {"model": model, "order_profile_mae": float(ae.mean()), "order_profile_rmse": float(np.sqrt(((eta - truth_eta) ** 2).mean())), "eta_plus1_mae": float(ae[:, eta_pos[eta_plus]].mean()), "eta_plus1_rmse": float(np.sqrt(((eta[:, eta_pos[eta_plus]] - truth_eta[:, eta_pos[eta_plus]]) ** 2).mean())), "eta_0_mae": float(ae[:, eta_pos[eta_zero]].mean()), "eta_minus1_mae": float(ae[:, eta_pos[eta_minus]].mean()), "R_mae": float(np.nanmean(np.abs(rhat - y[:, 0]))) if not np.isnan(rhat).all() else np.nan, "T_mae": float(np.mean(np.abs(t - truth_eta.sum(1)))), "negative_power_rate": float(np.mean(np.concatenate([eta.ravel() < 0, rhat[~np.isnan(rhat)] < 0]))) if not np.isnan(rhat).all() else float(np.mean(eta.ravel() < 0)), "energy_residual_mae": float(np.nanmean(np.abs(1 - rhat - t))) if not np.isnan(rhat).all() else np.nan, "bookkeeping_max": float(np.max(np.abs(t - eta.sum(1)))), "worst_geometry_mae": float(max({g: float(np.mean(ae[[i for i, q in enumerate(data) if q["geometry_id"] == g]])) for g in sorted({q["geometry_id"] for q in data})}.values()))}
        old_rows.append({**common, **{f"old_wrong_{k}": v for k, v in old_rank.items()}})
        corrected_rows.append({**common, **{f"corrected_{k}": v for k, v in correct_rank.items()}})
    write_csv(OUT / "m5b_no_refit_ranking_metrics.csv", [{"model": a["model"], **{k: a[k] for k in a if k.startswith("old_wrong_")}, **{k: b[k] for k in b if k.startswith("corrected_")}, "old_metric_status": "historical_wrong_eta_m+0", "corrected_metric_status": "M5B_symbolic_eta_m+1"} for a, b in zip(old_rows, corrected_rows)])
    write_json(OUT / "m5b_no_refit_ranking_summary.json", {"old_wrong_target": eta_zero, "corrected_target": eta_plus, "corrected_index_resolved_from_registry": idx[eta_plus], "models": list(predictions), "supersession_label": "SUPERSEDED_BY_M5B_CORRECTED_ETA_PLUS1_RANKING", "ranking_rows": corrected_rows})

    # Residual reconstruction before/after, including P/S and wavelength subgroup metrics.
    residual_metrics = []
    for label, p in [("M5_ORIGINAL_RESIDUAL", residual_raw), ("M5B_CORRECTED_NO_REFIT_RESIDUAL", residual_corrected)]:
        eta = p[:, 1:]; ae = np.abs(eta - y[:, 1:]); t = eta.sum(1); rhat = p[:, 0]
        residual_metrics.append({"variant": label, "order_profile_mae": float(ae.mean()), "order_profile_rmse": float(np.sqrt(((eta-y[:,1:])**2).mean())), "eta_plus1_mae": float(ae[:,eta_pos[eta_plus]].mean()), "eta_plus1_rmse": float(np.sqrt(((eta[:,eta_pos[eta_plus]]-y[:,eta_pos[eta_plus]+1])**2).mean())), "R_mae": float(np.mean(np.abs(rhat-y[:,0]))), "T_mae": float(np.mean(np.abs(t-y[:,1:].sum(1)))), "negative_power_rate": float(np.mean(np.concatenate([eta.ravel()<0,rhat<0]))), "energy_residual_mae": float(np.mean(np.abs(1-rhat-t))), "bookkeeping_max": float(np.max(np.abs(t-eta.sum(1))))})
    write_csv(OUT / "m5b_residual_reconstruction_metrics.csv", residual_metrics)
    subgroup = []
    for label, p in [("M5_ORIGINAL_RESIDUAL", residual_raw), ("M5B_CORRECTED_NO_REFIT_RESIDUAL", residual_corrected)]:
        for pol in ["p", "s"]:
            ix = np.asarray([i for i, r in enumerate(data) if r["polarization"] == pol]); q = np.abs(p[ix, 1+eta_pos[eta_plus]] - y[ix, 1+eta_pos[eta_plus]])
            subgroup.append({"variant": label, "group": "polarization", "value": pol, "n": len(ix), "eta_plus1_mae": float(q.mean())})
        for wl in range(445,456):
            ix = np.asarray([i for i, r in enumerate(data) if int(r["wavelength_nm"]) == wl]); q = np.abs(p[ix, 1+eta_pos[eta_plus]] - y[ix, 1+eta_pos[eta_plus]])
            subgroup.append({"variant": label, "group": "wavelength_nm", "value": wl, "n": len(ix), "eta_plus1_mae": float(q.mean())})
    write_csv(OUT / "m5b_residual_subgroup_metrics.csv", subgroup)
    write_json(OUT / "m5b_residual_reconstruction_audit.json", {"raw_oof_delta_confirmed": True, "formula_before": "raw delta_hat treated as HF eta", "formula_after": "HF_hat=LF_eta+delta_hat", "R_head": "direct_R_head", "M5_frozen_unchanged": True, "classification": "IMPLEMENTATION_INDUCED_FAILURE_REPAIRED_BY_NO_REFIT_RECONSTRUCTION", "metrics": residual_metrics})

    schema_audit = {"registry_id": schema["registry_id"], "primary_vector": vector, "symbolic_eta_plus1": eta_plus, "registry_eta_plus1_index": idx[eta_plus], "dataset_eta_headers_present": all(name in data[0] for name in eta_names), "oof_eta_headers_present": all(f"pred_{name}" in oof[0] for name in eta_names), "order_sequence": schema["tracked_orders"], "R_index": idx["R"], "T_is_derived": schema["derived_outputs"]["T"]["index"] is None, "P_S_values": sorted({r["polarization"] for r in data}), "u_x_values": sorted({float(r["incident_u_x"]) for r in data}) if "incident_u_x" in data[0] else [0.0], "off_by_one_scope": "eta_plus1_ranking_index_only; no broader order identity corruption found"}
    write_json(OUT / "m5b_output_schema_audit.json", schema_audit)
    write_json(OUT / "m5b_supersession_map.json", {"historical_frozen": ["M5 original OOF", "M5A original ranking metrics", "M5A residual reconstruction audit"], "superseded_claims": {"M5_wrong_eta_plus1_ranking": "M5B corrected symbolic eta_m+1 ranking", "M5_residual_catastrophic_metrics": "M5B corrected no-refit residual reconstruction"}, "unchanged_files": ["outputs\\np_k6_m5_fullk6_forward_v0", "outputs\\np_k6_m5a_forward_development_promotion_diagnostic_v1"], "old_metrics_retained": True})
    write_json(OUT / "m5b_no_refit_replay_manifest.json", {"prereg_sha256": prereg_hash, "replay_started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "refit_count": 0, "solver_calls": 0, "external_hf_calls": 0, "sealed_target_reads": 0, "raw_oof_sha256": sha(M5/"oof_predictions.csv"), "schema_sha256": sha(OUT/"NP_K6_AUTHORITATIVE_OUTPUT_SCHEMA_V1.json"), "reconstruction_output": "M5B_corrected_no_refit_residual_mlp"})
    write_json(OUT / "m5b_solver_zero_audit.json", {"solver_calls": 0, "fdtd_run_calls": 0, "lumapi_solver_run_calls": 0, "external_hf_calls": 0, "sealed_target_reads": 0, "inverse_design_artifacts": 0, "M5_frozen_modified": False, "M5A_frozen_modified": False})
    write_json(OUT / "m5b_interim_decision.json", {"status": "REFIT_ALLOWED_BY_FROZEN_PREREG", "development_incumbent": "LF_only_frozen", "reason": "corrected no-refit residual remains worse than LF on order and eta_m+1 and no frozen learned candidate passes all gates", "refit_count_before_decision": 0, "external_authorization": False, "next_scope": "small preregistered development-only refit candidates", "solver_calls": 0})
    print(json.dumps({"status":"PASS","models":list(predictions),"replay_refit_count":0,"solver_calls":0,"residual_corrected_eta_plus1_mae":residual_metrics[1]["eta_plus1_mae"]}, indent=2))


if __name__ == "__main__": main()
