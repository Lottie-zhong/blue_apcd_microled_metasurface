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
RESULT_CSV = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_results.csv"
RANKING_CSV = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_ranking.csv"
SUMMARY_JSON = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_summary.json"
REPORT_MD = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_report.md"
NEXT_MD = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_recommended_next.md"
TEMP_FDTD_DIR = REPORT_DIR / "stage11_4a3_fdtd_tmp"
RAW_TMP_CSV = REPORT_DIR / "stage11_4a3_raw_combined_tmp.csv"
RAW_TMP_MD = REPORT_DIR / "stage11_4a3_raw_summary_tmp.md"
A2_MANIFEST = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_manifest.json"
SOURCE_MANIFEST_3B4 = REPORT_DIR / "stage11_3b4_lp_h500_case_manifest.json"
WAVELENGTHS = [451, 452, 453]
TARGET_BIN = 240
GROUP_ID = "S11_4A2_H600_B240_ROLE_RECOMBINE"
BASELINE = {"worst_ratio": 1.003135, "phase_error_deg": 40.346637, "failure": "ratio/matrix/phase"}
RESULT_FIELDS = [
    "case_id", "group_id", "height_nm", "wavelength_nm", "phase_bin_deg", "candidate_id", "target_Tx",
    "y_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg", "matrix_error",
    "pass_level", "result_csv", "status",
]
RANK_FIELDS = [
    "candidate_id", "case_count", "complete_451_452_453", "worst_ratio", "worst_Tx", "worst_matrix_error",
    "max_phase_error_deg", "best_pass_level", "near_miss", "failed_gates", "score",
]


def load_module(name: str, rel: str):
    path = REPO_ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


rescue = load_module("stage11_3b2_for_4a3", "scripts/stage11_lp_apcd_spectral_rescue_stage11_3b2.py")
a1 = load_module("stage11_4a1_for_4a3", "scripts/stage11_lp_hnew_fixed_height_scout_stage11_4a1.py")


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


def pass_level(ratio: float, tx: float, matrix: float, phase: float) -> str:
    return a1.pass_level(ratio, tx, matrix, phase)


def candidate_id(row: dict[str, str]) -> str:
    return row.get("candidate_id") or row.get("dimer_case_id") or row.get("source_plan_id") or ""


def is_b240(row: dict[str, str]) -> bool:
    cid = candidate_id(row)
    target = rescue.row_target(row)
    return target == TARGET_BIN or "B240" in cid


def select_base_geometries(limit: int = 8) -> list[dict[str, str]]:
    data = json.loads(SOURCE_MANIFEST_3B4.read_text(encoding="utf-8"))
    pool = [dict(r) for r in data.get("cases", []) if is_b240(r)]
    if not pool:
        raise RuntimeError("No B240 source geometries found in tracked Stage11-3B4 manifest")
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    pool.sort(key=lambda r: (0 if "12A" in candidate_id(r) else 1, flt(r.get("gap_nm"), 999.0), candidate_id(r)))
    for row in pool:
        cid = candidate_id(row)
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(row)
        if len(out) >= limit:
            break
    if len(out) != limit:
        raise RuntimeError(f"Expected {limit} B240 geometries, got {len(out)}")
    return out

def run_matrix() -> list[dict[str, str]]:
    manifest = json.loads(A2_MANIFEST.read_text(encoding="utf-8"))
    group = next((g for g in manifest["run_groups"] if g["group_id"] == GROUP_ID), None)
    if not group or int(group["planned_cases"]) != 24:
        raise RuntimeError("A2 B240 group is missing or no longer has 24 planned cases")
    rows: list[dict[str, str]] = []
    for idx, base in enumerate(select_base_geometries(), start=1):
        base_cid = candidate_id(base)
        for wl in WAVELENGTHS:
            row = dict(base)
            cid = f"H600B240REC_{idx:03d}_FROM_{base_cid}"
            case_id = f"S11_4A3_H600_B240_REC{idx:03d}_WL{wl}"
            row.update({
                "case_id": case_id,
                "dimer_case_id": case_id,
                "group_id": GROUP_ID,
                "candidate_id": cid,
                "source_pair_id": base_cid,
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
                "geometry_legal": "true",
                "notes": "Stage11-4A3 H600 B240 role recombination scout; no K6.",
            })
            rows.append(row)
    if len(rows) != 24:
        raise RuntimeError(f"Expected 24 A3 run rows, got {len(rows)}")
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
    level = pass_level(ratio, tx, matrix, perr) if status == "ok" else "fail"
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


