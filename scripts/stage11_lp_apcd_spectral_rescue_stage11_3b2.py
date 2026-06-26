from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_10a_240bin_refinement import flt, fmt, read_csv, write_csv
from metasurface.stage12_12a_spectral_audit import RESULT_FIELDS, phase_distance_deg, spectral_metric_from_combined

WAVELENGTHS_NM = [449, 450, 451]
TARGET_BINS = [120, 240, 300]
MAX_BY_BIN = {120: 4, 240: 4, 300: 2}
REPORT_DIR = REPO_ROOT / "reports"
RESULT_CSV = REPORT_DIR / "stage11_3b2_lp_h500_spectral_rescue_candidates.csv"
SUMMARY_MD = REPORT_DIR / "stage11_3b2_lp_h500_spectral_rescue_summary.md"
TEMP_FDTD_DIR = REPORT_DIR / "stage11_3b2_fdtd_tmp"
EPS = 1e-12

CONTROLS = {
    120: "H500DIMER2C_004_B120_x_pair_swap_G60_O-20",
    240: "H500DIMER2F_026_B240_x_pair_swap_G90_O-28",
    300: "H500DIMER2D_006_B240_x_pair_swap_G80_O-30",
}

PLAN_SOURCES = [
    "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",
    "outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_alt_patch_plan_stage11_2c.csv",
    "outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/h500_dimer_final_gap_patch_plan_stage11_2d.csv",
    "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull/h500_dimer_240_fine_pull_plan_stage11_2e.csv",
    "outputs/blue10k6_lp_apcd_stage11_2f_h500_dimer_120_240_refine/h500_dimer_120_240_refine_patch_plan_stage11_2f.csv",
    "outputs/stage11_2h_h500_120_y_pair_micro_rescue/h500_120_y_pair_micro_rescue_plan_stage11_2h.csv",
    "outputs/stage12_10a_h500_lp_240bin_single_dimer_refinement/stage12_10a_240bin_candidate_plan.csv",
    "outputs/stage12_10b_h500_lp_240bin_broad_family_scout/stage12_10b_240bin_candidate_plan.csv",
    "outputs/stage12_10d_h500_lp_300bin_single_dimer_refinement/stage12_10d_300bin_candidate_plan.csv",
]

SUMMARY_FIELDS = RESULT_FIELDS + [
    "target_bin_deg",
    "phase_error_to_target_deg",
    "pass_flag",
    "rescue_score",
]

AGG_FIELDS = [
    "target_bin_deg",
    "candidate_id",
    "case_count",
    "complete_449_450_451",
    "worst_ratio",
    "worst_Tx",
    "worst_matrix_error",
    "max_abs_phase_error_to_target",
    "min_score",
    "rescue_candidate",
    "failed_gate",
]


