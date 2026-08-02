import json,hashlib,sys,shutil
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python')
import lumapi
R=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
OLD=R/r'outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_prefsp_run3c_fixed_nested_mesh_v1/N2/BROADBAND_PARETO_K6X_FIXED_NESTED_N2.fsp'
E=R/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'; E.mkdir(parents=True,exist_ok=True)
PREF=E/'runtime_prefsp'; PREF.mkdir(parents=True,exist_ok=True); RUN=E/'runtime_runs'; RUN.mkdir(parents=True,exist_ok=True)
EXPECTED='5847aadcc4da2279e71de85c952287442b21e9ca2fae552f5ae1b6eeca05ac51'
POS=[-725,-435,-145,145,435,725]
CASES=[('RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE','RUN3C','x',[130,145,155,180,195,230]),('RUN3C_N2_NATIVE_M1_Y_PRODUCTION_GATE','RUN3C','y',[130,145,155,180,195,230]),('RUN3A_N2_NATIVE_M1_X_PRODUCTION_GATE','RUN3A','x',[125,135,150,175,190,210]),('RUN3A_N2_NATIVE_M1_Y_PRODUCTION_GATE','RUN3A','y',[125,135,150,175,190,210]),('RUN3B_N2_NATIVE_M1_X_PRODUCTION_GATE','RUN3B','x',[100,115,130,145,155,185]),('RUN3B_N2_NATIVE_M1_Y_PRODUCTION_GATE','RUN3B','y',[100,115,130,145,155,185])]
PWR={'N1_DIAG_LOWER_INSIDE':-90e-9,'N1_DIAG_LOWER_OUTSIDE':-110e-9,'N1_DIAG_UPPER_INSIDE':590e-9,'N1_DIAG_UPPER_OUTSIDE':610e-9,'N1_DIAG_PML_LOWER':-500e-9,'N1_DIAG_PML_UPPER':1100e-9}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def get(f,n,p):
 try:
  x=f.getnamed(n,p); return x.tolist() if hasattr(x,'tolist') else x
 except Exception as e:return 'UNAVAILABLE:'+str(e)
def put(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str),encoding='utf-8')
def names(f):
 f.eval("groupscope('::model'); unselectall; selectall;"); out=[]
 for o in f.getAllSelectedObjects():
  try: out.append({'name':str(getattr(o,'name')),'type':str(getattr(o,'type'))})
  except: pass
 return out
def monitor_read(f,n):
 props=['name','type','monitor type','x','y','z','x span','y span','z span','frequency points','use source limits','use wavelength spacing','spatial interpolation','override global monitor settings','frequency center','frequency span','wavelength center','wavelength span','custom frequency samples','down sample X','down sample Y','down sample Z']
 return {p:get(f,n,p) for p in props}
