"""Pure DIAG2 migration checks; never launches Runner or creates a budget ledger."""
from copy import deepcopy
CASE_IDS=('K6V3_TIME_DIAG2_A1_5NM_6PS','K6V3_TIME_DIAG2_A2_5NM_6PS')
BATCH='K6V3_TIME_DIAG2_V1_BATCH_001'
CONTRACT='51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36'
GEOMETRIES=((120,160,165,175,160,195),(210,115,175,115,180,125))
def need(ok,why):
 if not ok:raise ValueError(why)
def validate_migration_record(record):
 need(record['batch_id']==BATCH,'original_batch_required')
 need(record['new_entry_budget']==0 and record['inherited_entry_ceiling']==2,'no_budget_expansion')
 need(record['physics_contract_sha']==CONTRACT,'original_six_ps_contract_required')
 need(record['current_task_solver_authorization']==0 and record['execution_enabled'] is False,'zero_solver_task')
 cases=record['cases'];need(len(cases)==2 and tuple(c['case_id'] for c in cases)==CASE_IDS,'only_original_two_science_identities')
 for c,g in zip(cases,GEOMETRIES):
  need(c['attempt_id']=='attempt_001','original_attempt_required');need(tuple(c['ordered_D_nm'])==g,'ordered_geometry_conflict')
  need(c['max_entries']==1 and c['entered_count']==0 and c['replay_count']==0,'entry_or_replay_conflict')
  need(c['simulation_time_s']==6e-12 and c['mesh_nm']==5 and c['auto_shutoff_min']==1e-6,'physical_contract_conflict')
  need(c['runner_job_id'] is None and c['runner_execution_attempt'] is None,'not_live_registered_in_preparation')
 return {'status':'PASS_IDENTITY_AND_BUDGET_SEMANTICS_ONLY','production_admission':False,'entry_record_created':False}
def final_verdict(gates):
 need(len(gates)==6,'six_required_gates')
 return 'DIAG2_V3_1_MIGRATION_PREFLIGHT_PASS' if all(x['status']=='PASS' for x in gates) else 'DIAG2_V3_1_MIGRATION_HOLD'
def validate_completed_is_not_labels(runner_status,profile_receipt):
 if runner_status=='COMPLETED' and profile_receipt is None:return 'POSTPROCESS_PENDING_NOT_LABELS_VALID'
 return 'VERIFY_EXISTING_PROFILE_AND_NATIVE_RECORD'
