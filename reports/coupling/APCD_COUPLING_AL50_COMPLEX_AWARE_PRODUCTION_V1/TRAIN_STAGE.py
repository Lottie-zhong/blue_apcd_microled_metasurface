"""Formal609D diagnostic: cached labels only, frozen H2, no electromagnetic APIs."""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='2'
from pathlib import Path
import json,csv,sys,time,sqlite3,subprocess,warnings,datetime
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.kernel_ridge import KernelRidge
from sklearn.ensemble import ExtraTreesRegressor
from threadpoolctl import threadpool_limits
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Path(sys.argv[1]);P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');AL=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';V2=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2'
sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import contracts as C,h1 as H
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 p=D/n;p.parent.mkdir(exist_ok=True,parents=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8');os.replace(tmp,p)
def snapshot_entries():
 co=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);v=co.execute('select count(*) from solver_entries').fetchone()[0];co.close();return v
def load_data():
 return np.load(D/'COMPLEX_DATASET.npz',allow_pickle=False)
def main():
 D.mkdir(exist_ok=True);z=load_data();xx=z['D_nm'];ids=list(z['case_ids']);N=len(ids);family=rd(D/'LOCAL_FAMILY_COMPONENTS.json');folds=rd(D/'FOLDS.json')
 prereg={'architectures':{'A':'6 geometry -> official609','B':'6 geometry+wavelength ->29; official609 reconstruction'},'models':['Mean per wavelength','RBF-KRR alpha.1 gamma1/n_input','ExtraTrees128 minleaf3 seeds17,29,43'],'fit_limit':40,'preprocessing':'train-only StandardScaler inputs, raw frozen Cartesian+logP targets, no per-channel whitening','lambda':21,'effective_geometry_count':N,'primary_eval':'same124 old validation geometries; samefolds; familypurged','phase_mask_relative_magnitude_thresholds':[.001,.01,.05],'primary_phase_threshold':.001,'phase_reference':'dominant training-only channel for each wavelength; absolute IN_REF gauge preserved','ensemble':'complex arithmetic mean and physical P_scale arithmetic mean after seed inverse-log, matching H1','no_hyperparameter_search':True,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,'cpu_threads':2};put('PREREGISTRATION.json',prereg)
 (D/'prediction_checkpoints').mkdir(exist_ok=True);logs=rd(D/'FIT_LEDGER.json') if (D/'FIT_LEDGER.json').exists() else [];before=rd(D/'EXECUTION_BOUNDARY_BEFORE.json') if (D/'EXECUTION_BOUNDARY_BEFORE.json').exists() else {'canonical_entries':snapshot_entries()};put('EXECUTION_BOUNDARY_BEFORE.json',before)
 for architecture in ['A','B']:
  for f in folds:
   train=np.array([ids.index(v) for v in f['train_ids']]);va=set(f['heldout_ids']);tr=set(f['train_ids']);assert not tr&va and not any(tr&set(g) and va&set(g) for g in family)
   Xt=xx[train] if architecture=='A' else np.c_[np.repeat(xx[train],21,axis=0),np.tile(np.arange(440,461),len(train))];Xa=xx if architecture=='A' else np.c_[np.repeat(xx,21,axis=0),np.tile(np.arange(440,461),len(ids))];Y=z['target609'][train] if architecture=='A' else z['target29'][train].reshape(-1,29);sc=StandardScaler().fit(Xt);xt=sc.transform(Xt);xa=sc.transform(Xa)
   for kind,seed in [('Mean',17),('KRR',17)]+[('ExtraTrees',s) for s in [17,29,43]]:
    ident=architecture+'_fold'+str(f['fold'])+'_'+kind+'_'+str(seed);p=D/'prediction_checkpoints'/(ident+'.npz')
    if p.exists():continue
    put('WORKER_STATE.json',{'state':'FITTING','fit':ident,'completed':sum(v['state']=='COMPLETE' for v in logs),'maximum':40});row=next((r for r in logs if r['id']==ident),None)
    if row is None:row={'id':ident,'state':'STARTED','n_geometries':len(train),'n_rows':len(Xt),'n_outputs':Y.shape[1]};logs.append(row)
    put('FIT_LEDGER.json',logs);tick=time.perf_counter()
    with warnings.catch_warnings(record=True) as ws:
     warnings.simplefilter('always')
     if kind=='Mean':pred=np.tile(z['target609'][train].mean(axis=0),(N,1)) if architecture=='A' else np.tile(z['target29'][train].mean(axis=0),(N,1,1))
     else:
      model=KernelRidge(alpha=.1,kernel='rbf',gamma=1/Xt.shape[1]) if kind=='KRR' else ExtraTreesRegressor(n_estimators=128,min_samples_leaf=3,random_state=seed,n_jobs=2);model.fit(xt,Y);pred=model.predict(xa)
     if architecture=='B':
      pp=pred.reshape(N,21,29);pred=np.c_[pp[:,:,:28].reshape(N,588),pp[:,:,28]]
     chat,pscale=C.unpack_model_target(pred)
    np.savez_compressed(p,C_hat=chat,P_scale=pscale);row.update(state='COMPLETE',seconds=time.perf_counter()-tick,warnings=[str(v.message) for v in ws]);put('FIT_LEDGER.json',logs)
   if not (D/('PHASE_REFERENCE_fold'+str(f['fold'])+'.json')).exists():
    ref=np.argmax((abs(z['C_hat'][train])**2).mean(axis=0).reshape(21,14),axis=1);put('PHASE_REFERENCE_fold'+str(f['fold'])+'.json',{'channel_flat_indices':ref,'training_only':True,'channel_mapping':'m=-3..3,TE,TM','train_ids':f['train_ids']})
 for arch in ['A','B']:
  arrays={}
  for kind in ['Mean','KRR','ExtraTrees']:
   nc=[];npw=[];cs=[];pp=[]
   for f in folds:
    zc=[];zp=[]
    for seed in ([17,29,43] if kind=='ExtraTrees' else [17]):
     v=np.load(D/'prediction_checkpoints'/(arch+'_fold'+str(f['fold'])+'_'+kind+'_'+str(seed)+'.npz'),allow_pickle=False);zc.append(v['C_hat']);zp.append(v['P_scale'])
    cs.append(np.array(zc));pp.append(np.array(zp));nc.append(np.mean(zc,axis=0));npw.append(np.mean(zp,axis=0))
   arrays[kind+'_C_hat']=np.array(nc);arrays[kind+'_P_scale']=np.array(npw);arrays[kind+'_C_hat_seeds']=np.array(cs);arrays[kind+'_P_scale_seeds']=np.array(pp)
  np.savez_compressed(D/('PREDICTIONS_'+arch+'.npz'),case_ids=np.array(ids),**arrays)
 assert len(logs)==40 and all(r['state']=='COMPLETE' for r in logs)
 after=snapshot_entries();assert before['canonical_entries']==after;put('TRAINING_COMPLETE.json',{'fits':40,'fit_seconds':sum(r['seconds'] for r in logs),'new_FDTD':0,'canonical_entries_before':before['canonical_entries'],'canonical_entries_after':after,'seed_count_ET':3,'warnings':sum(bool(r['warnings']) for r in logs)});put('WORKER_STATE.json',{'state':'TRAINING_COMPLETE','fits':40,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});print('COMPLEX609_TRAINING_COMPLETE',flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=2):main()
