import csv,json,hashlib
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); OUT=ROOT/r'outputs\np_k6_m5_fullk6_forward_v0'
def load(p): return json.loads(p.read_text())
def test_prereg_and_zero_solver():
    pre=OUT/'NP_K6_FULLK6_FORWARD_V0_PREREG_V1.json'; h=hashlib.sha256(pre.read_bytes()).hexdigest(); assert h==load(OUT/'preregistration_sha256.json')['sha256']; z=load(OUT/'solver_zero_audit.json'); assert z['fdtd_run_calls']==0 and z['sealed_hf_target_reads']==0
def test_authority_and_order_contract():
    a=load(OUT/'authority_audit.json'); s=load(OUT/'order_schema_audit.json'); assert a['normalized_authority_rows']==286 and a['geometry_count']==13 and a['case_count']==26 and a['all_m5_training_label_true']; assert s['orders']==[-3,-2,-1,0,1,2,3] and s['all_complete']
def test_grouped_oof_and_external_governance():
    folds=list(csv.DictReader((OUT/'fold_manifest.csv').open(encoding='utf-8-sig'))); assert len(folds)==13 and len({x['held_out_geometry'] for x in folds})==13
    oof=list(csv.DictReader((OUT/'oof_predictions.csv').open(encoding='utf-8-sig'))); assert len(oof)==4862
    e=load(OUT/'external_set_registry.json'); assert e['geometry_count']==12 and e['sealed_hf_target_read']==0 and not e['training_geometry_intersection']
def test_model_metrics_and_ps_audit():
    n=load(OUT/'numerical_metrics.json'); assert len(n['models'])==5 and n['output_order']==[-3,-2,-1,0,1,2,3]; p=list(csv.DictReader((OUT/'ps_delta_audit.csv').open(encoding='utf-8-sig'))); assert len(p)==5*13*11
