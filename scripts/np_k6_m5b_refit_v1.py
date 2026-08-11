from __future__ import annotations

import csv, json, hashlib, datetime, math, re, os, random
from pathlib import Path
from collections import defaultdict

import numpy as np

ROOT = Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
M5 = ROOT / "outputs" / "np_k6_m5_fullk6_forward_v0"
OUT = ROOT / "outputs" / "np_k6_m5b_forward_formulation_repair_v1"
SCHEMA_PATH = OUT / "NP_K6_AUTHORITATIVE_OUTPUT_SCHEMA_V1.json"
WLS = list(range(445, 456))
SEEDS = [17, 29, 43]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(obj), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rank_values(x):
    x = np.asarray(x, float)
    order = np.argsort(-x, kind="mergesort")
    r = np.empty(len(x), float)
    r[order] = np.arange(1, len(x) + 1)
    return r


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(rank_values(a), rank_values(b))[0, 1])


def parse_diameters(g):
    return [float(x) for x in re.findall(r"D(\d+)", g)]


def load_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    vector = list(schema["primary_vector"])
    index = {name: i for i, name in enumerate(vector)}
    eta_names = [name for name in vector if name.startswith("eta_")]
    return schema, vector, index, eta_names, index[schema["eta_plus1_symbolic_key"]]


def load_authority(schema, vector, index, eta_names):
    rows = read_csv(M5 / "m5_training_view_286rows.csv")
    oof_rows = read_csv(M5 / "oof_predictions.csv")
    by = defaultdict(dict)
    for q in oof_rows:
        if q["seed"] == "ensemble":
            by[q["model"]][(q["case_id"], int(q["wavelength_nm"]))] = q
    keys = [(r["case_id"], int(r["wavelength_nm"])) for r in rows]
    y = np.asarray([[float(r["R_total"])] + [float(r[name]) for name in eta_names] for r in rows], float)
    lf = np.full_like(y, np.nan)
    for i, key in enumerate(keys):
        q = by["lf_only"][key]
        for name in eta_names:
            lf[i, index[name]] = float(q["pred_" + name])
    frozen = {}
    for model in ["direct_mlp", "resmlp", "residual_mlp", "circular_cnn"]:
        p = np.full_like(y, np.nan)
        for i, key in enumerate(keys):
            q = by[model][key]
            if q.get("pred_R", "") not in ("", "None"):
                p[i, index["R"]] = float(q["pred_R"])
            for name in eta_names:
                p[i, index[name]] = float(q["pred_" + name])
        frozen[model] = p
    geometry = np.asarray([r["geometry_id"] for r in rows])
    features = []
    for r in rows:
        d = np.asarray(parse_diameters(r["geometry_id"]), float) / 230.0
        gaps = np.roll(d, -1) - d
        wl = (int(r["wavelength_nm"]) - 450.0) / 5.0
        pol = 1.0 if r["polarization"] == "s" else 0.0
        features.append(np.r_[d, gaps, wl, pol])
    return rows, keys, y, lf, frozen, geometry, np.asarray(features, float)


def normalize(x, tr):
    mu = x[tr].mean(axis=0)
    sd = x[tr].std(axis=0)
    sd[sd < 1e-10] = 1.0
    return (x - mu) / sd


def project(pred, index, eta_names):
    q = np.asarray(pred, float).copy()
    ri = index["R"]
    ei = [index[n] for n in eta_names]
    if np.isfinite(q[:, ri]).any():
        q[:, ri] = np.maximum(q[:, ri], 0.0)
    q[:, ei] = np.maximum(q[:, ei], 0.0)
    for i in range(len(q)):
        r = q[i, ri] if np.isfinite(q[i, ri]) else 0.0
        s = float(q[i, ei].sum())
        if r + s > 1.0 and s > 0:
            q[i, ei] *= max(0.0, 1.0 - r) / s
    return q


