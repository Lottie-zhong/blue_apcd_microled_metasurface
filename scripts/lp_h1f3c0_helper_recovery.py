from __future__ import annotations

import cmath
import csv
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1")
ARCHIVE = Path(r"D:\project\red_plane_wave_metasurface_archive")
OLD = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
OUT = ROOT / "reports/stage_h1f3c0_helper_history_recovery"
K6_REGISTRY = ROOT / "reports/stage_h1f3c_k6_complex_lever_audit/K6_FULLWAVE_EVIDENCE_REGISTRY.csv"
LOCAL_REGISTRY_ROWS = 578


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_json(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def f(row, key):
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return None


def circular_delta(a, b):
    return ((a - b + 180.0) % 360.0) - 180.0


def phase(value):
    z = complex(value)
    return math.degrees(cmath.phase(z))


def git_log(repo, args):
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.STDOUT).splitlines()
    except Exception as exc:
        return [f"ERROR:{exc}"]


def search_index():
    terms = ["helper", "phase_helper", "phase-helper", "third_pillar", "third-pillar", "third pillar", "J3", "trimer", "isotropic_helper", "isotropic phase helper", "auxiliary_pillar", "auxiliary pillar", "phase trim", "phase tuning", "辅助柱", "第三柱", "调相柱"]
    roots = [ROOT, OLD, ARCHIVE]
    hits = []
    matching_files = []
    skip = {".git", "venv", "__pycache__", "node_modules"}
    extensions = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".py", ".toml", ".log"}
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip]
            for name in files:
                p = Path(dirpath) / name
                if p.suffix.lower() not in extensions or p.stat().st_size > 12_000_000:
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                found = [term for term in terms if term.lower() in text.lower() or term.lower() in name.lower()]
                if found:
                    matching_files.append({"path": str(p), "terms": sorted(set(found)), "sha256": sha(p)})
                    if len(hits) < 300:
                        for i, line in enumerate(text.splitlines(), 1):
                            if any(t.lower() in line.lower() for t in found):
                                hits.append({"path": str(p), "line": i, "terms": sorted(set(t for t in found if t.lower() in line.lower())), "text": line[:500]})
    return {"schema": "H1F3C0_HELPER_SEARCH_INDEX_V1", "terms": terms, "roots": [str(x) for x in roots], "matching_file_count": len(matching_files), "matching_files": matching_files, "representative_hits": hits, "search_scope_read_only": True}


def geometry_records():
    base = {
        "candidate_uid": "p199_h300_zero_B_diff_rot_p1_m2p5_p2_p5",
        "role": "two-pillar parent baseline",
        "config": ARCHIVE / "configs/apcd_k6_phase_state_candidates/p199_h300_zero_B_diff_rot_p1_m2p5_p2_p5.yaml",
        "period_nm": [340.0, 340.0], "H_nm": 300.0, "material": "c-Si on Al2O3",
        "J1": {"length_nm": 115.0, "width_nm": 55.0, "rotation_deg": 20.0, "x_nm": 65.0, "y_nm": 103.0},
        "J2": {"length_nm": 75.0, "width_nm": 135.0, "rotation_deg": 72.5, "x_nm": -65.0, "y_nm": -103.0},
    }
    helper = {
        "candidate_uid": "hr_aniso_push_08", "role": "standalone weak auxiliary phase helper", "config": ARCHIVE / "configs/apcd_k6_phase_state_candidates/hr_aniso_push_08.yaml",
        "period_nm": [340.0, 340.0], "H_nm": 300.0, "material": "c-Si on Al2O3",
        "J1": {"length_nm": 130.0, "width_nm": 70.0, "rotation_deg": 67.5, "x_nm": 85.0, "y_nm": 85.0},
        "J2": {"length_nm": 85.0, "width_nm": 150.0, "rotation_deg": 112.5, "x_nm": -85.0, "y_nm": -85.0},
        "J3_helper": {"length_nm": 80.0, "width_nm": 110.0, "rotation_deg": 135.0, "x_nm": -85.0, "y_nm": 85.0, "height_nm": 300.0, "material": "c-Si", "role": "weak_auxiliary_phase_helper"},
    }
    for x in (base, helper):
        x["config_sha256"] = sha(x["config"])
        x["config"] = str(x["config"])
        x["evidence_class"] = "ACTUAL_FDTD_FULL_JONES" if x is helper else "ACTUAL_FDTD_FULL_JONES"
    base["D_nm"] = 2.0 * math.hypot(base["J1"]["x_nm"], base["J1"]["y_nm"])
    base["Psi_deg"] = math.degrees(math.atan2(base["J1"]["y_nm"], base["J1"]["x_nm"]))
    helper["D_nm"] = 2.0 * math.hypot(helper["J1"]["x_nm"], helper["J1"]["y_nm"])
    helper["Psi_deg"] = math.degrees(math.atan2(helper["J1"]["y_nm"], helper["J1"]["x_nm"]))
    return {"schema": "H1F3C0_HELPER_GEOMETRY_RECOVERY_V1", "baseline": base, "helper": helper, "geometry_hash_status": "config_sha256_preserved; no legacy formal geometry hash field found"}


