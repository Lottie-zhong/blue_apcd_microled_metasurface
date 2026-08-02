import json
from pathlib import Path
def test_np_k6_ml_d0_dft_and_links():
 root=Path(__file__).resolve().parents[1]; db=root/'outputs/np_k6_ml_d0_database_foundation_v1'
 a=json.loads((db/'dft_regression_audit.json').read_text()); assert a['status']=='PASS' and a['ideal_plus1_dominant'] and a['opposite_sign_rejected'] and a['passing_sextet_regression']
 l=json.loads((db/'candidate_linkage_audit.json').read_text()); assert l['passing_sextet_count']==8 and all(x['geometry_hash'] for x in l['anchors'].values())
 s=json.loads((db/'source_contract_reconciliation_audit.json').read_text()); assert s['formal_rows']==297 and s['formal_status']=='complete_27point_recovered_d180_v1' and s['legacy_conflict_preserved']
 t=json.loads((db/'k6_hf_task_ledger.json').read_text()); assert t['task_count']==120 and all(not r['entered'] and r['run_invocation_count']==0 and not r['solver_authorized'] for r in t['rows'])