def pair_indices(rows, train_idx, geometry):
    trset = set(int(i) for i in train_idx)
    out = []
    for g in sorted(set(geometry[train_idx])):
        for wl in WLS:
            p = next((i for i in train_idx if rows[i]["geometry_id"] == g and int(rows[i]["wavelength_nm"]) == wl and rows[i]["polarization"] == "p"), None)
            s = next((i for i in train_idx if rows[i]["geometry_id"] == g and int(rows[i]["wavelength_nm"]) == wl and rows[i]["polarization"] == "s"), None)
            if p is not None and s is not None and p in trset and s in trset:
                out.append((p, s))
    return out


def fit_refit(rows, y, lf, features, geometry, index, eta_names):
    from sklearn.linear_model import Ridge
    from sklearn.neural_network import MLPRegressor

    n = len(rows)
    models = ["LF_global_bias", "LF_wavelength_polarization_affine", "LF_ridge_residual", "LF_paired_shared_contrast", "corrected_residual_mlp"]
    preds = {m: np.full((n, len(index)), np.nan) for m in models}
    mlp_seed_preds = {s: np.full((n, len(index)), np.nan) for s in SEEDS}
    eta_i = [index[name] for name in eta_names]
    delta_target = y[:, eta_i] - lf[:, eta_i]
    f_all = np.c_[features, lf[:, eta_i]]
    for held in sorted(set(geometry)):
        te = np.where(geometry == held)[0]
        tr = np.where(geometry != held)[0]
        f_norm = normalize(f_all, tr)
        # A: fold-local LF bias calibration.
        a = np.full((len(te), len(index)), np.nan)
        a[:, index["R"]] = y[tr, index["R"]].mean()
        a[:, eta_i] = lf[te[:, None], eta_i] + delta_target[tr].mean(axis=0)
        preds["LF_global_bias"][te] = a
        # B: direct affine ridge, with ordered geometry features preserved.
        rb = Ridge(alpha=0.1).fit(f_norm[tr], y[tr])
        preds["LF_wavelength_polarization_affine"][te] = rb.predict(f_norm[te])
        # C: residual ridge; only eta receives LF baseline reconstruction.
        rc = Ridge(alpha=0.1).fit(f_norm[tr], np.c_[y[tr, index["R"]], delta_target[tr]])
        z = rc.predict(f_norm[te])
        c = np.full((len(te), len(index)), np.nan)
        c[:, index["R"]] = z[:, 0]
        c[:, eta_i] = lf[te[:, None], eta_i] + z[:, 1:]
        preds["LF_ridge_residual"][te] = c
        # D: paired common/contrast residual, retaining explicit P/S identity.
        pairs = pair_indices(rows, tr, geometry)
        pf = np.asarray([f_norm[p] for p, _ in pairs], float)
        common = []
        contrast = []
        for p, s in pairs:
            common.append(np.r_[0.5 * (y[p, index["R"]] + y[s, index["R"]]), 0.5 * (delta_target[p] + delta_target[s])])
            contrast.append(np.r_[0.5 * (y[p, index["R"]] - y[s, index["R"]]), 0.5 * (delta_target[p] - delta_target[s])])
        if pairs:
            cm = Ridge(alpha=0.1).fit(pf, np.asarray(common))
            ct = Ridge(alpha=0.1).fit(pf, np.asarray(contrast))
            for i in te:
                sign = 1.0 if rows[i]["polarization"] == "p" else -1.0
                u = f_norm[i:i+1]
                cc = cm.predict(u)[0]; dd = ct.predict(u)[0]
                q = np.full(len(index), np.nan)
                q[index["R"]] = cc[0] + sign * dd[0]
                q[eta_i] = lf[i, eta_i] + cc[1:] + sign * dd[1:]
                preds["LF_paired_shared_contrast"][i] = q
        # E: compact corrected residual MLP, three preregistered deterministic seeds.
        target = np.c_[y[tr, index["R"]], delta_target[tr]]
        for seed in SEEDS:
            random.seed(seed); np.random.seed(seed)
            net = MLPRegressor(hidden_layer_sizes=(32,), activation="tanh", solver="adam", alpha=1e-4,
                               learning_rate_init=0.01, max_iter=350, random_state=seed, early_stopping=False)
            net.fit(f_norm[tr], target)
            z = net.predict(f_norm[te])
            q = np.full((len(te), len(index)), np.nan)
            q[:, index["R"]] = z[:, 0]
            q[:, eta_i] = lf[te[:, None], eta_i] + z[:, 1:]
            mlp_seed_preds[seed][te] = q
        preds["corrected_residual_mlp"][te] = np.nanmean(np.stack([mlp_seed_preds[s][te] for s in SEEDS]), axis=0)
    return preds, mlp_seed_preds


