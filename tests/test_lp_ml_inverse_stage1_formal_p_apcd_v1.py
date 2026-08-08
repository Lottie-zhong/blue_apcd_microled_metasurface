import csv, json, hashlib
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
OUT=ROOT/'outputs/lp_ml_dataset_v1'; A=OUT/'analysis'; C=OUT/'contracts'

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def test_formal_matrix_exact_and_gauge():
    x=load(C/'lp_linear_x_projector_target_matrix_v1.json')
    assert x['matrix']['Re']==[[1.0,0.0],[0.0,0.0]]
    assert x['matrix']['Im']==[[0.0,0.0],[0.0,0.0]]
    assert x['frobenius_norm']==1.0 and x['rank']==1 and x['singular_values']==[1.0,0.0]
    assert x['global_phase_gauge']['arg_P_xx_deg']==0.0

def test_wang_and_invariant_audit():
    d=load(A/'lp_ml_inverse_stage1_wang_eq5_specialization_v2.json')
    assert d['pass'] and d['max_abs_error_to_diag_1_0']<=1e-12
    led=load(A/'lp_ml_inverse_stage1_p_apcd_source_authority_ledger_v2.json')
    assert led['numerical_matrix_available'] and len(led['formal_matrix_sha256'])==64
    rows=list(csv.DictReader((A/'lp_ml_inverse_stage1_35_formal_p_phase_recomputation_v2.csv').open(encoding='utf-8')))
    assert len(rows)==35 and all(abs(float(r['scalar_minus_txx_abs']))<=1e-15 for r in rows)
    cov=load(A/'lp_ml_inverse_stage1_377_formal_phase_coverage_v2.json')
    assert cov['row_count']==377

def test_tuple_and_gate():
    t=load(A/'lp_ml_inverse_stage1_formal_physics_tuple_closure_v2.json')
    assert t['tuple_count']==38880 and t['all_residuals_bounded_180']
    dec=load(A/'lp_ml_inverse_stage1_formal_p_apcd_phase_audit_decision_v2.json')
    assert dec['formal_P_APCD_frozen'] and dec['c_J_equals_txx_verified_raw35'] and dec['c_J_equals_txx_verified_clean377']
    assert dec['solver_calls']==0 and dec['five_d_insufficiency_confirmed'] is False

def test_no_solver_no_physics_rewrite_contract():
    dec=load(A/'lp_ml_inverse_stage1_formal_p_apcd_phase_audit_decision_v2.json')
    assert dec['raw_physics_modified'] is False and dec['solver_calls']==0
    checks=load(A/'lp_ml_inverse_stage1_formal_p_apcd_phase_audit_checksums_v2.json')
    assert all(len(v)==64 for v in checks['files'].values())
