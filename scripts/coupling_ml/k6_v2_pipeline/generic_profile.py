"""Candidate generic Science Owner profile adapter; no solver or formula changes."""
from __future__ import annotations

import importlib
import inspect
import re
import sys
from dataclasses import replace
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from . import contracts as C
from . import ingest as I
from .ingest import (ROOT, _ORDER, _artifact, _json, _validate_power_mapping_supplement,
                    assert_no_quarantine_linkage, geometry_sha, sha256_file)
from .h1 import load_h2_decoder, reconstruct_h2

PROFILE_ID = "coupling_609d_v1"
SCIENCE_OWNER_ID = "APCD_COUPLING_ML_SCIENCE_OWNER_V1"
CASE_REQUEST_CANON_SCHEMA = "APCD_COUPLING_CASE_REQUEST_CANON_V1"
AUTHORITY_SCHEMA = "APCD_GPU_V21_PROFILE_AUTHORITY_V1"
CERTIFICATION_SCHEMA = "APCD_COUPLING_609D_SCIENCE_PROFILE_CERTIFICATION_V1"
LEDGER_SCHEMA = "APCD_COUPLING_BATCH_ENTRY_LEDGER_V1"
KNOWN_ROLES = frozenset((C.ROLE_GLOBAL_DEV, C.ROLE_LOCAL_AXIS, "TIME_CONVERGENCE_DIAGNOSTIC_ONLY"))
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise I.DataAccessError(message)


def _sha(value: Any, label: str) -> str:
    _need(isinstance(value, str) and SHA_RE.fullmatch(value) is not None, label + "_sha256_invalid")
    return value


def _map(value: Any, label: str) -> Mapping[str, Any]:
    _need(isinstance(value, Mapping), label + "_mapping_required")
    return value


def _rule_allows(value: Any, rule: Any) -> bool:
    if isinstance(rule, (int, float)) and not isinstance(rule, bool):
        return value == rule
    if isinstance(rule, list):
        return value in rule
    if isinstance(rule, Mapping):
        lo, hi = rule.get("min"), rule.get("max")
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and isinstance(lo, (int, float)) and isinstance(hi, (int, float))
                and lo <= value <= hi)
    return False


