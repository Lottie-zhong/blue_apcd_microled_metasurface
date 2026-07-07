from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "scripts" / "lp_ml1"
if str(LP) not in sys.path:
    sys.path.insert(0, str(LP))

import lp_ml1b1_fdtd_smoke_test as base
from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

BATCH_ID = "LPML1B2A_BATCH_01"
B2A_BATCH = ROOT / "outputs" / "lp_ml1b2a_36case_pilot_plan" / "lp_ml1b2a_batch_plan.csv"
QUEUE = ROOT / "outputs" / "lp_ml1b0_runner_planning" / "lp_ml1b0_pilot_queue.csv"
OUT = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_01"
TMP_FDTD = OUT / "fdtd_tmp"
RESULTS = OUT / "lp_ml1b2b_batch01_results.csv"
FAILURES = OUT / "lp_ml1b2b_batch01_failure_log.csv"
RUNTIME = OUT / "lp_ml1b2b_batch01_runtime_manifest.csv"
SUMMARY = OUT / "lp_ml1b2b_batch01_summary.json"
RANKING = OUT / "lp_ml1b2b_batch01_candidate_ranking.csv"
REPORT = ROOT / "reports" / "lp_ml1b2b_batch01_execution_report.md"
WAVELENGTHS = base.WAVELENGTHS
POLARIZATIONS = ["x", "y"]
RESULT_FIELDS = ["batch_id"] + base.RESULT_FIELDS + ["preliminary_status"]
FAIL_FIELDS = ["batch_id"] + base.FAIL_FIELDS
RUN_FIELDS = ["batch_id"] + base.RUN_FIELDS
RANK_FIELDS = ["candidate_id", "target_bin", "nearest_bin_mode", "Tx_mean", "ratio_median", "phase_err_at_452nm", "anomaly_count", "preliminary_status", "runtime_sec"]
ANOMALY_FIELDS = ["candidate_id", "wavelength_nm", "flag_type", "message", "value", "threshold"]
ANOMALIES = OUT / "lp_ml1b2b_batch01_anomaly_flags.csv"
EPS = 1e-12


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({field: row.get(field, "") for field in fields})


