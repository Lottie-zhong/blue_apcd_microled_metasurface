from __future__ import annotations

import csv
import json
import math
import sys
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
sys.path.insert(0, str(ROOT / "scripts"))
import stage_r2_4d5_focused_cavity_termination_phase_optimization as d5

OUT = ROOT / "outputs" / "r2_4d5a_shortlist_te_tm_offaxis_risk_review"
FIG = OUT / "figures"
REPORT = ROOT / "reports" / "rcled_mdc_workspace_index.md"
D5OUT = ROOT / "outputs" / "r2_4d5_focused_cavity_termination_phase_optimization"
CANDIDATES = ["D5_BASE_13461", "D5_BASE_13481", "D5_BASE_13881", "D5_BASE_14322", "D5_BASE_08955"]
PRIMARY = "D5_BASE_13461"
ANGLE_FINE = np.arange(20.0, 60.0001, 0.25)
ANGLE_30_40 = np.arange(30.0, 40.0001, 0.25)
LAM_MAP = np.arange(450.0, 456.0001, 0.25)
ANG_MAP = np.arange(25.0, 50.0001, 0.5)


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


def get_metric_rows() -> dict[str, dict]:
    rows = {r["candidate_id"]: r for r in read_rows(D5OUT / "r2_4d5_all_trial_metrics.csv")}
    missing = [c for c in CANDIDATES if c not in rows]
    if missing:
        raise SystemExit(f"missing D5 candidate rows: {missing}")
    return rows


def stacks(row: dict, seed_layers):
    top = d5.scaled_stack(seed_layers["top"], f(row, "top_termination_nm"), f(row, "top_high_scale_multiplier", 1), f(row, "top_low_scale_multiplier", 1))
    bottom = d5.scaled_stack(seed_layers["bottom"], f(row, "bottom_termination_nm"), f(row, "bottom_high_scale_multiplier", 1), f(row, "bottom_low_scale_multiplier", 1))
    return top, bottom


def err_deg(top, bottom, cav, lam, ang, pol):
    return d5.rt(top, bottom, cav, lam, ang, pol)["err_deg"]


def width_below(values, threshold, step):
    return float(np.sum(np.asarray(values) < threshold) * step)


def risk_class(width10, width15):
    if width10 >= 2.0 or width15 >= 5.0:
        return "broad"
    if width10 <= 1.0 and width15 <= 2.0:
        return "narrow_localized"
    return "moderate_localized"


def update_report(decision: str) -> None:
    marker = "<!-- R2-4D5A_SHORTLIST_TE_TM_OFFAXIS_RISK_REVIEW -->"
    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# RCLED MDC Workspace Index\n"
    block = f"""\n{marker}\n\n- Stage: R2-4D5A shortlist TE/TM off-axis risk review.\n- No FDTD/Lumerical/FSP/LDF/raw monitor data.\n- Backup decision: {decision}.\n- Output folder: outputs/r2_4d5a_shortlist_te_tm_offaxis_risk_review\n"""
    REPORT.write_text((text[:text.index(marker)].rstrip() if marker in text else text.rstrip()) + "\n" + block, encoding="utf-8")


def plot_line(path: Path, xs, series: dict[str, list[float]], title: str, xlabel: str, ylabel: str):
    if plt is None:
        return
    plt.figure(figsize=(7, 4.3))
    for label, vals in series.items():
        plt.plot(xs, vals, label=label)
    plt.grid(True, alpha=0.25); plt.legend(fontsize=8); plt.title(title); plt.xlabel(xlabel); plt.ylabel(ylabel); plt.tight_layout()
    for ext in ["png", "svg"]:
        plt.savefig(path.with_suffix(f".{ext}"), dpi=180)
    plt.close()


def plot_heat(path: Path, xs, ys, arr, title: str):
    if plt is None:
        return
    plt.figure(figsize=(7, 4.7))
    plt.imshow(np.asarray(arr, float), origin="lower", aspect="auto", extent=[min(xs), max(xs), min(ys), max(ys)], cmap="viridis")
    plt.colorbar(label="TM phase error (deg)"); plt.title(title); plt.xlabel("angle (deg)"); plt.ylabel("wavelength (nm)"); plt.tight_layout()
    for ext in ["png", "svg"]:
        plt.savefig(path.with_suffix(f".{ext}"), dpi=180)
    plt.close()


