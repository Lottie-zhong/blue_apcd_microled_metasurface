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
RESULT_CSV = REPORT_DIR / "stage11_4a12_true_b300_mini_escape_results.csv"
RANKING_CSV = REPORT_DIR / "stage11_4a12_true_b300_mini_escape_ranking.csv"
SUMMARY_JSON = REPORT_DIR / "stage11_4a12_true_b300_mini_escape_summary.json"
REPORT_MD = REPORT_DIR / "stage11_4a12_true_b300_mini_escape_report.md"
NEXT_MD = REPORT_DIR / "stage11_4a12_true_b300_mini_escape_recommended_next.md"
A9_MANIFEST = REPORT_DIR / "stage11_4a9_true_b300_new_anchor_manifest.json"
SOURCE_MANIFEST_3B4 = REPORT_DIR / "stage11_3b4_lp_h500_case_manifest.json"
TEMP_FDTD_DIR = REPORT_DIR / "stage11_4a10_fdtd_tmp"
RAW_TMP_CSV = REPORT_DIR / "stage11_4a10_raw_combined_tmp.csv"
RAW_TMP_MD = REPORT_DIR / "stage11_4a10_raw_summary_tmp.md"
WAVELENGTHS = [451, 452, 453]
TARGET_BIN = 300
BINS = [0, 60, 120, 180, 240, 300]
GROUP_ID = "S11_4A9_G3_TRUE_B300_MINI_ESCAPE"
A8_B60_DONOR = {"ratio": 11.278722, "Tx": 0.752180, "matrix": 0.297811, "phase_error_to_B60": 24.596581}
EXCLUDED_SOURCE_IDS = {
    "H500DIMER12D_002_B300_x_pair_swap_G80_O-30",
    "H500DIMER12D_004_B300_x_pair_swap_G80_O-40",
    "H500DIMER12D_005_B300_x_pair_swap_G80_O-20",
    "H500DIMER12D_006_B300_x_pair_noswap_G80_O-30",
    "H500DIMER12D_003_B300_x_pair_swap_G90_O-30",
    "H500DIMER12D_007_B300_x_pair_noswap_G100_O-24",
}
RESULT_FIELDS = ["case_id", "group_id", "height_nm", "wavelength_nm", "phase_bin_deg", "candidate_id", "target_Tx", "y_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg", "matrix_error", "pass_level", "result_csv", "status", "nearest_actual_bin_deg", "reassignment_flag"]
RANK_FIELDS = ["candidate_id", "source_candidate_id", "case_count", "complete_451_452_453", "worst_ratio", "worst_Tx", "worst_matrix_error", "max_phase_error_deg", "nearest_actual_bins", "best_pass_level", "near_miss", "reassignment_flag", "failed_gates", "score"]


def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


a5 = load_module("stage11_4a5_helpers_for_4a10", "scripts/stage11_lp_h600_b240_mechanism_expansion_stage11_4a5.py")
rescue = a5.rescue
a1 = a5.a1


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
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


def circ_diff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def phase_error(phase: float, target: int = TARGET_BIN) -> float:
    return abs(circ_diff(phase, target))


def nearest_bin(phase: float) -> int:
    return min(BINS, key=lambda b: abs(circ_diff(phase, b)))


def candidate_id(row: dict[str, str]) -> str:
    return row.get("candidate_id") or row.get("dimer_case_id") or row.get("source_plan_id") or ""


def validate_group() -> None:
    data = json.loads(A9_MANIFEST.read_text(encoding="utf-8"))
    group = next((g for g in data["run_groups"] if g["group_id"] == GROUP_ID), None)
    if not group or int(group["planned_cases"]) != 6:
        raise RuntimeError("A9 G3 must be exactly 6 cases")


G3_SOURCE_IDS = {
    "H500DIMER12D_009_B300_y_pair_noswap_G80_O-30",
    "H500DIMER12D_011_B300_diag_pair_noswap_G80_O-30",
}


