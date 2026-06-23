from __future__ import annotations

import csv
import json
import math
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from metasurface.stage13_4_center_dipole import (
    CANDIDATE_ID,
    FIELD_MONITOR,
    PATCH_OPTION_ID,
    X_SOURCE,
    Y_SOURCE,
    _component_arrays,
    build_patch_inventory,
    build_setup,
    load_approved_plan,
    resolved_setup,
)
from metasurface.stage13_5_order_diagnosis import (
    TARGET_UX,
    angular_distance_deg,
    cone_rows,
    direction_grid,
    intensity_components,
    peak_rows,
    save_map,
)


CASE_ID = "a_small_xlp_plane_wave_plusz"
OUTPUT_DIR_NAME = "stage13_7b_lp_finite_patch_plane_wave_sanity"
PLANE_SOURCE = "stage13_7b_xlp_plane_wave"
SOURCE_Z_NM = -250.0
HEARTBEAT_SECONDS = 30.0
MEANINGFUL_MARGIN = 1.5

PEAK_FIELDS = ["case_id", "component", "peak_ux", "peak_uy", "peak_theta_x_deg", "peak_theta_y_deg", "peak_polar_angle_deg", "nearest_order", "distance_to_plus_target_deg", "distance_to_minus_target_deg", "peak_value", "status", "notes"]
ORDER_FIELDS = ["case_id", "order_id", "order_center_ux", "order_center_uy", "cone_deg", "target_LP_power", "leakage_LP_power", "LP_fraction", "target_to_leakage_ratio", "total_vector_power", "status", "notes"]
DECISION_FIELDS = ["case_id", "case_completed", "complex_vector_extraction_successful", "ex_peak_ux", "ex_peak_uy", "ex_peak_distance_to_plus_target_deg", "ex_peak_distance_to_minus_target_deg", "plus_target_power_5deg", "zero_order_power_5deg", "minus_target_power_5deg", "meaningful_margin_threshold", "plus_exceeds_zero_and_minus", "finite_patch_plane_wave_steering_pass", "sign_or_gradient_mismatch_suspected", "finite_patch_plane_wave_no_steering", "dipole_specific_mismatch", "recommended_next_step", "notes"]


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def add_plane_wave(fdtd: Any, setup: dict[str, object]) -> None:
    for name in (X_SOURCE, Y_SOURCE):
        fdtd.select(name); fdtd.delete()
    fdtd.addplane(); fdtd.set("name", PLANE_SOURCE)
    fdtd.set("injection axis", "z"); fdtd.set("direction", "Forward")
    fdtd.set("x", 0); fdtd.set("x span", float(setup["fdtd_x_span_nm"]) * 1e-9)
    fdtd.set("y", 0); fdtd.set("y span", float(setup["fdtd_y_span_nm"]) * 1e-9)
    fdtd.set("z", SOURCE_Z_NM * 1e-9)
    fdtd.set("wavelength start", float(setup["wavelength_nm"]) * 1e-9)
    fdtd.set("wavelength stop", float(setup["wavelength_nm"]) * 1e-9)
    fdtd.set("polarization angle", 0.0)


def source_preflight(fdtd: Any, setup: dict[str, object]) -> list[str]:
    errors: list[str] = []
    try:
        direction = str(fdtd.getnamed(PLANE_SOURCE, "direction")).strip().upper()
        axis = str(fdtd.getnamed(PLANE_SOURCE, "injection axis")).strip().upper()
        z_nm = float(fdtd.getnamed(PLANE_SOURCE, "z")) / 1e-9
        polarization = float(fdtd.getnamed(PLANE_SOURCE, "polarization angle"))
        if direction != "FORWARD": errors.append(f"direction={direction}; expected FORWARD")
        if axis not in {"Z", "Z-AXIS"}: errors.append(f"injection axis={axis}; expected Z/Z-AXIS")
        if z_nm >= 0: errors.append(f"source z={z_nm} nm is not below pillar base z=0")
        if abs(polarization) > 1e-9: errors.append(f"polarization angle={polarization}; expected 0 for x-LP")
    except Exception as exc:
        errors.append(f"cannot verify plane-wave direction/axis/polarization: {type(exc).__name__}: {exc}")
    for name in (X_SOURCE, Y_SOURCE):
        try:
            if int(round(float(fdtd.getnamednumber(name)))) != 0: errors.append(f"forbidden dipole object remains: {name}")
        except Exception:
            pass
    for forbidden in ("DBR", "RCLED"):
        try:
            if int(round(float(fdtd.getnamednumber(forbidden)))) != 0: errors.append(f"forbidden object exists: {forbidden}")
        except Exception:
            pass
    for prop in ("x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"):
        actual = str(fdtd.getnamed("FDTD", prop)).strip().upper()
        if actual != "PML": errors.append(f"FDTD {prop}={actual}; expected PML")
    return errors


