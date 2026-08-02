import json
from pathlib import Path
def test_gate0_hard_gate():
 r=Path(__file__).resolve().parents[1]; e=r/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1'
 s=json.loads((e/'gate0_hard_gate_audit.json').read_text())
 assert s['state']=='HARD_GATE_K6_GATE0_SETUP_CONTRACT_DRIFT'
 assert s['cases_entered']==0
 assert not s['scheduler_registered']
