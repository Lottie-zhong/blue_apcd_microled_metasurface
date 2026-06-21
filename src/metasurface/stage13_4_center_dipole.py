from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from metasurface.stage13_lp_dipole import CANDIDATE_ID, flt, read_csv_rows


NM = 1e-9
OUTPUT_DIR_NAME = "stage13_4_lp_no_dbr_center_dipole"
PATCH_OPTION_ID = "A_small"
NX = 3
NY = 19
EXPECTED_DIMERS = 342
EXPECTED_NANOPILLARS = 684
CASES = [
    {"case_id": "center_x", "orientation": "x", "theta_deg": 90.0, "phi_deg": 0.0},
    {"case_id": "center_y", "orientation": "y", "theta_deg": 90.0, "phi_deg": 90.0},
]
ALLOWED_CASE_IDS = [case["case_id"] for case in CASES]
CONES_DEG = [5.0, 10.0, 20.0]
FIELD_MONITOR = "stage13_4_top_complex_field"
POWER_MONITOR = "stage13_4_top_power"
X_SOURCE = "stage13_4_center_x_dipole"
Y_SOURCE = "stage13_4_center_y_dipole"
MATERIAL_INDEX = 2.6
LATERAL_PML_MARGIN_NM = 700.0
MONITOR_EDGE_MARGIN_NM = 100.0
FDTD_Z_MIN_NM = -900.0
FDTD_Z_MAX_NM = 1800.0
MONITOR_Z_NM = 1000.0
MESH_ACCURACY = 2
SOLVER_PROCESSES = 4

CASE_METRIC_FIELDS = [
    "case_id",
    "candidate_id",
    "patch_option_id",
    "position",
    "dipole_orientation",
    "cone_deg",
    "target_LP_power",
    "leakage_LP_power",
    "LP_fraction",
    "target_to_leakage_ratio",
    "total_cone_power",
    "farfield_grid",
    "source_x_nm",
    "source_y_nm",
    "source_z_nm",
    "simulation_time_fs",
    "result_csv",
    "fsp_path",
    "extraction_status",
    "runtime_minutes",
    "status",
    "notes",
]

INCOHERENT_FIELDS = [
    "candidate_id",
    "position",
    "cone_deg",
    "target_LP_power_xdip",
    "target_LP_power_ydip",
    "leakage_LP_power_xdip",
    "leakage_LP_power_ydip",
    "target_LP_power_incoherent",
    "leakage_LP_power_incoherent",
    "LP_fraction_incoherent",
    "target_to_leakage_ratio_incoherent",
    "total_cone_power_incoherent",
    "pass_center_lp_fraction_gt_0p60",
    "notes",
]


