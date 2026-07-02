from __future__ import annotations

import csv
import json
import math
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
OUT = ROOT / "outputs" / "r2_4d4_focused_cavity_phase_sweep"
FIG = OUT / "figures"
REPORT = ROOT / "reports" / "rcled_mdc_workspace_index.md"
N_H, N_L, N_GAN, N_AIR = 2.60, 1.46, 2.56, 1.0
BASE_H, BASE_L = 52.0, 100.0
LAM_GRID = np.arange(445.0, 461.0001, 0.25)
ANG_GRID = np.arange(0.0, 70.0001, 1.0)
SPACERS = np.arange(160.0, 430.0001, 2.0)
FOCUS_LAMS = [450.0, 453.0, 456.0]
FOCUS_ANGLES = [0.0, 5.0, 7.0, 10.0, 20.0, 30.0, 36.0, 40.0, 60.0]
POLS = ["TE", "TM"]
REPRESENTATIVES = [
    "R2_4B_OPT_06361", "R2_4B_OPT_06176",
    "R2_4D2_OPT_13003", "R2_4D2_OPT_13010", "R2_4D2_OPT_13013", "R2_4D2_OPT_12232", "R2_4D2_OPT_03742",
]
D2_DIR = ROOT / "outputs" / "r2_4d2_corrected_risk_aware_tmm_optimize"
B4_DIR = ROOT / "outputs" / "r2_4b_normal_rcled_variable_dbr_tmm_optimize"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, data: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(data)


def f(row: dict, key: str, default=0.0) -> float:
    try:
        v = row.get(key, default)
        return float(v if v not in (None, "") else default)
    except Exception:
        return float(default)


def i(row: dict, key: str, default=0) -> int:
    return int(round(f(row, key, default)))


def layer_series(pairs: int, h_scale: float, l_scale: float, chirp: float) -> list[tuple[str, float]]:
    out = []
    if pairs <= 0:
        return out
    mid = (pairs - 1) / 2.0 if pairs > 1 else 1.0
    for idx in range(pairs):
        frac = 0.0 if pairs == 1 else (idx - mid) / max(mid, 1.0)
        c = 1.0 + chirp * frac
        out += [("TiO2", float(round(BASE_H * h_scale * c))), ("SiO2", float(round(BASE_L * l_scale / max(c, 0.2))))]
    return out


def generated(row: dict, side: str) -> list[tuple[str, float]]:
    out = []
    term = f(row, f"{side}_termination_nm")
    if term:
        out.append(("SiO2_termination", term))
    out.extend(layer_series(i(row, f"{side}_pair_count"), f(row, f"{side}_high_scale", 1), f(row, f"{side}_low_scale", 1), f(row, f"{side}_chirp", 0)))
    return out


def manifests(path: Path) -> dict[tuple[str, str], list[tuple[str, float]]]:
    out = {}
    if not path.exists():
        return out
    for r in rows(path):
        out.setdefault((r["candidate_id"], r["stack"]), []).append((r["material"], f(r, "thickness_nm")))
    return out


def load_candidates():
    out = []
    for stage, d, metrics_name, layer_name in [
        ("R2-4B", B4_DIR, "r2_4b_all_candidate_metrics.csv", "r2_4b_top_candidate_layer_thicknesses.csv"),
        ("R2-4D2", D2_DIR, "r2_4d2_all_candidate_metrics.csv", "r2_4d2_top_candidate_layer_thicknesses.csv"),
    ]:
        metrics = {r["candidate_id"]: r for r in rows(d / metrics_name)}
        mf = manifests(d / layer_name)
        for cid in REPRESENTATIVES:
            if cid not in metrics:
                continue
            r = dict(metrics[cid])
            r["source_stage"] = stage
            r["top_layers"] = mf.get((cid, "top"), generated(r, "top"))
            r["bottom_layers"] = mf.get((cid, "bottom"), generated(r, "bottom"))
            r["layer_reconstruction"] = "manifest" if (cid, "top") in mf and (cid, "bottom") in mf else "regenerated_from_candidate_parameters"
            out.append(r)
    return out


def nmat(mat: str) -> float:
    return N_H if "TiO2" in mat else (N_L if "SiO2" in mat else N_AIR)


