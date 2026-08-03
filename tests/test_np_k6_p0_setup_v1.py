import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'outputs/np_k6_hf_p0_label_generator_recovery_v1'
ORDER = ['RUN3C_P_PILOT_HF_V1','RUN3C_S_PILOT_HF_V1','RUN3A_P_PILOT_HF_V1','RUN3A_S_PILOT_HF_V1','RUN3B_P_PILOT_HF_V1','RUN3B_S_PILOT_HF_V1']

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def test_six_case_setup_manifest_and_strict_order():
    m = read(STAGE / 'pilot_generator_manifest.json')
    assert m['strict_order'] == ORDER
    assert len(m['cases']) == 6
    assert m['solver_entered'] == 0
    assert m['run_invocation_count'] == 0

def test_setup_contracts_are_zero_run_and_single_scope():
    for case in ORDER:
        cdir = STAGE / 'cases' / case
        c = read(cdir / 'setup_contract.json')
        a = read(cdir / 'setup_readback_audit.json')
        l = read(cdir / 'attempt_ledger.json')
        assert c['entered'] is False and c['run_invocation_count'] == 0
        assert a['setup_diff_pass'] is True and a['unexpected_differences'] == []
        assert l['entered'] is False and l['run_invocation_count'] == 0
        assert c['pilot_scope_only'] is True and c['bulk_mdc_compatible'] is False
        assert c['wavelengths_nm'] == list(range(445, 456))

def test_native_m1_and_fixed_mesh_readback():
    for case in ORDER:
        a = read(STAGE / 'cases' / case / 'setup_readback_audit.json')
        assert a['native_m1_sampled_confirmed'] is True
        mesh = a['mesh_readback']
        assert mesh['dx'] == 5e-9 and mesh['dy'] == 5e-9 and mesh['dz'] == 5e-9
        assert mesh['x span'] == 1.74e-6 and mesh['y span'] == 2.9e-7 and mesh['z span'] == 7e-7

def test_no_solver_artifacts_or_sealed_touch():
    z = read(STAGE / 'solver_zero_audit.json')
    assert z['solver_run_called'] is False
    assert z['solver_entered'] == 0
    assert z['sealed_test_touched'] is False
