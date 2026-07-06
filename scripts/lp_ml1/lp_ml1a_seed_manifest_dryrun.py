from __future__ import annotations
import csv, json, math, random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "lp_ml1a_seed_manifest_dryrun"
ML0 = ROOT / "outputs" / "lp_ml0_existing_data_audit"
REPORT = ROOT / "reports" / "lp_ml1a_seed_manifest_plan.md"
RULES = ROOT / "reports" / "lp_ml1a_geometry_rules.yaml"
SEED = 20260706
RUN_POLICY = "LP-ML1B_periodic_plane_wave_fullwave_later"
WAVES = "450,450.5,451,451.5,452,452.5,453,453.5,454"
GROUP_TARGETS = {"B300_focused": 240, "B240_focused": 180, "H500_450nm_seed_robustification": 90, "global_escape": 90}
HEIGHT_TARGETS = {500: 270, 600: 210, 650: 90, 700: 30}
COLUMNS = ["candidate_id","target_bin_deg","sampling_group","source_candidate_id","source_stage","source_diagnosis_category","H_nm","L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg","gap_or_dx_nm","theta1_sin2","theta1_cos2","theta2_sin2","theta2_cos2","intended_lambda_min_nm","intended_lambda_max_nm","intended_lambda_points","intended_wavelengths_nm","run_policy","prepared_not_run","geometry_valid","geometry_reject_reason","duplicate_group_id","priority_score","notes"]


