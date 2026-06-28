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
REPORT_DIR = REPO_ROOT / "reports"
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

OUT_RESULTS = REPORT_DIR / "stage11_3b4_lp_h500_240_300_expanded_candidates.csv"
OUT_RANKING = REPORT_DIR / "stage11_3b4_lp_h500_240_300_expanded_ranking.csv"
OUT_EVIDENCE = REPORT_DIR / "stage11_3b4_lp_h500_evidence_completion.csv"
OUT_TUPLE = REPORT_DIR / "stage11_3b4_lp_h500_repaired_tuple_after_expansion.csv"
OUT_SUMMARY = REPORT_DIR / "stage11_3b4_lp_h500_240_300_expanded_summary.md"
OUT_MANIFEST = REPORT_DIR / "stage11_3b4_lp_h500_planned_cases.csv"
OUT_MANIFEST_JSON = REPORT_DIR / "stage11_3b4_lp_h500_case_manifest.json"
TEMP_FDTD_DIR = REPORT_DIR / "stage11_3b4_fdtd_tmp"

WAVELENGTHS = [449, 450, 451]
CONTROL_BINS = {
    0: "H500DIMER2C_029_B240_x_pair_noswap_G60_O-20",
    60: "H500DIMER2B_006_B180_x_pair_swap_G60_O-20",
    180: "H500DIMER2C_026_B240_x_pair_swap_G60_O-20",
}
FROZEN_240 = "H500DIMER2F_026_B240_x_pair_swap_G90_O-28"
BEST_240_3B2 = "H500DIMER12A_004_B240_x_pair_swap_G90_O-30"
FROZEN_300 = "H500DIMER2D_006_B240_x_pair_swap_G80_O-30"
FIXED_120 = "H500DIMER2H_003_B120_y_pair_noswap_G22_O-30"
MAX_BY_TARGET = {240: 12, 300: 12}
HARD_CAP = 75

RESULT_FIELDS = [
    "wavelength_nm", "target_bin_deg", "candidate_id", "dimer_case_id", "fdtd_status", "selected_phase_deg",
    "phase_error_to_target_deg", "Tx", "y_leakage", "conversion_to_leakage_ratio", "matrix_error", "pass_flag", "source_stage_or_source_file",
]
RANK_FIELDS = [
    "target_bin_deg", "candidate_id", "wavelengths_available", "complete_449_450_451", "worst_ratio", "worst_Tx", "worst_matrix_error", "max_abs_phase_error_to_target", "candidate_pass_flag", "failed_gates", "rank_score",
]
EVIDENCE_FIELDS = ["phase_bin_deg", "candidate_id", "before_available_wavelengths", "missing_before", "planned_missing_cases", "after_available_wavelengths", "evidence_completed"]
MANIFEST_FIELDS = ["run_reason", "target_bin_deg", "candidate_id", "dimer_case_id", "wavelength_nm", "source_stage_or_source_file"]


def load_module(name: str, rel: str):
    path = REPO_ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rescue = load_module("stage11_3b2_for_3b4", "scripts/stage11_lp_apcd_spectral_rescue_stage11_3b2.py")
tuplemod = load_module("stage11_3b3_for_3b4", "scripts/stage11_lp_apcd_repaired_tuple_search_stage11_3b3.py")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def flt(v: object, default: float = math.nan) -> float:
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def fmt(v: float) -> str:
    return "" if math.isnan(v) else f"{v:.6f}"


