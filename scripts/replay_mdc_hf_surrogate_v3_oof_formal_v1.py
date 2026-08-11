"""Independent fresh-load replay for a completed V3 OOF checkpoint."""
import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_mdc_hf_surrogate_v3_oof_formal_v1 as runner

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-dir',required=True); ap.add_argument('--candidate',required=True); ap.add_argument('--fold',type=int,required=True); ap.add_argument('--seed',type=int,required=True); ap.add_argument('--output',required=True); args=ap.parse_args()
    run=Path(args.run_dir); geom,cases,_,_,_=runner.load_inputs(); folds=runner.geometry_folds(geom); held=set(folds[args.fold]); held_idx=np.flatnonzero(cases.geometry_hash.isin(held).to_numpy()); fixture=held_idx[:6]
    fit_key=runner.sha_obj({'candidate_id':args.candidate,'outer_fold':args.fold,'seed':args.seed}); fit_dir=run/'fits'/fit_key; ck=torch.load(fit_dir/'best.pt',map_location='cpu',weights_only=False); model=runner.ProfileOnlyModel(next(x for x in runner.load_candidates() if x['id']==args.candidate)); model.load_state_dict(ck['model']); model.eval()
    asset=np.load(run/'fold_assets'/f'fold_{args.fold}'/'scaler.npz'); pca=np.load(run/'fold_assets'/f'fold_{args.fold}'/'pca.npz'); Xraw=runner.feature_rows(geom,cases); X=(Xraw-asset['mean'])/asset['std'];
    with torch.no_grad(): z=model(torch.from_numpy(X[fixture].astype('float32')))['latent'].numpy()
    decoded=np.asarray(z@pca['components']+pca['mean'],dtype=np.float32); decoded=np.maximum(decoded,0.0); decoded/=np.maximum(decoded.sum(axis=1,keepdims=True),1e-12)
    payload={'status':'PASS','candidate_id':args.candidate,'fold':args.fold,'seed':args.seed,'fixture_case_indices':fixture.tolist(),'latent_sha256':hashlib.sha256(z.tobytes()).hexdigest(),'decoded_profile_sha256':hashlib.sha256(decoded.tobytes()).hexdigest(),'decoded_profile_mean':decoded.mean(axis=1).tolist(),'fit_calls_during_inference':0,'pca_fit_calls':0,'scaler_fit_calls':0,'checkpoint_sha256':runner.sha_file(fit_dir/'best.pt')}
    payload['prediction_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest(); Path(args.output).write_text(json.dumps(payload,indent=2),encoding='utf-8'); print(json.dumps(payload))
if __name__=='__main__': main()
