from pathlib import Path
import json,csv,hashlib,subprocess
import numpy as np
import h5py
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
O=R/'reports'/'coupling'/'APCD_COUPLING_272G_K6_CYCLIC_EQUIVARIANCE_V1'
def readj(n): return json.loads((O/n).read_text(encoding='utf-8'))
def readcsv(n):
    with (O/n).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writej(n,v): (O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def add_section(path,marker,section):
    text=path.read_text(encoding='utf-8')
    if marker in text: text=text[:text.index(marker)].rstrip()
    path.write_text(text+'\n\n'+section.strip()+'\n',encoding='utf-8')

metrics=readj('CYCLIC_H2_PSCALE_DIAGNOSTICS.json')
orders=metrics['order_metrics_mean_by_model_order']
ps=metrics['p_scale_high_region_mean_by_model']
model_order=['A_original','B_augmented','C_six_view','D_augmented_six_view']
labels={'A_original':'A','B_augmented':'B','C_six_view':'C','D_augmented_six_view':'D'}

# Read the existing, labels-valid G001 H5 lineage without modifying it.
case='K6AL_COMPLEX_R03_G001'
attempt=R/'reports'/'coupling'/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1'/'science_outputs'/case/'attempt_001'
receipt=json.loads((attempt/'SCIENCE_RECEIPT.json').read_text(encoding='utf-8'))
truth_path=attempt/'truth.h5'
native_path=Path(receipt['native_h5'][0]['path'])
with h5py.File(truth_path,'r') as f:
    physical_contract_sha=str(f.attrs['physical_contract_sha256'])
    source_fsp_sha=str(f.attrs['source_fsp_sha256'])
if physical_contract_sha!='32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5':
    raise ValueError('representative H5 physical contract does not match frozen K6 contract')
def coord(a):
    a=np.asarray(a,dtype=float)
    return {'count':int(a.size),'min':float(a.min()),'max':float(a.max()),'first':float(a.reshape(-1)[0]),'last':float(a.reshape(-1)[-1])}
native={};truth={}
with h5py.File(native_path,'r') as f:
    for group in f:
        g=f[group]
        if not isinstance(g,h5py.Group):continue
        native[group]={axis:coord(g[axis][()]) for axis in ('x','y','z') if axis in g}
with h5py.File(truth_path,'r') as f:
    eh=f['EH_complex']
    for plane in ('IN','PRENP','POSTNP'):
        truth[plane]={axis:coord(eh[f'{plane}_{axis}'][()]) for axis in ('x','y','z')}
native_by_plane={'IN':'Monitor0','PRENP':'Monitor1','POSTNP':'Monitor2'}
coord_parity={}
with h5py.File(native_path,'r') as fn,h5py.File(truth_path,'r') as ft:
    for plane,group in native_by_plane.items():
        ng=fn[group];tg=ft['EH_complex']
        row={}
        for axis in ('x','y','z'):
            a=np.asarray(ng[axis][()],float).reshape(-1)*1e-6
            b=np.asarray(tg[f'{plane}_{axis}'][()],float).reshape(-1)
            if a.shape!=b.shape: row[axis]={'shape_match':False,'max_abs_m':None}
            else: row[axis]={'shape_match':True,'max_abs_m':float(np.max(np.abs(a-b)))}
        coord_parity[plane]=row
max_dx=max(coord_parity[p]['x']['max_abs_m'] for p in coord_parity)
max_dy=max(coord_parity[p]['y']['max_abs_m'] for p in coord_parity)
max_dz=max(coord_parity[p]['z']['max_abs_m'] for p in coord_parity)

contract_doc=O/'K6_CYCLIC_SYMMETRY_CONTRACT.md'
h5_section=f'''## H5 coordinates and z-reference bookkeeping

The representative existing labels-valid case `{case}` was read in place for a coordinate audit; this is not a rotated-pair FDTD parity test. Its receipt records `attempt_001`, `ML_TRAINING_GRADE`, source/setup SHA `{source_fsp_sha}`, truth-H5 SHA `{receipt['truth_h5_sha256']}`, and native-H5 SHA `{receipt['native_h5'][0]['sha256']}`; `truth.h5` stores the frozen physical-contract SHA `{physical_contract_sha}`. These are the already recorded identities; the large H5 files were not rehashed or modified.

The Runner native H5 stores monitor x/y coordinates centered at zero (Monitor0 x `[-0.87,+0.87]`, y `[-0.145,+0.145]`; 349 × 59 samples). In the canonical `truth.h5`, `EH_complex` stores the same coordinates in SI metres, x `[-8.70e-7,+8.70e-7]`, y `[-1.45e-7,+1.45e-7]`. After applying the native-to-canonical coordinate scale `1e-6`, the maximum absolute differences are x `{max_dx:.3e} m`, y `{max_dy:.3e} m`, z `{max_dz:.3e} m` for IN, PRENP, and POSTNP. This establishes the H5 lateral phase origin at `(x,y)=(0,0)` for the inspected case.

The actual H5 sample z planes for this case are IN `-100.787739 nm`, PRENP `1152 nm`, POSTNP `1802 nm`. The frozen extractor de-embeds to its pinned z references IN `-50 nm`, PRENP `1202 nm`, POSTNP `1722 nm` (`pw_complex_floquet_state_v1.py::_REFERENCE_NM`). The Fourier phase is evaluated on the actual recorded x/y coordinates with origin zero; the source contract is normal incidence with amplitude 1 and phase 0. The cyclic action changes only x; it does not alter these z references, monitor ordering, global incident-phase gauge, or TE/TM order.

Machine-readable audit: `CYCLIC_H5_COORDINATE_AUDIT.json`. The H5 coordinate inspection corroborates the code convention for one existing native case; no physical rotated-geometry pair was present, so real-solver cyclic parity remains **NOT MEASURED**.'''
add_section(contract_doc,'## H5 coordinates and z-reference bookkeeping',h5_section)

order_lines=[]
for m in range(-3,4):
    a=orders['A_original'][str(m)];d=orders['D_augmented_six_view'][str(m)]
    order_lines.append(f"| {m:+d} | {a['eta_MAE']:.5f} | {d['eta_MAE']:.5f} | {d['eta_MAE']-a['eta_MAE']:+.5f} | {a['power_MAE']:.5f} | {d['power_MAE']:.5f} | {d['power_MAE']-a['power_MAE']:+.5f} |")
ps_lines=[]
for m in model_order:
    q=ps[m]
    ps_lines.append(f"| {labels[m]} | {q['train_q75_threshold']:.4f} | {q['high_region_MAE']:.4f} | {q['high_region_bias_prediction_minus_truth']:+.4f} | {q['high_region_underprediction_fraction']:.3f} | {q['high_region_truth_mean']:.4f} | {q['high_region_prediction_mean']:.4f} |")
h2md=f'''# Frozen-H2 order and high-P_scale diagnostics

This is a zero-solver, zero-fit follow-up over the existing 272G dataset and saved OOF predictions. Frozen H2 was reloaded from its pinned module and recomputed for every model/seed prediction. Maximum parity difference against stored OOF H2 outputs was exactly 0 for both eta and absolute-order power. There were 336 order rows (4 models × 4 folds × 3 seeds × 7 orders) and 48 high-P_scale rows. All are development-fold evidence, not an independent test.

## Per-order H2 MAE: baseline A versus candidate D

Means pool the fixed fold × seed rows descriptively. Lower is better.

| Order m | A eta MAE | D eta MAE | D−A | A absolute-power MAE | D absolute-power MAE | D−A |
|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(order_lines)}

The propagating center order `m=0` has the largest eta and order-power MAE in both A and D; D reduces its eta MAE from 0.12339 to 0.08332 and absolute-order power MAE from 0.04615 to 0.03066. D lowers both errors for all seven orders in these fixed-fold means. This describes current validation predictions only.

## High-P_scale underestimation

For each fold, the high region is validation points with true `P_scale` at or above the 75th percentile of training-fold `P_scale` pooled over training geometries and wavelengths. The cut is fitted on training values only; validation truth is used solely to define the evaluated subgroup. Table entries are descriptive means across the 12 fold-seed rows per model. Average high-region sample count is 147 per fold-seed row.

| Model | Train q75 cut | High-region MAE | Prediction−truth bias | Underprediction fraction | Mean truth | Mean prediction |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(ps_lines)}

D improves high-region absolute error versus A (0.1000 to 0.0658), while the signed bias remains negative (-0.0351) and underprediction occurs in about 69% of high-region points. Thus the absolute-error gain does not remove the high-`P_scale` underestimation pattern. The overall P_scale MAE also improves (0.06543 to 0.05066).

## Artifacts and limits

- `CYCLIC_H2_ORDER_METRICS.csv`: fold × seed × model × order eta and absolute-power metrics.
- `CYCLIC_PSCALE_HIGH_REGION_DIAGNOSTICS.csv`: train-fold q75 cut and validation tail metrics.
- `CYCLIC_H2_PSCALE_DIAGNOSTICS.json`: H2 parity identity, row counts and aggregate values.
- `CYCLIC_H5_COORDINATE_AUDIT.json`: representative native/canonical H5 coordinate ranges and receipt lineage.

The repeated development folds are correlated and have been reused for model selection. These diagnostics do not certify final generalization or authorize a new dataset batch.'''
(O/'CYCLIC_H2_PSCALE_DIAGNOSTICS.md').write_text(h2md+'\n',encoding='utf-8')

h5_audit={'schema':'K6_CYCLIC_H5_COORDINATE_AUDIT_V1','case_id':case,'attempt_id':receipt['attempt_id'],'numerical_grade':receipt['numerical_grade'],
 'physical_contract_sha256':physical_contract_sha,'source_fsp_sha256':source_fsp_sha,'truth_h5_path':str(truth_path),'truth_h5_sha256_from_receipt':receipt['truth_h5_sha256'],
 'native_h5_path':str(native_path),'native_h5_sha256_from_receipt':receipt['native_h5'][0]['sha256'],
 'native_monitor_coordinates':native,'canonical_truth_h5_coordinates_m':truth,'monitor_correspondence':native_by_plane,
 'native_to_truth_coordinate_scale':1e-6,'coordinate_comparison_max_abs_m':coord_parity,
 'extractor_reference_planes_nm':{'IN':-50.0,'PRENP':1202.0,'POSTNP':1722.0},
 'source_phase':{'theta_deg':0.0,'phi_deg':0.0,'amplitude':1.0,'phase_deg':0.0},
 'phase_origin_xy_m':[0.0,0.0],'scope':'one existing labels-valid sample; H5 read-only; not a rotated-geometry FDTD parity test; no hashes recomputed'}
writej('CYCLIC_H5_COORDINATE_AUDIT.json',h5_audit)

extra=f'''## H2 order metrics and high-P_scale audit

All saved OOF predictions were replayed through the pinned frozen H2: stored and recomputed eta/absolute-order arrays matched exactly. D reduces mean per-order eta and order-power MAE relative to A for all seven orders, with `m=0` still the largest-error order. For validation points above the training-fold `P_scale` q75, D lowers mean absolute error versus A, but its mean signed bias remains negative and high-region underprediction remains common. Full fold/seed results and the q75 rule are in `CYCLIC_H2_PSCALE_DIAGNOSTICS.md`, `CYCLIC_H2_ORDER_METRICS.csv`, and `CYCLIC_PSCALE_HIGH_REGION_DIAGNOSTICS.csv`.'''
add_section(O/'CYCLIC_EQUIVARIANCE_DIAGNOSTICS.md','## H2 order metrics and high-P_scale audit',extra)

decision=f'''## Direct answers to the requested scientific questions

1. **Does the K6 cyclic shift satisfy the frozen contract?** Yes for the ideal periodic geometry and saved-label transform: the six-center lattice, x/y periodicity, uniform full-cell stack layers, normal-incidence source, and 5 nm mesh support an exact +290 nm translation. This is algebra/code/H5-coordinate evidence; a rotated-geometry FDTD pair was not present.
2. **What is the complex phase sign?** With the actual extractor kernel `exp(-i G_m x)`, `T^k=roll(D,+k)` corresponds to `C_m(T^kD)=C_m(D) exp(-i 2πmk/6)`; both TE and TM use the same factor. Inference aligns with the conjugate positive phase before averaging.
3. **Are there cyclic duplicates in 272G?** No: 272 ordered geometries form 272 canonical cyclic orbits.
4. **Do the existing folds split cyclic-equivalent cases?** No observed orbit has multiple cases; exact case/family/cyclic train-validation overlaps are zero in all four folds. All wavelengths remain grouped by geometry.
5. **Does six-view augmentation improve 28D complex learning?** On the fixed development folds, B improves complex NRMSE over A in 12/12 fold-seed pairs; D also improves every reported loss metric over C in 12/12 pairs. This is repeat-development evidence, not independent generalization.
6. **Is phase-aligned six-view inference better than direct NN3?** C improves the mean H2/ranking metrics against A but does not beat B on mean complex, TM, routing, or phase errors. D is the best development candidate when combined with augmentation.
7. **Do P(+1), Spearman, and Top20 improve together?** Their fold/seed means all improve from A to D. Spearman improves in 12/12 A→B pairs and 9/12 C→D pairs; Top20 improves in only 4/12 pairs for either comparison. Top20 therefore does not show stable paired improvement.
8. **Which model should be retained?** Keep D as the best development candidate, not as a production-ready or H1-passing model. H1 remains HOLD.
9. **Is P_scale spectral low-rank learning necessary now?** Not established by this experiment. Cyclic augmentation improves overall P_scale MAE (0.06543→0.05066) and high-region MAE (0.1000→0.0658), but high-region signed bias stays negative and underprediction remains frequent. First do a zero-solver, train-fold-only common spectral-trend/residual diagnostic; do not add a low-rank model solely from this result.
10. **Is another 50G needed now, and what should it cover?** This study does not justify automatically starting another 50G. H1 is still HOLD and the 124 cases are reused development data. If a new batch is later authorized after independent confirmation planning, prioritize six-dimensional coverage in geometries associated with high-`P_scale` underprediction and the higher-error `m=0` response while retaining broad coverage; do not spend the batch on synthetic cyclic copies.

H1 remains a development gate, all confirmation data remain sealed, and this study used zero FDTD runs and zero new Solver Entries.'''
add_section(O/'FORWARD_MODEL_SCIENTIFIC_DECISION.md','## Direct answers to the requested scientific questions',decision)

# Extend the existing focused source/checkpoint inventory with the supplemental scripts.
sha_path=O/'CYCLIC_CHECKPOINT_SHA256.csv'
with sha_path.open(encoding='utf-8-sig',newline='') as f:
    rd=csv.DictReader(f); fieldnames=rd.fieldnames; sha_rows=list(rd)
for filename in ['COMPUTE_CYCLIC_H2_PSCALE_DIAGNOSTICS.py','CYCLIC_SUPPLEMENTAL_AUDIT.py']:
    p=O/filename
    if not p.is_file(): continue
    full=str(p); new={'file':full,'size_bytes':str(p.stat().st_size),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'role':'reproducibility_source_or_config'}
    sha_rows=[r for r in sha_rows if r.get('file')!=full]
    sha_rows.append(new)
with sha_path.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fieldnames);w.writeheader();w.writerows(sha_rows)

print(json.dumps({'h2_module_sha256':metrics['H2_sha256'],'h2_parity':metrics['frozen_H2_recomputation_parity'],
 'order_rows':metrics['order_metric_rows'],'p_scale_rows':metrics['p_scale_region_rows'],'h5_coordinate_comparison':coord_parity,
 'h1':'HOLD','new_fits':0,'solver_entries':0,'updated_reports':['K6_CYCLIC_SYMMETRY_CONTRACT.md','CYCLIC_EQUIVARIANCE_DIAGNOSTICS.md','FORWARD_MODEL_SCIENTIFIC_DECISION.md'],'created':['CYCLIC_H2_PSCALE_DIAGNOSTICS.md','CYCLIC_H5_COORDINATE_AUDIT.json']},ensure_ascii=False,indent=2))
