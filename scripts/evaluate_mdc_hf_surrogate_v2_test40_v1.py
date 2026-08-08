from pathlib import Path
import json, hashlib, math
import numpy as np, pandas as pd
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2')
SEL=ROOT/'outputs/mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1/20260808T_test40_selection_conflict_resolution_489b54e'
RUN=ROOT/'runtime/mdc_hf_surrogate_v2_test40_external_eval_v1'
def dump(p,x): Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def norm(x):
 x=np.maximum(np.asarray(x,float),0); s=float(x.sum()); return x/s if s>0 else np.zeros_like(x)
def js(a,b):
 p=norm(a).ravel(); q=norm(b).ravel(); m=(p+q)/2; v=0.
 for x,y,z in zip(p,q,m):
  if x>0:v+=.5*x*math.log(x/z)
  if y>0:v+=.5*y*math.log(y/z)
 return float(v)
def l1(a,b): return float(np.mean(np.abs(norm(a)-norm(b))))
def rmse(a,b): return float(np.sqrt(np.mean((norm(a)-norm(b))**2)))
def cdf_l1(a,b): return float(np.mean(np.abs(np.cumsum(norm(a))-np.cumsum(norm(b)))))
def fwhm(x,y):
 ids=np.flatnonzero(np.asarray(y)>=np.nanmax(y)/2); return float(x[ids[-1]]-x[ids[0]]) if len(ids) else float('nan')
def summary(p,lam,ang):
 sm=norm(np.trapezoid(p,np.radians(ang),axis=1)); am=norm(np.trapezoid(p,lam,axis=0)); o={'peak_wavelength_nm':float(lam[np.argmax(sm)]),'spectral_fwhm_nm':fwhm(lam,sm),'peak_angle_deg':float(ang[np.argmax(am)]),'angular_fwhm_deg':fwhm(ang,am)}
 for c in (5,10,20): o[f'cone{c}']=float(np.trapezoid(am[np.abs(ang)<=c],np.radians(ang[np.abs(ang)<=c])))
 return o
def rank(a,b):
 a=pd.Series(a).rank().to_numpy(); b=pd.Series(b).rank().to_numpy()
 return float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else float('nan')
def agg(rows):
 ks=[k for k in rows[0] if k not in ('test_case_uid','geometry_hash','topology','boundary_class')]; out={}
 for k in ks:
  v=np.asarray([r[k] for r in rows],float); v=v[np.isfinite(v)]
  if len(v): out[k]={'mean':float(v.mean()),'median':float(np.median(v)),'p95':float(np.quantile(v,.95)),'max':float(v.max())}
 return out
