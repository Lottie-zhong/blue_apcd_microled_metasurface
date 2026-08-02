import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]; E=R/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'
s=json.loads((E/'corrected_setup_state.json').read_text()); assert s['state']=='READY_FOR_GATE0_SOLVER_AUTHORIZATION' and s['solver_entered']==0
a=json.loads((E/'corrected_monitor_contract_audit.json').read_text()); assert a['all_pass'] and a['solver_entered']==0 and a['old_n2_unchanged']
m=json.loads((E/'gate0_setup_manifest.json').read_text()); assert len(m['cases'])==6 and [x['case_order'] for x in m['cases']]==list(range(1,7))
for row in m['cases']:
 d=json.loads((E/'cases'/row['case_id']/'setup_readback_audit.json').read_text()); l=json.loads((E/'cases'/row['case_id']/'attempt_ledger.json').read_text()); assert d['setup_diff_pass'] and not d['unexpected_differences'] and d['native_m1_sampled_confirmed']; assert not l['entered'] and l['run_invocation_count']==0
assert not (R/'outputs/np_k6_hf_dataset_v1').exists()
print('PASS_NP_K6_HF_PILOT_GATE0_CORRECTED_SETUP_VALIDATOR')
