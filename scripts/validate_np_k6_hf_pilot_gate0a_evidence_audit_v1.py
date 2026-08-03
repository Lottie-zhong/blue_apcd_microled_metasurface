import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=R/'outputs/np_k6_hf_pilot_gate0a_run3c_x_n2_v1'
state=json.loads((E/'gate0a_state_update.json').read_text()); led=json.loads((E/'attempt_ledger.json').read_text()); num=json.loads((E/'n2_numerical_gate_audit.json').read_text()); nest=json.loads((E/'strict_actual_nesting_audit.json').read_text()); post=json.loads((E/'n2_post_reload_audit.json').read_text())
geo=json.loads((E/'run3c_geometry_authority_audit.json').read_text()); auth=json.loads((E/'active_hf_legacy_authority_audit.json').read_text()); tl=json.loads((E/'task_ledger_gate0a_audit.json').read_text()); bf=json.loads((E/'boundary_flux_449nm_audit.json').read_text()); mat=json.loads((E/'material_provenance_hash_audit.json').read_text()); rt=json.loads((E/'runtime_execution_summary.json').read_text())
assert state['state']=='NP_K6_HF_PILOT_GATE0A_BLOCKED_BY_NUMERICAL_FIDELITY' and state['diagnostic_only'] and not state['production_mesh_frozen'] and not state['training_label']
assert led['entered'] and led['run_invocation_count']==1 and led['engine_completed'] and led['controller_returned'] and led['post_saved'] and post['sha_stable'] and post['readonly_reload']
assert num['wavelength_count']==11 and not num['closure_pass'] and num['order_sum_pass'] and num['normalization_pass'] and not nest['strict_actual_nesting']
assert not (E/'runtime_runs'/led['case_id']/'attempt_002').exists()
assert geo['authority_pass'] and auth['authority_pass'] and tl['ledger_isolation_pass']
assert len(bf['planes_low_to_high'])==6 and abs(bf['source_slab_injection']['value'])>0.9 and max(x['raw_vs_monitor_abs'] for x in bf['planes_low_to_high'])<1e-8
assert all(mat['setup_post_material_hash_equal'].values()) and all(mat['setup'][m]['type']=='Sampled 3D data' and mat['setup'][m]['rows']==101 for m in mat['setup']) and not mat['run_called'] and not mat['save_called']
assert rt['run_invocation_count']==1 and not rt['attempt_002_present'] and rt['iterations']==104900
print('PASS_NP_K6_HF_PILOT_GATE0A_EVIDENCE_AUDIT_VALIDATOR')
