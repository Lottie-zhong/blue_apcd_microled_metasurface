from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import stage10_cp_bw1_spectral_tolerance as bw1

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "stage10_cp_bw1r_fresh_448nm_check"
FIG_DIR = OUT_DIR / "figures"
LOG_DIR = OUT_DIR / "logs"
OLD_CSV = ROOT / "outputs" / "stage10_cp_bw1_spectral_tolerance" / "stage10_cp_bw1_per_wavelength.csv"
WAVELENGTHS_NM = [447.0, 447.5, 448.0, 448.5, 449.0]
RATIO_PASS_THRESHOLD = 20.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage10 CP BW1R fresh 448 nm anomaly check.")
    p.add_argument("--runtime", default="configs/runtime.yaml")
    p.add_argument("--output-dir", default=str(OUT_DIR))
    p.add_argument("--mesh-accuracy", type=int, default=3)
    p.add_argument("--simulation-time-fs", type=float, default=bw1.b4.SIM_TIME_FS)
    p.add_argument("--show-gui", action="store_true")
    p.add_argument("--reuse", action="store_true", help="Reuse complete BW1R FSPs in this folder; never reads old BW1 FSPs.")
    return p.parse_args()


def wl_token(wavelength_nm: float) -> str:
    return f"{wavelength_nm:g}".replace(".", "p")


def fsp_path(out_dir: Path, wavelength_nm: float, linear_input: str) -> Path:
    return out_dir / "_saved_fsp" / f"BW1R_{bw1.CANDIDATE_ID}_{wl_token(wavelength_nm)}NM_{linear_input.upper()}IN.fsp"


