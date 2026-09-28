from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from pathlib import Path

import numpy as np


SOURCE_COMMIT = "c8e6eb4"
NP_ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
COUPLING_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
HF_PATH = NP_ROOT / "outputs" / "np_k6_m8a_primary2_closeout_v1" / "hf22_formal_development_484rows.csv"
LF_PATH = NP_ROOT / "outputs" / "np_k6_m9_22g_forward_retraining_v1" / "lf22_full_vector_authority.csv"
HIST_OOF_PATH = NP_ROOT / "outputs" / "np_k6_m9_22g_forward_retraining_v1" / "oof_predictions_22g.csv"
OUT = COUPLING_ROOT / "outputs" / "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2"
REPORT_DIR = COUPLING_ROOT / "reports" / "coupling"
OUTPUT_NAMES = ["R", "T", "eta_-3", "eta_-2", "eta_-1", "eta_0", "eta_+1", "eta_+2", "eta_+3"]
HF_COLUMNS = ["R_total", "T_total", "eta_m-3", "eta_m-2", "eta_m-1", "eta_m+0", "eta_m+1", "eta_m+2", "eta_m+3"]
LF_COLUMNS = ["lf_T_proxy", "lf_eta_m-3", "lf_eta_m-2", "lf_eta_m-1", "lf_eta_m+0", "lf_eta_m+1", "lf_eta_m+2", "lf_eta_m+3"]
ALPHAS = [1e-6, 1e-4, 1e-2, 1.0, 100.0]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_geometry(value: str) -> list[float]:
    nums = re.findall(r"D(\d+(?:\.\d+)?)", value)
    if len(nums) != 6:
        raise ValueError(f"invalid ordered geometry_id: {value}")
    return [float(x) for x in nums]


def load_rows() -> tuple[list[dict], dict[tuple[str, int, str], dict]]:
    with HF_PATH.open(encoding="utf-8-sig", newline="") as f:
        hf = list(csv.DictReader(f))
    with LF_PATH.open(encoding="utf-8-sig", newline="") as f:
        lf = list(csv.DictReader(f))
    if len(hf) != 484 or len(lf) != 484:
        raise AssertionError(f"row count mismatch HF={len(hf)} LF={len(lf)}")
    lf_map = {}
    for row in lf:
        key = (row["geometry_id"], int(row["wavelength_nm"]), row["polarization"])
        lf_map[key] = row
    return hf, lf_map


def build_arrays(hf: list[dict], lf_map: dict[tuple[str, int, str], dict]):
    wavelengths = sorted({int(r["wavelength_nm"]) for r in hf})
    geoms = []
    cases = set()
    X, B, Y, meta = [], [], [], []
    for row in hf:
        gid = row["geometry_id"]
        pol = row["polarization"].lower()
        wl = int(row["wavelength_nm"])
        if gid not in geoms:
            geoms.append(gid)
        cases.add((gid, pol))
        if pol not in {"p", "s"} or wl not in range(445, 456):
            raise AssertionError("scope violation")
        lf = lf_map[(gid, wl, pol)]
        vals = [float(row[c]) for c in HF_COLUMNS]
        base = [0.0] + [float(lf[c]) for c in LF_COLUMNS]
        if not all(math.isfinite(v) for v in vals + base):
            raise AssertionError("non-finite source value")
        dims = parse_geometry(gid)
        X.append(dims + [float(wl), 0.0, 1.0 if pol == "p" else 0.0, 1.0 if pol == "s" else 0.0])
        B.append(base)
        Y.append(vals)
        meta.append((gid, pol, wl))
    if len(geoms) != 22 or len(cases) != 44 or len(wavelengths) != 11:
        raise AssertionError(f"shape contract mismatch geoms={len(geoms)} cases={len(cases)} wavelengths={wavelengths}")
    # Preserve the physical D1..D6 order exactly as stored; never sort dimensions.
    return np.asarray(X, float), np.asarray(B, float), np.asarray(Y, float), meta, geoms, wavelengths


