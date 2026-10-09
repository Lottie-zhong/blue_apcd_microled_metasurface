import os,sys,json,traceback,subprocess,types,datetime,hashlib
from pathlib import Path
import numpy as np
v=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1/platform_v2');sys.path.insert(0,str(v))
runtime=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1');out=v/'reports/native_acceptance_v1';cfg=json.loads((runtime/'acceptance_config.json').read_text())
from apcd_gpu_v2.native_readonly import native_session,pinned_module,ReadOnlySession
from apcd_gpu_v2.artifacts import sha256
api=Path(cfg['lumapi_path']);sys.path.insert(0,str(api.parent));os.environ['ANSYS_LICENSING_DESKTOP_PORT_RANGE']='6200:6299'
os.environ['TEMP']=str(runtime/'api_temp');os.environ['TMP']=os.environ['TEMP']
lum=pinned_module(api,cfg['lumapi_sha256'],'lumapi')
def convert(x):
 if isinstance(x,dict):return {k:convert(z) for k,z in x.items()}
 if isinstance(x,(list,tuple)):return [convert(z) for z in x]
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 if isinstance(x,complex):return {'real':x.real,'imag':x.imag}
 return x
validator_path=Path(cfg['coupling_root'])/'scripts/coupling_ml/validate_pw_k6_5nm_full_period_prefsp_v1.py'
validator=pinned_module(validator_path,'b694ecf692376a33673b785774a8ea734c452f11009aad1cfe553f444817e2a8','v2_native_formal_setup_validator')
assert sha256(validator.BUILDER_PATH)=='fbd3a3e73212568023c47d84223a41b32d5cb3cf8fd48a04d09bef7bb94eded1'
sm_path=Path(cfg['g027_core']['controlled_admission']['source_manifest_path']);assert sha256(sm_path)==cfg['g027_core']['controlled_admission']['source_manifest_sha256']
sm=json.loads(sm_path.read_text());spec_desc=sm['artifacts']['five_nm_case_spec'];specp=sm_path.parent/spec_desc['path'];assert sha256(specp)==spec_desc['sha256'];spec=json.loads(specp.read_text())
receipt={'verdict':'FAIL','case_id':'K6GDP2_DEV_G027','source_fsp_sha256':sha256(cfg['g027_source']),'copy_before':sha256(cfg['g027_copy']),'source_manifest_sha256':sha256(sm_path),'case_spec_sha256':sha256(specp),'gpu_resource_name':cfg['gpu_resource'],'python':sys.executable,'lumapi_sha256':sha256(api),'official_command':'runsystemcheck("FDTD","GPU")','native_session':{}}
try:
 with native_session(lum.FDTD,{cfg['g027_copy']:cfg['g027_source_sha256']},receipt['native_session']) as fd:
  fd.load(cfg['g027_copy'])
  # Reuse only the frozen scientific inspector. Its factory is redirected in memory
  # to this already loaded guarded session; its close is deferred to this context.
  class InspectorFacade:
   def __getattr__(self,key):return getattr(fd,key)
   def close(self):return None
  def factory(path,hide=True):
   assert str(Path(path).resolve())==str(Path(cfg['g027_copy']).resolve())
   return InspectorFacade()
  validator.BUILDER.import_lumapi=lambda:types.SimpleNamespace(FDTD=factory)
  readback=validator.inspect_fsp(Path(cfg['g027_copy']),spec)
  expected=validator.validate_expected(readback,spec)
  receipt['setup_validation']=expected;receipt['setup_readback']=readback
  assert expected['status']=='PASS',expected
  resources=[]
  count=int(np.asarray(fd.getresource('FDTD')).item())
  for index in range(1,count+1):
   row={'index':index,'name':fd.getresource('FDTD',index,'name'),'properties':fd.getresource('FDTD',index)}
   resources.append(row)
  assert cfg['gpu_resource'] in [q['name'] for q in resources]
  receipt['resources_readback']=resources
  check=fd.runsystemcheck('FDTD','GPU');receipt['systemcheck']=convert(check)
  mem=check['Approximate_GPU_Memory_Requirements']
  receipt['minimum_bytes']=float(np.asarray(mem['Minimum_Bytes']).item());receipt['maximum_bytes']=float(np.asarray(mem['Maximum_Bytes']).item())
  receipt['verdict']='PASS'
except BaseException as exc:
 receipt['error']=repr(exc);receipt['traceback']=traceback.format_exc()
finally:
 receipt['copy_after']=sha256(cfg['g027_copy']);receipt['source_after']=sha256(cfg['g027_source'])
 receipt['files_unchanged']=receipt['copy_before']==receipt['copy_after']==receipt['source_fsp_sha256']==receipt['source_after']
 assert receipt['files_unchanged']
 x=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu','--format=csv,noheader'],capture_output=True);receipt['gpu_inventory']=x.stdout.decode(errors='replace').strip()
 x=subprocess.run(['powershell','-NoProfile','-Command',"(Get-Item 'N:\\Program Files\\ANSYS Inc\\v251\\Lumerical\\bin\\fdtd-solutions.exe').VersionInfo | Select-Object FileVersion,ProductVersion | ConvertTo-Json -Compress"],capture_output=True);receipt['installed_version']=x.stdout.decode(errors='replace').strip()
 (out/'g027_exact_systemcheck.json').write_text(json.dumps(convert(receipt),indent=2,default=str),encoding='utf-8')
 print('GPU_SYSTEMCHECK',receipt['verdict'],receipt.get('minimum_bytes'),receipt.get('maximum_bytes'),receipt.get('error'))
print('SYSTEMCHECK_FIELDS',receipt.get('systemcheck'))
# Run the existing official zero-solver license/API precheck, with a restricted factory.
license_path=Path(r'D:\project\worktrees\blue_apcd_gpu_production_runner_v1/scripts/shared_fdtd/gpu_runner_v1/license_preflight_v1.py')
license_module=pinned_module(license_path,sha256(license_path),'v2_existing_formal_license_precheck')
sessions=[]
class LicenseSession:
 def __init__(self,hide=True):
  self.receipt={};sessions.append(self.receipt)
  self.context=native_session(lum.FDTD,{},self.receipt,allow_license=True)
  self.guarded=self.context.__enter__()
 def eval(self,script):return self.guarded.eval(script)
 def close(self):return self.context.__exit__(None,None,None)
licdir=runtime/'license_precheck';licdir.mkdir(exist_ok=True)
license_receipt={'API_LICENSE_AVAILABLE':False,'GPU_ENGINE_LICENSE_CONFIRMED':False,'GPU_ENGINE_LICENSE_NOT_TESTED':True,'sessions':sessions,'feature_scope':'FDTD_Solutions_engine checkout only; no GPU engine/HPC dispatch','scientific_solver_invocations':0,'formal_precheck_source_sha256':sha256(license_path)}
try:
 result=license_module.run_lumerical_license_preflight(licdir,api,cfg['lumapi_sha256'],runtime/'license_temp',port_range='6200:6299',session_factory=LicenseSession)
 license_receipt['formal_result']=result;license_receipt['API_LICENSE_AVAILABLE']=result['result']=='PASS'
except BaseException as exc:license_receipt['error']=repr(exc);license_receipt['traceback']=traceback.format_exc()
(out/'license_scope.json').write_text(json.dumps(license_receipt,indent=2,default=str),encoding='utf-8')
print('LICENSE_SCOPE',license_receipt['API_LICENSE_AVAILABLE'],'GPU_ENGINE_LICENSE_NOT_TESTED',True,license_receipt.get('error'))
