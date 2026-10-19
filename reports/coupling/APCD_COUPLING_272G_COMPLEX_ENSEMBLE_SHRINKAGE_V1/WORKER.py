import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import sys,json,csv,time,sqlite3,subprocess,joblib
import numpy as np
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from threadpoolctl import threadpool_limits
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_272G_COMPLEX_ENSEMBLE_SHRINKAGE_V1';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';F=Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1/FORWARD'
D.mkdir(exist_ok=True);sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import h1 as H
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,default=lambda a:a.tolist() if hasattr(a,'tolist') else a.item(),allow_nan=False),encoding='utf-8')
def git():return {str(a):subprocess.run(['git','-C',str(R),*a],capture_output=True,text=True).stdout for a in [['status','--short'],['branch','--show-current'],['rev-parse','HEAD'],['rev-list','--left-right','--count','HEAD...@{u}'],['diff','--cached','--name-only']]}
def entries():
 p=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\data\runner_v31.db');c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);v=c.execute('select * from solver_entries').fetchall();c.close();return v
before=git();eb=entries();put('GIT_BEFORE.json',before);put('ENTRY_BEFORE.json',eb)
put('PREREGISTRATION.json',{'A':'384 raw leaf1 tree Cartesian mean','B':'mean magnitude times amplitude-weighted circular mean phase; no state normalization; native gauge','C':'mean frozen H2 tree routing, fixed A P_scale; application comparator only, no complex state','D':'7-64-64-29 tanh Adam MLP, train-only X/Y scaling, 300 fixed epochs, seeds17/29, 4 original folds; no search','P_scale_control':'A B C use identical saved Leaf1 physical seed-mean P_scale','validation':'existing124 primary geometries and exact family-purged fold train_ids; no sealed; no CVAE','uncertainty':'fold and seed descriptive; no independent-tree or wavelength confidence claims','NEW_FDTD':0})
z=np.load(B/'COMPLEX_DATASET.npz');ids=list(z['case_ids']);idx={s:i for i,s in enumerate(ids)};folds=rd(B/'FOLDS.json');old=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');w=z['cos_weights'];dec=H.load_h2_decoder();records=[];diag=[];orderdiag=[];gates={};pred=[];fitledger=[];metrics=[]
for fi,f in enumerate(folds):
 va=np.array([idx[s] for s in old[fi]['heldout_old_ids']]);tr=np.array([idx[s] for s in f['train_ids']]);assert not set(f['train_ids'])&set(f['heldout_ids']);assert f['family_overlap']==0
 x=np.c_[np.repeat(z['D_nm'][va],21,axis=0),np.tile(z['wavelengths_nm'],len(va))];trees=[]
 for seed in [17,29,43]:
  cache=D/f'trees_fold{fi+1}_seed{seed}.npz'
  if cache.exists():cs=np.load(cache)['C']
  else:
   a=joblib.load(F/f'Leaf1_fold{fi+1}_seed{seed}.joblib');assert a['train_ids']==f['train_ids'];xx=a['input_scaler'].transform(x);ys=np.array([t.predict(xx)/a['target_scale'] for t in a['model'].estimators_]);v=ys[:,:,:28].reshape(128,len(va),21,7,2,2);cs=v[...,0]+1j*v[...,1];np.savez_compressed(cache,C=cs)
  trees.append(cs)
  nt=np.sqrt((w[None,None,:,:,None]*abs(cs)**2).sum((3,4)));cm=cs.mean(0);nm=np.sqrt((w[None,:,:,None]*abs(cm)**2).sum((2,3)));rr=abs(cm)/np.maximum(abs(cs).mean(0),1e-15)
  diag.append({'fold':fi+1,'seed':seed,'n':len(va),'tree_norm':float(nt.mean()),'forest_norm':float(nm.mean()),'norm_ratio':float((nm/nt.mean(0)).mean()),'Re_tree_variance':float(np.var(cs.real,axis=0).mean()),'Im_tree_variance':float(np.var(cs.imag,axis=0).mean()),'TM_amplitude_weighted_circular_resultant':float((abs(cs[:,:,:,:,1]).mean(0)*rr[:,:,:,1]).sum()/abs(cs[:,:,:,:,1]).mean(0).sum())})
 allc=np.concatenate(trees);ca=allc.mean(0);mag=abs(allc).mean(0);cb=mag*np.exp(1j*np.angle(ca));pfile=np.load(F/'Leaf1_PREDICTIONS.npz');pa=pfile['P_scale'][fi,va];assert np.max(abs(ca-pfile['C_hat'][fi,va]))<1e-12
 tc=z['C_hat'][va];tp=z['P_scale'][va];te=z['eta_H2'][va];power=z['absolute_H2'][va];flux=(w[None,None,:,:,None]*abs(allc)**2).sum(-1);route=flux/flux.sum(-1,keepdims=True);ec=route.mean(0)
 candidates={'A_ReIm':(ca,pa,None),'B_MagnitudeCircular':(cb,pa,None),'C_PowerOnly':(None,pa,ec)}
 nncs=[];nnps=[]
 for seed in [17,29]:
  cache=D/f'NN_fold{fi+1}_seed{seed}.npz'
  if cache.exists():a=np.load(cache);cn=a['C'];pn=a['P']
  else:
   X=np.c_[np.repeat(z['D_nm'][tr],21,axis=0),np.tile(z['wavelengths_nm'],len(tr))];sx=StandardScaler().fit(X);sy=StandardScaler().fit(z['target29'][tr].reshape(-1,29));model=MLPRegressor(hidden_layer_sizes=(64,64),activation='tanh',solver='adam',max_iter=300,early_stopping=False,random_state=seed,batch_size=256,tol=0,n_iter_no_change=301);t=time.perf_counter()
   with threadpool_limits(limits=2):model.fit(sx.transform(X),sy.transform(z['target29'][tr].reshape(-1,29)))
   yy=sy.inverse_transform(model.predict(sx.transform(x))).reshape(len(va),21,29);a=yy[:,:,:28].reshape(len(va),21,7,2,2);cn=a[...,0]+1j*a[...,1];pn=np.exp(yy[:,:,28]);np.savez_compressed(cache,C=cn,P=pn);joblib.dump({'model':model,'X':sx,'Y':sy,'train_ids':f['train_ids']},D/f'NN_fold{fi+1}_seed{seed}.joblib');fitledger.append({'fold':fi+1,'seed':seed,'seconds':time.perf_counter()-t,'epochs':model.n_iter_});put('FIT_LEDGER.json',fitledger)
  nncs.append(cn);nnps.append(pn)
 candidates['D_NN29']=(np.mean(nncs,0),np.mean(nnps,0),None)
 for name,(cp,pp,ee) in candidates.items():
  hh=H.reconstruct_h2(cp,pp,dec) if cp is not None else {'eta':ee,'absolute_order':ee*pp[:,:,None]};e=hh['eta'];ap=hh['absolute_order'];tt=power[:,10,4];pr=ap[:,10,4];rho=float(spearmanr(tt,pr).statistic);n=int(np.ceil(.2*len(va)));top=len(set(np.argsort(tt)[-n:])&set(np.argsort(pr)[-n:]))/n
  row={'model':name,'fold':fi+1,'n':len(va),'P_scale_MAE':float(abs(pp-tp).mean()),'routing_MAE':float(abs(e-te).mean()),'eta_plus_MAE':float(abs(e[:,:,4]-te[:,:,4]).mean()),'Pplus_MAE':float(abs(ap[:,:,4]-power[:,:,4]).mean()),'rho450':rho,'Top20_recall':top}
  if cp is not None:
   af=tc.reshape(len(va),21,14);bf=cp.reshape(len(va),21,14);ref=np.array(rd(B/f'PHASE_REFERENCE_fold{fi+1}.json')['channel_flat_indices']);rr=np.broadcast_to(ref[None,:,None],(len(va),21,1));ar=np.take_along_axis(af,rr,2);br=np.take_along_axis(bf,rr,2);floor=.001*abs(af).max(2,keepdims=True);mask=(abs(af)>=floor)&(abs(ar)>=floor)&(abs(bf)>1e-12)&(abs(br)>1e-12)&(np.arange(14)[None,None,:]!=ref[None,:,None]);pe=abs(np.angle(bf*np.conj(br)*np.conj(af*np.conj(ar))));wt=abs(af)**2
   row.update(complex_SSE=float((abs(cp-tc)**2).sum()),complex_truth_energy=float((abs(tc)**2).sum()),complex_NRMSE=float(np.linalg.norm(cp-tc)/np.linalg.norm(tc)),TM_magnitude_MAE=float(abs(abs(cp[:,:,:,1])-abs(tc[:,:,:,1])).mean()),TM_variance_ratio=float(np.var(abs(cp[:,:,:,1]),axis=0,ddof=1).sum()/np.var(abs(tc[:,:,:,1]),axis=0,ddof=1).sum()),phase_numerator=float((wt[mask]*pe[mask]).sum()),phase_denominator=float(wt[mask].sum()),relative_phase_deg=float((wt[mask]*pe[mask]).sum()/wt[mask].sum()*180/np.pi),norm=float(np.sqrt((w[None,:,:,None]*abs(cp)**2).sum((2,3))).mean()))
  records.append(row)
  for k in range(7):orderdiag.append({'model':name,'fold':fi+1,'order':k-3,'routing_MAE':float(abs(e[:,:,k]-te[:,:,k]).mean()),'TM_magnitude_MAE':float(abs(abs(cp[:,:,k,1])-abs(tc[:,:,k,1])).mean()) if cp is not None else None,'TM_tree_amplitude_mean':float(abs(allc[:,:,:,k,1]).mean()),'TM_cartesian_mean_amplitude':float(abs(ca[:,:,k,1]).mean()),'TM_cancellation_ratio':float(abs(ca[:,:,k,1]).sum()/abs(allc[:,:,:,k,1]).mean(0).sum())})
  np.savez_compressed(D/f'{name}_fold{fi+1}.npz',case_ids=z['case_ids'][va],C=cp if cp is not None else np.empty(0),P=pp,eta=e,absolute=ap)
  if cp is not None:
   if name=='A_ReIm':cc=np.array([c.mean(0) for c in trees]);ps=pfile['P_scale_seeds'][fi,:,va].transpose(1,0,2) if False else np.array([pfile['P_scale_seeds'][fi,s,va] for s in range(3)])
   elif name=='B_MagnitudeCircular':cc=np.array([abs(c).mean(0)*np.exp(1j*np.angle(c.mean(0))) for c in trees]);ps=np.array([pfile['P_scale_seeds'][fi,s,va] for s in range(3)])
   else:cc=np.array(nncs);ps=np.array(nnps)
   pred.append((name,fi,va,cc,ps))
 print('FOLD_COMPLETE',fi+1,flush=True)
 put('FOLD_METRICS.json',records);put('TREE_DIAGNOSTIC.json',diag)
