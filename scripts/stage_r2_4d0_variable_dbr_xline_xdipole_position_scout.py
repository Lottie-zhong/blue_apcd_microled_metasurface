#!/usr/bin/env python3
"""R2-4D0 fast x-line scout: x-oriented dipole only.

Runs only two R2-4B candidates and only center_x templates from R2-4C.
Forbidden in this stage: z_outofplane, center_y, wavelength sweep, raw monitor
exports, .ldf/.mat/.h5 outputs.
"""
from __future__ import annotations

import csv
import json
import math
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

ROOT = Path(__file__).resolve().parents[1]
R2C = ROOT / "outputs" / "r2_4c_variable_dbr_setup_only_fsp" / "runtime_fsp"
R2B = ROOT / "outputs" / "r2_4b_normal_rcled_variable_dbr_tmm_optimize"
OUT = ROOT / "outputs" / "r2_4d0_variable_dbr_xline_xdipole_position_scout"
SOLVE_DIR = OUT / "runtime_solve_fsp"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"
LUMAPI_DIR = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

STAGE = "R2_4D0_variable_DBR_xline_xdipole_position_scout"
CANDIDATES = ["R2_4B_OPT_06361", "R2_4B_OPT_06176"]
X_POS_UM = [-1.4, -1.05, -0.70, -0.35, 0.0, 0.35, 0.70, 1.05, 1.4]
WAVELENGTH_NM = 453.0
MONITOR = "top_farfield_monitor"
SOURCE_NAME = "center_x_dipole"
UM = 1e-6


def import_lumapi() -> Any:
    sys.path.insert(0, str(LUMAPI_DIR))
    import lumapi  # type: ignore[import-not-found]
    return lumapi


def signed_nm(x_um: float) -> str:
    nm = int(round(x_um * 1000))
    return ("m" if nm < 0 else "p") + f"{abs(nm):04d}"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    if len(y) < 2:
        return float(np.sum(y))
    return float(np.trapezoid(y, x) if hasattr(np, "trapezoid") else np.trapz(y, x))


def sanitize(angles: Any, intensity: Any) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(angles, dtype=float).squeeze().reshape(-1)
    i = np.asarray(intensity, dtype=float).squeeze().reshape(-1)
    n = min(len(a), len(i))
    a = a[:n]
    i = np.nan_to_num(i[:n], nan=0.0, posinf=0.0, neginf=0.0)
    i = np.maximum(i, 0.0)
    order = np.argsort(a)
    return a[order], i[order]


def band_power(angles: np.ndarray, intensity: np.ndarray, lo: float, hi: float) -> float:
    mask = (np.abs(angles) >= lo) & (np.abs(angles) <= hi)
    return trapz(intensity[mask], angles[mask]) if np.count_nonzero(mask) >= 2 else 0.0


def cone_power(angles: np.ndarray, intensity: np.ndarray, cone: float) -> float:
    mask = np.abs(angles) <= cone
    return trapz(intensity[mask], angles[mask]) if np.count_nonzero(mask) >= 2 else 0.0


def fwhm_deg(angles: np.ndarray, intensity: np.ndarray) -> float:
    if len(angles) < 3 or float(np.max(intensity)) <= 0:
        return math.nan
    k = int(np.argmax(intensity))
    half = float(intensity[k]) * 0.5
    left = k
    while left > 0 and intensity[left] >= half:
        left -= 1
    right = k
    while right < len(intensity) - 1 and intensity[right] >= half:
        right += 1
    if left == 0 or right == len(intensity) - 1:
        return math.nan
    def cross(a0: float, y0: float, a1: float, y1: float) -> float:
        return a0 if y1 == y0 else a0 + (half - y0) * (a1 - a0) / (y1 - y0)
    return float(cross(float(angles[left]), float(intensity[left]), float(angles[left+1]), float(intensity[left+1])) * -1 + cross(float(angles[right-1]), float(intensity[right-1]), float(angles[right]), float(intensity[right])))


