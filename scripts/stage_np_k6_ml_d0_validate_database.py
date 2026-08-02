import csv, gzip, json, hashlib
from pathlib import Path
W=Path(__file__).resolve().parents[1]
def main():
    O=W/'outputs/np_k6_ml_d0_database_foundation_v1'
    rows=list(csv.DictReader(gzip.open(O/'k6_design_space_master.csv.gz','rt',encoding='utf-8')))
    assert len(rows)==296010 and all(int(r['D0'])<int(r['D1'])<int(r['D2'])<int(r['D3'])<int(r['D4'])<int(r['D5']) for r in rows)
    m=json.loads((O/'k6_lf_arrays_manifest.json').read_text()); assert m['geometry_wavelength_count']==3256110 and len(m['chunk_manifest'])==60
    p=json.loads((O/'k6_hf_pilot_geometry_manifest.json').read_text()); t=json.loads((O/'k6_hf_task_ledger.json').read_text()); assert p['development_count']==48 and p['sealed_test_count']==12 and t['task_count']==120
    assert all(not x['solver_authorized'] and not x['entered'] and x['run_invocation_count']==0 and x['production_mesh_id']=='PENDING' for x in t['rows'])
    d=json.loads((O/'determinism_audit.json').read_text()); assert d['all_samples_match'] and d['chunk_manifest_hashes_stable']
    c=json.loads((O/'database_checksum_manifest.json').read_text()); assert c['row_counts']=={'design_space':296010,'lf_geometry_wavelength':3256110,'pilot':60,'hf_tasks':120}
    for x in c['files']:
        q=O/x['relative_path']; assert hashlib.sha256(q.read_bytes()).hexdigest()==x['sha256']
    print('PASS_NP_K6_ML_D0_DATABASE_VALIDATOR')
if __name__=='__main__': main()
