import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=R/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1'
state=json.loads((E/'gate0_hard_gate_audit.json').read_text())
assert state['state']=='HARD_GATE_K6_GATE0_SETUP_CONTRACT_DRIFT'
assert state['cases_planned']==6 and state['cases_entered']==0 and state['solver_run_invocation_count']==0
assert not state['scheduler_registered'] and not state['hf_labels_promoted']
manifest=json.loads((E/'gate0_setup_manifest.json').read_text())
assert [x['case_order'] for x in manifest['cases']]==list(range(1,7))
assert manifest['source_n2_sha256']=='5847aadcc4da2279e71de85c952287442b21e9ca2fae552f5ae1b6eeca05ac51'
for row in manifest['cases']:
 d=json.loads((E/'cases'/row['case_id']/'setup_readback_audit.json').read_text())
 l=json.loads((E/'cases'/row['case_id']/'attempt_ledger.json').read_text())
 assert d['hard_gate']==state['state'] and d['unexpected_differences']
 assert not l['entered'] and l['run_invocation_count']==0
print('PASS_NP_K6_HF_PILOT_GATE0_SETUP_DRIFT_VALIDATOR')
