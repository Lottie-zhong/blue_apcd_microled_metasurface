from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('al',ROOT/'scripts'/'run_mdc_dipole_tmm_applicability_active_learning_v1.py')
al=importlib.util.module_from_spec(spec);spec.loader.exec_module(al)

def test_frozen_matrix_contract_cardinality():
    assert al.CFG['primary_geometries']==12
    assert len(al.CFG['source_positions_nm'])*len(al.CFG['orientations'])*al.CFG['primary_geometries']==72
    assert len(al.CFG['source_positions_nm'])*len(al.CFG['orientations'])*al.CFG['reserve_geometries']==24

def test_contract_has_prohibited_proxy_metrics():
    assert al.PAIR.exists()
    assert al.CFG['safety_counters']['FDTD_calls']==0

def test_completed_selection_has_disjoint_geometry_and_case_counts():
    import pandas as pd
    out=ROOT/'outputs'/'mdc_dipole_tmm_applicability_active_learning_v1'/'applicability-al-20260729T161300Z-899dbc46288e'
    p=pd.read_parquet(out/'primary_geometry_matrix.parquet'); r=pd.read_parquet(out/'reserve_geometry_matrix.parquet')
    c=pd.read_parquet(out/'future_case_matrix_primary_72.parquet'); rc=pd.read_parquet(out/'future_case_matrix_reserve_24.parquet')
    assert len(p)==12 and len(r)==4 and p.geometry_hash.is_unique and r.geometry_hash.is_unique
    assert not set(p.geometry_hash).intersection(r.geometry_hash)
    assert len(c)==72 and len(rc)==24
    assert c.groupby('geometry_hash').size().eq(6).all() and rc.groupby('geometry_hash').size().eq(6).all()
    assert set(c.case_status)=={'PLANNED_NOT_AUTHORIZED'} and set(rc.case_status)=={'RESERVE_NOT_AUTHORIZED'}