def heartbeat(stop: threading.Event, case_id: str, start: float, interval: float = HEARTBEAT_SECONDS) -> None:
    while not stop.wait(interval):
        print(f"HEARTBEAT case_id={case_id} elapsed_seconds={time.perf_counter()-start:.1f}", flush=True)


def run_with_heartbeat(fdtd: Any, case_id: str) -> None:
    start = time.perf_counter(); stop = threading.Event()
    thread = threading.Thread(target=heartbeat, args=(stop, case_id, start), daemon=True); thread.start()
    print(f"HEARTBEAT case_id={case_id} elapsed_seconds=0.0 status=run_start", flush=True)
    try:
        fdtd.run()
    finally:
        stop.set(); thread.join(timeout=5.0)
        print(f"HEARTBEAT case_id={case_id} elapsed_seconds={time.perf_counter()-start:.1f} status=run_end", flush=True)


def extract_fields(fdtd: Any, setup: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    grid = int(setup["farfield_grid"])
    vector = fdtd.farfieldvector3d(FIELD_MONITOR, 1, grid, grid)
    ux = fdtd.farfieldux(FIELD_MONITOR, 1, grid, grid); uy = fdtd.farfielduy(FIELD_MONITOR, 1, grid, grid)
    ex, ey, ez, debug = _component_arrays(vector); xx, yy = direction_grid(ux, uy, ex.shape)
    return {"ex": ex, "ey": ey, "ez": ez, "xx": xx, "yy": yy, "maps": intensity_components(ex, ey, ez)}, {"vector": debug, "ux_shape": list(np.asarray(ux).shape), "uy_shape": list(np.asarray(uy).shape), "raw_arrays_saved": False}


def build_peak_rows(maps: dict[str, np.ndarray], xx: np.ndarray, yy: np.ndarray) -> list[dict[str, object]]:
    raw = peak_rows(CASE_ID, maps, xx, yy)
    output = []
    for component in ("Ex_target", "Ey_leakage", "transverse_total"):
        row = next(item for item in raw if item["component"] == component)
        output.append({"case_id": CASE_ID, "component": component, "peak_ux": row["peak_ux"], "peak_uy": row["peak_uy"], "peak_theta_x_deg": row["peak_theta_x_deg"], "peak_theta_y_deg": row["peak_theta_y_deg"], "peak_polar_angle_deg": row["peak_polar_angle_deg"], "nearest_order": row["nearest_expected_order"], "distance_to_plus_target_deg": angular_distance_deg(float(row["peak_ux"]), float(row["peak_uy"]), TARGET_UX, 0.0), "distance_to_minus_target_deg": angular_distance_deg(float(row["peak_ux"]), float(row["peak_uy"]), -TARGET_UX, 0.0), "peak_value": row["peak_value"], "status": "ok", "notes": "numeric farfieldux/farfielduy global peak"})
    return output


def build_order_rows(maps: dict[str, np.ndarray], xx: np.ndarray, yy: np.ndarray) -> list[dict[str, object]]:
    return [{"case_id": CASE_ID, "order_id": row["order_id"], "order_center_ux": row["order_center_ux"], "order_center_uy": row["order_center_uy"], "cone_deg": row["cone_deg"], "target_LP_power": row["target_LP_power"], "leakage_LP_power": row["leakage_LP_power"], "LP_fraction": row["LP_fraction"], "target_to_leakage_ratio": row["target_to_leakage_ratio"], "total_vector_power": row["total_vector_power"], "status": "ok", "notes": row["notes"]} for row in cone_rows(CASE_ID, maps, xx, yy)]


def sanity_decision(peaks: Sequence[dict[str, object]], orders: Sequence[dict[str, object]]) -> dict[str, object]:
    ex = next(row for row in peaks if row["component"] == "Ex_target")
    def power(order_id: str) -> float:
        return float(next(row for row in orders if row["order_id"] == order_id and float(row["cone_deg"]) == 5.0)["target_LP_power"])
    plus, zero, minus = power("plus_target_order"), power("zero_order"), power("minus_target_order")
    plus_near = float(ex["distance_to_plus_target_deg"]) <= 3.0
    minus_near = float(ex["distance_to_minus_target_deg"]) <= 3.0
    margin = plus >= MEANINGFUL_MARGIN * max(zero, minus)
    passed = plus_near and margin
    no_steering = not plus_near and not minus_near
    if passed:
        recommendation = "Plane-wave sanity passes: continue with dipole-specific illumination/source-coupling diagnosis; do not add DBR/RCLED yet"
    elif minus_near:
        recommendation = "Return to finite-patch source/gradient sign implementation diagnosis before any dipole work"
    else:
        recommendation = "Stage13-8 finite-patch aperture/plane-wave implementation diagnosis before more dipole work"
    return {"case_id": CASE_ID, "case_completed": True, "complex_vector_extraction_successful": True, "ex_peak_ux": ex["peak_ux"], "ex_peak_uy": ex["peak_uy"], "ex_peak_distance_to_plus_target_deg": ex["distance_to_plus_target_deg"], "ex_peak_distance_to_minus_target_deg": ex["distance_to_minus_target_deg"], "plus_target_power_5deg": plus, "zero_order_power_5deg": zero, "minus_target_power_5deg": minus, "meaningful_margin_threshold": MEANINGFUL_MARGIN, "plus_exceeds_zero_and_minus": margin, "finite_patch_plane_wave_steering_pass": passed, "sign_or_gradient_mismatch_suspected": minus_near, "finite_patch_plane_wave_no_steering": no_steering, "dipole_specific_mismatch": passed, "recommended_next_step": recommendation, "notes": "pass requires Ex global peak within 3 deg of +target and +target 5deg Ex power >=1.5x zero and minus"}


def build_summary(setup: dict[str, object], peaks: Sequence[dict[str, object]], decision: dict[str, object], runtime_minutes: float) -> str:
    ex = next(row for row in peaks if row["component"] == "Ex_target")
    return f"""# Stage13-7B LP A_small finite-patch plane-wave sanity FDTD

## Scope and setup

- One case only: `{CASE_ID}`; normal-incidence x-LP plane wave from z={SOURCE_Z_NM} nm below the pillar-base plane, injection axis z, direction Forward, propagating toward +z.
- A_small: 3 x 19 tiles, 342 dimers / 684 nanopillars; frozen Stage12 geometry unchanged.
- DBR/RCLED off; default Stage13 background; wavelength 450 nm; simulation time {setup['simulation_time_fs']} fs; grid {setup['farfield_grid']}.
- Plane source spans the Stage13 FDTD x/y region; all dipole objects were deleted before setup save.
- Runtime: {runtime_minutes:.3f} minutes. Heartbeat interval: {HEARTBEAT_SECONDS} seconds.
- Preflight history: the first setup-only attempt stopped before `run()` because Lumerical returned the canonical injection-axis label `Z-AXIS`; the validator was corrected to accept `Z`/`Z-AXIS`, tests passed, and the successful run had no preflight errors.

## Extraction

- Complex farfieldvector3d Ex/Ey/Ez with numeric farfieldux/farfielduy.
- Ez excluded from LP projection and included only in total vector power. No raw complex arrays saved.

## Result

- Ex global peak: ux={ex['peak_ux']}, uy={ex['peak_uy']}; distance to +target={ex['distance_to_plus_target_deg']} deg; distance to -target={ex['distance_to_minus_target_deg']} deg.
- finite_patch_plane_wave_steering_pass: `{decision['finite_patch_plane_wave_steering_pass']}`.
- sign_or_gradient_mismatch_suspected: `{decision['sign_or_gradient_mismatch_suspected']}`.
- finite_patch_plane_wave_no_steering: `{decision['finite_patch_plane_wave_no_steering']}`.
- dipole_specific_mismatch: `{decision['dipole_specific_mismatch']}`.

## Single recommended next step

**{decision['recommended_next_step']}**

## Jones/APCD evidence boundary

- This finite-patch angular-power sanity check is not a periodic order-resolved J_xy/APCD reconstruction.
- No alpha/beta conversion or t_{{alpha*<-alpha}}^order claim is made.
"""


def build_notes(setup: dict[str, object], state: dict[str, object]) -> str:
    return f"""# Stage13-7B extraction notes

- Lifecycle: build finite patch, delete dipoles, add/verify plane wave, save setup, close, load configured case, verify source, save, run with heartbeat, save results, extract, close.
- Plane wave: injection axis=z; direction=Forward; z={SOURCE_Z_NM} nm; polarization angle=0 deg (x-LP); source below pillar base and propagating +z.
- Monitor: `{FIELD_MONITOR}`, +z/top plane inherited from Stage13-4.
- API: farfieldvector3d + farfieldux + farfielduy; intensity-only farfield3d not used for LP metrics.
- Order centers: zero and ux=+/-{TARGET_UX}; cone half-angles 3,5,10 deg.
- Ez excluded from LP projection; included in total vector power.
- Raw complex arrays saved: False.
- Preflight history: an initial setup-only gate stopped before FDTD because the API returned `Z-AXIS` rather than `Z`; these are equivalent z-axis labels. The validator was corrected and the completed run reports empty setup/run preflight error lists.
- FSP/log artifacts remain under ignored `_saved_fsp` and are not committed.
- Runtime state: `{json.dumps(state, ensure_ascii=False)}`.
"""
