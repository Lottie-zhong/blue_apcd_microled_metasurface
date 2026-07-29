from __future__ import annotations
import csv,json,math,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];E=R/'outputs/np_k6_p1d4b_k6x_blank_run1_freeze_v1';P=R/'outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_runs/K6_BLANK_FIXED_REFERENCE_X/attempt_001/K6_BLANK_FIXED_REFERENCE_X_attempt_001_post.fsp'
def flat(x):return np.asarray(x).reshape(-1)
def main():
 import lumapi
 fdtd=lumapi.FDTD(str(P),hide=True)
 try:
  tr=fdtd.getresult('transmission_monitor','T');rr=fdtd.getresult('reflection_monitor','T');lam=flat(tr['lambda'])*1e9;T=np.real(flat(tr['T'])); rawR=np.real(flat(rr['T']));Rpower=np.abs(rawR);n=min(len(lam),len(T),len(Rpower));lam,T,Rpower=lam[:n],T[:n],Rpower[:n]
  order_records=[]; n0_rows=[]; axis=[]; order_api='grating/gratingn/gratingu1_per_frequency_index'
  for fi in range(1,n+1):
   gp=flat(fdtd.grating('transmission_monitor',fi));gn=flat(fdtd.gratingn('transmission_monitor',fi));gu=flat(fdtd.gratingu1('transmission_monitor',fi));m=min(len(gp),len(gn),len(gu)); total=float(np.sum(np.abs(gp[:m])));n0=float(np.sum(np.abs(gp[:m][gn[:m]==0])))
   n0_rows.append({'wavelength_nm':float(lam[fi-1]),'n0_fraction':n0/total if total else 0.0,'nonzero_fraction':1-n0/total if total else 1.0})
   for j in range(m): order_records.append({'wavelength_nm':float(lam[fi-1]),'grating_order_n':int(gn[j]),'u_x':float(gu[j]),'absolute_power':float(gp[j]*T[fi-1]),'normalized_efficiency':float(gp[j])})
   axis=[{'n':int(gn[j]),'u_x':float(gu[j])} for j in range(m)]
  with (E/'spectral_tr_metrics.csv').open('w',newline='',encoding='utf-8') as f:
   w=csv.DictWriter(f,fieldnames=['case_type','candidate_physics_claim','wavelength_nm','T_total','R_total','closure','residual','transmission_monitor_power','reflection_monitor_power']);w.writeheader()
   for a,b,c in zip(lam,T,Rpower):w.writerow({'case_type':'blank_calibration','candidate_physics_claim':'false','wavelength_nm':a,'T_total':b,'R_total':c,'closure':b+c,'residual':1-b-c,'transmission_monitor_power':b,'reflection_monitor_power':c})
  with (E/'transmitted_order_spectrum.csv').open('w',newline='',encoding='utf-8') as f:
   w=csv.DictWriter(f,fieldnames=['case_type','candidate_physics_claim','wavelength_nm','grating_order_n','u_x','absolute_power','normalized_efficiency']);w.writeheader()
   for row in order_records:w.writerow({'case_type':'blank_calibration','candidate_physics_claim':'false',**row})
  (E/'reflected_order_spectrum.csv').write_text('case_type,candidate_physics_claim,status\nblank_calibration,false,reflection_order_api_not_extracted\n',encoding='utf-8')
  rows=n0_rows
  (E/'order_axis_mapping.json').write_text(json.dumps({'case_type':'blank_calibration','candidate_physics_claim':False,'api':order_api,'gratingn_axis':'x','gratingu1_axis':'u_x','orders':axis},indent=2),encoding='utf-8')
  (E/'energy_closure_audit.json').write_text(json.dumps({'case_type':'blank_calibration','candidate_physics_claim':False,'wavelengths_nm':[float(x) for x in lam],'max_abs_residual':float(max(abs(1-T-Rpower))),'pass':bool(max(abs(1-T-Rpower))<=0.02)},indent=2),encoding='utf-8')
  (E/'blank_n0_dominance_audit.json').write_text(json.dumps({'case_type':'blank_calibration','candidate_physics_claim':False,'rows':rows,'min_n0_fraction':min(x['n0_fraction'] for x in rows),'max_nonzero_fraction':max(x['nonzero_fraction'] for x in rows),'pass':all(x['n0_fraction']>=.995 for x in rows)},indent=2),encoding='utf-8')
  (E/'extraction_manifest.json').write_text(json.dumps({'case_type':'blank_calibration','candidate_physics_claim':False,'post_fsp':str(P),'readonly_session':True,'run_called':False,'wavelength_count':n,'wavelengths_nm':[float(x) for x in lam],'finite':bool(np.isfinite(T).all() and np.isfinite(Rpower).all())},indent=2),encoding='utf-8')
 finally:fdtd.close()
if __name__=='__main__':main()
