from __future__ import annotations

import csv, json, math, sys, time
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

PARENT_ID = "LPML1A4_0283_B240_exploration_B240_H650"
GROUP_ID = "LPML1B2E_SCOUT_01_0283_LOCAL_REFINEMENT"
PLAN = ROOT / "outputs" / "lp_ml1b2d_0283_refinement" / "lp_ml1b2d_0283_local_refinement_plan.csv"
OUT = ROOT / "outputs" / "lp_ml1b2e_0283_local_refinement" / "scout_01"
TMP_FDTD = OUT / "fdtd_tmp"
RESULTS = OUT / "lp_ml1b2e_scout01_results.csv"
FAILURES = OUT / "lp_ml1b2e_scout01_failure_log.csv"
RUNTIME = OUT / "lp_ml1b2e_scout01_runtime_manifest.csv"
SUMMARY = OUT / "lp_ml1b2e_scout01_summary.json"
RANKING = OUT / "lp_ml1b2e_scout01_selectivity_first_ranking.csv"
RANK_SUMMARY = OUT / "lp_ml1b2e_scout01_ranking_summary.json"
REPORT = ROOT / "reports" / "lp_ml1b2e_0283_local_refinement_scout01_execution_report.md"
RANK_REPORT = ROOT / "reports" / "lp_ml1b2e_0283_local_refinement_scout01_ranking.md"
WAVELENGTHS = base.WAVELENGTHS
POLARIZATIONS = ["x", "y"]
RESULT_FIELDS = ["group_id","candidate_id","parent_id","refinement_family","intended_reassigned_bin","height_nm","wavelength_nm","phase_bin_deg","txx_re","txx_im","txy_re","txy_im","tyx_re","tyx_im","tyy_re","tyy_im","selected_Tx","leakage_xin_to_yout","leakage_yin_to_xout","y_direct_leakage","conversion_to_leakage_ratio","selected_phase_deg","nearest_bin_deg","phase_error_deg","matrix_error","pass_level","result_csv","status","error_message"]
FAIL_FIELDS = ["group_id"] + base.FAIL_FIELDS
RUN_FIELDS = ["group_id"] + base.RUN_FIELDS
RANK_FIELDS = ["candidate_id","refinement_family","H_nm","nearest_bin_mode","Tx_mean","ratio_median","matrix_error","phase_err_to_120_at_452","nearest_bin_stability_count","b2c_style_class","next_use","runtime_sec"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k: "" if v is None else str(v) for k, v in r.items()} for r in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({field: row.get(field, "") for field in fields})


def f(v: Any, default: float = math.nan) -> float:
    try:
        if v is None or str(v).strip() == "":
            return default
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def fmt(v: float) -> str:
    return "" if not math.isfinite(v) else f"{v:.6f}"


def select_scout_rows(plan_path: Path = PLAN) -> list[dict[str, str]]:
    rows = [r for r in read_csv(plan_path) if r.get("parent_id") == PARENT_ID and r.get("geometry_valid", "").lower() == "true"]
    by_id = {r["candidate_id"]: r for r in rows}
    ids = ["LPML1B2D_B2D_0283_A01","LPML1B2D_B2D_0283_A02","LPML1B2D_B2D_0283_A03","LPML1B2D_B2D_0283_A04","LPML1B2D_B2D_0283_A05","LPML1B2D_B2D_0283_B01","LPML1B2D_B2D_0283_C02","LPML1B2D_B2D_0283_C05"]
    selected = [dict(by_id[i]) for i in ids]
    if len(selected) != 8 or sum(r["refinement_family"] == "fabrication_friendly_H_check" for r in selected) < 2 or not any(r["refinement_family"] == "phase_tuning_scout" for r in selected):
        raise ValueError("invalid B2E scout-01 selection")
    return selected


def print_scout_table(rows: list[dict[str, str]]) -> None:
    fields = ["candidate_id","parent_id","refinement_family","intended_reassigned_bin","H_nm","L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg","center_dx_nm","geometry_valid","rationale"]
    print(",".join(fields))
    for r in rows:
        print(",".join(r.get(x, "") for x in fields))


def existing_keys() -> set[tuple[str, float]]:
    if not RESULTS.exists():
        return set()
    return {(r["candidate_id"], f(r["wavelength_nm"])) for r in read_csv(RESULTS) if r.get("status") == "ok"}


