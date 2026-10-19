from pathlib import Path
import json,sys,subprocess,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1';C=Q/'APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import contracts as CT,h1 as H
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
stage=int(sys.argv[sys.argv.index('--stage')+1]);assert stage in [44];S=D/f'STAGE_{stage}';S.mkdir(exist_ok=True)
if (S/'STAGE_EVALUATION_COMPLETE.json').exists():print('STAGE_ALREADY_COMPLETE_NO_REFIT',stage);sys.exit(0)
pkg=rd(D/'AL50_COMPLEX_PRODUCTION_MANIFEST.json');ledger=rd(D/'AL50_SCIENCE_LEDGER.json');by={c['case_id']:c for c in pkg['cases']};accepted=[by[c] for c in ledger['execution_order'] if ledger['cases'][c].get('labels_valid')][:stage];assert len(accepted)==stage
base=np.load(C/'COMPLEX_DATASET_222G.npz');ids=list(base['case_ids']);xx=list(base['D_nm']);ch=list(base['C_hat']);ps=list(base['P_scale']);en=list(base['eta_native']);records=[]
for c in accepted:
 out=Path(c['science_output_directory']);rec=rd(out/'SCIENCE_RECEIPT.json');z=np.load(out/'labels_609d.npz');assert rec['case_id']==c['case_id'] and rec['labels_valid']==rec['truth_valid']=='PASS';assert c['physical_contract_sha256']==CT.PHYSICAL_CONTRACT_SHA256;assert rec['source_setup']==c['source_fsp_sha256'];assert str(z['case_id'])==c['case_id'];cc=z['C_hat_real']+1j*z['C_hat_imag'];pp=z['P_scale'];assert np.allclose(CT.pack_model_target(cc,pp),z['model_target'],atol=1e-13,rtol=0);assert np.isfinite(cc).all() and np.isfinite(pp).all() and (pp>0).all();ids.append(c['case_id']);xx.append(c['ordered_D_nm']);ch.append(cc);ps.append(pp);en.append(z['eta']);records.append({'case_id':c['case_id'],'ordered_D_nm':c['ordered_D_nm'],'labels':str(out/'labels_609d.npz'),'receipt':str(out/'SCIENCE_RECEIPT.json'),'entry_id':rec['entry_id'],'numerical_grade':'ML_TRAINING_GRADE'})
xx=np.array(xx);ch=np.array(ch);ps=np.array(ps);en=np.array(en);N=len(ids);assert N==222+stage==len(set(ids))==len(set(map(tuple,xx)))
h=H.reconstruct_h2(ch,ps,H.load_h2_decoder());target=CT.pack_model_target(ch,ps);t29=np.concatenate((target[:,:588].reshape(N,21,28),target[:,588:,None]),axis=2)
np.savez_compressed(S/'COMPLEX_DATASET.npz',case_ids=np.array(ids),D_nm=xx,C_hat=ch,P_scale=ps,eta_native=en,eta_H2=h['eta'],absolute_H2=h['absolute_order'],target609=target,target29=t29,cos_weights=base['cos_weights'],wavelengths_nm=np.arange(440,461),orders=np.arange(-3,4),polarizations=np.array(['TE','TM']))
# Connected-component guard across ALL current geometries; never split a 5nm local family.
parent=list(range(N))
def find(k):
 while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
 return k
edges=[]
for i in range(N):
 delta=np.abs(xx[i+1:]-xx[i]);js=np.flatnonzero((delta.sum(1)==5)&((delta!=0).sum(1)==1))+i+1
 for j in js:parent[find(j)]=find(i);edges.append((i,int(j)))
