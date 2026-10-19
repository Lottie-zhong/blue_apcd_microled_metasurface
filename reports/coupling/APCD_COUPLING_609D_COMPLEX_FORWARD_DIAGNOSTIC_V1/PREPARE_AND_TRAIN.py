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
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');AL=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';V2=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2'
sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import contracts as C,h1 as H
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 p=D/n;p.parent.mkdir(exist_ok=True,parents=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8');os.replace(tmp,p)
def snapshot_entries():
 co=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);v=co.execute('select count(*) from solver_entries').fetchone()[0];co.close();return v
def load_data():
 cache=D/'COMPLEX_DATASET_222G.npz'
 if cache.exists():return np.load(cache,allow_pickle=False)
 dec=H.load_h2_decoder();H.load_h1_authority() # Existing frozen loader owns minimal small-source hash checks.
 ds=np.load(AL/'STAGE_50/FAST_DATASET_222G.npz',allow_pickle=False);ids=list(ds['case_ids']);xx=ds['D_nm'];known={s:i for i,s in enumerate(ids)};ch=np.empty((222,21,7,2),complex);ps=np.empty((222,21));eta_native=np.empty((222,21,7));records=[]
 inventory=rd(Q/'APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json');old={c['case_id']:c for c in inventory['cases']};old32=np.load(Q/'PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/dataset_truth_32g.npz',allow_pickle=False);old32idx={s:i for i,s in enumerate(old32['case_ids'])}
 a16=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FAST_DATASET_MANIFEST.json');a50=rd(AL/'STAGE_50/FAST_DATASET_MANIFEST.json');new={c['case_id']:c for c in a16['new_cases']+a50['new_labels_valid']}
 assert len(ids)==len(set(ids))==len(set(map(tuple,xx)))==222 and set(ids)==set(old)|set(new) and len(old)==156 and len(new)==66
 for cid in ids:
  i=known[cid]
  if cid in old:
   row=old[cid];assert np.array_equal(row['ordered_D_nm'],xx[i]);art=row['artifacts'];meta=Path(art['state_metadata']['path']);assert row['physical_contract_sha256']==C.PHYSICAL_CONTRACT_SHA256 and float(row['reference_plane_nm'])==C.REFERENCE_PLANE_NM and row['role'] in C.DEVELOPMENT_ROLES
   if cid in old32idx:
    j=old32idx[cid];ch[i]=old32['C_hat'][j];ps[i]=old32['P_scale'][j];eta_native[i]=old32['eta'][j];assert np.array_equal(old32['ordered_D_nm'][j],xx[i]);label=Path(art['legacy_dataset']['path'])
   else:
    label=Path(art['label']['path']);z=np.load(label,allow_pickle=False);assert str(z['case_id'])==cid;assert 'ordered_D_nm' not in z or np.array_equal(z['ordered_D_nm'],xx[i]);assert 'order_m' not in z or np.array_equal(z['order_m'],np.arange(-3,4));assert 'polarization' not in z or list(z['polarization'])==['TE','TM'];ch[i]=(z['C_hat_real']+1j*z['C_hat_imag']) if 'C_hat_real' in z else z['C_hat'] if 'C_hat' in z else z['c_hat'];ps[i]=z['P_scale'] if 'P_scale' in z else z['p_scale'];eta_native[i]=z['eta']
   attempt=row['attempt_id'];role=row['role'];source_sha=art['legacy_dataset' if cid in old32idx else 'label']['sha256']
  else:
   row=new[cid];label=Path(row['labels']);z=np.load(label,allow_pickle=False);assert str(z['case_id'])==cid and np.array_equal(row['ordered_D_nm'],xx[i]);ch[i]=(z['C_hat_real']+1j*z['C_hat_imag']) if 'C_hat_real' in z else z['C_hat'] if 'C_hat' in z else z['c_hat'];ps[i]=z['P_scale'] if 'P_scale' in z else z['p_scale'];eta_native[i]=z['eta'];assert np.array_equal(z['orders'],np.arange(-3,4))
   receipt=rd(label.parent/'SCIENCE_RECEIPT.json');assert receipt['case_id']==cid and receipt['labels_valid']==receipt['truth_valid']=='PASS';assert np.allclose(C.pack_model_target(ch[i],ps[i]),z['model_target'],atol=1e-13,rtol=0)
   meta=next((label.parent/'state').glob('*pw_complex_floquet_state.json'));attempt=receipt['attempt_id'];role='FAST_DEVELOPMENT_LABELS_VALID';source_sha=receipt['labels_sha256']
   accepted=rd(AL/(cid+'_SCIENCE_ACCEPTANCE.json')) if cid in {c['case_id'] for c in a50['new_labels_valid']} else rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1'/(cid+'_SCIENCE_ACCEPTANCE.json'));assert accepted['energy_metrics']['reference_plane_deembedding']['status']=='PASS'
  md=rd(meta);norm=md['normalization'];assert md['schema_version']=='PW_COMPLEX_FLOQUET_STATE_V1' and md['polarizations']==['TE','TM'] and md['directions']==['+z','-z'] and md['planes']==['IN','PRENP','POSTNP']
  assert norm['normalization']=='incident_+z_(0,0)_TM_power_at_IN_REF' and norm['gauge']=='single_global_phase_per_wavelength_from_IN_REF_+z_(0,0)_TM; reused at all planes/channels' and norm['relative_phase_preserved'] and norm['zero_denominator_count']==0
  assert np.allclose(md['wavelengths_nm'],np.arange(440,461),atol=1e-8,rtol=0) and np.isfinite(norm['gauge_phase_rad']).all()
  records.append({'case_id':cid,'attempt_id':attempt,'role':role,'ordered_D_nm':xx[i],'label':str(label),'existing_label_sha256':source_sha,'state_metadata':str(meta),'gauge':norm['gauge'],'reference_plane_nm':C.REFERENCE_PLANE_NM,'reference_binding':'frozen development inventory or accepted production reference-plane evidence','no_fresh_native_hash':True,'legacy_geometry_binding':'frozen_inventory_checked_against222_dataset_when_legacy_cache_omits_geometry'})
 assert np.isfinite(ch).all() and np.isfinite(ps).all() and (ps>0).all() and np.allclose(ps,ds['P_scale'],atol=1e-13,rtol=0)
 h=H.reconstruct_h2(ch,ps,dec);assert np.allclose(h['absolute_order'][:,:,4],ds['P_plus1_H2'],atol=1e-12,rtol=0)
 cosw=np.array([[dec._mode(int(m),0,float(w),1.,1,'TE')['kz_rad_m'].real/(2*np.pi/(w*1e-9)) for m in range(-3,4)] for w in range(440,461)]);normsq=np.sum(cosw[None,:,:,None]*abs(ch)**2,axis=(2,3));assert np.max(abs(normsq-1))<1e-10
 y=C.pack_model_target(ch,ps);c2,p2=C.unpack_model_target(y);assert np.allclose(c2,ch,atol=1e-14,rtol=0) and np.allclose(p2,ps,atol=1e-14,rtol=0)
 yy=np.concatenate((y[:,:588].reshape(222,21,28),y[:,588:,None]),axis=2);back=np.c_[yy[:,:,:28].reshape(222,588),yy[:,:,28]];assert np.array_equal(back,y)
 np.savez_compressed(cache,case_ids=np.array(ids),D_nm=xx,C_hat=ch,P_scale=ps,eta_native=eta_native,eta_H2=h['eta'],absolute_H2=h['absolute_order'],target609=y,target29=yy,cos_weights=cosw,wavelengths_nm=np.arange(440,461),orders=np.arange(-3,4),polarizations=np.array(['TE','TM']))
 put('DATA_LINEAGE_222G.json',records);put('SCIENCE_CONTRACT_AUDIT.json',{'cases':222,'old':156,'AL16':16,'AL50':50,'H1_authority':C.H1_AUTHORITY_SHA256,'H2_decoder':C.H2_DECODER_SHA256,'physical_contract':C.PHYSICAL_CONTRACT_SHA256,'layout':C.MODEL_TARGET_LAYOUT,'gauge_uniform':True,'phase_relative_preserved':True,'weighted_norm_max_abs_error':float(abs(normsq-1).max()),'H2_vs_saved_power_max_abs':float(abs(h['absolute_order'][:,:,4]-ds['P_plus1_H2']).max()),'H2_eta_vs_native_max_abs':float(abs(h['eta']-eta_native).max()),'pack29_roundtrip_exact':True,'sealed_response_access':0,'DOE56_DIAG2_rows':0,'hash_policy':'only frozen small H1/H2 source checks through existing API; existing label pins reused; no native rehash','full_space_EH_learning':False,'Geometry_to_eta_formal_model':False})
 return np.load(cache,allow_pickle=False)