def f(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return math.nan


def batch_candidate_ids() -> list[str]:
    rows = read_csv(B2A_BATCH)
    batch = next((r for r in rows if r.get("batch_id") == BATCH_ID), None)
    if not batch:
        raise FileNotFoundError(f"Missing {BATCH_ID} in {B2A_BATCH}")
    ids = [x for x in batch["candidate_ids"].split(";") if x]
    if len(ids) != int(batch.get("candidate_count", len(ids))):
        raise ValueError("candidate_count mismatch in B2A batch plan")
    return ids


def selected_rows() -> list[dict[str, str]]:
    ids = batch_candidate_ids()
    if len(ids) > 6:
        raise ValueError(f"Batch-01 too large: {len(ids)} candidates")
    queue = {row["candidate_id"]: row for row in read_csv(QUEUE)}
    missing = [cid for cid in ids if cid not in queue]
    if missing:
        raise KeyError(f"Missing candidate(s) in pilot queue: {missing}")
    rows = [queue[cid] for cid in ids]
    print("candidate_id,target_bin,sampling_group,H_nm,expected_wavelengths,expected_polarizations,expected_subrun_count")
    for row in rows:
        print(f"{row['candidate_id']},{row['target_bin_deg']},{row.get('sampling_group','')},{row.get('H_nm','')},{len(WAVELENGTHS)},{len(POLARIZATIONS)},{len(WAVELENGTHS) * len(POLARIZATIONS)}")
    return rows


def read_existing_results() -> dict[tuple[str, float], dict[str, Any]]:
    if not RESULTS.exists():
        return {}
    out = {}
    for row in read_csv(RESULTS):
        if row.get("result_status") == "ok":
            out[(row["candidate_id"], f(row["wavelength_nm"]))] = row
    return out


def preliminary(row: dict[str, Any]) -> str:
    if row.get("result_status") != "ok":
        return "failed"
    tx = f(row.get("selected_Tx"))
    ratio = f(row.get("conversion_to_leakage_ratio"))
    phase = f(row.get("phase_error_deg"))
    matrix = f(row.get("matrix_error"))
    nearest = str(row.get("nearest_bin_deg", ""))
    target = str(row.get("target_bin_deg", ""))
    if nearest != target and math.isfinite(phase) and phase > 25:
        return "phase_wrong"
    if tx >= 0.45 and ratio >= 6 and phase <= 15 and matrix <= 0.60:
        return "strong"
    if tx >= 0.10 and ratio >= 3 and phase <= 25 and matrix <= 1.00:
        return "usable"
    return "weak"


def anomaly_flags(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags = []
    numeric = ["txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im", "selected_Tx", "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg", "matrix_error"]
    for row in rows:
        for col in numeric:
            val = f(row.get(col))
            if not math.isfinite(val):
                flags.append({"candidate_id": row.get("candidate_id", ""), "wavelength_nm": row.get("wavelength_nm", ""), "flag_type": "nonfinite", "message": f"{col} nonfinite", "value": row.get(col, ""), "threshold": "finite"})
        if f(row.get("selected_Tx")) > 2.0:
            flags.append({"candidate_id": row.get("candidate_id", ""), "wavelength_nm": row.get("wavelength_nm", ""), "flag_type": "Tx_gt_2", "message": "selected_Tx > 2", "value": row.get("selected_Tx", ""), "threshold": "<=2"})
        if row.get("result_status") != "ok":
            flags.append({"candidate_id": row.get("candidate_id", ""), "wavelength_nm": row.get("wavelength_nm", ""), "flag_type": "failed_row", "message": "result_status not ok", "value": row.get("result_status", ""), "threshold": "ok"})
    return flags


def ranking_rows(rows: list[dict[str, Any]], runtime_rows: list[dict[str, Any]], flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = defaultdict(list)
    for row in rows:
        by[row["candidate_id"]].append(row)
    runtime_by = defaultdict(float)
    for row in runtime_rows:
        runtime_by[row.get("candidate_id", "")] += f(row.get("runtime_sec"))
    flag_by = Counter(row.get("candidate_id", "") for row in flags)
    out = []
    for cid, group in by.items():
        txs = [f(r["selected_Tx"]) for r in group if r.get("result_status") == "ok"]
        ratios = [f(r["conversion_to_leakage_ratio"]) for r in group if r.get("result_status") == "ok"]
        bins = [str(r.get("nearest_bin_deg", "")) for r in group if r.get("result_status") == "ok"]
        mode = Counter(bins).most_common(1)[0][0] if bins else ""
        at452 = next((r for r in group if abs(f(r.get("wavelength_nm")) - 452) < 1e-9), group[0])
        statuses = [preliminary(r) for r in group]
        status = "failed" if "failed" in statuses else ("strong" if all(s == "strong" for s in statuses) else ("usable" if any(s in {"strong", "usable"} for s in statuses) else ("phase_wrong" if statuses.count("phase_wrong") >= max(1, len(statuses) // 2) else "weak")))
        out.append({"candidate_id": cid, "target_bin": group[0].get("target_bin_deg", ""), "nearest_bin_mode": mode, "Tx_mean": base.fmt(mean(txs)) if txs else "", "ratio_median": base.fmt(median(ratios)) if ratios else "", "phase_err_at_452nm": at452.get("phase_error_deg", ""), "anomaly_count": flag_by[cid], "preliminary_status": status, "runtime_sec": base.fmt(runtime_by[cid])})
    def score(r: dict[str, Any]) -> tuple[int, float, float]:
        rank = {"strong": 0, "usable": 1, "weak": 2, "phase_wrong": 3, "failed": 4}.get(r["preliminary_status"], 5)
        return (rank, -f(r.get("ratio_median")), f(r.get("phase_err_at_452nm")))
    return sorted(out, key=score)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    rows = selected_rows()
    expected_subruns = len(rows) * len(WAVELENGTHS) * len(POLARIZATIONS)
    expected_merged = len(rows) * len(WAVELENGTHS)
    base.TMP_FDTD = TMP_FDTD
    existing = read_existing_results()
    results = list(existing.values())
    runtime_rows = read_csv(RUNTIME) if RUNTIME.exists() else []
    failures = read_csv(FAILURES) if FAILURES.exists() else []
    runtime = load_runtime_config("configs/runtime.yaml")
    lumapi = import_lumapi(runtime)
    started = time.time()
    run_count = reused_count = 0
    smoke_overlap = {"LPML1A4_0028_B300_exploration_B300_H600", "LPML1A4_0234_B240_exploration_B240_H600"} & {r["candidate_id"] for r in rows}
    for row in rows:
        for wl in WAVELENGTHS:
            key = (row["candidate_id"], wl)
            if key in existing:
                reused_count += 2
                continue
            pol = {}
            for p in POLARIZATIONS:
                res = base.run_pol(lumapi, runtime, row, wl, p)
                res["batch_id"] = BATCH_ID
                pol[p] = res
                runtime_rows.append(res)
                run_count += 1
                if res["result_status"] != "ok":
                    failures.append(res)
                write_csv(RUNTIME, runtime_rows, RUN_FIELDS)
                write_csv(FAILURES, failures, FAIL_FIELDS)
            combined = base.combine(row, wl, pol["x"], pol["y"])
            combined["batch_id"] = BATCH_ID
            combined["preliminary_status"] = preliminary(combined)
            results.append(combined)
            existing[key] = combined
            write_csv(RESULTS, sorted(results, key=lambda r: (r["candidate_id"], f(r["wavelength_nm"]))), RESULT_FIELDS)
    results = sorted(results, key=lambda r: (r["candidate_id"], f(r["wavelength_nm"])))
    for row in results:
        row["preliminary_status"] = preliminary(row)
    flags = anomaly_flags(results)
    ranking = ranking_rows(results, runtime_rows, flags)
    write_csv(RESULTS, results, RESULT_FIELDS)
    write_csv(FAILURES, failures, FAIL_FIELDS)
    write_csv(RUNTIME, runtime_rows, RUN_FIELDS)
    write_csv(ANOMALIES, flags, ANOMALY_FIELDS)
    write_csv(RANKING, ranking, RANK_FIELDS)
    ok_rows = [r for r in results if r.get("result_status") == "ok"]
    heavy_files = sorted(TMP_FDTD.rglob("*.fsp")) if TMP_FDTD.exists() else []
    total_runtime = sum(f(r.get("runtime_sec")) for r in runtime_rows)
    summary = {"batch_id": BATCH_ID, "candidate_count": len(rows), "candidate_ids": [r["candidate_id"] for r in rows], "expected_subruns": expected_subruns, "actual_subrun_records": len(runtime_rows), "run_subruns_this_invocation": run_count, "reused_subruns": reused_count, "expected_merged_rows": expected_merged, "merged_row_count": len(results), "successful_merged_rows": len(ok_rows), "failed_merged_rows": len(results) - len(ok_rows), "failure_count": len(failures), "anomaly_count": len(flags), "total_runtime_sec": round(total_runtime, 2), "wall_runtime_sec_this_invocation": round(time.time() - started, 2), "temporary_fsp_count": len(heavy_files), "temporary_fsp_dir": str(TMP_FDTD), "smoke_overlap_candidates": sorted(smoke_overlap), "smoke_overlap_policy": "rerun_in_B2B_output_schema_for_clean_independent_dataset", "no_full_36case_run": True, "no_600_candidate_run": True, "no_gui": True, "no_fmm": True, "no_training": True, "no_k6": True}
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    table = ["| candidate_id | target | nearest mode | Tx mean | ratio median | phase err @452 | anomalies | status |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in ranking:
        table.append(f"| {r['candidate_id']} | {r['target_bin']} | {r['nearest_bin_mode']} | {r['Tx_mean']} | {r['ratio_median']} | {r['phase_err_at_452nm']} | {r['anomaly_count']} | {r['preliminary_status']} |")
    report = ["# LP-ML1B2B batch-01 execution report", "", f"Batch: {BATCH_ID}", "", "## Candidate table", "", "| candidate_id | target_bin | sampling_group | H_nm | wavelengths | polarizations | subruns |", "|---|---:|---|---:|---:|---:|---:|" ]
    for row in rows:
        report.append(f"| {row['candidate_id']} | {row['target_bin_deg']} | {row.get('sampling_group','')} | {row.get('H_nm','')} | {len(WAVELENGTHS)} | {len(POLARIZATIONS)} | {len(WAVELENGTHS)*len(POLARIZATIONS)} |")
    report += ["", "## Runtime", f"- expected subruns: {expected_subruns}", f"- actual subrun records: {len(runtime_rows)}", f"- run this invocation: {run_count}", f"- reused subruns: {reused_count}", f"- expected merged Jones rows: {expected_merged}", f"- merged Jones rows: {len(results)}", f"- total runtime seconds: {total_runtime:.2f}", f"- failures: {len(failures)}", f"- anomalies: {len(flags)}", f"- temporary .fsp files: {len(heavy_files)} in {TMP_FDTD}", f"- smoke overlap policy: {summary['smoke_overlap_policy']}", "", "## Ranking", "", *table, "", "## Boundaries", "- No full 36-case run was executed.", "- No 600-candidate run was executed.", "- No GUI, FMM solve, ML training, K=6, or coverage run was executed.", "- Heavy .fsp files are runtime artifacts under outputs and were not committed.", ""]
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