families={}
for i,cid in enumerate(ids):families.setdefault(find(i),[]).append(cid)
families=[f for f in families.values() if len(f)>1];put(S/'LOCAL_FAMILY_COMPONENTS.json',families)
folds=rd(C/'FOLDS.json');newids=ids[222:];baseline_train_unchanged=True
for f in folds:
 original=set(f['train_ids']);val=set(f['heldout_ids']);denied=set().union(*(set(g) for g in families if set(g)&val));train=(original|set(newids))-denied;f['train_ids']=[v for v in ids if v in train];f['heldout_ids']=[v for v in ids if v in val];baseline_train_unchanged &= (train&set(ids[:222]))==original;assert not train&val;assert not any(train&set(g) and val&set(g) for g in families)
assert baseline_train_unchanged,'Acquisition changed original222purge; matched baseline required, HOLD model comparison';put(S/'FOLDS.json',folds);put(S/'FAST_DATASET_MANIFEST.json',{'base222':str(C/'DATA_LINEAGE_222G.json'),'new_labels_valid':records,'total':N,'validation124unchanged':True,'baseline222trainsets_unchanged':True,'family_guard':'connected5nmfamilies, old32 train-only preserved','no_sealed_access':True})
for script in ['TRAIN_STAGE.py','ANALYZE_STAGE.py']:
 rc=subprocess.run([sys.executable,str(D/script),str(S)],cwd=str(R));assert rc.returncode==0,(script,rc.returncode)
# Extra requested TM variance/routing, and a strong output-domain mean as evaluation reference only.
foldfor={v:f['fold']-1 for f in folds for v in f['heldout_ids']};old=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');vi=np.array([ids.index(v) for f in old for v in f['heldout_old_ids']]);out={}
for arch in ['A','B']:
 pr=np.load(S/('PREDICTIONS_'+arch+'.npz'))
 for kind in ['Mean','KRR','ExtraTrees']:
  cp=np.array([pr[kind+'_C_hat'][foldfor[ids[i]],i] for i in vi]);pp=np.array([pr[kind+'_P_scale'][foldfor[ids[i]],i] for i in vi]);hh=H.reconstruct_h2(cp,pp,H.load_h2_decoder());out[arch+'_'+kind]={'TM_magnitude_MAE':float(abs(abs(cp[:,:,:,1])-abs(ch[vi,:,:,1])).mean()),'routing_each_order_MAE':np.mean(abs(hh['eta']-h['eta'][vi]),axis=(0,1)),'truth_magnitude_between_geometry_variance':float(np.var(abs(ch[vi,:,:,1]),axis=0).mean()),'pred_magnitude_between_geometry_variance':float(np.var(abs(cp[:,:,:,1]),axis=0).mean()),'pred_weighted_norm_mean':float(np.sqrt(np.sum(base['cos_weights'][None,:,:,None]*abs(cp)**2,axis=(2,3))).mean())}
baseline=[]
for f in folds:
 tr=np.array([ids.index(v) for v in f['train_ids']]);held=next(g['heldout_old_ids'] for g in old if g['fold']==f['fold']);va=np.array([ids.index(v) for v in held]);baseline.append({'fold':f['fold'],'Pplus_MAE':float(abs(h['absolute_order'][va,:,4]-h['absolute_order'][tr,:,4].mean(0)).mean()),'eta_MAE':float(abs(h['eta'][va,:,4]-h['eta'][tr,:,4].mean(0)).mean()),'Pscale_MAE':float(abs(ps[va]-ps[tr].mean(0)).mean()),'count':len(va)})
put(S/'TM_ROUTING_VARIANCE_DIAGNOSTICS.json',out);put(S/'OUTPUT_DOMAIN_MEAN_REFERENCE.json',{'reference_only_not_formal_surrogate':True,'folds':baseline,'Pplus_MAE':sum(v['count']*v['Pplus_MAE'] for v in baseline)/124})
put(S/'STAGE_EVALUATION_COMPLETE.json',{'stage':stage,'total':N,'same124':True,'family_purged':True,'old222trainsets_unchanged':True,'new_solver_calls_by_evaluation':0,'model_target':'complex609D, never direct power','training_tasks':40,'old_models_refit':0});print('STAGE_COMPLETE',stage,N)
