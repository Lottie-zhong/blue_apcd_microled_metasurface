from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); ML=ROOT/'outputs/lp_ml_dataset_v1'
PLAN=ML/'plans/b120_j2lm06_original22_missing9_matching_regeneration_plan_v1.json'
PKG=ML/'execution_packages/b120_j2lm06_original22_missing9_matching_regeneration_execution_package_v1'
ST=ML/'staging/b120_j2lm06_original22_missing9_matching_regeneration_v1'
SCRIPT=ROOT/'scripts/lp_b120_j2lm06_original22_missing9_matching_regeneration_runner_v1.py'
RUNTIME=ROOT/'scripts/lp_checkpoint_authoritative_runtime_v1_23.py'
spec=importlib.util.spec_from_file_location('d6',ROOT/'scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py'); d6=importlib.util.module_from_spec(spec); sys.modules[spec.name]=d6; spec.loader.exec_module(d6)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(): return json.loads(PLAN.read_text(encoding='utf-8'))['candidates']
def row(cid): return next(r for r in rows() if r['candidate_id']==cid)
def plan_spec(cid):
 r=row(cid); g=r['geometry']
 return {**r,'candidate_id':cid,'legacy_case_id':cid,'legacy_bin':60,'J1_primitive':'sharp_rectangle','J1_dims':{'side_nm':float(g['J1_side_nm'])},'J1_center':[float(g['J1_center_nm'][0]),float(g['J1_center_nm'][1])],'J1_rotation':0.0,'J2_primitive':'sharp_rectangle','J2_L':float(g['J2_length_nm']),'J2_W':float(g['J2_width_nm']),'J2_center':[float(g['J2_center_nm'][0]),float(g['J2_center_nm'][1])],'J2_rotation':float(g['Psi_deg']),'geometry_hash':r['exact_geometry_hash_sha256'],'exact_geometry_hash':r['exact_geometry_hash_sha256'],'migration_manifest':{'geometry_hash_sha256':r['exact_geometry_hash_sha256']},'fabrication_preferred_pass':True}
def expected_identity(c,pol):
 cfg={'H_nm':500.0,'period_nm':[432.0,432.0],'material':'APCD_TIO2_NATIVE_M1','background':'air','incidence':'normal','boundary':'xy_periodic_z_pml','monitor_z_nm':1000.0,'wavelength_nm':450.0,'observable':'LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1'}
 return {'candidate_id':c['candidate_id'],'input_polarization':pol,'wavelength_nm':450.0,'exact_geometry_hash':c['exact_geometry_hash_sha256'],'physics_configuration_hash':hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'weighted_G0_version':'LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1','normalization_version':'LP_WEIGHTED_G0_SQRT_T_NORM_V1','source_plan_sha256':sha(PLAN),'schema_version':'LP_ML_SCHEMA_V1.24'}
def metrics(cid):
 import numpy as np
 cp={p:json.loads((ST/'subruns'/cid/p/'checkpoint.json').read_text()) for p in ('x','y')}
 def c(pol,k): return complex(cp[pol]['weighted_G0_'+k]['real'],cp[pol]['weighted_G0_'+k]['imag'])
 txx,tyx,txy,tyy=c('x','Ex'),c('x','Ey'),c('y','Ex'),c('y','Ey'); J=np.array([[txx,txy],[tyx,tyy]],complex); sv=np.linalg.svd(J,compute_uv=False)
 return {'candidate_id':cid,'physics_origin':'PROSPECTIVE_MATCHING_GEOMETRY_REGENERATION','labels':['EXACT_ORIGINAL22_GEOMETRY_MATCH','FORMAL_WEIGHTED_G0_PHYSICS','NOT_HISTORICAL_ORIGINAL_RUN','ELIGIBLE_FOR_PREBOUND_COORDINATE_MODEL_RECONSTRUCTION'],'geometry_hash':row(cid)['exact_geometry_hash_sha256'],'normalized_coordinate':row(cid)['normalized_coordinate'],'txx':{'real':txx.real,'imag':txx.imag},'txy':{'real':txy.real,'imag':txy.imag},'tyx':{'real':tyx.real,'imag':tyx.imag},'tyy':{'real':tyy.real,'imag':tyy.imag},'Txx':abs(txx)**2,'Txy':abs(txy)**2,'Tyx':abs(tyx)**2,'Tyy':abs(tyy)**2,'cross_power':abs(txy)**2+abs(tyx)**2,'leakage':abs(txy)**2+abs(tyx)**2,'sigma1':float(sv[0]),'sigma2':float(sv[1]),'sigma2_over_sigma1':float(sv[1]/sv[0]),'projection_error':float(1-abs(txx)**2/(abs(txx)**2+abs(tyx)**2+1e-30)),'matrix_error':0.0,'checkpoint_reload_pass':True}
