from pathlib import Path
import sys,json,hashlib,subprocess,ast
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
OUT=ROOT/'reports/coupling/COUPLING_ML_COMPLEX_MODAL_PHASE_LEARNABILITY_AUDIT_V1'
sys.path.insert(0,str(ROOT/'scripts/coupling_ml'));sys.path.insert(0,str(OUT))
from k6_v2_pipeline.amended156 import adapter as A
import complex_modal_audit as M
read=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
write=lambda n,d:A.write(OUT/n,d)
d=read('COMPLEX_ERROR_AMPLITUDE_PHASE_DECOMPOSITION.json');o=read('RETROSPECTIVE_ORACLE_DIAGNOSTIC.json');g=read('GEOMETRY_LOCAL_RESPONSE_REGULARITY.json');s=read('STATE_NORM_COLLAPSE_ANALYSIS.json')
proposal={'status':'PROPOSAL_ONLY_NOT_EXECUTED_REQUIRES_NEXT_TASK_AUTHORITY','priority':'A: full-rank amplitude / absolute-unit-complex phase KRR pilot','reason':'Nonzero-mode contraction, amplitude bias and relative-phase dispersion coexist; common-phase correction explains little. Test target representation without adding NP inputs or optimizer confounding.','baseline':'reuse exact four n124 geometry-only KRR folds/models/P_scale; same train/heldout IDs, train-only input scaler, gamma/alpha and dtype; no search or baseline refit.','targets':'294 sqrt(A) coordinates and588 absolute cos/sin phase coordinates. Reconstruct A as square of predicted sqrt(A); normalize phase vector. All21 wavelengths,7orders,2channels retained; no full-state renormalization.','phase_rules':'Zero truth A ->unit1. Training coordinate fraction<1e-4 ->unit1 target; record frequencies and threshold sensitivity. Predicted phase norm<=64eps -> corresponding training circular mean; exact-zero circular mean ->unit1. No heldout truth fallback.','scales':'head-specific training means and shared RMS; unchanged kernel/ridge. Square and unit-vector maps are explicit candidate representation, never corrections to historical outputs.','fit_budget':'4 logical candidate fits =8 internal state-head multioutput KRR estimator fits/linear-system solves;0 baseline refits;0 new P_scale fits (reuse actually predicted frozen branches). Both fit conventions must be authorized explicitly in next task. Current execution=0.','output':'588 real reconstructed C_hat +21 independently predicted frozen P_scale =609. Same H2/H1; unchanged scale gate cannot improve.','evaluation':'one fixed candidate, original four folds, paired geometry deltas median/q95/worst, phase/norm/tails, all original conjunctive gates. No oracle H1 or confirmation response. Repeatedly analyzed heldouts are developmental.','risk':'Unit-phase projection may amplify wrong phase and worsen state. True-amplitude/pred-phase oracle already worsens KRR median to0.989. Full-rank structured prediction benefit is unproven; historical rank-2 polar POC cannot establish it.','backup':'D: restricted geometry-local surrogate only after primary review; not parallel arm. Local curvature and missingD6minus/repeatability prevent claiming complete six-dimensional affine validity.','HF':'156G suffices for this developmental pilot without new HF. Independent confirmation and controlled repeated-run/numerical error evidence need separate future authority; no broad extra HF recommended from this audit alone.'}
write('PRIORITIZED_MINIMUM_MODEL_EXPERIMENT.json',proposal)
tests="""from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts/coupling_ml'))
import numpy as np
import complex_modal_audit as M
def test_sse_zeros():
    t=np.array([1+2j,0j,1e-30+0j]);p=np.array([-2+1j,3j,0j]);a,b,e,_=M.error_decomposition(t,p)
    assert np.allclose(a+b,e,rtol=0,atol=2e-14) and b[1]==0 and b[2]==0
def test_wrapping():
    assert abs(np.angle(np.exp(1j*((-np.pi+.001)-(np.pi-.001))))-.002)<1e-12
def test_zero_gauge():
    c=np.zeros((2,21,7,2),complex);com,r,i=M.gauge(c)
    assert np.array_equal(r*com[...,None,None],c) and np.all(com==1)
def test_reference_switch():
    c=np.zeros((2,21,7,2),complex);c[:,:,3,1]=1e-30;c[:,:,6,1]=2j
    com,r,i=M.gauge(c,'fixed0_switch')
    assert np.all(i==13) and np.max(abs(com[...,None,None]*r-c))<1e-15
def test_oracle_sign():
    t=np.ones((2,21,7,2),complex);p=t*np.exp(1j*.7)
    assert np.max(abs(M.oracle_alignment(t,p)-t))<1e-14 and np.linalg.norm(p-t)>0
def test_weak_channel_mask():
    t=np.zeros((2,21,7,2),complex);t[:,:,3,1]=1;t[:,:,3,0]=1e-12;p=t.copy();p[:,:,3,0]*=-1
    assert M.angular_stats(t,p,1e-4)['absolute_phase_RMSE']['median']==0
def test_relative_phase():
    t=np.zeros((2,21,7,2),complex);t[:,:,2,1]=1;t[:,:,4,1]=1;p=t.copy();p[:,:,4,1]*=1j
    assert abs(M.angular_stats(t,p,1e-4)['relative_phase_RMSE']['median']-np.pi/2)<1e-12
def test_h2_phase_and_roundtrip():
    h=M.h1;dec=h.load_h2_decoder();rng=np.random.default_rng(42)
    c=rng.normal(size=(2,21,7,2))+1j*rng.normal(size=(2,21,7,2));p=np.ones((2,21));a,u=M.unit(c)
    x=h.reconstruct_h2(c,p,dec);y=h.reconstruct_h2(a*u,p,dec);z=h.reconstruct_h2(c*np.exp(1j*rng.normal(size=c.shape)),p,dec)
    for k in ['eta','absolute_order','total_power']:
        assert np.max(abs(x[k]-y[k]))<1e-12 and np.max(abs(x[k]-z[k]))<1e-12
"""
(OUT/'test_complex_modal_math.py').write_bytes(tests.encode())
r=subprocess.run([sys.executable,'-m','pytest',str(OUT/'test_complex_modal_math.py'),'-q','-p','no:cacheprovider'],cwd=OUT,capture_output=True,text=True)
(OUT/'TEST_OUTPUT.txt').write_bytes((r.stdout+r.stderr).encode());assert r.returncode==0,r.stdout+r.stderr
calls=[n.lineno for n in ast.walk(ast.parse((OUT/'complex_modal_audit.py').read_text())) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['fit','run','run_one']]
assert calls==[]
write('TEST_RESULTS.json',{'status':'PASS','synthetic_tests':8,'fits':0,'audit_fit_or_run_calls':calls,'bugs':'Pre-execution unescaped apostrophe fixed before protocol/input freeze; read-only detail reader JSON key typo. Neither affected historical science or repeated training.'})
rows=[]
for k in ['KRR','MLP','NP88']:
    v=d[k];ang=v['angular_threshold_sensitivity'][2]
    rows.append(f"|{k}|{100*v['pooled_amplitude_SSE_fraction']:.2f}%|{100*v['pooled_phase_SSE_fraction']:.2f}%|{s['models'][k]['state_norm_ratio']['median']:.3f}|{ang['absolute_phase_RMSE']['median']:.3f}|{ang['relative_phase_RMSE']['median']:.3f}|{100*o[k]['common_perlambda_SSE_explained_fraction']:.2f}%|")