def aggregate_eta(rows, pred, index, eta_plus_idx):
    geos = sorted(set(r["geometry_id"] for r in rows))
    vals = []
    for g in geos:
        pp = []
        for pol in ["p", "s"]:
            ix = [i for i, r in enumerate(rows) if r["geometry_id"] == g and r["polarization"] == pol]
            pp.append(float(np.nanmean(pred[ix, eta_plus_idx])))
        vals.append(float(np.mean(pp)))
    return geos, np.asarray(vals)


def metrics(rows, truth, pred, index, eta_names, eta_plus_idx):
    eta_i = [index[n] for n in eta_names]
    true_eta = truth[:, eta_i]
    eta = pred[:, eta_i]
    ae = np.abs(eta - true_eta)
    finite_r = np.isfinite(pred[:, index["R"]])
    r_mae = float(np.mean(np.abs(pred[finite_r, index["R"]] - truth[finite_r, index["R"]]))) if finite_r.any() else float("nan")
    t_true = true_eta.sum(axis=1); t_hat = eta.sum(axis=1)
    geos = sorted(set(r["geometry_id"] for r in rows))
    geom_err = {g: float(np.mean([ae[i].mean() for i, r in enumerate(rows) if r["geometry_id"] == g])) for g in geos}
    ps_contrast = []
    for g in geos:
        for wl in WLS:
            ip = next(i for i, r in enumerate(rows) if r["geometry_id"] == g and int(r["wavelength_nm"]) == wl and r["polarization"] == "p")
            is_ = next(i for i, r in enumerate(rows) if r["geometry_id"] == g and int(r["wavelength_nm"]) == wl and r["polarization"] == "s")
            ps_contrast.append(abs((pred[ip, eta_plus_idx] - pred[is_, eta_plus_idx]) - (truth[ip, eta_plus_idx] - truth[is_, eta_plus_idx])))
    true_rank = aggregate_eta(rows, truth, index, eta_plus_idx)[1]
    pred_rank = aggregate_eta(rows, pred, index, eta_plus_idx)[1]
    order = np.argsort(-true_rank)
    porder = np.argsort(-pred_rank)
    top3 = float(len(set(order[:3]) & set(porder[:3])) / 3.0)
    top5 = float(len(set(order[:5]) & set(porder[:5])) / 5.0)
    pred_rank_pos = int(np.where(porder == order[0])[0][0] + 1)
    neg_parts = [eta.ravel() < 0]
    if finite_r.any(): neg_parts.append(pred[finite_r, index["R"]])
    neg = float(np.mean(np.concatenate(neg_parts) < 0)) if neg_parts else 0.0
    energy = float(np.mean(np.abs(1.0 - pred[finite_r, index["R"]] - t_hat[finite_r]))) if finite_r.any() else float("nan")
    pol_mae = {}
    for pol in ["p", "s"]:
        ix = [i for i, r in enumerate(rows) if r["polarization"] == pol]
        pol_mae[pol] = float(np.mean(ae[ix, eta_names.index("eta_m+1")]))
    return {
        "order_profile_mae": float(ae.mean()), "order_profile_rmse": float(np.sqrt(np.mean((eta - true_eta) ** 2))),
        "eta_plus1_mae": float(np.mean(ae[:, eta_names.index("eta_m+1")])),
        "eta_plus1_rmse": float(np.sqrt(np.mean((eta[:, eta_names.index("eta_m+1")] - true_eta[:, eta_names.index("eta_m+1")]) ** 2))),
        "eta_0_mae": float(np.mean(ae[:, eta_names.index("eta_m+0")])),
        "eta_minus1_mae": float(np.mean(ae[:, eta_names.index("eta_m-1")])),
        "R_mae": r_mae, "T_mae": float(np.mean(np.abs(t_hat - t_true))),
        "negative_power_rate": neg, "energy_residual_mae": energy,
        "bookkeeping_max": float(np.max(np.abs(t_hat - eta.sum(axis=1)))),
        "ranking_spearman": spearman(true_rank, pred_rank), "top3_recall": top3, "top5_recall": top5,
        "true_champion_predicted_rank": pred_rank_pos, "near_champion_retrieval": float(len(set(order[:3]) & set(porder[:5])) > 0),
        "worst_geometry_mae": float(max(geom_err.values())), "worst_geometry": max(geom_err, key=geom_err.get),
        "ps_contrast_mae": float(np.mean(ps_contrast)), "P_eta_plus1_mae": pol_mae["p"], "S_eta_plus1_mae": pol_mae["s"],
        "geometry_errors": geom_err,
    }


