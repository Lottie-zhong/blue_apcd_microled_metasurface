from __future__ import annotations

import csv, math, statistics
from dataclasses import dataclass
from pathlib import Path

OUTPUT_DIR_NAME = "stage12_11a_h500_lp_k6_phase_origin_search"
TARGET_STEP_DEG = 60
DELTAS = list(range(60))
PREFERRED_TOL_DEG = 10.0
RELAXED_TOL_DEG = 15.0
EPS = 1e-12
OFFICIAL_IDS = {
    0: "H500DIMER2C_029_B240_x_pair_noswap_G60_O-20",
    60: "H500DIMER2B_006_B180_x_pair_swap_G60_O-20",
    120: "H500DIMER2D_040_B300_y_pair_noswap_G20_O-40",
    180: "H500DIMER2C_026_B240_x_pair_swap_G60_O-20",
    240: "H500DIMER2F_026_B240_x_pair_swap_G90_O-28",
    300: "H500DIMER2D_006_B240_x_pair_swap_G80_O-30",
}
POOL_FIELDS = ["candidate_id","source_stage","geometry_family","phase_deg","phase_mod_360_deg","nearest_60bin_deg","Tx","leakage","ratio","matrix_error","phase_error_to_selected_target","geometry_legal","minimum_clearance_nm","strict","result_csv","source_file"]
SCAN_FIELDS = ["delta_deg","target_phases","all_six_targets_filled","tolerance_mode","filled_count","min_ratio","median_ratio","harmonic_mean_ratio","min_Tx","max_matrix_error","rms_phase_error","max_estimated_leakage","family_count","tuple_score","candidate_ids"]
TOP_FIELDS = ["rank"] + SCAN_FIELDS
LIB_FIELDS = ["slot_index","target_phase_deg","candidate_id","geometry_family","phase_deg","phase_mod_360_deg","phase_error_deg","Tx","leakage","ratio","matrix_error","estimated_leakage","minimum_clearance_nm","tolerance_mode","source_file"]
COMPARE_FIELDS = ["tuple_name","delta_deg","candidate_ids","target_phases","min_ratio","median_ratio","harmonic_mean_ratio","max_estimated_leakage","min_Tx","max_matrix_error","rms_phase_error","tuple_score","improvement_min_ratio_pct","improvement_max_leakage_pct","recommend_k6_fdtd"]
COVERAGE_FIELDS = ["target_phase_deg","preferred_count","relaxed_count","best_preferred_candidate_id","best_preferred_ratio","best_relaxed_candidate_id","best_relaxed_ratio"]

@dataclass(frozen=True)
class Stage12_11APaths:
    output_dir: Path


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "": return default
        return float(value)
    except Exception:
        return default


def bool_from(value: object, default: bool = True) -> bool:
    text = str(value).strip().lower()
    if text == "": return default
    return text in {"true", "1", "yes", "ok"}


def wrap360(value: float) -> float:
    return value % 360.0


