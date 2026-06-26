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

from metasurface.stage12_12a_spectral_audit import RESULT_FIELDS, matrix_error, phase_distance_deg, spectral_metric_from_combined
from metasurface.stage12_10a_240bin_refinement import flt, fmt, nearest_bin, read_csv, write_csv

WAVELENGTHS_NM = [449, 451]
FROZEN = [
    (0, "H500DIMER2C_029_B240_x_pair_noswap_G60_O-20"),
    (60, "H500DIMER2B_006_B180_x_pair_swap_G60_O-20"),
    (120, "H500DIMER2C_004_B120_x_pair_swap_G60_O-20"),
    (180, "H500DIMER2C_026_B240_x_pair_swap_G60_O-20"),
    (240, "H500DIMER2F_026_B240_x_pair_swap_G90_O-28"),
    (300, "H500DIMER2D_006_B240_x_pair_swap_G80_O-30"),
]
REPORT_DIR = REPO_ROOT / "reports"
RESULT_CSV = REPORT_DIR / "stage11_3b1_lp_h500_frozen_sixbin_449_451_results.csv"
SUMMARY_MD = REPORT_DIR / "stage11_3b1_lp_h500_frozen_sixbin_449_451_summary.md"
TEMP_FDTD_DIR = REPORT_DIR / "stage11_3b1_fdtd_tmp"
PLAN_SOURCES = [
    REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_alt_patch_plan_stage11_2c.csv",
]
SUMMARY_FIELDS = RESULT_FIELDS + ["phase_error_to_bin_deg"]
EPS = 1e-12


