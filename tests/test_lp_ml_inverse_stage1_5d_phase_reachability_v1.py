import csv, json, math, hashlib
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
AN = ROOT/'outputs/lp_ml_dataset_v1/analysis'
PL = ROOT/'outputs/lp_ml_dataset_v1/plans'
EXPECTED_PAYLOAD = 'accd073c7d27086debc80e21056dade6b534080bc6e5d4fbb29f5f6f0f0f0f0f0'

def _sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def test_formal_p_hash_and_contract():
    d=json.loads((AN/'lp_ml_inverse_stage1_5d_phase_compatibility_ledger_v1.json').read_text())
    assert d['matrix_payload_sha256']=='accd073c7d27086debc80e21056dade6b534080bc6e5d4fbb7025821587348f0'
    assert d['matrix_payload_hash_pass'] is True
    assert d['formal_contract_hash_pass'] is True
    assert d['solver_calls']==0

def test_phase_arg_txx_and_quarantine_exclusion():
    rows=list(csv.DictReader((AN/'lp_ml_inverse_stage1_5d_all_compatible_phase_table_v1.csv').open(encoding='utf-8-sig')))
    assert rows
    assert not any('054' in r.get('candidate_id','') and 'SOBOL_054' not in r.get('candidate_id','') for r in rows)
    for r in rows[:25]:
        expected=math.degrees(math.atan2(float(r['txx_imag']),float(r['txx_real'])))%360
        assert abs(expected-float(r['phase_deg']))<1e-9
        assert r['admitted_formal_reachability_physics']=='True'

def test_compatibility_and_envelope_reproducible():
    led=json.loads((AN/'lp_ml_inverse_stage1_5d_phase_compatibility_ledger_v1.json').read_text())
    allowed={'FORMAL_CONTRACT_EXACT_COMPATIBLE','FORMAL_CONTRACT_NUMERICALLY_TRANSFORMABLE'}
    assert led['geometry054_admitted_rows']==0
    assert led['admitted_unique_geometry_count']==len(list(csv.DictReader((AN/'lp_ml_inverse_stage1_5d_all_compatible_phase_table_v1.csv').open(encoding='utf-8-sig'))))
    env=json.loads((AN/'lp_ml_inverse_stage1_5d_observed_phase_envelope_v1.json').read_text())
    assert env['label']=='OBSERVED_PHYSICS_PHASE_ENVELOPE'
    assert env['not_true_5d_limit'] is True
    assert env['count']==led['admitted_unique_geometry_count']
    assert all(x['classification'] in allowed or x['rows_450_complete_non054']==0 for x in led['sources'])

def test_dense_scan_prediction_only_and_probe_plan():
    dense=json.loads((AN/'lp_ml_inverse_stage1_5d_dense_surrogate_reachability_v1.json').read_text())
    assert dense['requested_points']>=200000
    assert dense['label']=='SURROGATE_REACHABILITY_HYPOTHESIS_ONLY'
    plan=list(csv.DictReader((PL/'lp_5d_phase_reachability_probe_v1.csv').open(encoding='utf-8-sig')))
    assert 24<=len(plan)<=36
    assert all(r['status']=='PLANNED_NOT_RUN' and r['physics_fields']=='ABSENT_NOT_SIMULATED' and r['solver_authorized']=='False' for r in plan)
    assert not any('D9' in r['planned_candidate_id'] for r in plan)

def test_protected_hashes_and_no_solver():
    c=json.loads((AN/'lp_ml_inverse_stage1_5d_reachability_checksums_v1.json').read_text())
    assert c['solver_calls']==0
    for x in c['protected_hashes_before_after'].values(): assert x['before']==x['after']
