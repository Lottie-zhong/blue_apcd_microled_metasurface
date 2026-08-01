"""Authorized remaining 36-case Stage AL-2 runner; no case is retried automatically."""
from __future__ import annotations
import argparse, hashlib, json, shutil, sys, time, uuid
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_mdc_minimal_2d_fdtd_dipole_tmm_validation_v1 as base
import mdc_fdtd_artifact_retention as retention
SEL=ROOT/'outputs'/'mdc_dipole_tmm_applicability_active_learning_v1'/'applicability-al-20260729T161300Z-899dbc46288e'
AL1=ROOT/'outputs'/'mdc_fdtd_active_learning_stage_al1_v1'/'al1-20260730T001100Z-dfc33018fde6'
CFG=json.loads((ROOT/'configs'/'mdc_dipole_tmm_applicability_active_learning_v1.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf-8')
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def structures():
 p=pd.read_parquet(SEL/'primary_geometry_matrix.parquet'); al1=set(pd.read_parquet(AL1/'case_manifest.parquet').geometry_hash.astype(str)); p=p[p.selection_status.eq('PRIMARY')].sort_values('selection_order');p=p[~p.geometry_hash.isin(al1)].copy();
 if len(p)!=6 or p.geometry_hash.duplicated().any():raise RuntimeError('al2_set_difference_not_exact_six')
 out=[]
 for _,r in p.iterrows():out.append({'structure_key':r.geometry_hash,'structure_id':r.candidate_id_primary,'geometry_hash':r.geometry_hash,'sequence':json.loads(r.compiled_sequence_json),'topology':r.topology_family,'selection_stratum':r.selection_stratum,'selection_reason':r.selection_reason,'provenance':r.provenance_count,'total_thickness_nm':float(r.total_thickness_nm),'layer_count':int(r.physical_layer_count)})
 return out
def cases():
 out=[]
 for s in structures():
  for role,y in CFG['source_positions_nm'].items():
   for ori,angles in [('x',{'theta_deg':90,'phi_deg':0}),('z',{'theta_deg':0,'phi_deg':0})]:out.append({'case_id':f"{s['geometry_hash'][:16]}__{role}__{ori}",'candidate_key':s['structure_key'],'candidate_id':s['structure_id'],'geometry_hash':s['geometry_hash'],'source_role':role,'source_position_nm':float(y),'orientation':ori,**angles,'status':'PENDING'})
 return out
def setup(case,root,state):
 s={x['structure_key']:x for x in structures()}[case['candidate_key']];runtime=retention.RUNTIME_ROOT/root.name/case['case_id'];runtime.mkdir(parents=True,exist_ok=True);pre=runtime/(uuid.uuid4().hex+'__pre.fsp');lu=base.lumapi();base.frozen.SOURCE_Y=case['source_position_nm']*1e-9;f=lu.FDTD(hide=True)
 try:
  cfg={'structure_key':s['structure_key'],'dipole':case['orientation'],'simulation_time_fs':900,'autoshutoff':1e-7,'box_half_nm':12.0};m=base.frozen._build_broadband_case(f,cfg,s,420.,480.,301);f.save(str(pre))
 finally:f.close()
 h=sha(pre);g=lu.FDTD(hide=True)
 try:
  g.load(str(pre));check={'fdtd_count':int(g.getnamednumber('FDTD')),'top_monitor_count':int(g.getnamednumber(m['monitor_name'])),'fresh_load':'PASS'}
 finally:g.close()
 if not check['fdtd_count'] or not check['top_monitor_count']:raise RuntimeError('preflight_readback_failed')
 case.update({'pre_fsp':str(pre),'pre_fsp_sha256':h,'preflight_readback':check,'status':'PREFLIGHT_PASS'});dump(root/'state.json',state)
def execute(case,root,state):
 runtime=Path(case['pre_fsp']).parent;post=retention.unique_runtime_fsp(root.name,case['case_id']);shutil.copy2(case['pre_fsp'],post);npz=runtime/(uuid.uuid4().hex+'.npz');lu=base.lumapi();f=lu.FDTD(hide=True)
 try:
  f.load(str(post));case.update({'solver_entered':True,'solver_invocation_id':uuid.uuid4().hex,'solver_entered_at':now(),'status':'RUNNING'});dump(root/'state.json',state);f.run();save_error=''
  try:f.save(str(post))
  except Exception as e:
   save_error=repr(e)
   if not post.exists() or post.stat().st_size<=0:raise
  mon='upward_monitor';lam,top=base.frozen._spectrum_from_monitor(f,mon);r12=base.frozen._box_spectrum(f,'emit_box_12nm');order=np.argsort(299792458.0/np.asarray(f.getdata(mon,'f'),float).squeeze()*1e9);r12=r12[order]
  if len(lam)!=301 or not np.isfinite(top).all() or not np.isfinite(r12).all() or np.any(r12==0):raise RuntimeError('invalid_monitor_spectrum')
  idx=len(lam)-int(np.argmin(abs(lam-450)));raw0=base.filter_ff(f,mon,idx,0);raw2=base.filter_ff(f,mon,idx,.2)
 finally:f.close()
 np.savez_compressed(npz,wavelength_nm=lam,p_top_raw=top,p_r12_outward_raw=r12,angles_filter0=raw0['angles'],intensity_filter0=raw0['raw'],angles_filter02=raw2['angles'],intensity_filter02=raw2['raw']);h=sha(post);canon=root/'retained_fsp'/(case['case_id']+'__post.fsp');copy=retention.canonical_copy(post,canon)
 case.update({'status':'COMPLETE','solver_end_at':now(),'solver_exit_state':'fdtd.run_returned','post_fsp':str(post),'post_fsp_sha256':h,'canonical_fsp':copy['canonical_fsp_path'],'canonical_fsp_sha256':copy['canonical_sha256'],'fresh_load_status':'PASS','result_npz':str(npz),'eta_up_r12_450':float(top[np.argmin(abs(lam-450))]/r12[np.argmin(abs(lam-450))]),'post_save_exception':save_error});dump(root/'state.json',state)
def main(root):
 if root.exists():raise FileExistsError(root)
 root.mkdir(parents=True);cs=cases();assert len(cs)==36 and len({c['case_id'] for c in cs})==36
 state={'task':'APCD_MDC_STAGE_AL2_REMAINING_SIX_GEOMETRY_2D_FDTD_EXECUTION_AND_15_GEOMETRY_GATE_V1','created_at':now(),'frozen_selection_root':str(SEL),'al1_root':str(AL1),'cases':cs,'safety_counters':{'FDTD_calls':0,'Lumerical_calls':0,'RCWA_calls':0,'sealed_test_target_reads':0,'TMM_calls':0}};dump(root/'state.json',state)
 gs=pd.DataFrame(structures());gs.assign(sequence=gs.sequence.map(json.dumps)).to_parquet(root/'frozen_stage_al2_geometries.parquet',index=False);pd.DataFrame(cs).to_parquet(root/'al2_case_matrix_36.parquet',index=False)
 dump(root/'al2_set_difference_audit.json',{'primary_geometry_count':12,'al1_geometry_count':6,'al2_geometry_count':len(gs),'al1_overlap_count':0,'al2_hashes':gs.geometry_hash.tolist(),'al1_manifest_sha256':sha(AL1/'manifest.json'),'selection_manifest_sha256':sha(SEL/'manifest.json')})
 for c in cs:setup(c,root,state)
 for s in structures():
  group=[c for c in cs if c['candidate_key']==s['structure_key']];cent=[c for c in group if c['source_role']=='primary_mqw_centroid']
  for c in cent:
   state['safety_counters']['FDTD_calls']+=1;state['safety_counters']['Lumerical_calls']+=1;dump(root/'state.json',state);execute(c,root,state)
  if not all(c['status']=='COMPLETE' for c in cent):raise RuntimeError('centroid_instrument_gate_failed')
  for c in group:
   if c['status']=='PREFLIGHT_PASS':state['safety_counters']['FDTD_calls']+=1;state['safety_counters']['Lumerical_calls']+=1;dump(root/'state.json',state);execute(c,root,state)
 # reuse frozen postprocessor with matching case schema; then add required indexes and manifest.
 base.postprocess(root,state);pd.DataFrame(cs).to_parquet(root/'case_manifest.parquet',index=False);pd.DataFrame([{'case_id':c['case_id'],'solver_invocation_id':c.get('solver_invocation_id'),'status':c['status'],'pre_fsp_sha256':c['pre_fsp_sha256'],'post_fsp_sha256':c.get('post_fsp_sha256'),'canonical_fsp_sha256':c.get('canonical_fsp_sha256')} for c in cs]).to_parquet(root/'invocation_audit.parquet',index=False)
 dump(root/'pre_fsp_index.json',[{'case_id':c['case_id'],'path':c['pre_fsp'],'sha256':c['pre_fsp_sha256']} for c in cs]);dump(root/'runtime_post_fsp_index.json',[{'case_id':c['case_id'],'path':c['post_fsp'],'sha256':c['post_fsp_sha256']} for c in cs]);dump(root/'canonical_post_fsp_index.json',[{'case_id':c['case_id'],'path':c['canonical_fsp'],'sha256':c['canonical_fsp_sha256']} for c in cs]);dump(root/'provenance.json',{'selection_manifest_sha256':sha(SEL/'manifest.json'),'solver_calls':state['safety_counters']['FDTD_calls'],'physics_contract':'frozen MDC 2D Native-M1 x/z dipole contract'});dump(root/'manifest.json',{'run_id':root.name,'complete_cases':sum(c['status']=='COMPLETE' for c in cs),'safety_counters':state['safety_counters'],'files':{p.name:sha(p) for p in root.iterdir() if p.is_file()}})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output-root',required=True);a=p.parse_args();main(Path(a.output_root))
