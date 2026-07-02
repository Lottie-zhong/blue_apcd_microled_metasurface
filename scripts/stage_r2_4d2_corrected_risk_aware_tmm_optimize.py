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
OUT = ROOT / "outputs" / "r2_4d2_corrected_risk_aware_tmm_optimize"
FIG = OUT / "figures"
REPORT = ROOT / "reports" / "rcled_mdc_workspace_index.md"
SEED = 20260702
N_RANDOM = 12000
N_LOCAL_PARENTS = 30
N_LOCAL_PER_PARENT = 45

N_H = 2.60
N_L = 1.46
N_GAN = 2.56
BASE_H = 52.0
BASE_L = 100.0
LAM_GRID = np.arange(445.0, 461.0001, 0.25)
ANG_GRID = np.arange(-70.0, 70.0001, 0.5)
FAIL_IDS = ["R2_4B_OPT_06361", "R2_4B_OPT_06176"]
OLD_CSV = ROOT / "outputs" / "r2_4b_normal_rcled_variable_dbr_tmm_optimize" / "r2_4b_all_candidate_metrics.csv"
D1_NEG = ROOT / "outputs" / "r2_4d1_xline_failure_diagnosis_proxy_correction" / "r2_4d1_negative_sample_table.csv"


def gaussian(x, mu, fwhm):
    return np.exp(-4.0 * np.log(2.0) * ((np.asarray(x) - mu) / max(float(fwhm), 1e-9)) ** 2)


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


def integrate(y, x):
    return float(np.trapezoid(y, x) if hasattr(np, "trapezoid") else np.trapz(y, x))


def layer_series(pairs, h_scale, l_scale, chirp):
    rows = []
    if int(pairs) <= 0:
        return rows
    mid = (pairs - 1) / 2.0 if pairs > 1 else 1.0
    for i in range(int(pairs)):
        frac = 0.0 if pairs == 1 else (i - mid) / max(mid, 1.0)
        c = 1.0 + chirp * frac
        h = round(BASE_H * h_scale * c)
        l = round(BASE_L * l_scale / max(c, 0.2))
        rows.extend([("TiO2", h), ("SiO2", l)])
    return rows


def q_match(thickness, n):
    center = 4.0 * n * thickness
    return math.exp(-((center - 453.0) / 80.0) ** 2)


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
    peak_angle = max(0.0, min(55.0, 6.0 + 40.0 * phase_bias * max(0.0, imbalance + 0.15)))
    mirror_q = 0.5 * (top["R"] + bot["R"])
    spec_fwhm = max(2.5, 9.2 * (1.0 - mirror_q) + 1.8 + 0.010 * abs(c["cavity_spacer_nm"] - 245.0))
    ang_fwhm = max(3.8, 18.0 * (1.0 - top["R"]) + 4.5 * top["R"] + 0.07 * peak_angle)
    extraction = max(0.02, top["T"] * (0.35 + 0.65 * bot["R"]))
    return top, bot, lam0, peak_angle, spec_fwhm, ang_fwhm, extraction


def response(c, lam, ang):
    top, bot, lam0, peak_angle, spec_fwhm, ang_fwhm, extraction = angular_model(c)
    spectral = gaussian(lam, lam0, spec_fwhm)
    ang_abs = np.abs(np.asarray(ang, dtype=float))
    normal = gaussian(ang_abs, peak_angle, ang_fwhm)
    weak_normal_seed = 0.08 * gaussian(ang_abs, 0.0, max(16.0, ang_fwhm * 1.6))
    off_center = 32.0 + 14.0 * abs(c["top_chirp"]) + 5.0 * max(0.0, top["R"] - bot["R"])
    off_axis_ripple = 0.08 * gaussian(ang_abs, off_center, 9.0) * (0.65 + 0.7 * top["R"])
    return extraction * spectral * (normal + weak_normal_seed + off_axis_ripple)


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
    c["top_pair_count"] = max(4, min(10, int(c["top_pair_count"]) + rng.choice([-1, 0, 1])))
    c["bottom_pair_count"] = max(4, min(12, int(c["bottom_pair_count"]) + rng.choice([-1, 0, 1])))
    for k, s, lo, hi in [
        ("cavity_spacer_nm", 16, 180, 360), ("top_termination_nm", 9, 0, 90), ("bottom_termination_nm", 9, 0, 90),
        ("top_high_scale", 0.032, 0.75, 1.25), ("top_low_scale", 0.032, 0.75, 1.25),
        ("bottom_high_scale", 0.032, 0.75, 1.25), ("bottom_low_scale", 0.032, 0.75, 1.25),
        ("top_chirp", 0.022, -0.15, 0.15), ("bottom_chirp", 0.022, -0.15, 0.15),
    ]:
        val = c[k] + rng.gauss(0, s)
        c[k] = round(max(lo, min(hi, val)), 4 if "scale" in k or "chirp" in k else 0)
    return c


