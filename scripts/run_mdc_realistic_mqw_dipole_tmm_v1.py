from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
import mdc_dipole_tmm as d
from mdc_mqw_source_module import load
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x): Path(p).write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf-8')
def rows(candidate,depth,orientation,wls,angles):
 out=[]
 for wl in wls:
  val=d.dipole_channel(candidate,wl,0.,depth,orientation)['I_air_relative']; out.append({'response_kind':'spectrum_normal','wavelength_nm':float(wl),'air_angle_deg':0.,'I_air_relative':val})
 for angle in angles:
  val=d.dipole_channel(candidate,450.,angle,depth,orientation)['I_air_relative']; out.append({'response_kind':'angular_450','wavelength_nm':450.,'air_angle_deg':float(angle),'I_air_relative':val})
 return out
def run(out):
 cfg=load(); wls=np.round(np.arange(420,480.0001,.2),8); angles=np.arange(-60,61,1.); candidates=(d.BARE_GAN_AIR,d.P1_ZL1_ALTERNATIVE_G3_A3); wells=cfg['primary_mqw']['well_centers_nm']; weights=cfg['primary_mqw']['weights']; x=[];z=[];avg=[];strain=[]
 common={'fidelity_id':'F0_REALISTIC_MQW_DIPOLE_TMM_V1','epi_material_scope':cfg['epi_material_scope'],'normalization_contract':'relative_reciprocity_air_channel'}
 for cand in candidates:
  for j,depth in enumerate(wells,1):
   for orientation,target in (('x',x),('z',z)):
    for r in rows(cand,depth,orientation,wls,angles): target.append(common|{'candidate_id':cand.candidate_id,'geometry_hash':cand.geometry_hash,'well_index':j,'source_depth_nm':depth,'orientation':orientation}|r)
  for depth in cfg['strain_release_mqw']['well_centers_nm']:
   for orientation in ('x','z'):
    for r in rows(cand,depth,orientation,wls,angles): strain.append(common|{'candidate_id':cand.candidate_id,'geometry_hash':cand.geometry_hash,'source_depth_nm':depth,'orientation':orientation,'formal_primary_emission_weight':0.0}|r)
 xdf,zdf=pd.DataFrame(x),pd.DataFrame(z); merge=xdf.merge(zdf,on=['fidelity_id','epi_material_scope','normalization_contract','candidate_id','geometry_hash','well_index','source_depth_nm','response_kind','wavelength_nm','air_angle_deg'],suffixes=('_x','_z')); avdf=merge.drop(columns=['orientation_x','orientation_z']).assign(orientation='avg',I_air_relative=lambda f:.5*(f.I_air_relative_x+f.I_air_relative_z)).drop(columns=['I_air_relative_x','I_air_relative_z'])
 primary=[]
 keys=['candidate_id','geometry_hash','response_kind','wavelength_nm','air_angle_deg']
 for key,g in avdf.groupby(keys):
  value=float(np.average(g.I_air_relative,weights=weights)); primary.append(dict(zip(keys,key))|common|{'orientation':'primary_12mqw_avg','I_air_relative':value,'weight_sum':float(sum(weights))})
 primary=pd.DataFrame(primary); centroid=[]; old=[]
 for cand in candidates:
  for label,depth,target in [('centroid',cfg['primary_mqw']['centroid_nm'],centroid),('legacy_equivalent_active_plane',-400.,old)]:
   xr=pd.DataFrame(rows(cand,depth,'x',wls,angles)); zr=pd.DataFrame(rows(cand,depth,'z',wls,angles)); m=xr.merge(zr,on=['response_kind','wavelength_nm','air_angle_deg'],suffixes=('_x','_z')); m['I_air_relative']=.5*(m.I_air_relative_x+m.I_air_relative_z)
   for _,r in m.iterrows(): target.append(common|{'candidate_id':cand.candidate_id,'geometry_hash':cand.geometry_hash,'comparison_source':label,'source_depth_nm':depth,'orientation':'avg','response_kind':r.response_kind,'wavelength_nm':r.wavelength_nm,'air_angle_deg':r.air_angle_deg,'I_air_relative':r.I_air_relative})
 comparison=pd.DataFrame(centroid+old); comp=primary.merge(comparison,on=keys+['fidelity_id','epi_material_scope','normalization_contract'],suffixes=('_12well','_reference')); comp['relative_delta']=(comp.I_air_relative_reference-comp.I_air_relative_12well)/comp.I_air_relative_12well
 ranks=[]
 for kind,g in primary.groupby('response_kind'):
  if kind=='angular_450':
   q=g[abs(g.air_angle_deg)<=10].groupby('candidate_id').I_air_relative.sum().sort_values(ascending=False)
   ranks += [{'ranking_metric':'cone10_relative_sum_450','rank':i+1,'candidate_id':c,'score':float(v)} for i,(c,v) in enumerate(q.items())]
 frames={'per_well_x.parquet':xdf,'per_well_z.parquet':zdf,'per_well_average.parquet':avdf,'primary_12mqw_average.parquet':primary,'strain_release_sensitivity.parquet':pd.DataFrame(strain),'centroid_vs_12well_comparison.parquet':comp,'candidate_ranking.parquet':pd.DataFrame(ranks)}
 for name,f in frames.items(): f.to_parquet(out/name,index=False)
 prov={'contract':cfg,'candidate_count':2,'material_config_sha':sha(ROOT/'configs'/'material_reference_apcd_blue.yaml'),'safety_counters':{'FDTD_calls':0,'Lumerical_calls':0,'RCWA_calls':0,'sealed_test_target_reads':0,'model_fit_calls':0,'prediction_calls':0},'legacy_400nm_readonly_comparator':True}; dump(out/'provenance.json',prov); dump(out/'manifest.json',{'run_id':out.name,'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'run_fingerprint':hashlib.sha256(json.dumps(prov,sort_keys=True).encode()).hexdigest(),'all_finite':all(np.isfinite(f.select_dtypes(include=[np.number]).to_numpy()).all() for f in frames.values())})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output-root',required=True);a=p.parse_args();o=Path(a.output_root);o.mkdir(parents=True,exist_ok=False);run(o)
