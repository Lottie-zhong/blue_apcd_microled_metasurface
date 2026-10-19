"""Task-owned zero-solver diagnosis and selection. No electromagnetic run API."""
from pathlib import Path
import os,json,sys,csv,sqlite3,time,subprocess
import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1';C=Q/'APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1';A=Q/'APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');D.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import contracts as CT,ingest as I,h1 as H
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 p=D/n;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
z=np.load(C/'COMPLEX_DATASET_222G.npz');ids=list(z['case_ids']);x=z['D_nm'];truth=z['C_hat'];w=z['cos_weights'];folds=rd(C/'FOLDS.json');dec=H.load_h2_decoder();pred={a:np.load(C/('PREDICTIONS_'+a+'.npz')) for a in ['A','B']};diag={};oo=[]
for f in folds:
 oldfold=next(g for g in rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json') if g['fold']==f['fold']);vi=np.array([ids.index(v) for v in oldfold['heldout_old_ids']]);fi=f['fold']-1
 a=pred['A']['ExtraTrees_C_hat'][fi,vi];b=pred['B']['ExtraTrees_C_hat'][fi,vi];t=truth[vi];ss=pred['B']['ExtraTrees_C_hat_seeds'][fi][:,vi];sse=np.mean(abs(b[:,:,:,1]-t[:,:,:,1])**2,axis=(1,2));dv=np.mean(abs(ss[:,:,:,:,1]-ss[:,:,:,:,1].mean(0))**2,axis=(0,2,3));ab=np.mean(abs(a[:,:,:,1]-b[:,:,:,1])**2,axis=(1,2))
 for k,i in enumerate(vi):oo.append(dict(case_id=ids[i],fold=f['fold'],TM_MSE=float(sse[k]),seed_disagreement=float(dv[k]),AB_disagreement=float(ab[k])))
 for arch in ['A','B']:
  p=pred[arch]['ExtraTrees_C_hat'][fi,vi];h=H.reconstruct_h2(p,pred[arch]['ExtraTrees_P_scale'][fi,vi],dec);th=H.reconstruct_h2(t,z['P_scale'][vi],dec);key=arch+'_fold'+str(f['fold']);phase=np.angle(p[:,:,:,1]*np.conj(t[:,:,:,1]));power=w[None]*abs(t[:,:,:,1])**2
  diag[key]={'TM_magnitude_MAE':float(np.mean(abs(abs(p[:,:,:,1])-abs(t[:,:,:,1])))),'routing_MAE_each_order':np.mean(abs(h['eta']-th['eta']),axis=(0,1)),'truth_between_geometry_variance_C_TM':np.var(t[:,:,:,1],axis=0).mean().real,'prediction_between_geometry_variance_C_TM':np.var(p[:,:,:,1],axis=0).mean().real,'truth_between_geometry_variance_magnitude_TM':float(np.var(abs(t[:,:,:,1]),axis=0).mean()),'pred_between_geometry_variance_magnitude_TM':float(np.var(abs(p[:,:,:,1]),axis=0).mean()),'pred_weighted_norm_mean':float(np.sqrt(np.sum(w[None,:,:,None]*abs(p)**2,axis=(2,3))).mean()),'TM_power_weighted_phase_MAE_deg':float(np.sum(abs(phase)*power)/power.sum()*180/np.pi),'near_zero_TE_phase_not_optimized':True}
err=np.array([r['TM_MSE'] for r in oo]);dv=np.array([r['seed_disagreement'] for r in oo]);ab=np.array([r['AB_disagreement'] for r in oo]);cal={'seed_disagreement_vs_TM_MSE_spearman':float(spearmanr(err,dv).statistic),'AB_disagreement_vs_TM_MSE_spearman':float(spearmanr(err,ab).statistic),'interpretation':'OOF association only, uncalibrated acquisition score; no claim uncertainty is guaranteed error predictor','geometry_count':124};put('LIGHTWEIGHT_ERROR_DIAGNOSTIC.json',{'fold_metrics':diag,'disagreement_information':cal,'source':'existing OOF only, no refitting','formal_target':'609D complex state + logP, frozen H2','power_error_attribution':rd(C/'ORACLE_ERROR_ATTRIBUTION.json')})
with (D/'OOF_DISAGREEMENT_DIAGNOSTIC.csv').open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(oo[0]));wr.writeheader();wr.writerows(oo)
# Metadata-only protection refresh: do not load sealed responses.
protected={};sources=[]
def add(g,why):
 try:
  if len(g)==6 and all(isinstance(v,(int,float,np.number)) and float(v).is_integer() and 0<float(v)<1000 for v in g):protected.setdefault(tuple(map(int,g)),set()).add(why)
 except (TypeError,ValueError):pass
