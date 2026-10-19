"""AL16 post-production merge and bounded light-model update. No solver API."""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='2'
from pathlib import Path
import json,sys,time,warnings,importlib.util,csv
import numpy as np,joblib
from scipy.spatial.distance import cdist
from threadpoolctl import threadpool_limits
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';B=Q/'APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1';A=Q/'APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';O=D/'ML_UPDATE';O.mkdir(exist_ok=True)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 p=O/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
def main():
 assert read(D/'CONTROLLER_STATE.json')['state']=='PRODUCTION_COMPLETE_PENDING_ML','Production still incomplete; no fitting'
 ledger=read(D/'AL16_SCIENCE_LEDGER.json');assert ledger['entered']==ledger['labels_valid']==16 and ledger['replay_count']==0
 assert not (O/'FIT_LEDGER.json').exists(),'Existing fits; reconcile checkpoints, never blindly repeat'
 package=read(B/'AL16_FAST_PRODUCTION_MANIFEST.json');inv=read(Q/'APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json');assert inv['valid_count']==156 and inv['contract']=='32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5'
 for c in inv['cases']:
  assert c['physical_contract_sha256']==inv['contract'] and c['reference_plane_nm']==1722 and c['wavelength_points']==list(range(440,461)) and c['status']=='SCIENCE_VALID_UNDER_FROZEN_CONTRACT'
 z=np.load(A/'TRAINING_DATA.npz',allow_pickle=False);ids=list(z['case_ids']);roles=list(z['roles']);x=list(z['D_nm']);eta=list(z['eta']);ps=list(z['P_scale']);truth=list(z['P_plus1_H2']);old_geom=set(map(tuple,z['D_nm']));rows=[]
 for case in package['cases']:
  assert case['physical_contract_sha256']==inv['contract'] and case['numerical_grade']=='ML_TRAINING_GRADE' and tuple(case['ordered_D_nm']) not in old_geom
  out=Path(case['science_output_directory']);rec=read(out/'SCIENCE_RECEIPT.json');acc=read(D/(case['case_id']+'_SCIENCE_ACCEPTANCE.json'));assert rec['labels_valid']==rec['truth_valid']=='PASS' and acc['status']=='PASS_ML_TRAINING_GRADE'
  lab=np.load(out/'labels_609d.npz',allow_pickle=False);assert lab['model_target'].shape==(609,) and lab['P_scale'].shape==(21,) and lab['eta'].shape==(21,7)
  assert np.isfinite(lab['model_target']).all() and np.all(lab['P_scale']>0)
  ids.append(case['case_id']);roles.append('AL16_FAST_DEVELOPMENT');x.append(case['ordered_D_nm']);eta.append(lab['eta'][:,4]);ps.append(lab['P_scale']);truth.append(lab['P_plus1_H2']);rows.append(dict(case_id=case['case_id'],ordered_D_nm=case['ordered_D_nm'],labels=str(out/'labels_609d.npz'),science_receipt=str(out/'SCIENCE_RECEIPT.json'),entry_id=rec['entry_id'],numerical_grade='ML_TRAINING_GRADE',fidelity_role='FAST_DATASET',strict_convergence='NOT_CERTIFIED',physics_contract_sha256=case['physical_contract_sha256']))
 ids=np.array(ids);roles=np.array(roles);x=np.array(x,float);eta=np.array(eta);ps=np.array(ps);truth=np.array(truth);y=np.c_[eta,np.log(ps)];assert len(x)==len(set(map(tuple,x)))==172
 provenance={'version':'FAST_DATASET_172G_AL16_R01_V1','total':172,'historical156_inventory':str(Q/'APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json'),'historical_cache':str(A/'TRAINING_DATA.npz'),'new_cases':rows,'grade':'ML_TRAINING_GRADE','history_grade_note':'Existing provenance-valid5nm3ps development data retained with numerical uncertainty; not re-certified strictconverged','contract':inv['contract'],'H1':inv['H1'],'H2':inv['H2'],'reference_plane_nm':1722,'wavelengths_nm':list(range(440,461)),'normalization':'Frozen incidentIN_REF/P_scale/H2; source definitions unchanged','new_native_eta_vs_H2_Pplus_factorization_max_abs':float(np.max(np.abs(eta[156:]*ps[156:]-truth[156:]))),'old32_train_only':True,'sealed_access':0,'DOE56_training_rows':0,'DIAG2_training_rows':0,'source_contract_compatibility':'PASS_SAME_FROZEN_FIELDS_AND_TARGET_DEFINITIONS','actual_manufacturing':'UNRESOLVED idealgeometry admitted','data_access':'No native fullrehash or repeated156G extraction; newlabels receipts and existing inventory reused'}
 put('FAST_DATASET_MANIFEST.json',provenance);np.savez_compressed(O/'FAST_DATASET_172G.npz',case_ids=ids,roles=roles,D_nm=x,eta=eta,P_scale=ps,P_plus1_H2=truth,numerical_grade=np.array(['ML_TRAINING_GRADE']*172))
 spec=importlib.util.spec_from_file_location('al16_reuse_light_models',R/'scripts/coupling_ml/gpu_active_learning_mainline_v1.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
 oldfolds=read(A/'FOLDS.json');before=read(A/'MODEL_METRICS.json');index={s:i for i,s in enumerate(ids)};heldold=set(s for f in oldfolds for s in f['heldout_ids']);old32=np.array([i for i in range(156) if ids[i] not in heldold]);assert len(old32)==32
 specs=[('Mean',17),('KRR',17)]+[(k,s) for k in ['ExtraTrees','MLP'] for s in [17,29,43]];kinds=['Mean','KRR','ExtraTrees','MLP'];oof={k:np.full((172,42),np.nan) for k in kinds};sd={k:np.full((172,42),np.nan) for k in ['ExtraTrees','MLP']};folds=[];fitlog=[];metrics={}
 put('TRAINING_PREREGISTRATION.json',{'fit_limit':40,'models':'Original make() hyperparameters unchanged; Mean,KRR,ET128leaf3,6-32-32-42MLP seeds17/29/43','folds':'original124 heldout frozen fourfold IDs; new16 deterministic roundrobin4folds, old32train-only','targets':'21nativeeta +21logP_scale; Ppluspredictioneta_hat*exp(logP_hat), compared to unchangedH2 truth','before_after':'before historical156 saved metrics, after compare exactlysame124holdouts; new16 separatelyOOF; no baseline refit','ranking':'Meanfold Spearman for comparablebefore; pooled after separately; top20percent ceil(n*.2),stablecaseID ties, constantpredundefined','no_tuning_or_new_architecture':True,'OOF_checkpoint_before_reload':True})
 def fit(kind,seed,ti,tag):
  model=M.make(kind,seed);row={'id':tag,'kind':kind,'seed':seed,'n_train':len(ti),'state':'STARTED'};fitlog.append(row);put('FIT_LEDGER.json',fitlog);t=time.perf_counter()
  with warnings.catch_warnings(record=True) as ws:
   warnings.simplefilter('always');model.fit(x[ti],y[ti])
  row.update(state='COMPLETE',seconds=time.perf_counter()-t,warnings=[str(w.message) for w in ws]);put('FIT_LEDGER.json',fitlog);return model
 def rankstats(a,b,ix):
  if np.std(b)<1e-14:return {'top20_recall':None,'reason':'constant predictions'}
  k=max(1,int(np.ceil(.2*len(a))));keys=ids[ix];tr=np.lexsort((keys,-a))[:k];pr=np.lexsort((keys,-b))[:k]
  return {'k':k,'top20_recall':len(set(tr)&set(pr))/k,'best_observed_regret':float(a.max()-a[pr].max()),'top20_oracle_mean_minus_selected_mean':float(a[tr].mean()-a[pr].mean())}
 for fdoc in oldfolds:
  f=fdoc['fold'];vaold=np.array([index[i] for i in fdoc['heldout_ids']]);vanew=np.array([156+i for i in range(16) if i%4==f-1]);va=np.r_[vaold,vanew]
  oldnew=np.array([i for i in range(156) if i not in set(vaold) and i not in set(old32)]);oldorder=np.random.default_rng(20261017+f).permutation(oldnew);ti=np.r_[old32,oldorder,[156+i for i in range(16) if 156+i not in set(vanew)]]
  assert not set(map(tuple,x[ti]))&set(map(tuple,x[va])) and not set(old32)&set(va)
  pred={};folds.append(dict(fold=f,train_ids=ids[ti],heldout_old_ids=ids[vaold],heldout_new_ids=ids[vanew]))
  for kind,seed in specs:
   model=fit(kind,seed,ti,f'fold{f}/{kind}/seed{seed}');pred.setdefault(kind,[]).append(model.predict(x[va]))
  for kind,values in pred.items():
   p=np.mean(values,axis=0);oof[kind][va]=p
   if kind in sd:sd[kind][va]=np.std(values,axis=0)
   metrics.setdefault(kind,[]).append(dict(fold=f,old=M.evaluate(y[vaold],p[:len(vaold)],truth[vaold]),new=M.evaluate(y[vanew],p[len(vaold):],truth[vanew]),top450_old=rankstats(truth[vaold,10],p[:len(vaold),10]*np.exp(p[:len(vaold),31]),vaold)))
  np.savez_compressed(O/'OOF_CHECKPOINT.npz',case_ids=ids,**oof,**{k+'_sd':v for k,v in sd.items()});put('FOLD_METRICS.json',metrics);put('FOLDS.json',folds);print('ML_FOLD_COMPLETE',f,flush=True)
 viold=np.array([index[i] for f in oldfolds for i in f['heldout_ids']]);vinew=np.arange(156,172);vi=np.r_[viold,vinew];after={};changes={}
 for kind in kinds:
  oldmetrics=M.evaluate(y[viold],oof[kind][viold],truth[viold]);newmetrics=M.evaluate(y[vinew],oof[kind][vinew],truth[vinew]);allmetrics=M.evaluate(y[vi],oof[kind][vi],truth[vi]);r={}
  for target in ['eta','P_scale','P_plus1_H2']:
   vals=[m['old'][target]['450nm']['Spearman'] for m in metrics[kind] if m['old'][target]['450nm']['Spearman'] is not None];rho=float(np.mean(vals)) if vals else None
   r[target]={'MAE_before':before[kind][target]['MAE'],'MAE_after_same124':oldmetrics[target]['MAE'],'MAE_change':oldmetrics[target]['MAE']-before[kind][target]['MAE'],'450nm_MAE_before':before[kind][target]['450nm']['MAE'],'450nm_MAE_after':oldmetrics[target]['450nm']['MAE'],'mean_fold_Spearman_before':before[kind][target]['450nm']['mean_fold_Spearman'],'mean_fold_Spearman_after':rho}
  changes[kind]=r;after[kind]={'same124_old':oldmetrics,'new16':newmetrics,'all140':allmetrics,'fold_top20_450_recall':[m['top450_old'] for m in metrics[kind]],'top20_before':'NOT_AVAILABLE; prior pooledOOF lost, not refit or invented','note':'pooledMean rank may reflect fold offsets; compare meanfold Spearman, undefined forconstantfold predictions'}
 put('MODEL_MAE_RANKING_BEFORE_AFTER.json',changes);put('MODEL_METRICS_AFTER.json',after);np.savez_compressed(O/'OOF_PREDICTIONS.npz',case_ids=ids,heldout=vi,**oof)
 final={};(O/'models').mkdir(exist_ok=True)
 for kind,seed in specs:
  model=fit(kind,seed,np.arange(172),f'final/{kind}/seed{seed}');path=O/f'models/{kind}_{seed}.joblib';joblib.dump(model,path);final.setdefault(kind,[]).append(model)
  # PersistedOOF already safe; reload check equal_nan guards validmatchingNaN diagnostics, no repeat fits.
  assert np.allclose(model.predict(x[:3]),joblib.load(path).predict(x[:3]),rtol=1e-10,atol=1e-12,equal_nan=True)
 # Coverage and next round use original pool, no new solver identities or budgets.
 pool=np.load(A/'PROVISIONAL_CANDIDATE_POOL.npz',allow_pickle=False)['ordered_D_nm'];db=cdist(pool/130,x[:156]/130).min(1);da=cdist(pool/130,x/130).min(1);existing=set(map(tuple,x));mask=np.array([tuple(v) not in existing for v in pool]);eligible=np.flatnonzero(mask)
 cov={'before_geometries':156,'after_geometries':172,'pool_size':len(pool),'uncomputed_original_pool_remaining':int(mask.sum()),'pool_min_distance_before_quantiles':np.quantile(db,[0,.25,.5,.75,1]),'pool_min_distance_after_quantiles':np.quantile(da,[0,.25,.5,.75,1]),'same_remaining_pool_mean_distance_before':float(db[eligible].mean()),'after':float(da[eligible].mean()),'axis_occupancy_before':[(len(np.unique(x[:156,i]))) for i in range(6)],'axis_occupancy_after':[len(np.unique(x[:,i])) for i in range(6)],'interpretation':'Coverage distances can shrink mechanically when16sitesadded; not proof of physical accuracy or improvedranking'};put('GEOMETRY_COVERAGE_CHANGE.json',cov)
 predpool={k:np.array([m.predict(pool) for m in models]) for k,models in final.items() if k!='Mean'};unc=np.std(np.concatenate([v for v in predpool.values()],axis=0)[:,:,:21],axis=0).mean(1)
 coverage=da.copy();selected=[];reasons=[]
 def pick(i,why):
  selected.append(int(i));reasons.append(why);coverage[:]=np.minimum(coverage,np.linalg.norm((pool-pool[i])/130,axis=1));coverage[~mask]=-np.inf;coverage[selected]=-np.inf
 coverage[~mask]=-np.inf
 for _ in range(8):pick(np.argmax(coverage),'coverage_maximin')
 for _ in range(4):
  valid=np.array([i for i in eligible if i not in selected and coverage[i]>=.4]);assert len(valid);pick(valid[np.argmax(unc[valid])],'uncalibrated_model_disagreement_with_diversity')
 rng=np.random.default_rng(20261018)
 for a,b in [(100,140),(140,165),(165,190),(190,231)]:
  valid=np.array([i for i in eligible if i not in selected and coverage[i]>=.4 and a<=pool[i].mean()<b]);
  if not len(valid):valid=np.array([i for i in eligible if i not in selected and coverage[i]>=.4])
  pick(rng.choice(valid),'stratified_random')
 with (O/'NEXT_ROUND_16_PROPOSALS_NOT_AUTHORIZED.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.writer(f);w.writerow(['proposal_rank','original_pool_index',*[f'D{i}_nm' for i in range(1,7)],'reason','nearest172_distance','uncalibrated_disagreement'])
  for rank,i in enumerate(selected,1):w.writerow([rank,int(i),*pool[i].tolist(),reasons[rank-1],float(da[i]),float(unc[i])])
 np.savez_compressed(O/'POOL_PRIORITY_UPDATE.npz',ordered_D_nm=pool,already_computed=~mask,nearest172_distance=da,uncalibrated_disagreement=unc,next_proposal_indices=np.array(selected))
 put('NEXT_ROUND_RECOMMENDATION.json',{'proposal_count':16,'solver_entries_authorized':0,'new_case_ids_created':0,'mix':'8coverage4disagreement4stratifiedrandom; ranking reliability not assumed','manufacturing_scope':'ideal geometry only, new16 require separate user approval; physical checks and freshprotectedmetadata dedup before packagefreeze','pool':str(A/'PROVISIONAL_CANDIDATE_POOL.npz'),'not_new_domain':True,'acquisition_uncertainty':'raw modeldisagreement, not calibrated confidence; do not exploit predictedhighest efficiency alone','new16_assessment':'activelyselected smallcohort, report separately, not randomgeneralization population','next_budget':'Only propose16FAST entries, not execute; highprecisionanchors separate optional proposal, no automaticconvergenceengineering expansion'})
 assert len(fitlog)==40
 put('TRAINING_COMPLETE.json',{'fits':len(fitlog),'fit_seconds_sum':sum(r['seconds'] for r in fitlog),'warning_fits':sum(bool(r['warnings']) for r in fitlog),'unique_total':172,'old32_train_only':32,'heldout_old':124,'heldout_new':16,'sealed_access':0,'solver_entries_during_ML':0,'baseline_refits':0})
 print('ML_UPDATE_COMPLETE',json.dumps(changes),flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=2):main()