for name in ['A_ReIm','B_MagnitudeCircular','D_NN29']:
 a=[r for r in pred if r[0]==name];va=np.concatenate([r[2] for r in a]);cc=np.concatenate([r[3] for r in a],axis=1);pp=np.concatenate([r[4] for r in a],axis=1);gates[name]=H.evaluate_original_h1(z['C_hat'][va],cc,z['P_scale'][va],pp,z['eta_native'][va],z['eta_native'][va]*z['P_scale'][va,:,None],decoder=dec)
put('H1_GATES.json',gates)
for name in ['A_ReIm','B_MagnitudeCircular','C_PowerOnly','D_NN29']:
 rows=[r for r in records if r['model']==name];out={'model':name,'n':sum(r['n'] for r in rows)}
 for k in rows[0]:
  if k not in ['model','fold','n','complex_SSE','complex_truth_energy','phase_numerator','phase_denominator']:out[k]=float(np.mean([r[k] for r in rows])) if k in ['rho450','Top20_recall'] else float(sum(r[k]*r['n'] for r in rows)/124)
 if 'complex_SSE' in rows[0]:out['complex_NRMSE']=float(np.sqrt(sum(r['complex_SSE'] for r in rows)/sum(r['complex_truth_energy'] for r in rows)));out['relative_phase_deg']=float(sum(r['phase_numerator'] for r in rows)/sum(r['phase_denominator'] for r in rows)*180/np.pi)
 metrics.append(out)
for name,rows in [('COMPLEX_AGGREGATION_ABLATION.csv',metrics),('FOLD_METRICS.csv',records),('TM_ORDER_DIAGNOSTIC.csv',orderdiag)]:
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (D/name).open('w',newline='',encoding='utf-8') as f:wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(rows)
put('SUMMARY.json',metrics);after=git();ea=entries();assert eb==ea;assert before["['diff', '--cached', '--name-only']"]==after["['diff', '--cached', '--name-only']"];put('GIT_AFTER.json',after);put('BOUNDARY_AUDIT.json',{'entries_before':len(eb),'entries_after':len(ea),'entries_identical':True,'staged_unchanged':True,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD','CVAE_fits':0});put('COMPLETE.json',{'status':'COMPLETE','folds':4,'tree_fits':0,'NN_fits':8});print(json.dumps(metrics),flush=True)
