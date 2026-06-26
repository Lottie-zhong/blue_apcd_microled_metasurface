from __future__ import annotations

import csv
import itertools
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports"
SRC_FILES = [
    REPORT_DIR / "stage11_3b1_lp_h500_frozen_sixbin_449_451_results.csv",
    REPORT_DIR / "stage11_3b2_lp_h500_spectral_rescue_candidates.csv",
]
WAVELENGTHS = [449, 450, 451]
SLOTS = [0, 60, 120, 180, 240, 300]
OUT_CAND = REPORT_DIR / "stage11_3b3_lp_h500_repaired_tuple_candidates.csv"
OUT_TUPLES = REPORT_DIR / "stage11_3b3_lp_h500_repaired_tuple_ranking.csv"
OUT_MD = REPORT_DIR / "stage11_3b3_lp_h500_repaired_tuple_summary.md"
OUT_RELABEL = REPORT_DIR / "stage11_3b3_lp_h500_relabeling_diagnostics.csv"

FROZEN = {
    0: "H500DIMER2C_029_B240_x_pair_noswap_G60_O-20",
    60: "H500DIMER2B_006_B180_x_pair_swap_G60_O-20",
    120: "H500DIMER2C_004_B120_x_pair_swap_G60_O-20",
    180: "H500DIMER2C_026_B240_x_pair_swap_G60_O-20",
    240: "H500DIMER2F_026_B240_x_pair_swap_G90_O-28",
    300: "H500DIMER2D_006_B240_x_pair_swap_G80_O-30",
}

CAND_FIELDS = [
    "candidate_id", "original_target_bin_deg", "wavelengths_available", "selected_phase_449_deg", "selected_phase_450_deg", "selected_phase_451_deg",
    "mean_selected_phase_deg", "phase_span_deg", "worst_ratio", "worst_Tx", "worst_matrix_error",
    "max_abs_phase_error_to_original_target_deg", "candidate_pass_flag", "failed_gates",
]
TUPLE_FIELDS = [
    "tuple_id", "mode", "offset_deg", "slot_0_candidate_id", "slot_60_candidate_id", "slot_120_candidate_id", "slot_180_candidate_id", "slot_240_candidate_id", "slot_300_candidate_id",
    "min_worst_ratio", "min_worst_Tx", "max_worst_matrix_error", "max_candidate_phase_span_deg", "max_relative_phase_error_deg", "rms_relative_phase_error_deg", "worst_wavelength_nm", "tuple_pass_flag", "failed_gates", "recommendation",
]


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


def wrap360(v: float) -> float:
    return v % 360.0


def phase_diff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def phase_dist(a: float, b: float) -> float:
    return abs(phase_diff(a, b))


def circular_mean(phases: list[float]) -> float:
    if not phases:
        return math.nan
    x = sum(math.cos(math.radians(p)) for p in phases)
    y = sum(math.sin(math.radians(p)) for p in phases)
    return wrap360(math.degrees(math.atan2(y, x)))


def phase_span(phases: list[float]) -> float:
    if len(phases) < 2:
        return 0.0 if phases else math.nan
    return max(phase_dist(a, b) for a, b in itertools.combinations(phases, 2))


def row_value(row: dict[str, str], *names: str, default: str = "") -> str:
    for name in names:
        if row.get(name, "") != "":
            return row[name]
    return default


def load_metric_rows() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for path in SRC_FILES:
        for row in read_csv(path):
            cid = row_value(row, "candidate_id", "dimer_case_id")
            if not cid:
                continue
            wl = int(flt(row_value(row, "wavelength_nm"), -1))
            phase = wrap360(flt(row_value(row, "selected_channel_phase_deg", "selected_phase_deg", "phase_deg")))
            target = int(flt(row_value(row, "target_bin_deg", "bin_deg", "phase_bin_deg"), -999))
            out.append({
                "candidate_id": cid,
                "wavelength_nm": wl,
                "original_target_bin_deg": target,
                "selected_phase_deg": phase,
                "Tx": flt(row_value(row, "Tx", "target_conversion", "selected_x_power"), 0.0),
                "ratio": flt(row_value(row, "conversion_to_leakage_ratio", "projection_selectivity_ratio"), 0.0),
                "matrix_error": flt(row_value(row, "matrix_error", "matrix_projection_error_norm"), 999.0),
                "source_file": str(path),
            })
    return out


