from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts/coupling_ml'))
import numpy as np
import structured_phase_pilot as S
def test_numerical_boundaries():
    assert S.numerical_tests()['status']=='PASS'
def test_negative_sqrt_not_clipped():
    c,info=S.reconstruct(-np.ones((2,294)),np.tile([1.,0.],(2,294)),np.ones((21,7,2),complex))
    assert np.all(c==1) and info['negative_sqrt_mask'].all()
def test_nearzero_phase_fallback_threshold():
    fallback=np.full((21,7,2),1j);v=np.tile([S.PHASE_EPS/2,0.],(1,294));c,info=S.reconstruct(np.ones((1,294)),v,fallback)
    assert np.all(c==1j) and info['fallback_mask'].all()
def test_training_scaler_immutable():
    y=np.arange(4*294,dtype=float).reshape(4,294);s=S.head_scaler(y);before=s['mean'].copy();scale=s['scale'];S.transform(y*1e9,s)
    assert np.array_equal(s['mean'],before) and s['scale']==scale
def test_phase_canonicalization_keeps_weak_amplitude():
    c=np.ones((2,21,7,2),complex);c[:,:,:,0]=1e-20j;a,p,mask,truth,u=S.targets(c)
    assert np.all(~mask[:,:,:,0]) and np.all(a.reshape(2,21,7,2)[:,:,:,0]>0)
    assert np.all(p.reshape(2,21,7,2,2)[:,:,:,0,:]==[1,0])
def test_raw_roundtrip_h2():
    rng=np.random.default_rng(2);c=rng.normal(size=(2,21,7,2))+1j*rng.normal(size=(2,21,7,2));a,u=S.D.unit(c)
    cp,info=S.reconstruct(np.sqrt(a).reshape(2,294),np.stack([u.real,u.imag],-1).reshape(2,588),np.ones((21,7,2),complex))
    dec=S.h1.load_h2_decoder();p=np.ones((2,21));x=S.h1.reconstruct_h2(c,p,dec);y=S.h1.reconstruct_h2(cp,p,dec)
    for k in ['eta','absolute_order','total_power']:assert np.max(abs(x[k]-y[k]))<1e-12
