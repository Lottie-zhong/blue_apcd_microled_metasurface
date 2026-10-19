"""Zero-solver staged AL50 evaluation with family-purged folds; no solver API."""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='2'
from pathlib import Path
import json,csv,sys,argparse,time,warnings,importlib.util
import numpy as np,joblib
from threadpoolctl import threadpool_limits
from scipy.stats import spearmanr
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';B=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2';AL=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
def rho(a,b):return None if len(a)<2 or np.std(a)<1e-14 or np.std(b)<1e-14 else float(spearmanr(a,b).statistic)
def main(stage):
 ledger=read(D/'AL50_SCIENCE_LEDGER.json');assert ledger['labels_valid']==stage and stage in [16,32,50]
 package=read(B/'AL50_FAST_PRODUCTION_MANIFEST_V2.json');cases=package['cases'];data=np.load(AL/'ML_UPDATE/FAST_DATASET_172G.npz',allow_pickle=False);ids=list(data['case_ids'])+[c['case_id'] for c in cases];idx={s:i for i,s in enumerate(ids)};x=np.r_[data['D_nm'],np.array([c['ordered_D_nm'] for c in cases])];assert len(set(map(tuple,x)))==222
 eta=np.full((222,21),np.nan);ps=eta.copy();truth=eta.copy();eta[:172]=data['eta'];ps[:172]=data['P_scale'];truth[:172]=data['P_plus1_H2'];known=set(range(172));records=[]
 for c in cases:
  if not ledger['cases'][c['case_id']]['labels_valid']:continue
  out=Path(c['science_output_directory']);r=read(out/'SCIENCE_RECEIPT.json');assert r['labels_valid']==r['truth_valid']=='PASS' and r['external_execution_id']==c['external_execution_id'] and r['entry_id']==ledger['cases'][c['case_id']]['entry_id'];z=np.load(out/'labels_609d.npz',allow_pickle=False);assert z['model_target'].shape==(1,609) and z['P_scale'].shape==(21,)
  i=idx[c['case_id']];eta[i]=z['eta'][:,4];ps[i]=z['P_scale'];truth[i]=z['P_plus1_H2'];known.add(i);records.append({'case_id':c['case_id'],'ordered_D_nm':c['ordered_D_nm'],'labels':str(out/'labels_609d.npz'),'receipt':str(out/'SCIENCE_RECEIPT.json'),'entry_id':r['entry_id'],'grade':'ML_TRAINING_GRADE','role':c['selection_role']})
 assert len(known)==172+stage and np.isfinite(ps[list(known)]).all() and (ps[list(known)]>0).all();y=np.c_[eta,np.log(ps)]
 S=D/f'STAGE_{stage:02d}';S.mkdir(exist_ok=True);assert not (S/'FIT_LEDGER.json').exists(),'existingstagefitledger; reconcile, never repeat completedfits'
 put(S/'FAST_DATASET_MANIFEST.json',{'base172':str(AL/'ML_UPDATE/FAST_DATASET_MANIFEST.json'),'new_labels_valid':records,'total':172+stage,'strict_convergence':'NOT_CERTIFIED','manufacturing':'UNRESOLVED','sealed':0,'DOE56_DIAG2_training_rows':0});ki=np.array(sorted(known));np.savez_compressed(S/f'FAST_DATASET_{172+stage}G.npz',case_ids=np.array(ids)[ki],roles=np.r_[data['roles'],np.array([c['selection_role'] for c in cases])][ki],D_nm=x[ki],eta=eta[ki],P_scale=ps[ki],P_plus1_H2=truth[ki],numerical_grade=np.array(['ML_TRAINING_GRADE']*len(ki)))
 families=read(B/'LOCAL_FAMILY_COMPONENTS.json');fam={cid:set(v) for v in families for cid in v};gfamily=fam['K6GDP2_DEV_G059'];sfamily=fam['K6V1_S31'];basefolds=read(AL/'ML_UPDATE/FOLDS.json');fold_for={cid:f['fold'] for f in basefolds for cid in f['heldout_old_ids']+f['heldout_new_ids']};
 for k,c in enumerate(cases):fold_for[c['case_id']]=3 if c['case_id'] in gfamily else (None if c['case_id'] in sfamily else k%4+1)
 old124=np.array([idx[cid] for f in basefolds for cid in f['heldout_old_ids']]);old140=np.array([idx[cid] for f in basefolds for cid in f['heldout_old_ids']+f['heldout_new_ids']]);newvalid=sorted(known-set(range(172)));globalnew={idx[c['case_id']] for c in cases if c['selection_role'] in ['coverage','disagreement','stratified_random']} &known;localnew=set(newvalid)-globalnew
 spec=importlib.util.spec_from_file_location('al50_original_models',R/'scripts/coupling_ml/gpu_active_learning_mainline_v1.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M);kinds=['Mean','KRR','ExtraTrees','MLP'];specs=[('Mean',17),('KRR',17)]+[(k,s) for k in ['ExtraTrees','MLP'] for s in [17,29,43]];fitlog=[]
 def fit(kind,seed,ti,tag):
  model=M.make(kind,seed);row={'id':tag,'kind':kind,'seed':seed,'n_train':len(ti),'state':'STARTED'};fitlog.append(row);put(S/'FIT_LEDGER.json',fitlog);t=time.perf_counter()
  with warnings.catch_warnings(record=True) as ws:warnings.simplefilter('always');model.fit(x[ti],y[ti])
  row.update(state='COMPLETE',seconds=time.perf_counter()-t,warnings=[str(w.message) for w in ws]);put(S/'FIT_LEDGER.json',fitlog);return model
 def evaluate_view(name,allowed):
  pred={k:np.full((4,222,42),np.nan) for k in kinds};foldnotes=[]
  for f in range(1,5):
   val={i for i in known if fold_for.get(ids[i])==f};blocked=set().union(*(fam.get(ids[i],{ids[i]}) for i in val));ti=np.array(sorted(i for i in allowed if i not in val and ids[i] not in blocked));vi=np.array(sorted(val));assert len(ti)>20 and not any(set(v)&{ids[i] for i in ti} and set(v)&{ids[i] for i in val} for v in families)
   foldnotes.append({'fold':f,'train_ids':[ids[i] for i in ti],'heldout_ids':[ids[i] for i in vi],'purged_ids':[ids[i] for i in allowed if i not in val and ids[i] in blocked],'family_overlap':0})
   estimates={}
   for kind,seed in specs:
    model=fit(kind,seed,ti,f'{name}/fold{f}/{kind}/{seed}');estimates.setdefault(kind,[]).append(model.predict(x))
   for k,v in estimates.items():pred[k][f-1]=np.mean(v,axis=0)
   np.savez_compressed(S/(name+'_PREDICTIONS_BY_FOLD_CHECKPOINT.npz'),**pred);put(S/(name+'_FOLDS.json'),foldnotes)
  return pred
 baseline_dir=D/'FAMILY_GUARDED_172_BASELINE';baseline_file=baseline_dir/'PREDICTIONS_BY_FOLD.npz'
 if baseline_file.exists():
  q=np.load(baseline_file,allow_pickle=False);baseline={k:q[k] for k in kinds}
 else:
  baseline=evaluate_view('MATCHED_172_BASELINE',set(range(172)));baseline_dir.mkdir(exist_ok=False);np.savez_compressed(baseline_file,case_ids=np.array(ids),D_nm=x,**baseline);put(baseline_dir/'BASELINE_POLICY.json',{'n':172,'familyguard':'sameconnectedfamilyasstageincludingfuturegeometriesonlymetadata; original124and140heldoutIDs preserved, trainingfamilymemberspurged','fits_once':32,'old32neverheldout':True,'legacy172metrics':'separatereferenceonly, notmixedwithguardedafter'})
 views={'ALL_V2_AVAILABLE':evaluate_view('ALL_V2_AVAILABLE',known),'GLOBAL_ONLY_ABLATION':evaluate_view('GLOBAL_ONLY_ABLATION',set(range(172))|globalnew)}
 if stage==50:
  mixed={idx[c['case_id']] for c in cases if c['selection_role'] in ['coverage','single_pillar_local','two_pillar_interaction']};assert len(mixed)==len(globalnew)==40;views['MATCHED_40_ACQUISITIONS_MIXED']=evaluate_view('MATCHED_40_ACQUISITIONS_MIXED',set(range(172))|mixed)
 def predictions(p,indices):return np.array([p[fold_for[ids[i]]-1,i] for i in indices])
 def summary(p):
  ans={}
  for k in kinds:
   a=predictions(p[k],old124);metric=M.evaluate(y[old124],a,truth[old124]);rs=[];top=[]
   for f in range(1,5):
    vi=np.array([i for i in old124 if fold_for[ids[i]]==f]);pp=p[k][f-1,vi,10]*np.exp(p[k][f-1,vi,31]);rr=rho(truth[vi,10],pp)
    if rr is not None:rs.append(rr)
    if np.std(pp)<1e-14:top.append(None)
    else:
     n=max(1,int(np.ceil(.2*len(vi))));t=np.lexsort((np.array(ids)[vi],-truth[vi,10]))[:n];pr=np.lexsort((np.array(ids)[vi],-pp))[:n];top.append(len(set(t)&set(pr))/n)
   metric['450nm_Pplus_mean_fold_Spearman']=float(np.mean(rs)) if rs else None;metric['450nm_top20_recall_mean']=float(np.mean([v for v in top if v is not None])) if any(v is not None for v in top) else None;metric['top20_recall_by_fold']=top;ans[k]=metric
  return ans
 summaries={'MATCHED_172_BASELINE':summary(baseline),**{v:summary(p) for v,p in views.items()}};put(S/'MODEL_METRICS_SAME124.json',summaries)
 # Preserve primaryOOF andsame140/newcohort scores separately, no newfitting.
 full=views['ALL_V2_AVAILABLE'];cohort={}
 for k in kinds:
  nn=np.array([i for i in newvalid if fold_for.get(ids[i]) is not None]);cohort[k]={'base140':M.evaluate(y[old140],predictions(full[k],old140),truth[old140]),'new_valid_evaluable_count':len(nn),'new_valid_OOF':M.evaluate(y[nn],predictions(full[k],nn),truth[nn])}
 put(S/'COHORT_METRICS_SEPARATE.json',cohort)
 edges=list(csv.DictReader((B/'AL50_LOCAL_PAIR_GRAPH.csv').open(encoding='utf-8')));groups=list(csv.DictReader((B/'AL50_INTERACTION_GROUPS.csv').open(encoding='utf-8')));targets={'P_plus1_H2':truth,'eta':eta,'P_scale':ps}
 def decode(p):return {'eta':p[:,:21],'P_scale':np.exp(p[:,21:]),'P_plus1_H2':p[:,:21]*np.exp(p[:,21:])}
 readyedges=[e for e in edges if idx[e['case_low']] in known and idx[e['case_high']] in known];eligible_edges=[e for e in readyedges if e['case_low'] in gfamily and e['case_high'] in gfamily];local={}
 for name,pred in {'MATCHED_172_BASELINE':baseline,**views}.items():
  local[name]={}
  for k in kinds:
   decoded=decode(pred[k][2]);bytarget={}
   for target,T in targets.items():
    diffs=[];prediffs=[]
    for e in eligible_edges:
     i,j=idx[e['case_low']],idx[e['case_high']];diffs.append(T[j]-T[i]);prediffs.append(decoded[target][j]-decoded[target][i])
    if diffs:
     a=np.array(diffs);b=np.array(prediffs);nz=a!=0;members=np.array([idx[cid] for cid in gfamily if idx[cid] in known]);rhos=[rho(T[members,w],decoded[target][members,w]) for w in range(21)];validrho=[v for v in rhos if v is not None]
     bytarget[target]={'local_delta_MAE':float(abs(a-b).mean()),'direction_accuracy_nonzero_truth':float(np.mean(np.sign(a[nz])==np.sign(b[nz]))) if nz.any() else None,'truth_exact_ties':int((~nz).sum()),'family_mean_spectral_rank_rho':float(np.mean(validrho)) if validrho else None,'edges':len(a),'independent_heldout_families':1}
    else:bytarget[target]={'status':'NO_COMPLETE_LOCAL_PAIR_YET'}
   local[name][k]=bytarget
 put(S/'LOCAL_DIFFERENCE_ACCURACY.json',local)
 interactions=[]
 for g in groups:
  ix=[idx[g[n]] for n in ['D','D_i','D_j','D_ij']];complete=all(i in known for i in ix);out={'group_id':g['group_id'],'anchor':g['anchor'],'complete_truth':complete,'known_corners':sum(i in known for i in ix),'nonadditivity_not_unique_nearfield_mechanism':True}
  if complete:
   out['targets']={}
   for t,T in targets.items():
    I=T[ix[3]]-T[ix[1]]-T[ix[2]]+T[ix[0]];z={'I_21':I,'peak_abs_I':float(abs(I).max()),'peak_wavelength_nm':int(440+abs(I).argmax()),'mean_abs_I':float(abs(I).mean())}
    if g['anchor']=='K6GDP2_DEV_G059':
     errors={}
     for view,p in {'MATCHED_172_BASELINE':baseline,**views}.items():
      errors[view]={}
      for k in kinds:
       F=decode(p[k][2])[t];Ip=F[ix[3]]-F[ix[1]]-F[ix[2]]+F[ix[0]];errors[view][k]={'Ihat_21':Ip,'interaction_prediction_MAE':float(abs(Ip-I).mean()),'heldout_family':True}
     z['prediction_errors']=errors
    else:z['prediction_errors']='NOT_SCORED_HELDOUT: historicalold32anchorrole; physicalIvalidonly'
    out['targets'][t]=z
  interactions.append(out)
 put(S/'INTERACTION_TRUTH_AND_PREDICTION.json',interactions)
 # Observedlocalamplitudes versus existingA1time-sensitivity: reference only, no statistical/noisebound claim.
 refs=list(csv.DictReader((Q/'APCD_COUPLING_DIAG2_V31_CONTROLLED_REAL_EXECUTION_V1/A1_science/WAVELENGTH_3PS_6PS_COMPARISON.csv').open(encoding='utf-8')));ref={'P_plus1_H2':np.array([abs(float(r['Pplus1_6ps'])-float(r['Pplus1_3ps'])) for r in refs]),'eta':np.array([abs(float(r['eta_plus1_6ps'])-float(r['eta_plus1_3ps'])) for r in refs]),'P_scale':np.array([abs(float(r['P_scale_6ps'])-float(r['P_scale_3ps'])) for r in refs])};amplitude=[];spectra=[]
 for e in readyedges:
  i,j=idx[e['case_low']],idx[e['case_high']]
  for t,T in targets.items():
   delta=T[j]-T[i];amplitude.append({'pair_id':e['pair_id'],'target':t,'max_abs_delta':float(abs(delta).max()),'wavelengths_above_A1_time_reference':int((abs(delta)>ref[t]).sum()),'n_wavelengths':21,'reference_not_geometry_matched_or_global_bound':True})
   for w in range(21):spectra.append({'pair_id':e['pair_id'],'case_low':e['case_low'],'case_high':e['case_high'],'axis':e['axis'],'wavelength_nm':440+w,'target':t,'Y_low':float(T[i,w]),'Y_high':float(T[j,w]),'delta':float(delta[w]),'A1_time_abs_reference':float(ref[t][w])})
 with (S/'LOCAL_RESPONSE_SPECTRA.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(spectra[0]));w.writeheader();w.writerows(spectra)
 put(S/'LOCAL_AMPLITUDE_VS_NUMERICAL_REFERENCE.json',{'pairs':amplitude,'interpretation':'Only observedA1same5nm3vs6ps reference acrossdifferentgeometries, not noiseconfidencebound; mesh4vs5evidence can be larger and remains unresolved. No claim statisticallysignificant above numericalerror fromoneunmatchedanchor.'})
 if stage==50:
  (S/'models').mkdir(exist_ok=True)
  for k,seed in specs:
   model=fit(k,seed,np.array(sorted(known)),f'FINAL_ALL/{k}/{seed}');joblib.dump(model,S/f'models/{k}_{seed}.joblib')
 assert all(r['state']=='COMPLETE' for r in fitlog)
 put(S/'STAGE_COMPLETE.json',{'stage_new_valid':stage,'FAST_DATASET_TOTAL':172+stage,'local_pair_truth_count':len(readyedges),'complete_interaction_group_count':sum(i['complete_truth'] for i in interactions),'fits_this_stage':len(fitlog),'fit_seconds_sum':sum(r['seconds'] for r in fitlog),'warning_fits':sum(bool(r['warnings']) for r in fitlog),'new_solver_entries_during_evaluation':0,'sealed_access':0,'familyguard':'PASS','local_generalization_families':1,'no_causal_comparison_to_unrunV1removed10':True})
 if stage==50:
  import subprocess
  for filename in ['AL50_CLOSEOUT.py','AL50_FINAL_FIGURES.py']:
   result=subprocess.run([sys.executable,str(D/filename)],cwd=str(D))
   assert result.returncode==0,('offlinecloseoutfailure',filename)
 print('STAGE_COMPLETE',stage,len(fitlog),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',type=int,required=True);args=p.parse_args()
 with threadpool_limits(limits=2):main(args.stage)
