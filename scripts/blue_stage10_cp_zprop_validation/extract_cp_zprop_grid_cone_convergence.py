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

OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation")
FIELD_MONITOR = "top_field_monitor_zprop"
GRID_SIZES = [31, 61, 101]
CONE_DEG = [10.0, 15.0, 20.0, 25.0, 30.0]
TIME_FS_DEFAULT = [100]
DEBUG_JSON = OUT_DIR / "cp_zprop_sanity_convergence_debug.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract +z far-field grid/cone convergence from existing CP zprop center FSPs.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--time-fs", type=int, nargs="*", default=TIME_FS_DEFAULT)
    parser.add_argument("--grid-sizes", type=int, nargs="*", default=GRID_SIZES)
    parser.add_argument("--cone-deg", type=float, nargs="*", default=CONE_DEG)
    parser.add_argument("--show-gui", action="store_true")
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def array_info(value: Any) -> dict[str, Any]:
    arr = np.asarray(value)
    return {"shape": list(arr.shape), "dtype": str(arr.dtype), "is_complex": bool(np.iscomplexobj(arr)), "size": int(arr.size)}


def fsp_path(out_dir: Path, orientation: str, time_fs: int) -> Path:
    return out_dir / "_saved_fsp" / f"CP_ZPROP_CENTER_{orientation.upper()}_T{time_fs}FS.fsp"


def cone_mask(ux: np.ndarray, uy: np.ndarray, shape: tuple[int, ...], cone_deg: float) -> np.ndarray | None:
    uxn = np.asarray(ux, dtype=float).squeeze()
    uyn = np.asarray(uy, dtype=float).squeeze()
    limit = math.sin(math.radians(cone_deg))
    if uxn.ndim == 1 and uyn.ndim == 1:
        xx, yy = np.meshgrid(uxn, uyn, indexing="ij")
    else:
        xx, yy = np.broadcast_arrays(uxn, uyn)
    mask = (xx**2 + yy**2) <= limit**2
    try:
        return np.broadcast_to(mask, shape)
    except Exception:
        if mask.T.shape == shape:
            return mask.T
    return None


