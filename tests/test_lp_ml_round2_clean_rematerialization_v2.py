import csv,json,hashlib
from pathlib import Path
ROOT=Path(r"D:\\project\\worktrees\\blue_apcd_lp_stage11_4")
OUT=ROOT/'outputs/lp_ml_dataset_v1/clean_v2'; Q='LPML_R1_GLOBAL_SOBOL_054'; R2='LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054'
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def test_quarantine_manifest():
 d=json.loads((OUT/'quarantine_manifest_v2.json').read_text());assert d['candidate_id']==Q and d['admitted_physics_rows']==0 and d['decision'].startswith('QUARANTINED');assert d['no_solver_this_task'] is True
def test_clean_counts_and_quarantine():
 r1=read(OUT/'lp_ml_dataset_v1_round1_clean_v2_255_geometry_2295_rows.csv');r2=read(OUT/'lp_ml_dataset_v1_round2_clean_v2_64_geometry_576_rows.csv');m=read(OUT/'lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv');assert len(r1)==2295 and len({x['candidate_id'] for x in r1})==255;assert len(r2)==576 and len({x['candidate_id'] for x in r2})==64;assert len(m)==2871 and len({x['candidate_id'] for x in m})==319;assert not any(x['candidate_id']==Q for x in m);assert sum(x['candidate_id']==R2 for x in m)==9
def test_complete_admission_and_no_duplicate():
 m=read(OUT/'lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv');assert all(x['Jones_complete'].lower()=='true' for x in m);assert all(x.get('model_fill','NONE') in ('NONE','') for x in m);assert len({(x['candidate_id'],x['wavelength_nm']) for x in m})==len(m);assert all(len({x['exact_geometry_hash_sha256'] for x in m if x['candidate_id']==c})==1 for c in {x['candidate_id'] for x in m})
def test_split_and_no_leakage():
 s=json.loads((OUT/'split_clean_v2.json').read_text());assert s['geometry_count']==319 and s['quarantine_absent'] and s['round2_external_geometry_count']==8;assert not s['canonical_leakage'] and not s['symmetry_leakage']
 rows=read(OUT/'split_clean_v2.csv');assert len(rows)==319 and Q not in {x['candidate_id'] for x in rows}
def test_normalization_clean_train_only():
 d=json.loads((OUT/'normalization_clean_v2.json').read_text());assert d['train_geometry_count']==227 and d['train_row_count']==2043;assert d['quarantine_absent']
def test_superseded_ledger_and_protected():
 d=json.loads((OUT/'superseded_artifacts_ledger_v2.json').read_text());assert d['round1_champion']['clean_input_match'] and not d['round1_champion']['superseded'];assert d['r2_distinct_suffix_candidate_preserved']==R2
 assert sha(ROOT/'reports/lp_ml1a3_git_history_geometry_reconstruction.md')=='9e46a7bd1927d65adc3a9cf9192040e7d239b839ed516adcd96870bf64bfcd02';assert sha(ROOT/'reports/stage11_4a20_legacy_fsp_object_inventory.md')=='ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708'
