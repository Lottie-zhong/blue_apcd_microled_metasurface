from pathlib import Path
import json,csv,sys
import numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_272G_COMPLEX_ENSEMBLE_SHRINKAGE_V1';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';F=Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1/FORWARD'
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
assert rd(D/'COMPLETE.json')['status']=='COMPLETE';z=np.load(B/'COMPLEX_DATASET.npz');idx={s:i for i,s in enumerate(z['case_ids'])};s=rd(D/'SUMMARY.json');rows=rd(D/'FOLD_METRICS.json');diag=rd(D/'TREE_DIAGNOSTIC.json');family=rd(B/'LOCAL_FAMILY_COMPONENTS.json');summary={r['model']:r for r in s};arrays={};v=None
for name in summary:
 a=[np.load(D/f'{name}_fold{f}.npz') for f in range(1,5)];cs=np.concatenate([p['C'] for p in a]) if name!='C_PowerOnly' else None;ids=np.concatenate([p['case_ids'] for p in a]);v=np.array([idx[i] for i in ids]);arrays[name]={'C':cs,'P':np.concatenate([p['P'] for p in a]),'eta':np.concatenate([p['eta'] for p in a]),'absolute':np.concatenate([p['absolute'] for p in a])}
 if cs is not None:summary[name]['TM_variance_ratio']=float(np.var(abs(cs[:,:,:,1]),axis=0,ddof=1).sum()/np.var(abs(z['C_hat'][v,:,:,1]),axis=0,ddof=1).sum())
# Restore pooled across-geometry variance definition used in predecessor reports.
fields=list(dict.fromkeys(k for r in summary.values() for k in r))
with (D/'COMPLEX_AGGREGATION_ABLATION.csv').open('w',newline='',encoding='utf-8') as f:wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(summary.values())
groups={str(cid):str(cid) for cid in ids}
for n,fam in enumerate(family):
 for cid in fam:
  if cid in groups:groups[cid]='family_'+str(n)
units=list(dict.fromkeys(groups.values()));unitindex=[np.array([j for j,cid in enumerate(ids) if groups[cid]==u]) for u in units];rng=np.random.default_rng(7341);boot={};errors={k:abs(a['absolute'][:,:,4]-z['absolute_H2'][v,:,4]).mean(1) for k,a in arrays.items()}
for name in summary:
 if name=='A_ReIm':continue
 delta=errors[name]-errors['A_ReIm'];values=[]
 for _ in range(2000):jj=np.concatenate([unitindex[k] for k in rng.integers(len(units),size=len(units))]);values.append(delta[jj].mean())
 boot[name]={'Pplus_MAE_delta_vs_A':float(delta.mean()),'family_cluster_percentile95':np.quantile(values,[.025,.975]).tolist(),'folds_improved':sum(next(r for r in rows if r['model']==name and r['fold']==f)['Pplus_MAE']<next(r for r in rows if r['model']=='A_ReIm' and r['fold']==f)['Pplus_MAE'] for f in range(1,5))}
(D/'PAIRED_FAMILY_STABILITY.json').write_text(json.dumps({'units':len(units),'bootstrap':2000,'interpretation':'descriptive OOF uncertainty conditional on fixed fitted models/acquisition; not refit uncertainty or independent external test','comparisons':boot},indent=2))
baseline=rd(F/'METRICS_FIXED124.json');assert abs(summary['A_ReIm']['complex_NRMSE']-baseline['Leaf1']['complex_NRMSE'])<1e-12;assert abs(summary['A_ReIm']['Pplus_MAE']-baseline['Leaf1']['Pplus_MAE'])<1e-12
def table():
 text='|Model|Complex NRMSE|TM amplitude MAE|TM variance/truth|Routing MAE|Relative phase °|P_scale MAE|eta+ MAE|P+ MAE|450nm rho|Top20 recall|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
 for n,a in summary.items():text+='|'+n+'|'+'|'.join(f'{a[k]:.6f}' if k in a else 'N/A' for k in ['complex_NRMSE','TM_magnitude_MAE','TM_variance_ratio','routing_MAE','relative_phase_deg','P_scale_MAE','eta_plus_MAE','Pplus_MAE','rho450','Top20_recall'])+'|\n'
 return text
