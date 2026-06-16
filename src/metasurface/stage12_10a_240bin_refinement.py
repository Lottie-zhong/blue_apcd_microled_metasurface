from __future__ import annotations

import csv, importlib.util, math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

OUTPUT_DIR_NAME = "stage12_10a_h500_lp_240bin_single_dimer_refinement"
OLD_240 = {
    "candidate_id": "H500DIMER2F_026_B240_x_pair_swap_G90_O-28",
    "nearest_bin_deg": 240,
    "phase_error_deg": 7.365287,
    "Tx": 0.737551,
    "ratio": 7.675497,
    "matrix_error": 0.360953,
    "estimated_leakage": 0.096092,
}
MAX_GENERATED_CANDIDATES = 16
MAX_FDTD_RUNS = 16
PLAN_FIELDS = ["dimer_case_id","refine_family","target_actual_bin_deg","source_pair_id","static_original_bin_deg","j1_candidate_id","j2_candidate_id","height_nm","lambda_nm","p_x_nm","p_y_nm","j1_shape_family","j1_geometry_params","j2_length_nm","j2_width_nm","j2_rotation_deg","placement_type","swap_order","gap_nm","local_offset_nm","j1_center_x_nm","j1_center_y_nm","j2_center_x_nm","j2_center_y_nm","dimer_gap_nm","edge_margin_nm","minimum_clearance_nm","clearance_below_20nm","geometry_legal","run_selected","notes"]
AUDIT_FIELDS = ["candidate_id","source_file","nearest_bin_deg","phase_deg","phase_error_deg","Tx","blocked_y_leakage","conversion_to_leakage_ratio","matrix_error","estimated_leakage","strict","geometry_legal","minimum_clearance_nm","score"]
RESULT_FIELDS = ["candidate_id","nearest_bin_deg","phase_deg","phase_error_deg","Tx","opposite_spin_or_yLP_leakage","conversion_to_leakage_ratio","matrix_error","geometry_legal","minimum_clearance_nm","strict","estimated_leakage","fdtd_status","hard_pass","preferred_pass","stretch_pass","x_fsp","y_fsp","notes"]
REJECT_FIELDS = ["candidate_id","reason","notes"]

@dataclass(frozen=True)
class Stage12_10APaths:
    output_dir: Path
    stage11_freeze_dir: Path
    fdtd_work_dir: Path


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


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def bool_from(value: object) -> bool:
    return str(value).strip().lower() in {"true","1","yes","ok"}


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def nearest_bin(phase_deg: float) -> int:
    wrapped = phase_deg % 360.0
    return min([0,60,120,180,240,300], key=lambda b: abs(wrap180(wrapped - b)))


def phase_error_to_bin(phase_deg: float, bin_deg: int = 240) -> float:
    return abs(wrap180(phase_deg - bin_deg))


def estimated_leakage(tx: float, ratio: float, direct: float = math.nan) -> float:
    if not math.isnan(direct) and direct >= 0:
        return direct
    return tx / max(ratio, 1e-12)


def classify_candidate(row: dict) -> dict[str, bool]:
    nearest = int(float(row.get("nearest_bin_deg", -999)))
    phase_err = flt(row.get("phase_error_deg"))
    tx = flt(row.get("Tx"))
    ratio = flt(row.get("conversion_to_leakage_ratio"))
    matrix = flt(row.get("matrix_error"))
    leakage = flt(row.get("estimated_leakage"))
    legal = bool_from(row.get("geometry_legal", True))
    hard = nearest == 240 and phase_err <= 12 and tx >= 0.70 and ratio >= 15 and matrix <= 0.32 and legal
    preferred = hard and phase_err <= 10 and tx >= 0.75 and ratio >= 20 and matrix <= 0.28
    stretch = hard and ratio >= 30 and leakage <= 0.03 and matrix <= 0.25
    return {"hard_pass": hard, "preferred_pass": preferred, "stretch_pass": stretch}


def candidate_score(row: dict) -> float:
    return (1000 if bool_from(row.get("strict")) else 0) + 20*flt(row.get("conversion_to_leakage_ratio"), 0) + 10*flt(row.get("Tx"),0) - 8*flt(row.get("phase_error_deg"),999) - 40*flt(row.get("matrix_error"),999) - 20*flt(row.get("estimated_leakage"),999)


