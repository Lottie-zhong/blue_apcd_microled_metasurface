import csv, hashlib, json, math, re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi

ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1'); EV=ROOT/'outputs/np_k6_p0_simtime_3ps_control_v1'; RT=ROOT/'outputs/np_k6_p0_simtime_3ps_control_v1_runtime'; CASE='RUN3C_P_PILOT_HF_SIMTIME_3PS_CONTROL_V1'; ATTEMPT='attempt_001'; RUN=RT/'runtime_runs'/CASE/ATTEMPT; W=np.arange(445,456,dtype=int)
PLANES=['N1_DIAG_PML_LOWER','N1_DIAG_LOWER_OUTSIDE','N1_DIAG_LOWER_INSIDE','N1_DIAG_UPPER_INSIDE','N1_DIAG_UPPER_OUTSIDE','N1_DIAG_PML_UPPER']
def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def ah(a): return hashlib.sha256(np.ascontiguousarray(np.asarray(a).reshape(-1)).astype('<f8',copy=False).tobytes()).hexdigest()
def flat(x): return np.asarray(x).reshape(-1)
def result(fd,name):
 try:
  d=fd.getresult(name,'T'); raw={k:flat(v) for k,v in d.items() if hasattr(v,'__len__')}; return {'keys':list(d.keys()),'raw':raw,'T':raw.get('T'),'lambda':raw.get('lambda',W*1e-9)}
 except Exception:
  try:return {'keys':['transmission'],'raw':{},'T':flat(fd.transmission(name)),'lambda':W*1e-9}
  except:return None
def grating(fd,name,index):
 out={}
 for key,fn in [('fraction','grating'),('order','gratingn'),('u_x','gratingu1')]:
  try:out[key]=flat(getattr(fd,fn)(name,index+1))
  except:out[key]=None
 return out
def prop(fd,name,field):
 try:return float(fd.getnamed(name,field))
 except:return None
def csv_write(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True); fields=list(rows[0]) if rows else []
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def runtime_log():
 logs=[p for p in RUN.rglob('*.log') if p.is_file()]; text='\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in logs)
 auto=[float(x) for x in re.findall(r'Auto Shutoff:\s*([0-9.eE+-]+)',text)]; elapsed=[float(x) for x in re.findall(r'Elapsed simulation time:\s*([0-9.eE+-]+)\s*secs',text)]; iters=re.findall(r'Starting\s+([0-9]+)\s+total iterations',text)
 return {'log_paths':[str(x) for x in logs],'final_auto_shutoff':auto[-1] if auto else None,'final_elapsed_simulation_time_s':elapsed[-1] if elapsed else None,'total_iterations':int(iters[-1]) if iters else None,'auto_shutoff_threshold':1e-5,'log_tail':text[-5000:]}
