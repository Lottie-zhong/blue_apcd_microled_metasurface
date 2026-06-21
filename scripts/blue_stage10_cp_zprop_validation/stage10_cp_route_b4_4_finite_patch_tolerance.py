from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

import stage10_cp_route_b2_finite_patch_xplus_test as b2
import stage10_cp_route_b4_3_tolerance_plane_wave_screen as b43

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "stage10_cp_route_b4_4_finite_patch_tolerance"
SAVED_FSP_ROOT = OUT_DIR / "_saved_fsp"
SETUP_FSP_DIR = OUT_DIR / "_setup_fsp"
NOMINAL_AVG_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b4_integer_finite_patch_xline" / "route_b4_integer_xline_position_averages.csv"
B43_METRICS_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b4_3_tolerance_plane_wave_screen" / "route_b4_3_tolerance_plane_wave_metrics.csv"

VARIANT_IDS = ["TOL_SIZE_ALL_P2", "TOL_J1_YP2", "TOL_J1_ROT_M1"]
VARIANTS = {case["case_id"]: case for case in b43.tolerance_cases() if case["case_id"] in VARIANT_IDS}
X_SOURCE = "route_b4_4_x_dipole_zprop"
Y_SOURCE = "route_b4_4_y_dipole_zprop"
GRID_N = 101
CONES_DEG = [5.0, 10.0, 20.0, 30.0]
ACTIVE_VARIANT: dict[str, Any] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage10 CP Route B4-4 finite-patch tolerance validation for three selected variants only.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--simulation-time-fs", type=float, default=b2.SIM_TIME_FS)
    parser.add_argument("--grid-n", type=int, default=GRID_N)
    parser.add_argument("--cone-deg", type=float, nargs="*", default=CONES_DEG)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def make_case(variant_id: str, position_id: str, orientation: str, x_nm: float) -> dict[str, Any]:
    return {
        "case_id": f"B4_4_{variant_id}_{position_id.upper()}_{orientation.upper()}_T100FS",
        "tolerance_variant": variant_id,
        "position_id": position_id,
        "orientation": orientation,
        "x_nm": x_nm,
        "y_nm": 0.0,
        "z_nm": b2.SOURCE_Z_NM,
        "enabled_source": X_SOURCE if orientation == "x" else Y_SOURCE,
        "disabled_source": Y_SOURCE if orientation == "x" else X_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 0.0 if orientation == "x" else 90.0,
    }


def manifest_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant_id in VARIANT_IDS:
        for position_id, x_nm in (("center", 0.0), ("x_plus_q", b2.Q_NM), ("x_minus_q", -b2.Q_NM)):
            for orientation in ("x", "y"):
                case = make_case(variant_id, position_id, orientation, x_nm)
                rows.append({
                    "case_id": case["case_id"], "tolerance_variant": variant_id,
                    "source_position": position_id, "dipole_orientation": orientation,
                    "source_x_nm": x_nm, "source_y_nm": 0.0, "source_z_nm": b2.SOURCE_Z_NM,
                    "grid_n": GRID_N, "cones_deg": ";".join(str(v) for v in CONES_DEG),
                    "expected_fsp": str(SAVED_FSP_ROOT / variant_id / f"{case['case_id']}.fsp"),
                    "run_enabled": "true", "note": "Stage10 CP Route B4-4 x-axis centerline only.",
                })
    return rows


