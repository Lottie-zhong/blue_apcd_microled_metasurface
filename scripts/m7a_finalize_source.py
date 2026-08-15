import hashlib, json
from pathlib import Path
from datetime import datetime, timezone
R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
O=R/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1'
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
obs=O/'m7a_concurrency3_trial_observation.json'
x=json.loads(obs.read_text(encoding='utf-8-sig'))
x['quality_gate_impact']='all 8 M7A Primary4 cases passed the frozen quality gates; no pending case at closeout'
x['closeout_timestamp']=datetime.now(timezone.utc).isoformat()
obs.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
man=O/'m7a_dataset_manifest.json'
m=json.loads(man.read_text(encoding='utf-8-sig'))
m['status']='NP_K6_M7A_PRIMARY4_TARGETED_HF_ACQUISITION_COMPLETE_20G_M8_RETRAIN_READY'
m['validator_status']='PASS'
m['validator_report_sha256']=sha(O/'m7a_final_validator_report.json')
m['closeout_timestamp']=datetime.now(timezone.utc).isoformat()
man.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'status':m['status'],'validator_report_sha256':m['validator_report_sha256']},indent=2))