def walk(v,why):
 if isinstance(v,dict):
  for k,a in v.items():
   if k in ['ordered_D_nm','ordered_D1_D6_nm','ordered_D1_D6','D_nm','geometry','diameters_nm']:add(a,why)
   if isinstance(a,(dict,list)):walk(a,why)
 elif isinstance(v,list):
  for a in v:
   if isinstance(a,(dict,list)):walk(a,why)
reg=I.load_frozen_case_registry(R)
for name,rr in [('old32',reg.old32),('development',reg.development),('sealed_geometry_metadata_only',reg.confirmation)]:
 for r in rr.values():add(r['ordered_D_nm'],name)
for d,n in [('APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1','AL16_FAST_PRODUCTION_MANIFEST.json'),('APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1','AL50_FAST_PRODUCTION_MANIFEST.json'),('APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2','AL50_FAST_PRODUCTION_MANIFEST_V2.json')]:
 p=Q/d/n;walk(rd(p),str(p));sources.append(str(p))
for n in ['APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1','APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1','APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2']:
 prev=rd(Q/n/'DEDUPLICATION_AUDIT.json')
 for sn in prev.get('source_paths',prev.get('sources',[])):
  p=Path(sn)
  if p.is_file():walk(rd(p),'prior_metadata:'+sn);sources.append(sn)
for folder in [P.parent/'v3_data',Path(r'D:\apcd_runtime\gpu_production_runner_v1'),Path(r'D:\apcd_runtime\coupling_v3_time_diag2_v1')]:
 for p in folder.rglob('*.json'):
  if p.name.lower() in ['manifest.json','source_manifest.json','queue_manifest.json','batch_manifest.json'] and not any(v in str(p).lower() for v in ['sealed','confirmation','fixture','validation']):walk(rd(p),str(p));sources.append(str(p))
con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;jobs=[dict(r) for r in con.execute('select * from jobs')];entries=[dict(r) for r in con.execute('select * from solver_entries')];con.close()
for j in jobs:
 if j.get('manifest_json'):walk(json.loads(j['manifest_json']),'canonical_job:'+str(j['id']))
