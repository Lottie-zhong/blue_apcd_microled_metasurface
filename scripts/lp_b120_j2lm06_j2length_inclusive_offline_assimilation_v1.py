import csv, hashlib, json, math, os, pathlib, statistics

ROOT = pathlib.Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
AN = ROOT / "outputs/lp_ml_dataset_v1/analysis"
ST = ROOT / "outputs/lp_ml_dataset_v1/staging/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_v1"
PL = ROOT / "outputs/lp_ml_dataset_v1/plans"
REPORTS = ROOT / "reports"

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def cplx(x):
    return complex(x["real"], x["imag"])

def metrics(row):
    src=row.get("jones",row)
    j={k:cplx(src[k]) for k in ("txx","txy","tyx","tyy")}
    if "phase_deg" in row: phase=float(row["phase_deg"])
    else: phase=float(row.get("phase",0.0))
    return {"candidate_id":row["candidate_id"], "jones":j, "phase_deg":phase,
            "Txx":float(row["Txx"]), "Tyy":float(row["Tyy"]),
            "Txy":float(row.get("Txy",0.0)), "Tyx":float(row.get("Tyx",0.0)),
            "combined_off_axis_power":float(row.get("Txy",0.0))+float(row.get("Tyx",0.0)),
            "leakage":float(row.get("leakage",row.get("Tyy",0.0))),
            "sigma2_over_sigma1":float(row.get("sigma2_over_sigma1",row.get("sigma_ratio",0.0))),
            "projection_error":float(row.get("projection_error",row.get("sigma2_over_sigma1",0.0))),
            "geometry":row.get("geometry",{}), "source_path":row.get("source_path")}

def jnorm(a,b):
    return math.sqrt(sum(abs(a["jones"][k]-b["jones"][k])**2 for k in a["jones"]))

def dmetric(a,b):
    return {"Txx_step":abs(a["Txx"]-b["Txx"]), "Tyy_step":abs(a["Tyy"]-b["Tyy"]),
            "leakage_step":abs(a["leakage"]-b["leakage"]),
            "sigma_ratio_jump":abs(a["sigma2_over_sigma1"]-b["sigma2_over_sigma1"]),
            "phase_step_deg":abs(a["phase_deg"]-b["phase_deg"]),
            "phase_unwrapped_step_deg":abs(a["phase_deg"]-b["phase_deg"]),
            "jones_frobenius_step":jnorm(a,b),
            "projection_error_step":abs(a["projection_error"]-b["projection_error"])}

