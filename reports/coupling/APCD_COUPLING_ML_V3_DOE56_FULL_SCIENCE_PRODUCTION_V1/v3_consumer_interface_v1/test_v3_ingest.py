from pathlib import Path
from dataclasses import replace
import json
import pytest
from k6_v2_pipeline import v3_ingest as V, ingest as I,contracts as C
from k6_v2_pipeline import v3_numerical_core as N

@pytest.fixture
def registry():
 f=I._json(I.ROOT/V.DOE_REL)
 rows={x['case_id']:{**x,'frozen_role':x['role'],
   'execution_role':V.EXECUTION_ROLES[x['role']],
   'ordered_D_nm':tuple(x['ordered_D_nm']),
   'contract_sha256':V.MESH4_SHA if x['mesh_nm']==4 else C.PHYSICAL_CONTRACT_SHA256}
   for x in f['cases']}
 return V.V3Registry(rows,'a'*64,'synthetic_registry',False)

def record(reg,cid):
 r=reg.cases[cid]
 return {'case_id':cid,'attempt_id':'attempt_001','role':r['frozen_role'],
 'ordered_D_nm':list(r['ordered_D_nm']),'physical_contract_sha256':r['contract_sha256']}

@pytest.mark.parametrize('entry',['load_development_runner_case','load_numerical_diagnostic_case'])
def test_sealed_before_artifact_access(registry,monkeypatch,entry):
 monkeypatch.setattr(I,'_artifact',lambda *a:pytest.fail('response_access'))
 for cid in registry.cases:
  if cid.startswith('K6V3_BLIND_'):
   with pytest.raises(I.DataAccessError,match='before_response_access'):
    getattr(V,entry)(record(registry,cid),registry=registry)

def test_unknown_identity(registry):
 with pytest.raises(I.DataAccessError,match='unknown_case'):
  V.load_development_runner_case({'case_id':'UNREGISTERED'},registry=registry)

def test_diagnostic_cannot_train(registry):
 for cid in ['K6V3_NUM_REPEAT_A1','K6V3_NUM_MESH4_A1']:
  with pytest.raises(I.DataAccessError,match='before_response_access'):
   V.load_development_runner_case(record(registry,cid),registry=registry)

def test_dev_cannot_diagnostic(registry):
 with pytest.raises(I.DataAccessError,match='before_response_access'):
  V.load_numerical_diagnostic_case(record(registry,'K6V3_DEV_GLOBAL_G001'),registry=registry)

def test_mesh_contract_not_parent(registry):
 r=record(registry,'K6V3_NUM_MESH4_A1');r['physical_contract_sha256']=C.PHYSICAL_CONTRACT_SHA256
 with pytest.raises(I.DataAccessError,match='contract_mismatch'):
  V.load_numerical_diagnostic_case(r,registry=registry)

def test_geometry_order_is_preserved(registry):
 r=record(registry,'K6V3_DEV_GLOBAL_G001');r['ordered_D_nm']=r['ordered_D_nm'][1:]+r['ordered_D_nm'][:1]
 with pytest.raises(I.DataAccessError,match='contract_mismatch'):
  V.load_development_runner_case(r,registry=registry)

def test_publication_escape(registry,tmp_path,monkeypatch):
 monkeypatch.setattr(V,'_verify_access_identity',lambda *a:None)
 r=record(registry,'K6V3_DEV_GLOBAL_G001');r['receipt']={'path':str(tmp_path.parent/'outside.json'),'sha256':'a'*64}
 with pytest.raises(I.DataAccessError,match='path_escape'):
  V.load_published_development_label(r,registry=registry,publication_root=tmp_path)

def test_legacy_public_loader_still_rejects_new_roles(registry):
 with pytest.raises(I.DataAccessError,match='only_accepts_development_roles'):
  I.load_verified_runner_case(record(registry,'K6V3_DEV_GLOBAL_G001'),expected_role='DEVELOPMENT_GLOBAL_V3')

def test_shared_core_rejects_unregistered_contract():
 with pytest.raises(I.DataAccessError,match='unsupported_expected_contract'):
  N._load_runner_truth({}, {}, set(), expected_contract_sha256='b'*64)

def test_privileged_token_cannot_consume(registry,monkeypatch):
 monkeypatch.setattr(V,'_actual_sid',lambda:'S-1-5-21-2958591235-2706656562-1210676212-1001')
 with pytest.raises(I.DataAccessError,match='restricted_consumer'):
  V._verify_access_identity(registry,'DEVELOPMENT_CONSUMER')

def test_consumer_cannot_impersonate_custodian(registry,monkeypatch):
 monkeypatch.setattr(V,'_actual_sid',lambda:'S-1-5-21-SYNTHETIC')
 with pytest.raises(I.DataAccessError,match='not_custodian'):
  V._verify_access_identity(registry,'PRODUCTION_CUSTODIAN')
