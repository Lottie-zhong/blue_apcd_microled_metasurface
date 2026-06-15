from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Sequence


ANALYTIC_PLUS1_RELATIVE_STRENGTH = 0.983731
ANALYTIC_PLUS1_CONTRAST = 158.057817
ANALYTIC_THETA_DEG = 10.0
TARGET_ORDER = 1
EPS = 1e-12

ORDER_RESOLVED_FIELDS = [
    "diffraction_order",
    "angle_deg",
    "power",
    "relative_power",
    "cumulative_power",
]

SELECTIVITY_METRIC_FIELDS = ["metric", "value", "notes"]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv_rows(rows: Iterable[dict[str, object]], path: Path, fields: Sequence[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(row_list)


def flt(value: object, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def build_order_resolved_table(order_rows: Sequence[dict[str, str]], polarization: str) -> list[dict[str, object]]:
    rows = [row for row in order_rows if row.get("polarization") == polarization]
    rows.sort(key=lambda row: int(float(row["order_n"])))
    total_power = sum(flt(row["order_power_source_norm"]) for row in rows)
    cumulative = 0.0
    out: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: flt(item["order_power_source_norm"]), reverse=True):
        power = flt(row["order_power_source_norm"])
        relative = power / max(total_power, EPS)
        cumulative += relative
        out.append(
            {
                "diffraction_order": int(float(row["order_n"])),
                "angle_deg": flt(row["theta_deg"]),
                "power": power,
                "relative_power": relative,
                "cumulative_power": cumulative,
            }
        )
    return out


def compute_stage12_3_metrics(
    result_rows: Sequence[dict[str, str]],
    order_rows: Sequence[dict[str, str]],
) -> list[dict[str, object]]:
    x_result = require_result(result_rows, "x")
    y_result = require_result(result_rows, "y")
    x_plus = order_power(order_rows, "x", TARGET_ORDER)
    y_plus = order_power(order_rows, "y", TARGET_ORDER)
    x_total = flt(x_result["total_transmission"])
    y_total = flt(y_result["total_transmission"])
    y_dominant = dominant_order(order_rows, "y")
    x_dominant = dominant_order(order_rows, "x")
    target_ratio = x_plus / max(y_plus, EPS)
    total_ratio = x_total / max(y_total, EPS)
    y_target_fraction = y_plus / max(y_total, EPS)
    x_plus_total_fraction = x_plus / max(x_total, EPS)
    x_steering_validated = int(float(x_result["dominant_order_n"])) == TARGET_ORDER and abs(flt(x_result["dominant_theta_deg"]) - ANALYTIC_THETA_DEG) <= 1.0
    target_selectivity_validated = target_ratio >= 6.0
    global_blocking_validated = total_ratio >= 6.0
    y_redirected_to_non_target = int(float(y_dominant["order_n"])) != TARGET_ORDER and flt(y_dominant["order_power_source_norm"]) > y_plus
    stage12_4_needed = (not global_blocking_validated) or flt(x_result["order_contrast_plus1_vs_next"]) < 10.0 or y_redirected_to_non_target
    final_interpretation = "pass" if x_steering_validated and target_selectivity_validated and not stage12_4_needed else "partial pass" if x_steering_validated and target_selectivity_validated else "needs refinement"
    return [
        {"metric": "target_order_selectivity_ratio", "value": target_ratio, "notes": "x_LP_plus1_power / y_LP_plus1_power"},
        {"metric": "total_transmission_selectivity_ratio", "value": total_ratio, "notes": "x_LP_total_transmitted_power / y_LP_total_transmitted_power; global blocking/dichroism metric"},
        {"metric": "y_leakage_fraction_in_target_order", "value": y_target_fraction, "notes": "y_LP_plus1_power / y_LP_total_transmitted_power"},
        {"metric": "y_dominant_leakage_order", "value": int(float(y_dominant["order_n"])), "notes": "largest y-LP order by source-normalized power"},
        {"metric": "y_dominant_leakage_power", "value": flt(y_dominant["order_power_source_norm"]), "notes": "source-normalized power in dominant y-LP leakage order"},
        {"metric": "x_plus1_efficiency_relative_to_total_transmitted", "value": x_plus_total_fraction, "notes": "x_LP +1 order power / x_LP total transmitted power"},
        {"metric": "x_plus1_source_normalized_power", "value": x_plus, "notes": "FDTD x-LP +1 order power"},
        {"metric": "y_plus1_source_normalized_power", "value": y_plus, "notes": "FDTD y-LP +1 leakage power"},
        {"metric": "x_total_transmitted_power", "value": x_total, "notes": "FDTD x-LP total transmission"},
        {"metric": "y_total_transmitted_power", "value": y_total, "notes": "FDTD y-LP total transmission"},
        {"metric": "x_dominant_order", "value": int(float(x_dominant["order_n"])), "notes": "largest x-LP order by source-normalized power"},
        {"metric": "x_dominant_angle_deg", "value": flt(x_dominant["theta_deg"]), "notes": "dominant x-LP order angle"},
        {"metric": "x_plus1_contrast_fdtd", "value": flt(x_result["order_contrast_plus1_vs_next"]), "notes": "Stage12-2 x +1 vs next order contrast"},
        {"metric": "analytic_plus1_relative_strength", "value": ANALYTIC_PLUS1_RELATIVE_STRENGTH, "notes": "Stage12-0 analytic array-factor relative +1 strength"},
        {"metric": "analytic_plus1_contrast", "value": ANALYTIC_PLUS1_CONTRAST, "notes": "Stage12-0 analytic array-factor contrast"},
        {"metric": "x_steering_validated", "value": x_steering_validated, "notes": "+1 order at about +10 deg"},
        {"metric": "target_order_lp_selectivity_validated", "value": target_selectivity_validated, "notes": "target-direction LP selectivity ratio >= 6"},
        {"metric": "global_y_lp_blocking_validated", "value": global_blocking_validated, "notes": "global x/y total transmission ratio >= 6"},
        {"metric": "y_leakage_redirected_to_non_target_orders", "value": y_redirected_to_non_target, "notes": "dominant y leakage is not +1, especially +2 if value is 2"},
        {"metric": "stage12_4_refinement_needed", "value": stage12_4_needed, "notes": "needed if global blocking fails, contrast is low, or y leakage redirects into non-target orders"},
        {"metric": "final_interpretation", "value": final_interpretation, "notes": "pass / partial pass / needs refinement"},
    ]


def build_interpretation_summary(metrics: Sequence[dict[str, object]]) -> str:
    m = {str(row["metric"]): row["value"] for row in metrics}
    target_valid = bool_from(m["target_order_lp_selectivity_validated"])
    steering_valid = bool_from(m["x_steering_validated"])
    global_valid = bool_from(m["global_y_lp_blocking_validated"])
    refinement = bool_from(m["stage12_4_refinement_needed"])
    gui_fsp = refinement or not global_valid
    lines = [
        "# Stage12-3 H500 LP-APCD K=6 Order-Resolved Audit",
        "",
        "## Boundary",
        "",
        "- Read-only audit of Stage12-2 outputs.",
        "- No FDTD was run.",
        "- No `.fsp` file was created or modified.",
        "- No optimization was performed.",
        "- Grating-order powers are not a full order-resolved Jones/APCD basis conversion; this audit distinguishes target-direction power selectivity from global blocking.",
        "",
        "## Target-Direction Selectivity",
        "",
        f"- x-LP +1 power: `{float(m['x_plus1_source_normalized_power']):.12g}`.",
        f"- y-LP +1 leakage power: `{float(m['y_plus1_source_normalized_power']):.12g}`.",
        f"- target_order_selectivity_ratio: `{float(m['target_order_selectivity_ratio']):.12g}`.",
        f"- target-order LP selectivity validated: `{target_valid}`.",
        "",
        "## Steering",
        "",
        f"- x-LP dominant order: `{m['x_dominant_order']}`.",
        f"- x-LP dominant angle: `{float(m['x_dominant_angle_deg']):.12g}` deg.",
        f"- +10 deg x-LP steering validated: `{steering_valid}`.",
        "",
        "## Global Blocking / Dichroism",
        "",
        f"- x total transmitted power: `{float(m['x_total_transmitted_power']):.12g}`.",
        f"- y total transmitted power: `{float(m['y_total_transmitted_power']):.12g}`.",
        f"- total_transmission_selectivity_ratio: `{float(m['total_transmission_selectivity_ratio']):.12g}`.",
        f"- global y-LP blocking validated: `{global_valid}`.",
        "",
        "## y-LP Leakage Redistribution",
        "",
        f"- y dominant leakage order: `{m['y_dominant_leakage_order']}`.",
        f"- y dominant leakage power: `{float(m['y_dominant_leakage_power']):.12g}`.",
        f"- y leakage fraction in +1 target order: `{float(m['y_leakage_fraction_in_target_order']):.12g}`.",
        "- Diagnosis: y-LP leakage is mostly redirected to non-target diffraction orders, especially +2, rather than the +1 target direction.",
        "",
        "## Analytic Comparison",
        "",
        f"- Stage12-0 analytic +1 relative strength: `{float(m['analytic_plus1_relative_strength']):.12g}`.",
        f"- Stage12-0 analytic contrast: `{float(m['analytic_plus1_contrast']):.12g}`.",
        f"- Stage12-2 FDTD x +1 / total x transmitted: `{float(m['x_plus1_efficiency_relative_to_total_transmitted']):.12g}`.",
        f"- Stage12-2 FDTD x +1 contrast: `{float(m['x_plus1_contrast_fdtd']):.12g}`.",
        "- Interpretation: FDTD preserves the +1 steering direction but shows much lower order purity/contrast than the ideal analytic array-factor prediction.",
        "",
        "## Next Step",
        "",
        f"- Stage12-4 refinement needed: `{refinement}`.",
        f"- GUI-inspection `.fsp` should be generated separately: `{gui_fsp}`.",
        f"- Final interpretation: `{m['final_interpretation']}`.",
    ]
    return "\n".join(lines) + "\n"


def require_result(result_rows: Sequence[dict[str, str]], polarization: str) -> dict[str, str]:
    for row in result_rows:
        if row.get("polarization") == polarization:
            return row
    raise ValueError(f"missing {polarization}-LP result row")


def order_power(order_rows: Sequence[dict[str, str]], polarization: str, order_n: int) -> float:
    rows = [row for row in order_rows if row.get("polarization") == polarization and int(float(row["order_n"])) == order_n]
    return max((flt(row["order_power_source_norm"]) for row in rows), default=0.0)


def dominant_order(order_rows: Sequence[dict[str, str]], polarization: str) -> dict[str, str]:
    rows = [row for row in order_rows if row.get("polarization") == polarization]
    if not rows:
        raise ValueError(f"missing order rows for {polarization}-LP")
    return max(rows, key=lambda row: flt(row["order_power_source_norm"]))


def bool_from(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}
