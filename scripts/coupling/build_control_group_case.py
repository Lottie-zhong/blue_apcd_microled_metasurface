from __future__ import annotations
import argparse, hashlib, importlib, json, subprocess, sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[2]; SRC=ROOT/'src'
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from apcd_coupling.joint_stack_builder import build_joint_case

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
 return h.hexdigest()
def write(path:Path,obj:Any): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def one(fdtd,name,prop):
 v=fdtd.getnamed(name,prop); return v.tolist() if hasattr(v,'tolist') else v
def load_helper(root):
 sys.path.insert(0,str(root/'scripts')); return importlib.import_module('apcd_native_materials')
def material_names(fdtd):
 raw=fdtd.getmaterial(); raw=raw.tolist() if hasattr(raw,'tolist') else raw
 return [x.strip() for x in raw.splitlines() if x.strip()] if isinstance(raw,str) else [str(x).strip() for x in raw if str(x).strip()]
def expected_objects(case,role): return [x for x in case['objects'] if x['role']==role]

def build_fsp(case,prefsp,helper_root):
 import lumapi
 helper=load_helper(helper_root); fdtd=lumapi.FDTD(hide=True)
 try:
  for mid in ('APCD_GAN_NATIVE_M1','APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1'): helper.register_lumerical_sampled_material(fdtd,mid)
  fdtd.addfdtd()
  pillar_objects=expected_objects(case,'np_pillar')
  monitor_z=(case['coordinates']['np_pillar_top_nm']+400.0)*1e-9 if pillar_objects else 1875e-9
  z_max=monitor_z+300e-9
  for prop,val in (('dimension','3D'),('x span',1740e-9),('y span',290e-9),('z min',-600e-9),('z max',z_max),('x min bc','Periodic'),('x max bc','Periodic'),('y min bc','Periodic'),('y max bc','Periodic'),('z min bc','PML'),('z max bc','PML'),('mesh accuracy',2),('pml layers',8),('simulation time',1e-12),('auto shutoff min',1e-5),('dt stability factor',0.99)): fdtd.set(prop,val)
  sub=next(x for x in case['objects'] if x['role']=='gan_substrate'); fdtd.addrect(); fdtd.set('name','GaN_substrate'); fdtd.set('x span',1740e-9); fdtd.set('y span',290e-9); fdtd.set('z min',sub['z_min_nm']*1e-9); fdtd.set('z max',sub['z_max_nm']*1e-9); fdtd.set('material',sub['material_id'])
  for role,prefix in (('mdc_layer','MDC_layer'),('interface_support_layer','Support_layer'),('extra_spacer','Extra_spacer')):
   for obj in expected_objects(case,role):
    fdtd.addrect(); fdtd.set('name',f"{prefix}_{int(obj.get('index',1)):02d}"); fdtd.set('x span',1740e-9); fdtd.set('y span',290e-9); fdtd.set('z min',obj['z_min_nm']*1e-9); fdtd.set('z max',obj['z_max_nm']*1e-9); fdtd.set('material',obj['material_id'])
  for obj in expected_objects(case,'np_pillar'):
   fdtd.addcircle(); fdtd.set('name',f"NP_pillar_{int(obj['index'])}"); fdtd.set('x',obj['x_nm']*1e-9); fdtd.set('y',obj['y_nm']*1e-9); fdtd.set('radius',obj['diameter_nm']*.5e-9); fdtd.set('z min',obj['z_min_nm']*1e-9); fdtd.set('z max',obj['z_max_nm']*1e-9); fdtd.set('material',obj['material_id'])
  fdtd.addplane(); fdtd.set('name','source_x_forward')
  for prop,val in (('injection axis','z-axis'),('direction','Forward'),('polarization angle',0),('x span',1740e-9),('y span',290e-9),('z',-250e-9),('wavelength start',450e-9),('wavelength stop',450e-9)): fdtd.set(prop,val)
  for name,z in (('reflection_monitor',-300e-9),('transmission_monitor',monitor_z),('order_monitor',monitor_z),('field_450_monitor',monitor_z)):
   fdtd.addpower(); fdtd.set('name',name); fdtd.set('monitor type','2D Z-normal'); fdtd.set('x span',1740e-9); fdtd.set('y span',290e-9); fdtd.set('z',z)
  fdtd.setglobalmonitor('use source limits',1); fdtd.setglobalmonitor('use wavelength spacing',1); fdtd.setglobalmonitor('frequency points',1); fdtd.save(str(prefsp))
 finally: fdtd.close()

