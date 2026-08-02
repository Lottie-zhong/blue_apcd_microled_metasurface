import csv, gzip, json
from pathlib import Path
W=Path(__file__).resolve().parents[1]
def test_database_geometry_and_lf_counts():
    O=W/'outputs/np_k6_ml_d0_database_foundation_v1'; rows=list(csv.DictReader(gzip.open(O/'k6_design_space_master.csv.gz','rt',encoding='utf-8')))
    assert len(rows)==296010 and all(int(r['D0'])<int(r['D1'])<int(r['D2'])<int(r['D3'])<int(r['D4'])<int(r['D5']) for r in rows)
    assert json.loads((O/'k6_lf_arrays_manifest.json').read_text())['geometry_wavelength_count']==3256110
def test_pilot_split_and_no_run_ledger():
    O=W/'outputs/np_k6_ml_d0_database_foundation_v1'; p=json.loads((O/'k6_hf_pilot_geometry_manifest.json').read_text()); t=json.loads((O/'k6_hf_task_ledger.json').read_text())
    assert p['development_count']==48 and p['sealed_test_count']==12 and len({x['geometry_hash'] for x in p['rows']})==60
    assert len(t['rows'])==120 and all(x['entered'] is False and x['run_invocation_count']==0 and x['solver_authorized'] is False for x in t['rows'])
def test_contract_is_pending_mesh_and_not_training():
    O=W/'outputs/np_k6_ml_d0_database_foundation_v1'; c=json.loads((O/'k6_hf_dataset_contract_v1.json').read_text()); s=json.loads((O/'k6_database_state.json').read_text())
    assert c['production_mesh_id']=='PENDING' and c['solver_calls']==0 and s['training_label'] is False
