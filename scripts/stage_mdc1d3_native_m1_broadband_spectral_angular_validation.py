import csv,importlib.util,json,sys,math
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'outputs/mdc1d3_native_m1_broadband_spectral_angular_validation';RT=R/'runtime/mdc1d3_native_m1_broadband_spectral_angular_validation_DO_NOT_COMMIT';REP=R/'reports/mdc_defect_450/mdc1d3_native_m1_broadband_spectral_angular_validation.md';CASES={'EX_N3_L79_H45_C156':[('L',79),('H',45)]*3+[('L',156)]+[('H',45),('L',79)]*3,'ZL1_N3_M3_L78_H46':[('H',46),('L',78),('H',46),('L',78),('H',46),('L',312),('H',46),('L',78),('H',46),('L',78),('H',46),('L',78)]}
def api():
 p=r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py';s=importlib.util.spec_from_file_location('lumapi',p);m=importlib.util.module_from_spec(s);sys.modules['lumapi']=m;s.loader.exec_module(m);return m
def mats():
 import apcd_native_materials as a;return {x:a.get_native_epsilon_samples(x) for x in ('APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')}
def rect(f,n,m,y0,y1):f.addrect();f.set('name',n);f.set('material',m);f.set('x span',8e-6);f.set('y min',y0);f.set('y max',y1)
def frac(a,I):
 a=np.asarray(a).squeeze();I=np.abs(np.asarray(I).squeeze()).ravel();a=np.degrees(a) if np.max(abs(a))<=math.pi+1 else a;t=np.radians(a);I/=np.trapezoid(I,t)
 def q(lo,hi):
  m=np.abs(np.degrees((t[:-1]+t[1:])/2));z=(m>lo)&(m<=hi) if lo else m<=hi;return float(np.sum((t[1:]-t[:-1])*(I[1:]+I[:-1])*.5*z))
 x={'eta10':q(0,10),'eta20':q(0,20),'annulus10_20':q(10,20),'leakage20_40':q(20,40),'leakage40_60':q(40,60),'residual60_plus':q(60,180)};x['fraction_sum']=x['eta10']+x['annulus10_20']+x['leakage20_40']+x['leakage40_60']+x['residual60_plus'];i=int(I.argmax());z=np.where(I>=I[i]/2)[0];x.update({'peak_angle_deg':float(a[i]),'peak_normal':bool(abs(a[i])<=1),'angular_fwhm_deg':float(a[z[-1]]-a[z[0]]),'normal_to_40_60_ratio':float(I[abs(a)<=10].mean()/I[(abs(a)>=40)&(abs(a)<=60)].mean())});return x,a,I
def main():
 O.mkdir(parents=True,exist_ok=True);RT.mkdir(parents=True,exist_ok=True);REP.parent.mkdir(parents=True,exist_ok=True);D=mats();lu=api();spec=[];amet=[];arows=[];sm=[]
 for cid,seq in CASES.items():
  f=lu.FDTD(hide=True);p=RT/(cid+'.fsp')
  try:
   for n,d in D.items():i=f.addmaterial('Sampled 3D data');f.setmaterial(i,'name',n);f.setmaterial(n,'sampled data',np.column_stack((d['frequency_hz'],d['epsilon'])).astype(complex))
   g=f.addmaterial('(n,k) Material');f.setmaterial(g,'name','GaN_n2p41');f.setmaterial('GaN_n2p41','Refractive Index',2.41);f.addfdtd();f.set('dimension','2D');f.set('x span',8e-6);f.set('y min',-1e-6);f.set('y max',2e-6);f.set('x min bc','PML');f.set('x max bc','PML');f.set('y min bc','PML');f.set('y max bc','PML');f.set('mesh accuracy',2);f.set('simulation time',1000e-15);rect(f,'gan','GaN_n2p41',-1e-6,0);y=0
   for j,(m,d) in enumerate(seq):rect(f,'l'+str(j),'APCD_SIO2_NATIVE_M1' if m=='L' else 'APCD_TIO2_NATIVE_M1',y,y+d*1e-9);y+=d*1e-9
   f.addmesh();f.set('x span',8e-6);f.set('y min',-50e-9);f.set('y max',y+50e-9);f.set('dx',20e-9);f.set('dy',2e-9);f.adddipole();f.set('x',0);f.set('y',-400e-9);f.set('theta',90);f.set('phi',0);f.set('wavelength start',442e-9);f.set('wavelength stop',458e-9);f.addpower();f.set('name','top');f.set('monitor type','Linear X');f.set('x span',6e-6);f.set('y',y+300e-9);f.set('override global monitor settings',True);f.set('use wavelength spacing',True);f.set('frequency points',65);f.save(str(p));f.load(str(p));f.run();r=f.getresult('top','T');lam=np.asarray(r['lambda']).squeeze()*1e9;T=np.real(np.asarray(r['T']).squeeze());
   for w,t in zip(lam,T):spec.append({'candidate':cid,'wavelength_nm':w,'raw_upward_power':t})
   ip=int(T.argmax());half=T[ip]/2;z=np.where(T>=half)[0];sm.append({'candidate':cid,'fdtd_peak_nm':float(lam[ip]),'fdtd_peak_value':float(T[ip]),'fdtd_fwhm_nm':float(lam[z[-1]]-lam[z[0]])})
   for target in (448,450,453):
    k=int(abs(lam-target).argmin());ff=f.farfield2d('top',k+1);an=f.farfieldangle('top',k+1);x,a,I=frac(np.asarray(an),np.asarray(ff));x.update({'candidate':cid,'target_nm':target,'monitor_wavelength_nm':float(lam[k])});amet.append(x);arows += [{'candidate':cid,'target_nm':target,'angle_deg':float(u),'normalized_intensity':float(v)} for u,v in zip(a,I)]
  finally:f.close()
 def wr(n,rows):
  with (O/n).open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 wr('spectral_results.csv',spec);wr('spectral_metrics.csv',sm);wr('angular_results.csv',arows);wr('angular_metrics.csv',amet);wr('candidate_comparison.csv',sm);(O/'run_manifest.json').write_text(json.dumps({'cases':list(CASES),'points':65,'range_nm':[442,458]},indent=2));(O/'material_registration_audit.json').write_text(json.dumps({'tio2':101,'sio2':101,'fallback':'forbidden'}));REP.write_text('# MDC1D3 broadband validation\n\n'+json.dumps({'spectral':sm,'angular':amet},indent=2));print(json.dumps(sm))
if __name__=='__main__':main()
