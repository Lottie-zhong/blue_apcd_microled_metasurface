#!/usr/bin/env python3
"""R2-4D7 x-line x-dipole-only FDTD scout for D5_BASE_13461.

Loads the nine R2-4D6 setup-only FSPs, copies them into a D7 runtime folder,
runs them, and extracts 2D angular far-field metrics. No geometry edits, no new
candidates, no y/z/broadband cases.
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

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
D6 = ROOT / "outputs" / "r2_4d6_setup_only_fsp_d5_primary"
D6_FSP = D6 / "runtime_fsp"
OUT = ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary"
SOLVE_DIR = OUT / "runtime_solve_fsp"
FIG = OUT / "figures"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"
LUMAPI_DIR = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

STAGE = "R2-4D7 x-line x-dipole FDTD scout for D5_BASE_13461"
CANDIDATE_ID = "D5_BASE_13461"
WAVELENGTH_NM = 453.0
MONITOR = "top_farfield_monitor"
EXPECTED_X = [-1.4, -1.05, -0.70, -0.35, 0.0, 0.35, 0.70, 1.05, 1.4]


def import_lumapi() -> Any:
    sys.path.insert(0, str(LUMAPI_DIR))
    import lumapi  # type: ignore[import-not-found]
    return lumapi


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
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


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    if len(y) < 2:
        return float(np.sum(y))
    return float(np.trapezoid(y, x) if hasattr(np, "trapezoid") else np.trapz(y, x))


def sanitize(angles: object, intensity: object) -> tuple[np.ndarray, np.ndarray]:
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

    l = cross(float(angles[left]), float(intensity[left]), float(angles[left + 1]), float(intensity[left + 1]))
    r = cross(float(angles[right - 1]), float(intensity[right - 1]), float(angles[right]), float(intensity[right]))
    return float(r - l)


def extract_angle(fdtd: Any) -> tuple[np.ndarray, np.ndarray, str]:
    ff = fdtd.farfield2d(MONITOR, 1)
    ang = fdtd.farfieldangle(MONITOR, 1)
    a, i = sanitize(ang, ff)
    return a, i, "farfield2d_farfieldangle"


def metrics(angles: np.ndarray, intensity: np.ndarray, runtime_s: float, mode: str) -> dict[str, object]:
    total = trapz(intensity, angles)
    k = int(np.argmax(intensity)) if len(intensity) else 0
    peak = float(angles[k]) if len(angles) else math.nan
    normal = band_power(angles, intensity, 0, 5)
    off20_60 = band_power(angles, intensity, 20, 60)
    off30_40 = band_power(angles, intensity, 30, 40)
    return {
        "runtime_s": round(runtime_s, 3),
        "signed_peak_angle_deg": peak,
        "peak_abs_angle_deg": abs(peak) if not math.isnan(peak) else math.nan,
        "angular_FWHM_deg": fwhm_deg(angles, intensity),
        "eta5": cone_power(angles, intensity, 5) / total if total > 0 else math.nan,
        "eta10": cone_power(angles, intensity, 10) / total if total > 0 else math.nan,
        "eta20": cone_power(angles, intensity, 20) / total if total > 0 else math.nan,
        "eta30": cone_power(angles, intensity, 30) / total if total > 0 else math.nan,
        "normal_0_5_response": normal,
        "offaxis_20_60_response": off20_60,
        "offaxis_30_40_response": off30_40,
        "normal_offaxis_ratio": normal / off20_60 if off20_60 > 0 else math.inf,
        "total_power_proxy": total,
        "extraction_mode": mode,
    }


def verdict(row: dict[str, object]) -> str:
    peak = float(row["peak_abs_angle_deg"])
    fwhm = float(row["angular_FWHM_deg"])
    ratio = float(row["normal_offaxis_ratio"])
    off30 = float(row["offaxis_30_40_response"])
    normal = float(row["normal_0_5_response"])
    if 30 <= peak <= 40 or ratio < 1 or off30 > normal:
        return "fail"
    if peak <= 5 and fwhm <= 10 and ratio > 1.5:
        return "preferred"
    if peak <= 10 and fwhm <= 25 and ratio > 1.0:
        return "acceptable"
    return "near_pass_or_fail"


def load_manifest() -> list[dict[str, object]]:
    p = D6 / "r2_4d6_case_manifest.csv"
    if not p.exists():
        raise FileNotFoundError(p)
    rows = []
    for r in read_csv(p):
        if r.get("candidate_id") != CANDIDATE_ID or r.get("dipole_orientation") != "x":
            continue
        if r.get("solved") != "False" or r.get("setup_only") != "True":
            raise RuntimeError(f"not a D6 setup-only unsolved case: {r}")
        x = float(r["source_x_um"])
        rows.append({
            "case_id": r["case_id"].replace("R2_4D6", "R2_4D7"),
            "source_x_um": x,
            "setup_fsp": Path(r["fsp_path"]),
            "runtime_solve_fsp": SOLVE_DIR / (Path(r["fsp_path"]).stem.replace("R2_4D6", "R2_4D7").replace("setup_only", "solved") + ".fsp"),
        })
    rows.sort(key=lambda r: float(r["source_x_um"]))
    xs = [round(float(r["source_x_um"]), 2) for r in rows]
    if xs != [round(x, 2) for x in EXPECTED_X]:
        raise RuntimeError(f"unexpected x positions: {xs}")
    for r in rows:
        if not Path(r["setup_fsp"]).exists():
            raise FileNotFoundError(r["setup_fsp"])
    return rows


def solve_cases(manifest: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[float, tuple[np.ndarray, np.ndarray]]]:
    lumapi = import_lumapi()
    SOLVE_DIR.mkdir(parents=True, exist_ok=True)
    metrics_rows = []
    cuts = {}
    fdtd = lumapi.FDTD(hide=True)
    try:
        for idx, item in enumerate(manifest, start=1):
            src = Path(item["setup_fsp"])
            dst = Path(item["runtime_solve_fsp"])
            shutil.copy2(src, dst)
            x = float(item["source_x_um"])
            t0 = time.time()
            print(f"[{idx}/{len(manifest)}] solve x={x:+.2f} um -> {dst}", flush=True)
            try:
                fdtd.load(str(dst))
                fdtd.run()
                runtime_s = time.time() - t0
                fdtd.save(str(dst))
                angles, intensity, mode = extract_angle(fdtd)
                row = dict(item)
                row.update(metrics(angles, intensity, runtime_s, mode))
                row.update({"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "dipole_orientation": "x", "status": "ok", "error_message": ""})
                row["runtime_solve_fsp"] = str(dst)
                row["setup_fsp"] = str(src)
                row["case_verdict"] = verdict(row)
                metrics_rows.append(row)
                for a, v in zip(angles, intensity):
                    pass
                cuts[x] = (angles, intensity)
            except Exception as exc:
                row = dict(item)
                row.update({"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "dipole_orientation": "x", "status": "failed", "error_message": str(exc), "runtime_s": round(time.time() - t0, 3), "runtime_solve_fsp": str(dst), "setup_fsp": str(src)})
                metrics_rows.append(row)
                if idx == 1:
                    raise
    finally:
        try:
            fdtd.close()
        except Exception:
            pass
    return metrics_rows, cuts


def combine_average(cuts: dict[float, tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    base_a = None
    intensities = []
    for x in EXPECTED_X:
        a, i = cuts[float(x)]
        if base_a is None:
            base_a = a
            intensities.append(i)
        else:
            intensities.append(i if len(a) == len(base_a) and np.allclose(a, base_a) else np.interp(base_a, a, i, left=0, right=0))
    assert base_a is not None
    return base_a, np.mean(np.vstack(intensities), axis=0)


def write_angle_data(cuts: dict[float, tuple[np.ndarray, np.ndarray]], avg_a: np.ndarray, avg_i: np.ndarray) -> None:
    rows = []
    for x, (a, i) in cuts.items():
        for aa, vv in zip(a, i):
            rows.append({"trace": "case", "source_x_um": x, "angle_deg": float(aa), "intensity_proxy": float(vv)})
    for aa, vv in zip(avg_a, avg_i):
        rows.append({"trace": "xline_average", "source_x_um": "avg", "angle_deg": float(aa), "intensity_proxy": float(vv)})
    write_csv(OUT / "r2_4d7_angle_cut_data.csv", rows)


def plot_outputs(metrics_rows: list[dict[str, object]], avg_a: np.ndarray, avg_i: np.ndarray, avg_row: dict[str, object]) -> None:
    if plt is None:
        return
    FIG.mkdir(parents=True, exist_ok=True)
    norm = avg_i / np.max(avg_i) if np.max(avg_i) > 0 else avg_i
    for ext in ("png", "svg"):
        plt.figure(figsize=(6, 4)); plt.plot(avg_a, norm, lw=2); plt.axvspan(-10, 10, color="green", alpha=0.08); plt.axvspan(-40, -30, color="red", alpha=0.06); plt.axvspan(30, 40, color="red", alpha=0.06); plt.xlabel("angle (deg)"); plt.ylabel("normalized intensity"); plt.title("R2-4D7 x-line average"); plt.grid(alpha=.3); plt.tight_layout(); plt.savefig(FIG / f"r2_4d7_xline_average_angle_cut.{ext}", dpi=180); plt.close()
        xs = [float(r["source_x_um"]) for r in metrics_rows if r.get("status") == "ok"]
        peaks = [float(r["peak_abs_angle_deg"]) for r in metrics_rows if r.get("status") == "ok"]
        plt.figure(figsize=(6, 4)); plt.plot(xs, peaks, marker="o"); plt.axhline(10, ls="--", color="green", lw=1); plt.axhline(30, ls="--", color="red", lw=1); plt.xlabel("source x (um)"); plt.ylabel("peak abs angle (deg)"); plt.grid(alpha=.3); plt.tight_layout(); plt.savefig(FIG / f"r2_4d7_source_position_peak_angles.{ext}", dpi=180); plt.close()
        plt.figure(figsize=(5, 4)); plt.bar(["normal 0-5", "off 20-60", "off 30-40"], [float(avg_row["normal_0_5_response"]), float(avg_row["offaxis_20_60_response"]), float(avg_row["offaxis_30_40_response"])]); plt.ylabel("integrated response proxy"); plt.xticks(rotation=15); plt.tight_layout(); plt.savefig(FIG / f"r2_4d7_normal_vs_offaxis_summary.{ext}", dpi=180); plt.close()


def update_index(avg_row: dict[str, object]) -> None:
    marker = "<!-- R2-4D7_XLINE_XDIPOLE_FDTD_SCOUT_D5_PRIMARY -->"
    text = INDEX.read_text(encoding="utf-8") if INDEX.exists() else "# RCLED MDC Workspace Index\n"
    block = f"""
{marker}

