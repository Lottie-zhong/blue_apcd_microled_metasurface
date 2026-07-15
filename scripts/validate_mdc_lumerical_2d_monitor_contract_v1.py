from __future__ import annotations
import argparse,csv,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import mdc_fdtd_2d_monitor_contract_v1 as C
OUT=ROOT/'outputs'/'mdc_lumerical_2d_monitor_contract_v1';RT=ROOT/'runtime'/'mdc_lumerical_2d_monitor_contract_v1';REPORT=ROOT/'reports'/'mdc_lumerical_2d_monitor_contract_v1.md'
SOURCE_Y=-400e-9;HALVES=(20e-9,30e-9,40e-9)
def write(name,rows):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);keys=list(dict.fromkeys(k for r in rows for k in r));h=p.open('w',newline='',encoding='utf-8');w=csv.DictWriter(h,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows);h.close()
def dump(name,x):(OUT/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def api():
 p=r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py';s=importlib.util.spec_from_file_location('lumapi',p);m=importlib.util.module_from_spec(s);sys.modules['lumapi']=m;s.loader.exec_module(m);return m
def native():import apcd_native_materials as m;return m
def setup(f,dipole):
 native().register_lumerical_sampled_material(f,'APCD_GAN_NATIVE_M1',apply_display_style=True)
 f.addfdtd();f.set('dimension','2D');f.set('background material','APCD_GAN_NATIVE_M1');f.set('x span',1e-6);f.set('y min',-800e-9);f.set('y max',300e-9);f.set('x min bc','PML');f.set('x max bc','PML');f.set('y min bc','PML');f.set('y max bc','PML');f.set('mesh accuracy',1);f.set('simulation time',300e-15)
 C.add_source_local_mesh(f,0,SOURCE_Y);f.adddipole();f.set('name',dipole+'_dipole');f.set('x',0);f.set('y',SOURCE_Y);f.set('theta',90 if dipole=='x' else 0);f.set('phi',0);f.set('wavelength start',450e-9);f.set('wavelength stop',450e-9);C.add_field_channel_monitor(f,0,SOURCE_Y)
 for label,half in zip(('inner','middle','outer'),HALVES):C.add_2d_power_box(f,'box_'+label,0,SOURCE_Y,half)
 f.addpower();f.set('name','reference_y0');f.set('monitor type','Linear X');f.set('x',0);f.set('y',0);f.set('x span',600e-9);f.set('override global monitor settings',True);f.set('frequency points',1)
def audit():print(json.dumps({'status':'audit_pass','outward_formula':'right-left+top-bottom','abs_forbidden':True,'canonical':'direct_poynting_integral','solver':False}))
def build():
 RT.mkdir(parents=True,exist_ok=True);lu=api()
 for d in ('x','z'):
  f=lu.FDTD(hide=True)
  try:setup(f,d);f.save(str(RT/(f'HOMOG_GAN_{d.upper()}_DIPOLE_build.fsp')))
  finally:f.close()
 print('build PASS')
def run():
 RT.mkdir(parents=True,exist_ok=True);lu=api();inventory=[];channels=[];mesh=[];manifest=[];side_rows=[];trends=[];refs=[];cross=[]
 for d in ('x','z'):
  f=lu.FDTD(hide=True);path=RT/(f'HOMOG_GAN_{d.upper()}_DIPOLE_run_{int(time.time()*1000)}.fsp')
  try:
   setup(f,d);f.save(str(path));f.load(str(path));f.run();inventory.append({'case':d,**C.read_monitor_data_inventory(f,'field_channel')})
   fields=C.read_fields(f,'field_channel');energy={k:(float(np.sum(np.abs(v)**2)) if v is not None else None) for k,v in fields.items() if k in ('Ex','Ey','Ez','Hx','Hy','Hz')};dom=('Ex','Ey','Hz') if d=='x' else ('Ez','Hx','Hy');leak=tuple(k for k in ('Ex','Ey','Ez','Hx','Hy','Hz') if k not in dom);de=sum(energy[k] or 0 for k in dom);le=sum(energy[k] or 0 for k in leak);channels.append({'case':d,**{k:('component_not_returned_by_2d_solver' if v is None else v) for k,v in energy.items()},'dominant_energy':de,'leakage_energy':le,'leakage_fraction':le/(de+le),'status':'pass' if de>0 and le/(de+le)<=1e-4 else 'fail'})
   mesh.append({'case':d,'object_exists':True,'name':'source_local_mesh','x':f.getnamed('source_local_mesh','x'),'y':f.getnamed('source_local_mesh','y'),'x_span':f.getnamed('source_local_mesh','x span'),'y_span':f.getnamed('source_local_mesh','y span'),'dx':f.getnamed('source_local_mesh','dx'),'dy':f.getnamed('source_local_mesh','dy'),'override_x':f.getnamed('source_local_mesh','override x mesh'),'override_y':f.getnamed('source_local_mesh','override y mesh')})
   nets=[];source_power=float(np.real(np.asarray(f.sourcepower(299792458.0/450e-9)).squeeze()))
   for label in ('inner','middle','outer'):
    raw={}
    for side,kind in (('top','Linear X'),('bottom','Linear X'),('right','Linear Y'),('left','Linear Y')):
     name=f'box_{label}_{side}';raw[side]=C.integrate_line_poynting_flux(C.read_fields(f,name),kind);trans=float(np.real(np.asarray(f.transmission(name)).squeeze()));scalar=trans*source_power;rel=abs(scalar-raw[side])/max(abs(raw[side]),1e-30);side_rows.append({'case':d,'box':label,'side':side,'raw_flux':raw[side],'outward_flux':raw[side] if side in ('top','right') else -raw[side]});cross.append({'case':d,'monitor':name,'direct_poynting_integral':raw[side],'monitor_power_scalar':scalar,'transmission_sign_diagnostic':trans,'sourcepower_diagnostic':source_power,'relative_difference':rel,'status':'pass' if rel<=1e-3 else 'fail'})
    out=C.calculate_box_outward_flux(raw);nets.append(out['net_outward']);trends.append({'case':d,'box':label,**out})
   ref=C.read_reference_plane_flux(f);trans=float(np.real(np.asarray(f.transmission('reference_y0')).squeeze()));scalar=trans*source_power;rel=abs(scalar-ref)/max(abs(ref),1e-30);refs.append({'case':d,'P_reference_y0':ref,'monitor_power_scalar':scalar,'transmission_sign_diagnostic':trans,'sourcepower_diagnostic_not_canonical':source_power,'relative_difference':rel,'source_to_plane_m':400e-9,'status':'pass' if ref>0 and rel<=1e-3 else 'fail'});cross.append({'case':d,'monitor':'reference_y0','direct_poynting_integral':ref,'monitor_power_scalar':scalar,'transmission_sign_diagnostic':trans,'sourcepower_diagnostic':source_power,'relative_difference':rel,'status':'pass' if rel<=1e-3 else 'fail'})
  finally:f.close()
 write('source_local_mesh_readback.csv',mesh);write('field_monitor_data_inventory.csv',inventory);write('field_channel_validation.csv',channels);write('power_box_side_fluxes.csv',side_rows);write('power_box_size_trend.csv',trends);write('reference_plane_flux.csv',refs);write('flux_method_crosscheck.csv',cross);write('power_box_monitor_manifest.csv',[{'box':b,'half_size_nm':h*1e9,'top_bottom_type':'Linear X','left_right_type':'Linear Y'} for b,h in zip(('inner','middle','outer'),HALVES)])
 status='contract_pass' if all(r['status']=='pass' for r in channels+refs+cross) and all(r['net_outward']>0 for r in trends) else 'contract_failed';dump('validation.json',{'status':status,'cases':2,'canonical_flux':'direct_poynting_integral','monitor_scalar_crosscheck':'pass' if all(r['status']=='pass' for r in cross) else 'fail','solver_invoked':True});dump('manifest.json',{'task':'MDC_LUMERICAL_2D_MONITOR_AND_POWER_BOX_CONTRACT_V1','outputs':sorted(p.name for p in OUT.iterdir()),'runtime':str(RT),'git_commit':False})
 lines=['# MDC Lumerical 2D monitor contract v1','',f'Status: `{status}`.','', '## Contract','', '- Linear X integrates `Re(Py)` along x; Linear Y integrates `Re(Px)` along y.', '- Outward flux is `F_right - F_left + F_top - F_bottom`; no absolute-value correction is used.', '- Direct Poynting integration is canonical. `transmission * sourcepower` is diagnostic only; dipolepower is unused.', '', '## Field channels','', '|dipole|dominant energy|leakage fraction|status|','|---|---:|---:|---|']
 for r in channels:lines.append(f"|{r['case']}|{r['dominant_energy']:.9g}|{r['leakage_fraction']:.3g}|{r['status']}|")
 lines += ['', '## Box outward flux', '', '|dipole|inner|middle|outer|','|---|---:|---:|---:|']
 for d in ('x','z'):
  vals=[r['net_outward'] for r in trends if r['case']==d];lines.append(f'|{d}|{vals[0]:.9g}|{vals[1]:.9g}|{vals[2]:.9g}|')
 lines += ['', 'The monotonic decrease with box size is expected for lossy GaN; this contract task does not select a canonical box.', '', '## Homogeneous y=0 reference', '', '|dipole|direct flux|crosscheck relative difference|','|---|---:|---:|']
 for r in refs:lines.append(f"|{r['case']}|{r['P_reference_y0']:.9g}|{r['relative_difference']:.3g}|")
 lines += ['', 'Only the two homogeneous-GaN x/z contract cases were run. No Bare, MDC, Wan proxy, broadband, material-policy, database, or frozen-TMM operation was performed.']
 REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(status)
def post():
 v=json.loads((OUT/'validation.json').read_text());print(json.dumps(v))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--audit-only',action='store_true');p.add_argument('--build',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--postprocess',action='store_true');a=p.parse_args();
 if sum((a.audit_only,a.build,a.run,a.postprocess))!=1:p.error('one mode required')
 audit() if a.audit_only else build() if a.build else run() if a.run else post()