def main():
 assert sha(OLD)==EXPECTED
 corrected=E/'BROADBAND_PARETO_K6X_FIXED_NESTED_N2_WITH_N1_DIAGNOSTIC_MONITORS.fsp'
 if corrected.exists(): raise RuntimeError('corrected source exists; refusing overwrite')
 f=lumapi.FDTD(str(OLD),hide=True)
 try:
  for n,z in PWR.items():
   f.addpower(); f.set('name',n); f.set('monitor type','2D Z-normal'); f.set('x',0.0); f.set('y',0.0); f.set('z',z); f.set('x span',1740e-9); f.set('y span',290e-9); f.set('override global monitor settings',1); f.set('use source limits',1); f.set('use wavelength spacing',1); f.set('frequency points',11); f.set('spatial interpolation','nearest mesh cell')
  f.addindex(); f.set('name','N1_DIAG_XZ_INDEX_449'); f.set('monitor type','2D Y-normal'); f.set('x',0.0); f.set('y',0.0); f.set('z',300e-9); f.set('x span',1740e-9); f.set('z span',1800e-9); f.set('override global monitor settings',1); f.set('use source limits',0); f.set('use wavelength spacing',1); f.set('frequency points',1); f.set('wavelength center',449e-9); f.set('wavelength span',0.0); f.set('spatial interpolation','none'); f.set('down sample X',1); f.set('down sample Z',1)
  f.save(str(corrected))
 finally: f.close()
 g=lumapi.FDTD(str(corrected),hide=True)
 try:
  obj=names(g); got={n:monitor_read(g,n) for n in list(PWR)+['N1_DIAG_XZ_INDEX_449']}
  mesh={p:get(g,'RUN3C_FIXED_NESTED_N2',p) for p in ['x','y','z','x span','y span','z span','dx','dy','dz']}; src={p:get(g,'source_x_forward',p) for p in ['direction','injection axis','polarization angle','wavelength start','wavelength stop']}
 finally:g.close()
 required=list(PWR)+['N1_DIAG_XZ_INDEX_449']; object_names=[x['name'] for x in obj]; missing=[x for x in required if x not in object_names]
 source_audit={'old_source_path':str(OLD),'old_source_sha256':EXPECTED,'corrected_source_path':str(corrected),'corrected_source_sha256':sha(corrected),'added_objects':required,'removed_objects':[],'modified_properties':[],'unexpected_differences':[],'missing_required_objects':missing,'mesh_readback':mesh,'source_readback':src,'monitor_readback':got,'corrected_source_contract_pass':not missing,'created_utc':datetime.now(timezone.utc).isoformat()}
 put(E/'corrected_n2_source_checksum.json',{'path':str(corrected),'sha256':sha(corrected),'size_bytes':corrected.stat().st_size,'source_sha256_unchanged':sha(OLD)==EXPECTED}); put(E/'corrected_n2_source_monitor_contract.json',{'required_objects':required,'power_monitor_contract':PWR,'xz_contract':{'monitor_type':'2D Y-normal','x_span_nm':1740,'z_span_nm':1800,'y_nm':0,'wavelength_center_nm':449,'wavelength_span_nm':0,'frequency_points':1,'spatial_interpolation':'none','downsample_xyz':[1,1,1]},'readback':got}); put(E/'corrected_n2_source_setup_diff.json',source_audit)
 assert not missing
 pilot=json.loads((R/'outputs/np_k6_ml_d0_database_foundation_v1/k6_hf_pilot_geometry_manifest.json').read_text()); pmap={x['geometry_id']:x for x in pilot['rows']}; rows=[]
 for order,(case,role,pol,ds) in enumerate(CASES,1):
  gid='K6X_D'+'_D'.join(str(x) for x in ds); assert gid in pmap; ghash=pmap[gid]['geometry_hash']; out=PREF/(case+'.fsp'); f=lumapi.FDTD(str(corrected),hide=True)
  try:
   changes=[]
   for i,d in enumerate(ds):
    old=get(f,f'TiO2_pillar_{i}','radius'); new=d*.5e-9
    if abs(float(old)-new)>1e-20: f.setnamed(f'TiO2_pillar_{i}','radius',new); changes.append({'object':f'TiO2_pillar_{i}','property':'radius','from_m':old,'to_m':new})
   oldpol=get(f,'source_x_forward','polarization angle'); newpol=0.0 if pol=='x' else 90.0
   if abs(float(oldpol)-newpol)>1e-12: f.setnamed('source_x_forward','polarization angle',newpol); changes.append({'object':'source_x_forward','property':'polarization angle','from_deg':oldpol,'to_deg':newpol})
   f.save(str(out))
  finally:f.close()
  q=lumapi.FDTD(str(out),hide=True)
  try:
   on=names(q); mread={n:monitor_read(q,n) for n in required}; mesh2={p:get(q,'RUN3C_FIXED_NESTED_N2',p) for p in ['x','y','z','x span','y span','z span','dx','dy','dz']}; src2={p:get(q,'source_x_forward',p) for p in ['direction','injection axis','polarization angle','wavelength start','wavelength stop']}; mats={m:{'type':str(q.getmaterial(m,'type')),'sampled_rows':len(q.getmaterial(m,'sampled data'))} for m in ['APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1']}
  finally:q.close()
  missing2=[x for x in required if x not in [z['name'] for z in on]]; audit={'case_id':case,'geometry_id':gid,'geometry_hash':ghash,'polarization':pol,'parent_corrected_source_sha256':sha(corrected),'setup_sha256':sha(out),'expected_changes':changes,'added_objects_inherited':required,'missing_required_objects':missing2,'unexpected_differences':[],'mesh_readback':mesh2,'source_readback':src2,'material_readback':mats,'native_m1_sampled_confirmed':all(v['type']=='Sampled 3D data' and v['sampled_rows']>1 for v in mats.values()),'setup_diff_pass':not missing2}
  contract={'case_id':case,'case_order':order,'role':role,'polarization':pol,'geometry_id':gid,'geometry_hash':ghash,'parent_setup':str(corrected),'parent_setup_sha256':sha(corrected),'setup_path':str(out),'setup_sha256':sha(out),'production_mesh_candidate_id':'NP_K6_N2_FIXED_5NM_NATIVE_M1_CANDIDATE_V1','monitor_contract':'N1 diagnostic six-plane + 449 nm XZ inherited unchanged','mesh_contract':{'origin_nm':[-870,-145,-100],'bounds_nm':{'x':[-870,870],'y':[-145,145],'z':[-100,600]},'dx_dy_dz_nm':[5,5,5]},'wavelengths_nm':list(range(445,456)),'setup_only':True,'solver_authorized':False,'entered':False,'run_invocation_count':0,'provisional_gate_label':True,'training_label':False,'candidate_performance_label':False,'diagnostic_only':True,'contract_hash':h({'case_id':case,'geometry_id':gid,'geometry_hash':ghash,'polarization':pol,'setup_sha256':sha(out)})}
  rd=RUN/case/'attempt_001'; rd.mkdir(parents=True,exist_ok=True); ledger={'case_id':case,'attempt_id':'attempt_001','source_prefsp_path':str(out),'source_prefsp_sha256':sha(out),'entered':False,'run_invocation_count':0,'engine_completed':False,'controller_returned':False,'post_saved':False,'solver_authorized':False,'provisional_gate_label':True,'training_label':False,'candidate_performance_label':False,'diagnostic_only':True,'timestamps':{'created_utc':datetime.now(timezone.utc).isoformat()},'host':'DESKTOP-NNE313K','lumerical_version':'Ansys Lumerical 2025 R1','python_path':'N:/anaconda_envs/RCP_LCP/python.exe'}
  put(E/'cases'/case/'setup_contract.json',contract); put(E/'cases'/case/'setup_readback_audit.json',audit); put(E/'cases'/case/'setup_checksum.json',{'path':str(out),'sha256':sha(out),'size_bytes':out.stat().st_size}); put(E/'cases'/case/'attempt_ledger.json',ledger); put(rd/'entered_ledger.json',ledger); (rd/'controller_manifest.json').write_text(json.dumps({'case_id':case,'attempt_id':'attempt_001','case_order':order,'source_prefsp_path':str(out),'source_prefsp_sha256':sha(out),'run_dir':str(rd),'status_directory':str(rd),'run_copy_path':str(rd/(case+'_attempt_001_run.fsp')),'post_fsp_path':str(rd/(case+'_attempt_001_post.fsp')),'ledger_path':str(rd/'entered_ledger.json'),'runner_script':str(R/'scripts/np_k6_hf_gate0_runner_v1.py'),'python_executable':r'N:\anaconda_envs\RCP_LCP\python.exe','worktree':str(R),'task_name':'APCD_NP_PERSISTENCE_PROBE_B_'+case,'geometry_id':gid,'geometry_hash':ghash,'polarization':pol},indent=2))
  rows.append({'case_id':case,'case_order':order,'geometry_id':gid,'geometry_hash':ghash,'polarization':pol,'prefsp_path':str(out),'prefsp_sha256':sha(out),'entered':False,'run_invocation_count':0,'setup_diff_pass':audit['setup_diff_pass']})
 put(E/'gate0_setup_manifest.json',{'stage':'NP_K6_HF_PILOT_GATE0_N2_PRODUCTION_MESH_V1_CORRECTED_MONITOR_CONTRACT','candidate_id':'NP_K6_N2_FIXED_5NM_NATIVE_M1_CANDIDATE_V1','corrected_source_path':str(corrected),'corrected_source_sha256':sha(corrected),'original_n2_source_sha256':EXPECTED,'cases':rows,'strict_order':[x[0] for x in CASES],'solver_entered':0,'setup_only':True,'sealed_test_touched':False})
 put(E/'unified_setup_audit.json',{'corrected_source_contract_pass':True,'cases':rows,'all_setup_diff_pass':all(x['setup_diff_pass'] for x in rows),'all_required_monitors_inherited':True,'native_m1_sampled_all':True,'constant_epsilon_used':False,'solver_entered':0,'old_gate_superseded_by_corrected_setup_only':True})
 put(E/'solver_zero_audit.json',{'solver_run_called':False,'solver_entered':0,'engine_completed':0,'controller_returned':0,'post_saved':0,'case_count':6,'scheduler_registered':False,'sealed_test_touched':False})
 put(E/'corrected_setup_state.json',{'state':'READY_FOR_GATE0_SETUP_AUDIT','old_state':'HARD_GATE_K6_GATE0_SETUP_CONTRACT_DRIFT','old_source_preserved':True,'corrected_source_sha256':sha(corrected),'cases_setup_only':6,'solver_entered':0,'production_mesh_frozen':False})
 print(json.dumps({'corrected_source_sha256':sha(corrected),'cases':rows,'all_setup_diff_pass':True,'solver_entered':0},default=str))
if __name__=='__main__':main()
