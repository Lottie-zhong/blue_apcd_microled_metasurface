import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
H=R/'outputs/np_k6_pretraining_handoff_v1'; D=R/'outputs/np_k6_ml_d0_database_foundation_v1'; E=R/'outputs/np_k6_hf_pilot_gate0a_run3c_x_n2_v1'
state=json.loads((H/'handoff_state.json').read_text()); man=json.loads((H/'np_k6_pretraining_handoff_manifest_v1.json').read_text()); reg=json.loads((H/'deferred_numerical_forensics_registry.json').read_text()); mdc=json.loads((H/'mdc_np_interface_pending_decisions_v1.json').read_text()); gate=json.loads((H/'np_k6_mainline_training_start_gate_v1.json').read_text()); imm=json.loads((H/'database_immutability_audit.json').read_text()); db=json.loads((D/'k6_database_state.json').read_text()); tasks=json.loads((D/'k6_hf_task_ledger.json').read_text()); led=json.loads((E/'attempt_ledger.json').read_text())
assert state['state']=='NP_K6_PRETRAINING_HANDOFF_COMPLETE_MDC_INTERFACE_DECISION_PENDING' and state['production_mesh_frozen'] is False and state['formal_HF_labels_generated'] is False and state['formal_model_training_started'] is False
assert state['solver_run_invocations_this_phase']==0 and state['new_FSP_this_phase']==0 and state['new_training_artifacts_this_phase']==0
assert man['phase_solver_budget']=={'run_invocation':0,'lumapi_engine':0,'new_attempt':0,'new_fsp':0,'model_training':0,'active_learning_acquisition':0,'sealed_test_access':0}
assert led['run_invocation_count']==1 and led['entered'] and led['post_saved'] and led['post_fsp_sha256']=='7ab701698d0351e3c11163ec712f68cb33994687d85ea93de41ff4772484bb1b'
assert db['design_space_geometry_count']==296010 and db['low_fidelity_geometry_wavelength_count']==3256110 and db['production_mesh_frozen'] is False and db['training_label'] is False
assert len(tasks['rows'])==120 and all(not r['entered'] and r['run_invocation_count']==0 and not r.get('solver_authorized',False) and not r.get('training_label',False) and not r.get('candidate_performance_label',False) for r in tasks['rows'])
assert imm['no_database_write_performed'] and imm['database_manifest_deep_equal_to_committed_baseline'] and imm['lf_manifest_deep_equal_to_committed_baseline'] and imm['lf_chunk_manifest_equal']
assert reg['status']=='DEFERRED' and not reg['blocking_mainline'] and not reg['automatic_resume'] and reg['resume_requires_explicit_user_authorization']
assert mdc['pending_decision_count']==8 and all(x['status'].startswith('PENDING') for x in mdc['decisions'])
assert gate['overall_authorized'] is False and gate['NP_K6_MAINLINE_TRAINING_AUTHORIZED'] is False and all(x['status']=='PENDING' and not x['authorized'] for x in gate['gates'])
assert man['exact_next_allowed_action']=='WAIT_FOR_MDC_INTERFACE_DECISION'
print('PASS_NP_K6_PRETRAINING_HANDOFF_VALIDATOR')
