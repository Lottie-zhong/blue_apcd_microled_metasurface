import csv,importlib.util,json,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'outputs/mdc1d1a_bare_2d_runtime_probe';RT=R/'runtime/mdc1d1a_bare_2d_runtime_probe_DO_NOT_COMMIT';REP=R/'reports/mdc_defect_450/mdc1d1a_bare_2d_runtime_probe.md'
def api():
 p=r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py';s=importlib.util.spec_from_file_location('lumapi',p);m=importlib.util.module_from_spec(s);sys.modules['lumapi']=m;s.loader.exec_module(m);return m
def main():
 O.mkdir(parents=True,exist_ok=True);RT.mkdir(parents=True,exist_ok=True);f=api().FDTD(hide=True);fsp=RT/'bare_probe_DO_NOT_COMMIT.fsp'
 try:
  g=f.addmaterial('(n,k) Material');f.setmaterial(g,'name','GaN_probe_n2p41');f.setmaterial('GaN_probe_n2p41','Refractive Index',2.41)
  f.addfdtd();f.set('dimension','2D');f.set('x span',6e-6);f.set('y min',-1e-6);f.set('y max',.8e-6);f.set('x min bc','PML');f.set('x max bc','PML');f.set('y min bc','PML');f.set('y max bc','PML');f.set('mesh accuracy',1);f.set('simulation time',150e-15)
  f.addrect();f.set('material','GaN_probe_n2p41');f.set('x span',6e-6);f.set('y min',-1e-6);f.set('y max',0)
  f.adddipole();f.set('name','xdipole');f.set('x',0);f.set('y',-300e-9);f.set('theta',90);f.set('phi',0);f.set('wavelength start',450e-9);f.set('wavelength stop',450e-9)
  f.addpower();f.set('name','top_monitor');f.set('monitor type','Linear X');f.set('x span',5e-6);f.set('y',300e-9);f.save(str(fsp));f.load(str(fsp));f.run()
  res=f.getresult('top_monitor','T');T=float(np.real(np.asarray(res['T']).squeeze()));ff=np.asarray(f.farfield2d('top_monitor',1)).squeeze();a=np.asarray(f.farfieldangle('top_monitor',1)).squeeze();assert ff.size and ff.size==a.size and np.all(np.isfinite(ff)) and np.all(np.isfinite(a))
  d={'case_id':'BARE_GAN_AIR_2D_RUNTIME_PROBE','result_status':'runtime_probe_only','run_returned':True,'monitor_fields':list(res.keys()),'raw_monitor_power':T,'angle_size':int(a.size),'intensity_finite':True,'normalization':'raw farfield intensity'}; (O/'probe_status.json').write_text(json.dumps(d,indent=2));(O/'monitor_result_fields.json').write_text(json.dumps(list(res.keys())));csv.writer((O/'compact_result.csv').open('w',newline='')).writerows([d.keys(),d.values()]);csv.writer((O/'angular_spectrum.csv').open('w',newline='')).writerows([['angle','intensity'],*zip(a,ff)]);REP.write_text('# Bare 2D runtime probe\n\nRuntime/monitor closure only; mesh accuracy 1 and short window are not physical conclusions. No FAB run.\n'+json.dumps(d,indent=2));print(json.dumps(d))
 finally:f.close()
if __name__=='__main__':main()
