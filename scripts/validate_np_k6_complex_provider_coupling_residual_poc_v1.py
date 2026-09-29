import os, json, hashlib
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),os.pardir))
POC=os.path.join(ROOT,"outputs","np_k6_complex_provider_coupling_residual_poc_v1")
def load(n):
    with open(os.path.join(POC,n),encoding="utf-8") as f:return json.load(f)
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def validate():
    m=load("poc_manifest.json");d=load("matched_domain_audit.json");r=load("reference_plane_audit.json");p=load("provider_interface_contract.json");c=load("artifact_checksums.json")
    assert m["schema"]=="NP_K6_COMPLEX_PROVIDER_AND_COUPLING_RESIDUAL_POC_V1"
    assert m["status"]=="COMPLEX_COMPONENT_COMPOSITION_BLOCKED_REFERENCE_PLANE" and m["zero_solver"] is True
    n=m["np_authority"];assert (n["rows"],n["logical_cases"],n["geometries"])==(8712,44,22)
    assert n["wavelengths_nm"]==list(range(445,456)) and n["u_x"]==0.0 and n["k_y"]==0.0
    assert n["transmission_orders"]==[-3,-2,-1,0,1,2,3] and n["reflection_orders"]==[-5,-4,-3,-2,-1,0,1,2,3,4,5]
    assert n["phase_contract"]["physical_component_composition_reference_plane"]=="PENDING"
    assert d["row_accounting"]["metadata_candidate_rows"]==440 and d["row_accounting"]["valid_C_component_rows"]==0
    assert d["geometry_identity"]["np_vs_coupling_overlap"] is False
    for k in ("coupling_h1_errors_used","coupling_candidate_labels_used","sealed_hf_target_read","new_model_fit","full_hf22_refit"):assert d["leakage_and_selection"][k] is False
    assert r["classification"]=="COMPLEX_COMPONENT_COMPOSITION_BLOCKED_REFERENCE_PLANE" and r["deterministic_transform_available"] is False and r["composition_allowed"] is False
    assert r["coupling_contract"]["mdc_right_plane_z_nm"]==975.0 and r["coupling_contract"]["np_component_plane_z_nm"]==1212.0 and r["coupling_contract"]["spacer_distance_nm"]==237.0
    assert r["coupling_contract"]["propagation_operator"]=="exp(+i*kz_sio2*d)"
    f=p["capability_flags"];assert f["NORMAL_INCIDENCE_ONLY"] is True and f["FULL_2x2_JONES_MATRIX"] is False and f["MULTI_INPUT_FLOQUET_SCATTERING_MATRIX"] is False and f["ARBITRARY_RETURNING_ORDER_RESCATTERING"] is False and f["PRODUCTION_APPROVED"] is False
    assert all(v==0 for v in p["governance"].values())
    assert m["baseline_plan"]["B1"]["status"]=="UNAVAILABLE_NOT_AUTHORITATIVE" and m["baseline_plan"]["B2"]["status"]=="BLOCKED_BEFORE_NUMERICAL_CONSTRUCTION"
    for rel,e in c["files"].items():
        path=os.path.join(POC,rel);assert os.path.isfile(path) and sha(path)==e["sha256"]
    assert not os.path.exists(os.path.join(ROOT,"outputs","np_k6_complex_deployment_provider_v1"))
    return {"status":"PASS","solver_calls":0,"metadata_candidate_rows":440,"valid_C_component_rows":0,"reference_plane_gate":True}
if __name__=="__main__":print(json.dumps(validate(),sort_keys=True))
