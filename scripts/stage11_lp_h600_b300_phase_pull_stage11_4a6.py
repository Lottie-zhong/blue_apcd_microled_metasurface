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
RESULT_CSV = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_results.csv"
RANKING_CSV = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_ranking.csv"
SUMMARY_JSON = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_summary.json"
REPORT_MD = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_report.md"
NEXT_MD = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_recommended_next.md"
SOURCE_MANIFEST_3B4 = REPORT_DIR / "stage11_3b4_lp_h500_case_manifest.json"
A2_MANIFEST = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_manifest.json"
A5_SUMMARY_JSON = REPORT_DIR / "stage11_4a5_h600_b240_mechanism_expansion_summary.json"
TEMP_FDTD_DIR = REPORT_DIR / "stage11_4a6_fdtd_tmp"
RAW_TMP_CSV = REPORT_DIR / "stage11_4a6_raw_combined_tmp.csv"
RAW_TMP_MD = REPORT_DIR / "stage11_4a6_raw_summary_tmp.md"
WAVELENGTHS = [451, 452, 453]
TARGET_BIN = 300
GROUP_ID = "S11_4A2_H600_B300_PHASE_PULL"
A1_B300_BASELINE = {
    "worst_ratio": 9.148207,
    "worst_Tx": 0.956956,
    "worst_matrix_error": 0.330634,
    "failure_mode": "phase_only",
}
RESULT_FIELDS = [
    "case_id", "group_id", "height_nm", "wavelength_nm", "phase_bin_deg", "candidate_id",
    "target_Tx", "y_leakage", "conversion_to_leakage_ratio", "selected_phase_deg",
    "phase_error_deg", "matrix_error", "pass_level", "result_csv", "status",
]
RANK_FIELDS = [
    "candidate_id", "source_candidate_id", "case_count", "complete_451_452_453", "worst_ratio",
    "worst_Tx", "worst_matrix_error", "max_phase_error_deg", "best_pass_level", "near_miss",
    "failed_gates", "selectivity_vs_a1_b300", "matrix_delta_vs_a1_b300", "score",
]


def load_module(name: str, rel: str):
    path = REPO_ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


a5 = load_module("stage11_4a5_helpers_for_4a6", "scripts/stage11_lp_h600_b240_mechanism_expansion_stage11_4a5.py")
rescue = a5.rescue
a1 = a5.a1


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


def phase_error(phase: float, target: int = TARGET_BIN) -> float:
    return abs((phase - target + 180.0) % 360.0 - 180.0)


def candidate_id(row: dict[str, str]) -> str:
    return row.get("candidate_id") or row.get("dimer_case_id") or row.get("source_plan_id") or ""


def is_b300_source(row: dict[str, str]) -> bool:
    cid = candidate_id(row)
    return "B300" in cid or str(row.get("target_actual_bin_deg") or row.get("phase_bin_deg") or "") in {"300", "300.0"}


def validate_group() -> None:
    data = json.loads(A2_MANIFEST.read_text(encoding="utf-8"))
    groups = data.get("run_groups") or data.get("included_case_groups") or []
    group = next((g for g in groups if g.get("group_id") == GROUP_ID), None)
    if group is None:
        raise RuntimeError(f"Missing A2 group {GROUP_ID}")
    if int(group.get("planned_cases", 0)) != 18:
        raise RuntimeError(f"A2 B300 group should be 18 cases, got {group.get('planned_cases')}")


def base_geometries() -> list[dict[str, str]]:
    data = json.loads(SOURCE_MANIFEST_3B4.read_text(encoding="utf-8"))
    pool = [dict(r) for r in data.get("cases", []) if is_b300_source(r)]
    priority_ids = [
        "H500DIMER12D_002_B300_x_pair_swap_G80_O-30",
        "H500DIMER12D_004_B300_x_pair_swap_G80_O-40",
        "H500DIMER12D_005_B300_x_pair_swap_G80_O-20",
        "H500DIMER12D_006_B300_x_pair_noswap_G80_O-30",
        "H500DIMER12D_003_B300_x_pair_swap_G90_O-30",
        "H500DIMER12D_007_B300_x_pair_noswap_G100_O-24",
    ]
    by_id = {candidate_id(row): row for row in pool}
    rows = [by_id[cid] for cid in priority_ids if cid in by_id]
    if len(rows) != 6:
        present = sorted(by_id)
        raise RuntimeError(f"Expected 6 tracked B300 sources, got {len(rows)} from {present}")
    return rows