def extract_one(fdtd: object, grid_n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    vec = fdtd.farfieldvector3d(FIELD_MONITOR, 1, grid_n, grid_n)
    arr = np.asarray(vec)
    if arr.shape[-1] >= 3:
        ex, ey = arr[..., 0], arr[..., 1]
    elif arr.shape[0] >= 3:
        ex, ey = arr[0, ...], arr[1, ...]
    else:
        raise ValueError(f"Cannot infer farfieldvector3d component axis from shape {arr.shape}")
    ux = np.asarray(fdtd.farfieldux(FIELD_MONITOR, 1, grid_n, grid_n), dtype=float).squeeze()
    uy = np.asarray(fdtd.farfielduy(FIELD_MONITOR, 1, grid_n, grid_n), dtype=float).squeeze()
    return np.asarray(ex, dtype=np.complex128).squeeze(), np.asarray(ey, dtype=np.complex128).squeeze(), ux, uy, {"farfieldvector3d": array_info(vec), "ux": array_info(ux), "uy": array_info(uy)}


def cp_row(case_id: str, orientation: str, time_fs: int, grid_n: int, cone: float, ex: np.ndarray, ey: np.ndarray, ux: np.ndarray, uy: np.ndarray, fsp: Path) -> dict[str, Any]:
    er = (ex - 1j * ey) / math.sqrt(2.0)
    el = (ex + 1j * ey) / math.sqrt(2.0)
    mask = cone_mask(ux, uy, er.shape, cone)
    if mask is None:
        use = np.ones(er.shape, dtype=bool)
        note = "no cone mask; integrated all samples"
    else:
        use = mask.astype(bool)
        note = "cone mask from farfieldux/farfielduy"
    ir = float(np.sum(np.abs(er[use]) ** 2))
    il = float(np.sum(np.abs(el[use]) ** 2))
    denom = ir + il
    return {
        "row_type": "case",
        "case_id": case_id,
        "orientation": orientation,
        "simulation_time_fs": time_fs,
        "grid_n": grid_n,
        "cone_deg": cone,
        "IR_cone": ir,
        "IL_cone": il,
        "DoCP_RminusL": (ir - il) / denom if denom else float("nan"),
        "DoCP_LminusR": (il - ir) / denom if denom else float("nan"),
        "total_cone_power": denom,
        "status": "ok",
        "result_fsp": str(fsp),
        "note": note,
    }


def load_extract_case(lumapi: Any, runtime: Any, fsp: Path, orientation: str, time_fs: int, grid_n: int, cones: list[float], show_gui: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    case_id = f"CP_ZPROP_CENTER_{orientation.upper()}_T{time_fs}FS"
    if not fsp.exists():
        return ([{"row_type": "case", "case_id": case_id, "orientation": orientation, "simulation_time_fs": time_fs, "grid_n": grid_n, "cone_deg": cone, "IR_cone": "", "IL_cone": "", "DoCP_RminusL": "", "DoCP_LminusR": "", "total_cone_power": "", "status": "missing_fsp", "result_fsp": str(fsp), "note": "FSP not found"} for cone in cones], {})
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        ex, ey, ux, uy, info = extract_one(fdtd, grid_n)
        return [cp_row(case_id, orientation, time_fs, grid_n, cone, ex, ey, ux, uy, fsp) for cone in cones], info
    except Exception as exc:
        return ([{"row_type": "case", "case_id": case_id, "orientation": orientation, "simulation_time_fs": time_fs, "grid_n": grid_n, "cone_deg": cone, "IR_cone": "", "IL_cone": "", "DoCP_RminusL": "", "DoCP_LminusR": "", "total_cone_power": "", "status": "failed", "result_fsp": str(fsp), "note": f"{type(exc).__name__}: {exc}"} for cone in cones], {"error": f"{type(exc).__name__}: {exc}"})
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def add_incoherent_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = list(rows)
    keys = sorted({(r["simulation_time_fs"], r["grid_n"], r["cone_deg"]) for r in rows if r.get("row_type") == "case"})
    for time_fs, grid_n, cone in keys:
        pair = [r for r in rows if r.get("row_type") == "case" and r["simulation_time_fs"] == time_fs and r["grid_n"] == grid_n and r["cone_deg"] == cone and r.get("status") == "ok"]
        if len(pair) != 2:
            continue
        ir = sum(float(r["IR_cone"]) for r in pair)
        il = sum(float(r["IL_cone"]) for r in pair)
        denom = ir + il
        out.append({"row_type": "incoherent_xy", "case_id": "INCOHERENT_XY", "orientation": "x+y", "simulation_time_fs": time_fs, "grid_n": grid_n, "cone_deg": cone, "IR_cone": ir, "IL_cone": il, "DoCP_RminusL": (ir - il) / denom if denom else float("nan"), "DoCP_LminusR": (il - ir) / denom if denom else float("nan"), "total_cone_power": denom, "status": "ok", "result_fsp": ";".join(r["result_fsp"] for r in pair), "note": "incoherent power sum only; no field coherence between x/y dipoles"})
    return out


def write_summary(out_dir: Path, rows: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    incoh = [r for r in rows if r.get("row_type") == "incoherent_xy" and r.get("status") == "ok"]
    t100_20 = [r for r in incoh if int(r["simulation_time_fs"]) == 100 and float(r["cone_deg"]) == 20.0]
    best_est = "not available"
    if t100_20:
        vals = [float(r["DoCP_RminusL"]) for r in t100_20]
        best_est = f"T100 +/-20 deg across available grids: min={min(vals):.6g}, max={max(vals):.6g}, mean={sum(vals)/len(vals):.6g}"
    lines = ["# CP +z Center-Dipole Sanity and Convergence Summary\n\n"]
    lines.append("## English\n")
    lines.append(f"- +z coordinate setup correct: {audit.get('audit_ok', False)}.\n")
    lines.append("- Ex/Ey are the transverse CP basis for +z extraction; this script uses R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).\n")
    lines.append("- Negative DoCP_RminusL means the L component is stronger under the current +z convention. Final handedness label still needs source-side / reciprocity plane-wave control.\n")
    lines.append(f"- Best current robust estimate for center x+y averaged DoCP: {best_est}.\n")
    lines.append("- Do not interpret these finite-patch dipole values as final absolute efficiency.\n")
    lines.append("\n## 中文\n")
    lines.append(f"- +z 坐标设置是否正确：{audit.get('audit_ok', False)}。\n")
    lines.append("- 对 +z 出射，Ex/Ey 是横向圆偏振基底；本脚本使用 R=(Ex-iEy)/sqrt(2)，L=(Ex+iEy)/sqrt(2)。\n")
    lines.append("- 负的 DoCP_RminusL 表示在当前 +z 约定下 L 分量更强。最终手性标签仍需源侧/互易 plane-wave control 校验。\n")
    lines.append(f"- 当前最稳健的中心 x+y 平均 DoCP 估计：{best_est}。\n")
    lines.append("- 这些有限阵列偶极结果不能当作最终绝对效率。\n")
    (out_dir / "cp_zprop_center_sanity_convergence_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    all_rows: list[dict[str, Any]] = []
    debug: dict[str, Any] = {"grid_cone_extraction": {}}
    for time_fs in args.time_fs:
        for grid_n in args.grid_sizes:
            for orientation in ["x", "y"]:
                fsp = fsp_path(out_dir, orientation, int(time_fs))
                rows, info = load_extract_case(lumapi, runtime, fsp, orientation, int(time_fs), int(grid_n), args.cone_deg, args.show_gui)
                all_rows.extend(rows)
                debug["grid_cone_extraction"][f"T{time_fs}_{orientation}_N{grid_n}"] = info
    all_rows = add_incoherent_rows(all_rows)
    write_csv(out_dir / "cp_zprop_grid_cone_convergence.csv", all_rows)
    existing: dict[str, Any] = {}
    if DEBUG_JSON.exists():
        try:
            existing = json.loads(DEBUG_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing.update(debug)
    DEBUG_JSON.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    audit = existing.get("static_audit", {})
    write_summary(out_dir, all_rows, audit)
    print(json.dumps({"rows": len(all_rows), "output": str(out_dir / "cp_zprop_grid_cone_convergence.csv")}, indent=2))
    return 0 if any(r.get("status") == "ok" for r in all_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
