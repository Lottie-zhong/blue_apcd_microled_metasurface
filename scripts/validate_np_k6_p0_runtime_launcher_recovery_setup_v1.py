import json, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
setup=root/'outputs/np_k6_p0_simtime_2ps_recovery_v2_setup'; launch=root/'outputs/np_k6_p0_runtime_launcher_recovery_setup_v1'
def j(p): return json.loads(p.read_text(encoding='utf-8-sig'))
errors=[]
try:
 m=j(setup/'recovery_case_manifest.json'); l=j(setup/'attempt_ledger.json'); c=j(setup/'setup_checksum.json'); v=j(setup/'setup_validator_report.json'); d=j(launch/'dummy_persistence_dry_run.json'); s=j(launch/'launcher_status.json'); a=j(launch/'runtime_abort_root_cause_audit.json'); p=j(launch/'evidence_path_reconciliation.json')
 if m.get('case_id')!='RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2': errors.append('case_id')
 if m.get('attempt_id')!='attempt_001': errors.append('attempt_id')
 if c.get('sha256')!='76d23a8961267fb6a720ad875ba016b56aed5c65e8c7379ce09b0cea6029ef1f' or c.get('sha256')!=c.get('expected_sha256'): errors.append('setup_sha256')
 for k,val in [('entered',False),('run_invocation_count',0),('engine_completed',False),('controller_returned',False),('post_saved',False),('solver_authorized',False)]:
  if l.get(k)!=val: errors.append(k)
 if not d.get('pass') or d.get('hardened_attempt',{}).get('duration_s',0)<60 or not d.get('hardened_attempt',{}).get('heartbeat_completed'): errors.append('dummy_persistence')
 if d.get('hardened_attempt',{}).get('exit_code')!=0 or not d.get('hardened_attempt',{}).get('pid_cleaned_after_completion'): errors.append('dummy_exit_or_pid')
 if s.get('manifest',{}).get('run_invocation_count')!=0 or s.get('manifest',{}).get('solver_calls')!=0: errors.append('launcher_zero_run')
 if a.get('classification')!='ROOT_CAUSE_UNRESOLVED' or not a.get('rerun_forbidden'): errors.append('abort_audit')
 if not p.get('path_conflict_is_reporting_only') or p.get('actual_path_exists') is not True: errors.append('path_reconciliation')
 if v.get('pass') is not True: errors.append('setup_report')
except Exception as e: errors.append('exception:'+repr(e))
print('validator: np_k6_p0_runtime_launcher_recovery_setup_v1')
print('errors:',errors)
print('pass:',not errors)
print('state:', 'READY_FOR_NP_K6_P0_SIMTIME_2PS_RECOVERY_V2_AUTHORIZATION' if not errors else 'BLOCKED')
sys.exit(1 if errors else 0)
