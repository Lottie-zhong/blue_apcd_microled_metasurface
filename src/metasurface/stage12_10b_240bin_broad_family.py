from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from metasurface.stage12_10a_240bin_refinement import (
    OLD_240,
    PLAN_FIELDS as PLAN_FIELDS_10A,
    RESULT_FIELDS,
    REJECT_FIELDS,
    Stage12_10APaths,
    aggregate_existing,
    bool_from,
    classify_candidate,
    clearance_ok,
    estimated_leakage,
    flt,
    fmt,
    load_current_240_plan_row,
    load_stage11_runner,
    nearest_bin,
    phase_error_to_bin,
    read_csv,
    result_to_metric,
    sizes,
    wrap180,
    write_csv,
)

OUTPUT_DIR_NAME = "stage12_10b_h500_lp_240bin_broad_family_scout"
MAX_NEW_CANDIDATES = 12
STAGE12_10A_BEST = {
    "candidate_id": "H500DIMER12A_002_B240_x_pair_swap_G85_O-28",
    "ratio": 7.974164,
    "Tx": 0.760663,
    "matrix_error": 0.3541350695295417,
    "estimated_leakage": 0.095391,
}
CLUSTER_FIELDS = ["family_key","geometry_family","placement_type","swap_order","candidate_count","best_candidate_id","best_ratio","best_Tx","best_phase_deg","best_phase_error_deg","best_matrix_error","best_estimated_leakage","strict_count","preferred_window_count","extended_window_count"]
PLAN_FIELDS = ["dimer_case_id","geometry_family","refine_family","target_actual_bin_deg","source_pair_id","static_original_bin_deg","j1_candidate_id","j2_candidate_id","height_nm","lambda_nm","p_x_nm","p_y_nm","j1_shape_family","j1_geometry_params","j2_length_nm","j2_width_nm","j2_rotation_deg","placement_type","swap_order","gap_nm","local_offset_nm","j1_center_x_nm","j1_center_y_nm","j2_center_x_nm","j2_center_y_nm","dimer_gap_nm","edge_margin_nm","minimum_clearance_nm","clearance_below_20nm","geometry_legal","run_selected","notes"]

@dataclass(frozen=True)
class Stage12_10BPaths:
    output_dir: Path
    stage11_freeze_dir: Path
    stage12_10a_dir: Path
    fdtd_work_dir: Path


def in_phase_window(phase_deg: float, low: float = 220.0, high: float = 260.0) -> bool:
    phase = phase_deg % 360.0
    return low <= phase <= high


def in_extended_window(phase_deg: float) -> bool:
    phase = phase_deg % 360.0
    return 210.0 <= phase <= 270.0


def parse_family(row: dict) -> str:
    family = str(row.get("geometry_family") or "").strip()
    if family:
        return family
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


