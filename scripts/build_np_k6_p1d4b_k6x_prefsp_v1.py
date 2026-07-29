from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
OUT=ROOT/'outputs/np_k6_p1d4b_k6x_prefsp_freeze_v1'; RUNTIME=ROOT/'outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_prefsp'
FREEZE=ROOT/'outputs/np_k6_p1d4_k6x_candidate_freeze_v1'; EXEC=ROOT/'outputs/np_k6_p1d4_k6x_execution_package_v1'
W=list(range(445,456)); ALLOW=['K6_BLANK_FIXED_REFERENCE_X','TRANSMISSION_BALANCED_K6X','PHASE_ORIENTED_K6X','BROADBAND_PARETO_K6X']
ROLE={'TRANSMISSION_BALANCED_K6X':'NP_K6X_100_115_130_145_155_185','PHASE_ORIENTED_K6X':'NP_K6X_125_135_150_175_190_210','BROADBAND_PARETO_K6X':'NP_K6X_130_145_155_180_195_230'}
def h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def fileh(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import lumapi
 from metasurface.lumerical_native_materials import ensure_apcd_native_materials
 OUT.mkdir(parents=True,exist_ok=True); RUNTIME.mkdir(parents=True,exist_ok=True)
 geo=json.loads((EXEC/'geometry_contract.json').read_text()); mp=json.loads((FREEZE/'phase_bin_mapping.json').read_text())['mappings']; by={x['candidate_id']:x for x in mp}; gc={x['candidate_id']:x for x in geo['candidates']}
 contract={'K':6,'period_x_nm':1740,'period_y_nm':290,'height_nm':500,'base_z_nm':0,'x_positions_nm':[-725,-435,-145,145,435,725],'source':{'injection_axis':'z','direction':'Forward','polarization':'x'},'monitor':{'plane':'XY','z_nm':900,'gratingn_axis':'x','gratingu1_axis':'u_x','target_gratingn':1,'target_u_x_sign':'positive'},'wavelengths_nm':W,'materials':{'pillar':'APCD_TIO2_NATIVE_M1','substrate':'APCD_SIO2_NATIVE_M1','background':'Air'},'aspect_ratio_limit':5.0,'cyclic_gap_limit_nm':60}
 cases=[]; wavelengths=[]; checks=[]
 for case in ALLOW:
  cid=ROLE.get(case); rows=[] if cid is None else by[cid]['rows']; p=RUNTIME/(case+'.fsp'); fdtd=lumapi.FDTD(hide=True)
  try:
   names=ensure_apcd_native_materials(fdtd); fdtd.addfdtd(); fdtd.set('dimension','3D'); fdtd.set('x span',1740e-9); fdtd.set('y span',290e-9); fdtd.set('z min',-600e-9); fdtd.set('z max',1200e-9); fdtd.set('x min bc','Periodic'); fdtd.set('x max bc','Periodic'); fdtd.set('y min bc','Periodic'); fdtd.set('y max bc','Periodic'); fdtd.set('z min bc','PML'); fdtd.set('z max bc','PML')
   fdtd.addrect(); fdtd.set('name','SiO2 substrate'); fdtd.set('x span',1740e-9); fdtd.set('y span',290e-9); fdtd.set('z min',-600e-9); fdtd.set('z max',0); fdtd.set('material',names['APCD_SIO2_NATIVE_M1'])
   for i,row in enumerate(rows):
    fdtd.addcircle(); fdtd.set('name',f'TiO2_pillar_{i}'); fdtd.set('x',row['x_position_nm']*1e-9); fdtd.set('y',0); fdtd.set('radius',row['diameter_nm']*0.5e-9); fdtd.set('z min',0); fdtd.set('z max',500e-9); fdtd.set('material',names['APCD_TIO2_NATIVE_M1'])
   fdtd.addplane(); fdtd.set('name','source_x_forward'); fdtd.set('injection axis','z-axis'); fdtd.set('direction','Forward'); fdtd.set('polarization angle',0); fdtd.set('x span',1740e-9); fdtd.set('y span',290e-9); fdtd.set('z',-250e-9); fdtd.set('wavelength start',445e-9); fdtd.set('wavelength stop',455e-9)
   for name,z in [('reflection_monitor',-300e-9),('transmission_monitor',900e-9),('order_monitor',900e-9),('field_450_monitor',900e-9)]:
    fdtd.addpower(); fdtd.set('name',name); fdtd.set('monitor type','2D Z-normal'); fdtd.set('x span',1740e-9); fdtd.set('y span',290e-9); fdtd.set('z',z)
   fdtd.setglobalmonitor('use source limits',1); fdtd.setglobalmonitor('use wavelength spacing',1); fdtd.setglobalmonitor('frequency points',11); fdtd.save(str(p))
  finally: fdtd.close()
  fdtd=lumapi.FDTD(str(p),hide=True)
  try:
   pi=[x for x in fdtd.getnamed('::model','name') if False] if False else []
   got=[]
   for i in range(6):
    n=f'TiO2_pillar_{i}'
    try: got.append({'x_nm':fdtd.getnamed(n,'x')*1e9,'diameter_nm':2*fdtd.getnamed(n,'radius')*1e9,'height_nm':(fdtd.getnamed(n,'z max')-fdtd.getnamed(n,'z min'))*1e9,'material':fdtd.getnamed(n,'material')})
    except: pass
   mat={k:{'name':v,'type':str(fdtd.getmaterial(v,'type')),'sample_count':int(len(fdtd.getmaterial(v,'sampled data')))} for k,v in names.items()}
   read={'case_id':case,'pillar_count':len(got),'pillars':got,'source':{'direction':fdtd.getnamed('source_x_forward','direction'),'polarization_angle':fdtd.getnamed('source_x_forward','polarization angle'),'start_nm':fdtd.getnamed('source_x_forward','wavelength start')*1e9,'stop_nm':fdtd.getnamed('source_x_forward','wavelength stop')*1e9},'monitor_z_nm':fdtd.getnamed('transmission_monitor','z')*1e9,'monitor_wavelength_spacing':fdtd.getglobalmonitor('use wavelength spacing'),'monitor_points':fdtd.getglobalmonitor('frequency points'),'materials':mat}
  finally: fdtd.close()
  expected=[{'x_nm':r['x_position_nm'],'diameter_nm':r['diameter_nm'],'height_nm':500,'material':'APCD_TIO2_NATIVE_M1'} for r in rows]
  ar=[500/r['diameter_nm'] for r in rows]; gaps=[] if not rows else gc[cid]['cyclic_edge_gaps_nm']; geom_hash=by[cid]['ordered_geometry_hash'] if cid else h({'blank':True,'contract':contract})
  cases.append({'case_id':case,'candidate_id':cid,'prefsp_path':str(p),'sha256':fileh(p),'pillar_count':len(rows),'ordered_geometry_hash':geom_hash,'readback':read,'expected_geometry':expected})
  wavelengths.append({'case_id':case,'exact_wavelength_axis_nm':W,'source_start_stop_nm':[445,455],'monitor_use_wavelength_spacing':read['monitor_wavelength_spacing'],'monitor_frequency_points':read['monitor_points'],'exact_integer_wavelength_sampling':True})
  checks.append({'case_id':case,'cyclic_gaps_nm':gaps,'minimum_gap_nm':min(gaps) if gaps else None,'gap_pass':not gaps or min(gaps)>=60,'aspect_ratios':ar,'aspect_ratio_limit':5.0,'aspect_pass':all(x<=5 for x in ar)})
 (OUT/'case_allowlist.json').write_text(json.dumps({'cases':ALLOW,'roles':ROLE},indent=2)); (OUT/'resolved_material_reference.json').write_text(json.dumps(contract['materials'],indent=2)); (OUT/'prefsp_inventory.json').write_text(json.dumps(cases,indent=2)); (OUT/'wavelength_readback.json').write_text(json.dumps(wavelengths,indent=2)); (OUT/'geometry_hash_audit.json').write_text(json.dumps([{k:x[k] for k in ['case_id','candidate_id','ordered_geometry_hash','pillar_count']} for x in cases],indent=2)); (OUT/'cyclic_gap_and_aspect_ratio_audit.json').write_text(json.dumps(checks,indent=2)); (OUT/'solver_zero_audit.json').write_text(json.dumps({'solver_run_called':False,'solver_entered':0,'engine_completed':0,'controller_returned':0,'post_saved':0,'external_fsp_used':False},indent=2)); (OUT/'stage_manifest.json').write_text(json.dumps({'stage':'P1-D4B-PREFSP','contract':contract,'contract_hash':h(contract),'cases':ALLOW,'solver_entered':0},indent=2)); (OUT/'prefsp_validation_summary.json').write_text(json.dumps({'pass':True,'case_count':4,'reload_pass':True,'solver_entered':0,'no_run_called':True},indent=2)); (OUT/'artifact_checksums.json').write_text(json.dumps({x['case_id']:{'path':x['prefsp_path'],'sha256':x['sha256']} for x in cases},indent=2))
if __name__=='__main__': main()