def rank_candidates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["candidate_id"], []).append(row)
    ranked: list[dict[str, str]] = []
    for cid, members in groups.items():
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
        levels = [m.get("pass_level", "fail") for m in ok]
        if complete and "strict" in levels and all(m.get("pass_level") in {"strict", "loose"} for m in ok):
            best_level = "strict"
        elif complete and any(l in {"strict", "loose"} for l in levels):
            best_level = "loose"
        else:
            best_level = "fail"
        failed = []
        if not complete: failed.append("missing")
        if worst_ratio < 6: failed.append("ratio")
        if worst_tx < 0.45: failed.append("Tx")
        if worst_matrix > 0.50: failed.append("matrix")
        if worst_phase > 25: failed.append("phase")
        near = complete and worst_ratio >= 2.0 and worst_tx >= 0.10 and worst_matrix <= 1.5 and worst_phase <= 45
        score = worst_ratio + 2.0 * worst_tx - worst_matrix - 0.03 * worst_phase
        ranked.append({
            "candidate_id": cid,
            "case_count": str(len(members)),
            "complete_451_452_453": str(complete).lower(),
            "worst_ratio": fmt(worst_ratio),
            "worst_Tx": fmt(worst_tx),
            "worst_matrix_error": fmt(worst_matrix),
            "max_phase_error_deg": fmt(worst_phase),
            "best_pass_level": best_level,
            "near_miss": str(near).lower(),
            "failed_gates": ";".join(failed) if failed else "none",
            "score": fmt(score),
        })
    ranked.sort(key=lambda r: (r["best_pass_level"] != "strict", r["best_pass_level"] != "loose", r["near_miss"] != "true", -flt(r["score"]), r["candidate_id"]))
    return ranked


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
            b = max(subset, key=lambda r: flt(r["conversion_to_leakage_ratio"], 0.0))
            per_wl.append({"wavelength_nm": wl, "candidate_id": b["candidate_id"], "ratio": b["conversion_to_leakage_ratio"], "phase_error_deg": b["phase_error_deg"]})
    next_step = "Stage11-4A4 run H600 B300 phase pull" if (loose or near) else "redesign B240 search space before B300"
    summary = {
        "stage": "Stage11-4A3",
        "group_id": GROUP_ID,
        "planned": counts["planned"],
        "reused": counts["reused"],
        "run": counts["run"],
        "failed": counts["failed"],
        "missing": max(0, counts["planned"] - len(rows)),
        "ok_rows": len(ok),
        "failed_rows": len(failed),
        "strict_candidates": len(strict),
        "loose_candidates": len(loose),
        "near_miss_candidates": len(near),
        "best_candidate": best,
        "best_by_wavelength": per_wl,
        "baseline_h600_b240": BASELINE,
        "recommended_next": next_step,
        "no_k6": True,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    REPORT_MD.write_text("\n".join([
        "# Stage11-4A3 H600 B240 Role Recombination Scout",
        "",
        "Scope: only H600 B240 role recombination, 24 cases over 451/452/453 nm. No K=6, H650, B300, coverage bins, H500 rescue, DBR/RCLED, dipole, or finite patch.",
        "",
        f"planned = {counts['planned']}",
        f"reused = {counts['reused']}",
        f"run = {counts['run']}",
        f"failed = {counts['failed']}",
        f"strict_candidates = {len(strict)}",
        f"loose_candidates = {len(loose)}",
        f"near_miss_candidates = {len(near)}",
        "",
        "## Best Candidate",
        "",
        json.dumps(best, indent=2),
        "",
        "## Baseline Comparison",
        "",
        "A1 H600 B240 baseline: worst_ratio 1.003135, phase_error 40.346637 deg, failed ratio/matrix/phase.",
        "",
        "## Best By Wavelength",
        "",
        json.dumps(per_wl, indent=2),
        "",
        "## Recommendation",
        "",
        next_step,
        "",
    ]), encoding="utf-8")
    NEXT_MD.write_text("# Stage11-4A3 Recommended Next\n\n" + next_step + "\n", encoding="utf-8")


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