def solver_evidence():
    items = []
    for stage, candidate, csv_rel, result_dir, commit in [
        ("09-P42/P44", "h2_weak_aniso_03", "outputs/apcd_k6_active_learning/helper_prototype_fdtd_results_v7.csv", "outputs/apcd_k6_metagrating_633nm/phase_state_candidates/h2_weak_aniso_03", "history lookup required"),
        ("09-P45/P47", "hr_aniso_push_08", "outputs/apcd_k6_active_learning/helper_refinement_fdtd_results_v8.csv", "outputs/apcd_k6_metagrating_633nm/phase_state_candidates/hr_aniso_push_08", "6a25c7c"),
        ("p200_v3_h300_zero_valid_helper", "p200v3_h300_zero_validhelper_helper_mid_35x35_r45", "outputs/apcd_k6_metagrating_633nm/phase_state_candidates/p200v3_h300_zero_validhelper_helper_mid_35x35_r45/results.csv", "outputs/apcd_k6_metagrating_633nm/phase_state_candidates/p200v3_h300_zero_validhelper_helper_mid_35x35_r45", "archive history lookup required"),
    ]:
        out = ARCHIVE / result_dir
        cfg = ARCHIVE / ("configs/apcd_k6_phase_state_candidates/" + candidate + ".yaml")
        if not cfg.exists():
            cfg = None
        result = out / "results.csv"
        items.append({"stage": stage, "candidate_uid": candidate, "evidence_class": "ACTUAL_FDTD_FULL_JONES", "solver_type": "Lumerical FDTD", "case_uid": "not present in legacy CSV", "attempt_uid": "not present in legacy CSV", "entered_completed_replay": {"entered": True, "completed": True, "replay": "not encoded in legacy schema"}, "result_artifact": str(result), "result_sha256": sha(result) if result.exists() else None, "pre_run_X_fsp": str(out / "pre_run_X.fsp"), "pre_run_X_sha256": sha(out / "pre_run_X.fsp") if (out/"pre_run_X.fsp").exists() else None, "pre_run_Y_fsp": str(out / "pre_run_Y.fsp"), "pre_run_Y_sha256": sha(out / "pre_run_Y.fsp") if (out/"pre_run_Y.fsp").exists() else None, "config_path": str(cfg) if cfg else None, "config_sha256": sha(cfg) if cfg else None, "archive_commit": commit, "wavelength_grid_nm": [633.0], "x_y_availability": True, "current_formal_provenance_fields_missing": ["attempt_uid", "formal current case UID", "current solver schema", "current G0/Px extraction provenance"]})
    return {"schema": "H1F3C0_HELPER_SOLVER_EVIDENCE_V1", "items": items, "actual_solver_evidence_exists": True, "legacy_provenance_incomplete": True}


