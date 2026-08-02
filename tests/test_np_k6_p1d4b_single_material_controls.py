import json, hashlib
from pathlib import Path
W=Path(__file__).resolve().parents[1]
def test_single_material_setups_are_no_run_and_independent():
    for d in ['tio2','sio2']:
        p=W/'outputs'/f'np_k6_p1d4b_k6x_run3c_n1_material_representation_{d}_constant_only_setup_v1'
        led=json.loads((p/'attempt_ledger.json').read_text()); assert led['entered'] is False; assert led['run_invocation_count']==0
        assert json.loads((p/'single_variable_contract_audit.json').read_text())['pass']
        c=json.loads((p/'setup_checksum.json').read_text()); assert hashlib.sha256(Path(c['path']).read_bytes()).hexdigest()==c['sha256']
def test_mixed_representation_and_factorial_manifest():
    f=W/'outputs/np_k6_p1d4b_k6x_material_representation_factorial_manifest_v1/material_representation_factorial_manifest.json'
    d=json.loads(f.read_text()); assert d['CS']['solver_entered'] is False and d['SC']['solver_entered'] is False
    assert d['setup_only_no_missing_effects_computed'] is True
