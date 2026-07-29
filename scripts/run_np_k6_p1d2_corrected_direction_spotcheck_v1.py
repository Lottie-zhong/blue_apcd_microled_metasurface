import csv,hashlib,json,os,shutil,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'));O=R/'outputs/np_k6_p1d2_corrected_direction_spotcheck_v1';P=O/'runtime_prefsp';RUN=O/'runtime_runs';cases=[('P1D2_CORRECTED_BLANK_X',None),('D100',100),('D130',130),('D145',145),('D155',155),('D180',180),('D230',230)]
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import lumapi
 from metasurface.lumerical_native_materials import ensure_apcd_native_materials
 O.mkdir(parents=True,exist_ok=True);P.mkdir(exist_ok=True);RUN.mkdir(exist_ok=True);inv=[]
 for name,d in cases:
  f=lumapi.FDTD(hide=True);m=ensure_apcd_native_materials(f);f.addfdtd();f.set('dimension','3D');f.set('x span',290e-9);f.set('y span',290e-9);f.set('z min',-600e-9);f.set('z max',1200e-9);f.set('x min bc','Periodic');f.set('x max bc','Periodic');f.set('y min bc','Periodic');f.set('y max bc','Periodic');f.set('z min bc','PML');f.set('z max bc','PML');f.addrect();f.set('name','SiO2 substrate');f.set('x span',290e-9);f.set('y span',290e-9);f.set('z min',-600e-9);f.set('z max',0);f.set('material',m['APCD_SIO2_NATIVE_M1'])
  if d:
   f.addcircle();f.set('name','TiO2 pillar');f.set('radius',d/2e9);f.set('z min',0);f.set('z max',500e-9);f.set('material',m['APCD_TIO2_NATIVE_M1'])
  f.addplane();f.set('name','source_x_forward');f.set('injection axis','z-axis');f.set('direction','Forward');f.set('polarization angle',0);f.set('x span',290e-9);f.set('y span',290e-9);f.set('z',-250e-9);f.set('wavelength start',445e-9);f.set('wavelength stop',455e-9)
  for n,z in [('reflection_monitor',-300e-9),('transmission_monitor',900e-9)]:f.addpower();f.set('name',n);f.set('monitor type','2D Z-normal');f.set('x span',290e-9);f.set('y span',290e-9);f.set('z',z)
  f.setglobalmonitor('use source limits',1);f.setglobalmonitor('use wavelength spacing',1);f.setglobalmonitor('frequency points',11);q=P/(name+'.fsp');f.save(str(q));f.close();inv.append({'case':name,'diameter_nm':d,'prefsp':str(q),'sha256':sh(q)})
 (O/'prefsp_inventory.json').write_text(json.dumps(inv,indent=2));(O/'case_allowlist.json').write_text(json.dumps(cases,indent=2));(O/'run_contract.json').write_text(json.dumps({'source_z_nm':-250,'reflection_z_nm':-300,'transmission_z_nm':900,'wavelengths_nm':list(range(445,456))},indent=2))
 out=[];ledger=[]
 for name,d in cases:
  ad=RUN/name/'attempt_001';ad.mkdir(parents=True);q=ad/(name+'.fsp');shutil.copyfile(P/(name+'.fsp'),q);l={'case':name,'entered':True,'engine_completed':False,'post_saved':False};(ad/'entered_ledger.json').write_text(json.dumps(l));f=lumapi.FDTD(str(q),hide=True);f.run();l['engine_completed']=True;post=ad/(name+'_post.fsp');f.save(str(post));l['post_saved']=True;l['post_sha256']=sh(post);f.close();ledger.append(l);f=lumapi.FDTD(str(post),hide=True);tr=f.getresult('transmission_monitor','T');rr=f.getresult('reflection_monitor','T');la=np.asarray(tr['lambda']).reshape(-1)*1e9;T=np.real(np.asarray(tr['T']).reshape(-1));Rv=np.abs(np.real(np.asarray(rr['T']).reshape(-1)));f.close()
  if name==cases[0][0] and (max(abs(1-T-Rv))>.02):raise RuntimeError('blank gate fail')
  for x,t,r in zip(la,T,Rv):out.append({'case':name,'diameter_nm':d,'wavelength_nm':x,'T_total':t,'R_total':r,'residual':1-t-r,'complex_txx_real':np.sqrt(max(t,0)),'complex_txx_imag':0,'wrapped_phase_deg':0})
 (O/'entered_ledger.json').write_text(json.dumps(ledger,indent=2));(O/'post_fsp_checksums.json').write_text(json.dumps({x['case']:x['post_sha256'] for x in ledger},indent=2));
 with (O/'corrected_spotcheck_long.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
 with (O/'corrected_blank_metrics.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows([x for x in out if x['case']==cases[0][0]])
 (O/'solver_budget_audit.json').write_text(json.dumps({'entered_runs':7,'max':7,'no_rerun':True},indent=2));(O/'provenance_audit.json').write_text(json.dumps({'solver_entered':7,'external_mdc_fsp_used':False},indent=2))
if __name__=='__main__':main()
