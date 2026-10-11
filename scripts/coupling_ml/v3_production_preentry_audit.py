"""Zero-entry test of actual installed V2 admission interfaces, never dispatch."""
from pathlib import Path
import sys,json,hashlib,subprocess,datetime
import numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');D=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_OVERNIGHT_PRODUCTION_DESIGN_V1'
O=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1';O.mkdir(exist_ok=True)
B=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1');cur=json.loads((B/'CURRENT_INSTALLATION.json').read_text(encoding='utf-8'));bp=Path(cur['binding_path'])
assert hashlib.sha256(bp.read_bytes()).hexdigest()==cur['binding_sha256']
binding=json.loads(bp.read_text(encoding='utf-8'));code=Path(binding['code_root']);inv=code/'CODE_SHA256.json'
assert hashlib.sha256(inv.read_bytes()).hexdigest()==binding['code_inventory_sha256']
print('CODE_INVENTORY_SCHEMA',str(json.loads(inv.read_text(encoding='utf-8')))[:200])
sys.path.insert(0,str(code/'platform_v2'))
from apcd_gpu_v2.serial import SerialRequest
from apcd_gpu_v2.coupling import validate_labels
from apcd_gpu_v2.config import CONTRACT_SHA
cases=json.loads((D/'V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json').read_text(encoding='utf-8'))['cases']
rows=[]
for c in cases:
 raw=dict(case_id=c['case_id'],attempt_id=c['attempt_id'],role=c['role'],ordered_D_nm=c['ordered_D_nm'],pre_fsp=c['source_fsp']['path'],pre_fsp_sha256=c['source_fsp']['sha256'],source_manifest={'path':str(D/'V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json'),'sha256':hashlib.sha256((D/'V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json').read_bytes()).hexdigest()},physical_contract={'path':str(D/'DIAGNOSTIC_CONTRACT_DESIGN.json'),'sha256':c['contract_design_sha256']},physical_contract_sha256=c['contract_design_sha256'] if c['mesh_nm']==4 else CONTRACT_SHA,config_sha256='0'*64)
 try:
  SerialRequest.model_validate(raw);errors=[]
 except Exception as exc:
  errors=[{'location':list(e['loc']),'type':e['type'],'message':e['msg']} for e in exc.errors()]
 assert any(e['location']==['case_id'] for e in errors),'V3_UNEXPECTEDLY_ADMITTED'
 rows.append({'case_id':c['case_id'],'role':c['role'],'status':'REJECTED_BEFORE_ENTRY','schema_errors':errors,'request_object_only':True,'native_API_called':False,'placeholder_not_executable_request':True})
rolechecks=[]
for role in ['DIAGNOSTIC_REPEAT','DIAGNOSTIC_MESH','SEALED_LOCAL','SEALED_GLOBAL']:
 try:validate_labels(np.zeros((21,7,2),complex),np.ones(21),role=role,physical_contract_sha256=CONTRACT_SHA)
 except Exception as exc:rolechecks.append({'role':role,'error_type':type(exc).__name__,'error':str(exc),'fixture_only':True})
 else:raise AssertionError('SEALED_DIAGNOSTIC_ROLE_UNEXPECTEDLY_ACCEPTED')
evidence={'schema':'V3_ACTUAL_INSTALLED_ADMISSION_ZERO_SOLVER_AUDIT_V1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'code_head':binding['code_head'],'binding_path':str(bp),'binding_sha256':cur['binding_sha256'],'code_inventory_path':str(inv),'code_inventory_sha256':binding['code_inventory_sha256'],'actual_api_source':str(Path(__import__('apcd_gpu_v2.serial',fromlist=['x']).__file__)),'actual_api_source_sha256':hashlib.sha256(Path(__import__('apcd_gpu_v2.serial',fromlist=['x']).__file__).read_bytes()).hexdigest(),'cases':rows,'role_fixture_rejections':rolechecks,'rejected56':len(rows),'admission_pass':False,'solver_entries':0,'fits':0,'confirmation_response_access':0,'replay':0,'fixture_arrays_are_synthetic':True}
(O/'ACTUAL_INSTALLED_API_REJECTION_EVIDENCE.json').write_bytes((json.dumps(evidence,ensure_ascii=False,indent=2)+'\n').encode())
print('AUDIT',json.dumps({k:v for k,v in evidence.items() if k not in ['cases']},ensure_ascii=False))