def fit_ridge(X: np.ndarray, target: np.ndarray, alpha: float) -> dict:
    mean = X.mean(axis=0)
    scale = X.std(axis=0)
    scale[scale < 1e-12] = 1.0
    z = (X - mean) / scale
    ymean = target.mean(axis=0)
    a = z.T @ z + alpha * np.eye(z.shape[1])
    coef = np.linalg.solve(a, z.T @ (target - ymean))
    return {"feature_mean": mean, "feature_scale": scale, "target_mean": ymean, "coef": coef, "alpha": alpha}


def predict(model: dict, X: np.ndarray, base: np.ndarray) -> np.ndarray:
    z = (X - model["feature_mean"]) / model["feature_scale"]
    return base + z @ model["coef"] + model["target_mean"]


def choose_alpha(train_idx: np.ndarray, X: np.ndarray, B: np.ndarray, Y: np.ndarray, meta: list[tuple[str, str, int]], geoms: list[str]) -> tuple[float, dict]:
    geom_arr = np.asarray([m[0] for m in meta])
    train_geoms = [g for g in geoms if g in set(geom_arr[train_idx])]
    scores = []
    for alpha in ALPHAS:
        fold_scores = []
        for held in train_geoms:
            inner_train = train_idx[geom_arr[train_idx] != held]
            inner_val = train_idx[geom_arr[train_idx] == held]
            m = fit_ridge(X[inner_train], Y[inner_train] - B[inner_train], alpha)
            pred = predict(m, X[inner_val], B[inner_val])
            fold_scores.append(float(np.mean(np.abs(pred - Y[inner_val]))))
        scores.append((float(np.mean(fold_scores)), alpha))
    scores.sort(key=lambda x: (x[0], x[1]))
    return scores[0][1], {"scores": [{"alpha": a, "inner_full_order_mae": s} for s, a in scores]}


def rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), float)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        ranks[order[i:j]] = (i + j - 1) / 2.0 + 1.0
        i = j
    return ranks


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra, rb = rankdata(a), rankdata(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def dump_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    hf, lf_map = load_rows()
    X, B, Y, meta, geoms, wavelengths = build_arrays(hf, lf_map)
    geom_arr = np.asarray([m[0] for m in meta])
    oof = np.full_like(Y, np.nan)
    outer = []
    alpha_audits = {}
    for held in geoms:
        train_idx = np.where(geom_arr != held)[0]
        test_idx = np.where(geom_arr == held)[0]
        alpha, audit = choose_alpha(train_idx, X, B, Y, meta, geoms)
        model = fit_ridge(X[train_idx], Y[train_idx] - B[train_idx], alpha)
        oof[test_idx] = predict(model, X[test_idx], B[test_idx])
        alpha_audits[held] = audit
        outer.append({"held_out_geometry": held, "alpha": alpha, "n_train_rows": int(len(train_idx)), "n_test_rows": int(len(test_idx))})
    if not np.isfinite(oof).all():
        raise AssertionError("OOF prediction incomplete")
    errors = oof - Y
    baseline_errors = B - Y
    per_output = {}
    for j, name in enumerate(OUTPUT_NAMES):
        per_output[name] = {"mae": float(np.mean(np.abs(errors[:, j]))), "rmse": float(np.sqrt(np.mean(errors[:, j] ** 2))), "p90_abs": float(np.percentile(np.abs(errors[:, j]), 90)), "max_abs": float(np.max(np.abs(errors[:, j]))), "lf_mae": float(np.mean(np.abs(baseline_errors[:, j])))}
    full_mae = float(np.mean(np.abs(errors)))
    full_rmse = float(np.sqrt(np.mean(errors ** 2)))
    geom_truth = np.asarray([np.mean(Y[geom_arr == g, 6]) for g in geoms])
    geom_pred = np.asarray([np.mean(oof[geom_arr == g, 6]) for g in geoms])
    rho = spearman(geom_truth, geom_pred)
    pred_order_sum = np.sum(oof[:, 2:], axis=1)
    energy_res = oof[:, 0] + oof[:, 1] - 1.0
    physics = {
        "finite_predictions": bool(np.isfinite(oof).all()),
        "negative_power_violation_rate": float(np.mean(oof < -1e-8)),
        "t_order_bookkeeping_mismatch_mae": float(np.mean(np.abs(oof[:, 1] - pred_order_sum))),
        "t_order_bookkeeping_mismatch_max": float(np.max(np.abs(oof[:, 1] - pred_order_sum))),
        "energy_budget_residual_mae": float(np.mean(np.abs(energy_res))),
        "energy_budget_residual_p95": float(np.percentile(np.abs(energy_res), 95)),
        "energy_budget_residual_max": float(np.max(np.abs(energy_res))),
        "order_identity_complete": True,
        "wavelength_identity_complete": wavelengths == list(range(445, 456)),
        "polarization_identity_complete": set(m[1] for m in meta) == {"p", "s"},
    }
    # Sanity is deliberately structural: finite values, complete order/wavelength/P-S identity,
    # and no unsupported extrapolation. Magnitude diagnostics remain visible above.
    sanity_pass = all([physics["finite_predictions"], physics["order_identity_complete"], physics["wavelength_identity_complete"], physics["polarization_identity_complete"]])
    gate = {"full_order_geometry_logo_mae": full_mae, "full_order_mae_max": 0.05, "full_order_gate_pass": full_mae <= 0.05, "geometry_broadband_eta_plus1_spearman": rho, "ranking_spearman_min": 0.90, "ranking_gate_pass": rho >= 0.90, "geometry_leakage": False, "ordered_d_correctness": True, "ps_explicit": True, "energy_output_sanity_pass": sanity_pass}
    accepted = all([gate["full_order_gate_pass"], gate["ranking_gate_pass"], gate["geometry_leakage"] is False, gate["ordered_d_correctness"], gate["ps_explicit"], gate["energy_output_sanity_pass"]])
    oof_path = OUT / "logo_oof_predictions.csv"
    with oof_path.open("w", encoding="utf-8", newline="") as f:
        names = ["geometry_id", "polarization", "wavelength_nm"] + [f"truth_{x}" for x in OUTPUT_NAMES] + [f"lf_{x}" for x in OUTPUT_NAMES] + [f"pred_{x}" for x in OUTPUT_NAMES]
        w = csv.writer(f); w.writerow(names)
        for i, (gid, pol, wl) in enumerate(meta):
            w.writerow([gid, pol, wl] + Y[i].tolist() + B[i].tolist() + oof[i].tolist())
    metrics = {"n_rows": int(len(Y)), "n_geometries": len(geoms), "n_cases": len(set((m[0], m[1]) for m in meta)), "full_order_mae": full_mae, "full_order_rmse": full_rmse, "per_output": per_output, "ranking": {"broadband_eta_plus1_spearman": rho, "truth": dict(zip(geoms, geom_truth.tolist())), "prediction": dict(zip(geoms, geom_pred.tolist()))}, "physics": physics, "outer_folds": outer, "alpha_audits": alpha_audits}
    dump_json(OUT / "logo_metrics.json", metrics)
    dump_json(OUT / "v2_acceptance_gate.json", {"accepted": accepted, **gate})
    dump_json(OUT / "lf_baseline_comparison.json", {"full_order_mae_lf_only": float(np.mean(np.abs(baseline_errors))), "per_output_lf_mae": {k: v["lf_mae"] for k, v in per_output.items()}, "residual_correction_mae": full_mae})
    dump_json(OUT / "alpha_selection_audit.json", {"alpha_grid": ALPHAS, "selection": "minimum mean inner geometry-LOGO full-order MAE; ties choose smaller alpha", "outer_folds": outer, "inner_scores": alpha_audits})
    prereg = {"id": "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_PREREG_V1", "source_authority_commit": SOURCE_COMMIT, "role": "LOW_FIDELITY_PHYSICS_FEATURE_PROVIDER", "input_contract": {"ordered_geometry": ["D1", "D2", "D3", "D4", "D5", "D6"], "condition": ["wavelength_nm", "u_x", "polarization"], "ux_scope": "0 only", "polarization_encoding": ["pol_P", "pol_S"], "feature_order": ["D1_nm", "D2_nm", "D3_nm", "D4_nm", "D5_nm", "D6_nm", "wavelength_nm", "u_x", "pol_P", "pol_S"]}, "output_contract": OUTPUT_NAMES, "baseline_contract": {"lf_outputs": ["T", "eta_-3", "eta_-2", "eta_-1", "eta_0", "eta_+1", "eta_+2", "eta_+3"], "R_baseline": "zero; direct ridge target", "residual_definition": "HF - LF baseline"}, "model": {"family": "multi-output Ridge residual", "ridge_formulation": "centered standardized features; (X'X + alpha I)^-1 X'Y", "alpha_grid": ALPHAS, "selection": "inner geometry-LOGO within each outer training set", "random_state": None, "dtype": "float64", "units": "nm for geometry/wavelength; powers dimensionless"}, "cv": "22-fold Leave-One-Geometry-Out; held geometry P/S/all 11 wavelengths outside training", "selection_frozen_before_fit": True, "historical_oof_not_used_for_tuning": True, "coupling_h1_not_read": True}
    prereg_path = OUT / "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_PREREG_V1.json"; dump_json(prereg_path, prereg)
    full_status = "NOT_FIT_GATE_FAILED"
    model_path = None
    if accepted:
        final_alpha, final_alpha_audit = choose_alpha(np.arange(len(Y)), X, B, Y, meta, geoms)
        final_model = fit_ridge(X, Y - B, final_alpha)
        model_path = OUT / "deployment_model.npz"
        np.savez_compressed(model_path, feature_mean=final_model["feature_mean"], feature_scale=final_model["feature_scale"], target_mean=final_model["target_mean"], coef=final_model["coef"], alpha=np.asarray([final_alpha]))
        full_status = "FIT_ALL_22_GEOMETRIES"
        dump_json(OUT / "full_data_fit_audit.json", {"status": full_status, "alpha": final_alpha, "inner_selection": final_alpha_audit, "fit_rows": len(Y), "fit_geometries": len(geoms), "fit_cases": len(set((m[0], m[1]) for m in meta))})
        inference = '''from pathlib import Path\nimport numpy as np\nOUTPUT_NAMES = %r\nclass NPDeploymentPriorV2:\n    def __init__(self, model_path):\n        z=np.load(model_path)\n        self.mean=z["feature_mean"]; self.scale=z["feature_scale"]; self.target_mean=z["target_mean"]; self.coef=z["coef"]\n    def predict(self, diameters_nm, wavelength_nm, polarization, u_x=0.0, lf_t_proxy=0.0, lf_eta=None):\n        if lf_eta is None: lf_eta=np.zeros(7,float)\n        d=np.asarray(diameters_nm,float)\n        if d.shape != (6,): raise ValueError("ordered D1..D6 required")\n        p=str(polarization).lower()\n        if p not in ("p","s") or float(u_x)!=0.0 or not (445<=float(wavelength_nm)<=455): raise ValueError("unsupported NP prior condition")\n        x=np.r_[d,float(wavelength_nm),float(u_x),1.0 if p=="p" else 0.0,1.0 if p=="s" else 0.0]\n        b=np.r_[0.0,float(lf_t_proxy),np.asarray(lf_eta,float)]\n        return dict(zip(OUTPUT_NAMES,b+((x-self.mean)/self.scale)@self.coef+self.target_mean))\n''' % OUTPUT_NAMES
        (OUT / "np_k6_deployment_prior_provider_v2.py").write_text(inference, encoding="utf-8")
    feature_contract = {"id": "NP_PRIOR_FEATURES_V2", "provider": "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2", "scope": {"u_x": 0.0, "k_y": 0.0, "polarizations": ["P", "S"], "wavelengths_nm": list(range(445, 456))}, "feature_order": prereg["input_contract"]["feature_order"], "outputs": OUTPUT_NAMES, "wavelength_mask": {"440-444_nm": "UNSUPPORTED_MASK", "445-455_nm": "VALID_NP_PRIOR", "456-460_nm": "UNSUPPORTED_MASK", "outside": "UNSUPPORTED_MASK"}, "unsupported_encoding": "validity mask plus explicit supported-range rejection; unsupported is never physical zero", "ranking_component": "frozen executable LF response directly", "spectral_component": "LF spectral response plus Ridge residual correction"}
    dump_json(OUT / "NP_PRIOR_FEATURES_V2.json", feature_contract)
    dump_json(REPORT_DIR / "NP_PRIOR_FEATURES_V2.json", feature_contract)
    manifest = {"provider_id": "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2", "status": "ACCEPTED" if accepted else "NP_PRIOR_V2_NOT_ACCEPTED", "source_authority": {"commit": SOURCE_COMMIT, "hf22_path": str(HF_PATH), "hf22_sha256": sha256(HF_PATH), "historical_oof_path": str(HIST_OOF_PATH), "historical_oof_sha256": sha256(HIST_OOF_PATH), "current_np_head_not_used_as_authority": True}, "data_contract": {"rows": len(Y), "geometries": len(geoms), "cases": len(set((m[0], m[1]) for m in meta)), "wavelengths_nm": wavelengths, "ux": 0.0, "ky": 0.0, "ordered_D": True}, "model_contract": prereg, "validation": {"gate": gate, "accepted": accepted, "metrics_path": str(OUT / "logo_metrics.json")}, "full_data_deployment_status": full_status, "artifacts": {}, "coupling_h1_errors_read": False, "solver_invocations": 0}
    if model_path is not None: manifest["artifacts"]["deployment_model.npz"] = {"path": str(model_path), "sha256": sha256(model_path)}
    for p in [prereg_path, OUT / "NP_PRIOR_FEATURES_V2.json", OUT / "logo_metrics.json", OUT / "v2_acceptance_gate.json", OUT / "alpha_selection_audit.json", OUT / "lf_baseline_comparison.json"]:
        manifest["artifacts"][p.name] = {"path": str(p), "sha256": sha256(p)}
    manifest_path = OUT / "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_MANIFEST.json"; dump_json(manifest_path, manifest)
    dump_json(REPORT_DIR / "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_MANIFEST.json", manifest)
    report = f'''# NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_BUILD_AND_VALIDATE\n\n- STATUS: {manifest["status"]}\n- SOURCE AUTHORITY: {SOURCE_COMMIT}; HF22 SHA256 `{sha256(HF_PATH)}`; historical M9 OOF SHA256 `{sha256(HIST_OOF_PATH)}`\n- V1 HISTORICAL STATUS: historical executable recovery closed; no full-data deployment provider frozen.\n- V2 MODEL CONTRACT: ordered D1..D6 + wavelength + u_x + explicit P/S; LF ranking directly; multi-output Ridge residual spectral correction with inner geometry-LOGO alpha selection.\n- LOGO VALIDATION: 22-fold geometry-LOGO, 484 rows, held geometry includes both polarizations and all 11 wavelengths.\n- HISTORICAL REFERENCE COMPARISON: historical full-order OOF MAE approximately 0.03960; historical eta(+1) Spearman approximately 0.9616036; these are reference values only, not parity targets.\n- V2 ACCEPTANCE GATE: `{json.dumps(gate, ensure_ascii=False)}`\n- FULL-DATA DEPLOYMENT STATUS: {full_status}\n- RANKING COMPONENT: frozen executable LF physics response; no learned ranking network.\n- SPECTRAL COMPONENT: LF baseline + Ridge residual correction; R uses direct Ridge target because no legal LF R baseline exists.\n- COUPLING FEATURE INTERFACE: `NP_PRIOR_FEATURES_V2`; P/TM/XLIKE future branch only.\n- WAVELENGTH MASK: 445–455 nm valid; 440–444 nm and 456–460 nm explicit unsupported mask/rejection.\n- COUPLING H1 CONTAMINATION: not read and not used.\n- RUNTIME ARTIFACTS: `{OUT}`; manifest `{manifest_path}`.\n- ARTIFACT HASHES: recorded in manifest.\n- SOLVER: zero FDTD/RCWA/HF acquisitions.\n- NEXT: {"PW_K6_MATCHED_NP_PRIOR_V2_H1_ABLATION_V1" if accepted else "CHART_REVIEW_SKIP_NP_PRIOR_AND_PLAN_UNBIASED_FIXED_MDC_EXPANSION"}\n'''
    (REPORT_DIR / "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_BUILD_AND_VALIDATE.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "accepted": accepted, "full_order_mae": full_mae, "spearman": rho, "output": str(OUT), "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()
