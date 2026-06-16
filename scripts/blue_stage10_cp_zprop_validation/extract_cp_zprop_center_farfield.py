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
POWER_MONITOR = "top_power_monitor_zprop"
COLLECTION_DEG = 20.0
FARFIELD_N = 31
CASES = [
    {"case_id": "CP_ZPROP_CENTER_X_T100FS", "orientation": "x"},
    {"case_id": "CP_ZPROP_CENTER_Y_T100FS", "orientation": "y"},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract +z CP far-field cone metrics from center x/y z-propagation FSP files.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
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
    try:
        arr = np.asarray(value)
        return {"shape": list(arr.shape), "dtype": str(arr.dtype), "is_complex": bool(np.iscomplexobj(arr)), "size": int(arr.size)}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def cone_mask(ux: np.ndarray, uy: np.ndarray, shape: tuple[int, ...], deg: float) -> np.ndarray | None:
    uxn = np.asarray(ux, dtype=float).squeeze()
    uyn = np.asarray(uy, dtype=float).squeeze()
    limit = math.sin(math.radians(deg))
    if uxn.ndim == 1 and uyn.ndim == 1:
        xx, yy = np.meshgrid(uxn, uyn, indexing="ij")
    else:
        xx, yy = np.broadcast_arrays(uxn, uyn)
    mask = (xx ** 2 + yy ** 2) <= limit ** 2
    try:
        return np.broadcast_to(mask, shape)
    except Exception:
        if mask.T.shape == shape:
            return mask.T
    return None


def extract_components(fdtd: object) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None, np.ndarray | None, np.ndarray | None, dict[str, Any]]:
    debug: dict[str, Any] = {}
    try:
        vec = fdtd.farfieldvector3d(FIELD_MONITOR, 1, FARFIELD_N, FARFIELD_N)
        debug["farfieldvector3d"] = {"ok": True, "info": array_info(vec)}
        arr = np.asarray(vec)
        if arr.shape[-1] >= 3:
            ex, ey, ez = arr[..., 0], arr[..., 1], arr[..., 2]
        elif arr.shape[0] >= 3:
            ex, ey, ez = arr[0, ...], arr[1, ...], arr[2, ...]
        else:
            raise ValueError(f"cannot infer vector component axis for shape {arr.shape}")
    except Exception as exc:
        debug["farfieldvector3d"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        ex = ey = ez = None
    try:
        ux = np.asarray(fdtd.farfieldux(FIELD_MONITOR, 1, FARFIELD_N, FARFIELD_N), dtype=float).squeeze()
        uy = np.asarray(fdtd.farfielduy(FIELD_MONITOR, 1, FARFIELD_N, FARFIELD_N), dtype=float).squeeze()
        debug["farfieldux"] = {"ok": True, "info": array_info(ux)}
        debug["farfielduy"] = {"ok": True, "info": array_info(uy)}
    except Exception as exc:
        debug["farfieldux_farfielduy"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        ux = uy = None
    for api_name in ["farfield3d", "farfieldpolar3d"]:
        try:
            val = getattr(fdtd, api_name)(FIELD_MONITOR, 1, FARFIELD_N, FARFIELD_N)
            debug[api_name] = {"ok": True, "info": array_info(val)}
        except Exception as exc:
            debug[api_name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return ex, ey, ez, ux, uy, debug


def cp_metrics(ex: np.ndarray, ey: np.ndarray, ux: np.ndarray | None, uy: np.ndarray | None) -> dict[str, Any]:
    er = (np.asarray(ex, dtype=np.complex128).squeeze() - 1j * np.asarray(ey, dtype=np.complex128).squeeze()) / math.sqrt(2.0)
    el = (np.asarray(ex, dtype=np.complex128).squeeze() + 1j * np.asarray(ey, dtype=np.complex128).squeeze()) / math.sqrt(2.0)
    mask = cone_mask(ux, uy, er.shape, COLLECTION_DEG) if ux is not None and uy is not None else None
    if mask is None:
        use = np.ones(er.shape, dtype=bool)
        note = "no cone mask available; integrated all samples"
    else:
        use = mask.astype(bool)
        note = "+/-20 deg cone mask from farfieldux/farfielduy"
    ir = float(np.sum(np.abs(er[use]) ** 2))
    il = float(np.sum(np.abs(el[use]) ** 2))
    denom = ir + il
    return {"IR_cone": ir, "IL_cone": il, "DoCP_RminusL": (ir - il) / denom if denom else float("nan"), "DoCP_LminusR": (il - ir) / denom if denom else float("nan"), "total_cone_power": denom, "integration_note": note}


def load_and_extract(lumapi: Any, runtime: Any, fsp_path: Path, show_gui: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp_path.resolve()))
        ex, ey, _ez, ux, uy, debug = extract_components(fdtd)
        if ex is None or ey is None:
            return {"status": "missing", "note": "farfieldvector3d did not return complex Ex/Ey components"}, debug
        m = cp_metrics(ex, ey, ux, uy)
        m.update({"status": "ok", "note": "+z CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)"})
        return m, debug
    except Exception as exc:
        return {"status": "failed", "note": f"{type(exc).__name__}: {exc}"}, {"exception": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def merge_debug(out_dir: Path, update: dict[str, Any]) -> dict[str, Any]:
    path = out_dir / "cp_zprop_center_debug.json"
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.update(update)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def write_summary(out_dir: Path, rows: list[dict[str, Any]], debug: dict[str, Any]) -> None:
    ok_rows = [r for r in rows if r.get("status") == "ok" and r.get("case_id") != "INCOHERENT_XY"]
    incoh = next((r for r in rows if r.get("case_id") == "INCOHERENT_XY"), None)
    fsp_files = [str(out_dir / "_saved_fsp" / f"{c['case_id']}.fsp") for c in CASES]
    ff_ok = bool(ok_rows) and all(debug.get("case_debug", {}).get(r["case_id"], {}).get("farfieldvector3d", {}).get("ok") for r in ok_rows)
    lines: list[str] = []
    lines.append("# Blue Stage10 CP +z Propagation Center Dipole Validation\n")
    lines.append("## English\n")
    lines.append("- Adapted old scripts: `scripts/stage10_cp_microled_center_dipole_time_convergence.py`, `scripts/stage10_cp_microled_uniform_patch_setup_only.py`, and `scripts/stage10_cp_microled_simplified_gan_clean_setup_only.py`.\n")
    lines.append("- Coordinate change: old +y model used x-z metasurface plane and y pillar height; this +z model uses x-y metasurface plane and z pillar height. Old local/array z coordinates are remapped to y, and pillar rotation axis is changed from y to z.\n")
    lines.append("- Metasurface plane: x-y. Height axis: z. Collection direction: +z.\n")
    lines.append("- Sources: center x-oriented and y-oriented electric dipoles at (x,y,z)=(0,0,-200) nm.\n")
    lines.append("- Monitor: 2D Z-normal top field/power monitors at z=1000 nm.\n")
    lines.append(f"- New FSP files generated/used: {fsp_files}.\n")
    lines.append(f"- farfieldvector3d worked: {ff_ok}.\n")
    for r in ok_rows:
        lines.append(f"- {r['orientation']} dipole +/-20 deg DoCP_RminusL: {r['DoCP_RminusL']}. IR={r['IR_cone']}, IL={r['IL_cone']}.\n")
    if incoh:
        lines.append(f"- Incoherent x+y +/-20 deg DoCP_RminusL: {incoh['DoCP_RminusL']}. IR={incoh['IR_cone']}, IL={incoh['IL_cone']}.\n")
    lines.append("- Next recommended step: inspect the +z outputs and, if the far-field method is stable, repeat only a short time-convergence check before any larger dipole-position sweep.\n")
    lines.append("\n## 中文\n")
    lines.append("- 改造来源脚本：`scripts/stage10_cp_microled_center_dipole_time_convergence.py`、`scripts/stage10_cp_microled_uniform_patch_setup_only.py`、`scripts/stage10_cp_microled_simplified_gan_clean_setup_only.py`。\n")
    lines.append("- 坐标变化：旧 +y 模型使用 x-z 超表面平面和 y 方向柱高；新 +z 模型使用 x-y 超表面平面和 z 方向柱高。旧局部/阵列 z 坐标映射为 y，柱子旋转轴从 y 改为 z。\n")
    lines.append("- 超表面平面为 x-y，柱高方向为 z，出射/提取方向为 +z。\n")
    lines.append("- 光源：中心 x 取向和 y 取向电偶极子，坐标 (x,y,z)=(0,0,-200) nm。\n")
    lines.append("- Monitor：顶部 2D Z-normal field/power monitor，z=1000 nm。\n")
    lines.append(f"- 已生成/使用的新 FSP 文件：{fsp_files}。\n")
    lines.append(f"- farfieldvector3d 是否成功：{ff_ok}。\n")
    for r in ok_rows:
        lines.append(f"- {r['orientation']} 偶极子的 +/-20 度 DoCP_RminusL：{r['DoCP_RminusL']}。IR={r['IR_cone']}，IL={r['IL_cone']}。\n")
    if incoh:
        lines.append(f"- x+y 非相干平均 +/-20 度 DoCP_RminusL：{incoh['DoCP_RminusL']}。IR={incoh['IR_cone']}，IL={incoh['IL_cone']}。\n")
    lines.append("- 下一步建议：先检查 +z 输出与远场提取是否稳定；若稳定，再做短时间收敛复核，不要直接进入更大位置扫描。\n")
    (out_dir / "cp_zprop_center_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    rows: list[dict[str, Any]] = []
    debug_update: dict[str, Any] = {"case_debug": {}}
    for case in CASES:
        fsp = out_dir / "_saved_fsp" / f"{case['case_id']}.fsp"
        if not fsp.exists():
            rows.append({"case_id": case["case_id"], "orientation": case["orientation"], "status": "missing", "IR_cone": "", "IL_cone": "", "DoCP_RminusL": "", "DoCP_LminusR": "", "total_cone_power": "", "integration_note": "", "note": f"missing FSP: {fsp}"})
            continue
        metrics, dbg = load_and_extract(lumapi, runtime, fsp, args.show_gui)
        debug_update["case_debug"][case["case_id"]] = dbg
        rows.append({"case_id": case["case_id"], "orientation": case["orientation"], "status": metrics.get("status", "unknown"), "IR_cone": metrics.get("IR_cone", ""), "IL_cone": metrics.get("IL_cone", ""), "DoCP_RminusL": metrics.get("DoCP_RminusL", ""), "DoCP_LminusR": metrics.get("DoCP_LminusR", ""), "total_cone_power": metrics.get("total_cone_power", ""), "integration_note": metrics.get("integration_note", ""), "note": metrics.get("note", "")})
    ok = [r for r in rows if r["status"] == "ok"]
    if len(ok) == 2:
        ir = sum(float(r["IR_cone"]) for r in ok)
        il = sum(float(r["IL_cone"]) for r in ok)
        denom = ir + il
        rows.append({"case_id": "INCOHERENT_XY", "orientation": "x+y_incoherent", "status": "ok", "IR_cone": ir, "IL_cone": il, "DoCP_RminusL": (ir - il) / denom if denom else float("nan"), "DoCP_LminusR": (il - ir) / denom if denom else float("nan"), "total_cone_power": denom, "integration_note": "+/-20 deg cone; unweighted x+y incoherent sum", "note": "IR_total=IR_x+IR_y; IL_total=IL_x+IL_y"})
    write_csv(out_dir / "cp_zprop_center_metrics.csv", rows)
    debug = merge_debug(out_dir, debug_update)
    write_summary(out_dir, rows, debug)
    print(json.dumps({"rows": rows}, indent=2))
    return 0 if len(ok) == 2 else 1

if __name__ == "__main__":
    raise SystemExit(main())