def source_rows() -> dict[str, dict[str, str]]:
    data = json.loads(SOURCE_MANIFEST_3B4.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for row in data.get("cases", []):
        cid = candidate_id(row)
        if cid in G3_SOURCE_IDS and cid not in out:
            out[cid] = dict(row)
    return out


def geometries() -> list[dict[str, str]]:
    src = source_rows()
    specs = [
        ("H500DIMER12D_009_B300_y_pair_noswap_G80_O-30", "y_pair", "J1-J2", 120.0),
        ("H500DIMER12D_011_B300_diag_pair_noswap_G80_O-30", "diag_pair", "J1-J2", 100.0),
    ]
    rows = []
    for idx, (sid, placement, swap, gap) in enumerate(specs, start=1):
        if sid not in src:
            raise RuntimeError(f"Missing source {sid}")
        row = a5.set_centers(src[sid], placement, swap, gap)
        if row is None:
            raise RuntimeError(f"Illegal geometry {sid} {placement} {swap} G{gap}")
        row["source_candidate_id"] = sid
        row["variant_index"] = f"{idx:03d}"
        rows.append(row)
    return rows

def run_matrix() -> list[dict[str, str]]:
    validate_group()
    rows = []
    for idx, base in enumerate(geometries(), start=1):
        for wl in WAVELENGTHS:
            gap = int(round(flt(base["gap_nm"])))
            cid = f"H600TRUEB300G3_{idx:03d}_{base['placement_type']}_{base['swap_order'].replace('-', '')}_G{gap}"
            case_id = f"S11_4A12_TRUE_B300_G3_{idx:03d}_WL{wl}"
            row = dict(base)
            row.update({
                "case_id": case_id,
                "dimer_case_id": case_id,
                "group_id": GROUP_ID,
                "candidate_id": cid,
                "source_pair_id": base["source_candidate_id"],
                "bin_deg": str(TARGET_BIN),
                "phase_bin_deg": str(TARGET_BIN),
                "target_bin_deg": str(TARGET_BIN),
                "target_actual_bin_deg": str(TARGET_BIN),
                "height_nm": "600.000000",
                "lambda_nm": f"{wl:.6f}",
                "wavelength_nm": str(wl),
                "static_output_phase_deg": str(TARGET_BIN),
                "static_predicted_ratio": "",
                "p_x_nm": row.get("p_x_nm") or "431.907786",
                "p_y_nm": row.get("p_y_nm") or "432.000000",
                "notes": "Stage11-4A12 true B300 G1 mini-escape only; no coverage/H650/K6, coverage, H650, K6.",
            })
            rows.append(row)
    if len(rows) != 6:
        raise RuntimeError(f"Expected 6 A12 rows, got {len(rows)}")
    return rows


def existing_results() -> dict[str, dict[str, str]]:
    return {r["case_id"]: r for r in read_csv(RESULT_CSV) if r.get("case_id") and r.get("status") in {"ok", "failed"}}


def reassignment_flag(nearest: int, level: str) -> str:
    if nearest == TARGET_BIN and level in {"strict", "loose", "near_miss"}:
        return "true_b300_candidate"
    if nearest != TARGET_BIN and level in {"strict", "loose", "near_miss"}:
        return f"reassigned_B{nearest}"
    return "none"


def result_row(row: dict[str, str], combined: dict[str, object], metric: dict[str, object]) -> dict[str, str]:
    phase = flt(metric.get("selected_channel_phase_deg"))
    perr = phase_error(phase) if not math.isnan(phase) else math.nan
    tx = flt(metric.get("Tx"), 0.0)
    leakage = flt(metric.get("blocked_y_total_leakage"), flt(metric.get("y_leakage"), math.nan))
    ratio = flt(metric.get("conversion_to_leakage_ratio"), 0.0)
    matrix = flt(metric.get("matrix_error"), 999.0)
    status = str(combined.get("fdtd_status", metric.get("fdtd_status", "failed")))
    level = a1.pass_level(ratio, tx, matrix, perr) if status == "ok" else "fail"
    nb = nearest_bin(phase) if not math.isnan(phase) else -1
    if level == "fail" and status == "ok" and ratio >= 6 and tx >= 0.45 and matrix <= 0.50 and perr <= 45:
        level = "near_miss"
    return {
        "case_id": row["case_id"], "group_id": GROUP_ID, "height_nm": "600", "wavelength_nm": row["wavelength_nm"], "phase_bin_deg": str(TARGET_BIN),
        "candidate_id": row["candidate_id"], "target_Tx": fmt(tx), "y_leakage": fmt(leakage), "conversion_to_leakage_ratio": fmt(ratio),
        "selected_phase_deg": fmt(phase % 360.0 if not math.isnan(phase) else math.nan), "phase_error_deg": fmt(perr), "matrix_error": fmt(matrix),
        "pass_level": level, "result_csv": str(combined.get("x_result_csv", "")) + ";" + str(combined.get("y_result_csv", "")), "status": status,
        "nearest_actual_bin_deg": str(nb), "reassignment_flag": reassignment_flag(nb, level),
    }


def cleanup_temp() -> None:
    if TEMP_FDTD_DIR.exists():
        shutil.rmtree(TEMP_FDTD_DIR)
    RAW_TMP_CSV.unlink(missing_ok=True)
    RAW_TMP_MD.unlink(missing_ok=True)


def run_extraction(runtime_path: str = "configs/runtime.yaml", dry_run: bool = False) -> tuple[list[dict[str, str]], dict[str, int]]:
    planned = run_matrix()
    existing = existing_results()
    missing = [r for r in planned if r["case_id"] not in existing]
    counts = {"planned": len(planned), "reused": len(planned) - len(missing), "run": 0, "failed": 0, "missing": len(missing)}
    if dry_run:
        return list(existing.values()), counts
    runner = rescue.load_stage11_runner()
    runner.FDTD_DIR = TEMP_FDTD_DIR
    runner.RESULT_CSV = RAW_TMP_CSV
    runner.SUMMARY_MD = RAW_TMP_MD
    runtime = runner.load_runtime_config(runtime_path)
    lumapi = runner.import_lumapi(runtime)
    rows = list(existing.values())
    try:
        for row in missing:
            print(f"running={row['case_id']} x")
            x = runner.run_one(lumapi, runtime, row, "x")
            print(f"running={row['case_id']} y")
            y = runner.run_one(lumapi, runtime, row, "y")
            combined = runner.combine(row, x, y)
            metric = rescue.spectral_metric_from_combined(combined, {**row, "_result_csv": str(RESULT_CSV)})
            out = result_row(row, combined, metric)
            rows.append(out)
            counts["run"] += 1
            if out["status"] != "ok":
                counts["failed"] += 1
            write_csv(RESULT_CSV, sorted(rows, key=lambda r: r["case_id"]), RESULT_FIELDS)
            print(f"done={row['case_id']} status={out['status']}")
    finally:
        cleanup_temp()
    counts["missing"] = max(0, len(planned) - len(rows))
    return sorted(rows, key=lambda r: r["case_id"]), counts


def source_candidate(cid: str) -> str:
    row = next((r for r in run_matrix() if r["candidate_id"] == cid), {})
    return row.get("source_pair_id", "")


def rank_candidates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["candidate_id"], []).append(row)
    ranked = []
    for cid, members in groups.items():
        ok = [m for m in members if m.get("status") == "ok"]
        complete = {int(float(m["wavelength_nm"])) for m in ok} == set(WAVELENGTHS)
        ratios = [flt(m["conversion_to_leakage_ratio"], 0.0) for m in ok]
        txs = [flt(m["target_Tx"], 0.0) for m in ok]
        matrices = [flt(m["matrix_error"], 999.0) for m in ok]
        phases = [flt(m["phase_error_deg"], 999.0) for m in ok]
        flags = {m["reassignment_flag"] for m in ok}
        bins = sorted({m["nearest_actual_bin_deg"] for m in ok})
        worst_ratio = min(ratios) if ratios else 0.0
        worst_tx = min(txs) if txs else 0.0
        worst_matrix = max(matrices) if matrices else 999.0
        worst_phase = max(phases) if phases else 999.0
        if complete and worst_ratio >= 6 and worst_tx >= 0.45 and worst_matrix <= 0.50 and worst_phase <= 25:
            level = "strict"
        elif complete and worst_ratio >= 3 and worst_tx >= 0.10 and worst_matrix <= 1.00 and worst_phase <= 35:
            level = "loose"
        elif complete and worst_ratio >= 6 and worst_tx >= 0.45 and worst_matrix <= 0.50 and worst_phase <= 45:
            level = "near_miss"
        else:
            level = "fail"
        failed = []
        if not complete: failed.append("missing")
        if worst_ratio < 6: failed.append("ratio")
        if worst_tx < 0.45: failed.append("Tx")
        if worst_matrix > 0.50: failed.append("matrix")
        if worst_phase > 25: failed.append("phase")
        score = worst_ratio + 2 * worst_tx - worst_matrix - 0.03 * worst_phase
        ranked.append({"candidate_id": cid, "source_candidate_id": source_candidate(cid), "case_count": str(len(members)), "complete_451_452_453": str(complete).lower(), "worst_ratio": fmt(worst_ratio), "worst_Tx": fmt(worst_tx), "worst_matrix_error": fmt(worst_matrix), "max_phase_error_deg": fmt(worst_phase), "nearest_actual_bins": ";".join(bins), "best_pass_level": level, "near_miss": str(level == "near_miss").lower(), "reassignment_flag": ";".join(sorted(flags)), "failed_gates": ";".join(failed) if failed else "none", "score": fmt(score)})
    ranked.sort(key=lambda r: (r["best_pass_level"] != "strict", r["best_pass_level"] != "loose", r["best_pass_level"] != "near_miss", -flt(r["score"]), r["candidate_id"]))
    return ranked


