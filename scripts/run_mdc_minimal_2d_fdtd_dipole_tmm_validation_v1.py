"""Bounded 18-subrun MDC 2D dipole/FDTD validation matrix.

Uses the frozen project-local Native-M1 build primitives but writes all state,
FSPs and results to an isolated run root. No existing FDTD or TMM artifact is
read-write reused.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, shutil, sys, time, traceback, uuid
from pathlib import Path
from typing import Any
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
import run_mdc_native_m1_2d_dipole_device_comparison_v1 as frozen
import mdc_fdtd_2d_monitor_contract_v1 as monitor
import mdc_fdtd_artifact_retention as retention
CONFIG=json.loads((ROOT/'configs'/'mdc_minimal_2d_fdtd_dipole_tmm_validation_v1.json').read_text())
MATERIALS=('APCD_GAN_NATIVE_M1','APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True),encoding='utf-8')
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def lumapi():
 p=r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py';s=importlib.util.spec_from_file_location('lumapi',p);m=importlib.util.module_from_spec(s);sys.modules['lumapi']=m;s.loader.exec_module(m);return m
def candidates():
 records={x['structure_key']:x for x in frozen.structures()}
 required=('bare','zl1_alternative');control='zl1_nominal' if 'zl1_nominal' in records else ('explicit' if 'explicit' in records else None)
 if any(x not in records for x in required):raise RuntimeError('frozen_candidate_missing')
 result=[records['bare'],records['zl1_alternative']]+([records[control]] if control else [])
 alt=result[1]
 if alt['geometry_hash']!='c38694d6f162c04322ae8a87def91622d4fd4f272e4ec286e85acc978f74d888':raise RuntimeError('alternative_geometry_hash_conflict')
 return result
def plan():
 rows=[]
 for c in candidates():
  for role,y in zip(('top_primary_well','primary_mqw_centroid','bottom_primary_well'),CONFIG['positions_nm']):
   for ori,ang in CONFIG['orientations'].items():rows.append({'case_id':f"{c['structure_key']}__{role}__{ori}",'candidate_key':c['structure_key'],'candidate_id':'BARE_GAN_AIR_REFERENCE' if c['structure_key']=='bare' else c['structure_id'],'geometry_hash':c['geometry_hash'],'source_role':role,'source_position_nm':y,'orientation':ori,**ang,'stage':'A' if c['structure_key']=='zl1_alternative' and role=='primary_mqw_centroid' else 'B','status':'PENDING'})
 return rows
def metric(angle,intensity):
 a=np.asarray(angle,float); i=np.abs(np.asarray(intensity,float));o=np.argsort(a);a=a[o];i=i[o]
 mask=np.abs(a)<=60;a=a[mask];i=i[mask];norm=i/np.trapezoid(i,np.deg2rad(a));peak=float(a[np.argmax(i)]);half=i.max()/2;hit=np.flatnonzero(i>=half);fwhm=float(a[hit[-1]]-a[hit[0]]) if len(hit) else float('nan')
 def cone(d):
  m=np.abs(a)<=d;return float(np.trapezoid(norm[m],np.deg2rad(a[m])))
 return {'peak_angle_set_deg':json.dumps(sorted(a[np.isclose(i,i.max())].tolist()),separators=(',',':')),'angular_fwhm_deg':fwhm,'cone5_fraction':cone(5),'cone10_fraction':cone(10),'cone20_fraction':cone(20),'symmetry_residual':float(np.max(np.abs(i-i[::-1]))),'normalized':norm,'angles':a,'raw':i}
def sfwhm(w,v):
 hit=np.flatnonzero(v>=v.max()/2);return float(w[hit[-1]]-w[hit[0]]) if len(hit) else float('nan')
def filter_ff(f,mon,index,value):
 # Lumerical's filter modifies only far-field projection postprocessing, not the solve.
 f.eval(f'farfieldfilter({float(value)});');ff=np.asarray(f.farfield2d(mon,index)).squeeze();ang=np.asarray(f.farfieldangle(mon,index)).squeeze();deg=np.degrees(ang) if np.max(abs(ang))<=np.pi+1 else ang;return metric(deg,ff)
def execute(case,root,state):
 structures={x['structure_key']:x for x in candidates()};structure=structures[case['candidate_key']]; stem=case['case_id'];runtime=retention.RUNTIME_ROOT/root.name/stem;runtime.mkdir(parents=True,exist_ok=True);pre=runtime/(uuid.uuid4().hex+'__pre.fsp');post=retention.unique_runtime_fsp(root.name,stem);npz=runtime/(uuid.uuid4().hex+'.npz');lu=lumapi();frozen.SOURCE_Y=case['source_position_nm']*1e-9
 # The verified lifecycle is intentionally two sessions: build/save/close,
 # then a genuinely fresh session load/run/extract.  No solver ledger is
 # written until the fresh load succeeds and the next operation is f.run().
 setup_f=lu.FDTD(hide=True)
 try:
  build={'structure_key':structure['structure_key'],'dipole':case['orientation'],'simulation_time_fs':900,'autoshutoff':1e-7,'box_half_nm':12.0}
  setup=frozen._build_broadband_case(setup_f,build,structure,420.,480.,301);setup_f.save(str(pre));pre_sha=sha(pre);shutil.copy2(pre,post)
 finally: setup_f.close()
 f=lu.FDTD(hide=True)
 try:
  f.load(str(post));case.update({'solver_entered':True,'solver_entered_at':now(),'pre_fsp':str(pre),'pre_fsp_sha256':pre_sha,'physical_contract_hash':state['physical_contract_hash'],'status':'RUNNING'});dump(root/'state.json',state)
  f.run(); f.save(str(post)); post_sha=sha(post); mon=setup['monitor_name'];lam,p_top=frozen._spectrum_from_monitor(f,mon);r12=frozen._box_spectrum(f,'emit_box_12nm');order=np.argsort(299792458.0/np.asarray(f.getdata(mon,'f'),float).squeeze()*1e9);r12=r12[order]
  if len(lam)!=301 or not all(np.all(np.isfinite(x)) for x in (lam,p_top,r12)) or np.any(r12<=0):raise RuntimeError('invalid_monitor_spectrum')
  idx=len(lam)-int(np.argmin(abs(lam-450.0))); raw0=filter_ff(f,mon,idx,0);raw2=filter_ff(f,mon,idx,.2)
  inventory={'materials':list(MATERIALS),'monitor_data':monitor.read_monitor_data_inventory(f,mon),'objects':'fresh_load_readback','plane_source_present':False,'boundaries':'x/y PML'}
 finally:f.close()
 np.savez_compressed(npz,wavelength_nm=lam,p_top_raw=p_top,p_r12_outward_raw=r12,angles_filter0=raw0['angles'],intensity_filter0=raw0['raw'],angles_filter02=raw2['angles'],intensity_filter02=raw2['raw'])
 case.update({'status':'COMPLETE','solver_exit_state':'fdtd.run_returned','solver_end_at':now(),'post_fsp':str(post),'post_fsp_sha256':post_sha,'result_npz':str(npz),'p_top_nonzero':bool(np.any(abs(p_top)>0)),'p_r12_outward_nonzero':bool(np.any(abs(r12)>0)),'eta_up_r12_450':float(p_top[np.argmin(abs(lam-450))]/r12[np.argmin(abs(lam-450))]),'inventory':inventory,'runtime_s':0.0});dump(root/'state.json',state)
 return {'case':case,'lambda':lam,'top':p_top,'r12':r12,'f0':raw0,'f02':raw2}
def postprocess(root,state):
 results=[]
 for c in state['cases']:
  z=np.load(c['result_npz']); f0=metric(z['angles_filter0'],z['intensity_filter0']);f2=metric(z['angles_filter02'],z['intensity_filter02']);results.append({'case':c,'lambda':z['wavelength_nm'],'top':z['p_top_raw'],'r12':z['p_r12_outward_raw'],'f0':f0,'f02':f2})
 spec=[];ang0=[];ang2=[];sub=[]
 for r in results:
  c=r['case']; norm=r['top']/np.trapezoid(r['top'],r['lambda']);
  for w,p,n in zip(r['lambda'],r['top'],norm):spec.append({'candidate_id':c['candidate_id'],'geometry_hash':c['geometry_hash'],'source_position_nm':c['source_position_nm'],'source_role':c['source_role'],'orientation':c['orientation'],'wavelength_nm':float(w),'P_top_raw':float(p),'spectral_normalized':float(n),'P_r12_outward_raw':float(r['r12'][np.argmin(abs(r['lambda']-w))])})
  for name,m,target in [('0',r['f0'],ang0),('0.2',r['f02'],ang2)]:
   for a,v,n in zip(m['angles'],m['raw'],m['normalized']):target.append({'candidate_id':c['candidate_id'],'source_position_nm':c['source_position_nm'],'source_role':c['source_role'],'orientation':c['orientation'],'air_angle_deg':float(a),'farfield_filter':name,'raw_intensity':float(v),'normalized_intensity':float(n)})
  sub.append({k:c[k] for k in ('case_id','candidate_id','geometry_hash','source_position_nm','source_role','orientation','theta_deg','phi_deg','pre_fsp_sha256','post_fsp_sha256','solver_entered_at','solver_end_at','solver_exit_state','eta_up_r12_450')}|{'spectral_fwhm_nm':sfwhm(r['lambda'],r['top']),'filter0_fwhm_deg':r['f0']['angular_fwhm_deg'],'filter02_fwhm_deg':r['f02']['angular_fwhm_deg'],'filter0_cone10':r['f0']['cone10_fraction'],'filter02_cone10':r['f02']['cone10_fraction']})
 pd.DataFrame(sub).to_parquet(root/'subrun_metrics.parquet',index=False);pd.DataFrame(spec).to_parquet(root/'spectral_raw.parquet',index=False);pd.DataFrame(spec).to_parquet(root/'spectral_normalized.parquet',index=False);pd.DataFrame(ang0).to_parquet(root/'angular_filter_0.parquet',index=False);pd.DataFrame(ang2).to_parquet(root/'angular_filter_0p2.parquet',index=False)
 raw=pd.DataFrame(spec);xz=[]
 for keys,g in raw.groupby(['candidate_id','source_position_nm','source_role','wavelength_nm']):
  x=float(g[g.orientation=='x'].P_top_raw.iloc[0]);z=float(g[g.orientation=='z'].P_top_raw.iloc[0]);xz.append(dict(zip(['candidate_id','source_position_nm','source_role','wavelength_nm'],keys))|{'I_x_raw':x,'I_z_raw':z,'I_xz_raw':.5*(x+z)})
 xz=pd.DataFrame(xz);xz.to_parquet(root/'xz_average.parquet',index=False);three=[]
 for keys,g in xz.groupby(['candidate_id','wavelength_nm']):three.append(dict(zip(['candidate_id','wavelength_nm'],keys))|{'I_3pos_raw':float(g.I_xz_raw.mean())})
 pd.DataFrame(three).to_parquet(root/'three_position_average.parquet',index=False)
 pd.DataFrame(sub).groupby('candidate_id').eta_up_r12_450.mean().sort_values(ascending=False).reset_index(name='fdtd_relative_upward_trend').assign(rank=lambda f:np.arange(1,len(f)+1)).to_parquet(root/'candidate_ranking_comparison.parquet',index=False)
 filt=pd.DataFrame(sub);filt['fwhm_delta_deg']=filt.filter02_fwhm_deg-filt.filter0_fwhm_deg;filt['cone10_delta']=filt.filter02_cone10-filt.filter0_cone10;filt.to_parquet(root/'filter_sensitivity.parquet',index=False)
 return sub
def main(out):
 cand=candidates();cases=plan();assert len(cases)<=CONFIG['budget_subruns']==18
 contract={'config':CONFIG,'candidates':cand,'builder_commit':'602d89c69258f630e1883f896a4dd4d249852efb','material_config_sha256':sha(ROOT/'configs'/'material_reference_apcd_blue.yaml')};state={'task':CONFIG['task'],'created_at':now(),'physical_contract_hash':hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest(),'cases':cases,'safety_counters':{'FDTD_calls':0,'Lumerical_calls':0,'sealed_test_target_reads':0,'TMM_calls':0,'RCWA_calls':0}}
 dump(out/'provenance.json',contract);dump(out/'state.json',state)
 for stage in ('A','B'):
  todo=[c for c in state['cases'] if c['stage']==stage]
  for c in todo:
   state['safety_counters']['FDTD_calls']+=1;state['safety_counters']['Lumerical_calls']+=1;dump(out/'state.json',state);execute(c,out,state)
  if stage=='A' and not all(c['status']=='COMPLETE' and c['p_top_nonzero'] and c['p_r12_outward_nonzero'] for c in todo):raise RuntimeError('stage_A_smoke_gate_failed')
 sub=postprocess(out,state);pre=[{'case_id':c['case_id'],'path':c['pre_fsp'],'sha256':c['pre_fsp_sha256']} for c in state['cases']];post=[{'case_id':c['case_id'],'path':c['post_fsp'],'sha256':c['post_fsp_sha256']} for c in state['cases']];dump(out/'pre_fsp_index.json',pre);dump(out/'post_fsp_index.json',post);manifest={'run_id':out.name,'subruns':len(state['cases']),'stage_a_pass':True,'all_complete':all(c['status']=='COMPLETE' for c in state['cases']),'safety_counters':state['safety_counters'],'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()}};dump(out/'manifest.json',manifest);print(json.dumps(manifest,sort_keys=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output-root',required=True);a=p.parse_args();o=Path(a.output_root);o.mkdir(parents=True,exist_ok=False);main(o)
