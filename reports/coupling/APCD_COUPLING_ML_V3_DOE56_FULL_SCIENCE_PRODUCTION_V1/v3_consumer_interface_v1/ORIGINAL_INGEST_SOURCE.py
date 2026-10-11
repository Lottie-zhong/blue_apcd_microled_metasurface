"""Fail-closed K6 V2 truth ingestion and role isolation."""
from __future__ import annotations
import csv,hashlib,json,os,threading,datetime,importlib.util,sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping,Any
import numpy as np
from . import contracts as C
from .consumer_exclusions import assert_no_quarantine_linkage, load_consumer_exclusion_registry
ROOT=Path(__file__).resolve().parents[3]
ADMIT=Path("reports/coupling/COUPLING_ML_K6_V2_DATASET_ADMISSION_PREPARATION_V1")
REV=Path("reports/coupling/COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2")
OLD=Path("reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1")
REG_SHA="22560277c3cd7032e48de6ef5b0023986eefe5aba3c3de07b6eff2bf51dc33f9"
ALLOW_SHA="7b9b103a742877dbe9b980ad530a68d667f54c91caedddbed60b906ed3a70830"
OLD_NPZ_SHA="fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28"
_DEV={C.ROLE_LOCAL_AXIS,C.ROLE_GLOBAL_DEV}
_ORDER=tuple((m,0) for m in range(-3,4))
class DataAccessError(ValueError): pass
def _need(x,m):
    if not x: raise DataAccessError(m)
def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def _json(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def _canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def geometry_sha(D): return hashlib.sha256(",".join(str(int(v)) for v in D).encode("ascii")).hexdigest()
def _float_array_sha256(value):
    """Hash finite float arrays using stable 15-significant-digit decimal values."""
    a=np.asarray(value,dtype=float)
    body={"shape":list(a.shape),"values":[format(float(x),".15g") for x in a.ravel(order="C")]}
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode("ascii")).hexdigest()

_POWER_SUPPLEMENT_SCHEMA="COUPLING_K6_V2_POWER_MAPPING_SUPPLEMENT_V1"
_POWER_AUDIT_SCHEMA="COUPLING_K6_V2_POWER_MAPPING_AUDIT_V1"
_POWER_SUPPLEMENT_CASE="K6LDA1_DEV_D1_M05"
_POWER_MAPPING={
    "eta_source":"power_fraction_of_monitor_total",
    "p_scale_source":"POSTNP_periodic_EH_Poynting_over_cell_area_times_IN_REF_incident_power_per_area",
    "source_fraction":"P_scale*eta",
}
def _validate_power_mapping_supplement(descriptor,record,artifact_hashes,p_scale,eta):
    """Validate the sole case-scoped, opt-in correction; default ingestion stays strict."""
    _need(isinstance(descriptor,Mapping),"power_mapping_supplement_descriptor_invalid")
    path=Path(str(descriptor.get("path","")))
    digest=descriptor.get("sha256")
    _need(path.is_file() and isinstance(digest,str) and sha256_file(path)==digest,
          "power_mapping_supplement_missing_or_sha_mismatch")
    doc=_json(path)
    _need(isinstance(doc,Mapping),"power_mapping_supplement_schema_invalid")
    cid=str(record.get("case_id","")); D=tuple(map(int,record.get("ordered_D_nm",())))
    _need(doc.get("schema")==_POWER_SUPPLEMENT_SCHEMA and doc.get("status")=="PASS"
          and doc.get("training_label_eligible") is True,
          "power_mapping_supplement_not_pass_or_training_eligible")
    _need(cid==_POWER_SUPPLEMENT_CASE and record.get("role")==C.ROLE_LOCAL_AXIS,
          "power_mapping_supplement_scope_forbidden")
    _need(doc.get("case_id")==cid and doc.get("attempt_id")==record.get("attempt_id")=="attempt_001"
          and doc.get("role")==record.get("role") and doc.get("ordered_D_nm")==list(D)
          and doc.get("ordered_geometry_sha256")==geometry_sha(D)
          and doc.get("physical_contract_sha256")==C.PHYSICAL_CONTRACT_SHA256,
          "power_mapping_supplement_case_binding_mismatch")
    _need(doc.get("artifact_sha256")==artifact_hashes,
          "power_mapping_supplement_artifact_binding_mismatch")
    numeric_hashes={"p_scale":_float_array_sha256(p_scale),"eta":_float_array_sha256(eta),
        "source_fraction":_float_array_sha256(np.asarray(p_scale)[:,None]*np.asarray(eta))}
    _need(doc.get("numeric_sha256")==numeric_hashes,
          "power_mapping_supplement_numeric_binding_mismatch")
    _need(doc.get("mapping")==_POWER_MAPPING,"power_mapping_supplement_mapping_mismatch")
    audit_desc=doc.get("independent_audit",{})
    _need(isinstance(audit_desc,Mapping),"power_mapping_audit_descriptor_invalid")
    ap=Path(str(audit_desc.get("path","")))
    _need(ap.is_file() and isinstance(audit_desc.get("sha256"),str)
          and sha256_file(ap)==audit_desc.get("sha256"),
          "power_mapping_audit_missing_or_sha_mismatch")
    audit=_json(ap)
    _need(isinstance(audit,Mapping),"power_mapping_audit_schema_invalid")
    _need(audit.get("schema")==_POWER_AUDIT_SCHEMA and audit.get("status")=="PASS"
          and audit.get("case_id")==cid and audit.get("attempt_id")==record.get("attempt_id")
          and audit.get("physical_contract_sha256")==C.PHYSICAL_CONTRACT_SHA256
          and audit.get("ordered_geometry_sha256")==geometry_sha(D)
          and audit.get("artifact_sha256")==artifact_hashes
          and audit.get("numeric_sha256")==numeric_hashes
          and audit.get("training_label_eligible") is True
          and audit.get("mapping")==_POWER_MAPPING,
          "power_mapping_audit_binding_or_status_invalid")
    return digest

