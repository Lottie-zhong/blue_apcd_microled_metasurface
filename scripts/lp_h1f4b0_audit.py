import csv, hashlib, json
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
REPORT=ROOT/'reports'/'stage_h1f4b0_secondary_compensator_grammar_audit'
REPORT.mkdir(parents=True,exist_ok=True)
REPS=ROOT/'reports'

def load(rel): return json.load(open(REPS/rel,encoding='utf-8-sig'))
def sha(rel): return hashlib.sha256((REPS/rel).read_bytes()).hexdigest()
def rows(rel): return sum(1 for _ in open(REPS/rel,encoding='utf-8-sig'))-1

sources={
 'h1e1_final':'stage_h1e1_j1_anisotropy/h1e1_final.json',
 'h1e2_route':'stage_h1e2_j1_anisotropy_attribution/h1e2_route_decision.json',
 'h1e2_child':'stage_h1e2_j1_anisotropy_attribution/h1e2_child_audit.json',
 'h1e2_sixbin':'stage_h1e2_j1_anisotropy_attribution/h1e2_sixbin_attribution.json',
 'h1e3a_route':'stage_h1e3a_j1_rotation_audit/h1e3a_route_decision.json',
 'h1e3a_risk':'stage_h1e3a_j1_rotation_audit/h1e3a_rotation_projector_risk.json',
 'h1e3b_route':'stage_h1e3b_j2_decoupling_audit/h1e3b_route_decision.json',
 'h1e3c_final':'stage_h1e3c_j2_decoupling_probe/h1e3c_final.json',
 'h1f3a_final':'stage_h1f3a_k6_level2_grammar_audit/h1f3a_final.json',
 'h1f3a_global_h':'stage_h1f3a_k6_level2_grammar_audit/h1f3a_global_h_k6_audit.json',
 'h1f3a_compare':'stage_h1f3a_k6_level2_grammar_audit/h1f3a_route_comparison.json',
 'h1f3b_final':'stage_h1f3b_k6_position_mode_level2/h1f3b_final.json',
 'h1f3b_transfer':'stage_h1f3b_k6_position_mode_level2/h1f3b_seed_transferability.json',
 'h1f3c1_summary':'stage_h1f3c1_helper_current_formal_revalidation/helper_current_formal_summary.json',
 'h1f3c1_results':'stage_h1f3c1_helper_current_formal_revalidation/execution_results.json',
 'h1f4a_transfer':'stage_h1f4a_phase2_grouped_d_transfer_validation/h1f4a_phase2_transfer_analysis.json',
 'h1f4a_rule':'stage_h1f4a_phase2_grouped_d_transfer_validation/H1F4A_PHASE2_DIRECTION_RULE_V1.json',
 'k6_registry':'stage_h1f3c_k6_complex_lever_audit/K6_FULLWAVE_EVIDENCE_REGISTRY.csv',
}
hashes={k:{'path':v,'sha256':sha(v)} for k,v in sources.items()}
hashes['k6_registry']['row_count']=rows(sources['k6_registry'])