def feature_distance(c, fail):
    terms = [
        ((c["top_pair_count"] - fail["top_pair_count"]) / 6.0) ** 2,
        ((c["bottom_pair_count"] - fail["bottom_pair_count"]) / 8.0) ** 2,
        ((c["cavity_spacer_nm"] - fail["cavity_spacer_nm"]) / 180.0) ** 2,
        ((c["top_termination_nm"] - fail["top_termination_nm"]) / 90.0) ** 2,
        ((c["bottom_termination_nm"] - fail["bottom_termination_nm"]) / 90.0) ** 2,
    ]
    for k in ["top_high_scale", "top_low_scale", "bottom_high_scale", "bottom_low_scale", "top_chirp", "bottom_chirp"]:
        terms.append(((c[k] - fail[k]) / (0.5 if "scale" in k else 0.3)) ** 2)
    return float(math.sqrt(sum(terms)))


def local_peak_metrics(x, y):
    peaks = []
    for i in range(1, len(y) - 1):
        if y[i] >= y[i - 1] and y[i] >= y[i + 1]:
            peaks.append((float(y[i]), float(x[i])))
    peaks = sorted(peaks, reverse=True)
    if not peaks:
        imax = int(np.argmax(y)); peaks = [(float(y[imax]), float(x[imax]))]
    first = peaks[0]
    second = next((p for p in peaks[1:] if abs(abs(p[1]) - abs(first[1])) > 5), (0.0, math.nan))
    return first[1], second[1], second[0] / max(first[0], 1e-12)


def read_old_failures():
    out = {}
    if not OLD_CSV.exists():
        return out
    with OLD_CSV.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("candidate_id") in FAIL_IDS:
                out[r["candidate_id"]] = {k: float(r[k]) if k not in ["candidate_id", "pass_level", "failure_mode"] and r[k] not in ["True", "False"] else r[k] for k in r}
    return out


