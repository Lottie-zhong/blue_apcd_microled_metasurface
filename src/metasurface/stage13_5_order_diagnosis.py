from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from metasurface.stage13_4_center_dipole import FIELD_MONITOR
from metasurface.stage13_lp_dipole import CANDIDATE_ID, flt


WAVELENGTH_NM = 450.0
SUPERCELL_PERIOD_X_NM = 2591.446716
TARGET_UX = WAVELENGTH_NM / SUPERCELL_PERIOD_X_NM
TARGET_THETA_DEG = math.degrees(math.asin(TARGET_UX))
GRID_N = 101
CONES_DEG = [3.0, 5.0, 10.0]
CASES = ["center_x", "center_y"]
ORDER_CENTERS = {
    "zero_order": (0.0, 0.0),
    "plus_target_order": (TARGET_UX, 0.0),
    "minus_target_order": (-TARGET_UX, 0.0),
}
COMPONENTS = ["Ex_target", "Ey_leakage", "transverse_total", "vector_total"]

PEAK_FIELDS = [
    "case_id",
    "candidate_id",
    "component",
    "peak_ux",
    "peak_uy",
    "peak_theta_x_deg",
    "peak_theta_y_deg",
    "peak_polar_angle_deg",
    "nearest_expected_order",
    "nearest_order_angular_distance_deg",
    "peak_close_to",
    "peak_value",
    "steering_present_within_3deg",
    "notes",
]

ORDER_FIELDS = [
    "case_id",
    "candidate_id",
    "order_id",
    "order_center_ux",
    "order_center_uy",
    "order_center_theta_x_deg",
    "cone_deg",
    "target_LP_power",
    "leakage_LP_power",
    "LP_fraction",
    "target_to_leakage_ratio",
    "total_vector_power",
    "target_order_fraction_of_all_orders",
    "leakage_order_fraction_of_all_orders",
    "cone_overlap_note",
    "extraction_status",
    "notes",
]

INCOHERENT_FIELDS = [
    "candidate_id",
    "position",
    "order_id",
    "order_center_ux",
    "order_center_theta_x_deg",
    "cone_deg",
    "target_LP_power_xdip",
    "target_LP_power_ydip",
    "leakage_LP_power_xdip",
    "leakage_LP_power_ydip",
    "target_LP_power_incoherent",
    "leakage_LP_power_incoherent",
    "LP_fraction_incoherent",
    "target_to_leakage_ratio_incoherent",
    "total_vector_power_incoherent",
    "pass_lp_fraction_gt_0p60",
    "failed_lp_fraction_lt_0p50",
    "notes",
]


