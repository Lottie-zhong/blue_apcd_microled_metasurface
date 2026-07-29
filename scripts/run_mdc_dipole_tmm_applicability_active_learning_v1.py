"""Freeze Dipole-TMM applicability and a no-solver MDC FDTD AL geometry matrix."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import mdc_dipole_tmm as dtmm
import mdc_tmm_core as ordinary
CFG=json.loads((ROOT/'configs'/'mdc_dipole_tmm_applicability_active_learning_v1.json').read_text())
PAIR=ROOT/'outputs'/'mdc_dipole_tmm_fdtd_residual_contract_v1'/'paired-residual-20260729T153500Z-ed71d1d48219'
DATA=ROOT/'datasets'/'mdc_ml_database_v1'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False),encoding='utf-8')
def norm(a):
 a=np.asarray(a,float); lo=np.nanmin(a,axis=0); hi=np.nanmax(a,axis=0); return (a-lo)/np.where(hi>lo,hi-lo,1),lo,hi
def fwhm(grid,v):
 i=np.flatnonzero(v>=np.max(v)/2);return float(grid[i[-1]]-grid[i[0]])
def cone(a,v,d):
 n=v/np.trapezoid(v,np.deg2rad(a));m=np.abs(a)<=d;return float(np.trapezoid(n[m],np.deg2rad(a[m])))
def seq(row):return [(x[0],float(x[1])) for x in json.loads(row.compiled_sequence_json)]
def candidate(row):return dtmm.Candidate(str(row.candidate_id_primary),str(row.geometry_hash),tuple(('APCD_TIO2_NATIVE_M1' if k=='H' else 'APCD_SIO2_NATIVE_M1',v) for k,v in seq(row)))
def ordinary_metrics(row):
 s=seq(row); w=np.linspace(420,480,301); a=np.arange(-60,61,dtype=float)
 sp=np.array([.5*(ordinary.emission_tmm(s,float(x),0,'TE')['T']+ordinary.emission_tmm(s,float(x),0,'TM')['T']) for x in w])
 an=np.array([.5*(ordinary.emission_tmm(s,450,float(x),'TE')['T']+ordinary.emission_tmm(s,450,float(x),'TM')['T']) for x in a])
 return {'ordinary_T450':float(sp[np.argmin(abs(w-450))]),'ordinary_spectral_fwhm_nm':fwhm(w,sp),'ordinary_angular_fwhm_deg':fwhm(a,an),'ordinary_cone5':cone(a,an,5),'ordinary_cone10':cone(a,an,10),'ordinary_cone20':cone(a,an,20),'ordinary_peak_angle_deg':float(a[np.argmax(an)])}
def tolerance_calc(row):
 s=seq(row); base=.5*(ordinary.emission_tmm(s,450,0,'TE')['T']+ordinary.emission_tmm(s,450,0,'TM')['T']); vals=[]
 for key,delta in [('H',-1.),('H',1.),('L',-1.),('L',1.)]:
  p=[(k,float(v)+delta if k==key else float(v)) for k,v in s]
  vals.append(.5*(ordinary.emission_tmm(p,450,0,'TE')['T']+ordinary.emission_tmm(p,450,0,'TM')['T']))
 return float(np.mean(np.abs(np.asarray(vals)-base)))
def allowed_dtmm(row):
 c=candidate(row);a=np.arange(-60,61,dtype=float);vals=[]
 for o in ('x','z'):vals.append(np.array([dtmm.dipole_channel(c,450,float(x),-276,o)['I_air_relative'] for x in a],float))
 v=.5*(vals[0]+vals[1]);return {'dipole_allowed_angular_fwhm_deg':fwhm(a,v),'dipole_allowed_cone5':cone(a,v,5),'dipole_allowed_cone10':cone(a,v,10),'dipole_allowed_cone20':cone(a,v,20)}
def farthest(frame,need,chosen):
 features=frame[['T450','spectral_FWHM_nm','normal_to_40_60_ratio','total_thickness_nm','physical_layer_count','tolerance_score']]
 features=features.fillna(features.median(numeric_only=True)).fillna(0.0)
 z,_,_=norm(features.to_numpy()); ids=frame.geometry_hash.tolist(); selected=list(chosen)
 while len(selected)<need:
  avail=[i for i,x in enumerate(ids) if x not in selected]
  score=[]
  for i in avail:
   if not selected:score.append((1e9,ids[i]))
   else:
    js=[ids.index(x) for x in selected];score.append((float(np.min(np.linalg.norm(z[i]-z[js],axis=1))),ids[i]))
  selected.append(sorted(score,key=lambda x:(-x[0],x[1]))[0][1])
 return selected
def run(out):
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True)
 master=pd.read_csv(DATA/'geometry_master.csv');metrics=pd.read_csv(DATA/'tmm_nominal_metrics.csv');tol=pd.read_csv(DATA/'tolerance_samples.csv')
 # Canonical non-sealed, accepted, Native-M1 geometries with a complete physical sequence.
 pool=master.merge(metrics[['geometry_hash','T450','spectral_FWHM_nm','normal_to_40_60_ratio','quality_status','usable_for_training']],on='geometry_hash',how='inner',suffixes=('','_metric'))
 # Raw tolerance samples retain perturbed T450 rather than a precomputed
 # delta label; use within-parent dispersion without inventing missing values.
 tr=tol.groupby('parent_nominal_geometry_hash')['T450'].std().rename('tolerance_score').reset_index()
 pool=pool.merge(tr,left_on='geometry_hash',right_on='parent_nominal_geometry_hash',how='left').drop(columns=['parent_nominal_geometry_hash'])
 existing={'090ed02536eced9e44ecc56f42228688c4b61f166327793e461b63fbcb9e07d9','ad8cbef5a96144d8d7d0e2d9bdba185905a6250f90a83b945bfb99b967482af5','c38694d6f162c04322ae8a87def91622d4fd4f272e4ec286e85acc978f74d888'}
 pool=pool[(pool.quality_status.eq('accepted'))&(pool.usable_for_training.fillna(False))&(pool.material_model.eq('native_m1'))&(~pool.geometry_hash.isin(existing))].drop_duplicates('geometry_hash').copy()
 pool['tolerance_score_available_from_legacy']=pool.tolerance_score.notna()
 if len(pool)<16 or pool.geometry_hash.isna().any() or pool.compiled_sequence_json.isna().any():raise RuntimeError('insufficient canonical pool')
 # Four deterministic strata; each contributes three primary geometry candidates before global coverage.
 qT=pool.T450.quantile(.65); qN=pool.normal_to_40_60_ratio.quantile(.65); qF=pool.spectral_FWHM_nm.quantile(.35)
 pool['selection_stratum']=np.select([(pool.T450>=qT)&(pool.normal_to_40_60_ratio<qN),(pool.normal_to_40_60_ratio>=qN)&(pool.T450<qT),(pool.T450>=pool.T450.quantile(.45))],['A_high_transmission_broad_angle','B_narrow_angle_power_risk','C_spectral_angle_pareto'],'D_geometry_boundary_sparse')
 seed=[]
 for s in ['A_high_transmission_broad_angle','B_narrow_angle_power_risk','C_spectral_angle_pareto','D_geometry_boundary_sparse']:
  g=pool[pool.selection_stratum.eq(s)].sort_values(['tolerance_score','geometry_hash'],ascending=[False,True]);seed += g.geometry_hash.head(2).tolist()
 if len(set(seed))<8:raise RuntimeError('stratum coverage insufficient')
 primary=farthest(pool,12,seed);reserve=farthest(pool[~pool.geometry_hash.isin(primary)],4,[])
 primary_df=pool.set_index('geometry_hash').loc[primary].reset_index();reserve_df=pool.set_index('geometry_hash').loc[reserve].reset_index()
 # Detailed allowed metrics are calculated only for frozen selections; prohibited Dipole-TMM power is never used.
 details=[]
 for status,frame in [('PRIMARY',primary_df),('RESERVE',reserve_df)]:
  for order,(_,r) in enumerate(frame.iterrows(),1):
   tscore=tolerance_calc(r);details.append(dict(r)|ordinary_metrics(r)|allowed_dtmm(r)|{'tolerance_score':tscore,'tolerance_score_method':'ordinary_TMM_global_H_L_plusminus_1nm_mean_abs_delta_T450','selection_status':status,'selection_order':order,'disagreement_score':abs(float(r.normal_to_40_60_ratio)-float(pool.normal_to_40_60_ratio.median())),'selection_reason':f"{r.selection_stratum}; farthest-point coverage; ordinary-TMM tolerance={tscore:.6g}"})
 detail=pd.DataFrame(details)
 # distances to the three completed FDTD geometry feature anchors, represented by their frozen physical contracts.
 anchors=np.array([[0,0,0,0,0,0],[46,78,312,978,12,0],[44,79,316,975,12,0]],float);feat=detail[['H_nm','L_nm','C_nm','total_thickness_nm','physical_layer_count','tolerance_score']].fillna(0).to_numpy(float);z,lo,hi=norm(np.vstack([feat,anchors]));dist=np.min(np.linalg.norm(z[:len(feat),None,:]-z[len(feat):][None,:,:],axis=2),axis=1);detail['nearest_existing_fdtd_geometry_distance']=dist
 # Deterministic primary/reserve matrices retain all layer/provenance and detail fields.
 primary_out=detail[detail.selection_status.eq('PRIMARY')].copy();reserve_out=detail[detail.selection_status.eq('RESERVE')].copy()
 future=[]
 for _,r in primary_out.iterrows():
  for role,y in CFG['source_positions_nm'].items():
   for ori in CFG['orientations']:future.append({'geometry_hash':r.geometry_hash,'candidate_id':r.candidate_id_primary,'source_role':role,'source_position_nm':y,'orientation':ori,'case_status':CFG['future_primary_status']})
 reserve_cases=[]
 for _,r in reserve_out.iterrows():
  for role,y in CFG['source_positions_nm'].items():
   for ori in CFG['orientations']:reserve_cases.append({'geometry_hash':r.geometry_hash,'candidate_id':r.candidate_id_primary,'source_role':role,'source_position_nm':y,'orientation':ori,'case_status':CFG['future_reserve_status']})
 if len(future)!=72 or len(reserve_cases)!=24:raise RuntimeError('future matrix cardinality')
 # Contract decisions traceable to paired residual evidence, not a performance claim.
 metric_table=pd.DataFrame([
  ('normalized_spectral_shape','DIAGNOSTIC_ONLY'),('peak_wavelength','DIAGNOSTIC_ONLY'),('spectral_FWHM','DIAGNOSTIC_ONLY'),('normalized_angular_shape','ALLOWED_FOR_SHAPE_PRIOR'),('angular_FWHM','ALLOWED_FOR_RANK_SCREENING'),('cone5','ALLOWED_FOR_RANK_SCREENING'),('cone10','ALLOWED_FOR_RANK_SCREENING'),('cone20','DIAGNOSTIC_ONLY'),('peak_angle_set','DIAGNOSTIC_ONLY'),('relative_upward_power','PROHIBITED_AS_FDTD_PROXY'),('x_z_polarization_delta','PROHIBITED_AS_FDTD_PROXY'),('source_depth_sensitivity','PROHIBITED_AS_FDTD_PROXY'),('absolute_extraction_efficiency','PROHIBITED_AS_FDTD_PROXY'),('Purcell_LDOS','PROHIBITED_AS_FDTD_PROXY')],columns=['metric','status'])
 contract={'contract_id':'MDC_DIPOLE_TMM_APPLICABILITY_V1','evidence_root':str(PAIR),'evidence_manifest_sha256':sha(PAIR/'manifest.json'),'conditions':['planar laterally invariant MDC','homogeneous_GaN_optical_approximation','Native-M1 materials','2D line-dipole reciprocity','fixed equal-weight x/z incoherent in-plane average'],'exclusions':['finite pixel','sidewalls','electrodes','NP','FDTD PML/monitor effects'],'metric_status':metric_table.to_dict(orient='records'),'prohibited_selection_metrics':['Dipole-TMM relative upward power','Dipole-TMM x/z polarization delta','Dipole-TMM source-depth sensitivity']}
 pareto=detail[['geometry_hash','candidate_id_primary','selection_status','selection_stratum','ordinary_T450','ordinary_spectral_fwhm_nm','ordinary_angular_fwhm_deg','ordinary_cone10','tolerance_score','nearest_existing_fdtd_geometry_distance']].copy()
 frames={'metric_evidence_table.parquet':metric_table,'candidate_pool.parquet':pool,'normalized_selection_features.parquet':detail,'primary_geometry_matrix.parquet':primary_out,'reserve_geometry_matrix.parquet':reserve_out,'future_case_matrix_primary_72.parquet':pd.DataFrame(future),'future_case_matrix_reserve_24.parquet':pd.DataFrame(reserve_cases),'geometry_distance_audit.parquet':detail[['geometry_hash','candidate_id_primary','nearest_existing_fdtd_geometry_distance']],'pareto_stratum_audit.parquet':pareto,'selection_rationale.parquet':detail[['geometry_hash','candidate_id_primary','selection_status','selection_stratum','selection_reason','nearest_existing_fdtd_geometry_distance','tolerance_score']]}
 for n,f in frames.items():f.to_parquet(out/n,index=False)
 budget={'stage_AL_1':{'primary_geometries':primary_out.sort_values('selection_order').geometry_hash.head(6).tolist(),'subruns':36,'status':'NOT_AUTHORIZED','gates':['geometry-dependent residual identifiable','leave-one-geometry-out stability','angular correction simplicity','power residual learnable structure']},'stage_AL_2':{'remaining_primary_geometries':6,'subruns':36,'status':'NOT_AUTHORIZED'},'reserve':{'geometries':4,'subruns':24,'status':'RESERVE_NOT_AUTHORIZED'},'sample_sufficiency':{'current_independent_geometries':3,'after_AL1':9,'after_primary':15,'identifiable_at_9':['global scalar correction','target-wise affine calibration only with grouped validation'], 'identifiable_at_15':['low-dimensional linear residual with grouped validation'], 'not_authorized_without_grouped_validation':['tree-based residual','neural residual surrogate']}}
 dump(out/'dipole_tmm_applicability_contract.json',contract);dump(out/'staged_budget_recommendation.json',budget)
 prov={'geometry_master_sha256':sha(DATA/'geometry_master.csv'),'tmm_metrics_sha256':sha(DATA/'tmm_nominal_metrics.csv'),'tolerance_sha256':sha(DATA/'tolerance_samples.csv'),'paired_evidence_manifest_sha256':sha(PAIR/'manifest.json'),'solver_calls':0,'sealed_test_access':0};dump(out/'provenance.json',prov);dump(out/'manifest.json',{'run_id':out.name,'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'primary_geometries':12,'reserve_geometries':4,'primary_cases':72,'reserve_cases':24,'solver_calls':0})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output-root',required=True);a=p.parse_args();run(Path(a.output_root))
