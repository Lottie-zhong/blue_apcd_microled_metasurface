from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
REPORT = BASE / "reports/iar4_orientation_causal_control_truth_v1"
OLD_PAIR_DIR = BASE / "reports/integrated_aware_lp_initial_truth_v1/pairs/IAR4"
NEW_PAIR_DIR = REPORT / "pairs/IAR4-OC1"
UTC = dt.timezone.utc

METRICS: dict[str, str] = {
    "pair_DoLP": "DoLP_pair",
    "C_source": "C_source",
    "C_angular": "angular::C_angular",
    "full_angle_DoLP": "angular::full_angle_pair_DoLP",
    "upward_source_normalized_power": "upward_source_normalized_power_pair",
    "useful_LP": "useful_LP_axisfree_pair",
    "P_LP_over_S0": "useful_LP_over_S0_pair",
    "cone_5deg_DoLP": "angular::normal_5deg_DoLP",
    "cone_10deg_DoLP": "angular::normal_10deg_DoLP",
    "cone_20deg_DoLP": "angular::normal_20deg_DoLP",
}
PRIMARY_PURITY = ["pair_DoLP", "C_source", "C_angular", "full_angle_DoLP"]
PRIMARY_POWER = ["upward_source_normalized_power", "useful_LP"]
EFFICIENCY = ["P_LP_over_S0"]
ALL_CAUSAL = list(METRICS)


def now() -> str:
    return dt.datetime.now(UTC).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temp.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"EMPTY_CSV:{path}")
    return rows


def finite(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"NONNUMERIC:{key}") from exc
    if not math.isfinite(value):
        raise RuntimeError(f"NONFINITE:{key}")
    return value


def sign(value: float) -> str:
    if value > 0.0:
        return "+"
    if value < 0.0:
        return "-"
    return "0"


def stats(values: list[float]) -> dict[str, Any]:
    if not values:
        raise RuntimeError("EMPTY_STATS")
    positive = sum(value > 0.0 for value in values)
    negative = sum(value < 0.0 for value in values)
    zero = len(values) - positive - negative
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "median": median(values),
        "minimum": min(values),
        "maximum": max(values),
        "positive_count": positive,
        "negative_count": negative,
        "zero_count": zero,
        "fraction_delta_gt_0_OC1_better": positive / len(values),
        "fraction_delta_lt_0_IAR4_better": negative / len(values),
        "fraction_delta_eq_0": zero / len(values),
    }


def join_pair(directory: Path) -> dict[float, dict[str, str]]:
    pair = read_csv(directory / "pair_wavelength_metrics.csv")
    angular = read_csv(directory / "angular_cancellation_metrics.csv")
    angular_by_wavelength = {round(finite(row, "wavelength_nm"), 9): row for row in angular}
    joined: dict[float, dict[str, str]] = {}
    for row in pair:
        wavelength = round(finite(row, "wavelength_nm"), 9)
        if wavelength not in angular_by_wavelength:
            raise RuntimeError(f"ANGULAR_WAVELENGTH_MISSING:{directory}:{wavelength}")
        joined[wavelength] = {
            **row,
            **{f"angular::{key}": value for key, value in angular_by_wavelength[wavelength].items() if key != "wavelength_nm"},
        }
    if len(pair) != 101 or len(angular) != 101 or len(joined) != 101:
        raise RuntimeError(f"EXPECTED_101_POINTS:{directory}:{len(pair)}:{len(angular)}:{len(joined)}")
    return joined


def sign_transitions(wavelengths: list[float], values: list[float]) -> dict[str, Any]:
    transitions: list[dict[str, Any]] = []
    for left_wl, right_wl, left_value, right_value in zip(wavelengths, wavelengths[1:], values, values[1:]):
        left_sign, right_sign = sign(left_value), sign(right_value)
        if left_sign != right_sign and left_sign != "0" and right_sign != "0":
            transitions.append({
                "from_wavelength_nm": left_wl,
                "to_wavelength_nm": right_wl,
                "from_sign": left_sign,
                "to_sign": right_sign,
            })
    return {
        "sign_flip_wavelengths_nm": [row["to_wavelength_nm"] for row in transitions],
        "sign_flip_intervals_nm": transitions,
    }


