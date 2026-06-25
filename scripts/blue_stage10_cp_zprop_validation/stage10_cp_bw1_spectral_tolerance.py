from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

import stage10_cp_route_b4_integer_plane_wave_screen as b4

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "stage10_cp_bw1_spectral_tolerance"
CANDIDATE_ID = "B4INT_J1J2_D194_T90_PSI97_H525"
D_NM = 194.0
THETA_DEG = 90.0
PSI_DEG = 97.0
WAVELENGTHS_NM = [447.0, 448.0, 449.0, 450.0, 451.0, 452.0, 453.0]
FWHM_NM = 6.0
TARGET_CHANNEL = "R_in_to_L_out"
LEGACY_CHANNEL = "L_in_to_R_out"
RATIO_PASS_THRESHOLD = 20.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage10 CP BW1 narrow-band metasurface-only periodic plane-wave validation.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--mesh-accuracy", type=int, default=3)
    parser.add_argument("--simulation-time-fs", type=float, default=b4.SIM_TIME_FS)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def fnum(value: float) -> str:
    return f"{value:.12g}"


def fsp_path(out_dir: Path, wavelength_nm: float, linear_input: str) -> Path:
    return out_dir / "_saved_fsp" / f"BW1_{CANDIDATE_ID}_{int(wavelength_nm)}NM_{linear_input.upper()}IN.fsp"