- Stage: R2-4D7 x-line x-dipole FDTD scout for D5_BASE_13461.
- Candidate: D5_BASE_13461 only; 9 x positions; x dipole only; 453 nm.
- Output: `outputs/r2_4d7_xline_xdipole_fdtd_scout_d5_primary`.
- X-line average verdict: `{avg_row['scout_verdict']}`.
- Peak abs angle: {float(avg_row['peak_abs_angle_deg']):.4g} deg; angular FWHM: {float(avg_row['angular_FWHM_deg']):.4g} deg; normal/offaxis: {float(avg_row['normal_offaxis_ratio']):.4g}.
- Runtime solve FSPs are heavy and must not be staged/committed.
""".strip()
    if marker in text:
        text = text[:text.index(marker)].rstrip()
    INDEX.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    write_csv(OUT / "r2_4d7_case_manifest.csv", [{k: (str(v) if isinstance(v, Path) else v) for k, v in r.items()} for r in manifest])
    metrics_rows, cuts = solve_cases(manifest)
    success = [r for r in metrics_rows if r.get("status") == "ok"]
    failures = [r for r in metrics_rows if r.get("status") != "ok"]
    write_csv(OUT / "r2_4d7_case_metrics.csv", metrics_rows)
    if len(success) == 9:
        avg_a, avg_i = combine_average(cuts)
        avg_row = metrics(avg_a, avg_i, sum(float(r["runtime_s"]) for r in success), "mean_over_9_xdipole_positions")
        avg_row.update({"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "source_positions_count": 9})
        avg_row["scout_verdict"] = verdict(avg_row)
        write_csv(OUT / "r2_4d7_xline_average_metrics.csv", [avg_row])
        write_angle_data(cuts, avg_a, avg_i)
        plot_outputs(success, avg_a, avg_i, avg_row)
    else:
        avg_row = {"candidate_id": CANDIDATE_ID, "scout_verdict": "failed_incomplete", "source_positions_count": len(success)}
        write_csv(OUT / "r2_4d7_xline_average_metrics.csv", [avg_row])
    peaks = [float(r["peak_abs_angle_deg"]) for r in success]
    ratios = [float(r["normal_offaxis_ratio"]) for r in success]
    robustness = [{
        "candidate_id": CANDIDATE_ID,
        "solved_case_count": len(success),
        "failed_case_count": len(failures),
        "peak_abs_angle_min_deg": min(peaks) if peaks else math.nan,
        "peak_abs_angle_max_deg": max(peaks) if peaks else math.nan,
        "peak_abs_angle_std_deg": float(np.std(peaks)) if peaks else math.nan,
        "normal_offaxis_ratio_min": min(ratios) if ratios else math.nan,
        "normal_offaxis_ratio_mean": float(np.mean(ratios)) if ratios else math.nan,
        "edge_dominated_or_unstable": bool((max(peaks) if peaks else 999) >= 30 or (float(avg_row.get("normal_offaxis_ratio", 0)) < 1)),
    }]
    write_csv(OUT / "r2_4d7_source_position_robustness.csv", robustness)
    warn = ["# R2-4D7 Failure or Warning Log", "", f"- Solved case count: {len(success)} / 9", f"- Failed case count: {len(failures)}"]
    for r in failures:
        warn.append(f"- {r.get('case_id','unknown')}: {r.get('error_message','')}")
    write_text(OUT / "r2_4d7_failure_or_warning_log.md", "\n".join(warn))
    verdict_text = str(avg_row.get("scout_verdict", "unknown"))
    write_text(OUT / "r2_4d7_next_steps.md", f"""
