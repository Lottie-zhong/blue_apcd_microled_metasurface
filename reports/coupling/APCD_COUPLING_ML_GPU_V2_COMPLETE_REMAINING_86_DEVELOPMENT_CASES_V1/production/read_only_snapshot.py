"""One explicit completed-case snapshot; no loop, dispatch, native LOAD or fit."""
from pathlib import Path
import json,importlib.util,datetime
P=Path('D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1/reports/coupling/APCD_COUPLING_ML_GPU_V2_COMPLETE_REMAINING_86_DEVELOPMENT_CASES_V1')
spec=importlib.util.spec_from_file_location('remaining86_scientific_audit',P/'verify_remaining_production.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result=module.audit()
name='SCIENTIFIC_AUDIT_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'
with (P/'production'/name).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ['status','observed_at_utc','errors','counts','complete','completed_new_count']}));print('SNAPSHOT_PATH',P/'production'/name)
