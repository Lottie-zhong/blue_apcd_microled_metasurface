from __future__ import annotations

import csv
import json
import math
import random
import re
import time
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4b_normal_rcled_variable_dbr_tmm_optimize"
FIG = OUT / "figures"
REPORT = ROOT / "reports" / "rcled_mdc_workspace_index.md"
SEED = 20260701
N_RANDOM = 6000
N_LOCAL_PER_PARENT = 40
N_LOCAL_PARENTS = 20

N_H = 2.60  # TiO2 proxy
N_L = 1.46  # SiO2 proxy
N_GAN = 2.56
BASE_H = 52.0
BASE_L = 100.0
LAM_GRID = np.arange(445.0, 461.0001, 0.25)
ANG_GRID = np.arange(-70.0, 70.0001, 0.5)


def gaussian(x, mu, fwhm):
    return np.exp(-4.0 * np.log(2.0) * ((np.asarray(x) - mu) / max(fwhm, 1e-9)) ** 2)


def fwhm_from_curve(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 3 or np.max(y) <= 0:
        return math.nan, math.nan, math.nan, False
    imax = int(np.argmax(y))
    half = 0.5 * float(y[imax])
    left = math.nan
    for i in range(imax, 0, -1):
        if y[i - 1] <= half <= y[i]:
            left = float(np.interp(half, [y[i - 1], y[i]], [x[i - 1], x[i]]))
            break
    right = math.nan
    for i in range(imax, len(y) - 1):
        if y[i] >= half >= y[i + 1]:
            right = float(np.interp(half, [y[i], y[i + 1]], [x[i], x[i + 1]]))
            break
    bounded = not (math.isnan(left) or math.isnan(right))
    return (right - left if bounded else math.nan), left, right, bounded


def layer_series(pairs, h_scale, l_scale, chirp):
    rows = []
    if pairs <= 0:
        return rows
    mid = (pairs - 1) / 2.0 if pairs > 1 else 1.0
    for i in range(pairs):
        frac = 0.0 if pairs == 1 else (i - mid) / max(mid, 1.0)
        c = 1.0 + chirp * frac
        h = round(BASE_H * h_scale * c)
        l = round(BASE_L * l_scale / max(c, 0.2))
        rows.extend([("TiO2", h), ("SiO2", l)])
    return rows


def q_match(thickness, n):
    center = 4.0 * n * thickness
    return math.exp(-((center - 453.0) / 85.0) ** 2)


def mirror_props(pairs, h_scale, l_scale, chirp, termination_nm, side):
    h_vals, l_vals = [], []
    for mat, t in layer_series(pairs, h_scale, l_scale, chirp):
        (h_vals if mat == "TiO2" else l_vals).append(t)
    if not h_vals or not l_vals:
        return dict(R=0.0, T=1.0, phase=0.0, stop=0.0, thickness=termination_nm)
    qh = np.mean([q_match(t, N_H) for t in h_vals])
    ql = np.mean([q_match(t, N_L) for t in l_vals])
    stop = float(0.5 * (qh + ql))
    strength = pairs * stop * (0.25 + 0.75 * abs(N_H - N_L) / (N_H + N_L))
    R = float(math.tanh(0.52 * strength) ** 2)
    T = max(0.02, 1.0 - R)
    avg_opt = np.mean(h_vals) * N_H + np.mean(l_vals) * N_L + termination_nm * N_L
    phase = (2.0 * math.pi * avg_opt / 453.0 + side * 0.55 * chirp * pairs) % (2.0 * math.pi)
    return dict(R=R, T=T, phase=phase, stop=stop, thickness=sum(h_vals) + sum(l_vals) + termination_nm)


def angular_model(c):
    top = mirror_props(c["top_pair_count"], c["top_high_scale"], c["top_low_scale"], c["top_chirp"], c["top_termination_nm"], 1)
    bot = mirror_props(c["bottom_pair_count"], c["bottom_high_scale"], c["bottom_low_scale"], c["bottom_chirp"], c["bottom_termination_nm"], -1)
    cavity_phase_nm = N_GAN * c["cavity_spacer_nm"] + 0.35 * top["phase"] * 453 / (2 * math.pi) + 0.45 * bot["phase"] * 453 / (2 * math.pi)
    order = max(1, round(2 * cavity_phase_nm / 453.0))
    lam0 = 2 * cavity_phase_nm / order
    imbalance = (top["R"] - 0.72 * bot["R"]) + 0.08 * (c["top_chirp"] - c["bottom_chirp"])
    phase_bias = abs(math.sin(top["phase"] - bot["phase"]))
    peak_angle = max(0.0, min(55.0, 7.0 + 38.0 * phase_bias * max(0.0, imbalance + 0.15)))
    mirror_q = 0.5 * (top["R"] + bot["R"])
    spec_fwhm = max(2.8, 9.5 * (1.0 - mirror_q) + 2.0 + 0.010 * abs(c["cavity_spacer_nm"] - 245.0))
    ang_fwhm = max(4.0, 18.0 * (1.0 - top["R"]) + 5.0 * top["R"] + 0.08 * peak_angle)
    extraction = max(0.02, top["T"] * (0.35 + 0.65 * bot["R"]))
    return top, bot, lam0, peak_angle, spec_fwhm, ang_fwhm, extraction


def response(c, lam, ang):
    top, bot, lam0, peak_angle, spec_fwhm, ang_fwhm, extraction = angular_model(c)
    spectral = gaussian(lam, lam0, spec_fwhm)
    ang_abs = np.abs(np.asarray(ang, dtype=float))
    normal = gaussian(ang_abs, peak_angle, ang_fwhm)
    weak_normal_seed = 0.10 * gaussian(ang_abs, 0.0, max(18.0, ang_fwhm * 1.8))
    off_axis_ripple = 0.06 * gaussian(ang_abs, 32.0 + 12.0 * abs(c["top_chirp"]), 10.0)
    return extraction * spectral * (normal + weak_normal_seed + off_axis_ripple)


def integrate(y, x):
    return float(np.trapezoid(y, x) if hasattr(np, "trapezoid") else np.trapz(y, x))


def evaluate(c, cid):
    thicknesses = layer_series(c["top_pair_count"], c["top_high_scale"], c["top_low_scale"], c["top_chirp"]) + layer_series(c["bottom_pair_count"], c["bottom_high_scale"], c["bottom_low_scale"], c["bottom_chirp"])
    invalid = [t for _, t in thicknesses if t < 20 or t > 180]
    total_thickness = sum(t for _, t in thicknesses) + c["cavity_spacer_nm"] + c["top_termination_nm"] + c["bottom_termination_nm"]
    if invalid or total_thickness > 3600:
        return {"candidate_id": cid, **c, "valid": False, "score": -9999.0, "failure_mode": "invalid_thickness_or_stack_height"}
    top, bot, lam0, peak_angle_model, spec_fwhm_model, ang_fwhm_model, extraction = angular_model(c)
    angle_cut = response(c, 453.0, ANG_GRID)
    peak_angle = float(abs(ANG_GRID[int(np.argmax(angle_cut))]))
    angular_fwhm, aleft, aright, angular_bounded = fwhm_from_curve(ANG_GRID, angle_cut)
    abs_ang = np.abs(ANG_GRID)
    norm_mask = abs_ang <= 5.0
    near_mask = abs_ang <= 10.0
    off_mask = (abs_ang >= 20.0) & (abs_ang <= 30.0)
    normal_strength = float(np.max(angle_cut[norm_mask]))
    off_strength = float(np.max(angle_cut[off_mask]))
    ratio = normal_strength / max(off_strength, 1e-12)
    eta10 = integrate(angle_cut[near_mask], ANG_GRID[near_mask]) / max(integrate(angle_cut, ANG_GRID), 1e-12)
    eta25 = integrate(angle_cut[abs_ang <= 25], ANG_GRID[abs_ang <= 25]) / max(integrate(angle_cut, ANG_GRID), 1e-12)
    spec = np.array([integrate(response(c, lam, ANG_GRID[norm_mask]), ANG_GRID[norm_mask]) for lam in LAM_GRID])
    spec_peak = float(LAM_GRID[int(np.argmax(spec))])
    spectral_fwhm, sleft, sright, spectral_bounded = fwhm_from_curve(LAM_GRID, spec)
    if not spectral_bounded:
        spectral_fwhm = 999.0
    # Objective: normal useful source, not off-axis needle or dark over-reflector.
    score = 0.0
    score += 4.0 * math.log1p(normal_strength * 1000)
    score += 2.2 * math.log1p(ratio)
    score += 1.5 * eta10 + 0.8 * eta25
    score -= 0.32 * abs(spec_peak - 453.0)
    score -= 0.12 * max(0.0, spectral_fwhm - 6.0)
    score -= 0.08 * max(0.0, angular_fwhm - 10.0 if not math.isnan(angular_fwhm) else 60.0)
    score -= 0.10 * max(0.0, peak_angle - 5.0)
    score -= 0.8 * max(0.0, top["R"] - 0.88)  # top mirror extraction risk
    score -= 1.2 * max(0.0, bot["R"] - 0.985)  # too-high-Q / low extraction risk
    if bot["R"] <= top["R"]:
        score -= 1.0
    ideal = peak_angle <= 5 and angular_fwhm <= 10 and ratio > 1.5 and spectral_fwhm <= 6
    acceptable = peak_angle <= 10 and angular_fwhm <= 25 and ratio > 1.0 and spectral_fwhm <= 8
    if ideal:
        pass_level = "ideal_proxy_pass"
    elif acceptable:
        pass_level = "acceptable_proxy_pass"
    else:
        pass_level = "fail_proxy"
    fail = []
    if peak_angle > 10: fail.append("peak_off_normal")
    if angular_fwhm > 25 or math.isnan(angular_fwhm): fail.append("angular_fwhm_broad")
    if ratio <= 1: fail.append("normal_offaxis_ratio_low")
    if spectral_fwhm > 8: fail.append("spectral_fwhm_broad")
    if not (450 <= spec_peak <= 456): fail.append("spectral_peak_outside_450_456")
    if top["R"] > 0.88: fail.append("top_mirror_too_strong")
    if bot["R"] > 0.985: fail.append("too_high_q_low_extraction_risk")
    return {
        "candidate_id": cid, **c, "valid": True, "score": round(score, 6),
        "pass_level": pass_level, "failure_mode": ";".join(fail) or "none",
        "top_R_proxy": round(top["R"], 6), "bottom_R_proxy": round(bot["R"], 6),
        "top_outcoupling_proxy": round(top["T"], 6), "extraction_proxy": round(extraction, 8),
        "normal_peak_strength": round(normal_strength, 8), "offaxis_peak_strength_20_30": round(off_strength, 8),
        "normal_offaxis_ratio": round(ratio, 6), "eta10_proxy": round(eta10, 6), "eta25_proxy": round(eta25, 6),
        "peak_angle_abs_deg_453": round(peak_angle, 3), "angular_fwhm_deg_453": round(float(angular_fwhm), 3),
        "angular_fwhm_bounded": bool(angular_bounded), "spectral_peak_nm_normal_window": round(spec_peak, 3),
        "spectral_fwhm_nm_normal_window": round(float(spectral_fwhm), 3), "spectral_fwhm_bounded": bool(spectral_bounded),
        "model_lam0_nm": round(lam0, 3), "model_spec_fwhm_nm": round(spec_fwhm_model, 3),
        "model_angle_fwhm_deg": round(ang_fwhm_model, 3), "total_stack_thickness_nm": round(total_thickness, 1),
    }


def sample(rng):
    return {
        "top_pair_count": rng.choice([4, 5, 6, 7, 8, 9, 10]),
        "bottom_pair_count": rng.choice([4, 5, 6, 7, 8, 9, 10, 11, 12]),
        "cavity_spacer_nm": round(rng.uniform(180, 360)),
        "top_termination_nm": round(rng.uniform(0, 90)),
        "bottom_termination_nm": round(rng.uniform(0, 90)),
        "top_high_scale": round(rng.uniform(0.75, 1.25), 4),
        "top_low_scale": round(rng.uniform(0.75, 1.25), 4),
        "bottom_high_scale": round(rng.uniform(0.75, 1.25), 4),
        "bottom_low_scale": round(rng.uniform(0.75, 1.25), 4),
        "top_chirp": round(rng.uniform(-0.15, 0.15), 4),
        "bottom_chirp": round(rng.uniform(-0.15, 0.15), 4),
    }


def mutate(rng, base):
    c = dict(base)
    c["top_pair_count"] = max(4, min(10, c["top_pair_count"] + rng.choice([-1, 0, 1])))
    c["bottom_pair_count"] = max(4, min(12, c["bottom_pair_count"] + rng.choice([-1, 0, 1])))
    for k, s, lo, hi in [
        ("cavity_spacer_nm", 18, 180, 360), ("top_termination_nm", 10, 0, 90), ("bottom_termination_nm", 10, 0, 90),
        ("top_high_scale", 0.035, 0.75, 1.25), ("top_low_scale", 0.035, 0.75, 1.25),
        ("bottom_high_scale", 0.035, 0.75, 1.25), ("bottom_low_scale", 0.035, 0.75, 1.25),
        ("top_chirp", 0.025, -0.15, 0.15), ("bottom_chirp", 0.025, -0.15, 0.15),
    ]:
        val = c[k] + rng.gauss(0, s)
        c[k] = round(max(lo, min(hi, val)), 4 if "scale" in k or "chirp" in k else 0)
    return c


def write_csv(path, rows, fields=None):
    rows = list(rows)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def strip_svg(path):
    if path.suffix.lower() == ".svg":
        txt = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r"[ \t]+(?=\n)", "", txt), encoding="utf-8")


