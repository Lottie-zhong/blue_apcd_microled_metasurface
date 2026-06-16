from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from metasurface.stage12_10a_240bin_refinement import (
    PLAN_FIELDS as PLAN_FIELDS_10A,
    REJECT_FIELDS,
    RESULT_FIELDS,
    bool_from,
    clearance_ok,
    estimated_leakage,
    flt,
    fmt,
    load_stage11_runner,
    nearest_bin,
    read_csv,
    result_to_metric,
    sizes,
    wrap180,
    write_csv,
)
from metasurface.stage12_10b_240bin_broad_family import parse_family

OUTPUT_DIR_NAME = "stage12_10c_h500_lp_180bin_single_dimer_refinement"
MAX_NEW_CANDIDATES = 12
FROZEN_180 = {
    "candidate_id": "H500DIMER2C_026_B240_x_pair_swap_G60_O-20",
    "ratio": 11.050389,
    "Tx": 0.921579,
    "phase_error_deg": 4.135187,
    "matrix_error": 0.301058,
    "estimated_leakage": 0.0834,
}
CLUSTER_FIELDS = ["family_key","geometry_family","placement_type","swap_order","candidate_count","best_candidate_id","best_ratio","best_Tx","best_phase_deg","best_phase_error_deg","best_matrix_error","best_estimated_leakage","strict_count","preferred_window_count","extended_window_count"]
PLAN_FIELDS = ["dimer_case_id","geometry_family","refine_family","target_actual_bin_deg","source_pair_id","static_original_bin_deg","j1_candidate_id","j2_candidate_id","height_nm","lambda_nm","p_x_nm","p_y_nm","j1_shape_family","j1_geometry_params","j2_length_nm","j2_width_nm","j2_rotation_deg","placement_type","swap_order","gap_nm","local_offset_nm","j1_center_x_nm","j1_center_y_nm","j2_center_x_nm","j2_center_y_nm","dimer_gap_nm","edge_margin_nm","minimum_clearance_nm","clearance_below_20nm","geometry_legal","run_selected","notes"]

@dataclass(frozen=True)
class Stage12_10CPaths:
    output_dir: Path
    stage11_freeze_dir: Path
    stage12_10b_dir: Path
    fdtd_work_dir: Path


def phase_error_to_180(phase_deg: float) -> float:
    return abs(wrap180(phase_deg - 180.0))


def in_phase_window(phase_deg: float, low: float = 165.0, high: float = 195.0) -> bool:
    phase = phase_deg % 360.0
    return low <= phase <= high


def in_extended_window(phase_deg: float) -> bool:
    phase = phase_deg % 360.0
    return 150.0 <= phase <= 210.0


def classify_candidate_180(row: dict) -> dict[str, bool]:
    nearest = int(float(row.get("nearest_bin_deg", -999)))
    phase_err = flt(row.get("phase_error_deg"))
    tx = flt(row.get("Tx"))
    ratio = flt(row.get("conversion_to_leakage_ratio"))
    matrix = flt(row.get("matrix_error"))
    leakage = flt(row.get("estimated_leakage"))
    legal = bool_from(row.get("geometry_legal", True))
    hard = nearest == 180 and phase_err <= 12 and tx >= 0.75 and ratio >= 20 and matrix <= 0.28 and legal
    preferred = hard and phase_err <= 8 and tx >= 0.80 and ratio >= 30 and matrix <= 0.25
    stretch = hard and ratio >= 50 and leakage <= 0.03 and matrix <= 0.20
    return {"hard_pass": hard, "preferred_pass": preferred, "stretch_pass": stretch}


def candidate_score_180(row: dict) -> float:
    return 25*flt(row.get("conversion_to_leakage_ratio"),0) + 10*flt(row.get("Tx"),0) - 10*flt(row.get("phase_error_deg"),999) - 50*flt(row.get("matrix_error"),999) - 25*flt(row.get("estimated_leakage"),999)


