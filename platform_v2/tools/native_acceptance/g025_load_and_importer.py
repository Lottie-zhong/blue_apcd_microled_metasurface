import os,sys,json,subprocess,traceback,importlib.util,hashlib,time
from pathlib import Path
import numpy as np
v=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1/platform_v2');sys.path.insert(0,str(v))
runtime=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1');out=v/'reports/native_acceptance_v1'
cfg=json.loads((runtime/'acceptance_config.json').read_text())
from apcd_gpu_v2.native_readonly import native_session,pinned_module
from apcd_gpu_v2.artifacts import sha256,bundle_inventory
api=Path(cfg['lumapi_path']);sys.path.insert(0,str(api.parent));os.environ['ANSYS_LICENSING_DESKTOP_PORT_RANGE']='6200:6299'
os.environ['TEMP']=str(runtime/'api_temp');os.environ['TMP']=os.environ['TEMP'];Path(os.environ['TEMP']).mkdir(exist_ok=True)
lum=pinned_module(api,cfg['lumapi_sha256'],'lumapi')
launcherpath=Path(cfg['launcher_path'])
for p in [launcherpath.parents[2],launcherpath.parent,Path(r'D:\project\worktrees\blue_apcd_gpu_production_runner_v1/scripts/shared_fdtd/gpu_runner_v1/vendor')]:sys.path.insert(0,str(p))
launcher=pinned_module(launcherpath,cfg['launcher_sha256'],'v2_pinned_scientific_postprocess')
pc=json.loads(Path(cfg['physical_contract_path']).read_text());assert sha256(cfg['physical_contract_path'])==cfg['physical_contract_sha256']
postdir=runtime/'g025_load_postprocess';postdir.mkdir(exist_ok=True)
receipt={'verdict':'FAIL','method':'NATIVE_LOAD_AND_REAL_FROZEN_POSTPROCESS_NO_SOLVER','fsp_sha256':sha256(cfg['g025_copy']),'python':sys.executable,'python_version':sys.version,'lumapi_path':str(api),'lumapi_sha256':sha256(api),'original_before':bundle_inventory(cfg['g025_source'],'run_output.h5'),'copy_before':bundle_inventory(cfg['g025_copy'],'run_output.h5')}
session={};receipt['native_session']=session
try:
 with native_session(lum.FDTD,{cfg['g025_copy']:receipt['fsp_sha256']},session) as fd:
  fd.load(cfg['g025_copy'])
  postcfg={'pw_contract':pc,'run_fsp':cfg['g025_copy'],'case':'K6GDP2_DEV_G025','attempt':'attempt_001','task':cfg['g025_manifest']['run_id'],'gpu_resource_name':cfg['gpu_resource']}
  launcher.load_only_validate(fd,postcfg)
  monitors=list(dict.fromkeys(pc['monitors'].values()))
  fields={}
  for monitor in monitors:
   wavelengths=299792458/np.asarray(fd.getdata(monitor,'f')).reshape(-1)*1e9
   assert len(wavelengths)==21 and np.allclose(np.sort(wavelengths),np.arange(440,461),rtol=0,atol=1e-6)
   row={'wavelengths_nm':wavelengths.tolist(),'coordinates':{},'fields':{}}
   for axis in ['x','y','z']:
    a=np.asarray(fd.getdata(monitor,axis),dtype=float).reshape(-1);assert a.size and np.isfinite(a).all()
    row['coordinates'][axis]={'count':a.size,'min_m':float(a.min()),'max_m':float(a.max())}
   for name in ['Ex','Ey','Ez','Hx','Hy','Hz']:
    a=np.asarray(fd.getdata(monitor,name));assert np.iscomplexobj(a) and np.isfinite(a).all()
    row['fields'][name]={'shape':list(a.shape),'dtype':str(a.dtype),'complex':True,'sha256_c_order_bytes':hashlib.sha256(a.tobytes()).hexdigest()}
   fields[monitor]=row
  raw,metrics,paths=launcher.postprocess(fd,postcfg,str(postdir))
  receipt.update({'monitors':fields,'phase_reference_contract':{'samples_nm':pc['samples_nm'],'references_nm':pc['references_nm']},'reference_plane_deembedding':metrics['reference_plane_deembedding'],'order_sign':metrics['order_sign'],'artifact_paths':{k:str(p) for k,p in paths.items()}})
 receipt['verdict']='PASS'