# R2-4D7 Next Steps

- Verdict: `{verdict_text}`.
- If preferred/acceptable: consider a separate z_outofplane or incoherent MQW validation stage.
- If failed: stop D5_BASE_13461 FDTD expansion and return to stack/proxy redesign.
""")
    write_text(OUT / "r2_4d7_summary.md", f"""
# R2-4D7 X-Line X-Dipole FDTD Scout for D5_BASE_13461

- Candidate: `{CANDIDATE_ID}` only.
- Source positions solved: {len(success)} / 9.
- Failed cases: {len(failures)}.
- Dipole: x-oriented only, theta=90 deg, phi=0 deg.
- Wavelength: {WAVELENGTH_NM:g} nm.
- X-line average verdict: `{verdict_text}`.
- X-line average peak abs angle: {float(avg_row.get('peak_abs_angle_deg', math.nan)):.6g} deg.
- X-line average angular FWHM: {float(avg_row.get('angular_FWHM_deg', math.nan)):.6g} deg.
- X-line average eta5/eta10/eta20/eta30: {float(avg_row.get('eta5', math.nan)):.6g}, {float(avg_row.get('eta10', math.nan)):.6g}, {float(avg_row.get('eta20', math.nan)):.6g}, {float(avg_row.get('eta30', math.nan)):.6g}.
- X-line average normal/offaxis ratio: {float(avg_row.get('normal_offaxis_ratio', math.nan)):.6g}.

Runtime solved FSPs are under `runtime_solve_fsp/` and must not be committed.
""")
    write_json(OUT / "r2_4d7_debug.json", {"stage": STAGE, "candidate_id": CANDIDATE_ID, "solved_case_count": len(success), "failed_case_count": len(failures), "xline_average": avg_row, "runtime_solve_dir": str(SOLVE_DIR)})
    update_index(avg_row)
    print(json.dumps({"output": str(OUT), "solved_case_count": len(success), "failed_case_count": len(failures), "xline_average": avg_row}, indent=2, ensure_ascii=False))
    return 0 if len(success) == 9 else 2


if __name__ == "__main__":
    raise SystemExit(main())
