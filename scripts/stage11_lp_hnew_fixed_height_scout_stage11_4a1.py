from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

REPORT_DIR = REPO_ROOT / "reports"
RESULT_CSV = REPORT_DIR / "stage11_4a1_lp_hnew_results.csv"
RANKING_CSV = REPORT_DIR / "stage11_4a1_lp_hnew_candidate_ranking.csv"
HEIGHT_SUMMARY_CSV = REPORT_DIR / "stage11_4a1_lp_hnew_height_summary.csv"
BOTTLENECK_MD = REPORT_DIR / "stage11_4a1_lp_hnew_bottleneck_summary.md"
NEXT_MD = REPORT_DIR / "stage11_4a1_lp_hnew_recommended_next.md"
SUMMARY_JSON = REPORT_DIR / "stage11_4a1_lp_hnew_summary.json"
REPORT_MD = REPORT_DIR / "stage11_4a1_lp_hnew_report.md"
TEMP_FDTD_DIR = REPORT_DIR / "stage11_4a1_fdtd_tmp"
RAW_TMP_CSV = REPORT_DIR / "stage11_4a1_raw_combined_tmp.csv"
RAW_TMP_MD = REPORT_DIR / "stage11_4a1_raw_summary_tmp.md"
MANIFEST = REPORT_DIR / "stage11_4a0_lp_hnew_case_manifest_stage11_4a1.json"
WAVELENGTHS = [451, 452, 453]
BINS = [0, 60, 120, 180, 240, 300]
EPS = 1e-12

TEMPLATE_BY_BIN = {
    0: "H500DIMER2C_029_B240_x_pair_noswap_G60_O-20",
    60: "H500DIMER2B_006_B180_x_pair_swap_G60_O-20",
    120: "H500DIMER2H_003_B120_y_pair_noswap_G22_O-30",
    180: "H500DIMER2C_026_B240_x_pair_swap_G60_O-20",
    240: "H500DIMER12A_012_B240_x_pair_swap_G85_O-32",
    300: "H500DIMER12D_003_B300_x_pair_swap_G90_O-30",
}
RESULT_FIELDS = [
    "case_id", "height_nm", "wavelength_nm", "phase_bin_deg", "candidate_id", "target_Tx", "y_leakage",
    "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg", "matrix_error", "pass_level",
    "result_csv", "status",
]
RANK_FIELDS = [
    "height_nm", "phase_bin_deg", "candidate_id", "complete_451_452_453", "worst_ratio", "worst_Tx",
    "worst_matrix_error", "max_phase_error_deg", "best_pass_level", "robust_3nm_pass", "failed_gates",
]
HEIGHT_FIELDS = [
    "height_nm", "planned_cases", "ok_cases", "failed_cases", "strict_cases", "loose_cases", "fail_cases",
    "complete_sixbin_451_452_453", "worst_ratio", "worst_Tx", "worst_matrix_error", "max_phase_error_deg",
    "bottleneck_bins", "recommendation",
]


def load_module(name: str, rel: str):
    path = REPO_ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