@dataclass(frozen=True)
class FrozenRegistry:
    old32: Mapping[str,Mapping[str,Any]]
    development: Mapping[str,Mapping[str,Any]]
    confirmation: Mapping[str,Mapping[str,Any]]
    confirmation_role_sha256: str
    pointset_sha256: str
    registration_sha256: str
def load_frozen_case_registry(root=None):
    root=Path(root) if root else ROOT
    load_consumer_exclusion_registry(root)
    ap=root/ADMIT; rp=root/REV
    pkgp=ap/"CASE_REGISTRATION_PACKAGE_V1.json"; allp=ap/"DEVELOPMENT_CASE_ALLOWLIST_V1.json"; candp=rp/"GLOBAL_DATASET_CANDIDATES_V2.csv"
    _need(sha256_file(pkgp)==REG_SHA,"registration_package_sha_mismatch")
    _need(sha256_file(allp)==ALLOW_SHA,"development_allowlist_sha_mismatch")
    _need(sha256_file(candp)==C.V2_CANDIDATE_CSV_SHA256,"candidate_pointset_sha_mismatch")
    pkg,allow=_json(pkgp),_json(allp); rows=pkg.get("cases",[])
    _need(len(rows)==160 and len({x.get("case_id") for x in rows})==160,"registration_count_or_duplicate")
    pcdesc=rows[0].get("physical_contract",{}); pcp=Path(pcdesc.get("path",""))
    _need(pcdesc.get("sha256")==C.PHYSICAL_CONTRACT_SHA256 and pcp.is_file() and sha256_file(pcp)==C.PHYSICAL_CONTRACT_SHA256,"physical_contract_authority_sha_mismatch")
    pc=_json(pcp)
    _need(set(pc.get("wavelengths_nm",[]))==set(C.WAVELENGTHS_NM) and pc.get("references_nm",{}).get("MON_POSTNP")==C.REFERENCE_PLANE_NM and pc.get("monitors",{}).get("output")=="MON_POSTNP","physical_contract_semantics_mismatch")
    with candp.open(encoding="utf-8-sig",newline="") as f: cm={x["case_id"]:x for x in csv.DictReader(f)}
    _need(len(cm)==160 and set(cm)=={x["case_id"] for x in rows},"candidate_registration_ids_mismatch")
    dev,conf={},{}
    for r in rows:
        cid,role=r["case_id"],r["role"]; D=tuple(map(int,r["ordered_D_nm"]))
        _need(len(D)==6 and geometry_sha(D)==r["ordered_geometry_sha256"],"registered_geometry_hash_mismatch:"+cid)
        _need(r.get("attempt_id")=="attempt_001" and r.get("physical_contract",{}).get("sha256")==C.PHYSICAL_CONTRACT_SHA256 and r.get("physical_contract",{}).get("path")==pcdesc.get("path"),"registration_contract_mismatch:"+cid)
        _need(tuple(int(cm[cid][f"D{i}_nm"]) for i in range(1,7))==D and cm[cid].get("role")==role,"candidate_row_mismatch:"+cid)
        q=dict(r); q["ordered_D_nm"]=D
        if role in _DEV: dev[cid]=q
        elif role in C.CONFIRMATION_ROLES or role=="SEALED_CONFIRMATION_GLOBAL":
            q["effective_role"]=C.ROLE_GLOBAL_STRESS_CONFIRM if r.get("boundary_stress") else role
            conf[cid]=q
        else: raise DataAccessError("unknown_registration_role:"+str(role))
    _need(len(dev)==128 and len(conf)==32,"registered_role_counts_mismatch")
    _need(sum(x["role"]==C.ROLE_LOCAL_AXIS for x in dev.values())==12 and sum(x["role"]==C.ROLE_GLOBAL_DEV for x in dev.values())==116,"development_strata_mismatch")
    _need(sum(x["role"]==C.ROLE_LOCAL_CONFIRM for x in conf.values())==4 and sum(x["role"]=="SEALED_CONFIRMATION_GLOBAL" for x in conf.values())==28,"confirmation_strata_mismatch")
    _need(sum(bool(x.get("boundary_stress")) for x in conf.values())==1,"stress_count_mismatch")
    olda=_json(root/OLD/"PW_K6_32G_DATASET_AUTHORITY_V1.json")
    oldids=list(allow.get("old32_case_ids",[]))
    _need(len(oldids)==32 and olda.get("physical_contract_sha256")==C.PHYSICAL_CONTRACT_SHA256 and olda.get("ordered_geometry_ids")==oldids,"old32_allowlist_order_mismatch")
    _need(set(allow.get("new_development_case_ids",[]))==set(dev) and set(allow.get("allowed_case_ids",[]))==set(oldids)|set(dev),"development_allowlist_mismatch")
    oldgeo=olda.get("ordered_D_nm",[]); _need(len(oldgeo)==32,"old32_authority_geometry_count_mismatch")
    old={cid:{"case_id":cid,"attempt_id":"attempt_001","role":C.ROLE_OLD32,"ordered_D_nm":tuple(map(int,oldgeo[i]))} for i,cid in enumerate(oldids)}
    rr=[{"case_id":k,"registered_role":v["role"],"boundary_stress":bool(v.get("boundary_stress")),"effective_role":v["effective_role"],"ordered_geometry_sha256":v["ordered_geometry_sha256"]} for k,v in sorted(conf.items())]
    return FrozenRegistry(old,dev,conf,_canon(rr),C.V2_CANDIDATE_CSV_SHA256,REG_SHA)

