import json, subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=R/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'
def test_gate0_contract_and_early_stop():
 m=json.loads((E/'gate0_setup_manifest.json').read_text())
 assert len(m['cases'])==6 and [c['case_order'] for c in m['cases']]==[1,2,3,4,5,6]
 assert m['strict_order'][0]=='RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE' and m['sealed_test_touched'] is False
 assert all(c['setup_diff_pass'] for c in m['cases'])
 c=json.loads((E/'production_mesh_candidate_contract_v1.json').read_text())
 ax=c['intended_axis_arrays_nm']
 assert all(x in ax['x'] for x in range(-870,871,10))
 assert all(y in ax['y'] for y in range(-145,146,10))
 assert all(z in ax['z'] for z in range(-100,601,10))
 s=list(__import__('csv').DictReader((E/'gate0_case_execution_summary.csv').open()))
 assert sum(r['entered']=='True' for r in s)==1 and all(r['entered']=='False' for r in s[1:])
 d=json.loads((E/'hf_promotion_decision.json').read_text())
 assert d['promoted_task_count']==0 and d['training_label_count']==0 and d['sealed_test_labels_generated']==0