pred=pd.read_parquet(SEL/'test40_blind_prediction_case_index.parquet').sort_values('test_case_uid').reset_index(drop=True)
pp=np.load(SEL/'test40_blind_prediction_profiles.npy',mmap_mode='r')
ci=pd.read_parquet(SEL/'test40_case_label_index_v1.parquet').set_index('test_case_uid')
gm=pd.read_csv(SEL/'test40_geometry_manifest_v1.csv').set_index('geometry_hash')
gpi=pd.read_parquet(SEL/'test40_geometry_profile_index_v1.parquet').set_index('geometry_hash')
assert len(pred)==len(ci)==240 and pp.shape==(240,301,2000)
case=[]; pb={}; powers={}
for _,r in pred.iterrows():
 row=ci.loc[r.test_case_uid]; z=np.load(row.joint_tensor_path); j=np.asarray(z['joint_raw'],float); lam=np.asarray(z['wavelength_nm'],float); ang=np.asarray(z['angle_deg'],float); p=norm(pp[int(r.profile_row)]); k=int(np.argmin(abs(lam-450))); lp=float(np.asarray(z['p_up_raw'])[k]); ls=summary(j,lam,ang); ps=summary(p,lam,ang)
 m={'test_case_uid':r.test_case_uid,'geometry_hash':r.geometry_hash,'joint_js':js(j,p),'joint_weighted_l1':l1(j,p),'joint_rmse':rmse(j,p),'spectral_cdf_l1':cdf_l1(np.trapezoid(j,np.radians(ang),axis=1),np.trapezoid(p,np.radians(ang),axis=1)),'angular_cdf_l1':cdf_l1(np.trapezoid(j,lam,axis=0),np.trapezoid(p,lam,axis=0)),'label_power':lp,'pred_power':float(r.ensemble_power),'label_log_power':float(np.log(max(lp,1e-30))),'pred_log_power':float(r.ensemble_log_power),'peak_wavelength_abs_error_nm':abs(ps['peak_wavelength_nm']-ls['peak_wavelength_nm']),'spectral_fwhm_abs_error_nm':abs(ps['spectral_fwhm_nm']-ls['spectral_fwhm_nm']),'peak_angle_abs_error_deg':abs(ps['peak_angle_deg']-ls['peak_angle_deg']),'angular_fwhm_abs_error_deg':abs(ps['angular_fwhm_deg']-ls['angular_fwhm_deg']),'cone5_abs_error':abs(ps['cone5']-ls['cone5']),'cone10_abs_error':abs(ps['cone10']-ls['cone10']),'cone20_abs_error':abs(ps['cone20']-ls['cone20']),'seed_power_std':float(r.seed_power_std),'seed_log_power_std':float(r.seed_log_power_std)}
 case.append(m); pb.setdefault(r.geometry_hash,[]).append(p); powers.setdefault(r.geometry_hash,[]).append(m)
geom=[]
for gh,pss in pb.items():
 z=np.load(gpi.loc[gh].profile_path); p=np.mean(pss,axis=0); j=np.asarray(z['normalized_joint']); lam=np.asarray(z['wavelength_nm']); ang=np.asarray(z['angle_deg']); a=summary(p,lam,ang); b=summary(j,lam,ang); rows=powers[gh]
 geom.append({'geometry_hash':gh,'joint_js':js(j,p),'joint_weighted_l1':l1(j,p),'joint_rmse':rmse(j,p),'spectral_cdf_l1':cdf_l1(z['spectral_norm'],np.trapezoid(p,np.radians(ang),axis=1)),'angular_cdf_l1':cdf_l1(z['angular_norm'],np.trapezoid(p,lam,axis=0)),'label_power':float(np.mean([x['label_power'] for x in rows])),'pred_power':float(np.mean([x['pred_power'] for x in rows])),'peak_wavelength_abs_error_nm':abs(a['peak_wavelength_nm']-b['peak_wavelength_nm']),'spectral_fwhm_abs_error_nm':abs(a['spectral_fwhm_nm']-b['spectral_fwhm_nm']),'peak_angle_abs_error_deg':abs(a['peak_angle_deg']-b['peak_angle_deg']),'angular_fwhm_abs_error_deg':abs(a['angular_fwhm_deg']-b['angular_fwhm_deg']),'cone5_abs_error':abs(a['cone5']-b['cone5']),'cone10_abs_error':abs(a['cone10']-b['cone10']),'cone20_abs_error':abs(a['cone20']-b['cone20'])})
for x in geom: x.update({'topology':str(gm.loc[x['geometry_hash'],'topology']),'boundary_class':str(gm.loc[x['geometry_hash'],'boundary_class'])})
cl=agg(case); gl=agg(geom); case_log=np.asarray([x['pred_log_power']-x['label_log_power'] for x in case]); pr=rank([x['pred_power'] for x in case],[x['label_power'] for x in case]); gr=rank([x['pred_power'] for x in geom],[x['label_power'] for x in geom])
groups={}
for key in ('topology','boundary_class'):
 groups[key]={v:agg([x for x in geom if x[key]==v]) for v in sorted({x[key] for x in geom})}
