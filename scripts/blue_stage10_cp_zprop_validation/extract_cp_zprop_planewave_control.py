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

OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation/planewave_control")
FIELD_MONITOR = "field_monitor"
POWER_MONITOR = "T"
CASES = [
    {"case_id": "EMPTY_XIN_ZPROP", "structure": "empty", "linear_input": "x"},
    {"case_id": "EMPTY_YIN_ZPROP", "structure": "empty", "linear_input": "y"},
    {"case_id": "DIMER_XIN_ZPROP", "structure": "frozen_dimer", "linear_input": "x"},
    {"case_id": "DIMER_YIN_ZPROP", "structure": "frozen_dimer", "linear_input": "y"},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract +z plane-wave CP control metrics from x/y FSPs.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--show-gui", action="store_true")
    return parser.parse_args()


def cstr(z: complex) -> str:
    return f"{z.real:.12g}{z.imag:+.12g}j"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def extract_mean_ex_ey(fdtd: object) -> tuple[complex, complex, dict[str, Any]]:
    result = fdtd.getresult(FIELD_MONITOR, "E")
    meta: dict[str, Any] = {"monitor": FIELD_MONITOR}
    if isinstance(result, dict):
        meta["keys"] = list(map(str, result.keys()))
        if "Ex" in result and "Ey" in result:
            ex = np.asarray(result["Ex"], dtype=np.complex128).squeeze()
            ey = np.asarray(result["Ey"], dtype=np.complex128).squeeze()
        elif "E" in result:
            arr = np.asarray(result["E"], dtype=np.complex128).squeeze()
            if arr.shape[-1] >= 2:
                ex, ey = arr[..., 0], arr[..., 1]
            elif arr.shape[0] >= 2:
                ex, ey = arr[0, ...], arr[1, ...]
            else:
                raise ValueError(f"Cannot infer Ex/Ey from E shape {arr.shape}")
        else:
            raise ValueError(f"E result has no Ex/Ey/E keys; keys={meta['keys']}")
    else:
        arr = np.asarray(result, dtype=np.complex128).squeeze()
        meta["result_type"] = str(type(result))
        if arr.shape[-1] >= 2:
            ex, ey = arr[..., 0], arr[..., 1]
        elif arr.shape[0] >= 2:
            ex, ey = arr[0, ...], arr[1, ...]
        else:
            raise ValueError(f"Cannot infer Ex/Ey from result shape {arr.shape}")
    meta["Ex_shape"] = list(np.asarray(ex).shape)
    meta["Ey_shape"] = list(np.asarray(ey).shape)
    return complex(np.mean(ex)), complex(np.mean(ey)), meta


def extract_case(lumapi: Any, runtime: Any, out_dir: Path, case: dict[str, Any], show_gui: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    fsp = out_dir / "_saved_fsp" / f"{case['case_id']}.fsp"
    if not fsp.exists():
        return {"case_id": case["case_id"], "structure": case["structure"], "linear_input": case["linear_input"], "status": "missing", "Ex_mean": "", "Ey_mean": "", "power_T": "", "result_fsp": str(fsp), "note": "missing FSP"}, {}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        ex, ey, meta = extract_mean_ex_ey(fdtd)
        power_t = ""
        try:
            t = fdtd.getresult(POWER_MONITOR, "T")
            if isinstance(t, dict):
                if "T" in t:
                    power_t = str(float(np.ravel(np.asarray(t["T"]))[0]))
            else:
                power_t = str(float(np.ravel(np.asarray(t))[0]))
        except Exception as exc:
            meta["power_T_error"] = f"{type(exc).__name__}: {exc}"
        return {"case_id": case["case_id"], "structure": case["structure"], "linear_input": case["linear_input"], "status": "ok", "Ex_mean": cstr(ex), "Ey_mean": cstr(ey), "power_T": power_t, "result_fsp": str(fsp), "note": "complex mean Ex/Ey extracted from transmitted field monitor"}, meta
    except Exception as exc:
        return {"case_id": case["case_id"], "structure": case["structure"], "linear_input": case["linear_input"], "status": "failed", "Ex_mean": "", "Ey_mean": "", "power_T": "", "result_fsp": str(fsp), "note": f"{type(exc).__name__}: {exc}"}, {}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def parse_complex(value: str) -> complex:
    return complex(value.replace("+-", "-"))


def cp_matrix_from_linear(j: np.ndarray) -> np.ndarray:
    s = math.sqrt(2.0)
    # rows R,L from linear output; columns R,L to linear input.
    a = np.array([[1 / s, -1j / s], [1 / s, 1j / s]], dtype=np.complex128)
    b = np.array([[1 / s, 1 / s], [1j / s, -1j / s]], dtype=np.complex128)
    return a @ j @ b


def build_structure_metrics(structure: str, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    xrow = next((r for r in rows if r["structure"] == structure and r["linear_input"] == "x" and r["status"] == "ok"), None)
    yrow = next((r for r in rows if r["structure"] == structure and r["linear_input"] == "y" and r["status"] == "ok"), None)
    if xrow is None or yrow is None:
        return [], {"status": "missing", "note": f"Need ok x/y rows for {structure}"}
    # J_linear rows are output x/y, columns are input x/y.
    j = np.array([[parse_complex(xrow["Ex_mean"]), parse_complex(yrow["Ex_mean"])], [parse_complex(xrow["Ey_mean"]), parse_complex(yrow["Ey_mean"])]], dtype=np.complex128)
    cp = cp_matrix_from_linear(j)
    labels = [("R", "R", cp[0, 0]), ("L", "R", cp[1, 0]), ("R", "L", cp[0, 1]), ("L", "L", cp[1, 1])]
    metrics: list[dict[str, Any]] = []
    # One row per input label with output powers.
    for input_label, col in [("R", 0), ("L", 1)]:
        tr = cp[0, col]
        tl = cp[1, col]
        ir = float(abs(tr) ** 2)
        il = float(abs(tl) ** 2)
        total = ir + il
        if ir >= il:
            dom = "R"
            ratio = ir / il if il else float("inf")
        else:
            dom = "L"
            ratio = il / ir if ir else float("inf")
        metrics.append({"structure": structure, "input_label": input_label, "IR_out": ir, "IL_out": il, "total_out": total, "DoCP_RminusL": (ir - il) / total if total else float("nan"), "DoCP_LminusR": (il - ir) / total if total else float("nan"), "dominant_output_label": dom, "conversion_ratio_dominant_to_opposite": ratio, "T_RR": cstr(cp[0, 0]), "T_LR": cstr(cp[1, 0]), "T_RL": cstr(cp[0, 1]), "T_LL": cstr(cp[1, 1]), "note": "T_output,input; CP basis from +z convention"})
    debug = {"status": "ok", "J_linear": [[cstr(v) for v in row] for row in j], "J_cp": [[cstr(v) for v in row] for row in cp], "power_table": {"R_in_to_R_out": float(abs(cp[0,0])**2), "R_in_to_L_out": float(abs(cp[1,0])**2), "L_in_to_R_out": float(abs(cp[0,1])**2), "L_in_to_L_out": float(abs(cp[1,1])**2)}}
    return metrics, debug


def write_summary(out_dir: Path, metrics: list[dict[str, Any]], debug: dict[str, Any]) -> None:
    empty_r = next((m for m in metrics if m["structure"] == "empty" and m["input_label"] == "R"), None)
    empty_l = next((m for m in metrics if m["structure"] == "empty" and m["input_label"] == "L"), None)
    dimer_rows = [m for m in metrics if m["structure"] == "frozen_dimer"]
    empty_pass = bool(empty_r and empty_l and empty_r["dominant_output_label"] == "R" and empty_l["dominant_output_label"] == "L")
    dimer_best = max(dimer_rows, key=lambda m: max(float(m["IR_out"]), float(m["IL_out"]))) if dimer_rows else None
    lines = ["# +z Plane-Wave CP Handedness Control\n\n"]
    lines.append("## English\n")
    lines.append(f"- Empty-cell handedness check passed: {empty_pass}.\n")
    if empty_r:
        lines.append(f"- Empty R input dominant output: {empty_r['dominant_output_label']}, DoCP_RminusL={empty_r['DoCP_RminusL']}.\n")
    if empty_l:
        lines.append(f"- Empty L input dominant output: {empty_l['dominant_output_label']}, DoCP_RminusL={empty_l['DoCP_RminusL']}.\n")
    if dimer_best:
        lines.append(f"- Frozen dimer strongest row: {dimer_best['input_label']} input -> {dimer_best['dominant_output_label']} output, dominant/opposite ratio={dimer_best['conversion_ratio_dominant_to_opposite']}.\n")
    lines.append("- Not a diffraction-order APCD steering claim: this is zero-order periodic unit-cell plane-wave convention control only.\n")
    lines.append("- Finite-patch dipole result should be labeled convention-calibrated according to the empty-cell result; if empty-cell passed, negative finite-patch DoCP_RminusL means L-output dominant under the current +z convention.\n")
    lines.append("- Next step: compare this plane-wave CP matrix with the finite-patch dipole sign, then decide whether a small 5-position x/y dipole sweep is warranted.\n")
    lines.append("\n## 中文\n")
    lines.append(f"- 空单元手性检查是否通过：{empty_pass}。\n")
    if empty_r:
        lines.append(f"- 空单元 R 输入主导输出：{empty_r['dominant_output_label']}，DoCP_RminusL={empty_r['DoCP_RminusL']}。\n")
    if empty_l:
        lines.append(f"- 空单元 L 输入主导输出：{empty_l['dominant_output_label']}，DoCP_RminusL={empty_l['DoCP_RminusL']}。\n")
    if dimer_best:
        lines.append(f"- Frozen dimer 最强通道：{dimer_best['input_label']} 输入 -> {dimer_best['dominant_output_label']} 输出，主导/相反通道比值={dimer_best['conversion_ratio_dominant_to_opposite']}。\n")
    lines.append("- 这不是衍射级次 APCD steering 结论；这里只是周期单元零级平面波约定校准。\n")
    lines.append("- 有限阵列偶极结果应根据空单元结果校准标签；若空单元通过，则负的 finite-patch DoCP_RminusL 表示当前 +z 约定下 L 输出占优。\n")
    lines.append("- 下一步建议：把这个 plane-wave CP 矩阵与 finite-patch dipole 符号对齐，再决定是否进入小规模 5-position x/y 偶极扫描。\n")
    (out_dir / "cp_zprop_planewave_control_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    case_rows: list[dict[str, Any]] = []
    case_debug: dict[str, Any] = {}
    for case in CASES:
        row, meta = extract_case(lumapi, runtime, out_dir, case, args.show_gui)
        case_rows.append(row)
        case_debug[case["case_id"]] = meta
    write_csv(out_dir / "cp_zprop_planewave_control_linear_fields.csv", case_rows)
    metrics: list[dict[str, Any]] = []
    matrix_debug: dict[str, Any] = {}
    for structure in ["empty", "frozen_dimer"]:
        m, dbg = build_structure_metrics(structure, case_rows)
        metrics.extend(m)
        matrix_debug[structure] = dbg
    write_csv(out_dir / "cp_zprop_planewave_control_metrics.csv", metrics)
    debug: dict[str, Any] = {}
    debug_path = out_dir / "cp_zprop_planewave_control_debug.json"
    if debug_path.exists():
        try:
            debug = json.loads(debug_path.read_text(encoding="utf-8"))
        except Exception:
            debug = {}
    debug.update({"field_extraction": case_debug, "matrix_debug": matrix_debug, "notation": "T_output,input; T_RL means L input to R output", "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)"})
    debug_path.write_text(json.dumps(debug, indent=2), encoding="utf-8")
    write_summary(out_dir, metrics, debug)
    print(json.dumps({"metrics": metrics}, indent=2))
    return 0 if metrics else 1


if __name__ == "__main__":
    raise SystemExit(main())
