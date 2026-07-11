import csv,importlib.util,json,sys,math
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'outputs/mdc1d2_native_m1_zl1_2d_validation';RT=R/'runtime/mdc1d2_native_m1_zl1_2d_validation_DO_NOT_COMMIT';REP=R/'reports/mdc_defect_450/mdc1d2_native_m1_zl1_2d_validation.md';SEQ=[('H',46),('L',78),('H',46),('L',78),('H',46),('L',312),('H',46),('L',78),('H',46),('L',78),('H',46),('L',78)]
def api():
 p=r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py';s=importlib.util.spec_from_file_location('lumapi',p);m=importlib.util.module_from_spec(s);sys.modules['lumapi']=m;s.loader.exec_module(m);return m
def mats():
 import apcd_native_materials as a;return {x:a.get_native_epsilon_samples(x) for x in ('APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')}
def rect(f,n,m,y0,y1):f.addrect();f.set('name',n);f.set('material',m);f.set('x span',8e-6);f.set('y min',y0);f.set('y max',y1)
def calc(a,I):
 a=np.degrees(a) if np.max(abs(a))<=math.pi+1 else a;I=np.abs(I).ravel();a=a.ravel();t=np.radians(a);total=np.trapezoid(I,t);I=I/total
 def q(lo,hi):
  m=np.abs(np.degrees((t[:-1]+t[1:])/2));x=(m>lo)&(m<=hi) if lo else m<=hi;return float(np.sum((t[1:]-t[:-1])*(I[1:]+I[:-1])*.5*x))
  f={'eta10':q(0,10),'eta20':q(0,20),'annulus10_20':q(10,20),'leakage20_40':q(20,40),'leakage40_60':q(40,60),'residual60_plus':q(60,180)};f['fraction_sum']=f['eta10']+f['annulus10_20']+f['leakage20_40']+f['leakage40_60']+f['residual60_plus'];mean10=I[np.abs(a)<=10].mean();mean4060=I[(np.abs(a)>=40)&(np.abs(a)<=60)].mean();f['ratio']=float(mean10/mean4060);i=int(I.argmax());h=I[i]/2;z=np.where(I>=h)[0];f['peak_angle']=float(a[i]);f['fwhm']=float(a[z[-1]]-a[z[0]]);return f,a,I
def main():
 O.mkdir(parents=True,exist_ok=True);RT.mkdir(parents=True,exist_ok=True);REP.parent.mkdir(parents=True,exist_ok=True);D=mats();f=api().FDTD(hide=True);path=RT/'zl1_DO_NOT_COMMIT.fsp'
 try:
  for n,d in D.items():i=f.addmaterial('Sampled 3D data');f.setmaterial(i,'name',n);f.setmaterial(n,'sampled data',np.column_stack((d['frequency_hz'],d['epsilon'])).astype(complex))
  g=f.addmaterial('(n,k) Material');f.setmaterial(g,'name','GaN_n2p41');f.setmaterial('GaN_n2p41','Refractive Index',2.41);f.addfdtd();f.set('dimension','2D');f.set('x span',8e-6);f.set('y min',-1e-6);f.set('y max',2e-6);f.set('x min bc','PML');f.set('x max bc','PML');f.set('y min bc','PML');f.set('y max bc','PML');f.set('mesh accuracy',2);f.set('simulation time',300e-15);rect(f,'gan','GaN_n2p41',-1e-6,0);y=0
  for j,(m,d) in enumerate(SEQ):rect(f,'layer'+str(j),'APCD_SIO2_NATIVE_M1' if m=='L' else 'APCD_TIO2_NATIVE_M1',y,y+d*1e-9);y+=d*1e-9
  f.addmesh();f.set('x span',8e-6);f.set('y min',-50e-9);f.set('y max',y+50e-9);f.set('dx',20e-9);f.set('dy',2e-9);f.adddipole();f.set('name','xdipole');f.set('x',0);f.set('y',-400e-9);f.set('theta',90);f.set('phi',0);f.set('wavelength start',450e-9);f.set('wavelength stop',450e-9);f.addpower();f.set('name','top_monitor');f.set('monitor type','Linear X');f.set('x span',6e-6);f.set('y',y+300e-9);f.save(str(path));f.load(str(path));f.run();r=f.getresult('top_monitor','T');ff=np.asarray(f.farfield2d('top_monitor',1));a=np.asarray(f.farfieldangle('top_monitor',1));x,aa,ii=calc(a,ff);row={'case_id':'ZL1_N3_M3_L78_H46_450_XDIPOLE','raw_upward_monitor_power':float(np.real(np.asarray(r['T']).squeeze())),'monitor_fields':';'.join(r.keys()),'farfield_points':int(ff.size),'layer_count':12,'total_thickness_nm':978,'sampled_tio2_count':101,'sampled_sio2_count':101,**x};
  with (O/'compact_result.csv').open('w',newline='') as h:w=csv.DictWriter(h,fieldnames=row);w.writeheader();w.writerow(row)
  with (O/'angular_spectrum.csv').open('w',newline='') as h:w=csv.writer(h);w.writerow(['angle_deg','normalized_intensity']);w.writerows(zip(aa,ii))
  (O/'material_registration_audit.json').write_text(json.dumps({'tio2':101,'sio2':101,'fallback':'forbidden'}));(O/'run_manifest.json').write_text(json.dumps({'compiled_sequence':SEQ,'layers':12,'thickness_nm':978},indent=2));REP.write_text('# ZL-1 Native-M1 2D validation\n\nSingle center x-dipole runtime validation; raw monitor power is not extraction efficiency.\n'+json.dumps(row,indent=2));print(json.dumps(row))
 finally:f.close()
if __name__=='__main__':main()
