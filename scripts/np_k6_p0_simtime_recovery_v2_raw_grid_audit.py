import csv,hashlib,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
EV=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2'
RT=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2_runtime'
post=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2_runtime/runtime_runs/RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2/attempt_001/RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2_attempt_001_post.fsp'
W=np.arange(445,456,dtype=int)
def ah(a):
 a=np.asarray(a)
 return hashlib.sha256(np.ascontiguousarray(a).astype('<f8',copy=False).tobytes()).hexdigest()
def get(fd,name,key): return np.asarray(fd.getdata(name,key)).reshape(-1)
fd=lumapi.FDTD(str(post),hide=True)
try:
 tf=get(fd,'transmission_monitor','power'); rf=get(fd,'reflection_monitor','power'); f=get(fd,'transmission_monitor','f'); sp=np.array([float(fd.sourcepower(float(x))) for x in f])
 tr=fd.getresult('transmission_monitor','T'); rr=fd.getresult('reflection_monitor','T'); T=np.real(np.asarray(tr['T']).reshape(-1)); Rsign=np.real(np.asarray(rr['T']).reshape(-1))
 rows=list(csv.DictReader((RT/'spectral_metrics_11points.csv').open(encoding='utf-8')))
 direct=[]; max_t=0.; max_r=0.
 for i,row in enumerate(rows):
  pt=float(np.real(tf[i])); pr=float(np.real(rf[i])); nt=pt/sp[i]; nr=pr/sp[i]; dt=nt-T[i]; dr=nr-Rsign[i]; max_t=max(max_t,abs(dt)); max_r=max(max_r,abs(dr)); row.update({'sourcepower_W':float(sp[i]),'raw_transmitted_power_W':pt,'raw_reflected_power_W':pr,'raw_power_origin':'direct_getdata_power','transmission_power_normalization_mismatch':float(dt),'reflection_power_normalization_mismatch':float(dr)}); direct.append({'wavelength_nm':int(W[i]),'sourcepower_W':float(sp[i]),'raw_transmitted_power_W':pt,'raw_reflected_power_W':pr,'normalized_direct_T':float(nt),'normalized_direct_R_signed':float(nr),'monitor_T':float(T[i]),'monitor_R_signed':float(Rsign[i]),'T_mismatch':float(dt),'R_mismatch':float(dr)})
 for p in [RT/'spectral_metrics_11points.csv',EV/'spectral_metrics_11points.csv']:
  with p.open('w',newline='',encoding='utf-8') as out:
   w=csv.DictWriter(out,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 coord={}
 for name in ['transmission_monitor','reflection_monitor','N1_DIAG_PML_LOWER','N1_DIAG_LOWER_OUTSIDE','N1_DIAG_LOWER_INSIDE','N1_DIAG_UPPER_INSIDE','N1_DIAG_UPPER_OUTSIDE','N1_DIAG_PML_UPPER','N1_DIAG_XZ_INDEX_449']:
  coord[name]={}
  for axis in ['x','y','z']:
   try:
    a=np.asarray(fd.getdata(name,axis)).reshape(-1); coord[name][axis]={'shape':list(np.asarray(fd.getdata(name,axis)).shape),'count':int(a.size),'min':float(np.min(a)),'max':float(np.max(a)),'monotonic_strict':bool(np.all(np.diff(a)>0)) if a.size>1 else True,'sha256':ah(a)}
   except Exception as e: coord[name][axis]={'error':repr(e)}
 out={'case_id':'RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2','attempt_id':'attempt_001','post_fsp_path':str(post),'readonly_reload':True,'run_called':False,'save_called':False,'direct_power_api':'getdata(power)','direct_power_available':True,'direct_power_rows':direct,'max_transmission_normalization_mismatch':float(max_t),'max_reflection_normalization_mismatch':float(max_r),'normalization_gate_pass':bool(max(max_t,max_r)<=1e-8),'coordinate_hashes':coord,'actual_monitor_grid_coordinate_readback':True,'solver_core_grid_equality_proven':False}
 (EV/'raw_power_and_grid_audit.json').write_text(json.dumps(out,indent=2,sort_keys=True,default=str),encoding='utf-8'); (RT/'raw_power_and_grid_audit.json').write_text(json.dumps(out,indent=2,sort_keys=True,default=str),encoding='utf-8'); print(json.dumps({'max_t_mismatch':max_t,'max_r_mismatch':max_r,'normalization_gate_pass':out['normalization_gate_pass'],'transmission_x_hash':coord['transmission_monitor']['x'].get('sha256'),'transmission_y_hash':coord['transmission_monitor']['y'].get('sha256'),'xz_z_hash':coord['N1_DIAG_XZ_INDEX_449']['z'].get('sha256')},indent=2,default=str))
finally:
 fd.close()
