import json
from pathlib import Path
def test_gate0a_final_blocked_state():
    r=Path(__file__).resolve().parents[1]; e=r/'outputs/np_k6_hf_pilot_gate0a_run3c_x_n2_v1'; s=json.loads((e/'gate0a_state_update.json').read_text()); l=json.loads((e/'attempt_ledger.json').read_text()); n=json.loads((e/'n2_numerical_gate_audit.json').read_text())
    assert s['state']=='NP_K6_HF_PILOT_GATE0A_BLOCKED_BY_NUMERICAL_FIDELITY' and l['run_invocation_count']==1 and n['closure_pass'] is False
