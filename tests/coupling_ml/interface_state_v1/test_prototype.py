import copy
import tempfile
from pathlib import Path
import numpy as np
import prototype as p

def run():
    results={}
    k=np.array([-8.,-np.pi,0.,np.pi,9.]);b,o,g=p.fold(k,2.)
    assert np.max(abs(k-b-g))<1e-12
    results['k_closure']='PASS'
    assert np.array_equal(p.fold(b+g,2.)[1],o)
    results['reciprocal_roundtrip']='PASS'
    basis=p.basis(np.array([[0.],[.4],[1.4]]),np.array([[0.,.2]]),1.)
    a=np.random.default_rng(43).normal(size=(4,3,2))+1j*np.random.default_rng(44).normal(size=(4,3,2))
    e,h=p.reconstruct(a,basis)
    assert np.allclose(p.project(e,h,basis),a,atol=1e-12)
    results['SP_reconstruction']='PASS'
    back=p.propagate(p.propagate(a,basis[3],-.013),basis[3],.013)
    assert np.allclose(back,a,atol=1e-12)
    results['deembedding_roundtrip']='PASS'
    assert basis[3][0,0]==1 and basis[3][-1,0].imag>0
    results['propagating_evanescent']='PASS'
    x=np.linspace(-1,1,17);kx,ax,inv,audit=p.transform_axis(x)
    f=np.exp(.7j*x)
    assert np.linalg.norm(inv@ax@f-f)/np.linalg.norm(f)<1e-10
    results['Fourier_reconstruction']='PASS'
    d=p.schema(Path('authority'));p.check_metadata(d)
    results['metadata_completeness']='PASS'
    bad=copy.deepcopy(d);bad['authority']['time_harmonic_convention']['authority_status']='FROZEN'
    try:p.check_metadata(bad)
    except ValueError:pass
    else:raise AssertionError('unresolved promoted')
    results['unresolved_not_frozen']='PASS'
    with tempfile.TemporaryDirectory() as tmp:
        q=Path(tmp);p.save_npz(q/'a.npz',{'a':a});p.save_npz(q/'b.npz',{'a':a})
        assert p.sha(q/'a.npz')==p.sha(q/'b.npz')
    results['deterministic_serialization']='PASS'
    return results

if __name__=='__main__':print(run())
