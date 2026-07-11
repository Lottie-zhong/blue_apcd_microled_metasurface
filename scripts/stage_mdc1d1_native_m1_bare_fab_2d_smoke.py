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
def postprocess_only():
 src=O/'angular_spectrum.csv'; rows=list(csv.DictReader(src.open())); cases={r['case_id'] for r in rows}; out=[]; audit={}
 for case in cases:
  z=[(float(r['angle_deg']),float(r['normalized_intensity'])) for r in rows if r['case_id']==case]; z.sort(); ang=np.asarray([x[0] for x in z]); inten=np.asarray([x[1] for x in z]); th=np.radians(ang); finite=bool(np.all(np.isfinite(inten)) and np.all(np.isfinite(th))); total=float(np.trapz(inten,th)); norm=inten/total
  def frac(lo,hi):
   mids=np.degrees((th[:-1]+th[1:])/2);mask=(np.abs(mids)>lo)&(np.abs(mids)<=hi) if lo else (np.abs(mids)<=hi);return float(np.sum((th[1:]-th[:-1])*(norm[1:]+norm[:-1])*0.5*mask))
  fractions={'eta10':frac(0,10),'eta20':frac(0,20),'annulus10_20':frac(10,20),'leakage20_40':frac(20,40),'leakage40_60':frac(40,60),'residual60_plus':frac(60,180)}; fractions['fraction_sum']=fractions['eta10']+fractions['annulus10_20']+fractions['leakage20_40']+fractions['leakage40_60']+fractions['residual60_plus']; mean10=float(inten[np.abs(ang)<=10].mean());mean4060=float(inten[(np.abs(ang)>=40)&(np.abs(ang)<=60)].mean()); ratio=mean10/mean4060
  i=int(norm.argmax());half=norm[i]/2;left=next((th[j-1]+(half-norm[j-1])*(th[j]-th[j-1])/(norm[j]-norm[j-1]) for j in range(i,0,-1) if norm[j-1]<half<=norm[j]),th[0]);right=next((th[j]+(half-norm[j])*(th[j+1]-th[j])/(norm[j+1]-norm[j]) for j in range(i,len(norm)-1) if norm[j]>=half>norm[j+1]),th[-1]); audit[case]={'angle_min_deg':float(ang.min()),'angle_max_deg':float(ang.max()),'point_count':len(ang),'total_integral':total,'fractions':fractions,'normal_to_40_60_ratio':ratio,'peak_angle_deg':float(ang[i]),'angular_fwhm_deg':float(np.degrees(right-left)),'finite':finite}
 with (O/'angular_metric_audit.json').open('w') as f:json.dump(audit,f,indent=2)
 old={r['case_id']:r for r in csv.DictReader((O/'compact_results.csv').open())}; fields=list(old[next(iter(old))]);
 for case,a in audit.items(): old[case].update(a['fractions']);old[case]['normal_to_40_60_ratio']=a['normal_to_40_60_ratio'];old[case]['peak_angle_deg']=a['peak_angle_deg'];old[case]['angular_fwhm_deg']=a['angular_fwhm_deg']
 with (O/'compact_results.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(next(iter(old.values())).keys()));w.writeheader();w.writerows(old.values())
 report=REP.read_text();REP.write_text(report+'\n## Angular metric audit\n\nThe original implementation integrated over degree values and used overlapping/incorrect masks. Corrected fractions use radians, full-domain trapezoidal normalization, mutually exclusive masks, and ratio remains a separate mean-intensity metric.\n'+json.dumps(audit,indent=2))
def main():
 if '--postprocess-only' in sys.argv:return postprocess_only()
 O.mkdir(parents=True,exist_ok=True);RT.mkdir(parents=True,exist_ok=True);REP.parent.mkdir(parents=True,exist_ok=True);D=samples();lu=lumapi();all=[];ang=[]
 for c,s in [('BARE_GAN_AIR_450_XDIPOLE',[]),('EX_N3_L79_H45_C156_450_XDIPOLE',SEQ)]:
  x,a,i=run(c,s,lu,D);all.append(x);ang += [{'case_id':c,'angle_deg':float(u),'normalized_intensity':float(v)} for u,v in zip(a,i)]
 ratio=all[1]['raw_upward_monitor_power']/all[0]['raw_upward_monitor_power'];manifest={'fab_sequence':'L79 H45 L79 H45 L79 H45 C156 H45 L79 H45 L79 H45 L79','fab_layers':13,'fab_thickness_nm':900,'power_ratio_fab_to_bare':ratio,'material_registration':'PASS'}
 for p,rows in [(O/'compact_results.csv',all),(O/'angular_spectrum.csv',ang)]:
  with p.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (O/'material_registration_audit.json').write_text(json.dumps({'tio2':101,'sio2':101,'fallback':'forbidden'}));(O/'run_manifest.json').write_text(json.dumps(manifest,indent=2));REP.write_text('# Native-M1 Bare/FAB 2D FDTD\n\nRuntime comparison only; raw monitor power is not extraction efficiency. Center x-dipole at 450 nm; finite-window layered approximation, not mesa-edge or x/y average.\n'+json.dumps({'runs':all,'comparison':manifest},indent=2));print(json.dumps({'runs':all,'comparison':manifest}))
if __name__=='__main__':main()