def aggregate_candidates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by: dict[str, list[dict[str, object]]] = {}
    for r in rows:
        by.setdefault(str(r["candidate_id"]), []).append(r)
    out = []
    for cid, members in by.items():
        by_wl: dict[int, dict[str, object]] = {}
        for r in members:
            wl = int(r["wavelength_nm"])
            old = by_wl.get(wl)
            if old is None or flt(r["ratio"], 0) > flt(old["ratio"], 0):
                by_wl[wl] = r
        wls = sorted(by_wl)
        phases = [flt(by_wl[w]["selected_phase_deg"]) for w in wls]
        target_vals = [int(m["original_target_bin_deg"]) for m in members if int(m["original_target_bin_deg"]) in SLOTS]
        original = target_vals[0] if target_vals else ""
        ratios = [flt(by_wl[w]["ratio"], 0) for w in wls]
        txs = [flt(by_wl[w]["Tx"], 0) for w in wls]
        matrices = [flt(by_wl[w]["matrix_error"], 999) for w in wls]
        complete = all(w in by_wl for w in WAVELENGTHS)
        failed = []
        if not complete: failed.append("missing_449_450_451")
        if ratios and min(ratios) < 6: failed.append("ratio")
        if txs and min(txs) < 0.45: failed.append("Tx")
        if matrices and max(matrices) > 0.50: failed.append("matrix_error")
        orig_err = max((phase_dist(flt(by_wl[w]["selected_phase_deg"]), float(original)) for w in wls), default=math.nan) if original != "" else math.nan
        row = {
            "candidate_id": cid,
            "original_target_bin_deg": original,
            "wavelengths_available": ";".join(str(w) for w in wls),
            "selected_phase_449_deg": fmt(flt(by_wl[449]["selected_phase_deg"])) if 449 in by_wl else "",
            "selected_phase_450_deg": fmt(flt(by_wl[450]["selected_phase_deg"])) if 450 in by_wl else "",
            "selected_phase_451_deg": fmt(flt(by_wl[451]["selected_phase_deg"])) if 451 in by_wl else "",
            "mean_selected_phase_deg": fmt(circular_mean(phases)),
            "phase_span_deg": fmt(phase_span(phases)),
            "worst_ratio": fmt(min(ratios) if ratios else math.nan),
            "worst_Tx": fmt(min(txs) if txs else math.nan),
            "worst_matrix_error": fmt(max(matrices) if matrices else math.nan),
            "max_abs_phase_error_to_original_target_deg": fmt(orig_err),
            "candidate_pass_flag": str(not failed).lower(),
            "failed_gates": ";".join(failed),
            "_by_wl": by_wl,
        }
        out.append(row)
    out.sort(key=lambda r: (r["candidate_pass_flag"] != "true", -flt(r["worst_ratio"], 0), flt(r["phase_span_deg"], 999)))
    return out


def candidate_score(c: dict[str, object]) -> float:
    return flt(c.get("worst_ratio"), 0) + 2 * flt(c.get("worst_Tx"), 0) - flt(c.get("worst_matrix_error"), 999) - 0.05 * flt(c.get("phase_span_deg"), 999)


def relative_errors(slot_map: dict[int, dict[str, object]], offset: float) -> tuple[float, float, str]:
    errs = []
    worst_wl = ""
    for wl in WAVELENGTHS:
        wl_errs = []
        for slot, cand in slot_map.items():
            by_wl = cand.get("_by_wl", {})
            if wl not in by_wl:
                return 999.0, 999.0, str(wl)
            target = wrap360(offset + slot)
            wl_errs.append(phase_dist(flt(by_wl[wl]["selected_phase_deg"]), target))
        if wl_errs and max(wl_errs) > (max(errs) if errs else -1):
            worst_wl = str(wl)
        errs.extend(wl_errs)
    rms = math.sqrt(sum(e * e for e in errs) / len(errs)) if errs else 999.0
    return (max(errs) if errs else 999.0), rms, worst_wl


