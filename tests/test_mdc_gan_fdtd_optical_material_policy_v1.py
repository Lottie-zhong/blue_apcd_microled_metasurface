from __future__ import annotations
import ast, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'mdc_gan_fdtd_optical_material_policy_audit_v1'

def module():
    spec=importlib.util.spec_from_file_location('gan_audit',ROOT/'scripts'/'audit_mdc_gan_fdtd_optical_material_policy_v1.py')
    value=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(value); return value

def test_policy_safety_contract():
    script=ROOT/'scripts'/'audit_mdc_gan_fdtd_optical_material_policy_v1.py'; text=script.read_text(); tree=ast.parse(text)
    assert 'N_GAN = 2.41' not in text and '.run(' not in text and 'runanalysis' not in text and 'saveas' not in text
    assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(getattr(x,'name','')=='lumapi' for x in tree.body) for n in tree.body)
    rows=(OUT/'gan_material_candidates.csv').read_text(); assert 'not_allowed_for_formal_fdtd' in rows

def test_blocked_policy_without_unique_candidate():
    validation=json.loads((OUT/'gan_material_validation.json').read_text()); policy=json.loads((OUT/'gan_material_policy_candidate.json').read_text())
    if validation['status'] != 'unique_formal_candidate_found': assert policy is None
    assert validation['solver_execution'] is False and validation['analysis_execution'] is False and validation['project_save'] is False

def test_identity_gates_and_conflict_are_blocking():
    audit=module()
    assert audit.decide([],None)==('no_formal_candidate_found',None)
    incomplete={'gan_materials':[{'material_object_name':'GaN','coverage_420_480_nm':True,'model_type':'sampled','extrapolation_policy':'unavailable'}]}
    assert audit.decide([],incomplete)==('formal_candidate_incomplete',None)
    conflict={'gan_materials':[dict(incomplete['gan_materials'][0],material_object_name='GaN_A'),dict(incomplete['gan_materials'][0],material_object_name='GaN_B')]}
    assert audit.decide([],conflict)==('multiple_conflicting_formal_candidates',None)

def test_coverage_extrapolation_sha_and_reproducibility_gates():
    audit=module(); base={'material_object_name':'GaN','coverage_420_480_nm':False,'model_type':'sampled','extrapolation_policy':'none'}
    assert audit.decide([] ,{'gan_materials':[base]})==('formal_candidate_incomplete',None)
    bad=dict(base,coverage_420_480_nm=True,extrapolation_policy='unauthorized_extrapolation')
    assert audit.decide([] ,{'gan_materials':[bad]})==('formal_candidate_incomplete',None)
    candidates=(OUT/'gan_material_candidates.csv').read_text(encoding='utf-8')
    assert 'FSP_GaN::GaN' in candidates and 'd7511bb92154152d5050d7ae664cb5b281ad3794a280129008359353b357e26f' in candidates
    before={p.name:p.read_bytes() for p in OUT.iterdir() if p.is_file()}; audit.build(False); after={p.name:p.read_bytes() for p in OUT.iterdir() if p.is_file()}; assert before==after