def write_reports(rows: list[dict[str, str]], counts: dict[str, int]) -> None:
    ranking = rank_candidates(rows)
    write_csv(RANKING_CSV, ranking, RANK_FIELDS)
    strict = [r for r in ranking if r["best_pass_level"] == "strict"]
    loose = [r for r in ranking if r["best_pass_level"] == "loose"]
    near = [r for r in ranking if r["best_pass_level"] == "near_miss"]
    reassigned = [r for r in ranking if "reassigned" in r["reassignment_flag"]]
    best = ranking[0] if ranking else {}
    if strict or loose:
        next_step = "Run coverage 0/120/180 next; true B300 has loose/strict evidence."
    elif reassigned:
        next_step = "Record donor reassignment and continue A9 G2 phase-opposite family."
    else:
        next_step = "Stop H600 true-B300 search and write Stage11-4A13 decision audit; G1/G2/G3 found no useful true B300."
    summary = {"stage": "Stage11-4A12", "group_id": GROUP_ID, **counts, "strict_candidates": len(strict), "loose_candidates": len(loose), "near_miss_candidates": len(near), "reassigned_candidates": len(reassigned), "best_candidate": best, "a8_b60_donor_reference": A8_B60_DONOR, "recommended_next": next_step, "no_coverage_h650_k6": True, "no_coverage": True, "no_h650": True, "no_k6": True}
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    REPORT_MD.write_text("\n".join(["# Stage11-4A12 True B300 Mini-Escape Scout", "", "Scope: only A9 G3, 6 H600 true-B300 mini-escape cases. No G1/G2 rerun, coverage, H650, K=6, H500 rescue.", "", f"planned = {counts['planned']}", f"run = {counts['run']}", f"failed = {counts['failed']}", f"missing = {counts['missing']}", f"strict = {len(strict)}", f"loose = {len(loose)}", f"near_miss = {len(near)}", f"reassigned = {len(reassigned)}", "", "## Best Candidate", "", "```json", json.dumps(best, indent=2), "```", "", "## A8 B60 Donor Reference", "", json.dumps(A8_B60_DONOR, indent=2), "", "## Recommendation", "", next_step, ""]), encoding="utf-8")
    NEXT_MD.write_text("# Stage11-4A12 Recommended Next\n\n" + next_step + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    args = parser.parse_args()
    rows, counts = run_extraction(args.runtime, args.dry_run)
    if not args.dry_run:
        write_reports(rows, counts)
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