def _old32(root,registry):
    p=root/OLD; authp=p/"PW_K6_32G_DATASET_AUTHORITY_V1.json"; datap=p/"dataset_truth_32g.npz"
    _need(sha256_file(authp)==C.DATASET_AUTHORITY_SHA256 and sha256_file(datap)==OLD_NPZ_SHA,"old32_frozen_sha_mismatch")
    a=_json(authp); inv=_json(p/"artifact_hashes.json")
    _need(a.get("status")=="PASS" and a.get("geometry_count")==32 and a.get("physical_contract_sha256")==C.PHYSICAL_CONTRACT_SHA256 and inv.get(datap.name)==OLD_NPZ_SHA,"old32_authority_mismatch")
    with np.load(datap,allow_pickle=False) as z:
        ids=[str(x) for x in z["case_ids"].tolist()]; g=np.asarray(z["ordered_D_nm"],int); c=np.asarray(z["C_hat"],complex); ps=np.asarray(z["P_scale"],float); eta=np.asarray(z["eta"],float); ab=np.asarray(z["absolute_order_power"],float)
    _need(len(ids)==32 and len(set(ids))==32 and g.shape==(32,6) and c.shape==(32,21,7,2) and ps.shape==(32,21) and eta.shape==(32,21,7) and ab.shape==(32,21,7),"old32_shape_mismatch")
    _need(np.isfinite(c.real).all() and np.isfinite(c.imag).all() and np.isfinite(ps).all() and (ps>0).all() and np.isfinite(eta).all() and np.isfinite(ab).all(),"old32_nonfinite_or_nonpositive")
    _need(np.allclose(eta.sum(2),1,rtol=0,atol=1e-9) and np.allclose(ab,ps[:,:,None]*eta,rtol=1e-9,atol=1e-12),"old32_factorization_mismatch")
    prov={x["case_id"]:x for x in a["case_provenance"]}
    _need(ids==list(registry.old32) and ids==a.get("ordered_geometry_ids") and set(ids)==set(prov),"old32_case_id_set_or_order_mismatch")
    _need(np.array_equal(g,np.asarray(a.get("ordered_D_nm"),dtype=np.int64)),"old32_authority_geometry_matrix_mismatch")
    out=[]
    for i,cid in enumerate(ids):
        q=prov[cid]; D=tuple(map(int,g[i]))
        _need(D==tuple(q["ordered_D_nm"])==registry.old32[cid]["ordered_D_nm"],"old32_ordered_geometry_mismatch:"+cid)
        out.append(C.CaseTruth(cid,"attempt_001",C.ROLE_OLD32,D,c[i],ps[i],eta[i],ab[i],{"dataset_npz_sha256":OLD_NPZ_SHA,"dataset_authority_sha256":C.DATASET_AUTHORITY_SHA256,"state_sha256":q.get("state_sha256"),"state_metadata_sha256":q.get("state_metadata_sha256"),"cohort":q.get("cohort")}))
    return tuple(out)

def load_old32_engineering_diagnostic(root=None, registry=None):
    """Load only the hash-pinned legacy 32G bundle for the 24/8 integration audit."""
    root = Path(root) if root else ROOT
    registry = registry or load_frozen_case_registry(root)
    cases = _old32(root, registry)
    if any(case.role != C.ROLE_OLD32 for case in cases):
        raise DataAccessError("engineering_diagnostic_old32_role_mismatch")
    return C.CaseCollection(
        purpose="old32_engineering_diagnostic",
        cases=cases,
        manifest_sha256=OLD_NPZ_SHA,
        provenance={
            "dataset_npz_sha256": OLD_NPZ_SHA,
            "dataset_authority_sha256": C.DATASET_AUTHORITY_SHA256,
            "physical_contract_sha256": C.PHYSICAL_CONTRACT_SHA256,
            "response_role": C.ROLE_OLD32,
            "confirmation_responses_opened": False,
            "diagnostic_only": True,
        },
    )