def tuple_row(tuple_id: str, mode: str, slot_map: dict[int, dict[str, object]], offset: float) -> dict[str, object]:
    ids = [slot_map.get(s, {}).get("candidate_id", "") for s in SLOTS]
    failed = []
    if len(set(ids)) != 6: failed.append("duplicate_candidate")
    if any(not x for x in ids): failed.append("missing_slot")
    min_ratio = min((flt(c.get("worst_ratio"), 0) for c in slot_map.values()), default=0.0)
    min_tx = min((flt(c.get("worst_Tx"), 0) for c in slot_map.values()), default=0.0)
    max_matrix = max((flt(c.get("worst_matrix_error"), 999) for c in slot_map.values()), default=999.0)
    max_span = max((flt(c.get("phase_span_deg"), 999) for c in slot_map.values()), default=999.0)
    max_err, rms, worst_wl = relative_errors(slot_map, offset)
    if min_ratio < 6: failed.append("ratio")
    if min_tx < 0.45: failed.append("Tx")
    if max_matrix > 0.50: failed.append("matrix_error")
    if max_err > 25: failed.append("relative_phase")
    if rms > 15: failed.append("rms_phase")
    if any(c.get("candidate_pass_flag") != "true" for c in slot_map.values()): failed.append("candidate_gate")
    recommendation = "freeze_repaired_tuple_and_run_448_452" if not failed else "expand_240_300_or_global_search"
    row = {
        "tuple_id": tuple_id,
        "mode": mode,
        "offset_deg": fmt(offset),
        "min_worst_ratio": fmt(min_ratio),
        "min_worst_Tx": fmt(min_tx),
        "max_worst_matrix_error": fmt(max_matrix),
        "max_candidate_phase_span_deg": fmt(max_span),
        "max_relative_phase_error_deg": fmt(max_err),
        "rms_relative_phase_error_deg": fmt(rms),
        "worst_wavelength_nm": worst_wl,
        "tuple_pass_flag": str(not failed).lower(),
        "failed_gates": ";".join(dict.fromkeys(failed)),
        "recommendation": recommendation,
    }
    for s in SLOTS:
        row[f"slot_{s}_candidate_id"] = slot_map.get(s, {}).get("candidate_id", "")
    return row


def fixed_tuple(cands: list[dict[str, object]]) -> dict[str, object]:
    slot_map = {}
    for slot in SLOTS:
        pool = [c for c in cands if str(c.get("original_target_bin_deg")) == str(slot)]
        pool.sort(key=candidate_score, reverse=True)
        if pool:
            slot_map[slot] = pool[0]
    return tuple_row("fixed_labels", "fixed_labels", slot_map, 0.0)


def relabel_tuples(cands: list[dict[str, object]]) -> list[dict[str, object]]:
    out = [fixed_tuple(cands)]
    usable = [c for c in cands if all(w in c.get("_by_wl", {}) for w in WAVELENGTHS)]
    offsets = sorted({round(wrap360(flt(c.get("mean_selected_phase_deg")) - s)) for c in usable for s in SLOTS})
    offsets += list(range(0, 360, 15))
    seen_offsets = []
    for off in offsets:
        if off in seen_offsets:
            continue
        seen_offsets.append(off)
        slot_map = {}
        used = set()
        for slot in SLOTS:
            target = wrap360(off + slot)
            pool = [c for c in usable if c["candidate_id"] not in used]
            pool.sort(key=lambda c: (phase_dist(flt(c.get("mean_selected_phase_deg")), target), -candidate_score(c)))
            if pool:
                slot_map[slot] = pool[0]; used.add(pool[0]["candidate_id"])
        out.append(tuple_row(f"offset_{int(off):03d}", "global_offset_relabel", slot_map, float(off)))
    out.sort(key=lambda r: (r["tuple_pass_flag"] != "true", flt(r["max_relative_phase_error_deg"], 999), flt(r["rms_relative_phase_error_deg"], 999), -flt(r["min_worst_ratio"], 0)))
    return out[:60]


