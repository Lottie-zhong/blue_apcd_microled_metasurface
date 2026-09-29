#!/usr/bin/env python
"""Independent ZERO-SOLVER validator for NP_K6 complex forward benchmark."""
from pathlib import Path
import json, hashlib, numpy as np, pandas as pd, sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/np_k6_complex_forward_surrogate_benchmark_v1'
SRC=ROOT/'outputs/np_k6_hf22_complex_scattering_state_extraction_v1'

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def fail(msg):
    raise AssertionError(msg)

def main():
    prereg=json.load(open(OUT/'preregistration.json',encoding='utf-8'))
    bench=json.load(open(OUT/'benchmark_manifest.json',encoding='utf-8'))
    fail('solver calls not zero') if bench.get('solver_calls')!=0 or prereg.get('solver_calls')!=0 else None
    for k in ('new_data','sealed_target_read','coupling_h1_read','full_data_fit'):
        if bench.get(k,0)!=0: fail(f'{k} != 0')
    if not (ROOT/'reports/NP_K6_COMPLEX_FORWARD_SURROGATE_BENCHMARK_V1.md').exists(): fail('report missing')
    src=SRC/'complex_scattering_state_long.csv'; d=pd.read_csv(src)
    if len(d)!=8712 or d.geometry_id.nunique()!=22 or d.case_id.nunique()!=44: fail('dataset membership mismatch')
    if sorted(d.wavelength_nm.unique().round(6).tolist()) != [float(x) for x in range(445,456)]: fail('wavelength contract mismatch')
    if set(d.polarization.unique()) != {'p','s'}: fail('polarization contract mismatch')
    if not bench.get('source_truth_sha256')==sha(src): fail('source hash mismatch')
    if not prereg['split_contract']['outer'].startswith('22-fold'): fail('split contract mismatch')
    if prereg['phase_contract']['deembedding'] is not False: fail('phase contract changed')
    if prereg['dataset_contract']['geometry_order'].find('no sorting')<0: fail('geometry order contract changed')
    if bench.get('jones_matrix')!='FULL_2x2_JONES_MATRIX_NOT_AVAILABLE': fail('Jones limitation missing')
    if OUT.stat().st_mtime > (OUT/'preregistration.json').stat().st_mtime: pass
    expected={'row_wise__M0_Ridge','row_wise__M1_RBF_KernelRidge','row_wise__M2_compact_MLP','spectral__M0_Ridge','spectral__M1_RBF_KernelRidge','spectral__M2_compact_MLP','spectral__M3_order_local_spectral_latent'}
    got=set()
    for p in OUT.glob('oof_*.npz'):
        tag=p.stem[len('oof_'):]; got.add(tag)
        a=np.load(p,allow_pickle=False)
        pred=a['pred']; truth=a['truth']; geom=a['geometry']; pol=a['polarization']
        if pred.shape!=truth.shape or np.isnan(pred).any() or np.isinf(pred).any(): fail(f'OOF invalid {tag}')
        if len(np.unique(geom))!=22: fail(f'geometry fold coverage {tag}')
        expected_per_geom=22 if tag.startswith('row_wise__') else 2
        counts=pd.Series(geom).value_counts()
        if set(counts.tolist())!={expected_per_geom}: fail(f'fold group count {tag}: {counts.to_dict()}')
    if got!=expected: fail(f'OOF model set mismatch: {got}')
    from datetime import datetime, timezone
    prereg_time=datetime.fromisoformat(prereg['created_utc'].replace('Z','+00:00')).timestamp()
    if any(p.stat().st_mtime < prereg_time for p in OUT.glob('oof_*.npz')): fail('fit timestamp predates preregistration timestamp')
    print(json.dumps({'status':'PASS','solver_calls':0,'rows':len(d),'geometries':22,'cases':44,'oof_models':len(got),'phase_threshold':prereg['phase_contract']['significance_threshold_absolute_efficiency']},indent=2))
if __name__=='__main__': main()