def _artifact(r,k):
    x=r.get(k); _need(isinstance(x,dict),"missing_artifact_descriptor:"+k)
    p=Path(x.get("path","")); h=x.get("sha256","")
    _need(p.is_file() and len(h)==64 and sha256_file(p)==h,"artifact_missing_or_sha_mismatch:"+k)
    return p,h

def _load_runner_truth(record,role_map,expected_roles,*,root=None,power_supplement=None):
    assert_no_quarantine_linkage(record,consumer="truth_import",root=root)
    cid=str(record.get("case_id","")); _need(cid in role_map,"case_id_not_in_role_allowlist:"+cid); reg=role_map[cid]
    role=record.get("role"); _need(role in expected_roles and role in (reg["role"],reg.get("effective_role")),"role_not_allowed:"+str(role))
    D=tuple(map(int,record.get("ordered_D_nm",())))
    _need(record.get("attempt_id")==reg["attempt_id"]=="attempt_001" and D==reg["ordered_D_nm"] and geometry_sha(D)==reg["ordered_geometry_sha256"],"case_identity_mismatch:"+cid)
    _need(record.get("physical_contract_sha256")==C.PHYSICAL_CONTRACT_SHA256,"physical_contract_mismatch:"+cid)
    _need(record.get("status") in ("DONE","RECOVERED_TRUTH_VALID") and record.get("solver_invocations")==1 and record.get("replay_count",0)==0,"truth_not_single_entry_valid:"+cid)
    mp,mh=_artifact(record,"source_manifest"); man=_json(mp)
    assert_no_quarantine_linkage(man,consumer="truth_import",root=root)
    _need(man.get("case_id")==cid and man.get("attempt_id")==record["attempt_id"] and man.get("geometry")==list(D) and man.get("physical_contract_sha256")==C.PHYSICAL_CONTRACT_SHA256,"source_manifest_identity_mismatch:"+cid)
    pf=man.get("pre_fsp_sha256",""); _need(isinstance(pf,str) and len(pf)==64,"source_manifest_pre_fsp_hash_missing:"+cid)
    smp,smh=_artifact(record,"state_metadata"); rmp,rmh=_artifact(record,"raw_metadata"); op,oh=_artifact(record,"orders_json")
    sm,rm,od=_json(smp),_json(rmp),_json(op)
    for metadata in (sm,rm,od): assert_no_quarantine_linkage(metadata,consumer="truth_import",root=root)
    sp,sh=_artifact(record,"state_npz"); rnp,rnh=_artifact(record,"raw_npz")
    _need(sm.get("sha256")==sh and sm.get("schema_version")=="PW_COMPLEX_FLOQUET_STATE_V1" and sm.get("planes")==["IN","PRENP","POSTNP"] and sm.get("directions")==["+z","-z"] and sm.get("polarizations")==["TE","TM"],"state_metadata_invalid:"+cid)
    rawdesc=rm.get("raw_complex_fields",{})
    _need(rawdesc.get("sha256")==rnh and rawdesc.get("schema")=="APCD_PW_RAW_COMPLEX_FIELDS_V1","raw_metadata_npz_binding_mismatch:"+cid)
    _need(rm.get("case_id")==cid and rm.get("attempt_id")==record["attempt_id"],"raw_metadata_identity_mismatch:"+cid)
    _need(Path(rawdesc.get("path","")).resolve()==rnp.resolve(),"raw_metadata_path_mismatch:"+cid)
    pcdesc=reg.get("physical_contract",{}); pcp=Path(pcdesc.get("path",""))
    _need(pcp.is_file() and sha256_file(pcp)==C.PHYSICAL_CONTRACT_SHA256,"physical_contract_file_sha_mismatch:"+cid)
    pc=_json(pcp); rc=rm.get("contract",{})
    _need(all(rc.get(k)==pc.get(k) for k in ("materials","monitors","references_nm","samples_nm","stack_layers","wavelengths_nm")),"raw_physical_contract_mismatch:"+cid)
    _need(rc.get("references_nm",{}).get("MON_POSTNP")==C.REFERENCE_PLANE_NM and rc.get("samples_nm",{}).get("MON_POSTNP")==1800.0 and rc.get("wavelengths_nm")==list(C.WAVELENGTHS_NM),"raw_reference_or_wavelength_contract_mismatch:"+cid)
    cs=rm.get("canonical_state",{})
    _need(cs.get("axis_order")==["plane","wavelength","order","direction","polarization"] and cs.get("directions")==list(C.DIRECTIONS) and cs.get("polarizations")==list(C.POLARIZATIONS),"raw_state_axis_or_mode_schema_mismatch:"+cid)
    extractor_path=ROOT/"scripts/coupling_ml/pw_k6_stage1_32g_frozen_forward_h1_v1.py"
    extractor_sha=sha256_file(extractor_path)
    _need(extractor_sha==C.H1_EVALUATOR_SOURCE_SHA256,"frozen_truth_extractor_sha_mismatch")
    decoder_path=ROOT/"scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py"
    _need(sha256_file(decoder_path)==C.H2_DECODER_SHA256,"frozen_h2_decoder_sha_mismatch")
    spec=importlib.util.spec_from_file_location("k6_v2_frozen_h2",decoder_path)
    h2=importlib.util.module_from_spec(spec);sys.modules[spec.name]=h2;spec.loader.exec_module(h2)
    with np.load(sp,allow_pickle=False) as z:
        need={"coefficients_real","coefficients_imag","wavelengths_nm","orders","propagating_mask","mode_kz_real"}
        _need(need.issubset(z.files),"state_npz_keys_missing:"+cid)
        _need(z["coefficients_real"].shape==(3,21,81,2,2) and np.allclose(z["wavelengths_nm"],C.WAVELENGTHS_NM,rtol=0,atol=1e-7),"state_shape_or_wavelength_mismatch:"+cid)
        oi={tuple(map(int,v)):i for i,v in enumerate(z["orders"].tolist())}
        _need(all(x in oi for x in _ORDER),"state_order_missing:"+cid); ix=[oi[x] for x in _ORDER]
        coeff=np.take(z["coefficients_real"][2],ix,axis=1)[:,:,0,:]+1j*np.take(z["coefficients_imag"][2],ix,axis=1)[:,:,0,:]
        kz=np.take(z["mode_kz_real"][2],ix,axis=1); mask=np.take(z["propagating_mask"][2],ix,axis=1)
        _need(mask.shape==(21,7) and np.all(mask) and coeff.shape==(21,7,2) and np.isfinite(coeff.real).all() and np.isfinite(coeff.imag).all() and np.isfinite(kz).all() and (kz>0).all(),"invalid_state_modes:"+cid)
        k0=2*np.pi/(np.asarray(C.WAVELENGTHS_NM)*1e-9)
        for j,wl in enumerate(C.WAVELENGTHS_NM):
            for q,mn in enumerate(_ORDER):
                km=h2._mode(mn[0],0,float(wl),1.0,1,"TE")["kz_rad_m"].real
                _need(abs(kz[j,q]-km)<=max(1e-5,abs(kz[j,q])*1e-11),"state_kz_disagrees_with_frozen_h2:"+cid)
        den=np.sum((kz/k0[:,None])[:,:,None]*abs(coeff)**2,axis=(1,2))
        _need(np.isfinite(den).all() and (den>0).all(),"state_normalization_invalid:"+cid)
        chat=coeff/np.sqrt(den)[:,None,None]
    wls=np.asarray(od.get("wavelengths_nm",[]),dtype=float); posts=od.get("post",[])
    _need(od.get("schema")=="APCD_PW_PERIODIC_DIFFRACTION_ORDERS_V1" and wls.shape==(21,) and len(posts)==21 and np.allclose(wls,C.WAVELENGTHS_NM,rtol=0,atol=1e-7),"orders_schema_or_wavelength_mismatch:"+cid)
    eta=np.zeros((21,7)); source_fraction=np.zeros((21,7))
    for j,row in enumerate(posts):
        _need(len(row)==7,"orders_count_mismatch:"+cid)
        for q,x in enumerate(row):
            _need((int(x.get("order_x",999)),int(x.get("order_y",999)))==_ORDER[q],"orders_sequence_mismatch:"+cid)
            eta[j,q]=float(x["power_fraction_of_monitor_total"])
            source_fraction[j,q]=float(x["power_fraction_of_source"])
    _need(np.isfinite(eta).all() and np.isfinite(source_fraction).all() and (eta>=0).all() and (source_fraction>=0).all() and np.allclose(eta.sum(1),1,atol=1e-6,rtol=0),"invalid_order_fractions:"+cid)
    with np.load(rnp,allow_pickle=False) as z:
        keys=("POSTNP_f","POSTNP_x","POSTNP_y","POSTNP_Ex","POSTNP_Ey","POSTNP_Hx","POSTNP_Hy")
        _need(all(k in z.files for k in keys),"raw_fields_keys_missing:"+cid)
        _need(np.allclose(299792458.0/np.asarray(z["POSTNP_f"]).reshape(-1)*1e9,C.WAVELENGTHS_NM,rtol=0,atol=1e-7),"raw_wavelength_mismatch:"+cid)
        x,y=np.asarray(z["POSTNP_x"]).reshape(-1),np.asarray(z["POSTNP_y"]).reshape(-1)
        _need(len(x)>1 and len(y)>1 and (np.diff(x)>0).all() and (np.diff(y)>0).all(),"raw_coordinates_invalid:"+cid)
        _need(np.isclose(x[-1]-x[0],1740e-9,rtol=0,atol=1e-12) and np.isclose(y[-1]-y[0],290e-9,rtol=0,atol=1e-12),"raw_fields_do_not_cover_full_period:"+cid)
        expected=(len(x),len(y),1,21)
        _need(all(np.asarray(z[k]).shape==expected and np.isfinite(z[k]).all() for k in ("POSTNP_Ex","POSTNP_Ey","POSTNP_Hx","POSTNP_Hy")),"raw_field_array_shape_or_finiteness_mismatch:"+cid)
        def tw(v):
            w=np.empty_like(v); w[0]=(v[1]-v[0])/2; w[-1]=(v[-1]-v[-2])/2; w[1:-1]=(v[2:]-v[:-2])/2; return w
        wx,wy=tw(x),tw(y); ex,ey=z["POSTNP_Ex"][:,:,0,:],z["POSTNP_Ey"][:,:,0,:]
        hx,hy=z["POSTNP_Hx"][:,:,0,:],z["POSTNP_Hy"][:,:,0,:]
        flux=np.sum(wx[:,None,None]*wy[None,:,None]*(.5*np.real(ex*np.conj(hy)-ey*np.conj(hx))),axis=(0,1))
    norm=rm.get("canonical_state",{}).get("normalization",{})
    pin=np.asarray(norm.get("incident_power_per_area"),float); phase=np.asarray(norm.get("gauge_phase_rad"),float)
    _need(pin.shape==(21,) and np.isfinite(pin).all() and (pin>0).all() and phase.shape==(21,) and np.isfinite(phase).all(),"source_normalization_invalid:"+cid)
    _need("single_global_phase_per_wavelength_from_IN_REF_+z_(0,0)_TM" in norm.get("gauge",""),"source_gauge_mismatch:"+cid)
    ps=flux/(1740e-9*290e-9*pin)
    _need(ps.shape==(21,) and np.isfinite(ps).all() and (ps>0).all(),"pscale_invalid:"+cid)
    artifact_hashes={"source_manifest":mh,"state_npz":sh,"state_metadata":smh,
        "raw_npz":rnh,"raw_metadata":rmh,"orders_json":oh}
    supplement_sha=None
    if power_supplement is None:
        _need(np.allclose(source_fraction,ps[:,None]*eta,rtol=1e-3,atol=1e-9),
              "source_normalized_order_power_mismatch:"+cid)
        mapping_source="runner_orders_json"
    else:
        supplement_sha=_validate_power_mapping_supplement(
            power_supplement,record,artifact_hashes,ps,eta)
        mapping_source="case_scoped_audited_p_scale_times_eta"
    return C.CaseTruth(cid,record["attempt_id"],role,D,chat,ps,eta,ps[:,None]*eta,
        {"source_manifest_sha256":mh,"state_npz_sha256":sh,"state_metadata_sha256":smh,
         "raw_npz_sha256":rnh,"raw_metadata_sha256":rmh,"orders_sha256":oh,
         "physical_contract_sha256":C.PHYSICAL_CONTRACT_SHA256,"reference_plane_nm":C.REFERENCE_PLANE_NM,
         "normalization":C.PSCALE_DEFINITION,"truth_extractor_sha256":extractor_sha,
         "truth_schema":C.STATE_SCHEMA,"power_mapping_source":mapping_source,
         "power_mapping_supplement_sha256":supplement_sha})