def _verified_authority(authority: Mapping[str, Any]):
    """Check payload bindings; pinned GPU load_batch must first verify ACL and byte SHAs."""
    authority = _map(authority, "authority")
    _need(authority.get("schema") == AUTHORITY_SCHEMA, "profile_authority_schema")
    _need(authority.get("profile_id") == PROFILE_ID, "profile_authority_id")
    manifest = _map(authority.get("manifest"), "manifest")
    _need(manifest.get("science_owner") == SCIENCE_OWNER_ID, "profile_science_owner")
    _need(manifest.get("case_request_canonicalization") == CASE_REQUEST_CANON_SCHEMA,
          "profile_case_request_canonicalization")
    admission = _map(authority.get("admission"), "admission")
    cert = _map(authority.get("certification"), "certification")
    manifest_sha = _sha(authority.get("manifest_file_sha"), "manifest_file")
    _sha(authority.get("admission_file_sha"), "admission_file")
    cert_sha = _sha(authority.get("certification_file_sha"), "certification_file")

    body = dict(manifest)
    declared = body.pop("manifest_sha", None)
    _need(isinstance(declared, str) and I._canon(body) == declared, "profile_manifest_digest")
    rows, ids = manifest.get("cases"), manifest.get("approved_case_set")
    _need(isinstance(rows, list) and isinstance(ids, list), "profile_case_set_missing")
    row_ids = [r.get("case_id") if isinstance(r, Mapping) else None for r in rows]
    _need(row_ids == ids and len(set(row_ids)) == len(ids)
          and len(ids) == manifest.get("case_count")
          and manifest.get("approved_entry_budget") == len(ids), "profile_case_budget_mismatch")
    _need(manifest.get("label_validation_profile") == PROFILE_ID, "profile_manifest_id")

    _need(admission.get("schema_version") == "APCD_GPU_V21_SCIENCE_ADMISSION_V1"
          and admission.get("batch_id") == manifest.get("batch_id")
          and admission.get("science_owner") == manifest.get("science_owner")
          and admission.get("manifest_sha") == declared
          and admission.get("manifest_file_sha") == manifest_sha
          and admission.get("approved_case_set") == ids
          and admission.get("approved_entry_budget") == len(ids)
          and admission.get("scientific_admission") == "PASS"
          and admission.get("engineering_admission") == "PASS"
          and admission.get("revoked") is False
          and admission.get("no_replay") is True
          and admission.get("label_validation_profile") == PROFILE_ID
          and admission.get("profile_certification_sha") == cert_sha
          and admission.get("science_ledger") == manifest.get("science_ledger"),
          "profile_admission_binding")

    _need(cert.get("schema") == CERTIFICATION_SCHEMA
          and cert.get("profile_id") == PROFILE_ID
          and cert.get("case_request_canonicalization") == CASE_REQUEST_CANON_SCHEMA
          and cert.get("verdict") == "PASS"
          and cert.get("scientific_validated") is True
          and cert.get("outputs") == C.MODEL_OUTPUTS
          and cert.get("science_owner") == manifest.get("science_owner")
          and cert.get("state_schema") == C.STATE_SCHEMA
          and cert.get("target_layout") == C.MODEL_TARGET_LAYOUT
          and cert.get("h1_authority_sha256") == C.H1_AUTHORITY_SHA256
          and cert.get("h2_decoder_sha256") == C.H2_DECODER_SHA256
          and cert.get("truth_extractor_sha256") == C.H1_EVALUATOR_SOURCE_SHA256,
          "science_owner_certificate_contract")
    roles = cert.get("allowed_roles")
    _need(isinstance(roles, list) and roles and len(roles) == len(set(roles))
          and set(roles) <= KNOWN_ROLES, "science_owner_roles_missing_or_unknown")
    policies = cert.get("allowed_contracts")
    _need(isinstance(policies, list) and policies, "science_owner_contract_policy_missing")
    policy_hashes = []
    for policy in policies:
        policy = _map(policy, "science_owner_contract_policy")
        policy_hashes.append(_sha(policy.get("sha256"), "science_owner_contract"))
        policy_roles = policy.get("allowed_roles")
        _need(isinstance(policy_roles, list) and policy_roles
              and len(policy_roles) == len(set(policy_roles))
              and set(policy_roles) <= KNOWN_ROLES,
              "science_owner_contract_roles_missing_or_unknown")
        _need(all(field in policy for field in
                  ("simulation_time_s", "mesh_nm", "auto_shutoff_min")),
              "science_owner_contract_rules_missing")
    _need(len(policy_hashes) == len(set(policy_hashes)),
          "science_owner_contract_policy_duplicate")
    source_validation = _map(cert.get("source_validation"), "science_owner_source_validation")
    required_source_fields = {
        "case_id", "attempt_id", "role", "ordered_D_nm", "source_fsp_sha",
        "source_manifest_sha", "physics_contract_sha", "physics_contract_file_sha256",
        "case_request_sha256", "source_acceptance_file_sha256", "native_fsp_sha256",
        "native_h5_sha256", "simulation_time_s", "mesh_nm", "auto_shutoff_min",
    }
    _need(source_validation.get("source_acceptance_required") is True
          and source_validation.get("verdict") == "PASS"
          and source_validation.get("fresh_load_verified") is True
          and set(source_validation.get("bound_fields", [])) >= required_source_fields,
          "science_owner_source_validation_missing")
    _need(cert.get("entry_ledger_schema") == LEDGER_SCHEMA
          and cert.get("budget_semantics") == "EXACT_APPROVED_CASE_SET_NO_REPLAY"
          and cert.get("reconciliation_semantics") == "ENTERED_THEN_TRUTH_VALID_THEN_LABELS_VALID_SUBSETS"
          and cert.get("source_acceptance_required") is True,
          "science_owner_entry_semantics_missing")
    toolchain = _map(cert.get("toolchain"), "certificate_toolchain")
    _need(toolchain.get("importer") == I.sha256_file(Path(__file__)), "science_owner_importer_pin")
    return manifest, admission, cert