def load_stage11_runner():
    path = REPO_ROOT / "scripts/stage11_lp_apcd_run_h500_dimer_fdtd_stage11_2a.py"
    spec = importlib.util.spec_from_file_location("stage11_2a_runner_for_3b1", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plan_rows_by_candidate() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for source in PLAN_SOURCES:
        for row in read_csv(source):
            cid = row.get("candidate_id") or row.get("dimer_case_id") or row.get("source_plan_id") or ""
            if cid and cid not in rows:
                row = dict(row)
                row["source_file"] = str(source)
                rows[cid] = row
    return rows


def make_run_matrix() -> list[dict[str, str]]:
    by_candidate = plan_rows_by_candidate()
    run_rows: list[dict[str, str]] = []
    missing = []
    for bin_deg, cid in FROZEN:
        base = by_candidate.get(cid)
        if not base:
            missing.append(cid)
            continue
        for wl in WAVELENGTHS_NM:
            row = dict(base)
            row["candidate_id"] = cid
            row["dimer_case_id"] = f"{cid}_WL{wl}NM"
            row["bin_deg"] = str(bin_deg)
            row["phase_bin_deg"] = str(bin_deg)
            row["lambda_nm"] = f"{wl:.6f}"
            row["wavelength_nm"] = str(wl)
            row["static_output_phase_deg"] = str(bin_deg)
            row.setdefault("static_predicted_ratio", "")
            row.setdefault("p_x_nm", "431.907786")
            row.setdefault("p_y_nm", "432.000000")
            row.setdefault("height_nm", "500.000000")
            row.setdefault("geometry_legal", "true")
            row["notes"] = "Stage11-3B1 frozen H500 LP six-bin 449/451 nm single-dimer spectral extraction; no K6."
            run_rows.append(row)
    if missing:
        raise FileNotFoundError("Missing geometry plan rows for: " + ", ".join(missing))
    return run_rows


def cleanup_temp_dir() -> None:
    if TEMP_FDTD_DIR.exists():
        shutil.rmtree(TEMP_FDTD_DIR)


def format_metric(metric: dict[str, object], row: dict[str, str]) -> dict[str, object]:
    phase = flt(metric.get("selected_channel_phase_deg"))
    bin_deg = int(flt(row.get("bin_deg")))
    metric["phase_error_to_bin_deg"] = fmt(phase_distance_deg(phase, bin_deg)) if not math.isnan(phase) else ""
    return metric


def run_extraction(runtime_path: str = "configs/runtime.yaml", dry_run: bool = False, keep_temp: bool = False) -> list[dict[str, object]]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run_rows = make_run_matrix()
    if dry_run:
        return [{"wavelength_nm": r["wavelength_nm"], "bin_deg": r["bin_deg"], "candidate_id": r["candidate_id"], "dimer_case_id": r["dimer_case_id"], "fdtd_status": "dry_run"} for r in run_rows]
    runner = load_stage11_runner()
    runner.FDTD_DIR = TEMP_FDTD_DIR
    runner.RESULT_CSV = REPORT_DIR / "stage11_3b1_raw_combined_tmp.csv"
    runner.SUMMARY_MD = REPORT_DIR / "stage11_3b1_raw_summary_tmp.md"
    runtime = runner.load_runtime_config(runtime_path)
    lumapi = runner.import_lumapi(runtime)
    combined_rows: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    try:
        for row in run_rows:
            print(f"running={row['dimer_case_id']} x")
            x = runner.run_one(lumapi, runtime, row, "x")
            print(f"running={row['dimer_case_id']} y")
            y = runner.run_one(lumapi, runtime, row, "y")
            combined = runner.combine(row, x, y)
            combined_rows.append(combined)
            metric = spectral_metric_from_combined(combined, {**row, "_result_csv": str(RESULT_CSV)})
            metrics.append(format_metric(metric, row))
            write_csv(RESULT_CSV, metrics, SUMMARY_FIELDS)
            print(f"done={row['dimer_case_id']} status={combined.get('fdtd_status')}")
    finally:
        if not keep_temp:
            cleanup_temp_dir()
        for tmp in [runner.RESULT_CSV, runner.SUMMARY_MD]:
            try:
                Path(tmp).unlink(missing_ok=True)
            except Exception:
                pass
    return metrics


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    ok = [r for r in rows if r.get("fdtd_status") == "ok"]
    failed = [r for r in rows if r.get("fdtd_status") not in {"ok", "dry_run"}]
    by_wl = {wl: [r for r in ok if int(flt(r.get("wavelength_nm"))) == wl] for wl in WAVELENGTHS_NM}
    weakest = min(ok, key=lambda r: flt(r.get("conversion_to_leakage_ratio"), math.inf), default={})
    worst_phase = max(ok, key=lambda r: flt(r.get("phase_error_to_bin_deg"), -math.inf), default={})
    all_complete = len(ok) == len(FROZEN) * len(WAVELENGTHS_NM)
    all_wavelengths_available = all(len(v) == len(FROZEN) for v in by_wl.values())
    plausible = all_complete and all(flt(r.get("conversion_to_leakage_ratio"), 0) >= 6 for r in ok)
    return {
        "total_cases": len(rows),
        "success": len(ok),
        "failed": len(failed),
        "all_12_cases_complete": all_complete,
        "all_449_451_available_for_six_bins": all_wavelengths_available,
        "weakest_selectivity_bin": weakest.get("bin_deg", ""),
        "weakest_selectivity_wavelength_nm": weakest.get("wavelength_nm", ""),
        "weakest_selectivity_ratio": weakest.get("conversion_to_leakage_ratio", ""),
        "worst_phase_drift_bin": worst_phase.get("bin_deg", ""),
        "worst_phase_drift_wavelength_nm": worst_phase.get("wavelength_nm", ""),
        "worst_phase_error_to_bin_deg": worst_phase.get("phase_error_to_bin_deg", ""),
        "frozen_set_plausible_449_450_451": plausible,
    }


def write_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    s = summarize(rows)
    lines = [
        "# Stage11-3B1 LP H500 Frozen Six-bin 449/451 nm Extraction Summary",
        "",
        "## Boundary",
        "- H500 frozen LP dimer candidates only.",
        "- Wavelengths run: 449 and 451 nm only; existing 450 nm was not rerun.",
        "- No K=6/metagrating, finite patch, dipole source, DBR, RCLED, or Stage10 CP files touched.",
        "",
        "## Completion",
        f"- Did all 12 cases complete? `{s['all_12_cases_complete']}` ({s['success']} success, {s['failed']} failed).",
        f"- Are 449/451 nm data now available for all six bins? `{s['all_449_451_available_for_six_bins']}`.",
        "",
        "## Weakest Cases",
        f"- Worst LP selectivity over 450±1 nm new points: bin `{s['weakest_selectivity_bin']}` at `{s['weakest_selectivity_wavelength_nm']}` nm, ratio `{s['weakest_selectivity_ratio']}`.",
        f"- Worst selected-channel phase drift: bin `{s['worst_phase_drift_bin']}` at `{s['worst_phase_drift_wavelength_nm']}` nm, phase error `{s['worst_phase_error_to_bin_deg']}` deg.",
        "",
        "## Decision",
        f"- Frozen six-bin set remains plausible over 449/450/451 nm: `{s['frozen_set_plausible_449_450_451']}`.",
        "- If false, Stage11-3B2 should switch to spectral rescue before any K=6 validation.",
        "",
        "## Per-case Results",
        "| wavelength_nm | bin | candidate_id | status | Tx | leakage | ratio | phase | phase_error | matrix_error |",
        "|---:|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r.get('wavelength_nm','')} | {r.get('bin_deg','')} | {r.get('candidate_id','')} | {r.get('fdtd_status','')} | "
            f"{r.get('Tx','')} | {r.get('blocked_y_total_leakage','')} | {r.get('conversion_to_leakage_ratio','')} | "
            f"{r.get('selected_channel_phase_deg','')} | {r.get('phase_error_to_bin_deg','')} | {r.get('matrix_error','')} |"
        )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return s


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()
    rows = run_extraction(args.runtime, dry_run=args.dry_run, keep_temp=args.keep_temp)
    write_csv(RESULT_CSV, rows, SUMMARY_FIELDS)
    summary = write_summary(rows)
    for k, v in summary.items():
        print(f"{k}={v}")
    print(f"result_csv={RESULT_CSV}")
    print(f"summary_md={SUMMARY_MD}")
    print("boundary=h500_frozen_sixbin_single_dimer_449_451_only_no_k6_no_stage10_cp_no_finite_patch_no_dipole_no_dbr_no_rcled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
