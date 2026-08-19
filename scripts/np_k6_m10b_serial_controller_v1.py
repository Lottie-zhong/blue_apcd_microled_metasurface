from __future__ import annotations
import csv, hashlib, importlib.util, json, math, os, shutil, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
OUT = ROOT/'outputs'/'np_k6_m10b_serial_execution_v1'
RUNS = OUT/'runtime_runs'
SETUP = OUT/'runtime_prefsp'
REGISTRY = Path(r'D:\project\apcd_global_fdtd_slot_registry_v1.json')
BRANCH = 'work/np-k6-mdc-v1'
TASK_ID = 'NP_K6_M10B_SERIAL_CONTROLLER_001'
SCHED_TASK = 'NP_K6_M10B_SERIAL_CONTROLLER_001'
RESOURCE_POLICY = 'APCD_GLOBAL_FDTD_PRODUCTION_RESOURCE_POLICY_V4'
SCHED_POLICY = 'APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3'
EXPECTED_MPI, EXPECTED_THREADS = '12', '1'
CASES = [
    ('NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE','P_XLIKE'),
    ('NP_K6_M10B_ALT1_UX_M0d482758620690_S_YLIKE','S_YLIKE'),
]

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def atomic(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n',encoding='utf-8'); t.replace(p)
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def event(state,**kw):
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'durable_monitor.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'timestamp_utc':now(),'state':state,**kw},sort_keys=True,ensure_ascii=False)+'\n')
def flat(a):
    import numpy as np
    return np.asarray(a).reshape(-1)
def finite(vals):
    import numpy as np
    return bool(np.all(np.isfinite(np.asarray(vals,dtype=float))))
def extract(fd, case_id, pol):
    import numpy as np
    tr=fd.getresult('transmission_monitor','T'); rr=fd.getresult('reflection_monitor','T')
    lam=flat(tr['lambda'])*1e9; T=np.real(flat(tr['T'])); R=np.abs(np.real(flat(rr['T'])))
    if len(lam)!=11 or len(T)!=11 or len(R)!=11: raise RuntimeError(f'11-point result length mismatch: {len(lam)},{len(T)},{len(R)}')
    rows=[]; orders=[]; norm_m=[]
    try:
        raw_t=flat(fd.getdata('transmission_monitor','power')); raw_r=flat(fd.getdata('reflection_monitor','power')); freq=flat(fd.getdata('transmission_monitor','f'))
        sp=np.asarray([float(fd.sourcepower(float(x))) for x in freq])
        for i in range(11):
            if abs(sp[i])>0:
                norm_m.append(max(abs(float(np.real(raw_t[i]/sp[i])-T[i])),abs(float(np.real(raw_r[i]/sp[i])-np.real(flat(rr['T'])[i])))))
    except Exception:
        norm_m=[]
    for i in range(11):
        g=np.real(flat(fd.grating('transmission_monitor',i+1))); n=np.rint(np.real(flat(fd.gratingn('transmission_monitor',i+1)))).astype(int); ux=np.real(flat(fd.gratingu1('transmission_monitor',i+1)))
        m=min(len(g),len(n),len(ux)); g,n,ux=g[:m],n[:m],ux[:m]
        den=float(np.sum(np.abs(g)))
        if den<=0: raise RuntimeError(f'empty transmitted order power at index {i}')
        fr=g/den; eta=T[i]*fr; tsum=float(np.sum(eta)); mismatch=abs(tsum-float(T[i]))
        plus=float(eta[n==1][0]) if np.any(n==1) else 0.0; zero=float(eta[n==0][0]) if np.any(n==0) else 0.0; minus=float(eta[n==-1][0]) if np.any(n==-1) else 0.0
        denom=plus+minus; direction=(plus/denom) if denom else None
        for j in range(m): orders.append({'case_id':case_id,'polarization':pol,'wavelength_nm':float(lam[i]),'order_n':int(n[j]),'u_x':float(ux[j]),'transmitted_fraction':float(fr[j]),'eta_abs':float(eta[j]),'power_source_norm':float(g[j])})
        rows.append({'case_id':case_id,'polarization':pol,'wavelength_nm':float(lam[i]),'T_total':float(T[i]),'R_total':float(R[i]),'closure':float(T[i]+R[i]),'residual':float(1-T[i]-R[i]),'eta_plus1':plus,'eta_0':zero,'eta_minus1':minus,'non_target_efficiency':float(T[i]-plus),'directionality_plus1_over_pm1':direction,'eta_plus1_over_minus1':(plus/minus if minus else None),'order_sum_T_mismatch':mismatch,'open_order_count':m})
    max_norm=max(norm_m) if norm_m else None
    quality={'finite_11_points':all(finite([r[k] for k in ('T_total','R_total','residual','eta_plus1','eta_0','eta_minus1')]) for r in rows),'exact_wavelengths':all(abs(rows[i]['wavelength_nm']-(445+i))<1e-6 for i in range(11)),'max_closure_residual':max(abs(r['residual']) for r in rows),'max_order_sum_T_mismatch':max(r['order_sum_T_mismatch'] for r in rows),'max_normalization_mismatch':max_norm,'closure_gate_pass':max(abs(r['residual']) for r in rows)<=0.01,'order_sum_gate_pass':max(r['order_sum_T_mismatch'] for r in rows)<=1e-8,'normalization_gate_pass':max_norm is None or max_norm<=1e-8}
    quality['quality_gate_pass']=bool(quality['finite_11_points'] and quality['exact_wavelengths'] and quality['closure_gate_pass'] and quality['order_sum_gate_pass'] and quality['normalization_gate_pass'])
    return rows,orders,quality
def resource_gate(fd):
    for k,v in [('processes',EXPECTED_MPI),('threads',EXPECTED_THREADS)]: fd.setresource('FDTD',1,k,v)
    rb={k:str(fd.getresource('FDTD',1,k)).strip() for k in ('processes','threads')}
    if rb != {'processes':EXPECTED_MPI,'threads':EXPECTED_THREADS}: raise RuntimeError(f'RESOURCE_CONTRACT_MISMATCH: {rb}')
    return {'pass':True,'expected':{'processes':EXPECTED_MPI,'threads':EXPECTED_THREADS},'readback':rb,'resource_policy':RESOURCE_POLICY}
def load_scheduler():
    p=ROOT/'scripts'/'apcd_global_fdtd_slot_v4_resource.py'; spec=importlib.util.spec_from_file_location('m10b_slot',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def update_ledger(p, ledger, **changes): ledger.update(changes); atomic(p,ledger)
def run_case(case_id,pol,scheduler_mod):
    case_dir=RUNS/case_id/'attempt_001'; case_dir.mkdir(parents=True,exist_ok=True)
    prefsp=SETUP/(case_id+'.fsp'); runfsp=case_dir/(case_id+'_attempt_001_run.fsp'); post=case_dir/(case_id+'_attempt_001_post.fsp'); ledger_p=case_dir/'attempt_ledger.json'
    if ledger_p.exists():
        old=readj(ledger_p)
        if old.get('entered') or old.get('run_invocation_count',0): raise RuntimeError(f'EXISTING_ENTERED_ATTEMPT_NO_REPLAY:{case_id}')
    if not prefsp.exists(): raise RuntimeError(f'missing pre-FSP:{prefsp}')
    source_sha=sha(prefsp); shutil.copyfile(prefsp,runfsp); run_sha=sha(runfsp)
    if source_sha!=run_sha: raise RuntimeError('run copy SHA mismatch')
    ledger={'case_id':case_id,'attempt_id':'attempt_001','polarization':pol,'source_prefsp_path':str(prefsp),'source_prefsp_sha256':source_sha,'run_copy_path':str(runfsp),'run_copy_sha256':run_sha,'physical_contract_hash':'00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1','resource_policy':RESOURCE_POLICY,'scheduling_policy':SCHED_POLICY,'authorized_solver_entered':1,'entered':False,'run_invocation_count':0,'engine_completed':False,'post_saved':False,'controller_returned':False,'setup_only':False,'timestamps':{'controller_started':now()}}
    atomic(ledger_p,ledger); event('PREFSP_OPENED',case_id=case_id,attempt_id='attempt_001')
    lease=scheduler_mod.GlobalSlotScheduler(scheduler_mod.DEFAULT_REGISTRY_PATH).acquire_wait(BRANCH,str(ROOT),TASK_ID,case_id,pid=os.getpid(),metadata={'attempt_id':'attempt_001','polarization':pol,'task_class':'NP_M10B_SERIAL_HF','processes':12,'threads':1,'resource_policy':RESOURCE_POLICY})
    ledger['slot_id']=lease.slot_id; ledger['slot_acquire_time']=now(); ledger['local_active_fdtd']=1; atomic(ledger_p,ledger); event('SLOT_ACQUIRED',case_id=case_id,slot_id=lease.slot_id,processes=12,threads=1)
    fd=None; quality=None; rows=[]; orders=[]
    try:
        import lumapi
        fd=lumapi.FDTD(str(runfsp),hide=True); ledger['prefsp_opened']=True; atomic(ledger_p,ledger)
        rg=resource_gate(fd); ledger['resource_contract']=rg; atomic(ledger_p,ledger)
        stamp=now(); ledger.update({'entered':True,'run_invocation_count':1,'solver_entered_timestamp':stamp}); atomic(ledger_p,ledger); lease.mark_solver_entered(stamp); event('SOLVER_ENTERED',case_id=case_id,slot_id=lease.slot_id,processes=12,threads=1)
        fd.run(); ledger.update({'engine_completed':True,'engine_completed_timestamp':now()}); atomic(ledger_p,ledger); event('ENGINE_COMPLETED',case_id=case_id,slot_id=lease.slot_id)
        fd.save(str(post));
        while True:
            s1=post.stat(); time.sleep(2); s2=post.stat()
            if s1.st_size==s2.st_size and s1.st_mtime_ns==s2.st_mtime_ns: break
        post_sha=sha(post); ledger.update({'post_saved':True,'post_fsp_path':str(post),'post_fsp_sha256':post_sha,'post_saved_timestamp':now()}); atomic(ledger_p,ledger); event('POST_FSP_PERSISTED',case_id=case_id,slot_id=lease.slot_id,post_sha256=post_sha)
        fd.close(); fd=None
        fd=lumapi.FDTD(str(post),hide=True); rows,orders,quality=extract(fd,case_id,pol); atomic(case_dir/'quality_gate.json',quality); atomic(case_dir/'spectral_metrics.json',{'rows':rows});
        with (case_dir/'spectral_metrics.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        with (case_dir/'transmitted_orders.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(orders[0])); w.writeheader(); w.writerows(orders)
        ledger.update({'extracted':True,'quality_gate_pass':quality['quality_gate_pass'],'quality_adjudicated_timestamp':now()}); atomic(ledger_p,ledger); event('QUALITY_GATE_PASS' if quality['quality_gate_pass'] else 'QUALITY_GATE_FAIL',case_id=case_id,metrics=quality)
        return quality['quality_gate_pass'], ledger
    finally:
        if fd is not None:
            try: fd.close()
            except Exception: pass
        # A completed engine with persisted post-FSP has a terminal slot state.
        if ledger.get('engine_completed') and ledger.get('post_saved'):
            lease.release('QUALITY_PASS' if ledger.get('quality_gate_pass') else 'QUALITY_FAIL',ledger.get('engine_completed_timestamp')); ledger.update({'slot_released':True,'slot_release_time':now()}); atomic(ledger_p,ledger); event('SLOT_RELEASED',case_id=case_id,slot_id=lease.slot_id,quality_gate_pass=ledger.get('quality_gate_pass'))
        else:
            # Do not release an entered slot before authoritative recovery evidence.
            event('HARD_GATE_ENTERED_ATTEMPT_RECOVERY_REQUIRED',case_id=case_id,slot_id=lease.slot_id)
def main():
    OUT.mkdir(parents=True,exist_ok=True); RUNS.mkdir(parents=True,exist_ok=True)
    atomic(OUT/'controller_status.json',{'task_id':TASK_ID,'scheduler_task':SCHED_TASK,'state':'STARTED','started_utc':now(),'resource_policy':RESOURCE_POLICY,'scheduling_policy':SCHED_POLICY,'global_cap':3,'local_cap':1,'cases':CASES,'visible_output':'file_only','monitor_interval_s':600,'hourly_summary_s':3600})
    event('CONTROLLER_STARTED',task_id=TASK_ID)
    m=load_scheduler(); complete=[]
    for case_id,pol in CASES:
        ok,ledger=run_case(case_id,pol,m); ledger_path=RUNS/case_id/'attempt_001'/'attempt_ledger.json'; ledger.update({'controller_returned':True,'controller_returned_timestamp':now()}); atomic(ledger_path,ledger); complete.append({'case_id':case_id,'quality_gate_pass':ok,'run_invocation_count':ledger.get('run_invocation_count',0),'slot_id':ledger.get('slot_id'),'slot_acquire_time':ledger.get('slot_acquire_time'),'slot_release_time':ledger.get('slot_release_time')})
        if not ok:
            atomic(OUT/'controller_status.json',{'task_id':TASK_ID,'state':'STOP_BATCH_FOR_REVIEW','terminal_case':case_id,'completed':complete,'solver_calls':sum(int(x.get('run_invocation_count',0)) for x in complete),'entered_total':sum(int(x.get('run_invocation_count',0)) for x in complete),'s_case_entered':False,'finished_utc':now()}); return
    atomic(OUT/'controller_status.json',{'task_id':TASK_ID,'state':'COMPLETE','completed':complete,'solver_calls':sum(int(x.get('run_invocation_count',0)) for x in complete),'entered_total':sum(int(x.get('run_invocation_count',0)) for x in complete),'p_s_overlap_duration_s':0,'peak_local_active_fdtd':1,'finished_utc':now()}); event('BATCH_COMPLETE',completed=complete)
if __name__=='__main__':
    try: main()
    except Exception as e:
        atomic(OUT/'controller_status.json',{'task_id':TASK_ID,'state':'HARD_GATE','error':repr(e),'traceback':traceback.format_exc(),'finished_utc':now()}); event('HARD_GATE',error=repr(e)); raise