def cos_layer(n0: float, n: float, theta_deg: float) -> complex:
    s = n0 * math.sin(math.radians(theta_deg)) / n
    return complex(np.sqrt(1.0 - complex(s * s)))


def reflection(layers: list[tuple[str, float]], lam: float, theta: float, pol: str) -> complex:
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


def perr(phi: float) -> float:
    return abs(math.atan2(math.sin(phi), math.cos(phi)))


def rt(row: dict, lam: float, theta: float, pol: str, spacer: float | None = None, top_layers=None, bottom_layers=None) -> dict:
    d = f(row, "cavity_spacer_nm") if spacer is None else float(spacer)
    top_layers = row["top_layers"] if top_layers is None else top_layers
    bottom_layers = row["bottom_layers"] if bottom_layers is None else bottom_layers
    rtop = reflection(top_layers, lam, theta, pol)
    rbot = reflection(bottom_layers, lam, theta, pol)
    kz = 2.0 * math.pi * N_GAN / lam * math.cos(math.radians(theta))
    phase = 2.0 * kz * d + float(np.angle(rtop)) + float(np.angle(rbot))
    err = perr(phase)
    return {"phi_top_rad": float(np.angle(rtop)), "phi_bottom_rad": float(np.angle(rbot)), "R_top": float(abs(rtop) ** 2), "R_bottom": float(abs(rbot) ** 2), "roundtrip_phase_rad": float(phase), "phase_error_rad": err, "phase_error_deg": math.degrees(err)}


def best_offaxis(row: dict, spacer: float, pol: str):
    vals = [(a, rt(row, 453.0, a, pol, spacer)["phase_error_rad"]) for a in np.arange(20.0, 60.0001, 1.0)]
    return min(vals, key=lambda x: x[1])


def plot_line(base: Path, x, series: dict[str, list[float]], title: str, xlabel: str, ylabel: str):
    if plt is None:
        return
    plt.figure(figsize=(7, 4.2))
    for label, y in series.items():
        plt.plot(x, y, label=label)
    plt.title(title); plt.xlabel(xlabel); plt.ylabel(ylabel); plt.grid(True, alpha=0.25); plt.legend(fontsize=8); plt.tight_layout()
    for ext in ["png", "svg"]:
        plt.savefig(base.with_suffix(f".{ext}"), dpi=180)
    plt.close()


def plot_heat(base: Path, xs, ys, z, title: str):
    if plt is None:
        return
    plt.figure(figsize=(7, 4.5))
    plt.imshow(np.asarray(z, float), aspect="auto", origin="lower", extent=[min(xs), max(xs), min(ys), max(ys)], cmap="viridis")
    plt.colorbar(label="phase error (deg)"); plt.title(title); plt.xlabel("internal GaN angle (deg)"); plt.ylabel("wavelength (nm)"); plt.tight_layout()
    for ext in ["png", "svg"]:
        plt.savefig(base.with_suffix(f".{ext}"), dpi=180)
    plt.close()


