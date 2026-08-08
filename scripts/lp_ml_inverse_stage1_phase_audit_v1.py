from pathlib import Path
import json,hashlib,csv,subprocess,collections
ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
OUT=ROOT/'outputs/lp_ml_dataset_v1'; A=OUT/'analysis'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def csvrows(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def audit():
 norm=OUT/'clean_v2/normalization_clean_v2.json'; manifest=json.loads((OUT/'clean_v2/clean_dataset_manifest_v2.json').read_text(encoding='utf-8-sig')); checks=json.loads((OUT/'clean_v2/clean_dataset_checksums_v2.json').read_text(encoding='utf-8-sig')); train=json.loads((A/'lp_ml_round2_clean_recompetition_training_v2.json').read_text(encoding='utf-8-sig'))
 stage=csvrows(OUT/'staging/lp_ml_inverse_stage1_fdt_validation_v1/candidate_wavelength_jones_v1.csv'); imm=csvrows(A/'lp_ml_inverse_stage1_35_physics_immutable_manifest_v1.csv'); merged=csvrows(OUT/'clean_v2/lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv'); c3=csvrows(OUT/'clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv')
 q='LPML_R1_GLOBAL_SOBOL_054'; qhash='f6bcfd429f3cd1b722f520bc67dbc62501854a686b17d8deae492cc66e950b21'
 rec={'normalization_artifact_sha256':sha(norm),'normalization_manifest_sha256':manifest['normalization_sha256'],'normalization_checksums_sha256':checks['outputs/lp_ml_dataset_v1/clean_v2/normalization_clean_v2.json'],'normalization_training_sha256':train['normalization_sha256'],'normalization_match':len({sha(norm),manifest['normalization_sha256'],checks['outputs/lp_ml_dataset_v1/clean_v2/normalization_clean_v2.json'],train['normalization_sha256']})==1,'stage1_rows':len(stage),'stage1_bins':dict(collections.Counter(r['target_bin'] for r in imm)),'stage1_complete_jones':all(r.get('Jones_complete','').lower()=='true' for r in stage),'clean_v3_rows':len(c3),'clean_v3_geometries':len({r['candidate_id'] for r in c3}),'clean_v2_rows':len(merged),'clean_v2_geometries':len({r['candidate_id'] for r in merged}),'geometry054_id_rows':sum(r['candidate_id']==q for r in merged),'geometry054_hash_rows':sum(r.get('exact_geometry_hash_sha256')==qhash for r in merged),'decision':json.loads((A/'lp_ml_inverse_stage1_phase_audit_decision_v1.json').read_text(encoding='utf-8-sig')),'protected_reports':{'reports/lp_ml1a3_git_history_geometry_reconstruction.md':sha(ROOT/'reports/lp_ml1a3_git_history_geometry_reconstruction.md'),'reports/stage11_4a20_legacy_fsp_object_inventory.md':sha(ROOT/'reports/stage11_4a20_legacy_fsp_object_inventory.md')},'solver_calls':0}
 return rec
if __name__=='__main__': print(json.dumps(audit(),indent=2,sort_keys=True))