def enforce_candidate_limit(rows: list[dict], limit: int = MAX_GENERATED_CANDIDATES) -> list[dict]:
    return rows[:limit]


def clearance_ok(clearance_nm: float, edge_nm: float, min_clearance_nm: float = 15.0) -> bool:
    return clearance_nm >= min_clearance_nm and edge_nm >= 0


def normalize_existing(row: dict[str,str], source_file: Path) -> dict | None:
    cid = row.get("candidate_id") or row.get("dimer_case_id") or row.get("best_case_id")
    if not cid or "H500" not in cid:
        return None
    phase = flt(row.get("actual_common_phase_deg"), flt(row.get("dimer_output_phase_deg"), flt(row.get("phase_deg"))))
    if math.isnan(phase):
        return None
    nearest = int(flt(row.get("nearest_bin_deg"), flt(row.get("actual_nearest_bin_deg"), nearest_bin(phase))))
    phase_err = flt(row.get("phase_err_deg"), flt(row.get("actual_common_phase_error_deg"), phase_error_to_bin(phase, 240)))
    tx = flt(row.get("selected_x_power"), flt(row.get("selected_power"), flt(row.get("target_x_power"))))
    leakage = flt(row.get("blocked_y_leakage"), flt(row.get("blocked_input_total_power"), flt(row.get("y_input_total_leak_power"))))
    ratio = flt(row.get("conversion_to_leakage_ratio"), flt(row.get("projection_selectivity_ratio"), flt(row.get("dimer_selectivity_ratio"))))
    matrix = flt(row.get("matrix_error"), flt(row.get("matrix_projection_error_norm")))
    if nearest != 240 and phase_error_to_bin(phase, 240) > 24:
        return None
    est = estimated_leakage(tx, ratio, leakage)
    strict = row.get("strict") or row.get("dimer_pass_strict") or ("strict" if "strict" in row.get("usable_status", "") else "")
    out = {"candidate_id": cid, "source_file": str(source_file), "nearest_bin_deg": nearest, "phase_deg": phase, "phase_error_deg": phase_err, "Tx": tx, "blocked_y_leakage": leakage, "conversion_to_leakage_ratio": ratio, "matrix_error": matrix, "estimated_leakage": est, "strict": bool_from(strict), "geometry_legal": bool_from(row.get("geometry_legal", True)), "minimum_clearance_nm": flt(row.get("minimum_clearance_nm"), flt(row.get("dimer_gap_nm"), math.nan))}
    out["score"] = candidate_score(out)
    return out


