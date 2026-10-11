from pathlib import Path
import sys,ast
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts/coupling_ml'));sys.path.insert(0,str(Path(__file__).parent))
import local_scale_phase_pilot as M
def test_complete_zero_fit_mathematics():
    assert M.synthetic()['status']=='PASS'
def test_known_nearest_neighbor_scale():
    x=np.zeros((3,6));x[:,0]=[0,1,3]
    gamma,l,nn=M.scale(x)
    assert np.array_equal(nn,[1,1,4]) and l==1 and gamma==.5
def test_kernel_reindexing_psd_and_query_shape():
    x=np.random.default_rng(12).normal(size=(8,6));g,_,_=M.scale(x);k=M.kernel(x,x,g);perm=[3,0,2,1,5,4,7,6]
    assert np.array_equal(M.kernel(x[perm],x[perm],g),k[np.ix_(perm,perm)])
    assert np.linalg.eigvalsh(k).min()>-1e-12
    assert M.kernel(x[:2],x,g).shape==(2,8)
def test_training_scale_does_not_consume_queries():
    x=np.random.default_rng(16).normal(size=(8,6));before=M.scale(x)[0]
    M.kernel(np.ones((4,6))*1e4,x,before)
    assert M.scale(x)[0]==before
def test_invalid_neighbors_fail_closed():
    for bad in [np.ones((3,6)),np.ones((1,6)),np.full((3,6),np.nan),np.zeros((3,5))]:
        with pytest.raises(ValueError):M.scale(bad)
def test_single_fit_call_only_inside_training_and_no_oracle():
    src=Path(M.__file__).read_text(encoding='utf-8');tree=ast.parse(src)
    fits=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='fit']
    assert len(fits)==1
    train=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='train')
    assert fits[0] in list(ast.walk(train))
    assert 'oracle_alignment(' not in src and 'lumapi' not in src
