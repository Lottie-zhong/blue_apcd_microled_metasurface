import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT
SETUP=WORK/'outputs/np_k6_p0_simtime_2ps_recovery_v2_setup'
LAUNCH=WORK/'outputs/np_k6_p0_runtime_launcher_recovery_setup_v1'
SHA='76d23a8961267fb6a720ad875ba016b56aed5c65e8c7379ce09b0cea6029ef1f'
def j(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def test_recovery_setup_is_zero_run_and_independent():
 m=j(SETUP/'recovery_case_manifest.json'); l=j(SETUP/'attempt_ledger.json'); c=j(SETUP/'setup_checksum.json'); v=j(SETUP/'setup_validator_report.json')
 assert m['case_id']=='RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2' and m['attempt_id']=='attempt_001'
 assert c['sha256']==SHA==c['expected_sha256']
 assert l['entered'] is False and l['run_invocation_count']==0 and l['solver_authorized'] is False
 assert l['engine_completed'] is False and l['controller_returned'] is False and l['post_saved'] is False
 assert m['simulation_time_s']==2e-12 and m['auto_shutoff_min']==1e-5 and v['pass'] is True
def test_launcher_dummy_persistence_passes_without_solver():
 d=j(LAUNCH/'dummy_persistence_dry_run.json'); s=j(LAUNCH/'launcher_status.json');
 assert d['pass'] is True and d['hardened_attempt']['duration_s']>=60
 assert d['hardened_attempt']['heartbeat_completed'] is True and d['hardened_attempt']['exit_code']==0
 assert d['hardened_attempt']['pid_cleaned_after_completion'] is True
 assert d['entered'] is False and d['run_invocation_count']==0 and d['solver_calls']==0
 assert s['manifest']['automatic_retry'] is False and s['manifest']['interactive_session_dependency'] is False
def test_old_abort_remains_unresolved_and_immutable():
 a=j(LAUNCH/'runtime_abort_root_cause_audit.json'); p=j(LAUNCH/'evidence_path_reconciliation.json')
 assert a['classification']=='ROOT_CAUSE_UNRESOLVED' and a['rerun_forbidden'] is True
 assert a['scheduler_last_result_hex']=='0xC000013A' and a['run_log_terminal_progress_percent']==27.203
 assert p['path_conflict_is_reporting_only'] is True and p['old_artifacts_deleted'] is False
def test_launcher_has_no_fdtd_call_or_auto_retry():
 src=(WORK/'scripts/np_k6_p0_runtime_launcher_v1.py').read_text(encoding='utf-8')
 assert 'lumapi' not in src.lower() and 'fdtd' not in src.lower() and 'automatic_retry' in src
 assert 'CREATE_BREAKAWAY_FROM_JOB' in src