evidence=[
 {'candidate':'J1 independent anisotropy','evidence_stage':'H1E1/H1E2','geometry_scope':'local dimer; J1 length/width differential','material_wavelength':'Native-M1, 450-454 nm local full-Jones evidence','evidence_class':'LOCAL_CURRENT_FORMAL','xy_full_jones':'partial H1E1 bank; accepted children include strict 9/9 H1E2 child','broadband_support':'strict child exists; other children center-only/inconsistent','projector_selectivity':'can improve projector error in selected local child; not uniform','phase_common_response':'mixed local empirical slopes; not formal full-K6 Jacobian','cross_pol_effect':'not established as full-K6 repair','spectral_stability':'weak/mixed; H1E2 strict child spectral spread up to 91.42 deg','fabrication_legality':'existing legal local grammar','full_k6_tested':False,'redundant_with_grouped_d':'LOW; anisotropy/Jones-balance role is orthogonal','transferability':'not yet demonstrated on K6','provenance_quality':'current-formal local artifacts; incomplete H1E1 coverage'},
 {'candidate':'J2 shape anisotropy direction','evidence_stage':'H1E3B/H1E3C','geometry_scope':'local dimer J2 shape/orientation grammar','material_wavelength':'Native-M1, 450-454 nm local full-Jones evidence','evidence_class':'LOCAL_CURRENT_FORMAL','xy_full_jones':'H1E3C 8 complete children/16 accepted subruns','broadband_support':'5 strict children; 3 non-strict','projector_selectivity':'tradeoff_improves=false; selectivity breaks','phase_common_response':'phase lever observed','cross_pol_effect':'selectivity degradation risk','spectral_stability':'phase-order crossing at 450.5-454.0 nm','fabrication_legality':'current grammar legal','full_k6_tested':False,'redundant_with_grouped_d':'MEDIUM/HIGH; phase-like response overlaps grouped-D','transferability':'not established on K6','provenance_quality':'strong local current-formal, but negative physics outcome'},
 {'candidate':'J2 orientation-position decoupling','evidence_stage':'H1E3C','geometry_scope':'local dimer; theta_J2=Psi+delta_theta','material_wavelength':'Native-M1, 450-454 nm','evidence_class':'LOCAL_CURRENT_FORMAL','xy_full_jones':'yes; 16 accepted subruns, 8 complete children','broadband_support':'5/8 strict','projector_selectivity':'explicitly breaks selectivity; tradeoff does not improve','phase_common_response':'yes, but not clean compensator','cross_pol_effect':'harmful/selectivity degrading','spectral_stability':'crossing observed over most grid','fabrication_legality':'current H550 grammar compatible','full_k6_tested':False,'redundant_with_grouped_d':'HIGH; phase response overlaps grouped-D','transferability':'not established on K6','provenance_quality':'strong local full-Jones negative evidence'},
 {'candidate':'J1 rotation','evidence_stage':'H1E3A','geometry_scope':'local dimer rotation audit','material_wavelength':'derived from existing local Jones/proxy evidence','evidence_class':'LOCAL_CURRENT_FORMAL','xy_full_jones':'audit/proxy; no new solver probe approved','broadband_support':'not a stable projector-preserving result','projector_selectivity':'PROJECTOR_MIXING_DOMINANT_FIRST_ORDER','phase_common_response':'false at first order','cross_pol_effect':'dominant risk','spectral_stability':'risk inherited from H1E1','fabrication_legality':'geometrically possible but not selected','full_k6_tested':False,'redundant_with_grouped_d':'MEDIUM; not a clean D duplicate','transferability':'not demonstrated','provenance_quality':'formal audit, zero new solver; probe explicitly rejected'},
 {'candidate':'whole-dimer position first harmonic','evidence_stage':'H1F3B','geometry_scope':'full K6 six-site position mode','material_wavelength':'Native-M1, 450-454 nm full-K6','evidence_class':'FULL_K6_CURRENT_FORMAL','xy_full_jones':'yes; 8/8 accepted','broadband_support':'weak for both selected seeds','projector_selectivity':'low-to-medium risk, but leverage weak','phase_common_response':'weak full-K6 response','cross_pol_effect':'not useful repair demonstrated','spectral_stability':'weak transferability','fabrication_legality':'PASS exact polygon envelope','full_k6_tested':True,'redundant_with_grouped_d':'MEDIUM/HIGH; spacing/structure-factor role','transferability':'WEAK_FOR_BOTH','provenance_quality':'strong full-K6 current-formal'},
 {'candidate':'helper/J3','evidence_stage':'H1F3C0/H1F3C1','geometry_scope':'local trimer/helper','material_wavelength':'Native-M1, 450-454 nm current formal local','evidence_class':'LOCAL_CURRENT_FORMAL','xy_full_jones':'yes; 2 accepted cases','broadband_support':'projector pass 6/9','projector_selectivity':'DEGRADED_PROJECTOR_6_OF_9','phase_common_response':'helper response not cleanly transferable','cross_pol_effect':'projector degradation','spectral_stability':'not sufficient','fabrication_legality':'current helper geometry audit passed','full_k6_tested':False,'redundant_with_grouped_d':'LOW/MEDIUM but damaging','transferability':'not transferable proof','provenance_quality':'current formal local, negative revalidation'},
 {'candidate':'global H','evidence_stage':'H1A/H1F3A','geometry_scope':'shared global H operating-manifold selector','material_wavelength':'local H grid 400/450/500/550/600 nm evidence','evidence_class':'LOCAL_CURRENT_FORMAL','xy_full_jones':'local/global-H audit, not current full-K6 grouped-D','broadband_support':'H600 compatible span 5.51 deg; H550 30.10 deg','projector_selectivity':'operating-point selector, not direct repair','phase_common_response':'can alter collective sensitivity; not a six-site phase knob','cross_pol_effect':'not established','spectral_stability':'H600 narrow compatible span; H550 broader span','fabrication_legality':'shared H grammar compatible; no per-site modulation','full_k6_tested':False,'redundant_with_grouped_d':'LOW as role; complementary selector, not compensator','transferability':'not established full-K6','provenance_quality':'zero-solver local audit; GLOBAL_H_REVISIT_VALUE=MEDIUM'},
 {'candidate':'grouped-D first harmonic','evidence_stage':'H1F4A','geometry_scope':'full K6 six-site D harmonic','material_wavelength':'Native-M1, 450-454 nm full-K6','evidence_class':'FULL_K6_CURRENT_FORMAL','xy_full_jones':'yes; Phase-1 8/8 and Transfer 4/4','broadband_support':'partial transfer; eta_x,+1 sign unstable','projector_selectivity':'primary steering lever; y-pol cost','phase_common_response':'real target-order leverage','cross_pol_effect':'eta_y,+1 increases under transfer','spectral_stability':'partial/unstable','fabrication_legality':'PASS','full_k6_tested':True,'redundant_with_grouped_d':'PRIMARY itself','transferability':'PARTIAL','provenance_quality':'strong full-K6 current-formal'},
]
with open(REPORT/'candidate_evidence_table.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(evidence[0])); w.writeheader(); w.writerows(evidence)

gh=load(sources['h1f3a_global_h'])
route={
 'schema':'H1F4B0_ROUTE_DECISION_V1','stage':'H1F-4B0','status':'PASS_ZERO_SOLVER_AUDIT','solver_entered_delta':0,'ml_admitted':False,
 'primary_route':'GROUPED_D_PLUS_J1_ANISOTROPY_COMPENSATOR_PROBE_READY','backup_route':{'route':'GLOBAL_H_GROUPED_D_MANIFOLD_REVISIT_READY','priority':'SECONDARY_BACKUP','reason':'global-H is a medium-value operating-manifold selector, not a demonstrated projector repair'},
 'ordered_gate_decision':{
   'gate_1_evidence_legitimacy':'PASS_WITH_LOCAL_SCOPE; J1 anisotropy has current-formal broadband local evidence but no full-K6 proof',
   'gate_2_projector_behavior':'BEST_AVAILABLE_LOCAL_COMPENSATOR SIGNAL; selected strict child is 9/9, but nonuniform',
   'gate_3_spectral_stability':'DEGRADED; mixed local spectral response, so next probe must use minimal amplitude and full broadband evaluator',
   'gate_4_grouped_d_orthogonality':'PASS; J1 anisotropy changes constituent Jones balance rather than six-site D phase/spacing',
   'gate_5_fabrication':'PASS_EXISTING_H550_GRAMMAR',
   'gate_6_evidence_strength':'J1 is below full-K6 but stronger and more orthogonal as compensator than J2 decoupling or rotation'
 },
 'rejected_or_deprioritized':{
   'J2_decoupling':'reject as primary: J2_DECOUPLING_PHASE_LEVER_BREAKS_SELECTIVITY, tradeoff_improves=false',
   'J1_rotation':'reject: PROJECTOR_MIXING_DOMINANT_FIRST_ORDER, probe_approved=false',
   'position':'reject as compensator: full-K6 response weak for both seeds',
   'helper':'reject: projector degraded 6/9',
   'global_H':'backup selector only: GLOBAL_H_REVISIT_VALUE_MEDIUM'
 },
 'proposed_next_solver_probe':{
   'solver_authorized_now':False,'maximum_cases_if_approved':4,'design':'one full-K6 seed x J1 anisotropy PLUS/MINUS x X/Y',
   'seed_uid':'K6_L1_C_POS_PLUS10','seed_hash':'a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198',
   'perturbation':'J1_length=J1_side+delta_nm; J1_width=J1_side-delta_nm, applied symmetrically as PLUS/MINUS around frozen seed local J1 geometry',
   'amplitude_nm':2.0,'amplitude_basis':'smallest existing H1E1 legal differential sample; do not extrapolate beyond legality',
   'expected_observable':'full-K6 x/y broadband Jones: eta_x,+1, eta_y,+1, eta_x,0, eta_x,-1, projector error, cross leakage, closure',
   'decision_rule':'ordered gates; no weighted composite; test whether J1 perturbation reduces y/projector cost without relying on post-hoc target improvement',
   'serial_order':['J1_ANISO_PLUS_X','J1_ANISO_PLUS_Y','J1_ANISO_MINUS_X','J1_ANISO_MINUS_Y'],'no_replay':True,'fresh_concurrency_audit':True
 },
 'global_h_revisit':{'value':gh['verdict'],'H_grid_nm':gh['H_grid_nm'],'H550_projector_compatible_span_deg':gh['H550_projector_compatible_span_deg'],'H600_projector_compatible_span_deg':gh['H600_projector_compatible_span_deg'],'interpretation':'selector of operating manifold; not per-site phase knob and not yet full-K6 proof'},
 'source_hashes':hashes,'historical_phase2_audit_preserved':str(REPS/'stage_h1f4a_phase2_grouped_d_transfer_validation/phase2_direction_zero_solver_audit.json')
}
with open(REPORT/'h1f4b0_route_decision.json','w',encoding='utf-8') as f: json.dump(route,f,indent=2)
with open(REPORT/'h1f4b0_evidence_inventory.json','w',encoding='utf-8') as f: json.dump({'schema':'H1F4B0_EVIDENCE_INVENTORY_V1','sources':hashes,'registry':{'K6_fullwave_registry_rows':hashes['k6_registry']['row_count'],'ml_admitted':False,'local_registry_rows_from_H1E3C':578,'local_registry_not_extended':True},'evidence_classes':['LEGACY','LOCAL_CURRENT_FORMAL','FULL_K6_CURRENT_FORMAL']},f,indent=2)
with open(REPORT/'h1f4b0_global_h_revisit.json','w',encoding='utf-8') as f: json.dump(route['global_h_revisit'],f,indent=2)
with open(REPORT/'h1f4b0_proposed_next_solver_design.json','w',encoding='utf-8') as f: json.dump(route['proposed_next_solver_probe'],f,indent=2)
with open(REPORT/'h1f4b0_summary.md','w',encoding='utf-8') as f:
 f.write('# H1F-4B0 secondary compensator grammar audit\n\n')
 f.write('- Status: `PASS_ZERO_SOLVER_AUDIT`\n- Primary route: `GROUPED_D_PLUS_J1_ANISOTROPY_COMPENSATOR_PROBE_READY`\n- Backup: `GLOBAL_H_GROUPED_D_MANIFOLD_REVISIT_READY`\n- `solver_entered_delta=0`; `ml_admitted=false`.\n\n')
 f.write('J2 decoupling is deprioritized because its authoritative full-Jones local probe reports `J2_DECOUPLING_PHASE_LEVER_BREAKS_SELECTIVITY` and `tradeoff_improves=false`. J1 rotation is projector-mixing dominant. Position is weak on full K6. Helper is projector-degraded. Global H is retained only as a medium-value operating-manifold selector.\n\n')
 f.write('The proposed next probe is not executed: one full-K6 seed (`K6_L1_C_POS_PLUS10`) with J1 length/width differential ±2 nm, X/Y serial, maximum 4 cases.\n')
print(json.dumps({'primary_route':route['primary_route'],'backup':route['backup_route'],'solver_entered_delta':0,'global_h':route['global_h_revisit']},indent=2))