def trim_svgs():
    for p in FIG.glob("*.svg"):
        p.write_text("\n".join(x.rstrip() for x in p.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    rows = get_metric_rows()
    seed_layers = d5.load_layers(d5.SEED_ID)
    if not seed_layers:
        raise SystemExit("cannot reconstruct R2-4D5 seed layer stack")

    manifest, fine_rows, map_rows, margin_rows = [], [], [], []
    scan_for_plot = {}
    map_primary = None
    for cid in CANDIDATES:
        row = rows[cid]
        top, bottom = stacks(row, seed_layers)
        cav = f(row, "cavity_spacer_nm")
        manifest.append({
            "candidate_id": cid,
            "cavity_spacer_nm": cav,
            "top_termination_nm": f(row, "top_termination_nm"),
            "bottom_termination_nm": f(row, "bottom_termination_nm"),
            "top_pair_count": row.get("top_pair_count", "10"),
            "bottom_pair_count": row.get("bottom_pair_count", "12"),
            "D5_score": f(row, "score"),
        })
        per_pol = {}
        for pol in ["TE", "TM"]:
            vals = [err_deg(top, bottom, cav, 453.0, float(a), pol) for a in ANGLE_FINE]
            vals_30 = [(float(a), v) for a, v in zip(ANGLE_FINE, vals) if 30.0 <= a <= 40.0]
            min_ang, min_err = min(vals_30, key=lambda x: x[1])
            w10 = width_below([v for _, v in vals_30], 10.0, 0.25)
            w15 = width_below([v for _, v in vals_30], 15.0, 0.25)
            w20 = width_below([v for _, v in vals_30], 20.0, 0.25)
            cls = risk_class(w10, w15)
            per_pol[pol] = {"min_30_40_angle": min_ang, "min_30_40_err": min_err, "width10": w10, "width15": w15, "width20": w20, "class": cls, "vals": vals}
            fine_rows.append({
                "candidate_id": cid, "polarization": pol,
                "min_phase_error_30_40_deg": min_err, "min_phase_error_30_40_angle_deg": min_ang,
                "width_phase_error_lt10_deg_in_30_40_deg": w10,
                "width_phase_error_lt15_deg_in_30_40_deg": w15,
                "width_phase_error_lt20_deg_in_30_40_deg": w20,
                "risk_interpretation": cls,
            })
        scan_for_plot[cid] = per_pol["TM"]["vals"]
        map_vals = []
        closest = (999.0, None, None)
        valley_453 = []
        for lam in LAM_MAP:
            row_vals = []
            for ang in ANG_MAP:
                e = err_deg(top, bottom, cav, float(lam), float(ang), "TM")
                row_vals.append(e)
                map_rows.append({"candidate_id": cid, "wavelength_nm": float(lam), "angle_deg": float(ang), "TM_phase_error_deg": e})
                if e < closest[0]:
                    closest = (e, float(lam), float(ang))
                if abs(lam - 453.0) < 1e-9 and 30.0 <= ang <= 40.0:
                    valley_453.append(e)
            map_vals.append(row_vals)
        if cid == PRIMARY:
            map_primary = map_vals
        for pol in ["TE", "TM"]:
            normal = err_deg(top, bottom, cav, 453.0, 0.0, pol)
            off20 = min(err_deg(top, bottom, cav, 453.0, float(a), pol) for a in ANGLE_FINE)
            off30 = min(err_deg(top, bottom, cav, 453.0, float(a), pol) for a in ANGLE_30_40)
            margin_rows.append({
                "candidate_id": cid, "polarization": pol,
                "normal_phase_error_453_deg": normal,
                "best_offaxis_phase_error_20_60_deg": off20,
                "best_offaxis_phase_error_30_40_deg": off30,
                "phase_margin_20_60_deg": off20 - normal,
                "phase_margin_30_40_deg": off30 - normal,
                "normal_TE_TM_mismatch_deg": abs(f(row, "TE_normal_phase_error_deg") - f(row, "TM_normal_phase_error_deg")),
                "closest_TM_map_error_deg": closest[0] if pol == "TM" else "",
                "closest_TM_map_wavelength_nm": closest[1] if pol == "TM" else "",
                "closest_TM_map_angle_deg": closest[2] if pol == "TM" else "",
                "TM_30_40_valley_at_453_min_deg": min(valley_453) if pol == "TM" else "",
                "TM_offaxis_resonance_crosses_453": bool(min(valley_453) < 10.0) if pol == "TM" else "",
            })

    # readiness and backup decision
    fine_by = {(r["candidate_id"], r["polarization"]): r for r in fine_rows}
    margin_by = {(r["candidate_id"], r["polarization"]): r for r in margin_rows}
    readiness = []
    for cid in CANDIDATES:
        r = rows[cid]
        tm = fine_by[(cid, "TM")]
        ready = (
            f(r, "TE_normal_phase_error_deg") <= 10 and f(r, "TM_normal_phase_error_deg") <= 10 and
            f(r, "worst_pol_phase_margin_deg") > 0 and tm["risk_interpretation"] != "broad" and
            f(r, "min_pol_top_outcoupling_proxy") > 1e-4 and f(r, "conservative_normal_offaxis_ratio") > 1
        )
        readiness.append({"candidate_id": cid, "setup_only_ready": ready, "TM_30_40_risk_interpretation": tm["risk_interpretation"], "TM_width_lt10_deg": tm["width_phase_error_lt10_deg_in_30_40_deg"], "TM_width_lt15_deg": tm["width_phase_error_lt15_deg_in_30_40_deg"], "min_top_outcoupling_proxy": f(r, "min_pol_top_outcoupling_proxy"), "reason": "ready_for_setup_only_review" if ready else "hold_for_phase_risk_or_outcoupling"})
    primary_ready = next(r for r in readiness if r["candidate_id"] == PRIMARY)
    backups = [r for r in readiness if r["candidate_id"] != PRIMARY and r["setup_only_ready"]]
    primary_tm_w15 = float(primary_ready["TM_width_lt15_deg"])
    better_backups = [b for b in backups if float(b["TM_width_lt15_deg"]) + 1.0 < primary_tm_w15]
    if primary_ready["setup_only_ready"] and not better_backups:
        decision = "A_only_D5_BASE_13461"
        decision_text = "Keep only D5_BASE_13461 for R2-4D6. Its TM 30-40 risk is classified as localized enough by the fine scan, and no backup improves the risk enough to justify extra setup files."
    elif primary_ready["setup_only_ready"] and better_backups:
        b = sorted(better_backups, key=lambda x: float(x["TM_width_lt15_deg"]))[0]
        decision = f"B_D5_BASE_13461_plus_{b['candidate_id']}"
        decision_text = f"Generate setup-only FSPs for D5_BASE_13461 plus backup {b['candidate_id']} because the backup has a narrower TM 30-40 risk width."
    else:
        ready = [r for r in readiness if r["setup_only_ready"]]
        decision = f"C_use_{ready[0]['candidate_id']}" if ready else "no_setup_ready_candidate"
        decision_text = "Do not use D5_BASE_13461 alone; choose the best ready backup if present, otherwise hold setup-only generation."

    write_csv(OUT / "r2_4d5a_candidate_manifest.csv", manifest, list(manifest[0]))
    write_csv(OUT / "r2_4d5a_fine_angle_phase_scan.csv", fine_rows, list(fine_rows[0]))
    write_csv(OUT / "r2_4d5a_wavelength_angle_tm_risk_map.csv", map_rows, list(map_rows[0]))
    write_csv(OUT / "r2_4d5a_normal_vs_offaxis_margin.csv", margin_rows, list(margin_rows[0]))

    (OUT / "r2_4d5a_backup_candidate_decision.md").write_text(f"# R2-4D5A Backup Candidate Decision\n\nDecision: `{decision}`\n\n{decision_text}\n", encoding="utf-8")
    ready_lines = [f"| {r['candidate_id']} | {r['setup_only_ready']} | {r['TM_30_40_risk_interpretation']} | {r['TM_width_lt10_deg']} | {r['TM_width_lt15_deg']} | {r['reason']} |" for r in readiness]
    (OUT / "r2_4d5a_setup_only_readiness.md").write_text("# R2-4D5A Setup-Only Readiness\n\nThis is not FDTD approval. It only decides whether setup-only FSP generation is reasonable.\n\n| candidate | setup-only ready | TM risk | TM width <10 deg | TM width <15 deg | reason |\n|---|---:|---|---:|---:|---|\n" + "\n".join(ready_lines) + "\n", encoding="utf-8")
    (OUT / "r2_4d5a_stop_decisions.md").write_text("# R2-4D5A Stop Decisions\n\n- Do not run FDTD in R2-4D5A.\n- Do not generate FSP in R2-4D5A.\n- Do not run z_outofplane or broadband spectral validation yet.\n- Do not call D5_BASE_13461 physically validated until x-line x-dipole FDTD is done.\n", encoding="utf-8")

    primary_tm = fine_by[(PRIMARY, "TM")]
    top_summary = "\n".join(f"| {r['candidate_id']} | {r['setup_only_ready']} | {r['TM_30_40_risk_interpretation']} | {float(r['TM_width_lt10_deg']):.2f} | {float(r['TM_width_lt15_deg']):.2f} |" for r in readiness)
    (OUT / "r2_4d5a_summary.md").write_text(f"""# R2-4D5A Shortlist TE/TM Off-Axis Risk Review

No FDTD, Lumerical, lumapi, setup-only FSP, LDF, MAT/H5, or raw monitor data were created.

## Reviewed Candidates

{', '.join(CANDIDATES)}

## Primary TM 30-40 Risk

D5_BASE_13461 TM 30-40 minimum phase error is {float(primary_tm['min_phase_error_30_40_deg']):.3f} deg at {float(primary_tm['min_phase_error_30_40_angle_deg']):.2f} deg. Widths inside 30-40 deg: <10 deg = {float(primary_tm['width_phase_error_lt10_deg_in_30_40_deg']):.2f} deg, <15 deg = {float(primary_tm['width_phase_error_lt15_deg_in_30_40_deg']):.2f} deg, <20 deg = {float(primary_tm['width_phase_error_lt20_deg_in_30_40_deg']):.2f} deg. Interpretation: `{primary_tm['risk_interpretation']}`.

## Setup-Only Readiness

| candidate | ready | TM risk | width <10 | width <15 |
|---|---:|---|---:|---:|
{top_summary}

## Decision

`{decision}`

{decision_text}

This remains a TMM phase risk review. Physical validation still requires x-line x-dipole FDTD after setup-only geometry inspection.
""", encoding="utf-8")

    debug = {"runtime_s": round(time.time() - t0, 3), "reviewed_candidates": CANDIDATES, "decision": decision, "primary_tm_risk": primary_tm, "created_heavy_files": False}
    (OUT / "r2_4d5a_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")

    plot_line(FIG / "r2_4d5a_tm_30_40_phase_risk_comparison", ANGLE_FINE, {cid: scan_for_plot[cid] for cid in CANDIDATES}, "TM phase error at 453 nm", "angle (deg)", "phase error (deg)")
    if map_primary is not None:
        plot_heat(FIG / "r2_4d5a_wavelength_angle_tm_risk_map_primary", ANG_MAP, LAM_MAP, map_primary, "D5_BASE_13461 TM wavelength-angle risk")
    plot_line(FIG / "r2_4d5a_normal_vs_offaxis_margin_comparison", list(range(len(CANDIDATES))), {"20-60 margin TM": [float(margin_by[(c, "TM")]["phase_margin_20_60_deg"]) for c in CANDIDATES], "30-40 margin TM": [float(margin_by[(c, "TM")]["phase_margin_30_40_deg"]) for c in CANDIDATES]}, "TM normal vs off-axis margin", "candidate index", "phase margin (deg)")
    if plt is not None:
        plt.figure(figsize=(6.6, 4.4))
        plt.scatter([float(r["TM_width_lt15_deg"]) for r in readiness], [f(rows[r["candidate_id"]], "worst_pol_phase_margin_deg") for r in readiness], c=[1 if r["setup_only_ready"] else 0 for r in readiness], cmap="coolwarm", s=60)
        for idx, r in enumerate(readiness):
            plt.text(float(r["TM_width_lt15_deg"]), f(rows[r["candidate_id"]], "worst_pol_phase_margin_deg"), r["candidate_id"].replace("D5_BASE_", ""), fontsize=7)
        plt.xlabel("TM 30-40 width <15 deg"); plt.ylabel("worst-pol phase margin deg"); plt.title("Candidate readiness scatter"); plt.grid(True, alpha=0.25); plt.tight_layout()
        for ext in ["png", "svg"]:
            plt.savefig((FIG / "r2_4d5a_candidate_readiness_scatter").with_suffix(f".{ext}"), dpi=180)
        plt.close()
    trim_svgs()
    update_report(decision)
    print(json.dumps(debug, indent=2))


if __name__ == "__main__":
    main()
