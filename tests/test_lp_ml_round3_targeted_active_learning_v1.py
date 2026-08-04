import csv, json
from pathlib import Path

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O=ROOT/'outputs/lp_ml_dataset_v1'; A=O/'analysis'; P=O/'plans'; S=O/'staging/lp_ml_dataset_v1_round3_targeted_active_learning_attempt1_v1'
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def test_round3_plan_and_category_quota():
    r=rows(P/'lp_ml_dataset_v1_round3_64_candidate_plan_v1.csv')
    assert len(r)==64 and len({x['candidate_id'] for x in r})==64
    assert {c:sum(x.get('category','').startswith(c+'_') for x in r) for c in ['B0','B1','B2','B3','B4','B5']}=={'B0':8,'B1':8,'B2':8,'B3':12,'B4':12,'B5':12}
    assert all(x['wavelength_authorization']=='450.0-454.0_nm_step_0.5_nm' for x in r)
    assert not any(x['candidate_id']=='LPML_R1_GLOBAL_SOBOL_054' for x in r)

def test_round3_accounting_and_partial_coverage():
    q=json.loads((S/'quality_audit_v1.json').read_text())
    a=json.loads(A.joinpath('lp_ml_round3_assimilation_summary_v1.json').read_text())
    assert q['planned_geometries']==64 and q['planned_subruns']==128
    assert q['solver_entered']==127 and q['successful_accepted_subruns']==121
    assert q['complete_recovery_geometries']==58 and q['spectral_rows']==522
    assert a['duplicate_invocations']==1 and a['coverage_gap']==6

def test_clean_v3_shape_and_no_model_fill():
    r=rows(O/'clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv')
    assert len(r)==3393 and len({x['candidate_id'] for x in r})==377
    assert not any(x['candidate_id']=='LPML_R1_GLOBAL_SOBOL_054' for x in r)
    assert not any(x.get('model_fill','NONE') not in ('','NONE') for x in r)
    assert len({(x['candidate_id'],x['wavelength_nm']) for x in r})==len(r)

def test_c5_selection_and_search_are_offline():
    t=json.loads(A.joinpath('lp_ml_round3_c5_training_v1.json').read_text())
    sel=json.loads(A.joinpath('lp_ml_round3_validation_selection_v1.json').read_text())
    m=json.loads(P.joinpath('lp_ml_six_bin_inverse_search_round3_v1/lp_ml_six_bin_inverse_execution_manifest_v1.json').read_text())
    assert t['seed_list']==[11,22,33,44,55] and t['from_scratch'] and not t['warm_start']
    assert sel['test_used_for_selection'] is False and sel['solver_calls']==0
    assert m['solver_calls']==0 and m['solver_authorized'] is False
    assert m['planning_model']=='OLD_C5_BLEND_0.95'

def test_final_audit_route():
    a=json.loads(A.joinpath('lp_ml_round3_final_audit_v1.json').read_text())
    assert a['outcome']=='LP_ML_ROUND3_SIX_BIN_PARTIAL_COVERAGE_ROUND4_RECOMMENDED'
    assert a['constraints']['inverse_fdtd'] is False and a['constraints']['geometry054_generated'] is False
    assert a['route']['coverage_ready_for_inverse_fdtd'] is False