g=rd(D/'H1_GATES.json');hg={k:{'gates':a['gates'],'production_admission':a['production_admission'],'seed_stability_status':a['seed_stability_status']} for k,a in g.items()};(D/'H1_SUMMARY.json').write_text(json.dumps(hg,indent=2))
norm=[a['norm_ratio'] for a in diag];an=summary['A_ReIm'];bn=summary['B_MagnitudeCircular'];dn=summary['D_NN29']
report=f'''# Complex ensemble shrinkage — 272G

## Scientific verdict
Cross-tree cancellation is a demonstrated major cause of norm shrinkage in this saved Leaf1 forest, across all four legal folds and three seeds. It is not proof that phase averaging alone is the cause of all prediction error. Tree modal-distribution disagreement and insufficient conditional information remain.

12 fold/seed checks, 124 primary heldout geometries (32/31/30/31), 128 trees per forest; Cartesian forest/mean-tree norm ratio range {min(norm):.6f}–{max(norm):.6f}. See TREE_DIAGNOSTIC.json for every fold/seed, Re/Im tree variance and amplitude-weighted circular resultants. These are evaluation-fold findings, not six-dimensional space-wide certification.

## Frozen method and comparison
609D truth remains 588 Cartesian components plus21 natural-log P_scale. Per-lambda29D is28 Cartesian+lnP. Same native phase gauge, POSTNP1722nm, orders -3…+3, TE/TM, same frozen H2. No field/label/reference-plane modification, no independent order rotations, no mechanical state normalization.

A reuses all384 saved Leaf1 trees per fold and exactly reproduces predecessor NRMSE and P+MAE (<1e-12). B uses arithmetic mean modal magnitude and amplitude-weighted circular phase: arg(sum C). Thus B retains A phase and changes amplitude without oracle alignment. Dark exact-zero circular resultant yields magnitude times angle(0)=0 phase convention; it must not be interpreted as phase certainty. Low concentration is reported. C averages frozen-H2 per-tree Routing at fixed A P_scale; no unique complex state, hence complex/phase metrics N/A. C is an application comparator, never a replacement609D model.

No valid cached29D neural-network checkpoint was identified in the inspected predecessor inventories. D is an explicitly new lightweight CPU-only7→64→64→29 tanh model, two fixed seeds17/29, four original family-purged folds,300epochs, no tuning. Train-only X/Y standardization; ordered geometry and wavelength preserved. Eight fits, zero forest refits, zero CVAE fits.

{table()}
TM variance ratio uses pooled124 geometry variance at fixed wavelength/mode. NRMSE pools SSE/true energy; MAE geometry-weighted; rho and Top20 average four folds. Top20 uses ceil(0.2*n) per fold and predecessor argsort convention. Non-comparable direct42D regressors were not substituted.

## Stability
{json.dumps(boot,indent=2)}
Paired bootstrap resamples connected local families/singletons (2000 replicates), conditional on existing OOF fits; no tree/wavelength pseudoreplication. Four folds and two/three seeds remain small. Acquisition was adaptive to predecessor data; this is development OOF, not a pristine external or sealed test. Point gains alone do not establish reliable unknown-K6 generalization.

## H1
{json.dumps(hg,indent=2)}
Frozen H1 is not relaxed. Power-onlyC cannot qualify609D. B's production ensemble pools all trees; H1 seed stability uses each forest's same aggregation separately. No inverse-production readiness is claimed.

## Evidence and boundaries
COMPLEX_AGGREGATION_ABLATION.csv, FOLD_METRICS.csv, TM_ORDER_DIAGNOSTIC.csv, TREE_DIAGNOSTIC.json, PAIRed family stability JSON, saved per-fold predictions and tree caches; source WORKER.py and FIT_LEDGER.json. FAST272, NEW_FDTD0, NEXT_BATCH_AUTHORIZED0, DIAG2=1/2,A2HOLD,DOE56HOLD. Runner/native/sealed untouched; canonical117 solver entries unchanged; original four staged files unchanged. No commit/push.
'''
(D/'COMPLEX_ENSEMBLE_SHRINKAGE_REPORT.md').write_text(report,encoding='utf-8')
phase='''# TM Routing and circular phase

Single X/P_XLIKE incidence only; full Jones/polarization selectivity is not evaluated. Seven orders TE/TM retained. Circular absolute angular errors and training-fold-only dominant-channel relative references are used. Primary relative-phase weights |C_true|² preserve predecessor convention; true amplitude <0.001 of per-case/lambda maximum is excluded, plus reference/near-zero predicted safeguards. Weak TE phase is not assigned meaningful large weight. This weighting is not cos(theta) modal flux; Routing itself uses exact frozen H2 flux weights.

B keeps A circular phase, so identical phase errors cannot demonstrate phase learning improvement. Tree resultant |mean C|/mean|C| describes cancellation/concentration, not phase accuracy. TM_ORDER_DIAGNOSTIC.csv exposes order-dependent attenuation and magnitude/Routing error for all folds; tree Re/Im variances are descriptive across trees, not confidence intervals.

H2 power depends on modal squared magnitudes and P_scale, with no cross-order phase interference in this decoder. Improved complex magnitude may improve Routing, but phase fidelity cannot be inferred from target power. Power ensemble C averages H2 outputs and has no validated609D phase state. Nonadditivity/cancellation does not uniquely prove a near-field mechanism.

'''+table()
(D/'TM_ROUTING_AND_PHASE_REPORT.md').write_text(phase,encoding='utf-8')
nextreport='''# H1 gap and next stage

No frozen H1 threshold changes. Consult H1_SUMMARY.json; failure of any required main gate retains HOLD, even when ranking or a point MAE improves. Current272G development OOF cannot certify arbitrary unknownK6 or inverse design.

Cancellation is demonstrated; removing it is not sufficient evidence that capacity and six-dimensional coverage are solved. B and C comparison separates amplitude restoration from H2 averaging. Residual phase, TM modal allocation, predicted geometry variance and P_scale must improve together. Fixed small NN comparison is a capacity/representation probe, not proof that a larger network is needed.

Next priority is zero-solver per-geometry error versus circular concentration, true powered-TM variance and nearest-neighbor distance, stratified by all six diameters. Inspect failures in training-fold-only response neighborhoods; use disagreement only if cross-validated against actual error. Keep Mean/output-power baselines and unchanged124/familyguard. Do not optimize weak-mode phase.

Another50G is scientifically defensible only as a separately authorized targeted information experiment, not guaranteed learning improvement or a route already ready for inverse design. Suggested starting allocation:28 joint-coverage samples (including sparse D2/D3 combinations without sacrificing other dimensions),10 powered-TM/Routing disagreement samples with low circular concentration and independently useful uncertainty,6 stratified random,6 complete local additions around existing legal anchors. Rebalance only from documented zero-solver diagnostic evidence. No FSP/jobs/entry identities or new budget created in this task. Compare frozen evaluation at16/32/50; stop only for scientific/safety faults, not to hide poor model gains. More samples alone may not resolve phase ambiguity or conditional mean shrinkage.

CVAE preserved and frozen. Strict FAST numerical convergence remains uncertified; ML_TRAINING_GRADE is not FINAL_VALIDATION_GRADE. DIAG2=1/2,A2HOLD,DOE56HOLD; NEXT_BATCH_AUTHORIZED0; NEW_FDTD0.
'''
(D/'FORWARD_H1_GAP_AND_NEXT_STAGE.md').write_text(nextreport,encoding='utf-8')
(D/'CONTINUATION.md').write_text('Offline shrinkage analysis complete. Four requested reports/CSV govern. Do not rerun completed8NNfits or oldET/CVAE fits. Original124 familyguard retained, no new solver. See H1_SUMMARY.json for frozen scientific gate results. No next batch authorization. Original four staged files preserved.\n',encoding='utf-8')
print(json.dumps({'summary':summary,'stability':boot,'H1':hg},indent=2))
