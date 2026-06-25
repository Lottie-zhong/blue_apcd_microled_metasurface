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
OUT_DIR = ROOT / "outputs" / "stage10_cp_bw1r2_dense_448nm_notch_check"
FIG_DIR = OUT_DIR / "figures"
OLD_BW1R_DIR = ROOT / "outputs" / "stage10_cp_bw1r_fresh_448nm_check"
OLD_BW1R_CSV = OLD_BW1R_DIR / "stage10_cp_bw1r_fresh_448nm_per_wavelength.csv"
NEW_WAVELENGTHS_NM = [447.25, 447.75, 448.25, 448.75]
CONTEXT_WAVELENGTHS_NM = [447.0, 447.5, 448.0, 448.5, 449.0]
RATIO_PASS_THRESHOLD = 20.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage10 CP BW1R2 dense 0.25 nm notch-width check.")
    p.add_argument("--runtime", default="configs/runtime.yaml")
    p.add_argument("--output-dir", default=str(OUT_DIR))
    p.add_argument("--mesh-accuracy", type=int, default=3)
    p.add_argument("--simulation-time-fs", type=float, default=bw1.b4.SIM_TIME_FS)
    p.add_argument("--show-gui", action="store_true")
    p.add_argument("--reuse", action="store_true")
    p.add_argument("--dry-run-manifest", action="store_true")
    return p.parse_args()


def wl_token(wavelength_nm: float) -> str:
    return f"{wavelength_nm:g}".replace(".", "p")


def fsp_path(out_dir: Path, wavelength_nm: float, linear_input: str) -> Path:
    return out_dir / "_saved_fsp" / f"BW1R2_{bw1.CANDIDATE_ID}_{wl_token(wavelength_nm)}NM_{linear_input.upper()}IN.fsp"


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


def manifest(out_dir: Path) -> dict[str, Any]:
    cases = []
    for wl in NEW_WAVELENGTHS_NM:
        for lin in ("x", "y"):
            cases.append({
                "wavelength_nm": wl,
                "linear_input": lin,
                "planned_fsp": str(fsp_path(out_dir, wl, lin)),
                "fresh_run_required": True,
            })
    return {
        "task": "Stage10-CP-BW1R2 dense 0.25nm notch-width check",
        "candidate_id": bw1.CANDIDATE_ID,
        "target_channel": "R_in_to_L_out",
        "new_wavelengths_nm": NEW_WAVELENGTHS_NM,
        "context_wavelengths_from_bw1r_nm": CONTEXT_WAVELENGTHS_NM,
        "new_fdtd_case_count": len(cases),
        "cases": cases,
        "scope_guard": "metasurface-only periodic plane wave; no DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13",
        "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
    }


def run_one(lumapi: Any, runtime: Any, out_dir: Path, wavelength_nm: float, linear_input: str, args: argparse.Namespace) -> dict[str, Any]:
    fsp = fsp_path(out_dir, wavelength_nm, linear_input)
    if args.reuse and fsp_complete(fsp):
        return {"wavelength_nm": wavelength_nm, "linear_input": linear_input, "fdtd_status": "reused_bw1r2", "fresh_run": True, "result_fsp": str(fsp)}
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
    for lin in ("X", "Y"):
        status, ex, ey, meta = bw1.b4.extract_linear(lumapi, runtime, fsp_path(out_dir, wavelength_nm, lin), show_gui)
        statuses.append(status)
        fields.append((ex, ey))
        debug[lin] = meta
    if statuses != ["ok", "ok"] or any(v is None for pair in fields for v in pair):
        return {"wavelength_nm": wavelength_nm, "fresh_run": "true", "extraction_status": "failed", "status": "FAIL", "notes": f"X={statuses[0]}; Y={statuses[1]}"}, debug
    exx, eyx = fields[0]
    exy, eyy = fields[1]
    jones = np.array([[exx, exy], [eyx, eyy]], dtype=np.complex128)
    cp = bw1.b4.cp_matrix_from_linear(jones)
    ir_rin = float(abs(cp[0, 0]) ** 2)
    il_rin = float(abs(cp[1, 0]) ** 2)
    ir_lin = float(abs(cp[0, 1]) ** 2)
    target = il_rin
    leakage = ir_rin
    total = target + leakage
    ratio = target / leakage if leakage else float("inf")
    lfrac = target / total if total else float("nan")
    rfrac = leakage / total if total else float("nan")
    docp = (leakage - target) / total if total else float("nan")
    if lfrac < 0.5:
        status = "FAIL"
        notes = "CP flip or target no longer dominant"
    elif ratio >= RATIO_PASS_THRESHOLD:
        status = "PASS"
        notes = "ratio >= existing B4 soft threshold"
    else:
        status = "BORDERLINE"
        notes = "L_out dominant but ratio < existing B4 soft threshold"
    return {
        "wavelength_nm": wavelength_nm,
        "fresh_run": "true",
        "x_run_fsp_path": str(fsp_path(out_dir, wavelength_nm, "x")),
        "y_run_fsp_path": str(fsp_path(out_dir, wavelength_nm, "y")),
        "target_cp_power": f"{target:.12g}",
        "same_spin_leakage_power": f"{leakage:.12g}",
        "optional_reverse_channel": f"{ir_lin:.12g}",
        "total_power": f"{total:.12g}",
        "L_fraction_under_R_in": f"{lfrac:.12g}",
        "R_fraction_under_R_in": f"{rfrac:.12g}",
        "DoCP_RminusL": f"{docp:.12g}",
        "conversion_to_leakage_ratio": f"{ratio:.12g}",
        "status": status,
        "notes": notes,
    }, debug


