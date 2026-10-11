"""Exact V3 identities layered over the existing frozen numerical importer.

OS custody isolation is enforced by the owner's restricted process token/ACLs;
these role guards supplement it and never claim to replace it.
"""
from pathlib import Path
from dataclasses import dataclass
import json
from . import contracts as C, ingest as I
from .consumer_exclusions import assert_no_quarantine_linkage
from .v3_numerical_core import _load_runner_truth

DOE_REL = 'reports/coupling/APCD_COUPLING_ML_V3_DOE56_OVERNIGHT_PRODUCTION_DESIGN_V1/V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json'
DOE_SHA = 'f0231e22b169f82f9239d7e89c3455f877ea85d493c422274f664c9dd91ba667'
MESH4_SHA = 'f8a59ebd65b168e52f76bde1f4bb7f91d545dfd5fd1838a32ab79e0548967d92'
EXECUTION_ROLES = {'DIAGNOSTIC_REPEAT':'DIAGNOSTIC_5NM',
 'DIAGNOSTIC_MESH':'DIAGNOSTIC_4NM','DEVELOPMENT_LOCAL':'DEVELOPMENT',
 'DEVELOPMENT_GLOBAL':'DEVELOPMENT','SEALED_LOCAL':'SEALED_EVALUATION',
 'SEALED_GLOBAL':'SEALED_EVALUATION'}
DEVELOPMENT = {'DEVELOPMENT_LOCAL','DEVELOPMENT_GLOBAL'}
DIAGNOSTIC = {'DIAGNOSTIC_REPEAT','DIAGNOSTIC_MESH'}

@dataclass(frozen=True)
class V3Registry:
    cases: dict
    sha256: str
    path: str
    production_admitted: bool
    consumer_sid: str | None = None

def load_registry(path, expected_sha256, *, root=None, identity_authority=None):
    """Registry is an integrity binding; installation/release checked by owner."""
    root=Path(root) if root else I.ROOT
    p=Path(path)
    I._need(I.sha256_file(p)==expected_sha256,'v3_registry_sha_mismatch')
    frozen_path=root/DOE_REL
    I._need(I.sha256_file(frozen_path)==DOE_SHA,'v3_frozen_doe_sha_mismatch')
    frozen={x['case_id']:x for x in I._json(frozen_path)['cases']}
    doc=I._json(p);rows=doc.get('cases',[])
    I._need(len(rows)==56 and len({x['case_id'] for x in rows})==56
        and {x['case_id'] for x in rows}==set(frozen),'v3_registry_exact_identity_set')
    checked={}
    for row in rows:
        cid=row['case_id'];f=frozen[cid];role=row.get('frozen_role')
        I._need(role==f['role'] and row.get('execution_role')==EXECUTION_ROLES[role]
          and row.get('ordered_D_nm')==f['ordered_D_nm']
          and row.get('attempt_id')=='attempt_001' and row.get('mesh_nm')==f['mesh_nm'],
          'v3_registry_identity_role_geometry_mesh:'+cid)
        contract=MESH4_SHA if f['mesh_nm']==4 else C.PHYSICAL_CONTRACT_SHA256
        desc=row['artifacts']['physical_contract']
        I._need(desc.get('sha256')==contract and I.sha256_file(desc['path'])==contract,
          'v3_contract_binding:'+cid)
        if f['mesh_nm']==4:
            bd=row.get('actual_contract_binding',{})
            I._need(bd.get('sha256') and I.sha256_file(bd['path'])==bd['sha256'],
                'v3_mesh4_actual_binding_missing:'+cid)
            b=I._json(bd['path'])
            I._need(b.get('case_id')==cid and b.get('attempt_id')=='attempt_001'
              and b.get('actual_physical_contract')==desc and b.get('core_step_nm')==[4,4,4]
              and b.get('training_allowed') is False,'v3_mesh4_binding_semantics:'+cid)
        checked[cid]=dict(row,role=role,physical_contract=desc,contract_sha256=contract,
          ordered_D_nm=tuple(f['ordered_D_nm']),ordered_geometry_sha256=f['geometry_sha256'])
    admitted=doc.get('status')=='PRODUCTION_ADMITTED' and doc.get('not_a_production_release') is False
    consumer_sid=doc.get('identity_boundary',{}).get('development_consumer_sid')
    if identity_authority is not None:
        ip=Path(identity_authority['path'])
        I._need(I.sha256_file(ip)==identity_authority['sha256'],'v3_identity_authority_sha')
        identity=I._json(ip);consumer=identity.get('consumer',{})
        I._need(identity.get('schema')=='V3_SEALED_IDENTITY_AUTHORITY_V1'
          and identity.get('custodian','').casefold()=='desktop-nne313k\\dell'
          and consumer.get('groups')==['S-1-5-32-545']
          and consumer.get('enabled') is True,'v3_identity_authority_semantics')
        sid=consumer.get('sid');I._need(isinstance(sid,str) and sid.startswith('S-1-5-21-')
          and (consumer_sid is None or consumer_sid==sid),'v3_identity_sid_conflict')
        consumer_sid=sid
    return V3Registry(checked,expected_sha256,str(p),admitted,consumer_sid)