ledger=json.loads((RUN/'entered_ledger.json').read_text(encoding='utf-8-sig')); post=Path(ledger.get('post_fsp_path',''))
if not post.exists(): raise RuntimeError(f'post-FSP not ready: {post}')
post_sha=sha(post); fd=lumapi.FDTD(str(post),hide=True)
try:
 tr,rr=result(fd,'transmission_monitor'),result(fd,'reflection_monitor')
 if not tr or not rr or tr['T'] is None or rr['T'] is None: raise RuntimeError('T/R unavailable')
 lam=np.rint(np.asarray(tr['lambda'])*1e9).astype(int)
 if list(lam)!=list(W): raise RuntimeError(f'wavelength grid {lam.tolist()}')
 t=np.real(tr['T']); rs=np.real(rr['T']); r=np.abs(rs); metrics=[]; orders=[]; refl=[]
 for i,wl in enumerate(W):
  g=grating(fd,'transmission_monitor',i)
  if g['fraction'] is None or g['order'] is None or g['u_x'] is None: raise RuntimeError('transmission grating API unavailable')
  frac=np.real(g['fraction']); order=np.rint(np.real(g['order'])).astype(int); ux=np.real(g['u_x']); eta={int(n):float(t[i]*frac[j]) for j,n in enumerate(order)}; p=eta.get(1,float('nan')); e0=eta.get(0,float('nan')); m=eta.get(-1,float('nan')); plus=np.flatnonzero(order==1); angle=float(np.degrees(np.arcsin(np.clip(ux[plus[0]],-1,1)))) if len(plus) else float('nan')
  for j,n in enumerate(order): orders.append({'wavelength_nm':int(wl),'order_n':int(n),'u_x':float(ux[j]),'angle_deg':float(np.degrees(np.arcsin(np.clip(ux[j],-1,1)))),'transmitted_fraction':float(frac[j]),'absolute_efficiency':float(t[i]*frac[j])})
  rg=grating(fd,'reflection_monitor',i)
  if rg['fraction'] is not None and rg['order'] is not None:
   for j,n in enumerate(np.rint(np.real(rg['order'])).astype(int)): refl.append({'wavelength_nm':int(wl),'order_n':int(n),'u_x':float(np.real(rg['u_x'][j])) if rg['u_x'] is not None else float('nan'),'reflected_fraction':float(np.real(rg['fraction'][j])),'absolute_efficiency':float(r[i]*np.real(rg['fraction'][j]))})
  f=tr['raw'].get('f'); sourcepower=float(fd.sourcepower(float(f[i]))) if f is not None else float('nan')
  metrics.append({'case_id':CASE,'wavelength_nm':int(wl),'T_total':float(t[i]),'R_signed_monitor':float(rs[i]),'R_total':float(r[i]),'closure':float(t[i]+r[i]),'signed_closure_residual':float(1-t[i]-r[i]),'sourcepower_W':sourcepower,'raw_transmitted_power_W':None,'raw_reflected_power_W':None,'normalization_path':'monitor_T_and_order_sum','transmitted_order_sum':float(np.sum(t[i]*frac)),'transmitted_order_sum_mismatch':float(np.sum(t[i]*frac)-t[i]),'eta_plus1':p,'eta_0':e0,'eta_minus1':m,'non_target_efficiency':float(t[i]-p) if np.isfinite(p) else float('nan'),'directionality':float(p/(p+m)) if np.isfinite(p) and np.isfinite(m) and p+m else float('nan'),'eta_plus1_over_minus1':float(p/m) if np.isfinite(p) and np.isfinite(m) and m else float('nan'),'plus1_transmitted_fraction':float(p/t[i]) if np.isfinite(p) and t[i] else float('nan'),'plus1_air_side_angle_deg':angle,'transmitted_order_count':int(len(order))})
 flux=[]; inv=[]
 for name in PLANES:
  d=result(fd,name); vals=d.get('T') if d else None; z=prop(fd,name,'z'); inv.append({'monitor':name,'z_m':z,'result_keys':d.get('keys',[]) if d else []})
  for i,wl in enumerate(W): flux.append({'monitor':name,'z_m':z,'wavelength_nm':int(wl),'signed_normalized_flux':float(vals[i]) if vals is not None and i<len(vals) else float('nan')})
 inv.sort(key=lambda x:x['z_m'] if x['z_m'] is not None else 1e99); csv_write(RT/'spectral_metrics_11points.csv',metrics); csv_write(EV/'spectral_metrics_11points.csv',metrics); csv_write(EV/'transmitted_orders_11points.csv',orders); csv_write(EV/'reflected_orders_11points.csv',refl); csv_write(EV/'boundary_plane_flux_spectrum.csv',flux)
 by={(x['monitor'],x['wavelength_nm']):x['signed_normalized_flux'] for x in flux}; intervals=[]
 for a,b in zip(inv,inv[1:]):
  for wl in W:
   fa,fb=by[(a['monitor'],int(wl))],by[(b['monitor'],int(wl))]; intervals.append({'from_monitor':a['monitor'],'to_monitor':b['monitor'],'wavelength_nm':int(wl),'flux_a':fa,'flux_b':fb,'delta_F':fb-fa,'abs_delta_F':abs(fb-fa) if np.isfinite(fa+fb) else float('nan')})
 csv_write(EV/'boundary_interval_flux_balance.csv',intervals)
 coord={}
 for name in ['transmission_monitor','reflection_monitor']+PLANES+['N1_DIAG_XZ_INDEX_449']:
  coord[name]={}
  for axis in ['x','y','z']:
   try:
    raw=np.asarray(fd.getdata(name,axis)); a=raw.reshape(-1); coord[name][axis]={'shape':list(raw.shape),'count':int(a.size),'min':float(np.min(a)),'max':float(np.max(a)),'monotonic_strict':bool(np.all(np.diff(a)>0)) if a.size>1 else True,'sha256':ah(a)}
   except Exception as exc:coord[name][axis]={'error':repr(exc)}
 raw_t=np.asarray(fd.getdata('transmission_monitor','power')).reshape(-1); raw_r=np.asarray(fd.getdata('reflection_monitor','power')).reshape(-1); freq=np.asarray(fd.getdata('transmission_monitor','f')).reshape(-1); sp=np.array([float(fd.sourcepower(float(x))) for x in freq]); max_t=max(abs(float(raw_t[i]/sp[i]-t[i])) for i in range(len(W))); max_r=max(abs(float(raw_r[i]/sp[i]-rs[i])) for i in range(len(W)))
 for i in range(len(W)):
  metrics[i].update({'raw_transmitted_power_W':float(np.real(raw_t[i])),'raw_reflected_power_W':float(np.real(raw_r[i])),'raw_power_origin':'direct_getdata_power','transmission_power_normalization_mismatch':float(raw_t[i]/sp[i]-t[i]),'reflection_power_normalization_mismatch':float(raw_r[i]/sp[i]-rs[i])})
 csv_write(RT/'spectral_metrics_11points.csv',metrics); csv_write(EV/'spectral_metrics_11points.csv',metrics)
 audit={'case_id':CASE,'attempt_id':ATTEMPT,'post_fsp_path':str(post),'post_fsp_sha256':post_sha,'readonly_reload':True,'run_called':False,'save_called':False,'direct_power_api':'getdata(power)','direct_power_available':True,'normalization_gate_pass':max(max_t,max_r)<=1e-8,'max_transmission_normalization_mismatch':max_t,'max_reflection_normalization_mismatch':max_r,'coordinate_hashes':coord,'solver_core_grid_equality_proven':False,'monitor_grid_coordinate_readback':True}
 (EV/'raw_power_and_grid_audit.json').write_text(json.dumps(audit,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8'); (RT/'raw_power_and_grid_audit.json').write_text(json.dumps(audit,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
 summary={'case_id':CASE,'attempt_id':ATTEMPT,'post_fsp_path':str(post),'post_fsp_sha256':post_sha,'readonly_reload':True,'run_called':False,'save_called':False,'wavelengths_nm':list(map(int,W)),'metrics':metrics,'boundary_monitor_inventory':inv,'runtime':runtime_log(),'max_abs_closure_residual':max(abs(x['signed_closure_residual']) for x in metrics),'worst_closure_wavelength_nm':int(max(metrics,key=lambda x:abs(x['signed_closure_residual']))['wavelength_nm']),'order_mismatch_max':max(abs(x['transmitted_order_sum_mismatch']) for x in metrics),'direct_power_normalization_mismatch_max':max(max_t,max_r)}
 (EV/'runtime_extraction_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8'); (RT/'runtime_extraction_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8'); print(json.dumps({'post_sha':post_sha,'max_closure':summary['max_abs_closure_residual'],'worst_wavelength':summary['worst_closure_wavelength_nm'],'order_mismatch':summary['order_mismatch_max'],'normalization_mismatch':summary['direct_power_normalization_mismatch_max']},indent=2))
finally: fd.close()
