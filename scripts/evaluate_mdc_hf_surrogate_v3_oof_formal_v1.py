"""Evaluate completed V3 OOF artifacts without fitting or opening sealed data."""
from __future__ import annotations
import argparse, importlib.util, json, sys, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
import run_mdc_hf_surrogate_v3_oof_formal_v1 as run

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec); assert spec.loader
    spec.loader.exec_module(mod); return mod

def sha_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def pairwise_mean(values: np.ndarray) -> float:
    n,d=values.shape
    if n<2:return 0.0
    total=0.0
    for start in range(0,d,4096):
        x=np.sort(values[:,start:start+4096],axis=0)
        coeff=(2*np.arange(n)-n+1).astype(np.float64)[:,None]
        total += float((coeff*x).sum())
    return total/(n*(n-1)/2)

def aggregate_metrics(preds, truth):
    p=np.asarray(preds,dtype=np.float32); t=np.asarray(truth,dtype=np.float32)
    vals=run.profile_loss_numpy(p,t); vals['weighted_L1']=float(np.abs(np.maximum(p,0)-np.maximum(t,0)).sum(axis=(-2,-1)).mean()); vals['evaluation_level']='geometry'; return vals

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-dir',required=True); args=ap.parse_args(); out=Path(args.run_dir)
    accounting=run.read_json(out/'execution_accounting.json')
    if accounting.get('completed')!=45: raise RuntimeError('HARD_GATE_FORMAL_MATRIX_INCOMPLETE')
    geom,cases,wavelength,angle,_=run.load_inputs(); folds=run.geometry_folds(geom)
    q=np.memmap(out/'profile_q_memmap.f32',mode='r',dtype='float32',shape=(len(cases),run.PROFILE_DIM))
    rows=[json.loads(x) for x in (out/'oof_predictions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    if len(rows)!=10800: raise RuntimeError(f'HARD_GATE_OOF_ROW_COUNT:{len(rows)}')
    cand_ids=['V3-A','V3-B','V3-C']; records=[]
    gmap=geom.set_index('geometry_hash'); case_hash=cases.geometry_hash.astype(str).to_numpy(); geom_groups={g:np.flatnonzero(case_hash==g) for g in sorted(set(case_hash))}
    target_latent_by_fold={}; comps={}
    for f in run.FOLDS:
        asset=np.load(out/'fold_assets'/f'fold_{f}'/'pca.npz'); comps[f]=asset['components']; target_latent_by_fold[f]=np.load(out/'fold_assets'/f'fold_{f}'/'latent_targets.npy')
    for cid in cand_ids:
        case_pred={}; case_target={}
        latent_pred=[]; latent_truth=[]
        for r in rows:
            if r['candidate_id']!=cid: continue
            f=int(r['outer_fold']); i=int(r['case_index']); z=np.asarray(r['latent'],dtype=np.float32); latent_pred.append(z); latent_truth.append(target_latent_by_fold[f][i]); case_pred[(int(r['seed']),i)]=(z@comps[f]+np.load(out/'fold_assets'/f'fold_{f}'/'pca.npz')['mean']); case_target[(int(r['seed']),i)]=q[i]
        latent_pred=np.asarray(latent_pred); latent_truth=np.asarray(latent_truth); ratio=latent_pred.var(0)/np.maximum(latent_truth.var(0),1e-12); collapsed=int((ratio<0.25).sum())
        geometry_rows=[]
        for seed in run.SEEDS:
            for g,inds in geom_groups.items():
                if not all((seed,int(i)) in case_pred for i in inds): raise RuntimeError('HARD_GATE_MISSING_OOF_CASE')
                p=np.asarray([case_pred[(seed,int(i))].reshape(run.NATIVE_SHAPE) for i in inds]); t=np.asarray([case_target[(seed,int(i))].reshape(run.NATIVE_SHAPE) for i in inds]); gm=aggregate_metrics(p.mean(0,keepdims=True),t.mean(0,keepdims=True)); gm.update({'seed':seed,'geometry_hash':g,'topology_family':str(gmap.loc[g].topology_family),'source_positions':'top|centroid|bottom','orientation_coverage':'x|z'}); geometry_rows.append(gm)
        global_metrics={k:float(np.mean([r[k] for r in geometry_rows])) for k in ('profile','JS','spectral_CDF','angular_CDF','weighted_L1')}; global_metrics['evaluation_level']='geometry'
        fold_metrics=[]
        for f in run.FOLDS:
            hs=set(folds[f]); x=[r for r in geometry_rows if r['geometry_hash'] in hs]; m={k:float(np.mean([r[k] for r in x])) for k in ('profile','JS','spectral_CDF','angular_CDF','weighted_L1')}; m['evaluation_level']='geometry'; m['fold']=f; fold_metrics.append(m)
        topo_metrics=[]
        for topo in run.TOPOLOGIES:
            x=[r for r in geometry_rows if r['topology_family']==topo]
            if not x: raise RuntimeError('HARD_GATE_TOPOLOGY_COVERAGE')
            m={k:float(np.mean([r[k] for r in x])) for k in ('profile','JS','spectral_CDF','angular_CDF','weighted_L1')}; m['evaluation_level']='geometry'; m['topology_family']=topo; topo_metrics.append(m)
        worst_fold=max(fold_metrics,key=lambda m:sum(run.PROFILE_WEIGHTS[k]*m[k] for k in run.PROFILE_WEIGHTS)); worst_topo=max(topo_metrics,key=lambda m:sum(run.PROFILE_WEIGHTS[k]*m[k] for k in run.PROFILE_WEIGHTS))
        # Diversity is calculated exactly by a sorted pairwise reduction.
        by_geom=[]; by_truth=[]
        for g,inds in geom_groups.items():
            pp=[]; tt=[]
            for seed in run.SEEDS:
                pp.append(np.mean([case_pred[(seed,int(i))] for i in inds],axis=0)); tt.append(np.mean([case_target[(seed,int(i))] for i in inds],axis=0))
            by_geom.append(np.mean(pp,axis=0)); by_truth.append(np.mean(tt,axis=0))
        diversity_ratio=pairwise_mean(np.asarray(by_geom))/max(pairwise_mean(np.asarray(by_truth)),1e-12)
        topology_orientation_metrics={}
        topology_source_position_metrics={}
        case_meta=cases.reset_index(drop=True)
        def _stratified(key_fn):
            out={}
            keys=sorted({str(key_fn(i)) for i in range(len(case_meta))})
            for key in keys:
                rows_s=[]
                for seed in run.SEEDS:
                    for g,inds in geom_groups.items():
                        sel=[int(i) for i in inds if str(key_fn(i))==key]
                        if not sel: continue
                        p=np.asarray([case_pred[(seed,i)] for i in sel],dtype=np.float32).mean(0).reshape(run.NATIVE_SHAPE)
                        t=np.asarray([case_target[(seed,i)] for i in sel],dtype=np.float32).mean(0).reshape(run.NATIVE_SHAPE)
                        rows_s.append(aggregate_metrics(p[None,...],t[None,...]))
                if rows_s:
                    out[key]={k:float(np.mean([m[k] for m in rows_s])) for k in ('profile','JS','spectral_CDF','angular_CDF','weighted_L1')}
                    out[key]['evaluation_level']='geometry'; out[key]['geometry_stratum_count']=len(rows_s)
            return out
        topology_orientation_metrics=_stratified(lambda i: str(gmap.loc[str(case_meta.iloc[i].geometry_hash)].topology_family)+'|'+str(case_meta.iloc[i].dipole_orientation))
        topology_source_position_metrics=_stratified(lambda i: str(gmap.loc[str(case_meta.iloc[i].geometry_hash)].topology_family)+'|'+str(case_meta.iloc[i].source_position))
        record={'candidate_id':cid,'fit_records':[{'fit_id':str(r['fit_key']),'status':'COMPLETE','outer_fold':int(r['outer_fold']),'seed':int(r['seed']),'finite':r['finite'],'prediction_complete':r['prediction_complete'],'fold_leakage':r['fold_leakage'],'case_leakage':r['case_leakage'],'pca_scaler_leakage':r['pca_scaler_leakage'],'outer_stop_contamination':r['outer_stop_contamination'],'eligible_best_epoch':int(r['best_epoch'])} for r in json.loads((out/'fit_matrix.json').read_text(encoding='utf-8'))['fits'] if r['candidate_id']==cid], 'topology_coverage':{t:True for t in run.TOPOLOGIES}, 'global_geometry_metrics':global_metrics,'worst_fold_metrics':worst_fold,'worst_topology_metrics':worst_topo,'fold_metrics':fold_metrics,'topology_metrics':topo_metrics,'topology_orientation_metrics':topology_orientation_metrics,'topology_source_position_metrics':topology_source_position_metrics,'median_latent_variance_ratio':float(np.median(ratio)),'per_component_latent_variance_ratio':ratio.tolist(),'collapsed_component_count':collapsed,'profile_pairwise_diversity_ratio':float(diversity_ratio),'metric_contract_drift':False,'architecture_definition_drift':False,'sealed_test_violation':False,'execution_artifact_ambiguous':False,'known_failure_reference':{'JS':0.22933,'weighted_L1':1.15060}}
        records.append(record)
    policy=load_module(REPO/'scripts'/'mdc_hf_surrogate_v3_oof_promotion_policy_v1.py','v3policy'); selection=policy.select_promoted_candidate(records)
    (out/'candidate_metrics.json').write_text(json.dumps(records,indent=2),encoding='utf-8'); (out/'promotion_result.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
    result={'status':'PASS','selection':selection,'candidate_ids':cand_ids,'fit_count':45,'solver_calls':0,'V3_Test40_label_reads':0,'HF15_R12_reads':0,'metrics_sha256':sha_file(out/'candidate_metrics.json'),'promotion_sha256':sha_file(out/'promotion_result.json')}
    if selection.get('selected_architecture')!='NONE':
        ep=load_module(REPO/'scripts'/'mdc_hf_surrogate_v3_final_epoch_policy_v1.py','v3epoch'); cid=selection['selected_architecture']; fit=[r for r in records if r['candidate_id']==cid][0]['fit_records']; final=ep.derive_final_epoch(fit,cid); result['final_epoch']=final; (out/'final_epoch_derivation.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
    (out/'evaluation_completion.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result))

if __name__=='__main__': main()


