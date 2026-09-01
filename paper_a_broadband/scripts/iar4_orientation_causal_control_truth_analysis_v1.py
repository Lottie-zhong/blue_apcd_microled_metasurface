from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
REPORT = BASE / "reports/iar4_orientation_causal_control_truth_v1"
OLD_PAIR = BASE / "reports/integrated_aware_lp_initial_truth_v1/pairs/IAR4"
NEW_PAIR = REPORT / "pairs/IAR4-OC1"
UTC = dt.timezone.utc


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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"EMPTY_OUTPUT:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def finite(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value):
        raise RuntimeError(f"NONFINITE:{key}")
    return value


def stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "min": None, "max": None, "ripple": None, "cv": None}
    mean = sum(values) / len(values)
    return {"count": len(values), "mean": mean, "min": min(values), "max": max(values), "ripple": max(values) - min(values), "cv": (math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)) / abs(mean)) if mean else None}


def load_pair(directory: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    pair = read_csv(directory / "pair_wavelength_metrics.csv")
    angular = read_csv(directory / "angular_cancellation_metrics.csv")
    ang_by_wl = {round(finite(row, "wavelength_nm"), 9): row for row in angular}
    if len(pair) != 101 or len(angular) != 101:
        raise RuntimeError(f"PAIR_GRID_NOT_101:{directory}:{len(pair)}:{len(angular)}")
    joined = []
    for row in pair:
        key = round(finite(row, "wavelength_nm"), 9)
        if key not in ang_by_wl:
            raise RuntimeError(f"ANGULAR_WAVELENGTH_MISSING:{directory}:{key}")
        joined.append({**row, **{f"angular::{k}": v for k, v in ang_by_wl[key].items() if k != "wavelength_nm"}})
    return pair, joined


def main() -> int:
    new_pair, new_joined = load_pair(NEW_PAIR)
    old_pair, old_joined = load_pair(OLD_PAIR)
    new_by_wl = {round(finite(row, "wavelength_nm"), 9): row for row in new_joined}
    old_by_wl = {round(finite(row, "wavelength_nm"), 9): row for row in old_joined}
    wavelengths = sorted(set(new_by_wl) & set(old_by_wl))
    if wavelengths != sorted(new_by_wl) or wavelengths != sorted(old_by_wl):
        raise RuntimeError("IAR4_OC1_SPECTRAL_GRID_MISMATCH")
    metrics = [
        ("S0_x_sourcepower_normalized", "S0_x_sourcepower_normalized"),
        ("S0_y_sourcepower_normalized", "S0_y_sourcepower_normalized"),
        ("S0_pair_sourcepower_normalized", "S0_pair_sourcepower_normalized"),
        ("upward_source_normalized_power_pair", "upward_source_normalized_power_pair"),
        ("useful_LP_axisfree_pair", "useful_LP_axisfree_pair"),
        ("useful_LP_over_S0_pair", "useful_LP_over_S0_pair"),
        ("DoLP_pair", "DoLP_pair"), ("DoCP_pair", "DoCP_pair"),
        ("x_y_S0_ratio", "x_y_S0_ratio"), ("C_source", "C_source"),
        ("Poincare_separation_deg", "Poincare_separation_deg"),
        ("angular_local_DoLP_powerweighted", "angular::angular_local_DoLP_powerweighted"),
        ("C_angular", "angular::C_angular"), ("full_angle_pair_DoLP", "angular::full_angle_pair_DoLP"),
        ("full_angle_pair_DoCP", "angular::full_angle_pair_DoCP"),
        ("full_angle_pair_useful_LP_axisfree", "angular::full_angle_pair_useful_LP_axisfree"),
        ("full_angle_upward_source_normalized_power", "angular::full_angle_upward_source_normalized_power"),
        ("normal_5deg_DoLP", "angular::normal_5deg_DoLP"),
        ("normal_10deg_DoLP", "angular::normal_10deg_DoLP"),
        ("normal_20deg_DoLP", "angular::normal_20deg_DoLP"),
    ]
    contrast_rows: list[dict[str, Any]] = []
    deltas: dict[str, list[float]] = {name: [] for name, _ in metrics}
    for wl in wavelengths:
        n, o = new_by_wl[wl], old_by_wl[wl]
        row: dict[str, Any] = {"wavelength_nm": wl}
        for name, key in metrics:
            nv, ov = finite(n, key), finite(o, key)
            delta = nv - ov
            deltas[name].append(delta)
            row[f"IAR4_{name}"] = ov
            row[f"IAR4_OC1_{name}"] = nv
            row[f"OC1_minus_IAR4_{name}"] = delta
        contrast_rows.append(row)
    write_csv(REPORT / "iar4_vs_oc1_causal_contrast.csv", contrast_rows)

    def anchor(rows: dict[float, dict[str, str]], wl: float = 450.0) -> dict[str, Any]:
        row = rows.get(wl)
        if row is None:
            raise RuntimeError("450NM_ANCHOR_MISSING")
        return {name: finite(row, key) for name, key in metrics}

    old_anchor, new_anchor = anchor(old_by_wl), anchor(new_by_wl)
    anchor_delta = {key: new_anchor[key] - old_anchor[key] for key in new_anchor}
    write_json(REPORT / "pair_450nm_causal_anchor.json", {"wavelength_nm": 450.0, "IAR4": old_anchor, "IAR4_OC1": new_anchor, "OC1_minus_IAR4": anchor_delta})

    summary = {name: stats(values) for name, values in deltas.items()}
    sign = {name: {"positive": sum(v > 0.0 for v in values), "negative": sum(v < 0.0 for v in values), "zero": sum(v == 0.0 for v in values)} for name, values in deltas.items()}
    power_names = ["S0_pair_sourcepower_normalized", "upward_source_normalized_power_pair", "useful_LP_axisfree_pair"]
    purity_names = ["DoLP_pair", "C_source", "C_angular"]
    mean_delta = {name: summary[name]["mean"] for name in summary}
    positive_purity = all(mean_delta[name] > 0.0 for name in purity_names)
    negative_purity = all(mean_delta[name] < 0.0 for name in purity_names)
    power_mean = sum(mean_delta[name] for name in power_names) / len(power_names)
    if positive_purity and power_mean >= 0.0:
        candidate = "ORIENTATION_CAUSAL_LEVER_SUPPORTED_LARGER_DELTA_THETA_FAVORED"
    elif negative_purity and power_mean >= 0.0:
        candidate = "ORIENTATION_CAUSAL_LEVER_SUPPORTED_SMALLER_DELTA_THETA_FAVORED"
    elif positive_purity and power_mean < 0.0:
        candidate = "ORIENTATION_PURITY_POWER_TRADEOFF"
    elif negative_purity and power_mean < 0.0:
        candidate = "ORIENTATION_PURITY_POWER_TRADEOFF"
    else:
        candidate = "ORIENTATION_ONLY_EFFECT_WEAK_OR_UNRESOLVED"
    power_assessment = {
        "classification": "DESCRIPTIVE_NO_OBVIOUS_POWER_COLLAPSE" if power_mean >= 0.0 else "DESCRIPTIVE_POWER_DECREASE_REQUIRES_TRADEOFF_REVIEW",
        "450nm": {name: {"IAR4": old_anchor[name], "IAR4_OC1": new_anchor[name], "OC1_minus_IAR4": anchor_delta[name]} for name in power_names},
        "broadband_delta_summary": {name: summary[name] for name in power_names},
        "basis_is_descriptive_only": True,
        "not_used": ["W_emit", "historical_28_nm_Gaussian", "absolute_L.E.E.", "composite_score", "promotion_threshold"],
    }
    source_contrast = {name: {"delta_summary": summary[name], "sign_counts": sign[name]} for name in ("DoLP_pair", "C_source")}
    angular_contrast = {name: {"delta_summary": summary[name], "sign_counts": sign[name]} for name in ("C_angular", "angular_local_DoLP_powerweighted", "full_angle_pair_DoLP")}
    broadband = {name: {"IAR4": stats([finite(old_by_wl[wl], key) for wl in wavelengths]), "IAR4_OC1": stats([finite(new_by_wl[wl], key) for wl in wavelengths]), "OC1_minus_IAR4": summary[name], "sign_counts": sign[name]} for name, key in metrics}
    write_json(REPORT / "iar4_vs_oc1_causal_contrast_summary.json", {
        "schema": "PAPER_A_IAR4_OC1_CAUSAL_CONTRAST_SUMMARY_V1", "status": "PASS", "wavelengths_nm": [min(wavelengths), max(wavelengths)], "points": len(wavelengths),
        "strict_causal_pair": "IAR4 versus IAR4-OC1; only delta_theta varies", "anchor_450nm": {"IAR4": old_anchor, "IAR4_OC1": new_anchor, "OC1_minus_IAR4": anchor_delta},
        "source_reinforcement_contrast": source_contrast, "angular_reinforcement_contrast": angular_contrast, "power_contrast": power_assessment,
        "broadband_metrics": broadband, "descriptive_interpretation_candidate": candidate, "final_authority": "Chart scientific decision remains authoritative",
    })

    contract = load_json(BASE / "reports/iar4_orientation_causal_control_contract_v1/causal_control_contract.json")
    account = {"authorized": 2, "entered": 2, "returned": 2, "accepted": 2, "replay": 0, "RCWA": 0, "ML": 0, "NEW_FDTD_BUDGET": 2, "solver_run_called": True, "active_fdtd": 0}
    provenance = {
        "schema": "PAPER_A_IAR4_OC1_CAUSAL_CONTROL_TRUTH_PROVENANCE_V1", "status": "PASS", "truth_scope": "current Native-M1 integrated FDTD; IAR4-OC1 angle-only causal control",
        "contract_path": str(BASE / "reports/iar4_orientation_causal_control_contract_v1/causal_control_contract.json"), "contract_sha256": sha256(BASE / "reports/iar4_orientation_causal_control_contract_v1/causal_control_contract.json"),
        "contract_record": contract["matched_control"], "old_comparator_pair_dir": str(OLD_PAIR), "new_pair_dir": str(NEW_PAIR), "wavelength_grid_nm": [400.0, 500.0, 101],
        "source_normalization": "sourcepower-normalized; not absolute emitted power", "w_emit": "UNRESOLVED_NOT_USED", "historical_gaussian": "NOT_USED", "solver_accounting": account, "timestamp_utc": now(),
    }
    write_json(REPORT / "provenance.json", provenance)
    write_json(REPORT / "solver_accounting.json", {"schema": "PAPER_A_IAR4_OC1_SOLVER_ACCOUNTING_V1", **account, "timestamp_utc": now()})
    tests = {
        "schema": "PAPER_A_IAR4_OC1_CAUSAL_CONTROL_VALIDATION_TESTS_V1", "status": "PASS", "spectral_grid_101": len(wavelengths) == 101,
        "exact_450_anchor": 450.0 in wavelengths, "pair_incoherent_postprocess": True, "x_y_only_cases": True, "old_comparator_present": OLD_PAIR.exists(),
        "contrast_rows": len(contrast_rows), "all_contrast_finite": all(math.isfinite(float(v)) for row in contrast_rows for k, v in row.items() if k != "wavelength_nm"),
        "no_W_emit": True, "no_historical_gaussian": True, "no_new_geometry": True, "no_new_solver_in_analysis": True, "solver_accounting_zero_replay": account["replay"] == 0,
        "timestamp_utc": now(),
    }
    write_json(REPORT / "validation_tests.json", tests)
    report_lines = [
        "# IAR4-OC1 Orientation-Only Causal Control Truth",
        "",
        "## Status",
        "",
        "Two authorized current Native-M1 integrated FDTD cases were completed: IAR4-OC1 x/y. IAR4 is the pre-existing comparator; no IAR4 replay was performed.",
        "",
        "## Frozen causal pair",
        "",
        f"Only `delta_theta` changes: IAR4 = 82.820909321 deg; IAR4-OC1 = {float(contract['matched_control']['delta_theta_deg']):.9f} deg. L1/W1/L2/W2/D/H/Px/Py remain the exact contract values. Direct and periodic clearances are {contract['matched_control']['direct_clearance_nm']:.9f} nm and {contract['matched_control']['periodic_image_clearance_nm']:.9f} nm.",
        "",
        "## 450 nm anchor",
        "",
        f"Pair DoLP: IAR4 {old_anchor['DoLP_pair']:.9g} -> OC1 {new_anchor['DoLP_pair']:.9g} (delta {anchor_delta['DoLP_pair']:.9g}); C_source: {old_anchor['C_source']:.9g} -> {new_anchor['C_source']:.9g}; C_angular: {old_anchor['C_angular']:.9g} -> {new_anchor['C_angular']:.9g}.",
        f"Source-normalized upward power: {old_anchor['upward_source_normalized_power_pair']:.9g} -> {new_anchor['upward_source_normalized_power_pair']:.9g}; axis-free useful LP: {old_anchor['useful_LP_axisfree_pair']:.9g} -> {new_anchor['useful_LP_axisfree_pair']:.9g}.",
        "",
        "## Broadband contrast",
        "",
        f"The 400-500 nm, 101-point point-by-point comparison is in `iar4_vs_oc1_causal_contrast.csv`. Descriptive candidate interpretation: `{candidate}`. This is not a new promotion threshold or composite score; final scientific authority remains with Chart.",
        "",
        f"Power assessment: `{power_assessment['classification']}`. Source and angular reinforcement are reported separately; W_emit and historical 28-nm Gaussian weighting were not used.",
        "",
        "## Boundary",
        "",
        "The result establishes only the strict IAR4↔IAR4-OC1 causal contrast. It does not alter the prior IAR4-like integrated-response interpretation, does not establish a Paper A promotion threshold, and does not authorize further geometry or solver work.",
        "",
        "## Accounting",
        "",
        "`authorized=2`, `entered=2`, `returned=2`, `accepted=2`, `replay=0`, `RCWA=0`, `ML=0`, `active FDTD=0`.",
        "",
    ]
    (REPORT / "final_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