def readback(case,prefsp,helper_root):
 import lumapi
 fdtd=lumapi.FDTD(str(prefsp),hide=True)
 try:
  solver={prop:one(fdtd,'FDTD',prop) for prop in ('dimension','x span','y span','z min','z max','x min bc','x max bc','y min bc','y max bc','z min bc','z max bc','mesh accuracy','pml layers','simulation time','auto shutoff min','dt stability factor')}
  source={prop:one(fdtd,'source_x_forward',prop) for prop in ('injection axis','direction','polarization angle','x span','y span','z','wavelength start','wavelength stop','angle theta','angle phi')}
  monitors={name:{prop:one(fdtd,name,prop) for prop in ('monitor type','z','x span','y span','frequency points','use source limits','use wavelength spacing')} for name in ('reflection_monitor','transmission_monitor','order_monitor','field_450_monitor')}
  stack=[]
  for role,prefix in (('mdc_layer','MDC_layer'),('interface_support_layer','Support_layer'),('extra_spacer','Extra_spacer')):
   for obj in expected_objects(case,role):
    name=f"{prefix}_{int(obj.get('index',1)):02d}"; stack.append({'role':role,'name':name,'material':one(fdtd,name,'material'),'z_min_nm':one(fdtd,name,'z min')*1e9,'z_max_nm':one(fdtd,name,'z max')*1e9})
  pillars=[]
  for obj in expected_objects(case,'np_pillar'):
   name=f"NP_pillar_{int(obj['index'])}"; pillars.append({'name':name,'material':one(fdtd,name,'material'),'x_nm':one(fdtd,name,'x')*1e9,'diameter_nm':2*one(fdtd,name,'radius')*1e9,'z_min_nm':one(fdtd,name,'z min')*1e9,'z_max_nm':one(fdtd,name,'z max')*1e9})
  names=material_names(fdtd); mats={mid:{'present':mid in names,'sample_count':int(len(fdtd.getmaterial(mid,'sampled data')))} for mid in ('APCD_GAN_NATIVE_M1','APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')}
  return {'solver':solver,'source':source,'monitors':monitors,'stack_objects':stack,'np_pillars':pillars,'materials':mats,'material_names':names,'reference_medium':'Air','readback_session_readonly':True}
 finally: fdtd.close()

