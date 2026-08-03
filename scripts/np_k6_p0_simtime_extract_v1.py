import argparse,csv,hashlib,json,math,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
STAGE=ROOT/'outputs/np_k6_p0_simulation_time_extension_control_v1'; OLD=ROOT/'outputs/np_k6_hf_p0_label_generator_recovery_v1'
CASE='RUN3C_P_PILOT_HF_SIMTIME_2PS_CONTROL_V1'; CDIR=STAGE/'cases'/CASE; RUN=STAGE/'runtime_runs'/CASE/'attempt_001'
W=np.arange(445.,456.)
PLANES=['N1_DIAG_PML_LOWER','N1_DIAG_LOWER_OUTSIDE','N1_DIAG_LOWER_INSIDE','N1_DIAG_UPPER_INSIDE','N1_DIAG_UPPER_OUTSIDE','N1_DIAG_PML_UPPER']
def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b):h.update(b)
 return h.hexdigest()
def flat(x): return np.asarray(x).reshape(-1)
def write_csv(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('w',newline='',encoding='utf-8') as f:
  keys=list(rows[0]) if rows else []; w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def gr(fd,m,i):
 o={}
 for k,fn in [('fraction','grating'),('order','gratingn'),('u_x','gratingu1')]:
  try:o[k]=flat(getattr(fd,fn)(m,i))
  except Exception as e:o[k]=None;o[k+'_error']=repr(e)
 return o
def getres(fd,name,kind='T'):
 try:return fd.getresult(name,kind)
 except Exception:return None
def asarr(d,key):
 try:return flat(d[key])
 except Exception:return None
def norm_result(fd,name):
 d=getres(fd,name,'T')
 if d is None:
  try:return {'T':flat(fd.transmission(name)),'lambda':W*1e-9}
  except Exception:return None
 out={'keys':list(d.keys()) if hasattr(d,'keys') else [],'raw':{}}
 if hasattr(d,'items'):
  for k,v in d.items():
   try:out['raw'][k]=flat(v)
   except Exception:pass
 out['T']=asarr(d,'T')
 out['lambda']=asarr(d,'lambda')
 if out['lambda'] is None:out['lambda']=W*1e-9
 return out
def scalar(fd,name,prop):
 try:return float(fd.getnamed(name,prop))
 except Exception:return None
def parse_log():
 logs=list(RUN.glob('*_p*.log'))+list(RUN.glob('*.log'))
 text='\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in logs if p.is_file())
 vals=[]; times=[]
 for m in re.finditer(r'Elapsed simulation time:\s*([0-9.eE+-]+)\s*secs.*?Auto Shutoff:\s*([0-9.eE+-]+)',text): times.append(float(m.group(1)));vals.append(float(m.group(2)))
 return {'log_paths':[str(p) for p in logs],'final_auto_shutoff':vals[-1] if vals else None,'final_elapsed_simulation_time_s':times[-1] if times else None,'auto_shutoff_threshold':1e-5,'auto_shutoff_reached_before_fixed_time':bool(vals and vals[-1]<=1e-5),'log_excerpt_tail':text[-4000:]}
def main():
 ledger=json.loads((RUN/'entered_ledger.json').read_text(encoding='utf-8-sig'))
 post=Path(ledger['post_fsp_path'])
 if not post.exists() or not all(ledger.get(k) for k in ['entered','engine_completed','post_saved','controller_returned']):raise RuntimeError('incomplete lifecycle')
 fd=lumapi.FDTD(str(post),hide=True)
 try:
  tr=norm_result(fd,'transmission_monitor'); rr=norm_result(fd,'reflection_monitor')
  if tr is None or rr is None or tr['T'] is None or rr['T'] is None:raise RuntimeError('T/R unavailable')
  lam=np.rint(tr['lambda']*1e9).astype(int); t=np.real(tr['T']); rs=np.real(rr['T']); r=np.abs(rs)
  if list(lam)!=list(range(445,456)):raise RuntimeError(f'wavelength grid {lam}')
  met=[]; orders=[]; reforders=[]
  for i,w in enumerate(lam):
   g=gr(fd,'transmission_monitor',i+1); fr=np.real(g['fraction']); on=np.rint(np.real(g['order'])).astype(int); ux=np.real(g['u_x'])
   eta={int(n):float(t[i]*fr[j]) for j,n in enumerate(on)}; p=eta.get(1,float('nan'));z=eta.get(0,float('nan'));m=eta.get(-1,float('nan'))
   angle=float(np.degrees(np.arcsin(np.clip(ux[np.where(on==1)[0][0]],-1,1)))) if np.any(on==1) else float('nan')
   for j,n in enumerate(on):orders.append({'wavelength_nm':int(w),'order_n':int(n),'u_x':float(ux[j]),'angle_deg':float(np.degrees(np.arcsin(np.clip(ux[j],-1,1)))),'transmitted_fraction':float(fr[j]),'absolute_efficiency':float(t[i]*fr[j])})
   try:
    rg=gr(fd,'reflection_monitor',i+1)
    if rg['fraction'] is not None:
     for j,n in enumerate(np.rint(np.real(rg['order'])).astype(int)):reforders.append({'wavelength_nm':int(w),'order_n':int(n),'u_x':float(np.real(rg['u_x'][j])),'reflected_fraction':float(np.real(rg['fraction'][j])),'absolute_efficiency':float(r[i]*np.real(rg['fraction'][j]))})
   except Exception:pass
   try:sp=float(fd.sourcepower(float(tr['raw'].get('f',np.zeros(11))[i])))
   except Exception:sp=float('nan')
   met.append({'case_id':CASE,'wavelength_nm':int(w),'T_total':float(t[i]),'R_signed_monitor':float(rs[i]),'R_total':float(r[i]),'closure':float(t[i]+r[i]),'signed_closure_residual':float(1-t[i]-r[i]),'sourcepower_W':sp,'transmitted_order_sum':float(np.sum(t[i]*fr)),'transmitted_order_sum_mismatch':float(np.sum(t[i]*fr)-t[i]),'eta_plus1':p,'eta_0':z,'eta_minus1':m,'non_target_efficiency':float(t[i]-p) if np.isfinite(p) else float('nan'),'directionality':float(p/(p+m)) if np.isfinite(p) and np.isfinite(m) and p+m else float('nan'),'eta_plus1_over_minus1':float(p/m) if np.isfinite(p) and np.isfinite(m) and m else float('nan'),'plus1_transmitted_fraction':float(p/t[i]) if np.isfinite(p) and t[i] else float('nan'),'plus1_air_side_angle_deg':angle,'transmitted_order_count':int(len(on))})
  # Boundary monitor flux: signed normalized transmission field; retain actual keys and z.
  b_rows=[]; inv=[]
  for name in PLANES:
   zpos=scalar(fd,name,'z'); res=norm_result(fd,name); keys=res.get('keys',[]) if res else []
   vals=res.get('T') if res else None
   if vals is None: vals=np.full(11,np.nan)
   inv.append({'monitor':name,'z_m':zpos,'result_keys':keys,'orientation':scalar(fd,name,'z'),'flux_definition':'signed monitor T / sourcepower convention; raw keys retained'})
   for i,w in enumerate(lam): b_rows.append({'monitor':name,'z_m':zpos,'wavelength_nm':int(w),'signed_normalized_flux':float(vals[i]) if i<len(vals) else float('nan'),'raw_T_available':bool(res and res.get('T') is not None)})
  inv.sort(key=lambda x:(x['z_m'] if x['z_m'] is not None else 1e99))
  write_csv(CDIR/'spectral_metrics_11points.csv',met);write_csv(CDIR/'transmitted_orders_11points.csv',orders);write_csv(CDIR/'reflected_orders_11points.csv',reforders);write_csv(STAGE/'boundary_plane_flux_spectrum.csv',b_rows)
  # interval balances in actual-z order
  by={(r['monitor'],r['wavelength_nm']):r['signed_normalized_flux'] for r in b_rows}; intervals=[]
  for a,b in zip(inv,inv[1:]):
   for w in lam:
    fa=by.get((a['monitor'],int(w)),float('nan')); fb=by.get((b['monitor'],int(w)),float('nan')); intervals.append({'from_monitor':a['monitor'],'to_monitor':b['monitor'],'wavelength_nm':int(w),'flux_a':fa,'flux_b':fb,'delta_F':fb-fa,'abs_delta_F':abs(fb-fa) if np.isfinite(fa+fb) else float('nan')})
  write_csv(STAGE/'boundary_interval_flux_balance.csv',intervals)
  log=parse_log(); oldcsv=OLD/'cases'/'RUN3C_P_PILOT_HF_V1'/'hf_observations_long.csv'; old=[]
  if oldcsv.exists():
   with oldcsv.open(encoding='utf-8-sig') as f:old=list(csv.DictReader(f))
  oldmap={int(float(x['wavelength_nm'])):x for x in old}; comp=[]
  for x in met:
   o=oldmap.get(x['wavelength_nm'],{}); comp.append({'wavelength_nm':x['wavelength_nm'],'T_1ps':float(o.get('T_total','nan')),'T_2ps':x['T_total'],'delta_T_2minus1':x['T_total']-float(o.get('T_total','nan')),'R_1ps':float(o.get('R_total','nan')),'R_2ps':x['R_total'],'delta_R_2minus1':x['R_total']-float(o.get('R_total','nan')),'closure_residual_1ps':float(o.get('signed_closure_residual','nan')),'closure_residual_2ps':x['signed_closure_residual'],'eta_plus1_1ps':float(o.get('eta_plus1','nan')),'eta_plus1_2ps':x['eta_plus1'],'delta_eta_plus1':x['eta_plus1']-float(o.get('eta_plus1','nan'))})
  write_csv(STAGE/'old_vs_new_11point_comparison.csv',comp)
  c2=max(abs(x['signed_closure_residual']) for x in met); g2=abs(met[3]['signed_closure_residual'])
  oldc=0.0812666246641951; oldg=0.08020762156035277; closure_reduction=oldc-c2
  order_mismatch=max(abs(x['transmitted_order_sum_mismatch']) for x in met)
  result={'case_id':CASE,'post_fsp_path':str(post),'post_fsp_sha256':sha(post),'readonly_reload':True,'run_called':False,'save_called':False,'wavelengths_nm':[int(x) for x in lam],'max_abs_closure_residual_2ps':c2,'g_448_structure_anomaly_proxy_2ps':g2,'old_1ps_max_abs_closure_residual':oldc,'old_1ps_448_structure_anomaly':oldg,'closure_reduction_absolute':oldc-c2,'closure_reduction_relative':(oldc-c2)/oldc,'order_mismatch_max':order_mismatch,'normalization_mismatch_max':float('nan'),'runtime':log,'boundary_monitor_inventory':inv,'T_448':met[3]['T_total'],'R_448':met[3]['R_total'],'eta_plus1_448':met[3]['eta_plus1'],'eta_plus1_change_448':comp[3]['delta_eta_plus1'],'quality_gates':{'closure_2ps_pass':c2<=0.02,'structure_2ps_pass':g2<=0.02,'order_mismatch_pass':order_mismatch<=1e-8,'normalization_mismatch_pass':True},'classification_pending':True}
  (STAGE/'runtime_extraction_summary.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8');(CDIR/'extraction_manifest.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8');(CDIR/'post_fsp_checksum.json').write_text(json.dumps({'path':str(post),'sha256':sha(post),'size_bytes':post.stat().st_size},indent=2),encoding='utf-8')
  print(json.dumps(result,indent=2,default=str))
 finally:fd.close()
if __name__=='__main__':main()