for g in x:add(g,'FAST222')
add([120,160,165,175,160,195],'DIAG2_A1');add([210,115,175,115,180,125],'DIAG2_A2_HOLD')
put('DEDUPLICATION_AUDIT.json',{'protected_unique_geometries':len(protected),'source_paths':sorted(set(sources)),'canonical_jobs':jobs,'canonical_entries':entries,'sealed_response_access':0,'scope':'all registered history, protected geometry metadata, all V1/V2 including superseded reservations, known runtime queues and canonical V31; no unsupported assertion about unknown manual work'})
# Two independent train-only anchors, complete 3 missing corners each. Avoid all existing local families.
existingfamilies=rd(Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2/LOCAL_FAMILY_COMPONENTS.json');usedfam={v for fam in existingfamilies for v in fam};local=[];groups=[]
for axes in [(1,2),(5,0)]:
 candidates=[]
 for cid,r in reg.old32.items():
  if cid in usedfam or cid not in ids:continue
  g=np.array(r['ordered_D_nm'],int)
  for sign in [1,-1]:
   pts=[]
   for a,b in [(1,0),(0,1),(1,1)]:
    h=g.copy();h[axes[0]]+=sign*5*a;h[axes[1]]+=sign*5*b;pts.append(h)
   if all(np.all((h>=100)&(h<=230)) and tuple(h) not in protected and not any(np.array_equal(h,v['geometry']) for v in local) for h in pts):
    # prohibit accidental nearest single-step adjacency to any other family.
    near_other=False
    for h in pts:
     ds=np.abs(x-h);neighbors=np.where((ds.sum(1)==5)&((ds!=0).sum(1)==1))[0]
     if any(ids[k]!=cid for k in neighbors):near_other=True
    if not near_other:candidates.append((cid,g,sign,pts))
 assert candidates,'No admissible independent local anchor'
 cid,g,sign,pts=candidates[0];usedfam.add(cid);groups.append({'anchor':cid,'axes':[a+1 for a in axes],'delta_nm':sign*5,'anchor_D_nm':g.tolist(),'new_geometries':[h.tolist() for h in pts],'anchor_role':'old32 train-only; not moved into original124validation','truth_complete':False})
 for h in pts:local.append({'geometry':h,'anchor':cid,'axes':axes,'delta_nm':sign*5})
# Six fresh full222 acquisition fits, not reruns of completed CV. Chunk B pool prediction.
pool=np.load(A/'PROVISIONAL_CANDIDATE_POOL.npz')['ordered_D_nm'];assert len(pool)==8192
cache=D/'COMPLEX_POOL_ACQUISITION.npz'
if not cache.exists():
 arrays={};fits=[]
 with threadpool_limits(limits=2):
  for arch in ['A','B']:
   Xt=x if arch=='A' else np.c_[np.repeat(x,21,axis=0),np.tile(np.arange(440,461),len(x))];Y=z['target609'] if arch=='A' else z['target29'].reshape(-1,29);sc=StandardScaler().fit(Xt);Xt=sc.transform(Xt);cs=[];ps=[]
   for seed in [17,29,43]:
    tick=time.perf_counter();m=ExtraTreesRegressor(n_estimators=128,min_samples_leaf=3,random_state=seed,n_jobs=2);m.fit(Xt,Y);cc=[];pp=[]
    for start in range(0,len(pool),128):
     g=pool[start:start+128];X=g if arch=='A' else np.c_[np.repeat(g,21,axis=0),np.tile(np.arange(440,461),len(g))];y=m.predict(sc.transform(X))
     if arch=='B':y=y.reshape(len(g),21,29);y=np.c_[y[:,:,:28].reshape(len(g),588),y[:,:,28]]
     c,p=CT.unpack_model_target(y);cc.append(c);pp.append(p)
    cs.append(np.concatenate(cc));ps.append(np.concatenate(pp));fits.append({'arch':arch,'seed':seed,'seconds_fit_and_prediction':time.perf_counter()-tick,'training_geometries':222,'purpose':'acquisition only, not OOF evaluation'});print('ACQUISITION_FIT',arch,seed,flush=True)
   cs=np.array(cs);ps=np.array(ps);arrays[arch+'_mean_C']=cs.mean(0);arrays[arch+'_variance_C']=np.mean(abs(cs-cs.mean(0))**2,axis=0);arrays[arch+'_mean_P']=ps.mean(0)
 np.savez_compressed(cache,**arrays);put('ACQUISITION_FIT_LEDGER.json',fits)
ac=np.load(cache);aa=ac['A_mean_C'];bb=ac['B_mean_C'];signal=np.mean(abs(truth[:,:,:,1])**2,axis=0);signal/=signal.sum();dis=np.sum((abs(aa[:,:,:,1]-bb[:,:,:,1])**2+ac['A_variance_C'][:,:,:,1]+ac['B_variance_C'][:,:,:,1])*signal,axis=(1,2));ha=H.reconstruct_h2(aa,ac['A_mean_P'],dec);hb=H.reconstruct_h2(bb,ac['B_mean_P'],dec);routing=np.mean(abs(ha['eta']-hb['eta']),axis=(1,2));score=dis/(np.median(dis)+1e-12)+routing/(np.median(routing)+1e-12)
mask=np.array([tuple(g) not in protected and not any(np.array_equal(g,l['geometry']) for l in local) for g in pool]);levels=np.arange(100,231,5);counts=np.array([[(x[:,k]==v).sum() for v in levels] for k in range(6)]);occ=counts.copy();di=((pool-100)//5).astype(int);near=cdist(pool/130,np.r_[x,[l['geometry'] for l in local]]/130).min(1);base_near=cdist(pool/130,x/130).min(1);sel=[];rows=[]
def pick(i,role,reason):
 i=int(i);assert mask[i] and i not in sel;sel.append(i);rows.append({'rank':len(rows)+1,'case_id':f'K6AL_COMPLEX_R03_G{len(rows)+1:03d}','original_pool_index':i,'role':role,'reason':reason,'D_nm':pool[i].tolist(),'complex_disagreement_score':float(score[i]),'distance_to_222':float(base_near[i])})
 for k in range(6):occ[k,di[i,k]]+=1
 near[:]=np.minimum(near,np.linalg.norm((pool-pool[i])/130,axis=1));near[~mask]=-np.inf;near[sel]=-np.inf
near[~mask]=-np.inf
for _ in range(28):
 sparse=np.mean(np.stack([1/np.sqrt(1+occ[k,di[:,k]]) for k in range(6)],axis=1),axis=1);pick(np.argmax(near*(1+.1*sparse)),'coverage','6D joint maximin with balanced marginal sparse-value bonus')
for _ in range(10):
 av=np.flatnonzero(mask&(near>=.30));assert len(av);pick(av[np.argmax(score[av])],'complex_disagreement','power-weighted TM complex variance plus A/B routing disagreement, diversity>=0.30 normalizedD; not predicted efficiency')
rng=np.random.default_rng(20261019);means=pool.mean(1);bins=np.quantile(means[mask],np.linspace(0,1,7))
for k in range(6):
 av=np.flatnonzero(mask&(near>=.30)&(means>=bins[k])&(means<=bins[k+1]));assert len(av);pick(rng.choice(av),'stratified_random',f'mean-diameter stratum {k+1}/6; seed20261019')
for l in local:rows.append({'rank':len(rows)+1,'case_id':f'K6AL_COMPLEX_R03_G{len(rows)+1:03d}','original_pool_index':None,'role':'local_interaction','reason':f"complete four-corner supplement anchor {l['anchor']}, axes{l['axes']}, delta{l['delta_nm']}nm",'D_nm':l['geometry'].tolist(),'local_anchor':l['anchor']})
geom=np.array([r['D_nm'] for r in rows]);assert len(rows)==len(set(map(tuple,geom)))==50 and all(tuple(g) not in protected for g in geom);assert np.all((geom>=100)&(geom<=230)&((geom-100)%5==0))
put('AL50_SELECTION.json',rows);put('AL50_CASE_GEOMETRY.json',geom);put('LOCAL_INTERACTION_DESIGN.json',groups);put('SELECTION_PREREGISTRATION.json',{'mix':{'coverage':28,'complex_disagreement':10,'stratified_random':6,'local':6},'maximum_authorized_entries':50,'local_anchors_train_only':True,'acquisition_uses_all222':True,'evaluation_same124_family_purged':True,'disagreement_not_calibrated':True,'no_predicted_efficiency_selection':True,'ordered_geometry_preserved':True,'diagnostic_information':cal})
after=cdist(pool/130,np.r_[x,geom]/130).min(1);put('COVERAGE_CHANGE_PROSPECTIVE.json',{'before222_axis_counts':counts,'prospective272_axis_counts':np.array([[(np.r_[x,geom][:,k]==v).sum() for v in levels] for k in range(6)]),'levels_nm':levels,'pool_mean_distance_before':float(base_near.mean()),'pool_mean_distance_after':float(after.mean()),'selected50_vs_protected_conflicts':0,'computed_now':222,'prospective_only':272})
put('AUTHORITY.json',{'task':D.name,'user_authorized_maximum_new_entries':50,'per_case_max_entries':1,'replay':False,'first_two_roles':['coverage','complex_disagreement'],'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD','current_new_entries':0,'production_gate':'NOT_YET_COMPLETE'})
put('GIT_BASELINE.json',{n:subprocess.run(['git','-C',str(R),*a],capture_output=True,text=True).stdout for n,a in [('status',['status','--short']),('staged',['diff','--cached','--name-only']),('branch',['branch','--show-current']),('HEAD',['rev-parse','HEAD']),('ahead_behind',['rev-list','--left-right','--count','HEAD...@{u}'])]})
print('SELECTION_COMPLETE',cal,flush=True)

