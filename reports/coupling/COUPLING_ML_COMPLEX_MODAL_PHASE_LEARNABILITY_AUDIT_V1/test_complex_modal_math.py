from pathlib import Path
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