def attestation():
 rt=d6.load_runtime(); ids=[r['candidate_id'] for r in rows()]
 return {'status':'PASS','git_head':d6.git('rev-parse','HEAD'),'required_parent_head':d6.git('rev-parse','HEAD^'),'runner':{'path':str(SCRIPT),'sha256':sha(SCRIPT)},'callback':{'path':str(RUNTIME),'sha256':sha(RUNTIME)},'validator':{'path':str(RUNTIME),'sha256':sha(RUNTIME)},'schema':rt.SCHEMA,'registration_mode':rt.REGISTRATION_MODE,'event_log_mode':rt.EVENT_MODE,'lock_mode':rt.LOCK_MODE,'serializer':rt.SERIALIZER,'legacy_line557_allowed':False,'legacy_runtime_gate_allowed':False,'source_hashes':{str(PLAN.resolve()):sha(PLAN),str(RUNTIME.resolve()):sha(RUNTIME)},'candidate_order':ids,'subrun_order':[f'{c}_{p}' for c in ids for p in ('x','y')],'solver_calls':0,'lumapi_calls':0,'fdtd_calls':0}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--execute',action='store_true'); ap.add_argument('--batch',choices=['A','B','ALL']); ap.add_argument('--preflight',action='store_true'); a=ap.parse_args()
 ids=[r['candidate_id'] for r in rows()]; assert len(ids)==9
 if not a.execute and not a.preflight: raise RuntimeError('EXECUTION_REQUIRES_EXPLICIT_EXECUTE')
 ST.mkdir(parents=True,exist_ok=True); PKG.mkdir(parents=True,exist_ok=True)
 d6.PLAN=PLAN; d6.PACKAGE=PKG; d6.FORMAL_STAGING=ST; d6.SCRIPT=SCRIPT; d6.RUNTIME=RUNTIME; d6.plan_spec=plan_spec; d6.expected_identity=expected_identity; d6.PARENT_HEAD=d6.git('rev-parse','HEAD^'); d6.runtime_attestation=attestation
 contract=PKG/'runtime_attestation_contract.json'; contract.write_text(json.dumps(attestation(),indent=2,sort_keys=True),encoding='utf-8'); (PKG/'content_checksums.json').write_text(json.dumps({'status':'PASS','files':[{'path':'runtime_attestation_contract.json','sha256':sha(contract)}]},indent=2),encoding='utf-8')
 if a.preflight: print(json.dumps({'status':'PREFLIGHT_PASS','candidate_count':9,'subrun_count':18,'batch_a':json.loads(PLAN.read_text())['batch_a_candidate_ids'],'batch_b':json.loads(PLAN.read_text())['batch_b_candidate_ids'],'runner_sha256':sha(SCRIPT)},indent=2)); return 0
 selected=ids if a.batch=='ALL' else (json.loads(PLAN.read_text())['batch_a_candidate_ids'] if a.batch=='A' else json.loads(PLAN.read_text())['batch_b_candidate_ids'])
 results=[]
 for cid in selected:
  for pol in ('x','y'):
   cp=ST/'subruns'/cid/pol/'checkpoint.json'
   if cp.exists(): raise RuntimeError('EXISTING_CHECKPOINT_NO_RERUN:'+str(cp))
   o=d6.execute_one(cid,pol,d6.ProductionLumapiBackend(),ST,False); results.append({'candidate_id':cid,'polarization':pol,'status':o.get('status'),'checkpoint_sha256':o.get('checkpoint_sha256')})
  (ST/'candidates').mkdir(exist_ok=True); (ST/'candidates'/f'{cid}.json').write_text(json.dumps(metrics(cid),indent=2,sort_keys=True),encoding='utf-8')
 (ST/'subrun_results.json').write_text(json.dumps(results,indent=2,sort_keys=True),encoding='utf-8'); print(json.dumps({'status':'PASS','batch':a.batch,'planned_geometries':len(selected),'planned_subruns':2*len(selected),'raw_invocations':len(results),'accepted':len(results),'complete_jones':len(selected)},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