def _case_row(manifest: Mapping[str, Any], case_id: str, attempt_id: str):
    matches = [r for r in manifest["cases"] if isinstance(r, Mapping) and r.get("case_id") == case_id]
    _need(len(matches) == 1 and case_id in manifest["approved_case_set"], "profile_case_not_authorized")
    row = matches[0]
    _need(attempt_id == row.get("attempt_id") == "attempt_001", "profile_attempt_mismatch")
    _need(row.get("role") in KNOWN_ROLES, "profile_role_unknown")
    d = row.get("ordered_D_nm")
    _need(isinstance(d, (list, tuple)) and len(d) == 6
          and all(isinstance(v, int) and not isinstance(v, bool) for v in d), "profile_geometry_invalid")
    contract_pin = _map(row.get("physics_contract"), "case_physics_contract")
    contract_sha = _sha(row.get("physics_contract_sha"), "case_physics_contract")
    _need(contract_pin.get("sha256") == contract_sha
          and isinstance(contract_pin.get("path"), str) and contract_pin.get("path"),
          "profile_physical_contract_mismatch")
    for key in ("source_fsp", "source_manifest", "source_acceptance"):
        pin = _map(row.get(key), "case_" + key)
        _sha(pin.get("sha256"), "case_" + key)
        _need(isinstance(pin.get("path"), str) and pin["path"], "case_" + key + "_path")
    return row


