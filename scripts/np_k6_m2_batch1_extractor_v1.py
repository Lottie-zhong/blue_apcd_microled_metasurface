import argparse,csv,hashlib,json,math,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python'); import lumapi
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1'); STAGE=ROOT/'outputs/np_k6_m2_batch1_hf_acquisition_v1'; W=list(range(445,456)); PLANES=['N1_DIAG_PML_LOWER','N1_DIAG_LOWER_OUTSIDE','N1_DIAG_LOWER_INSIDE','N1_DIAG_UPPER_INSIDE','N1_DIAG_UPPER_OUTSIDE','N1_DIAG_PML_UPPER']
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def flat(x): return np.asarray(x).reshape(-1)
def write(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True); f=p.open('w',newline='',encoding='utf-8');
 if not rows: f.close(); return
 w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows); f.close()
def gr(fd,name,i):
 out={}
 for k,fn in [('fraction','grating'),('order','gratingn'),('u_x','gratingu1')]:
  try: out[k]=flat(getattr(fd,fn)(name,i+1))
  except Exception: out[k]=None
 return out
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--case',required=True); a=ap.parse_args(); case=a.case; cdir=STAGE/'cases'/case; run=STAGE/'runtime_runs'/case/'attempt_001'; led=json.loads((run/'entered_ledger.json').read_text(encoding='utf-8-sig')); post=Path(led['post_fsp_path'])
 if not (led.get('entered') and led.get('engine_completed') and led.get('controller_returned') and led.get('post_saved') and post.exists()): raise RuntimeError('V2 lifecycle incomplete')
 fd=lumapi.FDTD(str(post),hide=True)
 try:
  tr=fd.getresult('transmission_monitor','T'); rr=fd.getresult('reflection_monitor','T'); lam=flat(tr['lambda'])*1e9; freq=flat(tr['f']) if 'f' in tr else np.zeros(len(W)); t=np.real(flat(tr['T'])); rs=np.real(flat(rr['T'])); r=np.abs(rs)
  if list(np.rint(lam).astype(int))!=W: raise RuntimeError(f'wavelength mismatch {lam}')
  metrics=[]; orders=[]; refl=[]; norm=[]
  for i,wl in enumerate(W):
   g=gr(fd,'transmission_monitor',i)
   if any(g[k] is None for k in ['fraction','order','u_x']): raise RuntimeError('order API unavailable')
   fr=np.real(g['fraction']); oo=np.rint(np.real(g['order'])).astype(int); ux=np.real(g['u_x']); eta={int(n):float(t[i]*fr[j]) for j,n in enumerate(oo)}; p=eta.get(1,float('nan')); z=eta.get(0,float('nan')); m=eta.get(-1,float('nan')); ix=np.where(oo==1)[0]; ang=float(np.degrees(np.arcsin(np.clip(ux[ix[0]],-1,1)))) if len(ix) else float('nan')
   for j,n in enumerate(oo): orders.append({'case_id':case,'wavelength_nm':int(wl),'order_n':int(n),'u_x':float(ux[j]),'angle_deg':float(np.degrees(np.arcsin(np.clip(ux[j],-1,1)))),'transmitted_fraction':float(fr[j]),'absolute_efficiency':float(t[i]*fr[j])})
   rg=gr(fd,'reflection_monitor',i)
   if rg['fraction'] is not None and rg['order'] is not None and rg['u_x'] is not None:
    for j,n in enumerate(np.rint(np.real(rg['order'])).astype(int)): refl.append({'case_id':case,'wavelength_nm':int(wl),'order_n':int(n),'u_x':float(np.real(rg['u_x'][j])),'angle_deg':float(np.degrees(np.arcsin(np.clip(np.real(rg['u_x'][j]),-1,1)))),'reflected_fraction':float(np.real(rg['fraction'][j])),'absolute_efficiency':float(r[i]*np.real(rg['fraction'][j]))})
   sp=float(fd.sourcepower(float(freq[i]))) if len(freq)>i else float('nan'); rawt=rawr=float('nan')
   try:
    rawt=float(np.real(flat(fd.getdata('transmission_monitor','power'))[i])); rawr=float(np.real(flat(fd.getdata('reflection_monitor','power'))[i])); norm.append(max(abs(rawt/sp-t[i]),abs(rawr/sp-rs[i])))
   except Exception: norm.append(float('nan'))
   metrics.append({'case_id':case,'wavelength_nm':int(wl),'frequency_hz':float(freq[i]) if len(freq)>i else float('nan'),'T_total':float(t[i]),'R_total':float(r[i]),'R_signed_monitor':float(rs[i]),'closure':float(t[i]+r[i]),'signed_closure_residual':float(1-t[i]-r[i]),'sourcepower_W':sp,'raw_transmitted_power_W':rawt,'raw_reflected_power_W':rawr,'transmitted_order_sum':float(np.sum(t[i]*fr)),'transmitted_order_sum_mismatch':float(np.sum(t[i]*fr)-t[i]),'eta_plus1':p,'eta_0':z,'eta_minus1':m,'non_target_efficiency':float(t[i]-p) if np.isfinite(p) else float('nan'),'directionality':float(p/(p+m)) if np.isfinite(p) and np.isfinite(m) and p+m else float('nan'),'eta_plus1_over_minus1':float(p/m) if np.isfinite(p) and np.isfinite(m) and m else float('nan'),'plus1_transmitted_fraction':float(p/t[i]) if np.isfinite(p) and t[i] else float('nan'),'plus1_air_side_angle_deg':ang,'transmitted_order_count':int(len(oo))})
  flux=[]; zs={}
  for name in PLANES:
   try: z=float(fd.getnamed(name,'z')); zs[name]=z; vals=flat(fd.getresult(name,'T')['T'])
   except Exception: z=float('nan'); vals=np.full(len(W),np.nan); zs[name]=z
   for i,wl in enumerate(W): flux.append({'case_id':case,'monitor':name,'z_m':z,'wavelength_nm':int(wl),'signed_normalized_flux':float(np.real(vals[i])) if len(vals)>i else float('nan')})
  intervals=[]; order=sorted([(n,zs[n]) for n in PLANES],key=lambda x:x[1] if np.isfinite(x[1]) else 1e99)
  by={(x['monitor'],x['wavelength_nm']):x['signed_normalized_flux'] for x in flux}
  for (na,za),(nb,zb) in zip(order,order[1:]):
   for wl in W: intervals.append({'case_id':case,'from_monitor':na,'to_monitor':nb,'wavelength_nm':wl,'delta_F':by[(nb,wl)]-by[(na,wl)],'abs_delta_F':abs(by[(nb,wl)]-by[(na,wl)])})
  idx=[x for x in intervals if x['wavelength_nm']==448 and x['from_monitor']=='N1_DIAG_LOWER_INSIDE' and x['to_monitor']=='N1_DIAG_UPPER_INSIDE']; structure=float(idx[0]['delta_F']) if idx else float('nan')
  closure=max(abs(x['signed_closure_residual']) for x in metrics); osum=max(abs(x['transmitted_order_sum_mismatch']) for x in metrics); direct=max([x for x in norm if np.isfinite(x)] or [float('nan')]); finite=all(np.isfinite([x['T_total'],x['R_total'],x['eta_plus1'],x['eta_0'],x['eta_minus1']]).all() for x in metrics)
  write(cdir/'hf_observations_long.csv',metrics); write(cdir/'hf_transmitted_orders_long.csv',orders); write(cdir/'hf_reflected_orders_long.csv',refl); write(cdir/'boundary_plane_flux_spectrum.csv',flux); write(cdir/'boundary_interval_flux_balance.csv',intervals)
  manifest={'schema_version':'np_k6_m2_batch1_extraction_manifest','case_id':case,'attempt_id':'attempt_001','post_fsp_path':str(post),'post_fsp_sha256':sha(post),'readonly_reload':True,'run_called':False,'save_called':False,'wavelengths_nm':W,'exact_11_points':True,'all_finite':finite,'max_abs_closure_residual':closure,'structure_anomaly_448':structure,'order_sum_mismatch_max':osum,'direct_raw_sourcepower_mismatch_max':direct,'gate_closure_pass':closure<=0.01,'gate_structure_pass':np.isfinite(structure) and abs(structure)<=0.01,'gate_order_sum_pass':osum<=1e-8,'gate_direct_normalization_pass':bool(np.isfinite(direct) and direct<=1e-8),'batch_id':'NP_K6_M2_BATCH1','active_learning_batch':1,'quality_gate_pass':bool(finite and closure<=0.01 and np.isfinite(structure) and abs(structure)<=0.01 and osum<=1e-8 and np.isfinite(direct) and direct<=1e-8),'dominant_order':int(max(orders,key=lambda x:x['absolute_efficiency'])['order_n'])}
  (cdir/'extraction_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8'); (cdir/'post_fsp_checksum.json').write_text(json.dumps({'path':str(post),'sha256':sha(post),'size_bytes':post.stat().st_size,'sha_stable':sha(post)==led.get('post_fsp_sha256')},indent=2)+'\n',encoding='utf-8'); led.update({'extraction_completed':True,'quality_gate_pass':manifest['quality_gate_pass'],'extraction_manifest_path':str(cdir/'extraction_manifest.json'),'training_label':False,'provisional_hf_label':bool(manifest['quality_gate_pass'])}); (run/'entered_ledger.json').write_text(json.dumps(led,indent=2)+'\n',encoding='utf-8'); (cdir/'attempt_ledger.json').write_text(json.dumps(led,indent=2)+'\n',encoding='utf-8'); print(json.dumps(manifest,indent=2,default=str))
 finally: fd.close()
if __name__=='__main__': main()