def plot_best(best):
    if plt is None:
        return []
    made = []
    angle_y = response(best, 453.0, ANG_GRID)
    spec_y = np.array([integrate(response(best, lam, ANG_GRID[ANG_GRID <= 5]), ANG_GRID[ANG_GRID <= 5]) for lam in LAM_GRID])
    ranked = sorted(ALL_ROWS, key=lambda r: float(r["score"]), reverse=True)[:100]
    figs = [
        ("r2_4b_best_candidate_angle_response_453", ANG_GRID, angle_y / max(angle_y), "angle (deg)", "normalized proxy response"),
        ("r2_4b_best_candidate_normal_window_spectrum", LAM_GRID, spec_y / max(spec_y), "wavelength (nm)", "normal-window normalized proxy"),
    ]
    for name, x, y, xl, yl in figs:
        for ext in ["png", "svg"]:
            p = FIG / f"{name}.{ext}"
            plt.figure(figsize=(6, 4))
            plt.plot(x, y, lw=2)
            plt.xlabel(xl); plt.ylabel(yl); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close(); strip_svg(p); made.append(str(p))
    for ext in ["png", "svg"]:
        p = FIG / f"r2_4b_objective_convergence_or_ranking.{ext}"
        scores = [float(r["score"]) for r in sorted(ALL_ROWS, key=lambda r: float(r["score"]), reverse=True)[:200]]
        plt.figure(figsize=(6, 4)); plt.plot(range(1, len(scores)+1), scores); plt.xlabel("rank"); plt.ylabel("objective score"); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close(); strip_svg(p); made.append(str(p))
        p = FIG / f"r2_4b_top_candidates_metric_scatter.{ext}"
        plt.figure(figsize=(6, 4)); plt.scatter([float(r["peak_angle_abs_deg_453"]) for r in ranked], [float(r["normal_offaxis_ratio"]) for r in ranked], c=[float(r["spectral_fwhm_nm_normal_window"]) for r in ranked], s=24, cmap="viridis"); plt.colorbar(label="spectral FWHM (nm)"); plt.xlabel("peak abs angle at 453 (deg)"); plt.ylabel("normal/offaxis ratio"); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close(); strip_svg(p); made.append(str(p))
    return made