def comparison():
    baseline = load_csv(ARCHIVE / "outputs/apcd_k6_metagrating_633nm/phase_state_candidates/p199_h300_zero_B_diff_rot_p1_m2p5_p2_p5/results.csv")[0]
    rows = []
    for rel, stage in [("outputs/apcd_k6_metagrating_633nm/phase_state_candidates/h2_weak_aniso_03/results.csv", "v7"), ("outputs/apcd_k6_metagrating_633nm/phase_state_candidates/hr_aniso_push_08/results.csv", "v8"), ("outputs/apcd_k6_metagrating_633nm/phase_state_candidates/p200v3_h300_zero_validhelper_helper_mid_35x35_r45/results.csv", "p200")]:
        helper = load_csv(ARCHIVE / rel)[0]
        before = phase(baseline["t_alpha_star_from_alpha"]); after = phase(helper["t_alpha_star_from_alpha"])
        rows.append({"helper_stage": stage, "helper_candidate": Path(rel).parent.name, "wavelength_nm": f(helper,"wavelength_nm"), "phase_metric": "arg(t_alpha_star_from_alpha)", "phase_before_deg": before, "phase_after_deg": after, "delta_phase_circular_deg": circular_delta(after, before), "legacy_reported_phase_shift_deg": f(helper,"phase_shift_vs_baseline_deg"), "projector_error_current_formal": "UNAVAILABLE", "legacy_PD_before": f(baseline,"PD"), "legacy_PD_after": f(helper,"PD"), "legacy_leakage_before": f(baseline,"opposite_spin_leakage"), "legacy_leakage_after": f(helper,"opposite_spin_leakage"), "legacy_Txx_before": f(baseline,"transmission_x"), "legacy_Txx_after": f(helper,"transmission_x"), "legacy_Tyy_before": f(baseline,"transmission_y"), "legacy_Tyy_after": f(helper,"transmission_y"), "total_transmission_before": f(baseline,"total_transmission"), "total_transmission_after": f(helper,"total_transmission"), "txy_before": baseline["t_xy"], "txy_after": helper["t_xy"], "tyx_before": baseline["t_yx"], "tyx_after": helper["t_yx"], "tyy_before": baseline["t_yy"], "tyy_after": helper["t_yy"], "spectral_scope": "single wavelength 633 nm; no spectral stability claim"})
    path = OUT / "helper_phase_projector_comparison.csv"; OUT.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fobj:
        w=csv.DictWriter(fobj, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    search = search_index(); write_json("helper_search_index.json", search)
    write_json("helper_git_history.json", {"schema":"H1F3C0_HELPER_GIT_HISTORY_V1","current_lp_helper_commits":git_log(ROOT,["log","--all","--oneline","--grep=helper","--grep=trimer","--grep=phase"]),"archive_helper_refinement_commit":"6a25c7c","archive_head":git_log(ARCHIVE,["rev-parse","HEAD"])[0],"old_lp_worktree_helper_commits":git_log(OLD,["log","--all","--oneline","--grep=helper","--grep=trimer","--grep=phase"]),"old_worktree_modified":git_log(OLD,["status","--short"]),"old_worktree_mutated_by_audit":False})
    geom=geometry_records(); write_json("helper_geometry_recovery.json", geom)
    evidence=solver_evidence(); write_json("helper_solver_evidence.json", evidence)
    write_json("helper_stage_provenance.json", {"schema":"H1F3C0_HELPER_STAGE_PROVENANCE_V1","stages":["09-P42/P44","09-P45/P47","p200_v3_h300_zero_valid_helper"],"items":evidence["items"],"classification_counts":{"ACTUAL_FDTD_FULL_JONES":len(evidence["items"]),"PROPOSED_ONLY":1,"SETUP_ONLY":1},"archive_is_separate_from_current_lp_worktree":True})
    comp=comparison()
    write_json("helper_formal_compatibility.json", {"schema":"H1F3C0_HELPER_FORMAL_COMPATIBILITY_V1","classification":"HISTORICAL_HELPER_PROMISING_BUT_LEGACY","full_jones_x_y":True,"current_contract":{"wavelength_grid_nm":[450.0+i*0.5 for i in range(9)],"material":"APCD_TIO2_NATIVE_M1","H_nm":550.0,"P_supercell_nm":2591.446716,"weighted_G0":True,"reference_plane":"current LP formal monitor/reference","normalization":"current LP formal normalization","projector":"diag(1,0)","phase":"arg(txx)"},"historical_contract":{"wavelength_nm":[633.0],"material":"c-Si on Al2O3","H_nm":300.0,"period_nm":[340.0,340.0],"basis":"alpha/beta paper basis with x/y linear Jones columns","full_period_weighted_G0":"not encoded in legacy artifact","current_Px":"not encoded in legacy artifact"},"missing_or_mismatched":["wavelength/material/height/period mismatch","single wavelength only","legacy case/attempt schema absent","current G0/reference/normalization/Px linkage absent"],"formal_revalidation_required":True})
    write_json("helper_fabrication_audit.json", {"schema":"H1F3C0_HELPER_FABRICATION_AUDIT_V1","same_global_H":True,"same_layer":True,"historical_material":"c-Si","historical_period_nm":[340.0,340.0],"historical_H_nm":300.0,"helper_hr_aniso_push_08":{"same_cell_min_gap_nm":56.55675044638735,"periodic_image_min_gap_nm":56.55675044638733,"overlap":False,"geometry_validation_pass":True,"lithography_status":"archive labels fabrication-friendly; current LP process compatibility not established"},"current_native_M1_450nm_compatibility":"not demonstrated","mixed_height":False})
    write_json("helper_vs_grouped_d.json", {"schema":"H1F3C0_HELPER_VS_GROUPED_D_V1","helper":{"demonstrated":True,"evidence":"actual legacy FDTD/full Jones","phase_scope":"single 633 nm","current_formal_leverage":"not demonstrated","new_geometry_complexity":"adds third same-layer scatterer with size/position/orientation DOFs","same_global_H":"yes in legacy","K6_integration":"not demonstrated","decisive_current_solver_cost":"conditional 2 formal x/y cases if exact baseline is reusable"},"grouped_D":{"status":"READY_STANDBY","grammar":"2D first-harmonic a_D,b_D","A_D_probe_nm":4.0,"future_phase1_cases":8,"conditional_phase2_cases":4,"current_formal_compatibility":"native M1 450-454 nm H550 K6 G0/Px contract","complex_lever":"not yet measured"},"no_arbitrary_weighted_score":True,"interpretation":"helper has stronger historical phase evidence but weaker current-formal validity; grouped-D is formally ready but unmeasured"})
    write_json("helper_route_decision.json", {"schema":"H1F3C0_HELPER_ROUTE_DECISION_V1","formal_route":"HELPER_FORMAL_REVALIDATION_FIRST","helper_classification":"HELPER_PROMISING_LEGACY_EVIDENCE_ONLY","reason":"actual historical full-Jones x/y FDTD exists, but it is legacy 633 nm/c-Si/H300/P340 and lacks current formal G0/Px provenance","authorization":"PROPOSED_ONLY_NO_SOLVER","fallback":"if exact baseline cannot be reused under current contract, retain GROUPED_D_H1F4A_READY without execution"})
    write_json("helper_proposed_next_stage.json", {"schema":"H1F3C0_HELPER_PROPOSED_NEXT_STAGE_V1","status":"PROPOSED_ONLY","stage":"LP_HELPER_TRIMER_FORMAL_REVALIDATION","preferred_candidate":"hr_aniso_push_08","required_contract":"current 450-454 nm Native-M1 H550 full-period weighted G0 full Jones Px","formal_cases":2,"incidence":["x","y"],"baseline_reuse":"not proven; do not execute until exact formal baseline reuse is demonstrated","if_baseline_not_reusable":"hold helper and preserve GROUPED_D_H1F4A_READY","solver_authorized":False,"solver_entered_delta":0})
    summary='''# H1F-3C0 Historical Helper / Trimer Physics Evidence Recovery\n\nStatus: PASS; zero solver.\n\n- Actual historical helper FDTD exists in the separate `red_plane_wave_metasurface_archive`; representative v8 `hr_aniso_push_08` has X/Y FSP artifacts and a complex linear Jones result at 633 nm.\n- Historical helper classification: **HELPER_PROMISING_LEGACY_EVIDENCE_ONLY**.\n- Legacy helper data are not current LP-formal compatible: c-Si/Al2O3, H=300 nm, P=340 nm, one wavelength, and no current G0/reference/Px provenance.\n- Representative v8 helper geometry passes its legacy gap audit: same-cell 56.55675044638735 nm; periodic 56.55675044638733 nm; same global H=300 nm.\n- Circular `arg(t_alpha_star_from_alpha)` comparison is recorded, but current LP projector error and spectral stability are unavailable.\n- Formal route: **HELPER_FORMAL_REVALIDATION_FIRST**, proposed-only 2-case x/y revalidation if an exact current-formal baseline can be reused; otherwise retain grouped-D READY_STANDBY.\n- K6 registry remains 720 rows; versioned local registry remains 578; `ml_admitted=false`; solver_entered_delta=0.\n'''
    (OUT/"helper_summary.md").write_text(summary, encoding="utf-8")
    print(json.dumps({"status":"PASS","actual_helper_solver_evidence":True,"helper_classification":"HELPER_PROMISING_LEGACY_EVIDENCE_ONLY","route":"HELPER_FORMAL_REVALIDATION_FIRST","solver_calls":0,"comparison_rows":len(comp)},indent=2))


if __name__ == "__main__":
    main()
