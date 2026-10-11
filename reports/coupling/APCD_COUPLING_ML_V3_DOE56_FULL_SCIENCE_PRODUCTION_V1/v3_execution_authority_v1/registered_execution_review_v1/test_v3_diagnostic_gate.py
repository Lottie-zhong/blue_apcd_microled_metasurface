import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('gate',Path(__file__).parent.parent/'v3_diagnostic_gate.py')
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

@pytest.mark.parametrize('phase_offset,expected',[(0,'DIAGNOSTIC_ADVANCE_PASS'),(.1,'DIAGNOSTIC_HOLD')])
def test_complete_synthetic_receipt_flow(tmp_path,monkeypatch,phase_offset,expected):
 """Synthetic native archive/labels, explicit identity/importer doubles, no LOAD/fit."""
 import types,h5py
 rows={};records={};bases=[];decoder=gate.h1.load_h2_decoder()
 a=np.ones((21,7,2),complex);p=np.full(21,.3)
 def label(path,cid,role,geometry,c):
  np.savez(path,case_id=np.array(cid),attempt_id=np.array('attempt_001'),role=np.array(role),ordered_D_nm=geometry,wavelengths_nm=gate.C.WAVELENGTHS_NM,order_m=gate.C.ORDER_M,polarization=gate.C.POLARIZATIONS,C_hat_real=c.real,C_hat_imag=c.imag,P_scale=p)
  return pin(path)
 for bid,geometry in gate.M.ANCHORS.items():
  path=tmp_path/(bid+'.npz');d=label(path,bid,'DEVELOPMENT_GLOBAL',geometry,a)
  bases.append(dict(case_id=bid,ordered_D_nm=geometry,artifacts={'label':d,'truth_h5':d,'runner_status':d}))
 for cid,(bid,mesh) in gate.M.EXPECTED.items():
  root=tmp_path/cid;root.mkdir();(root/'run').mkdir();fsp=root/'run.fsp';fsp.write_bytes(b'SYNTHETIC_NO_SOLVER')
  hp=root/'run/run_output.h5'
  with h5py.File(hp,'w') as f:
   for k in ('Ex','Ey','Ez','Hx','Hy','Hz'):f.create_dataset('Monitor1/'+k,data=np.ones((1,2,1,21),complex))
  files={str(x.relative_to(root)).replace('\\','/'):{'bytes':x.stat().st_size,'sha256':pin(x)['sha256']} for x in (fsp,hp)}
  bp=root/'bundle_receipt.json';bp.write_text(json.dumps(dict(schema='APCD_V2_NATIVE_PAIR_V1',files=files)))
  role='DIAGNOSTIC_REPEAT' if mesh==5 else 'DIAGNOSTIC_MESH';geom=gate.M.ANCHORS[bid]
  lp=label(root/'labels.npz',cid,role,geom,a*np.exp(1j*phase_offset))
  sm=root/'source_manifest.json';sm.write_text(json.dumps({'pre_fsp_sha256':pin(fsp)['sha256']}))
  record={'case_id':cid,'source_manifest':pin(sm),'truth_h5':pin(hp)}
  v=dict(verdict='PASS',outputs=609,fresh_load_verified=True,actual_importer='load_verified_runner_case',native_session={'synthetic_only':True},record=record,labels_artifact=lp)
  (root/'validation.json').write_text(json.dumps(v))
  records[cid]=dict(phase='V3_TRUTH_VALID',entry_consumed=True,evidence=dict(validation=v,bundle=dict(path=str(root),files=files,receipt_sha256=pin(bp)['sha256'])))
  rows[cid]=dict(frozen_role=role,ordered_D_nm=geom,contract_sha256=gate.C.PHYSICAL_CONTRACT_SHA256 if mesh==5 else gate.V.MESH4_SHA,artifacts={'pre_fsp':pin(fsp)})
 ledger=tmp_path/'ledger.json';ledger.write_text(json.dumps(dict(scope='V3_DOE56',authorized_case_count=56,frozen_manifest_sha256=gate.V.DOE_SHA,truth_valid_case_ids=list(rows),labels_valid_case_ids=list(rows),case_records=records)))
 refs=tmp_path/'refs.json';refs.write_text(json.dumps({'baselines':bases}));monkeypatch.setattr(gate,'PINFILE',refs)
 original_checked=gate.checked
 def checker(d):
  if d['path']==str(refs):return refs # Isolated synthetic baseline pin, never production use.
  return original_checked(d)
 monkeypatch.setattr(gate,'checked',checker)
 monkeypatch.setattr(gate.V,'load_registry',lambda *a,**k:types.SimpleNamespace(cases=rows))
 monkeypatch.setattr(gate.V,'_verify_access_identity',lambda *a:None)
 monkeypatch.setattr(gate.V,'load_numerical_diagnostic_case',lambda *args,**k:types.SimpleNamespace(c_hat=a*np.exp(1j*phase_offset),p_scale=p))
 registry=tmp_path/'registry';registry.write_text('SYNTHETIC')
 result=gate.evaluate_ledger(pin(ledger),pin(registry),pin(registry))
 assert result['status']==expected
 assert result['no_solver_or_fit'] and len(result['comparisons'])==4