def write_csv_rows(path: Path, rows: Iterable[dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_case_selection(case_ids: Sequence[str]) -> None:
    if list(case_ids) != ALLOWED_CASE_IDS:
        raise ValueError(f"Stage13-4 requires exact ordered cases {ALLOWED_CASE_IDS}; got {list(case_ids)}")


def load_approved_plan(config_json: Path, cases_csv: Path, layout_csv: Path) -> dict[str, object]:
    if not config_json.is_file():
        raise FileNotFoundError(f"approved Stage13-3 config missing: {config_json}")
    config = json.loads(config_json.read_text(encoding="utf-8"))
    case_rows = read_csv_rows(cases_csv)
    layout_rows = read_csv_rows(layout_csv)
    if config.get("finite_patch") != PATCH_OPTION_ID:
        raise ValueError("Stage13-4 requires approved A_small patch")
    replication = config.get("manual_approvals", {}).get("finite_patch", {}).get("replication", {})
    geometry = config.get("manual_approvals", {}).get("finite_patch", {}).get("estimated_geometry", {})
    if replication != {"N_supercells_x": NX, "N_supercells_y": NY}:
        raise ValueError(f"approved patch replication changed: {replication}")
    if geometry != {"dimers": EXPECTED_DIMERS, "nanopillars": EXPECTED_NANOPILLARS}:
        raise ValueError(f"approved geometry count changed: {geometry}")
    if config.get("device_options") != {"DBR": "off", "RCLED": "off"}:
        raise ValueError("Stage13-4 requires DBR=off and RCLED=off")
    if config.get("next_fdtd_case_ids") != ALLOWED_CASE_IDS:
        raise ValueError(f"approved next cases changed: {config.get('next_fdtd_case_ids')}")
    if len(layout_rows) != 6:
        raise ValueError(f"frozen Stage12 K=6 layout must have six dimers; got {len(layout_rows)}")
    selected_case_rows = [row for row in case_rows if row.get("case_id") in ALLOWED_CASE_IDS]
    if [row.get("case_id") for row in selected_case_rows] != ALLOWED_CASE_IDS:
        raise ValueError("approved center_x/center_y case rows are missing or out of order")
    for row in selected_case_rows:
        if any(abs(flt(row.get(key)) - expected) > 1e-9 for key, expected in (("source_x_nm", 0.0), ("source_y_nm", 0.0), ("source_z_nm", -200.0))):
            raise ValueError(f"approved source coordinates changed for {row.get('case_id')}: {row}")
    first = layout_rows[0]
    wavelength_nm = flt(first.get("lambda_nm"))
    height_nm = flt(first.get("height_nm"))
    period_x_nm = flt(first.get("supercell_period_lambda_nm"))
    period_y_nm = flt(first.get("p_y_nm"))
    if any(math.isnan(value) for value in (wavelength_nm, height_nm, period_x_nm, period_y_nm)):
        raise ValueError("frozen Stage12 wavelength/height/period metadata is incomplete")
    if any(abs(flt(row.get("supercell_period_lambda_nm")) - period_x_nm) > 1e-6 for row in layout_rows):
        raise ValueError("inconsistent Stage12 x supercell period")
    if any(abs(flt(row.get("p_y_nm")) - period_y_nm) > 1e-6 for row in layout_rows):
        raise ValueError("inconsistent Stage12 y pitch")
    plan = {
        "candidate_id": CANDIDATE_ID,
        "patch_option_id": PATCH_OPTION_ID,
        "Nx": NX,
        "Ny": NY,
        "estimated_dimers": EXPECTED_DIMERS,
        "estimated_nanopillars": EXPECTED_NANOPILLARS,
        "wavelength_nm": wavelength_nm,
        "height_nm": height_nm,
        "period_x_nm": period_x_nm,
        "period_y_nm": period_y_nm,
        "source_x_nm": 0.0,
        "source_y_nm": 0.0,
        "source_z_nm": -200.0,
        "source_z_status": "diagnostic_manual_placeholder",
        "source_z_reference": "Stage12 pillar-base plane z=0 nm",
        "farfield_grid": int(config.get("farfield_grid", 101)),
        "simulation_time_fs": float(config.get("simulation_time_fs", 100.0)),
        "cone_deg_list": [float(value) for value in config.get("cone_deg_list", CONES_DEG)],
        "DBR": False,
        "RCLED": False,
        "background_stack": "default background only; no substrate/device-stack object",
        "layout_rows": layout_rows,
        "selected_cases": ALLOWED_CASE_IDS,
        "config_sha256": sha256_file(config_json),
        "cases_sha256": sha256_file(cases_csv),
        "layout_sha256": sha256_file(layout_csv),
    }
    if plan["farfield_grid"] != 101 or plan["simulation_time_fs"] != 100.0 or plan["cone_deg_list"] != CONES_DEG:
        raise ValueError("Stage13-4 grid/time/cone defaults differ from the approved values")
    return plan


def _j1_shape(row: dict[str, str]) -> tuple[str, float, float, float]:
    params = json.loads(row.get("j1_geometry_params") or "{}")
    family = row.get("j1_shape_family", "")
    rotation = flt(params.get("rotation_deg"), 0.0)
    if family == "circle":
        diameter = flt(params.get("diameter_nm"))
        return "circle", diameter, diameter, rotation
    if family == "square":
        side = flt(params.get("side_nm"))
        return "rect", side, side, rotation
    return "rect", flt(params.get("length_nm")), flt(params.get("width_nm")), rotation


def build_patch_inventory(plan: dict[str, object]) -> list[dict[str, object]]:
    period_x = float(plan["period_x_nm"])
    period_y = float(plan["period_y_nm"])
    center_shift = period_x / 2.0
    rows = plan["layout_rows"]
    inventory: list[dict[str, object]] = []
    for tile_x in range(-(NX // 2), NX // 2 + 1):
        for tile_y in range(-(NY // 2), NY // 2 + 1):
            for row in rows:
                dimer_index = int(flt(row.get("supercell_index")))
                j1_type, j1_w, j1_h, j1_rotation = _j1_shape(row)
                inventory.append(
                    {
                        "name": f"lp_tx{tile_x}_ty{tile_y}_d{dimer_index}_j1",
                        "role": "J1",
                        "shape": j1_type,
                        "x_nm": flt(row.get("j1_abs_center_x_nm")) - center_shift + tile_x * period_x,
                        "y_nm": flt(row.get("j1_abs_center_y_nm")) + tile_y * period_y,
                        "width_x_nm": j1_w,
                        "width_y_nm": j1_h,
                        "rotation_deg": j1_rotation,
                        "height_nm": flt(row.get("height_nm")),
                        "tile_x": tile_x,
                        "tile_y": tile_y,
                        "dimer_index": dimer_index,
                        "phase_bin_deg": int(flt(row.get("phase_bin_deg"))),
                        "candidate_id": row.get("candidate_id", ""),
                    }
                )
                inventory.append(
                    {
                        "name": f"lp_tx{tile_x}_ty{tile_y}_d{dimer_index}_j2",
                        "role": "J2",
                        "shape": "rect",
                        "x_nm": flt(row.get("j2_abs_center_x_nm")) - center_shift + tile_x * period_x,
                        "y_nm": flt(row.get("j2_abs_center_y_nm")) + tile_y * period_y,
                        "width_x_nm": flt(row.get("j2_length_nm")),
                        "width_y_nm": flt(row.get("j2_width_nm")),
                        "rotation_deg": flt(row.get("j2_rotation_deg"), 0.0),
                        "height_nm": flt(row.get("height_nm")),
                        "tile_x": tile_x,
                        "tile_y": tile_y,
                        "dimer_index": dimer_index,
                        "phase_bin_deg": int(flt(row.get("phase_bin_deg"))),
                        "candidate_id": row.get("candidate_id", ""),
                    }
                )
    if len(inventory) != EXPECTED_NANOPILLARS:
        raise ValueError(f"resolved patch has {len(inventory)} nanopillars; expected {EXPECTED_NANOPILLARS}")
    return inventory


def geometry_bounds(inventory: Sequence[dict[str, object]]) -> dict[str, float]:
    return {
        "x_min_nm": min(float(item["x_nm"]) - float(item["width_x_nm"]) / 2.0 for item in inventory),
        "x_max_nm": max(float(item["x_nm"]) + float(item["width_x_nm"]) / 2.0 for item in inventory),
        "y_min_nm": min(float(item["y_nm"]) - float(item["width_y_nm"]) / 2.0 for item in inventory),
        "y_max_nm": max(float(item["y_nm"]) + float(item["width_y_nm"]) / 2.0 for item in inventory),
    }


def resolved_setup(plan: dict[str, object], inventory: Sequence[dict[str, object]]) -> dict[str, object]:
    bounds = geometry_bounds(inventory)
    max_abs_x = max(abs(bounds["x_min_nm"]), abs(bounds["x_max_nm"]))
    max_abs_y = max(abs(bounds["y_min_nm"]), abs(bounds["y_max_nm"]))
    return {
        **{key: plan[key] for key in ("candidate_id", "patch_option_id", "Nx", "Ny", "estimated_dimers", "estimated_nanopillars", "wavelength_nm", "height_nm", "source_x_nm", "source_y_nm", "source_z_nm", "source_z_status", "source_z_reference", "farfield_grid", "simulation_time_fs", "cone_deg_list", "DBR", "RCLED", "background_stack", "selected_cases")},
        "propagation_direction": "+z",
        "monitor_direction": "+z",
        "target_LP": "x",
        "leakage_LP": "y",
        "geometry_bounds_nm": bounds,
        "lateral_pml_margin_nm": LATERAL_PML_MARGIN_NM,
        "monitor_edge_margin_nm": MONITOR_EDGE_MARGIN_NM,
        "fdtd_x_span_nm": 2.0 * (max_abs_x + LATERAL_PML_MARGIN_NM),
        "fdtd_y_span_nm": 2.0 * (max_abs_y + LATERAL_PML_MARGIN_NM),
        "fdtd_z_min_nm": FDTD_Z_MIN_NM,
        "fdtd_z_max_nm": FDTD_Z_MAX_NM,
        "monitor_x_span_nm": 2.0 * (max_abs_x + MONITOR_EDGE_MARGIN_NM),
        "monitor_y_span_nm": 2.0 * (max_abs_y + MONITOR_EDGE_MARGIN_NM),
        "monitor_z_nm": MONITOR_Z_NM,
        "mesh_accuracy": MESH_ACCURACY,
        "solver_processes": SOLVER_PROCESSES,
        "Ez_handling": "excluded from x/y LP projection; included only in total_cone_power",
        "angular_integration": "solid-angle weighted integration on farfieldux/farfielduy grid",
    }


def add_patch(fdtd: object, inventory: Sequence[dict[str, object]]) -> None:
    for item in inventory:
        if item["shape"] == "circle":
            fdtd.addcircle()
            fdtd.set("radius", float(item["width_x_nm"]) * NM / 2.0)
        else:
            fdtd.addrect()
            fdtd.set("x span", float(item["width_x_nm"]) * NM)
            fdtd.set("y span", float(item["width_y_nm"]) * NM)
        fdtd.set("name", str(item["name"]))
        fdtd.set("x", float(item["x_nm"]) * NM)
        fdtd.set("y", float(item["y_nm"]) * NM)
        fdtd.set("z min", 0)
        fdtd.set("z max", float(item["height_nm"]) * NM)
        rotation = float(item["rotation_deg"])
        if abs(rotation) > 1e-12:
            fdtd.set("first axis", "z")
            fdtd.set("rotation 1", rotation)
        fdtd.set("material", "<Object defined dielectric>")
        fdtd.set("index", MATERIAL_INDEX)


def add_dipoles(fdtd: object, setup: dict[str, object]) -> None:
    for name, theta, phi in ((X_SOURCE, 90.0, 0.0), (Y_SOURCE, 90.0, 90.0)):
        fdtd.adddipole()
        fdtd.set("name", name)
        fdtd.set("x", float(setup["source_x_nm"]) * NM)
        fdtd.set("y", float(setup["source_y_nm"]) * NM)
        fdtd.set("z", float(setup["source_z_nm"]) * NM)
        fdtd.set("wavelength start", float(setup["wavelength_nm"]) * NM)
        fdtd.set("wavelength stop", float(setup["wavelength_nm"]) * NM)
        fdtd.set("theta", theta)
        fdtd.set("phi", phi)
        fdtd.set("enabled", 0)


def add_monitors(fdtd: object, setup: dict[str, object]) -> None:
    for add, name in ((fdtd.addprofile, FIELD_MONITOR), (fdtd.addpower, POWER_MONITOR)):
        add()
        fdtd.set("name", name)
        fdtd.set("monitor type", "2D Z-normal")
        fdtd.set("x", 0)
        fdtd.set("y", 0)
        fdtd.set("x span", float(setup["monitor_x_span_nm"]) * NM)
        fdtd.set("y span", float(setup["monitor_y_span_nm"]) * NM)
        fdtd.set("z", float(setup["monitor_z_nm"]) * NM)


def build_setup(fdtd: object, setup: dict[str, object], inventory: Sequence[dict[str, object]]) -> None:
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x", 0)
    fdtd.set("y", 0)
    fdtd.set("x span", float(setup["fdtd_x_span_nm"]) * NM)
    fdtd.set("y span", float(setup["fdtd_y_span_nm"]) * NM)
    fdtd.set("z min", float(setup["fdtd_z_min_nm"]) * NM)
    fdtd.set("z max", float(setup["fdtd_z_max_nm"]) * NM)
    for prop in ("x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"):
        fdtd.set(prop, "PML")
    fdtd.set("mesh accuracy", int(setup["mesh_accuracy"]))
    fdtd.set("simulation time", float(setup["simulation_time_fs"]) * 1e-15)
    add_patch(fdtd, inventory)
    add_dipoles(fdtd, setup)
    add_monitors(fdtd, setup)


def configure_case(fdtd: object, case_id: str, setup: dict[str, object]) -> None:
    case = next(case for case in CASES if case["case_id"] == case_id)
    fdtd.select("FDTD")
    fdtd.set("simulation time", float(setup["simulation_time_fs"]) * 1e-15)
    enabled_source = X_SOURCE if case_id == "center_x" else Y_SOURCE
    disabled_source = Y_SOURCE if case_id == "center_x" else X_SOURCE
    for name, enabled in ((enabled_source, 1), (disabled_source, 0)):
        fdtd.select(name)
        fdtd.set("enabled", enabled)
        fdtd.set("x", float(setup["source_x_nm"]) * NM)
        fdtd.set("y", float(setup["source_y_nm"]) * NM)
        fdtd.set("z", float(setup["source_z_nm"]) * NM)
    fdtd.select(enabled_source)
    fdtd.set("theta", case["theta_deg"])
    fdtd.set("phi", case["phi_deg"])


def preflight_case(fdtd: object, case_id: str, setup: dict[str, object]) -> list[str]:
    errors: list[str] = []
    enabled_source = X_SOURCE if case_id == "center_x" else Y_SOURCE
    disabled_source = Y_SOURCE if case_id == "center_x" else X_SOURCE
    for name in ("FDTD", enabled_source, disabled_source, FIELD_MONITOR, POWER_MONITOR):
        try:
            fdtd.select(name)
        except Exception as exc:
            errors.append(f"missing object {name}: {type(exc).__name__}: {exc}")
    for name, expected in ((enabled_source, 1), (disabled_source, 0)):
        try:
            actual = int(round(float(fdtd.getnamed(name, "enabled"))))
            if actual != expected:
                errors.append(f"{name} enabled={actual}; expected {expected}")
        except Exception as exc:
            errors.append(f"cannot read {name}.enabled: {type(exc).__name__}: {exc}")
    for prop in ("x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"):
        try:
            actual = str(fdtd.getnamed("FDTD", prop)).strip().upper()
            if actual != "PML":
                errors.append(f"FDTD {prop}={actual}; expected PML")
        except Exception as exc:
            errors.append(f"cannot read FDTD {prop}: {type(exc).__name__}: {exc}")
    for forbidden in ("DBR", "RCLED"):
        try:
            count = int(round(float(fdtd.getnamednumber(forbidden))))
            if count:
                errors.append(f"forbidden object name {forbidden} exists count={count}")
        except Exception:
            pass
    return errors


def _component_arrays(vector: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    arr = np.asarray(vector).squeeze()
    if arr.ndim < 3:
        raise ValueError(f"farfieldvector3d returned insufficient shape {arr.shape}")
    if arr.shape[-1] == 3:
        ex, ey, ez = arr[..., 0], arr[..., 1], arr[..., 2]
        axis = -1
    elif arr.shape[0] == 3:
        ex, ey, ez = arr[0, ...], arr[1, ...], arr[2, ...]
        axis = 0
    else:
        raise ValueError(f"cannot infer Ex/Ey/Ez component axis from shape {arr.shape}")
    if not np.iscomplexobj(arr):
        raise ValueError("farfieldvector3d did not return complex vector data")
    return (
        np.asarray(ex, dtype=np.complex128).squeeze(),
        np.asarray(ey, dtype=np.complex128).squeeze(),
        np.asarray(ez, dtype=np.complex128).squeeze(),
        {"shape": list(arr.shape), "dtype": str(arr.dtype), "is_complex": True, "component_axis": axis},
    )


def _direction_grid(ux: Any, uy: Any, shape: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    uxa = np.asarray(ux, dtype=float).squeeze()
    uya = np.asarray(uy, dtype=float).squeeze()
    if uxa.ndim == 1 and uya.ndim == 1:
        xx, yy = np.meshgrid(uxa, uya, indexing="ij")
    else:
        xx, yy = np.broadcast_arrays(uxa, uya)
    if xx.shape == shape:
        return xx, yy
    if xx.T.shape == shape:
        return xx.T, yy.T
    raise ValueError(f"direction grid shape {xx.shape} cannot align with field shape {shape}")


def _solid_angle_weights(xx: np.ndarray, yy: np.ndarray) -> np.ndarray:
    ux_values = np.unique(xx)
    uy_values = np.unique(yy)
    dux = float(np.median(np.abs(np.diff(ux_values)))) if ux_values.size > 1 else 1.0
    duy = float(np.median(np.abs(np.diff(uy_values)))) if uy_values.size > 1 else 1.0
    uz = np.sqrt(np.clip(1.0 - xx**2 - yy**2, 1e-12, None))
    return dux * duy / uz


def lp_metrics_from_fields(
    ex: np.ndarray,
    ey: np.ndarray,
    ez: np.ndarray,
    ux: Any,
    uy: Any,
    cones: Sequence[float],
) -> list[dict[str, float]]:
    if ex.shape != ey.shape or ex.shape != ez.shape:
        raise ValueError(f"component shape mismatch: Ex={ex.shape}, Ey={ey.shape}, Ez={ez.shape}")
    xx, yy = _direction_grid(ux, uy, ex.shape)
    weights = _solid_angle_weights(xx, yy)
    ix = np.abs(ex) ** 2
    iy = np.abs(ey) ** 2
    iz = np.abs(ez) ** 2
    rows: list[dict[str, float]] = []
    for cone in cones:
        mask = (xx**2 + yy**2) <= math.sin(math.radians(float(cone))) ** 2
        if not np.any(mask):
            raise ValueError(f"empty far-field mask for +/-{cone} deg cone")
        target = float(np.sum(ix[mask] * weights[mask]))
        leakage = float(np.sum(iy[mask] * weights[mask]))
        ez_power = float(np.sum(iz[mask] * weights[mask]))
        lp_denom = target + leakage
        rows.append(
            {
                "cone_deg": float(cone),
                "target_LP_power": target,
                "leakage_LP_power": leakage,
                "LP_fraction": target / lp_denom if lp_denom else float("nan"),
                "target_to_leakage_ratio": target / leakage if leakage else float("inf"),
                "total_cone_power": target + leakage + ez_power,
                "Ez_cone_power": ez_power,
            }
        )
    return rows


def extract_from_session(fdtd: object, setup: dict[str, object]) -> tuple[list[dict[str, float]], dict[str, object]]:
    grid = int(setup["farfield_grid"])
    debug: dict[str, object] = {"api": "farfieldvector3d + farfieldux + farfielduy"}
    vector = fdtd.farfieldvector3d(FIELD_MONITOR, 1, grid, grid)
    ex, ey, ez, vector_info = _component_arrays(vector)
    ux = fdtd.farfieldux(FIELD_MONITOR, 1, grid, grid)
    uy = fdtd.farfielduy(FIELD_MONITOR, 1, grid, grid)
    debug.update(
        {
            "farfieldvector3d": vector_info,
            "farfieldux_shape": list(np.asarray(ux).shape),
            "farfielduy_shape": list(np.asarray(uy).shape),
            "raw_arrays_saved": False,
            "Ez_handling": setup["Ez_handling"],
            "integration": setup["angular_integration"],
        }
    )
    return lp_metrics_from_fields(ex, ey, ez, ux, uy, setup["cone_deg_list"]), debug


def _failure_rows(case_id: str, setup: dict[str, object], fsp_path: Path, runtime_minutes: float, status: str, extraction_status: str, note: str, output_dir: Path) -> list[dict[str, object]]:
    orientation = next(case["orientation"] for case in CASES if case["case_id"] == case_id)
    return [
        {
            "case_id": case_id,
            "candidate_id": CANDIDATE_ID,
            "patch_option_id": PATCH_OPTION_ID,
            "position": "center",
            "dipole_orientation": orientation,
            "cone_deg": cone,
            "target_LP_power": "",
            "leakage_LP_power": "",
            "LP_fraction": "",
            "target_to_leakage_ratio": "",
            "total_cone_power": "",
            "farfield_grid": setup["farfield_grid"],
            "source_x_nm": setup["source_x_nm"],
            "source_y_nm": setup["source_y_nm"],
            "source_z_nm": setup["source_z_nm"],
            "simulation_time_fs": setup["simulation_time_fs"],
            "result_csv": str(output_dir / "stage13_4_case_metrics.csv"),
            "fsp_path": str(fsp_path),
            "extraction_status": extraction_status,
            "runtime_minutes": runtime_minutes,
            "status": status,
            "notes": note,
        }
        for cone in setup["cone_deg_list"]
    ]


def run_case(
    lumapi: Any,
    runtime: Any,
    setup_fsp: Path,
    case_id: str,
    setup: dict[str, object],
    output_dir: Path,
    show_gui: bool = False,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    fsp_path = output_dir / "_saved_fsp" / f"stage13_4_{case_id}.fsp"
    fdtd = None
    start = time.perf_counter()
    state: dict[str, object] = {"case_id": case_id, "fsp_path": str(fsp_path), "lifecycle": []}
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.setresource("FDTD", 1, "processes", str(int(setup["solver_processes"])))
        state["solver_processes"] = int(setup["solver_processes"])
        fdtd.load(str(setup_fsp.resolve()))
        state["lifecycle"].append("load_setup")
        configure_case(fdtd, case_id, setup)
        errors = preflight_case(fdtd, case_id, setup)
        state["preflight_errors"] = errors
        if errors:
            elapsed = (time.perf_counter() - start) / 60.0
            note = " | ".join(errors)
            return _failure_rows(case_id, setup, fsp_path, elapsed, "preflight_failed", "not_attempted", note, output_dir), state
        fdtd.save(str(fsp_path.resolve()))
        state["lifecycle"].append("save_configured_case")
        fdtd.run()
        state["lifecycle"].append("run")
        fdtd.save(str(fsp_path.resolve()))
        state["lifecycle"].append("save_with_results")
        metrics, extraction_debug = extract_from_session(fdtd, setup)
        state["lifecycle"].append("extract_complex_vector")
        state["extraction_debug"] = extraction_debug
        elapsed = (time.perf_counter() - start) / 60.0
        orientation = next(case["orientation"] for case in CASES if case["case_id"] == case_id)
        rows = []
        for metric in metrics:
            rows.append(
                {
                    "case_id": case_id,
                    "candidate_id": CANDIDATE_ID,
                    "patch_option_id": PATCH_OPTION_ID,
                    "position": "center",
                    "dipole_orientation": orientation,
                    "cone_deg": metric["cone_deg"],
                    "target_LP_power": metric["target_LP_power"],
                    "leakage_LP_power": metric["leakage_LP_power"],
                    "LP_fraction": metric["LP_fraction"],
                    "target_to_leakage_ratio": metric["target_to_leakage_ratio"],
                    "total_cone_power": metric["total_cone_power"],
                    "farfield_grid": setup["farfield_grid"],
                    "source_x_nm": setup["source_x_nm"],
                    "source_y_nm": setup["source_y_nm"],
                    "source_z_nm": setup["source_z_nm"],
                    "simulation_time_fs": setup["simulation_time_fs"],
                    "result_csv": str(output_dir / "stage13_4_case_metrics.csv"),
                    "fsp_path": str(fsp_path),
                    "extraction_status": "complex_vector_ok",
                    "runtime_minutes": elapsed,
                    "status": "ok",
                    "notes": f"solid-angle weighted Ex/Ey LP projection; Ez={metric['Ez_cone_power']} included only in total_cone_power",
                }
            )
        state["status"] = "ok"
        state["runtime_minutes"] = elapsed
        return rows, state
    except Exception as exc:
        elapsed = (time.perf_counter() - start) / 60.0
        state["status"] = "failed"
        state["error"] = f"{type(exc).__name__}: {exc}"
        extraction_attempted = "run" in state["lifecycle"]
        return _failure_rows(
            case_id,
            setup,
            fsp_path,
            elapsed,
            "failed",
            "failed" if extraction_attempted else "not_attempted",
            state["error"],
            output_dir,
        ), state
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def extract_case_fsp(lumapi: Any, runtime: Any, case_id: str, setup: dict[str, object], output_dir: Path, show_gui: bool = False) -> tuple[list[dict[str, object]], dict[str, object]]:
    fsp_path = output_dir / "_saved_fsp" / f"stage13_4_{case_id}.fsp"
    if not fsp_path.is_file():
        return _failure_rows(case_id, setup, fsp_path, 0.0, "missing_fsp", "missing_fsp", f"missing FSP: {fsp_path}", output_dir), {"case_id": case_id, "status": "missing_fsp"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp_path.resolve()))
        metrics, debug = extract_from_session(fdtd, setup)
        orientation = next(case["orientation"] for case in CASES if case["case_id"] == case_id)
        rows: list[dict[str, object]] = []
        for metric in metrics:
            rows.append(
                {
                    "case_id": case_id,
                    "candidate_id": CANDIDATE_ID,
                    "patch_option_id": PATCH_OPTION_ID,
                    "position": "center",
                    "dipole_orientation": orientation,
                    "cone_deg": metric["cone_deg"],
                    "target_LP_power": metric["target_LP_power"],
                    "leakage_LP_power": metric["leakage_LP_power"],
                    "LP_fraction": metric["LP_fraction"],
                    "target_to_leakage_ratio": metric["target_to_leakage_ratio"],
                    "total_cone_power": metric["total_cone_power"],
                    "farfield_grid": setup["farfield_grid"],
                    "source_x_nm": setup["source_x_nm"],
                    "source_y_nm": setup["source_y_nm"],
                    "source_z_nm": setup["source_z_nm"],
                    "simulation_time_fs": setup["simulation_time_fs"],
                    "result_csv": str(output_dir / "stage13_4_case_metrics.csv"),
                    "fsp_path": str(fsp_path),
                    "extraction_status": "complex_vector_ok",
                    "runtime_minutes": "",
                    "status": "ok",
                    "notes": f"re-extracted from saved FSP; solid-angle weighted Ex/Ey; Ez={metric['Ez_cone_power']} only in total_cone_power",
                }
            )
        return rows, {"case_id": case_id, "status": "ok", "extraction_debug": debug}
    except Exception as exc:
        note = f"{type(exc).__name__}: {exc}"
        return _failure_rows(case_id, setup, fsp_path, 0.0, "extraction_failed", "failed", note, output_dir), {"case_id": case_id, "status": "failed", "error": note}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def read_case_metrics(path: Path) -> list[dict[str, str]]:
    return read_csv_rows(path)


def incoherent_rows(case_rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    good = [row for row in case_rows if str(row.get("status")) == "ok" and str(row.get("extraction_status")) == "complex_vector_ok"]
    output: list[dict[str, object]] = []
    for cone in CONES_DEG:
        xrow = next((row for row in good if row.get("case_id") == "center_x" and abs(flt(row.get("cone_deg")) - cone) < 1e-9), None)
        yrow = next((row for row in good if row.get("case_id") == "center_y" and abs(flt(row.get("cone_deg")) - cone) < 1e-9), None)
        if xrow is None or yrow is None:
            continue
        tx = flt(xrow.get("target_LP_power"))
        ty = flt(yrow.get("target_LP_power"))
        lx = flt(xrow.get("leakage_LP_power"))
        ly = flt(yrow.get("leakage_LP_power"))
        target = tx + ty
        leakage = lx + ly
        denom = target + leakage
        fraction = target / denom if denom else float("nan")
        total = flt(xrow.get("total_cone_power")) + flt(yrow.get("total_cone_power"))
        output.append(
            {
                "candidate_id": CANDIDATE_ID,
                "position": "center",
                "cone_deg": cone,
                "target_LP_power_xdip": tx,
                "target_LP_power_ydip": ty,
                "leakage_LP_power_xdip": lx,
                "leakage_LP_power_ydip": ly,
                "target_LP_power_incoherent": target,
                "leakage_LP_power_incoherent": leakage,
                "LP_fraction_incoherent": fraction,
                "target_to_leakage_ratio_incoherent": target / leakage if leakage else float("inf"),
                "total_cone_power_incoherent": total,
                "pass_center_lp_fraction_gt_0p60": fraction > 0.60,
                "notes": "x/y dipole powers summed incoherently; no field addition; Ez included only in each total_cone_power",
            }
        )
    return output


def interpret_center(incoherent: Sequence[dict[str, object]]) -> tuple[str, str]:
    if len(incoherent) != len(CONES_DEG):
        return "incomplete_or_blocked", "Stop: both complex-vector center cases are required before interpretation or +/-q runs."
    by_cone = {flt(row.get("cone_deg")): flt(row.get("LP_fraction_incoherent")) for row in incoherent}
    if all(value > 0.60 for value in by_cone.values()):
        return "pass_minimal_center", "Center diagnostic passes all cones; +/-q cases may be considered in a separate authorized stage."
    if any(value < 0.50 for value in by_cone.values()):
        note = "Stop for mechanism diagnosis before +/-q cases."
        if by_cone.get(5.0, 1.0) < 0.50:
            note += " The +/-5 deg cone is also poor, so this is probably not only a DBR problem."
        return "fail_or_near_balance", note
    if by_cone.get(5.0, 0.0) > 0.60 and by_cone.get(20.0, 1.0) <= 0.60:
        return "wide_angle_degradation", "Stop before +/-q; likely angular-spectrum degradation. DBR/RCLED relevance may be assessed later, not added now."
    return "hold_for_mechanism_review", "Hold before +/-q cases; center LP fraction does not pass all three cones."


def build_extraction_notes(setup: dict[str, object], runtime_state: dict[str, object] | None = None) -> str:
    state = runtime_state or {}
    return f"""# Stage13-4 Extraction Notes

- Required API: `farfieldvector3d` for complex Ex/Ey/Ez plus `farfieldux` and `farfielduy`.
- Far-field grid: `{setup['farfield_grid']} x {setup['farfield_grid']}`.
- Cone half-angles: `{setup['cone_deg_list']}` degrees.
- LP projection: target x-LP uses solid-angle-weighted `|Ex|^2`; leakage y-LP uses solid-angle-weighted `|Ey|^2`.
- LP fraction denominator contains Ex and Ey only.
- Ez handling: excluded from LP projection and included only in `total_cone_power`.
- Total cone power: integral of `|Ex|^2 + |Ey|^2 + |Ez|^2` over the cone.
- Integration grid: direction cosines from `farfieldux/farfielduy`, weighted by `du_x du_y / u_z`.
- Raw complex arrays saved: `False`.
- Intensity-only `farfield3d` is not used to infer LP metrics.
- x/y dipoles are separate simulations; only powers are summed incoherently.
- This finite-patch cone analysis is not an order-resolved Jones/APCD selectivity claim.
- Runtime extraction state: `{json.dumps(state, ensure_ascii=False)}`.
"""


def build_run_summary(setup: dict[str, object], case_rows: Sequence[dict[str, object]], incoherent: Sequence[dict[str, object]], runtime_state: dict[str, object] | None = None) -> str:
    interpretation, recommendation = interpret_center(incoherent)
    state = runtime_state or {}
    lines = [
        "# Stage13-4 LP No-DBR Center Dipole Diagnostic",
        "",
        "## Scope and resolved setup",
        "",
        f"- Frozen candidate: `{setup['candidate_id']}`; patch `{setup['patch_option_id']}` = `{setup['Nx']} x {setup['Ny']}` tiles.",
        f"- Geometry: `{setup['estimated_dimers']}` dimers / `{setup['estimated_nanopillars']}` nanopillars.",
        f"- Source: `({setup['source_x_nm']}, {setup['source_y_nm']}, {setup['source_z_nm']}) nm`; source-z is a diagnostic placeholder relative to pillar-base z=0.",
        "- Coordinate system: x-y metasurface, z height, +z emission/monitor, x gradient, target x-LP.",
        f"- Wavelength `{setup['wavelength_nm']}` nm; height `{setup['height_nm']}` nm; object-defined dielectric index `{MATERIAL_INDEX}`.",
        f"- Background: `{setup['background_stack']}`.",
        "- DBR: off; RCLED: off; no optimization; no source-position sweep.",
        f"- FDTD spans: x `{setup['fdtd_x_span_nm']:.6f}` nm, y `{setup['fdtd_y_span_nm']:.6f}` nm, z `{setup['fdtd_z_min_nm']}` to `{setup['fdtd_z_max_nm']}` nm.",
        f"- Monitor: +z plane at `{setup['monitor_z_nm']}` nm.",
        f"- Solver processes: `{setup['solver_processes']}` (limited to avoid oversubscribing the concurrent 12-worker external job).",
        "",
        "## Run gate",
        "",
        f"- center_x status: `{state.get('center_x', {}).get('status', 'not_available')}`.",
        f"- center_y status: `{state.get('center_y', {}).get('status', 'not_available')}`.",
        "- center_y was permitted only after center_x run and complex-vector extraction succeeded.",
        "",
        "## LP fractions",
        "",
        "| case | cone | LP_fraction | target/leakage | extraction |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in case_rows:
        fraction = row.get("LP_fraction", "")
        ratio = row.get("target_to_leakage_ratio", "")
        lines.append(f"| {row.get('case_id')} | {row.get('cone_deg')} | {fraction} | {ratio} | {row.get('extraction_status')} |")
    lines.extend(["", "## Center incoherent result", "", "| cone | LP_fraction | pass >0.60 |", "| ---: | ---: | --- |"])
    for row in incoherent:
        lines.append(f"| {row.get('cone_deg')} | {row.get('LP_fraction_incoherent')} | {row.get('pass_center_lp_fraction_gt_0p60')} |")
    lines.extend(
        [
            "",
            f"- Stage interpretation: `{interpretation}`.",
            f"- Recommendation: {recommendation}",
            "- This is a finite-patch angular-cone LP diagnostic, not an order-resolved Jones-matrix/APCD claim.",
            "",
        ]
    )
    return "\n".join(lines)


def build_readme(setup: dict[str, object]) -> str:
    return f"""# Stage13-4 LP No-DBR Center Dipole Diagnostic

- Runs only `center_x`, then `center_y` after the center_x complex-vector gate.
- Patch: A_small, 3 x 19 tiles, 342 dimers / 684 nanopillars.
- DBR/RCLED: off. No substrate/device-stack object is added; the Stage12 default background is retained.
- Source: (0, 0, -200) nm relative to the Stage12 pillar-base z=0 plane; diagnostic placeholder only.
- Complex-vector Ex/Ey/Ez is required. Ez contributes only to total cone power, not LP projection.
- Cones: 5, 10, 20 degrees; grid: {setup['farfield_grid']}.
- x/y dipole powers are combined incoherently; fields are never added.
- `.fsp` files under `_saved_fsp/` are runtime artifacts and must not be committed.
"""