def normalize_existing_180(row: dict[str,str], source_file: Path) -> dict | None:
    cid = row.get("candidate_id") or row.get("dimer_case_id") or row.get("best_case_id")
    if not cid or "H500" not in cid:
        return None
    phase = flt(row.get("actual_common_phase_deg"), flt(row.get("dimer_output_phase_deg"), flt(row.get("phase_deg"))))
    if math.isnan(phase) or not in_extended_window(phase):
        return None
    tx = flt(row.get("selected_x_power"), flt(row.get("selected_power"), flt(row.get("target_x_power"))))
    leakage = flt(row.get("blocked_y_leakage"), flt(row.get("blocked_input_total_power"), flt(row.get("y_input_total_leak_power"))))
    ratio = flt(row.get("conversion_to_leakage_ratio"), flt(row.get("projection_selectivity_ratio"), flt(row.get("dimer_selectivity_ratio"))))
    matrix = flt(row.get("matrix_error"), flt(row.get("matrix_projection_error_norm")))
    out = {"candidate_id": cid, "source_file": str(source_file), "nearest_bin_deg": nearest_bin(phase), "phase_deg": phase, "phase_error_deg": phase_error_to_180(phase), "Tx": tx, "blocked_y_leakage": leakage, "conversion_to_leakage_ratio": ratio, "matrix_error": matrix, "estimated_leakage": estimated_leakage(tx, ratio, leakage), "strict": bool_from(row.get("strict") or row.get("dimer_pass_strict") or ("true" if "strict" in row.get("usable_status", "") else "")), "geometry_legal": bool_from(row.get("geometry_legal", True)), "minimum_clearance_nm": flt(row.get("minimum_clearance_nm"), flt(row.get("dimer_gap_nm"), math.nan)), "geometry_family": row.get("geometry_family") or parse_family(row)}
    out["score"] = candidate_score_180(out)
    return out


def aggregate_existing(repo_root: Path, paths: Stage12_10CPaths) -> list[dict]:
    patterns = [
        "outputs/blue10k6_lp_apcd_stage11_2*_h500*/*fdtd_results*.csv",
        "outputs/stage11_2*_h500*/*fdtd_results*.csv",
        "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/*.csv",
        "outputs/stage12_10b_h500_lp_240bin_broad_family_scout/*.csv",
    ]
    seen: dict[str, dict] = {}
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            for raw in read_csv(path):
                row = normalize_existing_180(raw, path)
                if row is None:
                    continue
                cid = row["candidate_id"]
                if cid not in seen or candidate_score_180(row) > candidate_score_180(seen[cid]):
                    seen[cid] = row
    rows = sorted(seen.values(), key=lambda r: (int(flt(r.get("nearest_bin_deg"),-999)) != 180, flt(r.get("phase_error_deg"),999), -flt(r.get("conversion_to_leakage_ratio"),0), -flt(r.get("Tx"),0)))
    return rows


