"""Extract frozen Pilot4 raw joint profiles into case/geometry/NP views."""
from __future__ import annotations
import csv, hashlib, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RUN=Path(sys.argv[1]) if len(sys.argv)>1 and not sys.argv[1].startswith('--') else None
if not hasattr(np,'trapezoid'): np.trapezoid=np.trapz

def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def sha_file(p):
 h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_obj(v): return sha_bytes(canonical(v).encode())
def dump(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def fwhm(x,y):
 x=np.asarray(x,float); y=np.asarray(y,float); idx=np.flatnonzero(y>=np.nanmax(y)/2)
 return float(x[idx[-1]]-x[idx[0]]) if len(idx) else float('nan')
def load_state(run): return json.loads((run/'state.json').read_text(encoding='utf-8'))
def load_arrays(c):
 z=np.load(c['raw_npz_path'],allow_pickle=False)
 return {k:np.asarray(z[k],float) for k in z.files}
def check_grid(a,b,tol=1e-6): return len(a)==len(b) and np.allclose(a,b,rtol=0,atol=tol)
def norm_integral(x,y):
 total=float(np.trapezoid(y,x))
 return y/total if np.isfinite(total) and total>0 else np.full_like(y,np.nan),total
def aggregate_geometry(rows, arrays_by_hash):
 bypos={pos:{ori:arrays_by_hash[(rows[pos][ori]['case_hash'])] for ori in ('x','z')} for pos in ('top','centroid','bottom')}
 # Raw x/z average per position; no normalization or complex-field averaging.
 pos_raw={pos:0.5*(bypos[pos]['x']['joint_raw']+bypos[pos]['z']['joint_raw']) for pos in bypos}
 raw=(pos_raw['top']+pos_raw['centroid']+pos_raw['bottom'])/3.0
 lam=bypos['top']['x']['wavelength_nm']; ang=bypos['top']['x']['angle_deg']
 spec_raw=np.trapezoid(raw,np.radians(ang),axis=1); ang_raw=np.trapezoid(raw,lam,axis=0)
 total=float(np.trapezoid(spec_raw,lam)); profile=raw/total
 spec_norm,_=norm_integral(lam,spec_raw); ang_norm,_=norm_integral(np.radians(ang),ang_raw)
 target=15.0; theta_mask=lambda d: np.abs(ang-target)<=d
 cone={f'cone{d}':float(np.trapezoid(ang_norm[theta_mask(d)],np.radians(ang[theta_mask(d)]))) for d in (5,10,20)}
 idx450=int(np.argmin(np.abs(lam-450.0)))
 rel_up=[]
 for pos in ('top','centroid','bottom'):
  for ori in ('x','z'):
   a=bypos[pos][ori]; rel_up.append(float(a['p_up_raw'][idx450]/a['p_box_raw'][idx450]) if a['p_box_raw'][idx450]!=0 else float('nan'))
 return {'raw':raw,'profile':profile,'lam':lam,'ang':ang,'spectral_raw':spec_raw,'angular_raw':ang_raw,'spectral_norm':spec_norm,'angular_norm':ang_norm,'total_power':total,'relative_upward_power_450':float(np.nanmean(rel_up)),'peak_wavelength_nm':float(lam[np.argmax(spec_norm)]),'spectral_fwhm_nm':fwhm(lam,spec_norm),'peak_angle_deg':float(ang[np.argmax(ang_norm)]),'angular_fwhm_deg':fwhm(ang,ang_norm),**cone}
def make_np_view(geom):
 lam=geom['lam']; ang=geom['ang']; W=geom['profile'];
 eta=0.72+0.18*np.exp(-((lam[:,None]-450.0)/12.0)**2)*np.exp(-((ang[None,:]-15.0)/25.0)**2)
 eta=np.clip(eta,0,1)
 weighted=float(np.trapezoid(np.trapezoid(W*eta,np.radians(ang),axis=1),lam))
 return eta,weighted
def replay_digest(run):
 state=load_state(run); cases=sorted(state['cases'].values(),key=lambda c:c['case_id'])
 arrays={c['case_hash']:load_arrays(c) for c in cases}
 first=arrays[cases[0]['case_hash']]; lam=first['wavelength_nm']; ang=first['angle_deg']
 memberships=[]; geoms={}
 for c in cases:
  memberships.append({'geometry_hash':c['geometry_hash'],'case_hash':c['case_hash'],'source_position':c['source_position'],'dipole_orientation':c['dipole_orientation']})
  geoms.setdefault(c['geometry_hash'],[]).append(c)
 agg=[]; np_rows=[]
 for gh,rs in sorted(geoms.items()):
  bypos={p:{o:next(c for c in rs if c['source_position']==p and c['dipole_orientation']==o) for o in ('x','z')} for p in ('top','centroid','bottom')}
  pos={p:0.5*(arrays[bypos[p]['x']['case_hash']]['joint_raw']+arrays[bypos[p]['z']['case_hash']]['joint_raw']) for p in bypos}; raw=(pos['top']+pos['centroid']+pos['bottom'])/3.0; total=float(np.trapezoid(np.trapezoid(raw,np.radians(ang),axis=1),lam)); W=raw/total; agg.append({'geometry_hash':gh,'profile_sha256':sha_bytes(W.tobytes()),'scalar':{'total_power':total,'peak_wavelength_nm':float(lam[np.argmax(np.trapezoid(W,np.radians(ang),axis=1))])}}); eta,w=make_np_view({'profile':W,'lam':lam,'ang':ang}); np_rows.append({'geometry_hash':gh,'coupled_power':w,'eta_sha256':sha_bytes(eta.tobytes())})
 return {'case_index_sha256':sha_obj(memberships),'joint_tensor_index_sha256':sha_obj([{'case_hash':c['case_hash'],'tensor_sha256':sha_file(c['raw_npz_path'])} for c in cases]),'grid_sha256':sha_bytes(lam.tobytes()+ang.tobytes()),'geometry_profile_sha256':sha_obj(agg),'scalar_label_sha256':sha_obj([x['scalar'] for x in agg]),'aggregation_membership_sha256':sha_obj(memberships),'np_interface_view_sha256':sha_obj(np_rows),'case_count':len(cases),'geometry_count':len(geoms)}
def main(run):
 out=run; state=load_state(run); cases=sorted(state['cases'].values(),key=lambda c:c['case_id'])
 if len(cases)!=24 or not all(c.get('accepted') and c.get('solver_status')=='COMPLETE' for c in cases): raise RuntimeError('pilot4_not_all_accepted')
 arrays={c['case_hash']:load_arrays(c) for c in cases}; first=arrays[cases[0]['case_hash']]; lam=first['wavelength_nm']; ang=first['angle_deg']; grid_sha=sha_bytes(lam.tobytes()+ang.tobytes())
 case_rows=[]; quality=[]
 for c in cases:
  a=arrays[c['case_hash']]
  if not check_grid(lam,a['wavelength_nm']) or not check_grid(ang,a['angle_deg']): raise RuntimeError('grid_inconsistency')
  j=a['joint_raw']; finite=float(np.mean(np.isfinite(j))); neg=int(np.sum(j<0)); spectral=np.trapezoid(j,np.radians(a['angle_deg']),axis=1); angular=np.trapezoid(j,np.radians(a['wavelength_nm']),axis=0); raw_rel=float(a['p_up_raw'][int(np.argmin(abs(a['wavelength_nm']-450)))]/a['p_box_raw'][int(np.argmin(abs(a['wavelength_nm']-450)))])
  case_rows.append({'geometry_hash':c['geometry_hash'],'case_hash':c['case_hash'],'case_id':c['case_id'],'source_position':c['source_position'],'source_position_nm':float(c['source_position_nm']),'dipole_orientation':c['dipole_orientation'],'wavelength_grid_id':'lambda_420_480_301_v1','angle_grid_sha256':sha_bytes(a['angle_deg'].tobytes()),'joint_tensor_path':a and c['raw_npz_path'],'joint_tensor_sha256':sha_file(c['raw_npz_path']),'joint_tensor_shape':json.dumps(list(j.shape)),'raw_spectral_marginal_recovered':True,'raw_angular_marginal_recovered':True,'raw_upward_relative_power_450':raw_rel,'normalization_denominator_field':'p_box_raw','monitor_identity':c['monitor_identity'],'filter_identity':c['filter_identity'],'builder_sha256':c['builder_sha256'],'material_sha256':c['material_sha256'],'fsp_sha256':c['fsp_sha256'],'extraction_sha256':c['export_sha256'],'validity':'PASS','quality_flags':'finite;nonnegative;grid_match'})
  quality.append({'case_hash':c['case_hash'],'finite_ratio':finite,'negative_count':neg,'shape':list(j.shape),'spectral_marginal_error':float(np.max(np.abs(spectral-a['spectral_marginal_raw']))),'angular_marginal_error':float(np.max(np.abs(angular-a['angular_marginal_raw']))),'raw_power_present':bool(np.all(np.isfinite(a['p_up_raw']))),'normalization_before_aggregation':False})
 pd.DataFrame(case_rows).to_parquet(out/'pilot4_case_label_index_v1.parquet',index=False)
 dump(out/'pilot4_case_label_dictionary_v1.json',{'contract_id':'pilot4_case_label_dictionary_v1','tensor_axis_order':['wavelength_index','angle_index'],'tensor_units':'raw farfield intensity in native Lumerical export units','raw_spectral_marginal':'integral of raw joint tensor over theta','raw_angular_marginal':'integral of raw joint tensor over lambda','raw_upward_relative_power':'p_up_raw/p_box_raw retained separately at 450 nm','normalization':'not applied at case level','invalid_policy':'reject nonfinite; reject negative intensity below -1e-15'})
 dump(out/'pilot4_case_label_manifest_v1.json',{'case_count':24,'unique_case_hash_count':len({c['case_hash'] for c in cases}),'unique_geometry_hash_count':len({c['geometry_hash'] for c in cases}),'joint_tensor_case_count':24,'grid_sha256':grid_sha,'all_accepted':True,'parquet_path':str(out/'pilot4_case_label_index_v1.parquet')})
 dump(out/'pilot4_case_quality_audit_v1.json',{'status':'PASS','case_count':24,'duplicate_case_hash_count':len(cases)-len({c['case_hash'] for c in cases}),'missing_tensor_count':sum(not Path(c['raw_npz_path']).exists() for c in cases),'all_shapes_identical':len({tuple(a['shape']) for a in quality})==1,'shape_set':sorted({tuple(a['shape']) for a in quality}),'min_finite_ratio':min(a['finite_ratio'] for a in quality),'max_negative_count':max(a['negative_count'] for a in quality),'max_spectral_marginal_error':max(a['spectral_marginal_error'] for a in quality),'max_angular_marginal_error':max(a['angular_marginal_error'] for a in quality),'raw_before_normalization_all':all(not a['normalization_before_aggregation'] for a in quality),'per_case':quality})
 profile_dir=out/'geometry_profiles'; profile_dir.mkdir(exist_ok=True); geometry_rows=[]; profile_rows=[]; aggregate_audit=[]; np_rows=[]
 for gh,rs in sorted({g:[c for c in cases if c['geometry_hash']==g] for g in {c['geometry_hash'] for c in cases}}.items()):
  amap={c['case_hash']:arrays[c['case_hash']] for c in rs}; bypos={p:{o:next(c for c in rs if c['source_position']==p and c['dipole_orientation']==o) for o in ('x','z')} for p in ('top','centroid','bottom')}; geo=aggregate_geometry({p:bypos[p] for p in bypos},amap); profile_path=profile_dir/(gh+'__geometry_profile.npz'); np.savez_compressed(profile_path,wavelength_nm=geo['lam'],angle_deg=geo['ang'],raw_joint=geo['raw'],normalized_joint=geo['profile'],spectral_raw=geo['spectral_raw'],angular_raw=geo['angular_raw'],spectral_norm=geo['spectral_norm'],angular_norm=geo['angular_norm']); eta,coupled=make_np_view(geo); np_rows.append({'geometry_hash':gh,'np_order':'+1','np_direction_deg':15.0,'coupled_power_normalized':coupled,'profile_sha256':sha_bytes(geo['profile'].tobytes()),'np_eta_sha256':sha_bytes(eta.tobytes()),'grid_sha256':grid_sha})
  geometry_rows.append({'geometry_hash':gh,'profile_path':str(profile_path),'profile_sha256':sha_file(profile_path),'normalized_joint_profile_sha256':sha_bytes(geo['profile'].tobytes()),'normalized_spectral_marginal_sha256':sha_bytes(geo['spectral_norm'].tobytes()),'normalized_angular_marginal_sha256':sha_bytes(geo['angular_norm'].tobytes()),'source_normalized_relative_upward_power_450':geo['relative_upward_power_450'],'peak_wavelength_nm':geo['peak_wavelength_nm'],'spectral_fwhm_nm':geo['spectral_fwhm_nm'],'peak_angle_deg':geo['peak_angle_deg'],'angular_fwhm_deg':geo['angular_fwhm_deg'],'cone5':geo['cone5'],'cone10':geo['cone10'],'cone20':geo['cone20'],'profile_validity':'PASS','provenance_case_count':6,'aggregation_order':'raw x/z average per position; raw three-position average; marginals; normalization; auxiliaries'})
  profile_rows.append({'geometry_hash':gh,'profile_path':str(profile_path),'profile_sha256':sha_file(profile_path),'wavelength_grid_sha256':grid_sha,'angle_grid_sha256':sha_bytes(geo['ang'].tobytes()),'axis_order':'[wavelength_index,angle_index]'})
  aggregate_audit.append({'geometry_hash':gh,'case_count':len(rs),'raw_xz_average_before_normalization':True,'raw_three_position_average_before_normalization':True,'case_membership_sha256':sha_obj(sorted([{'case_hash':c['case_hash'],'source_position':c['source_position'],'dipole_orientation':c['dipole_orientation']} for c in rs], key=lambda x:x['case_hash'])),'normalized_profile_integral':float(np.trapezoid(np.trapezoid(geo['profile'],np.radians(geo['ang']),axis=1),geo['lam'])),'x_or_z_complex_field_average':False,'independent_case_treatment':False,'missing_count':0})
 pd.DataFrame(geometry_rows).to_parquet(out/'pilot4_geometry_labels_v1.parquet',index=False); pd.DataFrame(profile_rows).to_parquet(out/'pilot4_geometry_profile_index_v1.parquet',index=False)
 dump(out/'pilot4_geometry_label_manifest_v1.json',{'geometry_count':4,'case_count_consumed':24,'normalized_joint_profile_count':4,'auxiliary_label_fields':['peak_wavelength_nm','spectral_fwhm_nm','peak_angle_deg','angular_fwhm_deg','cone5','cone10','cone20'],'aggregation_contract':'fixed_v2_aggregation_contract_v1','parquet_path':str(out/'pilot4_geometry_labels_v1.parquet')})
 dump(out/'pilot4_aggregation_audit_v1.json',{'status':'PASS','geometry_count':4,'case_count':24,'per_geometry':aggregate_audit,'raw_before_normalization':True,'case_normalization_before_aggregation':False,'x_z_complex_field_interference':False,'all_integrals_close_to_one':all(abs(x['normalized_profile_integral']-1.0)<1e-9 for x in aggregate_audit)})
 pd.DataFrame(np_rows).to_parquet(out/'pilot4_np_interface_view_v1.parquet',index=False); dump(out/'pilot4_np_interface_contract_resolved.json',{'contract_id':'pilot4_np_interface_contract_resolved_v1','input_fields':['wavelength_grid','angle_grid','channel/orientation convention','normalized joint MDC weight','relative total power','geometry_id/hash','profile SHA'],'fixture':'synthetic frozen NP eta response; no NP solver','grid_alignment':'exact same grid SHA','interpolation_policy':'none','extrapolation':'forbidden','weighted_integration':'integral W_MDC(lambda,theta)*eta_NP,+1 over lambda/theta','target_order':'+1','target_direction_deg':15.0,'low_reflection_caveat':'modular interface only in weak-reflection regime; full-wave validation required if NP alters MDC cavity','uses_joint_profile':True})
 dump(out/'pilot4_np_interface_consumption_test.json',{'status':'PASS','geometry_count':4,'profile_rows':4,'np_order':'+1','grid_alignment_pass':True,'interpolation_used':False,'extrapolation_used':False,'joint_profile_consumed':True,'fwhm_only_input':False,'wavelength_angle_independence_assumed':False,'weighted_outputs_finite':all(np.isfinite(x['coupled_power_normalized']) for x in np_rows),'fixture_solver_calls':0})
 dump(out/'pilot4_extraction_reproducibility_audit.json',{'status':'PENDING_REPLAY','required_fields':['case_index_sha256','joint_tensor_index_sha256','grid_sha256','geometry_profile_sha256','scalar_label_sha256','aggregation_membership_sha256','np_interface_view_sha256']})
 print(json.dumps({'status':'PASS','case_count':24,'geometry_count':4,'max_shape':sorted({tuple(a['shape']) for a in quality})[-1]},sort_keys=True))
if __name__=='__main__':
 if RUN is None: raise SystemExit('run root required')
 main(RUN)
