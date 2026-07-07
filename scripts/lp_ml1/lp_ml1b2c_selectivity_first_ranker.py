from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BATCH_DIR = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_01"
DEFAULT_OUT_ROOT = ROOT / "outputs" / "lp_ml1b2c_selectivity_first_ranking"
DEFAULT_REPORT = ROOT / "reports" / "lp_ml1b2c_selectivity_first_ranking.md"

THRESHOLDS = {
    "selected_Tx_min": 0.45,
    "ratio_median_min": 6.0,
    "y_direct_leakage_budget": "selected_Tx / 6",
    "phase_err_at_452nm_max_deg": 15.0,
    "phase_near_diagnostic_max_deg": 30.0,
    "nearest_bin_instability_max_modes": 1,
    "matrix_error_max": 0.60,
    "usable_ratio_median_min": 3.0,
    "usable_phase_err_at_452nm_max_deg": 25.0,
    "usable_matrix_error_max": 1.00,
}

RANK_FIELDS = [
    "candidate_id", "target_bin", "nearest_bin_mode", "unique_nearest_bins", "Tx_mean", "ratio_median",
    "matrix_error_median", "y_direct_leakage_median", "phase_err_at_452nm", "phase_err_max",
    "extraction_schema_gate", "projector_gate", "phase_bin_gate", "wavelength_stability_gate",
    "b2c_class", "class_meaning_cn", "soft_rank_score", "geometry_margin_note",
]

