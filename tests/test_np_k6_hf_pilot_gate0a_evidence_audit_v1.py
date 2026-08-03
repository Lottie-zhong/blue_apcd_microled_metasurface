import json
from pathlib import Path
def test_authority_runtime_and_boundary_evidence():
 e=Path(__file__).resolve().parents[1]/'outputs/np_k6_hf_pilot_gate0a_run3c_x_n2_v1'
 assert json.loads((e/'run3c_geometry_authority_audit.json').read_text())['authority_pass']
 assert json.loads((e/'active_hf_legacy_authority_audit.json').read_text())['authority_pass']
 assert json.loads((e/'task_ledger_gate0a_audit.json').read_text())['ledger_isolation_pass']
 b=json.loads((e/'boundary_flux_449nm_audit.json').read_text()); assert len(b['planes_low_to_high'])==6 and abs(b['source_slab_injection']['value'])>0.9
 m=json.loads((e/'material_provenance_hash_audit.json').read_text()); assert all(m['setup_post_material_hash_equal'].values()) and not m['run_called'] and not m['save_called']
def test_failed_gate_remains_diagnostic_only():
 e=Path(__file__).resolve().parents[1]/'outputs/np_k6_hf_pilot_gate0a_run3c_x_n2_v1'; s=json.loads((e/'gate0a_state_update.json').read_text()); n=json.loads((e/'n2_numerical_gate_audit.json').read_text()); a=json.loads((e/'strict_actual_nesting_audit.json').read_text())
 assert s['diagnostic_only'] and not s['production_mesh_frozen'] and not s['training_label'] and not n['closure_pass'] and not a['strict_actual_nesting']
