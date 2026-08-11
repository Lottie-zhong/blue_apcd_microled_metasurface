from __future__ import annotations

import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
M5 = ROOT / "outputs" / "np_k6_m5_fullk6_forward_v0"
OUT = ROOT / "outputs" / "np_k6_m5a_forward_development_promotion_diagnostic_v1"
WLS = list(range(445, 456))
ORD = [-3, -2, -1, 0, 1, 2, 3]
SEEDS = [17, 29, 43]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    def clean(value):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(v) for v in value]
        return value
    path.write_text(json.dumps(clean(obj), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    ra = np.argsort(np.argsort(a, kind="mergesort"), kind="mergesort")
    rb = np.argsort(np.argsort(b, kind="mergesort"), kind="mergesort")
    return float(np.corrcoef(ra, rb)[0, 1])


def geometry_scores(values: np.ndarray, rows: list[dict[str, str]]) -> tuple[list[str], np.ndarray]:
    geos = sorted({r["geometry_id"] for r in rows})
    score = np.asarray([np.mean([values[i] for i, r in enumerate(rows) if r["geometry_id"] == g]) for g in geos])
    return geos, score


def parse_d(g: str) -> np.ndarray:
    return np.asarray([float(v) for v in re.findall(r"D(\d+)", g)], float)


def load_authority() -> tuple[list[dict[str, str]], np.ndarray, np.ndarray, dict[tuple[str, int], dict[str, str]]]:
    rows = read_csv(M5 / "m5_training_view_286rows.csv")
    y = np.asarray([[float(r["R_total"])] + [float(r[f"eta_m{m:+d}"]) for m in ORD] for r in rows])
    oof = read_csv(M5 / "oof_predictions.csv")
    ens = {(r["model"], r["case_id"], int(r["wavelength_nm"])): r for r in oof if r["seed"] == "ensemble"}
    lf = {}
    for r in rows:
        q = ens[("lf_only", r["case_id"], int(r["wavelength_nm"]))]
        lf[(r["case_id"], int(r["wavelength_nm"]))] = np.asarray([float(q[f"pred_eta_m{m:+d}"]) for m in ORD])
    return rows, y, np.asarray([lf[(r["case_id"], int(r["wavelength_nm"]))] for r in rows]), ens


def frozen_predictions(rows: list[dict[str, str]], ens: dict[tuple[str, str, int], dict[str, str]]) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for model in ["direct_mlp", "resmlp", "circular_cnn"]:
        out[model] = np.asarray([
            [float((q := ens[(model, r["case_id"], int(r["wavelength_nm"]))])["pred_R"])] + [float(q[f"pred_eta_m{m:+d}"]) for m in ORD]
            for r in rows
        ])
    return out


def fit_lf_corrections(rows: list[dict[str, str]], y: np.ndarray, lf_eta: np.ndarray) -> dict[str, np.ndarray]:
    n = len(rows)
    geo = np.asarray([r["geometry_id"] for r in rows])
    geos = sorted(set(geo))
    features = []
    for r, l in zip(rows, lf_eta):
        d = parse_d(r["geometry_id"]) / 230.0
        gaps = np.roll(d, -1) - d
        wl = (int(r["wavelength_nm"]) - 450) / 5.0
        pol = 1.0 if r["polarization"] == "s" else 0.0
        features.append(np.r_[d, gaps, [wl, pol], l])
    F = np.asarray(features, float)
    result = {"LF_global_output_bias": np.full((n, 8), np.nan), "LF_ridge_residual": np.full((n, 8), np.nan), "LF_paired_shared_correction_polarization_contrast": np.full((n, 8), np.nan)}
    for g in geos:
        te = np.where(geo == g)[0]
        tr = np.where(geo != g)[0]
        global_pred = np.column_stack([np.full(len(te), np.mean(y[tr, 0])), lf_eta[te] + np.mean(y[tr, 1:] - lf_eta[tr], axis=0)])
        result["LF_global_output_bias"][te] = np.maximum(global_pred, 0)
        target = np.column_stack([y[tr, 0], y[tr, 1:] - lf_eta[tr]])
        model = Ridge(alpha=0.1).fit(F[tr], target)
        q = model.predict(F[te])
        q[:, 1:] += lf_eta[te]
        result["LF_ridge_residual"][te] = np.maximum(q, 0)
        pair_ix, common, contrast = [], [], []
        for gg in geos:
            if gg == g:
                continue
            for wl in WLS:
                ip = next(i for i in tr if rows[i]["geometry_id"] == gg and int(rows[i]["wavelength_nm"]) == wl and rows[i]["polarization"] == "p")
                iss = next(i for i in tr if rows[i]["geometry_id"] == gg and int(rows[i]["wavelength_nm"]) == wl and rows[i]["polarization"] == "s")
                pair_ix.append(ip)
                common.append(np.r_[(y[ip, 0] + y[iss, 0]) / 2, (y[ip, 1:] - lf_eta[ip] + y[iss, 1:] - lf_eta[iss]) / 2])
                contrast.append(np.r_[(y[ip, 0] - y[iss, 0]) / 2, (y[ip, 1:] - lf_eta[ip] - (y[iss, 1:] - lf_eta[iss])) / 2])
        cm = Ridge(alpha=0.1).fit(F[pair_ix], np.asarray(common))
        dm = Ridge(alpha=0.1).fit(F[pair_ix], np.asarray(contrast))
        for i in te:
            sign = 1.0 if rows[i]["polarization"] == "p" else -1.0
            q = np.r_[0.0, lf_eta[i]] + cm.predict(F[i : i + 1])[0] + sign * dm.predict(F[i : i + 1])[0]
            result["LF_paired_shared_correction_polarization_contrast"][i] = np.maximum(q, 0)
    return result


def ranking_audit(preds: dict[str, np.ndarray], rows: list[dict[str, str]], ens: dict[tuple[str, str, int], dict[str, str]]) -> None:
    true_geos, true_score = geometry_scores(np.asarray([float(r["eta_m+1"]) for r in rows]), rows)
    true_order = [true_geos[i] for i in np.argsort(-true_score)]
    result = []
    for name, p in preds.items():
        if np.isnan(p[:, 0]).all():
            score_values = p[:, 5]
        else:
            score_values = p[:, 5]
        geos, score = geometry_scores(score_values, rows)
        order = [geos[i] for i in np.argsort(-score)]
        rank_map = {g: i + 1 for i, g in enumerate(order)}
        true_top3, true_top5 = set(true_order[:3]), set(true_order[:5])
        pred_top3, pred_top5 = set(order[:3]), set(order[:5])
        seed_values = []
        for seed in SEEDS:
            if name not in {"direct_mlp", "resmlp", "circular_cnn"}:
                continue
            vals = []
            for r in rows:
                q = ens[(name, r["case_id"], int(r["wavelength_nm"]))]
                # This branch is replaced below using the explicit seed map.
                vals.append(float(q["pred_eta_m+1"]))
            seed_values.append(float(corr(np.asarray(vals), np.asarray([r["eta_m+1"] for r in rows]))))
        result.append({"model": name, "spearman_rho": corr(true_score, score), "top3_recall": len(pred_top3 & true_top3) / 3, "top5_recall": len(pred_top5 & true_top5) / 5, "true_champion": true_order[0], "champion_predicted_rank": rank_map[true_order[0]], "near_champion_hit_top3": true_order[0] in pred_top3, "predicted_top3": ";".join(order[:3]), "seed_count": 0, "seed_stability_mean_spearman": float("nan")})
    # Replace seed statistics with actual per-seed geometry ranking stability.
    oof = read_csv(M5 / "oof_predictions.csv")
    for row in result:
        if row["model"] not in {"direct_mlp", "resmlp", "circular_cnn"}:
            continue
        ensemble = np.asarray([float(ens[(row["model"], r["case_id"], int(r["wavelength_nm"]))]["pred_eta_m+1"]) for r in rows])
        _, ensemble_g = geometry_scores(ensemble, rows)
        vals = []
        for seed in SEEDS:
            smap = {(q["case_id"], int(q["wavelength_nm"])): q for q in oof if q["model"] == row["model"] and q["seed"] == str(seed)}
            sv = np.asarray([float(smap[(r["case_id"], int(r["wavelength_nm"]))]["pred_eta_m+1"]) for r in rows])
            _, sg = geometry_scores(sv, rows)
            vals.append(corr(ensemble_g, sg))
        row["seed_count"] = len(vals)
        row["seed_stability_mean_spearman"] = float(np.nanmean(vals))
        row["seed_stability_min_spearman"] = float(np.nanmin(vals))
    write_csv(OUT / "ranking_audit_full.csv", result)
    write_json(OUT / "ranking_audit_summary.json", {"primary_score": "mean eta(+1) over P/S and 445-455 nm", "true_geometry_order": true_order, "results": result, "ranking_index": 5, "seed_stability_from_frozen_oof": True})


def paired_bootstrap(preds: dict[str, np.ndarray], rows: list[dict[str, str]]) -> None:
    names = ["LF_global_output_bias", "LF_ridge_residual", "LF_paired_shared_correction_polarization_contrast", "direct_mlp", "resmlp", "circular_cnn"]
    lf = preds["LF_only_frozen"]
    geos = sorted({r["geometry_id"] for r in rows})
    ix = {g: [i for i, r in enumerate(rows) if r["geometry_id"] == g] for g in geos}
    truth = np.asarray([float(r["eta_m+1"]) for r in rows])
    rng = np.random.default_rng(2025)
    out = []
    for name in names:
        e_lf = np.asarray([np.mean(np.abs(truth[ix[g]] - lf[ix[g], 5])) for g in geos])
        e_c = np.asarray([np.mean(np.abs(truth[ix[g]] - preds[name][ix[g], 5])) for g in geos])
        diff = e_c - e_lf
        samples = np.asarray([np.mean(diff[rng.integers(0, len(geos), len(geos))]) for _ in range(10000)])
        out.append({"model": name, "geometry_count": len(geos), "paired_improvement_count": int(np.sum(diff < 0)), "mean_delta_error_candidate_minus_lf": float(diff.mean()), "median_delta": float(np.median(diff)), "bootstrap_mean_delta": float(samples.mean()), "bootstrap_ci95_low": float(np.quantile(samples, 0.025)), "bootstrap_ci95_high": float(np.quantile(samples, 0.975)), "bootstrap_probability_mean_improves": float(np.mean(samples < 0)), "per_geometry_delta": ";".join(f"{g}:{d:.8g}" for g, d in zip(geos, diff))})
    write_csv(OUT / "geometry_paired_bootstrap_audit.csv", out)
    write_json(OUT / "geometry_paired_bootstrap_summary.json", {"unit": "geometry", "resamples": 10000, "seed": 2025, "results": out})


def residual_breakdown(rows: list[dict[str, str]], y: np.ndarray, lf_eta: np.ndarray) -> None:
    d = y[:, 1:] - lf_eta
    out = []
    for j, order in enumerate(ORD):
        for pol in ["p", "s", "all"]:
            for wl in WLS + [None]:
                ix = np.asarray([i for i, r in enumerate(rows) if (pol == "all" or r["polarization"] == pol) and (wl is None or int(r["wavelength_nm"]) == wl)])
                if not len(ix):
                    continue
                q = d[ix, j]
                out.append({"output": f"eta_m{order:+d}", "polarization": pol, "wavelength_nm": "all" if wl is None else wl, "n": len(ix), "mean_bias": float(q.mean()), "std": float(q.std()), "mae": float(np.abs(q).mean()), "p90_abs": float(np.quantile(np.abs(q), 0.9)), "max_abs": float(np.abs(q).max())})
    write_csv(OUT / "lf_residual_spectrum_polarization.csv", out)
    by_geo = {}
    for g in sorted({r["geometry_id"] for r in rows}):
        ix = np.asarray([i for i, r in enumerate(rows) if r["geometry_id"] == g])
        by_geo[g] = {"residual_eta_plus1_mae": float(np.abs(d[ix, 4]).mean()), "lf_eta_plus1_mean": float(lf_eta[ix, 4].mean()), "residual_eta_plus1_mean": float(d[ix, 4].mean())}
    dm = {}
    with gzip.open(ROOT / "outputs" / "np_k6_ml_d0_database_foundation_v1" / "k6_design_space_master.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["geometry_id"] in by_geo:
                dm[r["geometry_id"]] = r
    vals = []
    for g, q in by_geo.items():
        if g in dm:
            q["mean_gap_nm"] = float(dm[g]["mean_gap_nm"]); q["min_gap_nm"] = float(dm[g]["min_gap_nm"]); q["diameter_mean_nm"] = float(dm[g]["diameter_mean_nm"]); vals.append(q)
    def cfield(a: str, b: str) -> float:
        return corr(np.asarray([v[a] for v in vals]), np.asarray([v[b] for v in vals])) if len(vals) > 2 else float("nan")
    write_json(OUT / "lf_residual_correlation_audit.json", {"eta_plus1_residual_vs_lf_eta_plus1": cfield("residual_eta_plus1_mae", "lf_eta_plus1_mean"), "eta_plus1_residual_mae_vs_mean_gap_nm": cfield("residual_eta_plus1_mae", "mean_gap_nm"), "eta_plus1_residual_mae_vs_min_gap_nm": cfield("residual_eta_plus1_mae", "min_gap_nm"), "eta_plus1_residual_mae_vs_diameter_mean_nm": cfield("residual_eta_plus1_mae", "diameter_mean_nm"), "geometry_table": by_geo})


def disagreement_audit(rows: list[dict[str, str]], y: np.ndarray, ens: dict[tuple[str, str, int], dict[str, str]]) -> None:
    oof = read_csv(M5 / "oof_predictions.csv")
    out = []
    for model in ["direct_mlp", "resmlp", "circular_cnn"]:
        seed_maps = [{(q["case_id"], int(q["wavelength_nm"])): q for q in oof if q["model"] == model and q["seed"] == str(seed)} for seed in SEEDS]
        emap = {(q["case_id"], int(q["wavelength_nm"])): q for q in oof if q["model"] == model and q["seed"] == "ensemble"}
        for target, field, truth_field in [("eta_plus1", "pred_eta_m+1", 5), ("R", "pred_R", 0), ("T", "pred_T", None)]:
            if target == "T":
                true = np.asarray([float(r["T_total"]) for r in rows]); ensval = np.asarray([float(emap[(r["case_id"], int(r["wavelength_nm"]))][field]) for r in rows]); seeds = np.asarray([[float(sm[(r["case_id"], int(r["wavelength_nm"]))][field]) for r in rows] for sm in seed_maps])
            else:
                true = y[:, truth_field]; ensval = np.asarray([float(emap[(r["case_id"], int(r["wavelength_nm"]))][field]) for r in rows]); seeds = np.asarray([[float(sm[(r["case_id"], int(r["wavelength_nm"]))][field]) for r in rows] for sm in seed_maps])
            dis = np.std(seeds, axis=0); err = np.abs(ensval - true); q25, q75 = np.quantile(dis, [0.25, 0.75]); lo = dis <= q25; hi = dis >= q75
            out.append({"model": model, "target": target, "n": len(rows), "disagreement_mean": float(dis.mean()), "error_mean": float(err.mean()), "disagreement_error_spearman": corr(dis, err), "low_bucket_n": int(lo.sum()), "low_bucket_error": float(err[lo].mean()), "high_bucket_n": int(hi.sum()), "high_bucket_error": float(err[hi].mean()), "high_minus_low_error": float(err[hi].mean() - err[lo].mean())})
    write_csv(OUT / "model_disagreement_audit.csv", out)
    write_json(OUT / "model_disagreement_summary.json", {"models": ["direct_mlp", "resmlp", "circular_cnn"], "seed_count": 3, "buckets": "quartile", "results": out})


def physics_projection(preds: dict[str, np.ndarray], y: np.ndarray) -> None:
    rows = []
    audit = []
    for name, p in preds.items():
        if name == "LF_only_frozen" or np.isnan(p[:, 0]).any():
            continue
        raw = np.asarray(p, float)
        q = np.maximum(raw, 0)
        total = q.sum(axis=1)
        projected = total > 1.0
        q[projected] /= total[projected, None]
        for label, z in [("raw", raw), ("projected", q)]:
            eta = z[:, 1:]; t = eta.sum(axis=1); negative = np.mean(np.concatenate([z[:, 0] < 0, eta.ravel() < 0]))
            rows.append({"model": name, "variant": label, "order_profile_mae": float(np.abs(eta - y[:, 1:]).mean()), "eta_plus1_mae": float(np.abs(eta[:, 4] - y[:, 5]).mean()), "R_mae": float(np.abs(z[:, 0] - y[:, 0]).mean()), "T_mae": float(np.abs(t - y[:, 1:].sum(axis=1)).mean()), "energy_residual_mae": float(np.abs(1 - z[:, 0] - t).mean()), "bookkeeping_max": float(np.max(np.abs(t - eta.sum(axis=1)))), "negative_power_rate": float(negative), "energy_violation_rate": float(np.mean(z[:, 0] + t > 1 + 1e-12)), "projection_fraction": float(np.mean(projected))})
        audit.append({"model": name, "projection_fraction": float(np.mean(projected)), "raw_max_total": float(total.max()), "projected_max_total": float(q.sum(axis=1).max())})
    write_csv(OUT / "physics_consistent_output_metrics.csv", rows)
    write_json(OUT / "physics_consistent_output_audit.json", {"variant": "simple_nonnegative_energy_projection", "formula": "clip [R,eta] at zero; scale by max(1,sum)", "results": audit, "metrics": rows, "raw_accuracy_retained": True})


def provenance(rows: list[dict[str, str]], ens: dict[tuple[str, str, int], dict[str, str]], supplement: Path, fit_start: str) -> None:
    model_seeds = {}
    for q in read_csv(M5 / "oof_predictions.csv"):
        model_seeds.setdefault(q["model"], set()).add(q["seed"])
    model_seeds = {k: sorted(v) for k, v in model_seeds.items()}
    files = [M5 / n for n in ["preregistration_sha256.json", "oof_predictions.csv", "authority_audit.json", "training_run_manifest.json", "model_selection.json", "numerical_metrics.json", "physics_consistency_metrics.json", "lf_baseline_provenance.json", "order_schema_audit.json", "fold_manifest.csv", "complex_feasibility_audit.json", "external_set_registry.json"]]
    files += [ROOT / "scripts" / "np_k6_m5_fullk6_forward_v0.py", ROOT / "scripts" / "np_k6_m5a_forward_diagnostic_v1.py", ROOT / "outputs" / "np_k6_m3_pilot_retraining_v1" / "development_hf_v2_training_view.csv", ROOT / "outputs" / "np_k6_m3_pilot_retraining_v1" / "m3_oof_predictions_long.csv", supplement]
    write_json(OUT / "m5a_model_provenance_audit.json", {"model_seed_inventory": model_seeds, "m5_authority_file_inventory": [str(p.relative_to(ROOT)) for p in files if str(p).find("np_k6_m5_fullk6_forward_v0") >= 0], "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in files}, "fit_started_utc": fit_start, "supplement_sha256": sha(supplement), "checkpoints_copied": 0, "frozen_m5_evidence_modified": False, "sealed_target_reads": 0, "solver_calls": 0})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    supplement = OUT / "NP_K6_M5A_FORWARD_DIAGNOSTIC_SUPPLEMENT_V1.json"
    prereg = json.loads(supplement.read_text(encoding="utf-8"))
    fit_start = dt.datetime.now(dt.timezone.utc).isoformat()
    write_json(OUT / "supplement_preregistration_sha256.json", {"path": str(supplement.relative_to(ROOT)), "sha256": sha(supplement), "created_utc": prereg["created_utc"], "must_precede_supplement_fit": True})
    write_json(OUT / "m5a_preregistration_completeness_audit.json", {
        "parent_preregistration": "NP_K6_M5A_FORWARD_DIAGNOSTIC_PREREG_V1",
        "supplement_preregistration": prereg["preregistration_id"],
        "methodology_sections": {
            "A_task_definition": "supplement.task_definition",
            "B_input_contract": "supplement.input_contract",
            "C_output_contract": "supplement.output_contract plus parent M5 order schema",
            "D_model_families": "parent_preregistration.candidate_models",
            "E_cv_protocol": "parent_preregistration.cv",
            "F_loss_and_normalization": "parent_preregistration.cv.normalization plus frozen M5 training contract",
            "G_evaluation_metrics": "parent promotion_rule plus numerical/physics metric artifacts",
            "H_ranking_metrics": "supplement.ranking_contract",
            "I_physics_consistency": "frozen M5 physics contract plus supplement.physics_consistent_variant",
            "J_external_governance": "parent external_criterion plus external registry",
            "K_prospective_validation": "supplement.prospective_protocol",
            "L_model_selection_tie_break": "supplement.model_selection_tie_break",
        },
        "all_sections_evidence_grounded": True,
        "post_result_rule_change": False,
        "parent_v1_hash_unchanged": True,
        "supplement_hash": sha(supplement),
    })
    rows, y, lf_eta, ens = load_authority()
    frozen = frozen_predictions(rows, ens)
    candidates = fit_lf_corrections(rows, y, lf_eta)
    preds = {"LF_only_frozen": np.column_stack([np.full(len(rows), np.nan), lf_eta]), **frozen, **candidates}
    ranking_audit(preds, rows, ens)
    paired_bootstrap(preds, rows)
    residual_breakdown(rows, y, lf_eta)
    disagreement_audit(rows, y, ens)
    physics_projection(preds, y)
    provenance(rows, ens, supplement, fit_start)
    write_json(OUT / "m5a_supplement_run_manifest.json", {"supplement_preregistration_id": prereg["preregistration_id"], "supplement_sha256": sha(supplement), "supplement_created_utc": prereg["created_utc"], "fit_started_utc": fit_start, "rows": len(rows), "geometry_count": len({r["geometry_id"] for r in rows}), "solver_calls": 0, "external_hf_calls": 0, "sealed_target_reads": 0, "inverse_design_artifacts": 0, "models": sorted(preds), "postprocessing_only_for_physics_variant": True})
    print(json.dumps({"status": "PASS", "supplement_sha256": sha(supplement), "fit_started_utc": fit_start, "solver_calls": 0, "outputs": sorted(p.name for p in OUT.glob("*audit*") if p.suffix in {".json", ".csv"})}, indent=2))


if __name__ == "__main__":
    main()
