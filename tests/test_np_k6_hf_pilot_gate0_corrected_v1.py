import json
from pathlib import Path
def test_corrected_gate0_setup():
 e=Path(__file__).resolve().parents[1]/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'; assert json.loads((e/'corrected_setup_state.json').read_text())['state']=='READY_FOR_GATE0_SOLVER_AUTHORIZATION'; assert json.loads((e/'corrected_monitor_contract_audit.json').read_text())['all_pass']