rescue = load_module("stage11_3b2_for_4a1", "scripts/stage11_lp_apcd_spectral_rescue_stage11_3b2.py")
runner_mod = None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def phase_dist(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def load_template_rows() -> dict[str, dict[str, str]]:
    rows = {}
    for row in rescue.load_plan_rows():
        cid = row.get("candidate_id") or row.get("dimer_case_id") or row.get("source_plan_id") or ""
        if cid and cid not in rows:
            rows[cid] = dict(row)
    missing = [cid for cid in TEMPLATE_BY_BIN.values() if cid not in rows]
    if missing:
        raise RuntimeError("Missing H500 template plan rows: " + ";".join(missing))
    return rows


def planned_case_rows() -> list[dict[str, str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("hard_case_cap", 0) < 42:
        raise RuntimeError("Stage11-4A1 hard case cap is below 42")
    templates = load_template_rows()
    rows = []
    for height, bins in [(600, BINS), (650, BINS), (700, [240, 300])]:
        for bin_deg in bins:
            base = dict(templates[TEMPLATE_BY_BIN[bin_deg]])
            for wl in WAVELENGTHS:
                case_id = f"S11_4A1_H{height}_B{bin_deg:03d}_WL{wl}"
                row = dict(base)
                row.update({
                    "case_id": case_id,
                    "dimer_case_id": case_id,
                    "candidate_id": f"H{height}_FROM_{TEMPLATE_BY_BIN[bin_deg]}",
                    "source_pair_id": TEMPLATE_BY_BIN[bin_deg],
                    "bin_deg": str(bin_deg),
                    "phase_bin_deg": str(bin_deg),
                    "target_bin_deg": str(bin_deg),
                    "target_actual_bin_deg": str(bin_deg),
                    "height_nm": f"{height:.6f}",
                    "lambda_nm": f"{wl:.6f}",
                    "wavelength_nm": str(wl),
                    "static_output_phase_deg": str(bin_deg),
                    "static_predicted_ratio": "",
                    "static_target_x_power": "",
                    "static_leak_y_power": "",
                    "p_x_nm": row.get("p_x_nm") or "431.907786",
                    "p_y_nm": row.get("p_y_nm") or "432.000000",
                    "geometry_legal": "true",
                    "notes": "Stage11-4A1 Hnew fixed-height single-dimer spectral scout; no K6.",
                })
                rows.append(row)
    if len(rows) != 42:
        raise RuntimeError(f"Expected 42 planned cases, got {len(rows)}")
    return rows


def existing_results() -> dict[str, dict[str, str]]:
    out = {}
    for row in read_csv(RESULT_CSV):
        case_id = row.get("case_id", "")
        if case_id and row.get("status") in {"ok", "failed"}:
            out[case_id] = row
    return out


def pass_level(ratio: float, tx: float, matrix: float, phase_error: float) -> str:
    if ratio >= 6 and tx >= 0.45 and matrix <= 0.50 and phase_error <= 25:
        return "strict"
    if ratio >= 3 and tx >= 0.10 and matrix <= 1.00 and phase_error <= 35:
        return "loose"
    return "fail"


def result_row(row: dict[str, str], combined: dict[str, object], metric: dict[str, object]) -> dict[str, str]:
    phase = flt(metric.get("selected_channel_phase_deg"))
    target = int(float(row["phase_bin_deg"]))
    phase_error = phase_dist(phase, target) if not math.isnan(phase) else math.nan
    tx = flt(metric.get("Tx"), 0.0)
    leakage = flt(metric.get("blocked_y_total_leakage"), flt(metric.get("y_leakage"), math.nan))
    ratio = flt(metric.get("conversion_to_leakage_ratio"), 0.0)
    matrix = flt(metric.get("matrix_error"), 999.0)
    status = str(combined.get("fdtd_status", metric.get("fdtd_status", "failed")))
    level = pass_level(ratio, tx, matrix, phase_error) if status == "ok" else "fail"
    return {
        "case_id": row["case_id"],
        "height_nm": str(int(float(row["height_nm"]))),
        "wavelength_nm": str(int(float(row["wavelength_nm"]))),
        "phase_bin_deg": str(target),
        "candidate_id": row["candidate_id"],
        "target_Tx": fmt(tx),
        "y_leakage": fmt(leakage),
        "conversion_to_leakage_ratio": fmt(ratio),
        "selected_phase_deg": fmt(phase % 360.0 if not math.isnan(phase) else math.nan),
        "phase_error_deg": fmt(phase_error),
        "matrix_error": fmt(matrix),
        "pass_level": level,
        "result_csv": str(combined.get("x_result_csv", "")) + ";" + str(combined.get("y_result_csv", "")),
        "status": status,
    }


def cleanup_temp_dir() -> None:
    if TEMP_FDTD_DIR.exists():
        shutil.rmtree(TEMP_FDTD_DIR)
    RAW_TMP_CSV.unlink(missing_ok=True)
    RAW_TMP_MD.unlink(missing_ok=True)


def run_missing(runtime_path: str = "configs/runtime.yaml", dry_run: bool = False) -> tuple[list[dict[str, str]], dict[str, int]]:
    planned = planned_case_rows()
    existing = existing_results()
    missing = [row for row in planned if row["case_id"] not in existing]
    counts = {"planned": len(planned), "reused": len(planned) - len(missing), "run": 0, "failed": 0, "missing": len(missing)}
    if dry_run:
        return list(existing.values()), counts
    global runner_mod
    runner_mod = rescue.load_stage11_runner()
    runner_mod.FDTD_DIR = TEMP_FDTD_DIR
    runner_mod.RESULT_CSV = RAW_TMP_CSV
    runner_mod.SUMMARY_MD = RAW_TMP_MD
    runtime = runner_mod.load_runtime_config(runtime_path)
    lumapi = runner_mod.import_lumapi(runtime)
    rows = list(existing.values())
    try:
        for row in missing:
            print(f"running={row['case_id']} x")
            x = runner_mod.run_one(lumapi, runtime, row, "x")
            print(f"running={row['case_id']} y")
            y = runner_mod.run_one(lumapi, runtime, row, "y")
            combined = runner_mod.combine(row, x, y)
            metric = rescue.spectral_metric_from_combined(combined, {**row, "_result_csv": str(RESULT_CSV)})
            out = result_row(row, combined, metric)
            rows.append(out)
            counts["run"] += 1
            if out["status"] != "ok":
                counts["failed"] += 1
            write_csv(RESULT_CSV, sorted(rows, key=lambda r: r["case_id"]), RESULT_FIELDS)
            print(f"done={row['case_id']} status={out['status']}")
    finally:
        cleanup_temp_dir()
    return sorted(rows, key=lambda r: r["case_id"]), counts


def rank_candidates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped = {}
    for row in rows:
        key = (row["height_nm"], row["phase_bin_deg"], row["candidate_id"])
        grouped.setdefault(key, []).append(row)
    out = []
    for (height, bin_deg, cid), members in grouped.items():
        ok = [m for m in members if m.get("status") == "ok"]
        wls = {int(float(m["wavelength_nm"])) for m in ok}
        ratios = [flt(m["conversion_to_leakage_ratio"], 0.0) for m in ok]
        txs = [flt(m["target_Tx"], 0.0) for m in ok]
        matrices = [flt(m["matrix_error"], 999.0) for m in ok]
        phases = [flt(m["phase_error_deg"], 999.0) for m in ok]
        complete = all(w in wls for w in WAVELENGTHS)
        worst_ratio = min(ratios) if ratios else 0.0
        worst_tx = min(txs) if txs else 0.0
        worst_matrix = max(matrices) if matrices else 999.0
        worst_phase = max(phases) if phases else 999.0
        failed = []
        if not complete: failed.append("missing")
        if worst_ratio < 6: failed.append("ratio")
        if worst_tx < 0.45: failed.append("Tx")
        if worst_matrix > 0.50: failed.append("matrix")
        if worst_phase > 25: failed.append("phase")
        levels = [m.get("pass_level", "fail") for m in ok]
        out.append({
            "height_nm": height,
            "phase_bin_deg": bin_deg,
            "candidate_id": cid,
            "complete_451_452_453": str(complete).lower(),
            "worst_ratio": fmt(worst_ratio),
            "worst_Tx": fmt(worst_tx),
            "worst_matrix_error": fmt(worst_matrix),
            "max_phase_error_deg": fmt(worst_phase),
            "best_pass_level": "strict" if "strict" in levels else ("loose" if "loose" in levels else "fail"),
            "robust_3nm_pass": str(not failed).lower(),
            "failed_gates": ";".join(failed),
        })
    out.sort(key=lambda r: (int(r["height_nm"]), int(r["phase_bin_deg"])))
    return out


def height_summary(rows: list[dict[str, str]], ranking: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    h500_history = {240: 4.564178, 300: 4.507269}
    for height in [600, 650, 700]:
        members = [r for r in rows if int(r["height_nm"]) == height]
        ranks = [r for r in ranking if int(r["height_nm"]) == height]
        active_bins = [240, 300] if height == 700 else BINS
        complete = all(any(int(r["phase_bin_deg"]) == b and r["robust_3nm_pass"] == "true" for r in ranks) for b in active_bins)
        ratios = [flt(r["conversion_to_leakage_ratio"], 0.0) for r in members if r.get("status") == "ok"]
        txs = [flt(r["target_Tx"], 0.0) for r in members if r.get("status") == "ok"]
        matrices = [flt(r["matrix_error"], 999.0) for r in members if r.get("status") == "ok"]
        phases = [flt(r["phase_error_deg"], 999.0) for r in members if r.get("status") == "ok"]
        bottlenecks = [r["phase_bin_deg"] for r in ranks if r["robust_3nm_pass"] != "true"]
        if complete and height in [600, 650]:
            rec = f"refine H{height} tuple or expand to 448/452 validation"
        elif height == 700:
            rec = "scout H700 more only if H600/H650 fail"
        else:
            rec = f"refine H{height}" if ranks else "no data"
        out.append({
            "height_nm": str(height),
            "planned_cases": str(len(members)),
            "ok_cases": str(sum(1 for r in members if r.get("status") == "ok")),
            "failed_cases": str(sum(1 for r in members if r.get("status") != "ok")),
            "strict_cases": str(sum(1 for r in members if r.get("pass_level") == "strict")),
            "loose_cases": str(sum(1 for r in members if r.get("pass_level") == "loose")),
            "fail_cases": str(sum(1 for r in members if r.get("pass_level") == "fail")),
            "complete_sixbin_451_452_453": str(complete and height in [600, 650]).lower(),
            "worst_ratio": fmt(min(ratios) if ratios else 0.0),
            "worst_Tx": fmt(min(txs) if txs else 0.0),
            "worst_matrix_error": fmt(max(matrices) if matrices else 999.0),
            "max_phase_error_deg": fmt(max(phases) if phases else 999.0),
            "bottleneck_bins": ";".join(bottlenecks),
            "recommendation": rec,
        })
    return out


def write_reports(rows: list[dict[str, str]], counts: dict[str, int]) -> dict[str, object]:
    write_csv(RESULT_CSV, rows, RESULT_FIELDS)
    ranking = rank_candidates(rows)
    write_csv(RANKING_CSV, ranking, RANK_FIELDS)
    heights = height_summary(rows, ranking)
    write_csv(HEIGHT_SUMMARY_CSV, heights, HEIGHT_FIELDS)
    best_height = next((h for h in heights if h["complete_sixbin_451_452_453"] == "true"), None)
    bottleneck_lines = ["# Stage11-4A1 Bottleneck Summary", ""]
    for rank in ranking:
        if rank["robust_3nm_pass"] != "true" or rank["phase_bin_deg"] in {"240", "300"}:
            bottleneck_lines.append(f"- H{rank['height_nm']} bin {rank['phase_bin_deg']}: robust={rank['robust_3nm_pass']}, worst_ratio={rank['worst_ratio']}, worst_Tx={rank['worst_Tx']}, max_phase_error={rank['max_phase_error_deg']}, failed={rank['failed_gates']}.")
    BOTTLENECK_MD.write_text("\n".join(bottleneck_lines) + "\n", encoding="utf-8")
    if best_height:
        next_text = f"Stage11-4A2 recommendation: refine H{best_height['height_nm']} or validate adjacent 448/452 nm before K=6."
    else:
        next_text = "Stage11-4A2 recommendation: stop direct Hnew height-scaled template rescue; no H600/H650/H700 scout produced a viable 3-nm tuple. Use broader fixed-height geometry reconstruction before any K=6 work."
    NEXT_MD.write_text("# Stage11-4A1 Recommended Next\n\n" + next_text + "\n", encoding="utf-8")
    summary = {
        **counts,
        "ok_cases": sum(1 for r in rows if r.get("status") == "ok"),
        "failed_cases": sum(1 for r in rows if r.get("status") != "ok"),
        "h600_complete_sixbin": any(h["height_nm"] == "600" and h["complete_sixbin_451_452_453"] == "true" for h in heights),
        "h650_complete_sixbin": any(h["height_nm"] == "650" and h["complete_sixbin_451_452_453"] == "true" for h in heights),
        "any_height_robust_3nm": any(h["complete_sixbin_451_452_453"] == "true" for h in heights),
        "recommended_next": next_text,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = ["# Stage11-4A1 LP-Hnew Report", "", f"planned={counts['planned']} reused={counts['reused']} run={counts['run']} failed={counts['failed']}", "", next_text, "", "## Height Summary"]
    for h in heights:
        lines.append(f"- H{h['height_nm']}: complete={h['complete_sixbin_451_452_453']}, worst_ratio={h['worst_ratio']}, bottlenecks={h['bottleneck_bins']}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    planned = planned_case_rows()
    existing = existing_results()
    missing = [row for row in planned if row["case_id"] not in existing]
    print(f"planned_case_count={len(planned)}")
    print(f"existing_reusable_count={len(planned) - len(missing)}")
    print(f"missing_case_count={len(missing)}")
    rows, counts = run_missing(args.runtime, dry_run=args.dry_run)
    summary = write_reports(rows, counts)
    for key, value in summary.items():
        print(f"{key}={value}")
    print("boundary=H600_H650_all_bins_H700_240_300_only_no_K6_no_patch_no_dipole_no_DBR_no_RCLED_no_H500_rescue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