def write_csv_rows(path: Path, rows: Iterable[dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def component_arrays(vector: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    arr = np.asarray(vector).squeeze()
    if arr.ndim < 3:
        raise ValueError(f"farfieldvector3d returned insufficient shape {arr.shape}")
    if arr.shape[-1] == 3:
        ex, ey, ez = arr[..., 0], arr[..., 1], arr[..., 2]
        axis = -1
    elif arr.shape[0] == 3:
        ex, ey, ez = arr[0], arr[1], arr[2]
        axis = 0
    else:
        raise ValueError(f"cannot infer Ex/Ey/Ez component axis from shape {arr.shape}")
    if not np.iscomplexobj(arr):
        raise ValueError("farfieldvector3d did not return complex data")
    return (
        np.asarray(ex, dtype=np.complex128).squeeze(),
        np.asarray(ey, dtype=np.complex128).squeeze(),
        np.asarray(ez, dtype=np.complex128).squeeze(),
        {"shape": list(arr.shape), "dtype": str(arr.dtype), "is_complex": True, "component_axis": axis},
    )


def direction_grid(ux: Any, uy: Any, shape: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
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
    raise ValueError(f"direction grid shape {xx.shape} does not match field shape {shape}")


def solid_angle_weights(xx: np.ndarray, yy: np.ndarray) -> np.ndarray:
    ux_values = np.unique(xx)
    uy_values = np.unique(yy)
    dux = float(np.median(np.abs(np.diff(ux_values)))) if ux_values.size > 1 else 1.0
    duy = float(np.median(np.abs(np.diff(uy_values)))) if uy_values.size > 1 else 1.0
    uz = np.sqrt(np.clip(1.0 - xx**2 - yy**2, 1e-12, None))
    return dux * duy / uz


def order_mask(xx: np.ndarray, yy: np.ndarray, order_ux: float, order_uy: float, cone_deg: float) -> np.ndarray:
    valid = xx**2 + yy**2 <= 1.0
    uz = np.sqrt(np.clip(1.0 - xx**2 - yy**2, 0.0, None))
    center_uz = math.sqrt(max(0.0, 1.0 - order_ux**2 - order_uy**2))
    dot = np.clip(xx * order_ux + yy * order_uy + uz * center_uz, -1.0, 1.0)
    separation = np.arccos(dot)
    return valid & (separation <= math.radians(cone_deg))


def angular_distance_deg(ux: float, uy: float, center_ux: float, center_uy: float) -> float:
    uz = math.sqrt(max(0.0, 1.0 - ux**2 - uy**2))
    center_uz = math.sqrt(max(0.0, 1.0 - center_ux**2 - center_uy**2))
    dot = max(-1.0, min(1.0, ux * center_ux + uy * center_uy + uz * center_uz))
    return math.degrees(math.acos(dot))


def intensity_components(ex: np.ndarray, ey: np.ndarray, ez: np.ndarray) -> dict[str, np.ndarray]:
    ex2 = np.abs(ex) ** 2
    ey2 = np.abs(ey) ** 2
    ez2 = np.abs(ez) ** 2
    return {
        "Ex_target": ex2,
        "Ey_leakage": ey2,
        "transverse_total": ex2 + ey2,
        "vector_total": ex2 + ey2 + ez2,
    }


def peak_rows(case_id: str, maps: dict[str, np.ndarray], xx: np.ndarray, yy: np.ndarray) -> list[dict[str, object]]:
    valid = xx**2 + yy**2 <= 1.0
    rows: list[dict[str, object]] = []
    for component in COMPONENTS:
        values = np.where(valid, maps[component], -np.inf)
        index = np.unravel_index(int(np.nanargmax(values)), values.shape)
        peak_ux = float(xx[index])
        peak_uy = float(yy[index])
        distances = {
            order_id: angular_distance_deg(peak_ux, peak_uy, center[0], center[1])
            for order_id, center in ORDER_CENTERS.items()
        }
        nearest = min(distances, key=distances.get)
        nearest_distance = distances[nearest]
        label = nearest if nearest_distance <= 3.0 else "other"
        close_to = {
            "plus_target_order": "+10deg",
            "zero_order": "0deg",
            "minus_target_order": "-10deg",
            "other": "other",
        }[label]
        rows.append(
            {
                "case_id": case_id,
                "candidate_id": CANDIDATE_ID,
                "component": component,
                "peak_ux": peak_ux,
                "peak_uy": peak_uy,
                "peak_theta_x_deg": math.degrees(math.asin(max(-1.0, min(1.0, peak_ux)))),
                "peak_theta_y_deg": math.degrees(math.asin(max(-1.0, min(1.0, peak_uy)))),
                "peak_polar_angle_deg": math.degrees(math.asin(min(1.0, math.hypot(peak_ux, peak_uy)))),
                "nearest_expected_order": label,
                "nearest_order_angular_distance_deg": nearest_distance,
                "peak_close_to": close_to,
                "peak_value": float(maps[component][index]),
                "steering_present_within_3deg": component == "Ex_target" and label in {"plus_target_order", "minus_target_order"},
                "notes": "global propagating-region peak on the sampled ux/uy grid",
            }
        )
    return rows


def cone_rows(case_id: str, maps: dict[str, np.ndarray], xx: np.ndarray, yy: np.ndarray) -> list[dict[str, object]]:
    weights = solid_angle_weights(xx, yy)
    rows: list[dict[str, object]] = []
    for cone in CONES_DEG:
        cone_rows_for_case: list[dict[str, object]] = []
        for order_id, (center_ux, center_uy) in ORDER_CENTERS.items():
            mask = order_mask(xx, yy, center_ux, center_uy, cone)
            if not np.any(mask):
                raise ValueError(f"empty mask for {case_id} {order_id} +/-{cone} deg")
            target = float(np.sum(maps["Ex_target"][mask] * weights[mask]))
            leakage = float(np.sum(maps["Ey_leakage"][mask] * weights[mask]))
            total_vector = float(np.sum(maps["vector_total"][mask] * weights[mask]))
            denom = target + leakage
            cone_rows_for_case.append(
                {
                    "case_id": case_id,
                    "candidate_id": CANDIDATE_ID,
                    "order_id": order_id,
                    "order_center_ux": center_ux,
                    "order_center_uy": center_uy,
                    "order_center_theta_x_deg": math.degrees(math.asin(center_ux)),
                    "cone_deg": cone,
                    "target_LP_power": target,
                    "leakage_LP_power": leakage,
                    "LP_fraction": target / denom if denom else float("nan"),
                    "target_to_leakage_ratio": target / leakage if leakage else float("inf"),
                    "total_vector_power": total_vector,
                    "target_order_fraction_of_all_orders": "",
                    "leakage_order_fraction_of_all_orders": "",
                    "cone_overlap_note": "10deg order-centered cones overlap strongly" if cone >= 10 else ("5deg cones touch near midpoint" if cone >= 5 else "3deg cones are separated"),
                    "extraction_status": "complex_vector_ok",
                    "notes": "solid-angle weighted; Ez excluded from LP projection and included in total_vector_power",
                }
            )
        target_sum = sum(float(row["target_LP_power"]) for row in cone_rows_for_case)
        leakage_sum = sum(float(row["leakage_LP_power"]) for row in cone_rows_for_case)
        for row in cone_rows_for_case:
            row["target_order_fraction_of_all_orders"] = float(row["target_LP_power"]) / target_sum if target_sum else float("nan")
            row["leakage_order_fraction_of_all_orders"] = float(row["leakage_LP_power"]) / leakage_sum if leakage_sum else float("nan")
        rows.extend(cone_rows_for_case)
    return rows


def incoherent_rows(order_rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for order_id, (center_ux, _) in ORDER_CENTERS.items():
        for cone in CONES_DEG:
            xrow = next(row for row in order_rows if row["case_id"] == "center_x" and row["order_id"] == order_id and abs(flt(row["cone_deg"]) - cone) < 1e-9)
            yrow = next(row for row in order_rows if row["case_id"] == "center_y" and row["order_id"] == order_id and abs(flt(row["cone_deg"]) - cone) < 1e-9)
            tx = flt(xrow["target_LP_power"])
            ty = flt(yrow["target_LP_power"])
            lx = flt(xrow["leakage_LP_power"])
            ly = flt(yrow["leakage_LP_power"])
            target = tx + ty
            leakage = lx + ly
            denom = target + leakage
            fraction = target / denom if denom else float("nan")
            rows.append(
                {
                    "candidate_id": CANDIDATE_ID,
                    "position": "center",
                    "order_id": order_id,
                    "order_center_ux": center_ux,
                    "order_center_theta_x_deg": math.degrees(math.asin(center_ux)),
                    "cone_deg": cone,
                    "target_LP_power_xdip": tx,
                    "target_LP_power_ydip": ty,
                    "leakage_LP_power_xdip": lx,
                    "leakage_LP_power_ydip": ly,
                    "target_LP_power_incoherent": target,
                    "leakage_LP_power_incoherent": leakage,
                    "LP_fraction_incoherent": fraction,
                    "target_to_leakage_ratio_incoherent": target / leakage if leakage else float("inf"),
                    "total_vector_power_incoherent": flt(xrow["total_vector_power"]) + flt(yrow["total_vector_power"]),
                    "pass_lp_fraction_gt_0p60": fraction > 0.60,
                    "failed_lp_fraction_lt_0p50": fraction < 0.50,
                    "notes": "independent center_x/center_y powers summed incoherently; no field addition",
                }
            )
    return rows


def mechanism_classification(
    peaks: Sequence[dict[str, object]],
    order_rows: Sequence[dict[str, object]],
    incoherent: Sequence[dict[str, object]],
) -> dict[str, object]:
    x_peak = next(row for row in peaks if row["case_id"] == "center_x" and row["component"] == "Ex_target")
    y_peak = next(row for row in peaks if row["case_id"] == "center_y" and row["component"] == "Ey_leakage")
    steering_present = bool(x_peak["steering_present_within_3deg"])
    actual_order = str(x_peak["nearest_expected_order"]) if steering_present else "unresolved"
    sign_flip = actual_order == "minus_target_order"
    contamination_by_order: dict[str, dict[str, float]] = {}
    for order_id in ("plus_target_order", "minus_target_order"):
        ratios: dict[str, float] = {}
        for cone in (3.0, 5.0):
            xrow = next(row for row in order_rows if row["case_id"] == "center_x" and row["order_id"] == order_id and flt(row["cone_deg"]) == cone)
            yrow = next(row for row in order_rows if row["case_id"] == "center_y" and row["order_id"] == order_id and flt(row["cone_deg"]) == cone)
            ratios[str(int(cone))] = flt(yrow["leakage_LP_power"]) / flt(xrow["target_LP_power"]) if flt(xrow["target_LP_power"]) else float("inf")
        contamination_by_order[order_id] = ratios
    contaminated = max(contamination_by_order[actual_order].values()) >= 0.5 if steering_present else None
    actual_incoherent = [row for row in incoherent if row["order_id"] == actual_order] if steering_present else []
    by_cone = {flt(row["cone_deg"]): flt(row["LP_fraction_incoherent"]) for row in actual_incoherent}
    may_continue = steering_present and by_cone.get(3.0, 0.0) > 0.60 and by_cone.get(5.0, 0.0) > 0.60
    failed = any(value < 0.50 for value in by_cone.values()) if steering_present else None
    y_peak_order = str(y_peak["nearest_expected_order"])
    if not steering_present:
        primary = "class_C_no_steering"
    elif sign_flip:
        primary = "class_D_sign_flip"
    elif contaminated:
        primary = "class_B_target_order_contaminated"
    elif y_peak_order in {"zero_order", "minus_target_order", "other"}:
        primary = "class_A_angle_separated_leakage"
    else:
        primary = "class_B_target_order_contaminated"
    if primary == "class_A_angle_separated_leakage" and may_continue:
        recommendation = "Target order is comparatively clean; perform angular/order filtering diagnosis before considering DBR. +/-q may proceed only with separate approval."
    elif primary == "class_B_target_order_contaminated":
        recommendation = "Return to dimer/source-coupling mechanism diagnosis; do not run +/-q or add DBR/RCLED."
    elif primary == "class_C_no_steering":
        recommendation = "Diagnose finite-patch phase-ramp/source coupling and coordinate mapping; do not run +/-q or add DBR/RCLED."
    elif primary == "class_D_sign_flip":
        recommendation = "Resolve phase-gradient sign/coordinate convention before any +/-q run."
    else:
        recommendation = "Resolve extraction or coordinate consistency before further simulation."
    return {
        "primary_class": primary,
        "steering_present": steering_present,
        "actual_target_order": actual_order,
        "sign_flip": sign_flip,
        "center_y_leakage_peak_order": y_peak_order,
        "target_order_contaminated": contaminated,
        "contamination_ratio_yEy_over_xEx": contamination_by_order.get(actual_order),
        "contamination_ratio_by_expected_order": contamination_by_order,
        "actual_target_incoherent_lp_fraction": {str(int(key)): value for key, value in by_cone.items()},
        "order_resolved_center_may_continue": may_continue,
        "order_resolved_center_failed": failed,
        "recommendation": recommendation,
    }


def save_map(path: Path, title: str, values: np.ndarray, xx: np.ndarray, yy: np.ndarray, peak: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    valid = xx**2 + yy**2 <= 1.0
    maximum = float(np.nanmax(np.where(valid, values, np.nan)))
    normalized_db = 10.0 * np.log10(np.clip(values / maximum, 1e-6, None)) if maximum > 0 else np.full(values.shape, -60.0)
    fig, ax = plt.subplots(figsize=(6.4, 5.3), constrained_layout=True)
    mesh = ax.pcolormesh(xx, yy, np.where(valid, normalized_db, np.nan), shading="auto", cmap="magma", vmin=-40, vmax=0)
    fig.colorbar(mesh, ax=ax, label="Normalized component power (dB)")
    ax.scatter([0], [0], marker="o", facecolors="none", edgecolors="white", s=70, linewidths=1.3, label="zero")
    ax.scatter([TARGET_UX], [0], marker=">", c="#42d4f4", s=70, label="+target")
    ax.scatter([-TARGET_UX], [0], marker="<", c="#3cb44b", s=70, label="-target")
    ax.scatter([float(peak["peak_ux"])], [float(peak["peak_uy"])], marker="x", c="white", s=75, linewidths=1.5, label="global peak")
    ax.axhline(0, color="white", alpha=0.2, linewidth=0.7)
    ax.axvline(0, color="white", alpha=0.2, linewidth=0.7)
    ax.set_xlabel("$u_x$")
    ax.set_ylabel("$u_y$")
    ax.set_title(title)
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.75)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def build_report(classification: dict[str, object], peaks: Sequence[dict[str, object]], incoherent: Sequence[dict[str, object]]) -> str:
    x_peak = next(row for row in peaks if row["case_id"] == "center_x" and row["component"] == "Ex_target")
    y_peak = next(row for row in peaks if row["case_id"] == "center_y" and row["component"] == "Ey_leakage")
    lines = [
        "# Stage13-5 LP No-DBR Center Order-Resolved Mechanism Diagnosis",
        "",
        "## Boundary",
        "",
        "- No new FDTD simulation was run; Stage13-4 center_x/center_y FSPs were reopened read-only for extraction.",
        "- No +/-q cases, DBR, RCLED, geometry change, or optimization.",
        "- Complex Ex/Ey/Ez from farfieldvector3d was used; intensity-only farfield3d was not used.",
        "- Ez is excluded from LP projection and included only in total vector power.",
        "",
        "## Expected orders",
        "",
        f"- lambda = `{WAVELENGTH_NM}` nm; Lambda_x = `{SUPERCELL_PERIOD_X_NM}` nm.",
        f"- |u_target| = lambda/Lambda_x = `{TARGET_UX}`.",
        f"- |theta_target| = `{TARGET_THETA_DEG}` deg; uy = 0.",
        "- Angular centers analyzed: zero, +target, and -target; half-angle cones 3, 5, and 10 deg.",
        "",
        "## Peak diagnosis",
        "",
        f"- center_x Ex peak: ux `{x_peak['peak_ux']}`, uy `{x_peak['peak_uy']}`, theta_x `{x_peak['peak_theta_x_deg']}` deg, nearest `{x_peak['nearest_expected_order']}`.",
        f"- center_y Ey leakage peak: ux `{y_peak['peak_ux']}`, uy `{y_peak['peak_uy']}`, theta_x `{y_peak['peak_theta_x_deg']}` deg, nearest `{y_peak['nearest_expected_order']}`.",
        f"- Steering present within 3 deg: `{classification['steering_present']}`.",
        f"- Actual target-order sign: `{classification['actual_target_order']}`; sign flip: `{classification['sign_flip']}`.",
        "",
        "## Incoherent LP fraction at expected order centers",
        "",
        "- The actual target-order sign is unresolved because the center_x Ex global peak is not within 3 deg of either expected order center.",
        "- Therefore no actual-target LP_fraction is claimed; both expected centers are reported below.",
        "",
        "| order center | cone half-angle | LP_fraction_incoherent | pass >0.60 | failed <0.50 |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for order_id in ("plus_target_order", "minus_target_order"):
        for row in [item for item in incoherent if item["order_id"] == order_id]:
            lines.append(f"| {order_id} | {row['cone_deg']} | {row['LP_fraction_incoherent']} | {row['pass_lp_fraction_gt_0p60']} | {row['failed_lp_fraction_lt_0p50']} |")
    lines.extend(
        [
            "",
            "## Mechanism classification",
            "",
            f"- Primary class: `{classification['primary_class']}`.",
            f"- target_order_contaminated: `{classification['target_order_contaminated']}` (not classifiable while the actual target order is unresolved).",
            f"- y-Ey/x-Ex contamination ratios at both expected centers, 3/5 deg: `{json.dumps(classification['contamination_ratio_by_expected_order'])}`.",
            f"- order_resolved_center_may_continue: `{classification['order_resolved_center_may_continue']}`.",
            f"- order_resolved_center_failed: `{classification['order_resolved_center_failed']}`.",
            f"- Recommendation: {classification['recommendation']}",
            "",
            "## Jones/APCD evidence boundary",
            "",
            "- Orders were analyzed as finite-patch angular centers (zero, +target, -target), not periodic grating-order amplitudes.",
            "- An incident-wave order-resolved J_xy matrix was not constructed: center_x/center_y are independent dipole-source simulations and are combined incoherently.",
            "- alpha/beta -> alpha*/beta* conversion was not performed.",
            "- t_{alpha*<-alpha}^{order}: unavailable/not claimed.",
            "- Therefore this report diagnoses angular LP-power routing only; it does not claim full APCD Jones selectivity.",
            "",
        ]
    )
    return "\n".join(lines)


def build_extraction_notes(debug: dict[str, object]) -> str:
    return f"""# Stage13-5 Extraction Notes

- Input FSPs: existing Stage13-4 `stage13_4_center_x.fsp` and `stage13_4_center_y.fsp`.
- Lifecycle used: open hidden FDTD session, load saved FSP, extract monitor data, close. No `run`, save, or switch-to-layout call.
- API: `farfieldvector3d`, `farfieldux`, `farfielduy` on monitor `{FIELD_MONITOR}`.
- Grid: `{GRID_N} x {GRID_N}`.
- Complex extraction debug: `{json.dumps(debug, ensure_ascii=False)}`.
- LP target/leakage: solid-angle-weighted |Ex|^2 / |Ey|^2.
- Ez: excluded from LP projection; included in total vector power.
- Order-cone masks use true spherical angular distance from each order direction vector.
- Order centers: zero ux=0; plus ux={TARGET_UX}; minus ux={-TARGET_UX}; all uy=0.
- Cone half-angles: {CONES_DEG} deg.
- At 5 deg adjacent cones touch near their midpoint; 10 deg cones overlap strongly, so order-fraction columns are comparative rather than a disjoint power partition.
- Peak positions are global maxima over the valid propagating ux^2+uy^2<=1 region.
- PNG maps show each component normalized to its own peak in dB; raw peak values remain in the peak CSV.
- Raw complex arrays saved: False.
- No intensity-only farfield3d LP inference.
- No coherent addition of center_x and center_y fields; only power sums are used.
"""


def build_readme(classification: dict[str, object]) -> str:
    return f"""# Stage13-5 Center Order Diagnosis

Read-only post-processing of Stage13-4 center_x/center_y FSP results. No FDTD run was performed.

- Expected order centers: ux = 0, +{TARGET_UX}, -{TARGET_UX}; uy=0.
- Cones: 3, 5, 10 degrees.
- Complex Ex/Ey/Ez only; Ez enters total vector power but not LP projection.
- Primary classification: `{classification['primary_class']}`.
- Recommendation: {classification['recommendation']}
- Large FSP/log files remain ignored and must not be committed.
"""
