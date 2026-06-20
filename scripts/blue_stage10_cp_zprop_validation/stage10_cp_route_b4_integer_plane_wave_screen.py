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

NM = 1e-9
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b4_integer_plane_wave_screen"
REFERENCE_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b1_dtheta_plane_wave_scout" / "route_b1_plane_wave_metrics.csv"

WAVELENGTH_NM = 450.0
PERIOD_X_NM = 431.907786
PERIOD_Y_NM = 432.0
HEIGHT_NM = 525.0
MATERIAL_INDEX = 2.6
SOURCE_Z_NM = -250.0
MONITOR_Z_NM = HEIGHT_NM + 350.0
Z_MIN_NM = -500.0
Z_MAX_NM = HEIGHT_NM + 700.0
SIM_TIME_FS = 300.0
FIELD_MONITOR = "field_monitor"
POWER_MONITOR = "T"
INTEGER_TOL = 1e-8

J1_LENGTH_NM = 230.0
J1_WIDTH_NM = 100.0
J2_LENGTH_NM = 180.0
J2_WIDTH_NM = 90.0
CANDIDATES = [
    (194.0, 90.0, 97.0),
    (194.0, 90.0, 98.0),
    (196.0, 90.0, 97.0),
    (196.0, 90.0, 98.0),
]
REFERENCE_ID = "RB1_J1J2_D195_T90_PSI97p5_H525"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage10 CP Route B4-1 fabrication-integer periodic +z plane-wave screen; no finite-patch FDTD."
    )
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--simulation-time-fs", type=float, default=SIM_TIME_FS)
    parser.add_argument("--mesh-accuracy", type=int, default=3)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def token(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return str(value).replace(".", "p")


def candidate_id(d_nm: float, theta_deg: float, psi_deg: float) -> str:
    return f"B4INT_J1J2_D{token(d_nm)}_T{token(theta_deg)}_PSI{token(psi_deg)}_H525"


def fnum(value: float) -> str:
    return f"{value:.12g}"


def cstr(value: complex) -> str:
    return f"{value.real:.12g}{value.imag:+.12g}j"


def is_integer(value: float) -> bool:
    return abs(value - round(value)) <= INTEGER_TOL


def geometry(d_nm: float, theta_deg: float, psi_deg: float) -> dict[str, Any]:
    angle = math.radians(theta_deg)
    half_dx = 0.5 * d_nm * math.cos(angle)
    half_dy = 0.5 * d_nm * math.sin(angle)
    j1_rotation = 90.0 - psi_deg
    j2_rotation = 135.0 - psi_deg
    raw_coords = [half_dx, half_dy, -half_dx, -half_dy]
    coordinates_integer = all(is_integer(v) for v in raw_coords)
    rotations_integer = is_integer(j1_rotation) and is_integer(j2_rotation)
    return {
        "J1_x_raw_nm": half_dx,
        "J1_y_raw_nm": half_dy,
        "J2_x_raw_nm": -half_dx,
        "J2_y_raw_nm": -half_dy,
        "J1_x_nm": int(round(half_dx)),
        "J1_y_nm": int(round(half_dy)),
        "J2_x_nm": int(round(-half_dx)),
        "J2_y_nm": int(round(-half_dy)),
        "J1_rotation_raw_deg": j1_rotation,
        "J2_rotation_raw_deg": j2_rotation,
        "J1_rotation_deg": int(round(j1_rotation)),
        "J2_rotation_deg": int(round(j2_rotation)),
        "delta_x_nm": -2.0 * half_dx,
        "delta_y_nm": -2.0 * half_dy,
        "x_bias_abs_nm": abs(2.0 * half_dx),
        "center_coordinates_are_integer": coordinates_integer,
        "rotations_are_integer": rotations_integer,
        "fabrication_integer_ready": coordinates_integer and rotations_integer,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def candidate_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for d_nm, theta_deg, psi_deg in CANDIDATES:
        g = geometry(d_nm, theta_deg, psi_deg)
        rows.append({
            "candidate_id": candidate_id(d_nm, theta_deg, psi_deg),
            "d_nm": int(d_nm),
            "theta_deg": int(theta_deg),
            "psi_deg": int(psi_deg),
            "J1_L_nm": int(J1_LENGTH_NM),
            "J1_W_nm": int(J1_WIDTH_NM),
            "J2_L_nm": int(J2_LENGTH_NM),
            "J2_W_nm": int(J2_WIDTH_NM),
            "J1_x_nm": g["J1_x_nm"],
            "J1_y_nm": g["J1_y_nm"],
            "J2_x_nm": g["J2_x_nm"],
            "J2_y_nm": g["J2_y_nm"],
            "J1_rotation_deg": g["J1_rotation_deg"],
            "J2_rotation_deg": g["J2_rotation_deg"],
            "height_nm": int(HEIGHT_NM),
            "wavelength_nm": int(WAVELENGTH_NM),
            "period_x_nm": fnum(PERIOD_X_NM),
            "period_y_nm": int(PERIOD_Y_NM),
            "material_index": MATERIAL_INDEX,
            "fabrication_integer_ready": str(g["fabrication_integer_ready"]).lower(),
            "note": "Integer fabrication instruction coordinates and rotations; J1/J2 terminology only.",
        })
    return rows


def geometry_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for d_nm, theta_deg, psi_deg in CANDIDATES + [(195.0, 90.0, 97.5)]:
        g = geometry(d_nm, theta_deg, psi_deg)
        cid = candidate_id(d_nm, theta_deg, psi_deg) if psi_deg != 97.5 else REFERENCE_ID
        rows.append({
            "candidate_id": cid,
            "row_role": "integer_candidate" if psi_deg != 97.5 else "physical_reference_not_integer_ready",
            "d_nm": fnum(d_nm),
            "theta_deg": fnum(theta_deg),
            "psi_deg": fnum(psi_deg),
            "J1_L_nm": fnum(J1_LENGTH_NM),
            "J1_W_nm": fnum(J1_WIDTH_NM),
            "J2_L_nm": fnum(J2_LENGTH_NM),
            "J2_W_nm": fnum(J2_WIDTH_NM),
            "J1_x_nm": g["J1_x_nm"],
            "J1_y_nm": g["J1_y_nm"],
            "J2_x_nm": g["J2_x_nm"],
            "J2_y_nm": g["J2_y_nm"],
            "J1_rotation_deg": g["J1_rotation_deg"],
            "J2_rotation_deg": g["J2_rotation_deg"],
            "J1_x_raw_nm": fnum(g["J1_x_raw_nm"]),
            "J1_y_raw_nm": fnum(g["J1_y_raw_nm"]),
            "J2_x_raw_nm": fnum(g["J2_x_raw_nm"]),
            "J2_y_raw_nm": fnum(g["J2_y_raw_nm"]),
            "J1_rotation_raw_deg": fnum(g["J1_rotation_raw_deg"]),
            "J2_rotation_raw_deg": fnum(g["J2_rotation_raw_deg"]),
            "delta_x_nm": fnum(g["delta_x_nm"]),
            "delta_y_nm": fnum(g["delta_y_nm"]),
            "x_bias_abs_nm": fnum(g["x_bias_abs_nm"]),
            "center_coordinates_are_integer": str(g["center_coordinates_are_integer"]).lower(),
            "rotations_are_integer": str(g["rotations_are_integer"]).lower(),
            "fabrication_integer_ready": str(g["fabrication_integer_ready"]).lower(),
            "note": "Rounded columns are fabrication coordinates; raw columns are numerical audit only.",
        })
    return rows


def add_pillars(fdtd: object, d_nm: float, theta_deg: float, psi_deg: float) -> None:
    g = geometry(d_nm, theta_deg, psi_deg)
    roles = [
        ("J1", J1_LENGTH_NM, J1_WIDTH_NM, g["J1_x_raw_nm"], g["J1_y_raw_nm"], g["J1_rotation_raw_deg"]),
        ("J2", J2_LENGTH_NM, J2_WIDTH_NM, g["J2_x_raw_nm"], g["J2_y_raw_nm"], g["J2_rotation_raw_deg"]),
    ]
    for role, length_nm, width_nm, x_nm, y_nm, rotation_deg in roles:
        fdtd.addrect()
        fdtd.set("name", f"{role}_pillar")
        fdtd.set("x", x_nm * NM)
        fdtd.set("y", y_nm * NM)
        fdtd.set("x span", length_nm * NM)
        fdtd.set("y span", width_nm * NM)
        fdtd.set("z min", 0.0)
        fdtd.set("z max", HEIGHT_NM * NM)
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", rotation_deg)
        fdtd.set("material", "<Object defined dielectric>")
        fdtd.set("index", MATERIAL_INDEX)


def build_model(fdtd: object, d_nm: float, theta_deg: float, psi_deg: float, linear_input: str, sim_time_fs: float, mesh_accuracy: int) -> None:
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z min", Z_MIN_NM * NM)
    fdtd.set("z max", Z_MAX_NM * NM)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", int(mesh_accuracy))
    fdtd.set("simulation time", sim_time_fs * 1e-15)
    add_pillars(fdtd, d_nm, theta_deg, psi_deg)
    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", SOURCE_Z_NM * NM)
    fdtd.set("wavelength start", WAVELENGTH_NM * NM)
    fdtd.set("wavelength stop", WAVELENGTH_NM * NM)
    fdtd.set("polarization angle", 0.0 if linear_input == "x" else 90.0)
    fdtd.addpower()
    fdtd.set("name", POWER_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", MONITOR_Z_NM * NM)
    fdtd.addprofile()
    fdtd.set("name", FIELD_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", MONITOR_Z_NM * NM)


def fsp_complete(path: Path) -> bool:
    # Completed periodic result files are about 0.85 MB; setup-only files are much smaller.
    return path.exists() and path.stat().st_size > 500_000


def run_one(lumapi: Any, runtime: Any, out_dir: Path, candidate: tuple[float, float, float], linear_input: str, args: argparse.Namespace) -> dict[str, Any]:
    d_nm, theta_deg, psi_deg = candidate
    cid = candidate_id(d_nm, theta_deg, psi_deg)
    fsp = out_dir / "_saved_fsp" / f"{cid}_{linear_input.upper()}IN.fsp"
    if fsp_complete(fsp) and not args.force:
        return {"candidate_id": cid, "linear_input": linear_input, "fdtd_status": "reused", "result_fsp": str(fsp), "note": "completed FSP reused"}
    if args.dry_run:
        return {"candidate_id": cid, "linear_input": linear_input, "fdtd_status": "not_run", "result_fsp": str(fsp), "note": "dry run"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        build_model(fdtd, d_nm, theta_deg, psi_deg, linear_input, args.simulation_time_fs, args.mesh_accuracy)
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
        return {"candidate_id": cid, "linear_input": linear_input, "fdtd_status": "ok", "result_fsp": str(fsp), "note": "setup/save/load/run/save complete"}
    except Exception as exc:
        return {"candidate_id": cid, "linear_input": linear_input, "fdtd_status": "failed", "result_fsp": str(fsp), "note": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def extract_mean_ex_ey(fdtd: object) -> tuple[complex, complex, dict[str, Any]]:
    result = fdtd.getresult(FIELD_MONITOR, "E")
    meta: dict[str, Any] = {"monitor": FIELD_MONITOR}
    if isinstance(result, dict) and "Ex" in result and "Ey" in result:
        ex = np.asarray(result["Ex"], dtype=np.complex128).squeeze()
        ey = np.asarray(result["Ey"], dtype=np.complex128).squeeze()
        meta["keys"] = list(map(str, result.keys()))
    else:
        arr = np.asarray(result["E"] if isinstance(result, dict) and "E" in result else result, dtype=np.complex128).squeeze()
        if arr.shape[-1] >= 2:
            ex, ey = arr[..., 0], arr[..., 1]
        elif arr.shape[0] >= 2:
            ex, ey = arr[0, ...], arr[1, ...]
        else:
            raise ValueError(f"Cannot infer Ex/Ey from E shape {arr.shape}")
    meta["Ex_shape"] = list(np.asarray(ex).shape)
    meta["Ey_shape"] = list(np.asarray(ey).shape)
    return complex(np.mean(ex)), complex(np.mean(ey)), meta


def extract_linear(lumapi: Any, runtime: Any, fsp: Path, show_gui: bool) -> tuple[str, complex | None, complex | None, dict[str, Any]]:
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        ex, ey, meta = extract_mean_ex_ey(fdtd)
        return "ok", ex, ey, meta
    except Exception as exc:
        return "failed", None, None, {"note": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def cp_matrix_from_linear(jones: np.ndarray) -> np.ndarray:
    root2 = math.sqrt(2.0)
    out_transform = np.array([[1 / root2, -1j / root2], [1 / root2, 1j / root2]], dtype=np.complex128)
    in_transform = np.array([[1 / root2, 1 / root2], [1j / root2, -1j / root2]], dtype=np.complex128)
    return out_transform @ jones @ in_transform


def extract_metrics(lumapi: Any, runtime: Any, out_dir: Path, candidate: tuple[float, float, float], show_gui: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    d_nm, theta_deg, psi_deg = candidate
    cid = candidate_id(d_nm, theta_deg, psi_deg)
    statuses = []
    fields = []
    debug: dict[str, Any] = {}
    for linear_input in ("X", "Y"):
        status, ex, ey, meta = extract_linear(lumapi, runtime, out_dir / "_saved_fsp" / f"{cid}_{linear_input}IN.fsp", show_gui)
        statuses.append(status)
        fields.append((ex, ey))
        debug[linear_input] = meta
    if statuses != ["ok", "ok"] or any(v is None for pair in fields for v in pair):
        return {"candidate_id": cid, "status": "missing_or_failed", "note": f"X={statuses[0]}; Y={statuses[1]}"}, debug
    exx, eyx = fields[0]
    exy, eyy = fields[1]
    jones = np.array([[exx, exy], [eyx, eyy]], dtype=np.complex128)
    cp = cp_matrix_from_linear(jones)
    ir_r, il_r, ir_l, il_l = (float(abs(cp[0, 0]) ** 2), float(abs(cp[1, 0]) ** 2), float(abs(cp[0, 1]) ** 2), float(abs(cp[1, 1]) ** 2))
    total_r = ir_r + il_r
    docp = (ir_r - il_r) / total_r
    l_fraction = il_r / total_r
    target_ratio = il_r / ir_r if ir_r else float("inf")
    all_other_ratio = il_r / (ir_r + ir_l + il_l) if (ir_r + ir_l + il_l) else float("inf")
    g = geometry(d_nm, theta_deg, psi_deg)
    soft_pass = g["fabrication_integer_ready"] and docp < -0.8 and l_fraction > 0.90 and il_r > 0.3 and target_ratio > 20.0 and g["x_bias_abs_nm"] < 1e-6
    debug["J_linear"] = [[cstr(v) for v in row] for row in jones]
    debug["J_cp_T_output_input"] = [[cstr(v) for v in row] for row in cp]
    return {
        "candidate_id": cid,
        "row_role": "integer_candidate",
        "d_nm": int(d_nm),
        "theta_deg": int(theta_deg),
        "psi_deg": int(psi_deg),
        "status": "ok",
        "IR_Rin": fnum(ir_r),
        "IL_Rin": fnum(il_r),
        "DoCP_RminusL_for_Rin": fnum(docp),
        "L_fraction_for_Rin": fnum(l_fraction),
        "IR_Lin": fnum(ir_l),
        "IL_Lin": fnum(il_l),
        "target_to_Rin_opposite_ratio": fnum(target_ratio),
        "target_to_all_other_ratio": fnum(all_other_ratio),
        "fabrication_integer_ready": "true",
        "x_bias_abs_nm": fnum(g["x_bias_abs_nm"]),
        "soft_pass": "yes" if soft_pass else "no",
        "note": "Calibrated +z CP matrix reconstructed from periodic x/y complex fields; T_output,input.",
    }, debug


def reference_row() -> dict[str, Any]:
    with REFERENCE_CSV.open(newline="", encoding="utf-8") as handle:
        row = next(r for r in csv.DictReader(handle) if r["candidate_id"] == REFERENCE_ID)
    return {
        "candidate_id": REFERENCE_ID,
        "row_role": "physical_reference_reused_not_integer_ready",
        "d_nm": row["d_nm"],
        "theta_deg": row["theta_deg"],
        "psi_deg": row["psi_deg"],
        "status": "reused_route_b1",
        "IR_Rin": row["IR_Rin"],
        "IL_Rin": row["IL_Rin"],
        "DoCP_RminusL_for_Rin": row["DoCP_RminusL_for_Rin"],
        "L_fraction_for_Rin": row["L_fraction_for_Rin"],
        "IR_Lin": row["IR_Lin"],
        "IL_Lin": row["IL_Lin"],
        "target_to_Rin_opposite_ratio": row["target_to_Rin_opposite_ratio"],
        "target_to_all_other_ratio": row["target_to_all_other_ratio"],
        "fabrication_integer_ready": "false",
        "x_bias_abs_nm": fnum(geometry(195.0, 90.0, 97.5)["x_bias_abs_nm"]),
        "soft_pass": "reference_only",
        "note": "Existing Route B1 reference; not rerun because d=195 gives +/-97.5 nm and psi=97.5 gives half-degree rotations.",
    }


def rank_rows(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for row in metrics:
        if row.get("row_role") != "integer_candidate" or row.get("status") != "ok":
            continue
        cp_strength = max(0.0, -float(row["DoCP_RminusL_for_Rin"]))
        target = float(row["IL_Rin"])
        ratio = float(row["target_to_Rin_opposite_ratio"])
        xbias = float(row["x_bias_abs_nm"])
        score = cp_strength * target * math.log10(max(ratio, 1.0) + 1.0) / (1.0 + xbias)
        ranked.append({**row, "ranking_score": fnum(score), "recommendation": "Route B4-2 top candidate" if row["soft_pass"] == "yes" else "screening only"})
    ranked.sort(key=lambda row: (row["fabrication_integer_ready"] == "true", row["soft_pass"] == "yes", float(row["ranking_score"])), reverse=True)
    for rank, row in enumerate(ranked, 1):
        row["rank"] = rank
        if rank != 1:
            row["recommendation"] = "backup integer candidate" if row["soft_pass"] == "yes" else "screening only"
    return ranked


def write_summary(out_dir: Path, metrics: list[dict[str, Any]], ranked: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    integer_rows = [r for r in metrics if r.get("row_role") == "integer_candidate"]
    ready = [r["candidate_id"] for r in integer_rows if r.get("fabrication_integer_ready") == "true"]
    lines = [
        "# Stage10 CP Route B4-1 fabrication-integer periodic plane-wave screen\n\n",
        "## English\n\n",
        "- Route B4-1; CP-APCD J1/J2 dimer branch only.\n",
        "- Finite-patch dipole FDTD: not run. No source-position cases were run.\n",
        "- D195_T90_PSI97p5 remains the physical robust reference, but is not fabrication-integer-ready because its centers are y=+/-97.5 nm and its J1/J2 rotations are -7.5/+37.5 deg.\n",
        "- D194/D196 make the theta=90 deg centers exactly +/-97 or +/-98 nm; PSI97/PSI98 make both actual pillar rotations integer degrees.\n",
        f"- Integer candidates screened: {len(integer_rows)}; fabrication_integer_ready: {', '.join(ready)}.\n",
        "- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); negative DoCP_RminusL means L-output dominant.\n\n",
        "| rank | candidate | J1 center | J2 center | rotations J1/J2 | DoCP R-in | L fraction | IL_Rin | R-input IL/IR ratio | x-bias | soft pass |\n",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---|\n",
    ]
    geometry_map = {r["candidate_id"]: r for r in geometry_rows()}
    for row in ranked:
        g = geometry_map[row["candidate_id"]]
        lines.append(f"| {row['rank']} | {row['candidate_id']} | ({g['J1_x_nm']}, {g['J1_y_nm']}) | ({g['J2_x_nm']}, {g['J2_y_nm']}) | {g['J1_rotation_deg']}/{g['J2_rotation_deg']} | {row['DoCP_RminusL_for_Rin']} | {row['L_fraction_for_Rin']} | {row['IL_Rin']} | {row['target_to_Rin_opposite_ratio']} | {row['x_bias_abs_nm']} | {row['soft_pass']} |\n")
    reference = next(r for r in metrics if r.get("row_role", "").startswith("physical_reference"))
    lines.extend([
        f"\nReference D195_T90_PSI97p5: DoCP={reference['DoCP_RminusL_for_Rin']}, L_fraction={reference['L_fraction_for_Rin']}, IL_Rin={reference['IL_Rin']}, R-input IL/IR ratio={reference['target_to_Rin_opposite_ratio']}; reference only, not rerun.\n",
        "\nRatio note: the soft threshold uses IL_Rin/IR_Rin for reconstructed R input. The stricter IL_Rin/(IR_Rin+IR_Lin+IL_Lin) is reported separately as target_to_all_other_ratio.\n",
        f"\nRecommended Route B4-2 candidate: `{ranked[0]['candidate_id']}`. Next, and not in this task, run only center_x/y, x_plus_qp_x/y, and x_minus_qp_x/y for that candidate.\n",
        "\n## 中文\n\n",
        "- 本任务是 Route B4-1，只处理 CP-APCD J1/J2 dimer 支线。\n",
        "- 没有运行 finite-patch dipole FDTD，也没有运行任何源位置 case。\n",
        "- D195_T90_PSI97p5 仍是物理鲁棒 reference，但其中心为 y=+/-97.5 nm、J1/J2 旋转为 -7.5/+37.5 deg，因此不是整数加工就绪设计。\n",
        "- D194/D196 在 theta=90 deg 时分别给出精确 +/-97 nm 和 +/-98 nm 中心；PSI97/PSI98 使两根柱的实际旋转角均为整数度。\n",
        f"- 共筛选 {len(integer_rows)} 个整数候选；fabrication_integer_ready：{', '.join(ready)}。\n",
        "- CP 约定：R=(Ex-iEy)/sqrt(2)，L=(Ex+iEy)/sqrt(2)；负 DoCP_RminusL 表示 L 输出占优。\n",
        f"- 推荐进入 Route B4-2 的候选：`{ranked[0]['candidate_id']}`。下一阶段只对该候选运行 center_x/y、x_plus_qp_x/y、x_minus_qp_x/y，本任务不运行。\n",
    ])
    (out_dir / "route_b4_integer_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    (out_dir / "_saved_fsp").mkdir(parents=True, exist_ok=True)
    candidates = candidate_rows()
    geometry_audit = geometry_rows()
    write_csv(out_dir / "route_b4_integer_candidates.csv", candidates)
    write_csv(out_dir / "route_b4_integer_geometry_audit.csv", geometry_audit)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    run_rows: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        for linear_input in ("x", "y"):
            run_rows.append(run_one(lumapi, runtime, out_dir, candidate, linear_input, args))
    metrics: list[dict[str, Any]] = [reference_row()]
    extract_debug: dict[str, Any] = {}
    if args.dry_run:
        for candidate in CANDIDATES:
            d_nm, theta_deg, psi_deg = candidate
            metrics.append({"candidate_id": candidate_id(*candidate), "row_role": "integer_candidate", "d_nm": int(d_nm), "theta_deg": int(theta_deg), "psi_deg": int(psi_deg), "status": "not_run", "fabrication_integer_ready": "true", "soft_pass": "no", "note": "dry run"})
    else:
        for candidate in CANDIDATES:
            row, debug = extract_metrics(lumapi, runtime, out_dir, candidate, args.show_gui)
            metrics.append(row)
            extract_debug[row["candidate_id"]] = debug
    write_csv(out_dir / "route_b4_integer_plane_wave_metrics.csv", metrics)
    ranked = rank_rows(metrics)
    write_csv(out_dir / "route_b4_integer_ranked_candidates.csv", ranked)
    if ranked:
        write_summary(out_dir, metrics, ranked, run_rows)
    debug = {
        "route": "B4-1",
        "branch": "CP-APCD J1/J2 only",
        "finite_patch_fdtd_runs": 0,
        "periodic_linear_fdtd_planned": 8,
        "run_rows": run_rows,
        "extract_debug": extract_debug,
        "reference_reused": REFERENCE_ID,
        "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
        "fabrication_rule": "integer nm centers and integer degree rotations",
        "soft_ratio_definition": "IL_Rin/IR_Rin",
        "strict_all_other_ratio_definition": "IL_Rin/(IR_Rin+IR_Lin+IL_Lin)",
        "top_candidate": ranked[0]["candidate_id"] if ranked else None,
    }
    (out_dir / "route_b4_integer_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(out_dir), "candidate_count": len(CANDIDATES), "run_rows": run_rows, "ranked": ranked}, indent=2))
    failed = [row for row in run_rows if row["fdtd_status"] not in {"ok", "reused", "not_run"}]
    return 1 if failed or (not args.dry_run and len(ranked) != len(CANDIDATES)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
