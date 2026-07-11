import csv,importlib.util,json,sys,math
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'outputs/mdc1d1_native_m1_bare_fab_2d_smoke';RT=R/'runtime/mdc1d1_native_m1_bare_fab_2d_smoke_DO_NOT_COMMIT';REP=R/'reports/mdc_defect_450/mdc1d1_native_m1_bare_fab_2d_smoke.md';SEQ=[('L',79),('H',45)]*3+[('L',156)]+[('H',45),('L',79)]*3
def lumapi():
 p=r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py';s=importlib.util.spec_from_file_location('lumapi',p);m=importlib.util.module_from_spec(s);sys.modules['lumapi']=m;s.loader.exec_module(m);return m
def samples():
 import apcd_native_materials as a
 return {k:a.get_native_epsilon_samples(k) for k in ('APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')}
def addmat(f,n,d):
 i=f.addmaterial('Sampled 3D data');f.setmaterial(i,'name',n);f.setmaterial(n,'sampled data',np.column_stack((d['frequency_hz'],d['epsilon'])).astype(complex));return len(d['frequency_hz'])
def rect(f,n,m,y0,y1):
 f.addrect();f.set('name',n);f.set('material',m);f.set('x span',8e-6);f.set('y min',y0);f.set('y max',y1)
def metrics(a,I):
 a=np.degrees(a) if np.nanmax(abs(a))<=math.pi+1 else a;I=np.abs(I).ravel();a=a.ravel();I/=np.trapz(I,a)
 def integ(lo,hi):return float(np.trapz(I[(abs(a)>=lo)&(abs(a)<=hi)],a[(abs(a)>=lo)&(abs(a)<=hi)]))
 def mean(lo,hi):
  z=I[(abs(a)>=lo)&(abs(a)<=hi)];return float(z.mean())
 i=int(I.argmax());half=I[i]/2;z=np.where(I>=half)[0]
 return {'peak_angle_deg':float(a[i]),'angular_fwhm_deg':float(a[z[-1]]-a[z[0]]),'eta10':integ(0,10),'eta20':integ(0,20),'leakage20_40':integ(20,40),'leakage40_60':integ(40,60),'normal_to_40_60_ratio':mean(0,10)/(mean(40,60)+1e-30)},a,I
def run(case,stack,lu,D):
 f=lu.FDTD(hide=True);path=RT/(case+'.fsp')
 try:
  ct=cs=0
  if stack:ct=addmat(f,'APCD_TIO2_NATIVE_M1',D['APCD_TIO2_NATIVE_M1']);cs=addmat(f,'APCD_SIO2_NATIVE_M1',D['APCD_SIO2_NATIVE_M1'])
  g=f.addmaterial('(n,k) Material');f.setmaterial(g,'name','GaN_n2p41');f.setmaterial('GaN_n2p41','Refractive Index',2.41)
  f.addfdtd();f.set('dimension','2D');f.set('x span',8e-6);f.set('y min',-1e-6);f.set('y max',2e-6);f.set('x min bc','PML');f.set('x max bc','PML');f.set('y min bc','PML');f.set('y max bc','PML');f.set('mesh accuracy',2);f.set('simulation time',300e-15)
  rect(f,'gan','GaN_n2p41',-1e-6,0);y=0
  for j,(m,d) in enumerate(stack):rect(f,'layer'+str(j),'APCD_SIO2_NATIVE_M1' if m=='L' else 'APCD_TIO2_NATIVE_M1',y,y+d*1e-9);y+=d*1e-9
  f.addmesh();f.set('x span',8e-6);f.set('y min',-50e-9);f.set('y max',y+50e-9);f.set('dx',20e-9);f.set('dy',2e-9)
  f.adddipole();f.set('name','xdipole');f.set('x',0);f.set('y',-400e-9);f.set('theta',90);f.set('phi',0);f.set('wavelength start',450e-9);f.set('wavelength stop',450e-9)
  f.addpower();f.set('name','top_monitor');f.set('monitor type','Linear X');f.set('x span',6e-6);f.set('y',y+300e-9)
  f.save(str(path));f.load(str(path));f.run();r=f.getresult('top_monitor','T');T=float(np.real(np.asarray(r['T']).squeeze()));ff=np.asarray(f.farfield2d('top_monitor',1)).squeeze();an=np.asarray(f.farfieldangle('top_monitor',1)).squeeze();q,an,ff=metrics(an,ff)
  return {'case_id':case,'raw_upward_monitor_power':T,'absolute_extraction_status':'pending','monitor_fields':';'.join(r.keys()),'sampled_tio2_count':ct,'sampled_sio2_count':cs,'layer_count':len(stack),'total_thickness_nm':sum(x[1] for x in stack),**q},an,ff
 finally:f.close()
def main():
 O.mkdir(parents=True,exist_ok=True);RT.mkdir(parents=True,exist_ok=True);REP.parent.mkdir(parents=True,exist_ok=True);D=samples();lu=lumapi();all=[];ang=[]
 for c,s in [('BARE_GAN_AIR_450_XDIPOLE',[]),('EX_N3_L79_H45_C156_450_XDIPOLE',SEQ)]:
  x,a,i=run(c,s,lu,D);all.append(x);ang += [{'case_id':c,'angle_deg':float(u),'normalized_intensity':float(v)} for u,v in zip(a,i)]
 ratio=all[1]['raw_upward_monitor_power']/all[0]['raw_upward_monitor_power'];manifest={'fab_sequence':'L79 H45 L79 H45 L79 H45 C156 H45 L79 H45 L79 H45 L79','fab_layers':13,'fab_thickness_nm':900,'power_ratio_fab_to_bare':ratio,'material_registration':'PASS'}
 for p,rows in [(O/'compact_results.csv',all),(O/'angular_spectrum.csv',ang)]:
  with p.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (O/'material_registration_audit.json').write_text(json.dumps({'tio2':101,'sio2':101,'fallback':'forbidden'}));(O/'run_manifest.json').write_text(json.dumps(manifest,indent=2));REP.write_text('# Native-M1 Bare/FAB 2D FDTD\n\nRuntime comparison only; raw monitor power is not extraction efficiency. Center x-dipole at 450 nm; finite-window layered approximation, not mesa-edge or x/y average.\n'+json.dumps({'runs':all,'comparison':manifest},indent=2));print(json.dumps({'runs':all,'comparison':manifest}))
if __name__=='__main__':main()
