from pathlib import Path
import csv,json,collections,subprocess
import numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
Q=R/'reports'/'coupling';O=Q/'APCD_COUPLING_272G_K6_CYCLIC_EQUIVARIANCE_V1'
rd=lambda n:json.loads((O/n).read_text(encoding='utf-8-sig'))
def readcsv(p):
 with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(p,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def writejson(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def fmt(x,n=4):return f'{float(x):.{n}f}'
audit=rd('CYCLIC_EQUIVALENCE_AND_LEAKAGE_AUDIT.json');test=rd('CYCLIC_LABEL_TRANSFORM_TESTS.json');summary=rd('CYCLIC_MODEL_SUMMARY.json');h1=rd('CYCLIC_H1_GATE_RESULTS.json');config=rd('CYCLIC_MODEL_CONFIG.json')
h1seed=rd('CYCLIC_H1_PER_SEED_GATE_RESULTS.json')
foldsrc=Q/'APCD_COUPLING_272G_DATA_LEAKAGE_AUDIT_V1'/'CV_SPLIT_IDENTITY_CHECK.csv'
foldrows=[r for r in readcsv(foldsrc) if r['record_type']=='GEOMETRY']
data=np.load(Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1'/'STAGE_50'/'COMPLEX_DATASET.npz',allow_pickle=False)
ids=[str(x) for x in data['case_ids'].tolist()];D=np.asarray(data['D_nm'],int)
def canon(d):return min(tuple(np.roll(d,k).tolist()) for k in range(6))
def self_size(d):return len({tuple(np.roll(d,k).tolist()) for k in range(6)})
cycle={cid:canon(D[i]) for i,cid in enumerate(ids)};orbit_counts=collections.Counter(cycle.values())
role_summary={};out_fold=[]
for fi in range(1,5):
 rs=[r for r in foldrows if int(r['fold'])==fi];role_summary[str(fi)]=dict(collections.Counter(r['split_role'] for r in rs))
 train=[r for r in rs if r['split_role']=='TRAIN'];val=[r for r in rs if r['split_role']=='PRIMARY_VALIDATION']
 train_ids={r['case_id'] for r in train};val_ids={r['case_id'] for r in val}
 famcross=sorted({r['family_id'] for r in train}&{r['family_id'] for r in val})
 cyc_train={cycle[r['case_id']] for r in train};cyc_val={cycle[r['case_id']] for r in val};cyccross=sorted(cyc_train&cyc_val)
 famcross_set=set(famcross);cyccross_set=set(cyccross)
 # annotate every geometry row, retaining all original split identities and labels.
 for r in rs:
  cid=r['case_id'];dv=[r[f'D{i}_nm'] for i in range(1,7)]
  out_fold.append({'fold':fi,'role':r['split_role'],'case_id':cid,'family_id':r['family_id'],
   'D1_nm':r['D1_nm'],'D2_nm':r['D2_nm'],'D3_nm':r['D3_nm'],'D4_nm':r['D4_nm'],'D5_nm':r['D5_nm'],'D6_nm':r['D6_nm'],
   'wavelength_count':r['wavelength_count'],'all_wavelengths_grouped':str(r['wavelength_count'])=='21',
   'canonical_cycle_D':';'.join(map(str,cycle[cid])),'self_rotation_unique_views':self_size(D[ids.index(cid)]),
   'family_train_validation_cross':r['family_id'] in famcross_set,
   'cycle_train_validation_cross':cycle[cid] in cyccross_set})
 role_summary[str(fi)]['train_validation_case_overlap']=len(train_ids&val_ids)
 role_summary[str(fi)]['train_validation_family_overlap']=len(famcross)
 role_summary[str(fi)]['train_validation_cycle_orbit_overlap']=len(cyccross)
 role_summary[str(fi)]['train_ids']=sorted(train_ids);role_summary[str(fi)]['validation_ids']=sorted(val_ids)
 role_summary[str(fi)]['train_families']=sorted({r['family_id'] for r in train});role_summary[str(fi)]['validation_families']=sorted({r['family_id'] for r in val})
writecsv(O/'CYCLIC_FOLD_IDENTITY_AUDIT.csv',out_fold)

# Add fold-mean and seed-mean rows to the requested headline comparison CSV.
metric_rows=[r for r in readcsv(O/'CYCLIC_AUGMENTATION_MODEL_COMPARISON.csv') if r.get('fold') not in ('FOUR_FOLD_MEAN','MEAN_4FOLD_3SEED')]
metric_names=['complex_NRMSE','complex_MAE','real_MAE','imag_MAE','TE_complex_NRMSE','TM_complex_NRMSE','TM_magnitude_MAE','TM_strong_q75_train_magnitude_MAE','routing_MAE_all7','relative_phase_weighted_deg','P_scale_MAE','P_scale_RMSE','P_scale_bias','eta_plus_MAE','Pplus_MAE','Pplus_RMSE','rho450','Top20_recall450']
model_labels={'A_original':'A_original_NN3','B_augmented':'B_cycle_augmented_NN3','C_six_view':'C_six_view_inference','D_augmented_six_view':'D_augmentation_plus_ensemble'}
aggregate_rows=[]
for model,seeds in summary.items():
 for seed in ('17','29','43'):
  m=seeds[seed]['fold_mean'];p=seeds[seed]['oof_pooled']
  aggregate_rows.append({'model':model_labels[model],'fold':'FOUR_FOLD_MEAN','seed':seed,'n_geometry':124,**m,**{'OOF_'+k:v for k,v in p.items()}})
 vals=[seeds[s]['fold_mean'] for s in ('17','29','43')];pooled=[seeds[s]['oof_pooled'] for s in ('17','29','43')]
 aggregate_rows.append({'model':model_labels[model],'fold':'MEAN_4FOLD_3SEED','seed':'17|29|43','n_geometry':124,
  **{k:float(np.mean([x[k] for x in vals])) for k in metric_names},
  **{'OOF_'+k:float(np.mean([x[k] for x in pooled])) for k in pooled[0]}})
writecsv(O/'CYCLIC_AUGMENTATION_MODEL_SUMMARY.csv',aggregate_rows)
writecsv(O/'CYCLIC_AUGMENTATION_MODEL_COMPARISON.csv',metric_rows+aggregate_rows)

fold_md=[]
for fi in range(1,5):
 x=role_summary[str(fi)];fold_md.append(f"| {fi} | {x.get('TRAIN',0)} | {x.get('PRIMARY_VALIDATION',0)} | {x.get('PURGED',0)} | {x.get('OTHER_HELDOUT',0)} | {x['train_validation_family_overlap']} | {x['train_validation_cycle_orbit_overlap']} |")
contract=f'''# K6 cyclic symmetry contract

Status: **PASS for the ideal, periodic K6 label transform used in this zero-solver study.** This is an algebraic and code-path validation; no independent rotated-geometry FDTD pair exists in the 272G table, so it is not a new physical-solver parity claim.

## Geometry action

The frozen builder places ordered `D1…D6` at ascending x centers `[-725,-435,-145,145,435,725] nm` in a `1740 nm` x-periodic cell. The generator's `T(D)=roll(D,+1)=[D6,D1,D2,D3,D4,D5]` moves each pillar center by `+290 nm` modulo `1740 nm`. Thus `T^6(D)=D`. It preserves pillar order around the periodic cell, x/y axes, normal incidence, and TE/TM channel labels; it is a translation, not a mirror, reversal, or 60-degree physical rotation. The exact 5 nm mesh divides both the shift (58 cells) and the superperiod (348 cells).

Implementation evidence: `scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py`, `pillar_centers_nm` lines 51–52, periodic x/y boundaries lines 158–162, and ordered `NP_D1…NP_D6` construction lines 171–174. The frozen full-cell contract retains the 290 nm pitch and 1740 nm x period.

## 609D complex-state action

The production projector uses the negative Fourier kernel `exp(-i G_m x)` (`scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py`, line 230). Translating a field by `+k·290 nm` therefore gives:

`C_hat(T^k D)[λ,m,pol] = C_hat(D)[λ,m,pol] · exp(-i·2π·m·k/6)` for `m=-3,…,+3`.

Both TE and TM receive the same order-dependent phase. `m=0` is unchanged. Complex magnitudes are unchanged for every order and polarization. `P_scale` is unchanged because the incident normal-incidence reference and global phase gauge are unchanged under lateral translation. No independent channel phase rotation, magnitude normalization, or label modification is applied.

The frozen H2 decoder (`scripts/coupling_ml/k6_v2_pipeline/h1.py`, lines 41–53) constructs modal power from fixed TE/TM modal weights times `abs(C_hat)**2`, normalizes across the seven orders, and multiplies by `P_scale`. It is therefore invariant under this phase action. The decoder identity used in this study is `{test['h2_identity']['expected_sha256']}`; the H1 authority identity is `{h1['D_augmented_six_view']['h1_gate_sha256']}`.

## Authorized use in this experiment

1. **Training augmentation:** for training-only unique rotations `D_k=roll(D,k)`, transform the complex target by the formula above and keep `P_scale` unchanged. All 21 wavelengths of a geometry remain together. Deduplicate identical views within each geometry before expansion.
2. **Six-view inference:** evaluate all six rotated inputs, multiply each predicted complex response back by `exp(+i·2π·m·k/6)`, and take the arithmetic mean of aligned complex responses; average positive-domain `P_scale` predictions arithmetically.
3. **H2 decoding:** decode the final aligned response with the existing frozen H2. The symmetry transform does not change the H2 definition or any truth label.

The 272G table contains 272 distinct canonical cyclic orbits, and each checked training geometry has six distinct rotations. Synthetic rotations are training views, not additional physical geometries or FDTD labels.

## Scope boundary

This contract applies to the normal-incidence, x-periodic, ordered six-pillar supercell and its frozen global incident-phase gauge. It does not authorize reordering labels arbitrarily, reversing the sequence, changing the period or reference plane, or treating symmetry-generated copies as independently measured truth. FAST data remain `ML_TRAINING_GRADE`; H1 remains a development-only gate and final generalization remains uncertified.
'''
(O/'K6_CYCLIC_SYMMETRY_CONTRACT.md').write_text(contract,encoding='utf-8')

proj=test['tests']['production_projector_sign'];h2=test['tests']['frozen_h2_all_272G_21lambda_TE_TM'];ran=test['tests']['random_21lambda_7orders_TE_TM']
tests_md=f'''# Cyclic label-transform tests

All checks were run against the frozen production projector and frozen H2 decoder on the existing 272G dataset. They are zero-solver numerical/software tests; no FDTD, Runner, sealed data, or ledger write was used.

| Test | Result | Evidence |
|---|---|---|
| `T^6(D)=D` geometry identity | PASS | exact max diameter difference {test['tests']['geometry_six_cycle']['max_abs_nm']} nm |
| stabilizer-aware view deduplication | PASS | 1-, 2-, 3-, and 6-period test vectors yield 1, 2, 3, and 6 unique views |
| complex `T^6` for 21 λ × 7 orders × TE/TM | PASS | max abs {ran['complex_six_cycle']['max_abs']:.3e}; relative L2 {ran['complex_six_cycle']['relative_l2']:.3e} |
| magnitude invariance / zero-order phase | PASS | max magnitude error {ran['magnitude_max_abs']:.3e}; zero-order max complex error {ran['zero_order_max_abs']:.3e} |
| production Fourier-projector sign | PASS | six shifts, max abs {proj['max_abs']:.3e}; max relative L2 {proj['max_relative_l2']:.3e} |
| frozen H2 invariance over 272 × 21 × 7 × 2 | PASS | η max error {max(x['eta']['max_abs'] for x in h2['per_k'].values()):.3e}; absolute order max error {max(x['absolute_order']['max_abs'] for x in h2['per_k'].values()):.3e}; P_scale exact |

The randomized algebra check includes all wavelengths 440–460 nm, all seven orders `m=-3…+3`, and both polarizations. The synthetic projector fixture uses the same projection function as the production 609D extractor; it verifies the sign convention, not the electromagnetic accuracy of a fabricated field.

Reproduction code: `test_cyclic_label_transform.py`. Machine-readable results: `CYCLIC_LABEL_TRANSFORM_TESTS.json`. H2 decoder expected identity: `{test['h2_identity']['expected_sha256']}`.
'''
(O/'CYCLIC_LABEL_TRANSFORM_TESTS.md').write_text(tests_md,encoding='utf-8')

leak_md='''# Cyclic equivalence and validation leakage audit

## Data and cyclic equivalence

The source is the existing `STAGE_50/COMPLEX_DATASET.npz`, backed by its `FAST_DATASET_MANIFEST.json`: 222G historical FAST data plus 50 labels-valid AL50 cases, total 272 distinct case IDs; validation124 and old 222G training identities are recorded unchanged, and the manifest states no sealed access. All 272 ordered six-diameter vectors are unique. Canonicalization by the lexicographically minimum of the six cyclic rolls yields 272 orbit classes, each containing one observed case. Therefore there are **zero real-data rotated duplicate pairs** to compare phase-aligned complex labels against; native-response parity for a matched rotated pair is NOT MEASURED. The exact transformation is tested algebraically and against the production projector separately.

## Fixed four-fold identity audit

The audit reuses the established family-guarded 124-development geometry split. Full row-level identities, ordered diameters, family IDs, all-21-wavelength grouping, canonical cyclic key, and fold-role overlaps are in `CYCLIC_FOLD_IDENTITY_AUDIT.csv`. Role counts below come from the prior frozen `CV_SPLIT_IDENTITY_CHECK.csv` geometry rows.

| Fold | Train | Primary validation | Purged | Other held out | Train/validation family overlap | Train/validation cyclic-orbit overlap |
|---:|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(fold_md)+'''

For every fold, case IDs are disjoint between train and primary validation; family overlap is zero; cyclic-orbit overlap is zero; every geometry carries all 21 wavelengths in a single role. No cyclic leakage was found, so the validation manifest was not regenerated. Counts marked `PURGED` and `OTHER_HELDOUT` preserve the existing audit roles rather than being reclassified.

## Limits

No validation geometry or family was moved. The 124 geometries have been repeatedly used in development/model selection, so all new metrics remain **DEVELOPMENT EVIDENCE**, not final generalization certification. The separate sealed confirmation remains untouched. Synthetic augmented rotations are generated only from training labels inside each fold; validation rotations are used only for inference diagnostics.
'''
(O/'CYCLIC_EQUIVALENCE_AND_LEAKAGE_AUDIT.md').write_text(leak_md,encoding='utf-8')

# Human-readable four-way model comparison and paired fold-seed evidence.
cols=[('complex_NRMSE','609D complex NRMSE ↓'),('TM_magnitude_MAE','TM magnitude MAE ↓'),('routing_MAE_all7','Routing MAE ↓'),('relative_phase_weighted_deg','relative phase (deg) ↓'),('P_scale_MAE','P_scale MAE ↓'),('eta_plus_MAE','η(+1) MAE ↓'),('Pplus_MAE','P(+1) MAE ↓'),('rho450','450 nm Spearman ↑'),('Top20_recall450','Top20 recall ↑')]
labels={'A_original':'A · 原始 NN3','B_augmented':'B · 训练循环增强','C_six_view':'C · 六视图推理集成','D_augmented_six_view':'D · 增强 + 六视图集成'}
metric_md='| Model | '+' | '.join(v for _,v in cols)+' |\n|---|'+'|'.join(['---:']*len(cols))+'|\n'
for model in ('A_original','B_augmented','C_six_view','D_augmented_six_view'):
 values=[]
 for key,_ in cols:
  ss=[summary[model][s]['fold_mean'][key] for s in ('17','29','43')]
  values.append(fmt(np.mean(ss),4))
 metric_md+='| '+labels[model]+' | '+' | '.join(values)+' |\n'
pair=readcsv(O/'CYCLIC_PAIRED_DELTAS.csv');pairlines=[]
for contrast in ('B_minus_A','D_minus_C'):
 q=[r for r in pair if r['contrast']==contrast]
 wins={key:sum(float(r['delta_'+key])<0 if key not in ('rho450','Top20_recall450') else float(r['delta_'+key])>0 for r in q) for key,_ in cols}
 deltas={key:float(np.mean([float(r['delta_'+key]) for r in q])) for key,_ in cols}
 pairlines.append(f"- `{contrast}`：12 个 fold-seed 配对中，complex NRMSE {wins['complex_NRMSE']}/12 改善，P(+1) MAE {wins['Pplus_MAE']}/12 改善，η(+1) MAE {wins['eta_plus_MAE']}/12 改善；Spearman 改善 {wins['rho450']}/12、Top20 改善 {wins['Top20_recall450']}/12。配对平均差：complex NRMSE {deltas['complex_NRMSE']:+.4f}，P(+1) MAE {deltas['Pplus_MAE']:+.4f}，Spearman {deltas['rho450']:+.4f}。")
eq=readcsv(O/'CYCLIC_EQUIVARIANCE_DIAGNOSTICS.csv');eqstats={}
for model in ('A_original','B_augmented','C_six_view','D_augmented_six_view'):
 q=[r for r in eq if r['model']==model];eqstats[model]={'mean':float(np.mean([float(x['complex_equivariance_relative_l2_mean_k1_5']) for x in q])),'max':max(float(x['complex_equivariance_relative_l2_max_k1_5']) for x in q),'pmax':max(float(x['P_scale_rotation_relative_l2_max_k1_5']) for x in q)}
fit=json.loads((O/'CYCLIC_RUN_COMPLETE.json').read_text(encoding='utf-8-sig'))
gates=[]
for model in ('A_original','B_augmented','C_six_view','D_augmented_six_view'):
 v=h1[model];gates.append(f"| {labels[model]} | {v['gates'].get('state')} | {v['gates'].get('routing')} | {v['gates'].get('absolute_order')} | {v['gates'].get('thresholded_absolute_order')} | {v['gates'].get('total_power')} | **{v['production_admission']}** |")
diag=f'''# Cyclic equivariance and model diagnostics

## Main comparison

Means below are the arithmetic mean of the four fixed-fold metrics and three seeds, on the same 124 development geometries. Lower is better except ranking metrics. Full fold × seed rows are in `CYCLIC_AUGMENTATION_MODEL_COMPARISON.csv`; the per-order/per-polarization breakdown is `CYCLIC_ORDER_POLARIZATION_METRICS.csv`.

{metric_md}

The B training augmentation improved all 12 paired fold-seed results for complex NRMSE, TM magnitude MAE, routing MAE, weighted relative phase, P_scale MAE, η(+1) MAE, P(+1) MAE and 450 nm Spearman. Top20 recall improved in 4/12 paired runs although its fold/seed mean increased. D vs C improved every paired fold-seed loss metric; ranking improved in 9/12 runs and Top20 in 4/12, while both mean ranking metrics increased.

{chr(10).join(pairlines)}

## Equivariance residuals

Raw model equivariance residual is relative L2 across k=1…5, computed on the same validation geometries. Group-averaged C/D satisfy equivariance to floating precision by construction.

| Model | Mean raw complex residual | Max complex residual | Max P_scale rotation residual |
|---|---:|---:|---:|
| A raw NN3 | {eqstats['A_original']['mean']:.4f} | {eqstats['A_original']['max']:.4f} | {eqstats['A_original']['pmax']:.4f} |
| B raw augmented NN3 | {eqstats['B_augmented']['mean']:.4f} | {eqstats['B_augmented']['max']:.4f} | {eqstats['B_augmented']['pmax']:.4f} |
| C six-view group average | {eqstats['C_six_view']['mean']:.3e} | {eqstats['C_six_view']['max']:.3e} | {eqstats['C_six_view']['pmax']:.3e} |
| D augmented + group average | {eqstats['D_augmented_six_view']['mean']:.3e} | {eqstats['D_augmented_six_view']['max']:.3e} | {eqstats['D_augmented_six_view']['pmax']:.3e} |

Training augmentation alone did not reduce the raw network's complex equivariance residual in this fixed-budget fit; it did reduce predicted P_scale's rotation residual. Six-view inference projects the prediction onto the group-equivariant output by construction and reduces both residuals to numerical precision. D had the best mean complex and H2-target metrics, but requires both augmentation training and sixfold forward inference.

## Training and H1

New fits: {fit['new_augmented_fits']} independent augmented NN3 fits (4 folds × 3 seeds), {fit['elapsed_fit_seconds']:.1f} s total; 300 epochs each. All emitted the expected sklearn max-iteration convergence warning. No extra epochs or best-seed selection were used. A/C reused the previously saved original NN3 checkpoints, whose recomputed predictions matched saved validation predictions exactly (`max |ΔC|=0`, `max |ΔP|=0`).

| Model | State | Routing | Absolute order | Thresholded order | Total power | H1 production admission |
|---|---|---|---|---|---|---|
'''+ '\n'.join(gates)+'''

Every candidate has `production_admission=false`; H1 remains **HOLD**. B and D clear the state gate, but routing, thresholded absolute order, and total power gates remain failed. These results are still development evidence only; the 124 development cases are not an independent final test.

The per-seed frozen-H1 replay is in `CYCLIC_H1_PER_SEED_GATE_RESULTS.json`: the same gate pattern holds across all three seeds for each of A–D, and production admission is false for all 12 model/seed combinations.
'''
(O/'CYCLIC_EQUIVARIANCE_DIAGNOSTICS.md').write_text(diag,encoding='utf-8')

decision=f'''# Forward-model scientific decision

## Decision

The K6 cyclic transform is supported by the frozen periodic geometry, production Fourier convention, and H2 invariance tests. On the fixed 124-geometry development folds, six-cycle training augmentation improved the 29D NN3 baseline, and six-view inference further improved the augmented model. The best development candidate is **D: train-only cyclic augmentation plus six-view inference ensemble**.

| Measure (four-fold × three-seed mean) | A original | D augmented + ensemble | Change |
|---|---:|---:|---:|
| 609D complex NRMSE | {np.mean([summary['A_original'][s]['fold_mean']['complex_NRMSE'] for s in ('17','29','43')]):.4f} | {np.mean([summary['D_augmented_six_view'][s]['fold_mean']['complex_NRMSE'] for s in ('17','29','43')]):.4f} | lower is better |
| TM magnitude MAE | {np.mean([summary['A_original'][s]['fold_mean']['TM_magnitude_MAE'] for s in ('17','29','43')]):.4f} | {np.mean([summary['D_augmented_six_view'][s]['fold_mean']['TM_magnitude_MAE'] for s in ('17','29','43')]):.4f} | lower is better |
| routing MAE | {np.mean([summary['A_original'][s]['fold_mean']['routing_MAE_all7'] for s in ('17','29','43')]):.4f} | {np.mean([summary['D_augmented_six_view'][s]['fold_mean']['routing_MAE_all7'] for s in ('17','29','43')]):.4f} | lower is better |
| P_scale MAE | {np.mean([summary['A_original'][s]['fold_mean']['P_scale_MAE'] for s in ('17','29','43')]):.4f} | {np.mean([summary['D_augmented_six_view'][s]['fold_mean']['P_scale_MAE'] for s in ('17','29','43')]):.4f} | lower is better |
| η(+1) MAE | {np.mean([summary['A_original'][s]['fold_mean']['eta_plus_MAE'] for s in ('17','29','43')]):.4f} | {np.mean([summary['D_augmented_six_view'][s]['fold_mean']['eta_plus_MAE'] for s in ('17','29','43')]):.4f} | lower is better |
| P(+1) MAE | {np.mean([summary['A_original'][s]['fold_mean']['Pplus_MAE'] for s in ('17','29','43')]):.4f} | {np.mean([summary['D_augmented_six_view'][s]['fold_mean']['Pplus_MAE'] for s in ('17','29','43')]):.4f} | lower is better |
| 450 nm Spearman | {np.mean([summary['A_original'][s]['fold_mean']['rho450'] for s in ('17','29','43')]):.4f} | {np.mean([summary['D_augmented_six_view'][s]['fold_mean']['rho450'] for s in ('17','29','43')]):.4f} | higher is better |
| Top20 recall | {np.mean([summary['A_original'][s]['fold_mean']['Top20_recall450'] for s in ('17','29','43')]):.4f} | {np.mean([summary['D_augmented_six_view'][s]['fold_mean']['Top20_recall450'] for s in ('17','29','43')]):.4f} | higher is better |

## Limits and recommendation

- H1 remains **HOLD**. All four variants fail at least routing, thresholded order, and total-power frozen gates; no candidate has production admission.
- The 124 validation geometries are repeatedly used development cases. This experiment cannot certify unknown-K6 final generalization or authorize production inverse design.
- Fixed 300-epoch fits reached the iteration ceiling and emitted convergence warnings; improvements are conditional on this budget and are not evidence of an optimized NN architecture.
- The 272G dataset remains unchanged; symmetry views are synthetic training examples, not new physical truth. No independent FDTD label pair exists for rotated twins.
- Six-view inference uses six model passes; whether that runtime is acceptable for future acquisition needs a separate deployment measurement.

Recommended next development step: keep D as a candidate under the same grouped folds, preserve the four-way ablation, and seek an independent confirmation set through the existing authorization process. Do not change H1 thresholds, access sealed data, launch a new batch, or declare final model readiness from this development result.

Boundary: `NEW_FDTD=0`, `NEXT_BATCH_AUTHORIZED=0`, `DIAG2=1/2`, `A2=HOLD`, `DOE56=HOLD`, `CVAE=PAUSED`.
'''
(O/'FORWARD_MODEL_SCIENTIFIC_DECISION.md').write_text(decision,encoding='utf-8')

# Reproducible diagnostic figures; training loss curves are shown within model only
# because train-only StandardScaler targets differ under augmentation.
figure_status=[]
try:
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 curve=readcsv(O/'CYCLIC_TRAINING_CURVES.csv')
 fig,axs=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
 for ax,model,title in zip(axs,('A_original','B_augmented'),('A · original NN3','B · cyclic-augmented NN3')):
  rr=[r for r in curve if r['model']==model]
  by=collections.defaultdict(list)
  for r in rr:by[int(r['epoch'])].append(float(r['training_loss']))
  ep=sorted(by);med=np.array([np.median(by[e]) for e in ep]);lo=np.array([np.quantile(by[e],.25) for e in ep]);hi=np.array([np.quantile(by[e],.75) for e in ep])
  ax.plot(ep,med,color='#146C94',lw=2);ax.fill_between(ep,lo,hi,color='#146C94',alpha=.18);ax.set_title(title);ax.set_xlabel('Epoch');ax.set_ylabel('Training loss (fold/seed median; IQR)');ax.grid(alpha=.2)
 fig.suptitle('Fixed 300-epoch training curves; targets scaled within each training fold')
 fig.savefig(O/'CYCLIC_TRAINING_LOSS.png',dpi=180);plt.close(fig);figure_status.append('CYCLIC_TRAINING_LOSS.png:PASS')
 fig,axs=plt.subplots(2,2,figsize=(9,7),constrained_layout=True)
 plotmetrics=[('complex_NRMSE','609D complex NRMSE'),('Pplus_MAE','P(+1) MAE'),('rho450','450 nm Spearman'),('Top20_recall450','Top20 recall')]
 names=('A_original','B_augmented','C_six_view','D_augmented_six_view');colors=['#777777','#2B7A78','#D17B0F','#2E6F9E']
 for ax,(met,title) in zip(axs.ravel(),plotmetrics):
  vals=[np.mean([summary[n][s]['fold_mean'][met] for s in ('17','29','43')]) for n in names]
  ax.bar(range(4),vals,color=colors);ax.set_xticks(range(4),['A','B','C','D']);ax.set_title(title);ax.grid(axis='y',alpha=.2)
 fig.suptitle('Same 124 development geometries; fold/seed means')
 fig.savefig(O/'CYCLIC_MODEL_COMPARISON.png',dpi=180);plt.close(fig);figure_status.append('CYCLIC_MODEL_COMPARISON.png:PASS')
except Exception as e:figure_status.append('PLOT_GENERATION_UNAVAILABLE:'+repr(e))

# Final integrity/status snapshot, without modifying existing staged/dirty files.
status=subprocess.run(['git','-C',str(R),'status','--short'],capture_output=True,text=True).stdout
branch=subprocess.run(['git','-C',str(R),'branch','--show-current'],capture_output=True,text=True).stdout.strip()
head=subprocess.run(['git','-C',str(R),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
ab=subprocess.run(['git','-C',str(R),'rev-list','--left-right','--count','HEAD...@{u}'],capture_output=True,text=True).stdout.strip()
staged=subprocess.run(['git','-C',str(R),'diff','--cached','--name-only'],capture_output=True,text=True).stdout.splitlines()
unstaged=subprocess.run(['git','-C',str(R),'diff','--name-only'],capture_output=True,text=True).stdout.splitlines()
untracked=[line[3:] for line in status.splitlines() if line.startswith('?? ')]
task_path=str(O.relative_to(R)).replace('\\','/')
compact_roles={fold:{k:v for k,v in values.items() if k not in ('train_ids','validation_ids','train_families','validation_families')} for fold,values in role_summary.items()}
summary2={'source_dataset_cases':len(ids),'distinct_case_ids':len(set(ids)),'distinct_exact_geometry':len(set(map(tuple,D.tolist()))),'cyclic_orbits':len(orbit_counts),'cyclic_orbits_with_multiple_cases':sum(n>1 for n in orbit_counts.values()),'fold_role_counts':compact_roles,'fit_count':fit['new_augmented_fits'],'fit_seconds':fit['elapsed_fit_seconds'],'no_solver':True,'h1_hold':True,'git':{'branch':branch,'head':head,'ahead_behind':ab,'status_lines':len(status.splitlines()),'staged_paths':len(staged),'unstaged_paths':len(unstaged),'untracked_paths':len(untracked),'task_output_untracked':any(p.replace('\\','/').startswith(task_path) for p in untracked)},'figures':figure_status}
writejson(O/'CYCLIC_CLOSEOUT_SUMMARY.json',summary2)
print(json.dumps(summary2,ensure_ascii=False,indent=2))
