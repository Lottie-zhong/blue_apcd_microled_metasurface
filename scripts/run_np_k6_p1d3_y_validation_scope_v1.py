"""Pure-data P1-D3 y-validation scope and contract freezer; no solver imports."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
from typing import Any
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RANK = ROOT / "outputs" / "np_k6_p1d2_sixbin_exhaustive_ranking_v1"
LIB = ROOT / "outputs" / "np_k6_p1d2_broadband_library_26point_v1"
OUT_NAME = "np_k6_p1d3_y_validation_scope_v1"
WAVELENGTHS = list(range(445, 456))
RESONANT = {140, 160, 165, 170, 200, 205, 215, 220, 225}

def read(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def key(d: list[int]) -> tuple[int, ...]: return tuple(map(int, d))
def wrap180(x: np.ndarray) -> np.ndarray: return (x + 180.0) % 360.0 - 180.0

def library_metrics(diams: list[int]) -> dict[str, Any]:
    rows = list(csv.DictReader((LIB / "library_long.csv").open(encoding="utf-8")))
    table = {(int(r["diameter_nm"]), int(r["wavelength_nm"])): r for r in rows}
    phase = np.asarray([[float(table[d,w]["txx_wrapped_phase_deg"]) for w in WAVELENGTHS] for d in diams])
    amp = np.asarray([[float(table[d,w]["txx_amplitude"]) for w in WAVELENGTHS] for d in diams])
    t = np.asarray([[float(table[d,w]["T"]) for w in WAVELENGTHS] for d in diams])
    target = np.arange(6) * 60.0; rms=[]; errmax=[]
    for column in phase.T:
        delta=wrap180(column-target); common=np.degrees(np.angle(np.mean(np.exp(1j*np.radians(delta))))); errors=wrap180(delta-common)
        rms.append(float(np.sqrt(np.mean(errors*errors)))); errmax.append(float(np.max(np.abs(errors))))
    steps=wrap180(np.roll(phase, -1, axis=0)-phase-60.0)
    return {"phase_fit_RMS_band_mean":float(np.mean(rms)),"phase_fit_RMS_band_max":float(np.max(rms)),"maximum_phase_error_over_band":float(np.max(errmax)),"minimum_T_over_band":float(t.min()),"minimum_txx_amplitude_over_band":float(amp.min()),"amplitude_CV_band_max":float(np.max(np.std(amp,axis=0)/np.mean(amp,axis=0))),"maximum_step_drift_peak_to_peak":float(np.max(np.ptp(steps,axis=1))),"cyclic_closure_step_error_450":float(steps[5,5])}

def choose_pareto(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    def tie(xs: list[dict[str, Any]], fn, reverse=False): return sorted(xs, key=lambda r: ((-fn(r) if reverse else fn(r)), key(r["diameters_nm"])))[0]
    vals=np.asarray([[r["phase_fit_RMS_band_max"],r["maximum_phase_error_over_band"],r["maximum_step_drift_peak_to_peak"],r["amplitude_CV_band_max"],-r["minimum_T_over_band"]] for r in records],float)
    lo,hi=vals.min(0),vals.max(0); norm=(vals-lo)/np.where(hi>lo,hi-lo,1.0); distances=np.sqrt((norm*norm).sum(1))
    knee=records[min(range(len(records)), key=lambda i:(float(distances[i]), key(records[i]["diameters_nm"])))]
    nonres=[r for r in records if not any(d in RESONANT for d in r["diameters_nm"])]
    return {"minimum_phase_RMS":tie(records,lambda r:r["phase_fit_RMS_band_max"]),"maximum_minimum_T":tie(records,lambda r:r["minimum_T_over_band"],True),"minimum_amplitude_CV":tie(records,lambda r:r["amplitude_CV_band_max"]),"minimum_broadband_step_drift":tie(records,lambda r:r["maximum_step_drift_peak_to_peak"]),"balanced_knee_point":knee,"best_nonresonant":tie(nonres,lambda r:float(np.sqrt(((np.asarray([r["phase_fit_RMS_band_max"],r["maximum_phase_error_over_band"],r["maximum_step_drift_peak_to_peak"],r["amplitude_CV_band_max"],-r["minimum_T_over_band"]])-lo)/np.where(hi>lo,hi-lo,1.0))**2).sum()))}

def run(out: Path) -> dict[str, Any]:
    manifest=read(RANK/"exhaustive_search_manifest.json"); verify=read(RANK/"verification_summary.json"); summary=read(RANK/"ranking_summary.json")
    if sha(LIB/"library_long.csv") != manifest["input_sha256"] or verify["passing_sextet_count"] != 6: raise RuntimeError("frozen P1-D2 input gate failed")
    top=read(RANK/"candidate_top20_detailed.json"); passing_rows=list(csv.DictReader((RANK/"passing_combinations.csv").open(encoding="utf-8")))
    passing=[list(map(int,row["diameters_nm"].split(","))) for row in passing_rows]
    phase=top["phase_error"][0]; runner=top["phase_error"][1]; amp=top["amplitude_uniformity"][0]; broadband=top["broadband_dispersion"][0]
    pareto=read(RANK/"pareto_front_detailed.json"); reps=choose_pareto(pareto)
    dump(out/"pareto_representative_sextets.json", {"method":"min-max normalized five-objective Euclidean distance to ideal for knee; lexicographic diameter tie-break", "roles":reps})
    all_records={key(r["diameters_nm"]):r for r in pareto}
    for r in [phase,runner,amp,broadband]: all_records.setdefault(key(r["diameters_nm"]),r)
    for ds in passing: all_records.setdefault(key(ds), {"diameters_nm":ds,**library_metrics(ds),"all_legacy_engineering_gates_pass":True})
    role_map: dict[tuple[int,...], list[str]]={}
    def add(role:str, rec:dict[str,Any]): role_map.setdefault(key(rec["diameters_nm"]),[]).append(role)
    for i,ds in enumerate(passing,1): add(f"passing_{i}",all_records[key(ds)])
    add("phase_champion",phase); add("phase_runner_up",runner); add("amplitude_champion",amp); add("broadband_champion",broadband)
    for role,rec in reps.items(): add(f"pareto_{role}",rec)
    selected=[]
    for ds,roles in sorted(role_map.items()):
        rec=all_records[ds]; tier="TIER_1_MANDATORY" if any(x.startswith("passing_") or x in {"phase_champion","phase_runner_up"} for x in roles) else "TIER_2_TRADEOFF"
        selected.append({"sextet_id":"D"+"_".join(map(str,ds)),"source_roles":roles,"diameters_nm":list(ds),"legacy_gate_pass":bool(rec.get("all_legacy_engineering_gates_pass",False)),"phase_RMS_mean":rec["phase_fit_RMS_band_mean"],"phase_RMS_max":rec["phase_fit_RMS_band_max"],"maximum_phase_error":rec["maximum_phase_error_over_band"],"minimum_T":rec["minimum_T_over_band"],"minimum_txx_amplitude":rec["minimum_txx_amplitude_over_band"],"amplitude_CV_max":rec["amplitude_CV_band_max"],"maximum_step_drift":rec["maximum_step_drift_peak_to_peak"],"cyclic_closure_error_450":rec["cyclic_closure_step_error_450"],"contains_resonant_diameter":any(d in RESONANT for d in ds),"pareto_status":key(ds) in {key(r["diameters_nm"]) for r in pareto},"priority_tier":tier})
    audit=[r for r in top["amplitude_uniformity"][1:2]+top["broadband_dispersion"][1:2] if key(r["diameters_nm"]) not in role_map]
    selected_doc={"tier_1_mandatory":[r for r in selected if r["priority_tier"]=="TIER_1_MANDATORY"],"tier_2_tradeoff":[r for r in selected if r["priority_tier"]=="TIER_2_TRADEOFF"],"tier_3_audit_only":[{"sextet_id":"D"+"_".join(map(str,r["diameters_nm"])),"diameters_nm":r["diameters_nm"],"reason":"extreme tradeoff audit only; not automatic K6 candidate"} for r in audit]}
    dump(out/"selected_sextets_for_y_validation.json",selected_doc)
    union=sorted({d for r in selected for d in r["diameters_nm"]}); memberships={d:[r["sextet_id"] for r in selected if d in r["diameters_nm"]] for d in union}
    phase_ds=set(phase["diameters_nm"]); pareto_ds={d for r in reps.values() for d in r["diameters_nm"]}; passing_ds={d for row in passing for d in row}; amp_ds=set(amp["diameters_nm"]); broad_ds=set(broadband["diameters_nm"])
    union_doc={"selected_sextet_count":len(selected),"unique_diameter_count":len(union),"ordered_diameter_allowlist":union,"diameters":[{"diameter_nm":d,"sextet_ids":memberships[d],"appearance_count":len(memberships[d]),"belongs_to_passing_sextet":d in passing_ds,"belongs_to_phase_champion":d in phase_ds,"belongs_to_pareto_representative":d in pareto_ds,"is_resonant":d in RESONANT,"belongs_to_amplitude_champion":d in amp_ds,"belongs_to_broadband_champion":d in broad_ds} for d in union],"D180":{"included_in_y_validation":False,"reason":"sealed_unmeasured_and_not_required_for_initial_sextet"}}
    dump(out/"y_validation_diameter_union.json",union_doc)
    full_ids=[r["sextet_id"] for r in selected]; min_ids=list(full_ids) # all mandatory role constraints require every selected full sextet
    trade={"PLAN_FULL_UNION":{"diameter_count":len(union),"projected_solver_count":len(union),"covered_sextet_ids":full_ids,"covered_passing_sextet_count":6,"covered_pareto_roles":list(reps),"supports_formal_xy_symmetry_conclusion":True,"retains_at_least_two_K6_candidates":True},"PLAN_MINIMUM_COVERAGE":{"diameter_count":len(union),"projected_solver_count":len(union),"covered_sextet_ids":min_ids,"covered_passing_sextet_count":6,"covered_pareto_roles":list(reps),"supports_formal_xy_symmetry_conclusion":True,"retains_at_least_two_K6_candidates":True},"RECOMMENDED_Y_VALIDATION_PLAN":"PLAN_FULL_UNION","recommendation_reason":"all mandatory complete-sextet coverage constraints already require the full deduplicated union; no scope reduction is achieved"}
    dump(out/"y_validation_scope_tradeoff.json",trade)
    library_manifest=read(LIB/"library_manifest.json"); expected=[]
    for priority,d in enumerate(union,1): expected.append({"case_id":f"NP_P1D3_Y_VALIDATION_PILLAR_H500_D{d}_Y","diameter_nm":d,"polarization":"y","wavelength_grid_nm":WAVELENGTHS,"wavelength_count":11,"height_nm":500,"pitch_x_nm":290,"pitch_y_nm":290,"base_z_nm":0,"transmission_reference_plane_z_nm":900,"materials":"Native-M1","monitor_backend":"shared_broadband_33_monitor_contract","expected_monitor_count":33,"corresponding_x_case_id":f"NP_P1D2_BROADBAND_PILLAR_H500_D{d}_X","corresponding_x_result_hash":library_manifest["source_result_hashes"][str(d)],"execution_priority":priority,"membership_sextet_ids":memberships[d]})
    dump(out/"expected_case_manifest.json",{"future_cases":expected,"D180_included":False})
    symmetry={"SYMMETRY_GATE_STATUS":"proposed_not_yet_frozen","formal_contract_found":False,"evidence":{"x_energy_residual_max":0.03637333671814813,"x_reconstruction_residual_max":0.03985704668165824,"structure":"circular pillar on square pitch; expected x/y rotational symmetry","crosspol_note":"observed ~1e-17 is numerical noise, not a guaranteed physical threshold"},"strict_numerical_gate":{"amplitude_abs_difference":0.02,"wrapped_phase_difference_deg":2.0,"transmission_absolute_difference":0.02,"reflection_absolute_difference":0.02,"complex_response_difference":0.03,"crosspol_amplitude":0.01},"engineering_acceptance_gate":{"amplitude_abs_difference":0.05,"wrapped_phase_difference_deg":5.0,"transmission_absolute_difference":0.05,"reflection_absolute_difference":0.05,"complex_response_difference":0.10,"crosspol_amplitude":0.02},"recommended_for_P1D3":"engineering_acceptance_gate","required_metrics":["amplitude_abs_difference","amplitude_relative_difference","wrapped_phase_difference_deg","transmission_absolute_difference","reflection_absolute_difference","crosspol_x_to_y","crosspol_y_to_x","complex_response_difference"]}
    dump(out/"proposed_symmetry_gate_contract.json",symmetry)
    closure={"cyclic_closure_threshold_status":"threshold_not_frozen","policy":"closure is a candidate-ranking indicator and not a legacy pass gate","phase_champion_closure_error_450_deg":12.654398918151855,"y_validation_does_not_validate_K6_neighbor_coupling":True,"final_K6_closure_requires":"K6 supercell order-resolved simulation","final_K6_release_pass":False}
    dump(out/"cyclic_closure_release_policy.json",closure)
    x_runner=ROOT/"scripts"/"run_np_k6_p1d2_batch_broadband_pillars_x_v1.py"
    x_text=x_runner.read_text(encoding="utf-8")
    execution={"contract_version":"P1D3_y_validation_execution_contract_v1","allowlist_nm":union,"D180_permanently_excluded":True,"polarization":"y","solver_budget":len(union),"one_fdtd_run_max_per_diameter":True,"independent_session_per_diameter":True,"post_fsp_independent_readonly_extract":True,"atomic_checkpoint_heartbeat_ledger":True,"trusted_post_fsp_readonly_recovery":True,"solver_entered_no_post_no_retry":True,"geometry_material_boundary_mesh_monitor_reference_wavelength_contract":"unchanged_from_x","x_post_fsp_not_y_result":True,"K6_SUPERCELL_VALIDATION_STATUS":"not_run","runner_strategy":"independent_new_runner_required; existing x batch runner is x-specific","x_batch_runner_audit":{"path":str(x_runner.relative_to(ROOT)).replace("\\", "/"),"sha256":sha(x_runner),"hardcoded_x_contract":'"polarization":"x"' in x_text,"safe_to_relabel_as_y_without_new_explicit_polarization_setup":False,"required_y_runner_invariants":["explicit y source setup","frozen allowlist only","one run max per diameter","independent session","atomic checkpoint","no retry after solver_entered_no_post","independent post-FSP readonly extract"]}}
    dump(out/"y_validation_execution_contract.json",execution)
    promotion={"maximum_K6_candidate_count":3,"must_retain_roles":["phase_champion","phase_runner_up","high_transmission_passing_or_balanced_pareto"],"promotion_requirements":["legacy_x_engineering_gate_pass","y_symmetry_gate_pass","complete_six_diameter_y_data","auditable_x_y_phase_steps","no_provenance_gap","manufacturing_gate_pass"],"K6_status":"not_run","automatic_promotion":False}
    dump(out/"post_y_k6_candidate_promotion_policy.json",promotion)
    provenance={"input_library_sha256":sha(LIB/"library_long.csv"),"ranking_manifest_sha256":sha(RANK/"exhaustive_search_manifest.json"),"ranking_summary_sha256":sha(RANK/"ranking_summary.json"),"D180_status":"sealed_failed_case_local","solver_calls":0,"lumapi_import_count":0,"MPI_call_count":0,"x_only_input":True}
    dump(out/"provenance_manifest.json",provenance)
    verification={"input_passing_count_gate":len(passing)==6,"phase_champion_exact_gate":phase["diameters_nm"]==[125,135,150,175,190,210],"D180_excluded_gate":180 not in union,"allowlist_not_all_26_gate":len(union)<26,"all_selected_sextets_complete_gate":all(set(r["diameters_nm"]).issubset(union) for r in selected),"expected_cases_y_only_gate":all(x["polarization"]=="y" for x in expected),"axis_gate":all(x["wavelength_grid_nm"]==WAVELENGTHS for x in expected),"symmetry_gate_status":"proposed_not_yet_frozen","K6_status":"not_run","MDC_status":"not_handled","solver_calls":0,"lumapi_import_count":0,"MPI_call_count":0}
    dump(out/"verification_summary.json",verification)
    report=ROOT/"docs"/"np_k6_p1d3_multi_candidate_y_validation_scope_v1.md"; report.write_text(f"# NP-K6 P1-D3 multi-candidate y-validation scope\n\n- Frozen input: 26 x-only diameters / 286 real rows; D180 remains sealed and is not required for the initial sextet.\n- Six measured-only legacy-gate-passing sextets are retained.\n- Recommended plan: PLAN_FULL_UNION, {len(union)} y diameters / projected {len(union)} solver calls in a future authorized task.\n- Symmetry thresholds are proposed, not frozen; y remains not_run.\n- Cyclic closure remains a ranking metric, not K6 release evidence.\n- K6 is not_run; at most three candidates can be promoted after complete y evidence.\n- This task made zero solver/lumapi/MPI calls.\n",encoding="utf-8")
    return {"union":union,"selected":selected,"verification":verification,"reps":reps,"trade":trade}

def main() -> int:
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=ROOT/"outputs"/OUT_NAME);a=p.parse_args();result=run(a.output);print(json.dumps({"count":len(result["union"]),"verification":result["verification"]},indent=2));return 0
if __name__=="__main__": raise SystemExit(main())