def evaluate_base(c, cid, failures):
    thicknesses = layer_series(c["top_pair_count"], c["top_high_scale"], c["top_low_scale"], c["top_chirp"]) + layer_series(c["bottom_pair_count"], c["bottom_high_scale"], c["bottom_low_scale"], c["bottom_chirp"])
    invalid = [t for _, t in thicknesses if t < 20 or t > 180]
    total_thickness = sum(t for _, t in thicknesses) + c["cavity_spacer_nm"] + c["top_termination_nm"] + c["bottom_termination_nm"]
    if invalid or total_thickness > 4200:
        return {"candidate_id": cid, **c, "valid": False, "score": -9999.0, "failure_mode": "invalid_thickness_or_stack_height"}
    top, bot, lam0, peak_model, spec_fwhm_model, ang_fwhm_model, extraction = angular_model(c)
    cut = response(c, 453.0, ANG_GRID)
    total = integrate(cut, ANG_GRID)
    abs_ang = np.abs(ANG_GRID)
    masks = {
        "n5": abs_ang <= 5,
        "n10": abs_ang <= 10,
        "off20_60": (abs_ang >= 20) & (abs_ang <= 60),
        "off30_40": (abs_ang >= 30) & (abs_ang <= 40),
    }
    peak_angle = float(abs(ANG_GRID[int(np.argmax(cut))]))
    angular_fwhm, _, _, angular_bounded = fwhm_from_curve(ANG_GRID, cut)
    normal5 = integrate(cut[masks["n5"]], ANG_GRID[masks["n5"]])
    normal10 = integrate(cut[masks["n10"]], ANG_GRID[masks["n10"]])
    off20_60 = integrate(cut[masks["off20_60"]], ANG_GRID[masks["off20_60"]])
    off30_40 = integrate(cut[masks["off30_40"]], ANG_GRID[masks["off30_40"]])
    ratio = normal10 / max(off20_60, 1e-12)
    ratio30 = off30_40 / max(normal10, 1e-12)
    ratio20 = off20_60 / max(normal10, 1e-12)
    first_angle, second_angle, second_ratio = local_peak_metrics(ANG_GRID, cut)
    spec5 = np.array([integrate(response(c, lam, ANG_GRID[masks["n5"]]), ANG_GRID[masks["n5"]]) for lam in LAM_GRID])
    spec10 = np.array([integrate(response(c, lam, ANG_GRID[masks["n10"]]), ANG_GRID[masks["n10"]]) for lam in LAM_GRID])
    spec_peak = float(LAM_GRID[int(np.argmax(spec5))])
    spectral_fwhm, _, _, spectral_bounded = fwhm_from_curve(LAM_GRID, spec5)
    if not spectral_bounded:
        spectral_fwhm = 999.0
    d06361 = feature_distance(c, failures["R2_4B_OPT_06361"]) if "R2_4B_OPT_06361" in failures else 999.0
    d06176 = feature_distance(c, failures["R2_4B_OPT_06176"]) if "R2_4B_OPT_06176" in failures else 999.0
    min_dist = min(d06361, d06176)
    # Corrected objective: reward absolute normal power, punish absolute off-axis and failed-family similarity.
    score = 0.0
    score += 7.0 * math.log1p(normal5 * 1000)
    score += 4.0 * math.log1p(normal10 * 800)
    score += 2.5 * math.log1p(ratio)
    score -= 8.0 * math.log1p(off20_60 * 1000)
    score -= 10.0 * math.log1p(off30_40 * 1200)
    score -= 1.4 * max(0.0, peak_angle - 5.0)
    score -= 0.25 * max(0.0, (angular_fwhm if not math.isnan(angular_fwhm) else 60.0) - 10.0)
    score -= 0.40 * max(0.0, spectral_fwhm - 6.0)
    score -= 0.70 * max(0.0, abs(spec_peak - 453.0) - 1.5)
    score -= 2.4 * max(0.0, ratio30 - 0.18)
    score -= 1.2 * max(0.0, second_ratio - 0.45)
    score -= 1.0 * max(0.0, top["R"] - 0.86)
    score -= 0.5 * max(0.0, bot["R"] - 0.985)
    if bot["R"] <= top["R"]:
        score -= 2.0
    if min_dist < 0.24:
        score -= 2.0 * (0.24 - min_dist) / 0.24
    failure = []
    if peak_angle > 7: failure.append("peak_angle_gt7")
    if math.isnan(angular_fwhm) or angular_fwhm > 15: failure.append("angular_fwhm_gt15")
    if spectral_fwhm > 8: failure.append("spectral_fwhm_gt8")
    if not (450 <= spec_peak <= 456): failure.append("spectral_peak_outside_450_456")
    if ratio30 > 0.30: failure.append("30_40_resonance_risk")
    if second_ratio > 0.55: failure.append("multi_peak_risk")
    if min_dist < 0.18: failure.append("near_failed_family")
    return {
        "candidate_id": cid, **c, "valid": True, "score": round(score, 6),
        "corrected_proxy_peak_abs_angle_deg": round(peak_angle, 3),
        "corrected_proxy_angular_FWHM_deg": round(float(angular_fwhm), 3),
        "angular_fwhm_bounded": bool(angular_bounded),
        "normal_window_response_0_5": round(normal5, 10),
        "normal_window_response_0_10": round(normal10, 10),
        "offaxis_20_60_response": round(off20_60, 10),
        "offaxis_30_40_response": round(off30_40, 10),
        "corrected_normal_offaxis_ratio": round(ratio, 6),
        "offaxis_peak_30_40_to_normal_ratio": round(ratio30, 6),
        "offaxis_peak_20_60_to_normal_ratio": round(ratio20, 6),
        "strongest_peak_angle": round(first_angle, 3),
        "second_peak_angle": round(second_angle, 3) if not math.isnan(second_angle) else "",
        "second_to_first_peak_ratio": round(second_ratio, 6),
        "spectral_peak_nm_normal_window": round(spec_peak, 3),
        "spectral_fwhm_nm_normal_window": round(float(spectral_fwhm), 3),
        "spectral_fwhm_bounded": bool(spectral_bounded),
        "near_normal_spectrum_0_5_peak": round(float(np.max(spec5)), 10),
        "near_normal_spectrum_0_10_peak": round(float(np.max(spec10)), 10),
        "top_R_proxy": round(top["R"], 6), "bottom_R_proxy": round(bot["R"], 6),
        "top_outcoupling_proxy": round(top["T"], 6), "extraction_proxy": round(extraction, 8),
        "model_lam0_nm": round(lam0, 3), "model_spec_fwhm_nm": round(spec_fwhm_model, 3),
        "model_angle_fwhm_deg": round(ang_fwhm_model, 3), "total_stack_thickness_nm": round(total_thickness, 1),
        "distance_to_R2_4B_OPT_06361": round(d06361, 6),
        "distance_to_R2_4B_OPT_06176": round(d06176, 6),
        "failure_mode": ";".join(failure) or "none",
        "pass_level": "pending_population_threshold",
    }