def _actual_sid():
    import csv,io,subprocess
    output=subprocess.check_output(['whoami','/user','/fo','csv','/nh'],text=True)
    return next(csv.reader(io.StringIO(output)))[1]

def _token_security():
    """Read current process token; no caller-supplied elevation evidence."""
    import ctypes as ct
    from ctypes import wintypes as wt
    import subprocess
    k=ct.WinDLL('kernel32',use_last_error=True)
    a=ct.WinDLL('advapi32',use_last_error=True)
    k.GetCurrentProcess.restype=wt.HANDLE
    a.OpenProcessToken.argtypes=[wt.HANDLE,wt.DWORD,ct.POINTER(wt.HANDLE)]
    a.GetTokenInformation.argtypes=[wt.HANDLE,ct.c_int,ct.c_void_p,wt.DWORD,ct.POINTER(wt.DWORD)]
    k.CloseHandle.argtypes=[wt.HANDLE]
    token=wt.HANDLE()
    if not a.OpenProcessToken(k.GetCurrentProcess(),8,ct.byref(token)):raise ct.WinError(ct.get_last_error())
    def data(kind):
        size=wt.DWORD();a.GetTokenInformation(token,kind,None,0,ct.byref(size))
        buf=ct.create_string_buffer(size.value)
        if not a.GetTokenInformation(token,kind,buf,size.value,ct.byref(size)):raise ct.WinError(ct.get_last_error())
        return buf
    try:
        elevated=bool(ct.cast(data(20),ct.POINTER(wt.DWORD)).contents.value)
        restricted=int(ct.cast(data(11),ct.POINTER(wt.DWORD)).contents.value)
        groups=subprocess.check_output(['whoami','/groups','/fo','csv','/nh'],text=True)
        return {'elevated':elevated,'restricted_sid_count':restricted,
            'administrators_group_present':'S-1-5-32-544' in groups}
    finally:k.CloseHandle(token)

def _verify_access_identity(registry, access_role):
    sid=_actual_sid()
    custodian='S-1-5-21-2958591235-2706656562-1210676212-1001'
    if access_role=='PRODUCTION_CUSTODIAN':
        I._need(sid==custodian,'v3_not_custodian_token')
    elif access_role=='DEVELOPMENT_CONSUMER':
        I._need(registry.consumer_sid and registry.consumer_sid!=custodian
            and sid==registry.consumer_sid,'v3_not_registered_restricted_consumer_token')
        security=_token_security()
        I._need(not security['elevated'] and security['restricted_sid_count']>0
            and not security['administrators_group_present'],
            'v3_consumer_token_not_nonadmin_restricted')
    else:raise I.DataAccessError('v3_unknown_access_role')

def _identity(record, registry, allowed):
    # Identity and purpose checked before touching any response descriptor.
    cid=str(record.get('case_id',''))
    I._need(cid in registry.cases,'v3_unknown_case')
    r=registry.cases[cid];role=r['frozen_role']
    I._need(role in allowed,'v3_sealed_diagnostic_or_wrong_role_rejected_before_response_access')
    I._need(record.get('role')==role and record.get('attempt_id')=='attempt_001'
      and tuple(record.get('ordered_D_nm',()))==r['ordered_D_nm']
      and record.get('physical_contract_sha256')==r['contract_sha256'],
      'v3_record_identity_contract_mismatch')
    assert_no_quarantine_linkage(record,consumer='truth_import')
    return r

def _runner_case(record, registry, allowed, *, root=None):
    r=_identity(record,registry,allowed)
    # Verify all six stored field components, not just the four used by flux.
    import numpy as np
    raw_path,_=I._artifact(record,'raw_npz')
    with np.load(raw_path,allow_pickle=False) as z:
        for plane in ('IN','PRENP','POSTNP'):
            for field in ('Ex','Ey','Ez','Hx','Hy','Hz'):
                key=plane+'_'+field
                I._need(key in z.files and np.iscomplexobj(z[key])
                    and np.isfinite(z[key]).all(),'v3_missing_nonfinite_complex_eh:'+key)
    # Caller's request+release+registry SHA must be independently owner validated.
    # Never infer entry/terminal state from a setup LOAD proof.
    out=_load_runner_truth(record,registry.cases,{r['frozen_role']},root=root,
        expected_contract_sha256=r['contract_sha256'])
    role=(C.ROLE_LOCAL_AXIS if r['frozen_role']=='DEVELOPMENT_LOCAL'
          else C.ROLE_GLOBAL_DEV if r['frozen_role']=='DEVELOPMENT_GLOBAL'
          else r['frozen_role'])
    return C.CaseTruth(out.case_id,out.attempt_id,role,out.ordered_D_nm,
        out.c_hat,out.p_scale,out.eta,out.absolute_order,
        dict(out.provenance,v3_registry_sha256=registry.sha256,
          frozen_doe_sha256=DOE_SHA,scientific_role=r['frozen_role'],
          execution_role=r['execution_role'],training_label_eligible=r['frozen_role'] in DEVELOPMENT))

