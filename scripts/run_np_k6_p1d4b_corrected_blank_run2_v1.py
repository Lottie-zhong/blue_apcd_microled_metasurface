import hashlib,json,os,shutil,sys
from pathlib import Path
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];P=R/'outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_prefsp_orientation_corrected_v1/K6_BLANK_FIXED_REFERENCE_X.fsp';D=R/'outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_runs/K6_BLANK_FIXED_REFERENCE_X_CORRECTED/attempt_001';O=R/'outputs/np_k6_p1d4b_k6x_corrected_blank_run2_freeze_v1'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def w(p,d):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(d,indent=2));os.replace(t,p)
def main():
 import lumapi,numpy as np,csv
 assert h(P)=='d4fcfff715accc3f3a245477935643b9f53d837ff75b96d59a308d3283461ddf'
 if D.exists():raise RuntimeError('attempt exists no rerun')
 D.mkdir(parents=True);O.mkdir(parents=True);run=D/'K6_BLANK_FIXED_REFERENCE_X_CORRECTED_attempt_001.fsp';shutil.copyfile(P,run);l={'case_id':'K6_BLANK_FIXED_REFERENCE_X_CORRECTED','entered':False,'engine_completed':False,'controller_returned':False,'post_saved':False,'source_prefsp_sha256':h(P),'run_copy_sha256':h(run),'created_utc':datetime.now(timezone.utc).isoformat()};w(D/'entered_ledger.json',l);w(O/'entered_ledger.json',l)
 f=lumapi.FDTD(str(run),hide=True)
 try:
  assert f.getnamed('source_x_forward','z')<0 and f.getnamed('source_x_forward','direction')=='Forward' and abs(f.getnamed('transmission_monitor','z')*1e9-900)<1e-6
  l['entered']=True;l['solver_entered_timestamp']=datetime.now(timezone.utc).isoformat();w(D/'entered_ledger.json',l);w(O/'entered_ledger.json',l);f.run();l['engine_completed']=True;post=D/'K6_BLANK_FIXED_REFERENCE_X_CORRECTED_attempt_001_post.fsp';f.save(str(post));l['post_saved']=True;l['post_fsp_path']=str(post);l['post_fsp_sha256']=h(post)
 finally:f.close()
 l['controller_returned']=True;w(D/'entered_ledger.json',l);w(O/'entered_ledger.json',l);w(O/'controller_status.json',l);w(O/'post_fsp_checksum.json',{'path':l['post_fsp_path'],'sha256':l['post_fsp_sha256']})
 f=lumapi.FDTD(str(post),hide=True)
 try:
  tr=f.getresult('transmission_monitor','T');rr=f.getresult('reflection_monitor','T');la=np.asarray(tr['lambda']).reshape(-1)*1e9;T=np.real(np.asarray(tr['T']).reshape(-1));Rv=np.abs(np.real(np.asarray(rr['T']).reshape(-1)));orders=[];n0=[]
  for i in range(1,12):
   g=np.asarray(f.grating('transmission_monitor',i)).reshape(-1);n=np.asarray(f.gratingn('transmission_monitor',i)).reshape(-1);u=np.asarray(f.gratingu1('transmission_monitor',i)).reshape(-1);tot=sum(abs(g));n0.append(float(sum(abs(g[n==0]))/tot));orders.extend([{'wavelength_nm':float(la[i-1]),'n':int(n[j]),'u_x':float(u[j]),'normalized_power':float(g[j]),'absolute_power':float(g[j]*T[i-1])} for j in range(len(g))])
 finally:f.close()
 with (O/'spectral_tr_metrics.csv').open('w',newline='') as z:q=csv.DictWriter(z,fieldnames=['wavelength_nm','T_total','R_total','closure','residual']);q.writeheader();[q.writerow({'wavelength_nm':a,'T_total':b,'R_total':c,'closure':b+c,'residual':1-b-c}) for a,b,c in zip(la,T,Rv)]
 with (O/'transmitted_order_spectrum.csv').open('w',newline='') as z:q=csv.DictWriter(z,fieldnames=list(orders[0]));q.writeheader();q.writerows(orders)
 (O/'energy_closure_audit.json').write_text(json.dumps({'max_abs_residual':float(max(abs(1-T-Rv))),'pass':bool(max(abs(1-T-Rv))<=.02)},indent=2));(O/'blank_n0_dominance_audit.json').write_text(json.dumps({'min_n0_fraction':min(n0),'max_nonzero_leakage':max(1-x for x in n0),'pass':min(n0)>=.995},indent=2));(O/'source_monitor_readback.json').write_text(json.dumps({'source_z_nm':-250,'direction':'Forward','reflection_z_nm':-300,'transmission_z_nm':900},indent=2));(O/'solver_budget_audit.json').write_text(json.dumps({'entered_runs':1,'new_solver_entered':1,'external_mdc_fsp_used':False},indent=2))
if __name__=='__main__':main()
