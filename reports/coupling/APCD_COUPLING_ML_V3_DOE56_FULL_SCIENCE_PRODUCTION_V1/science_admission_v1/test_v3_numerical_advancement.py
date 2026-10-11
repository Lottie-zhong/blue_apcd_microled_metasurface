import numpy as np
import pytest
from v3_numerical_advancement import compare_arrays,advancement,EXPECTED
from k6_v2_pipeline import h1

@pytest.fixture
def data():
 c=np.ones((21,7,2),complex);p=np.full(21,.3)
 decoder=h1.load_h2_decoder()
 return c,p,lambda c,p:h1.reconstruct_h2(c,p,decoder)

def test_identical_and_frozen_h2(data):
 c,p,d=data;r=compare_arrays(c,p,c,p,decode=d)
 assert r['comparison_pass'] and all(v==0 for v in r['maxima'].values())

def test_known_phase_no_oracle(data):
 c,p,d=data;r=compare_arrays(c,p,c*np.exp(.06j),p,decode=d)
 assert not r['gates']['significant_phase_rmse_rad'] and not r['gates']['state_relative_l2']
 assert r['gates']['routing_max_abs'] and r['gates']['total_power_relative']

def test_known_scale_error(data):
 c,p,d=data;r=compare_arrays(c,p,c,1.02*p,decode=d)
 assert not r['gates']['total_power_relative'] and r['gates']['state_relative_l2']

def test_single_wavelength_failure_not_pooled(data):
 c,p,d=data;b=c.copy();b[10]*=np.exp(.06j)
 assert not compare_arrays(c,p,b,p,decode=d)['comparison_pass']

def test_weak_phase_not_main_gate(data):
 c,p,d=data;c[:,0,0]=1e-6;b=c.copy();b[:,0,0]*=-1
 assert compare_arrays(c,p,b,p,decode=d)['comparison_pass']

def test_zero_significant_and_nonfinite_rejected(data):
 c,p,d=data;b=c.copy();b[:,0,0]=0
 with pytest.raises(ValueError,match='undefined'):compare_arrays(c,p,b,p,decode=d)
 with pytest.raises(ValueError,match='nonfinite'):compare_arrays(c,p,c,p*float('nan'),decode=d)

def test_no_advance_missing_identity(data):
 with pytest.raises(ValueError):advancement({},'a'*64)
 c,p,d=data;comparison=compare_arrays(c,p,c,p,decode=d)
 rs={k:{'case_id':k,'pair_identity_verified':True,'durable_receipts_verified':True,'protocol_sha256':'a'*64,'comparison':comparison} for k in EXPECTED}
 assert advancement(rs,'a'*64)['advance_to_development']
 rs[next(iter(rs))]['comparison']={**comparison,'comparison_pass':False}
 assert not advancement(rs,'a'*64)['advance_to_development']
