import csv,hashlib,json
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); STAGE=ROOT/'outputs/np_k6_p0_simulation_time_extension_control_v1'; CASE='RUN3C_P_PILOT_HF_SIMTIME_2PS_CONTROL_V1'; CDIR=STAGE/'cases'/CASE
def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  while True:
   chunk=f.read(1<<20)
   if not chunk:break
   h.update(chunk)
 return h.hexdigest()
def main():
 errors=[]; c=json.loads((CDIR/'setup_contract.json').read_text()); l=json.loads((CDIR/'attempt_ledger.json').read_text()); f=json.loads((STAGE/'runtime_failure_recovery_audit.json').read_text()) if (STAGE/'runtime_failure_recovery_audit.json').exists() else None
 if c.get('simulation_time_s')!=2e-12 or abs(c.get('auto_shutoff_min',0)-1e-5)>1e-12:errors.append('setup_properties')
 if c.get('unexpected_differences')!=[]:errors.append('unexpected_differences')
 if not l.get('entered') or l.get('run_invocation_count')!=1:errors.append('one_entered_run')
 if f:
  if f.get('scheduler_last_result_hex')!='0xC000013A':errors.append('abort_code')
  if f.get('post_fsp_exists') or f.get('checkpoint_fsp_exists'):errors.append('unexpected_post_or_checkpoint')
  if not f.get('rerun_forbidden') or not f.get('old_parent_post_immutable'):errors.append('immutability')
  classification='INCONCLUSIVE_RUNTIME_ABORT_NO_POST'
 else:
  classification='COMPLETED_METRICS_PENDING'
  if not l.get('engine_completed') or not l.get('post_saved') or not l.get('controller_returned'):errors.append('lifecycle')
 result={'validator':'np_k6_p0_simtime_control_v1','case_id':CASE,'errors':errors,'pass':not errors,'classification':classification,'entered':l.get('entered'),'run_invocation_count':l.get('run_invocation_count'),'training_label':False,'candidate_performance_label':False,'no_partial_promotion':True}
 (STAGE/'standalone_validator_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));raise SystemExit(0 if not errors else 1)
if __name__=='__main__':main()