def relabel_diagnostics(cands: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for c in cands:
        mean = flt(c.get("mean_selected_phase_deg"))
        slot = min(SLOTS, key=lambda s: phase_dist(mean, s)) if not math.isnan(mean) else ""
        rows.append({"candidate_id": c["candidate_id"], "original_target_bin_deg": c["original_target_bin_deg"], "mean_selected_phase_deg": c["mean_selected_phase_deg"], "nearest_nominal_slot_deg": slot, "distance_to_nearest_nominal_slot_deg": fmt(phase_dist(mean, float(slot))) if slot != "" else "", "candidate_pass_flag": c["candidate_pass_flag"], "failed_gates": c["failed_gates"]})
    return rows


def write_summary(cands: list[dict[str, object]], tuples: list[dict[str, object]]) -> None:
    best = tuples[0] if tuples else {}
    fixed = next((r for r in tuples if r["mode"] == "fixed_labels"), {})
    has_120_rescue = any("H500DIMER2H_003" in str(r.values()) for r in tuples[:10])
    frozen_ok = {s: any(c["candidate_id"] == FROZEN[s] and c["candidate_pass_flag"] == "true" for c in cands) for s in [0, 60, 180]}
    complete_pass = best.get("tuple_pass_flag") == "true"
    limiting = sorted({g for r in tuples[:10] for g in str(r.get("failed_gates", "")).split(";") if g})
    next_step = "freeze repaired tuple and run 448/452 validation" if complete_pass else "expand 240/300 candidate search; current report-only pool cannot prove a robust six-bin tuple"
    lines = [
        "# Stage11-3B3 H500 LP Repaired Tuple Search",
        "",
        "## Boundary",
        "- Analysis only. No FDTD, no Lumerical, no K=6/metagrating, no finite patch, no dipole, no DBR/RCLED.",
        "- Data sources restricted to Stage11-3B1 and Stage11-3B2 CSV reports under reports/; outputs/ was not read.",
        "",
        "## Answers",
        f"1. Repaired six-bin tuple using the 120 deg rescue: `{complete_pass}`. Best tuple `{best.get('tuple_id','')}` uses 120 rescue in top candidates: `{has_120_rescue}`.",
        f"2. Can 0/60/180 frozen bins remain from this report-only evidence? `{all(frozen_ok.values())}`. Per-bin pass evidence: `{frozen_ok}`.",
        f"3. Limiting bins/gates after relabeling: `{';'.join(limiting)}`. 240/300 remain suspect because 3B2 showed low long-wavelength ratio/matrix margins.",
        f"4. Does global phase offset solve the issue? `{complete_pass}`. Best max relative phase error `{best.get('max_relative_phase_error_deg','')}`, RMS `{best.get('rms_relative_phase_error_deg','')}`.",
        f"5. Recommended Stage11-3B4: {next_step}.",
        "",
        "## Best Tuple",
        "| mode | offset | min_ratio | min_Tx | max_matrix | max_rel_phase_err | rms_rel_phase_err | pass | failed_gates |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
        f"| {best.get('mode','')} | {best.get('offset_deg','')} | {best.get('min_worst_ratio','')} | {best.get('min_worst_Tx','')} | {best.get('max_worst_matrix_error','')} | {best.get('max_relative_phase_error_deg','')} | {best.get('rms_relative_phase_error_deg','')} | {best.get('tuple_pass_flag','')} | {best.get('failed_gates','')} |",
        "",
        "## Fixed-label Tuple",
        f"- tuple_pass_flag: `{fixed.get('tuple_pass_flag','')}`; failed_gates: `{fixed.get('failed_gates','')}`.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    metrics = load_metric_rows()
    cands = aggregate_candidates(metrics)
    tuples = relabel_tuples(cands)
    write_csv(OUT_CAND, [{k: v for k, v in c.items() if not k.startswith("_")} for c in cands], CAND_FIELDS)
    write_csv(OUT_TUPLES, tuples, TUPLE_FIELDS)
    write_csv(OUT_RELABEL, relabel_diagnostics(cands), ["candidate_id", "original_target_bin_deg", "mean_selected_phase_deg", "nearest_nominal_slot_deg", "distance_to_nearest_nominal_slot_deg", "candidate_pass_flag", "failed_gates"])
    write_summary(cands, tuples)
    print(f"candidate_count={len(cands)}")
    print(f"tuple_count={len(tuples)}")
    print(f"best_tuple_pass={tuples[0]['tuple_pass_flag'] if tuples else ''}")
    print(f"best_tuple_failed_gates={tuples[0]['failed_gates'] if tuples else ''}")
    print(f"candidate_csv={OUT_CAND}")
    print(f"tuple_csv={OUT_TUPLES}")
    print(f"summary_md={OUT_MD}")
    print("boundary=analysis_only_reports_csv_no_outputs_no_fdtd_no_k6_no_stage10_cp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