def update_report():
    marker = "<!-- R2-4D4_FOCUSED_CAVITY_PHASE_SWEEP -->"
    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# RCLED MDC Workspace Index\n"
    block = f"""\n{marker}\n\n- Stage: R2-4D4 focused cavity-phase sweep.\n- No FDTD/Lumerical/FSP/LDF/raw monitor data.\n- Output folder: outputs/r2_4d4_focused_cavity_phase_sweep\n- Purpose: explicit angle-dependent top/bottom reflection phase and round-trip phase maps before further FDTD.\n"""
    REPORT.write_text((text[:text.index(marker)].rstrip() if marker in text else text.rstrip()) + "\n" + block, encoding="utf-8")


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    cands = load_candidates()
    found = {c["candidate_id"] for c in cands}
    missing = sorted(set(REPRESENTATIVES) - found)
    if missing:
        raise SystemExit(f"missing representative candidates: {missing}")

    manifest = [{"candidate_id": c["candidate_id"], "source_stage": c["source_stage"], "layer_reconstruction": c["layer_reconstruction"], "top_pair_count": i(c, "top_pair_count"), "bottom_pair_count": i(c, "bottom_pair_count"), "cavity_spacer_nm": f(c, "cavity_spacer_nm"), "top_termination_nm": f(c, "top_termination_nm"), "bottom_termination_nm": f(c, "bottom_termination_nm"), "top_layers": len(c["top_layers"]), "bottom_layers": len(c["bottom_layers"])} for c in cands]
    write_csv(OUT / "r2_4d4_representative_candidate_manifest.csv", manifest, list(manifest[0]))
    write_csv(OUT / "r2_4d4_reconstructability_report.csv", [{"candidate_id": c["candidate_id"], "source_stage": c["source_stage"], "layer_reconstruction": c["layer_reconstruction"], "reconstructable": True} for c in cands], ["candidate_id", "source_stage", "layer_reconstruction", "reconstructable"])

    refl, rte, normal_map, off_map = [], [], [], []
    for c in cands:
        for lam in FOCUS_LAMS:
            for ang in FOCUS_ANGLES:
                for pol in POLS:
                    v = rt(c, lam, ang, pol)
                    base = {"candidate_id": c["candidate_id"], "wavelength_nm": lam, "angle_deg_internal_GaN": ang, "polarization": pol}
                    refl.append({**base, "phi_top_rad": v["phi_top_rad"], "phi_bottom_rad": v["phi_bottom_rad"], "R_top": v["R_top"], "R_bottom": v["R_bottom"]})
                    rte.append({**base, "cavity_spacer_nm": f(c, "cavity_spacer_nm"), "phase_error_rad": v["phase_error_rad"], "phase_error_deg": v["phase_error_deg"], "roundtrip_phase_rad": v["roundtrip_phase_rad"]})
        for lam in LAM_GRID:
            for ang in [0.0, 5.0, 10.0, 20.0, 30.0, 36.0, 40.0, 60.0]:
                v = rt(c, float(lam), ang, "TE")
                (normal_map if ang <= 10 else off_map).append({"candidate_id": c["candidate_id"], "wavelength_nm": float(lam), "angle_deg_internal_GaN": ang, "polarization": "TE", "phase_error_deg": v["phase_error_deg"], "R_top": v["R_top"], "R_bottom": v["R_bottom"]})
    write_csv(OUT / "r2_4d4_reflection_phase_metrics.csv", refl, list(refl[0]))
    write_csv(OUT / "r2_4d4_roundtrip_phase_error_table.csv", rte, list(rte[0]))
    write_csv(OUT / "r2_4d4_phase_map_normal_window.csv", normal_map, list(normal_map[0]))
    write_csv(OUT / "r2_4d4_phase_map_offaxis_window.csv", off_map, list(off_map[0]))

    sweep = []
    for c in cands:
        for pol in POLS:
            for sp in SPACERS:
                ne = rt(c, 453.0, 0.0, pol, sp)["phase_error_rad"]
                oa, oe = best_offaxis(c, sp, pol)
                sweep.append({"candidate_id": c["candidate_id"], "polarization": pol, "cavity_spacer_nm": float(sp), "normal_error_deg_453": math.degrees(ne), "best_offaxis_angle_deg_20_60": float(oa), "best_offaxis_error_deg_453": math.degrees(oe), "phase_margin_deg_offaxis_minus_normal": math.degrees(oe - ne), "normal_reachable_le_15deg": ne <= math.radians(15), "normal_beats_offaxis": ne < oe})
    write_csv(OUT / "r2_4d4_cavity_spacer_sweep.csv", sweep, list(sweep[0]))

    best = []
    for cid in REPRESENTATIVES:
        rs = [r for r in sweep if r["candidate_id"] == cid]
        best.append(sorted(rs, key=lambda x: (not x["normal_reachable_le_15deg"], -float(x["phase_margin_deg_offaxis_minus_normal"]), float(x["normal_error_deg_453"])))[0])
    write_csv(OUT / "r2_4d4_best_phase_guided_spacers.csv", best, list(best[0]))

    term = []
    byid = {c["candidate_id"]: c for c in cands}
    for cid in ["R2_4D2_OPT_13003", "R2_4D2_OPT_13010"]:
        c = byid[cid]
        for side in ["top", "bottom"]:
            base = f(c, f"{side}_termination_nm")
            for delta in range(-40, 41, 5):
                c2 = dict(c); c2[f"{side}_termination_nm"] = max(0.0, base + delta); c2[f"{side}_layers"] = generated(c2, side)
                ne = rt(c2, 453.0, 0.0, "TE")["phase_error_rad"]; oa, oe = best_offaxis(c2, f(c2, "cavity_spacer_nm"), "TE")
                term.append({"candidate_id": cid, "changed_side": side, "base_termination_nm": base, "termination_delta_nm": delta, "new_termination_nm": c2[f"{side}_termination_nm"], "normal_error_deg_453_TE": math.degrees(ne), "best_offaxis_angle_deg": float(oa), "best_offaxis_error_deg_453_TE": math.degrees(oe), "phase_margin_deg_offaxis_minus_normal": math.degrees(oe - ne)})
    write_csv(OUT / "r2_4d4_termination_sensitivity.csv", term, list(term[0]))

    asym = []
    for c in cands:
        v = rt(c, 453.0, 0.0, "TE")
        asym.append({"candidate_id": c["candidate_id"], "R_top_453_0deg_TE": v["R_top"], "R_bottom_453_0deg_TE": v["R_bottom"], "bottom_minus_top_R": v["R_bottom"] - v["R_top"], "top_outcoupling_proxy_1_minus_Rtop": max(0.0, 1.0 - v["R_top"]), "top_mirror_too_strong_flag": v["R_top"] > 0.95, "bottom_not_stronger_than_top_flag": v["R_bottom"] <= v["R_top"]})
    write_csv(OUT / "r2_4d4_mirror_asymmetry_diagnosis.csv", asym, list(asym[0]))

    global_best = sorted(best, key=lambda x: (not x["normal_reachable_le_15deg"], -float(x["phase_margin_deg_offaxis_minus_normal"]), float(x["normal_error_deg_453"])))[0]
    normal_reachable = any(r["normal_reachable_le_15deg"] for r in best)
    normal_margin = any(r["normal_reachable_le_15deg"] and r["normal_beats_offaxis"] for r in best)
    route = "A" if normal_margin else ("B" if normal_reachable else "C")

    (OUT / "r2_4d4_design_space_reset_recommendation.md").write_text(f"""# R2-4D4 Design-Space Reset Recommendation

Recommended route: `{route}`.

- A: normal 453 nm is reachable by cavity/termination and beats off-axis.
- B: normal 453 nm is reachable, but 20-60 degree phase competition remains.
- C: normal 453 nm is not reliably reachable in this representative set; expand DBR design space.
- D: inconclusive; store phase maps in future proxies before FDTD.

Best phase-guided spacer: `{global_best['candidate_id']}`, pol `{global_best['polarization']}`, spacer {global_best['cavity_spacer_nm']} nm, normal error {float(global_best['normal_error_deg_453']):.3f} deg, off-axis error {float(global_best['best_offaxis_error_deg_453']):.3f} deg, margin {float(global_best['phase_margin_deg_offaxis_minus_normal']):.3f} deg.
""", encoding="utf-8")
    (OUT / "r2_4d4_stop_decisions.md").write_text("""# R2-4D4 Stop Decisions

- Do not generate FSP from R2-4D2 no-pass candidates.
- Do not run FDTD for R2-4D2 candidates.
- Do not continue old R2-4B top5 backup blindly.
- Do not run z_outofplane or broadband spectral validation for rejected candidates.
- Do not optimize only reflectance; angle-dependent phase maps must be part of the next proxy.
""", encoding="utf-8")
    (OUT / "r2_4d4_summary.md").write_text(f"""# R2-4D4 Focused Cavity-Phase Sweep

No FDTD, Lumerical, FSP, LDF, MAT/H5, or raw monitor data were created. This is a Python-only transfer-matrix reflection-phase diagnosis.

## Scope

- Representative candidates: {len(cands)}
- Wavelength grid: 445-461 nm, 0.25 nm step
- Angle grid: 0-70 deg, 1 deg step
- Angle convention: internal GaN/cavity angle
- Polarizations: TE and TM
- Cavity spacer sweep: 160-430 nm, 2 nm step
- Layer convention: top and bottom stacks are evaluated from the GaN cavity side toward air; manifest layers are reused where available, otherwise regenerated from committed candidate parameters.

## Key Result

- Normal 453 nm phase reachability within 15 deg phase error: `{normal_reachable}`
- Normal phase beating best 20-60 deg off-axis competitor: `{normal_margin}`
- Recommended route: `{route}`

## Best Phase-Guided Spacer

| candidate | pol | spacer nm | normal error deg | off-axis angle deg | off-axis error deg | margin deg |
|---|---:|---:|---:|---:|---:|---:|
| {global_best['candidate_id']} | {global_best['polarization']} | {global_best['cavity_spacer_nm']} | {float(global_best['normal_error_deg_453']):.3f} | {global_best['best_offaxis_angle_deg_20_60']} | {float(global_best['best_offaxis_error_deg_453']):.3f} | {float(global_best['phase_margin_deg_offaxis_minus_normal']):.3f} |

## Interpretation

The representative stacks can be phase-aligned near normal only if their 20-60 degree competitors are tracked. The next proxy must include explicit angle-dependent reflection phase and a phase-margin term, not just reflectance or a normal/off-axis intensity proxy.
""", encoding="utf-8")

    debug = {"stage": "R2-4D4", "runtime_s": round(time.time() - t0, 3), "no_fdtd": True, "no_lumerical": True, "representative_count": len(cands), "normal_reachable": normal_reachable, "normal_with_phase_margin": normal_margin, "recommended_route": route, "best_phase_guided_spacer": global_best}
    (OUT / "r2_4d4_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")

    best_cid = global_best["candidate_id"]
    heat = [r for r in rte if r["candidate_id"] == best_cid and r["polarization"] == "TE"]
    z = [[next(float(r["phase_error_deg"]) for r in heat if float(r["wavelength_nm"]) == lam and float(r["angle_deg_internal_GaN"]) == ang) for ang in FOCUS_ANGLES] for lam in FOCUS_LAMS]
    plot_heat(FIG / "r2_4d4_phase_error_map_best_candidate", FOCUS_ANGLES, FOCUS_LAMS, z, f"{best_cid} TE phase error")
    pr = [r for r in sweep if r["candidate_id"] == best_cid and r["polarization"] == global_best["polarization"]]
    plot_line(FIG / "r2_4d4_cavity_spacer_phase_margin", [r["cavity_spacer_nm"] for r in pr], {"normal error": [r["normal_error_deg_453"] for r in pr], "offaxis error": [r["best_offaxis_error_deg_453"] for r in pr], "margin": [r["phase_margin_deg_offaxis_minus_normal"] for r in pr]}, f"{best_cid} phase margin", "cavity spacer (nm)", "degrees")
    plot_line(FIG / "r2_4d4_normal_vs_offaxis_phase_error", [r["cavity_spacer_nm"] for r in pr], {"normal": [r["normal_error_deg_453"] for r in pr], "best 20-60": [r["best_offaxis_error_deg_453"] for r in pr]}, f"{best_cid} normal vs off-axis", "cavity spacer (nm)", "phase error (deg)")
    d13003_top = [r for r in term if r["candidate_id"] == "R2_4D2_OPT_13003" and r["changed_side"] == "top"]
    d13003_bot = [r for r in term if r["candidate_id"] == "R2_4D2_OPT_13003" and r["changed_side"] == "bottom"]
    plot_line(FIG / "r2_4d4_termination_sensitivity", [r["termination_delta_nm"] for r in d13003_top], {"top": [r["normal_error_deg_453_TE"] for r in d13003_top], "bottom": [r["normal_error_deg_453_TE"] for r in d13003_bot]}, "Termination sensitivity R2_4D2_OPT_13003", "termination delta (nm)", "normal phase error (deg)")
    plot_line(FIG / "r2_4d4_mirror_reflection_asymmetry", list(range(len(asym))), {"R top": [r["R_top_453_0deg_TE"] for r in asym], "R bottom": [r["R_bottom_453_0deg_TE"] for r in asym]}, "Mirror reflection asymmetry", "candidate index", "R")
    update_report()
    print(json.dumps({"output": str(OUT), **debug}, indent=2))


if __name__ == "__main__":
    main()
