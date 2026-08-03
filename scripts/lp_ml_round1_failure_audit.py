import csv, hashlib, json
from pathlib import Path

R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
S=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_production_attempt1_v1'
A=R/'outputs/lp_ml_dataset_v1/analysis'
REPORT=R/'reports/lp_ml_dataset_v1_round1_production_attempt1_partial_hard_gate_v1.md'
PROTECTED={
 'reports/lp_ml1a3_git_history_geometry_reconstruction.md':'d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161',
 'reports/stage11_4a20_legacy_fsp_object_inventory.md':'ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708',
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
with (S/'subrun_records_v1.csv').open(encoding='utf-8-sig',newline='') as f: sub=list(csv.DictReader(f))
with (S/'candidate_wavelength_jones_v1.csv').open(encoding='utf-8-sig',newline='') as f: prod=list(csv.DictReader(f))
with (S/'entered_accounting_v1.json').open(encoding='utf-8') as f: entered=load(S/'entered_accounting_v1.json')
failure=load(S/'failure_evidence_v1.json') if (S/'failure_evidence_v1.json').exists() else {}
failed=[r for r in sub if r.get('status')!='ACCEPTED']
complete=sorted({r['candidate_id'] for r in prod})
smoke=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_smoke_attempt2_v1/candidate_wavelength_jones_v1.csv'
with smoke.open(encoding='utf-8-sig',newline='') as f: smoke_rows=list(csv.DictReader(f))
combined=smoke_rows+prod
outcsv=A/'lp_ml_dataset_v1_round1_partial_assembly_v1.csv'; outcsv.parent.mkdir(parents=True,exist_ok=True)
fields=[]
for r in combined:
    for k in r:
        if k not in fields: fields.append(k)
with outcsv.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(combined)
qa={
 'outcome':'LP_ML_ROUND1_DATA_OR_MODEL_FIX_REQUIRED',
 'raw_runner_outcome':load(S/'quality_audit_v1.json').get('outcome'),
 'hard_gate':'PRODUCTION_SOLVER_SUBRUN_FAILURE_NO_RETRY_AUTHORIZED',
 'failure_stage': failed[0].get('failure_stage') if failed else None,
 'failure_code':'EXTRACTION_NEGATIVE_TRANSMISSION_MATH_DOMAIN',
 'failure_subrun': failed[0].get('subrun_id') if failed else None,
 'failure_mechanism': failed[0].get('error') if failed else None,
 'planned_geometries':240,'planned_subruns':480,'solver_entered':entered.get('count',0),
 'accepted_subruns':sum(r.get('status')=='ACCEPTED' for r in sub),
 'failed_subruns':len(failed),'complete_production_geometries':len(complete),
 'production_spectral_rows':len(prod),'smoke_geometries':16,'smoke_spectral_rows':len(smoke_rows),
 'partial_round1_geometries':len(set(complete)|{r['candidate_id'] for r in smoke_rows}),
 'partial_round1_spectral_rows':len(combined),'model_training_status':'NOT_RUN_HARD_GATE',
 'retry_count':0,'budget_expansion_required':True,'no_d9':True,
 'old_attempt_excluded':True,'protected_sha256':{p:sha(R/p) for p in PROTECTED}
}
(A/'lp_ml_dataset_v1_round1_production_failure_audit_v1.json').write_text(json.dumps(qa,indent=2,sort_keys=True)+'\n',encoding='utf-8')
manifest=load(S/'dataset_manifest_v1.json'); manifest.update({'outcome':qa['outcome'],'complete_geometries':qa['partial_round1_geometries'],'spectral_row_count':qa['partial_round1_spectral_rows'],'solver_entries':qa['solver_entered'],'failed_subruns':qa['failed_subruns'],'model_training_status':'NOT_RUN_HARD_GATE','failure_code':qa['failure_code']})
(S/'dataset_manifest_v1.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
rawqa=load(S/'quality_audit_v1.json'); rawqa.update({'outcome':qa['outcome'],'raw_runner_outcome':qa['raw_runner_outcome'],'failure_code':qa['failure_code'],'failure_subrun':qa['failure_subrun'],'model_training_status':'NOT_RUN_HARD_GATE','budget_expansion_required':True})
(S/'quality_audit_v1.json').write_text(json.dumps(rawqa,indent=2,sort_keys=True)+'\n',encoding='utf-8')
files={str(p.relative_to(S)):sha(p) for p in S.rglob('*') if p.is_file() and p.name!='checksums_v1.json'}
(S/'checksums_v1.json').write_text(json.dumps({'files':files},indent=2,sort_keys=True)+'\n',encoding='utf-8')
REPORT.write_text(f'''# LP_ML_DATASET_V1 Round-1 production partial hard gate\n\n## Outcome\n\n`{qa['outcome']}`\n\n## Accounting\n\n- Planned: 240 geometries / 480 x-y subruns\n- Entered solver: {qa['solver_entered']}\n- Accepted: {qa['accepted_subruns']}\n- Failed: {qa['failed_subruns']}\n- Complete production geometries: {qa['complete_production_geometries']}\n- Partial Round-1 (including retained smoke): {qa['partial_round1_geometries']} geometries / {qa['partial_round1_spectral_rows']} spectral rows\n\n## Failure\n\nSubrun `{qa['failure_subrun']}` entered the solver and then failed during formal weighted-G0 extraction with `{qa['failure_mechanism']}`. The runner stopped; no retry was issued. A second invocation would require budget expansion and is not authorized by this task.\n\n## Model gate\n\nFull Round-1 assembly, split, baseline training, residual MLP ensemble, uncertainty calibration, and Round-2 proposal are **not run** because the production hard gate was not met. No model-filled physics rows were created.\n\n## Integrity\n\nThe old five-point attempt remains excluded. The 16-geometry smoke Attempt-2 remains retained. Protected report hashes were unchanged. No D9, active-learning solver, or additional geometry was generated.\n''',encoding='utf-8')
print(json.dumps(qa,indent=2,sort_keys=True))
