"""Compile science report from completed predictions and receipts, never fits."""
from pathlib import Path
import json,datetime,collections,hashlib
from . import adapter as A
def md(name,s):(A.OUT/name).write_bytes((s.strip()+'\n').encode())
def main():
 H=A.read(A.OUT/'H1_H2_FINAL_EVALUATION.json');R=H['evaluations'];D=A.read(A.OUT/'ERROR_MODE_AND_NORM_AUDIT.json');L=A.read(A.OUT/'FIT_EXECUTION_LEDGER.json');P=A.read(A.OUT/'PAIRED_MODEL_COMPARISON.json');T=A.read(A.OUT/'TRAIN_VS_HELDOUT_DIAGNOSTIC.json');E=A.read(A.OUT/'CPU_WORKER_EXIT_RECEIPT.json')
 assert len(L['fits'])==268 and all(q['status']=='COMPLETE' for q in L['fits'].values())
 lines=['| Model | Refit G | State med/q95 | Routing med/q95 | Routing r | Absolute med/q95 | Thresholded relative med/q95 | P_scale/total med/q95 | Power r | Norm ratio med | Seed std | Gates |','|---|---:|---|---|---:|---|---|---|---:|---:|---|---|']
 for model,values in R.items():
  for n,r in values.items():
   m=r['aggregate']['metrics'];fmt=lambda k:f"{m[k]['median']:.6f}/{m[k]['q95']:.6f}";g=', '.join(k+':'+('N/A' if v is None else 'PASS' if v else 'FAIL') for k,v in r['gates'].items());std='N/A' if r['seed_state_median_std'] is None else f"{r['seed_state_median_std']:.6f}"
   lines.append(f"| {model} | {n} | {fmt('state_relative_rmse')} | {fmt('routing_eta_rmse')} | {r['aggregate']['routing_pearson']:.6f} | {fmt('absolute_order_source_normalized_rmse')} | {fmt('thresholded_absolute_order_relative_median')} | {fmt('p_scale_relative_rmse')} | {r['aggregate']['total_power_pearson']:.6f} | {D[model+'_n'+n]['norm_ratio']['median']:.6f} | {std} | {g} |")
 table='\n'.join(lines);md('LEARNING_CURVE_NUMERIC_TABLE.md',table)
 highlights=[]
 for model in R:
  r=R[model]['124'];d=D[model+'_n124'];rows=r['aggregate']['per_geometry'];worst=max(zip(d['geometry_rows'],rows),key=lambda q:q[1]['state_relative_rmse']);delta=P['learning_curve_deltas'][model]
  highlights.append(f"### {model}\n\n124G held-out state median/q95 {r['aggregate']['metrics']['state_relative_rmse']['median']:.6f}/{r['aggregate']['metrics']['state_relative_rmse']['q95']:.6f}; zero-prediction state baseline1. Norm ratio median {d['norm_ratio']['median']:.6f}. Matched124-minus32 state median delta {delta['124_minus32']['median']:.6f}: {delta['improved']} geometry wins/{delta['worsened']} losses. Fold deltas: `{json.dumps(delta['by_fold'])}`.\n\nWorst state geometry {worst[0]['case_id']} ({worst[0]['stratum']}), error {worst[1]['state_relative_rmse']:.6f}. Worst wavelength diagnostic `{json.dumps(d['worst_wavelength'])}`; worst order diagnostic `{json.dumps(d['worst_order'])}`. State-error energy fractions orders m=-3..3: `{d['error_energy_fraction_by_order']}`; TE/TM: `{d['error_energy_fraction_TE_TM']}`. Truth-weighted significant absolute-phase RMSE median {d['truth_weighted_phase_RMSE']['median']:.6f}rad; relative-phase median {d['relative_phase_RMSE']['median']:.6f}rad.\n\n124G gates: `{json.dumps(r['gates'])}`; final status {H['development_status'][model]}. All gates retain original numeric authority; deterministic KRR seed stability N/A.")
 selected=A.read(A.OUT/'INNER_SELECTED_CONFIGURATIONS.json')
 updates=[q['actual_updates'] for q in L['fits'].values() if q['task']['model_kind']=='CARTESIAN_MLP'];wall=sum(q['wall_seconds'] for q in L['fits'].values())
 start=datetime.datetime.fromisoformat(E['started_utc']);end=datetime.datetime.fromisoformat(E['finished_utc']);elapsed=(end-start).total_seconds()
 c=dict(collections.Counter(q['task']['phase']+':'+q['task']['model_kind'] for q in L['fits'].values()))
 highlights_text='\n\n'.join(highlights)
 report=f'''# APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1

**PASS — approved execution completed.** Scientific model verdicts: `{json.dumps(H['development_status'])}`. No independent confirmation, production surrogate admission, inverse-design or dipole validation is claimed.

## Frozen scope and execution

156 unique development groups: old32 + local11 + global113. Original160G/V2 authority retained; approved version COUPLING_K6_V2_DEVELOPMENT_156G_AMENDMENT_V1 binds closure inventory SHA `{A.INVENTORY_SHA}`. Source truth/label/native FSP/H5 byte hashes rechecked before first fit. Actual legacy S16 attempt002 preserved; S35 failed and recovered provenance remain separate. Historical old32 EXT02 is legal; independent diagnostic EXT02, queue21, reserve, four failed attempts and confirmation responses excluded.

268/268 logical CPU fits complete, no failed or extra fit:108innerKRR+108innerMLP+12curveKRR+36curveMLP+1finalKRR+3finalMLP. Internal KRR state/log-P heads belong to one logical joint fit; standalone P_scale fits0. Actual MLP optimizer updates `{sum(updates)}`. Summed per-fit wall time {wall:.1f}s; worker including ingestion/evaluation {elapsed:.1f}s. Solver0, GPU FDTD0, replay0, local0, NP0, confirmation-response accesses0; synthetic model fits0.

Interpreter N:\\anaconda_envs\\RCP_LCP\\python.exe, Python3.10.20, torch2.5.1+cu121, numpy2.2.5, scipy1.15.3, sklearn1.7.1. CUDA hidden, execution CPU two threads. Torch/CUDA not reinstalled. Exclusive task CPU owner claim archived on normal exit. Engine checkpoint every optimizer update; all268 fitted models independently saved/reloaded with exact prediction equality and rehashed. Full models/preprocessors/predictions/trajectories retained outside Git; SHA inventory records durable files. Original foreign working/staged states preserved.

## Validation and training sizes

Four fixed survivor outer validation groups32/31/30/31 (total124), all new development identities:113global+11local. Old32 remain outer-training-only and historically exposed; they can appear in original inner validation groups. Outer train124/125/126/125. Inner memberships unchanged except missing IDs removed. Full21-wavelength response belongs to one geometry group. Inner preprocessing fitted only corresponding inner-train; each refit preprocessing only its32/64/124 groups. Hyperparameters and fixed MLP epochs selected only using corresponding outer-train3-fold inner CV.

32/64/124 are **actual refit counts**, not total response budgets: all levels see the same124–126 outer-train groups during configuration selection. Fixed outer evaluation identity at every size; training subsets nested and response-blind frozen. Max124 curve leaves0/1/2/1 outer-train groups unused for refit; all included in applicable inner search and final156 fits. Not exactly comparable to hypothetical160G/128 or old65G's different validation IDs. Matched within-run curves are primary evidence of sample-size effect, not cross-experiment causal claims or wavelength-times-seed independent statistics.

## Original H1/H2 results

{table}

P_scale and total-power metrics are identical by frozen decoder definition: total_power=physical predictedP_scale; routing is normalized modal powers and absolute_order=routing*P_scale. This identity is not independent power validation. Full state errors use raw predicted C_hat without phase alignment, norm rescaling, clipping or projection. C_hat three-seed complex mean, P_scale physical arithmetic mean after per-seed log inverse/exp; original per-seed metrics and mean-norm change retained.

{highlights_text}

## Failure-mode interpretation and limitations

Per-geometry, wavelength, order, TE/TM, role and boundary-stratum outputs are retained. Phase diagnostics use preregistered per-wavelength truth significance>=1e-4, truth-amplitude-squared weights and separately prediction-dependent weights; weight changes do not prove phase improvement. Relative phase compares all order pairs within each polarization; no oracle common-phase alignment. Very weak TE fields can have large relative errors without dominating state-energy error. Actual observations are numerical deltas/norms/phase/routing; sparse-coverage, rapid phase variation, regularization/optimization and representation explanations are hypotheses, not causal proofs.

Training errors versus held-out results are separately in TRAIN_VS_HELDOUT_DIAGNOSTIC.json. Lower training error alone is not generalization. No architecture/width/rank/loss/seed/config expansion was performed in reaction to outer results. Existing finite RBF KRR grid and21377-parameter6->32->32GELU Cartesian MLP unchanged, full588real Cartesian coordinates plus21logP_scale, no rank2PCA. Positive finite P_scale truth required; noepsilon/clipping; train-only shared state residualRMS/log statistics and original L_C+L_P objective.

Original13 local fits remain SUSPENDED (missingD6_M05; original six-dimensional LOAO rank deficiency); localconfirmation4 unopened. All32 confirmation responses sealed. Both final global candidates fit all156 groups, and geometry-only predictions for27core+1stress were frozen with model/preprocessor/evaluator SHA. These are predictions awaiting separate confirmation HF/evaluation authority, not validated responses. NP88D paired65G twoKRR experiment remainsPENDING and is not included in268. FixedMDC not retrained; complexLF residual still unavailable until LF/HF contracts align.

## Minimal next proposal — do not execute

Review the matched124G state/phase/norm andpower evidence first. If originalH1 remains failed, consider the already frozen65G geometry-only versusNP88D twoKRR paired experiment as a limited physics-feature test; do not treat it as156G confirmation. A156G feature experiment needs its own frozen matched protocol and authorization. No extraHF merely to pad160G, no network expansion or complexLF residual here. Independent confirmation remains a separate decision after reviewing these development results.

## Recovery and artifacts

Read CONTINUATION.md, SCIENTIFIC_AUTHORIZATION.txt, DEVELOPMENT_156G_AMENDMENT_V1.json, EXECUTION_SOURCE_FREEZE.json and APPROVED_268_FIT_MANIFEST.json. FIT_EXECUTION_LEDGER.json is COMPLETE for all268; do not restart fits. Final source inventory andMODEL_ARTIFACTS_AND_SHA.json bind models and preprocessing. Report folder `{A.OUT}`. Git commits use exact task allowlist; FSP/H5 and model binaries not added.
'''
 md('FINAL_SCIENTIFIC_REPORT.md',report)
 md('CONTINUATION.md',f'''# Completed156G approved global forward training

Task APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1 COMPLETE. Read FINAL_SCIENTIFIC_REPORT.md, SHA_INVENTORY.json, H1_H2_FINAL_EVALUATION.json, ERROR_MODE_AND_NORM_AUDIT.json andMODEL_ARTIFACTS_AND_SHA.json first. HostDESKTOP-NNE313K/dell, worktree D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1, branchwork/mdc-np-coupling-ml-v1. CPU interpreter N:\\anaconda_envs\\RCP_LCP\\python.exe.268/268fits COMPLETE; no furtherfits authorized by this task. Preserve fit ledger/checkpoints/predictions, no recomputation.

Approved156amendment frozen; actual curves32/64/124, configuration selection sees124–126outertrain. Old32outertrain-only; validation124new=113global+11local, fixed survivor folds. Final1KRR+3MLP fitall156. Scientific statuses `{json.dumps(H['development_status'])}`. No independentconfirmation/productionadmission. All32confirmationresponsessealed, final28globalgeometry-onlypredictions hashed, local4sealed/no model; local13SUSPENDED missingD6_M05. NPpaired65G2KRR PENDING; complexLF residual not authorized. FDTD/replay/local/NP/standaloneP_scale/syntheticfits/confirmationaccess0.

All fitted reload predictions exact; checkpoint/provenance SHA verified. Read execution receipts and any reportingfix record; H1/H2/science unchanged. Next: Chat scientific review of completed learning curve, then separately authorize any feature comparison orconfirmation. Do not launch newsolver/train/inverse.
''')
 print('REPORT_READY',H['development_status'],c,elapsed,flush=True)
