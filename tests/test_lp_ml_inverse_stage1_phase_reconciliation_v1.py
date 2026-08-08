import csv,hashlib,json
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
OUT=ROOT/'outputs/lp_ml_dataset_v1'; A=OUT/'analysis'
def test_normalization_sha_reconciliation():
 p=OUT/'clean_v2/normalization_clean_v2.json'; actual=hashlib.sha256(p.read_bytes()).hexdigest(); m=json.loads((OUT/'clean_v2/clean_dataset_manifest_v2.json').read_text()); c=json.loads((OUT/'clean_v2/clean_dataset_checksums_v2.json').read_text()); t=json.loads((A/'lp_ml_round2_clean_recompetition_training_v2.json').read_text()); assert actual==m['normalization_sha256']==c['outputs/lp_ml_dataset_v1/clean_v2/normalization_clean_v2.json']==t['normalization_sha256']; assert len(actual)==64

def test_stage1_and_clean_v3_closure():
 with (OUT/'staging/lp_ml_inverse_stage1_fdt_validation_v1/candidate_wavelength_jones_v1.csv').open(encoding='utf-8-sig',newline='') as f: stage=list(csv.DictReader(f))
 with (A/'lp_ml_inverse_stage1_35_physics_immutable_manifest_v1.csv').open(encoding='utf-8-sig',newline='') as f: imm=list(csv.DictReader(f))
 with (OUT/'clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv').open(encoding='utf-8-sig',newline='') as f: c3=list(csv.DictReader(f))
 assert len(stage)==35 and all(r['Jones_complete'].lower()=='true' for r in stage); assert {r['target_bin'] for r in imm}=={'0','1','2','3','4','5'}; assert len(c3)==3393 and len({r['candidate_id'] for r in c3})==377

def test_quarantine_and_decision_gate():
 with (OUT/'clean_v2/lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 assert not any(r['candidate_id']=='LPML_R1_GLOBAL_SOBOL_054' for r in rows); assert not any(r.get('exact_geometry_hash_sha256')=='f6bcfd429f3cd1b722f520bc67dbc62501854a686b17d8deae492cc66e950b21' for r in rows)
 d=json.loads((A/'lp_ml_inverse_stage1_phase_audit_decision_v1.json').read_text()); assert d['outcome']=='LP_ML_INVERSE_STAGE1_PHASE_AUDIT_HARD_GATE'; assert d['solver_calls']==0; assert d['five_d_insufficiency_confirmed'] is False

def test_protected_hashes_unchanged():
 assert hashlib.sha256((ROOT/'reports/lp_ml1a3_git_history_geometry_reconstruction.md').read_bytes()).hexdigest()=='9e46a7bd1927d65adc3a9cf9192040e7d239b839ed516adcd96870bf64bfcd02'; assert hashlib.sha256((ROOT/'reports/stage11_4a20_legacy_fsp_object_inventory.md').read_bytes()).hexdigest()=='ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708'