CASES = [
    make_case(row["tolerance_variant"], row["source_position"], row["dipole_orientation"], float(row["source_x_nm"]))
    for row in manifest_rows()
]


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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def add_tolerance_patch(fdtd: object) -> list[dict[str, Any]]:
    if ACTIVE_VARIANT is None:
        raise RuntimeError("ACTIVE_VARIANT was not set before patch construction")
    variant_id = str(ACTIVE_VARIANT["case_id"])
    parent = f"CP_route_b4_4_{variant_id}_uniform_patch_7x3_group"
    inventory: list[dict[str, Any]] = []
    roles = [
        {"role": "J1", "x_nm": ACTIVE_VARIANT["J1_x_nm"], "y_nm": ACTIVE_VARIANT["J1_y_nm"], "length_nm": ACTIVE_VARIANT["J1_L_nm"], "width_nm": ACTIVE_VARIANT["J1_W_nm"], "rotation_deg": ACTIVE_VARIANT["J1_rotation_deg"]},
        {"role": "J2", "x_nm": ACTIVE_VARIANT["J2_x_nm"], "y_nm": ACTIVE_VARIANT["J2_y_nm"], "length_nm": ACTIVE_VARIANT["J2_L_nm"], "width_nm": ACTIVE_VARIANT["J2_W_nm"], "rotation_deg": ACTIVE_VARIANT["J2_rotation_deg"]},
    ]
    fdtd.addstructuregroup()
    fdtd.set("name", parent)
    fdtd.groupscope(f"::model::{parent}")
    for ix, x0 in zip(b2.IX_VALUES, b2.X_CENTERS_NM):
        for iy, y0 in zip(b2.IY_VALUES, b2.Y_CENTERS_NM):
            group = f"DIMER_ix{ix}_iy{iy}_{variant_id}"
            fdtd.addstructuregroup()
            fdtd.set("name", group)
            fdtd.groupscope(f"::model::{parent}::{group}")
            for role in roles:
                x_nm = x0 + float(role["x_nm"])
                y_nm = y0 + float(role["y_nm"])
                fdtd.addrect()
                fdtd.set("name", f"{role['role']}_pillar")
                fdtd.set("x", x_nm * b2.NM)
                fdtd.set("y", y_nm * b2.NM)
                fdtd.set("x span", float(role["length_nm"]) * b2.NM)
                fdtd.set("y span", float(role["width_nm"]) * b2.NM)
                fdtd.set("z min", 0.0)
                fdtd.set("z max", b2.HEIGHT_NM * b2.NM)
                fdtd.set("first axis", "z")
                fdtd.set("rotation 1", float(role["rotation_deg"]))
                fdtd.set("material", "<Object defined dielectric>")
                fdtd.set("index", b2.MATERIAL_INDEX)
                inventory.append({"variant": variant_id, "dimer_ix": ix, "dimer_iy": iy, "role": role["role"], "x_nm": x_nm, "y_nm": y_nm, "rotation_deg": role["rotation_deg"]})
            fdtd.groupscope(f"::model::{parent}")
    fdtd.groupscope("::model")
    return inventory


def patch_b2_globals(saved_dir: Path) -> None:
    b2.OUT_DIR = OUT_DIR
    b2.CANDIDATE_OUT = OUT_DIR
    b2.SAVED_FSP_DIR = saved_dir
    b2.X_SOURCE = X_SOURCE
    b2.Y_SOURCE = Y_SOURCE
    b2.add_uniform_patch = add_tolerance_patch


def build_setups(lumapi: Any, runtime: Any, args: argparse.Namespace) -> tuple[dict[str, Path], list[dict[str, Any]], list[str]]:
    global ACTIVE_VARIANT
    setups: dict[str, Path] = {}
    inventories: list[dict[str, Any]] = []
    warnings: list[str] = []
    for variant_id in VARIANT_IDS:
        ACTIVE_VARIANT = VARIANTS[variant_id]
        variant_saved = SAVED_FSP_ROOT / variant_id
        variant_saved.mkdir(parents=True, exist_ok=True)
        patch_b2_globals(variant_saved)
        setup_path = SETUP_FSP_DIR / f"{variant_id}_setup.fsp"
        fdtd = None
        try:
            fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
            setup_warnings, inventory = b2.build_setup(fdtd, args.simulation_time_fs)
            fdtd.save(str(setup_path.resolve()))
            warnings.extend(f"{variant_id}: {warning}" for warning in setup_warnings)
            inventories.extend(inventory)
            setups[variant_id] = setup_path
        finally:
            if fdtd is not None:
                try:
                    fdtd.close()
                except Exception:
                    pass
    ACTIVE_VARIANT = None
    return setups, inventories, warnings


