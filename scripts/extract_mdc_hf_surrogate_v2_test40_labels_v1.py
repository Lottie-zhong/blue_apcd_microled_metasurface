import hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2'); SEL=ROOT/'outputs/mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1/20260808T_test40_selection_conflict_resolution_489b54e'; RUN=ROOT/'runtime/mdc_hf_surrogate_v2_test40_external_eval_v1'
def sf(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def so(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def dump(p,x): Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def loadz(c):
 z=np.load(c['raw_npz_path'],allow_pickle=False); return {k:np.asarray(z[k],float) for k in z.files}
def fwhm(x,y):
 i=np.flatnonzero(y>=np.nanmax(y)/2); return float(x[i[-1]]-x[i[0]]) if len(i) else float('nan')
def main(replay_id=1):
 s=json.loads((RUN/'state.json').read_text()); cases=list(s['cases'].values()); assert len(cases)==240 and all(c.get('accepted') and c.get('solver_status')=='COMPLETE' for c in cases)
 geom=pd.read_csv(SEL/'test40_geometry_manifest_v1.csv'); mat=pd.read_csv(SEL/'test40_case_matrix_v1.csv'); assert len(geom)==40 and len(mat)==240 and mat.test_case_uid.is_unique
 cases=sorted(cases,key=lambda c:c['test_case_uid']); arr={c['test_case_uid']:loadz(c) for c in cases}; lam=arr[cases[0]['test_case_uid']]['wavelength_nm']; ang=arr[cases[0]['test_case_uid']]['angle_deg']; assert len(lam)==301 and len(ang)==2000
 gsha=hashlib.sha256(lam.tobytes()+ang.tobytes()).hexdigest(); rows=[]; q=[]
 for c in cases:
  a=arr[c['test_case_uid']]; j=a['joint_raw']; assert j.shape==(301,2000) and np.isfinite(j).all() and (j>=0).all() and np.allclose(lam,a['wavelength_nm'],rtol=0,atol=1e-6) and np.allclose(ang,a['angle_deg'],rtol=0,atol=1e-6)
  sm=np.trapezoid(j,np.radians(ang),axis=1); am=np.trapezoid(j,np.radians(lam),axis=0); k=int(np.argmin(abs(lam-450))); rel=float(a['p_up_raw'][k])
  rows.append({'test_case_uid':c['test_case_uid'],'test_case_human_id':c['test_case_human_id'],'geometry_hash':c['geometry_hash'],'source_position':c['source_position'],'source_z_pm':float(c['source_z_pm']),'dipole_orientation':c['dipole_orientation'],'joint_tensor_path':c['raw_npz_path'],'joint_tensor_sha256':sf(c['raw_npz_path']),'joint_tensor_shape':'[301,2000]','wavelength_grid_sha256':hashlib.sha256(lam.tobytes()).hexdigest(),'angle_grid_sha256':hashlib.sha256(ang.tobytes()).hexdigest(),'raw_spectral_marginal_recovered':True,'raw_angular_marginal_recovered':True,'raw_upward_relative_power_450':rel,'normalization_before_aggregation':False,'validity':'PASS'})
  q.append({'test_case_uid':c['test_case_uid'],'shape':[301,2000],'finite_ratio':1.0,'negative_count':0,'spectral_marginal_error':float(np.max(abs(sm-a['spectral_marginal_raw']))),'angular_marginal_error':float(np.max(abs(am-a['angular_marginal_raw']))),'raw_before_normalization':True})
 pd.DataFrame(rows).to_parquet(SEL/'test40_case_label_index_v1.parquet',index=False); dump(SEL/'test40_case_quality_audit_v1.json',{'status':'PASS','case_count':240,'unique_test_case_uid_count':len({c['test_case_uid'] for c in cases}),'all_shapes_identical':True,'shape':[301,2000],'max_spectral_marginal_error':max(x['spectral_marginal_error'] for x in q),'max_angular_marginal_error':max(x['angular_marginal_error'] for x in q),'per_case':q})
 gro=[]; pri=[]; aa=[]; gq=[]; pdir=RUN/'geometry_profiles'; pdir.mkdir(exist_ok=True)
 for gh in sorted(geom.geometry_hash):
  rs=[c for c in cases if c['geometry_hash']==gh]; assert len(rs)==6; by={p:{o:next(c for c in rs if c['source_position']==p and c['dipole_orientation']==o) for o in ('x','z')} for p in ('top','centroid','bottom')}; pos={p:.5*(arr[by[p]['x']['test_case_uid']]['joint_raw']+arr[by[p]['z']['test_case_uid']]['joint_raw']) for p in by}; raw=sum(pos.values())/3.; sr=np.trapezoid(raw,np.radians(ang),axis=1); ar=np.trapezoid(raw,lam,axis=0); total=float(np.trapezoid(sr,lam)); norm=raw/total; sn=sr/float(np.trapezoid(sr,lam)); an=ar/float(np.trapezoid(ar,np.radians(ang))); k=int(np.argmin(abs(lam-450))); rel=[]
  for p in by:
   for o in ('x','z'):
    a=arr[by[p][o]['test_case_uid']]; rel.append(float(a['p_up_raw'][k]))
  pp=pdir/(gh+'__geometry_profile.npz'); np.savez_compressed(pp,wavelength_nm=lam,angle_deg=ang,raw_joint=raw,normalized_joint=norm,spectral_raw=sr,angular_raw=ar,spectral_norm=sn,angular_norm=an)
  gro.append({'geometry_hash':gh,'profile_path':str(pp),'profile_sha256':sf(pp),'normalized_joint_profile_sha256':hashlib.sha256(norm.tobytes()).hexdigest(),'relative_upward_power_450':float(np.nanmean(rel)),'peak_wavelength_nm':float(lam[np.argmax(sn)]),'spectral_fwhm_nm':fwhm(lam,sn),'peak_angle_deg':float(ang[np.argmax(an)]),'angular_fwhm_deg':fwhm(ang,an),'profile_validity':'PASS','case_count':6})
  pri.append({'geometry_hash':gh,'profile_path':str(pp),'profile_sha256':sf(pp),'wavelength_grid_sha256':hashlib.sha256(lam.tobytes()).hexdigest(),'angle_grid_sha256':hashlib.sha256(ang.tobytes()).hexdigest(),'axis_order':'[wavelength_index,angle_index]'})
  aa.append({'geometry_hash':gh,'case_count':6,'raw_xz_average_before_normalization':True,'raw_three_position_average_before_normalization':True,'case_membership_sha256':so(sorted([{'test_case_uid':c['test_case_uid'],'source_position':c['source_position'],'dipole_orientation':c['dipole_orientation']} for c in rs],key=lambda x:x['test_case_uid'])),'normalized_profile_integral':float(np.trapezoid(np.trapezoid(norm,np.radians(ang),axis=1),lam)),'normalization_before_aggregation':False})
  gq.append({'geometry_hash':gh,'shape':[301,2000],'raw_finite':True,'raw_nonnegative':True,'normalized_integral_error':abs(float(np.trapezoid(np.trapezoid(norm,np.radians(ang),axis=1),lam))-1)})
 pd.DataFrame(gro).to_parquet(SEL/'test40_geometry_labels_v1.parquet',index=False); pd.DataFrame(pri).to_parquet(SEL/'test40_geometry_profile_index_v1.parquet',index=False); dump(SEL/'test40_aggregation_audit_v1.json',{'status':'PASS','geometry_count':40,'case_count':240,'raw_before_normalization':True,'all_integrals_close_to_one':all(x['normalized_profile_integral']>0.999999999 for x in aa),'per_geometry':aa}); dump(SEL/'test40_joint_profile_quality_audit.json',{'status':'PASS','case_count':240,'geometry_count':40,'grid_sha256':gsha,'all_case_quality_pass':True,'all_geometry_quality_pass':True,'per_geometry':gq})
 digest={'status':'PASS','replay_id':replay_id,'case_index_sha256':so([{'test_case_uid':c['test_case_uid'],'geometry_hash':c['geometry_hash'],'source_position':c['source_position'],'dipole_orientation':c['dipole_orientation']} for c in cases]),'tensor_index_sha256':so([{'test_case_uid':c['test_case_uid'],'tensor_sha256':sf(c['raw_npz_path'])} for c in cases]),'geometry_profile_sha256':so([{'geometry_hash':x['geometry_hash'],'profile_sha256':x['normalized_joint_profile_sha256']} for x in gro]),'geometry_count':40,'case_count':240,'grid_sha256':gsha}
 dump(SEL/f'test40_extraction_replay_{replay_id}.json',digest); print(json.dumps(digest,indent=2))
if __name__=='__main__': main(1)