def main():
 D.mkdir(exist_ok=True);z=load_data();xx=z['D_nm'];ids=list(z['case_ids']);family=rd(V2/'LOCAL_FAMILY_COMPONENTS.json');folds=rd(AL/'STAGE_50/ALL_V2_AVAILABLE_FOLDS.json');put('FOLDS.json',folds)
 prereg={'architectures':{'A':'6 geometry -> official609','B':'6 geometry+wavelength ->29; official609 reconstruction'},'models':['Mean per wavelength','RBF-KRR alpha.1 gamma1/n_input','ExtraTrees128 minleaf3 seeds17,29,43'],'fit_limit':40,'preprocessing':'train-only StandardScaler inputs, raw frozen Cartesian+logP targets, no per-channel whitening','lambda':21,'effective_geometry_count':222,'primary_eval':'same124 old validation geometries; samefolds; familypurged','phase_mask_relative_magnitude_thresholds':[.001,.01,.05],'primary_phase_threshold':.001,'phase_reference':'dominant training-only channel for each wavelength; absolute IN_REF gauge preserved','ensemble':'complex arithmetic mean and physical P_scale arithmetic mean after seed inverse-log, matching H1','no_hyperparameter_search':True,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,'cpu_threads':2};put('PREREGISTRATION.json',prereg)
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
     if kind=='Mean':pred=np.tile(z['target609'][train].mean(axis=0),(222,1)) if architecture=='A' else np.tile(z['target29'][train].mean(axis=0),(222,1,1))
     else:
      model=KernelRidge(alpha=.1,kernel='rbf',gamma=1/Xt.shape[1]) if kind=='KRR' else ExtraTreesRegressor(n_estimators=128,min_samples_leaf=3,random_state=seed,n_jobs=2);model.fit(xt,Y);pred=model.predict(xa)
     if architecture=='B':
      pp=pred.reshape(222,21,29);pred=np.c_[pp[:,:,:28].reshape(222,588),pp[:,:,28]]
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
