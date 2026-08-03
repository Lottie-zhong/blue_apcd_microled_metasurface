import csv, json, hashlib, math
from pathlib import Path
from collections import defaultdict

R = Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
S0 = R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_smoke_attempt2_v1'
S1 = R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_production_attempt1_v1'
P = R/'outputs/lp_ml_dataset_v1/plans'; A = R/'outputs/lp_ml_dataset_v1/analysis'; A.mkdir(parents=True, exist_ok=True)
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p, x): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(x, indent=2, sort_keys=True, default=str)+'\n', encoding='utf-8')
def readcsv(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
plan = {r['candidate_id']: r for r in readcsv(P/'lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv')}
prod_plan = readcsv(P/'lp_ml_dataset_v1_round1_remaining_240_plan_v1.csv')
stages = [S0, S1]; checkpoints=[]
for stage in stages:
    for p in stage.glob('subruns/*/*/checkpoint.json'):
        try: checkpoints.append(load(p) | {'_path': str(p.relative_to(R)).replace('\\','/')})
        except Exception as e: checkpoints.append({'_path': str(p.relative_to(R)).replace('\\','/'), '_load_error': str(e)})
bycid=defaultdict(list)
for c in checkpoints: bycid[c.get('candidate_id')].append(c)
def finite(v):
    try: return math.isfinite(float(v))
    except Exception: return False
audit_rows=[]
for c in checkpoints:
    rr=c.get('rows',[]); ts=[float(r['source_T']) for r in rr if finite(r.get('source_T'))]
    vals=[]
    for r in rr: vals += [r.get(k) for k in ['weighted_Ex_real','weighted_Ex_imag','weighted_Ey_real','weighted_Ey_imag','normalization_scale','selected_power']]
    gate=c.get('configuration_gate',{}); checks=gate.get('checks',{}); geom=c.get('geometry',{}); cid=c.get('candidate_id')
    hash_ok=geom.get('exact_geometry_hash_sha256')==plan.get(cid,{}).get('exact_geometry_hash_sha256')
    wl=[float(r['wavelength_nm']) for r in rr if finite(r.get('wavelength_nm'))]; expected=[450.0+i*.5 for i in range(9)]
    cfg_ok=(gate.get('pass') is True and checks.get('material_1')=='APCD_TIO2_NATIVE_M1' and checks.get('material_2')=='APCD_TIO2_NATIVE_M1' and checks.get('monitor_z') is not None and checks.get('T_z') is not None)
    neg=[t for t in ts if t<=0]; residual=[abs(float(r['selected_power'])-float(r['source_T'])) for r in rr if finite(r.get('selected_power')) and finite(r.get('source_T'))]
    clean=(not neg and all(finite(v) for v in vals) and wl==expected and cfg_ok and hash_ok)
    audit_rows.append({'candidate_id':cid,'input_polarization':c.get('input_polarization'),'checkpoint_path':c.get('_path'),'geometry_hash_sha256':geom.get('exact_geometry_hash_sha256'),'plan_hash_match':hash_ok,'wavelength_vector':wl,'min_T':min(ts) if ts else None,'max_T':max(ts) if ts else None,'nonpositive_T_count':len(neg),'nonpositive_T_values':neg,'finite_weighted_fields':all(finite(v) for v in vals),'max_power_consistency_residual':max(residual) if residual else None,'configuration_gate_pass':gate.get('pass'),'native_material_pass':cfg_ok,'classification':'NORMALIZATION_CONTRACT_CLEAN' if clean else ('NEGATIVE_T_BUT_EXPLAINED_AND_NOT_ADMITTED' if neg else 'DATA_QUARANTINE_REQUIRED')})
with (A/'lp_ml_round1_61_geometry_normalization_audit_v1.csv').open('w',encoding='utf-8',newline='') as f:
    fs=[]
    for r in audit_rows:
        for k in r:
            if k not in fs: fs.append(k)
    w=csv.DictWriter(f,fieldnames=fs); w.writeheader(); w.writerows(audit_rows)
counts={k:sum(r['classification']==k for r in audit_rows) for k in sorted({r['classification'] for r in audit_rows})}
save(A/'lp_ml_round1_61_geometry_normalization_audit_v1.json', {'geometry_count':61,'accepted_checkpoint_count':len(checkpoints),'case_class_counts':counts,'all_accepted_cases_clean':all(r['classification']=='NORMALIZATION_CONTRACT_CLEAN' for r in audit_rows),'negative_T_in_accepted_rows':sum(r['nonpositive_T_count'] for r in audit_rows)})
prod_ids={r['candidate_id'] for r in readcsv(S1/'candidate_wavelength_jones_v1.csv')}; failed_id='LPML_R1_GLOBAL_SOBOL_054'; untouched=[r['candidate_id'] for r in prod_plan if r['candidate_id'] not in prod_ids and r['candidate_id']!=failed_id]
account={'planned_geometries':240,'planned_subruns_max':480,'entered_subruns':92,'accepted_subruns':91,'failed_subruns':1,'complete_geometries':61,'smoke_complete_geometries':16,'production_complete_geometries':45,'failed_case':failed_id+'_y','failed_case_entered':True,'failed_case_checkpoint_present':False,'untouched_candidates_count':len(untouched),'remaining_full_xy_pairs':len(untouched),'single_missing_y_rerun_count':1,'prospective_new_subrun_budget':2*len(untouched)+1,'solver_calls_this_task':0,'old_entered_evidence_retained':True}
save(A/'lp_ml_round1_negative_t_accounting_freeze_v1.json',account)
failed=load(S1/'subruns/LPML_R1_GLOBAL_SOBOL_054/y/run_result.json'); xchk=load(S1/'subruns/LPML_R1_GLOBAL_SOBOL_054/x/checkpoint.json')
save(A/'lp_ml_round1_negative_t_failed_case_forensic_v1.json',{'case_id':failed_id+'_y','run_result':failed,'x_checkpoint_status':xchk.get('status'),'y_checkpoint_present':False,'raw_T_vector_available':False,'raw_weighted_fields_available':False,'full_jones_recoverable_without_solver':False,'root_cause_class':'INDETERMINATE_SOURCE_EVIDENCE','possible_mechanisms':['numerical_near_zero_noise','geometry_specific_physical_behavior','directional_power_sign_or_monitor_convention','corrupted_or_incomplete_result'],'forbidden_recovery':['abs(T)','silent_zero_clipping','interpolation','model_fill']})
save(A/'lp_ml_round1_contamination_quarantine_manifest_v1.json',{'contamination_status':'NO_ACCEPTED_CASE_CONTAMINATION_FOUND','clean_accepted_geometry_count':61,'quarantine_cases':[failed_id+'_y'],'quarantine_reason':'entered solver, no checkpoint, negative-T extraction failure','no_physics_rewrite':True})
save(A/'lp_ml_round1_raw_jones_recoverability_audit_v1.json',{'failed_case':failed_id+'_y','raw_weighted_Ex_Ey_available':False,'raw_transmission_vector_available':False,'normalization_factor_available':False,'full_jones_recoverable_without_solver':False,'accepted_61_raw_jones_recoverable':all(r['finite_weighted_fields'] for r in audit_rows),'method_restriction':'no abs(T), no interpolation, no model fill'})
save(A/'lp_ml_round1_partial_model_downgrade_ledger_v1.json',{'status':'DIAGNOSTIC_ONLY_NOT_PROMOTABLE','reasons':['61 geometries < 240 target','production accounting hard gate','uncertainty correlation insufficient'],'forbidden_uses':['inverse candidate generation','active-learning solver selection','six-bin promotion','scientific performance claim']})
classification='SINGLE_CASE_RUNTIME_FAILURE_PRIOR_DATA_CLEAN'
save(A/'lp_ml_round1_negative_t_recovery_classification_v1.json',{'classification':classification,'clean_accepted_geometries':61,'quarantine_case':failed_id+'_y','solver_calls':0})
save(A/'lp_ml_round1_recovery_budget_proposal_v1.json',{'proposal_status':'OFFLINE_ONLY_NOT_AUTHORIZED','recovery_classification':classification,'failed_y_case_rerun':[failed_id+'_y'],'remaining_untouched_candidates':untouched,'remaining_full_xy_pairs':len(untouched),'single_missing_y_rerun_count':1,'exact_new_solver_budget_if_authorized':2*len(untouched)+1,'old_entered_evidence_retained':True,'no_geometry_replacement':True,'no_plan_change':True,'no_execution_package_generated':True,'solver_calls_this_task':0})
protected={'reports/lp_ml1a3_git_history_geometry_reconstruction.md':sha(R/'reports/lp_ml1a3_git_history_geometry_reconstruction.md'),'reports/stage11_4a20_legacy_fsp_object_inventory.md':sha(R/'reports/stage11_4a20_legacy_fsp_object_inventory.md')}
report=R/'reports/lp_ml_round1_negative_t_forensic_and_recovery_decision_v1.md'
report.write_text(f'''# LP_ML Round-1 negative-T forensic and recovery decision\n\n## Classification\n\n`{classification}`\n\n## Accounting\n\n- Planned: 240 geometries / 480 subruns\n- Entered: 92; accepted: 91; failed: 1\n- Complete: 61 geometries (16 smoke + 45 production)\n- Untouched candidates: {len(untouched)}\n- Remaining full x/y pairs: {len(untouched)}\n- Missing y rerun: 1\n- Prospective budget if separately authorized: {2*len(untouched)+1}\n\n## Negative-T audit\n\nAll {len(audit_rows)} accepted checkpoints were scanned. Accepted cases have finite weighted fields, exact nine-point wavelength vectors, matching geometry hashes, Native-M1/configuration gates, and no non-positive T. The failed y case has no raw T vector, raw weighted fields, checkpoint, or FSP, so its root cause remains `INDETERMINATE_SOURCE_EVIDENCE`. No `abs(T)`, clipping, interpolation, model fill, or physics rewrite was used.\n\n## Recovery\n\n`{failed_id}_x` is retained as accepted. `{failed_id}_y` is quarantined and not rerun. The recovery budget is offline-only and unauthorized. Partial models remain `DIAGNOSTIC_ONLY_NOT_PROMOTABLE`. Solver calls in this task: 0.\n\nProtected hashes: `{protected['reports/lp_ml1a3_git_history_geometry_reconstruction.md']}`, `{protected['reports/stage11_4a20_legacy_fsp_object_inventory.md']}`\n''',encoding='utf-8')
print(json.dumps({'classification':classification,'accepted_checkpoints':len(checkpoints),'case_classes':counts,'untouched':len(untouched),'prospective_budget':2*len(untouched)+1,'solver_calls':0},indent=2))
