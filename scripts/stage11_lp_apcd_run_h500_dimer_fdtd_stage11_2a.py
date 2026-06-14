from __future__ import annotations

import argparse
import cmath
import csv
import json
import math
import sys
import traceback
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi


OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_2a_h500_dimer_validation"
PLAN_CSV = OUT_DIR / "h500_dimer_validation_plan_stage11_2a.csv"
FDTD_DIR = OUT_DIR / "fdtd_h500_dimer_validation"
RESULT_CSV = OUT_DIR / "h500_dimer_fdtd_results_stage11_2a.csv"
SUMMARY_MD = OUT_DIR / "h500_dimer_fdtd_summary_stage11_2a.md"
EPS = 1e-12

SUMMARY_FIELDS = ["dimer_case_id", "polarization", "t_co", "t_cross", "transmission", "status", "fsp", "note"]
RESULT_FIELDS = [
    "dimer_case_id", "bin_deg", "source_pair_id", "j1_candidate_id", "j2_candidate_id", "height_nm",
    "placement_type", "geometry_legal", "fdtd_status",
    "t_xx_amp", "t_xx_phase_deg", "t_yx_amp", "t_yx_phase_deg", "t_xy_amp", "t_xy_phase_deg", "t_yy_amp", "t_yy_phase_deg",
    "target_x_power", "x_input_cross_leak_power", "y_input_total_leak_power", "polarization_purity_x",
    "dimer_selectivity_ratio", "dimer_output_phase_deg", "static_output_phase_deg", "dimer_vs_static_phase_error_deg",
    "static_predicted_ratio", "dimer_vs_static_ratio_drop", "dimer_pass_loose", "dimer_pass_strict",
    "x_result_csv", "y_result_csv", "x_fsp", "y_fsp", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def f(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def truth(value: bool) -> str:
    return "true" if value else "false"


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def wrap360(value: float) -> float:
    return value % 360.0


def complex_amp_phase(z: complex) -> tuple[str, str]:
    return fmt(abs(z)), fmt(wrap180(math.degrees(cmath.phase(z))) if abs(z) > EPS else math.nan)


def safe_transmission(fdtd: object) -> float:
    value = fdtd.transmission("T")
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (list, tuple)):
        value = value[0]
    return max(float(value), 0.0)


def center_value(fdtd: object, key: str) -> complex:
    value = fdtd.getdata("field_monitor", key)
    if hasattr(value, "squeeze"):
        value = value.squeeze()
    shape = getattr(value, "shape", ())
    if shape:
        cur = value
        for axis_size in [int(s) for s in shape if int(s) != 1]:
            cur = cur[axis_size // 2]
        value = cur
    return complex(value)


def normalized_components(fdtd: object) -> tuple[complex, complex, float]:
    ex = center_value(fdtd, "Ex")
    ey = center_value(fdtd, "Ey")
    total = safe_transmission(fdtd)
    norm = math.sqrt(abs(ex) ** 2 + abs(ey) ** 2)
    if norm <= EPS:
        return 0j, 0j, total
    scale = math.sqrt(total) / norm
    return ex * scale, ey * scale, total


def add_j1(fdtd: object, row: dict[str, str]) -> None:
    nm = 1e-9
    params = json.loads(row["j1_geometry_params"])
    shape = row["j1_shape_family"]
    if shape == "circle":
        fdtd.addcircle()
        fdtd.set("name", "j1_identity")
        fdtd.set("radius", 0.5 * f(params.get("diameter_nm")) * nm)
    else:
        fdtd.addrect()
        fdtd.set("name", "j1_identity")
        if shape == "square":
            side = f(params.get("side_nm"))
            fdtd.set("x span", side * nm)
            fdtd.set("y span", side * nm)
        else:
            fdtd.set("x span", f(params.get("length_nm")) * nm)
            fdtd.set("y span", f(params.get("width_nm")) * nm)
    fdtd.set("x", f(row["j1_center_x_nm"]) * nm)
    fdtd.set("y", f(row["j1_center_y_nm"]) * nm)
    fdtd.set("z min", 0)
    fdtd.set("z max", f(row["height_nm"]) * nm)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", 2.6)


def add_j2(fdtd: object, row: dict[str, str]) -> None:
    nm = 1e-9
    fdtd.addrect()
    fdtd.set("name", "j2_hwp")
    fdtd.set("x", f(row["j2_center_x_nm"]) * nm)
    fdtd.set("y", f(row["j2_center_y_nm"]) * nm)
    fdtd.set("x span", f(row["j2_length_nm"]) * nm)
    fdtd.set("y span", f(row["j2_width_nm"]) * nm)
    fdtd.set("z min", 0)
    fdtd.set("z max", f(row["height_nm"]) * nm)
    rot = f(row.get("j2_rotation_deg"), 0.0)
    if abs(rot) > 1e-9:
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", rot)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", 2.6)


def build_model(fdtd: object, row: dict[str, str], polarization: str) -> None:
    nm = 1e-9
    px = f(row["p_x_nm"]) * nm
    py = f(row["p_y_nm"]) * nm
    height = f(row["height_nm"]) * nm
    wavelength = f(row["lambda_nm"]) * nm
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z min", -500 * nm)
    fdtd.set("z max", height + 700 * nm)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", 2)
    fdtd.set("simulation time", 1000e-15)
    add_j1(fdtd, row)
    add_j2(fdtd, row)
    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", -250 * nm)
    fdtd.set("wavelength start", wavelength)
    fdtd.set("wavelength stop", wavelength)
    fdtd.set("polarization angle", 0 if polarization == "x" else 90)
    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", height + 350 * nm)
    fdtd.addprofile()
    fdtd.set("name", "field_monitor")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", height + 350 * nm)


def run_one(lumapi: object, runtime: object, row: dict[str, str], polarization: str) -> dict[str, object]:
    case_dir = FDTD_DIR / row["dimer_case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    fsp_path = case_dir / f"{row['dimer_case_id']}_{polarization}.fsp"
    summary_path = case_dir / f"{row['dimer_case_id']}_{polarization}_summary.csv"
    status = "error"
    note = ""
    co = cross = 0j
    total = math.nan
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        build_model(fdtd, row, polarization)
        fdtd.save(str(fsp_path))
        fdtd.close()
        fdtd = None
        fdtd = lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        fdtd.load(str(fsp_path))
        fdtd.run()
        tx, ty, total = normalized_components(fdtd)
        if polarization == "x":
            co, cross = tx, ty
        else:
            co, cross = ty, tx
        status = "ok"
    except Exception as exc:
        note = f"{type(exc).__name__}: {exc}\n{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    summary = {
        "dimer_case_id": row["dimer_case_id"],
        "polarization": polarization,
        "t_co": repr(co),
        "t_cross": repr(cross),
        "transmission": fmt(total),
        "status": status,
        "fsp": str(fsp_path),
        "note": note,
        "summary_path": str(summary_path),
    }
    write_csv(summary_path, [summary], SUMMARY_FIELDS)
    return summary


def combine(row: dict[str, str], x: dict[str, object], y: dict[str, object]) -> dict[str, object]:
    base = {k: row.get(k, "") for k in ["dimer_case_id", "bin_deg", "source_pair_id", "j1_candidate_id", "j2_candidate_id", "height_nm", "placement_type", "geometry_legal"]}
    if x["status"] != "ok" or y["status"] != "ok":
        return {
            **base,
            "fdtd_status": "failed",
            "x_result_csv": x.get("summary_path", ""),
            "y_result_csv": y.get("summary_path", ""),
            "x_fsp": x.get("fsp", ""),
            "y_fsp": y.get("fsp", ""),
            "notes": (str(x.get("note", "")) + "; " + str(y.get("note", "")))[:1000],
        }
    t_xx = complex(x["t_co"])
    t_yx = complex(x["t_cross"])
    t_yy = complex(y["t_co"])
    t_xy = complex(y["t_cross"])
    target_x_power = abs(t_xx) ** 2
    x_cross = abs(t_yx) ** 2
    y_total = abs(t_xy) ** 2 + abs(t_yy) ** 2
    purity = target_x_power / max(target_x_power + x_cross, EPS)
    selectivity = target_x_power / max(y_total, EPS)
    out_phase = wrap360(math.degrees(cmath.phase(t_xx))) if abs(t_xx) > EPS else math.nan
    static_phase = f(row["static_output_phase_deg"])
    phase_err = abs(wrap180(out_phase - static_phase))
    static_ratio = f(row["static_predicted_ratio"])
    ratio_drop = static_ratio / max(selectivity, EPS)
    loose = selectivity >= 3 and target_x_power >= 0.10 and purity >= 0.80 and phase_err <= 25
    strict = selectivity >= 6 and target_x_power >= 0.15 and purity >= 0.90 and phase_err <= 15
    t_xx_amp, t_xx_phase = complex_amp_phase(t_xx)
    t_yx_amp, t_yx_phase = complex_amp_phase(t_yx)
    t_xy_amp, t_xy_phase = complex_amp_phase(t_xy)
    t_yy_amp, t_yy_phase = complex_amp_phase(t_yy)
    return {
        **base,
        "fdtd_status": "ok",
        "t_xx_amp": t_xx_amp,
        "t_xx_phase_deg": t_xx_phase,
        "t_yx_amp": t_yx_amp,
        "t_yx_phase_deg": t_yx_phase,
        "t_xy_amp": t_xy_amp,
        "t_xy_phase_deg": t_xy_phase,
        "t_yy_amp": t_yy_amp,
        "t_yy_phase_deg": t_yy_phase,
        "target_x_power": fmt(target_x_power),
        "x_input_cross_leak_power": fmt(x_cross),
        "y_input_total_leak_power": fmt(y_total),
        "polarization_purity_x": fmt(purity),
        "dimer_selectivity_ratio": fmt(selectivity),
        "dimer_output_phase_deg": fmt(out_phase),
        "static_output_phase_deg": fmt(static_phase),
        "dimer_vs_static_phase_error_deg": fmt(phase_err),
        "static_predicted_ratio": fmt(static_ratio),
        "dimer_vs_static_ratio_drop": fmt(ratio_drop),
        "dimer_pass_loose": truth(loose),
        "dimer_pass_strict": truth(strict),
        "x_result_csv": x.get("summary_path", ""),
        "y_result_csv": y.get("summary_path", ""),
        "x_fsp": x.get("fsp", ""),
        "y_fsp": y.get("fsp", ""),
        "notes": "Stage11-2A H500 dimer validation; component-normalized center-field Jones estimate",
    }


def write_summary(rows: list[dict[str, object]], dry_run: bool) -> None:
    ok = [r for r in rows if r.get("fdtd_status") == "ok"]
    failed = [r for r in rows if r.get("fdtd_status") == "failed"]
    loose = [r for r in ok if r.get("dimer_pass_loose") == "true"]
    strict = [r for r in ok if r.get("dimer_pass_strict") == "true"]
    lines = [
        "# Stage11-2A H500 Dimer FDTD Summary",
        "",
        f"mode = {'dry_run_no_lumerical' if dry_run else 'real_h500_dimer_fdtd'}",
        f"result_count = {len(rows)}",
        f"success = {len(ok)}",
        f"failed = {len(failed)}",
        f"skipped = 0",
        f"dimer_pass_loose = {len(loose)}",
        f"dimer_pass_strict = {len(strict)}",
        "",
        "Evidence boundary: H500 dimer validation only. No K=6 full FDTD, no phase-gradient supercell, no H600/H700.",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default=str(PLAN_CSV))
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = [r for r in read_csv(Path(args.plan)) if r.get("geometry_legal") == "true"][: args.max_cases]
    print(f"selected_legal_dimer_count={len(rows)}")
    for row in rows[: min(12, len(rows))]:
        print(f"case={row['dimer_case_id']} bin={row['bin_deg']} placement={row['placement_type']} x/y")
    if args.dry_run:
        dry = [{**{k: r.get(k, "") for k in RESULT_FIELDS}, "fdtd_status": "dry_run"} for r in rows]
        write_summary(dry, dry_run=True)
        return 0
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    results: list[dict[str, object]] = []
    for row in rows:
        print(f"running={row['dimer_case_id']} x")
        x = run_one(lumapi, runtime, row, "x")
        print(f"running={row['dimer_case_id']} y")
        y = run_one(lumapi, runtime, row, "y")
        combined = combine(row, x, y)
        results.append(combined)
        write_csv(RESULT_CSV, results, RESULT_FIELDS)
        write_summary(results, dry_run=False)
        print(f"done={row['dimer_case_id']} status={combined['fdtd_status']}")
    print(f"result_csv={RESULT_CSV}")
    print(f"success={sum(1 for r in results if r['fdtd_status'] == 'ok')}")
    print(f"failed={sum(1 for r in results if r['fdtd_status'] == 'failed')}")
    print("skipped=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