def fsp_complete(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 500_000


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def run_one(lumapi: Any, runtime: Any, out_dir: Path, wavelength_nm: float, linear_input: str, args: argparse.Namespace) -> dict[str, Any]:
    fsp = fsp_path(out_dir, wavelength_nm, linear_input)
    if args.reuse and fsp_complete(fsp):
        return {"wavelength_nm": wavelength_nm, "linear_input": linear_input, "fdtd_status": "reused_bw1r", "fresh_run": True, "result_fsp": str(fsp)}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        bw1.build_model(fdtd, wavelength_nm, linear_input, args.simulation_time_fs, args.mesh_accuracy)
        fdtd.save(str(fsp.resolve()))
    finally:
        if fdtd is not None:
            fdtd.close()
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        fdtd.run()
        fdtd.save(str(fsp.resolve()))
        return {"wavelength_nm": wavelength_nm, "linear_input": linear_input, "fdtd_status": "ok", "fresh_run": True, "result_fsp": str(fsp)}
    except Exception as exc:
        return {"wavelength_nm": wavelength_nm, "linear_input": linear_input, "fdtd_status": "failed", "fresh_run": False, "result_fsp": str(fsp), "note": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def extract_one(lumapi: Any, runtime: Any, out_dir: Path, wavelength_nm: float, show_gui: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = []
    statuses = []
    debug: dict[str, Any] = {}
    for linear_input in ("X", "Y"):
        status, ex, ey, meta = bw1.b4.extract_linear(lumapi, runtime, fsp_path(out_dir, wavelength_nm, linear_input), show_gui)
        statuses.append(status)
        fields.append((ex, ey))
        debug[linear_input] = meta
    if statuses != ["ok", "ok"] or any(v is None for pair in fields for v in pair):
        return {"wavelength_nm": wavelength_nm, "fresh_run": "true", "status": "FAIL", "notes": f"X={statuses[0]}; Y={statuses[1]}"}, debug
    exx, eyx = fields[0]
    exy, eyy = fields[1]
    jones = np.array([[exx, exy], [eyx, eyy]], dtype=np.complex128)
    cp = bw1.b4.cp_matrix_from_linear(jones)
    ir_rin = float(abs(cp[0, 0]) ** 2)
    il_rin = float(abs(cp[1, 0]) ** 2)
    ir_lin = float(abs(cp[0, 1]) ** 2)
    il_lin = float(abs(cp[1, 1]) ** 2)
    target = il_rin
    leakage = ir_rin
    total = target + leakage
    ratio = target / leakage if leakage else float("inf")
    docp = (leakage - target) / total if total else float("nan")
    lfrac = target / total if total else float("nan")
    rfrac = leakage / total if total else float("nan")
    if target <= leakage:
        status = "FAIL"
    elif ratio >= RATIO_PASS_THRESHOLD:
        status = "PASS"
    else:
        status = "BORDERLINE"
    debug["J_cp_T_output_input"] = [[bw1.b4.cstr(v) for v in row] for row in cp]
    return {
        "wavelength_nm": wavelength_nm,
        "fresh_run": "true",
        "target_cp_power": f"{target:.12g}",
        "same_spin_leakage_power": f"{leakage:.12g}",
        "optional_reverse_channel": f"{ir_lin:.12g}",
        "total_power": f"{total:.12g}",
        "L_fraction_under_R_in": f"{lfrac:.12g}",
        "R_fraction_under_R_in": f"{rfrac:.12g}",
        "DoCP_RminusL": f"{docp:.12g}",
        "conversion_to_leakage_ratio": f"{ratio:.12g}",
        "status": status,
        "x_run_fsp_path": str(fsp_path(out_dir, wavelength_nm, "x")),
        "y_run_fsp_path": str(fsp_path(out_dir, wavelength_nm, "y")),
    }, debug


def load_old_rows() -> dict[float, dict[str, str]]:
    with OLD_CSV.open(newline="", encoding="utf-8") as handle:
        return {float(row["wavelength_nm"]): row for row in csv.DictReader(handle)}


def verdict(fresh: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> str:
    by = {float(r["wavelength_nm"]): r for r in fresh}
    r448 = float(by[448.0]["conversion_to_leakage_ratio"])
    r4475 = float(by[447.5]["conversion_to_leakage_ratio"])
    r4485 = float(by[448.5]["conversion_to_leakage_ratio"])
    old448 = next(float(r["old_ratio"]) for r in comparison if float(r["wavelength_nm"]) == 448.0)
    neighbor_mean = 0.5 * (r4475 + r4485)
    if abs(r448 - neighbor_mean) / max(neighbor_mean, 1e-30) < 0.35 and old448 < 0.5 * neighbor_mean:
        return "old_448_likely_stale_or_extraction_anomaly"
    if r448 < 20.0 and r4475 < 20.0 and r4485 < 20.0:
        return "real_spectral_notch"
    if r448 < 20.0 and (r4475 >= 20.0 or r4485 >= 20.0):
        return "unresolved_recommend_0p25nm_check"
    return "fresh_448_not_anomalous"


def make_comparison(fresh: list[dict[str, Any]]) -> list[dict[str, Any]]:
    old = load_old_rows()
    f = {float(row["wavelength_nm"]): row for row in fresh}
    rows = []
    for wl in (447.0, 448.0, 449.0):
        o = old[wl]
        n = f[wl]
        old_target = float(o["target_cp_power"])
        fresh_target = float(n["target_cp_power"])
        old_leak = float(o["same-spin_leakage_power"])
        fresh_leak = float(n["same_spin_leakage_power"])
        old_ratio = float(o["conversion_to_leakage_ratio"])
        fresh_ratio = float(n["conversion_to_leakage_ratio"])
        old_lfrac = float(o["L_fraction"])
        fresh_lfrac = float(n["L_fraction_under_R_in"])
        rows.append({
            "wavelength_nm": wl,
            "old_target": old_target,
            "fresh_target": fresh_target,
            "old_leakage": old_leak,
            "fresh_leakage": fresh_leak,
            "old_ratio": old_ratio,
            "fresh_ratio": fresh_ratio,
            "old_L_fraction": old_lfrac,
            "fresh_L_fraction": fresh_lfrac,
            "target_relative_change": fresh_target / old_target if old_target else "inf",
            "ratio_relative_change": fresh_ratio / old_ratio if old_ratio else "inf",
            "L_fraction_delta": fresh_lfrac - old_lfrac,
            "anomaly_verdict": "context_point",
        })
    v = verdict(fresh, rows)
    for row in rows:
        if float(row["wavelength_nm"]) == 448.0:
            row["anomaly_verdict"] = v
    return rows


def plot_outputs(fresh: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> list[str]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    wl = [float(r["wavelength_nm"]) for r in fresh]
    target = [float(r["target_cp_power"]) for r in fresh]
    leak = [float(r["same_spin_leakage_power"]) for r in fresh]
    ratio = [float(r["conversion_to_leakage_ratio"]) for r in fresh]
    lfrac = [float(r["L_fraction_under_R_in"]) for r in fresh]
    docp = [float(r["DoCP_RminusL"]) for r in fresh]
    paths = []
    def save(name: str) -> None:
        path = FIG_DIR / name
        plt.tight_layout()
        plt.savefig(path, dpi=160)
        plt.close()
        paths.append(str(path))
    plt.figure(figsize=(6, 4)); plt.plot(wl, target, "o-", label="target R_in->L_out"); plt.plot(wl, leak, "o-", label="same-spin leakage"); plt.xlabel("wavelength (nm)"); plt.ylabel("relative power proxy"); plt.legend(); save("bw1r_fresh_target_leakage.png")
    plt.figure(figsize=(6, 4)); plt.plot(wl, ratio, "o-"); plt.axhline(20, color="0.5", linestyle="--"); plt.xlabel("wavelength (nm)"); plt.ylabel("target/leakage ratio"); save("bw1r_fresh_ratio.png")
    plt.figure(figsize=(6, 4)); plt.plot(wl, lfrac, "o-", label="L fraction"); plt.plot(wl, docp, "s-", label="DoCP R-L"); plt.xlabel("wavelength (nm)"); plt.legend(); save("bw1r_fresh_lfraction_docp.png")
    cwl = [float(r["wavelength_nm"]) for r in comparison]
    plt.figure(figsize=(6, 4)); plt.plot(cwl, [float(r["old_ratio"]) for r in comparison], "o--", label="old BW1"); plt.plot(cwl, [float(r["fresh_ratio"]) for r in comparison], "s-", label="fresh BW1R"); plt.xlabel("wavelength (nm)"); plt.ylabel("target/leakage ratio"); plt.legend(); save("bw1r_old_vs_fresh_ratio.png")
    return paths


def write_setup_sanity(out_dir: Path) -> None:
    text = f"""# Stage10-CP-BW1R fresh 448 nm setup sanity

- selected candidate id: `{bw1.CANDIDATE_ID}`
- geometry: d=194 nm, theta=90 deg, psi=97 deg, H=525 nm, J1=230x100 nm, J2=180x90 nm, period_x={bw1.b4.PERIOD_X_NM} nm, period_y={bw1.b4.PERIOD_Y_NM} nm, index={bw1.b4.MATERIAL_INDEX}
- base script reused: `scripts/blue_stage10_cp_zprop_validation/stage10_cp_bw1_spectral_tolerance.py`, which reuses `stage10_cp_route_b4_integer_plane_wave_screen.py`
- fresh wavelength list: {', '.join(str(v) for v in WAVELENGTHS_NM)} nm
- new FDTD simulations are run in this output folder; previous BW1 FSPs are not used for metrics
- old BW1 CSV/FSPs are inspected only for old-vs-fresh comparison
- source: +z periodic plane wave, x/y linear basis runs
- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)
- target convention: R_in_to_L_out
- monitor/extraction: complex Ex/Ey from `{bw1.b4.FIELD_MONITOR}`, CP Jones reconstruction from x/y linear fields
- excluded by construction: no DBR, no RCLED, no MQW, no dipole, no finite patch, no +/-q, no tolerance geometry
"""
    (out_dir / "setup_sanity.md").write_text(text, encoding="utf-8")


def write_summary(out_dir: Path, fresh: list[dict[str, Any]], comparison: list[dict[str, Any]], plots: list[str], run_log: list[dict[str, Any]]) -> None:
    v = verdict(fresh, comparison)
    lines = ["# Stage10-CP-BW1R fresh 448 nm anomaly check\n\n", f"- Candidate: `{bw1.CANDIDATE_ID}`\n", "- Target: `R_in_to_L_out`; same-spin leakage: `R_in_to_R_out`.\n", "- Fresh simulations ran in a new folder; old BW1 FSPs were not used for metrics.\n", "- Scope: metasurface-only periodic plane wave. No DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry.\n\n", "## Fresh metrics\n\n", "| nm | target | same-spin leakage | ratio | L fraction | DoCP R-L | status |\n", "|---:|---:|---:|---:|---:|---:|---|\n"]
    for r in fresh:
        lines.append(f"| {r['wavelength_nm']} | {r['target_cp_power']} | {r['same_spin_leakage_power']} | {r['conversion_to_leakage_ratio']} | {r['L_fraction_under_R_in']} | {r['DoCP_RminusL']} | {r['status']} |\n")
    lines.extend(["\n## Old vs fresh comparison\n\n", "| nm | old ratio | fresh ratio | old L frac | fresh L frac | verdict |\n", "|---:|---:|---:|---:|---:|---|\n"])
    for r in comparison:
        lines.append(f"| {r['wavelength_nm']} | {r['old_ratio']:.12g} | {r['fresh_ratio']:.12g} | {r['old_L_fraction']:.12g} | {r['fresh_L_fraction']:.12g} | {r['anomaly_verdict']} |\n")
    lines.extend([f"\n## Verdict\n\n`{v}`\n\n", "If unresolved, the next minimal check is a 0.25 nm fresh grid around 448 nm.\n\n", "## Run log\n\n"])
    for r in run_log:
        lines.append(f"- {r['wavelength_nm']} nm {r['linear_input']}: {r['fdtd_status']}, runtime_s={r.get('runtime_s', '')}, fsp={r['result_fsp']}\n")
    lines.append("\n## Figures\n\n")
    for p in plots:
        lines.append(f"- `{p}`\n")
    (out_dir / "stage10_cp_bw1r_fresh_448nm_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    (out_dir / "_saved_fsp").mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    write_setup_sanity(out_dir)
    runtime = bw1.load_runtime_config(args.runtime)
    lumapi = bw1.import_lumapi(runtime)
    run_log = []
    for wl in WAVELENGTHS_NM:
        for linear_input in ("x", "y"):
            start = time.time()
            row = run_one(lumapi, runtime, out_dir, wl, linear_input, args)
            row["runtime_s"] = round(time.time() - start, 3)
            run_log.append(row)
    fresh = []
    debug = {}
    for wl in WAVELENGTHS_NM:
        row, dbg = extract_one(lumapi, runtime, out_dir, wl, args.show_gui)
        fresh.append(row)
        debug[str(wl)] = dbg
    comparison = make_comparison(fresh)
    plots = plot_outputs(fresh, comparison)
    write_csv(out_dir / "stage10_cp_bw1r_fresh_448nm_per_wavelength.csv", fresh)
    write_csv(out_dir / "stage10_cp_bw1r_old_vs_fresh_comparison.csv", comparison)
    write_csv(LOG_DIR / "stage10_cp_bw1r_run_log.csv", run_log)
    debug_doc = {"run_log": run_log, "extract_debug": debug, "verdict": verdict(fresh, comparison), "plots": plots}
    (out_dir / "stage10_cp_bw1r_debug.json").write_text(json.dumps(debug_doc, indent=2), encoding="utf-8")
    write_summary(out_dir, fresh, comparison, plots, run_log)
    print(json.dumps({"output_dir": str(out_dir), "verdict": verdict(fresh, comparison), "fresh": fresh, "comparison": comparison, "run_log": run_log}, indent=2))
    return 1 if any(r["fdtd_status"] == "failed" for r in run_log) else 0


if __name__ == "__main__":
    raise SystemExit(main())