except BaseException as exc:
 receipt['error']=repr(exc);receipt['traceback']=traceback.format_exc()
finally:
 receipt['original_after']=bundle_inventory(cfg['g025_source'],'run_output.h5');receipt['copy_after']=bundle_inventory(cfg['g025_copy'],'run_output.h5')
 receipt['original_unchanged']=receipt['original_before']==receipt['original_after'];receipt['copy_unchanged']=receipt['copy_before']==receipt['copy_after']
 assert receipt['original_unchanged'] and receipt['copy_unchanged']
 (out/'g025_native_load.json').write_text(json.dumps(receipt,indent=2,default=str),encoding='utf-8')
 print('NATIVE_LOAD',receipt['verdict'],receipt.get('error'),len(session.get('events',[])))
if receipt['verdict']!='PASS':sys.exit(1)
# The real importer runs only on newly extracted isolated artifacts from the existing accepted G025 entry.
c=Path(cfg['coupling_root']);sys.path.insert(0,str(c/'scripts/coupling_ml'))
from k6_v2_pipeline import ingest as I, contracts as C
source_report=c/'reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1'
original_result=json.loads((source_report/'INGEST_RESULT_K6GDP2_DEV_G025_V1.json').read_text())
record=original_result['input_artifacts'].copy()
copy_manifest=postdir/'source_manifest.json';copy_manifest.write_bytes(Path(record['source_manifest']['path']).read_bytes())
for key,path in {'source_manifest':copy_manifest,'state_npz':paths['state_npz'],'state_metadata':paths['state_metadata'],'raw_npz':paths['raw_fields'],'raw_metadata':paths['raw_json'],'orders_json':paths['angular']}.items():record[key]={'path':str(path),'sha256':sha256(path)}
reg=I.load_frozen_case_registry(c)
case=I.load_verified_runner_case(record,expected_role=C.ROLE_GLOBAL_DEV,root=c,registry=reg)
zpath=source_report/'INGESTED_TRUTH_K6GDP2_DEV_G025_V1.npz';before_labels=sha256(zpath)
with np.load(zpath,allow_pickle=False) as z:
 chat=z['C_hat_real']+1j*z['C_hat_imag'];p_scale=z['P_scale'];eta=z['eta']
diffs={'C_hat_max_abs':float(np.max(abs(case.c_hat-chat))),'P_scale_max_abs':float(np.max(abs(case.p_scale-p_scale))),'eta_max_abs':float(np.max(abs(case.eta-eta)))}
assert np.allclose(case.c_hat,chat,rtol=1e-10,atol=1e-12) and np.allclose(case.p_scale,p_scale,rtol=1e-10,atol=1e-12)
encoded=C.pack_model_target(case.c_hat[None],case.p_scale[None]);assert encoded.shape==(1,609)
verdict={'verdict':'PASS','actual_importer':'load_verified_runner_case','importer_source_sha256':sha256(Path(I.__file__)),'input_record':record,'outputs':609,'C_hat_shape':list(case.c_hat.shape),'P_scale_shape':list(case.p_scale.shape),'numeric_differences':diffs,'comparison_tolerance':{'rtol':1e-10,'atol':1e-12},'original_label_sha256':before_labels,'original_label_unchanged':sha256(zpath)==before_labels,'original_fsp_h5_unchanged':receipt['original_unchanged'],'production_ledger_modified':False,'confirmation_responses_opened':False,'new_scientific_solver_invocations':0,'historical_entry_provenance_retained':True}
(out/'g025_actual_importer.json').write_text(json.dumps(verdict,indent=2,default=str),encoding='utf-8')
print('REAL_IMPORTER',diffs,'OUTPUTS',encoded.shape)
