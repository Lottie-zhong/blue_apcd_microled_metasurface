from __future__ import annotations

import cmath
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "lp_ml1b1a_smoke_result_sanity_audit"
REPORTS = ROOT / "reports"
RESULTS = ROOT / "outputs" / "lp_ml1b1_fdtd_smoke_test" / "lp_ml1b1_smoke_results.csv"
SUMMARY_IN = ROOT / "outputs" / "lp_ml1b1_fdtd_smoke_test" / "lp_ml1b1_smoke_summary.json"
FAILURES_IN = ROOT / "outputs" / "lp_ml1b1_fdtd_smoke_test" / "lp_ml1b1_failure_log.csv"
RUNTIME_IN = ROOT / "outputs" / "lp_ml1b1_fdtd_smoke_test" / "lp_ml1b1_runtime_manifest.csv"
SCHEMA_IN = ROOT / "outputs" / "lp_ml1b0_runner_planning" / "lp_ml1b0_expected_result_schema.csv"
SMOKE_IN = ROOT / "outputs" / "lp_ml1b0_runner_planning" / "lp_ml1b0_smoke_test_recommendation.csv"
METRIC_SUMMARY = OUT / "lp_ml1b1a_metric_summary.csv"
CANDIDATE_SUMMARY = OUT / "lp_ml1b1a_candidate_summary.csv"
WAVELENGTH_SUMMARY = OUT / "lp_ml1b1a_wavelength_summary.csv"
ANOMALIES = OUT / "lp_ml1b1a_anomaly_flags.csv"
SUMMARY_OUT = OUT / "lp_ml1b1a_summary.json"
REPORT_MD = REPORTS / "lp_ml1b1a_smoke_result_sanity_audit.md"
DECISION_MD = REPORTS / "lp_ml1b1a_next_action_decision.md"
EXPECTED_WAVELENGTHS = [450, 450.5, 451, 451.5, 452, 452.5, 453, 453.5, 454]
BINS = [0, 60, 120, 180, 240, 300]
JONES = ["txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im"]
NUMERIC = JONES + ["selected_Tx", "leakage_xin_to_yout", "leakage_yin_to_xout", "y_direct_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg", "matrix_error"]
ANOMALY_FIELDS = ["candidate_id", "wavelength_nm", "flag_type", "category", "message", "value", "threshold"]
EPS = 1e-12


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def ff(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return math.nan


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def wrap360(value: float) -> float:
    return value % 360.0


def nearest_bin(phase: float) -> int:
    return min(BINS, key=lambda b: abs(wrap180(phase - b)))


def close_enough(actual: float, expected: float, abs_tol: float = 1e-6, rel_tol: float = 1e-4) -> bool:
    if not math.isfinite(actual) or not math.isfinite(expected):
        return False
    return abs(actual - expected) <= max(abs_tol, rel_tol * max(abs(expected), EPS))


def add_flag(flags: list[dict[str, Any]], row: dict[str, Any], flag: str, category: str, message: str, value: Any, threshold: str) -> None:
    flags.append({"candidate_id": row.get("candidate_id", ""), "wavelength_nm": row.get("wavelength_nm", ""), "flag_type": flag, "category": category, "message": message, "value": value, "threshold": threshold})


def recompute(row: dict[str, str]) -> dict[str, Any]:
    txx = complex(ff(row["txx_re"]), ff(row["txx_im"]))
    txy = complex(ff(row["txy_re"]), ff(row["txy_im"]))
    tyx = complex(ff(row["tyx_re"]), ff(row["tyx_im"]))
    tyy = complex(ff(row["tyy_re"]), ff(row["tyy_im"]))
    tx = abs(txx) ** 2
    leak_xy = abs(tyx) ** 2
    leak_yx = abs(txy) ** 2
    y_dir = abs(tyy) ** 2
    phase = wrap360(math.degrees(cmath.phase(txx))) if abs(txx) > EPS else math.nan
    near = nearest_bin(phase) if math.isfinite(phase) else math.nan
    target = ff(row.get("target_bin_deg"))
    err = abs(wrap180(phase - target)) if math.isfinite(phase) and math.isfinite(target) else math.nan
    ratio = tx / max(leak_yx + y_dir, EPS)
    matrix = math.sqrt(leak_xy + leak_yx + y_dir) / max(abs(txx), EPS)
    return {"selected_Tx": tx, "leakage_xin_to_yout": leak_xy, "leakage_yin_to_xout": leak_yx, "y_direct_leakage": y_dir, "conversion_to_leakage_ratio": ratio, "selected_phase_deg": phase, "nearest_bin_deg": near, "phase_error_deg": err, "matrix_error": matrix}


def validate_inputs() -> None:
    missing = [p for p in [RESULTS, SUMMARY_IN, FAILURES_IN, RUNTIME_IN, SCHEMA_IN, SMOKE_IN] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing LP-ML1B1 audit input(s): " + ", ".join(str(p) for p in missing))


def main() -> None:
    validate_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    rows = read_csv(RESULTS)
    smoke = {row["candidate_id"]: row for row in read_csv(SMOKE_IN)}
    runtime = read_csv(RUNTIME_IN)
    with SUMMARY_IN.open(encoding="utf-8") as f:
        prior_summary = json.load(f)

    flags: list[dict[str, Any]] = []
    required = set(["candidate_id", "target_bin_deg", "wavelength_nm", "result_status"] + JONES)
    missing_cols = required - set(rows[0].keys() if rows else [])
    if missing_cols:
        flags.append({"candidate_id": "", "wavelength_nm": "", "flag_type": "missing_column", "category": "schema", "message": ";".join(sorted(missing_cols)), "value": "", "threshold": "required columns"})

    ids = sorted({row.get("candidate_id", "") for row in rows})
    wls = sorted({ff(row.get("wavelength_nm")) for row in rows})
    if len(ids) != 2:
        flags.append({"candidate_id": "", "wavelength_nm": "", "flag_type": "candidate_count", "category": "schema", "message": "expected exactly 2 candidates", "value": len(ids), "threshold": "2"})
    if len(rows) != 18 and prior_summary.get("failed_rows") == 0:
        flags.append({"candidate_id": "", "wavelength_nm": "", "flag_type": "row_count", "category": "schema", "message": "expected 18 rows", "value": len(rows), "threshold": "18"})
    if wls != EXPECTED_WAVELENGTHS:
        flags.append({"candidate_id": "", "wavelength_nm": "", "flag_type": "wavelength_grid", "category": "schema", "message": "unexpected wavelength grid", "value": ";".join(map(str, wls)), "threshold": ";".join(map(str, EXPECTED_WAVELENGTHS))})

    enriched = []
    mismatch_count = 0
    for row in rows:
        calc = recompute(row)
        item = dict(row)
        item.update({f"recomputed_{k}": v for k, v in calc.items()})
        enriched.append(item)
        if row.get("result_status") != "ok":
            add_flag(flags, row, "result_status", "schema", "result_status not success", row.get("result_status"), "ok")
        for col in NUMERIC:
            val = ff(row.get(col))
            if not math.isfinite(val):
                add_flag(flags, row, "nonfinite", "extraction", f"{col} nonfinite", row.get(col), "finite")
        comparisons = ["selected_Tx", "leakage_xin_to_yout", "leakage_yin_to_xout", "y_direct_leakage", "conversion_to_leakage_ratio", "matrix_error"]
        for col in comparisons:
            csv_val = ff(row.get(col))
            if not close_enough(calc[col], csv_val):
                mismatch_count += 1
                add_flag(flags, row, "recompute_mismatch", "extraction", f"{col} mismatch", fmt(calc[col] - csv_val), "1e-6 abs or 1e-4 rel")
        csv_phase = ff(row.get("selected_phase_deg"))
        if math.isfinite(csv_phase) and abs(wrap180(calc["selected_phase_deg"] - csv_phase)) > 1e-3:
            mismatch_count += 1
            add_flag(flags, row, "phase_mismatch", "extraction", "selected_phase_deg mismatch", fmt(wrap180(calc["selected_phase_deg"] - csv_phase)), "1e-3 deg")
        csv_phase_err = ff(row.get("phase_error_deg"))
        if math.isfinite(csv_phase_err) and abs(calc["phase_error_deg"] - csv_phase_err) > 1e-3:
            mismatch_count += 1
            add_flag(flags, row, "phase_error_mismatch", "extraction", "phase_error_deg mismatch", fmt(calc["phase_error_deg"] - csv_phase_err), "1e-3 deg")
        csv_near = int(ff(row.get("nearest_bin_deg"))) if math.isfinite(ff(row.get("nearest_bin_deg"))) else None
        if csv_near != calc["nearest_bin_deg"]:
            add_flag(flags, row, "nearest_bin_inconsistent", "extraction", "nearest_bin inconsistent with selected_phase_deg", csv_near, str(calc["nearest_bin_deg"]))
        tx = calc["selected_Tx"]
        leak1 = calc["leakage_xin_to_yout"]
        leak2 = calc["leakage_yin_to_xout"]
        ydir = calc["y_direct_leakage"]
        if tx < 0:
            add_flag(flags, row, "negative_tx", "extraction", "selected_Tx < 0", fmt(tx), ">=0")
        for col, val in [("leakage_xin_to_yout", leak1), ("leakage_yin_to_xout", leak2), ("y_direct_leakage", ydir)]:
            if val < 0:
                add_flag(flags, row, "negative_leakage", "extraction", f"{col} < 0", fmt(val), ">=0")
        if tx > 2.0:
            add_flag(flags, row, "selected_Tx_gt_2", "physical", "selected_Tx > 2.0", fmt(tx), "<=2.0")
        if tx + leak1 > 2.0:
            add_flag(flags, row, "x_input_proxy_gt_2", "physical", "|txx|^2 + |tyx|^2 > 2.0", fmt(tx + leak1), "<=2.0")
        if leak2 + ydir > 2.0:
            add_flag(flags, row, "y_input_proxy_gt_2", "physical", "|txy|^2 + |tyy|^2 > 2.0", fmt(leak2 + ydir), "<=2.0")
        if not (0 <= calc["phase_error_deg"] <= 180):
            add_flag(flags, row, "phase_error_range", "extraction", "phase_error_deg missing or outside 0-180", fmt(calc["phase_error_deg"]), "0..180")
        if calc["phase_error_deg"] > 80:
            add_flag(flags, row, "phase_error_gt_80", "physical", "phase_error_deg outside smoke sanity 0-80 window", fmt(calc["phase_error_deg"]), "<=80")
        if calc["conversion_to_leakage_ratio"] <= 0 or not math.isfinite(calc["conversion_to_leakage_ratio"]):
            add_flag(flags, row, "ratio_nonpositive", "extraction", "conversion_to_leakage_ratio <=0 or nonfinite", fmt(calc["conversion_to_leakage_ratio"]), ">0 finite")
        if not math.isfinite(calc["matrix_error"]):
            add_flag(flags, row, "matrix_error_nonfinite", "extraction", "matrix_error nonfinite", fmt(calc["matrix_error"]), "finite")

    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched:
        by_candidate[row["candidate_id"]].append(row)
    for cid, group in by_candidate.items():
        ordered = sorted(group, key=lambda r: ff(r["wavelength_nm"]))
        phases = [ff(r["selected_phase_deg"]) for r in ordered]
        txs = [ff(r["selected_Tx"]) for r in ordered]
        for prev, cur in zip(phases, phases[1:]):
            if abs(wrap180(cur - prev)) > 90:
                add_flag(flags, {"candidate_id": cid, "wavelength_nm": "adjacent"}, "spectral_phase_jump", "physical", "phase jump >90 deg between adjacent wavelengths", fmt(abs(wrap180(cur - prev))), ">90 deg")
        if max(txs) - min(txs) > 0.5:
            add_flag(flags, {"candidate_id": cid, "wavelength_nm": "450-454"}, "selected_Tx_variation", "physical", "selected_Tx variation >0.5 absolute", fmt(max(txs) - min(txs)), "<=0.5")

    runtime_by_candidate: dict[str, float] = defaultdict(float)
    for row in runtime:
        runtime_by_candidate[row.get("candidate_id", "")] += ff(row.get("runtime_sec", 0))

    candidate_rows = []
    for cid, group in sorted(by_candidate.items()):
        tx = [ff(r["selected_Tx"]) for r in group]
        leak_xy = [ff(r["leakage_xin_to_yout"]) for r in group]
        leak_yx = [ff(r["leakage_yin_to_xout"]) for r in group]
        ydir = [ff(r["y_direct_leakage"]) for r in group]
        ratio = [ff(r["conversion_to_leakage_ratio"]) for r in group]
        phase_err = [ff(r["phase_error_deg"]) for r in group]
        matrix = [ff(r["matrix_error"]) for r in group]
        bins = [str(r["nearest_bin_deg"]) for r in group]
        mode, mode_count = Counter(bins).most_common(1)[0]
        at_452 = next((r for r in group if abs(ff(r["wavelength_nm"]) - 452) < 1e-9), group[0])
        anomaly_count = sum(1 for flag in flags if flag.get("candidate_id") == cid)
        recommendation = "template_numeric_ok_candidate_physics_poor" if anomaly_count else "template_numeric_ok"
        candidate_rows.append({"candidate_id": cid, "target_bin_deg": group[0]["target_bin_deg"], "H_nm": smoke.get(cid, {}).get("H_nm", ""), "row_count": len(group), "selected_Tx_mean": fmt(mean(tx)), "selected_Tx_min": fmt(min(tx)), "selected_Tx_max": fmt(max(tx)), "leakage_xin_to_yout_mean": fmt(mean(leak_xy)), "leakage_yin_to_xout_mean": fmt(mean(leak_yx)), "y_direct_leakage_mean": fmt(mean(ydir)), "conversion_to_leakage_ratio_median": fmt(median(ratio)), "selected_phase_deg_at_452nm": at_452["selected_phase_deg"], "phase_error_deg_at_452nm": at_452["phase_error_deg"], "phase_error_deg_mean": fmt(mean(phase_err)), "nearest_bin_mode": mode, "nearest_bin_consistency_rate": fmt(mode_count / len(group)), "matrix_error_mean": fmt(mean(matrix)), "anomaly_count": anomaly_count, "runtime_seconds_total": fmt(runtime_by_candidate[cid]), "recommendation": recommendation})

    metric_rows = []
    for metric in ["selected_Tx", "leakage_xin_to_yout", "leakage_yin_to_xout", "y_direct_leakage", "conversion_to_leakage_ratio", "phase_error_deg", "matrix_error"]:
        vals = [ff(r[metric]) for r in rows]
        metric_rows.append({"metric": metric, "min": fmt(min(vals)), "mean": fmt(mean(vals)), "median": fmt(median(vals)), "max": fmt(max(vals))})

    wavelength_rows = []
    for wl in EXPECTED_WAVELENGTHS:
        group = [r for r in rows if abs(ff(r["wavelength_nm"]) - wl) < 1e-9]
        wavelength_rows.append({"wavelength_nm": wl, "row_count": len(group), "selected_Tx_mean": fmt(mean(ff(r["selected_Tx"]) for r in group)), "ratio_median": fmt(median(ff(r["conversion_to_leakage_ratio"]) for r in group)), "phase_error_mean": fmt(mean(ff(r["phase_error_deg"]) for r in group))})

    extraction_flags = [f for f in flags if f.get("category") in {"schema", "extraction"}]
    physical_flags = [f for f in flags if f.get("category") == "physical"]
    if not extraction_flags and not physical_flags and len(rows) == 18:
        decision = "template_numeric_sanity_pass_proceed_to_LP-ML1B2_planning"
        go_no_go = "Go"
    elif not extraction_flags and len(rows) == 18:
        decision = "template_ok_but_candidate_performance_poor_still_can_proceed_to_pilot"
        go_no_go = "Go"
    else:
        decision = "fix_LP-ML1B1_extraction_before_pilot"
        go_no_go = "No-Go"

    write_csv(METRIC_SUMMARY, metric_rows, ["metric", "min", "mean", "median", "max"])
    write_csv(CANDIDATE_SUMMARY, candidate_rows, list(candidate_rows[0].keys()))
    write_csv(WAVELENGTH_SUMMARY, wavelength_rows, list(wavelength_rows[0].keys()))
    write_csv(ANOMALIES, flags, ANOMALY_FIELDS)
    summary = {"candidate_count": len(ids), "row_count": len(rows), "anomaly_count": len(flags), "extraction_anomaly_count": len(extraction_flags), "physical_anomaly_count": len(physical_flags), "recompute_mismatch_count": mismatch_count, "decision": decision, "go_no_go": go_no_go, "no_fdtd_run": True, "no_fmm_solve": True, "no_heavy_files_committed": True}
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    table = ["| candidate_id | target | Tx mean | phase err @452 | nearest bin mode | ratio median | anomalies |", "|---|---:|---:|---:|---:|---:|---:|"]
    for r in candidate_rows:
        table.append(f"| {r['candidate_id']} | {r['target_bin_deg']} | {r['selected_Tx_mean']} | {r['phase_error_deg_at_452nm']} | {r['nearest_bin_mode']} | {r['conversion_to_leakage_ratio_median']} | {r['anomaly_count']} |")
    REPORT_MD.write_text("\n".join(["# LP-ML1B1A smoke result sanity audit", "", "Purpose: numerical sanity audit of completed LP-ML1B1 smoke-test Jones results before any LP-ML1B2 expansion.", "", "## Input files", f"- {RESULTS}", f"- {SUMMARY_IN}", f"- {FAILURES_IN}", f"- {RUNTIME_IN}", f"- {SCHEMA_IN}", f"- {SMOKE_IN}", "", f"Row count: {len(rows)}", f"Candidate count: {len(ids)}", "", "## Candidate-level summary", *table, "", "## Key metric ranges", *[f"- {r['metric']}: min={r['min']}, mean={r['mean']}, median={r['median']}, max={r['max']}" for r in metric_rows], "", "## Anomaly summary", f"- total anomaly flags: {len(flags)}", f"- extraction/schema anomaly flags: {len(extraction_flags)}", f"- physical-performance anomaly flags: {len(physical_flags)}", "", "## Recompute consistency check", f"- recompute mismatch count: {mismatch_count}", "", "## Phase/bin consistency check", "- nearest bins were recomputed from selected_phase_deg using bins 0, 60, 120, 180, 240, 300.", "", "## Runtime summary", f"- LP-ML1B1 prior total runtime: about {sum(runtime_by_candidate.values()):.2f} s.", "", f"Decision: {decision}", "", "No FDTD was run.", "No FMM solver was executed.", "No heavy files were committed.", ""]), encoding="utf-8")
    fixes = "None for extraction/schema; observed flags are candidate physics/performance sanity warnings." if not extraction_flags else "Fix extraction/schema mismatches listed in anomaly CSV before larger run."
    DECISION_MD.write_text("\n".join(["# LP-ML1B1A next action decision", "", f"Go/No-Go for LP-ML1B2 36-case pilot planning: {go_no_go}.", "", f"Decision code: {decision}", "", "If Go: split LP-ML1B2 into planning plus execution; run the 36-case pilot before any 600-candidate expansion.", "If No-Go: do not run larger jobs until the exact extraction/schema issues are fixed.", "", f"Required fixes before larger run: {fixes}", "", "Estimated runtime: LP-ML1B1 two candidates total runtime was about 637.28 s. A 36-candidate pilot at similar speed is roughly 3.2 hours plus overhead.", "Do not run 600 candidates.", "", "No FDTD was run.", "No FMM solver was executed.", "No heavy files were committed.", ""]), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