def cluster_existing(rows: list[dict], paths: Stage12_10CPaths) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        key = row.get("geometry_family") or parse_family(row)
        row["family_key"] = key
        groups.setdefault(key, []).append(row)
    clusters = []
    for key, group in groups.items():
        ranked = sorted(group, key=lambda r: (int(flt(r.get("nearest_bin_deg"),-999)) != 180, flt(r.get("phase_error_deg"),999), -flt(r.get("conversion_to_leakage_ratio"),0)))
        best = ranked[0]
        parts = key.rsplit("_", 1)
        clusters.append({"family_key": key, "geometry_family": key, "placement_type": parts[0] if len(parts)==2 else key, "swap_order": parts[1] if len(parts)==2 else "", "candidate_count": len(group), "best_candidate_id": best.get("candidate_id"), "best_ratio": best.get("conversion_to_leakage_ratio"), "best_Tx": best.get("Tx"), "best_phase_deg": best.get("phase_deg"), "best_phase_error_deg": best.get("phase_error_deg"), "best_matrix_error": best.get("matrix_error"), "best_estimated_leakage": best.get("estimated_leakage"), "strict_count": sum(1 for r in group if bool_from(r.get("strict"))), "preferred_window_count": sum(1 for r in group if in_phase_window(flt(r.get("phase_deg")))), "extended_window_count": len(group)})
    clusters = sorted(clusters, key=lambda r: (-int(r["preferred_window_count"]), flt(r.get("best_phase_error_deg"),999), -flt(r.get("best_ratio"),0)))
    write_csv(paths.output_dir / "stage12_10c_180bin_family_cluster_audit.csv", clusters, CLUSTER_FIELDS)
    lines = ["# Stage12-10C 180-bin Family Cluster Summary", "", f"broad_180_neighborhood_candidate_count = {len(rows)}", f"family_cluster_count = {len(clusters)}", "", "| family | count | preferred-window | best candidate | best ratio | best Tx | best phase error | best matrix error |", "|---|---:|---:|---|---:|---:|---:|---:|"]
    for row in clusters:
        lines.append(f"| {row['family_key']} | {row['candidate_count']} | {row['preferred_window_count']} | {row['best_candidate_id']} | {row['best_ratio']} | {row['best_Tx']} | {row['best_phase_error_deg']} | {row['best_matrix_error']} |")
    (paths.output_dir / "stage12_10c_180bin_family_cluster_summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return clusters


def load_plan_row(repo_root: Path, candidate_id: str) -> dict[str,str]:
    for path in repo_root.glob("outputs/**/*plan*.csv"):
        for row in read_csv(path):
            if row.get("dimer_case_id") == candidate_id or row.get("candidate_id") == candidate_id:
                return row
    raise FileNotFoundError(candidate_id)


def place_family(row: dict[str,str], placement: str, gap: float, offset: float, swap: bool) -> tuple[float,float,float,float,float,float,bool]:
    j1x,j1y,j2x,j2y = sizes(row)
    if placement == "x_pair":
        sep = (j1x+j2x)/2 + gap
        x1,y1,x2,y2 = -sep/2 + offset/2, 0.0, sep/2 + offset/2, 0.0
        dgap = abs(x2-x1) - (j1x+j2x)/2
    elif placement == "y_pair":
        sep = (j1y+j2y)/2 + gap
        x1,y1,x2,y2 = offset/2, -sep/2, offset/2, sep/2
        dgap = abs(y2-y1) - (j1y+j2y)/2
    else:
        sepx = (j1x+j2x)/2 + gap / math.sqrt(2)
        sepy = (j1y+j2y)/2 + gap / math.sqrt(2)
        x1,y1,x2,y2 = -sepx/2 + offset/2, -sepy/2, sepx/2 + offset/2, sepy/2
        dx = abs(x2-x1) - (j1x+j2x)/2
        dy = abs(y2-y1) - (j1y+j2y)/2
        dgap = math.hypot(dx, dy) if dx >= 0 and dy >= 0 else min(dx, dy)
    if swap:
        x1,y1,x2,y2 = x2,y2,x1,y1
    px, py = flt(row.get("p_x_nm"),431.907786), flt(row.get("p_y_nm"),432.0)
    edge = min(px/2 - max(abs(x1)+j1x/2, abs(x2)+j2x/2), py/2 - max(abs(y1)+j1y/2, abs(y2)+j2y/2))
    return x1,y1,x2,y2,dgap,edge,clearance_ok(dgap, edge)


def candidate_specs() -> list[tuple[str,bool,float,float,str]]:
    return [
        ("x_pair", True, 50, -20, "x_pair_swap_lowG"),
        ("x_pair", True, 60, -20, "x_pair_swap_frozen_control"),
        ("x_pair", True, 70, -20, "x_pair_swap_highG"),
        ("x_pair", False, 60, -20, "x_pair_noswap_control"),
        ("x_pair", False, 80, -24, "x_pair_noswap_highG"),
        ("y_pair", True, 90, -20, "y_pair_swap_stage12_10b_donor"),
        ("y_pair", True, 80, -20, "y_pair_swap_pull_lowG"),
        ("y_pair", True, 100, -20, "y_pair_swap_pull_highG"),
        ("y_pair", False, 90, -20, "y_pair_noswap_control"),
        ("diag_pair", True, 80, -20, "diag_pair_swap_control"),
        ("diag_pair", False, 80, -20, "diag_pair_noswap_control"),
        ("diag_pair", True, 100, -16, "diag_pair_swap_highG"),
    ]


def generate_candidate_plan(repo_root: Path, paths: Stage12_10CPaths) -> tuple[list[dict], list[dict]]:
    source = load_plan_row(repo_root, FROZEN_180["candidate_id"])
    rows, rejected = [], []
    for idx, (placement, swap, gap, offset, label) in enumerate(candidate_specs(), 1):
        x1,y1,x2,y2,dgap,edge,legal = place_family(source, placement, float(gap), float(offset), swap)
        swap_label = "swap" if swap else "noswap"
        cid = f"H500DIMER12C_{idx:03d}_B180_{placement}_{swap_label}_G{int(gap)}_O{int(offset)}"
        if not legal:
            rejected.append({"candidate_id": cid, "reason": "geometry_illegal_or_clearance_below_15nm", "notes": f"clearance={dgap}, edge={edge}"})
            continue
        row = dict(source)
        row.update({"dimer_case_id": cid, "geometry_family": f"{placement}_{swap_label}", "refine_family": f"stage12_10c_{label}", "target_actual_bin_deg": "180", "bin_deg": "180", "static_output_phase_deg": "180", "static_predicted_ratio": "", "static_phase_error_deg": "", "static_target_x_power": "", "static_leak_y_power": "", "height_nm": "500.000000", "lambda_nm": source.get("lambda_nm", "450.000000"), "placement_type": placement, "swap_order": "J2-J1" if swap else "J1-J2", "gap_nm": fmt(float(gap)), "local_offset_nm": fmt(float(offset)), "j1_center_x_nm": fmt(x1), "j1_center_y_nm": fmt(y1), "j2_center_x_nm": fmt(x2), "j2_center_y_nm": fmt(y2), "dimer_gap_nm": fmt(dgap), "edge_margin_nm": fmt(edge), "minimum_clearance_nm": fmt(dgap), "clearance_below_20nm": str(dgap < 20).lower(), "geometry_legal": "true", "run_selected": "true", "notes": "Stage12-10C H500 180-degree single-dimer high-margin refinement; no K=6."})
        rows.append(row)
    rows = rows[:MAX_NEW_CANDIDATES]
    write_csv(paths.output_dir / "stage12_10c_180bin_candidate_plan.csv", rows, PLAN_FIELDS)
    write_csv(paths.output_dir / "stage12_10c_180bin_geometry_audit.csv", rows, PLAN_FIELDS)
    write_csv(paths.output_dir / "stage12_10c_180bin_failed_or_rejected_candidates.csv", rejected, REJECT_FIELDS)
    return rows, rejected


def run_fdtd(repo_root: Path, paths: Stage12_10CPaths, plan_rows: list[dict], runtime_path: str = "configs/runtime.yaml") -> list[dict]:
    runner = load_stage11_runner(repo_root)
    runner.FDTD_DIR = paths.fdtd_work_dir
    runner.RESULT_CSV = paths.output_dir / "stage12_10c_180bin_raw_fdtd_results.csv"
    runner.SUMMARY_MD = paths.output_dir / "stage12_10c_180bin_fdtd_summary.md"
    runtime = runner.load_runtime_config(runtime_path)
    lumapi = runner.import_lumapi(runtime)
    results = []
    for row in [r for r in plan_rows if bool_from(r.get("run_selected"))]:
        x = runner.run_one(lumapi, runtime, row, "x")
        y = runner.run_one(lumapi, runtime, row, "y")
        combined = runner.combine(row, x, y)
        results.append(combined)
        runner.write_csv(runner.RESULT_CSV, results, runner.RESULT_FIELDS)
    return results


def result_to_metric_180(row: dict, plan_by_id: dict[str,dict]) -> dict:
    plan = plan_by_id.get(row.get("dimer_case_id"), {})
    if plan:
        row = {**row, "dimer_gap_nm": plan.get("minimum_clearance_nm", plan.get("dimer_gap_nm", ""))}
    out = result_to_metric(row)
    phase = flt(out.get("phase_deg"))
    out["nearest_bin_deg"] = nearest_bin(phase)
    out["phase_error_deg"] = phase_error_to_180(phase)
    out["geometry_family"] = plan.get("geometry_family", parse_family(plan or out))
    out.update(classify_candidate_180(out))
    return out


def rank_results(results: list[dict], paths: Stage12_10CPaths) -> list[dict]:
    plan_by_id = {row.get("dimer_case_id"): row for row in read_csv(paths.output_dir / "stage12_10c_180bin_candidate_plan.csv")}
    rows = [result_to_metric_180(row, plan_by_id) for row in results]
    rows = sorted(rows, key=lambda r: (not bool_from(r.get("hard_pass")), int(flt(r.get("nearest_bin_deg"),-999)) != 180, flt(r.get("phase_error_deg"),999), -flt(r.get("conversion_to_leakage_ratio"),0), -flt(r.get("Tx"),0), flt(r.get("matrix_error"),999)))
    fields = ["candidate_id","geometry_family"] + [f for f in RESULT_FIELDS if f != "candidate_id"]
    write_csv(paths.output_dir / "stage12_10c_180bin_fdtd_results.csv", rows, fields)
    write_csv(paths.output_dir / "stage12_10c_180bin_ranked_candidates.csv", rows, fields)
    return rows


def write_summaries(paths: Stage12_10CPaths, ranked: list[dict], cluster_count: int, generated_count: int, fdtd_runs: int) -> dict:
    best = ranked[0] if ranked else {}
    hard = bool_from(best.get("hard_pass")); pref = bool_from(best.get("preferred_pass")); stretch = bool_from(best.get("stretch_pass"))
    improves = bool(best) and flt(best.get("conversion_to_leakage_ratio"),0) > FROZEN_180["ratio"] and flt(best.get("estimated_leakage"),999) < FROZEN_180["estimated_leakage"]
    lines = ["# Stage12-10C 180-bin Best Candidate Summary", "", f"- Family clusters audited: {cluster_count}.", f"- New 180-degree candidates generated: {generated_count}.", f"- Single-source FDTD runs: {fdtd_runs}.", f"- New 180-degree candidate improves over frozen 180-degree bin: {improves}.", f"- Best candidate ID: {best.get('candidate_id','')}.", f"- Best family: {best.get('geometry_family','')}.", f"- Best ratio: {best.get('conversion_to_leakage_ratio','')}.", f"- Best Tx: {best.get('Tx','')}.", f"- Best phase error: {best.get('phase_error_deg','')}.", f"- Best matrix_error: {best.get('matrix_error','')}.", f"- Estimated leakage: {best.get('estimated_leakage','')}.", f"- Hard pass: {hard}.", f"- Preferred pass: {pref}.", f"- Stretch pass: {stretch}.", f"- Use this candidate in a later K=6 replacement test: {hard}.", "- If 180-degree improves strongly, recommend Stage12-10D for 300-degree or Stage12-11 for K=6 replacement test using improved bins.", "- Boundary: single-dimer only; no K=6, no dipoles, no CP, no y-gradient, no H600/H700."]
    (paths.output_dir / "stage12_10c_180bin_best_candidate_summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    rec = ["# Stage12-10C Next Recommendation", "", ("Candidate is eligible for later K=6 replacement validation after an explicit freeze." if hard else "Do not replace the frozen 180-degree bin yet."), "If no strong 180-degree gain is confirmed, move to 300-degree margin improvement or a broader high-margin library redesign."]
    (paths.output_dir / "stage12_10c_next_recommendation.md").write_text("\n".join(rec)+"\n", encoding="utf-8")
    return {"best_candidate_id": best.get("candidate_id",""), "best_family": best.get("geometry_family",""), "best_ratio": best.get("conversion_to_leakage_ratio",""), "best_Tx": best.get("Tx",""), "best_leakage": best.get("estimated_leakage",""), "hard_pass": hard, "preferred_pass": pref, "stretch_pass": stretch}


def run_stage12_10c(repo_root: Path, paths: Stage12_10CPaths, runtime_path: str = "configs/runtime.yaml") -> dict:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    existing = aggregate_existing(repo_root, paths)
    clusters = cluster_existing(existing, paths)
    plan, _ = generate_candidate_plan(repo_root, paths)
    raw = run_fdtd(repo_root, paths, plan, runtime_path)
    ranked = rank_results(raw, paths)
    selected_count = sum(1 for row in plan if bool_from(row.get("run_selected")))
    summary = write_summaries(paths, ranked, len(clusters), len(plan), selected_count*2)
    return {"output_dir": str(paths.output_dir), "family_clusters": len(clusters), "new_candidates": len(plan), "fdtd_runs": selected_count*2, **summary}