def cluster_existing(rows: list[dict], paths: Stage12_10BPaths) -> list[dict]:
    broad = [r for r in rows if in_extended_window(flt(r.get("phase_deg")))]
    groups: dict[str, list[dict]] = {}
    for row in broad:
        key = parse_family(row)
        row["family_key"] = key
        groups.setdefault(key, []).append(row)
    cluster_rows = []
    for key, group in groups.items():
        ranked = sorted(group, key=lambda r: (-flt(r.get("conversion_to_leakage_ratio"),0), -flt(r.get("Tx"),0), flt(r.get("phase_error_deg"),999), flt(r.get("matrix_error"),999)))
        best = ranked[0]
        parts = key.rsplit("_", 1)
        cluster_rows.append({
            "family_key": key,
            "geometry_family": key,
            "placement_type": parts[0] if len(parts) == 2 else key,
            "swap_order": parts[1] if len(parts) == 2 else "",
            "candidate_count": len(group),
            "best_candidate_id": best.get("candidate_id"),
            "best_ratio": best.get("conversion_to_leakage_ratio"),
            "best_Tx": best.get("Tx"),
            "best_phase_deg": best.get("phase_deg"),
            "best_phase_error_deg": best.get("phase_error_deg"),
            "best_matrix_error": best.get("matrix_error"),
            "best_estimated_leakage": best.get("estimated_leakage"),
            "strict_count": sum(1 for r in group if bool_from(r.get("strict"))),
            "preferred_window_count": sum(1 for r in group if in_phase_window(flt(r.get("phase_deg")))),
            "extended_window_count": len(group),
        })
    cluster_rows = sorted(cluster_rows, key=lambda r: (-int(r["preferred_window_count"]), -flt(r.get("best_ratio"),0), -flt(r.get("best_Tx"),0)))
    write_csv(paths.output_dir / "stage12_10b_240bin_family_cluster_audit.csv", cluster_rows, CLUSTER_FIELDS)
    lines = ["# Stage12-10B 240-bin Family Cluster Summary", "", f"broad_240_neighborhood_candidate_count = {len(broad)}", f"family_cluster_count = {len(cluster_rows)}", "", "| family | count | preferred-window | best candidate | best ratio | best Tx | best phase error | best matrix error |", "|---|---:|---:|---|---:|---:|---:|---:|"]
    for row in cluster_rows:
        lines.append(f"| {row['family_key']} | {row['candidate_count']} | {row['preferred_window_count']} | {row['best_candidate_id']} | {row['best_ratio']} | {row['best_Tx']} | {row['best_phase_error_deg']} | {row['best_matrix_error']} |")
    (paths.output_dir / "stage12_10b_240bin_family_cluster_summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return cluster_rows


def enforce_candidate_limit(rows: list[dict], limit: int = MAX_NEW_CANDIDATES) -> list[dict]:
    return rows[:limit]


def place_family(row: dict[str, str], placement: str, gap: float, offset: float, swap: bool) -> tuple[float,float,float,float,float,float,bool]:
    j1x,j1y,j2x,j2y = sizes(row)
    if placement == "x_pair":
        sep = (j1x + j2x) / 2 + gap
        x1,y1,x2,y2 = -sep/2 + offset/2, 0.0, sep/2 + offset/2, 0.0
        dgap = abs(x2-x1) - (j1x+j2x)/2
    elif placement == "y_pair":
        sep = (j1y + j2y) / 2 + gap
        x1,y1,x2,y2 = offset/2, -sep/2, offset/2, sep/2
        dgap = abs(y2-y1) - (j1y+j2y)/2
    else:
        sepx = (j1x + j2x)/2 + gap / math.sqrt(2)
        sepy = (j1y + j2y)/2 + gap / math.sqrt(2)
        x1,y1,x2,y2 = -sepx/2 + offset/2, -sepy/2, sepx/2 + offset/2, sepy/2
        dx = abs(x2-x1) - (j1x+j2x)/2
        dy = abs(y2-y1) - (j1y+j2y)/2
        dgap = math.hypot(dx, dy) if dx >= 0 and dy >= 0 else min(dx, dy)
    if swap:
        x1,y1,x2,y2 = x2,y2,x1,y1
    px, py = flt(row.get("p_x_nm"),431.907786), flt(row.get("p_y_nm"),432.0)
    edge = min(px/2 - max(abs(x1)+j1x/2, abs(x2)+j2x/2), py/2 - max(abs(y1)+j1y/2, abs(y2)+j2y/2))
    return x1,y1,x2,y2,dgap,edge,clearance_ok(dgap, edge)


def candidate_specs() -> list[tuple[str, bool, float, float, str]]:
    return [
        ("x_pair", True, 75, -36, "x_pair_swap_away_lowG"),
        ("x_pair", True, 105, -20, "x_pair_swap_away_highG"),
        ("x_pair", False, 80, -30, "x_pair_noswap_control"),
        ("x_pair", False, 100, -24, "x_pair_noswap_highG"),
        ("y_pair", True, 70, -28, "y_pair_swap_control"),
        ("y_pair", False, 70, -28, "y_pair_noswap_control"),
        ("diag_pair", True, 80, -28, "diag_pair_swap_control"),
        ("diag_pair", False, 80, -28, "diag_pair_noswap_control"),
        ("diag_pair", True, 100, -20, "diag_pair_swap_highG"),
        ("y_pair", True, 90, -20, "y_pair_swap_highG"),
        ("x_pair", True, 70, -44, "x_pair_swap_asymmetric_farO"),
        ("x_pair", False, 110, -16, "x_pair_noswap_far_highG"),
    ]


def generate_candidate_plan(repo_root: Path, paths: Stage12_10BPaths) -> tuple[list[dict], list[dict]]:
    source = load_current_240_plan_row(repo_root)
    rows, rejected = [], []
    for idx, (placement, swap, gap, offset, label) in enumerate(candidate_specs(), 1):
        x1,y1,x2,y2,dgap,edge,legal = place_family(source, placement, float(gap), float(offset), swap)
        swap_label = "swap" if swap else "noswap"
        cid = f"H500DIMER12B_{idx:03d}_B240_{placement}_{swap_label}_G{int(gap)}_O{int(offset)}"
        if not legal:
            rejected.append({"candidate_id": cid, "reason": "geometry_illegal_or_clearance_below_15nm", "notes": f"clearance={dgap}, edge={edge}"})
            continue
        row = dict(source)
        row.update({
            "dimer_case_id": cid,
            "geometry_family": f"{placement}_{swap_label}",
            "refine_family": f"stage12_10b_{label}",
            "target_actual_bin_deg": "240",
            "bin_deg": "240",
            "static_output_phase_deg": "240",
            "static_predicted_ratio": "",
            "static_phase_error_deg": "",
            "static_target_x_power": "",
            "static_leak_y_power": "",
            "height_nm": "500.000000",
            "lambda_nm": source.get("lambda_nm", "450.000000"),
            "placement_type": placement,
            "swap_order": "J2-J1" if swap else "J1-J2",
            "gap_nm": fmt(float(gap)),
            "local_offset_nm": fmt(float(offset)),
            "j1_center_x_nm": fmt(x1), "j1_center_y_nm": fmt(y1),
            "j2_center_x_nm": fmt(x2), "j2_center_y_nm": fmt(y2),
            "dimer_gap_nm": fmt(dgap), "edge_margin_nm": fmt(edge),
            "minimum_clearance_nm": fmt(dgap),
            "clearance_below_20nm": str(dgap < 20).lower(),
            "geometry_legal": "true",
            "run_selected": "true",
            "notes": "Stage12-10B H500 240-degree broad-family single-dimer scout; no K=6.",
        })
        rows.append(row)
    rows = enforce_candidate_limit(rows, MAX_NEW_CANDIDATES)
    write_csv(paths.output_dir / "stage12_10b_240bin_candidate_plan.csv", rows, PLAN_FIELDS)
    write_csv(paths.output_dir / "stage12_10b_240bin_geometry_audit.csv", rows, PLAN_FIELDS)
    write_csv(paths.output_dir / "stage12_10b_240bin_failed_or_rejected_candidates.csv", rejected, REJECT_FIELDS)
    return rows, rejected


def run_fdtd(repo_root: Path, paths: Stage12_10BPaths, plan_rows: list[dict], runtime_path: str = "configs/runtime.yaml") -> list[dict]:
    runner = load_stage11_runner(repo_root)
    runner.FDTD_DIR = paths.fdtd_work_dir
    runner.RESULT_CSV = paths.output_dir / "stage12_10b_240bin_raw_fdtd_results.csv"
    runner.SUMMARY_MD = paths.output_dir / "stage12_10b_240bin_fdtd_summary.md"
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


def result_to_metric_with_family(row: dict, plan_by_id: dict[str, dict]) -> dict:
    plan = plan_by_id.get(row.get("dimer_case_id"), {})
    if plan:
        row = {**row, "dimer_gap_nm": plan.get("minimum_clearance_nm", plan.get("dimer_gap_nm", ""))}
    out = result_to_metric(row)
    out["geometry_family"] = plan.get("geometry_family", parse_family(plan or out))
    return out


def rank_results(results: list[dict], paths: Stage12_10BPaths) -> list[dict]:
    plan_by_id = {row.get("dimer_case_id"): row for row in read_csv(paths.output_dir / "stage12_10b_240bin_candidate_plan.csv")}
    rows = [result_to_metric_with_family(row, plan_by_id) for row in results]
    rows = sorted(rows, key=lambda r: (
        not bool_from(r.get("hard_pass")),
        int(flt(r.get("nearest_bin_deg"), -999)) != 240,
        flt(r.get("phase_error_deg"), 999) > 24,
        flt(r.get("phase_error_deg"), 999),
        -flt(r.get("conversion_to_leakage_ratio"),0),
        -flt(r.get("Tx"),0),
        flt(r.get("matrix_error"),999),
    ))
    fields = ["candidate_id","geometry_family"] + [f for f in RESULT_FIELDS if f != "candidate_id"]
    write_csv(paths.output_dir / "stage12_10b_240bin_fdtd_results.csv", rows, fields)
    write_csv(paths.output_dir / "stage12_10b_240bin_ranked_candidates.csv", rows, fields)
    return rows


def summarize_existing_stage12_10b(paths: Stage12_10BPaths) -> dict:
    raw = read_csv(paths.output_dir / "stage12_10b_240bin_raw_fdtd_results.csv")
    ranked = rank_results(raw, paths)
    clusters = read_csv(paths.output_dir / "stage12_10b_240bin_family_cluster_audit.csv")
    plan = read_csv(paths.output_dir / "stage12_10b_240bin_candidate_plan.csv")
    selected_count = sum(1 for row in plan if bool_from(row.get("run_selected")))
    summary = write_summaries(paths, ranked, len(clusters), len(plan), selected_count * 2)
    return {"output_dir": str(paths.output_dir), "family_clusters": len(clusters), "new_candidates": len(plan), "fdtd_runs": 0, **summary}


def write_summaries(paths: Stage12_10BPaths, ranked: list[dict], cluster_count: int, generated_count: int, fdtd_runs: int) -> dict:
    best = ranked[0] if ranked else {}
    hard = bool_from(best.get("hard_pass")); pref = bool_from(best.get("preferred_pass")); stretch = bool_from(best.get("stretch_pass"))
    improves_old = bool(best) and flt(best.get("conversion_to_leakage_ratio"),0) > OLD_240["ratio"] and flt(best.get("estimated_leakage"),999) < OLD_240["estimated_leakage"]
    improves_10a = bool(best) and flt(best.get("conversion_to_leakage_ratio"),0) > STAGE12_10A_BEST["ratio"] and flt(best.get("estimated_leakage"),999) < STAGE12_10A_BEST["estimated_leakage"]
    lines = [
        "# Stage12-10B 240-bin Best Candidate Summary", "",
        f"- Family clusters audited: {cluster_count}.",
        f"- New broad-family candidates generated: {generated_count}.",
        f"- Single-source FDTD runs: {fdtd_runs}.",
        f"- Broad-family search improves over frozen 240-degree bin: {improves_old}.",
        f"- Broad-family search improves over Stage12-10A best: {improves_10a}.",
        f"- Best candidate ID: {best.get('candidate_id','')}.",
        f"- Best family: {best.get('geometry_family','')}.",
        f"- Best ratio: {best.get('conversion_to_leakage_ratio','')}.",
        f"- Best Tx: {best.get('Tx','')}.",
        f"- Best phase error: {best.get('phase_error_deg','')}.",
        f"- Best matrix_error: {best.get('matrix_error','')}.",
        f"- Estimated leakage: {best.get('estimated_leakage','')}.",
        f"- Hard pass: {hard}.",
        f"- Preferred pass: {pref}.",
        f"- Stretch pass: {stretch}.",
        f"- Use this candidate in a later K=6 replacement test: {hard}.",
        "- If no strong improvement is found, move to 180-degree/300-degree bin margin improvement or broader high-margin library redesign, not more 240-degree local tuning.",
        "- Boundary: single-dimer only; no K=6, no dipoles, no CP, no y-gradient, no H600/H700.",
    ]
    (paths.output_dir / "stage12_10b_240bin_best_candidate_summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    rec = ["# Stage12-10B Next Recommendation", "", ("Promote the candidate only through a later explicit K=6 replacement validation." if hard else "Do not replace the frozen 240-degree bin yet."), "If stronger margin is required, prioritize 180-degree/300-degree margin improvement or a broader high-margin single-dimer library redesign."]
    (paths.output_dir / "stage12_10b_next_recommendation.md").write_text("\n".join(rec)+"\n", encoding="utf-8")
    return {"best_candidate_id": best.get("candidate_id",""), "best_family": best.get("geometry_family",""), "best_ratio": best.get("conversion_to_leakage_ratio",""), "best_Tx": best.get("Tx",""), "best_matrix_error": best.get("matrix_error",""), "best_leakage": best.get("estimated_leakage",""), "hard_pass": hard, "preferred_pass": pref, "stretch_pass": stretch}


def run_stage12_10b(repo_root: Path, paths: Stage12_10BPaths, runtime_path: str = "configs/runtime.yaml") -> dict:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    audit_paths = Stage12_10APaths(paths.output_dir, paths.stage11_freeze_dir, paths.fdtd_work_dir)
    existing = aggregate_existing(repo_root, audit_paths)
    clusters = cluster_existing(existing, paths)
    plan, _ = generate_candidate_plan(repo_root, paths)
    raw = run_fdtd(repo_root, paths, plan, runtime_path)
    ranked = rank_results(raw, paths)
    selected_count = sum(1 for row in plan if bool_from(row.get("run_selected")))
    summary = write_summaries(paths, ranked, len(clusters), len(plan), selected_count * 2)
    return {"output_dir": str(paths.output_dir), "family_clusters": len(clusters), "new_candidates": len(plan), "fdtd_runs": selected_count * 2, **summary}