def run_case(row: dict[str, str], lumapi: Any, runtime: Any, wl: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sim = dict(row)
    sim["target_bin_deg"] = row["intended_reassigned_bin"]
    pol, runs = {}, []
    for p in POLARIZATIONS:
        res = base.run_pol(lumapi, runtime, sim, wl, p)
        res["group_id"] = GROUP_ID
        pol[p] = res
        runs.append(res)
    c = base.combine(sim, wl, pol["x"], pol["y"])
    out = {"group_id": GROUP_ID, "candidate_id": row["candidate_id"], "parent_id": row["parent_id"], "refinement_family": row["refinement_family"], "intended_reassigned_bin": row["intended_reassigned_bin"], "height_nm": row["H_nm"], "wavelength_nm": wl, "phase_bin_deg": row["intended_reassigned_bin"], "result_csv": str(RESULTS), "status": c.get("result_status", "failed"), "pass_level": c.get("spectral_pass", "fail"), "error_message": c.get("error_message", "")}
    for key in ["txx_re","txx_im","txy_re","txy_im","tyx_re","tyx_im","tyy_re","tyy_im","selected_Tx","leakage_xin_to_yout","leakage_yin_to_xout","y_direct_leakage","conversion_to_leakage_ratio","selected_phase_deg","nearest_bin_deg","phase_error_deg","matrix_error"]:
        out[key] = c.get(key, "")
    return out, runs


def b2c_class(r: dict[str, Any]) -> str:
    tx, ratio, matrix, phase = f(r.get("Tx_mean"),0), f(r.get("ratio_median"),0), f(r.get("matrix_error"),999), f(r.get("phase_err_to_120_at_452"),999)
    stability = int(f(r.get("nearest_bin_stability_count"),999))
    if tx >= 0.45 and ratio >= 6 and phase <= 15 and stability <= 1 and matrix <= 0.60:
        return "strong_B120_refined_seed"
    if tx >= 0.45 and ratio >= 3 and phase <= 25 and stability <= 2 and matrix <= 1.00:
        return "usable_B120_refined_seed"
    if tx >= 0.45 and ratio >= 6 and matrix <= 0.60:
        return "projector_pass_phase_wrong"
    return "failed_or_negative"


def next_use(r: dict[str, Any]) -> str:
    cls, phase = r["b2c_style_class"], f(r.get("phase_err_to_120_at_452"),999)
    if cls == "strong_B120_refined_seed" and phase < 12.457755:
        return "strong_B120_refined_seed"
    if cls == "strong_B120_refined_seed":
        return "usable_B120_refined_seed"
    if cls == "usable_B120_refined_seed" and r.get("refinement_family") == "fabrication_friendly_H_check":
        return "H_reduction_candidate"
    if cls in {"usable_B120_refined_seed", "projector_pass_phase_wrong"}:
        return "phase_tuning_direction"
    return "negative_sample"


def rank_results(results: list[dict[str, Any]], runtime_rows: list[dict[str, Any]], selected: list[dict[str, str]]) -> list[dict[str, Any]]:
    meta = {r["candidate_id"]: r for r in selected}
    by, rt = defaultdict(list), defaultdict(float)
    for r in results:
        if r.get("status") == "ok":
            by[r["candidate_id"]].append(r)
    for r in runtime_rows:
        rt[r.get("candidate_id", "")] += f(r.get("runtime_sec"), 0)
    out = []
    for cid, rows in by.items():
        bins = [str(r.get("nearest_bin_deg", "")) for r in rows]
        at452 = next((r for r in rows if abs(f(r.get("wavelength_nm")) - 452.0) < 1e-9), {})
        row = {"candidate_id": cid, "refinement_family": meta[cid]["refinement_family"], "H_nm": meta[cid]["H_nm"], "nearest_bin_mode": Counter(bins).most_common(1)[0][0] if bins else "", "Tx_mean": fmt(mean(f(r.get("selected_Tx"),0) for r in rows)), "ratio_median": fmt(median(f(r.get("conversion_to_leakage_ratio"),0) for r in rows)), "matrix_error": fmt(median(f(r.get("matrix_error"),999) for r in rows)), "phase_err_to_120_at_452": at452.get("phase_error_deg", ""), "nearest_bin_stability_count": len(set(bins)), "runtime_sec": fmt(rt[cid])}
        row["b2c_style_class"] = b2c_class(row)
        row["next_use"] = next_use(row)
        out.append(row)
    order = {"strong_B120_refined_seed":0,"usable_B120_refined_seed":1,"projector_pass_phase_wrong":2,"failed_or_negative":3}
    return sorted(out, key=lambda r: (order.get(r["b2c_style_class"],9), f(r.get("phase_err_to_120_at_452"),999), -f(r.get("ratio_median"),0)))


def anomaly_count(results: list[dict[str, Any]]) -> int:
    count = 0
    numeric = ["txx_re","txx_im","txy_re","txy_im","tyx_re","tyy_re","selected_Tx","conversion_to_leakage_ratio","selected_phase_deg","phase_error_deg","matrix_error"]
    for row in results:
        if row.get("status") != "ok":
            count += 1
        for key in numeric:
            if not math.isfinite(f(row.get(key))):
                count += 1
    return count


def write_reports(selected, results, failures, runtime_rows, ranking, run_count, reused_count, started):
    expected_subruns, expected_merged = len(selected)*len(WAVELENGTHS)*2, len(selected)*len(WAVELENGTHS)
    anomalies = anomaly_count(results)
    total_runtime = sum(f(r.get("runtime_sec"),0) for r in runtime_rows)
    improved = [r for r in ranking if r["b2c_style_class"] == "strong_B120_refined_seed" and f(r.get("phase_err_to_120_at_452"),999) < 12.457755]
    h_pass = [r for r in ranking if r["refinement_family"] == "fabrication_friendly_H_check" and r["b2c_style_class"] in {"strong_B120_refined_seed","usable_B120_refined_seed"}]
    summary = {"group_id":GROUP_ID,"candidate_count":len(selected),"candidate_ids":[r["candidate_id"] for r in selected],"expected_subruns":expected_subruns,"actual_subrun_records":len(runtime_rows),"run_subruns_this_invocation":run_count,"reused_subruns":reused_count,"expected_merged_rows":expected_merged,"merged_row_count":len(results),"failure_count":len(failures),"anomaly_count":anomalies,"total_runtime_sec":round(total_runtime,2),"per_candidate_runtime_sec":round(total_runtime/max(len(selected),1),2),"wall_runtime_sec_this_invocation":round(time.time()-started,2),"improved_phase_candidate_count":len(improved),"h600_h500_projector_preserved_count":len(h_pass),"no_batch05":True,"no_full_36case_run":True,"no_600_candidate_run":True,"no_gui":True,"no_fmm":True,"no_training":True,"no_k6":True}
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    RANK_SUMMARY.write_text(json.dumps({"class_counts":dict(Counter(r["b2c_style_class"] for r in ranking)),"next_use_counts":dict(Counter(r["next_use"] for r in ranking)),**summary}, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    cand = ["| candidate_id | family | H | rationale |","|---|---|---:|---|"] + [f"| {r['candidate_id']} | {r['refinement_family']} | {r['H_nm']} | {r['rationale']} |" for r in selected]
    rank = ["| candidate_id | family | H | nearest | Tx_mean | ratio_median | matrix | phase_err_120@452 | stability | class | next_use |","|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"] + [f"| {r['candidate_id']} | {r['refinement_family']} | {r['H_nm']} | {r['nearest_bin_mode']} | {r['Tx_mean']} | {r['ratio_median']} | {r['matrix_error']} | {r['phase_err_to_120_at_452']} | {r['nearest_bin_stability_count']} | {r['b2c_style_class']} | {r['next_use']} |" for r in ranking]
    REPORT.write_text("\n".join(["# LP-ML1B2E 0283 local refinement scout-01 execution","","This run executed only 8 selected local refinement candidates from the frozen B2D 0283 plan.","","## Selected candidates","",*cand,"","## Runtime",f"- expected FDTD subruns: {expected_subruns}",f"- actual subrun records: {len(runtime_rows)}",f"- run this invocation: {run_count}",f"- reused subruns: {reused_count}",f"- expected merged Jones rows: {expected_merged}",f"- merged Jones rows: {len(results)}",f"- failures: {len(failures)}",f"- anomalies: {anomalies}",f"- total runtime sec: {total_runtime:.2f}",f"- per candidate runtime sec: {total_runtime/max(len(selected),1):.2f}","","## Boundary","No batch-05, full 36-case, 600-candidate, GUI, FMM, training, K=6, or coverage run was executed.",""])+"\n", encoding="utf-8")
    RANK_REPORT.write_text("\n".join(["# LP-ML1B2E scout-01 selectivity-first ranking","","Target is the reassigned B120 bin, not original B240.","",*rank,"","## Decision",f"- candidates improving B120 phase over parent while preserving projector: {len(improved)}",f"- H600/H500 variants preserving projector: {len(h_pass)}","- Do not declare K=6 readiness from scout-01.",""])+"\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    selected = select_scout_rows()
    print_scout_table(selected)
    base.TMP_FDTD = TMP_FDTD
    existing = existing_keys()
    results = read_csv(RESULTS) if RESULTS.exists() else []
    runtime_rows = read_csv(RUNTIME) if RUNTIME.exists() else []
    failures = read_csv(FAILURES) if FAILURES.exists() else []
    runtime = load_runtime_config("configs/runtime.yaml")
    lumapi = import_lumapi(runtime)
    started, run_count, reused_count = time.time(), 0, 0
    for row in selected:
        for wl in WAVELENGTHS:
            if (row["candidate_id"], wl) in existing:
                reused_count += 2
                continue
            combined, runs = run_case(row, lumapi, runtime, wl)
            results.append(combined)
            runtime_rows.extend(runs)
            run_count += len(runs)
            failures.extend([{**r, "group_id": GROUP_ID} for r in runs if r.get("result_status") != "ok"])
            write_csv(RESULTS, sorted(results, key=lambda r: (r["candidate_id"], f(r["wavelength_nm"]))), RESULT_FIELDS)
            write_csv(RUNTIME, runtime_rows, RUN_FIELDS)
            write_csv(FAILURES, failures, FAIL_FIELDS)
    results = sorted(results, key=lambda r: (r["candidate_id"], f(r["wavelength_nm"])))
    ranking = rank_results(results, runtime_rows, selected)
    write_csv(RESULTS, results, RESULT_FIELDS)
    write_csv(RUNTIME, runtime_rows, RUN_FIELDS)
    write_csv(FAILURES, failures, FAIL_FIELDS)
    write_csv(RANKING, ranking, RANK_FIELDS)
    write_reports(selected, results, failures, runtime_rows, ranking, run_count, reused_count, started)
    print(SUMMARY.read_text(encoding="utf-8"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
