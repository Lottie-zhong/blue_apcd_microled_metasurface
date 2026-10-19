"""Historical read-only FSP/H5 re-extraction; no solver-facing API exposed."""
from pathlib import Path
import sys,json,hashlib,importlib.util,time
import numpy as np,h5py
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');O=R/'reports/coupling/APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1';G=Path(r'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1')
sys.path.insert(0,str(R/'scripts/coupling_ml'));sys.path.insert(0,str(G/'platform_v2'))
from k6_v2_pipeline import ingest as I,contracts as C,generic_profile as GP
sys.path.insert(0,str(R/'scripts'))
from apcd_gpu_v2.native_readonly import native_session,pinned_module
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8')
def sha(p):return I.sha256_file(p)
cfg=read(Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\serial_config.json'));pins=cfg['truth_toolchain']
for k in ['postprocessor','lumapi','decoder']:assert sha(pins[k]['path'])==pins[k]['sha256']
assert pins['decoder']['sha256']==C.H2_DECODER_SHA256
sys.path.insert(0,str(Path(pins['postprocessor']['path']).parent));sys.path.insert(0,str(Path(pins['lumapi']['path']).parent))
post=pinned_module(pins['postprocessor']['path'],pins['postprocessor']['sha256'],'coupling_migration_frozen_loadonly_post')
lum=pinned_module(pins['lumapi']['path'],pins['lumapi']['sha256'],'lumapi')
reg=I.load_frozen_case_registry(R);inv=read(R/'reports/coupling/APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json');results=[]
for cid in ['K6GDP2_DEV_G001','K6GDP2_DEV_G004']:
 row=next(x for x in inv['cases'] if x['case_id']==cid);assert cid in reg.development and cid not in reg.confirmation
 dest=O/'historical_readonly_reextraction_v2'/cid;dest.mkdir(parents=True,exist_ok=False)
 native=row['native_files'];fsp=next(x for x in native if x['path'].endswith('.fsp'));nh5=next(x for x in native if x['path'].endswith('.h5'))
 for a in [fsp,nh5]:assert Path(a['path']).stat().st_size==a['bytes'] and sha(a['path'])==a['sha256']
 h5summary={'path':nh5['path'],'bytes':nh5['bytes'],'sha256':nh5['sha256']}
 with h5py.File(nh5['path'],'r') as hf:h5summary['top_level_keys']=list(hf.keys())
 pc=read(reg.development[cid]['physical_contract']['path']);pcfg={'pw_contract':pc,'case':cid,'attempt':row['attempt_id'],'task':'READONLY_REEXTRACTION_'+cid,'run_fsp':fsp['path']};session={}
 try:
  with native_session(lum.FDTD,{fsp['path']:fsp['sha256']},session) as fd:
   fd.load(fsp['path']);post.load_only_validate(fd,pcfg)
   raw,metrics,paths=post.postprocess(fd,pcfg,str(dest))
 except BaseException as ex:
  put(dest/'NATIVE_SESSION.json',session);put(O/'NATIVE_REEXTRACTION_ERROR.json',{'case_id':cid,'error':repr(ex),'real_entries':0,'session':session});raise
 put(dest/'NATIVE_SESSION.json',session)
 assert session['close_called'] and not session['after_children'] and all(e['api'] not in ['run','runparallel','save','switchtolayout','eval'] for e in session['events'])
 for key in ['order_sign','reference_plane_deembedding','lossy_gan']:assert metrics[key]['status']=='PASS'
 # Preserve the original science identity and source_manifest; only postprocess artifacts are isolated.
 raw['run_id']=read(row['artifacts']['source_manifest']['path']).get('run_id',raw.get('task_id'));put(paths['raw_json'],raw)
 truth=dest/'truth.h5'
 with h5py.File(truth,'x') as hf:
  for k,v in {'case_id':cid,'attempt_id':row['attempt_id'],'audit_only':True,'new_scientific_entry':False}.items():hf.attrs[k]=v
  for k,v in {'raw_json':raw,'metrics_json':metrics}.items():hf.create_dataset(k,data=json.dumps(v,sort_keys=True,default=str),dtype=h5py.string_dtype('utf-8'))
 def desc(p):return {'path':str(p),'sha256':sha(p)}
 record={'case_id':cid,'attempt_id':row['attempt_id'],'role':row['role'],'ordered_D_nm':row['ordered_D_nm'],'physical_contract_sha256':C.PHYSICAL_CONTRACT_SHA256,'status':'DONE','solver_invocations':1,'replay_count':0,'source_manifest':{'path':row['artifacts']['source_manifest']['path'],'sha256':row['artifacts']['source_manifest']['sha256']},'state_npz':desc(paths['state_npz']),'state_metadata':desc(paths['state_metadata']),'raw_npz':desc(paths['raw_fields']),'raw_metadata':desc(paths['raw_json']),'orders_json':desc(paths['angular']),'truth_h5':desc(truth)}
 imported=I.load_verified_runner_case(record,expected_role=row['role'],root=R);numeric=GP._validate_609d_numeric_payload(imported)
 with np.load(row['artifacts']['label']['path'],allow_pickle=False) as z:
  oldc=z['C_hat_real']+1j*z['C_hat_imag'] if 'C_hat_real' in z.files else z['C_hat'] if 'C_hat' in z.files else z['c_hat'];oldp=z['P_scale'] if 'P_scale' in z.files else z['p_scale']
  parity={'C_hat_max_abs_delta':float(np.max(np.abs(imported.c_hat-oldc))),'P_scale_max_abs_delta':float(np.max(np.abs(imported.p_scale-oldp))),'eta_max_abs_delta':float(np.max(np.abs(imported.eta-z['eta']))),'absolute_order_max_abs_delta':float(np.max(np.abs(imported.absolute_order-z['absolute_order'])))}
 assert all(v<1e-10 for v in parity.values()),parity
 packed=C.pack_model_target(imported.c_hat,imported.p_scale);assert packed.shape==(1,609)
 np.savez_compressed(dest/'labels_readonly.npz',case_id=cid,attempt_id=row['attempt_id'],C_hat_real=imported.c_hat.real,C_hat_imag=imported.c_hat.imag,P_scale=imported.p_scale,eta=imported.eta,absolute_order=imported.absolute_order)
 put(dest/'RUNNER_RECORD_READONLY.json',record)
 result={'case_id':cid,'attempt_id':row['attempt_id'],'original_identity_preserved':True,'new_entry':0,'native_pair':{'fsp':fsp,'h5':h5summary},'outputs':609,'parity':parity,'numeric':numeric,'session_close_called':True,'session_run_calls':0,'readonly_record':str(dest/'RUNNER_RECORD_READONLY.json'),'native_3ps_only':True,'science_ledger_written':False}
 results.append(result);put(O/'HISTORICAL_NATIVE_REEXTRACTION.json',{'status':'PASS_PARTIAL_CASES' if len(results)==1 else 'PASS','cases':results,'new_entries':0,'new_FDTD':0,'labels_not_admitted_as_new_truth':True,'six_ps_truth':'NOT_RUN','V31_postsolve_adapter':'NOT_YET_LIVE_VERIFIED'})
 print('NATIVE_REEXTRACTION_COMPLETE',cid,parity,flush=True)
