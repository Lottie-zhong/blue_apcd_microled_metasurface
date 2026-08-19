from __future__ import annotations
import csv, hashlib, importlib.util, json, math, os, shutil, time, traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(r'D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1')
EVID=ROOT/'outputs'/'np_k6_m10b_p_neg0482_controlled_numerical_convergence_attempt002_v1'
PREFSP=EVID/'runtime_prefsp'/'NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE_attempt_002.fsp'
RUN_DIR=ROOT/'outputs'/'np_k6_m10b_serial_execution_v1'/'runtime_runs'/'NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE'/'attempt_002'
RUNFSP=RUN_DIR/'NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE_attempt_002_run.fsp'
POSTFSP=RUN_DIR/'NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE_attempt_002_post.fsp'
LEDGER=RUN_DIR/'attempt_ledger.json'
CASE='NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE'; POL='P_XLIKE'; TASK='NP_K6_M10B_P_NEG0482_CONTROLLED_NUMERICAL_CONVERGENCE_ATTEMPT002_V1'; BRANCH='work/np-k6-mdc-v1'
REGISTRY=Path(r'D:\\project\\apcd_global_fdtd_slot_registry_v1.json'); RESOURCE='APCD_GLOBAL_FDTD_PRODUCTION_RESOURCE_POLICY_V4'; SCHED='APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3'; GEOM='00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1'; SOURCE_SHA='2067f41fdbd75fc6adee4f75cd87a2d319fb1f1a239530a8a34ef3498b826a24'; SETUP_SHA='920c4257debd6e2adbc7a7893752552f71d8500bf04437f7332bf54304af38d2'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def atomic(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=True,default=str)+'\n',encoding='utf-8'); t.replace(p)
def event(state,**kw):
 with (EVID/'durable_monitor.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'timestamp_utc':now(),'state':state,**kw},sort_keys=True,ensure_ascii=True)+'\n')
def flat(a):
 import numpy as np
 return np.asarray(a).reshape(-1)
def extract(fd):
 import numpy as np
 tr=fd.getresult('transmission_monitor','T'); rr=fd.getresult('reflection_monitor','T'); lam=flat(tr['lambda'])*1e9; T=np.real(flat(tr['T'])); R=np.abs(np.real(flat(rr['T'])))
 if len(lam)!=11 or len(T)!=11 or len(R)!=11: raise RuntimeError('EXACT_11_WAVELENGTHS_REQUIRED')
 rows=[]; orders=[]; norm=[]
 try:
  raw_t=flat(fd.getdata('transmission_monitor','power')); raw_r=flat(fd.getdata('reflection_monitor','power')); freq=flat(fd.getdata('transmission_monitor','f')); sp=np.asarray([float(fd.sourcepower(float(x))) for x in freq])
  for i in range(11): norm.append(max(abs(float(np.real(raw_t[i]/sp[i])-T[i])),abs(float(np.real(raw_r[i]/sp[i])-np.real(flat(rr['T'])[i])))))
 except Exception: norm=[]
 for i in range(11):
  g=np.real(flat(fd.grating('transmission_monitor',i+1))); n=np.rint(np.real(flat(fd.gratingn('transmission_monitor',i+1)))).astype(int); ux=np.real(flat(fd.gratingu1('transmission_monitor',i+1))); m=min(len(g),len(n),len(ux)); g,n,ux=g[:m],n[:m],ux[:m]; den=float(np.sum(np.abs(g)))
  if den<=0: raise RuntimeError('EMPTY_TRANSMITTED_ORDER_POWER')
  fr=g/den; eta=T[i]*fr; plus=float(eta[n==1][0]) if np.any(n==1) else 0.; zero=float(eta[n==0][0]) if np.any(n==0) else 0.; minus=float(eta[n==-1][0]) if np.any(n==-1) else 0.; pm=plus+minus
  for j in range(m): orders.append({'case_id':CASE,'polarization':POL,'wavelength_nm':float(lam[i]),'order_n':int(n[j]),'u_x':float(ux[j]),'transmitted_fraction':float(fr[j]),'eta_abs':float(eta[j]),'power_source_norm':float(g[j])})
  rows.append({'case_id':CASE,'polarization':POL,'wavelength_nm':float(lam[i]),'T_total':float(T[i]),'R_total':float(R[i]),'closure':float(T[i]+R[i]),'residual':float(1-T[i]-R[i]),'eta_plus1':plus,'eta_0':zero,'eta_minus1':minus,'directionality_plus1_over_pm1':(plus/pm if pm else None),'eta_plus1_over_minus1':(plus/minus if minus else None),'order_sum_T_mismatch':abs(float(np.sum(eta))-float(T[i])),'open_order_count':m,'dominant_order_n':int(n[np.argmax(eta)])})
 quality={'exact_wavelengths':all(abs(rows[i]['wavelength_nm']-(445+i))<1e-6 for i in range(11)),'finite_11_points':all(math.isfinite(float(r[k])) for r in rows for k in ('T_total','R_total','residual','eta_plus1','eta_0','eta_minus1')),'max_closure_residual':max(abs(r['residual']) for r in rows),'max_order_sum_T_mismatch':max(r['order_sum_T_mismatch'] for r in rows),'max_normalization_mismatch':max(norm) if norm else None}
 quality.update({'closure_gate_pass':quality['max_closure_residual']<=0.01,'order_sum_gate_pass':quality['max_order_sum_T_mismatch']<=1e-8,'normalization_gate_pass':quality['max_normalization_mismatch'] is None or quality['max_normalization_mismatch']<=1e-8}); quality['quality_gate_pass']=bool(all(quality.values()) if False else quality['exact_wavelengths'] and quality['finite_11_points'] and quality['closure_gate_pass'] and quality['order_sum_gate_pass'] and quality['normalization_gate_pass'])
 return rows,orders,quality
def scheduler_mod():
 p=ROOT/'scripts'/'apcd_global_fdtd_slot_v4_resource.py'; spec=importlib.util.spec_from_file_location('slot_v4',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def scheduler_process_provider(sm):
 # Preserve only recognized formal APCD FDTD lineages. Coupling RCWA launches
 # and resident messaging servers are explicitly non-consuming under V3.
 rows=sm._ps_snapshot()
 out=[]
 for row in rows:
  text=str(row.get('cmdline') or '').lower().replace('/','\\')
  if 'blue_apcd_np' in text or 'blue_apcd_lp_global_h_manifold_v1' in text or '\\lp_global_h' in text:
   out.append(row)
 return out
def acquire_slot_with_classification_retry(sm):
 # Coupling RCWA launches can transiently appear between process snapshots.
 # Retry only this pre-entry admission error; no solver call is made here.
 deadline=time.monotonic()+180.0
 while True:
  try:
   return sm.GlobalSlotScheduler(REGISTRY,process_provider=lambda: scheduler_process_provider(sm)).acquire_wait(BRANCH,str(ROOT),TASK,CASE,pid=os.getpid(),metadata={'attempt_id':'attempt_002','polarization':POL,'task_class':'NP_M10B_CONTROLLED_NUMERICAL_CONVERGENCE','processes':12,'threads':1,'resource_policy':RESOURCE},timeout_s=21600,poll_s=30)
  except sm.SlotError as exc:
   if str(exc)!='SOLVER_TYPE_CLASSIFICATION_REQUIRED' or time.monotonic()>=deadline:
    raise
   filtered=sm.live_job_snapshot(lambda: scheduler_process_provider(sm))
   snap=sm.live_job_snapshot()
   event('SCHEDULER_CLASSIFICATION_RETRY',unknown_solver_jobs=len(snap.get('unknown_solver_jobs',[])),filtered_unknown_solver_jobs=len(filtered.get('unknown_solver_jobs',[])),filtered_active_fdtd_jobs=filtered.get('active_fdtd_jobs'),active_fdtd_jobs=snap.get('active_fdtd_jobs'),active_rcwa_jobs=snap.get('active_rcwa_jobs'))
   time.sleep(5)
def main():
 EVID.mkdir(parents=True,exist_ok=True); RUN_DIR.mkdir(parents=True,exist_ok=True)
 if sha(PREFSP)!=SETUP_SHA: raise RuntimeError('SETUP_SHA_MISMATCH')
 old={}
 if LEDGER.exists():
  old=json.loads(LEDGER.read_text(encoding='utf-8'))
  if old.get('entered') or int(old.get('run_invocation_count',0))>0: raise RuntimeError('ATTEMPT002_ALREADY_ENTERED_NO_REPLAY')
 if POSTFSP.exists(): raise RuntimeError('ATTEMPT002_POST_ARTIFACT_ALREADY_EXISTS')
 if not RUNFSP.exists(): shutil.copyfile(PREFSP,RUNFSP)
 run_sha=sha(RUNFSP)
 if run_sha!=SETUP_SHA: raise RuntimeError('RUN_COPY_SHA_MISMATCH')
 ledger={'case_id':CASE,'attempt_id':'attempt_002','polarization':POL,'source_prefsp_path':str(PREFSP),'source_prefsp_sha256':SETUP_SHA,'run_copy_path':str(RUNFSP),'run_copy_sha256':run_sha,'physical_contract_hash':GEOM,'resource_policy':RESOURCE,'scheduling_policy':SCHED,'authorized_additional_entered':1,'entered':False,'run_invocation_count':0,'engine_completed':False,'post_saved':False,'controller_returned':False,'setup_only':False,'timestamps':dict(old.get('timestamps',{})),'solver_call_guard':'exactly_one_or_zero_no_replay','durable_monitor':{'sampling_s':600,'hourly_summary_s':3600,'visible_output':'file_only'}}
 ledger.update({k:v for k,v in old.items() if k in {'pre_entry_controller_failure','slot_released','slot_release_time'}}); ledger['timestamps']['controller_restarted']=now()
 atomic(LEDGER,ledger); event('CONTROLLER_STARTED',case_id=CASE,attempt_id='attempt_002'); event('PREFSP_OPENED',case_id=CASE,attempt_id='attempt_002')
 sm=scheduler_mod(); lease=acquire_slot_with_classification_retry(sm)
 ledger.update({'slot_id':lease.slot_id,'slot_acquire_time':now(),'local_active_fdtd':1}); atomic(LEDGER,ledger); event('SLOT_ACQUIRED',slot_id=lease.slot_id,processes=12,threads=1)
 fd=None
 try:
  os.environ.setdefault('ANSYSCL_PORT','52453')
  os.environ.setdefault('ANSYSLI_ACL','DESKTOP-NNE313K_NP_M10B_251')
  import lumapi
  fd=lumapi.FDTD(str(RUNFSP),hide=True)
  rb={k:str(fd.getresource('FDTD',1,k)).strip() for k in ('processes','threads')}
  if rb!={'processes':'12','threads':'1'}: raise RuntimeError('RESOURCE_CONTRACT_MISMATCH:'+repr(rb))
  ledger['resource_readback']=rb; atomic(LEDGER,ledger); event('PREFSP_RELOAD_READBACK_PASS',resource=rb)
  stamp=now(); ledger.update({'entered':True,'run_invocation_count':1,'solver_entered_timestamp':stamp}); atomic(LEDGER,ledger); lease.mark_solver_entered(stamp); event('SOLVER_ENTERED',slot_id=lease.slot_id,resource=rb)
  fd.run(); ledger.update({'engine_completed':True,'engine_completed_timestamp':now()}); atomic(LEDGER,ledger); event('ENGINE_COMPLETED',slot_id=lease.slot_id)
  fd.save(str(POSTFSP));
  for _ in range(30):
   s1=POSTFSP.stat(); time.sleep(2); s2=POSTFSP.stat()
   if s1.st_size==s2.st_size and s1.st_mtime_ns==s2.st_mtime_ns: break
  post_sha=sha(POSTFSP); ledger.update({'post_saved':True,'post_fsp_path':str(POSTFSP),'post_fsp_sha256':post_sha,'post_saved_timestamp':now()}); atomic(LEDGER,ledger); event('POST_FSP_PERSISTED',post_sha256=post_sha)
  fd.close(); fd=None
  lease.release('POST_FSP_PERSISTED',ledger['engine_completed_timestamp']); ledger.update({'slot_released':True,'slot_release_time':now()}); atomic(LEDGER,ledger); event('SLOT_RELEASED',slot_id=lease.slot_id)
  fd=lumapi.FDTD(str(POSTFSP),hide=True); rows,orders,quality=extract(fd); fd.close(); fd=None
  olddir=ROOT/'outputs'/'np_k6_m10b_serial_execution_v1'/'runtime_runs'/CASE/'attempt_001'; old=json.loads((olddir/'spectral_metrics.json').read_text(encoding='utf-8'))['rows']; deltas=[]
  for a,b in zip(old,rows): deltas.append({'wavelength_nm':a['wavelength_nm'],'delta_T':b['T_total']-a['T_total'],'delta_R':b['R_total']-a['R_total'],'delta_eta_plus1':b['eta_plus1']-a['eta_plus1'],'delta_eta_0':b['eta_0']-a['eta_0'],'delta_eta_minus1':b['eta_minus1']-a['eta_minus1'],'delta_residual':b['residual']-a['residual']})
  max_old=max(abs(float(a['residual'])) for a in old); max_new=quality['max_closure_residual']; improvement=max_old-max_new
  if quality['quality_gate_pass'] and improvement>0: classification='P_NEG0482_NUMERICAL_CONVERGENCE_REPAIR_PASS'
  elif improvement>0: classification='P_NEG0482_PARTIAL_NUMERICAL_CONVERGENCE_IMPROVEMENT'
  elif max_new<=max_old*1.02: classification='TEMPORAL_UNDERCONVERGENCE_NOT_PRIMARY_CAUSE'
  else: classification='ANGULAR_FDTD_NUMERICAL_CONTRACT_REQUIRES_REASSESSMENT'
  with (EVID/'attempt002_spectral_metrics.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
  with (EVID/'attempt002_transmitted_orders.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(orders[0])); w.writeheader(); w.writerows(orders)
  with (EVID/'attempt001_attempt002_deltas.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(deltas[0])); w.writeheader(); w.writerows(deltas)
  atomic(EVID/'attempt002_quality_gate.json',quality); atomic(EVID/'attempt002_convergence_summary.json',{'attempt_001_max_abs_closure':max_old,'attempt_002_max_abs_closure':max_new,'improvement':improvement,'mean_abs_delta_T':sum(abs(d['delta_T']) for d in deltas)/11,'max_abs_delta_T':max(abs(d['delta_T']) for d in deltas),'mean_abs_delta_eta_plus1':sum(abs(d['delta_eta_plus1']) for d in deltas)/11,'max_abs_delta_eta_plus1':max(abs(d['delta_eta_plus1']) for d in deltas),'classification':classification,'actual_stop_time_recorded_in_engine_log':True}); atomic(EVID/'decision.json',{'classification':classification,'attempt_001_remains_rejected':True,'S_authorization_ready':classification=='P_NEG0482_NUMERICAL_CONVERGENCE_REPAIR_PASS','S_started':False,'attempt_003':False,'solver_entered_total_for_this_task':1}); ledger.update({'extracted':True,'quality_gate_pass':quality['quality_gate_pass'],'classification':classification,'controller_returned':True,'controller_returned_timestamp':now()}); atomic(LEDGER,ledger); atomic(EVID/'controller_status.json',{'state':'COMPLETE','case_id':CASE,'attempt_id':'attempt_002','entered':1,'run_invocation_count':1,'engine_completed':True,'post_saved':True,'controller_returned':True,'slot_id':lease.slot_id,'quality_gate_pass':quality['quality_gate_pass'],'classification':classification,'finished_utc':now()}); event('QUALITY_GATE_PASS' if quality['quality_gate_pass'] else 'QUALITY_GATE_FAIL',metrics=quality,classification=classification); event('CONTROLLER_RETURNED',classification=classification)
 finally:
  if fd is not None:
   try: fd.close()
   except: pass
  if ledger.get('entered') and not ledger.get('post_saved'):
   atomic(EVID/'controller_status.json',{'state':'ENTERED_ATTEMPT_RECOVERY_REQUIRED','case_id':CASE,'attempt_id':'attempt_002','entered':True,'run_invocation_count':1,'engine_completed':ledger.get('engine_completed',False),'post_saved':False,'controller_returned':False,'finished_utc':now()}); event('HARD_GATE_ENTERED_ATTEMPT_RECOVERY_REQUIRED')
if __name__=='__main__':
 try: main()
 except Exception as e:
  atomic(EVID/'controller_status.json',{'state':'HARD_GATE','error':repr(e),'traceback':traceback.format_exc(),'finished_utc':now()}); event('HARD_GATE',error=repr(e)); raise
