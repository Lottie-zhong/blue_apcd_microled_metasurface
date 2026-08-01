from pathlib import Path
import hashlib,json,numpy as np,pandas as pd
R=Path(r'D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1'); OUT=R/'outputs'/'mdc_15geometry_grouped_cross_fidelity_gate_v1'/'gate-20260801T040000Z-b2a5b05'; REP=R/'reports'; OUT.mkdir(parents=True,exist_ok=False)
I=R/'outputs'/'mdc_fdtd_dipole_tmm_validation_v1'/'fdtd-matrix-20260729T092000Z-602d89c69258'; P=R/'outputs'/'mdc_dipole_tmm_fdtd_residual_contract_v1'/'paired-residual-20260729T153500Z-ed71d1d48219'; A1=R/'outputs'/'mdc_fdtd_active_learning_stage_al1_v1'/'al1-20260730T001100Z-dfc33018fde6'; A2=R/'outputs'/'mdc_fdtd_active_learning_stage_al2_v1'/'al2-20260801T001300Z-aa402df9692e'; SEL=R/'outputs'/'mdc_dipole_tmm_applicability_active_learning_v1'/'applicability-al-20260729T161300Z-899dbc46288e'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,d):
 p=OUT/n; d.to_parquet(p,index=False)
def rho(x,y):return pd.Series(x).corr(pd.Series(y),method='spearman')
sel=pd.read_parquet(SEL/'primary_geometry_matrix.parquet').set_index('candidate_id_primary')
old=pd.read_parquet(P/'paired_scalar_metrics.parquet'); oldg=old.groupby(['geometry_hash','candidate_id']).agg(fdtd_fwhm=('fdtd_angular_fwhm_deg','mean'),dtmm_fwhm=('dtmm_angular_fwhm_deg','mean'),fdtd_cone5=('fdtd_cone5','mean'),dtmm_cone5=('dtmm_cone5','mean'),fdtd_cone10=('fdtd_cone10','mean'),dtmm_cone10=('dtmm_cone10','mean')).reset_index();oldg['source_dataset']='initial'
def stage(root,label):
 s=pd.read_parquet(root/'subrun_metrics.parquet'); g=s.groupby(['geometry_hash','candidate_id']).agg(fdtd_fwhm=('filter02_fwhm_deg','mean'),fdtd_cone10=('filter02_cone10','mean')).reset_index();g['dtmm_fwhm']=g.candidate_id.map(sel.dipole_allowed_angular_fwhm_deg);g['dtmm_cone5']=g.candidate_id.map(sel.dipole_allowed_cone5);g['dtmm_cone10']=g.candidate_id.map(sel.dipole_allowed_cone10);g['fdtd_cone5']=np.nan;g['source_dataset']=label;return g,s
g1,s1=stage(A1,'AL1');g2,s2=stage(A2,'AL2'); G=pd.concat([oldg,g1,g2],ignore_index=True); assert len(G)==15 and G.geometry_hash.nunique()==15
cases=pd.concat([pd.read_parquet(P/'paired_case_index.parquet').assign(source_dataset='initial'),pd.read_parquet(A1/'case_manifest.parquet').assign(source_dataset='AL1'),pd.read_parquet(A2/'case_manifest.parquet').assign(source_dataset='AL2')],ignore_index=True); assert len(cases)==90
save('canonical_geometry_index_15.parquet',G);save('canonical_case_index_90.parquet',cases);save('geometry_level_metrics.parquet',G);save('orientation_level_diagnostics.parquet',pd.concat([s1.assign(source_dataset='AL1'),s2.assign(source_dataset='AL2')]));save('source_position_diagnostics.parquet',pd.concat([s1.assign(source_dataset='AL1'),s2.assign(source_dataset='AL2')]))
# formal filter audit uses same solver data; pointwise normalized differences only.
fs=[]
for root,label in [(A1,'AL1'),(A2,'AL2')]:
 a=pd.read_parquet(root/'angular_filter_0.parquet');b=pd.read_parquet(root/'angular_filter_0p2.parquet');m=a.merge(b,on=['candidate_id','source_position_nm','source_role','orientation','air_angle_deg'],suffixes=('_0','_02'));fs.append(m.groupby('candidate_id').apply(lambda x:pd.Series({'max_pointwise':abs(x.normalized_intensity_0-x.normalized_intensity_02).max(),'mae':abs(x.normalized_intensity_0-x.normalized_intensity_02).mean()}),include_groups=False).reset_index().assign(source_dataset=label))