def load_verified_runner_case(record,*,expected_role,root=None,registry=None,power_supplement=None):
    _need(expected_role in _DEV,"runner_entry_only_accepts_development_roles")
    reg=registry or load_frozen_case_registry(root)
    return _load_runner_truth(record,reg.development,{expected_role},root=root,
                              power_supplement=power_supplement)

def load_development_collection(aggregate_npz_path=None,new_case_records=(),*,allowlist_path=None,expected_case_ids=None,root=None,registry=None,power_supplements=None):
    root=Path(root) if root else ROOT; reg=registry or load_frozen_case_registry(root); recs=list(new_case_records)
    if aggregate_npz_path is not None:
        _need(Path(aggregate_npz_path).resolve()==(root/OLD/"dataset_truth_32g.npz").resolve(),"aggregate_npz_override_forbidden")
    for record in recs: assert_no_quarantine_linkage(record,consumer="training",root=root)
    ids=[str(x.get("case_id","")) for x in recs]
    _need(all(x.get("role") in _DEV and x.get("case_id") in reg.development for x in recs),"confirmation_diagnostic_or_unknown_case_rejected_before_response_access")
    _need(len(recs)==128 and len(ids)==128 and len(set(ids))==128 and set(ids)==set(reg.development),"development_allowlist_incomplete_or_duplicate")
    if expected_case_ids is not None: _need(set(expected_case_ids)==set(reg.development),"expected_ids_mismatch")
    if allowlist_path: _need(sha256_file(allowlist_path)==ALLOW_SHA,"development_allowlist_sha_mismatch")
    _need(power_supplements is None or isinstance(power_supplements,Mapping),
          "power_mapping_supplements_must_be_case_mapping")
    supplements=dict(power_supplements or {})
    _need(set(supplements).issubset(set(reg.development)) and set(supplements).issubset({_POWER_SUPPLEMENT_CASE}),
          "power_mapping_supplement_case_not_allowlisted")
    old=_old32(root,reg)
    new=tuple(_load_runner_truth(x,reg.development,{x["role"]},root=root,
        power_supplement=supplements.get(x["case_id"])) for x in recs); cases=old+new
    _need(len(cases)==160 and len({x.case_id for x in cases})==160 and all(x.role in C.DEVELOPMENT_ROLES for x in cases),"development_collection_integrity_failure")
    return C.CaseCollection("development",cases,REG_SHA,{"old32_sha256":OLD_NPZ_SHA,"registration_sha256":REG_SHA,"pointset_sha256":C.V2_CANDIDATE_CSV_SHA256,"all_wavelengths_grouped":True})

