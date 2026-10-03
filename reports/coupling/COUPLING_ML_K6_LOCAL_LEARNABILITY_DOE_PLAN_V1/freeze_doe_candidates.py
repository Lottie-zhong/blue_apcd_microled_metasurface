import json,hashlib,math,csv
from pathlib import Path
from datetime import datetime,timezone
W=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=W/"reports/coupling/COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1"
OUT.mkdir(parents=True,exist_ok=True)
def read(rel): return json.loads((W/rel).read_text(encoding="utf-8"))
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def geom_hash(g): return sha_bytes(",".join(str(int(x)) for x in g).encode("ascii"))
def dist(a,b): return math.sqrt(sum(((int(x)-int(y))/130.0)**2 for x,y in zip(a,b)))
def gaps(g): return [290.0-(g[i]+g[(i+1)%6])/2.0 for i in range(6)]
geo_auth=read("reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json")
data_auth=read("reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json")
exp=read("reports/coupling/PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json")
excl=read("reports/coupling/PW_K6_GEOMETRY_EXCLUSION_REGISTRY_V1.json")
runner=read("DUMMY") if False else json.loads(Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1\APCD_GPU_PRODUCTION_RUNNER_V1_AUTHORITY.json").read_text(encoding="utf-8"))
loadauth=read("reports/coupling/PW_K6_5NM_FULL_PERIOD_MESH_STAGE1_LOAD_ONLY_VALIDATION_V1.json")
assert data_auth["status"]=="PASS" and len(data_auth["case_provenance"])==32
assert geo_auth["geometry_grammar"]["observed_bounds_nm"]==[100,230] and geo_auth["geometry_grammar"]["grid_step_nm"]==5
assert geo_auth["distance_convention"]=="sqrt(sum(((x-y)/130.0)^2 for x,y in zip(a,b)))"
rows=data_auth["case_provenance"]
valid=[]
for r in rows:
 g=list(map(int,r["ordered_D_nm"]))
 assert (r.get("scientific_validation") in {None,"PASS"} and r.get("scientific_state") in {None,"DONE","RECOVERED_TRUTH_VALID"}) and not r.get("replay",False) and geom_hash(g)==r["geometry_hash_sha256"]
 valid.append((r["case_id"],g))
assert len({tuple(g) for _,g in valid})==32
center=[sum(g[i] for _,g in valid)/len(valid) for i in range(6)]
reserved=[x["ordered_D_nm"] for x in exp["prospective_reserve_only"]]
protected=[x["ordered_D_nm"] for x in excl["entries"]]
existing=[g for _,g in valid]
for x in exp["training_expansion_stage1"]:
 if x["ordered_D_nm"] not in existing: existing.append(x["ordered_D_nm"])
for x in exp["existing_20G"]:
 if x["ordered_D_nm"] not in existing: existing.append(x["ordered_D_nm"])
for g in reserved+protected:
 if g not in existing: existing.append(g)
patterns=[[1,1,1,-1,-1,-1],[1,-1,-1,-1,1,1],[-1,1,-1,1,-1,1],[-1,-1,1,1,1,-1]]
assert all(sum(p[j] for p in patterns)==0 for j in range(6))
assert all(len(set(p))==2 and all(s in [-1,1] for s in p) for p in patterns)
rank=[]
for cid,g in valid:
 m=min(min(v-100,230-v) for v in g)
 mingap=min(gaps(g))
 center_d=math.sqrt(sum(((g[i]-center[i])/130.0)**2 for i in range(6)))
 # anchor must host exact symmetric 5 nm axial points and every sign-combination inside the frozen domain
 candidates=[]
 for i in range(6):
  for s in [-1,1]:
   q=g.copy();q[i]+=5*s;candidates.append(q)
 for p in patterns: candidates.append([g[i]+5*p[i] for i in range(6)])
 if not all(all(100<=v<=230 and v%5==0 for v in q) and min(gaps(q))>0 for q in candidates): continue
 if any(tuple(q) in {tuple(x) for x in existing} for q in candidates): continue
 rank.append((-m,-mingap,center_d,cid,g,mingap,candidates))
assert rank, "no truth-valid anchor accommodates the frozen symmetric design without collision"
rank.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
_,_,_,anchor_id,anchor,min_gap,geoms=rank[0]
# deterministic fallback ranking frozen by the above geometry-only tuple; response labels were not read
case_rows=[]
for i in range(6):
 for s,label in [(-1,"M"),(1,"P")]:
  g=anchor.copy();g[i]+=5*s
  cid=f"K6LDA1_DEV_D{i+1}_{label}05"
  case_rows.append({"case_id":cid,"role":"DEVELOPMENT_AXIS","axis_coordinate":f"D{i+1}","direction":label,"delta_nm":5*s,"ordered_D_nm":g})
for j,p in enumerate(patterns,1):
 g=[anchor[i]+5*p[i] for i in range(6)]
 case_rows.append({"case_id":f"K6LDA1_SEAL_C{j}","role":"SEALED_CONFIRMATION_COMBINATION","sign_pattern":p,"ordered_D_nm":g})
for q in case_rows:
 g=q["ordered_D_nm"]
 q["geometry_sha256_comma_joined_D1_D6"]=geom_hash(g)
 q["min_periodic_neighbor_clearance_nm"]=min(gaps(g))
 q["all_periodic_neighbor_clearances_nm"]=gaps(g)
 q["grid_domain_check"]=(len(g)==6 and all(100<=v<=230 and v%5==0 for v in g))
 q["no_overlap_check"]=min(gaps(g))>0
 q["duplicate_vs_existing32_or_reserved_or_protected"]=False
 q["canonical_pre_fsp_path"]=None
 q["runner_authority_status"]="NOT_AUTHORIZED_NO_CASE_MANIFEST_OR_LOAD_ONLY_PROOF"
assert len(case_rows)==16 and len({q["case_id"] for q in case_rows})==16
assert len({tuple(q["ordered_D_nm"]) for q in case_rows})==16
assert all(q["grid_domain_check"] and q["no_overlap_check"] for q in case_rows)
assert not any(tuple(q["ordered_D_nm"]) in {tuple(x) for x in existing} for q in case_rows)
# Check axial symmetry and sign-balanced confirmation only; no model outcomes used.
assert sum(1 for q in case_rows if q["role"]=="DEVELOPMENT_AXIS")==12
assert sum(1 for q in case_rows if q["role"]=="SEALED_CONFIRMATION_COMBINATION")==4
assert all(sum(p[j] for p in patterns)==0 for j in range(6))
now=datetime.now(timezone.utc).isoformat()
protocol={
 "schema":"COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_PROTOCOL_V1",
 "task":"COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1",
 "status":"FROZEN_GEOMETRY_RULES_BEFORE_RESPONSE_ANALYSIS",
 "frozen_utc":now,
 "authority":{"32G_dataset":"reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json","32G_dataset_sha256":sha_bytes((W/"reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json").read_bytes()),"geometry_domain":"reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json","geometry_domain_sha256":sha_bytes((W/"reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json").read_bytes()),"expansion_manifest_sha256":sha_bytes((W/"reports/coupling/PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json").read_bytes()),"geometry_exclusion_registry_sha256":sha_bytes((W/"reports/coupling/PW_K6_GEOMETRY_EXCLUSION_REGISTRY_V1.json").read_bytes()),"physical_contract_sha256":"32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5","ordered_geometry":"D1..D6 are position sensitive; sorting/cyclic registration/permutation augmentation forbidden"},
 "scope":{"fixed_MDC":True,"spacer_nm":237,"K":6,"pitch_nm":290,"ordered_diameter_domain_nm":[100,230],"grid_nm":5,"wavelength_nm":[440,460,1],"contract":"current integrated 3D periodic plane-wave FDTD contract","solver_entries_authorized":0,"training_fits_authorized":0,"reserve_cases":False},
 "anchor_selection":{"truth_valid_source":"32G formal dataset authority only","response_or_model_metrics_used":False,"eligibility":"anchor supports exact +/-5 nm on each of D1..D6 and all four frozen sign combinations; all points on 5 nm grid, within [100,230], non-overlap and no match with 32G, reserve, or protected ordered geometry","ordered_rule":["maximize minimum diameter-boundary margin min_i(min(D_i-100,230-D_i))","maximize minimum cyclic neighbor geometric clearance 290-(D_i+D_(i+1))/2; geometric non-overlap only, not a manufacturing threshold","minimize normalized Euclidean distance to coordinatewise centroid of formal 32G","lexicographic case_id"],"selected_anchor_case_id":anchor_id,"selected_anchor_ordered_D_nm":anchor,"selected_anchor_geometry_sha256":geom_hash(anchor),"boundary_margin_nm":min(min(v-100,230-v) for v in anchor),"min_periodic_neighbor_clearance_nm":min_gap,"32G_geometry_centroid_nm":center},
 "DOE":{"new_logical_cases":16,"development_axis_cases":12,"sealed_confirmation_cases":4,"axis_step_nm":5,"axis_rule":"for each ordered coordinate D_i, one case anchor with D_i-5 and one with D_i+5; all other coordinates fixed at anchor","confirmation_sign_patterns_by_ordered_D1_to_D6":patterns,"confirmation_rule":"all six coordinates move +/-5 nm, each coordinate has two plus and two minus across four cases; combinations remain sealed until model/protocol freeze","cyclic_permutation_augmentation":False,"clip_or_asymmetric_truncation":False,"all_rows_unique_from_truth32_reserve_and_exclusion_registry":True},
 "coverage_protocol":{"geometry_distance":"sqrt(sum(((D_i-D'_i)/130)^2)); formal geometry-domain authority","fixed_distance_bins":[[0,0.5],[0.5,1.0],[1.0,1.5],[1.5,None]],"neighbor_count_radii":[0.5,0.75,1.0,1.25,1.5],"pairwise_responses":{"C_hat":"symmetric complex-state relative L2 = 2||C_i-C_j||2/(||C_i||2+||C_j||2), aggregating 21 wavelengths x 7 transmitted orders x TE/TM; coordinates use formal C_PW reconstruction/H2 normalization","routing":"RMS eta difference over same paired 21x7 values from frozen H2","P_scale":"mean absolute log ratio |ln(P_i/P_j)| over 21 wavelength values from official truth P_scale"},"summaries":"per-coordinate ranges/quantiles; nearest-neighbor and radius neighbor counts; sample-cluster summary; Pearson/Spearman and fixed-bin summaries for pairwise geometry-distance vs response-difference","interpretation":"descriptive dependent pair comparisons only; no causal D_i derivative, no geometry*wavelength pseudo-replication, no ML fit/OOD feature use"},
 "future_local_validation":{"local_domain":"ordered six-dimensional discrete hypercube around anchor, each D_i in {anchor_i-5,anchor_i,anchor_i+5}; only anchor, 12 axial development points and 4 of 64 possible combined vertices sampled","inputs":"six ordered diameters, fixed positions/origin and wavelength grid; wavelength remains grouped within geometry","outputs":"Cartesian normalized C_hat per transmitted order and TE/TM coordinate plus independent positive scalar P_scale; same formal reference, source normalization and units","candidate":"single local affine Taylor/Ridge-free OLS baseline on centered deltaD/5 features; independent output channels for C_hat real/imaginary coordinates and separate P_scale; no PCA/rank truncation, no neural architecture search, no oracle physics labels","development_evaluation":"12 leave-one-axial-geometry-out folds; anchor plus other 11 development geometries train, all 21 wavelengths of held geometry test; after CV, one final fit on anchor+12 axial groups","confirmation":"freeze code, coefficients, preprocessing, metrics and protocol after development; only then open 4 combo truth once; no tuning/selection on confirmation; 4 points support only local check, not full-domain inference","decoder_and_gates":"predicted C_hat and predicted P_scale through original physical-state reconstruction and frozen H2; report original H1 component thresholds unchanged, including N/A/FAIL. No production admission; deterministic OLS cannot establish original seed-stability gate, so complete conjunctive H1 PASS is not claimable","training_budget":"zero neural optimizer updates; 12 deterministic geometry-grouped OLS solves for development CV plus one final OLS fit; 4 sealed evaluations once after freeze; no model selection or additional candidates","limits":"axial finite differences diagnose local coordinate response only; cannot show cross-coordinate interactions vanish; combo points assess only these four locations"},
 "setup_status":{"candidate_manifest":"design-only; no runner attempt or run ID","canonical_pre_fsp":"not generated: frozen Runner accepts only 12 approved Stage-1 identities and requires exact per-case authority manifest, LOAD-only proof, canonical FSP path/hash; no novel-case builder/schema is supported by current handoff","setup_builders_reviewed":["scripts/shared_fdtd/tools/build_medium_pw_setup_only_v1.py: fixed W2H setup only, not generic K6 case builder","PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1: 12 approved cases only"],"runner_head":"1afa3e30f1de5e0192be6240a3754c89e2eb6f25","runner_frozen_code_head":"783bd5741eb5e6853a3be5532624f4282f9488b7","diagnostic_overlay_supported":False,"production_monitor":"inherit current authority unchanged; independent two-air-plane audit blocked before setup/entry; monitor review is a launch dependency","zero_solver_structure_check":"geometry hashes, grid/domain, ordered IDs, duplicate/exclusion, periodic non-overlap, sign balance checked in candidate manifest"},
 "data_dependencies":{"existing_truth":"official 32 individual PW_COMPLEX_FLOQUET_STATE_V1 cases, verified against dataset authority SHA; do not consume prior aggregate prediction archives","C_hat":"POSTNP +z, orders m=-3..+3, n=0, TE/TM, formal H2 normalization","P_scale":"20G formal truth scalar; Stage-1 raw POSTNP E/H trapezoidal Poynting integration / unit-cell area / incident power per area","future_extraction":"frozen Runner truth path must generate state and raw E/H provenance; current novel-case authority missing; no label extraction or solve in this task"}
}
(OUT/"PREREGISTERED_PROTOCOL_V1.json").write_text(json.dumps(protocol,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf-8")
manifest={"schema":"COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_CANDIDATE_MANIFEST_V1","task":"COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1","status":"DESIGN_ONLY_NOT_RUNNER_AUTHORIZED","frozen_utc":now,"anchor":{"case_id":anchor_id,"ordered_D_nm":anchor,"geometry_sha256":geom_hash(anchor)},"base_contract_sha256":"32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5","candidate_count":16,"cases":case_rows,"setup":{"pre_fsp_generated":False,"pre_fsp_paths":[],"reason":"No supported novel-case authority/build flow; current Runner case-specific validator cannot accept design-only IDs."},"solver_authority":{"authorized":False,"entries":0,"new_hf_launch_authorized":False}}
(OUT/"CANDIDATE_MANIFEST_V1.json").write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf-8")
fields=["case_id","role","ordered_D1_D6_nm","geometry_sha256_comma_joined_D1_D6","min_periodic_neighbor_clearance_nm","runner_authority_status"]
with (OUT/"ORDERED_GEOMETRIES_V1.csv").open("w",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for q in case_rows:w.writerow({"case_id":q["case_id"],"role":q["role"],"ordered_D1_D6_nm":",".join(map(str,q["ordered_D_nm"])),"geometry_sha256_comma_joined_D1_D6":q["geometry_sha256_comma_joined_D1_D6"],"min_periodic_neighbor_clearance_nm":q["min_periodic_neighbor_clearance_nm"],"runner_authority_status":q["runner_authority_status"]})
pre={"schema":"COUPLING_ML_K6_LOCAL_DOE_ZERO_SOLVER_GEOMETRY_PREFLIGHT_V1","geometry_domain_status":geo_auth["status"],"bounds_nm":[100,230],"grid_nm":5,"ordered_parameters":geo_auth["geometry_grammar"]["ordered_parameters"],"sort_or_permutation":False,"candidate_count":len(case_rows),"all_in_domain_on_grid":all(q["grid_domain_check"] for q in case_rows),"all_periodic_nonoverlap":all(q["no_overlap_check"] for q in case_rows),"min_neighbor_clearance_nm":min(q["min_periodic_neighbor_clearance_nm"] for q in case_rows),"max_neighbor_clearance_nm":max(max(q["all_periodic_neighbor_clearances_nm"]) for q in case_rows),"min_neighbor_clearance_by_case":{q["case_id"]:q["min_periodic_neighbor_clearance_nm"] for q in case_rows},"all_unique_vs_32g_reserve_protected":True,"manufacturing_acceptance":"NOT_ASSERTED; independent fabrication minimum-gap authority unresolved","canonical_prefsp":"NOT_GENERATED_UNSUPPORTED_BY_CURRENT_NOVEL-CASE_AUTHORITY","runner_approved_case_ids":loadauth["approved_case_ids"],"new_case_ids_runner_approved":False,"solver_entry":False,"training":False}
(OUT/"GEOMETRY_PREFLIGHT_V1.json").write_text(json.dumps(pre,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf-8")
print(json.dumps({"anchor":anchor_id,"ordered_D_nm":anchor,"boundary_margin_nm":min(min(v-100,230-v) for v in anchor),"anchor_min_gap_nm":min_gap,"center":center,"cases":case_rows,"preflight":pre,"protocol_sha256":sha_bytes((OUT/"PREREGISTERED_PROTOCOL_V1.json").read_bytes()),"manifest_sha256":sha_bytes((OUT/"CANDIDATE_MANIFEST_V1.json").read_bytes())},ensure_ascii=False))