def metric_sign_relation(rows: list[dict[str, Any]], left: str, right: str) -> dict[str, Any]:
    left_values = [row[left] for row in rows]
    right_values = [row[right] for row in rows]
    same = sum(sign(a) == sign(b) for a, b in zip(left_values, right_values))
    opposite = sum(sign(a) != sign(b) and sign(a) != "0" and sign(b) != "0" for a, b in zip(left_values, right_values))
    return {
        "left_metric": left,
        "right_metric": right,
        "points": len(rows),
        "same_sign_count": same,
        "opposite_nonzero_sign_count": opposite,
        "same_sign_fraction": same / len(rows),
        "opposite_nonzero_sign_fraction": opposite / len(rows),
    }


def quadrant_summary(rows: list[dict[str, Any]], purity: str, power: str) -> dict[str, Any]:
    quadrants = {"purity_positive_power_positive": [], "purity_positive_power_negative": [],
                 "purity_negative_power_positive": [], "purity_negative_power_negative": [],
                 "zero_involved": []}
    for row in rows:
        p_sign, q_sign = sign(row[purity]), sign(row[power])
        if p_sign == "0" or q_sign == "0":
            quadrants["zero_involved"].append(row["wavelength_nm"])
        elif p_sign == "+" and q_sign == "+":
            quadrants["purity_positive_power_positive"].append(row["wavelength_nm"])
        elif p_sign == "+" and q_sign == "-":
            quadrants["purity_positive_power_negative"].append(row["wavelength_nm"])
        elif p_sign == "-" and q_sign == "+":
            quadrants["purity_negative_power_positive"].append(row["wavelength_nm"])
        else:
            quadrants["purity_negative_power_negative"].append(row["wavelength_nm"])
    return {
        "purity_metric": purity,
        "power_metric": power,
        "counts": {key: len(value) for key, value in quadrants.items()},
        "wavelengths_nm": quadrants,
    }


def scope_rows(deltas: list[dict[str, Any]], low: float, high: float) -> list[dict[str, Any]]:
    return [row for row in deltas if low <= row["wavelength_nm"] <= high]


