"""Provisional ordered K6 exploration proposals; no production geometry admission."""
from pathlib import Path
import sys,json,csv,collections,time
import numpy as np,joblib
from scipy.spatial.distance import cdist
from scipy.stats import qmc
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');O=R/'reports/coupling/APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import ingest
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 (O/n).write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda z:z.tolist() if isinstance(z,np.ndarray) else z.item())+'\n',encoding='utf-8')
assert not (O/'CANDIDATES_PROPOSED_16.csv').exists()
reg=ingest.load_frozen_case_registry(R);z=np.load(O/'TRAINING_DATA.npz',allow_pickle=False);x=z['D_nm'];y=np.c_[z['eta'],np.log(z['P_scale'])];excluded={};sources=[]
def add(g,why):
 try:
  if len(g)==6 and all(isinstance(v,(float,int,np.integer,np.floating)) and float(v).is_integer() and 0<float(v)<1000 for v in g):excluded.setdefault(tuple(map(int,g)),set()).add(why)
 except (TypeError,ValueError):pass
for role,rows in [('existing',reg.old32),('registered_development_entered_or_failed',reg.development),('sealed_geometry_metadata_only',reg.confirmation)]:
 for r in rows.values():add(r['ordered_D_nm'],role)
def walk(v,why):
 if isinstance(v,dict):
  for k,a in v.items():
   if k in ['ordered_D_nm','ordered_D1_D6_nm','ordered_D1_D6','D_nm','geometry','diameters_nm']:add(a,why)
   if isinstance(a,(dict,list)):walk(a,why)
 elif isinstance(v,list):
  for a in v:
   if isinstance(a,(dict,list)):walk(a,why)