def aggregate_existing(repo_root: Path, paths: Stage12_10APaths) -> list[dict]:
    patterns = [
        "outputs/blue10k6_lp_apcd_stage11_2*_h500*/*fdtd_results*.csv",
        "outputs/stage11_2*_h500*/*fdtd_results*.csv",
        "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/*.csv",
        "outputs/stage12_8_h500_lp_k6_xgrad_selectivity_refinement/*.csv",
        "outputs/stage12_9_h500_lp_k6_xgrad_leakage_cancellation/*.csv",
    ]
    seen: dict[str, dict] = {}
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            for raw in read_csv(path):
                row = normalize_existing(raw, path)
                if row is None: continue
                cid = row["candidate_id"]
                if cid not in seen or candidate_score(row) > candidate_score(seen[cid]):
                    seen[cid] = row
    rows = sorted(seen.values(), key=lambda r: (-bool_from(r.get("strict")), -flt(r.get("conversion_to_leakage_ratio"),0), -flt(r.get("Tx"),0), flt(r.get("phase_error_deg"),999), flt(r.get("matrix_error"),999)))
    write_csv(paths.output_dir / "stage12_10a_existing_240bin_candidate_audit.csv", rows, AUDIT_FIELDS)
    lines = ["# Stage12-10A Existing 240-bin Top Candidates", "", f"existing_240deg_candidate_count = {len(rows)}", "", "| rank | candidate_id | ratio | Tx | phase_error | matrix_error | estimated_leakage | strict |", "|---:|---|---:|---:|---:|---:|---:|---|"]
    for i, row in enumerate(rows[:12], 1):
        lines.append(f"| {i} | {row['candidate_id']} | {row['conversion_to_leakage_ratio']} | {row['Tx']} | {row['phase_error_deg']} | {row['matrix_error']} | {row['estimated_leakage']} | {row['strict']} |")
    (paths.output_dir / "stage12_10a_existing_240bin_top_candidates.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return rows


def load_stage11_runner(repo_root: Path):
    script = repo_root / "scripts/stage11_lp_apcd_run_h500_dimer_fdtd_stage11_2a.py"
    spec = importlib.util.spec_from_file_location("stage11_2a_runner", script)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def load_current_240_plan_row(repo_root: Path) -> dict[str,str]:
    for path in [repo_root / "outputs/blue10k6_lp_apcd_stage11_2f_h500_dimer_120_240_refine/h500_dimer_120_240_refine_patch_plan_stage11_2f.csv", repo_root / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"]:
        for row in read_csv(path):
            if row.get("dimer_case_id") == OLD_240["candidate_id"] or row.get("candidate_id") == OLD_240["candidate_id"]:
                return row
    raise FileNotFoundError("current frozen 240-degree source plan row not found")


def sizes(row: dict[str,str]) -> tuple[float,float,float,float]:
    import json
    geom = json.loads(row["j1_geometry_params"])
    fam = row["j1_shape_family"]
    if fam == "circle": j1x = j1y = flt(geom.get("diameter_nm"))
    elif fam == "square": j1x = j1y = flt(geom.get("side_nm"))
    else: j1x, j1y = flt(geom.get("length_nm")), flt(geom.get("width_nm"))
    return j1x, j1y, flt(row["j2_length_nm"]), flt(row["j2_width_nm"])


def place(row: dict[str,str], gap: float, offset: float, swap: bool = True) -> tuple[float,float,float,float,float,float,bool]:
    j1x,j1y,j2x,j2y = sizes(row)
    sep = (j1x + j2x)/2 + gap
    x1,y1,x2,y2 = -sep/2 + offset/2, 0.0, sep/2 + offset/2, 0.0
    if swap: x1,y1,x2,y2 = x2,y2,x1,y1
    dgap = abs(x2-x1) - (j1x+j2x)/2
    px, py = flt(row.get("p_x_nm"),431.907786), flt(row.get("p_y_nm"),432.0)
    edge = min(px/2 - max(abs(x1)+j1x/2, abs(x2)+j2x/2), py/2 - max(abs(y1)+j1y/2, abs(y2)+j2y/2))
    return x1,y1,x2,y2,dgap,edge,clearance_ok(dgap, edge)


def generate_candidate_plan(repo_root: Path, paths: Stage12_10APaths) -> tuple[list[dict], list[dict]]:
    source = load_current_240_plan_row(repo_root)
    specs = [(90,-28),(85,-28),(95,-28),(90,-30),(90,-26),(80,-28),(100,-28),(90,-32),(90,-24),(75,-28),(105,-28),(85,-32),(95,-24),(80,-34),(100,-22),(90,-36)]
    rows, rejected = [], []
    for idx, (gap, offset) in enumerate(specs, 1):
        x1,y1,x2,y2,dgap,edge,legal = place(source, float(gap), float(offset), True)
        cid = f"H500DIMER12A_{idx:03d}_B240_x_pair_swap_G{gap}_O{offset}"
        if not legal:
            rejected.append({"candidate_id": cid, "reason": "geometry_illegal_or_clearance_below_15nm", "notes": f"clearance={dgap}, edge={edge}"})
            continue
        row = dict(source)
        row.update({"dimer_case_id": cid, "refine_family": "stage12_10a_240bin_local_GO", "target_actual_bin_deg": "240", "bin_deg": "240", "static_output_phase_deg": "240", "static_predicted_ratio": "", "static_phase_error_deg": "", "static_target_x_power": "", "static_leak_y_power": "", "height_nm": "500.000000", "lambda_nm": source.get("lambda_nm", "450.000000"), "placement_type": "x_pair", "swap_order": "J2-J1", "gap_nm": fmt(float(gap)), "local_offset_nm": fmt(float(offset)), "j1_center_x_nm": fmt(x1), "j1_center_y_nm": fmt(y1), "j2_center_x_nm": fmt(x2), "j2_center_y_nm": fmt(y2), "dimer_gap_nm": fmt(dgap), "edge_margin_nm": fmt(edge), "minimum_clearance_nm": fmt(dgap), "clearance_below_20nm": str(dgap < 20).lower(), "geometry_legal": "true", "run_selected": str(len(rows) < MAX_FDTD_RUNS//2).lower(), "notes": "Stage12-10A H500 240-degree single-dimer local G/O refinement; no K=6."})
        rows.append(row)
    rows = enforce_candidate_limit(rows, MAX_GENERATED_CANDIDATES)
    write_csv(paths.output_dir / "stage12_10a_240bin_candidate_plan.csv", rows, PLAN_FIELDS)
    write_csv(paths.output_dir / "stage12_10a_240bin_geometry_audit.csv", rows, PLAN_FIELDS)
    write_csv(paths.output_dir / "stage12_10a_240bin_failed_or_rejected_candidates.csv", rejected, REJECT_FIELDS)
    return rows, rejected


def run_fdtd(repo_root: Path, paths: Stage12_10APaths, plan_rows: list[dict], runtime_path: str = "configs/runtime.yaml") -> list[dict]:
    runner = load_stage11_runner(repo_root)
    runner.FDTD_DIR = paths.fdtd_work_dir
    runner.RESULT_CSV = paths.output_dir / "stage12_10a_240bin_raw_fdtd_results.csv"
    runner.SUMMARY_MD = paths.output_dir / "stage12_10a_240bin_fdtd_summary.md"
    runtime = runner.load_runtime_config(runtime_path)
    lumapi = runner.import_lumapi(runtime)
    rows = [dict(row) for row in plan_rows if bool_from(row.get("run_selected"))]
    results = []
    for row in rows:
        x = runner.run_one(lumapi, runtime, row, "x")
        y = runner.run_one(lumapi, runtime, row, "y")
        combined = runner.combine(row, x, y)
        results.append(combined)
        runner.write_csv(runner.RESULT_CSV, results, runner.RESULT_FIELDS)
    return results


def result_to_metric(row: dict) -> dict:
    tx = flt(row.get("target_x_power"))
    leakage = flt(row.get("y_input_total_leak_power"))
    ratio = flt(row.get("dimer_selectivity_ratio"))
    phase = flt(row.get("dimer_output_phase_deg"))
    phase_err = phase_error_to_bin(phase, 240)
    xcross = flt(row.get("x_input_cross_leak_power"), 0)
    matrix = math.sqrt(max(xcross,0) + max(leakage,0)) / max(math.sqrt(max(tx,0)), 1e-12)
    strict = int(nearest_bin(phase)) == 240 and phase_err <= 12 and tx >= 0.70 and ratio >= 15 and matrix <= 0.32 and bool_from(row.get("geometry_legal"))
    out = {"candidate_id": row.get("dimer_case_id"), "nearest_bin_deg": nearest_bin(phase), "phase_deg": phase, "phase_error_deg": phase_err, "Tx": tx, "opposite_spin_or_yLP_leakage": leakage, "conversion_to_leakage_ratio": ratio, "matrix_error": matrix, "geometry_legal": bool_from(row.get("geometry_legal")), "minimum_clearance_nm": flt(row.get("dimer_gap_nm"), math.nan), "strict": strict, "estimated_leakage": estimated_leakage(tx, ratio, leakage), "fdtd_status": row.get("fdtd_status"), "x_fsp": row.get("x_fsp"), "y_fsp": row.get("y_fsp"), "notes": row.get("notes", "")}
    out.update(classify_candidate(out))
    return out


def rank_results(results: list[dict], paths: Stage12_10APaths) -> list[dict]:
    plan_by_id = {row.get("dimer_case_id"): row for row in read_csv(paths.output_dir / "stage12_10a_240bin_candidate_plan.csv")}
    enriched = []
    for row in results:
        plan = plan_by_id.get(row.get("dimer_case_id"), {})
        if plan:
            row = {**row, "dimer_gap_nm": plan.get("minimum_clearance_nm", plan.get("dimer_gap_nm", ""))}
        enriched.append(row)
    rows = [result_to_metric(r) for r in enriched]
    rows = sorted(rows, key=lambda r: (not bool_from(r.get("hard_pass")), -flt(r.get("conversion_to_leakage_ratio"),0), -flt(r.get("Tx"),0), flt(r.get("phase_error_deg"),999), flt(r.get("matrix_error"),999)))
    write_csv(paths.output_dir / "stage12_10a_240bin_fdtd_results.csv", rows, RESULT_FIELDS)
    write_csv(paths.output_dir / "stage12_10a_240bin_ranked_candidates.csv", rows, RESULT_FIELDS)
    return rows


def summarize_existing_stage12_10a(paths: Stage12_10APaths) -> dict:
    raw = read_csv(paths.output_dir / "stage12_10a_240bin_raw_fdtd_results.csv")
    ranked = rank_results(raw, paths)
    existing_count = len(read_csv(paths.output_dir / "stage12_10a_existing_240bin_candidate_audit.csv"))
    generated_count = len(read_csv(paths.output_dir / "stage12_10a_240bin_candidate_plan.csv"))
    selected_count = sum(1 for row in read_csv(paths.output_dir / "stage12_10a_240bin_candidate_plan.csv") if bool_from(row.get("run_selected")))
    summary = write_summaries(paths, ranked, existing_count, generated_count, selected_count * 2)
    return {"output_dir": str(paths.output_dir), "existing_240_candidates": existing_count, "new_240_candidates": generated_count, "fdtd_runs": 0, **summary, "best_gui_fsp_generated": False}


def write_summaries(paths: Stage12_10APaths, ranked: list[dict], existing_count: int, generated_count: int, fdtd_runs: int) -> dict:
    best = ranked[0] if ranked else {}
    improved = bool(best) and flt(best.get("conversion_to_leakage_ratio"),0) > OLD_240["ratio"] and flt(best.get("estimated_leakage"),999) < OLD_240["estimated_leakage"]
    hard = bool_from(best.get("hard_pass")); pref = bool_from(best.get("preferred_pass")); stretch = bool_from(best.get("stretch_pass"))
    lines = ["# Stage12-10A 240-bin Best Candidate Summary", "", f"- Existing 240-degree candidates audited: {existing_count}.", f"- New 240-degree candidates generated: {generated_count}.", f"- Single-source FDTD runs: {fdtd_runs}.", f"- New candidate improves over frozen 240-degree bin: {improved}.", f"- Best candidate ID: {best.get('candidate_id','')}.", f"- Best ratio: {best.get('conversion_to_leakage_ratio','')}.", f"- Best Tx: {best.get('Tx','')}.", f"- Best phase error: {best.get('phase_error_deg','')}.", f"- Best matrix_error: {best.get('matrix_error','')}.", f"- Estimated leakage: {best.get('estimated_leakage','')}.", f"- Hard pass: {hard}.", f"- Preferred pass: {pref}.", f"- Stretch pass: {stretch}.", f"- Use this candidate in a later K=6 replacement test: {hard}.", "- If no strong improvement is found, 240-degree likely requires broader library expansion, not local tuning.", "- Boundary: single-dimer only; no K=6, no dipoles, no CP, no y-gradient, no H600/H700."]
    (paths.output_dir / "stage12_10a_240bin_best_candidate_summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    rec = ["# Stage12-10A Next Recommendation", "", ("Proceed to a later K=6 replacement test only after an explicit freeze/checkpoint." if hard else "Do not replace the 240-degree bin yet."), "If higher margin is still required, expand the 240-degree single-dimer library beyond local G/O tuning before additional K=6 tests."]
    (paths.output_dir / "stage12_10a_next_recommendation.md").write_text("\n".join(rec)+"\n", encoding="utf-8")
    return {"best_candidate_id": best.get("candidate_id",""), "best_ratio": best.get("conversion_to_leakage_ratio", ""), "best_Tx": best.get("Tx", ""), "best_matrix_error": best.get("matrix_error", ""), "best_leakage": best.get("estimated_leakage", ""), "hard_pass": hard, "preferred_pass": pref, "stretch_pass": stretch}


def run_stage12_10a(repo_root: Path, paths: Stage12_10APaths, runtime_path: str = "configs/runtime.yaml") -> dict:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    existing = aggregate_existing(repo_root, paths)
    plan, rejected = generate_candidate_plan(repo_root, paths)
    selected = [r for r in plan if bool_from(r.get("run_selected"))]
    raw = run_fdtd(repo_root, paths, plan, runtime_path)
    ranked = rank_results(raw, paths)
    summary = write_summaries(paths, ranked, len(existing), len(plan), len(selected)*2)
    return {"output_dir": str(paths.output_dir), "existing_240_candidates": len(existing), "new_240_candidates": len(plan), "fdtd_runs": len(selected)*2, **summary, "best_gui_fsp_generated": False}