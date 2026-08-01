from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('al2',ROOT/'scripts'/'run_mdc_stage_al2_2d_fdtd_v1.py');al2=importlib.util.module_from_spec(spec);spec.loader.exec_module(al2)
def test_frozen_stage_al2_set_difference_is_exact():
    structures=al2.structures(); cases=al2.cases()
    assert len(structures)==6 and len({x['geometry_hash'] for x in structures})==6
    assert len(cases)==36 and len({x['case_id'] for x in cases})==36
    assert all(sum(c['candidate_key']==s['structure_key'] for c in cases)==6 for s in structures)
    assert {c['orientation'] for c in cases}=={'x','z'}
    al1_hashes=set(__import__('pandas').read_parquet(al2.AL1/'case_manifest.parquet').geometry_hash)
    assert not ({x['geometry_hash'] for x in structures}&al1_hashes)
