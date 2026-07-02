from __future__ import annotations

import csv
import json
import math
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4d5_focused_cavity_termination_phase_optimization"
FIG = OUT / "figures"
REPORT = ROOT / "reports" / "rcled_mdc_workspace_index.md"
B4 = ROOT / "outputs" / "r2_4b_normal_rcled_variable_dbr_tmm_optimize"
D2 = ROOT / "outputs" / "r2_4d2_corrected_risk_aware_tmm_optimize"
N_H, N_L, N_GAN, N_AIR = 2.60, 1.46, 2.56, 1.0
SEED_ID = "R2_4B_OPT_06176"
DIAG_IDS = ["R2_4B_OPT_06361", "R2_4D2_OPT_13003"]
LAM_SCAN = np.arange(445.0, 461.0001, 0.5)
CAVITY_GRID = range(150, 231, 1)
TOP_TERM_GRID = range(0, 97, 5)
BOTTOM_TERM_GRID = range(13, 114, 5)
OFF_ANGLES = np.arange(20.0, 60.0001, 2.0)
RISK_ANGLES = np.arange(30.0, 40.0001, 1.0)
POLS = ["TE", "TM"]
SCALE_PROFILES = [
    ("base", 1.0, 1.0, 1.0, 1.0),
    ("top_minus2", 0.98, 0.98, 1.0, 1.0),
    ("top_plus2", 1.02, 1.02, 1.0, 1.0),
    ("bottom_minus2", 1.0, 1.0, 0.98, 0.98),
    ("bottom_plus2", 1.0, 1.0, 1.02, 1.02),
    ("all_minus2", 0.98, 0.98, 0.98, 0.98),
    ("all_plus2", 1.02, 1.02, 1.02, 1.02),
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, data: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(data)


def f(row: dict, key: str, default=0.0) -> float:
    try:
        v = row.get(key, default)
        return float(v if v not in (None, "") else default)
    except Exception:
        return float(default)


def load_metric_row(cid: str) -> dict | None:
    for d, name in [(B4, "r2_4b_top20_candidate_metrics.csv"), (B4, "r2_4b_all_candidate_metrics.csv"), (D2, "r2_4d2_top20_candidate_metrics.csv")]:
        p = d / name
        if not p.exists():
            continue
        for r in read_rows(p):
            if r.get("candidate_id") == cid:
                return r
    return None


def load_layers(cid: str) -> dict[str, list[tuple[str, float]]] | None:
    for d, name in [(B4, "r2_4b_top_candidate_layer_thicknesses.csv"), (D2, "r2_4d2_top_candidate_layer_thicknesses.csv")]:
        p = d / name
        if not p.exists():
            continue
        stacks: dict[str, list[tuple[str, float]]] = {"top": [], "bottom": []}
        for r in read_rows(p):
            if r.get("candidate_id") == cid and r.get("stack") in stacks:
                mat = r["material"]
                if "termination" not in mat:
                    stacks[r["stack"]].append((mat, f(r, "thickness_nm")))
        if stacks["top"] and stacks["bottom"]:
            return stacks
    return None


def nmat(mat: str) -> float:
    if "TiO2" in mat:
        return N_H
    if "SiO2" in mat:
        return N_L
    return N_AIR


def scaled_stack(base: list[tuple[str, float]], term_nm: float, high_scale: float, low_scale: float) -> list[tuple[str, float]]:
    out = []
    if term_nm > 0:
        out.append(("SiO2_termination", float(term_nm)))
    for mat, t in base:
        scale = high_scale if "TiO2" in mat else low_scale
        tt = round(float(t) * scale, 3)
        out.append((mat, tt))
    return out


def stack_ok(layers: list[tuple[str, float]]) -> bool:
    return all(20.0 <= t <= 180.0 for mat, t in layers if "termination" not in mat)


def cos_layer(n0: float, n: float, theta_deg: float) -> complex:
    s = n0 * math.sin(math.radians(theta_deg)) / n
    return complex(np.sqrt(1.0 - complex(s * s)))


@lru_cache(maxsize=None)
def reflection(layers: tuple[tuple[str, float], ...], lam: float, theta: float, pol: str) -> complex:
    n0, ns = N_GAN, N_AIR
    M = np.eye(2, dtype=complex)
    for mat, thick in layers:
        n = nmat(mat)
        c = cos_layer(n0, n, theta)
        delta = 2.0 * math.pi * n * c * thick / lam
        q = n * c if pol == "TE" else c / n
        m = np.array([[np.cos(delta), 1j * np.sin(delta) / q], [1j * q * np.sin(delta), np.cos(delta)]], dtype=complex)
        M = M @ m
    c0, cs = cos_layer(n0, n0, theta), cos_layer(n0, ns, theta)
    q0 = n0 * c0 if pol == "TE" else c0 / n0
    qs = ns * cs if pol == "TE" else cs / ns
    B = M[0, 0] + M[0, 1] * qs
    C = M[1, 0] + M[1, 1] * qs
    return (q0 * B - C) / (q0 * B + C)


def phase_error_rad(x: float) -> float:
    return abs(math.atan2(math.sin(x), math.cos(x)))


def rt(top: list[tuple[str, float]], bottom: list[tuple[str, float]], cavity_nm: float, lam: float, theta: float, pol: str) -> dict:
    rtop = reflection(tuple(top), lam, theta, pol)
    rbot = reflection(tuple(bottom), lam, theta, pol)
    kz = 2.0 * math.pi * N_GAN / lam * math.cos(math.radians(theta))
    phase = 2.0 * kz * cavity_nm + float(np.angle(rtop)) + float(np.angle(rbot))
    err = phase_error_rad(phase)
    return {"err_rad": err, "err_deg": math.degrees(err), "R_top": float(abs(rtop) ** 2), "R_bottom": float(abs(rbot) ** 2), "phi_top": float(np.angle(rtop)), "phi_bottom": float(np.angle(rbot))}


def score_candidate(row: dict) -> float:
    if not row["combined_accept"]:
        return -999.0 + row["worst_pol_phase_margin_deg"] * 0.01
    return (
        4.0 * row["conservative_normal_offaxis_ratio"]
        + 0.25 * row["worst_pol_phase_margin_deg"]
        + 0.03 * row["min_pol_top_outcoupling_proxy"] * 100.0
        - 0.35 * row["worst_pol_normal_phase_error_deg"]
        - 0.15 * row["max_pol_offaxis_30_40_risk_deg"]
        - 0.10 * abs(row["avg_normal_resonance_nm"] - 453.0)
    )


def eval_design(design_id: str, top_base, bottom_base, cavity: float, top_term: float, bottom_term: float, scale_label: str, ths: float, tls: float, bhs: float, bls: float) -> dict:
    top = scaled_stack(top_base, top_term, ths, tls)
    bottom = scaled_stack(bottom_base, bottom_term, bhs, bls)
    invalid = (not stack_ok(top)) or (not stack_ok(bottom)) or (sum(t for _, t in top + bottom) + cavity > 4200)
    per_pol = {}
    for pol in POLS:
        n0 = rt(top, bottom, cavity, 453.0, 0.0, pol)
        off = [rt(top, bottom, cavity, 453.0, float(a), pol)["err_rad"] for a in OFF_ANGLES]
        risk = [rt(top, bottom, cavity, 453.0, float(a), pol)["err_rad"] for a in RISK_ANGLES]
        lam_err = [rt(top, bottom, cavity, float(lam), 0.0, pol)["err_rad"] for lam in LAM_SCAN]
        risk_lam = [min(rt(top, bottom, cavity, float(lam), float(a), pol)["err_rad"] for a in RISK_ANGLES) for lam in LAM_SCAN]
        normal_resp = math.exp(-(n0["err_rad"] / math.radians(8.0)) ** 2) * max(0.02, 1.0 - n0["R_top"])
        off_resp = float(np.mean(np.exp(-(np.asarray(off) / math.radians(8.0)) ** 2))) * max(0.02, 1.0 - n0["R_top"])
        risk_resp = float(np.mean(np.exp(-(np.asarray(risk) / math.radians(8.0)) ** 2))) * max(0.02, 1.0 - n0["R_top"])
        per_pol[pol] = {
            "normal_phase_error_deg": n0["err_deg"],
            "best_offaxis_error_deg": math.degrees(min(off)),
            "phase_margin_deg": math.degrees(min(off) - n0["err_rad"]),
            "risk_30_40_deg": math.degrees(min(risk)),
            "normal_resonance_nm": float(LAM_SCAN[int(np.argmin(lam_err))]),
            "nearest_30_40_resonance_nm": float(LAM_SCAN[int(np.argmin(risk_lam))]),
            "normal_window_response": normal_resp,
            "offaxis_20_60_response": off_resp,
            "risk_30_40_response": risk_resp,
            "normal_offaxis_ratio": normal_resp / max(off_resp, 1e-12),
            "top_outcoupling_proxy": max(0.0, 1.0 - n0["R_top"]),
            "R_top": n0["R_top"],
            "R_bottom": n0["R_bottom"],
        }
    worst_normal = max(per_pol[p]["normal_phase_error_deg"] for p in POLS)
    worst_margin = min(per_pol[p]["phase_margin_deg"] for p in POLS)
    max_risk = min(per_pol[p]["risk_30_40_deg"] for p in POLS)
    min_resp = min(per_pol[p]["normal_window_response"] for p in POLS)
    min_ratio = min(per_pol[p]["normal_offaxis_ratio"] for p in POLS)
    min_out = min(per_pol[p]["top_outcoupling_proxy"] for p in POLS)
    avg_lam = float(np.mean([per_pol[p]["normal_resonance_nm"] for p in POLS]))
    failures = []
    if invalid:
        failures.append("invalid_layer_or_stack_height")
    if worst_normal > 10:
        failures.append("normal_phase_error_gt10deg")
    if worst_margin <= 0:
        failures.append("phase_margin_not_positive")
    if max_risk <= worst_normal + 5:
        failures.append("30_40_phase_risk_too_close")
    if not (450 <= avg_lam <= 456):
        failures.append("normal_resonance_outside_450_456")
    if min_ratio <= 1:
        failures.append("normal_offaxis_ratio_le1")
    if min_out < 1e-4:
        failures.append("top_outcoupling_too_low")
    row = {
        "candidate_id": design_id,
        "scale_profile": scale_label,
        "top_pair_count": 10,
        "bottom_pair_count": 12,
        "cavity_spacer_nm": cavity,
        "top_termination_nm": top_term,
        "bottom_termination_nm": bottom_term,
        "top_high_scale_multiplier": ths,
        "top_low_scale_multiplier": tls,
        "bottom_high_scale_multiplier": bhs,
        "bottom_low_scale_multiplier": bls,
        "TE_normal_phase_error_deg": per_pol["TE"]["normal_phase_error_deg"],
        "TM_normal_phase_error_deg": per_pol["TM"]["normal_phase_error_deg"],
        "TE_phase_margin_deg": per_pol["TE"]["phase_margin_deg"],
        "TM_phase_margin_deg": per_pol["TM"]["phase_margin_deg"],
        "TE_30_40_risk_deg": per_pol["TE"]["risk_30_40_deg"],
        "TM_30_40_risk_deg": per_pol["TM"]["risk_30_40_deg"],
        "TE_normal_resonance_nm": per_pol["TE"]["normal_resonance_nm"],
        "TM_normal_resonance_nm": per_pol["TM"]["normal_resonance_nm"],
        "TE_normal_offaxis_ratio": per_pol["TE"]["normal_offaxis_ratio"],
        "TM_normal_offaxis_ratio": per_pol["TM"]["normal_offaxis_ratio"],
        "TE_top_outcoupling_proxy": per_pol["TE"]["top_outcoupling_proxy"],
        "TM_top_outcoupling_proxy": per_pol["TM"]["top_outcoupling_proxy"],
        "worst_pol_normal_phase_error_deg": worst_normal,
        "worst_pol_phase_margin_deg": worst_margin,
        "max_pol_offaxis_30_40_risk_deg": max_risk,
        "min_pol_normal_window_response": min_resp,
        "conservative_normal_offaxis_ratio": min_ratio,
        "min_pol_top_outcoupling_proxy": min_out,
        "avg_normal_resonance_nm": avg_lam,
        "combined_accept": len(failures) == 0,
        "failure_mode": "none" if not failures else ";".join(failures),
    }
    row["score"] = score_candidate(row)
    return row


def rows_for_layers(shortlist: list[dict], top_base, bottom_base) -> list[dict]:
    out = []
    for r in shortlist:
        top = scaled_stack(top_base, f(r, "top_termination_nm"), f(r, "top_high_scale_multiplier", 1), f(r, "top_low_scale_multiplier", 1))
        bottom = scaled_stack(bottom_base, f(r, "bottom_termination_nm"), f(r, "bottom_high_scale_multiplier", 1), f(r, "bottom_low_scale_multiplier", 1))
        for stack, layers in [("top", top), ("bottom", bottom)]:
            for idx, (mat, th) in enumerate(layers):
                out.append({"candidate_id": r["candidate_id"], "stack": stack, "layer_index": idx, "material": mat, "thickness_nm": th})
    return out


def plot_scatter(path: Path, rows_: list[dict]):
    if plt is None or not rows_:
        return
    plt.figure(figsize=(6.5, 4.5))
    x = [float(r["worst_pol_normal_phase_error_deg"]) for r in rows_]
    y = [float(r["worst_pol_phase_margin_deg"]) for r in rows_]
    c = [float(r["conservative_normal_offaxis_ratio"]) for r in rows_]
    plt.scatter(x, y, c=c, s=34, cmap="viridis")
    plt.colorbar(label="conservative normal/offaxis")
    plt.axvline(10, color="r", ls="--", lw=1)
    plt.axhline(0, color="r", ls="--", lw=1)
    plt.xlabel("worst-pol normal phase error (deg)"); plt.ylabel("worst-pol phase margin (deg)")
    plt.tight_layout()
    for ext in ["png", "svg"]:
        plt.savefig(path.with_suffix(f".{ext}"), dpi=180)
    plt.close()


def plot_line(path: Path, xs, ys: dict[str, list[float]], title: str, xlabel: str, ylabel: str):
    if plt is None:
        return
    plt.figure(figsize=(7, 4.2))
    for k, v in ys.items():
        plt.plot(xs, v, label=k)
    plt.title(title); plt.xlabel(xlabel); plt.ylabel(ylabel); plt.grid(True, alpha=0.25); plt.legend(fontsize=8); plt.tight_layout()
    for ext in ["png", "svg"]:
        plt.savefig(path.with_suffix(f".{ext}"), dpi=180)
    plt.close()


def plot_grid(path: Path, rows_: list[dict]):
    if plt is None or not rows_:
        return
    piv = {(int(float(r["cavity_spacer_nm"])), int(float(r["top_termination_nm"])), int(float(r["bottom_termination_nm"]))): float(r["worst_pol_phase_margin_deg"]) for r in rows_ if r["scale_profile"] == "base"}
    # ponytail: show the best bottom-termination slice instead of a 3D plot; enough to inspect the map.
    best_b = max(sorted({k[2] for k in piv}), key=lambda b: max(v for k, v in piv.items() if k[2] == b))
    xs = sorted({k[0] for k in piv if k[2] == best_b})
    ys = sorted({k[1] for k in piv if k[2] == best_b})
    arr = [[piv.get((x, y, best_b), np.nan) for x in xs] for y in ys]
    plt.figure(figsize=(7, 4.8)); plt.imshow(arr, aspect="auto", origin="lower", extent=[min(xs), max(xs), min(ys), max(ys)], cmap="viridis")
    plt.colorbar(label="worst-pol phase margin (deg)"); plt.title(f"Phase margin map, bottom term {best_b} nm"); plt.xlabel("cavity spacer (nm)"); plt.ylabel("top termination (nm)"); plt.tight_layout()
    for ext in ["png", "svg"]:
        plt.savefig(path.with_suffix(f".{ext}"), dpi=180)
    plt.close()


def svg_trim():
    for p in FIG.glob("*.svg"):
        lines = [line.rstrip() for line in p.read_text(encoding="utf-8").splitlines()]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_report(best_id: str, robust: bool):
    marker = "<!-- R2-4D5_FOCUSED_CAVITY_TERMINATION_PHASE_OPTIMIZATION -->"
    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# RCLED MDC Workspace Index\n"
    block = f"""\n{marker}\n\n- Stage: R2-4D5 focused cavity/termination phase-guided optimization.\n- No FDTD/Lumerical/FSP/LDF/raw monitor data.\n- Best candidate: `{best_id}`.\n- Robust TE/TM shortlist exists: `{robust}`.\n- Output folder: outputs/r2_4d5_focused_cavity_termination_phase_optimization\n"""
    REPORT.write_text((text[:text.index(marker)].rstrip() if marker in text else text.rstrip()) + "\n" + block, encoding="utf-8")


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    seed_layers = load_layers(SEED_ID)
    if not seed_layers:
        raise SystemExit(f"cannot reconstruct seed layers: {SEED_ID}")
    reconstruct = [{"candidate_id": SEED_ID, "role": "primary_seed", "reconstructable": True}]
    for cid in DIAG_IDS:
        reconstruct.append({"candidate_id": cid, "role": "diagnostic_seed", "reconstructable": load_layers(cid) is not None})

    trials = []
    counter = 0
    for cav in CAVITY_GRID:
        for tt in TOP_TERM_GRID:
            for bt in BOTTOM_TERM_GRID:
                counter += 1
                trials.append(eval_design(f"D5_BASE_{counter:05d}", seed_layers["top"], seed_layers["bottom"], float(cav), float(tt), float(bt), "base", 1.0, 1.0, 1.0, 1.0))
    base_rank = sorted(trials, key=lambda r: r["score"], reverse=True)
    refine_bases = base_rank[:30]
    for base in refine_bases:
        for label, ths, tls, bhs, bls in SCALE_PROFILES[1:]:
            counter += 1
            trials.append(eval_design(f"D5_REFINE_{counter:05d}", seed_layers["top"], seed_layers["bottom"], f(base, "cavity_spacer_nm"), f(base, "top_termination_nm"), f(base, "bottom_termination_nm"), label, ths, tls, bhs, bls))

    ranked = sorted(trials, key=lambda r: r["score"], reverse=True)
    top20 = ranked[:20]
    accepts = [r for r in ranked if r["combined_accept"]]
    robust_exists = bool(accepts)
    shortlist = []
    if accepts:
        primary = accepts[0] | {"shortlist_role": "D5_PRIMARY"}
        robust = sorted(accepts, key=lambda r: (r["worst_pol_phase_margin_deg"], -r["max_pol_offaxis_30_40_risk_deg"]), reverse=True)[0] | {"shortlist_role": "D5_ROBUST"}
        te_candidates = sorted(ranked, key=lambda r: (r["TE_phase_margin_deg"] - r["TE_normal_phase_error_deg"], r["TE_normal_offaxis_ratio"]), reverse=True)
        te = te_candidates[0] | {"shortlist_role": "D5_TE_STRONG"}
        seen = set()
        for r in [primary, te, robust]:
            if r["candidate_id"] not in seen:
                shortlist.append(r); seen.add(r["candidate_id"])
        shortlist = shortlist[:3]

    fields = list(ranked[0].keys())
    write_csv(OUT / "r2_4d5_all_trial_metrics.csv", ranked, fields)
    write_csv(OUT / "r2_4d5_top20_phase_guided_candidates.csv", top20, fields)
    write_csv(OUT / "r2_4d5_phase_guided_shortlist.csv", shortlist, ["shortlist_role"] + fields if shortlist else ["shortlist_role"] + fields)
    write_csv(OUT / "r2_4d5_candidate_layer_thicknesses.csv", rows_for_layers(shortlist or top20[:3], seed_layers["top"], seed_layers["bottom"]), ["candidate_id", "stack", "layer_index", "material", "thickness_nm"])
    write_csv(OUT / "r2_4d5_te_tm_risk_summary.csv", [{k: r[k] for k in ["candidate_id", "score", "TE_normal_phase_error_deg", "TM_normal_phase_error_deg", "TE_phase_margin_deg", "TM_phase_margin_deg", "TE_30_40_risk_deg", "TM_30_40_risk_deg", "combined_accept", "failure_mode"]} for r in top20], ["candidate_id", "score", "TE_normal_phase_error_deg", "TM_normal_phase_error_deg", "TE_phase_margin_deg", "TM_phase_margin_deg", "TE_30_40_risk_deg", "TM_30_40_risk_deg", "combined_accept", "failure_mode"])
    write_csv(OUT / "r2_4d5_cavity_termination_grid_metrics.csv", [r for r in ranked if r["scale_profile"] == "base"], fields)
    write_csv(OUT / "r2_4d5_phase_margin_metrics.csv", [{"candidate_id": r["candidate_id"], "worst_pol_phase_margin_deg": r["worst_pol_phase_margin_deg"], "TE_phase_margin_deg": r["TE_phase_margin_deg"], "TM_phase_margin_deg": r["TM_phase_margin_deg"], "max_pol_offaxis_30_40_risk_deg": r["max_pol_offaxis_30_40_risk_deg"]} for r in top20], ["candidate_id", "worst_pol_phase_margin_deg", "TE_phase_margin_deg", "TM_phase_margin_deg", "max_pol_offaxis_30_40_risk_deg"])
    write_csv(OUT / "r2_4d5_outcoupling_proxy_metrics.csv", [{"candidate_id": r["candidate_id"], "TE_top_outcoupling_proxy": r["TE_top_outcoupling_proxy"], "TM_top_outcoupling_proxy": r["TM_top_outcoupling_proxy"], "min_pol_top_outcoupling_proxy": r["min_pol_top_outcoupling_proxy"], "conservative_normal_offaxis_ratio": r["conservative_normal_offaxis_ratio"]} for r in top20], ["candidate_id", "TE_top_outcoupling_proxy", "TM_top_outcoupling_proxy", "min_pol_top_outcoupling_proxy", "conservative_normal_offaxis_ratio"])
    rejected = [r for r in ranked if not r["combined_accept"]][:200]
    write_csv(OUT / "r2_4d5_rejected_candidate_failure_modes.csv", [{"candidate_id": r["candidate_id"], "score": r["score"], "failure_mode": r["failure_mode"], "worst_pol_normal_phase_error_deg": r["worst_pol_normal_phase_error_deg"], "worst_pol_phase_margin_deg": r["worst_pol_phase_margin_deg"], "conservative_normal_offaxis_ratio": r["conservative_normal_offaxis_ratio"]} for r in rejected], ["candidate_id", "score", "failure_mode", "worst_pol_normal_phase_error_deg", "worst_pol_phase_margin_deg", "conservative_normal_offaxis_ratio"])

    best = ranked[0]
    cfg = {"stage": "R2-4D5", "primary_seed": SEED_ID, "pair_counts_fixed": {"top": 10, "bottom": 12}, "cavity_spacer_grid_nm": [150, 230, 1], "top_termination_grid_nm": [0, 96, 5], "bottom_termination_grid_nm": [13, 113, 5], "scale_profiles": SCALE_PROFILES, "trial_count": len(ranked), "no_fdtd": True, "no_lumerical": True, "reconstructability": reconstruct}
    (OUT / "r2_4d5_optimization_config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    (OUT / "r2_4d5_proxy_limitations.md").write_text("# R2-4D5 Proxy Limitations\n\nThis package is a Python-only TMM phase/outcoupling proxy. It does not model dipole source coupling, finite aperture diffraction, 2D/3D FDTD fields, or APCD coupling. Setup-only FSP generation should wait for review of the TE/TM risk table and shortlist.\n", encoding="utf-8")
    (OUT / "r2_4d5_next_steps.md").write_text(("# R2-4D5 Next Steps\n\n" + ("1. Review the D5 shortlist.\n2. If approved, run R2-4D6 setup-only FSP generation for only the shortlist, no solve.\n3. GUI inspect.\n4. Then run R2-4D7 x-line x-dipole-only FDTD scout.\n" if robust_exists else "No robust combined TE/TM shortlist exists. Expand beyond fixed 10/12 pair count or revise mirror asymmetry/top-outcoupling before FSP generation.\n")), encoding="utf-8")

    top5 = top20[:5]
    md_rows = "\n".join(f"| {r['candidate_id']} | {r['score']:.3f} | {r['cavity_spacer_nm']} | {r['top_termination_nm']} | {r['bottom_termination_nm']} | {r['worst_pol_normal_phase_error_deg']:.3f} | {r['worst_pol_phase_margin_deg']:.3f} | {r['conservative_normal_offaxis_ratio']:.3g} | {r['combined_accept']} |" for r in top5)
    short_rows = "\n".join(f"| {r.get('shortlist_role','')} | {r['candidate_id']} | {r['cavity_spacer_nm']} | {r['top_termination_nm']} | {r['bottom_termination_nm']} | {r['TE_normal_phase_error_deg']:.3f} | {r['TM_normal_phase_error_deg']:.3f} | {r['TE_phase_margin_deg']:.3f} | {r['TM_phase_margin_deg']:.3f} | {r['TE_30_40_risk_deg']:.3f} | {r['TM_30_40_risk_deg']:.3f} | {r['avg_normal_resonance_nm']:.2f} | {r['conservative_normal_offaxis_ratio']:.3g} | {r['min_pol_top_outcoupling_proxy']:.3g} |" for r in shortlist) if shortlist else "| none | no robust combined TE/TM shortlist | | | | | | | | | | | | |"
    (OUT / "r2_4d5_summary.md").write_text(f"""# R2-4D5 Focused Cavity/Termination Phase-Guided Optimization

No FDTD, Lumerical, lumapi, setup-only FSP, LDF, MAT/H5, or raw monitor data were created.

## Scope

- Primary seed: `{SEED_ID}`
- Fixed pair counts: top=10, bottom=12
- Trials evaluated: {len(ranked)}
- Robust combined TE/TM shortlist exists: `{robust_exists}`
- Best candidate ID: `{best['candidate_id']}`

## Top 5 Phase-Guided Candidates

| candidate | score | cavity | top term | bottom term | worst normal err deg | worst margin deg | conservative N/O | accept |
|---|---:|---:|---:|---:|---:|---:|---:|---|
{md_rows}

## Final Shortlist

| role | candidate | cavity | top term | bottom term | TE normal err | TM normal err | TE margin | TM margin | TE 30-40 risk | TM 30-40 risk | avg normal resonance | N/O proxy | top outcoupling |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{short_rows}

## Interpretation

The shortlist is still a TMM phase/outcoupling proxy. It is ready for setup-only FSP generation only after review; FDTD should wait until the generated geometry is GUI-inspected.
""", encoding="utf-8")

    debug = {"runtime_s": round(time.time() - t0, 3), "trial_count": len(ranked), "best_candidate": best["candidate_id"], "robust_shortlist_exists": robust_exists, "shortlist_ids": [r["candidate_id"] for r in shortlist], "created_heavy_files": False}
    (OUT / "r2_4d5_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")

    plot_grid(FIG / "r2_4d5_cavity_termination_phase_margin_map", [r for r in ranked if r["scale_profile"] == "base"])
    plot_scatter(FIG / "r2_4d5_shortlist_metric_scatter", top20)
    plot_line(FIG / "r2_4d5_te_tm_phase_risk_comparison", list(range(len(top20))), {"TE normal": [r["TE_normal_phase_error_deg"] for r in top20], "TM normal": [r["TM_normal_phase_error_deg"] for r in top20], "TE 30-40": [r["TE_30_40_risk_deg"] for r in top20], "TM 30-40": [r["TM_30_40_risk_deg"] for r in top20]}, "TE/TM phase risk top20", "rank", "phase error (deg)")
    plot_line(FIG / "r2_4d5_normal_vs_offaxis_response_proxy", list(range(len(top20))), {"TE N/O": [r["TE_normal_offaxis_ratio"] for r in top20], "TM N/O": [r["TM_normal_offaxis_ratio"] for r in top20]}, "Normal/offaxis response proxy", "rank", "ratio")
    if shortlist:
        cand = shortlist[0]
        top = scaled_stack(seed_layers["top"], f(cand, "top_termination_nm"), f(cand, "top_high_scale_multiplier", 1), f(cand, "top_low_scale_multiplier", 1))
        bottom = scaled_stack(seed_layers["bottom"], f(cand, "bottom_termination_nm"), f(cand, "bottom_high_scale_multiplier", 1), f(cand, "bottom_low_scale_multiplier", 1))
        xs = list(range(0, 61, 2)); ys = [450, 453, 456]
        arr = [[rt(top, bottom, f(cand, "cavity_spacer_nm"), lam, a, "TE")["err_deg"] for a in xs] for lam in ys]
        if plt is not None:
            plt.figure(figsize=(7, 4.5)); plt.imshow(arr, aspect="auto", origin="lower", extent=[min(xs), max(xs), min(ys), max(ys)], cmap="viridis"); plt.colorbar(label="TE phase error deg"); plt.xlabel("internal angle deg"); plt.ylabel("wavelength nm"); plt.title(f"{cand['candidate_id']} TE phase error"); plt.tight_layout()
            for ext in ["png", "svg"]:
                plt.savefig((FIG / "r2_4d5_best_candidate_phase_error_map").with_suffix(f".{ext}"), dpi=180)
            plt.close()
    svg_trim()
    update_report(best["candidate_id"], robust_exists)
    print(json.dumps({"output": str(OUT), **debug}, indent=2))


if __name__ == "__main__":
    main()