paths=[R/'reports/coupling/PW_K6_GEOMETRY_EXCLUSION_REGISTRY_V1.json',R/'reports/coupling/PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST.json',R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_OVERNIGHT_PRODUCTION_DESIGN_V1/V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json']
for base in [R/'reports/coupling',Path(r'D:\apcd_runtime\coupling_v3_time_diag2_v1')]:
 if base.exists():
  paths.extend(p for p in base.rglob('*.json') if p.stat().st_size<10_000_000 and p.name.lower() in ['manifest.json','queue_manifest.json','source_manifest.json','batch_manifest.json','case_registration_package.json'] and not any(s in str(p).lower() for s in ['confirmation','sealed',str(O.name).lower()]))
for p in dict.fromkeys(paths):
 if not p.exists():continue
 walk(read(p),'protected_metadata:'+str(p));sources.append(str(p))
assert all(tuple(map(int,g)) in excluded for g in x)
put('CANDIDATE_SELECTION_PLAN.json',{'geometry_domain':'PROVISIONAL observed100..230nm/5 grid; ordered6; pitch290nm;height500nm; no coordinate permutation','formal_domain_authority':'independent manufacturing authority missing; old authority restricts extension to frozen pool','production_eligible':False,'proposal_count':16,'mixture':{'coverage':8,'model_disagreement':4,'stratified_random':4},'rationale':'weak eta/P+ ranking and uncalibrated uncertainty; emphasize geometry coverage; no best-predicted-power selection','pool_generation':'seeded scrambled Halton8192, floor27 grid; filter protected geometry metadata','forbidden_access':'sealed responses never loaded; sealed geometry registry only','minimum_diversity_distance':.4,'distance':'Euclidean on (D/130); same convention as historical domain','new_scientific_ids_created':False,'new_real_entry_authority':0})
pool=100+5*np.floor(qmc.Halton(6,scramble=True,seed=20261017).random(8192)*27).astype(int)
pool=np.unique(pool,axis=0);keep=np.array([tuple(g) not in excluded for g in pool]);removed=int((~keep).sum());pool=pool[keep]
# Physical geometric checks only. These do not constitute manufacturing approval.
gaps=290-(pool+np.roll(pool,-1,axis=1))/2;ygap=290-pool.max(1);margin=(290-pool.max(1))/2
assert (gaps>0).all() and (ygap>0).all() and (margin>0).all()
near=cdist(pool/130,x/130).min(1);pred={};seedvar={};start=time.perf_counter()
for k in ['KRR','ExtraTrees','MLP']:
 vals=np.array([joblib.load(O/f'models/{k}_{s}.joblib').predict(pool) for s in ([17] if k=='KRR' else [17,29,43])]);pred[k]=vals.mean(0);seedvar[k]=vals.std(0)
unc=np.std(np.array(list(pred.values())),axis=0);score=np.sqrt(np.mean((unc/np.maximum(y.std(0),1e-8))**2,axis=1));seconds=time.perf_counter()-start
picked=[];reasons=[];d=near.copy()
for _ in range(8):
 i=int(np.argmax(d));picked.append(i);reasons.append('geometry_coverage_maximin');d=np.minimum(d,cdist(pool/130,pool[[i]]/130)[:,0]);d[picked]=-1
for _ in range(4):
 v=score*np.minimum(d/.8,1);v[d<.4]=-1;v[picked]=-1;i=int(np.argmax(v));assert v[i]>=0;picked.append(i);reasons.append('model_disagreement_with_diversity');d=np.minimum(d,cdist(pool/130,pool[[i]]/130)[:,0]);d[picked]=-1
rng=np.random.default_rng(20261017);mean=pool.mean(1);bins=np.digitize(mean,np.quantile(mean,[.25,.5,.75]))
for b in range(4):
 eligible=np.where((bins==b)&(d>=.4))[0];i=int(rng.choice(eligible));picked.append(i);reasons.append('stratified_random_mean_diameter_q'+str(b+1));d=np.minimum(d,cdist(pool/130,pool[[i]]/130)[:,0]);d[picked]=-1
selected=pool[picked];assert len(set(map(tuple,selected)))==16 and not set(map(tuple,selected))&set(excluded)
pair=cdist(selected/130,selected/130);pair[np.diag_indices(16)]=np.inf;assert pair.min()>=.4
with (O/'CANDIDATES_PROPOSED_16.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['proposal_rank','proposal_id']+[f'D{i}_nm' for i in range(1,7)]+['reason','distance_to_development156','raw_model_disagreement','min_periodic_x_gap_nm','min_periodic_y_gap_nm','min_halfcell_margin_nm','production_status'])
 for rank,(i,reason) in enumerate(zip(picked,reasons),1):w.writerow([rank,f'PROPOSAL_ONLY_AL_R01_{rank:02d}',*pool[i],reason,near[i],score[i],gaps[i].min(),ygap[i],margin[i],'HOLD_MANUFACTURING_AND_NUMERICAL_CONTRACT_NOT_ADMITTED'])
np.savez_compressed(O/'PROVISIONAL_CANDIDATE_POOL.npz',ordered_D_nm=pool,nearest_development_distance=near,raw_model_disagreement=score,selection_indices=np.array(picked))
occupancy={f'D{i+1}':{str(v):int((x[:,i]==v).sum()) for v in range(100,231,5)} for i in range(6)}
put('GEOMETRY_COVERAGE.json',{'development_count':156,'nominal_discrete_space_size':27**6,'observed_fraction_of_provisional_cartesian_grid':156/27**6,'axis_level_occupancy':occupancy,'candidate_nearest_development_distance_quantiles':np.quantile(near,[0,.25,.5,.75,1]),'selected_nearest_development_distance':near[picked],'minimum_selected_pair_distance':float(pair.min()),'min_selected_periodic_x_gap_nm':float(gaps[picked].min()),'min_selected_y_gap_nm':float(ygap[picked].min()),'min_selected_halfcell_margin_nm':float(margin[picked].min()),'manufacturing_acceptance':False,'generalization_gap':'sparse six-dimensional joint coverage; axis-level occupancy is insufficient','candidate_predict_seconds':seconds})
put('EXCLUSION_AUDIT.json',{'protected_unique_geometries':len(excluded),'sealed_confirmation_geometry_metadata_count':len(reg.confirmation),'response_access':0,'DOE56_all_56_reserved':True,'sources':sources,'all156_excluded':True,'registered_failed_cases_excluded':True,'pool_removed_protected_count':removed,'provisional_pool_count':len(pool),'selected_unique':16,'selected_protected_intersection':0,'queue_live_completeness':'PARTIAL; V31 lacks scientific identity registry; final resource/queue snapshot must be refreshed before admission','legal_production_pool':'BLOCKED: manufacturing contract not established; these are review-only proposals'})
put('GROWTH_PROTOCOL.json',{'initial_proposed_entry_budget':16,'authorization_now':0,'first_prerequisite':'DIAG2 same approved2 identities, exact5nm6ps contract, max1/case mapping confirmation and passing platform resource gate','no_direct_3ps_expansion':True,'scientific_acceptance':['single immutable case/attempt entry before solver','nativeFSP/H5/EH21wavelengths persistence','frozen609D/H2/refplane1722 checks','truth/labels receipt valid; energy/numerical contract gates','only labels-valid nonsealed newgeometry enters versioned development dataset'],'per_round_record':['dataset_version','proposal_reason','coverage','entry_consumed','truth_valid','labels_valid','failure_rate','FDTD_walltime','model_metrics','marginal_gain'],'growth_250_500_1000_is_budget':False,'inverse_production':'HOLD until independent grouped skill/ranking thresholds preregistered and met','budget_stop':'no auto retry entered attempt; failures consume entry; no replacements without separate budget','next_dataset_manifest':'not created:0newtruth;156Gversionunchanged','batch_hold':['manufacturing authority','numerical precision closure after DIAG2','bounded science budget','V31 external resource/SHA/case/attempt fences and native export mapping']})
print('SELECTION_COMPLETE',json.dumps({'proposals':selected.tolist(),'pool':len(pool),'excluded':len(excluded),'production':'HOLD'}),flush=True)