def extract_angle(fdtd: Any) -> tuple[np.ndarray, np.ndarray, str]:
    try:
        ff = fdtd.farfield2d(MONITOR, 1)
        ang = fdtd.farfieldangle(MONITOR, 1)
        a, i = sanitize(ang, ff)
        return a, i, "farfield2d_farfieldangle"
    except Exception as exc:
        try:
            t = float(fdtd.transmission(MONITOR))
            a = np.linspace(-90.0, 90.0, 181)
            i = np.zeros_like(a)
            i[len(a)//2] = max(t, 0.0)
            return a, i, f"fallback_transmission_delta_normal_after_farfield_error:{exc}"
        except Exception as exc2:
            raise RuntimeError(f"farfield2d failed: {exc}; transmission fallback failed: {exc2}")


def metrics(candidate_id: str, x_um: float, angles: np.ndarray, intensity: np.ndarray, runtime_s: float, extraction_mode: str, warnings: str = "") -> dict[str, Any]:
    total = trapz(intensity, angles)
    k = int(np.argmax(intensity)) if len(intensity) else 0
    peak = float(angles[k]) if len(angles) else math.nan
    normal = band_power(angles, intensity, 0, 5)
    offaxis = band_power(angles, intensity, 20, 60)
    return {
        "candidate_id": candidate_id,
        "x_position_um": x_um,
        "dipole": "x",
        "runtime_s": round(runtime_s, 3),
        "signed_peak_angle_deg": peak,
        "peak_abs_angle_deg": abs(peak) if not math.isnan(peak) else math.nan,
        "angular_FWHM_deg": fwhm_deg(angles, intensity),
        "eta5": cone_power(angles, intensity, 5) / total if total > 0 else math.nan,
        "eta10": cone_power(angles, intensity, 10) / total if total > 0 else math.nan,
        "eta20": cone_power(angles, intensity, 20) / total if total > 0 else math.nan,
        "eta30": cone_power(angles, intensity, 30) / total if total > 0 else math.nan,
        "I_normal_0_5deg": normal,
        "I_offaxis_20_60deg": offaxis,
        "normal_offaxis_ratio": normal / offaxis if offaxis > 0 else math.inf,
        "total_upward_power_proxy": total,
        "extraction_success": True,
        "extraction_mode": extraction_mode,
        "warnings": warnings,
    }


def write_angle(path: Path, angles: np.ndarray, intensity: np.ndarray) -> None:
    write_csv(path, [{"angle_deg": float(a), "intensity_proxy": float(v)} for a, v in zip(angles, intensity)])


def load_proxy() -> dict[str, dict[str, str]]:
    with (R2B / "r2_4b_top20_candidate_metrics.csv").open(newline="", encoding="utf-8") as f:
        rows = {r["candidate_id"]: r for r in csv.DictReader(f) if r["candidate_id"] in CANDIDATES}
    if set(rows) != set(CANDIDATES):
        raise RuntimeError(f"missing proxy rows: {sorted(set(CANDIDATES)-set(rows))}")
    return rows


def setup_template(candidate_id: str) -> Path:
    return R2C / f"R2_4C_{candidate_id}_453_center_x_setup_only.fsp"


def solve_path(candidate_id: str, x_um: float) -> Path:
    return SOLVE_DIR / f"R2_4D0_{candidate_id}_453_xpos_{signed_nm(x_um)}_x_solve.fsp"


def run_cases() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, tuple[np.ndarray, np.ndarray]]]:
    SOLVE_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for cid in CANDIDATES:
        template = setup_template(cid)
        if not template.exists():
            raise RuntimeError(f"missing center_x setup template: {template}")
        for x in X_POS_UM:
            manifest.append({
                "candidate_id": cid,
                "x_position_um": x,
                "dipole": "x",
                "setup_fsp": str(template),
                "runtime_solve_fsp": str(solve_path(cid, x)),
                "will_solve": True,
            })
    if any("z_outofplane" in r["runtime_solve_fsp"] or "center_y" in r["runtime_solve_fsp"] for r in manifest):
        raise RuntimeError("forbidden z_outofplane or center_y appeared in solve queue")
    write_csv(OUT / "r2_4d0_run_manifest.csv", manifest)
    write_json(OUT / "r2_4d0_run_manifest.json", manifest)

    lumapi = import_lumapi()
    case_rows: list[dict[str, Any]] = []
    cuts: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    first_case = True
    total_cases = len(manifest)
    fdtd = lumapi.FDTD(hide=True)
    try:
        for idx, item in enumerate(manifest, start=1):
            cid = str(item["candidate_id"])
            x = float(item["x_position_um"])
            src = Path(str(item["setup_fsp"])); dst = Path(str(item["runtime_solve_fsp"]))
            shutil.copy2(src, dst)
            t0 = time.time()
            print(f"[{idx}/{total_cases}] solve {cid} x={x:+.2f} um -> {dst}", flush=True)
            try:
                fdtd.load(str(dst))
                fdtd.switchtolayout()
                fdtd.setnamed(SOURCE_NAME, "x", x * UM)
                theta = float(fdtd.getnamed(SOURCE_NAME, "theta"))
                phi = float(fdtd.getnamed(SOURCE_NAME, "phi"))
                if abs(theta - 90.0) > 1e-9 or abs(phi) > 1e-9:
                    raise RuntimeError(f"source orientation changed: theta={theta}, phi={phi}")
                fdtd.save(str(dst))
                fdtd.run()
                runtime = time.time() - t0
                fdtd.save(str(dst))
                angles, intensity, mode = extract_angle(fdtd)
                row = metrics(cid, x, angles, intensity, runtime, mode)
                row["case_id"] = f"R2_4D0_{cid}_453_xpos_{signed_nm(x)}_x"
                row["runtime_solve_fsp"] = str(dst)
                case_rows.append(row)
                write_angle(OUT / f"r2_4d0_angle_cut_453_{cid}_xpos_{signed_nm(x)}_x.csv", angles, intensity)
                cuts[f"{cid}|{x}"] = (angles, intensity)
                first_case = False
            except Exception as exc:
                runtime = time.time() - t0
                case_rows.append({"candidate_id": cid, "x_position_um": x, "dipole": "x", "runtime_s": round(runtime, 3), "extraction_success": False, "warnings": str(exc), "runtime_solve_fsp": str(dst)})
                if first_case:
                    write_csv(OUT / "r2_4d0_case_metrics.csv", case_rows)
                    write_json(OUT / "r2_4d0_case_metrics.json", case_rows)
                    raise RuntimeError(f"first case failed; stopping: {exc}") from exc
    finally:
        try:
            fdtd.close()
        except Exception:
            pass
    return manifest, case_rows, cuts