def write_csv(path, rows, fields=None):
    rows = list(rows)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def percentile(rows, key, pct):
    vals = np.array([float(r[key]) for r in rows if r.get("valid") and r.get(key) not in ["", None]])
    return float(np.percentile(vals, pct))


def apply_thresholds(rows):
    valid = [r for r in rows if r.get("valid")]
    thresholds = {
        "normal_window_response_0_5_min": percentile(valid, "normal_window_response_0_5", 60),
        "normal_window_response_0_10_min": percentile(valid, "normal_window_response_0_10", 60),
        "offaxis_20_60_response_max": percentile(valid, "offaxis_20_60_response", 35),
        "offaxis_30_40_response_max": percentile(valid, "offaxis_30_40_response", 35),
        "corrected_normal_offaxis_ratio_min": percentile(valid, "corrected_normal_offaxis_ratio", 70),
        "offaxis_peak_30_40_to_normal_ratio_max": percentile(valid, "offaxis_peak_30_40_to_normal_ratio", 35),
        "second_to_first_peak_ratio_max": 0.55,
        "failed_family_distance_min": 0.18,
    }
    for r in rows:
        if not r.get("valid"):
            continue
        fail = [] if r["failure_mode"] == "none" else r["failure_mode"].split(";")
        checks = [
            (float(r["corrected_proxy_peak_abs_angle_deg"]) <= 7, "peak_angle_rule"),
            (float(r["corrected_proxy_angular_FWHM_deg"]) <= 15, "angular_fwhm_rule"),
            (float(r["normal_window_response_0_5"]) >= thresholds["normal_window_response_0_5_min"], "normal5_below_population_threshold"),
            (float(r["normal_window_response_0_10"]) >= thresholds["normal_window_response_0_10_min"], "normal10_below_population_threshold"),
            (float(r["offaxis_20_60_response"]) <= thresholds["offaxis_20_60_response_max"], "offaxis20_60_above_threshold"),
            (float(r["offaxis_30_40_response"]) <= thresholds["offaxis_30_40_response_max"], "offaxis30_40_above_threshold"),
            (float(r["corrected_normal_offaxis_ratio"]) >= thresholds["corrected_normal_offaxis_ratio_min"], "normal_offaxis_ratio_below_threshold"),
            (float(r["offaxis_peak_30_40_to_normal_ratio"]) <= thresholds["offaxis_peak_30_40_to_normal_ratio_max"], "30_40_to_normal_above_threshold"),
            (float(r["second_to_first_peak_ratio"]) <= thresholds["second_to_first_peak_ratio_max"], "multi_peak_above_threshold"),
            (float(r["spectral_fwhm_nm_normal_window"]) <= 8, "spectral_fwhm_rule"),
            (450 <= float(r["spectral_peak_nm_normal_window"]) <= 456, "spectral_peak_rule"),
            (min(float(r["distance_to_R2_4B_OPT_06361"]), float(r["distance_to_R2_4B_OPT_06176"])) >= thresholds["failed_family_distance_min"], "failed_family_distance_rule"),
        ]
        fail.extend(name for ok, name in checks if not ok)
        r["failure_mode"] = ";".join(dict.fromkeys(fail)) or "none"
        r["pass_level"] = "corrected_proxy_pass" if r["failure_mode"] == "none" else "fail_corrected_proxy"
    return thresholds