def phase_dist(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def cid(row: dict[str, str]) -> str:
    return row.get("candidate_id") or row.get("dimer_case_id") or row.get("source_plan_id") or ""


def target_of(row: dict[str, str]) -> int | None:
    for key in ["target_bin_deg", "target_actual_bin_deg", "phase_bin_deg", "bin_deg", "static_original_bin_deg"]:
        if row.get(key, ""):
            try:
                return int(float(row[key]))
            except ValueError:
                pass
    name = cid(row)
    if "B240" in name:
        return 240
    if "B300" in name:
        return 300
    return None


def metric_key(candidate_id: str, wl: int) -> tuple[str, int]:
    return candidate_id, wl


def normalize_existing_row(row: dict[str, str], source: str) -> dict[str, object] | None:
    candidate = cid(row)
    if not candidate:
        return None
    wl = int(flt(row.get("wavelength_nm"), -1))
    if wl not in WAVELENGTHS:
        return None
    target = int(flt(row.get("target_bin_deg", row.get("bin_deg", row.get("phase_bin_deg", -999))), -999))
    phase = flt(row.get("selected_phase_deg", row.get("selected_channel_phase_deg", row.get("phase_deg"))))
    if math.isnan(phase):
        return None
    return {
        "wavelength_nm": wl,
        "target_bin_deg": target,
        "candidate_id": candidate,
        "dimer_case_id": row.get("dimer_case_id", candidate),
        "fdtd_status": row.get("fdtd_status", "ok"),
        "selected_phase_deg": fmt(phase % 360.0),
        "phase_error_to_target_deg": fmt(phase_dist(phase, target)) if target in [0, 60, 120, 180, 240, 300] else "",
        "Tx": row.get("Tx") or row.get("target_conversion") or row.get("selected_x_power") or "",
        "y_leakage": row.get("blocked_y_total_leakage") or row.get("y_leakage") or row.get("blocked_y_leakage") or "",
        "conversion_to_leakage_ratio": row.get("conversion_to_leakage_ratio") or row.get("projection_selectivity_ratio") or "",
        "matrix_error": row.get("matrix_error") or row.get("matrix_projection_error_norm") or "",
        "pass_flag": row.get("pass_flag", ""),
        "source_stage_or_source_file": source,
    }


def load_existing_metrics() -> dict[tuple[str, int], dict[str, object]]:
    out: dict[tuple[str, int], dict[str, object]] = {}
    for path in [
        REPORT_DIR / "stage11_3b1_lp_h500_frozen_sixbin_449_451_results.csv",
        REPORT_DIR / "stage11_3b2_lp_h500_spectral_rescue_candidates.csv",
    ]:
        for row in read_csv(path):
            norm = normalize_existing_row(row, str(path))
            if not norm:
                continue
            key = metric_key(str(norm["candidate_id"]), int(norm["wavelength_nm"]))
            old = out.get(key)
            if old is None or flt(norm["conversion_to_leakage_ratio"], 0) > flt(old["conversion_to_leakage_ratio"], 0):
                out[key] = norm
    return out


def plan_rows_by_candidate() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for row in rescue.load_plan_rows():
        candidate = cid(row)
        if candidate and candidate not in rows:
            rows[candidate] = dict(row)
    return rows


def candidate_score(row: dict[str, str], target: int) -> float:
    name = cid(row)
    score = 0.0
    if target == 240 and name in {FROZEN_240, BEST_240_3B2}:
        score += 10000.0
    if target == 300 and name == FROZEN_300:
        score += 10000.0
    if target == 240 and "12A" in name:
        score += 500.0
    if target == 240 and "12B" in name:
        score += 250.0
    if target == 300 and "12D" in name:
        score += 500.0
    if f"B{target}" in name:
        score += 80.0
    if row.get("run_selected", "").lower() == "true":
        score += 20.0
    score -= abs(flt(row.get("gap_nm"), 80.0) - (90.0 if target == 240 else 70.0)) * 0.2
    return score


def select_expanded_candidates(rows_by_id: dict[str, dict[str, str]]) -> dict[int, list[dict[str, str]]]:
    selected: dict[int, list[dict[str, str]]] = {}
    for target in [240, 300]:
        pool = [r for r in rows_by_id.values() if target_of(r) == target or (target == 240 and cid(r) in {FROZEN_240, BEST_240_3B2}) or (target == 300 and cid(r) == FROZEN_300)]
        pool.sort(key=lambda r: (-candidate_score(r, target), cid(r)))
        seen = set()
        chosen = []
        for row in pool:
            name = cid(row)
            if name in seen:
                continue
            seen.add(name)
            row = dict(row)
            row["target_bin_deg"] = str(target)
            row["candidate_id"] = name
            chosen.append(row)
            if len(chosen) >= MAX_BY_TARGET[target]:
                break
        selected[target] = chosen
    return selected


def available_wavelengths(existing: dict[tuple[str, int], dict[str, object]], candidate: str) -> list[int]:
    return sorted(w for w in WAVELENGTHS if (candidate, w) in existing)


def build_manifest(existing: dict[tuple[str, int], dict[str, object]], rows_by_id: dict[str, dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    manifest: list[dict[str, str]] = []
    evidence_rows = []
    for slot, candidate in CONTROL_BINS.items():
        before = available_wavelengths(existing, candidate)
        missing = [w for w in WAVELENGTHS if w not in before]
        # 3B1 already supplies 449/451; this should normally be just 450.
        for wl in missing:
            if candidate not in rows_by_id:
                continue
            row = dict(rows_by_id[candidate])
            row.update({"run_reason": "evidence_completion", "target_bin_deg": str(slot), "candidate_id": candidate, "wavelength_nm": str(wl)})
            manifest.append(row)
        evidence_rows.append({
            "phase_bin_deg": slot,
            "candidate_id": candidate,
            "before_available_wavelengths": ";".join(str(w) for w in before),
            "missing_before": ";".join(str(w) for w in missing),
            "planned_missing_cases": len(missing),
            "after_available_wavelengths": "",
            "evidence_completed": "false",
        })
    expanded = select_expanded_candidates(rows_by_id)
    for target, candidates in expanded.items():
        for base in candidates:
            candidate = base["candidate_id"]
            for wl in WAVELENGTHS:
                if (candidate, wl) in existing:
                    continue
                row = dict(base)
                row.update({"run_reason": "expanded_240_300", "target_bin_deg": str(target), "candidate_id": candidate, "wavelength_nm": str(wl)})
                manifest.append(row)
    return manifest, evidence_rows


def concrete_run_row(plan: dict[str, str]) -> dict[str, str]:
    row = dict(plan)
    wl = int(float(row["wavelength_nm"]))
    target = int(float(row["target_bin_deg"]))
    candidate = row["candidate_id"]
    row["dimer_case_id"] = f"{candidate}_3B4_WL{wl}NM"
    row["bin_deg"] = str(target)
    row["phase_bin_deg"] = str(target)
    row["target_actual_bin_deg"] = str(target)
    row["lambda_nm"] = f"{wl:.6f}"
    row["static_output_phase_deg"] = str(target)
    row.setdefault("static_predicted_ratio", "")
    row.setdefault("static_phase_error_deg", "")
    row.setdefault("static_target_x_power", "")
    row.setdefault("static_leak_y_power", "")
    row.setdefault("p_x_nm", "431.907786")
    row.setdefault("p_y_nm", "432.000000")
    row.setdefault("height_nm", "500.000000")
    row.setdefault("geometry_legal", "true")
    row["notes"] = "Stage11-3B4 H500 LP spectral evidence completion / 240-300 expansion; no K6."
    return row


def load_stage11_runner():
    return rescue.load_stage11_runner()


def cleanup_temp_dir() -> None:
    if TEMP_FDTD_DIR.exists():
        shutil.rmtree(TEMP_FDTD_DIR)


def metric_from_combined(combined: dict[str, object], row: dict[str, str]) -> dict[str, object]:
    metric = rescue.spectral_metric_from_combined(combined, {**row, "_result_csv": str(OUT_RESULTS)})
    phase = flt(metric.get("selected_channel_phase_deg"))
    target = int(float(row["target_bin_deg"]))
    ratio = flt(metric.get("conversion_to_leakage_ratio"), 0)
    tx = flt(metric.get("Tx"), 0)
    matrix = flt(metric.get("matrix_error"), 999)
    err = phase_dist(phase, target) if not math.isnan(phase) else math.nan
    return {
        "wavelength_nm": row["wavelength_nm"],
        "target_bin_deg": row["target_bin_deg"],
        "candidate_id": row["candidate_id"],
        "dimer_case_id": row["dimer_case_id"],
        "fdtd_status": metric.get("fdtd_status", ""),
        "selected_phase_deg": fmt(phase % 360.0),
        "phase_error_to_target_deg": fmt(err),
        "Tx": metric.get("Tx", ""),
        "y_leakage": metric.get("blocked_y_total_leakage", ""),
        "conversion_to_leakage_ratio": metric.get("conversion_to_leakage_ratio", ""),
        "matrix_error": metric.get("matrix_error", ""),
        "pass_flag": str(ratio >= 6 and tx >= 0.45 and matrix <= 0.50 and (not math.isnan(err) and err <= 25)).lower(),
        "source_stage_or_source_file": row.get("source_file", ""),
    }


def run_missing_cases(manifest: list[dict[str, str]], runtime_path: str, keep_temp: bool = False) -> list[dict[str, object]]:
    if len(manifest) > HARD_CAP:
        return []
    runner = load_stage11_runner()
    runner.FDTD_DIR = TEMP_FDTD_DIR
    runner.RESULT_CSV = REPORT_DIR / "stage11_3b4_raw_combined_tmp.csv"
    runner.SUMMARY_MD = REPORT_DIR / "stage11_3b4_raw_summary_tmp.md"
    runtime = runner.load_runtime_config(runtime_path)
    lumapi = runner.import_lumapi(runtime)
    rows = []
    try:
        for item in manifest:
            row = concrete_run_row(item)
            print(f"running={row['dimer_case_id']} x")
            x = runner.run_one(lumapi, runtime, row, "x")
            print(f"running={row['dimer_case_id']} y")
            y = runner.run_one(lumapi, runtime, row, "y")
            combined = runner.combine(row, x, y)
            rows.append(metric_from_combined(combined, row))
            write_csv(OUT_RESULTS, rows, RESULT_FIELDS)
            print(f"done={row['dimer_case_id']} status={combined.get('fdtd_status')}")
    finally:
        if not keep_temp:
            cleanup_temp_dir()
        for tmp in [runner.RESULT_CSV, runner.SUMMARY_MD]:
            Path(tmp).unlink(missing_ok=True)
    return rows


def merged_results(existing: dict[tuple[str, int], dict[str, object]], new_rows: list[dict[str, object]], planned_candidates: set[str]) -> list[dict[str, object]]:
    rows = [dict(r) for (candidate, _), r in existing.items() if candidate in planned_candidates or candidate in set(CONTROL_BINS.values()) or candidate == FIXED_120]
    for r in new_rows:
        rows.append(dict(r))
    rows.sort(key=lambda r: (str(r.get("candidate_id")), int(flt(r.get("wavelength_nm"), 0))))
    return rows


def rank_candidates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str], list[dict[str, object]]] = {}
    for r in rows:
        target = int(flt(r.get("target_bin_deg"), -999))
        if target not in [0, 60, 120, 180, 240, 300]:
            continue
        grouped.setdefault((target, str(r.get("candidate_id"))), []).append(r)
    out = []
    for (target, candidate), members in grouped.items():
        by_wl = {int(flt(r.get("wavelength_nm"))): r for r in members}
        wls = sorted(by_wl)
        ratios = [flt(by_wl[w].get("conversion_to_leakage_ratio"), 0) for w in wls]
        txs = [flt(by_wl[w].get("Tx"), 0) for w in wls]
        matrices = [flt(by_wl[w].get("matrix_error"), 999) for w in wls]
        errs = [flt(by_wl[w].get("phase_error_to_target_deg"), 999) for w in wls]
        failed = []
        if not all(w in by_wl for w in WAVELENGTHS): failed.append("missing_wavelength")
        if min(ratios, default=0) < 6: failed.append("ratio")
        if min(txs, default=0) < 0.45: failed.append("Tx")
        if max(matrices, default=999) > 0.50: failed.append("matrix_error")
        if max(errs, default=999) > 25: failed.append("phase")
        score = min(ratios, default=0) + 2 * min(txs, default=0) - max(matrices, default=999) - 0.05 * max(errs, default=999)
        out.append({
            "target_bin_deg": target,
            "candidate_id": candidate,
            "wavelengths_available": ";".join(str(w) for w in wls),
            "complete_449_450_451": str(all(w in by_wl for w in WAVELENGTHS)).lower(),
            "worst_ratio": fmt(min(ratios, default=math.nan)),
            "worst_Tx": fmt(min(txs, default=math.nan)),
            "worst_matrix_error": fmt(max(matrices, default=math.nan)),
            "max_abs_phase_error_to_target": fmt(max(errs, default=math.nan)),
            "candidate_pass_flag": str(not failed).lower(),
            "failed_gates": ";".join(failed),
            "rank_score": fmt(score),
        })
    out.sort(key=lambda r: (int(r["target_bin_deg"]), r["candidate_pass_flag"] != "true", -flt(r["rank_score"], 0)))
    return out


def update_evidence(evidence_rows: list[dict[str, object]], all_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by = {(str(r.get("candidate_id")), int(flt(r.get("wavelength_nm"), -1))) for r in all_rows}
    out = []
    for row in evidence_rows:
        candidate = str(row["candidate_id"])
        after = sorted(w for w in WAVELENGTHS if (candidate, w) in by)
        row = dict(row)
        row["after_available_wavelengths"] = ";".join(str(w) for w in after)
        row["evidence_completed"] = str(all(w in after for w in WAVELENGTHS)).lower()
        out.append(row)
    return out


def to_tuple_metric_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for r in rows:
        out.append({
            "candidate_id": str(r.get("candidate_id")),
            "wavelength_nm": int(flt(r.get("wavelength_nm"), -1)),
            "original_target_bin_deg": int(flt(r.get("target_bin_deg"), -999)),
            "selected_phase_deg": flt(r.get("selected_phase_deg")),
            "Tx": flt(r.get("Tx"), 0),
            "ratio": flt(r.get("conversion_to_leakage_ratio"), 0),
            "matrix_error": flt(r.get("matrix_error"), 999),
        })
    return out


def tuple_after_expansion(all_rows: list[dict[str, object]], ranking: list[dict[str, object]]) -> list[dict[str, object]]:
    cands = tuplemod.aggregate_candidates(to_tuple_metric_rows(all_rows))
    rows = tuplemod.relabel_tuples(cands)
    # Also prepend the explicit repaired tuple requested by the stage prompt.
    by_id = {c["candidate_id"]: c for c in cands}
    def best(target: int) -> str:
        pool = [r for r in ranking if int(r["target_bin_deg"]) == target]
        pool.sort(key=lambda r: (r["candidate_pass_flag"] != "true", -flt(r["rank_score"], 0)))
        return str(pool[0]["candidate_id"]) if pool else ""
    explicit_ids = {
        0: CONTROL_BINS[0], 60: CONTROL_BINS[60], 120: FIXED_120, 180: CONTROL_BINS[180], 240: best(240), 300: best(300),
    }
    if all(v in by_id for v in explicit_ids.values()):
        explicit = tuplemod.tuple_row("explicit_repaired_after_3b4", "fixed_repaired_after_expansion", {s: by_id[c] for s, c in explicit_ids.items()}, 0.0)
        rows = [explicit] + rows
    return rows


def write_summary(manifest: list[dict[str, str]], new_rows: list[dict[str, object]], evidence: list[dict[str, object]], ranking: list[dict[str, object]], tuple_rows: list[dict[str, object]], stopped: bool) -> None:
    best240 = next((r for r in ranking if int(r["target_bin_deg"]) == 240), {})
    best300 = next((r for r in ranking if int(r["target_bin_deg"]) == 300), {})
    best120 = next((r for r in ranking if r["candidate_id"] == FIXED_120), {})
    best_tuple = tuple_rows[0] if tuple_rows else {}
    rec = "freeze repaired tuple and run 448/452 validation" if best_tuple.get("tuple_pass_flag") == "true" else "expand 240/300 search further or consider broader H500/H600/H700/material rescue"
    lines = [
        "# Stage11-3B4 H500 LP 240/300 Expanded Search Summary",
        "",
        "## Boundary",
        "- H500 LP single-dimer spectral rescue over 449/450/451 nm only.",
        "- No K=6/metagrating, finite patch, dipole, DBR, RCLED, H600/H700, or Stage10 CP modification.",
        "",
        "## Completion",
        f"- planned_cases = {len(manifest)}",
        f"- run_cases = {len(new_rows)}",
        f"- succeeded = {sum(1 for r in new_rows if r.get('fdtd_status') == 'ok')}",
        f"- failed = {sum(1 for r in new_rows if r.get('fdtd_status') != 'ok')}",
        f"- stopped_before_fdtd_due_to_cap = {stopped}",
        "",
        "## Answers",
        f"1. 0/60/180 report-level evidence completed: `{all(str(r['evidence_completed']) == 'true' for r in evidence)}`.",
        f"2. 120 rescue kept fixed and valid: `{best120.get('candidate_pass_flag', '')}` for `{FIXED_120}`.",
        f"3. Best 240 replacement: `{best240.get('candidate_id', '')}`, failed_gates `{best240.get('failed_gates', '')}`, worst_ratio `{best240.get('worst_ratio', '')}`.",
        f"4. Best 300 replacement: `{best300.get('candidate_id', '')}`, failed_gates `{best300.get('failed_gates', '')}`, worst_ratio `{best300.get('worst_ratio', '')}`.",
        f"5. Repaired six-bin tuple passes after expansion: `{best_tuple.get('tuple_pass_flag', '')}`.",
        f"6. Tuple failed gates: `{best_tuple.get('failed_gates', '')}`.",
        f"7. Recommended Stage11-3B5: {rec}.",
        "",
        "## Best Tuple",
        f"- tuple_id: `{best_tuple.get('tuple_id', '')}`",
        f"- min_worst_ratio: `{best_tuple.get('min_worst_ratio', '')}`",
        f"- min_worst_Tx: `{best_tuple.get('min_worst_Tx', '')}`",
        f"- max_worst_matrix_error: `{best_tuple.get('max_worst_matrix_error', '')}`",
        f"- max_relative_phase_error_deg: `{best_tuple.get('max_relative_phase_error_deg', '')}`",
    ]
    OUT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(runtime_path: str = "configs/runtime.yaml", keep_temp: bool = False) -> dict[str, object]:
    existing = load_existing_metrics()
    rows_by_id = plan_rows_by_candidate()
    manifest, evidence = build_manifest(existing, rows_by_id)
    write_csv(OUT_MANIFEST, [{"run_reason": r.get("run_reason", ""), "target_bin_deg": r.get("target_bin_deg", ""), "candidate_id": r.get("candidate_id", ""), "dimer_case_id": f"{r.get('candidate_id', '')}_3B4_WL{r.get('wavelength_nm', '')}NM", "wavelength_nm": r.get("wavelength_nm", ""), "source_stage_or_source_file": r.get("source_file", "")} for r in manifest], MANIFEST_FIELDS)
    OUT_MANIFEST_JSON.write_text(json.dumps({"planned_cases": len(manifest), "hard_cap": HARD_CAP, "cases": manifest}, indent=2), encoding="utf-8")
    stopped = len(manifest) > HARD_CAP
    new_rows: list[dict[str, object]] = [] if stopped else run_missing_cases(manifest, runtime_path, keep_temp)
    planned_candidates = {r["candidate_id"] for r in manifest}
    all_rows = merged_results(existing, new_rows, planned_candidates)
    ranking = rank_candidates(all_rows)
    evidence = update_evidence(evidence, all_rows)
    tuple_rows = tuple_after_expansion(all_rows, ranking)
    write_csv(OUT_RESULTS, all_rows, RESULT_FIELDS)
    write_csv(OUT_RANKING, ranking, RANK_FIELDS)
    write_csv(OUT_EVIDENCE, evidence, EVIDENCE_FIELDS)
    write_csv(OUT_TUPLE, tuple_rows, tuplemod.TUPLE_FIELDS)
    write_summary(manifest, new_rows, evidence, ranking, tuple_rows, stopped)
    return {"planned_cases": len(manifest), "run_cases": len(new_rows), "success": sum(1 for r in new_rows if r.get("fdtd_status") == "ok"), "failed": sum(1 for r in new_rows if r.get("fdtd_status") != "ok"), "stopped": stopped, "best_tuple_pass": tuple_rows[0].get("tuple_pass_flag", "") if tuple_rows else ""}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()
    summary = run(args.runtime, args.keep_temp)
    for k, v in summary.items():
        print(f"{k}={v}")
    print(f"results_csv={OUT_RESULTS}")
    print(f"ranking_csv={OUT_RANKING}")
    print(f"summary_md={OUT_SUMMARY}")
    print("boundary=h500_lp_single_dimer_449_450_451_only_no_k6_no_stage10_cp_no_finite_patch_no_dipole_no_dbr_no_rcled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