@dataclass(frozen=True)
class ConfirmationCaseTruth:
    truth:C.CaseTruth
    registered_role:str
    stratum:str
@dataclass(frozen=True)
class DiagnosticCaseArtifacts:
    case_id:str
    attempt_id:str
    role:str
    geometry_nm:tuple
    protocol_sha256:str
    artifact_descriptors:Mapping[str,Any]

_REVEAL_SENTINEL=object()
def _reject_sealed_path(path):
    parts={x.lower() for x in Path(str(path)).parts}
    forbidden={"truth_access","sealed_truth","confirmation_truth","sealed_responses","confirmation_responses"}
    _need(not (parts&forbidden),"freeze_artifact_path_inside_sealed_response_root")
def _manifest_artifact(base,bundle,key_path,key_sha):
    rel=bundle.get(key_path); digest=bundle.get(key_sha)
    _need(isinstance(rel,str) and isinstance(digest,str) and len(digest)==64,"freeze_artifact_descriptor_invalid:"+key_path)
    _reject_sealed_path(rel)
    p=Path(rel); p=p if p.is_absolute() else base/p
    _need(p.is_file() and sha256_file(p)==digest,"freeze_artifact_missing_or_sha_mismatch:"+key_path)
    return str(p.resolve()),digest
class RevealAuthorization:
    def __init__(self,freeze_sha,freeze_path,point_sha,role_sha,ids,ledger,authority_paths,*,_issuer=None):
        if _issuer is not _REVEAL_SENTINEL: raise DataAccessError("reveal_token_must_be_issued_by_freeze_gate")
        self.freeze_sha,self.freeze_path,self.point_sha,self.role_sha=freeze_sha,freeze_path,point_sha,role_sha
        self.ids=frozenset(ids); self.ledger=Path(ledger); self.authority_paths=authority_paths; self.used=set(); self.started=False; self.lock=threading.Lock()
    def consume(self,cid):
        with self.lock:
            _need(cid in self.ids,"confirmation_id_not_allowlisted")
            _need(cid not in self.used,"confirmation_reveal_reuse_denied:"+cid)
            self.ledger.parent.mkdir(parents=True,exist_ok=True); now=datetime.datetime.now(datetime.timezone.utc).isoformat()
            row={"schema":"K6_V2_CONFIRMATION_REVEAL_LEDGER_V1","status":"REVEAL_STARTED","freeze_manifest_path":self.freeze_path,"freeze_manifest_sha256":self.freeze_sha,"pointset_sha256":self.point_sha,"role_allowlist_sha256":self.role_sha,"authority_paths":self.authority_paths,"first_case_id":cid,"started_utc":now}
            if not self.started:
                try:
                    with self.ledger.open("x",encoding="utf-8") as f: f.write(json.dumps(row,sort_keys=True)); f.write(chr(10)); f.flush(); os.fsync(f.fileno())
                except FileExistsError as e: raise DataAccessError("reveal_ledger_already_started_no_resume") from e
                self.started=True
            else:
                with self.ledger.open("a",encoding="utf-8") as f: f.write(json.dumps({"event":"CASE_REVEAL_CONSUMED","case_id":cid,"utc":now},sort_keys=True)+"\n"); f.flush(); os.fsync(f.fileno())
            self.used.add(cid)
