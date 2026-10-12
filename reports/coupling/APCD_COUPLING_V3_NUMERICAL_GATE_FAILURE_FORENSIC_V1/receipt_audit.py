from pathlib import Path
import json,hashlib,subprocess
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');D=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1';O=R/'reports/coupling/APCD_COUPLING_V3_NUMERICAL_GATE_FAILURE_FORENSIC_V1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(8*1024*1024),b''):h.update(v)
 return h.hexdigest()
L=json.loads((D/'v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json').read_text());out={}
for cid in L['entered_case_ids']:
 r=L['case_records'][cid];e=json.loads(Path(r['v2_entry_receipt']).read_text());assert e['case_id']==cid and e['attempt_id']=='attempt_001' and e['solver_entered'] and e['automatic_replay']==0 and e['request_sha']==r['request_sha256'];bundle=r['evidence']['bundle'];checks={}
 for rel,v in bundle['files'].items():
  p=Path(bundle['path'])/rel;assert sha(p)==v['sha256'] and p.stat().st_size==v['bytes'];checks[rel]=v
 v=r['evidence']['validation'];assert v['verdict']=='PASS' and v['outputs']==609 and v['fresh_load_verified']
 out[cid]={'entry_receipt_sha':r['v2_entry_receipt_sha256'],'case_attempt_request_match':True,'entry':1,'replay':0,'conservative_receipt_physical_process_confirmed':e['physical_process_confirmed'],'later_engine_confirmation':'verified by SQLite ENGINE_PROCESS + successful 3D run_p0.log; initial conservative receipt flag is intentionally not retroactively changed','bundle_hashes_match':checks,'actual_importer':v['actual_importer'],'native_session':v['native_session']}
assert L['entered_count']==L['truth_valid_count']==L['labels_valid_count']==4 and L['remaining_unentered_count']==52 and L['automatic_replay_count']==L['training_fit_count']==L['p_scale_fit_count']==L['confirmation_response_access_count']==0
staged=hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=R)).hexdigest();assert staged=='b8ebeccf47f668d94b60727b89b67799a78de885e252127c6988f3a8ee9d6a78'
(O/'RECEIPT_AND_FINAL_COUNTER_AUDIT.json').write_text(json.dumps({'cases':out,'counts':{k:L[k] for k in ['entered_count','truth_valid_count','labels_valid_count','remaining_unentered_count','automatic_replay_count','training_fit_count','p_scale_fit_count','confirmation_response_access_count']},'foreign_staged_sha_unchanged':staged},indent=2)+'\n')
print('AUDIT_PASS')
