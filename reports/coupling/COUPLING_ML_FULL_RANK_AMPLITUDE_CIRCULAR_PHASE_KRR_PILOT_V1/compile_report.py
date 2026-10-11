from pathlib import Path
import sys,json,hashlib,subprocess,numpy as np
root=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');out=root/'reports/coupling/COUPLING_ML_FULL_RANK_AMPLITUDE_CIRCULAR_PHASE_KRR_PILOT_V1'
sys.path.insert(0,str(root/'scripts/coupling_ml'));sys.path.insert(0,str(out))
import structured_phase_pilot as S
from k6_v2_pipeline.amended156 import adapter as A
def read(n):return A.read(out/n)
def put(n,d):A.write(out/n,d)
col=A.load_collection(False);by={c.case_id:c for c in col.cases};folds=read('FOUR_FOLD_MATCHING_AND_SHA.json')['folds'];ids=sum([t['heldout_case_ids'] for t in folds],[]);truth=np.array([by[cid].c_hat for cid in ids]);fraction=abs(truth)**2/(abs(truth)**2).sum((2,3),keepdims=True);mask=fraction>=1e-4
norms=np.concatenate([np.load(out/'models'/t['task_id']/'predictions.npz')['phase_vector_norm'] for t in folds])
reliable=norms[mask];weak=norms[~mask];diag={'strong_truth_mask_threshold':1e-4,'strong_phase_vector_norm':S.stats(reliable),'strong_fraction_below_point1':float((reliable<.1).mean()),'strong_fraction_below_point5':float((reliable<.5).mean()),'weak_phase_vector_norm':S.stats(weak),'all_TE_canonical_fraction_in_training':'100%TE weak by frozen training threshold; all-mode raw norm median1 is misleading','truth_mask_used_only_for_diagnostic':True,'nearzero_phase_fallback_count':sum(read(t['task_id']+'_PROVENANCE.json')['fallback_count'] for t in folds),'negative_sqrt_prediction_count':0}
put('STRONG_WEAK_PHASE_VECTOR_DIAGNOSTIC.json',diag)
h=read('H1_H2_FINAL_EVALUATION.json');paired=read('PAIRED_CARTESIAN_KRR_COMPARISON.json');d=read('RECONSTRUCTED_COMPLEX_STATE_RESULTS.json');decomp=read('AMPLITUDE_PHASE_ERROR_DECOMPOSITION.json');modal=read('NONZERO_ORDER_MODAL_ANALYSIS.json');verdict=read('FINAL_SCIENTIFIC_VERDICT.json')
amp=read('AMPLITUDE_HEAD_RESULTS.json');training=amp['training'];spectra=read('WAVELENGTH_STRATIFIED_RESULTS.json')
rows=['|Metric|Cartesian A median/q95|Structured B median/q95|Improved/worsened|','|---|---:|---:|---:|']
for k in paired:
 p=paired[k];rows.append(f"|{k}|{p['A']['median']:.6f}/{p['A']['q95']:.6f}|{p['B']['median']:.6f}/{p['B']['q95']:.6f}|{p['wins']}/{p['losses']}|")
table='\n'.join(rows)
gate_rows=['|Original gate|A|B|','|---|---|---|']+[f'|{k}|{h["A"]["gates"][k]}|{h["B"]["gates"][k]}|' for k in h['A']['gates']]
fold_rows=['|Fold|State wins/losses|State median delta|Routing wins/losses|Routing median delta|','|---|---:|---:|---:|---:|']
for f in ['1','2','3','4']:
 s=paired['state_relative_rmse']['folds'][f];r=paired['routing_eta_rmse']['folds'][f];fold_rows.append(f"|{f}|{s['wins']}/{s['losses']}|{s['delta']['median']:.6f}|{r['wins']}/{r['losses']}|{r['delta']['median']:.6f}|")