CLASS_CN = {
    "strong_projector_phase_good": "投影选择矩阵和目标相位都通过，优先保留",
    "usable_projector_phase_good": "投影选择基本可用且相位接近，可作为候选/近失配",
    "projector_pass_phase_wrong": "投影选择可用，但 selected-channel phase 落错 bin",
    "high_Tx_but_nonselective": "透过高但泄漏/矩阵误差导致投影选择失败",
    "phase_near_but_nonselective": "相位接近目标，但投影选择失败，不能算 APCD LP 成功",
    "phase_drifted_nonselective": "相位漂移且投影选择失败，可作为负样本",
    "low_Tx_nonselective": "Tx 低且投影选择失败",
    "schema_or_extraction_fail": "提取或数据 schema 失败",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def fmt(value: float | str) -> str:
    if isinstance(value, str):
        return value
    return f"{value:.6f}" if math.isfinite(value) else ""


def mode(values: list[int]) -> int | None:
    if not values:
        return None
    counts = Counter(values)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def finite_jones_row(row: dict[str, str]) -> bool:
    required = [
        "txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im",
        "selected_Tx", "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg",
    ]
    for key in required:
        try:
            value = float(row.get(key, ""))
        except (TypeError, ValueError):
            return False
        if not math.isfinite(value):
            return False
    return row.get("result_status", "ok") == "ok"


def summarize_candidate(rows: list[dict[str, str]]) -> dict[str, object]:
    cid = rows[0].get("candidate_id", "") if rows else ""
    target = int(to_float(rows[0].get("target_bin_deg", "0"))) if rows else 0
    ok_rows = [r for r in rows if finite_jones_row(r)]
    extraction_pass = len(ok_rows) == len(rows) and bool(rows)
    tx_vals = [to_float(r.get("selected_Tx")) for r in ok_rows]
    ratio_vals = [to_float(r.get("conversion_to_leakage_ratio")) for r in ok_rows]
    matrix_vals = [to_float(r.get("matrix_error"), 999.0) for r in ok_rows]
    y_direct_vals = [to_float(r.get("y_direct_leakage")) for r in ok_rows]
    phase_vals = [to_float(r.get("phase_error_deg"), 999.0) for r in ok_rows]
    nearest_vals = [int(to_float(r.get("nearest_bin_deg"))) for r in ok_rows]
    at452 = next((r for r in ok_rows if int(to_float(r.get("wavelength_nm"))) == 452), ok_rows[0] if ok_rows else {})

    tx_mean = mean(tx_vals) if tx_vals else 0.0
    ratio_med = median(ratio_vals) if ratio_vals else 0.0
    matrix_med = median(matrix_vals) if matrix_vals else 999.0
    y_direct_med = median(y_direct_vals) if y_direct_vals else 999.0
    phase_452 = to_float(at452.get("phase_error_deg"), 999.0)
    phase_max = max(phase_vals) if phase_vals else 999.0
    nearest_mode = mode(nearest_vals)
    unique_bins = sorted(set(nearest_vals))

    y_budget_ok = y_direct_med <= tx_mean / 6.0 if tx_mean > 0 else False
    projector_pass = tx_mean >= THRESHOLDS["selected_Tx_min"] and ratio_med >= THRESHOLDS["ratio_median_min"] and y_budget_ok and matrix_med <= THRESHOLDS["matrix_error_max"]
    projector_usable = tx_mean >= THRESHOLDS["selected_Tx_min"] and ratio_med >= THRESHOLDS["usable_ratio_median_min"] and matrix_med <= THRESHOLDS["usable_matrix_error_max"]
    phase_pass = nearest_mode == target and phase_452 <= THRESHOLDS["phase_err_at_452nm_max_deg"]
    phase_usable = nearest_mode == target and phase_452 <= THRESHOLDS["usable_phase_err_at_452nm_max_deg"]
    phase_near = nearest_mode == target and phase_452 <= THRESHOLDS["phase_near_diagnostic_max_deg"]
    stable_pass = len(unique_bins) <= THRESHOLDS["nearest_bin_instability_max_modes"]

    if not extraction_pass:
        cls = "schema_or_extraction_fail"
    elif projector_pass and phase_pass and stable_pass:
        cls = "strong_projector_phase_good"
    elif projector_usable and phase_usable and len(unique_bins) <= 2:
        cls = "usable_projector_phase_good"
    elif projector_usable and not phase_usable:
        cls = "projector_pass_phase_wrong"
    elif phase_near and not projector_usable:
        cls = "phase_near_but_nonselective"
    elif tx_mean >= THRESHOLDS["selected_Tx_min"] and not projector_usable:
        cls = "high_Tx_but_nonselective"
    elif nearest_mode != target and not projector_usable:
        cls = "phase_drifted_nonselective"
    else:
        cls = "low_Tx_nonselective"

    score = 0.0
    if extraction_pass:
        score += 1000
    if projector_pass:
        score += 1000
    elif projector_usable:
        score += 500
    if phase_pass:
        score += 300
    elif phase_usable:
        score += 100
    if stable_pass:
        score += 100
    score += min(tx_mean, 2.0) * 20 + min(ratio_med, 20.0) * 5 - min(matrix_med, 5.0) * 20 - min(phase_452, 180.0)

    return {
        "candidate_id": cid,
        "target_bin": target,
        "nearest_bin_mode": nearest_mode if nearest_mode is not None else "",
        "unique_nearest_bins": ";".join(str(x) for x in unique_bins),
        "Tx_mean": fmt(tx_mean),
        "ratio_median": fmt(ratio_med),
        "matrix_error_median": fmt(matrix_med),
        "y_direct_leakage_median": fmt(y_direct_med),
        "phase_err_at_452nm": fmt(phase_452),
        "phase_err_max": fmt(phase_max),
        "extraction_schema_gate": "pass" if extraction_pass else "fail",
        "projector_gate": "pass" if projector_pass else ("usable" if projector_usable else "fail"),
        "phase_bin_gate": "pass" if phase_pass else ("usable" if phase_usable else ("near" if phase_near else "fail")),
        "wavelength_stability_gate": "pass" if stable_pass else "fail",
        "b2c_class": cls,
        "class_meaning_cn": CLASS_CN[cls],
        "soft_rank_score": fmt(score),
        "geometry_margin_note": "not_available_in_batch_results",
    }


def batch_token(batch_name: str) -> str:
    return batch_name.replace("_", "")


def rank_batch(batch_dir: Path, output_dir: Path, batch_name: str = "batch_01") -> tuple[list[dict[str, object]], dict[str, object]]:
    preferred = batch_dir / f"lp_ml1b2b_{batch_token(batch_name)}_results.csv"
    if preferred.exists():
        results_path = preferred
    else:
        matches = sorted(batch_dir.glob("*_results.csv"))
        if not matches:
            raise FileNotFoundError(f"No results CSV found under {batch_dir}")
        results_path = matches[0]
    rows = read_csv(results_path)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("candidate_id", "")].append(row)
    ranked = [summarize_candidate(group) for _, group in sorted(grouped.items())]
    class_order = {
        "strong_projector_phase_good": 0,
        "usable_projector_phase_good": 1,
        "projector_pass_phase_wrong": 2,
        "high_Tx_but_nonselective": 3,
        "phase_near_but_nonselective": 4,
        "phase_drifted_nonselective": 5,
        "low_Tx_nonselective": 6,
        "schema_or_extraction_fail": 7,
    }
    ranked.sort(key=lambda r: (class_order.get(str(r["b2c_class"]), 99), -to_float(r["soft_rank_score"]), str(r["candidate_id"])))
    token = batch_token(batch_name)
    write_csv(output_dir / f"lp_ml1b2c_{token}_selectivity_first_ranking.csv", ranked, RANK_FIELDS)
    summary = {
        "batch_dir": str(batch_dir),
        "candidate_count": len(ranked),
        "class_counts": dict(Counter(str(r["b2c_class"]) for r in ranked)),
        "strong_or_usable_count": sum(1 for r in ranked if r["b2c_class"] in {"strong_projector_phase_good", "usable_projector_phase_good"}),
        "thresholds": THRESHOLDS,
        "no_fdtd_run": True,
        "no_gui": True,
        "no_fmm": True,
        "no_training": True,
        "no_k6": True,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"lp_ml1b2c_{token}_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ranked, summary


def write_global_outputs(ranked: list[dict[str, object]], summary: dict[str, object], out_root: Path, report_path: Path = DEFAULT_REPORT) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "lp_ml1b2c_thresholds.json").write_text(json.dumps(THRESHOLDS, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    recommendation = {
        "recommended_next_batch_id": "LPML1B2A_BATCH_04",
        "batch_02_label": "B300 continuation / statistical failure mapping",
        "recommendation": "LPML1B2A_BATCH_04 remains recommended if next FDTD is authorized; do not run until B2C ranker is adopted.",
        "do_not_modify_frozen_b2a_plan": True,
        "do_not_declare_k6_readiness": True,
        "no_fdtd_run": True,
    }
    (out_root / "lp_ml1b2c_next_action_recommendation.json").write_text(json.dumps(recommendation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    table = ["| candidate_id | target | nearest | Tx_mean | ratio_median | matrix_error | phase_err_452 | class |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for row in ranked:
        table.append(f"| {row['candidate_id']} | {row['target_bin']} | {row['nearest_bin_mode']} | {row['Tx_mean']} | {row['ratio_median']} | {row['matrix_error_median']} | {row['phase_err_at_452nm']} | {row['b2c_class']} |")
    lines = [
        "# LP-ML1B2C selectivity-first ranking",
        "",
        "## Hierarchy implemented",
        "1. Hard gate 1: extraction/schema pass.",
        "2. Hard gate 2: projector/selectivity pass using selected_Tx, selected-to-leakage ratio, y_direct leakage budget, and matrix_error.",
        "3. Hard gate 3: phase-bin pass using nearest_bin_mode and phase_err_at_452nm.",
        "4. Hard gate 4: wavelength stability pass using nearest-bin mode count.",
        "5. Soft ranking: Tx, ratio, matrix_error, phase error, and stability.",
        "",
        "## Batch result",
        f"- candidate_count: {summary['candidate_count']}",
        f"- class_counts: `{summary['class_counts']}`",
        f"- strong_or_usable_count: {summary['strong_or_usable_count']}",
        "",
    ] + table + [
        "",
        "## Next action",
        "LPML1B2A_BATCH_04 remains the recommended next FDTD batch if another batch is authorized, because batch-02 is still B300 continuation / statistical failure mapping.",
        "Do not declare K=6 readiness. Do not modify the frozen B2A plan.",
        "",
        "No FDTD was run by this ranker. No GUI, FMM, ML training, K=6, coverage, or heavy output generation was performed by ranking.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="LP-ML1B2C selectivity-first no-FDTD ranker")
    parser.add_argument("--batch-dir", default=str(DEFAULT_BATCH_DIR))
    parser.add_argument("--output-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--batch-name", default="batch_01")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()
    batch_dir = Path(args.batch_dir)
    out_root = Path(args.output_root)
    output_dir = out_root / args.batch_name
    ranked, summary = rank_batch(batch_dir, output_dir, args.batch_name)
    write_global_outputs(ranked, summary, out_root, Path(args.report))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