def fsp_complete(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 500_000


def build_model(fdtd: object, wavelength_nm: float, linear_input: str, sim_time_fs: float, mesh_accuracy: int) -> None:
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", b4.PERIOD_X_NM * b4.NM)
    fdtd.set("y span", b4.PERIOD_Y_NM * b4.NM)
    fdtd.set("z min", b4.Z_MIN_NM * b4.NM)
    fdtd.set("z max", b4.Z_MAX_NM * b4.NM)
    for prop in ("x min bc", "x max bc", "y min bc", "y max bc"):
        fdtd.set(prop, "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", int(mesh_accuracy))
    fdtd.set("simulation time", sim_time_fs * 1e-15)
    b4.add_pillars(fdtd, D_NM, THETA_DEG, PSI_DEG)
    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", b4.PERIOD_X_NM * b4.NM)
    fdtd.set("y span", b4.PERIOD_Y_NM * b4.NM)
    fdtd.set("z", b4.SOURCE_Z_NM * b4.NM)
    fdtd.set("wavelength start", wavelength_nm * b4.NM)
    fdtd.set("wavelength stop", wavelength_nm * b4.NM)
    fdtd.set("polarization angle", 0.0 if linear_input == "x" else 90.0)
    fdtd.addpower()
    fdtd.set("name", b4.POWER_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", b4.PERIOD_X_NM * b4.NM)
    fdtd.set("y span", b4.PERIOD_Y_NM * b4.NM)
    fdtd.set("z", b4.MONITOR_Z_NM * b4.NM)
    fdtd.addprofile()
    fdtd.set("name", b4.FIELD_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", b4.PERIOD_X_NM * b4.NM)
    fdtd.set("y span", b4.PERIOD_Y_NM * b4.NM)
    fdtd.set("z", b4.MONITOR_Z_NM * b4.NM)


def run_one(lumapi: Any, runtime: Any, out_dir: Path, wavelength_nm: float, linear_input: str, args: argparse.Namespace) -> dict[str, Any]:
    fsp = fsp_path(out_dir, wavelength_nm, linear_input)
    if fsp_complete(fsp) and not args.force:
        return {"wavelength_nm": wavelength_nm, "linear_input": linear_input, "fdtd_status": "reused", "result_fsp": str(fsp)}
    if args.dry_run:
        return {"wavelength_nm": wavelength_nm, "linear_input": linear_input, "fdtd_status": "not_run", "result_fsp": str(fsp)}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        build_model(fdtd, wavelength_nm, linear_input, args.simulation_time_fs, args.mesh_accuracy)
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
        return {"wavelength_nm": wavelength_nm, "linear_input": linear_input, "fdtd_status": "ok", "result_fsp": str(fsp)}
    except Exception as exc:
        return {"wavelength_nm": wavelength_nm, "linear_input": linear_input, "fdtd_status": "failed", "result_fsp": str(fsp), "note": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def extract_at_wavelength(lumapi: Any, runtime: Any, out_dir: Path, wavelength_nm: float, show_gui: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = []
    statuses = []
    debug: dict[str, Any] = {}
    for linear_input in ("X", "Y"):
        status, ex, ey, meta = b4.extract_linear(lumapi, runtime, fsp_path(out_dir, wavelength_nm, linear_input), show_gui)
        statuses.append(status)
        fields.append((ex, ey))
        debug[linear_input] = meta
    if statuses != ["ok", "ok"] or any(value is None for pair in fields for value in pair):
        return {"wavelength_nm": int(wavelength_nm), "extraction_status": "failed", "pass_fail": "FAIL", "notes": f"X={statuses[0]}; Y={statuses[1]}"}, debug
    exx, eyx = fields[0]
    exy, eyy = fields[1]
    jones = np.array([[exx, exy], [eyx, eyy]], dtype=np.complex128)
    cp = b4.cp_matrix_from_linear(jones)
    ir_rin = float(abs(cp[0, 0]) ** 2)
    il_rin = float(abs(cp[1, 0]) ** 2)
    ir_lin = float(abs(cp[0, 1]) ** 2)
    il_lin = float(abs(cp[1, 1]) ** 2)
    target = il_rin
    leakage = ir_rin
    total = target + leakage
    ratio = target / leakage if leakage else float("inf")
    docp = (leakage - target) / total if total else float("nan")
    l_fraction = target / total if total else float("nan")
    r_fraction = leakage / total if total else float("nan")
    legacy_ratio = ir_lin / il_lin if il_lin else float("inf")
    target_dominant = target > leakage
    if not target_dominant:
        pass_fail = "FAIL"
        notes = "calibrated B4 target R_in->L_out no longer dominant"
    elif ratio >= RATIO_PASS_THRESHOLD:
        pass_fail = "PASS"
        notes = "target dominant and above existing B4 plane-wave soft ratio threshold"
    else:
        pass_fail = "BORDERLINE"
        notes = "target dominant but below existing B4 plane-wave soft ratio threshold"
    debug["J_linear"] = [[b4.cstr(v) for v in row] for row in jones]
    debug["J_cp_T_output_input"] = [[b4.cstr(v) for v in row] for row in cp]
    return {
        "wavelength_nm": int(wavelength_nm),
        "candidate_id": CANDIDATE_ID,
        "target_channel": TARGET_CHANNEL,
        "target_cp_power": fnum(target),
        "same-spin_leakage_power": fnum(leakage),
        "total_power": fnum(total),
        "R_fraction": fnum(r_fraction),
        "L_fraction": fnum(l_fraction),
        "DoCP_RminusL": fnum(docp),
        "conversion_to_leakage_ratio": fnum(ratio),
        "optional_reverse_channel_L_in_to_R_out": fnum(ir_lin),
        "optional_reverse_same_spin_L_in_to_L_out": fnum(il_lin),
        "optional_reverse_channel_ratio": fnum(legacy_ratio),
        "pass_fail": pass_fail,
        "result_csv": str(out_dir / "stage10_cp_bw1_per_wavelength.csv"),
        "notes": notes,
    }, debug


def gaussian_weight(wavelength_nm: float) -> float:
    return math.exp(-4.0 * math.log(2.0) * ((wavelength_nm - 450.0) / FWHM_NM) ** 2)


def weighted_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok_rows = [r for r in rows if r.get("extraction_status") != "failed"]
    weights = np.array([gaussian_weight(float(r["wavelength_nm"])) for r in ok_rows], dtype=float)
    weights /= float(weights.sum())
    target = np.array([float(r["target_cp_power"]) for r in ok_rows], dtype=float)
    leak = np.array([float(r["same-spin_leakage_power"]) for r in ok_rows], dtype=float)
    ratios = np.array([float(r["conversion_to_leakage_ratio"]) for r in ok_rows], dtype=float)
    weighted_target = float(np.sum(weights * target))
    weighted_leak = float(np.sum(weights * leak))
    worst_idx = int(np.argmin(ratios))
    flips = [r for r in ok_rows if float(r["target_cp_power"]) <= float(r["same-spin_leakage_power"])]
    edge_447 = next(float(r["conversion_to_leakage_ratio"]) for r in ok_rows if int(float(r["wavelength_nm"])) == 447)
    edge_450 = next(float(r["conversion_to_leakage_ratio"]) for r in ok_rows if int(float(r["wavelength_nm"])) == 450)
    edge_453 = next(float(r["conversion_to_leakage_ratio"]) for r in ok_rows if int(float(r["wavelength_nm"])) == 453)
    return {
        "candidate_id": CANDIDATE_ID,
        "target_channel": TARGET_CHANNEL,
        "legacy_requested_channel_reported": LEGACY_CHANNEL,
        "wavelengths_nm": [int(float(r["wavelength_nm"])) for r in ok_rows],
        "gaussian_fwhm_nm": FWHM_NM,
        "normalized_weights": {str(int(float(r["wavelength_nm"]))): float(w) for r, w in zip(ok_rows, weights)},
        "weighted_target_power_FWHM6": weighted_target,
        "weighted_same_spin_leakage_power_FWHM6": weighted_leak,
        "weighted_conversion_to_same_spin_leakage_ratio_FWHM6": weighted_target / weighted_leak if weighted_leak else float("inf"),
        "weighted_DoCP_RminusL_FWHM6": (weighted_leak - weighted_target) / (weighted_target + weighted_leak),
        "weighted_L_fraction_FWHM6": weighted_target / (weighted_target + weighted_leak),
        "worst_wavelength_nm": int(float(ok_rows[worst_idx]["wavelength_nm"])),
        "worst_case_reason": "lowest target/same-spin leakage ratio over sampled wavelengths",
        "edge_ratio_447_nm": edge_447,
        "edge_ratio_450_nm": edge_450,
        "edge_ratio_453_nm": edge_453,
        "cp_dominance_flips": len(flips) > 0,
        "flip_wavelengths_nm": [int(float(r["wavelength_nm"])) for r in flips],
        "leakage_rises_sharply_at_edge": max(edge_447, edge_453) < 0.5 * edge_450,
        "notes": "For the current frozen B4INT candidate in the existing Stage10 +z scripts, the calibrated target is R_in->L_out. L_in->R_out is reported only as optional_reverse_channel.",
    }


def plot_outputs(out_dir: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    wl = [float(r["wavelength_nm"]) for r in rows]
    target = [float(r["target_cp_power"]) for r in rows]
    leak = [float(r["same-spin_leakage_power"]) for r in rows]
    ratio = [float(r["conversion_to_leakage_ratio"]) for r in rows]
    lfrac = [float(r["L_fraction"]) for r in rows]
    weights = [summary["normalized_weights"][str(int(w))] for w in wl]
    paths: list[str] = []
    def save(name: str) -> None:
        path = out_dir / name
        plt.tight_layout()
        plt.savefig(path, dpi=160)
        plt.close()
        paths.append(str(path))
    plt.figure(figsize=(6, 4))
    plt.plot(wl, target, "o-", label="target R_in->L_out")
    plt.plot(wl, leak, "o-", label="same-spin leakage R_in->R_out")
    plt.xlabel("wavelength (nm)")
    plt.ylabel("relative power proxy")
    plt.legend()
    save("stage10_cp_bw1_target_leakage_power.png")
    plt.figure(figsize=(6, 4))
    plt.plot(wl, ratio, "o-")
    plt.xlabel("wavelength (nm)")
    plt.ylabel("target/same-spin leakage ratio")
    save("stage10_cp_bw1_ratio.png")
    plt.figure(figsize=(6, 4))
    plt.plot(wl, lfrac, "o-")
    plt.xlabel("wavelength (nm)")
    plt.ylabel("target L fraction for R input")
    save("stage10_cp_bw1_cp_fraction.png")
    plt.figure(figsize=(6, 4))
    plt.plot(wl, weights, "o-")
    plt.xlabel("wavelength (nm)")
    plt.ylabel("normalized Gaussian weight, FWHM=6 nm")
    save("stage10_cp_bw1_gaussian_weights.png")
    return paths


def write_setup_sanity(out_dir: Path) -> None:
    text = f"""# Stage10-CP-BW1 setup sanity

- selected frozen CP candidate id: `{CANDIDATE_ID}`
- source base script/FSP path: `scripts/blue_stage10_cp_zprop_validation/stage10_cp_route_b4_integer_plane_wave_screen.py` logic reused; new BW1 script varies wavelength only.
- structure: metasurface-only periodic J1/J2 dimer unit cell.
- absent objects confirmed by construction: no DBR, no RCLED cavity, no MQW, no dipole source, no finite patch.
- boundary conditions: x/y periodic; z min/max PML.
- source: +z plane wave below metasurface; x and y linear inputs are run separately and combined into CP Jones channels.
- monitors: `{b4.FIELD_MONITOR}` complex E monitor and `{b4.POWER_MONITOR}` power monitor from B4 plane-wave setup.
- exact wavelength list: {', '.join(str(int(v)) for v in WAVELENGTHS_NM)} nm.
- CP channel definitions: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).
- convention audit: formula matches the calibrated Stage10 +z/B4 scripts.
- Physical target: for the current frozen B4INT candidate in the existing Stage10 +z scripts, the calibrated target channel is RCP input -> LCP output, i.e. R_in -> L_out. Therefore BW1 treats R_in_to_L_out as the target channel. Do not use the older L_in -> R_out wording unless an inspected script explicitly proves this setup uses the opposite convention.
"""
    (out_dir / "setup_sanity.md").write_text(text, encoding="utf-8")


def write_summary(out_dir: Path, rows: list[dict[str, Any]], summary: dict[str, Any], plots: list[str]) -> None:
    lines = [
        "# Stage10-CP-BW1 narrow-band plane-wave validation\n\n",
        "## English\n\n",
        f"- Candidate: `{CANDIDATE_ID}`.\n",
        "- Scope: CP-APCD metasurface-only periodic plane-wave validation; no DBR, RCLED, MQW, dipole source, finite patch, +/-q cases, tolerance geometry, or optimization.\n",
        "- Base: B4 integer periodic plane-wave setup logic reused, with only wavelength changed.\n",
        "- Method: 7 wavelength points, each reconstructed from x/y linear plane-wave runs (14 small periodic FDTD runs unless reused).\n",
        "- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).\n",
        "- Physical target: for the current frozen B4INT candidate in the existing Stage10 +z scripts, the calibrated target channel is RCP input -> LCP output, i.e. R_in -> L_out. Therefore BW1 treats R_in_to_L_out as the target channel.  Do not use the older L_in -> R_out wording unless an inspected script proves the opposite convention; here it is reported only as an optional reverse channel.\n\n",
        "| wavelength nm | target_cp_power = R_in_to_L_out | same-spin_leakage_power = R_in_to_R_out | conversion_to_leakage_ratio | L_fraction under R_in | DoCP_RminusL | status |\n",
        "|---:|---:|---:|---:|---:|---:|---|\n",
    ]
    for r in rows:
        lines.append(f"| {r['wavelength_nm']} | {r['target_cp_power']} | {r['same-spin_leakage_power']} | {r['conversion_to_leakage_ratio']} | {r['L_fraction']} | {r['DoCP_RminusL']} | {r['pass_fail']} |\n")
    lines.extend([
        "\n### FWHM=6 nm weighted result\n\n",
        f"- weighted target power: {summary['weighted_target_power_FWHM6']:.12g}\n",
        f"- weighted same-spin leakage power: {summary['weighted_same_spin_leakage_power_FWHM6']:.12g}\n",
        f"- weighted target/same-spin leakage ratio: {summary['weighted_conversion_to_same_spin_leakage_ratio_FWHM6']:.12g}\n",
        f"- weighted L fraction: {summary['weighted_L_fraction_FWHM6']:.12g}\n",
        f"- weighted DoCP_RminusL: {summary['weighted_DoCP_RminusL_FWHM6']:.12g}\n",
        f"- worst wavelength: {summary['worst_wavelength_nm']} nm ({summary['worst_case_reason']})\n",
        f"- edge ratios 447/450/453 nm: {summary['edge_ratio_447_nm']:.6g} / {summary['edge_ratio_450_nm']:.6g} / {summary['edge_ratio_453_nm']:.6g}\n",
        f"- CP dominance flips: {summary['cp_dominance_flips']}\n",
        f"- generated plots: {', '.join(Path(p).name for p in plots)}\n",
        "- Interpretation: if all rows remain PASS, the 447-453 nm metasurface-only response is acceptable for later RCLED FWHM around 6 nm. Narrower 2-3 nm RCLED is not required by BW1 alone; cavity work remains separate.\n\n",
        "## Chinese\n\n",
        f"- 候选：`{CANDIDATE_ID}`。\n",
        "- 范围：只做 CP-APCD metasurface-only 周期平面波验证；没有 DBR、RCLED、MQW、dipole、finite patch、+/-q、容差几何或优化。\n",
        "- 基础：复用 B4 整数候选周期平面波建模/提取逻辑，只改变波长。\n",
        "- 方法：7 个波长点，每个波长用 x/y 线偏振重构 CP Jones（若无缓存则共 14 个小周期 FDTD）。\n",
        "- CP 约定：R=(Ex-iEy)/sqrt(2)，L=(Ex+iEy)/sqrt(2)。\n",
        "- 物理目标：对当前冻结 B4INT 候选，在现有 Stage10 +z 脚本中校准目标是 RCP input -> LCP output，即 R_in -> L_out。因此 BW1 将 R_in_to_L_out 作为目标通道；旧的 L_in -> R_out 只作为 optional reverse channel。\n",
        f"- FWHM=6 nm 加权 target/same-spin leakage ratio = {summary['weighted_conversion_to_same_spin_leakage_ratio_FWHM6']:.12g}，加权 L_fraction = {summary['weighted_L_fraction_FWHM6']:.12g}。\n",
        f"- 最差波长：{summary['worst_wavelength_nm']} nm；边缘 447/450/453 nm ratio = {summary['edge_ratio_447_nm']:.6g} / {summary['edge_ratio_450_nm']:.6g} / {summary['edge_ratio_453_nm']:.6g}。\n",
        "- 若全部为 PASS，则 447-453 nm 对后续 FWHM≈6 nm RCLED 是可接受的；本 metasurface-only 结果本身不要求先收窄到 2-3 nm。\n",
    ])
    (out_dir / "stage10_cp_bw1_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    (out_dir / "_saved_fsp").mkdir(parents=True, exist_ok=True)
    write_setup_sanity(out_dir)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    run_rows: list[dict[str, Any]] = []
    for wavelength_nm in WAVELENGTHS_NM:
        for linear_input in ("x", "y"):
            run_rows.append(run_one(lumapi, runtime, out_dir, wavelength_nm, linear_input, args))
    rows: list[dict[str, Any]] = []
    debug_extract: dict[str, Any] = {}
    if args.dry_run:
        rows = [{"wavelength_nm": int(w), "extraction_status": "not_run", "pass_fail": "DRY_RUN"} for w in WAVELENGTHS_NM]
        summary: dict[str, Any] = {"dry_run": True}
        plots: list[str] = []
    else:
        for wavelength_nm in WAVELENGTHS_NM:
            row, debug = extract_at_wavelength(lumapi, runtime, out_dir, wavelength_nm, args.show_gui)
            rows.append(row)
            debug_extract[str(int(wavelength_nm))] = debug
        write_csv(out_dir / "stage10_cp_bw1_per_wavelength.csv", rows)
        if any(r.get("extraction_status") == "failed" for r in rows):
            summary = {"error": "extraction failure", "rows": rows}
            plots = []
        else:
            summary = weighted_summary(rows)
            plots = plot_outputs(out_dir, rows, summary)
            write_summary(out_dir, rows, summary, plots)
    if args.dry_run:
        write_csv(out_dir / "stage10_cp_bw1_per_wavelength.csv", rows)
    (out_dir / "stage10_cp_bw1_weighted_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    debug_doc = {
        "task": "Stage10-CP-BW1 narrow-band plane-wave validation",
        "candidate_id": CANDIDATE_ID,
        "base_script": "scripts/blue_stage10_cp_zprop_validation/stage10_cp_route_b4_integer_plane_wave_screen.py",
        "runs": run_rows,
        "extract_debug": debug_extract,
        "plots": plots,
        "convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
        "target_channel": TARGET_CHANNEL,
        "legacy_requested_channel": LEGACY_CHANNEL,
        "no_dbr_no_rcled_no_mqw_no_dipole_no_finite_patch": True,
    }
    (out_dir / "stage10_cp_bw1_debug.json").write_text(json.dumps(debug_doc, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(out_dir), "runs": run_rows, "summary": summary}, indent=2))
    failed_runs = [r for r in run_rows if r["fdtd_status"] not in {"ok", "reused", "not_run"}]
    failed_extract = [r for r in rows if r.get("extraction_status") == "failed"]
    return 1 if failed_runs or failed_extract else 0


if __name__ == "__main__":
    raise SystemExit(main())


