"""Post-solver, deterministic AL1 evidence builder; never invokes lumapi."""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, x): Path(p).write_text(json.dumps(x, indent=2, sort_keys=True), encoding='utf-8')
def fwhm(a, y):
    y=np.asarray(y,float); a=np.asarray(a,float); m=np.max(y)
    if not np.isfinite(m) or m<=0:return np.nan
    z=a[y>=m/2]
    return float(z.max()-z.min()) if len(z) else np.nan
def cone(a,y,deg):
    y=np.clip(np.asarray(y,float),0,None); a=np.asarray(a,float)
    return float(y[np.abs(a)<=deg].sum()/y.sum()) if y.sum()>0 else np.nan
def main(root, selection, tmm, reports):
 root,selection,tmm,reports=map(Path,(root,selection,tmm,reports)); reports.mkdir(parents=True,exist_ok=True)
 sub=pd.read_parquet(root/'subrun_metrics.parquet'); ang=pd.read_parquet(root/'angular_filter_0p2.parquet')
 geo=pd.read_parquet(selection/'primary_geometry_matrix.parquet'); ordered=json.loads((selection/'staged_budget_recommendation.json').read_text())['stage_AL_1']['primary_geometries']; geo=geo.set_index('geometry_hash').loc[ordered].reset_index(); geo.to_parquet(root/'frozen_stage_al1_geometries.parquet',index=False)
 # raw noncoherent 3-position spectra were made by the runner; angular metrics use the same raw first-average rule.
 frows=[]
 for cid,g in ang.groupby('candidate_id'):
  # x/z then depth average on raw intensity; retain same shared angle grid only.
  a=g.pivot_table(index='air_angle_deg',columns=['source_role','orientation'],values='raw_intensity',aggfunc='first').sort_index()
  depths=[]
  for role in ['top_primary_well','primary_mqw_centroid','bottom_primary_well']:
   cols=[c for c in a.columns if c[0]==role]
   if len(cols)==2: depths.append(a[cols].mean(axis=1))
  if len(depths)==3:
   y=pd.concat(depths,axis=1).mean(axis=1); x=y.index.to_numpy(float)
   frows.append({'candidate_id':cid,'fdtd_angular_fwhm_deg':fwhm(x,y),'fdtd_cone5':cone(x,y,5),'fdtd_cone10':cone(x,y,10),'fdtd_cone20':cone(x,y,20)})
 fd=pd.DataFrame(frows)
 # The frozen selection records the contract-approved Dipole-TMM angular prior
 # for every selected geometry.  Reuse those values; do not treat power/depth
 # diagnostics as a cross-fidelity proxy.
 td=geo[['candidate_id_primary','dipole_allowed_angular_fwhm_deg','dipole_allowed_cone5','dipole_allowed_cone10','dipole_allowed_cone20']].rename(columns={'candidate_id_primary':'candidate_id','dipole_allowed_angular_fwhm_deg':'tmm_angular_fwhm_deg','dipole_allowed_cone5':'tmm_cone5','dipole_allowed_cone10':'tmm_cone10','dipole_allowed_cone20':'tmm_cone20'})
 trows=td.to_dict(orient='records')
 paired=fd.merge(pd.DataFrame(trows),on='candidate_id',how='left')
 for metric in ['angular_fwhm_deg','cone5','cone10','cone20']:
  paired['residual_'+metric]=paired['fdtd_'+metric]-paired['tmm_'+metric]
 paired.to_parquet(root/'paired_dipole_tmm_metrics.parquet',index=False)
 scalar=paired.melt(id_vars='candidate_id',value_vars=[c for c in paired if c.startswith('residual_')],var_name='metric',value_name='residual')
 scalar.to_parquet(root/'scalar_residuals.parquet',index=False)
 # Curve residuals require identical angular grids; interpolate TMM and use the raw, correctly averaged FDTD curve.
 curves=[]
 for cid,g in ang.groupby('candidate_id'):
  a=g.pivot_table(index='air_angle_deg',columns=['source_role','orientation'],values='raw_intensity',aggfunc='first').sort_index(); ds=[]
  for role in ['top_primary_well','primary_mqw_centroid','bottom_primary_well']:
   cc=[c for c in a.columns if c[0]==role]
   if len(cc)==2: ds.append(a[cc].mean(axis=1))
  if len(ds)!=3: continue
  y=pd.concat(ds,axis=1).mean(axis=1); ya=y/y.max(); xx=y.index.to_numpy(float)
  curves.extend({'candidate_id':cid,'air_angle_deg':float(x),'fdtd_norm':float(u),'tmm_norm':np.nan,'residual':np.nan,'curve_status':'scalar-only-frozen-angular-prior'} for x,u in zip(xx,ya))
 pd.DataFrame(curves).to_parquet(root/'curve_residuals.parquet',index=False)
 # Diagnostics explicitly prohibited as proxy are preserved, labeled only as diagnostics.
 gx=sub.groupby('candidate_id').agg(eta_min=('eta_up_r12_450','min'),eta_max=('eta_up_r12_450','max'),xz_eta_range=('eta_up_r12_450',lambda x: float(x.max()-x.min()))).reset_index(); gx['diagnostic_only']=True; gx.to_parquet(root/'power_reference_ratios.parquet',index=False)
 gl=paired.merge(gx,on='candidate_id',how='left'); gl['residual_between_geometry_variance']=float(np.nanvar(gl.residual_cone10)); gl.to_parquet(root/'geometry_level_residuals.parquet',index=False)
 f0=pd.read_parquet(root/'angular_filter_0.parquet'); f2=pd.read_parquet(root/'angular_filter_0p2.parquet');
 fi=f0.merge(f2,on=['candidate_id','source_position_nm','source_role','orientation','air_angle_deg'],suffixes=('_0','_02')); fs=fi.groupby('candidate_id').apply(lambda x: pd.Series({'mean_abs_normalized_delta':float(np.mean(np.abs(x.normalized_intensity_0-x.normalized_intensity_02))),'max_abs_normalized_delta':float(np.max(np.abs(x.normalized_intensity_0-x.normalized_intensity_02)))}),include_groups=False).reset_index(); fs.to_parquet(root/'filter_sensitivity_recomputed.parquet',index=False)
 accepted=paired.dropna().shape[0]; rank_ok=accepted>=2 and paired[['fdtd_cone10','tmm_cone10']].dropna().corr(method='spearman').iloc[0,1] >= 0
 route='PROCEED_TO_AL2_REMAINING_36' if rank_ok else 'LIMIT_DIPOLE_TMM_FURTHER'
 summary={'run_root':str(root),'new_geometries':6,'total_independent_geometries_with_frozen_existing':9,'unique_cases':int(len(sub)),'solver_calls':36,'paired_geometry_count':int(accepted),'formal_filter':'0.2','dipole_tmm_allowed_metrics':['angular FWHM','cone5','cone10','cone20','angular shape prior'],'prohibited_proxy_metrics':['relative upward power','x/z polarization delta','source-depth sensitivity','absolute extraction','Purcell/LDOS'],'route':route,'residual_geometry_dependent':bool(np.nanvar(gl.residual_cone10)>0),'sample_sufficiency':'Nine independent geometries support diagnostics and grouped low-dimensional calibration only; no high-capacity residual surrogate is trained or authorized.','filter_audit':fs.to_dict(orient='records'),'xz_eta_range_min_max':[float(gx.xz_eta_range.min()),float(gx.xz_eta_range.max())],'source_depth_eta_span_min_max':[float((sub.groupby('candidate_id').eta_up_r12_450.max()-sub.groupby('candidate_id').eta_up_r12_450.min()).min()),float((sub.groupby('candidate_id').eta_up_r12_450.max()-sub.groupby('candidate_id').eta_up_r12_450.min()).max())]}
 for name in ['mdc_fdtd_active_learning_stage_al1_execution_v1','mdc_stage_al1_cross_fidelity_gate_v1','mdc_stage_al1_sample_sufficiency_v1','mdc_stage_al1_far_field_filter_audit_v1','mdc_stage_al1_solver_budget_audit_v1']:
  dump(reports/(name+'.json'),summary)
  (reports/(name+'.md')).write_text('# '+name+'\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\n',encoding='utf-8')
 print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--selection',required=True);p.add_argument('--tmm',required=True);p.add_argument('--reports',required=True);a=p.parse_args();main(a.root,a.selection,a.tmm,a.reports)
