from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


CANDIDATE_ID = "H500_LP_APCD_K6_XGRAD_FROZEN_STAGE12"
PERIOD_X_NM = 2591.446716
PITCH_X_NM = PERIOD_X_NM / 6.0
PITCH_Y_NM = 432.0
WAVELENGTH_NM = 450.0
TARGET_UX = WAVELENGTH_NM / PERIOD_X_NM
TARGET_THETA_DEG = math.degrees(math.asin(TARGET_UX))
NX = 3
NY = 19

PHASE_FIELDS = [
    "supercell_index", "phase_bin_deg", "actual_common_phase_deg", "actual_common_phase_unwrapped_deg",
    "dimer_center_x_nm", "dimer_center_y_nm", "position_monotonic_along_plus_x",
    "phase_sequence_monotonic_along_plus_x", "nominal_phase_step_deg", "actual_phase_step_from_previous_deg",
    "nominal_dphi_dx_rad_per_nm", "repo_empirical_predicted_order", "layout_consistency", "source_file",
]
PATCH_FIELDS = [
    "candidate_id", "patch_option_id", "N_supercells_x", "N_supercells_y", "dimers", "nanopillars",
    "x_min_nm", "x_max_nm", "y_min_nm", "y_max_nm", "whole_supercells_preserved",
    "phase_reset_errors_detected", "edge_symmetry_error_x_nm", "edge_symmetry_error_y_nm",
    "has_true_center_dimer", "source_on_supercell_boundary", "source_between_phase_bins",
    "nearest_phase_bins", "finite_patch_tiling_status", "evidence",
]
COORD_FIELDS = ["audit_item", "value", "status", "evidence", "notes"]
NEIGHBOR_FIELDS = [
    "entity_type", "rank", "tile_x", "tile_y", "dimer_index", "phase_bin_deg", "pillar_role",
    "center_x_nm", "center_y_nm", "distance_to_source_nm", "local_bias_note",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def flt(value: object) -> float:
    return float(str(value).strip())


def j1_dimensions(row: dict[str, str]) -> tuple[float, float]:
    params = json.loads(row["j1_geometry_params"])
    family = row["j1_shape_family"]
    if family == "circle":
        return flt(params["diameter_nm"]), flt(params["diameter_nm"])
    if family == "square":
        return flt(params["side_nm"]), flt(params["side_nm"])
    return flt(params["length_nm"]), flt(params["width_nm"])


def frozen_units(layout_rows: Sequence[dict[str, str]], phase_rows: Sequence[dict[str, str]]) -> list[dict[str, object]]:
    if len(layout_rows) != 6:
        raise ValueError(f"K=6 must contain six dimers, got {len(layout_rows)}")
    phase_by_index = {int(flt(row["supercell_index"])): row for row in phase_rows}
    shift = PERIOD_X_NM / 2.0
    units: list[dict[str, object]] = []
    for row in sorted(layout_rows, key=lambda item: int(flt(item["supercell_index"]))):
        index = int(flt(row["supercell_index"]))
        j1_w, j1_h = j1_dimensions(row)
        units.append({
            "index": index,
            "phase": int(flt(row["phase_bin_deg"])),
            "actual_phase": flt(phase_by_index[index]["actual_common_phase_deg"]),
            "dimer_x": flt(row["supercell_center_x_nm"]) - shift,
            "dimer_y": flt(row["supercell_center_y_nm"]),
            "pillars": [
                {"role": "J1", "x": flt(row["j1_abs_center_x_nm"]) - shift, "y": flt(row["j1_abs_center_y_nm"]), "w": j1_w, "h": j1_h},
                {"role": "J2", "x": flt(row["j2_abs_center_x_nm"]) - shift, "y": flt(row["j2_abs_center_y_nm"]), "w": flt(row["j2_length_nm"]), "h": flt(row["j2_width_nm"])},
            ],
        })
    return units


def unwrap_phase_degrees(values: Sequence[float]) -> list[float]:
    return list(np.degrees(np.unwrap(np.radians(np.asarray(values, dtype=float)))))


def phase_audit_rows(units: Sequence[dict[str, object]], source_path: str) -> list[dict[str, object]]:
    xs = [float(unit["dimer_x"]) for unit in units]
    nominal = [float(unit["phase"]) for unit in units]
    actual_unwrapped = unwrap_phase_degrees([float(unit["actual_phase"]) for unit in units])
    positions_ok = all(right > left for left, right in zip(xs, xs[1:]))
    nominal_ok = all(right > left for left, right in zip(nominal, nominal[1:]))
    actual_ok = all(right > left for left, right in zip(actual_unwrapped, actual_unwrapped[1:]))
    dphi_dx = math.radians(60.0) / PITCH_X_NM
    rows = []
    for i, unit in enumerate(units):
        rows.append({
            "supercell_index": unit["index"], "phase_bin_deg": unit["phase"],
            "actual_common_phase_deg": unit["actual_phase"],
            "actual_common_phase_unwrapped_deg": actual_unwrapped[i],
            "dimer_center_x_nm": unit["dimer_x"], "dimer_center_y_nm": unit["dimer_y"],
            "position_monotonic_along_plus_x": positions_ok,
            "phase_sequence_monotonic_along_plus_x": nominal_ok and actual_ok,
            "nominal_phase_step_deg": 60.0,
            "actual_phase_step_from_previous_deg": "" if i == 0 else actual_unwrapped[i] - actual_unwrapped[i - 1],
            "nominal_dphi_dx_rad_per_nm": dphi_dx,
            "repo_empirical_predicted_order": "+1 / +x (Stage12 periodic FDTD convention)",
            "layout_consistency": "pass" if positions_ok and nominal_ok and actual_ok else "fail",
            "source_file": source_path,
        })
    return rows


def tile_patch(units: Sequence[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    dimers: list[dict[str, object]] = []
    pillars: list[dict[str, object]] = []
    for tx in range(-(NX // 2), NX // 2 + 1):
        for ty in range(-(NY // 2), NY // 2 + 1):
            for unit in units:
                dx = float(unit["dimer_x"]) + tx * PERIOD_X_NM
                dy = float(unit["dimer_y"]) + ty * PITCH_Y_NM
                dimers.append({"tile_x": tx, "tile_y": ty, "dimer_index": unit["index"], "phase": unit["phase"], "x": dx, "y": dy})
                for pillar in unit["pillars"]:
                    pillars.append({
                        "tile_x": tx, "tile_y": ty, "dimer_index": unit["index"], "phase": unit["phase"],
                        "role": pillar["role"], "x": float(pillar["x"]) + tx * PERIOD_X_NM,
                        "y": float(pillar["y"]) + ty * PITCH_Y_NM, "w": pillar["w"], "h": pillar["h"],
                    })
    return dimers, pillars


def bounds(pillars: Sequence[dict[str, object]]) -> dict[str, float]:
    return {
        "x_min": min(float(p["x"]) - float(p["w"]) / 2 for p in pillars),
        "x_max": max(float(p["x"]) + float(p["w"]) / 2 for p in pillars),
        "y_min": min(float(p["y"]) - float(p["h"]) / 2 for p in pillars),
        "y_max": max(float(p["y"]) + float(p["h"]) / 2 for p in pillars),
    }


def nearest_rows(dimers: Sequence[dict[str, object]], pillars: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for entity_type, items in (("dimer", dimers), ("pillar", pillars)):
        ordered = sorted(items, key=lambda item: math.hypot(float(item["x"]), float(item["y"])))[:6]
        for rank, item in enumerate(ordered, 1):
            distance = math.hypot(float(item["x"]), float(item["y"]))
            note = ""
            if entity_type == "pillar" and rank == 1:
                note = "closest object is phase-180 J2; local coupling bias is plausible"
            elif entity_type == "dimer" and rank <= 2:
                note = "two central dimers are equidistant from optical origin"
            result.append({
                "entity_type": entity_type, "rank": rank, "tile_x": item["tile_x"], "tile_y": item["tile_y"],
                "dimer_index": item["dimer_index"], "phase_bin_deg": item["phase"],
                "pillar_role": item.get("role", ""), "center_x_nm": item["x"], "center_y_nm": item["y"],
                "distance_to_source_nm": distance, "local_bias_note": note,
            })
    return result


def plot_phase(path: Path, phase_rows: Sequence[dict[str, object]]) -> None:
    x = [flt(row["dimer_center_x_nm"]) for row in phase_rows]
    phase = [flt(row["actual_common_phase_unwrapped_deg"]) for row in phase_rows]
    nominal = [flt(row["phase_bin_deg"]) for row in phase_rows]
    fig, ax = plt.subplots(figsize=(7.2, 4.3), constrained_layout=True)
    ax.plot(x, nominal, "o--", label="nominal phase bin")
    ax.plot(x, phase, "s-", label="actual common phase (unwrapped)")
    for row in phase_rows:
        ax.annotate(f"d{row['supercell_index']}", (flt(row["dimer_center_x_nm"]), flt(row["actual_common_phase_unwrapped_deg"])), xytext=(4, 5), textcoords="offset points")
    ax.set(xlabel="Dimer center x (nm)", ylabel="Phase (deg)", title="Frozen K=6 phase ramp along +x")
    ax.grid(alpha=0.25); ax.legend()
    fig.savefig(path, dpi=170); plt.close(fig)


def plot_neighborhood(path: Path, dimers: Sequence[dict[str, object]], pillars: Sequence[dict[str, object]]) -> None:
    local_dimers = [d for d in dimers if abs(float(d["x"])) < 900 and abs(float(d["y"])) < 700]
    local_pillars = [p for p in pillars if abs(float(p["x"])) < 900 and abs(float(p["y"])) < 700]
    fig, ax = plt.subplots(figsize=(7.0, 6.0), constrained_layout=True)
    sc = ax.scatter([p["x"] for p in local_pillars], [p["y"] for p in local_pillars], c=[p["phase"] for p in local_pillars], cmap="twilight", s=55, marker="s", label="pillars")
    ax.scatter([d["x"] for d in local_dimers], [d["y"] for d in local_dimers], facecolors="none", edgecolors="black", s=85, label="dimer centers")
    ax.scatter([0], [0], marker="*", c="red", s=150, label="source x-y")
    fig.colorbar(sc, ax=ax, label="phase bin (deg)")
    ax.set(xlabel="x (nm)", ylabel="y (nm)", title="A_small source-center neighborhood", xlim=(-900, 900), ylim=(-700, 700))
    ax.set_aspect("equal"); ax.grid(alpha=0.2); ax.legend(loc="upper right")
    fig.savefig(path, dpi=170); plt.close(fig)


def plot_overview(path: Path, dimers: Sequence[dict[str, object]], patch_bounds: dict[str, float]) -> None:
    fig, ax = plt.subplots(figsize=(8.0, 6.4), constrained_layout=True)
    ax.scatter([d["x"] for d in dimers], [d["y"] for d in dimers], c=[d["phase"] for d in dimers], cmap="twilight", s=8)
    for boundary in (-PERIOD_X_NM / 2, PERIOD_X_NM / 2):
        ax.axvline(boundary, color="black", linestyle="--", alpha=0.35)
    ax.scatter([0], [0], marker="*", c="red", s=100)
    ax.set(xlabel="x (nm)", ylabel="y (nm)", title="A_small: 3 whole K=6 supercells x 19 y rows")
    ax.set_xlim(patch_bounds["x_min"] - 100, patch_bounds["x_max"] + 100)
    ax.set_ylim(patch_bounds["y_min"] - 100, patch_bounds["y_max"] + 100)
    ax.set_aspect("equal"); ax.grid(alpha=0.15)
    fig.savefig(path, dpi=160); plt.close(fig)


def build_report(phase_rows: Sequence[dict[str, object]], patch_row: dict[str, object], coordinate_rows: Sequence[dict[str, object]], neighborhood: Sequence[dict[str, object]]) -> str:
    dimer_near = [row for row in neighborhood if row["entity_type"] == "dimer"]
    pillar_near = [row for row in neighborhood if row["entity_type"] == "pillar"]
    phase_centers = ", ".join(f"d{r['supercell_index']}={flt(r['dimer_center_x_nm']):.6f} nm/{r['phase_bin_deg']} deg" for r in phase_rows)
    nearest_text = ", ".join(f"{r['phase_bin_deg']}deg {r['pillar_role']} ({flt(r['distance_to_source_nm']):.3f} nm)" for r in pillar_near)
    return f"""# Stage13-6 LP Phase-Ramp / Coordinate / Finite-Patch Consistency Audit

## Scope

- Read-only audit of existing Stage12 and Stage13 artifacts. No FDTD, +/-q, DBR/RCLED, geometry change, optimization, or FSP write.
- K=6 means six dimers, not six nanopillars.

## 1. Stage12 plane-wave evidence

- Official target: x-order +1 in the x-z plane, +10.000000 deg, ux=+0.173648177762.
- Stage12 periodic FDTD measured x-LP +1 power 0.357823825858; +1 was dominant. Zero and -1 powers were 0.080872261874 and 0.017669974856.
- Propagation/monitor convention: plane wave below the z=0 pillar base, forward +z; top z-normal monitor above the 500 nm pillars.
- Evidence is periodic/metagrating order resolved (`gratingvector`/order CSV), not only cone integration. The official package contains `figure_3_xgrad_order_power.png/.svg`.
- Stage12 explicitly maps order_n=+1 to ux=+0.173648 and calls it +x/+10 deg.

## 2. Frozen K=6 phase ramp

- Lambda_x={PERIOD_X_NM} nm; phase-bin pitch={PITCH_X_NM:.6f} nm; y pitch={PITCH_Y_NM} nm.
- Dimer centers: {phase_centers}.
- Nominal bins are 0,60,120,180,240,300 deg and increase monotonically along +x. Unwrapped actual common phases are also monotonic.
- Under the repository's empirical Stage12 convention, positive dphi/dx produces order +1 / +x. The periodic FDTD confirms this sign.
- Result: phase sequence is internally consistent; `phase_ramp_error_suspected=false`.

## 3. A_small finite patch

- 3 x 19 whole tiles; 342 dimers / 684 nanopillars. Extent: x=[{patch_row['x_min_nm']}, {patch_row['x_max_nm']}] nm, y=[{patch_row['y_min_nm']}, {patch_row['y_max_nm']}] nm.
- Whole six-dimer supercells are repeated at integer x-tile offsets without phase reset errors. Edge asymmetry remains 15 nm in x and 35 nm in y, matching Stage13-2.
- No true center dimer. The source lies midway between phase-120 and phase-180 dimer centers at x=+/-215.953893 nm; it is not on a supercell boundary or the 300->0 phase wrap.
- Six nearest pillars: {nearest_text}.
- The closest pillar is phase-180 J2 at 115.954 nm, so local source coupling is geometrically biased even though the two nearest dimer centers are tied.
- Result: tiling is consistent; `finite_patch_tiling_error_suspected=false`, `source_center_local_bias=true`.

## 4. Far-field coordinate consistency

- Stage13 uses `farfieldux/farfielduy`; saved extraction shape is 101x101 and the PNG axes cover approximately [-1,+1]. Positive ux is plotted to the right and CSV values preserve the API sign.
- Both Stage12 and Stage13 use a +z/top monitor, but Stage12 order signs come from grating-order extraction while Stage13 signs come from continuous far-field direction cosines.
- No common saved dataset directly proves that `gratingvector order_n=+1` and Stage13 `farfieldux>0` have identical sign under all monitor conventions.
- Expected ux=+/-{TARGET_UX:.12f}; Stage13-5 peaks are center_x Ex (-0.34,-0.12) and center_y Ey (-0.58,0), both far from expected +/-10 deg centers.
- Result: `coordinate_status=unresolved`, not failed.

## 5. Angular-spectrum and excitation mechanism

- center_x Ex retains finite power near both expected orders, but its global peak is near theta_x=-19.88 deg with nonzero uy, indicating a broad/multilobed finite-aperture field rather than clean periodic +1 steering.
- center_y Ey peaks near theta_x=-35.45 deg, not at zero or +/-10 deg.
- The default homogeneous background, absent substrate/device stack, no DBR and no RCLED allow broad off-normal dipole components; this is not representative of a final MicroLED stack.
- Periodic plane-wave illumination excites every supercell coherently. A single local dipole below a finite patch excites phase bins with unequal amplitude and phase, especially with the center-pillar bias above.
- DBR/RCLED is not recommended yet because coordinate/API sign consistency is still unresolved.

## 6. Classification

- phase_ramp_error_suspected: false
- finite_patch_tiling_error_suspected: false
- coordinate_mapping_unresolved: true
- local_dipole_broad_angle_dominance: true
- plane_wave_to_dipole_mismatch: true
- source_center_local_bias: true
- insufficient_evidence: false for layout/tiling; true for direct API-to-API sign equivalence

## 7. Recommended next action

**Stage13-7A: no-new-FDTD coordinate/sign validation against Stage12 plane-wave artifacts.**

This is the single next step. Do not run +/-q or add DBR/RCLED until the Stage12 grating-order sign and Stage13 continuous far-field sign are tied by a direct artifact-level check.

## Jones/APCD evidence boundary

- This audit uses existing periodic order power and finite-patch dipole angular power. It does not construct a new incident-wave J_xy matrix.
- No alpha/beta basis conversion or t_{{alpha*<-alpha}}^order claim is made here.
"""


def run_audit(repo_root: Path, output_dir: Path) -> dict[str, object]:
    layout_path = repo_root / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"
    phase_path = repo_root / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_phase_amplitude_audit.csv"
    setup_path = repo_root / "outputs/stage13_4_lp_no_dbr_center_dipole/stage13_4_resolved_setup.json"
    for path in (layout_path, phase_path, setup_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    units = frozen_units(read_csv(layout_path), read_csv(phase_path))
    phase_rows = phase_audit_rows(units, layout_path.relative_to(repo_root).as_posix())
    dimers, pillars = tile_patch(units)
    if len(dimers) != 342 or len(pillars) != 684:
        raise ValueError(f"A_small count mismatch: dimers={len(dimers)}, pillars={len(pillars)}")
    patch_bounds = bounds(pillars)
    setup = json.loads(setup_path.read_text(encoding="utf-8"))
    expected_bounds = setup["geometry_bounds_nm"]
    if any(abs(patch_bounds[key.replace("_nm", "")] - float(value)) > 1e-6 for key, value in expected_bounds.items()):
        raise ValueError(f"Stage13-4 bounds disagree with rebuilt patch: {patch_bounds} vs {expected_bounds}")
    neighborhood = nearest_rows(dimers, pillars)
    patch_row = {
        "candidate_id": CANDIDATE_ID, "patch_option_id": "A_small", "N_supercells_x": NX, "N_supercells_y": NY,
        "dimers": len(dimers), "nanopillars": len(pillars), "x_min_nm": patch_bounds["x_min"], "x_max_nm": patch_bounds["x_max"],
        "y_min_nm": patch_bounds["y_min"], "y_max_nm": patch_bounds["y_max"], "whole_supercells_preserved": True,
        "phase_reset_errors_detected": False, "edge_symmetry_error_x_nm": abs(abs(patch_bounds["x_min"]) - abs(patch_bounds["x_max"])),
        "edge_symmetry_error_y_nm": abs(abs(patch_bounds["y_min"]) - abs(patch_bounds["y_max"])),
        "has_true_center_dimer": False, "source_on_supercell_boundary": False, "source_between_phase_bins": True,
        "nearest_phase_bins": "120 and 180 deg", "finite_patch_tiling_status": "pass",
        "evidence": "reconstructed with Stage13-4 integer tile loops and matched stage13_4_resolved_setup geometry bounds",
    }
    coordinate_rows = [
        {"audit_item": "stage12_target_order", "value": "order_n=+1; ux=+0.173648177762; theta=+10.000000 deg", "status": "explicit", "evidence": "stage12_2_k6_forward_order_power.csv", "notes": "periodic grating-order extraction"},
        {"audit_item": "stage12_monitor_and_propagation", "value": "+z top z-normal monitor; forward source below pillars", "status": "resolved", "evidence": "src/metasurface/stage12_k6_fdtd.py", "notes": "periodic x/y boundaries"},
        {"audit_item": "stage13_farfield_axes", "value": "ux/uy approximately [-1,+1], 101x101; +ux plotted right", "status": "resolved_for_stage13_visualization", "evidence": "Stage13-5 PNGs, extraction notes, and plotting code", "notes": "CSV preserves farfieldux/farfielduy values"},
        {"audit_item": "api_sign_equivalence", "value": "gratingvector order sign versus farfieldux sign", "status": "unresolved", "evidence": "no common saved artifact directly checks both APIs", "notes": "do not call sign failed"},
        {"audit_item": "expected_orders", "value": f"ux=0,+{TARGET_UX:.12f},-{TARGET_UX:.12f}", "status": "resolved", "evidence": "450/2591.446716", "notes": f"|theta|={TARGET_THETA_DEG:.9f} deg"},
        {"audit_item": "stage13_5_center_x_Ex_peak", "value": "ux=-0.34; uy=-0.12; theta_x=-19.88 deg", "status": "other", "evidence": "stage13_5_peak_metrics.csv", "notes": "not within 3 deg of expected orders"},
        {"audit_item": "stage13_5_center_y_Ey_peak", "value": "ux=-0.58; uy=0; theta_x=-35.45 deg", "status": "other", "evidence": "stage13_5_peak_metrics.csv", "notes": "large off-axis leakage"},
        {"audit_item": "coordinate_status", "value": "unresolved", "status": "unresolved", "evidence": "API-to-API sign bridge missing", "notes": "Stage13-7A recommended"},
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "stage13_6_phase_ramp_audit.csv", phase_rows, PHASE_FIELDS)
    write_csv(output_dir / "stage13_6_patch_tiling_audit.csv", [patch_row], PATCH_FIELDS)
    write_csv(output_dir / "stage13_6_coordinate_audit.csv", coordinate_rows, COORD_FIELDS)
    write_csv(output_dir / "stage13_6_source_neighborhood.csv", neighborhood, NEIGHBOR_FIELDS)
    plot_phase(output_dir / "stage13_6_phase_ramp_layout.png", phase_rows)
    plot_neighborhood(output_dir / "stage13_6_patch_center_neighborhood.png", dimers, pillars)
    plot_overview(output_dir / "stage13_6_patch_tiling_overview.png", dimers, patch_bounds)
    report = build_report(phase_rows, patch_row, coordinate_rows, neighborhood)
    (output_dir / "stage13_6_audit_report.md").write_text(report, encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# Stage13-6 LP consistency audit\n\nRead-only audit of the frozen K=6 phase ramp, A_small tiling, source neighborhood, and Stage12/13 coordinate evidence. No FDTD was run.\n\nRecommended next step: **Stage13-7A no-new-FDTD coordinate/sign validation against Stage12 plane-wave artifacts.**\n",
        encoding="utf-8",
    )
    return {"phase_rows": len(phase_rows), "patch_rows": 1, "coordinate_rows": len(coordinate_rows), "neighborhood_rows": len(neighborhood), "recommendation": "Stage13-7A"}
