"""H1F-0 zero-solver local-dimer route closure.

This module only reads accepted reports and performs deterministic offline
analysis.  It deliberately has no runtime or training dependencies.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUT = REPORTS / "stage_h1f0_lp_route_closure"
SCOPE = "CURRENT_H550_LOCAL_DIMER_GRAMMAR_PHASE_LEVERAGE_INSUFFICIENT"
WAVELENGTHS = [450.0 + 0.5 * i for i in range(9)]


def read_json(relative: str):
    return json.loads((REPORTS / relative).read_text(encoding="utf-8-sig"))


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def old_and_new_strict_bank():
    old = read_json("stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json")
    updated = read_json("stage_h1e3c_j2_decoupling_probe/h1e3c_strict_bank_updated.json")
    by_id = {g["geometry_uid"]: dict(g) for g in old["geometries"]}
    for g in updated["geometries"]:
        if g["geometry_uid"] not in by_id:
            by_id[g["geometry_uid"]] = dict(g)
    return old, updated, [by_id[k] for k in sorted(by_id)]


def strict_bank_summary():
    old, updated, geometries = old_and_new_strict_bank()
    assert len(geometries) == 12
    phase_trajectories = [p for g in geometries for p in g.get("phase_trajectory_deg", [])]
    old_metrics = []
    for g in old["geometries"]:
        old_metrics.append({
            "geometry_uid": g["geometry_uid"],
            "exact_hash": g["exact_hash"],
            "source": "H1C1B1_STRICT_BANK",
            "minimum_projector_margin": g["minimum_projector_margin"],
            "minimum_throughput": g["minimum_throughput"],
            "worst_projector_error": g["worst_projector_error"],
            "phase_trajectory_deg": [t["phi_deg"] for t in g["trajectory"]],
            "coordinates_5d": g.get("coordinates_5d"),
        })
    old_by_id = {g["geometry_uid"]: g for g in old_metrics}
    rows = []
    for g in geometries:
        if g["geometry_uid"] in old_by_id:
            rows.append(old_by_id[g["geometry_uid"]])
        else:
            rows.append({
                "geometry_uid": g["geometry_uid"],
                "exact_hash": None,
                "source": "H1E3C_STRICT_BANK_UPDATED",
                "minimum_projector_margin": 1.0 - g["worst_projector_error"],
                "minimum_throughput": g["min_throughput"],
                "median_projector_error": g["median_projector_error"],
                "median_throughput": g["median_throughput"],
                "worst_projector_error": g["worst_projector_error"],
                "phase_trajectory_deg": g["phase_trajectory_deg"],
                "parent_uid": g.get("parent_uid"),
                "mode": g.get("mode"),
            })
    old_coords = [g["coordinates_5d"] for g in old["geometries"]]
    coordinate_ranges = {}
    for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"):
        values = [float(c[key]) for c in old_coords]
        coordinate_ranges[key] = {"min": min(values), "max": max(values), "span": max(values) - min(values)}
    selected_phase = updated["coverage_after"]
    return {
        "schema": "H1F0_STRICT_BANK_SUMMARY_V1",
        "source_old": "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json",
        "source_updated": "reports/stage_h1e3c_j2_decoupling_probe/h1e3c_strict_bank_updated.json",
        "old_strict_count": old["count"],
        "new_strict_count": updated["new_strict_count"],
        "strict_count": len(rows),
        "wavelength_grid_nm": WAVELENGTHS,
        "selected_phase_coverage": selected_phase,
        "phase_trajectory_distribution": {
            "trajectory_count": len(rows),
            "sample_count": len(phase_trajectories),
            "raw_min_deg": min(phase_trajectories),
            "raw_max_deg": max(phase_trajectories),
            "raw_span_deg": max(phase_trajectories) - min(phase_trajectories),
            "per_geometry_mean_deg": {g["geometry_uid"]: sum(g["phase_trajectory_deg"]) / len(g["phase_trajectory_deg"]) for g in rows},
            "per_geometry_span_deg": {g["geometry_uid"]: max(g["phase_trajectory_deg"]) - min(g["phase_trajectory_deg"]) for g in rows},
        },
        "projector_margin_distribution": {
            "minimum_margin_by_geometry": {g["geometry_uid"]: g["minimum_projector_margin"] for g in rows},
            "min": min(g["minimum_projector_margin"] for g in rows),
            "median": median(g["minimum_projector_margin"] for g in rows),
            "max": max(g["minimum_projector_margin"] for g in rows),
        },
        "throughput_distribution": {
            "minimum_by_geometry": {g["geometry_uid"]: g["minimum_throughput"] for g in rows},
            "min": min(g["minimum_throughput"] for g in rows),
            "median": median(g["minimum_throughput"] for g in rows),
            "max": max(g["minimum_throughput"] for g in rows),
        },
        "geometry_space_diversity": {
            "explicit_5d_coordinate_records": len(old_coords),
            "coordinate_ranges_old_bank": coordinate_ranges,
            "new_child_count_with_parent_mode_labels": updated["new_strict_count"],
            "distinct_parent_uids_new_children": sorted({g.get("parent_uid") for g in updated["geometries"] if g.get("parent_uid")}),
            "distinct_new_modes": sorted({g.get("mode") for g in updated["geometries"] if g.get("mode")}),
            "interpretation": "12 distinct geometry UIDs occupy a narrow selected optical phase arc; coordinate diversity is fully explicit for the seven historical parents and mode/parent diversity is explicit for five H1E3C children.",
            "label": "GEOMETRIC_DIVERSITY_WITH_OPTICAL_PHASE_CLUSTERING",
        },
        "rows": rows,
        "registry_rows_total_if_extended": read_json("stage_h1e3c_j2_decoupling_probe/h1e3c_final.json")["registry_rows_total_if_extended"],
    }


def evidence_chain():
    a = read_json("stage_h1a_global_h/stage_h1a_global_h_final.json")
    b1 = read_json("stage_h1b1_global_h/h1b1_final.json")
    b3 = read_json("stage_h1b3_global_h/h1b3_final.json")
    c1a = read_json("stage_h1c1a_broadband_global/h1c1a_final.json")
    c1b0 = read_json("stage_h1c1b0_broadband_attribution/h1c1b0_authoritative_snapshot.json")
    c1b1 = read_json("stage_h1c1b1_sixbin_closure/h1c1b1_phase_coverage.json")
    c1c = read_json("stage_h1c1c_phase_gap/h1c1c_final.json")
    d1 = read_json("stage_h1d1_detour_feasibility/h1d1_final.json")
    d2 = read_json("stage_h1d2_structure_factor_forensic/h1d2_route_decision.json")
    e1 = read_json("stage_h1e1_j1_anisotropy/h1e1_final.json")
    e2 = read_json("stage_h1e2_j1_anisotropy_attribution/h1e2_route_decision.json")
    e3a = read_json("stage_h1e3a_j1_rotation_audit/h1e3a_route_decision.json")
    e3b = read_json("stage_h1e3b_j2_decoupling_audit/h1e3b_route_decision.json")
    e3c = read_json("stage_h1e3c_j2_decoupling_probe/h1e3c_final.json")
    b3span = b3["span_comparison"]["new_merged_H550_projector_compatible_span_deg"]
    rows = [
        {"stage":"H1A","new_physical_lever":"shared global H, geometry-dependent response","strict_yield":"not broadband strict; 3/6 H550 anchor projector-compatible slice","strict_phase_coverage_deg":44.844205999649034,"six_bin_error":"not evaluated as a strict bank","main_conclusion":a["verdict"]},
        {"stage":"H1B","new_physical_lever":"H550 local dimer refinement / lateral grammar","strict_yield":f"H1B1 {b1['solver_accounting']['solver_subruns_accepted']} accepted; H1B2/H1B3 each 10 accepted; strict bank not yet closed","strict_phase_coverage_deg":b3span,"six_bin_error":"below 60-degree target; H1B1/B2/B3 remain sub-60","main_conclusion":"successive span expansion, still below six-phase reachability"},
        {"stage":"H1C","new_physical_lever":"broadband strict projector-compatible screening and gap closure","strict_yield":f"H1C1A {c1a['strict_candidate_count']}/24; H1C1B0 {c1b0['status_counts']['BROADBAND_PROJECTOR_COMPATIBLE_STRICT']}/21; final bank 7","strict_phase_coverage_deg":32.207338325516275,"six_bin_error":"H1C1B1 clustered; H1C1C no new strict region","main_conclusion":c1c["physics_outcome"]},
        {"stage":"H1D","new_physical_lever":"K6 positional detour / primitive-period test","strict_yield":f"{d1['accepted_formal_cases']} coupled cases accepted; no new local strict geometry","strict_phase_coverage_deg":0.0,"six_bin_error":"not a local six-bin result; pure detour full-wave unsupported","main_conclusion":d2["dominant_failure_mechanism"]},
        {"stage":"H1E1","new_physical_lever":"independent J1 anisotropy","strict_yield":f"{e1['new_strict_children']} new strict children; {e1['complete_full_jones_children']}/{e1['planned_geometries']} complete full-Jones children","strict_phase_coverage_deg":e1['coverage_after']['coverage_deg'],"six_bin_error":164.83274477479677,"main_conclusion":e2["physics_classification"]},
        {"stage":"H1E3A","new_physical_lever":"J1 rotation audit","strict_yield":"zero new solver; no accepted new strict bank","strict_phase_coverage_deg":35.65331618996703,"six_bin_error":164.83274477479677,"main_conclusion":e3a["j1_rotation_classification"]},
        {"stage":"H1E3B","new_physical_lever":"J2 anisotropy / orientation-displacement coupling audit","strict_yield":"zero new solver; route selection only","strict_phase_coverage_deg":32.207338325516275,"six_bin_error":165.14025291649796,"main_conclusion":"J2 anisotropy is existing DOF; decouple orientation from displacement as final local probe"},
        {"stage":"H1E3C","new_physical_lever":"independent J2 orientation-displacement decoupling","strict_yield":f"{e3c['new_strict_children']} new strict children; {e3c['accepted_formal_subruns']}/{e3c['planned_formal_subruns']} accepted","strict_phase_coverage_deg":e3c['coverage_after']['coverage_deg'],"six_bin_error":164.77205884862167,"main_conclusion":e3c["physics_outcome"]},
    ]
    return {"schema":"H1F0_LOCAL_DIMER_EVIDENCE_CHAIN_V1","scope":SCOPE,"wavelength_grid_nm":WAVELENGTHS,"formal_compatibility":"9/9 projector-compatible broadband acceptance where labelled strict","rows":rows,"selectivity_vs_reachability":{"broadband_selectivity_achievement":"supported: strict 9/9 projector-compatible trajectories exist; final strict bank has 12 geometries after H1E3C","broadband_six_phase_reachability":"insufficient: selected circular coverage remains 32.207338325516275 deg and worst six-bin error 164.77205884862167 deg","interpretation":"selectivity is a successful constraint to preserve; six-bin synthesis is not achieved"}}


def global_h_audit():
    b0 = read_json("stage_h1b0_global_h/h1b0_fixed_h_ranking.json")
    per = b0["per_H"]
    table = []
    for h in (400.0,450.0,500.0,550.0,600.0):
        x = per[str(h)]
        table.append({"H_global_nm":h,"raw_span_deg":x["raw_anchor_circular_phase_span_deg"],"projector_compatible_span_deg":x["dedicated_projector_compatible_circular_phase_span_deg"],"max_abs_residual_deg":x["max_abs_residual_deg"],"rms_residual_deg":x["rms_residual_deg"]})
    return {"schema":"H1F0_GLOBAL_H_REVISIT_AUDIT_V1","source":"reports/stage_h1b0_global_h/h1b0_fixed_h_ranking.json","H_grid_nm":[400,450,500,550,600],"table":table,"H550_supporting_evidence":{"projector_compatible_span_deg":per["550.0"]["dedicated_projector_compatible_circular_phase_span_deg"],"ranking_primary":b0["ranking"]["PRIMARY_H_CANDIDATE"],"leave_one_out_survives":b0["leave_one_anchor_out"]["primary_survives_all_single_anchor_removals"]},"sparse_H_uncertainty":{"sample_count":5,"spacing_nm":50,"geometry_dependent_response":True,"interpolation_local_neighborhood_physically_plausible":True,"proof_of_new_broadband_phase_region":False,"basis":"H1A/H1B0 provides geometry-dependent residuals and nonmonotonic spans, but no dense neighborhood or new strict broadband phase region outside the H550 cluster"},"GLOBAL_H_REVISIT_VALUE":"MEDIUM","decision_role":"worth a final probe only if it is cheaper and more decisive than direct coupled K6; it is not the primary recommendation"}


def metamolecule_options():
    return {"schema":"H1F0_METAMOLECULE_EXTENSION_OPTIONS_V1","scope":"architecture-level extension, not another scalar parameter in the same rectangular dimer","options":[{"id":"B1_TRIMER","architecture":"third same-layer local scatterer / trimer","phase_degrees_of_freedom":"additional resonant amplitude, phase and coupling path","projector_preservation":"must be constrained with full Jones Px checks; risk higher than dimer","fabrication_complexity":"medium-high","solver_dimensionality":"high","reuse_578_rows":"strict dimer parents can seed two sites; no labels for the third-site coupling","APCD_logic":"compatible with parallel scatterers if same-layer and independently legal","recommendation":"not automatic; requires a geometry contract"},{"id":"B2_NONRECTANGULAR","architecture":"non-rectangular same-layer pillar shape","phase_degrees_of_freedom":"shape resonances and anisotropic scattering","projector_preservation":"unknown until full Jones evidence","fabrication_complexity":"medium-high","solver_dimensionality":"high","reuse_578_rows":"geometry legality and strict dimer phase data remain useful as baselines only","APCD_logic":"potentially compatible, but physical scattering interpretation changes","recommendation":"not automatic"},{"id":"B3_EXTRA_RESONANT","architecture":"additional same-layer local resonant element","phase_degrees_of_freedom":"new local resonance and controlled mutual coupling","projector_preservation":"must be treated as a new metamolecule contract","fabrication_complexity":"high","solver_dimensionality":"very high","reuse_578_rows":"use strict parents for initialization, not as coupled labels","APCD_logic":"possible but requires explicit parallel-scatterer and fabrication audit","recommendation":"not automatic"}],"assessment":"Route B can add genuine architecture-level leverage, but it introduces more physical and fabrication complexity than the demonstrated bottleneck requires; no option is selected here."}


def full_k6_audit():
    return {"schema":"H1F0_FULL_K6_ROUTE_AUDIT_V1","motivation":"H1D showed naive additive/detour reasoning can fail after actual supercell symmetry and primitive-period recovery; direct order-level coupling is the demonstrated bottleneck","six_bin_local_phase_library":"strategy_or_initialization_not_Maxwell_requirement","parameterizations":[{"id":"K6-A","description":"one or few strict dimer parent types plus small legal grouped position adjustments","free_variables":"site assignment groups plus bounded positions","dimensionality":"low","risk":"may under-explore local diversity but is decisive and interpretable"},{"id":"K6-B","description":"six site-specific selections from strict/near-strict bank plus constrained position freedom","free_variables":"6 discrete parent choices plus grouped legal displacements","dimensionality":"medium","risk":"larger combinatorial space; preserves bank legality"},{"id":"K6-C","description":"low-dimensional perturbations around current strict dimers with one shared/grouped coupling control","free_variables":"few continuous perturbations and grouped positions","dimensionality":"medium","risk":"new local perturbation legality must be audited"}],"primary_objectives":["broadband eta_x,+1(lambda)","broadband suppression eta_y,+1(lambda)","fabrication legality"],"diagnostic_metrics":["eta_x,0(lambda)","eta_x,-1(lambda)","other propagating-order leakage","polarization contrast","spectral robustness over 450-454 nm"],"full_jones_requirement":"x and y source subruns are required before final polarization-selectivity acceptance; x-first can only be a resource triage screen and cannot create a final label","coupling_aware_advantages":["neighbor coupling","collective supercell modes","amplitude redistribution","multiple scattering","nonlocal phase compensation","order-level interference"],"risks":["large search space","high 3D broadband FDTD cost","nonconvexity","local phase loses standalone interpretability","fabrication sensitivity","surrogate/active-learning/adjoint infrastructure may be needed later"],"existing_method_reuse":["12 strict dimer parents after H1E3C","geometry legality constraints","full Jones projector evidence","phase trajectories","H=550 evidence","versioned 578-row registry with ml_admitted=false"],"method_comparison":[{"method":"deterministic coarse search","fit":"best first decisive small batch","cost":"bounded","interpretability":"high","role":"first level-0 screen"},{"method":"active learning","fit":"later after coupled labels exist","cost":"medium","interpretability":"medium","role":"adaptive expansion after a seed set"},{"method":"evolutionary optimization","fit":"nonconvex mixed discrete/continuous K6","cost":"very high","interpretability":"low","role":"not first step"},{"method":"adjoint optimization","fit":"continuous geometry after a legal seed","cost":"high per setup, efficient gradients","interpretability":"medium","role":"later refinement"},{"method":"coupling-aware forward surrogate plus search","fit":"later when coupled labels accumulate","cost":"high upfront","interpretability":"medium","role":"second phase, not before labels"}],"workflow_recommendation":"deterministic small K6 seed batch -> full x/y order-resolved validation of any survivor -> only then active learning or adjoint refinement"}


def registry_audit():
    p = REPORTS / "stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv"
    with p.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    ml_values = sorted({str(r.get("ml_admitted", "")).lower() for r in rows})
    e3c = read_json("stage_h1e3c_j2_decoupling_probe/h1e3c_registry_audit.json")
    final = read_json("stage_h1e3c_j2_decoupling_probe/h1e3c_final.json")
    return {"schema":"H1F0_ML_ROLE_AUDIT_V1","canonical_registry_path":str(p.relative_to(ROOT)),"canonical_registry_rows":len(rows),"canonical_registry_sha256":sha256(p),"canonical_registry_ml_admitted_values":ml_values,"canonical_registry_unchanged":e3c["canonical_registry_unchanged"],"versioned_local_dimer_rows":final["registry_rows_total_if_extended"],"versioned_accounting":"506 prior versioned rows + 72 accepted H1E3C rows = 578","ml_admitted":False,"ml_roles":{"local_dimer_forward_model":"potentially useful after explicit admission; no training performed","K6_constituent_screening":"useful as legal strict/near-strict seed bank","coupled_K6_model":"not valid from local-dimer rows alone because they contain no coupled-supercell labels"},"training_performed":False}


def route_comparison():
    return {"schema":"H1F0_ROUTE_COMPARISON_V1","scoring":"qualitative evidence matrix; no arbitrary weighted score","routes":{"GLOBAL_H_REVISIT":{"physical_leverage":"medium; H550 has best sampled compatible span but sparse 50-nm grid","broadband_selectivity_risk":"medium; H changes can perturb projector and dispersion","directional_plus1":"indirect; still needs K6 coupling validation","new_solver_cost":"small final H probe, then full broadband strict validation","new_dimensionality":"one shared fabrication parameter","reuse_578_rows":"high for anchors, not coupled labels","fabrication_complexity":"low; unchanged architecture","interpretability":"high","time_to_decisive_result":"medium"},"LOCAL_METAMOLECULE_ARCHITECTURE_EXTENSION":{"physical_leverage":"potentially high but unmeasured","broadband_selectivity_risk":"high until full Jones evidence","directional_plus1":"indirect; architecture must still be embedded in a coupled supercell","new_solver_cost":"high","new_dimensionality":"high","reuse_578_rows":"seed/baseline only","fabrication_complexity":"medium-high to high","interpretability":"medium","time_to_decisive_result":"long"},"COUPLING_AWARE_FULL_K6_OPTIMIZATION":{"physical_leverage":"directly attacks order-level coupling bottleneck","broadband_selectivity_risk":"medium; strict dimer parents preserve a tested broadband mechanism, but coupling can break it","directional_plus1":"direct objective","new_solver_cost":"high but can be bounded by a small decisive batch","new_dimensionality":"low-medium with grouped parameters","reuse_578_rows":"high as seed bank and legality evidence, not K6 labels","fabrication_complexity":"unchanged if same-layer dimer K6 grammar is retained","interpretability":"medium-high for constrained K6","time_to_decisive_result":"shortest path to testing whether coupling provides new leverage"}},"decision":"COUPLING_AWARE_FULL_K6_FIRST","rationale":"directly tests the demonstrated order-level bottleneck while preserving the successful strict broadband dimer mechanism and avoiding an unmeasured architecture expansion"}


def proposed_next_stage():
    return {"schema":"H1F0_PROPOSED_NEXT_STAGE_V1","status":"PROPOSED_ONLY_NO_EXECUTION","stage":"LP_K6_COUPLING_AWARE_LEVEL0_DESIGN","seed_bank":"12 authoritative H1E3C strict geometries; use strict parents as seeds, not an exact six-bin requirement","candidates":{"K6-A":4,"K6-B":4,"K6-C":2},"selection":"prepare a small deterministic candidate manifest; execute only the smallest decisive subset after a future admission decision","budget":{"x_pol_prescreen_candidates":4,"y_pol_completion_max":2,"maximum_fdt_cases_if_staged":6,"formal_full_acceptance":"x+y required; no x-only candidate can be accepted as polarization-selective","wavelengths_nm":WAVELENGTHS,"new_solver_runs_proposed_only":6,"solver_entered_now":0},"metrics":{"primary":["eta_x,+1","eta_y,+1 suppression","fabrication legality"],"diagnostic":["eta_x,0","eta_x,-1","other propagating leakage","polarization contrast","broadband robustness"]},"stop_go":{"go":"at least one x+y-complete candidate shows reproducible broadband +1 redistribution and a measurable improvement over the identical-dimer/detour baseline while remaining fabrication-legal","stop":"no candidate exceeds the baseline on order-level redistribution, or all survivors lose strict broadband Px compatibility, or legality fails","not_required_at_level0":"final device performance and six isolated 60-degree phase bins"},"scheduler":"preserve solver-type-aware accounting, MAX_ACTIVE_FDTD_PER_BRANCH=1, global validated FDTD concurrency=2, and entered=true no-replay"}


def main():
    chain = evidence_chain(); bank = strict_bank_summary(); gh = global_h_audit(); b = metamolecule_options(); k6 = full_k6_audit(); ml = registry_audit(); comparison = route_comparison(); proposed = proposed_next_stage()
    scheduler = read_json("global_scheduler_recovery/global_scheduler_recovery_final.json")
    route_decision = {"schema":"H1F0_ROUTE_DECISION_V1","scope":SCOPE,"recommendation":"COUPLING_AWARE_FULL_K6_FIRST","GLOBAL_H_REVISIT_VALUE":gh["GLOBAL_H_REVISIT_VALUE"],"decision_basis":comparison["rationale"],"isolated_six_bin_library_mandatory":False,"hard_gates":[],"execution_guard":{"new_fdtd_runs":0,"new_rcwa_runs":0,"new_ml_training_runs":0,"new_inverse_runs":0,"new_k6_full_wave_runs":0,"solver_entered_delta":0},"scheduler":{"active_fdtd_jobs":scheduler["active_fdtd_jobs"],"active_rcwa_jobs":scheduler["active_rcwa_jobs"],"unknown_solver_jobs":scheduler["unknown_solver_jobs"],"unresolved_entered_cases":scheduler["unresolved_entered_cases"],"classification":scheduler["classification"]}}
    for name, value in [("h1f0_local_dimer_evidence_chain.json",chain),("h1f0_strict_bank_summary.json",bank),("h1f0_global_h_revisit_audit.json",gh),("h1f0_metamolecule_extension_options.json",b),("h1f0_full_k6_route_audit.json",k6),("h1f0_ml_role_audit.json",ml),("h1f0_route_comparison.json",comparison),("h1f0_route_decision.json",route_decision), ("h1f0_proposed_next_stage.json",proposed)]: write_json(name,value)
    summary = f'''# H1F-0 LP local-dimer route closure

## Status

`PASS` — zero-solver offline closure.

## Scoped conclusion

`{SCOPE}`

Scope: shared H_global=550 nm, tested rectangular two-pillar dimer lateral/J1/J2/D/Psi grammar, J2 orientation-displacement decoupling, 450.0–454.0 nm at 0.5 nm, nine wavelengths, formal 9/9 projector-compatible strict trajectories. This is not a claim about all heights, shapes, dimers, metamolecules, or full supercells.

## Quantitative closure

- Strict bank: 7 historical + 5 H1E3C children = **12**.
- Selected strict phase coverage: **32.207338°**; largest circular gap **327.792662°**.
- H1E3C six-bin best: worst error **164.772059°**, RMS **99.959384°**; phase ordering crosses within the band.
- Broadband selectivity is demonstrated by strict 9/9 projector-compatible trajectories; six-phase reachability is not.
- Strict-bank geometry evidence supports `GEOMETRIC_DIVERSITY_WITH_OPTICAL_PHASE_CLUSTERING`.
- `GLOBAL_H_REVISIT_VALUE = MEDIUM`; H550 has the best sampled projector-compatible span (**30.096722°** in H1B0), but sparse H sampling does not prove a new region.

## Route decision

`COUPLING_AWARE_FULL_K6_FIRST`

Direct K6 order-resolved optimization attacks the H1D-demonstrated coupling/order bottleneck while retaining the tested strict broadband dimer bank. The isolated six-bin library remains a strategy/initialization method, not a Maxwell requirement.

## Proposed-only next stage

`LP_K6_COUPLING_AWARE_LEVEL0_DESIGN` — no execution. Use K6-A/B/C constrained seeds, with at most 4 x-pol prescreens and y-pol completion for up to 2 survivors; final acceptance requires x+y. Proposed maximum is 6 FDTD cases, solver-entered now is 0.

## Governance

The versioned local-dimer evidence count is **578** (506 prior + 72 H1E3C); the canonical registry is preserved unchanged and `ml_admitted=false`. No ML training and no K6 labels were fabricated.

## Scheduler

Current live accounting: FDTD={scheduler["active_fdtd_jobs"]}, RCWA={scheduler["active_rcwa_jobs"]}, UNKNOWN={len(scheduler["unknown_solver_jobs"])}; LP remains admissible because global FDTD occupancy is below 2 and LP active occupancy is 0.

See the companion JSON reports in this directory for source paths and deterministic fields.
'''
    OUT.mkdir(parents=True, exist_ok=True); (OUT/'h1f0_summary.md').write_text(summary, encoding='utf-8')
    print(json.dumps({"status":"PASS","scope":SCOPE,"strict_count":bank["strict_count"],"phase_coverage_deg":bank["selected_phase_coverage"]["coverage_deg"],"route":comparison["decision"],"solver_entered_delta":0}, indent=2))


if __name__ == "__main__": main()