def combine_candidate(candidate_id: str, cuts: dict[str, tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    weights_raw = np.ones(len(X_POS_UM), dtype=float)
    weights_raw[0] = weights_raw[-1] = 0.5
    weights = weights_raw / np.sum(weights_raw)
    base_a = None
    total = None
    for x, w in zip(X_POS_UM, weights):
        a, i = cuts[f"{candidate_id}|{x}"]
        if base_a is None:
            base_a = a
            total = w * i
        else:
            ii = i if len(a) == len(base_a) and np.allclose(a, base_a) else np.interp(base_a, a, i, left=0, right=0)
            total = total + w * ii
    assert base_a is not None and total is not None
    return base_a, total


def pass_label(row: dict[str, Any]) -> str:
    peak = float(row["xline_xdipole_peak_abs_angle_deg"])
    fwhm = float(row["xline_xdipole_angular_FWHM_deg"])
    ratio = float(row["xline_xdipole_normal_offaxis_ratio"])
    if peak <= 5 and fwhm <= 10 and ratio > 1.5:
        return "ideal"
    if peak <= 10 and fwhm <= 25 and ratio > 1.0:
        return "acceptable"
    return "fail"


def plot_outputs(avg_cuts: dict[str, tuple[np.ndarray, np.ndarray]], case_rows: list[dict[str, Any]], proxy_cmp: list[dict[str, Any]]) -> None:
    if plt is None:
        return
    for cid, (a, i) in avg_cuts.items():
        norm = i / np.max(i) if np.max(i) > 0 else i
        for ext in ("png", "svg"):
            p = OUT / f"r2_4d0_xline_xdipole_angle_response_453_{cid}.{ext}"
            plt.figure(figsize=(6,4)); plt.plot(a, norm, lw=2); plt.xlabel("angle (deg)"); plt.ylabel("normalized x-line intensity"); plt.grid(alpha=.3); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close()
    for ext in ("png", "svg"):
        p = OUT / f"r2_4d0_source_position_peak_angle_map.{ext}"
        plt.figure(figsize=(6,4))
        for cid in CANDIDATES:
            xs = [float(r["x_position_um"]) for r in case_rows if r.get("candidate_id") == cid and r.get("extraction_success")]
            ys = [float(r["peak_abs_angle_deg"]) for r in case_rows if r.get("candidate_id") == cid and r.get("extraction_success")]
            plt.plot(xs, ys, marker="o", label=cid)
        plt.xlabel("source x (um)"); plt.ylabel("peak abs angle (deg)"); plt.legend(fontsize=8); plt.grid(alpha=.3); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close()
        p = OUT / f"r2_4d0_proxy_vs_xline_xdipole_fdtd_summary.{ext}"
        labels = [r["candidate_id"] for r in proxy_cmp]
        x = np.arange(len(labels)); width=.35
        plt.figure(figsize=(6,4)); plt.bar(x-width/2, [float(r["proxy_peak_abs_angle_deg"]) for r in proxy_cmp], width, label="proxy peak"); plt.bar(x+width/2, [float(r["fdtd_xline_peak_abs_angle_deg"]) for r in proxy_cmp], width, label="FDTD xline peak"); plt.xticks(x, labels, rotation=15, ha="right"); plt.ylabel("peak abs angle (deg)"); plt.legend(); plt.tight_layout(); plt.savefig(p, dpi=180); plt.close()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    proxy = load_proxy()
    manifest, case_rows, cuts = run_cases()
    write_csv(OUT / "r2_4d0_case_metrics.csv", case_rows)
    write_json(OUT / "r2_4d0_case_metrics.json", case_rows)
    success = [r for r in case_rows if r.get("extraction_success")]
    warnings = [r for r in case_rows if not r.get("extraction_success")]

    avg_rows: list[dict[str, Any]] = []
    robustness: list[dict[str, Any]] = []
    proxy_cmp: list[dict[str, Any]] = []
    avg_cuts: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for cid in CANDIDATES:
        cid_success = [r for r in success if r["candidate_id"] == cid]
        if len(cid_success) != len(X_POS_UM):
            warnings.append({"candidate_id": cid, "warnings": "candidate average unavailable: missing x positions"})
            continue
        a, i = combine_candidate(cid, cuts)
        avg_cuts[cid] = (a, i)
        write_angle(OUT / f"r2_4d0_angle_cut_453_{cid}_xline_xdipole_avg.csv", a, i)
        m = metrics(cid, 0.0, a, i, 0.0, "weighted_xline_average")
        avg = {
            "candidate_id": cid,
            "xline_xdipole_signed_peak_angle_deg": m["signed_peak_angle_deg"],
            "xline_xdipole_peak_abs_angle_deg": m["peak_abs_angle_deg"],
            "xline_xdipole_angular_FWHM_deg": m["angular_FWHM_deg"],
            "xline_xdipole_eta5": m["eta5"],
            "xline_xdipole_eta10": m["eta10"],
            "xline_xdipole_eta20": m["eta20"],
            "xline_xdipole_eta30": m["eta30"],
            "xline_xdipole_I_normal_0_5deg": m["I_normal_0_5deg"],
            "xline_xdipole_I_offaxis_20_60deg": m["I_offaxis_20_60deg"],
            "xline_xdipole_normal_offaxis_ratio": m["normal_offaxis_ratio"],
            "xline_xdipole_total_upward_power_proxy": m["total_upward_power_proxy"],
        }
        avg["fast_scout_verdict"] = pass_label(avg)
        avg_rows.append(avg)
        peaks = np.array([float(r["peak_abs_angle_deg"]) for r in cid_success])
        ratios = np.array([float(r["normal_offaxis_ratio"]) for r in cid_success])
        edge = [r for r in cid_success if abs(float(r["x_position_um"])) >= 1.05]
        center = [r for r in cid_success if abs(float(r["x_position_um"])) <= 0.35]
        edge_mean = float(np.mean([float(r["normal_offaxis_ratio"]) for r in edge])) if edge else math.nan
        center_mean = float(np.mean([float(r["normal_offaxis_ratio"]) for r in center])) if center else math.nan
        robustness.append({
            "candidate_id": cid,
            "peak_angle_mean_deg": float(np.mean(peaks)),
            "peak_angle_std_deg": float(np.std(peaks)),
            "peak_angle_min_deg": float(np.min(peaks)),
            "peak_angle_max_deg": float(np.max(peaks)),
            "normal_offaxis_ratio_min": float(np.min(ratios)),
            "normal_offaxis_ratio_mean": float(np.mean(ratios)),
            "edge_positions_degrade_normal_directionality": bool(edge_mean < 0.8 * center_mean) if not math.isnan(edge_mean) and not math.isnan(center_mean) else "unknown",
            "xline_average_dominated_by_edge_offaxis_positions": bool(avg["xline_xdipole_peak_abs_angle_deg"] > 10 or edge_mean > center_mean * 1.5) if not math.isnan(edge_mean) and not math.isnan(center_mean) else "unknown",
            "edge_ratio_mean": edge_mean,
            "center_ratio_mean": center_mean,
        })
        p = proxy[cid]
        proxy_cmp.append({
            "candidate_id": cid,
            "proxy_peak_abs_angle_deg": p["peak_angle_abs_deg_453"],
            "proxy_angular_FWHM_deg": p["angular_fwhm_deg_453"],
            "proxy_normal_offaxis_ratio": p["normal_offaxis_ratio"],
            "proxy_spectral_peak_nm": p["spectral_peak_nm_normal_window"],
            "proxy_spectral_FWHM_nm": p["spectral_fwhm_nm_normal_window"],
            "fdtd_xline_peak_abs_angle_deg": avg["xline_xdipole_peak_abs_angle_deg"],
            "fdtd_xline_angular_FWHM_deg": avg["xline_xdipole_angular_FWHM_deg"],
            "fdtd_xline_normal_offaxis_ratio": avg["xline_xdipole_normal_offaxis_ratio"],
            "proxy_agreement": "agrees" if avg["fast_scout_verdict"] in ("ideal", "acceptable") else "contradicts_or_not_passed",
        })
    write_csv(OUT / "r2_4d0_xline_xdipole_average_metrics.csv", avg_rows)
    write_json(OUT / "r2_4d0_xline_xdipole_average_metrics.json", avg_rows)
    write_csv(OUT / "r2_4d0_source_position_robustness.csv", robustness)
    write_csv(OUT / "r2_4d0_proxy_vs_fdtd_comparison.csv", proxy_cmp)
    plot_outputs(avg_cuts, case_rows, proxy_cmp)

    warn_lines = ["# R2-4D0 Failure or Warning Log", "", "- Only x-oriented dipoles were solved.", "- z_outofplane and center_y were not solved."]
    for r in warnings:
        warn_lines.append(f"- {r.get('candidate_id','unknown')} x={r.get('x_position_um','')} warning: {r.get('warnings','')}")
    write_text(OUT / "r2_4d0_failure_or_warning_log.md", "\n".join(warn_lines))
    next_lines = ["# R2-4D0 Next Steps", ""]
    for avg in avg_rows:
        verdict = avg["fast_scout_verdict"]
        cid = avg["candidate_id"]
        if verdict in ("ideal", "acceptable"):
            next_lines.append(f"- {cid}: x-dipole x-line scout {verdict}; next add z_outofplane x-line scan and x+z incoherent average.")
        else:
            next_lines.append(f"- {cid}: x-dipole x-line scout failed; inspect angle cuts before spending runtime on z_outofplane.")
    write_text(OUT / "r2_4d0_next_steps.md", "\n".join(next_lines))
    summary = ["# R2-4D0 Variable DBR X-Line X-Dipole Scout", "", "Solved only x-oriented dipoles for two R2-4B candidates at 453 nm. z_outofplane and center_y were not solved.", "", f"Completed FDTD cases: {len(success)} / {len(manifest)}", "", "## X-line average verdicts", ""]
    for avg in avg_rows:
        summary.append(f"- {avg['candidate_id']}: {avg['fast_scout_verdict']}; peak_abs={float(avg['xline_xdipole_peak_abs_angle_deg']):.3g} deg, FWHM={float(avg['xline_xdipole_angular_FWHM_deg']):.3g} deg, normal/offaxis={float(avg['xline_xdipole_normal_offaxis_ratio']):.3g}.")
    write_text(OUT / "r2_4d0_summary.md", "\n".join(summary))

    note = """

## R2-4D0 fast x-line x-dipole scout

- Candidates: R2_4B_OPT_06361 and R2_4B_OPT_06176.
- Dipole solved: x only. z_outofplane and center_y not solved.
- Output folder: outputs/r2_4d0_variable_dbr_xline_xdipole_position_scout.
""".rstrip()
    old = INDEX.read_text(encoding="utf-8") if INDEX.exists() else "# RCLED MDC Workspace Index\n"
    if "## R2-4D0 fast x-line x-dipole scout" not in old:
        INDEX.write_text(old.rstrip() + "\n\n" + note + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