def run_cases(lumapi: Any, runtime: Any, setups: dict[str, Path], args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in CASES:
        variant_id = str(case["tolerance_variant"])
        saved_dir = SAVED_FSP_ROOT / variant_id
        patch_b2_globals(saved_dir)
        if args.dry_run:
            rows.append({"case_id": case["case_id"], "tolerance_variant": variant_id, "source_position": case["position_id"], "dipole_orientation": case["orientation"], "fdtd_status": "not_run", "result_fsp": str(saved_dir / f"{case['case_id']}.fsp"), "note": "dry run"})
            continue
        result = b2.run_case(lumapi, runtime, setups[variant_id], case, args.simulation_time_fs, args.show_gui, args.force)
        result["tolerance_variant"] = variant_id
        result["source_position"] = result.pop("position_id")
        result["dipole_orientation"] = result.pop("orientation")
        rows.append(result)
    return rows


def extract_cases(lumapi: Any, runtime: Any, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    debug: list[dict[str, Any]] = []
    for case in CASES:
        variant_id = str(case["tolerance_variant"])
        patch_b2_globals(SAVED_FSP_ROOT / variant_id)
        extracted, info = b2.extract_case(lumapi, runtime, case, args.grid_n, args.cone_deg, args.show_gui)
        for row in extracted:
            rows.append({
                "case_id": row["case_id"], "tolerance_variant": variant_id,
                "source_position": row["position_id"], "dipole_orientation": row["orientation"],
                "source_x_nm": row["x_nm"], "source_y_nm": row["y_nm"], "source_z_nm": row["z_nm"],
                "cone_deg": row["cone_deg"], "grid_n": row["grid_n"],
                "cone_power_total": row.get("total_cone_power", ""),
                "cone_power_R": row.get("IR_cone", ""), "cone_power_L": row.get("IL_cone", ""),
                "DoCP_RminusL": row.get("DoCP_RminusL", ""), "L_fraction": row.get("L_fraction", ""), "R_fraction": row.get("R_fraction", ""),
                "extraction_status": row["extraction_status"],
                "E_components_used": "farfieldvector3d Ex/Ey for calibrated +z CP basis",
                "result_fsp": row["result_fsp"],
                "note": "B4-4 finite-patch tolerance; x/y dipoles remain separate at case level.",
            })
        info["tolerance_variant"] = variant_id
        debug.append(info)
    return rows, debug


def combined_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in case_rows if float(row["cone_deg"]) == 20.0]


def average_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    averages: list[dict[str, Any]] = []
    for variant_id in VARIANT_IDS:
        for position in ("center", "x_plus_q", "x_minus_q"):
            for cone in sorted({float(row["cone_deg"]) for row in case_rows}):
                pair = [row for row in case_rows if row["tolerance_variant"] == variant_id and row["source_position"] == position and float(row["cone_deg"]) == cone and row["extraction_status"] == "ok"]
                if {row["dipole_orientation"] for row in pair} != {"x", "y"}:
                    continue
                power_r = sum(float(row["cone_power_R"]) for row in pair)
                power_l = sum(float(row["cone_power_L"]) for row in pair)
                total = power_r + power_l
                averages.append({
                    "tolerance_variant": variant_id, "source_position": position, "cone_deg": cone,
                    "included_cases": ";".join(row["case_id"] for row in pair),
                    "avg_cone_power_total": total, "avg_cone_power_R": power_r, "avg_cone_power_L": power_l,
                    "avg_DoCP_RminusL": (power_r - power_l) / total if total else float("nan"),
                    "avg_L_fraction": power_l / total if total else float("nan"),
                    "avg_R_fraction": power_r / total if total else float("nan"),
                    "note": "Incoherent x/y power sum; no field addition.",
                })
    return averages


def nominal_map() -> dict[tuple[str, float], dict[str, str]]:
    position_map = {"x_plus_qp": "x_plus_q", "x_minus_qp": "x_minus_q", "center": "center"}
    return {(position_map[row["position_id"]], float(row["cone_deg"])): row for row in read_csv(NOMINAL_AVG_CSV)}


def comparison_rows(averages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nominal = nominal_map()
    rows: list[dict[str, Any]] = []
    for row in averages:
        if float(row["cone_deg"]) != 20.0:
            continue
        ref = nominal[(str(row["source_position"]), 20.0)]
        nominal_power = float(ref["P_total"])
        nominal_docp = float(ref["DoCP_RminusL"])
        nominal_l_fraction = float(ref["L_fraction"])
        power = float(row["avg_cone_power_total"])
        docp = float(row["avg_DoCP_RminusL"])
        l_fraction = float(row["avg_L_fraction"])
        power_ratio = power / nominal_power if nominal_power else float("nan")
        if math.copysign(1.0, docp) != math.copysign(1.0, nominal_docp):
            cp_label = "flipped"
        elif abs(docp) >= abs(nominal_docp):
            cp_label = "preserved_or_improved"
        else:
            cp_label = "degraded_but_same_handedness"
        power_label = "collapsed" if power_ratio < 0.25 else "reduced" if power_ratio < 1.0 else "preserved_or_increased"
        rows.append({
            "tolerance_variant": row["tolerance_variant"], "source_position": row["source_position"], "cone_deg": 20.0,
            "avg_cone_power_total": power, "avg_cone_power_R": row["avg_cone_power_R"], "avg_cone_power_L": row["avg_cone_power_L"],
            "avg_DoCP_RminusL": docp, "avg_L_fraction": l_fraction,
            "nominal_cone_power_total": nominal_power, "nominal_DoCP_RminusL": nominal_docp, "nominal_L_fraction": nominal_l_fraction,
            "relative_power_vs_nominal_same_position": power_ratio,
            "delta_DoCP_vs_nominal_same_position": docp - nominal_docp,
            "delta_L_fraction_vs_nominal_same_position": l_fraction - nominal_l_fraction,
            "cp_purity_interpretation": cp_label, "cone_power_interpretation": power_label,
            "size_p2_plane_wave_warning_reproduced": "yes" if row["tolerance_variant"] == "TOL_SIZE_ALL_P2" and l_fraction > 0.60 and power_ratio < 0.25 else "no",
            "note": "Collapsed uses the existing Stage10 operational power guard <0.25x nominal; no new pass/fail threshold introduced.",
        })
    return rows


def write_summary(comparison: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Stage10 CP Route B4-4 finite-patch tolerance validation\n\n",
        "## Scope and convention\n\n",
        "- Route B4-4 only; three tolerance variants: TOL_SIZE_ALL_P2, TOL_J1_YP2, TOL_J1_ROT_M1.\n",
        "- Nominal B4-2 finite-patch results were reused and not rerun.\n",
        "- Exactly 18 new finite-patch cases: three variants x center/+q/-q x x/y dipoles.\n",
        "- The actual B4-2 +z convention is R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2). Ex/Ez would be inconsistent with +z transverse fields and was not used.\n",
        "- x/y dipoles are combined incoherently by power addition only. Cone metrics below use +/-20 deg, grid101.\n",
        "- No new pass/fail threshold is introduced. CP labels compare sign and magnitude with nominal. Power labels use the existing Stage10 <0.25x catastrophic-power guard.\n\n",
        "## Nominal comparison\n\n",
        "| variant | position | DoCP | L fraction | power ratio | CP interpretation | power interpretation | plane-wave warning reproduced |\n",
        "|---|---|---:|---:|---:|---|---|---|\n",
    ]
    for row in comparison:
        lines.append(f"| {row['tolerance_variant']} | {row['source_position']} | {float(row['avg_DoCP_RminusL']):.6g} | {float(row['avg_L_fraction']):.6g} | {float(row['relative_power_vs_nominal_same_position']):.6g} | {row['cp_purity_interpretation']} | {row['cone_power_interpretation']} | {row['size_p2_plane_wave_warning_reproduced']} |\n")
    lines.extend([
        "\n## Interpretation\n\n",
        "- DoCP_RminusL < 0 means L-output dominant; DoCP_RminusL > 0 means R-output dominant.\n",
        "- TOL_SIZE_ALL_P2 is specifically checked for the B4-3 warning: CP handedness/purity may remain useful while usable cone power collapses.\n",
        "- This report does not modify or rerun the frozen nominal geometry.\n",
        f"- Completed/reused tolerance cases: {sum(row['fdtd_status'] in {'ok','reused'} for row in run_rows)}/18.\n",
    ])
    (OUT_DIR / "stage10_cp_route_b4_4_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SAVED_FSP_ROOT.mkdir(parents=True, exist_ok=True)
    SETUP_FSP_DIR.mkdir(parents=True, exist_ok=True)
    manifest = manifest_rows()
    write_csv(OUT_DIR / "stage10_cp_route_b4_4_manifest.csv", manifest)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    setups, inventory, setup_warnings = build_setups(lumapi, runtime, args)
    run_rows = run_cases(lumapi, runtime, setups, args)
    case_rows: list[dict[str, Any]] = []
    extract_debug: list[dict[str, Any]] = []
    if not args.dry_run:
        case_rows, extract_debug = extract_cases(lumapi, runtime, args)
    combined = combined_rows(case_rows) if case_rows else []
    averages = average_rows(case_rows) if case_rows else []
    comparison = comparison_rows(averages) if averages else []
    write_csv(OUT_DIR / "stage10_cp_route_b4_4_per_case.csv", case_rows)
    write_csv(OUT_DIR / "stage10_cp_route_b4_4_combined_summary.csv", combined)
    write_csv(OUT_DIR / "stage10_cp_route_b4_4_incoherent_averages.csv", averages)
    write_csv(OUT_DIR / "stage10_cp_route_b4_4_nominal_comparison.csv", comparison)
    if comparison:
        write_summary(comparison, run_rows)
    debug = {
        "route": "B4-4", "branch": "Stage10 CP J1/J2 only",
        "nominal_reused": True, "nominal_rerun": False, "nominal_source": str(NOMINAL_AVG_CSV),
        "selected_variants": VARIANT_IDS, "new_fdtd_cases_requested": 18,
        "actual_cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
        "convention_correction": "User text said Ex/Ez, but exact B4-2 +z extraction uses transverse Ex/Ey; B4-4 preserves B4-2.",
        "run_rows": run_rows, "extract_debug": extract_debug,
        "setup_warnings": setup_warnings, "patch_inventory_count": len(inventory),
        "no_new_arbitrary_pass_fail_threshold": True,
        "power_collapse_guard_source": "Existing Stage10 B4-2 operational guard: power ratio <0.25",
    }
    (OUT_DIR / "stage10_cp_route_b4_4_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    print(json.dumps({"run_rows": run_rows, "combined_summary": combined, "incoherent_averages": averages, "nominal_comparison": comparison}, indent=2))
    failed_runs = [row for row in run_rows if row["fdtd_status"] not in {"ok", "reused", "not_run"}]
    failed_extract = [row for row in extract_debug if row.get("status") != "ok"]
    return 1 if failed_runs or failed_extract else 0


if __name__ == "__main__":
    raise SystemExit(main())