def run_matrix() -> list[dict[str, str]]:
    validate_group()
    rows: list[dict[str, str]] = []
    for idx, base in enumerate(base_geometries(), start=1):
        for wl in WAVELENGTHS:
            row = dict(base)
            base_cid = candidate_id(base)
            cid = f"H600B300PULL_{idx:03d}_FROM_{base_cid}"
            case_id = f"S11_4A6_H600_B300_PULL{idx:03d}_WL{wl}"
            row.update({
                "case_id": case_id,
                "dimer_case_id": case_id,
                "group_id": GROUP_ID,
                "candidate_id": cid,
                "source_pair_id": base_cid,
                "source_candidate_id": base_cid,
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
                "notes": "Stage11-4A6 H600 B300 phase pull only; no coverage, H650, K6, H500 rescue.",
            })
            rows.append(row)
    if len(rows) != 18:
        raise RuntimeError(f"Expected 18 A6 rows, got {len(rows)}")
    return rows


def existing_results() -> dict[str, dict[str, str]]:
    return {r["case_id"]: r for r in read_csv(RESULT_CSV) if r.get("case_id") and r.get("status") in {"ok", "failed"}}


def result_row(row: dict[str, str], combined: dict[str, object], metric: dict[str, object]) -> dict[str, str]:
    phase = flt(metric.get("selected_channel_phase_deg"))
    perr = phase_error(phase) if not math.isnan(phase) else math.nan
    tx = flt(metric.get("Tx"), 0.0)
    leakage = flt(metric.get("blocked_y_total_leakage"), flt(metric.get("y_leakage"), math.nan))
    ratio = flt(metric.get("conversion_to_leakage_ratio"), 0.0)
    matrix = flt(metric.get("matrix_error"), 999.0)
    status = str(combined.get("fdtd_status", metric.get("fdtd_status", "failed")))
    level = a1.pass_level(ratio, tx, matrix, perr) if status == "ok" else "fail"
    return {
        "case_id": row["case_id"],
        "group_id": GROUP_ID,
        "height_nm": "600",
        "wavelength_nm": row["wavelength_nm"],
        "phase_bin_deg": str(TARGET_BIN),
        "candidate_id": row["candidate_id"],
        "target_Tx": fmt(tx),
        "y_leakage": fmt(leakage),
        "conversion_to_leakage_ratio": fmt(ratio),
        "selected_phase_deg": fmt(phase % 360.0 if not math.isnan(phase) else math.nan),
        "phase_error_deg": fmt(perr),
        "matrix_error": fmt(matrix),
        "pass_level": level,
        "result_csv": str(combined.get("x_result_csv", "")) + ";" + str(combined.get("y_result_csv", "")),
        "status": status,
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
    marker = "_FROM_"
    return cid.split(marker, 1)[1] if marker in cid else ""


def candidate_level(worst_ratio: float, worst_tx: float, worst_matrix: float, worst_phase: float, complete: bool) -> str:
    if complete and worst_ratio >= 6.0 and worst_tx >= 0.45 and worst_matrix <= 0.50 and worst_phase <= 25.0:
        return "strict"
    if complete and worst_ratio >= 3.0 and worst_tx >= 0.10 and worst_matrix <= 1.00 and worst_phase <= 35.0:
        return "loose"
    return "fail"


def is_near_miss(worst_ratio: float, worst_tx: float, worst_matrix: float, worst_phase: float, complete: bool, level: str) -> bool:
    if not complete or level != "fail":
        return False
    phase_only = worst_ratio >= 6.0 and worst_tx >= 0.45 and worst_matrix <= 0.50 and worst_phase <= 45.0
    close_gates = sum([worst_ratio >= 3.0, worst_tx >= 0.45, worst_matrix <= 0.80, worst_phase <= 45.0])
    return phase_only or close_gates >= 3


def rank_candidates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["candidate_id"], []).append(row)
    ranked: list[dict[str, str]] = []
    for cid, members in groups.items():
        ok = [m for m in members if m.get("status") == "ok"]
        wls = {int(float(m["wavelength_nm"])) for m in ok}
        complete = all(w in wls for w in WAVELENGTHS)
        ratios = [flt(m["conversion_to_leakage_ratio"], 0.0) for m in ok]
        txs = [flt(m["target_Tx"], 0.0) for m in ok]
        matrices = [flt(m["matrix_error"], 999.0) for m in ok]
        phases = [flt(m["phase_error_deg"], 999.0) for m in ok]
        worst_ratio = min(ratios) if ratios else 0.0
        worst_tx = min(txs) if txs else 0.0
        worst_matrix = max(matrices) if matrices else 999.0
        worst_phase = max(phases) if phases else 999.0
        level = candidate_level(worst_ratio, worst_tx, worst_matrix, worst_phase, complete)
        failed = []
        if not complete: failed.append("missing")
        if worst_ratio < 6.0: failed.append("ratio")
        if worst_tx < 0.45: failed.append("Tx")
        if worst_matrix > 0.50: failed.append("matrix")
        if worst_phase > 25.0: failed.append("phase")
        near = is_near_miss(worst_ratio, worst_tx, worst_matrix, worst_phase, complete, level)
        score = worst_ratio + 2.0 * worst_tx - worst_matrix - 0.03 * worst_phase
        ranked.append({
            "candidate_id": cid,
            "source_candidate_id": source_candidate(cid),
            "case_count": str(len(members)),
            "complete_451_452_453": str(complete).lower(),
            "worst_ratio": fmt(worst_ratio),
            "worst_Tx": fmt(worst_tx),
            "worst_matrix_error": fmt(worst_matrix),
            "max_phase_error_deg": fmt(worst_phase),
            "best_pass_level": level,
            "near_miss": str(near).lower(),
            "failed_gates": ";".join(failed) if failed else "none",
            "selectivity_vs_a1_b300": fmt(worst_ratio / max(A1_B300_BASELINE["worst_ratio"], 1e-12)),
            "matrix_delta_vs_a1_b300": fmt(A1_B300_BASELINE["worst_matrix_error"] - worst_matrix),
            "score": fmt(score),
        })
    ranked.sort(key=lambda r: (r["best_pass_level"] != "strict", r["best_pass_level"] != "loose", r["near_miss"] != "true", -flt(r["score"]), r["candidate_id"]))
    return ranked


