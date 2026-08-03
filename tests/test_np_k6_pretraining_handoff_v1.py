import json
from pathlib import Path
def test_handoff_is_frozen_no_run_or_training():
 r=Path(__file__).resolve().parents[1]; h=r/'outputs/np_k6_pretraining_handoff_v1'; s=json.loads((h/'handoff_state.json').read_text()); g=json.loads((h/'np_k6_mainline_training_start_gate_v1.json').read_text())
 assert s['solver_run_invocations_this_phase']==0 and s['new_FSP_this_phase']==0 and s['new_training_artifacts_this_phase']==0 and not g['overall_authorized']
def test_handoff_authority_and_task_ledger():
 r=Path(__file__).resolve().parents[1]; h=r/'outputs/np_k6_pretraining_handoff_v1'; m=json.loads((h/'np_k6_pretraining_handoff_manifest_v1.json').read_text()); imm=json.loads((h/'database_immutability_audit.json').read_text())
 assert m['d0_authority']['geometry_count']==296010 and m['d0_authority']['lf_rows']==3256110 and m['pilot_split_task_ledger']['potential_hf_tasks']==120 and m['pilot_split_task_ledger']['all_120_unentered'] and imm['no_database_write_performed']
def test_mdc_pending_schema_and_deferred_forensics():
 r=Path(__file__).resolve().parents[1]; h=r/'outputs/np_k6_pretraining_handoff_v1'; m=json.loads((h/'mdc_np_interface_pending_decisions_v1.json').read_text()); d=json.loads((h/'deferred_numerical_forensics_registry.json').read_text())
 assert m['pending_decision_count']==8 and len(m['decisions'])==8 and d['status']=='DEFERRED' and d['resume_requires_explicit_user_authorization']