def main():
    schema, vector, index, eta_names, eta_plus_idx = load_schema()
    rows, keys, truth, lf, frozen, geometry, features = load_authority(schema, vector, index, eta_names)
    n = len(rows)
    if n != 286 or len(set(geometry)) != 13:
        raise RuntimeError("M5B authority shape mismatch")
    fit_start = now()
    refit_preds, seed_preds = fit_refit(rows, truth, lf, features, geometry, index, eta_names)
    all_preds = {"LF_only_frozen": lf.copy()}
    all_preds.update(refit_preds)
    all_preds["M5_direct_MLP_frozen"] = frozen["direct_mlp"]
    all_preds["M5_ResMLP_frozen"] = frozen["resmlp"]
    all_preds["M5_CircularCNN_frozen"] = frozen["circular_cnn"]
    # Correct the frozen residual OOF deterministically: R direct, eta LF + raw delta.
    raw_res = frozen["residual_mlp"]
    corrected = raw_res.copy()
    eta_i = [index[nm] for nm in eta_names]
    corrected[:, eta_i] = lf[:, eta_i] + raw_res[:, eta_i]
    all_preds["M5B_corrected_no_refit_residual_mlp"] = corrected
    metric_rows = []
    metric_map = {}
    for name, pred in all_preds.items():
        mm = metrics(rows, truth, pred, index, eta_names, eta_plus_idx)
        metric_map[name + "_raw"] = mm
        metric_rows.append({"model": name, "variant": "raw", **{k: v for k, v in mm.items() if k != "geometry_errors"}})
        constrained = project(pred, index, eta_names)
        mc = metrics(rows, truth, constrained, index, eta_names, eta_plus_idx)
        metric_map[name + "_constrained"] = mc
        metric_rows.append({"model": name, "variant": "constrained", **{k: v for k, v in mc.items() if k != "geometry_errors"}})
    write_csv(OUT / "m5b_refit_metrics.csv", metric_rows)
    ge_rows = []
    for name, pred in all_preds.items():
        mm = metric_map[name + "_raw"]
        for g, e in mm["geometry_errors"].items():
            ge_rows.append({"model": name, "variant": "raw", "geometry_id": g, "order_profile_mae": e})
        c = project(pred, index, eta_names)
        mc = metric_map[name + "_constrained"]
        for g, e in mc["geometry_errors"].items():
            ge_rows.append({"model": name, "variant": "constrained", "geometry_id": g, "order_profile_mae": e})
    write_csv(OUT / "m5b_refit_geometry_metrics.csv", ge_rows)
    ranking_rows = [{"model": r["model"], "variant": r["variant"], "ranking_spearman": r["ranking_spearman"], "top3_recall": r["top3_recall"], "top5_recall": r["top5_recall"], "true_champion_predicted_rank": r["true_champion_predicted_rank"], "near_champion_retrieval": r["near_champion_retrieval"]} for r in metric_rows]
    write_csv(OUT / "m5b_refit_ranking_metrics.csv", ranking_rows)
    subgroup_rows = []
    for name, pred in all_preds.items():
        for variant, q in [("raw", pred), ("constrained", project(pred, index, eta_names))]:
            for pol in ["p", "s"]:
                ix = [i for i, r in enumerate(rows) if r["polarization"] == pol]
                subgroup_rows.append({"model": name, "variant": variant, "group": "polarization", "value": pol, "eta_plus1_mae": float(np.mean(np.abs(q[ix, eta_plus_idx] - truth[ix, eta_plus_idx])))})
            for wl in WLS:
                ix = [i for i, r in enumerate(rows) if int(r["wavelength_nm"]) == wl]
                subgroup_rows.append({"model": name, "variant": variant, "group": "wavelength", "value": wl, "eta_plus1_mae": float(np.mean(np.abs(q[ix, eta_plus_idx] - truth[ix, eta_plus_idx])))})
    write_csv(OUT / "m5b_refit_subgroup_metrics.csv", subgroup_rows)
    # Seed disagreement is an audit, not a probability calibration claim.
    dis_rows = []
    ens = refit_preds["corrected_residual_mlp"]
    stack = np.stack([seed_preds[s] for s in SEEDS])
    d = np.nanstd(stack[:, :, eta_plus_idx], axis=0)
    e = np.abs(ens[:, eta_plus_idx] - truth[:, eta_plus_idx])
    for i, r in enumerate(rows):
        dis_rows.append({"case_id": r["case_id"], "geometry_id": r["geometry_id"], "polarization": r["polarization"], "wavelength_nm": r["wavelength_nm"], "eta_plus1_ensemble_disagreement": float(d[i]), "eta_plus1_abs_error": float(e[i])})
    write_csv(OUT / "m5b_uncertainty_disagreement.csv", dis_rows)
    # Raw and constrained prediction table for reproducible downstream audits.
    pred_rows = []
    for name, pred in all_preds.items():
        for variant, q in [("raw", pred), ("constrained", project(pred, index, eta_names))]:
            for i, r in enumerate(rows):
                z = {"model": name, "variant": variant, "case_id": r["case_id"], "geometry_id": r["geometry_id"], "polarization": r["polarization"], "wavelength_nm": r["wavelength_nm"]}
                for nm in vector:
                    z["pred_" + nm] = q[i, index[nm]]
                z["pred_T_derived"] = float(np.nansum(q[i, eta_i]))
                pred_rows.append(z)
    write_csv(OUT / "m5b_refit_candidate_oof.csv", pred_rows)
    # Promotion gates are frozen and evaluated on constrained outputs for learned candidates.
    lf = metric_map["LF_only_frozen_constrained"]
    gate_rows = []
    for name in ["LF_global_bias", "LF_wavelength_polarization_affine", "LF_ridge_residual", "LF_paired_shared_contrast", "corrected_residual_mlp", "M5_direct_MLP_frozen", "M5_ResMLP_frozen", "M5_CircularCNN_frozen", "M5B_corrected_no_refit_residual_mlp"]:
        mm = metric_map[name + "_constrained"]
        improved = sum(mm["geometry_errors"][g] < lf["geometry_errors"][g] for g in mm["geometry_errors"])
        gates = {
            "order_profile": mm["order_profile_mae"] <= lf["order_profile_mae"],
            "eta_plus1": mm["eta_plus1_mae"] < lf["eta_plus1_mae"],
            "ranking": mm["ranking_spearman"] >= lf["ranking_spearman"] - 0.05,
            "worst_geometry": mm["worst_geometry_mae"] <= lf["worst_geometry_mae"] * 1.05,
            "negative_power": mm["negative_power_rate"] <= 1e-6,
            "energy": mm["energy_residual_mae"] <= 0.15,
            "ps_contrast": mm["ps_contrast_mae"] < lf["ps_contrast_mae"],
            "paired_geometry_improvement_count": improved >= 8,
            "R_T_quantitative": math.isfinite(mm["R_mae"]) and math.isfinite(mm["T_mae"]),
        }
        gate_rows.append({"model": name, **gates, "paired_geometry_improvement_count": improved, "promotion_pass": all(gates.values())})
    write_csv(OUT / "m5b_promotion_gate.csv", gate_rows)
    passed = [r for r in gate_rows if r["promotion_pass"] and not r["model"].endswith("frozen")]
    status = "NP_K6_M5B_FORMULATION_REPAIR_COMPLETE_EXTERNAL_HF_READY" if passed else "NP_K6_M5B_FORMULATION_REPAIR_COMPLETE_MORE_DEVELOPMENT_HF_REQUIRED"
    # Common HF9 comparison uses only metadata membership from the existing development view.
    hf9 = {r["geometry_id"] for r in read_csv(ROOT / "outputs" / "np_k6_m3_pilot_retraining_v1" / "development_hf_v2_training_view.csv")}
    common = []
    for name, pred in all_preds.items():
        ix = [i for i, r in enumerate(rows) if r["geometry_id"] in hf9]
        if ix:
            mm = metrics([rows[i] for i in ix], truth[ix], pred[ix], index, eta_names, eta_plus_idx)
            common.append({"model": name, "rows": len(ix), "order_profile_mae": mm["order_profile_mae"], "eta_plus1_mae": mm["eta_plus1_mae"]})
    dump(OUT / "m5b_common_hf9_comparison.json", {"hf9_geometry_count": len(hf9), "comparisons": common, "historical_m3_m5_numbers_not_directly_pooled": True})
    dump(OUT / "m5b_residual_reconstruction_audit.json", {"historical_raw_residual_target": "delta=HF-LF", "corrected_formula": "eta_hat=LF_eta+delta_hat", "R_head": "direct_R_head", "no_refit_reconstruction_performed": True, "raw_vs_corrected_files": ["m5b_residual_reconstruction_metrics.csv", "m5b_refit_metrics.csv"], "implementation_issue_preserved": True})
    dump(OUT / "m5b_refit_physics_audit.json", {"constraint": "nonnegative power and energy-budget projection", "raw_and_constrained_reported": True, "no_truth_mutation": True, "eta_plus1_symbolic_key": schema["eta_plus1_symbolic_key"], "eta_plus1_index": eta_plus_idx, "models": {k: {"raw": metric_map[k + "_raw"], "constrained": metric_map[k + "_constrained"]} for k in all_preds}})
    dump(OUT / "m5b_final_decision.json", {"status": status, "development_incumbent": "LF_only_frozen", "promotion_pass_models": [r["model"] for r in passed], "promotion_rule_frozen": True, "external_registry": "NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1", "external_target_reads": 0, "solver_calls": 0, "sealed_target_reads": 0, "inverse_design_artifacts": 0, "reason": "No learned full-response candidate passed every corrected numerical, ranking, worst-case, P/S and physics gate." if not passed else "A corrected candidate passed all gates; external authorization remains a separate user gate."})
    prereg_hash = json.loads((OUT / "m5b_preregistration_sha256.json").read_text())["prereg_sha256"]
    add_hash = json.loads((OUT / "m5b_refit_addendum_sha256.json").read_text())["sha256"]
    manifest = {"status": "PASS", "fit_started_utc": fit_start, "fit_finished_utc": now(), "preregistration_sha256": prereg_hash, "refit_addendum_sha256": add_hash, "schema_sha256": sha(SCHEMA_PATH), "rows": n, "geometry_count": len(set(geometry)), "paired_cases": 26, "wavelengths": WLS, "models": list(all_preds), "seeds": SEEDS, "outer_cv": "13-fold LOGO", "normalization": "fold-local", "refit_count": 1, "solver_calls": 0, "external_hf_calls": 0, "sealed_target_reads": 0, "inverse_design_artifacts": 0, "sealed_metadata_only": True, "history_frozen": True}
    dump(OUT / "m5b_refit_manifest.json", manifest)
    dump(OUT / "m5b_solver_zero_audit.json", {"solver_calls": 0, "fdtd_run_calls": 0, "lumapi_solver_run_calls": 0, "new_hf_acquisition": 0, "external_hf_calls": 0, "sealed_target_reads": 0, "inverse_design_artifacts": 0})
    print(json.dumps({"status": status, "rows": n, "geometries": len(set(geometry)), "eta_plus1_index": eta_plus_idx, "promotion_pass_models": [r["model"] for r in passed], "solver_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