def issue_reveal_authorization(*,freeze_manifest_path,freeze_manifest_sha256,pointset_sha256,role_allowlist_sha256,reveal_ledger_path,root=None):
    root=Path(root) if root else ROOT; reg=load_frozen_case_registry(root); fm=Path(freeze_manifest_path)
    _reject_sealed_path(fm)
    _need(fm.is_file() and sha256_file(fm)==freeze_manifest_sha256,"freeze_manifest_missing_or_sha_mismatch")
    m=_json(fm); _need(m.get("schema")=="COUPLING_ML_K6_V2_CONFIRMATION_FREEZE_V1","freeze_manifest_schema_mismatch")
    _need(pointset_sha256==reg.pointset_sha256==m.get("pointset_sha256") and role_allowlist_sha256==reg.confirmation_role_sha256==m.get("confirmation_role_allowlist_sha256"),"reveal_allowlist_binding_mismatch")
    ev=m.get("evaluators",{}); evaluator_path=root/"scripts/coupling_ml/k6_v2_pipeline/h1.py"
    evaluator_sha=sha256_file(evaluator_path)
    orchestrator_path=root/"scripts/coupling_ml/k6_v2_pipeline/confirmation.py"
    orchestrator_sha=sha256_file(orchestrator_path)
    _need(ev.get("h1_authority_sha256")==C.H1_AUTHORITY_SHA256 and ev.get("h2_decoder_sha256")==C.H2_DECODER_SHA256 and ev.get("confirmation_evaluator_sha256")==evaluator_sha and ev.get("confirmation_orchestrator_sha256")==orchestrator_sha,"freeze_evaluator_hash_mismatch")
    bundles=m.get("prediction_bundles",{}); _need(set(bundles)=={"RBF_KRR","CARTESIAN_MLP","LOCAL_AFFINE"},"freeze_bundle_keys_mismatch")
    global_ids={k for k,v in reg.confirmation.items() if v["role"]=="SEALED_CONFIRMATION_GLOBAL"}
    local_ids={k for k,v in reg.confirmation.items() if v["role"]==C.ROLE_LOCAL_CONFIRM}
    required={"case_ids","prediction_path","prediction_sha256","config_path","config_sha256","model_path","model_sha256","preprocessing_path","preprocessing_sha256","evaluator_path","evaluator_sha256"}
    hashes={}
    for name,b in bundles.items():
        _need(isinstance(b,dict) and required.issubset(b),"freeze_bundle_schema_incomplete:"+name)
        wanted=local_ids if name=="LOCAL_AFFINE" else global_ids; got=list(b["case_ids"])
        _need(len(got)==len(set(got)) and set(got)==wanted,"freeze_bundle_confirmation_coverage_mismatch:"+name)
        for k in ("prediction","config","model","preprocessing","evaluator"):
            hashes[name+"."+k]=_manifest_artifact(fm.parent,b,k+"_path",k+"_sha256")
        _need(b["evaluator_sha256"]==evaluator_sha,"bundle_evaluator_hash_mismatch:"+name)
    ledger=Path(reveal_ledger_path); _need(not ledger.exists(),"reveal_ledger_already_started_no_resume")
    paths={"registration_package_path":str((root/ADMIT/"CASE_REGISTRATION_PACKAGE_V1.json").resolve()),"registration_package_sha256":REG_SHA,
      "role_allowlist_path":str((root/ADMIT/"DEVELOPMENT_CASE_ALLOWLIST_V1.json").resolve()),"role_allowlist_file_sha256":ALLOW_SHA,
      "pointset_path":str((root/REV/"GLOBAL_DATASET_CANDIDATES_V2.csv").resolve()),"pointset_sha256":C.V2_CANDIDATE_CSV_SHA256}
    return RevealAuthorization(freeze_manifest_sha256,str(fm.resolve()),pointset_sha256,role_allowlist_sha256,reg.confirmation.keys(),ledger,paths,_issuer=_REVEAL_SENTINEL)
