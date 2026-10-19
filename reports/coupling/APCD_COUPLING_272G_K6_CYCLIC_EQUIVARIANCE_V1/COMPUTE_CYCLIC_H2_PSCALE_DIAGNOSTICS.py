from pathlib import Path
import sys, json, csv, hashlib, collections
import numpy as np

R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
O=R/'reports'/'coupling'/'APCD_COUPLING_272G_K6_CYCLIC_EQUIVARIANCE_V1'
D=R/'reports'/'coupling'/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1'/'STAGE_50'/'COMPLEX_DATASET.npz'
sys.path.insert(0,str(R))
from scripts.coupling_ml.k6_v2_pipeline.h1 import load_h2_decoder, reconstruct_h2

MODEL_FILES={
 'A_original':'CYCLIC_OOF_A_original.npz',
 'B_augmented':'CYCLIC_OOF_B_augmented.npz',
 'C_six_view':'CYCLIC_OOF_C_six_view.npz',
 'D_augmented_six_view':'CYCLIC_OOF_D_augmented_six_view.npz',
}
def write_csv(path, rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def load_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

dataset=np.load(D,allow_pickle=False)
case_ids=[str(x) for x in dataset['case_ids']]
di={x:i for i,x in enumerate(case_ids)}
fold_rows=load_csv(O/'CYCLIC_FOLD_IDENTITY_AUDIT.csv')
primary={};train_ids={}
for fold in ('1','2','3','4'):
    rr=[r for r in fold_rows if r['fold']==fold]
    primary[fold]=[r['case_id'] for r in rr if r['role']=='PRIMARY_VALIDATION']
    train_ids[fold]=[r['case_id'] for r in rr if r['role']=='TRAIN']
if len({c for f in primary for c in primary[f]})!=124: raise ValueError('primary validation identities do not total 124 unique cases')
if set(case_ids)!={r['case_id'] for r in fold_rows}: raise ValueError('fold identity table does not cover dataset')
decoder=load_h2_decoder()
h2_path=R/'scripts'/'shared_fdtd'/'tools'/'pw_complex_floquet_state_v1.py'
h2_sha=hashlib.sha256(h2_path.read_bytes()).hexdigest()

order_rows=[];ps_rows=[];parity={}; model_data={}
for model,file in MODEL_FILES.items():
    z=np.load(O/file,allow_pickle=False)
    pred_ids=[str(x) for x in z['case_ids']]
    if set(pred_ids)!=set(sum(primary.values(),[])) or len(pred_ids)!=124: raise ValueError('OOF IDs differ from fixed primary124 for '+model)
    pindex={cid:i for i,cid in enumerate(pred_ids)}
    seeds=[int(x) for x in z['seeds']]
    decoded_by_seed={}
    for si,seed in enumerate(seeds):
        decoded=reconstruct_h2(z['C'][si],z['P_scale'][si],decoder)
        eta_saved=np.asarray(z['eta'][si]);power_saved=np.asarray(z['absolute_order'][si])
        eta_err=float(np.max(np.abs(decoded['eta']-eta_saved)))
        power_err=float(np.max(np.abs(decoded['absolute_order']-power_saved)))
        if eta_err>1e-12 or power_err>1e-12: raise ValueError(f'frozen H2 parity failed {model} seed {seed}: {eta_err} {power_err}')
        parity[f'{model}_seed{seed}']={'eta_max_abs':eta_err,'absolute_order_max_abs':power_err}
        decoded_by_seed[seed]=decoded
    model_data[model]=(z,pindex,decoded_by_seed)

for model,(z,pindex,decoded_by_seed) in model_data.items():
    for fold in ('1','2','3','4'):
        ids=primary[fold]; idx=np.array([pindex[c] for c in ids],dtype=int); di_idx=np.array([di[c] for c in ids],dtype=int)
        tr=np.array([di[c] for c in train_ids[fold]],dtype=int)
        threshold=float(np.quantile(dataset['P_scale'][tr].reshape(-1),0.75))
        for si,seed in enumerate([int(x) for x in z['seeds']]):
            decoded=decoded_by_seed[seed]
            pred_eta=decoded['eta'][idx];pred_power=decoded['absolute_order'][idx]
            truth_eta=dataset['eta_H2'][di_idx];truth_power=dataset['absolute_H2'][di_idx]
            for oi,m in enumerate(dataset['orders'].tolist()):
                y=truth_eta[:,:,oi];p=pred_eta[:,:,oi];yp=truth_power[:,:,oi];pp=pred_power[:,:,oi]
                order_rows.append({'model':model,'fold':fold,'seed':seed,'order_m':int(m),
                    'eta_MAE':float(np.mean(np.abs(p-y))),'eta_bias':float(np.mean(p-y)),
                    'eta_truth_mean':float(np.mean(y)),'eta_pred_mean':float(np.mean(p)),
                    'absolute_order_power_MAE':float(np.mean(np.abs(pp-yp))),
                    'absolute_order_power_bias':float(np.mean(pp-yp)),
                    'truth_power_mean':float(np.mean(yp)),'pred_power_mean':float(np.mean(pp))})
            yps=dataset['P_scale'][di_idx]
            pps=z['P_scale'][si,idx]
            mask=yps>=threshold
            if not np.any(mask): raise ValueError('empty high-P_scale validation subset')
            err=pps-yps
            ps_rows.append({'model':model,'fold':fold,'seed':seed,'threshold_source':'training-fold P_scale q75',
                'train_q75_threshold':threshold,'n_validation_points':int(yps.size),
                'n_high_region_points':int(mask.sum()),'high_region_truth_mean':float(np.mean(yps[mask])),
                'high_region_prediction_mean':float(np.mean(pps[mask])),'high_region_MAE':float(np.mean(np.abs(err[mask]))),
                'high_region_bias_prediction_minus_truth':float(np.mean(err[mask])),
                'high_region_underprediction_fraction':float(np.mean(err[mask]<0)),
                'all_region_bias_prediction_minus_truth':float(np.mean(err))})

write_csv(O/'CYCLIC_H2_ORDER_METRICS.csv',order_rows)
write_csv(O/'CYCLIC_PSCALE_HIGH_REGION_DIAGNOSTICS.csv',ps_rows)
def means(rows,group,metrics):
    out={}
    for name in MODEL_FILES:
        rr=[r for r in rows if r['model']==name]
        out[name]={k:float(np.mean([r[k] for r in rr])) for k in metrics}
    return out
order_means={name:{int(m):{'eta_MAE':float(np.mean([r['eta_MAE'] for r in order_rows if r['model']==name and int(r['order_m'])==m])),
                         'power_MAE':float(np.mean([r['absolute_order_power_MAE'] for r in order_rows if r['model']==name and int(r['order_m'])==m]))}
                   for m in dataset['orders'].tolist()} for name in MODEL_FILES}
ps_means=means(ps_rows,None,['train_q75_threshold','n_high_region_points','high_region_truth_mean','high_region_prediction_mean','high_region_MAE','high_region_bias_prediction_minus_truth','high_region_underprediction_fraction'])
result={'schema':'K6_CYCLIC_FROZEN_H2_PSCALE_REGION_DIAGNOSTICS_V1','dataset_cases':len(case_ids),'primary_validation_cases':124,
 'folds':4,'seeds':[17,29,43],'new_fits':0,'solver_entries':0,'H2_module':str(h2_path),'H2_sha256':h2_sha,
 'frozen_H2_recomputation_parity':parity,'order_metric_rows':len(order_rows),'p_scale_region_rows':len(ps_rows),
 'order_metrics_mean_by_model_order':order_means,'p_scale_high_region_mean_by_model':ps_means,
 'high_region_definition':'Validation P_scale >= q75 of all training-fold P_scale values across training geometries and 21 wavelengths; threshold fitted on training fold only.',
 'interpretation_boundary':'All results are repeated development-fold diagnostics, not independent generalization evidence.'}
(O/'CYCLIC_H2_PSCALE_DIAGNOSTICS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'rows':{'order':len(order_rows),'p_scale':len(ps_rows)},'h2_sha256':h2_sha,'parity_max_abs':{'eta':max(x['eta_max_abs'] for x in parity.values()),'absolute_order':max(x['absolute_order_max_abs'] for x in parity.values())},'order_means':order_means,'p_scale_means':ps_means},ensure_ascii=False,indent=2))