def read_csv(p: Path) -> list[dict]:
    with p.open("r", encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def write_csv(p: Path, rows: list[dict], fields: list[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def fnum(x):
    try:
        if x in (None, ""): return None
        v = float(x); return None if math.isnan(v) else v
    except ValueError: return None

def trig(theta: float) -> tuple[float, float]:
    r = math.radians(2 * theta); return round(math.sin(r), 8), round(math.cos(r), 8)

def load_inputs():
    paths = [ML0 / "lp_hnew_all_candidates_unified.csv", ML0 / "lp_hnew_b240_b300_diagnosis.csv", ML0 / "lp_h500_450nm_single_point_seed_library.csv", ML0 / "lp_ml0_audit_summary.json"]
    if not all(p.exists() for p in paths):
        import subprocess
        subprocess.run([r"N:\anaconda_envs\RCP_LCP\python.exe", str(ROOT / "scripts/lp_ml0/lp_ml0_existing_data_audit.py")], cwd=ROOT, check=True)
    return read_csv(paths[0]), read_csv(paths[1]), read_csv(paths[2]), json.loads(paths[3].read_text(encoding="utf-8"))

def pools(diag, seeds):
    b300 = [r for r in diag if r.get("diagnosis_bucket", "").startswith("b300_candidates:projector_good_phase_wrong")]
    b300 += [r for r in diag if r.get("diagnosis_bucket", "").startswith("b300") and (fnum(r.get("phase_error_deg")) or 999) <= 35]
    b240 = [r for r in diag if "b240_candidates:phase_near_projector_bad" in r.get("diagnosis_bucket", "") or "b240_candidates:projector_good_phase_wrong" in r.get("diagnosis_bucket", "")]
    return {"B300_focused": b300 or [r for r in diag if r.get("target_bin_deg") == "300"], "B240_focused": b240 or [r for r in diag if r.get("target_bin_deg") == "240"], "H500_450nm_seed_robustification": seeds, "global_escape": diag + seeds}

def height_picker():
    rem = dict(HEIGHT_TARGETS)
    def pick(group):
        if group == "H500_450nm_seed_robustification": rem[500] -= 1; return 500
        choices = [h for h, n in rem.items() if n > 0]
        h = max(choices, key=lambda x: rem[x]) if choices else 500
        rem[h] -= 1
        return h
    return pick

def geometry(rng, group, i):
    ranges = {
        "B300_focused": (range(170,331,10), range(80,151,10), [-20,-15,-10,-5,5,10,15,20], [-30,-20,-10,10,20,30]),
        "B240_focused": (range(160,311,10), range(80,151,10), [-15,-10,-5,5,10,15], [-20,-10,10,20]),
        "H500_450nm_seed_robustification": (range(150,291,10), range(80,141,10), [-10,-5,0,5,10], [-10,0,10]),
        "global_escape": (range(130,341,10), range(70,171,10), list(range(-30,31,5)), list(range(-30,31,10))),
    }[group]
    lr, wr, td, gd = ranges
    t1 = (i * 17 + rng.choice(td)) % 180
    t2 = (t1 + rng.choice([0,45,90,135])) % 180
    return {"L1_nm": rng.choice(list(lr)), "W1_nm": rng.choice(list(wr)), "theta1_deg": t1, "L2_nm": rng.choice(list(lr)), "W2_nm": rng.choice(list(wr)), "theta2_deg": t2, "gap_or_dx_nm": max(20, min(120, 60 + rng.choice(gd) + (i % 3) * 2))}

def valid(g):
    dims = [g[k] for k in ["L1_nm","W1_nm","L2_nm","W2_nm"]]
    if min(dims) < 40: return False, "min_feature_below_40nm"
    if max(dims) > 360: return False, "max_feature_above_360nm"
    if g["gap_or_dx_nm"] < 20: return False, "minimum_gap_below_20nm_no_overlap"
    return True, ""

def score(group, diag, dup, g):
    base = {"B300_focused":400, "B240_focused":300, "H500_450nm_seed_robustification":200, "global_escape":100}[group]
    if "projector_good_phase_wrong" in diag: base += 40
    if "phase_near_projector_bad" in diag or "loose" in diag: base += 30
    base -= sum(1 for k in ["L1_nm","W1_nm","L2_nm","W2_nm"] if g[k] <= 50 or g[k] >= 340) * 5
    if dup: base -= 20
    return round(base, 3)

def make_manifest(poolmap):
    rng = random.Random(SEED); pick_h = height_picker(); rows=[]; rejects=[]; seen={}; seq=0
    for group, count in GROUP_TARGETS.items():
        pool = poolmap.get(group) or [{}]
        for i in range(count):
            src = pool[i % len(pool)]; h = 500 if group == "H500_450nm_seed_robustification" else pick_h(group)
            target = int(fnum(src.get("target_bin_deg")) or fnum(src.get("nearest_bin_deg")) or ([0,60,120,180,240,300][i%6]))
            if group == "B300_focused": target = 300
            if group == "B240_focused": target = 240
            g = geometry(rng, group, i); ok, reason = valid(g)
            if not all(src.get(k) for k in ["L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg"]):
                rejects.append({"source_candidate_id": src.get("candidate_id", ""), "sampling_group": group, "reject_reason": "source_geometry_missing_used_metadata_only_not_numeric_perturbation"})
            key = (h,target,g["L1_nm"],g["W1_nm"],g["theta1_deg"],g["L2_nm"],g["W2_nm"],g["theta2_deg"],g["gap_or_dx_nm"])
            dup = key in seen; seen[key] = seen.get(key, 0) + 1
            if not ok: rejects.append({"source_candidate_id": src.get("candidate_id", ""), "sampling_group": group, "reject_reason": reason}); continue
            s1,c1=trig(g["theta1_deg"]); s2,c2=trig(g["theta2_deg"]); diag=src.get("diagnosis_bucket") or src.get("strict_or_loose_or_fail") or "project_default_source"; seq += 1
            row = {"candidate_id": f"LPML1A_{seq:04d}_{group}_B{target}_H{h}", "target_bin_deg": target, "sampling_group": group, "source_candidate_id": src.get("candidate_id", ""), "source_stage": src.get("source_stage", "lp_ml0"), "source_diagnosis_category": diag, "H_nm": h, **g, "theta1_sin2": s1, "theta1_cos2": c1, "theta2_sin2": s2, "theta2_cos2": c2, "intended_lambda_min_nm": 450, "intended_lambda_max_nm": 454, "intended_lambda_points": 9, "intended_wavelengths_nm": WAVES, "run_policy": RUN_POLICY, "prepared_not_run": "true", "geometry_valid": "true", "geometry_reject_reason": "", "duplicate_group_id": f"DUP{seen[key]:03d}" if dup else "", "priority_score": score(group, diag, dup, g), "notes": "manifest_only_project_default_geometry; future Jones extraction must use complex fields, not intensity-only farfield3d"}
            rows.append({c: row.get(c, "") for c in COLUMNS})
    return sorted(rows, key=lambda r: (-float(r["priority_score"]), r["candidate_id"]))[:600], rejects

def md_table(rows, cols, n):
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"]*len(cols)) + " |"]
    for r in rows[:n]: lines.append("| " + " | ".join(str(r.get(c,"")) for c in cols) + " |")
    return "\n".join(lines)

def write_rules(unified):
    complete = sum(1 for r in unified if all(r.get(k) for k in ["L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg"]))
    RULES.parent.mkdir(parents=True, exist_ok=True)
    RULES.write_text(f"""# LP-ML1A geometry legality rules. Manifest-only; no FDTD.
range_sources:
  L1_nm: project_default
  W1_nm: project_default
  L2_nm: project_default
  W2_nm: project_default
  gap_or_dx_nm: observed_data_quantile_when_available_else_project_default
  observed_complete_geometry_rows: {complete}
min_feature_size_rule: minimum pillar dimension >= 40 nm
max_feature_size_rule: maximum pillar dimension <= 360 nm
minimum_gap_no_overlap_rule: minimum gap >= 20 nm; no-overlap required before LP-ML1B
angle_periodicity_rule: theta encoded by sin(2theta), cos(2theta); theta modulo 180 deg
H_allowed_set: [500, 600, 650, 700]
duplicate_tolerance_rule: exact rounded geometry duplicates are penalized by priority_score and tagged by duplicate_group_id
fabrication_caution_notes:
  - Project-default geometry is a dry-run scaffold, not fabrication approval.
  - Future Jones/phase extraction must use complex fields, not intensity-only farfield3d phase.
  - Use farfieldvector3d, farfieldpolar3d, or equivalent complex-field monitor data.
  - LP-ML1B is normal-incidence periodic plane-wave dimer simulation only.
  - Later angled validation requires Bloch/BFAST, not plain periodic.
  - Batch Lumerical script calls through lumapi.eval where appropriate.
""", encoding="utf-8")

def write_report(rows, rejects, summary):
    top = ["candidate_id","target_bin_deg","sampling_group","H_nm","source_candidate_id","source_diagnosis_category","priority_score"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join([
        "# LP-ML1A Seed Manifest Dry-Run", "", "Purpose: generate a seed full-wave candidate manifest and geometry legality dry-run for future LP-ML1B data generation.", "", "Baseline: LP-ML0 pushed at 604c38b Stage LP-ML0 existing data audit and schema freeze.", "", "Input files used:", "- outputs/lp_ml0_existing_data_audit/lp_hnew_all_candidates_unified.csv", "- outputs/lp_ml0_existing_data_audit/lp_hnew_b240_b300_diagnosis.csv", "- outputs/lp_ml0_existing_data_audit/lp_h500_450nm_single_point_seed_library.csv", "- outputs/lp_ml0_existing_data_audit/lp_ml0_audit_summary.json", "", f"Generated candidates: {len(rows)}", f"Rejected/source-metadata-only records: {len(rejects)}", "", "## Count by target bin", "```json\n" + json.dumps(summary["count_by_target_bin"], indent=2, sort_keys=True) + "\n```", "## Count by sampling group", "```json\n" + json.dumps(summary["count_by_sampling_group"], indent=2, sort_keys=True) + "\n```", "## Count by H_nm", "```json\n" + json.dumps(summary["count_by_H_nm"], indent=2, sort_keys=True) + "\n```", "## Count by source diagnosis category", "```json\n" + json.dumps(summary["count_by_source_diagnosis_category"], indent=2, sort_keys=True) + "\n```", "## Geometry Missingness Summary", "LP-ML0 source rows have sparse L/W/theta fields. Rows with missing source geometry were used as metadata anchors only; project_default geometry ranges were used explicitly and documented in reports/lp_ml1a_geometry_rules.yaml.", "", "## Top 20 Highest-Priority Candidates", md_table(rows, top, 20), "", "## Why B300 Receives More Samples Than B240", "B300 is the unresolved phase/projector decoupling bottleneck, so it receives 240 candidates. B240 has partial loose evidence and receives 180 focused candidates.", "", "## Priority Score", "base(B300=400, B240=300, H500 seed=200, global=100) + source bonuses for projector-good/phase-wrong or phase-near evidence - fabrication-edge and duplicate penalties.", "", "No FDTD was run.", "No Lumerical GUI was opened.", "No model was trained.", "No K=6 was attempted.", "", "Next recommended step: LP-ML1B full-wave runner planning, not execution."])+"\n", encoding="utf-8")

def main():
    unified, diag, seeds, ml0 = load_inputs(); poolmap = pools(diag, seeds); rows, rejects = make_manifest(poolmap); OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT/"lp_ml1a_seed_manifest.csv", rows, COLUMNS)
    write_csv(OUT/"lp_ml1a_rejected_candidates.csv", rejects, ["source_candidate_id","sampling_group","reject_reason"])
    write_csv(OUT/"lp_ml1a_sampling_sources.csv", [{"sampling_group":k,"source_rows":len(v)} for k,v in poolmap.items()], ["sampling_group","source_rows"])
    summary = {"candidate_count": len(rows), "rejected_candidate_count": len(rejects), "count_by_sampling_group": dict(sorted(Counter(r["sampling_group"] for r in rows).items())), "count_by_H_nm": dict(sorted(Counter(str(r["H_nm"]) for r in rows).items())), "count_by_target_bin": dict(sorted(Counter(str(r["target_bin_deg"]) for r in rows).items())), "count_by_source_diagnosis_category": dict(sorted(Counter(r["source_diagnosis_category"] for r in rows).items())), "lp_ml0_summary_total_candidates": ml0.get("total_candidate_count"), "prepared_not_run": True, "no_fdtd_run": True}
    (OUT/"lp_ml1a_seed_manifest_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    write_rules(unified); write_report(rows, rejects, summary); print(json.dumps(summary, sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