def _case_request_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical request projection avoids a self-referential acceptance-file hash."""
    body = dict(row)
    body.pop("case_request_sha256", None)
    acceptance = _map(body.pop("source_acceptance", None), "case_source_acceptance")
    return {
        "schema": CASE_REQUEST_CANON_SCHEMA,
        "case_request": body,
        "source_acceptance_path": acceptance.get("path"),
    }


def _case_request_digest(row: Mapping[str, Any]) -> str:
    return I._canon(_case_request_payload(row))


def _verify_case_request(row: Mapping[str, Any], record: Mapping[str, Any]) -> str:
    declared = _sha(row.get("case_request_sha256"), "case_request")
    _need(_case_request_digest(row) == declared, "profile_case_request_digest")
    _need(record.get("request_sha256") == declared, "profile_runner_request_sha")
    return declared


def _verify_source_acceptance(row: Mapping[str, Any], request_sha256: str) -> str:
    pin = _map(row.get("source_acceptance"), "case_source_acceptance")
    path = Path(pin["path"])
    digest = _sha(pin.get("sha256"), "case_source_acceptance")
    _need(path.is_file() and I.sha256_file(path) == digest, "source_acceptance_file_sha_mismatch")
    proof = I._json(path)
    contract_pin = _map(row.get("physics_contract"), "case_physics_contract")
    contract_sha = _sha(row.get("physics_contract_sha"), "case_physics_contract_semantic")
    expected = {
        "verdict": "PASS", "fresh_load_verified": True, "case_id": row["case_id"],
        "attempt_id": row["attempt_id"], "role": row["role"],
        "ordered_D_nm": list(row["ordered_D_nm"]),
        "source_fsp_sha": row["source_fsp"]["sha256"],
        "source_manifest_sha256": row["source_manifest"]["sha256"],
        "physics_contract_sha": contract_sha,
        "physics_contract_file_sha256": contract_pin["sha256"],
        "case_request_sha256": request_sha256,
        "simulation_time_s": row["simulation_time_s"],
        "mesh_nm": row["mesh_nm"],
        "auto_shutoff_min": row["auto_shutoff_min"],
    }
    _need(all(proof.get(k) == v for k, v in expected.items()), "source_acceptance_binding")
    return digest


def _verify_native_outputs(record: Mapping[str, Any]) -> dict[str, str]:
    hashes = {}
    for key, suffix in (("native_fsp", ".fsp"), ("native_h5", ".h5")):
        path, digest = I._artifact(record, key)
        _need(path.suffix.lower() == suffix, "native_output_extension:" + key)
        hashes[key + "_sha256"] = digest
    return hashes


def _load_authorized_runner_truth(record,role_map,expected_roles,*,contract_sha256,root=None,power_supplement=None):
    assert_no_quarantine_linkage(record,consumer="truth_import",root=root)
    cid=str(record.get("case_id","")); _need(cid in role_map,"case_id_not_in_role_allowlist:"+cid); reg=role_map[cid]
    role=record.get("role"); _need(role in expected_roles and role in (reg["role"],reg.get("effective_role")),"role_not_allowed:"+str(role))
    D=tuple(map(int,record.get("ordered_D_nm",())))
    _need(record.get("attempt_id")==reg["attempt_id"]=="attempt_001" and D==reg["ordered_D_nm"] and geometry_sha(D)==reg["ordered_geometry_sha256"],"case_identity_mismatch:"+cid)
    _need(record.get("physical_contract_sha256")==contract_sha256,"physical_contract_mismatch:"+cid)
    _need(record.get("status") in ("DONE","RECOVERED_TRUTH_VALID") and record.get("solver_invocations")==1 and record.get("replay_count",0)==0,"truth_not_single_entry_valid:"+cid)
    mp,mh=_artifact(record,"source_manifest"); man=_json(mp)
    assert_no_quarantine_linkage(man,consumer="truth_import",root=root)
    _need(man.get("case_id")==cid and man.get("attempt_id")==record["attempt_id"] and man.get("geometry")==list(D) and man.get("physical_contract_sha256")==contract_sha256,"source_manifest_identity_mismatch:"+cid)
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
    _need(pcp.is_file() and sha256_file(pcp)==contract_sha256,"physical_contract_file_sha_mismatch:"+cid)
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
         "physical_contract_sha256":contract_sha256,"reference_plane_nm":C.REFERENCE_PLANE_NM,
         "normalization":C.PSCALE_DEFINITION,"truth_extractor_sha256":extractor_sha,
         "truth_schema":C.STATE_SCHEMA,"power_mapping_source":mapping_source,
         "power_mapping_supplement_sha256":supplement_sha})


def validate_profile_admission(*, authority: Mapping[str, Any], case_id: str, attempt_id: str) -> dict[str, Any]:
    """Independent scientific scope decision; does not authorize a solver entry."""
    manifest, admission, cert = _verified_authority(authority)
    row = _case_row(manifest, case_id, attempt_id)
    role = row["role"]
    _need(role in cert["allowed_roles"], "science_owner_role_not_certified")
    matches = [p for p in cert["allowed_contracts"]
               if isinstance(p, Mapping) and p.get("sha256") == row["physics_contract_sha"]]
    _need(len(matches) == 1, "science_owner_contract_not_certified")
    policy = matches[0]
    _need(role in policy.get("allowed_roles", []), "science_owner_contract_role_not_certified")
    for field in ("simulation_time_s", "mesh_nm", "auto_shutoff_min"):
        _need(field in row and field in policy and _rule_allows(row[field], policy[field]),
              "science_owner_physical_rule_mismatch:" + field)
    return {
        "verdict": "PASS", "scientific_admission": "PASS", "profile_id": PROFILE_ID,
        "batch_id": manifest["batch_id"], "case_id": case_id, "attempt_id": attempt_id,
        "role": role, "ordered_D_nm": list(row["ordered_D_nm"]),
        "physical_contract_sha256": row["physics_contract_sha"],
        "manifest_file_sha256": authority["manifest_file_sha"],
        "admission_file_sha256": authority["admission_file_sha"],
        "certification_file_sha256": authority["certification_file_sha"],
        "authorized_entry_budget": admission["approved_entry_budget"],
        "no_replay": admission["no_replay"], "entry_authorization": False,
    }


def load_authorized_runner_case(record: Mapping[str, Any], *, expected_role: str,
                               root: str | Path, authority: Mapping[str, Any]) -> C.CaseTruth:
    """Bind a dynamic identity, then reuse the frozen K6 V2 609D truth extractor."""
    record = _map(record, "runner_record")
    decision = validate_profile_admission(authority=authority, case_id=str(record.get("case_id", "")),
                                          attempt_id=str(record.get("attempt_id", "")))
    manifest, _, _ = _verified_authority(authority)
    row = _case_row(manifest, decision["case_id"], decision["attempt_id"])
    request_sha = _verify_case_request(row, record)
    source_acceptance_sha = _verify_source_acceptance(row, request_sha)
    native_hashes = _verify_native_outputs(record)
    _need(expected_role == row["role"] == record.get("role"), "profile_expected_role_mismatch")
    ordered = tuple(row["ordered_D_nm"])
    _need(tuple(record.get("ordered_D_nm", ())) == ordered
          and record.get("physical_contract_sha256") == row["physics_contract_sha"],
          "profile_runner_identity_mismatch")
    _need(record.get("physical_contract_file_sha256") == row["physics_contract"]["sha256"],
          "profile_runner_contract_file_sha")
    run_manifest_path, _ = I._artifact(record, "source_manifest")
    run_manifest = I._json(run_manifest_path)
    fsp_pin, source_pin = row["source_fsp"], row["source_manifest"]
    _need(run_manifest.get("pre_fsp_sha256") == fsp_pin["sha256"]
          and run_manifest.get("source_manifest_path") == source_pin["path"]
          and run_manifest.get("source_manifest_sha256") == source_pin["sha256"]
          and run_manifest.get("batch_id") == manifest["batch_id"]
          and run_manifest.get("profile_id") == PROFILE_ID
          and run_manifest.get("admission_sha256") == authority["admission_file_sha"]
          and run_manifest.get("request_sha256") == request_sha
          and run_manifest.get("source_acceptance_file_sha256") == source_acceptance_sha
          and run_manifest.get("native_fsp_sha256") == native_hashes["native_fsp_sha256"]
          and run_manifest.get("native_h5_sha256") == native_hashes["native_h5_sha256"],
          "profile_source_binding")
    for pin in (fsp_pin, source_pin, row["physics_contract"], row["source_acceptance"]):
        _need(Path(pin["path"]).is_file() and I.sha256_file(Path(pin["path"])) == pin["sha256"],
              "profile_source_pin")
    role = row["role"]
    registry = {row["case_id"]: {
        "case_id": row["case_id"], "attempt_id": row["attempt_id"],
        "role": role, "effective_role": role, "ordered_D_nm": ordered,
        "ordered_geometry_sha256": I.geometry_sha(ordered),
        "physical_contract": dict(row["physics_contract"]),
    }}
    imported = _load_authorized_runner_truth(
        record, registry, {role}, contract_sha256=decision["physical_contract_sha256"],
        root=Path(root), power_supplement=None)
    provenance = dict(imported.provenance)
    provenance.update({
        "batch_id": decision["batch_id"], "profile_id": PROFILE_ID,
        "manifest_file_sha256": decision["manifest_file_sha256"],
        "admission_file_sha256": decision["admission_file_sha256"],
        "certification_file_sha256": decision["certification_file_sha256"],
        "original_source_manifest_path": source_pin["path"],
        "original_source_manifest_sha256": source_pin["sha256"],
        "case_request_sha256": request_sha,
        "physics_contract_file_sha256": row["physics_contract"]["sha256"],
        "source_acceptance_file_sha256": source_acceptance_sha,
        "native_fsp_sha256": native_hashes["native_fsp_sha256"],
        "native_h5_sha256": native_hashes["native_h5_sha256"],
    })
    return replace(imported, provenance=provenance)


def _validate_609d_numeric_payload(imported: C.CaseTruth) -> dict[str, Any]:
    c, p = np.asarray(imported.c_hat), np.asarray(imported.p_scale)
    eta, absolute = np.asarray(imported.eta, float), np.asarray(imported.absolute_order, float)
    _need(c.shape == C.C_HAT_SHAPE and np.iscomplexobj(c), "profile_c_hat_shape")
    _need(np.isfinite(c.real).all() and np.isfinite(c.imag).all(), "profile_c_hat_nonfinite")
    _need(p.shape == (21,) and np.isfinite(p).all() and (p > 0).all(), "profile_p_scale_invalid")
    _need(eta.shape == (21,7) and absolute.shape == (21,7)
          and np.isfinite(eta).all() and np.isfinite(absolute).all() and (eta >= 0).all()
          and np.allclose(eta.sum(axis=1),1.0,rtol=0.0,atol=1e-6)
          and np.allclose(absolute,p[:,None]*eta,rtol=1e-9,atol=1e-12),
          "profile_order_power_invalid")
    packed = C.pack_model_target(c, p)
    _need(packed.shape == (1, C.MODEL_OUTPUTS), "profile_target_not_609d")
    decoded = reconstruct_h2(c, p, load_h2_decoder())
    _need(np.allclose(decoded["eta"].sum(axis=-1),1.0,rtol=0.0,atol=1e-12)
          and np.array_equal(decoded["total_power"][0],p), "profile_h2_decode_invalid")
    return {"outputs": int(packed.shape[1]), "target_sha256": I._float_array_sha256(packed),
            "h2_eta_max_abs_delta": float(np.max(np.abs(decoded["eta"][0]-eta)))}


def validate_authorized_labels(imported: C.CaseTruth, *, authority: Mapping[str, Any]) -> dict[str, Any]:
    decision = validate_profile_admission(authority=authority, case_id=imported.case_id,
                                          attempt_id=imported.attempt_id)
    manifest, _, _ = _verified_authority(authority)
    row = _case_row(manifest, decision["case_id"], decision["attempt_id"])
    provenance = imported.provenance
    _need(imported.role == decision["role"]
          and tuple(imported.ordered_D_nm) == tuple(decision["ordered_D_nm"])
          and provenance.get("physical_contract_sha256") == decision["physical_contract_sha256"]
          and provenance.get("batch_id") == decision["batch_id"]
          and provenance.get("profile_id") == PROFILE_ID
          and provenance.get("manifest_file_sha256") == decision["manifest_file_sha256"]
          and provenance.get("admission_file_sha256") == decision["admission_file_sha256"]
          and provenance.get("certification_file_sha256") == decision["certification_file_sha256"]
          and provenance.get("original_source_manifest_path") == row["source_manifest"]["path"]
          and provenance.get("original_source_manifest_sha256") == row["source_manifest"]["sha256"]
          and provenance.get("case_request_sha256") == row["case_request_sha256"]
          and provenance.get("physics_contract_file_sha256") == row["physics_contract"]["sha256"]
          and provenance.get("source_acceptance_file_sha256") == row["source_acceptance"]["sha256"],
          "profile_label_identity")
    _sha(provenance.get("native_fsp_sha256"), "profile_native_fsp")
    _sha(provenance.get("native_h5_sha256"), "profile_native_h5")
    numeric = _validate_609d_numeric_payload(imported)
    body = {
        "schema": "APCD_COUPLING_SCIENCE_VALIDITY_RECEIPT_V1",
        "verdict": "PASS", "outputs": numeric["outputs"], "scientific_validated": True,
        "profile_id": PROFILE_ID, "physical_contract_sha256": decision["physical_contract_sha256"],
        "physics_contract_file_sha256": provenance["physics_contract_file_sha256"],
        "batch_id": decision["batch_id"], "case_id": imported.case_id,
        "attempt_id": imported.attempt_id, "role": imported.role,
        "ordered_D_nm": decision["ordered_D_nm"],
        "case_request_sha256": provenance["case_request_sha256"],
        "manifest_file_sha256": decision["manifest_file_sha256"],
        "admission_file_sha256": decision["admission_file_sha256"],
        "certification_file_sha256": decision["certification_file_sha256"],
        "source_manifest_sha256": provenance["original_source_manifest_sha256"],
        "source_acceptance_file_sha256": provenance["source_acceptance_file_sha256"],
        "native_fsp_sha256": provenance["native_fsp_sha256"],
        "native_h5_sha256": provenance["native_h5_sha256"],
        "target_sha256": numeric["target_sha256"],
        "h2_eta_max_abs_delta": numeric["h2_eta_max_abs_delta"],
    }
    body["science_receipt_sha256"] = I._canon(body)
    return body
