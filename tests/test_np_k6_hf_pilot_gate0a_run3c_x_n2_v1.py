import json, hashlib
from pathlib import Path
def test_gate0a_setup_only_evidence():
    r=Path(__file__).resolve().parents[1]; e=r/'outputs/np_k6_hf_pilot_gate0a_run3c_x_n2_v1'; case='RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE0A'
    s=e/'runtime_prefsp'/f'{case}.fsp'; assert s.exists()
    assert json.loads((e/'setup_checksum.json').read_text())['sha256']==hashlib.sha256(s.read_bytes()).hexdigest()
    m=json.loads((e/'setup_manifest.json').read_text()); assert m['solver_entered']==0 and m['run_invocation_count']==0
    assert json.loads((e/'single_variable_contract_audit.json').read_text())['unexpected_differences']==[]