def load_stage11_runner():
    path = REPO_ROOT / "scripts/stage11_lp_apcd_run_h500_dimer_fdtd_stage11_2a.py"
    spec = importlib.util.spec_from_file_location("stage11_2a_runner_for_3b2", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def candidate_id(row: dict[str, str]) -> str:
    return row.get("candidate_id") or row.get("dimer_case_id") or row.get("source_plan_id") or ""


def row_target(row: dict[str, str]) -> int | None:
    for key in ["target_actual_bin_deg", "phase_bin_deg", "bin_deg", "static_original_bin_deg"]:
        value = row.get(key, "")
        if str(value).strip():
            try:
                return int(float(value))
            except ValueError:
                pass
    cid = candidate_id(row)
    if "B120" in cid:
        return 120
    if "B240" in cid:
        return 240
    if "B300" in cid:
        return 300
    return None


def family_score(row: dict[str, str], target: int) -> float:
    cid = candidate_id(row)
    score = 0.0
    if cid == CONTROLS.get(target):
        score += 10000.0
    if target == 120 and "2H" in cid:
        score += 500.0
    if target == 120 and "y_pair_noswap" in cid:
        score += 80.0
    if target == 240 and "12A" in cid:
        score += 300.0
    if target == 240 and "G90" in cid:
        score += 60.0
    if target == 300 and "12D" in cid:
        score += 250.0
    if "x_pair" in cid:
        score += 10.0
    if "diag_pair" in cid:
        score += 5.0
    if row.get("run_selected", "").lower() == "true":
        score += 20.0
    try:
        score -= abs(flt(row.get("gap_nm"), 60.0) - 60.0) * 0.1
    except Exception:
        pass
    return score


def load_plan_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rel in PLAN_SOURCES:
        path = REPO_ROOT / rel
        for row in read_csv(path):
            cid = candidate_id(row)
            if not cid.startswith("H500DIMER"):
                continue
            row = dict(row)
            row["source_file"] = str(path)
            rows.append(row)
    return rows


def select_candidate_geometries(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    seen: set[tuple[int, str]] = set()
    for target in TARGET_BINS:
        pool = [r for r in rows if row_target(r) == target or candidate_id(r) == CONTROLS[target]]
        pool.sort(key=lambda r: (-family_score(r, target), candidate_id(r)))
        picked = []
        for row in pool:
            cid = candidate_id(row)
            key = (target, cid)
            if key in seen:
                continue
            seen.add(key)
            row = dict(row)
            row["target_bin_deg"] = str(target)
            row["candidate_id"] = cid
            picked.append(row)
            if len(picked) >= MAX_BY_BIN[target]:
                break
        selected.extend(picked)
    return selected[:20]


def make_run_matrix() -> list[dict[str, str]]:
    selected = select_candidate_geometries(load_plan_rows())
    if not selected:
        raise RuntimeError("No Stage11-3B2 candidate geometries found.")
    rows: list[dict[str, str]] = []
    for base in selected:
        cid = base["candidate_id"]
        target = int(float(base["target_bin_deg"]))
        for wl in WAVELENGTHS_NM:
            row = dict(base)
            row["candidate_id"] = cid
            row["dimer_case_id"] = f"{cid}_3B2_WL{wl}NM"
            row["bin_deg"] = str(target)
            row["phase_bin_deg"] = str(target)
            row["target_actual_bin_deg"] = str(target)
            row["lambda_nm"] = f"{wl:.6f}"
            row["wavelength_nm"] = str(wl)
            row["static_output_phase_deg"] = str(target)
            row.setdefault("static_predicted_ratio", "")
            row.setdefault("static_phase_error_deg", "")
            row.setdefault("static_target_x_power", "")
            row.setdefault("static_leak_y_power", "")
            row.setdefault("p_x_nm", "431.907786")
            row.setdefault("p_y_nm", "432.000000")
            row.setdefault("height_nm", "500.000000")
            row.setdefault("geometry_legal", "true")
            row["notes"] = "Stage11-3B2 H500 LP spectral rescue over 449/450/451 nm; no K6."
            rows.append(row)
    return rows


def cleanup_temp_dir() -> None:
    if TEMP_FDTD_DIR.exists():
        shutil.rmtree(TEMP_FDTD_DIR)


def format_metric(metric: dict[str, object], row: dict[str, str]) -> dict[str, object]:
    phase = flt(metric.get("selected_channel_phase_deg"))
    target = int(float(row["target_bin_deg"]))
    phase_err = phase_distance_deg(phase, target) if not math.isnan(phase) else math.nan
    ratio = flt(metric.get("conversion_to_leakage_ratio"), 0.0)
    tx = flt(metric.get("Tx"), 0.0)
    matrix = flt(metric.get("matrix_error"), 999.0)
    ok = ratio >= 6 and tx >= 0.45 and matrix <= 0.50 and (not math.isnan(phase_err) and phase_err <= 25)
    score = min(ratio, 20.0) + 4.0 * tx - 0.08 * (phase_err if not math.isnan(phase_err) else 180.0) - 2.0 * matrix
    metric["target_bin_deg"] = str(target)
    metric["phase_error_to_target_deg"] = fmt(phase_err)
    metric["pass_flag"] = str(ok).lower()
    metric["rescue_score"] = fmt(score)
    return metric


def run_extraction(runtime_path: str = "configs/runtime.yaml", dry_run: bool = False, keep_temp: bool = False) -> list[dict[str, object]]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run_rows = make_run_matrix()
    if dry_run:
        return [{"target_bin_deg": r["target_bin_deg"], "wavelength_nm": r["wavelength_nm"], "candidate_id": r["candidate_id"], "dimer_case_id": r["dimer_case_id"], "fdtd_status": "dry_run"} for r in run_rows]
    runner = load_stage11_runner()
    runner.FDTD_DIR = TEMP_FDTD_DIR
    runner.RESULT_CSV = REPORT_DIR / "stage11_3b2_raw_combined_tmp.csv"
    runner.SUMMARY_MD = REPORT_DIR / "stage11_3b2_raw_summary_tmp.md"
    runtime = runner.load_runtime_config(runtime_path)
    lumapi = runner.import_lumapi(runtime)
    metrics: list[dict[str, object]] = []
    try:
        for row in run_rows:
            print(f"running={row['dimer_case_id']} x")
            x = runner.run_one(lumapi, runtime, row, "x")
            print(f"running={row['dimer_case_id']} y")
            y = runner.run_one(lumapi, runtime, row, "y")
            combined = runner.combine(row, x, y)
            metric = spectral_metric_from_combined(combined, {**row, "_result_csv": str(RESULT_CSV)})
            metrics.append(format_metric(metric, row))
            write_csv(RESULT_CSV, metrics, SUMMARY_FIELDS)
            print(f"done={row['dimer_case_id']} status={combined.get('fdtd_status')}")
    finally:
        if not keep_temp:
            cleanup_temp_dir()
        for tmp in [runner.RESULT_CSV, runner.SUMMARY_MD]:
            Path(tmp).unlink(missing_ok=True)
    return metrics


def summarize_candidates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str], list[dict[str, object]]] = {}
    for row in rows:
        if row.get("fdtd_status") != "ok":
            continue
        key = (int(flt(row.get("target_bin_deg"))), str(row.get("candidate_id")))
        grouped.setdefault(key, []).append(row)
    out = []
    for (target, cid), members in grouped.items():
        wls = {int(flt(r.get("wavelength_nm"))) for r in members}
        ratios = [flt(r.get("conversion_to_leakage_ratio"), 0.0) for r in members]
        txs = [flt(r.get("Tx"), 0.0) for r in members]
        matrices = [flt(r.get("matrix_error"), 999.0) for r in members]
        phases = [flt(r.get("phase_error_to_target_deg"), 999.0) for r in members]
        complete = all(w in wls for w in WAVELENGTHS_NM)
        worst_ratio = min(ratios) if ratios else 0.0
        worst_tx = min(txs) if txs else 0.0
        worst_matrix = max(matrices) if matrices else 999.0
        worst_phase = max(phases) if phases else 999.0
        failed = []
        if not complete: failed.append("missing_wavelength")
        if worst_ratio < 6: failed.append("ratio")
        if worst_tx < 0.45: failed.append("Tx")
        if worst_matrix > 0.50: failed.append("matrix_error")
        if worst_phase > 25: failed.append("phase")
        score = worst_ratio + 3.0 * worst_tx - 0.05 * worst_phase - worst_matrix
        out.append({
            "target_bin_deg": target,
            "candidate_id": cid,
            "case_count": len(members),
            "complete_449_450_451": complete,
            "worst_ratio": fmt(worst_ratio),
            "worst_Tx": fmt(worst_tx),
            "worst_matrix_error": fmt(worst_matrix),
            "max_abs_phase_error_to_target": fmt(worst_phase),
            "min_score": fmt(score),
            "rescue_candidate": str(not failed).lower(),
            "failed_gate": ";".join(failed),
        })
    out.sort(key=lambda r: (int(r["target_bin_deg"]), r["rescue_candidate"] != "true", -flt(r["min_score"])))
    return out