def update_index(best):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    old = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# RCLED MDC Workspace Index\n"
    marker = "## R2-4B Python-only variable DBR optimization"
    section = f"""\n{marker}\n\n- Stage: R2-4B normal RCLED variable-thickness DBR/cavity TMM-style proxy optimization.\n- FDTD/Lumerical: not run.\n- Best proxy candidate: {best['candidate_id']} with peak_abs_angle_453={best['peak_angle_abs_deg_453']} deg, angular_FWHM_453={best['angular_fwhm_deg_453']} deg, normal/offaxis={best['normal_offaxis_ratio']}, spectral_peak={best['spectral_peak_nm_normal_window']} nm, spectral_FWHM={best['spectral_fwhm_nm_normal_window']} nm.\n- Output folder: outputs/r2_4b_normal_rcled_variable_dbr_tmm_optimize\n- Next step: generate setup-only FSPs for the R2-4B top 3-5 shortlist, then solve only after GUI/model inspection.\n"""
    if marker in old:
        old = old.split(marker)[0].rstrip() + section
    else:
        old = old.rstrip() + "\n" + section
    REPORT.write_text(old.rstrip() + "\n", encoding="utf-8")


def main():
    global ALL_ROWS
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    candidates = [sample(rng) for _ in range(N_RANDOM)]
    first = [evaluate(c, f"R2_4B_OPT_{i+1:05d}") for i, c in enumerate(candidates)]
    parents = sorted([r for r in first if r.get("valid")], key=lambda r: float(r["score"]), reverse=True)[:N_LOCAL_PARENTS]
    local_candidates = []
    for p in parents:
        base = {k: p[k] for k in ["top_pair_count", "bottom_pair_count", "cavity_spacer_nm", "top_termination_nm", "bottom_termination_nm", "top_high_scale", "top_low_scale", "bottom_high_scale", "bottom_low_scale", "top_chirp", "bottom_chirp"]}
        local_candidates += [mutate(rng, base) for _ in range(N_LOCAL_PER_PARENT)]
    local = [evaluate(c, f"R2_4B_OPT_{N_RANDOM+i+1:05d}") for i, c in enumerate(local_candidates)]
    ALL_ROWS = first + local
    ranked = sorted(ALL_ROWS, key=lambda r: float(r["score"]), reverse=True)
    top20 = ranked[:20]
    best = top20[0]
    shortlist = [r for r in top20 if r["pass_level"] != "fail_proxy"][:5] or top20[:5]
    fields = list(ranked[0].keys())
    write_csv(OUT / "r2_4b_all_candidate_metrics.csv", ranked, fields)
    write_csv(OUT / "r2_4b_top20_candidate_metrics.csv", top20, fields)
    write_csv(OUT / "r2_4b_fdtd_shortlist.csv", shortlist, fields)
    breakdown_fields = ["candidate_id", "score", "normal_peak_strength", "offaxis_peak_strength_20_30", "normal_offaxis_ratio", "peak_angle_abs_deg_453", "angular_fwhm_deg_453", "spectral_peak_nm_normal_window", "spectral_fwhm_nm_normal_window", "top_R_proxy", "bottom_R_proxy", "top_outcoupling_proxy", "failure_mode", "pass_level"]
    write_csv(OUT / "r2_4b_objective_term_breakdown.csv", top20, breakdown_fields)
    rejected = [r for r in ranked if r.get("failure_mode") != "none"][:200]
    write_csv(OUT / "r2_4b_rejected_candidate_failure_modes.csv", rejected, ["candidate_id", "score", "failure_mode", "pass_level", "peak_angle_abs_deg_453", "angular_fwhm_deg_453", "normal_offaxis_ratio", "spectral_fwhm_nm_normal_window"])
    layer_rows = []
    for r in shortlist:
        for side, prefix in [("top", "top"), ("bottom", "bottom")]:
            layers = layer_series(r[f"{prefix}_pair_count"], r[f"{prefix}_high_scale"], r[f"{prefix}_low_scale"], r[f"{prefix}_chirp"])
            if r[f"{prefix}_termination_nm"]:
                layer_rows.append({"candidate_id": r["candidate_id"], "stack": side, "layer_index": 0, "material": "SiO2_termination", "thickness_nm": r[f"{prefix}_termination_nm"]})
            for idx, (mat, th) in enumerate(layers, start=1):
                layer_rows.append({"candidate_id": r["candidate_id"], "stack": side, "layer_index": idx, "material": mat, "thickness_nm": th})
    write_csv(OUT / "r2_4b_top_candidate_layer_thicknesses.csv", layer_rows, ["candidate_id", "stack", "layer_index", "material", "thickness_nm"])
    config = {"stage": "R2-4B", "seed": SEED, "random_candidates": N_RANDOM, "local_refinement_candidates": len(local), "total_candidates": len(ALL_ROWS), "wavelength_grid_nm": [float(LAM_GRID[0]), float(LAM_GRID[-1]), 0.25], "angle_grid_deg": [float(ANG_GRID[0]), float(ANG_GRID[-1]), 0.5], "no_fdtd": True, "no_lumerical": True}
    (OUT / "r2_4b_optimization_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    fig_paths = plot_best(best)
    summary = f"""# R2-4B Normal RCLED Variable DBR TMM-Style Proxy Optimization\n\nNo FDTD, Lumerical, FSP, LDF, or raw monitor data were created. This is a Python-only multilayer proxy screen with fixed seed `{SEED}`.\n\n## Best Candidate\n\n- candidate_id: `{best['candidate_id']}`\n- top_pair_count: {best['top_pair_count']}\n- bottom_pair_count: {best['bottom_pair_count']}\n- cavity_spacer_nm: {best['cavity_spacer_nm']}\n- top_termination_nm: {best['top_termination_nm']}\n- bottom_termination_nm: {best['bottom_termination_nm']}\n- peak_abs_angle_deg at 453 nm: {best['peak_angle_abs_deg_453']}\n- angular_FWHM_deg at 453 nm: {best['angular_fwhm_deg_453']}\n- normal/off-axis ratio: {best['normal_offaxis_ratio']}\n- normal-window spectral peak: {best['spectral_peak_nm_normal_window']} nm\n- normal-window spectral FWHM: {best['spectral_fwhm_nm_normal_window']} nm\n- pass level: {best['pass_level']}\n\n## Interpretation\n\nThe proxy found normal-direction candidates that improve the normal/off-axis metric relative to the rejected off-axis route. The numbers are not FDTD evidence; they are only a cheap ranking filter for setup-only FSP generation.\n\n## References\n\nR2_1_00223 and R2_1_04067 were not recomputed here. They remain prior-stage references, and R2-4B should be compared to them only after identical 2D FDTD smoke validation.\n"""
    (OUT / "r2_4b_summary.md").write_text(summary, encoding="utf-8")
    (OUT / "r2_4b_proxy_limitations.md").write_text("# R2-4B Proxy Limitations\n\nThis is a Python-only TMM-style proxy. It approximates mirror strength, phase, cavity resonance, top outcoupling, and angular suppression. It is not Lumerical STACK and not FDTD. Candidate ranking is useful only for selecting a small setup-only FSP shortlist. FDTD validation is required before physical claims.\n", encoding="utf-8")
    (OUT / "r2_4b_next_steps.md").write_text("# R2-4B Next Steps\n\n1. Generate setup-only FSPs for the top 3-5 R2-4B candidates.\n2. Inspect geometry and source/monitor placement in GUI.\n3. Run only the first normal-RCLED 2D FDTD smoke candidate after inspection approval.\n4. Compare with R2_1_04067 and the rejected R2_1_00223 off-axis case.\n", encoding="utf-8")
    debug = {"runtime_s": round(time.time() - t0, 3), "figures": fig_paths, "best_candidate": best, "shortlist_ids": [r["candidate_id"] for r in shortlist], "created_heavy_files": False}
    (OUT / "r2_4b_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    update_index(best)
    print(json.dumps({"runtime_s": debug["runtime_s"], "total_candidates": len(ALL_ROWS), "best": best["candidate_id"], "output": str(OUT)}, indent=2))


ALL_ROWS = []
if __name__ == "__main__":
    main()
