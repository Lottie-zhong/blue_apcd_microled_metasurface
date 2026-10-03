import importlib.util,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parents[2]/'scripts/coupling_ml/coupling_ml_32g_complex_state_representation_diagnostic_v1.py'
spec=importlib.util.spec_from_file_location('representation_diagnostic',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_gauge_switch_wrap_zero_and_two_components():
 c=np.zeros((1,4,7,2),complex)
 c[0,0,0,0]=2*np.exp(3.13j);c[0,0,1,1]=np.exp(-3.13j)
 c[0,1,1,1]=3*np.exp(-3.13j);c[0,1,0,0]=np.exp(3.13j)
 c[0,2,0,:]=[1j,-1j]
 a,p,q,ix=m.gauge(c)
 assert ix[0,0]!=ix[0,1]
 assert np.max(abs(m.ungauge(a,p,q)-c))<=1e-12
 assert p[0,3]==0
 assert np.max(abs(c-abs(c)*np.exp(1j*np.angle(c))))<=1e-12
def test_common_vs_relative_phase_oracle():
 t=np.ones((2,7,2),complex);p=t*np.exp(1.2j)
 d=m.diagnose(t,p)
 assert d['amplitude_relative_rmse']==0
 assert d['oracle_common_aligned_rmse']<1e-12
 assert abs(d['oracle_common_explained_sse_fraction']-1)<1e-12
 p[:,0,:]=t[:,0,:]*np.exp(-1.2j)
 d=m.diagnose(t,p)
 assert d['oracle_common_aligned_rmse']>.1
 assert d['oracle_order_aligned_rmse']<1e-12
def test_amplitude_phase_exact_identity_and_weak_energy():
 t=np.ones((2,7,2),complex);t[...,0]=1e-8
 p=t.copy();p[...,0]*=-1;p[...,1]*=.7*np.exp(.2j)
 d=m.diagnose(t,p)
 assert abs(d['amplitude_sse_fraction']+d['phase_sse_fraction']-1)<1e-12
 assert d['weak_truth_energy_fraction']<1e-12
 assert d['weak_complex_sse_fraction']<1e-12
def test_source_has_no_solver_runner_or_process_entry():
 import ast
 tree=ast.parse(P.read_text(encoding='utf-8'))
 imports=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
  if isinstance(n,ast.ImportFrom):imports.append(n.module or '')
 assert not any(any(k in name.lower() for k in ['lumapi','runner','gpu_bundle']) for name in imports)
 calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='run']
 assert len(calls)==1  # Only explicit ['git', '-C', ...] subprocess in git().
 assert "['git','-C',str(R),*args]" in P.read_text(encoding='utf-8')