def best_for_bin(summary_rows: list[dict[str, object]], target: int) -> dict[str, object]:
    rows = [r for r in summary_rows if int(r["target_bin_deg"]) == target]
    rows.sort(key=lambda r: (r["rescue_candidate"] != "true", -flt(r["min_score"])))
    return rows[0] if rows else {}


def write_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    cand = summarize_candidates(rows)
    write_csv(REPORT_DIR / "stage11_3b2_lp_h500_spectral_rescue_candidate_ranking.csv", cand, AGG_FIELDS)
    ok_cases = [r for r in rows if r.get("fdtd_status") == "ok"]
    planned = len(make_run_matrix())
    complete = len(ok_cases) == planned
    best120, best240, best300 = best_for_bin(cand, 120), best_for_bin(cand, 240), best_for_bin(cand, 300)
    repaired = bool(best120) and bool(best240) and best120.get("rescue_candidate") == "true" and best240.get("rescue_candidate") == "true"
    keep300 = bool(best300) and flt(best300.get("worst_ratio"), 0) >= 6 and flt(best300.get("max_abs_phase_error_to_target"), 999) <= 25
    if repaired and keep300:
        next_step = "Stage11-3B3 freeze repaired bins and recompute six-bin spectral tuple."
    elif any(r.get("rescue_candidate") == "true" for r in cand):
        next_step = "Stage11-3B3 can try repaired-bin tuple search plus limited global-offset relabeling."
    else:
        next_step = "Stage11-3B3 should expand candidate search; current rescue batch has no full-gate replacement."
    lines = [
        "# Stage11-3B2 LP H500 Spectral Rescue Summary",
        "",
        "## Boundary",
        "- H500 LP dimer rescue only over 449/450/451 nm.",
        "- No K=6/metagrating, finite patch, dipole source, DBR, RCLED, H600/H700, or Stage10 CP modification.",
        "",
        "## Completion",
        f"- Planned spectral cases: `{planned}`.",
        f"- Successful cases: `{len(ok_cases)}`.",
        f"- Did all planned rescue cases complete? `{complete}`.",
        "",
        "## Best Candidates",
        f"- Best 120 deg replacement: `{best120.get('candidate_id','')}`; worst_ratio `{best120.get('worst_ratio','')}`, worst_Tx `{best120.get('worst_Tx','')}`, max_phase_error `{best120.get('max_abs_phase_error_to_target','')}`, failed_gate `{best120.get('failed_gate','')}`.",
        f"- Best 240 deg replacement: `{best240.get('candidate_id','')}`; worst_ratio `{best240.get('worst_ratio','')}`, worst_Tx `{best240.get('worst_Tx','')}`, max_phase_error `{best240.get('max_abs_phase_error_to_target','')}`, failed_gate `{best240.get('failed_gate','')}`.",
        f"- 300 deg check: `{best300.get('candidate_id','')}`; keep frozen/check candidate acceptable: `{keep300}`; failed_gate `{best300.get('failed_gate','')}`.",
        "",
        "## Decision",
        f"- Repaired six-bin library plausible without global phase-offset relabeling: `{repaired and keep300}`.",
        f"- Recommended next step: {next_step}",
        "",
        "## Candidate Ranking",
        "| target | candidate_id | complete | worst_ratio | worst_Tx | worst_matrix_error | max_phase_error | rescue | failed_gate |",
        "|---:|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in cand:
        lines.append(f"| {row['target_bin_deg']} | {row['candidate_id']} | {row['complete_449_450_451']} | {row['worst_ratio']} | {row['worst_Tx']} | {row['worst_matrix_error']} | {row['max_abs_phase_error_to_target']} | {row['rescue_candidate']} | {row['failed_gate']} |")
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"planned_cases": planned, "success": len(ok_cases), "all_complete": complete, "best120": best120.get("candidate_id", ""), "best240": best240.get("candidate_id", ""), "keep300": keep300, "next_step": next_step}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()
    rows = run_extraction(args.runtime, dry_run=args.dry_run, keep_temp=args.keep_temp)
    write_csv(RESULT_CSV, rows, SUMMARY_FIELDS)
    summary = write_summary(rows)
    for key, value in summary.items():
        print(f"{key}={value}")
    print(f"result_csv={RESULT_CSV}")
    print(f"summary_md={SUMMARY_MD}")
    print("boundary=h500_lp_single_dimer_449_450_451_rescue_only_no_k6_no_stage10_cp_no_finite_patch_no_dipole_no_dbr_no_rcled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
