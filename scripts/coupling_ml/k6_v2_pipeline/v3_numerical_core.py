"""V3 numerical extraction adapted from original importer; old module unchanged."""
from pathlib import Path
import importlib.util,sys
import numpy as np
from . import contracts as C
from .ingest import (_need,_artifact,_json,geometry_sha,sha256_file,_ORDER,ROOT, _validate_power_mapping_supplement)
from .consumer_exclusions import assert_no_quarantine_linkage

def _load_runner_truth(record,role_map,expected_roles,*,root=None,power_supplement=None,expected_contract_sha256=None):
    expected_contract_sha256 = expected_contract_sha256 or C.PHYSICAL_CONTRACT_SHA256
    _need(expected_contract_sha256 in {C.PHYSICAL_CONTRACT_SHA256,
        'f8a59ebd65b168e52f76bde1f4bb7f91d545dfd5fd1838a32ab79e0548967d92'},
        'unsupported_expected_contract')
    assert_no_quarantine_linkage(record,consumer="truth_import",root=root)
    cid=str(record.get("case_id","")); _need(cid in role_map,"case_id_not_in_role_allowlist:"+cid); reg=role_map[cid]
    role=record.get("role"); _need(role in expected_roles and role in (reg["role"],reg.get("effective_role")),"role_not_allowed:"+str(role))
    D=tuple(map(int,record.get("ordered_D_nm",())))
    _need(record.get("attempt_id")==reg["attempt_id"]=="attempt_001" and D==reg["ordered_D_nm"] and geometry_sha(D)==reg["ordered_geometry_sha256"],"case_identity_mismatch:"+cid)
    _need(record.get("physical_contract_sha256")==expected_contract_sha256,"physical_contract_mismatch:"+cid)
    _need(record.get("status") in ("DONE","RECOVERED_TRUTH_VALID") and record.get("solver_invocations")==1 and record.get("replay_count",0)==0,"truth_not_single_entry_valid:"+cid)
    mp,mh=_artifact(record,"source_manifest"); man=_json(mp)
    assert_no_quarantine_linkage(man,consumer="truth_import",root=root)
    _need(man.get("case_id")==cid and man.get("attempt_id")==record["attempt_id"] and man.get("geometry")==list(D) and man.get("physical_contract_sha256")==expected_contract_sha256,"source_manifest_identity_mismatch:"+cid)
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
    _need(pcp.is_file() and sha256_file(pcp)==expected_contract_sha256,"physical_contract_file_sha_mismatch:"+cid)
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
         "physical_contract_sha256":expected_contract_sha256,"reference_plane_nm":C.REFERENCE_PLANE_NM,
         "normalization":C.PSCALE_DEFINITION,"truth_extractor_sha256":extractor_sha,
         "truth_schema":C.STATE_SCHEMA,"power_mapping_source":mapping_source,
         "power_mapping_supplement_sha256":supplement_sha})