def load_development_runner_case(record, *, registry, root=None):
    return _runner_case(record,registry,DEVELOPMENT,root=root)

def load_numerical_diagnostic_case(record, *, registry, root=None):
    _verify_access_identity(registry,'PRODUCTION_CUSTODIAN')
    return _runner_case(record,registry,DIAGNOSTIC,root=root)

def load_verified_runner_case(record, *, expected_role, root=None, registry,
                              access_role='PRODUCTION_CUSTODIAN'):
    """Owner validator-compatible entry; custody can validate but not publish sealed."""
    _verify_access_identity(registry,access_role)
    I._need(record.get('role')==expected_role,'v3_expected_role_mismatch')
    allowed=set(EXECUTION_ROLES) if access_role=='PRODUCTION_CUSTODIAN' else DEVELOPMENT
    r=_identity(record,registry,allowed)
    # This trusted custody entry preserves the frozen scientific role for validator.
    import numpy as np
    rp,_=I._artifact(record,'raw_npz')
    with np.load(rp,allow_pickle=False) as z:
        for plane in ('IN','PRENP','POSTNP'):
            for field in ('Ex','Ey','Ez','Hx','Hy','Hz'):
                key=plane+'_'+field
                I._need(key in z.files and np.iscomplexobj(z[key])
                    and np.isfinite(z[key]).all(),'v3_missing_nonfinite_complex_eh:'+key)
    return _load_runner_truth(record,registry.cases,{r['frozen_role']},root=root,
        expected_contract_sha256=r['contract_sha256'])

def load_published_development_label(descriptor, *, registry, publication_root):
    """Restricted consumer reads only a SHA-bound development publication.

    Custodian supplies receipt+label through the dedicated development view.
    Never offers a generic sealed loader or a reveal flag.
    """
    _identity(descriptor,registry,DEVELOPMENT)
    _verify_access_identity(registry,'DEVELOPMENT_CONSUMER')
    base=Path(publication_root).resolve()
    def confined(key):
        d=descriptor[key];p=Path(d['path']).resolve()
        I._need(p.is_relative_to(base),'v3_publication_path_escape')
        I._need(I.sha256_file(p)==d['sha256'],'v3_publication_sha:'+key)
        return p
    receipt=I._json(confined('receipt'));p=confined('label')
    I._need(receipt.get('schema')=='V3_DEVELOPMENT_LABEL_PUBLICATION_V1'
      and receipt.get('status')=='PASS' and receipt.get('training_label_eligible') is True
      and receipt.get('case_id')==descriptor['case_id']
      and receipt.get('attempt_id')=='attempt_001'
      and receipt.get('role')==descriptor['role']
      and receipt.get('ordered_D_nm')==descriptor['ordered_D_nm']
      and receipt.get('physical_contract_sha256')==C.PHYSICAL_CONTRACT_SHA256
      and receipt.get('registry_sha256')==registry.sha256
      and receipt.get('label_sha256')==descriptor['label']['sha256']
      and receipt.get('h2_validation',{}).get('status')=='PASS',
      'v3_development_publication_receipt')
    import numpy as np
    from . import h1
    with np.load(p,allow_pickle=False) as z:
        I._need(str(z['case_id'].item())==descriptor['case_id']
          and str(z['attempt_id'].item())=='attempt_001'
          and str(z['role'].item())==descriptor['role']
          and np.array_equal(z['ordered_D_nm'],descriptor['ordered_D_nm'])
          and np.array_equal(z['wavelengths_nm'],C.WAVELENGTHS_NM)
          and np.array_equal(z['order_m'],C.ORDER_M)
          and list(z['polarization'])==list(C.POLARIZATIONS),'v3_published_coordinate_identity')
        c=z['C_hat_real']+1j*z['C_hat_imag'];ps=z['P_scale'];eta=z['eta'];ab=z['absolute_order']
        C.pack_model_target(c,ps)
        I._need(eta.shape==(21,7) and ab.shape==(21,7)
          and np.isfinite(eta).all() and np.isfinite(ab).all(),'v3_published_power_shape_finite')
        h=h1.reconstruct_h2(c,ps,h1.load_h2_decoder())
        # Existing published labels retain native grating tolerances; no new gate.
        I._need(np.allclose(eta.sum(1),1,atol=1e-6,rtol=0)
          and np.allclose(ab,eta*ps[:,None],atol=1e-9,rtol=1e-3),
          'v3_published_power_mapping')
    r=registry.cases[descriptor['case_id']]
    role=C.ROLE_LOCAL_AXIS if r['frozen_role']=='DEVELOPMENT_LOCAL' else C.ROLE_GLOBAL_DEV
    return C.CaseTruth(descriptor['case_id'],'attempt_001',role,r['ordered_D_nm'],
        c,ps,eta,ab,dict(receipt['provenance'],v3_registry_sha256=registry.sha256,
        scientific_role=r['frozen_role'],published_label_sha256=descriptor['label']['sha256']))