def diverse_shortlist(rows, max_n=3):
    passed = [r for r in rows if r.get("pass_level") == "corrected_proxy_pass"]
    picked = []
    families = set()
    for r in sorted(passed, key=lambda x: float(x["score"]), reverse=True):
        fam = (int(r["top_pair_count"]), int(r["bottom_pair_count"]), round(float(r["cavity_spacer_nm"]) / 30) * 30)
        if fam in families and len(picked) < min(max_n, len(passed)):
            continue
        picked.append(r); families.add(fam)
        if len(picked) >= max_n:
            break
    return picked


def strip_svg(path):
    if path.suffix.lower() == ".svg":
        path.write_text(re.sub(r"[ \t]+(?=\n)", "", path.read_text(encoding="utf-8")), encoding="utf-8")


def plot_outputs(best, top20, old_vs):
    if plt is None or not best:
        return []
    made = []
    FIG.mkdir(parents=True, exist_ok=True)
    angle_y = response(best, 453.0, ANG_GRID)
    n5 = np.abs(ANG_GRID) <= 5
    spec_y = np.array([integrate(response(best, lam, ANG_GRID[n5]), ANG_GRID[n5]) for lam in LAM_GRID])
    plots = [
        ("r2_4d2_best_candidate_angle_response_453", ANG_GRID, angle_y / max(angle_y), "angle (deg)", "normalized proxy response"),
        ("r2_4d2_best_candidate_normal_window_spectrum", LAM_GRID, spec_y / max(spec_y), "wavelength (nm)", "normal-window response"),
        ("r2_4d2_corrected_objective_ranking", np.arange(1, min(200, len(top20)) + 1), [float(r["score"]) for r in top20[:200]], "rank", "corrected score"),
    ]
    for name, x, y, xl, yl in plots:
        for ext in ["png", "svg"]:
            p = FIG / f"{name}.{ext}"
            plt.figure(figsize=(6, 4)); plt.plot(x, y, lw=2); plt.xlabel(xl); plt.ylabel(yl); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close(); strip_svg(p); made.append(str(p))
    for ext in ["png", "svg"]:
        p = FIG / f"r2_4d2_offaxis_risk_scatter.{ext}"
        plt.figure(figsize=(6, 4))
        plt.scatter([float(r["offaxis_20_60_response"]) for r in top20], [float(r["normal_window_response_0_10"]) for r in top20], c=[float(r["corrected_proxy_peak_abs_angle_deg"]) for r in top20], s=28, cmap="viridis")
        plt.colorbar(label="peak abs angle (deg)"); plt.xlabel("offaxis 20-60 response"); plt.ylabel("normal 0-10 response"); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close(); strip_svg(p); made.append(str(p))
        p = FIG / f"r2_4d2_old_vs_corrected_proxy_top_candidates.{ext}"
        labels = [r["candidate_id"] for r in old_vs]
        xs = np.arange(len(labels))
        plt.figure(figsize=(7, 4))
        plt.bar(xs - 0.18, [float(r.get("old_proxy_normal_offaxis_ratio", 0) or 0) for r in old_vs], width=0.36, label="old proxy ratio")
        plt.bar(xs + 0.18, [float(r.get("corrected_normal_offaxis_ratio", 0) or 0) for r in old_vs], width=0.36, label="corrected ratio")
        plt.xticks(xs, labels, rotation=25, ha="right"); plt.ylabel("normal/offaxis ratio"); plt.legend(); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close(); strip_svg(p); made.append(str(p))
    return made


def md_table(rows, fields):
    if not rows:
        return "No rows."
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(f, "")) for f in fields) + " |")
    return "\n".join(out)