def validate(case,rb):
 exp_layers=expected_objects(case,'mdc_layer')+expected_objects(case,'interface_support_layer')+expected_objects(case,'extra_spacer'); exp_p=expected_objects(case,'np_pillar'); got=rb['stack_objects']; expected_monitor_z=((case['coordinates']['np_pillar_top_nm']+400.0)*1e-9 if exp_p else 1875e-9)
 checks={'dimension_3d':rb['solver']['dimension']=='3D','periodic_xy':all(rb['solver'][key]=='Periodic' for key in ('x min bc','x max bc','y min bc','y max bc')),'pml_z':rb['solver']['z min bc']=='PML' and rb['solver']['z max bc']=='PML','pml_layers':float(rb['solver']['pml layers'])==8.0,'mesh_accuracy':float(rb['solver']['mesh accuracy'])==2.0,'simulation_time':float(rb['solver']['simulation time'])==1e-12,'autoshutoff':float(rb['solver']['auto shutoff min'])==1e-5,'source_x_normal':rb['source']['direction']=='Forward' and float(rb['source']['polarization angle'])==0 and float(rb['source']['angle theta'])==0 and float(rb['source']['angle phi'])==0,'source_wavelength':float(rb['source']['wavelength start'])==450e-9 and float(rb['source']['wavelength stop'])==450e-9,'stack_presence_absence':len(got)==len(exp_layers) and len(rb['np_pillars'])==len(exp_p),'layer_identity':all(a['material']==b['material_id'] and abs(a['z_max_nm']-a['z_min_nm']-b['thickness_nm'])<1e-6 for a,b in zip(got,exp_layers)),'pillar_identity':all(a['material']==b['material_id'] and abs(a['x_nm']-b['x_nm'])<1e-6 and abs(a['diameter_nm']-b['diameter_nm'])<1e-6 and abs(a['z_max_nm']-a['z_min_nm']-500)<1e-6 for a,b in zip(rb['np_pillars'],exp_p)),'native_materials':all(x['present'] and x['sample_count']>1 for x in rb['materials'].values()),'no_gap_no_overlap':all(abs(a['z_max_nm']-b['z_min_nm'])<1e-6 for a,b in zip(sorted(got,key=lambda x:x['z_min_nm'])[:-1],sorted(got,key=lambda x:x['z_min_nm'])[1:])) and (not got or abs(sorted(got,key=lambda x:x['z_max_nm'])[-1]['z_max_nm']-case['coordinates']['stack_top_nm'])<1e-6),'same_material_continuity':(not expected_objects(case,'extra_spacer')) or (got[-1]['material']=='APCD_SIO2_NATIVE_M1' and abs(got[-1]['z_min_nm']-case['coordinates']['mdc_top_nm'])<1e-6 and abs(got[-1]['z_max_nm']-case['coordinates']['np_pillar_bottom_nm'])<1e-6),'monitor_positions':rb['monitors']['reflection_monitor']['z']==-300e-9 and abs(rb['monitors']['transmission_monitor']['z']-expected_monitor_z)<1e-15 and abs(rb['solver']['z max']-rb['monitors']['transmission_monitor']['z']-300e-9)<1e-15}
 return {'pass':all(checks.values()),'checks':checks}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--fixture-registry',type=Path,required=True); ap.add_argument('--control-group',required=True); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--material-helper-root',type=Path,default=Path('D:/project/worktrees/blue_apcd_mdc_hf_surrogate_v2')); args=ap.parse_args()
 cfg=json.loads(args.fixture_registry.read_text(encoding='utf-8')); item=next(x for x in cfg['controls'] if x['control_group']==args.control_group); case=build_joint_case(item['mdc_candidate'],item['np_candidate'],item.get('spacer_nm',0),450,'x',0,interface_candidate=item.get('interface_candidate'),case_id=item['case_id'],control_group=item['control_group']); out=args.output_dir; out.mkdir(parents=True,exist_ok=True); write(out/'joint_case.json',case); setup=out/'setup'; setup.mkdir(exist_ok=True); pre=setup/f"{case['case_id']}_pre.fsp"; build_fsp(case,pre,args.material_helper_root); rb=readback(case,pre,args.material_helper_root); gate=validate(case,rb); manifest={'schema_version':'stage_a_control_setup_manifest_v1','case_id':case['case_id'],'control_group':args.control_group,'case':case,'readback':rb,'setup_gate':gate,'pre_fsp_path':str(pre),'pre_fsp_sha256':sha256(pre),'solver_entered':False,'solver_completed':False,'source_commits':cfg['source_commits'],'coupling_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()}; write(out/'setup_manifest.json',manifest); write(out/'setup_readback.json',rb); write(out/'setup_gate.json',gate); print(json.dumps({'case_id':case['case_id'],'control_group':args.control_group,'setup_gate':gate,'pre_fsp_sha256':manifest['pre_fsp_sha256']},indent=2));
 if not gate['pass']: raise SystemExit('SETUP_GATE_FAIL')
if __name__=='__main__': main()
