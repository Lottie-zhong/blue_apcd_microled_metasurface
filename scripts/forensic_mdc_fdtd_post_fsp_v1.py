from __future__ import annotations
import hashlib, importlib.util, json, os, shutil, subprocess, sys, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import mdc_fdtd_artifact_retention as retention
import run_mdc_native_m1_2d_dipole_device_comparison_v1 as frozen
TARGET=ROOT/'outputs'/'mdc_fdtd_dipole_tmm_validation_v1'/'fdtd-matrix-20260729T092000Z-602d89c69258';RUNTIME=TARGET/'runtime';ORIGINAL=RUNTIME/'zl1_alternative__primary_mqw_centroid__x__post.fsp';FORENSIC=TARGET/'forensic';SHORT=Path(r'D:\apcd_runtime\mdc_fdtd_validation_v1\salvage\zl1_alt_centroid_x_attempt2.fsp')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True),encoding='utf-8')
def lumapi():
 p=r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py';s=importlib.util.spec_from_file_location('lumapi',p);m=importlib.util.module_from_spec(s);sys.modules['lumapi']=m;s.loader.exec_module(m);return m
def stat(p):
 s=p.stat();return {'path':str(p),'size_bytes':s.st_size,'creation_time_ns':s.st_ctime_ns,'last_write_time_ns':s.st_mtime_ns,'sha256':sha(p),'path_length':len(str(p)),'attributes':str(s.st_file_attributes) if hasattr(s,'st_file_attributes') else 'unavailable'}
def readback(path):
 lu=lumapi();f=lu.FDTD(hide=True)
 try:
  f.load(str(path)); names=[]
  for name in ('upward_monitor','emit_box_12nm_top','x_dipole'):
   try:names.append({'name':name,'exists':bool(f.getnamednumber(name))})
   except Exception as e:names.append({'name':name,'exists':False,'error':repr(e)})
  result={}
  for query in (('upward_monitor','T'),('upward_monitor','E')):
   try:
    v=f.getresult(*query);result['/'.join(query)]={'available':True,'keys':list(v.keys()) if hasattr(v,'keys') else str(type(v))}
   except Exception as e:result['/'.join(query)]={'available':False,'error':repr(e)}
  return {'load':'PASS','objects':names,'results':result,'classification':'VALID_COMPLETE' if result.get('upward_monitor/T',{}).get('available') else 'VALID_PARTIAL'}
 except Exception as e:return {'load':'FAIL','classification':'INVALID','error':repr(e)}
 finally:f.close()
def setup_save_load(path):
 lu=lumapi();f=lu.FDTD(hide=True)
 try:
  c={x['structure_key']:x for x in frozen.structures()}['zl1_alternative'];frozen.SOURCE_Y=-276e-9;case={'structure_key':'zl1_alternative','dipole':'x','simulation_time_fs':900,'autoshutoff':1e-7,'box_half_nm':12.0};frozen._build_broadband_case(f,case,c,420.,480.,301);f.save(str(path))
 finally:f.close()
 g=lu.FDTD(hide=True)
 try:g.load(str(path));ok=True
 finally:g.close()
 return {'save_load':'PASS' if ok else 'FAIL','size_bytes':path.stat().st_size,'sha256':sha(path)}
def main():
 FORENSIC.mkdir(exist_ok=True);before=stat(ORIGINAL);original=readback(ORIGINAL);after=stat(ORIGINAL)
 if before['sha256']!=after['sha256'] or before['last_write_time_ns']!=after['last_write_time_ns']:raise RuntimeError('original_mutated_during_readonly_forensics')
 short_path=SHORT;short_path.parent.mkdir(parents=True,exist_ok=True)
 if short_path.exists():short_path=short_path.with_name('zl1_alt_centroid_x_attempt2_'+uuid.uuid4().hex+'.fsp')
 shutil.copy2(ORIGINAL,short_path);copy=stat(short_path);short=readback(short_path)
 deep=FORENSIC/('deep_setup_'+uuid.uuid4().hex+'.fsp');shorttest=retention.unique_runtime_fsp('retention_test',uuid.uuid4().hex)
 a=setup_save_load(shorttest);b=setup_save_load(deep);copytest=retention.canonical_copy(shorttest,FORENSIC/('runtime_copy_'+uuid.uuid4().hex+'.fsp'))
 rootcause={'deep_path_length':len(str(deep)),'short_path_save_load':'PASS','deep_path_save_load':'PASS','existing_destination_overwrite':'NOT_TESTED_BY_DESIGN','post_run_save_failure':'PROVEN; two run-returned attempts fail saving post FSP in deep worktree','path_length':'UNPROVEN_as_root_cause','acl':'UNPROVEN','likely_scope':'post-run Lumerical save-state/path handling; setup-only save/load does not reproduce'}
 payload={'budget':{'original_solver_cap':18,'additional_authorized_cap':1,'current_solver_cap':19,'actual_solver_invocations':2,'unique_physics_cases_attempted':1,'artifact_save_failure_events':2},'original_before':before,'original_after':after,'original_readback':original,'short_copy':copy,'short_readback':short,'zero_solver_tests':{'short':a,'deep':b,'copy':copytest},'retention_diagnosis':rootcause,'solver_calls_this_task':0,'remaining_solver_capacity':17,'remaining_unique_cases':17 if original['classification']=='VALID_COMPLETE' else 18}
 dump(FORENSIC/'forensic.json',payload);print(json.dumps(payload,sort_keys=True))
if __name__=='__main__':main()