def b240_has_loose_evidence() -> bool:
    if not A5_SUMMARY_JSON.exists():
        return False
    data = json.loads(A5_SUMMARY_JSON.read_text(encoding="utf-8"))
    return int(data.get("strict_candidates", 0)) > 0 or int(data.get("loose_candidates", 0)) > 0


def write_reports(rows: list[dict[str, str]], counts: dict[str, int]) -> None:
    ranking = rank_candidates(rows)
    write_csv(RANKING_CSV, ranking, RANK_FIELDS)
    ok = [r for r in rows if r.get("status") == "ok"]
    failed = [r for r in rows if r.get("status") != "ok"]
    strict = [r for r in ranking if r["best_pass_level"] == "strict"]
    loose = [r for r in ranking if r["best_pass_level"] == "loose"]
    near = [r for r in ranking if r["near_miss"] == "true"]
    best = ranking[0] if ranking else {}
    per_wl = []
    for wl in WAVELENGTHS:
        subset = [r for r in rows if r.get("status") == "ok" and int(float(r["wavelength_nm"])) == wl]
        if subset:
            b = max(subset, key=lambda r: flt(r["conversion_to_leakage_ratio"], 0.0) - 0.05 * flt(r["phase_error_deg"], 0.0))
            per_wl.append({"wavelength_nm": wl, "candidate_id": b["candidate_id"], "ratio": b["conversion_to_leakage_ratio"], "phase_error_deg": b["phase_error_deg"], "matrix_error": b["matrix_error"]})
    b240_ready = b240_has_loose_evidence()
    if (strict or loose) and b240_ready:
        next_step = "Run H600 coverage 0/60/120/180 next; B240 has loose evidence and B300 now has loose/strict evidence."
    elif near:
        next_step = "Run focused B300 refinement; B300 is a phase-only near-miss."
    else:
        next_step = "Redesign B300 search; this phase-pull set lost selectivity or did not approach the target phase."
    summary = {
        "stage": "Stage11-4A6",
        "group_id": GROUP_ID,
        **counts,
        "ok_rows": len(ok),
        "failed_rows": len(failed),
        "strict_candidates": len(strict),
        "loose_candidates": len(loose),
        "near_miss_candidates": len(near),
        "best_candidate": best,
        "best_by_wavelength": per_wl,
        "a1_b300_baseline": A1_B300_BASELINE,
        "b240_loose_evidence_from_a5": b240_ready,
        "recommended_next": next_step,
        "no_coverage": True,
        "no_h650": True,
        "no_k6": True,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    REPORT_MD.write_text("\n".join([
        "# Stage11-4A6 H600 B300 Phase Pull",
        "",
        "Scope: only H600 B300 phase pull, 18 cases over 451/452/453 nm. No coverage, H650, K=6, H500 rescue, DBR/RCLED, dipole, or finite patch.",
        "",
        f"planned = {counts['planned']}", f"reused = {counts['reused']}", f"run = {counts['run']}", f"failed = {counts['failed']}", f"missing = {counts['missing']}",
        f"strict_candidates = {len(strict)}", f"loose_candidates = {len(loose)}", f"near_miss_candidates = {len(near)}",
        "",
        "## Best Candidate", "", "```json", json.dumps(best, indent=2), "```",
        "", "## A1 H600 B300 Baseline", "", json.dumps(A1_B300_BASELINE, indent=2),
        "", "## Best By Wavelength", "", "```json", json.dumps(per_wl, indent=2), "```",
        "", "## Recommendation", "", next_step, "",
    ]), encoding="utf-8")
    NEXT_MD.write_text("# Stage11-4A6 Recommended Next\n\n" + next_step + "\n", encoding="utf-8")


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