def load_confirmation_case(record,*,reveal_authorization,root=None,registry=None):
    root=Path(root) if root else ROOT
    assert_no_quarantine_linkage(record,consumer="truth_handoff",root=root)
    reg=registry or load_frozen_case_registry(root); cid=str(record.get("case_id","")); item=reg.confirmation.get(cid)
    _need(item is not None,"confirmation_id_not_allowlisted"); role=record.get("role")
    _need(role in C.CONFIRMATION_ROLES and role in (item["role"],item.get("effective_role")),"confirmation_role_mismatch")
    _need(isinstance(reveal_authorization,RevealAuthorization) and reveal_authorization.point_sha==reg.pointset_sha256 and reveal_authorization.role_sha==reg.confirmation_role_sha256,"confirmation_reveal_token_invalid")
    reveal_authorization.consume(cid)
    truth=_load_runner_truth(record,reg.confirmation,{role},root=root)
    return ConfirmationCaseTruth(truth,item["role"],"LOCAL_COMBINATION" if item["role"]==C.ROLE_LOCAL_CONFIRM else ("STRESS" if item.get("boundary_stress") else "CORE"))
def load_diagnostic_case(record):
    assert_no_quarantine_linkage(record,consumer="diagnostic_import")
    _need(record.get("case_id")==C.TWO_PLANE_CASE_ID and record.get("attempt_id")==C.TWO_PLANE_ATTEMPT_ID and record.get("role")==C.ROLE_DIAGNOSTIC and record.get("protocol_sha256")==C.TWO_PLANE_PROTOCOL_SHA256,"diagnostic_identity_or_contract_mismatch")
    D=tuple(map(int,record.get("ordered_D_nm",())))
    _need(D==(220,120,155,100,105,110),"diagnostic_geometry_mismatch")
    a=record.get("artifacts",{}); _need(isinstance(a,dict),"diagnostic_descriptors_invalid")
    return DiagnosticCaseArtifacts(C.TWO_PLANE_CASE_ID,C.TWO_PLANE_ATTEMPT_ID,C.ROLE_DIAGNOSTIC,D,C.TWO_PLANE_PROTOCOL_SHA256,dict(a))