report=f'''# {S.TASK}
STATUS PASS — experiment completed within budget. Scientific verdict: **{verdict['verdict']}**. Full model remains **DEVELOPMENT_H1_FAIL**.

## Frozen scope and actual execution
DESKTOP-NNE313K/dell, N:\\anaconda_envs\\RCP_LCP\\python.exe, branch work/mdc-np-coupling-ml-v1. Source HEAD674b36df4bd0f3317590c3402c4f5468c0d13a72.156G science-valid development identity and complete previous artifact inventories were checked before fit. The same original four n124 train subsets and heldouts32/31/30/31 were used, with no baseline fit or hyperparameter selection. Geometry standardization, RBF gamma1/6 and alpha1 are the frozen same-fold values. All21 wavelengths follow geometry groups; reference1722nm, seven ordered m=-3..+3, TE/TM, full294complex/588real state and21physicalP_scale remain unchanged.

4 logical candidates, **8 CPU state-head fits** (fourAmplitude, fourPhase); no P_scale fits, baseline refits, MLP, NP/MDC retraining, FDTD, replay or confirmation response access. Eight per-head invocations were ledgered before each .fit and saved once complete. All8 completed; no reruns. Zero-fit preflight and6synthetic tests passed before fitting. Model saves/reloads reproduce predictions elementwise exactly.

## One preregistered representation
Amplitude targets sqrt(abs(C_hat)) are standardized by training coordinate means and one global RMS per head, predicted and inverse-scaled, then squared for nonnegative A. No clipping; zero negative sqrt predictions occurred. Phase targets are294absolute[cos,sin] pairs, standardized independently with training means/globalRMS. Training coordinates with fraction<1e-4 or A=0 use deterministic[1,0], never treated as reliable phase. Inverse-scaled predicted vectors are unit-normalized; norm<=64float64eps would use unit mean of reliable training phasors (no reliable/zero mean ->unit1). Actual fallback count0. No reference switching, test-truth mask, oracle alignment or full-state renormalization enters B prediction.

About50.02..50.03% training coordinates were weak (all TE and very fewTM); their truth energy was only1.88e-7..3.28e-7. The raw polar representation is fully invertible, tested through zero/tiny/wrap cases; weak-phase target canonicalization deliberately discards unreliable supervision and is not asserted to roundtrip those phases. All294 amplitudes and bothchannels remain in output. H2 roundtrip test meets1e-12; raw complex roundtrip tolerance2e-15. Protected sources and original268/NP88/zero-fit audit predictions were preserved.

## Matched original evaluator
{table}

Norm ratio A {d['A']['norm_ratio']['median']:.6f}/{d['A']['norm_ratio']['q95']:.6f} versus B {d['B']['norm_ratio']['median']:.6f}/{d['B']['norm_ratio']['q95']:.6f} (median/q95). Restored norm alone does not mean restored complex state. P_scale A/B is elementwise identical in every fold and mergedOOF. Absolute-order changes come from routing only; H2 total=P_scale, so total/scale errors coincide by definition. Frozen A aggregate and all original gates match the original n124 result exactly.

{chr(10).join(gate_rows)}

Routing Pearson A={h['A']['aggregate']['routing_pearson']}, B={h['B']['aggregate']['routing_pearson']}; total-power Pearson A={h['A']['aggregate']['total_power_pearson']}, B={h['B']['aggregate']['total_power_pearson']}. Deterministic one-seed KRR has seed stability N/A, not an inventedPASS. B attains the original absolute-order gate, but state/routing/thresholded-relative/total gates fail. No independent confirmation or production admission.

## Amplitude learned; absolute/relative phase not improved
Amplitude relative RMSE0.672675/0.797020 ->0.430317/0.601391;121/124 geometries improve, allfour fold median deltas negative. Amplitude pooled SSE1290.43 ->596.36 (53.8% reduction). Yet phase pooled SSE959.62 ->2596.14 (2.71x); phase now81.32% of B complex SSE versus42.65% in A. Phase direction median/q95 itself worsens1.220526/1.768362 ->1.281598/1.862608rad; relative phase1.721010/1.961726 ->1.750114/1.963318rad. Absolute phase51wins/73losses; phase-component RMSE worsens in all124. This is not an amplitude-and-phase joint gain.

Raw phase-vector norms require a strong/weak distinction: strong truth-mask norm median{diag['strong_phase_vector_norm']['median']:.6f}, q95{diag['strong_phase_vector_norm']['q95']:.6f}; {100*diag['strong_fraction_below_point5']:.2f}% below0.5 and {100*diag['strong_fraction_below_point1']:.2f}% below0.1. The all-coordinate median1 is largely weak-TE fixed[1,0], not proof of confident physical phases. Unit-circle projection restores length but cannot improve direction; with0fallbacks it preserves the predicted phase angle. Larger learned amplitude magnifies still-wrong directions through2*A_pred*A_true*(1-cosdelta), explaining the observed SSE tradeoff algebraically. It does not establish that another phase representation will generalize.

## Nonzero, zero and +1 orders
Nonzero state0.973604/1.129514 ->1.162706/1.677441;13wins/111losses. Nonzero norm0.343782 ->0.842894 recovers while complex correctness worsens. m0 state0.550113/1.872078 ->0.584045/2.197658, with itsnorm0.812537 ->1.011012. +1 state0.921086/1.337575 ->1.096359/2.468508: severe target-order tail deterioration. +1routing median0.089712 ->0.101143 worsens even though q95improves; do not generalize overall routing gain to every order. +1absolute median0.032824 ->0.033185 also slightly worsens. Full per-order TE/TM/state/power diagnostics retained.

B nonzero contribution88.25% of total complex SSE. TE contributes~1.28e-9 to B SSE; the error remains TM/nonzero phase dominated, not weak-channel phase noise. Strong and weak bins retain absolute SSE quantities to avoid misleading percentages from tiny denominators. Wavelength bands440..444,445..455,456..460 and fullband are reported independently; none selected model rules.

## Paired geometry and tails
{chr(10).join(fold_rows)}

Amplitude gains121/3; routing106/18; absolute-order101/23. State12/112, with pairedmedian+0.163908 and descriptive geometry-bootstrap95% medianCI[0.133515,0.203176]. Routing pairedmedian-0.063964, CI[-0.072127,-0.046431]. No wavelength pseudo-replication or statistical independence claim; folds/history are correlated and heldouts repeatedly examined.

Largest state delta: G0110.902081->1.244564 (+0.342483), G0091.156564->1.486358 (+0.329794), G0510.953989->1.279414 (+0.325424). Overall worst state A={paired['state_relative_rmse']['A']['worst']:.6f}, B={paired['state_relative_rmse']['B']['worst']:.6f}; preregistered research tail rule passes={verdict['consistent_gain']['state_tail_rule']}. Significant routing regressions includeG1110.061714->0.181633 andG0420.072071->0.183430. No NaN, overflow, negative A, replay or numerical projection exception occurred; these are predictive failures. Every geometry delta and top10worsenings permetric are saved, not only favorable averages.

## Train versus heldout and evidence limits
Per-fold training state medians: {[round(v['train_state_relative_RMSE']['median'],6) for v in training]}; training amplitude medians: {[round(v['train_amplitude_relative_RMSE']['median'],6) for v in training]}. Full trainingphase diagnostics retained. Single matched frozenkernel/head scheme proves neither phase fundamentally unlearnable nor every structured model ineffective. Current evidence supports useful amplitude/power prediction, continued phase uncertainty, and harmful recovery of large wrong-phase vectors. No oracle result enters official H1.

## Next — DO NOT EXECUTE
Retain the evidence of amplitude/routing gain for scientific review; do not promote B or replace baseline/confirmation predictions. Priority is an order-resolved phase-structure experiment that retains absolute/common and relative phases and tests train-defined local geometry conditioning, with explicit invertible reconstruction and matched KRR controls. A concrete new protocol/budget requires Chat review; do not append another candidate, wider MLP or kernel-scale trial now. Full-rank amplitude-only recovery or global-phase-only compensation is insufficient. Existing156G can support a further developmental test; independent confirmation and numerical repeatability remain separate obligations.

## Artifacts, hashes and isolation
STRUCTURED_MODEL_FROZEN_SPEC and FOUR_FOLD_MATCHING_AND_SHA freeze code, identities, input dependencies, transforms and model choices before fits. FIT_LEDGER proves8invocations. MODEL_ARTIFACTS_AND_SHA references allhead/model/prediction binaries retained durably on thisserver; only scoped source/report/test/provenance text is committed. SHA_INVENTORY contains full hashes. FINAL_ISOLATION_CHECK re-verifies originals, no confirmation access and unchanged P_scale. Local13 continues SUSPENDED, original32confirmation roles/responses sealed and28input-side predictions unchanged. Foreign dirty/staged preserved. DELIVERY_RECEIPT contains finalGit/push snapshot and is outside its own committed inventory.
'''
(out/'FINAL_REPORT.md').write_bytes(report.encode())
put('MODEL_ARTIFACTS_AND_SHA.json',{'fits':8,'logical_candidates':4,'artifacts':[S.pin(p) for p in sorted((out/'models').rglob('*')) if p.is_file()],'not_committed_binaries':'durable remote artifacts; hashes/provenance committed','actual_fit_entry':'sklearn.kernel_ridge.KernelRidge.fit on same frozen transformed124 traininggeometry inputs, two independent targets; recorded once/head'})
put('RUN_COMMAND_PROVENANCE.json',{'remote_python':sys.executable,'host':'DESKTOP-NNE313K','entry_modes':['structured_phase_pilot.py prepare','structured_phase_pilot.py train','structured_phase_pilot.py evaluate'],'actual_invocation':'SSH stdin Python helper executes these runpy modes; syntheticpytest finishes before train','sklearn':'same existing RCP_LCP environment, no installs','new_CPU_model_fits':8,'synthetic_fits':0})
(out/'CONTINUATION.md').write_bytes((f'# {S.TASK} COMPLETE\nHost DESKTOP-NNE313K/dell; worktree {root}; branch work/mdc-np-coupling-ml-v1; source HEAD674b36df4bd0f3317590c3402c4f5468c0d13a72; interpreter N:\\anaconda_envs\\RCP_LCP\\python.exe. Read FINAL_REPORT, STRUCTURED_MODEL_FROZEN_SPEC, FIT_LEDGER, FINAL_ISOLATION_CHECK and SHA_INVENTORY first.8/8heads completed,4logical candidates; do not rerun train or refreeze. Resume only reporting from saved checkpoints if necessary. Verdict STRUCTURED_AMPLITUDE_ONLY_GAIN; state0.873->1.039 worsens, amplitude0.673->0.430 androuting0.182->0.122 improve. P_scale exact frozen, no newscale fits. FullH1FAIL despite absolute-order gate attained. Confirmation sealed, old268/NP88/audit unchanged, local13SUSPENDED. Nextorder-resolvedphase/localconditioning proposal requires Chat authority; no automaticextraexperiment.0solver/replay/confirmation, no GPUplatform change. Modelbinary/SHA retained onserver, scopedtext commit only. Deliveryreceipt provides finalGit/push recovery pointer.\n').encode())
(out/'.gitattributes').write_bytes(b'* -text\n*.py whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n')
S.check_pins();spec=read('STRUCTURED_MODEL_FROZEN_SPEC.json');assert hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=root)).hexdigest()==spec['foreign_index_sha256']
files=[p for p in out.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ['SHA_INVENTORY.json','DELIVERY_RECEIPT.json']]
put('SHA_INVENTORY.json',{'task':S.TASK,'files':[S.pin(p) for p in sorted(files)],'source_pins':'STRUCTURED_MODEL_FROZEN_SPEC.json','models_durable_remote':True,'confirmation_access':0,'new_head_fits':8})
print('PHASE_DIAGNOSTIC',json.dumps(diag));print('REPORT_SHA',A.sha(out/'FINAL_REPORT.md'));print('INVENTORY_SHA',A.sha(out/'SHA_INVENTORY.json'));print('PEARSON',h['A']['aggregate']['routing_pearson'],h['B']['aggregate']['routing_pearson']);print('TRAIN',[(v['fold'],v['train_state_relative_RMSE']) for v in training])