def load_context_rows() -> list[dict[str, Any]]:
    with OLD_BW1R_CSV.open(newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append({
                "wavelength_nm": float(row["wavelength_nm"]),
                "data_source": "BW1R_context_reused_csv",
                "fresh_run": "false",
                "target_cp_power": row["target_cp_power"],
                "same_spin_leakage_power": row["same_spin_leakage_power"],
                "total_power": row["total_power"],
                "L_fraction_under_R_in": row["L_fraction_under_R_in"],
                "R_fraction_under_R_in": row["R_fraction_under_R_in"],
                "DoCP_RminusL": row["DoCP_RminusL"],
                "conversion_to_leakage_ratio": row["conversion_to_leakage_ratio"],
                "status": row["status"],
            })
    return rows


def merged_rows(fresh: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = load_context_rows()
    rows.extend({**r, "data_source": "BW1R2_fresh_fdtd"} for r in fresh)
    rows.sort(key=lambda r: float(r["wavelength_nm"]))
    return rows


def analyze_merged(rows: list[dict[str, Any]]) -> dict[str, Any]:
    borderline = [float(r["wavelength_nm"]) for r in rows if float(r["conversion_to_leakage_ratio"]) < RATIO_PASS_THRESHOLD]
    flips = [float(r["wavelength_nm"]) for r in rows if float(r["L_fraction_under_R_in"]) < 0.5]
    target_vals = [float(r["target_cp_power"]) for r in rows]
    leak_vals = [float(r["same_spin_leakage_power"]) for r in rows]
    worst = min(rows, key=lambda r: float(r["conversion_to_leakage_ratio"]))
    return {
        "notch_center_or_broad": "broader across 447.5-448.25 nm" if any(abs(w - 448.25) < 1e-9 for w in borderline) else "localized near 447.5-448.0 nm",
        "borderline_wavelengths_nm": borderline,
        "borderline_width_nm_min_sampled": (max(borderline) - min(borderline)) if borderline else 0.0,
        "all_dense_points_L_out_dominant": len(flips) == 0,
        "cp_flip_wavelengths_nm": flips,
        "worst_wavelength_nm": float(worst["wavelength_nm"]),
        "worst_ratio": float(worst["conversion_to_leakage_ratio"]),
        "weakness_driver": "target-channel drop dominates" if min(target_vals) / max(target_vals) < min(leak_vals) / max(leak_vals) else "leakage increase dominates",
        "recommendation": "multi-wavelength B4INT re-screen should be considered; RCLED spectral avoidance alone may need tight centering away from 447.5-448.25 nm" if borderline else "RCLED spectral avoidance appears sufficient in this sampled range",
    }


def plot_outputs(rows: list[dict[str, Any]]) -> list[str]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    wl = [float(r["wavelength_nm"]) for r in rows]
    ratio = [float(r["conversion_to_leakage_ratio"]) for r in rows]
    target = [float(r["target_cp_power"]) for r in rows]
    leak = [float(r["same_spin_leakage_power"]) for r in rows]
    lfrac = [float(r["L_fraction_under_R_in"]) for r in rows]
    docp = [float(r["DoCP_RminusL"]) for r in rows]
    paths = []
    def save(name: str) -> None:
        p = FIG_DIR / name
        plt.tight_layout(); plt.savefig(p, dpi=160); plt.close(); paths.append(str(p))
    plt.figure(figsize=(6,4)); plt.plot(wl, ratio, "o-"); plt.axhline(20, color="0.5", linestyle="--"); plt.xlabel("wavelength (nm)"); plt.ylabel("target/leakage ratio"); save("bw1r2_dense_ratio.png")
    plt.figure(figsize=(6,4)); plt.plot(wl, target, "o-", label="target R_in->L_out"); plt.plot(wl, leak, "o-", label="same-spin leakage"); plt.xlabel("wavelength (nm)"); plt.ylabel("relative power proxy"); plt.legend(); save("bw1r2_dense_target_leakage.png")
    plt.figure(figsize=(6,4)); plt.plot(wl, lfrac, "o-", label="L fraction"); plt.plot(wl, docp, "s-", label="DoCP R-L"); plt.xlabel("wavelength (nm)"); plt.legend(); save("bw1r2_dense_lfraction_docp.png")
    return paths


def write_summary(out_dir: Path, fresh: list[dict[str, Any]], merged: list[dict[str, Any]], analysis: dict[str, Any], warnings: list[str], plots: list[str]) -> None:
    lines = ["# Stage10-CP-BW1R2 dense 448 nm notch-width check\n\n", f"- Candidate: `{bw1.CANDIDATE_ID}`\n", "- Scope: Stage10 CP-APCD metasurface-only periodic plane-wave spectral stability. No DBR/RCLED/MQW/dipole/finite patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13.\n", "- Target: `R_in -> L_out`; negative DoCP_RminusL is desired L_out dominance, not failure.\n\n", "## Fresh BW1R2 points\n\n", "| nm | target | leakage | ratio | L fraction | DoCP | status |\n", "|---:|---:|---:|---:|---:|---:|---|\n"]
    for r in fresh:
        lines.append(f"| {r['wavelength_nm']} | {r['target_cp_power']} | {r['same_spin_leakage_power']} | {r['conversion_to_leakage_ratio']} | {r['L_fraction_under_R_in']} | {r['DoCP_RminusL']} | {r['status']} |\n")
    lines.extend(["\n## Dense merged 447-449 nm table\n\n", "| nm | source | ratio | L fraction | DoCP | status |\n", "|---:|---|---:|---:|---:|---|\n"])
    for r in merged:
        lines.append(f"| {r['wavelength_nm']} | {r['data_source']} | {r['conversion_to_leakage_ratio']} | {r['L_fraction_under_R_in']} | {r['DoCP_RminusL']} | {r['status']} |\n")
    lines.extend(["\n## Answers\n\n", f"- Notch center/width: {analysis['notch_center_or_broad']}.\n", f"- Borderline region where ratio < 20: {analysis['borderline_wavelengths_nm']}; sampled width at least {analysis['borderline_width_nm_min_sampled']} nm.\n", f"- All dense points still L_out dominant under R_in: {analysis['all_dense_points_L_out_dominant']}.\n", f"- CP flip wavelengths: {analysis['cp_flip_wavelengths_nm']}.\n", f"- Weakness driver: {analysis['weakness_driver']}.\n", f"- Recommendation: {analysis['recommendation']}.\n"])
    if warnings:
        lines.append("\n## Warnings\n\n")
        for w in warnings:
            lines.append(f"- {w}\n")
    lines.append("\n## Figures\n\n")
    for p in plots:
        lines.append(f"- `{p}`\n")
    (out_dir / "stage10_cp_bw1r2_dense_448nm_notch_check_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    (out_dir / "_saved_fsp").mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    m = manifest(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stage10_cp_bw1r2_manifest.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
    if args.dry_run_manifest:
        print(json.dumps(m, indent=2))
        return 0
    runtime = bw1.load_runtime_config(args.runtime)
    lumapi = bw1.import_lumapi(runtime)
    run_rows = []
    for wl in NEW_WAVELENGTHS_NM:
        for lin in ("x", "y"):
            start = time.time(); row = run_one(lumapi, runtime, out_dir, wl, lin, args); row["runtime_s"] = round(time.time() - start, 3); run_rows.append(row)
    fresh = []
    debug = {}
    for wl in NEW_WAVELENGTHS_NM:
        row, dbg = extract_one(lumapi, runtime, out_dir, wl, args.show_gui); fresh.append(row); debug[str(wl)] = dbg
    merged = merged_rows(fresh)
    analysis = analyze_merged(merged)
    warnings = []
    if any(r["status"] == "BORDERLINE" for r in merged): warnings.append("Some wavelengths are BORDERLINE under the existing B4 ratio threshold of 20.")
    if analysis["cp_flip_wavelengths_nm"]: warnings.append("CP flip detected; inspect immediately.")
    plots = plot_outputs(merged)
    write_csv(out_dir / "stage10_cp_bw1r2_fresh_run_table.csv", run_rows)
    write_csv(out_dir / "stage10_cp_bw1r2_fresh_per_wavelength.csv", fresh)
    write_csv(out_dir / "stage10_cp_bw1r2_dense_merged_447_449nm.csv", merged)
    (out_dir / "stage10_cp_bw1r2_debug.json").write_text(json.dumps({"run_rows": run_rows, "extract_debug": debug, "analysis": analysis, "warnings": warnings, "plots": plots}, indent=2), encoding="utf-8")
    write_summary(out_dir, fresh, merged, analysis, warnings, plots)
    print(json.dumps({"output_dir": str(out_dir), "fresh": fresh, "merged": merged, "analysis": analysis, "warnings": warnings, "run_rows": run_rows}, indent=2))
    return 1 if any(r["fdtd_status"] == "failed" for r in run_rows) or any(r.get("extraction_status") == "failed" for r in fresh) else 0


if __name__ == "__main__":
    raise SystemExit(main())