metrics={'status':'PASS','scope_decision':'MDC_HF_SURROGATE_V2_TEST40_RANKING_SCREENING_ONLY','scope_reason':'No frozen quantitative acceptance threshold was found for post-lock Test40; raw 2D FDTD p_up values are not on the M1 source-normalized power scale, so absolute-power and profile numbers are descriptive and ranking is the only defensible external use.','case_count':240,'geometry_count':40,'case_metrics_summary':cl,'geometry_metrics_summary':gl,'case_power_rank_spearman':pr,'geometry_power_rank_spearman':gr,'case_log_power_mae':float(np.mean(abs(case_log))),'case_log_power_rmse':float(np.sqrt(np.mean(case_log**2))),'case_log_power_bias':float(np.mean(case_log)),'case_metrics':case,'geometry_metrics':geom,'no_label_tuning':True,'no_solver_after_extraction':True}
gen={'status':'PASS','training_scope':'576 DOE96 cases / 96 geometries','oof_scope':'frozen internal OOF only','test40_case_count':240,'test40_geometry_count':40,'case_prediction_shrinkage_to_label_power_ratio':float(np.std([x['pred_power'] for x in case])/max(np.std([x['label_power'] for x in case]),1e-30)),'case_seed_spread_vs_abs_log_power_error_rank_corr':rank([x['seed_log_power_std'] for x in case],abs(case_log)),'geometry_prediction_shrinkage_to_label_power_ratio':float(np.std([x['pred_power'] for x in geom])/max(np.std([x['label_power'] for x in geom]),1e-30)),'geometry_power_rank_corr':gr,'topology_boundary_groups':groups,'worst_geometries_by_joint_js':sorted(geom,key=lambda x:x['joint_js'],reverse=True)[:5],'no_model_refit':True,'no_tuning':True}
dump(SEL/'test40_external_evaluation_metrics_v1.json',metrics); dump(SEL/'test40_generalization_diagnostics_v1.json',gen)
r1=json.loads((SEL/'test40_extraction_replay_1.json').read_text()); r2=json.loads((SEL/'test40_extraction_replay_2.json').read_text()); dump(SEL/'test40_extraction_reproducibility_audit.json',{'status':'PASS' if r1==r2 else 'FAIL','replay_1':r1,'replay_2':r2,'identical_fields':['case_index_sha256','tensor_index_sha256','geometry_profile_sha256','grid_sha256'],'np_interface_view_status':'DERIVED_METADATA_ONLY_NO_NP_SOLVER','np_solver_calls':0,'case_count':240,'geometry_count':40})
pd.DataFrame([{'geometry_hash':x['geometry_hash'],'profile_path':gpi.loc[x['geometry_hash'],'profile_path'],'normalized_joint_profile_sha256':gpi.loc[x['geometry_hash'],'profile_sha256'],'interface_scope':'2D_FDTD_to_NP_one_way_profile_view','np_solver_calls':0,'new_physics_inferred':False} for x in geom]).to_parquet(SEL/'test40_np_interface_view_v1.parquet',index=False)
(SEL/'test40_external_evaluation_report.md').write_text(f"# Test40 external evaluation\n\nScope: {metrics['scope_decision']}\n\n{metrics['scope_reason']}\n\nCases/geometries: 240 / 40\n\nCase profile JS mean: {cl['joint_js']['mean']:.6g}\n\nGeometry profile JS mean: {gl['joint_js']['mean']:.6g}\n\nCase power rank Spearman: {pr:.6g}\n\nGeometry power rank Spearman: {gr:.6g}\n\nCase log-power MAE/RMSE/bias: {metrics['case_log_power_mae']:.6g} / {metrics['case_log_power_rmse']:.6g} / {metrics['case_log_power_bias']:.6g}\n\nNo tuning, refit, sealed-test, HF15, TMM, RCWA or NP solver calls were made during extraction/evaluation.\n",encoding='utf-8')
print(json.dumps({'scope_decision':metrics['scope_decision'],'case_power_rank_spearman':pr,'geometry_power_rank_spearman':gr,'case_log_power_mae':metrics['case_log_power_mae'],'geometry_js_mean':gl['joint_js']['mean'],'replay_status':json.loads((SEL/'test40_extraction_reproducibility_audit.json').read_text())['status']},indent=2))