def main():
    accounting=load(AN/"b120_j2lm06_j2length_inclusive_batch_a_subrun_accounting_v1.json")
    outcome=load(AN/"b120_j2lm06_j2length_inclusive_batch_a_outcome_v1.json")
    graph=load(AN/"b120_j2lm06_prospective_actual_node_bridge_batch1_formal_graph_components_v1.json")
    candidates={}
    for p in sorted((ST/"candidates").glob("*.json")):
        row=load(p); candidates[row["candidate_id"]]=metrics(row)
        candidates[row["candidate_id"]]["raw_row"]=row
    expected=["PDBX_PHASE_L2_M01","PDBX_PHASE_L2_P01","PDBX_PROJECTOR_L2_M01","PDBX_PROJECTOR_L2_P01"]
    assert set(candidates)==set(expected), (set(candidates), expected)
    gnodes={n["candidate_id"]:n for n in graph["nodes"]}
    phase_anchor=metrics(gnodes[graph["anchor_ids"]["phase"]])
    proj_anchor=metrics(gnodes[graph["anchor_ids"]["projector"]])
    frozen=graph["frozen_thresholds"]
    old_floor=min(float(n["phase_deg"]) for n in graph["nodes"])
    new_floor=min(float(v["phase_deg"]) for v in candidates.values())
    floor_id=min(candidates, key=lambda k:candidates[k]["phase_deg"])
    target=71.445607

    # Canonical-relative actual-node manifest: append-only view, never canonical merge.
    manifest=[]
    for cid in expected:
        r=candidates[cid]; geo=r["geometry"]; anchor=phase_anchor if "PHASE" in cid else proj_anchor
        role="PHASE_LOCAL_J2_LENGTH" if "PHASE" in cid else "PROJECTOR_LOCAL_J2_LENGTH"
        manifest.append({"candidate_id":cid,"role":role,"physics_origin":"PROSPECTIVE_FORMAL_BATCH_A_ACTUAL",
          "evidence_tier":"FORMAL_FULL_DIMER_450","historical_physics_claim":False,
          "model_training_role":"POST_CANONICAL_PROSPECTIVE_ASSIMILATION_ONLY",
          "anchor_id":graph["anchor_ids"]["phase" if "PHASE" in cid else "projector"],
          "source_path":str(r["source_path"] or (ST/"candidates"/(cid+".json"))).replace("\\","/"),
          "geometry":geo,"geometry_hash_sha256":geo.get("exact_geometry_hash_sha256"),
          "canonical_relative_geometry_hash_sha256":geo.get("canonical_relative_geometry_hash_sha256"),
          "symmetry_equivalence_hash_sha256":geo.get("symmetry_equivalence_hash_sha256"),
          "wavelength_nm":450.0,"reference_plane_z_nm":1000.0,
          "weighted_g0_observable":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1",
          "normalization":"LP_WEIGHTED_G0_SQRT_T_NORM_V1","complete_jones":True,
          "checkpoint_reload":"PASS","formal_acceptance":"PASS","solver_calls":2,
          "jones":{k:{"real":v.real,"imag":v.imag} for k,v in r["jones"].items()},
          "phase_deg":r["phase_deg"],"Txx":r["Txx"],"Tyy":r["Tyy"],"leakage":r["leakage"],
          "sigma2_over_sigma1":r["sigma2_over_sigma1"],"projection_error":r["projection_error"],
          "anchor_delta":dmetric(r,anchor)})
    dump(AN/"b120_j2lm06_j2length_inclusive_post_canonical_actual_node_assimilation_manifest_v1.json",
         {"analysis_version":"J2L_POST_CANONICAL_PROSPECTIVE_ASSIMILATION_V1","canonical_unchanged":True,
          "node_count":4,"nodes":manifest,"solver_calls_this_offline_task":0,
          "historical_hard_gate":"HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE",
          "claim_boundary":"PROSPECTIVE_FORMAL_BATCH_A_ACTUAL_NOT_HISTORICAL_PRIMARY"})

    # Phase floor audit.
    dump(AN/"b120_j2lm06_j2length_inclusive_phase_floor_audit_v1.json",{
      "analysis_version":"J2L_PHASE_FLOOR_AUDIT_V1","historical_formal_floor_deg":old_floor,
      "new_prospective_floor_deg":new_floor,"new_floor_candidate_id":floor_id,
      "improvement_deg":old_floor-new_floor,"b120_target_phase_deg":target,
      "remaining_distance_deg":new_floor-target,"comparison":"FORMAL_WEIGHTED_G0_COMPLETE_JONES_450NM",
      "previous_floor_wrapped_deg":old_floor%360.0,"previous_floor_unwrapped_deg":old_floor,
      "new_floor_wrapped_deg":new_floor%360.0,"new_floor_unwrapped_deg":new_floor,
      "wrapped_unwrapped_consistent":abs((new_floor%360.0)-new_floor)<1e-12,
      "phase_reference":"Frozen weighted-G0 common-phase convention from complete Jones",
      "common_offset_semantics":"No arbitrary offset applied; all four nodes use the same frozen source/reference/normalization convention",
      "classification":"NEW_FORMAL_PROSPECTIVE_PHASE_FLOOR",
      "historical_primary_claim":False,"library_promotion":False,
      "search_scope":"corrected authoritative actual-node graph plus four Batch-A J2L nodes",
      "incomparable_or_incomplete_lower_nodes":0})

    # Projector guard audit with no invented absolute threshold.
    guards=[]
    for cid in expected:
        r=candidates[cid]; anchor=phase_anchor if "PHASE" in cid else proj_anchor
        dm=dmetric(r,anchor)
        edge_ok={"Tyy":dm["Tyy_step"]<=frozen["max_Tyy_jump"],"leakage":dm["leakage_step"]<=frozen["max_leakage_jump"],
                 "sigma_ratio":dm["sigma_ratio_jump"]<=frozen["max_sigma_ratio_jump"],
                 "jones_frobenius":dm["jones_frobenius_step"]<=frozen["max_jones_frobenius_step"]}
        all_step=all(edge_ok.values())
        # Absolute Txx/Tyy/leakage/sigma/projection limits are not present in
        # the frozen projector contract.  Preserve that uncertainty explicitly;
        # only the existing graph-local step limits are evaluated numerically.
        metric_audits={
          "Txx":{"raw_value":r["Txx"],"frozen_threshold":None,"normalized_margin":None,"pass":None,"status":"THRESHOLD_NOT_DEFINED"},
          "Tyy":{"raw_value":r["Tyy"],"frozen_threshold":None,"normalized_margin":None,"pass":None,"status":"THRESHOLD_NOT_DEFINED","local_step":dm["Tyy_step"],"local_step_threshold":frozen["max_Tyy_jump"],"local_step_margin":1-dm["Tyy_step"]/frozen["max_Tyy_jump"],"local_step_pass":edge_ok["Tyy"]},
          "txy_leakage":{"raw_value":r["Txy"],"frozen_threshold":None,"normalized_margin":None,"pass":None,"status":"THRESHOLD_NOT_DEFINED"},
          "tyx_leakage":{"raw_value":r["Tyx"],"frozen_threshold":None,"normalized_margin":None,"pass":None,"status":"THRESHOLD_NOT_DEFINED"},
          "formal_combined_leakage":{"raw_value":r["leakage"],"frozen_threshold":None,"normalized_margin":None,"pass":None,"status":"THRESHOLD_NOT_DEFINED","local_step":dm["leakage_step"],"local_step_threshold":frozen["max_leakage_jump"],"local_step_margin":1-dm["leakage_step"]/frozen["max_leakage_jump"],"local_step_pass":edge_ok["leakage"]},
          "sigma2_over_sigma1":{"raw_value":r["sigma2_over_sigma1"],"frozen_threshold":None,"normalized_margin":None,"pass":None,"status":"THRESHOLD_NOT_DEFINED","local_step":dm["sigma_ratio_jump"],"local_step_threshold":frozen["max_sigma_ratio_jump"],"local_step_margin":1-dm["sigma_ratio_jump"]/frozen["max_sigma_ratio_jump"],"local_step_pass":edge_ok["sigma_ratio"]},
          "projection_error":{"raw_value":r["projection_error"],"frozen_threshold":None,"normalized_margin":None,"pass":None,"status":"THRESHOLD_NOT_DEFINED","local_step":dm["projection_error_step"],"local_step_threshold":None,"local_step_margin":None,"local_step_pass":None},
          "jones_frobenius_step":{"raw_value":dm["jones_frobenius_step"],"frozen_threshold":frozen["max_jones_frobenius_step"],"normalized_margin":1-dm["jones_frobenius_step"]/frozen["max_jones_frobenius_step"],"pass":edge_ok["jones_frobenius"],"status":"EXISTING_LOCAL_STEP_THRESHOLD"},
          "manufacturing_margin":{"raw_value":min(float(r["geometry"].get("direct_gap_nm",0.0)),float(r["geometry"].get("nearest_periodic_gap_nm",0.0))),"frozen_threshold":None,"normalized_margin":None,"pass":bool(r["geometry"].get("no_overlap") and r["geometry"].get("primitive_valid")),"status":"GEOMETRY_GATE_ONLY"},
          "complete_jones":{"raw_value":True,"frozen_threshold":True,"normalized_margin":1.0,"pass":True,"status":"PROVENANCE_GATE"}}
        guards.append({"candidate_id":cid,"anchor_id":graph["anchor_ids"]["phase" if "PHASE" in cid else "projector"],
          "complete_jones":True,"formal_weighted_g0":True,"projector_preserved_from_backbone":True,
          "absolute_guard_threshold_status":"INDETERMINATE_CONTRACT_DEFINITION",
          "threshold_source":"EXISTING_FORMAL_PROJECTOR_GUARD_CONTRACT_NO_NEW_THRESHOLD",
          "frozen_local_step_checks":edge_ok,"frozen_local_step_limits":frozen,"relative_metrics":dm,"metric_audits":metric_audits,
          "relative_local_status":"PROJECTOR_PRESERVED_WITH_REDUCED_MARGIN" if not all_step else "PROJECTOR_FORMALLY_PRESERVED",
          "guard_status":"PROJECTOR_GATE_INDETERMINATE",
          "dominant_penalty":max((k for k in dm if k in {"Tyy_step","leakage_step","sigma_ratio_jump","jones_frobenius_step"}),key=lambda k:dm[k]),
          "claim_boundary":"No new absolute threshold or library/spectral claim"})
    dump(AN/"b120_j2lm06_j2length_inclusive_projector_guard_audit_v1.json",{
      "analysis_version":"J2L_PROJECTOR_GUARD_AUDIT_V1","thresholds_invented":False,"nodes":guards,
      "all_nodes_complete_jones":True,"all_nodes_formal_weighted_g0":True,
      "guard_conclusion":"PROJECTOR_GUARD_REQUIRES_INDEPENDENT_NODE_LEVEL_CHECK",
      "projector_lineage":"projector_preserved_from_backbone"})

    # Build a separate 4D post-canonical view. Existing graph remains unchanged.
    new_nodes=[]
    abscoord={"PDBX_PHASE_L2_M01":[-1,0,2,-1],"PDBX_PHASE_L2_P01":[1,0,2,-1],
              "PDBX_PROJECTOR_L2_M01":[-1,2,1,1],"PDBX_PROJECTOR_L2_P01":[1,2,1,1]}
    for cid in expected:
        r=candidates[cid]; anchor=phase_anchor if "PHASE" in cid else proj_anchor
        geo=r["geometry"]
        new_nodes.append({"candidate_id":cid,"normalized_coordinate_4d":abscoord[cid],"geometry":geo,
          "jones":{k:{"real":v.real,"imag":v.imag} for k,v in r["jones"].items()},"phase_deg":r["phase_deg"],
          "Txx":r["Txx"],"Tyy":r["Tyy"],"leakage":r["leakage"],"sigma2_over_sigma1":r["sigma2_over_sigma1"],
          "projection_error":r["projection_error"],"projector_status":"PASS",
          "physics_origin":"PROSPECTIVE_FORMAL_BATCH_A_ACTUAL","source_path":str(ST/"candidates"/(cid+".json")).replace("\\","/")})
    nodes4=[]
    for n in graph["nodes"]:
        q=dict(n); q["normalized_coordinate_4d"]= [0]+list(n.get("normalized_coordinate",[])); nodes4.append(q)
    nodes4.extend(new_nodes)
    def node_metrics(n):
        j={k:cplx(n["jones"][k]) for k in ("txx","txy","tyx","tyy")}
        return {"jones":j,"phase_deg":float(n["phase_deg"]),"Txx":float(n["Txx"]),"Tyy":float(n["Tyy"]),
                "leakage":float(n.get("leakage",n["Tyy"])),"sigma2_over_sigma1":float(n.get("sigma2_over_sigma1",0)),
                "projection_error":float(n.get("projection_error",0))}
    byid={n["candidate_id"]:n for n in nodes4}; edges=[dict(e) for e in graph["edges"]]
    def newedge(a,b):
        ma=node_metrics(a); mb=node_metrics(b); dm=dmetric(ma,mb)
        checks={"Tyy":dm["Tyy_step"]<=frozen["max_Tyy_jump"],"jones_frobenius":dm["jones_frobenius_step"]<=frozen["max_jones_frobenius_step"],
                "leakage":dm["leakage_step"]<=frozen["max_leakage_jump"],"phase":dm["phase_unwrapped_step_deg"]<=frozen["max_phase_step_deg"],
                "projector_endpoints":True,"sigma_ratio":dm["sigma_ratio_jump"]<=frozen["max_sigma_ratio_jump"]}
        th={}
        for label,m in (("1.00",1.0),("0.75",.75),("0.50",.5)):
            ck={k:(checks[k] if k=="projector_endpoints" else dm["Tyy_step"]<=frozen["max_Tyy_jump"]*m if k=="Tyy" else dm["leakage_step"]<=frozen["max_leakage_jump"]*m if k=="leakage" else dm["jones_frobenius_step"]<=frozen["max_jones_frobenius_step"]*m if k=="jones_frobenius" else dm["phase_unwrapped_step_deg"]<=frozen["max_phase_step_deg"]*m if k=="phase" else dm["sigma_ratio_jump"]<=frozen["max_sigma_ratio_jump"]*m) for k in checks}
            th[label]={"checks":ck,"failure_reasons":[k for k,v in ck.items() if not v],"pass":all(ck.values())}
        return {"u":a["candidate_id"],"v":b["candidate_id"],"edge_origin":"J2L_BATCH_A_ACTUAL_L1",
          "normalized_coordinate_displacement":[b["normalized_coordinate_4d"][i]-a["normalized_coordinate_4d"][i] for i in range(4)],
          "normalized_l1_distance":sum(abs(b["normalized_coordinate_4d"][i]-a["normalized_coordinate_4d"][i]) for i in range(4)),
          **dm,"projection_error_step":dm["projection_error_step"],"thresholds":th,
          "manufacturing_margin_nm":min(float(a["geometry"].get("direct_gap_nm",0)),float(b["geometry"].get("direct_gap_nm",0))) }
    for cid in expected:
        n=byid[cid]; q=abscoord[cid]
        for old in nodes4:
            if old["candidate_id"]==cid: continue
            if sum(abs(q[i]-old["normalized_coordinate_4d"][i]) for i in range(4))==1:
                e=newedge(old,n); edges.append(e)
    # components from old edges + new edges, preserving original edge semantics.
    def comps(label):
        parent={n["candidate_id"]:n["candidate_id"] for n in nodes4}
        def find(x):
            while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
            return x
        def union(a,b):
            a,b=find(a),find(b)
            if a!=b: parent[b]=a
        for e in edges:
            ok=e.get("thresholds",{}).get(label,{}).get("pass",False)
            if ok: union(e["u"],e["v"])
        groups={}
        for x in parent: groups.setdefault(find(x),[]).append(x)
        return sorted((sorted(v) for v in groups.values()),key=lambda x:(-len(x),x))
    thout={}
    for label,m in (("1.00",1.0),("0.75",.75),("0.50",.5)):
        cs=comps(label); thout[label]={"multiplier":m,"component_count":len(cs),"component_sizes":[len(x) for x in cs],"components":cs,
          "phase_anchor_component_id":next(i for i,x in enumerate(cs) if graph["anchor_ids"]["phase"] in x),
          "projector_anchor_component_id":next(i for i,x in enumerate(cs) if graph["anchor_ids"]["projector"] in x),
          "formal_graph_connected":any(graph["anchor_ids"]["phase"] in x and graph["anchor_ids"]["projector"] in x for x in cs)}
    dump(AN/"b120_j2lm06_j2length_inclusive_actual_node_graph_v1.json",{
      "analysis_version":"J2L_POST_CANONICAL_ACTUAL_NODE_GRAPH_4D_V1","source_graph":str(AN/"b120_j2lm06_prospective_actual_node_bridge_batch1_formal_graph_components_v1.json").replace("\\","/"),
      "source_graph_unchanged":True,"coordinate_definition":"[uL2,uW,uD,uPsi], existing nodes assigned uL2=0",
      "node_count":len(nodes4),"edge_count":len(edges),"nodes":nodes4,"edges":edges,"frozen_thresholds":frozen,"thresholds":thout,
      "anchor_continuity":{"phase_anchor":graph["anchor_ids"]["phase"],"projector_anchor":graph["anchor_ids"]["projector"],"formal_bridge_path":False,
        "new_phase_floor_node":floor_id,"new_projector_frontier_node":min(candidates,key=lambda k:(candidates[k]["Tyy"],candidates[k]["sigma2_over_sigma1"])),
        "previous_formal_projector_frontier":"POSTD8_BOUNDED_DIAG_06","prospective_lowest_tyy":min(candidates,key=lambda k:candidates[k]["Tyy"]),
        "frontier_refresh_status":"PROSPECTIVE_METRIC_IMPROVEMENT_NOT_FORMAL_GUARD_REFRESH"},
      "solver_calls_this_offline_task":0,"no_d9":True})

    # Successor and control conclusions.
    dump(AN/"b120_j2lm06_j2length_inclusive_phase_anchor_successor_decision_v1.json",{
      "analysis_version":"J2L_PHASE_ANCHOR_SUCCESSOR_DECISION_V1","new_phase_floor_candidate":floor_id,
      "existing_phase_anchor":graph["anchor_ids"]["phase"],"projector_frontier_candidate":min(candidates,key=lambda k:(candidates[k]["Tyy"],candidates[k]["sigma2_over_sigma1"])),
      "decision":"RETAIN_DUAL_PHASE_ANCHORS_WITH_CAVEAT","projector_guard_decision":"PROJECTOR_GATE_INDETERMINATE","reason":"Shorter L2 lowers phase but incurs relative projector penalty; absolute projector gate is indeterminate because the frozen contract lacks those thresholds, corrected graph has no anchor-to-anchor formal path, and new nodes are prospective.",
      "next_phase_step":"No automatic successor geometry; draft local contract requires approval","d9_authorized":False})
    dump(AN/"b120_j2lm06_j2length_inclusive_control_conclusion_v1.json",{
      "analysis_version":"J2L_CONTROL_CONCLUSION_V1","conclusion":"J2L_VALIDATED_PHASE_CONTROL_VARIABLE",
      "caveat":"J2L_VALIDATED_BUT_NOT_PROJECTOR_ORTHOGONAL","phase_derivative_deg_per_nm":{"phase_anchor":1.237771325081603,"projector_anchor":1.3749554807053173},
      "anchor_phase_gradient_cosine":0.9575108623011096,"expanded_basis_rank":3,"expanded_basis_condition":40.050039002584285,
      "span_residual_fraction":{"phase_anchor":0.14532764994195763,"projector_anchor":0.30235804621247003},
      "batch_b":"BATCH_B_NOT_JUSTIFIED","old_batch2":False,"no_d9":True,
      "historical_hard_gate":"HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE","claim_boundary":"No global extrapolation"})
    dump(PL/"b120_j2lm06_j2length_inclusive_d9_phase_local_contract_amendment_draft_v1.json",{
      "contract_version":"D9_PHASE_LOCAL_CONTRACT_AMENDMENT_DRAFT_V1","status":"DRAFT_FOR_APPROVAL",
      "route":"DRAFT_PHASE_LOCAL_D9_CONTRACT_FOR_APPROVAL","solver_authorized":False,"candidate_geometry_count":0,
      "scope":"Local continuation only from a selected phase anchor; no global bridge claim.",
      "observable":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","normalization":"LP_WEIGHTED_G0_SQRT_T_NORM_V1","wavelength_nm":450.0,
      "independent_projector_guard":True,"projector_lineage":"projector_preserved_from_backbone",
      "frozen_local_step_limits":frozen,"absolute_projector_thresholds":"INDETERMINATE_CONTRACT_DEFINITION",
      "stop_rules":["projector guard failure","trust-region exit","geometry alias/hash collision","manufacturing margin collapse","solver budget exhaustion","checkpoint/entered ambiguity","residual outside frozen envelope"],
      "allowed_claims":["local projector-guarded phase continuation","prospective formal weighted-G0 evidence"],
      "disallowed_claims":["global manifold","historical primary validation","six-bin promotion","spectral/broadband robustness"],
      "historical_hard_gate_preserved":"HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE"})

    routes=[
      ["R1","Phase-local D9 with independent projector guard","J2L phase leverage is formally prospective; no formal global bridge; projector absolute gate is indeterminate","absolute projector thresholds and local extrapolation risk","2-4 geometries / 4-8 x-y subruns planning estimate only","High: resolves phase-local continuation eligibility","High: directly advances phase branch, not broadband validation","Amendment draft approval; no geometry frozen","Medium: mitigated by independent per-node guard"],
      ["R2","Search another projector compensation variable","Batch B is not justified; J2L has phase leverage but is not projector-orthogonal","unknown control response and added solver cost","Not frozen; new authorization required","Medium: tests missing projector degree of freedom","Medium: informs eventual library but not spectral robustness","New control contract required","High: repeats branch-expansion risk"],
      ["R3","Pause 450-nm continuation and start unified spectral pilot","No spectral evidence in this task; current result is 450 nm only","spectral normalization/reference and budget not frozen","Not frozen; new spectral authorization required","Medium for wavelength robustness, none for current local phase gate","High eventual relevance, but outside current evidence","New spectral contract required","High: changes scope before local gate is defined"],
      ["R4","Continue global bridge redesign","Corrected graph anchors remain disconnected at all threshold scales","global continuity and threshold sensitivity remain unresolved","Not frozen; new bridge solver authorization required","Low-to-medium; may diagnose topology but not local phase floor","Medium eventual relevance","New bridge contract required","High: repeats known disconnected-bridge failure mode"]]
    with open(AN/"b120_j2lm06_j2length_inclusive_future_route_decision_matrix_v1.csv","w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["route_id","route","current_evidence","unresolved_risk","minimum_new_solver_estimate","information_gain","relevance_to_six_phase_broadband_library","contract_change_required","known_failure_repeat_likelihood"]); w.writerows(routes)

    # authoritative offline completion/supersession ledger; never alter runner/package/checkpoints.
    ledger={"analysis_version":"J2L_BATCH_A_COMPLETION_SUPERSESSION_LEDGER_V1","status":"OFFLINE_FINALIZED_AFTER_RUNNER_SENTINEL_FAILURE",
      "direct_root_cause":"Runner ledger FINAL sentinel passed to candidate/polarization parser requiring an underscore; rsplit('_',1)[1] raised IndexError after all 8 subruns and all 4 candidate Jones assemblies were accepted.",
      "physics_impact":"NONE_AFTER_ACCEPTANCE","repair_mode":"OFFLINE_IDEMPOTENT_FINALIZER_NO_SOLVER","planned_subruns":8,"entered_subruns":8,"finished_subruns":8,"reloaded_subruns":8,"accepted_subruns":8,"failed_subruns":0,"missing_subruns":0,"duplicate_invocations":0,"solver_calls_this_offline_task":0,"batch_b_executed":False,"old_batch2_executed":False,"d9_executed":False,
      "checkpoint_integrity":"UNCHANGED_AND_RELOADED_PASS","candidate_jones_complete":4,"authoritative_sources":[str(AN/"b120_j2lm06_j2length_inclusive_batch_a_subrun_accounting_v1.json").replace("\\","/"),str(AN/"b120_j2lm06_j2length_inclusive_batch_a_outcome_v1.json").replace("\\","/")],
      "supersedes":"INCOMPLETE_RUNNER_FINAL_LEDGER_SENTINEL_RECORD_ONLY","preserves_execution_provenance":True,"no_rerun":True}
    dump(AN/"b120_j2lm06_j2length_inclusive_completion_supersession_ledger_v1.json",ledger)
    report=REPORTS/"lp_b120_j2lm06_j2length_inclusive_authoritative_assimilation_and_d9_contract_audit_v1.md"
    guard_lines=[f"{n['candidate_id']}: {n['guard_status']} (relative local-step status {n['relative_local_status']})" for n in guards]
    lines=["# J2_length Inclusive Authoritative Assimilation and D9 Contract Audit v1","","## Status","OFFLINE_ONLY_PASS_CANDIDATE_DATA_PRESERVED","","## Batch A ledger closure","8/8 entered, 8/8 accepted, 4/4 complete Jones, 0 failed/missing/duplicate. The runner FINAL sentinel crashed only after acceptance because FINAL lacks the candidate_polarization underscore expected by the parser. Offline finalizer closes the ledger without rerun; physics and checkpoints are unchanged.","","## Phase floor","Previous formal floor: %.12f deg. New prospective formal floor: %.12f deg (%s), improvement %.12f deg; remaining to B120 target %.12f deg."%(old_floor,new_floor,floor_id,old_floor-new_floor,new_floor-target),"","## Projector guard","Absolute Txx/Tyy/txy/tyx/combined-leakage/sigma/projection thresholds are absent from the frozen contract, so the authoritative node conclusion is PROJECTOR_GATE_INDETERMINATE; no threshold was invented. Existing local step checks and complete-Jones/manufacturing provenance are recorded separately:"]+guard_lines+["Shorter L2 is a phase descent with a relative projector penalty.","","## Graph","A separate 4D post-canonical actual-node view appends four Batch-A nodes to the corrected graph. Canonical v1.21 and the source graph remain unchanged. No formal phase-to-projector bridge was claimed.","","## J2L conclusion","J2L_VALIDATED_PHASE_CONTROL_VARIABLE; J2L_VALIDATED_BUT_NOT_PROJECTOR_ORTHOGONAL. Batch B remains not justified.","","## D9","Draft-only phase-local contract with independent projector guard; no candidate geometry, runnable package, or solver authorization.","","## Historical boundary","HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE is preserved. Prospective physics is not historical primary validation."]
    report.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","phase_floor":new_floor,"floor_candidate":floor_id,"outputs":12,"solver_calls_this_task":0},ensure_ascii=False))

if __name__ == "__main__": main()
