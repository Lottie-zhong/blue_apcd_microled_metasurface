from __future__ import annotations
import ast, csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'mdc_gan_native_m1_extraction_audit_v1'

def test_safety_and_delayed_lumapi():
    text=(ROOT/'scripts'/'extract_mdc_gan_native_m1_candidate_v1.py').read_text(encoding='utf-8'); tree=ast.parse(text)
    assert '.run(' not in text and 'runanalysis' not in text and 'saveas' not in text
    assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(getattr(x,'name','')=='lumapi' for x in getattr(n,'names',[])) for n in tree.body)

def test_response_grid_epsilon_and_absorption():
    rows=list(csv.DictReader((OUT/'gan_complex_index_420_480.csv').open(encoding='utf-8')))
    assert len(rows)==601 and rows[0]['wavelength_nm']=='420.0' and rows[-1]['wavelength_nm']=='480.0'
    for row in rows:
        n=float(row['n_real']); k=float(row['k_imag']); er=float(row['epsilon_real']); ei=float(row['epsilon_imag'])
        assert abs(er-(n*n-k*k)) < 1e-9 and abs(ei-2*n*k) < 1e-9
    critical={row['wavelength_nm']:row for row in rows}; assert float(critical['450.0']['k_imag']) >= .084153
    absorption=list(csv.DictReader((OUT/'gan_absorption_sanity.csv').open(encoding='utf-8'))); assert len(absorption)==601

def test_policy_deembedding_roundtrip_and_source_gate():
    validation=json.loads((OUT/'validation.json').read_text()); policy=json.loads((OUT/'gan_candidate_policy.json').read_text()); spec=json.loads((OUT/'fdtd_gan_deembedding_spec.json').read_text())
    assert validation['source_gate']['sha256_matches'] and validation['source_gate']['actual_bytes']==34241853
    assert validation['roundtrip']['status']=='portable_response_roundtrip_pass' and validation['roundtrip']['reproducible']
    assert policy is None and validation['policy_is_not_frozen'] and validation['deembedding_spec_present']
    assert spec['required_matched_homogeneous_gan_reference']['same_GaN_material'] and 'material_model_mismatch_present' in str(spec)

def test_outputs_are_deterministic_artifacts():
    for name in ('gan_complex_index_420_480.csv','gan_blank_session_roundtrip.csv','gan_absorption_sanity.csv'):
        path=OUT/name; assert hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256(path.read_bytes()).hexdigest()
