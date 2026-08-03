from __future__ import annotations
import csv, hashlib, json, math, os
from pathlib import Path
import numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); P=R/'outputs/lp_ml_dataset_v1/plans'; A=R/'outputs/lp_ml_dataset_v1/analysis'; S=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_smoke_v1'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_csv(p,rs):
 fields=[]
 for r in rs:
  for k in r:
   if k not in fields: fields.append(k)
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rs)
def projection(J):
 t=np.array([[1+0j,0j],[0j,0j]]); den=np.linalg.norm(t)**2*np.linalg.norm(J)**2
 return float(1-abs(np.vdot(t,J))**2/den)
plan=rows(P/'lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv'); smoke=rows(P/'lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv'); contract=js(P/'lp_ml_dataset_v1_contract_v1.json'); qa=js(S/'quality_audit_v1.json'); ent=js(S/'entered_accounting_v1.json')
comp={k:sum(r['category']==k for r in plan) for k in ['GLOBAL_SOBOL','PHASE_REGION','PROJECTOR_REGION','BOUNDARY_FAILURE']}; smcomp={k:sum(r['category']==k for r in smoke) for k in ['GLOBAL_SOBOL','PHASE_REGION','PROJECTOR_REGION','BOUNDARY_FAILURE']}
J=np.array([[1+2j,0.1-0.2j],[0.3+0.4j,0.05+0.01j]]); alpha=2.3*np.exp(1j*0.7); scalar_invariance=abs(projection(J)-projection(alpha*J))<1e-12
protected={str(R/'reports/lp_ml1a3_git_history_geometry_reconstruction.md'):'d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161',str(R/'reports/stage11_4a20_legacy_fsp_object_inventory.md'):'ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708'}
actual={k:sha(Path(k)) for k in protected}; heavy=[str(p.relative_to(S)) for p in S.rglob('*') if p.suffix.lower() in {'.fsp','.fspx','.ldf','.log','.h5','.mat','.npy','.npz'}]
diag={'diagnostic_version':'LP_ML_SMOKE_FAILURE_DIAGNOSTIC_V1','outcome':qa['outcome'],'failure_class':'BROADBAND_MONITOR_FREQUENCY_CARDINALITY_MISMATCH','failure_stage':'SOLVER_POST_EXTRACTION','solver_entered':ent['count'],'failed_subrun':ent['solver_entries'][0]['attempt_id'],'observed_T_frequency_count':5,'required_frequency_count':9,'required_wavelengths_nm':[450.0,450.5,451.0,451.5,452.0,452.5,453.0,453.5,454.0],'automatic_retry':False,'remaining_solver_authorization_revoked':True,'checkpoint_recovery':'NO_TRUSTED_COMPLETE_CHECKPOINT','heavy_artifacts_in_staging':heavy,'protected_report_sha256_before':protected,'protected_report_sha256_after':actual,'protected_reports_unchanged':actual==protected,'projection_error_scalar_invariance_unit_test':scalar_invariance,'plan_count':len(plan),'plan_composition':comp,'smoke_count':len(smoke),'smoke_composition':smcomp,'no_D9_generated':True,'no_model_training':True}
(A/'lp_ml_dataset_v1_round1_smoke_failure_diagnostic_v1.json').write_text(json.dumps(diag,indent=2,sort_keys=True)+'\n',encoding='utf-8')
cov=A/'lp_ml_dataset_v1_wavelength_coverage_summary_v1.json'; c=js(cov); c.update({'actual_solver_entered':ent['count'],'actual_accepted_subruns':qa['successful_accepted_subruns'],'actual_spectral_rows':qa['spectral_rows'],'outcome':qa['outcome'],'observed_T_frequency_count':5}); cov.write_text(json.dumps(c,indent=2,sort_keys=True)+'\n',encoding='utf-8')
report=R/'reports/lp_ml_dataset_v1_round1_smoke_and_d9_closeout_v1.md'; report.write_text(f'''# LP_ML_DATASET_V1 Round-1 smoke and D9 closeout\n\n## D9 closeout\n- Decision: `CONTRACT_EVIDENCE_GAP`; D9 solver/candidate generation remains unauthorized.\n- Absolute projector guard: `PROJECTOR_GUARD_CONTRACT_NOT_IDENTIFIABLE`; phase anchor retained.\n- Historical hard gate preserved: `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`.\n\n## Contract and plan\n- 256 planned candidates: {comp}.\n- Smoke subset: 16 candidates: {smcomp}.\n- Inputs are the five geometry variables plus sin/cos(Psi); fixed H=500 nm, period=432 nm, Native-M1, field_monitor z=1000 nm and weighted-G0 normalization.\n- `projection_error_apcd_v1` is continuous, target-Jones scalar/phase-invariant, and not an absolute guard.\n\n## Smoke execution\n- Planned: 16 geometries / 32 x-y subruns / 450.0--454.0 nm at 0.5 nm.\n- Entered: {ent['count']}; accepted: {qa['successful_accepted_subruns']}; complete geometries: {qa['complete_geometries']}; spectral rows: {qa['spectral_rows']}.\n- First subrun `{ent['solver_entries'][0]['attempt_id']}` entered the solver once. The monitor returned 5 transmission frequency samples while the contract requires 9. No retry was made and scheduling stopped.\n- Outcome: `LP_ML_PIPELINE_SMOKE_PARTIAL_FIX_REQUIRED`.\n\n## Integrity\n- Protected reports unchanged by SHA256. No D9 geometry, model training, inverse design, K6, remaining 240 production points, or heavy artifact was generated.\n- Failure evidence and entered accounting are retained under `{S}`.\n''',encoding='utf-8')
# Recompute staging checksums after diagnostics already present.
files={str(p.relative_to(S)).replace('\\','/'):sha(p) for p in S.rglob('*') if p.is_file() and p.name!='checksums_v1.json'}
(S/'checksums_v1.json').write_text(json.dumps({'checksums_version':'LP_ML_CHECKSUMS_V1','files':files,'count':len(files)},indent=2,sort_keys=True)+'\n',encoding='utf-8')
# Make partial execution explicit at planned-row granularity without inventing physics.
first=ent['solver_entries'][0]['attempt_id']
geom=[]; sr=[]
for r in smoke:
    cid=r['candidate_id']; status='FAILED_SOLVER_POST_EXTRACTION' if cid==ent['solver_entries'][0]['case_id'] else 'NOT_RUN_AFTER_HARD_STOP'
    geom.append({**r,'execution_status':status,'solver_entered_subruns':1 if cid==ent['solver_entries'][0]['case_id'] else 0,'complete_jones':False,'physics_label':'ABSENT_NOT_SIMULATED'})
    for pol in ('x','y'):
        st='FAILED_SOLVER_POST_EXTRACTION' if cid==ent['solver_entries'][0]['case_id'] and pol=='x' else 'NOT_RUN_AFTER_HARD_STOP'
        sr.append({'subrun_id':f'{cid}_{pol}','candidate_id':cid,'input_polarization':pol,'status':st,'solver_entered':bool(cid==ent['solver_entries'][0]['case_id'] and pol=='x'),'failure_code':'BROADBAND_MONITOR_FREQUENCY_CARDINALITY_MISMATCH' if st.startswith('FAILED') else 'NOT_SCHEDULED_AFTER_STOP','wavelength_nm_contract':'450.0..454.0 step 0.5','physics_label':'ABSENT_NOT_SIMULATED'})
write_csv(S/'geometry_records_v1.csv',geom); write_csv(S/'subrun_records_v1.csv',sr)
qa.update({'planned_subruns':32,'missing_or_not_run_subruns':31,'failed_subruns':1,'accepted_subruns':0}); (S/'quality_audit_v1.json').write_text(json.dumps(qa,indent=2,sort_keys=True)+'\n',encoding='utf-8')
files={str(p.relative_to(S)).replace('\\','/'):sha(p) for p in S.rglob('*') if p.is_file() and p.name!='checksums_v1.json'}
(S/'checksums_v1.json').write_text(json.dumps({'checksums_version':'LP_ML_CHECKSUMS_V1','files':files,'count':len(files)},indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(diag,indent=2,sort_keys=True))