report='''# COUPLING_ML_COMPLEX_MODAL_PHASE_LEARNABILITY_AUDIT_V1
STATUS: PASS (audit complete); all frozen models remain DEVELOPMENT_H1_FAIL.
Host DESKTOP-NNE313K/dell; branch work/mdc-np-coupling-ml-v1; source HEAD d481a82796d3b2998313f7e21f19cec80eae3cab.

## Authority and scope
156 labels (32 historical +113 global +11 local) passed existing SHA-gated ingestion. Heldout comparisons use exactly the same124 new geometries in four frozen outer folds. Old32 remain historical development/training data. KRR one seed; MLP complex seed-mean and physical-domain arithmetic P_scale mean of seeds0/1/2; NP88 four matched models. INPUT_PINS verifies1551 original-training and43 NP88 artifact entries plus physical sources. Confirmation input-side predictions were only hash-checked; no confirmation responses accessed.
All counts are zero: FDTD, replay, CPU model fits, P_scale fits, NP/MDC retraining, confirmation response access. Fixed input-kernel influence weights are diagnostic mathematics, not target fitting. All original results and H1/H2 unchanged.

## A. Amplitude and phase (OBSERVED)
Exact coordinate SSE identity: (A_pred-A)^2 +2*A_pred*A*(1-cos(delta_phi)). Pooled shares below are not optimized loss weights or median geometry shares. Zero amplitudes automatically have zero phase SSE. Significant phase threshold is truth energy fraction>=1e-4;1e-6..1e-2 sensitivity retains99.777%..100% energy and barely changes medians.

|Model|Amplitude SSE|Phase SSE|Norm median|Absolute phase rad median|Relative phase rad median|Oracle common-per-lambda SSE explained|
|---|---:|---:|---:|---:|---:|---:|
TABLE

Amplitude is the larger numerical term, but unresolved phase can cause vector shrinkage and suppress the phase term through A_pred. True-amplitude/predicted-phase RETROSPECTIVE_ORACLE_DIAGNOSTIC state medians0.989/1.206/1.126 exceed actual KRR/MLP/NP880.873/0.924/0.904. Predicted-amplitude/true-phase medians0.673/0.760/0.680 remain high. Both branches need improvement. Oracle tables are not forward predictions, H1 or admission evidence.

## B. Modal concentration (OBSERVED)
KRR error shares m=-3..+3:13.87%,15.22%,15.50%,14.08%,15.21%,13.46%,12.67%; nonzero orders sum85.92%. MLP largest order -1 contributes17.07%, NP88 -1 contributes18.26%. No single order explains failure; +1 is not unique. Matched truth Cartesian m0 energy25.13%, power-metric m0 energy28.68%. Predicted m0 power fractions59.07%/85.37%/65.79%. KRR m0 norm ratio0.813 versus nonzero0.366..0.404. MLP +1 ratio0.140 versus m0 ratio0.899. This is selective nonzero-mode contraction.
True TE energy fraction~9.5e-10; TM dominates under P_XLIKE incidence. Weak TE phase is not the bottleneck. MLP predicted TE fraction0.000762 is still secondary. Both coordinates remain in full output. Single incoming polarization does not define a full Jones operator or polarization selectivity.

## C. Common and relative phase (OBSERVED)
Oracle one phase per geometry explains5.12%/8.31%/8.97% SSE; per-wavelength common phase8.10%/10.41%/11.48%. Most error remains. Relative-phase medians1.721/1.819/1.780rad are substantial. Common-phase-only correction is not the priority.
Across156 geometries, m0 TM phase coherence is0.79..0.86 across wavelengths, much stronger than many nonzero TM modes. Spectral weighted principal phase-step median0.310rad/nm, q950.391. There are1033 raw wrapping events in21812 significant adjacent pairs;1.279% principal steps exceed pi/2. Wrapping differs from physical phase variation.1nm sampling cannot prove between-sample behavior around zeros.
Dominant-mode reference switches433 times along spectra. Fixed m0TM never requires a near-zero fallback on these156 truths, but this retrospective fact cannot guarantee a future safe reference. All common phases must still be predicted.

## D. Local response (OBSERVED; limitations)
Ordered geometry distance is ||deltaD||/130nm using formal100..230nm design domain. All156 have66 pairs within0.1, median symmetric state distance0.360 versus all-pair1.296. These share the local cluster, not independent trials. Global113 have zero pairs within0.25;29 pairs in(0.25,0.5] already have state distance median1.208. Sparse sampling cannot establish physical discontinuity.
S31 eleven ±5nm responses range0.165..0.532 state distance. D1 both signs~0.53; phase component usually exceeds amplitude. Symmetric curvature-to-linear ratios D1-D5=1.526/0.823/1.101/0.435/0.470. Local variation is smaller than global but not demonstrably affine or uniformly gentle. D6_M05 absent; full6D two-sided validity unverified. Old-anchor/new-run differences lack controlled repeatability bounds; same-run crossheight agreement cannot substitute.
Actual-fold nearest-train state difference correlates with KRR error (Pearson0.864, Spearman0.663); nearest phase difference Spearman0.589. These support a neighborhood-resolution concern without proving cause. Boundary and geometry results are retained; shared pairs/wavelengths must not inflate independent sample counts.

## E. NP88 negative gain (OBSERVED / SUPPORTED_HYPOTHESIS)
Global-only shared pairs: NP distance correlates with amplitude distance Pearson0.644 and routing0.562, but complex state0.124, weighted phase0.073 and phase-component -0.080. All-data standardization here is descriptive only, never predictive preprocessing. Frozen NP audit showed power features' cyclic registration ambiguity and +/-3 alias/redundancy. Raw orderedD remains, so the complete fusion input is not registration-invariant.
Fixed-kernel influence reconstruction matches saved predictions to<=1.21e-15. Median effective absolute-weight neighbors increase26.4..28.5 to36.4..39.1; centered-vector coherence falls0.184..0.200 to0.157..0.183; mean nearest-kernel similarity falls~0.72..0.74 to~0.56..0.60. Signed ridge weights are not convex averages. Feature fusion plausibly connects power-similar but phase-dissimilar states, increasing cancellation/m0 bias. Regularized conditioning was benign; pure numerical ill-conditioning is not supported. Unique cause and alternative scaling effects remain UNRESOLVED; no trials executed.

## F. Physical contract and Cartesian coordinates
C_hat=C_PW/sqrt(sum(kz/k0*|C_PW|²)), weighted unit norm to1.11e-15. P_scale is independent source-normalized POSTNP E/H power, not generally the same denominator. H2 uses weighted squared amplitudes with no TE/TM phase cross term; absolute=eta*P_scale and total=P_scale. State/P_scale error Pearson0.211/0.155/0.293 indicates distinct difficulties. Routing/phase correlation cannot establish a direct phase effect on H2 powers.
Extraction uses complete periodic six-field E/H, actual sampling coordinates, trapezoidal endpoint half weights, Fourier exp(-ikx*x-iky*y), six-field/four-channel complex LS for ±z TE/TM, passive kz, +z exp(+ikz*(zref-zsample)) and opposite -z sign. The incident IN TM gauge is applied to outputs per wavelength; reference1722nm. Fixed negative-kx TE/TM basis signs differ from zero/positive modes but are not geometry-dependent.
Cartesian is complete/invertible; no evidence of label corruption. A fixed unitary reference/basis rotation commutes with uncompressed scalar-kernel KRR and cannot improve original Euclidean error. No claim of finite-optimization MLP invariance. Polar/gauge/power-basis roundtrips max<4.72e-16, H2 preservation<3.34e-16. Power basis changes loss weighting; gauge still must retain14 coordinates/common phase. Mathematical reversibility does not confer prediction ability or compression accuracy.
EXT02 independent saved two-height fields meet frozen same-case thresholds (state max0.0077824; phase max0.0064994rad). This supports that case's de-embedding, not global absolute convergence or controlled cross-run repeatability. Local mesh-transition/PML readback gaps remain. No physical-contract conflict found; no truth/source/decoder modified.

## Model learning failure (OBSERVED / SUPPORTED_HYPOTHESIS / UNRESOLVED)
KRR heldout medians32/64/124=0.951/0.911/0.873: coverage helps but train medians0.469/0.588/0.626 still large. Prediction residual energy about training mean captures15..19% of heldout truth. Dispersed complex-vector interpolation and sparse broad neighborhoods plausibly limit it; not a unique causal proof.
MLP64/124 heldout0.921/0.924, train0.819/0.870; outer-selected refit median146 updates reused across sizes. Predicted geometry variance only2.5..5.4% of truth, with coherent m0 dominance.108 inner best updates median140.5;84 below200; none reached1000. Constrained fitting/early selection plus phase complexity is supported; longer training/capacity/representation benefit remains unproven. Near1 RMSE alone does not prove broken training; zero baseline is exactly1.

## G-H. One priority, one backup — DO NOT EXECUTE
Priority: full-rank amplitude + absolute circular phase KRR paired to existing four folds, no NP/MDC input or PCA. Proposed4 logical fits =8 internal state-head estimator fits;0 baseline/scale fits, reused actually predicted scale branch. sqrt(A) head squared and unit phase with training-only fallback; no full-state projection. Complete609D reconstruction, original H1/H2 and all tails. Explicit proposal JSON freezes suggested rules for Chat review. Wrong-phase projection may worsen error; this is a falsifiable test, not a forecast of success.
Backup only: restricted geometry-local surrogate after repeatability/nonlinearity review; no parallel arm. Seven identical-kernel Cartesian heads would be algebraically the same KRR, not a useful new candidate. Common-phase-only and simple larger MLP are not prioritized.

## I-J. Data sufficiency / HF
156G suffices for this developmental test without new HF, not for claimed global reliability. Reused124 heldouts are development exploration, not new confirmation. All32 confirmation roles and28 frozen input-side predictions remain sealed/unchanged. Controlled repetition and eventual independent confirmation need future authority; no broad HF or replay automatically justified. Original state/routing/power gates remain FAIL; unchanged P_scale remains an independent failure.

## Tests and delivery
Eight synthetic pytest checks PASS: SSE/zeros, wrapping, zero/switch gauges, oracle sign, weak-channel mask, relative phase, H2 phase independence/roundtrip. Original hashes verified before/after mathematics and final reporting. Pre-execution string typo and a read-only JSON-reader typo corrected; no historical outputs affected. Audit source contains no fit/run calls. Exact scoped allowlist commit/push only; foreign staged/dirty preserved. SHA_INVENTORY covers code, tables, reports/tests; INPUT_PINS covers original artifacts. DELIVERY_RECEIPT.json records commit/push and is excluded from self inventory/commit.
'''.replace('TABLE','\n'.join(rows))
(OUT/'FINAL_SCIENTIFIC_REPORT.md').write_bytes(report.encode())
(OUT/'CONTINUATION.md').write_bytes((f'# {M.TASK}\nCompleted zero-fit audit. Read FINAL_SCIENTIFIC_REPORT, INPUT_PINS, DIAGNOSTIC_PROTOCOL and SHA_INVENTORY first. Source HEAD d481a82796d3b2998313f7e21f19cec80eae3cab; host DESKTOP-NNE313K/dell; worktree {ROOT}; branch work/mdc-np-coupling-ml-v1. Python N:\\anaconda_envs\\RCP_LCP\\python.exe.\nAll156G/268-fit/NP88 results unchanged. Nonzero-mode contraction and amplitude/relative-phase errors coexist; common phase not primary. D6minus/repeatability unresolved. Priority amplitude/circular KRR proposal4 logical/8 internal estimator fits,0 baseline/scale, NOT EXECUTED or authorized. One backup restricted local surrogate. No solver/fit/replay/confirmation access. Await Chat scientific review; do not train automatically. Git/SHA delivery receipt provides recovery pointer. Foreign dirty/staged preserved.\n').encode())
(OUT/'.gitattributes').write_bytes(b'* -text\n')
pins=read('INPUT_PINS.json');assert A.sha(OUT/'complex_modal_audit.py')==pins['source_code_sha256']
for f in pins['files']:assert A.sha(f['path'])==f['sha256'],f['path']
assert hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT)).hexdigest()==pins['foreign_index_sha256']
files=[p for p in OUT.iterdir() if p.is_file() and p.name not in ['SHA_INVENTORY.json','DELIVERY_RECEIPT.json']]
write('SHA_INVENTORY.json',{'task':M.TASK,'files':[{'path':str(p),'sha256':A.sha(p),'bytes':p.stat().st_size} for p in sorted(files)],'self_and_delivery_receipt_excluded':True,'source_pins':'INPUT_PINS.json','execution_counts':read('ZERO_EXECUTION_AND_ISOLATION_AUDIT.json')})
print('FINAL_REPORT',A.sha(OUT/'FINAL_SCIENTIFIC_REPORT.md'));print('SHA_INVENTORY',A.sha(OUT/'SHA_INVENTORY.json'));print(r.stdout);print('FOREIGN_INDEX_UNCHANGED',pins['foreign_index_sha256'])