def phase_distance_deg(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def delta_target_phases(delta: int) -> list[float]:
    return [float((delta + TARGET_STEP_DEG * i) % 360) for i in range(6)]


def nearest_60bin(phase_deg: float) -> int:
    phase = wrap360(phase_deg)
    return min([0,60,120,180,240,300], key=lambda b: phase_distance_deg(phase, b))


def harmonic_mean(values: list[float]) -> float:
    clean = [v for v in values if v > EPS and not math.isnan(v)]
    if not clean: return 0.0
    return len(clean) / sum(1.0 / v for v in clean)


def infer_stage(path: Path) -> str:
    parent = path.parent.name
    if "stage12_10a" in parent: return "Stage12-10A"
    if "stage12_10b" in parent: return "Stage12-10B"
    if "stage12_10c" in parent: return "Stage12-10C"
    if "stage12_10d" in parent: return "Stage12-10D"
    if "stage11_2i" in parent: return "Stage11-2I"
    if "stage11_2h" in parent: return "Stage11-2H"
    if "stage11_2g" in parent: return "Stage11-2G"
    if "2f" in parent: return "Stage11-2F"
    if "2e" in parent: return "Stage11-2E"
    if "2d" in parent: return "Stage11-2D"
    if "2c" in parent: return "Stage11-2C"
    if "2b" in parent: return "Stage11-2B"
    if "2a" in parent: return "Stage11-2A"
    return parent


def parse_family(row: dict) -> str:
    family = str(row.get("geometry_family") or "").strip()
    if family: return family
    cid = str(row.get("candidate_id") or row.get("dimer_case_id") or "")
    placement = str(row.get("placement_type") or "")
    swap = str(row.get("swap_order") or "")
    if "diag_pair" in cid or placement == "diag_pair": placement = "diag_pair"
    elif "y_pair" in cid or placement == "y_pair": placement = "y_pair"
    elif "x_pair" in cid or placement == "x_pair": placement = "x_pair"
    else: placement = "unknown_pair"
    if "noswap" in cid or swap == "J1-J2": state = "noswap"
    elif "swap" in cid or swap == "J2-J1": state = "swap"
    else: state = "unknown"
    return f"{placement}_{state}"


def normalize_candidate(raw: dict[str,str], source_file: Path) -> dict | None:
    cid = raw.get("candidate_id") or raw.get("dimer_case_id") or raw.get("best_case_id")
    if not cid or "H500" not in cid: return None
    phase = flt(raw.get("actual_common_phase_deg"), flt(raw.get("dimer_output_phase_deg"), flt(raw.get("phase_deg"))))
    if math.isnan(phase): return None
    tx = flt(raw.get("selected_x_power"), flt(raw.get("selected_power"), flt(raw.get("target_x_power"), flt(raw.get("Tx")))))
    leakage = flt(raw.get("blocked_y_leakage"), flt(raw.get("blocked_input_total_power"), flt(raw.get("y_input_total_leak_power"), flt(raw.get("opposite_spin_or_yLP_leakage")))))
    ratio = flt(raw.get("conversion_to_leakage_ratio"), flt(raw.get("projection_selectivity_ratio"), flt(raw.get("dimer_selectivity_ratio"), flt(raw.get("ratio")))))
    matrix = flt(raw.get("matrix_error"), flt(raw.get("matrix_projection_error_norm")))
    clearance = flt(raw.get("minimum_clearance_nm"), flt(raw.get("dimer_gap_nm")))
    legal = bool_from(raw.get("geometry_legal", "true"), True)
    strict = bool_from(raw.get("strict") or raw.get("dimer_pass_strict") or ("true" if "strict" in raw.get("usable_status", "") else ""), False)
    if not legal or math.isnan(tx) or math.isnan(ratio) or tx < 0.50 or ratio < 5.0: return None
    if not math.isnan(clearance) and clearance < 15.0: return None
    phase_mod = wrap360(phase)
    nearest = nearest_60bin(phase_mod)
    leakage_est = leakage if not math.isnan(leakage) and leakage >= 0 else tx / max(ratio, EPS)
    return {
        "candidate_id": cid, "source_stage": raw.get("source_stage") or infer_stage(source_file),
        "geometry_family": parse_family({**raw, "candidate_id": cid}), "phase_deg": phase,
        "phase_mod_360_deg": phase_mod, "nearest_60bin_deg": nearest, "Tx": tx,
        "leakage": leakage_est, "ratio": ratio, "matrix_error": matrix,
        "phase_error_to_selected_target": phase_distance_deg(phase_mod, nearest),
        "geometry_legal": legal, "minimum_clearance_nm": clearance, "strict": strict,
        "result_csv": str(source_file), "source_file": str(source_file),
    }


def candidate_quality(row: dict) -> float:
    matrix = flt(row.get("matrix_error"), 1.0)
    clearance = flt(row.get("minimum_clearance_nm"), 999.0)
    clearance_penalty = 10.0 if clearance < 20.0 else 0.0
    return 3*flt(row.get("ratio"),0) + 2*flt(row.get("Tx"),0) - 5*matrix - 4*flt(row.get("phase_error_to_selected_target"),0) - clearance_penalty


def aggregate_candidate_pool(repo_root: Path) -> list[dict]:
    patterns = [
        "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/*.csv",
        "outputs/blue10k6_lp_apcd_stage11_2*_h500*/*fdtd_results*.csv",
        "outputs/stage11_2*_h500*/*fdtd_results*.csv",
        "outputs/stage12_10a_h500_lp_240bin_single_dimer_refinement/*.csv",
        "outputs/stage12_10b_h500_lp_240bin_broad_family_scout/*.csv",
        "outputs/stage12_10c_h500_lp_180bin_single_dimer_refinement/*.csv",
        "outputs/stage12_10d_h500_lp_300bin_single_dimer_refinement/*.csv",
    ]
    seen: dict[str, dict] = {}
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            for raw in read_csv(path):
                row = normalize_candidate(raw, path)
                if row is None: continue
                cid = row["candidate_id"]
                if cid not in seen or candidate_quality(row) > candidate_quality(seen[cid]):
                    seen[cid] = row
    return sorted(seen.values(), key=lambda r: (-flt(r.get("ratio"),0), -flt(r.get("Tx"),0), flt(r.get("matrix_error"),999)))


def candidate_for_target(pool: list[dict], target: float, tolerance: float, used: set[str]) -> dict | None:
    options = []
    for row in pool:
        if row["candidate_id"] in used: continue
        err = phase_distance_deg(flt(row["phase_mod_360_deg"]), target)
        if err <= tolerance:
            opt = dict(row); opt["target_phase_deg"] = target; opt["phase_error_deg"] = err; opt["estimated_leakage"] = flt(row["leakage"])
            options.append(opt)
    if not options: return None
    return sorted(options, key=lambda r: (-flt(r["ratio"]), flt(r["estimated_leakage"]), -flt(r["Tx"]), flt(r.get("matrix_error"),999), flt(r["phase_error_deg"])))[0]


def construct_tuple(pool: list[dict], delta: int) -> tuple[list[dict], str]:
    targets = delta_target_phases(delta)
    used: set[str] = set(); chosen: list[dict] = []; mode = "preferred"
    for target in targets:
        row = candidate_for_target(pool, target, PREFERRED_TOL_DEG, used)
        if row is None:
            mode = "relaxed"
            row = candidate_for_target(pool, target, RELAXED_TOL_DEG, used)
        if row is None:
            return chosen, "missing"
        row["tolerance_mode"] = mode if phase_distance_deg(flt(row["phase_mod_360_deg"]), target) > PREFERRED_TOL_DEG else "preferred"
        used.add(row["candidate_id"]); chosen.append(row)
    if any(r["tolerance_mode"] == "relaxed" for r in chosen): mode = "relaxed"
    return chosen, mode


def score_tuple(chosen: list[dict], delta: int, mode: str) -> dict:
    ratios = [flt(r["ratio"]) for r in chosen]
    txs = [flt(r["Tx"]) for r in chosen]
    matrices = [flt(r.get("matrix_error"), 999) for r in chosen]
    phase_errs = [flt(r["phase_error_deg"]) for r in chosen]
    leaks = [flt(r["estimated_leakage"]) for r in chosen]
    families = {r.get("geometry_family", "") for r in chosen}
    filled = len(chosen) == 6
    if not filled:
        return {"delta_deg": delta, "target_phases": ";".join(str(int(p)) for p in delta_target_phases(delta)), "all_six_targets_filled": False, "tolerance_mode": "missing", "filled_count": len(chosen), "tuple_score": -1e9, "candidate_ids": ";".join(r["candidate_id"] for r in chosen)}
    min_ratio = min(ratios); median_ratio = statistics.median(ratios); hmean = harmonic_mean(ratios)
    min_tx = min(txs); max_matrix = max(matrices); rms_phase = math.sqrt(sum(e*e for e in phase_errs)/len(phase_errs)); max_leak = max(leaks)
    preferred_bonus = 10.0 if mode == "preferred" else 0.0
    score = 4*min_ratio + 2*hmean + median_ratio + 5*min_tx - 12*max_matrix - 2*rms_phase - 80*max_leak + 0.5*len(families) + preferred_bonus
    return {"delta_deg": delta, "target_phases": ";".join(str(int(p)) for p in delta_target_phases(delta)), "all_six_targets_filled": True, "tolerance_mode": mode, "filled_count": 6, "min_ratio": min_ratio, "median_ratio": median_ratio, "harmonic_mean_ratio": hmean, "min_Tx": min_tx, "max_matrix_error": max_matrix, "rms_phase_error": rms_phase, "max_estimated_leakage": max_leak, "family_count": len(families), "tuple_score": score, "candidate_ids": ";".join(r["candidate_id"] for r in chosen)}


def official_tuple(pool: list[dict]) -> tuple[list[dict], dict]:
    by_id = {r["candidate_id"]: r for r in pool}
    rows = []
    for target, cid in OFFICIAL_IDS.items():
        row = dict(by_id[cid])
        row["target_phase_deg"] = float(target); row["phase_error_deg"] = phase_distance_deg(flt(row["phase_mod_360_deg"]), float(target)); row["estimated_leakage"] = flt(row["leakage"]); row["tolerance_mode"] = "official"
        rows.append(row)
    return rows, score_tuple(rows, 0, "official")


def coverage_map(pool: list[dict]) -> list[dict]:
    rows = []
    for target in range(360):
        pref = [r for r in pool if phase_distance_deg(flt(r["phase_mod_360_deg"]), target) <= PREFERRED_TOL_DEG]
        relax = [r for r in pool if phase_distance_deg(flt(r["phase_mod_360_deg"]), target) <= RELAXED_TOL_DEG]
        pref_best = sorted(pref, key=lambda r: -flt(r["ratio"],0))[0] if pref else {}
        relax_best = sorted(relax, key=lambda r: -flt(r["ratio"],0))[0] if relax else {}
        rows.append({"target_phase_deg": target, "preferred_count": len(pref), "relaxed_count": len(relax), "best_preferred_candidate_id": pref_best.get("candidate_id", ""), "best_preferred_ratio": pref_best.get("ratio", ""), "best_relaxed_candidate_id": relax_best.get("candidate_id", ""), "best_relaxed_ratio": relax_best.get("ratio", "")})
    return rows


def recommendation(best: dict, official: dict) -> bool:
    min_ratio_gain = (flt(best["min_ratio"]) / max(flt(official["min_ratio"]), EPS)) - 1.0
    leak_drop = 1.0 - flt(best["max_estimated_leakage"]) / max(flt(official["max_estimated_leakage"]), EPS)
    score_gain = flt(best["tuple_score"]) - flt(official["tuple_score"])
    return min_ratio_gain >= 0.50 or leak_drop >= 0.25 or flt(best["min_ratio"]) > 15.0 or score_gain > 10.0


def write_library(path: Path, rows: list[dict]) -> None:
    lib = []
    for i, row in enumerate(rows):
        lib.append({"slot_index": i, "target_phase_deg": row["target_phase_deg"], "candidate_id": row["candidate_id"], "geometry_family": row.get("geometry_family", ""), "phase_deg": row["phase_deg"], "phase_mod_360_deg": row["phase_mod_360_deg"], "phase_error_deg": row["phase_error_deg"], "Tx": row["Tx"], "leakage": row["leakage"], "ratio": row["ratio"], "matrix_error": row["matrix_error"], "estimated_leakage": row["estimated_leakage"], "minimum_clearance_nm": row.get("minimum_clearance_nm", ""), "tolerance_mode": row.get("tolerance_mode", ""), "source_file": row.get("source_file", "")})
    write_csv(path, lib, LIB_FIELDS)


def run_stage12_11a(repo_root: Path, paths: Stage12_11APaths) -> dict:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    pool = aggregate_candidate_pool(repo_root)
    write_csv(paths.output_dir / "stage12_11a_candidate_pool.csv", pool, POOL_FIELDS)
    scan_rows = []; tuple_by_delta: dict[int, list[dict]] = {}
    for delta in DELTAS:
        chosen, mode = construct_tuple(pool, delta)
        tuple_by_delta[delta] = chosen
        scan_rows.append(score_tuple(chosen, delta, mode))
    write_csv(paths.output_dir / "stage12_11a_phase_origin_scan.csv", scan_rows, SCAN_FIELDS)
    valid = [r for r in scan_rows if bool_from(r.get("all_six_targets_filled"), False)]
    ranked = sorted(valid, key=lambda r: -flt(r.get("tuple_score"), -1e9))
    top = [{"rank": i+1, **r} for i, r in enumerate(ranked[:20])]
    write_csv(paths.output_dir / "stage12_11a_top_phase_origin_tuples.csv", top, TOP_FIELDS)
    best = ranked[0]
    best_rows = tuple_by_delta[int(best["delta_deg"])]
    write_library(paths.output_dir / "stage12_11a_best_tuple_library.csv", best_rows)
    official_rows, official = official_tuple(pool)
    rec = recommendation(best, official)
    compare = []
    for name, row in [("official_delta0_frozen", official), ("best_shifted", best)]:
        compare.append({"tuple_name": name, **row, "improvement_min_ratio_pct": ((flt(best["min_ratio"])/max(flt(official["min_ratio"]),EPS))-1)*100 if name=="best_shifted" else 0, "improvement_max_leakage_pct": (1-flt(best["max_estimated_leakage"])/max(flt(official["max_estimated_leakage"]),EPS))*100 if name=="best_shifted" else 0, "recommend_k6_fdtd": rec if name=="best_shifted" else False})
    write_csv(paths.output_dir / "stage12_11a_official_vs_best_tuple_comparison.csv", compare, COMPARE_FIELDS)
    write_csv(paths.output_dir / "stage12_11a_phase_coverage_map.csv", coverage_map(pool), COVERAGE_FIELDS)
    lines = ["# Stage12-11A Phase-Origin Search Recommendation", "", "Boundary: read-only candidate tuple mining only. No FDTD, no K=6 simulation, no dipoles, no CP, no y-gradient, no H600/H700.", "", f"- Shifted phase origin improves over official delta=0 tuple: {flt(best['tuple_score']) > flt(official['tuple_score'])}.", f"- Best delta: {best['delta_deg']} deg.", f"- Best tuple candidate IDs: {best['candidate_ids']}.", f"- Best tuple target phases: {best['target_phases']}.", f"- min ratio: {best['min_ratio']}.", f"- median ratio: {best['median_ratio']}.", f"- harmonic mean ratio: {best['harmonic_mean_ratio']}.", f"- max estimated leakage: {best['max_estimated_leakage']}.", f"- min Tx: {best['min_Tx']}.", f"- max matrix_error: {best['max_matrix_error']}.", f"- rms phase error: {best['rms_phase_error']}.", f"- all targets filled within: {best['tolerance_mode']} tolerance.", f"- Stage12-11B K=6 FDTD replacement test recommended: {rec}."]
    if rec:
        lines.append("- Reason: shifted tuple clears at least one decision threshold for min-ratio, leakage, ratio floor, or tuple score improvement.")
    else:
        lines.append("- Recommendation: no clear shifted tuple improvement; stop H500 plane-wave refinement and report current Stage12 baseline as-is, or start a new high-margin library redesign with changed height/period/family.")
    (paths.output_dir / "stage12_11a_recommendation.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return {"output_dir": str(paths.output_dir), "candidate_pool_size": len(pool), "valid_delta_tuples": len(valid), "official_min_ratio": official["min_ratio"], "official_median_ratio": official["median_ratio"], "official_hmean_ratio": official["harmonic_mean_ratio"], "official_max_leakage": official["max_estimated_leakage"], "official_score": official["tuple_score"], "best_delta": best["delta_deg"], "best_candidate_ids": best["candidate_ids"], "best_min_ratio": best["min_ratio"], "best_median_ratio": best["median_ratio"], "best_hmean_ratio": best["harmonic_mean_ratio"], "best_max_leakage": best["max_estimated_leakage"], "best_min_Tx": best["min_Tx"], "best_max_matrix_error": best["max_matrix_error"], "best_rms_phase_error": best["rms_phase_error"], "recommend_stage12_11b": rec}