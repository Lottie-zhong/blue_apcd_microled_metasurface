import csv, json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=R/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'
C=E/'cases/RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE'
def test_gate0_run1_evidence():
 s=json.loads((C/'extraction_manifest.json').read_text())
 assert s['wavelengths_nm'].__len__()==11 and s['all_finite'] and not s['gate_closure_pass']
 a=json.loads((C/'run_attempt_ledger.json').read_text())
 assert (a['entered'],a['run_invocation_count'],a['engine_completed'],a['post_saved'],a['controller_returned'])==(True,1,True,True,True)
 b=json.loads((E/'solver_budget_audit.json').read_text())
 assert b['entered_total_corrected_root']==1 and b['attempt_002_count']==0
 rows=list(csv.DictReader((C/'results_11points.csv').open()))
 assert len(rows)==11 and max(abs(float(r['order_sum_relative_error'])) for r in rows)<=1e-8
