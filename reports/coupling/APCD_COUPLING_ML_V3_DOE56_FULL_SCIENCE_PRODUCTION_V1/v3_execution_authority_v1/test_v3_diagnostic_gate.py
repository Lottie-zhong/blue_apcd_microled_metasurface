import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('gate',Path(__file__).with_name('v3_diagnostic_gate.py'))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def test_artifact_mutation_rejected(tmp_path):
 p=tmp_path/'data';p.write_bytes(b'original');d=pin(p);p.write_bytes(b'changed')
 with pytest.raises(ValueError,match='sha_mismatch'):gate.checked(d)
def test_bundle_requires_native_pair(tmp_path):
 p=tmp_path/'bundle_receipt.json';p.write_text(json.dumps({'schema':'APCD_V2_NATIVE_PAIR_V1','files':{}}))
 with pytest.raises(ValueError,match='native_pair_missing'):gate.verified_bundle(pin(p))
def test_bundle_traversal_rejected(tmp_path):
 p=tmp_path/'bundle_receipt.json';p.write_text(json.dumps({'schema':'APCD_V2_NATIVE_PAIR_V1','files':{'../../outside':{'bytes':1,'sha256':'a'*64},'run.fsp':{},'run/run_output.h5':{}}}))
 with pytest.raises(ValueError,match='path_escape'):gate.verified_bundle(pin(p))
def test_wrong_label_identity_rejected(tmp_path):
 p=tmp_path/'fixture.npz';np.savez(p,case_id=np.array('SEALED'),attempt_id=np.array('attempt_001'))
 with pytest.raises(ValueError,match='label_case_attempt'):gate.label_arrays(pin(p),'NUMERIC','DIAGNOSTIC_REPEAT',[1]*6)
def test_undefined_significant_phase_holds():
 a=np.ones((21,7,2),complex);b=a.copy();b[0,0,0]=0
 with pytest.raises(ValueError,match='undefined_significant'):gate.M.compare_arrays(a,np.ones(21),b,np.ones(21),decode=lambda *a:None)
def test_all_four_required():
 with pytest.raises(ValueError,match='four_diagnostics'):gate.M.advancement({},gate.PROTOCOL_SHA)