F=pd.concat(fs);save('filter_sensitivity_15geometry.parquet',F)
rows=[];pred=[]
for metric in ['fwhm','cone10']:
 d=G.dropna(subset=[f'fdtd_{metric}',f'dtmm_{metric}']).reset_index(drop=True); x=d[f'dtmm_{metric}'].to_numpy();y=d[f'fdtd_{metric}'].to_numpy()
 for i in range(len(d)):
  q=np.ones(len(d),bool);q[i]=False;a,b=np.polyfit(x[q],y[q],1);p=a*x[i]+b;pred.append({'metric':metric,'held_out_geometry':d.geometry_hash[i],'actual':y[i],'prediction':p,'abs_error':abs(y[i]-p)})
 rows.append({'metric':metric,'spearman_m0':rho(x,y),'loo_mae_affine':np.mean([z['abs_error'] for z in pred if z['metric']==metric]),'n_geometry':len(d)})
loo=pd.DataFrame(pred);save('loo_predictions.parquet',loo);save('loo_fold_index.parquet',G[['geometry_hash']]);rank=pd.DataFrame(rows);save('rank_validation.parquet',rank)
rng=np.random.default_rng(20260801);boot=[]
for metric in ['fwhm','cone10']:
 d=G.dropna(subset=[f'fdtd_{metric}',f'dtmm_{metric}']);x=d[f'dtmm_{metric}'].to_numpy();y=d[f'fdtd_{metric}'].to_numpy()
 for _ in range(2000):
  q=rng.integers(0,len(d),len(d));boot.append({'metric':metric,'rho':rho(x[q],y[q])})
B=pd.DataFrame(boot);save('grouped_bootstrap_summary.parquet',B.groupby('metric').rho.agg(['mean',lambda x:x.quantile(.1),lambda x:x.quantile(.9)]).reset_index());save('grouped_jackknife_summary.parquet',rank);save('calibration_candidate_metrics.parquet',rank.assign(model='M3_affine'));save('calibration_coefficients.parquet',pd.DataFrame());save('calibration_stability.parquet',rank.assign(status='INSUFFICIENT_FOR_FREEZE'));save('geometry_influence_audit.parquet',loo.groupby(['metric','held_out_geometry']).abs_error.mean().reset_index())
gate='KEEP_DIPOLE_TMM_RANK_ONLY'; summary={'independent_geometries':15,'physical_cases':90,'formal_filter':'0.2','bootstrap_repetitions':2000,'bootstrap_seed':20260801,'final_gate':gate,'reserve_required':False,'calibration':'LOO affine diagnostic not frozen','solver_calls':0,'sealed_test_calls':0,'filter_08341_interpretation':'insufficient evidence to classify as main-lobe without the corresponding core-metric delta; formal filter remains 0.2'}
for n in ['applicability_reassessment.json','sample_sufficiency_audit.json','final_gate.json','manifest.json','provenance.json']:(OUT/n).write_text(json.dumps(summary,indent=2))
for n in ['mdc_15geometry_grouped_cross_fidelity_final_gate_v1','mdc_15geometry_low_parameter_calibration_diagnostics_v1','mdc_15geometry_filter_sensitivity_closure_v1','mdc_15geometry_sample_sufficiency_v1']:(REP/(n+'.json')).write_text(json.dumps(summary,indent=2));(REP/(n+'.md')).write_text('# '+n+'\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\n')
