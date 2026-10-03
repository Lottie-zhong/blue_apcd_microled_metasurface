import importlib.util
import os
from pathlib import Path
import numpy as np
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import torch

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'scripts/coupling_ml/coupling_ml_32g_amplitude_circular_phase_forward_poc_v1.py'
spec=importlib.util.spec_from_file_location('amplitude_phase_poc',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_uncompressed_amplitude_unit_phase_roundtrip_including_weak_coordinates():
    rng=np.random.default_rng(7)
    c=(rng.normal(size=(4,21,7,2))+1j*rng.normal(size=(4,21,7,2))).astype(np.complex128)
    c[:, :, 0, 0]*=1e-5
    amp=np.abs(c);u=np.ones_like(c);nz=amp>0;u[nz]=c[nz]/amp[nz]
    assert np.max(np.abs(amp*u-c))<=1e-12
    assert np.any(m.weak_mask(c)&nz)

def test_phase_decoder_returns_unit_complex_and_handles_near_zero_vectors():
    v=torch.tensor([0+0j,1e-12+0j,3+4j,complex(-1,1e-14)],dtype=torch.complex64)
    u=m.unit_safe_torch(v)
    assert torch.isfinite(u.real).all() and torch.isfinite(u.imag).all()
    assert torch.allclose(torch.abs(u),torch.ones_like(torch.abs(u)),atol=1e-6)
    assert u[0]==1+0j and u[1]==1+0j

def test_circular_phase_is_continuous_across_principal_angle_wrap():
    d=2e-6
    a=torch.tensor(np.pi-d,dtype=torch.float64);b=torch.tensor(-np.pi+d,dtype=torch.float64)
    ua=torch.complex(torch.cos(a),torch.sin(a));ub=torch.complex(torch.cos(b),torch.sin(b))
    loss=1-torch.real(ua*torch.conj(ub))
    assert loss.item()<1e-10

def test_circular_phase_loss_is_independent_of_predicted_amplitude():
    truth=torch.tensor([1+0j],dtype=torch.complex64)
    weak=torch.tensor([False])
    predicted=torch.tensor([0+1j],dtype=torch.complex64)
    low=m.circular_phase_loss(.1*predicted,truth,weak)
    high=m.circular_phase_loss(5.*predicted,truth,weak)
    assert torch.allclose(low,high,atol=1e-7)
    assert abs(float(low)-1.0)<1e-6

def test_common_phase_alignment_remains_oracle_only_and_relative_phase_is_invariant():
    rng=np.random.default_rng(27)
    truth=(.2+rng.random((21,7,2)))*np.exp(1j*rng.uniform(-np.pi,np.pi,(21,7,2)))
    pred=truth*np.exp(1j*.37)
    d=m.state_detail(truth,pred)
    assert d['state']>0.1
    assert d['oracle_common_phase_aligned_state']<1e-12
    assert abs(d['oracle_common_phase_explained_sse_fraction']-1.0)<1e-12
    assert d['relative_phase_rmse_rad']<1e-12

def test_error_attribution_reports_geometry_wavelength_and_order_dimensions():
    rng=np.random.default_rng(33)
    truth=(.2+rng.random((1,21,7,2)))*np.exp(1j*rng.uniform(-np.pi,np.pi,(1,21,7,2)))
    pred=truth*(1.0+.02j)
    eta=np.full((1,21,7),1/7)
    power=np.full((1,21,7),1/7)
    scale=np.ones((1,21))
    wv,od=m.attribution_rows('TEST',truth,pred,eta,power,scale,scale,np.ones((1,21,7)),0.,['G01'],tuple(range(440,461)))
    assert len(wv)==21 and len(od)==7
    assert all('pscale_relative_abs_error' in row for row in wv)
    assert all('order_m' in row and 'absolute_order_rmse' in row for row in od)

def test_c1_basis_rank_budget_is_fit_only_and_prediction_reconstruction_is_finite():
    rng=np.random.default_rng(12);n=10
    amp=.2+rng.random((n,21,7,2));phase=rng.uniform(-np.pi,np.pi,(n,21,7,2))
    c=amp*np.exp(1j*phase);c[:, :, 0, 0]*=1e-5
    basis=m.C1Basis().fit(c,np.arange(8))
    assert all(p.n_samples_==8 for p in basis.amp+basis.phase)
    assert all(p.n_components_==2 for p in basis.amp+basis.phase)
    prediction=basis.decode_numpy(basis.encode(c[8:]))
    assert prediction.shape==(2,21,7,2)
    assert np.isfinite(prediction.real).all() and np.isfinite(prediction.imag).all()
    assert np.all(np.abs(prediction)>=0)

def test_frozen_cartesian_and_amplitude_phase_parameter_counts():
    frozen=importlib.util.spec_from_file_location('frozen_m5_test',ROOT/'scripts/coupling_ml/pw_k6_stage1_32g_frozen_model_v1.py')
    fm=importlib.util.module_from_spec(frozen);frozen.loader.exec_module(fm)
    assert sum(p.numel() for p in fm.Net().parameters())==2684
    assert sum(p.numel() for p in m.C1Net().parameters())==4056
