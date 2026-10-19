from pathlib import Path
import numpy as np,json
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';D=Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1/FORWARD';z=np.load(B/'COMPLEX_DATASET.npz');ids=list(z['case_ids']);folds=json.loads((B/'FOLDS.json').read_text());rows=[]
te=[4*k+j for k in range(7) for j in range(2)];tm=[4*k+2+j for k in range(7) for j in range(2)]
for f in folds:
 y=z['target29'][[ids.index(s) for s in f['train_ids']]].reshape(-1,29);v=y.var(axis=0);std=np.sqrt(v);ref=np.median(std[tm]);scale=np.ones(29);scale[tm]=ref/np.maximum(std[tm],.05);scale[28]=ref/max(std[28],.05);wv=v*scale**2
 rows.append({'fold':f['fold'],'raw_variance_fraction':{'TE':v[te].sum()/v.sum(),'TM':v[tm].sum()/v.sum(),'logP':v[28]/v.sum()},'balanced_variance_fraction':{'TE':wv[te].sum()/wv.sum(),'TM':wv[tm].sum()/wv.sum(),'logP':wv[28]/wv.sum()},'meaning':'training root-node output variance contribution to multi-output squared-error criterion; does not equal actual cumulative tree impurity reductions'})
(D/'TRAIN_FOLD_TARGET_VARIANCE.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