def read_old_rows(ids):
    rows = {}
    if OLD_CSV.exists():
        with OLD_CSV.open(newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("candidate_id") in ids:
                    rows[r["candidate_id"]] = r
    return rows


def update_index(best, pass_count):
    marker = "## R2-4D2 corrected risk-aware TMM optimization"
    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# RCLED MDC Workspace Index\n"
    block = f"""
{marker}
- Output: `outputs/r2_4d2_corrected_risk_aware_tmm_optimize`
- FDTD/Lumerical/lumapi: not run.
- Corrected proxy passes: {pass_count}.
- Best candidate: `{best.get('candidate_id', 'none')}`.
- Next step: R2-4D3 setup-only FSP generation for the corrected shortlist if approved.
"""
    if marker not in text:
        REPORT.write_text(text.rstrip() + "\n" + block, encoding="utf-8")


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    failures = read_old_failures()
    rng = random.Random(SEED)
    candidates = [sample(rng) for _ in range(N_RANDOM)]
    first = [evaluate_base(c, f"R2_4D2_OPT_{i+1:05d}", failures) for i, c in enumerate(candidates)]
    parents = sorted([r for r in first if r.get("valid")], key=lambda r: float(r["score"]), reverse=True)[:N_LOCAL_PARENTS]
    local_candidates = []
    for p in parents:
        base = {k: p[k] for k in ["top_pair_count", "bottom_pair_count", "cavity_spacer_nm", "top_termination_nm", "bottom_termination_nm", "top_high_scale", "top_low_scale", "bottom_high_scale", "bottom_low_scale", "top_chirp", "bottom_chirp"]}
        local_candidates += [mutate(rng, base) for _ in range(N_LOCAL_PER_PARENT)]
    local = [evaluate_base(c, f"R2_4D2_OPT_{N_RANDOM+i+1:05d}", failures) for i, c in enumerate(local_candidates)]
    all_rows = first + local
    thresholds = apply_thresholds(all_rows)
    ranked = sorted(all_rows, key=lambda r: float(r["score"]), reverse=True)
    top20 = ranked[:20]
    passed = [r for r in ranked if r.get("pass_level") == "corrected_proxy_pass"]
    shortlist = diverse_shortlist(ranked, 3)
    best = ranked[0]
    fields = list(best.keys())
    write_csv(OUT / "r2_4d2_all_candidate_metrics.csv", ranked, fields)
    write_csv(OUT / "r2_4d2_top20_candidate_metrics.csv", top20, fields)
    write_csv(OUT / "r2_4d2_fdtd_shortlist.csv", shortlist, fields)
    write_csv(OUT / "r2_4d2_objective_term_breakdown.csv", top20, ["candidate_id", "score", "normal_window_response_0_5", "normal_window_response_0_10", "offaxis_20_60_response", "offaxis_30_40_response", "corrected_normal_offaxis_ratio", "offaxis_peak_30_40_to_normal_ratio", "second_to_first_peak_ratio", "corrected_proxy_peak_abs_angle_deg", "corrected_proxy_angular_FWHM_deg", "spectral_peak_nm_normal_window", "spectral_fwhm_nm_normal_window", "failure_mode", "pass_level"])
    write_csv(OUT / "r2_4d2_corrected_proxy_thresholds.csv", [{"threshold": k, "value": v, "selection_basis": "population percentile or fixed conservative rule"} for k, v in thresholds.items()], ["threshold", "value", "selection_basis"])
    dist_rows = [{"candidate_id": r["candidate_id"], "distance_to_R2_4B_OPT_06361": r["distance_to_R2_4B_OPT_06361"], "distance_to_R2_4B_OPT_06176": r["distance_to_R2_4B_OPT_06176"], "failure_mode": r["failure_mode"], "pass_level": r["pass_level"]} for r in top20]
    write_csv(OUT / "r2_4d2_negative_sample_distance.csv", dist_rows)
    write_csv(OUT / "r2_4d2_rejected_candidate_failure_modes.csv", [r for r in ranked if r.get("pass_level") != "corrected_proxy_pass"][:300], ["candidate_id", "score", "failure_mode", "pass_level", "corrected_proxy_peak_abs_angle_deg", "corrected_proxy_angular_FWHM_deg", "corrected_normal_offaxis_ratio", "offaxis_20_60_response", "offaxis_30_40_response", "spectral_fwhm_nm_normal_window"])
    layer_rows = []
    for r in shortlist or top20[:3]:
        for side, prefix in [("top", "top"), ("bottom", "bottom")]:
            if float(r[f"{prefix}_termination_nm"]):
                layer_rows.append({"candidate_id": r["candidate_id"], "stack": side, "layer_index": 0, "material": "SiO2_termination", "thickness_nm": round(float(r[f"{prefix}_termination_nm"]))})
            for idx, (mat, th) in enumerate(layer_series(int(r[f"{prefix}_pair_count"]), float(r[f"{prefix}_high_scale"]), float(r[f"{prefix}_low_scale"]), float(r[f"{prefix}_chirp"])), start=1):
                layer_rows.append({"candidate_id": r["candidate_id"], "stack": side, "layer_index": idx, "material": mat, "thickness_nm": th})
    write_csv(OUT / "r2_4d2_top_candidate_layer_thicknesses.csv", layer_rows, ["candidate_id", "stack", "layer_index", "material", "thickness_nm"])
    old_rows = read_old_rows(FAIL_IDS)
    old_vs = []
    for cid, old in old_rows.items():
        old_vs.append({"candidate_id": cid, "old_proxy_peak_abs_angle_deg": old.get("peak_angle_abs_deg_453", ""), "old_proxy_normal_offaxis_ratio": old.get("normal_offaxis_ratio", ""), "corrected_normal_offaxis_ratio": "", "status": "negative_sample_old_proxy_failed_fdtd"})
    for r in top20[:5]:
        old_vs.append({"candidate_id": r["candidate_id"], "old_proxy_peak_abs_angle_deg": "", "old_proxy_normal_offaxis_ratio": "", "corrected_normal_offaxis_ratio": r["corrected_normal_offaxis_ratio"], "status": "r2_4d2_corrected_proxy_candidate"})
    write_csv(OUT / "r2_4d2_old_vs_corrected_proxy_comparison.csv", old_vs)
    config = {"stage": "R2-4D2", "seed": SEED, "random_candidates": N_RANDOM, "local_refinement_candidates": len(local), "total_candidates": len(all_rows), "thresholds": thresholds, "no_fdtd": True, "no_lumerical": True, "used_negative_samples": FAIL_IDS}
    (OUT / "r2_4d2_optimization_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    figs = plot_outputs(best, ranked[:200], old_vs)
    top_fields = ["candidate_id", "score", "top_pair_count", "bottom_pair_count", "cavity_spacer_nm", "corrected_proxy_peak_abs_angle_deg", "corrected_proxy_angular_FWHM_deg", "normal_window_response_0_10", "offaxis_20_60_response", "offaxis_30_40_response", "corrected_normal_offaxis_ratio", "spectral_peak_nm_normal_window", "spectral_fwhm_nm_normal_window", "pass_level"]
    summary = f"""# R2-4D2 Corrected Risk-aware TMM/STACK Proxy Optimization

No FDTD, Lumerical, lumapi, FSP, LDF, MAT/H5, raw monitor data, or full adjoint run was performed.

- Candidates evaluated: {len(all_rows)}
- Runtime: {time.time() - t0:.3f} s
- Conservative corrected-proxy passes: {len(passed)}
- Best candidate: `{best['candidate_id']}`
- FDTD-ready shortlist count: {len(shortlist)}

## Top 5 Corrected-proxy Candidates

{md_table(top20[:5], top_fields)}

## FDTD-ready Shortlist

{md_table(shortlist, top_fields)}

## Interpretation

This is still only a Python proxy. R2-4D1 showed the old proxy failed badly against x-line x-dipole FDTD, so these candidates must be validated first by setup-only FSP generation, GUI inspection, and then x-line x-dipole-only FDTD scout. Do not treat these metrics as physical RCLED evidence.
"""
    (OUT / "r2_4d2_summary.md").write_text(summary, encoding="utf-8")
    (OUT / "r2_4d2_proxy_limitations.md").write_text("# R2-4D2 Proxy Limitations\n\nThis is a corrected Python-only TMM/STACK-style proxy informed by negative FDTD samples. It still cannot model finite-aperture dipole emission, source-position coupling, or full Lumerical FDTD behavior. Shortlisted candidates require R2-4D3 setup-only FSP generation and R2-4D4 x-line x-dipole FDTD scout before any source-module claim.\n", encoding="utf-8")
    next_step = "R2-4D3 setup-only FSP generation for only the corrected shortlist, then GUI inspection, then R2-4D4 x-line x-dipole-only FDTD scout." if shortlist else "No candidate passed. Revise the variable space or run a focused cavity-phase proxy sweep before FDTD."
    (OUT / "r2_4d2_next_steps.md").write_text("# R2-4D2 Next Steps\n\n" + next_step + "\n", encoding="utf-8")
    debug = {"runtime_s": round(time.time() - t0, 3), "total_candidates": len(all_rows), "pass_count": len(passed), "best_candidate": best, "shortlist_ids": [r["candidate_id"] for r in shortlist], "figures": figs, "created_heavy_files": False}
    (OUT / "r2_4d2_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    update_index(best, len(passed))
    print(json.dumps({"runtime_s": debug["runtime_s"], "total_candidates": len(all_rows), "pass_count": len(passed), "best": best["candidate_id"], "shortlist": debug["shortlist_ids"], "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