def scope_audit(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    wavelengths = [row["wavelength_nm"] for row in rows]
    metric_audit: dict[str, Any] = {}
    for metric in METRICS:
        values = [row[metric] for row in rows]
        metric_audit[metric] = {**stats(values), **sign_transitions(wavelengths, values)}
    relations = {
        "pair_DoLP_vs_C_source": metric_sign_relation(rows, "pair_DoLP", "C_source"),
        "C_angular_vs_C_source": metric_sign_relation(rows, "C_angular", "C_source"),
    }
    power_vs_purity = {
        "primary_power_metrics": {
            f"{purity}_vs_{power}": quadrant_summary(rows, purity, power)
            for purity in PRIMARY_PURITY for power in PRIMARY_POWER
        },
        "efficiency_metric_P_LP_over_S0": {
            purity: quadrant_summary(rows, purity, "P_LP_over_S0") for purity in PRIMARY_PURITY
        },
    }
    return {
        "label": label,
        "wavelength_min_nm": min(wavelengths),
        "wavelength_max_nm": max(wavelengths),
        "points": len(rows),
        "metrics": metric_audit,
        "sign_consistency": relations,
        "power_vs_purity_quadrants": power_vs_purity,
    }


def anchor_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    anchor = next(row for row in rows if row["wavelength_nm"] == 450.0)
    neighbors = [row for row in rows if row["wavelength_nm"] != 450.0]
    return {
        "anchor_450nm_signs": {metric: sign(anchor[metric]) for metric in METRICS},
        "anchor_450nm_values": {metric: anchor[metric] for metric in METRICS},
        "445_455_neighbor_sign_counts": {
            metric: {
                "positive": sum(row[metric] > 0.0 for row in neighbors),
                "negative": sum(row[metric] < 0.0 for row in neighbors),
                "zero": sum(row[metric] == 0.0 for row in neighbors),
            }
            for metric in METRICS
        },
    }


def choose_verdict(scope_445_455: dict[str, Any], scope_full: dict[str, Any], anchor: dict[str, Any]) -> str:
    window_metrics = scope_445_455["metrics"]
    all_window_smaller = all(
        item["negative_count"] == item["count"] for item in window_metrics.values()
    )
    any_window_flip = any(item["sign_flip_intervals_nm"] for item in window_metrics.values())
    center_smaller = all(anchor["anchor_450nm_signs"][metric] == "-" for metric in ALL_CAUSAL)
    full_nonuniform = any(
        item["positive_count"] > 0 and item["negative_count"] > 0
        for item in scope_full["metrics"].values()
    )
    if all_window_smaller:
        return "ORIENTATION_CAUSAL_LEVER_SUPPORTED_BLUE_WINDOW_SMALLER_DELTA_THETA_FAVORED"
    if any_window_flip:
        return "ORIENTATION_CAUSAL_EFFECT_WAVELENGTH_DEPENDENT"
    if center_smaller and full_nonuniform:
        return "ORIENTATION_CAUSAL_LEVER_SUPPORTED_AT_450NM_BROADBAND_NONUNIFORM"
    return "ORIENTATION_CAUSAL_EFFECT_WAVELENGTH_DEPENDENT"


def update_report(path: Path, text: str) -> None:
    marker = "\n## Scoped causal-scope audit (zero-solver)\n"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip() + "\n"
    path.write_text(existing + marker + text, encoding="utf-8")


def main() -> int:
    old = join_pair(OLD_PAIR_DIR)
    new = join_pair(NEW_PAIR_DIR)
    wavelengths = sorted(set(old) & set(new))
    if wavelengths != list(old) or wavelengths != list(new):
        raise RuntimeError("IAR4_OC1_GRID_MISMATCH")

    deltas: list[dict[str, Any]] = []
    for wavelength in wavelengths:
        row: dict[str, Any] = {"wavelength_nm": wavelength}
        for metric, key in METRICS.items():
            old_value, new_value = finite(old[wavelength], key), finite(new[wavelength], key)
            row[metric] = new_value - old_value
            row[f"{metric}__IAR4"] = old_value
            row[f"{metric}__IAR4_OC1"] = new_value
            row[f"{metric}__sign"] = sign(row[metric])
        deltas.append(row)

    scopes = {
        "A_450_nm_exact": scope_rows(deltas, 450.0, 450.0),
        "B_445_455_nm_unweighted_diagnostic": scope_rows(deltas, 445.0, 455.0),
        "C_400_500_nm_full_diagnostic": scope_rows(deltas, 400.0, 500.0),
    }
    audited = {name: scope_audit(rows, name) for name, rows in scopes.items()}
    anchor = anchor_context(scopes["B_445_455_nm_unweighted_diagnostic"])
    verdict = choose_verdict(audited["B_445_455_nm_unweighted_diagnostic"], audited["C_400_500_nm_full_diagnostic"], anchor)

    old_summary_path = REPORT / "iar4_vs_oc1_causal_contrast_summary.json"
    old_summary = load_json(old_summary_path)
    old_label = old_summary.get("descriptive_interpretation_candidate")
    tradeoff_audit = {
        "original_label": old_label,
        "recommended_scoped_label": "FULL_BAND_DESCRIPTIVE_NONUNIFORMITY",
        "top_level_verdict_suitability": "NOT_SUITABLE_AS_TOP_LEVEL_CAUSAL_VERDICT",
        "reason": "Full-band deltas are wavelength-nonuniform; quadrant counts are reported per metric pair without composite scoring.",
        "full_band_purity_vs_power_quadrants": audited["C_400_500_nm_full_diagnostic"]["power_vs_purity_quadrants"],
        "445_455_purity_vs_power_quadrants": audited["B_445_455_nm_unweighted_diagnostic"]["power_vs_purity_quadrants"],
        "450nm_anchor_isolation": anchor,
    }

    audit = {
        "schema": "PAPER_A_IAR4_OC1_CAUSAL_SCOPE_AUDIT_V1",
        "status": "PASS",
        "truth_scope": "existing current Native-M1 IAR4 versus IAR4-OC1 integrated FDTD truth only",
        "strict_causal_comparator": "IAR4 versus IAR4-OC1; only delta_theta differs",
        "input_provenance": {
            "IAR4_pair_wavelength_metrics_csv": {"path": str(OLD_PAIR_DIR / "pair_wavelength_metrics.csv"), "sha256": sha256(OLD_PAIR_DIR / "pair_wavelength_metrics.csv")},
            "IAR4_angular_cancellation_metrics_csv": {"path": str(OLD_PAIR_DIR / "angular_cancellation_metrics.csv"), "sha256": sha256(OLD_PAIR_DIR / "angular_cancellation_metrics.csv")},
            "IAR4_OC1_pair_wavelength_metrics_csv": {"path": str(NEW_PAIR_DIR / "pair_wavelength_metrics.csv"), "sha256": sha256(NEW_PAIR_DIR / "pair_wavelength_metrics.csv")},
            "IAR4_OC1_angular_cancellation_metrics_csv": {"path": str(NEW_PAIR_DIR / "angular_cancellation_metrics.csv"), "sha256": sha256(NEW_PAIR_DIR / "angular_cancellation_metrics.csv")},
            "prior_causal_contrast_summary_json": {"path": str(old_summary_path), "sha256": sha256(old_summary_path)},
        },
        "scopes": audited,
        "anchor_context": anchor,
        "tradeoff_label_audit": tradeoff_audit,
        "final_scoped_verdict": verdict,
        "W_emit": "UNRESOLVED_NOT_USED",
        "historical_28nm_Gaussian": "NOT_USED",
        "composite_score": "NOT_USED",
        "promotion_threshold": "NOT_CREATED",
        "solver_run_called": False,
        "solver_entered": 0,
        "timestamp_utc": now(),
    }
    write_json(REPORT / "causal_scope_audit.json", audit)

    csv_path = REPORT / "causal_scope_spectral_deltas.csv"
    fields: list[str] = []
    for row in deltas:
        for field in row:
            if field not in fields:
                fields.append(field)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(deltas)

    validation = {
        "schema": "PAPER_A_IAR4_OC1_CAUSAL_SCOPE_VALIDATION_V1",
        "status": "PASS",
        "input_pair_grids": {"IAR4": len(old), "IAR4_OC1": len(new)},
        "input_files_hashed": True,
        "full_scope_points": len(scopes["C_400_500_nm_full_diagnostic"]),
        "window_445_455_points": len(scopes["B_445_455_nm_unweighted_diagnostic"]),
        "anchor_450_present": len(scopes["A_450_nm_exact"]) == 1,
        "all_deltas_finite": all(math.isfinite(value) for row in deltas for key, value in row.items() if key != "wavelength_nm" and not key.endswith("__sign")),
        "sign_flip_fields_present": all("sign_flip_intervals_nm" in item for scope in audited.values() for item in scope["metrics"].values()),
        "no_W_emit": True,
        "no_historical_28nm_Gaussian": True,
        "no_composite_score": True,
        "no_new_promotion_threshold": True,
        "solver_run_called": False,
        "solver_entered": 0,
        "timestamp_utc": now(),
    }
    write_json(REPORT / "causal_scope_validation.json", validation)

    report = [
        "This zero-solver audit reads only the existing 101-point IAR4 and IAR4-OC1 truth.",
        "The 445–455 nm scope is an unweighted diagnostic window, not production W_emit weighting.",
        "W_emit and the historical 28-nm Gaussian remain unresolved and were not used.",
        "",
        f"Final scoped verdict: `{verdict}`.",
        f"The prior descriptive label `{old_label}` is retained in provenance but downgraded to `FULL_BAND_DESCRIPTIVE_NONUNIFORMITY`; it is not a top-level causal verdict.",
        "The preserved `terminal_failure.json` records an earlier analysis-only NameError; it is superseded by the later `terminal_success.json` and is not a physics failure or solver replay.",
        "",
        "Delta convention: OC1 minus IAR4. Complete per-wavelength values and sign-flip intervals are in `causal_scope_spectral_deltas.csv` and `causal_scope_audit.json`.",
        "No composite score, promotion threshold, solver, replay, RCWA, or ML was introduced.",
    ]
    update_report(REPORT / "final_report.md", "\n".join(report) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
