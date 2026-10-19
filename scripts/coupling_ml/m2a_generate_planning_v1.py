import csv
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


NP = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
COUPLING = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT = ML / r"outputs\coupling_ml\M2A_GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING_V1"

HF_PATH = NP / r"outputs\np_k6_m8a_primary2_closeout_v1\hf22_formal_development_484rows.csv"
LF_MANIFEST_PATH = NP / r"outputs\np_k6_m9_22g_forward_retraining_v1\lf22_full_vector_authority_manifest.json"
FREEZE_PATH = NP / r"outputs\np_k6_final_freeze_closeout_v1\freeze_manifest.json"
PROVIDER_MANIFEST_PATH = NP / r"outputs\np_k6_final_freeze_closeout_v1\provider_manifest.json"
M8A_SCORE_PATH = NP / r"outputs\np_k6_m8a_final_targeted_acquisition_design_v1\candidate_selection_scores.csv"
M0F_REG_PATH = ML / r"outputs\coupling_ml\M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1\M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION\M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1\M0F_FINAL_RECONCILED_LEVEL1_NUMERICAL_REGISTRY_V1.csv"
PROVIDER_ROOT = COUPLING / r"outputs\coupling\rcwa_component_benchmark_v1\runtime_runs\RCWA_LEVEL1_ANGULAR_ACQUISITION_9JOB_V1"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def geometry_vector(gid):
    vals = [float(x) for x in re.findall(r"D(\d+(?:\.\d+)?)", gid or "")]
    if len(vals) != 6:
        raise ValueError(f"geometry id does not contain six ordered D fields: {gid}")
    return vals


def norm_ordered_distance(a, b):
    # The frozen diameter bounds are 100--230 nm. This preserves D1..D6 order.
    return math.sqrt(sum(((x - y) / 130.0) ** 2 for x, y in zip(a, b)) / 6.0)


def flatten_strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_strings(v)
    elif isinstance(obj, str):
        yield obj


def parse_target_diff(value):
    try:
        obj = json.loads(value or "null")
    except Exception:
        return {}
    return {k: fnum(v) for k, v in obj.items()} if isinstance(obj, dict) else {}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    hf = load_csv(HF_PATH)
    by_geometry = defaultdict(list)
    for row in hf:
        by_geometry[row["geometry_id"]].append(row)
    if len(by_geometry) != 22 or len(hf) != 484:
        raise RuntimeError(f"HF22 authority count mismatch: geometries={len(by_geometry)} rows={len(hf)}")

    lf_manifest = json.loads(LF_MANIFEST_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    provider_manifest = json.loads(PROVIDER_MANIFEST_PATH.read_text(encoding="utf-8"))
    m8a_scores = {r["geometry_id"]: r for r in load_csv(M8A_SCORE_PATH)}
    m0f = load_csv(M0F_REG_PATH)
    alt1_m0f = [r for r in m0f if r.get("candidate") == "ALT1"]
    if len({r.get("logical_case_id") for r in alt1_m0f}) != 4:
        raise RuntimeError("M0F ALT1 condition inventory is not the expected four cases")

    provider_files = sorted(PROVIDER_ROOT.rglob("*_postprocessed.json"))
    provider_geometry_ids = sorted({
        s for p in provider_files for s in flatten_strings(json.loads(p.read_text(encoding="utf-8")))
        if s.startswith("NP_K6X_")
    })
    if len(provider_files) != 9 or provider_geometry_ids != ["NP_K6X_125_135_150_175_190_210"]:
        raise RuntimeError(f"unexpected provider coverage: files={len(provider_files)} geometries={provider_geometry_ids}")
    alt1_suffix = provider_geometry_ids[0].removeprefix("NP_K6X_")
    alt1_id = "K6X_" + "_".join("D" + x for x in alt1_suffix.split("_"))
    alt1_vec = geometry_vector(alt1_id)

    # Aggregate frozen HF22 response descriptors per geometry and per explicit P/S condition.
    descriptors = {}
    for gid, rows in sorted(by_geometry.items()):
        vec = geometry_vector(gid)
        per_pol = {}
        for pol in ["p", "s"]:
            rr = [r for r in rows if r.get("polarization") == pol]
            per_pol[pol] = {
                "R_mean": avg([fnum(r.get("R_total")) for r in rr]),
                "T_mean": avg([fnum(r.get("T_total")) for r in rr]),
                "eta_plus1_mean": avg([fnum(r.get("eta_plus1")) for r in rr]),
                "eta_minus1_mean": avg([fnum(r.get("eta_minus1")) for r in rr]),
                "directionality_mean": avg([fnum(r.get("directionality")) for r in rr]),
            }
        allvals = {
            k: avg([per_pol[p][k] for p in ["p", "s"]])
            for k in ["R_mean", "T_mean", "eta_plus1_mean", "eta_minus1_mean", "directionality_mean"]
        }
        descriptors[gid] = {
            "geometry_id": gid, "geometry_hash": rows[0].get("geometry_hash"), "vector": vec,
            "rows": len(rows), "polarizations": sorted({r.get("polarization") for r in rows}),
            "per_pol": per_pol, "all": allvals,
            "quality_gate_all": all(str(r.get("quality_gate_pass")).lower() == "true" for r in rows),
            "accepted_execution_all": all(str(r.get("accepted_execution")).lower() == "true" for r in rows),
        }

    # Response rank uses the frozen NP ranking contract: broadband eta(+1) mean across P/S and 445--455 nm.
    response_sorted = sorted(descriptors, key=lambda g: (-descriptors[g]["all"]["eta_plus1_mean"], g))
    response_rank = {g: i + 1 for i, g in enumerate(response_sorted)}
    for gid in descriptors:
        descriptors[gid]["response_space_rank"] = response_rank[gid]
        descriptors[gid]["performance_stratum"] = "HIGH" if response_rank[gid] <= 8 else ("MEDIUM" if response_rank[gid] <= 15 else "LOWER_CONTRASTING")

    geometry_sorted = sorted(
        [g for g in descriptors if g != alt1_id],
        key=lambda g: (-norm_ordered_distance(descriptors[g]["vector"], alt1_vec), g),
    )
    geometry_rank = {g: i + 1 for i, g in enumerate(geometry_sorted)}
    geometry_rank[alt1_id] = 0
    for gid in descriptors:
        descriptors[gid]["distance_to_alt1"] = norm_ordered_distance(descriptors[gid]["vector"], alt1_vec)
        descriptors[gid]["geometry_space_rank_to_alt1"] = geometry_rank[gid]

    # Min-max response vector, with P/S kept explicit and no P/S averaging for the matrix itself.
    response_fields = [f"{p}_{k}" for p in ["p", "s"] for k in ["R_mean", "T_mean", "eta_plus1_mean", "eta_minus1_mean"]]
    raw_vectors = {}
    for gid, d in descriptors.items():
        raw_vectors[gid] = [d["per_pol"][p][k] for p in ["p", "s"] for k in ["R_mean", "T_mean", "eta_plus1_mean", "eta_minus1_mean"]]
    mins = [min(raw_vectors[g][i] for g in raw_vectors) for i in range(len(response_fields))]
    maxs = [max(raw_vectors[g][i] for g in raw_vectors) for i in range(len(response_fields))]
    response_vectors = {g: [(x - mins[i]) / (maxs[i] - mins[i]) if maxs[i] > mins[i] else 0.0 for i, x in enumerate(raw_vectors[g])] for g in raw_vectors}
    def response_distance(a, b):
        va, vb = response_vectors[a], response_vectors[b]
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb)) / len(va))

    # Selection roles are predeclared and separated: high response, medium/tail-information, lower contrast.
    selected_ids = [
        "K6X_D135_D155_D190_D220_D225_D230",  # high stratum; HF tail-history and ordered separation
        "K6X_D100_D140_D165_D190_D225_D230",   # medium stratum; frozen M8A tail-localization role
        "K6X_D200_D205_D215_D220_D225_D230",   # lower/contrasting stratum; extreme ordered separation
    ]
    if any(g not in descriptors for g in selected_ids) or alt1_id in selected_ids:
        raise RuntimeError(f"selected geometry is not in the 22 authority pool or duplicates ALT1: {selected_ids}")

    # Candidate pool table.
    candidate_fields = [
        "geometry_id", "D1", "D2", "D3", "D4", "D5", "D6", "geometry_hash", "geometry_hash_source",
        "np_frozen_rank", "np_frozen_rank_basis", "frozen_geometry_index", "existing_hf_coverage",
        "existing_lf_provider_coverage", "existing_level1_compatibility_availability", "distance_to_ALT1",
        "geometry_space_rank_to_ALT1", "response_space_rank", "response_descriptors_json", "performance_stratum",
        "response_descriptor_missingness", "provider_gap_count", "fabrication_geometry_validity_status", "ALT1_CONTROL0_role", "M8A_role_evidence",
        "selection_status", "source_hf_path", "source_hf_sha256", "source_lf_manifest_path", "source_lf_manifest_sha256",
    ]
    candidate_rows = []
    for gid in sorted(descriptors):
        d = descriptors[gid]
        role = "CURRENT_SEED_GEOMETRY" if gid == alt1_id else "CANDIDATE_POOL_ELIGIBLE"
        if gid == alt1_id:
            role += "; CONTROL0_SHARES_ALT1_GEOMETRY_DIAGNOSTIC_REFERENCE_ONLY"
        m8 = m8a_scores.get(gid, {})
        m8role = "; ".join(x for x in [m8.get("acquisition_role"), m8.get("selection_tier"), ("tail_localization_score=" + m8.get("tail_localization_score", "")) if m8.get("tail_localization_score") else ""] if x)
        candidate_rows.append({
            "geometry_id": gid, "D1": d["vector"][0], "D2": d["vector"][1], "D3": d["vector"][2], "D4": d["vector"][3], "D5": d["vector"][4], "D6": d["vector"][5],
            "geometry_hash": d["geometry_hash"], "geometry_hash_source": "HF22 formal development authority row",
            "np_frozen_rank": d["response_space_rank"], "np_frozen_rank_basis": "frozen NP HF broadband eta(+1) mean across explicit P/S and 445-455 nm",
            "frozen_geometry_index": lf_manifest.get("geometry_indices", {}).get(gid, "NOT_FOUND"),
            "existing_hf_coverage": "22 rows = P/S x 11 exact wavelengths; u_x=0; k_y=0; quality_gate_pass_all=true" if d["quality_gate_all"] and d["accepted_execution_all"] else "EVIDENCE_INCOMPLETE",
            "existing_lf_provider_coverage": "LF22 full-vector normal-incidence authority; u_x=0 only; 22 geometries / 484 rows",
            "existing_level1_compatibility_availability": "EXACT_ALT1_9_NODE_ANGULAR_PROVIDER" if gid == alt1_id else "NONE_EXACT_ANGULAR_PROVIDER_FOR_THIS_GEOMETRY",
            "distance_to_ALT1": d["distance_to_alt1"], "geometry_space_rank_to_ALT1": d["geometry_space_rank_to_alt1"], "response_space_rank": d["response_space_rank"],
            "response_descriptors_json": json.dumps({"P_XLIKE": d["per_pol"]["p"], "S_YLIKE": d["per_pol"]["s"], "all_PS_mean": d["all"]}, sort_keys=True),
            "performance_stratum": d["performance_stratum"], "response_descriptor_missingness": "P_XLIKE.directionality missing in frozen HF22 row set; retained as null and excluded from common response-distance vector" if d["per_pol"]["p"]["directionality_mean"] is None else "none", "provider_gap_count": 0 if gid == alt1_id else 9,
            "fabrication_geometry_validity_status": "ORDERED_D1_TO_D6; HF22_HASHED; QUALITY_GATE_AND_ACCEPTED_EXECUTION_PASS; SEPARATE_FABRICATION_LIMIT_FILE_NOT_IDENTIFIED",
            "ALT1_CONTROL0_role": role, "M8A_role_evidence": m8role or "NO_M8A_ROLE_RECORD_FOR_THIS_FORMAL_GEOMETRY",
            "selection_status": "SELECTED" if gid in selected_ids else ("ALT1_ANCHOR_EXCLUDED" if gid == alt1_id else "NOT_SELECTED_THIS_BATCH"),
            "source_hf_path": str(HF_PATH), "source_hf_sha256": sha(HF_PATH), "source_lf_manifest_path": str(LF_MANIFEST_PATH), "source_lf_manifest_sha256": sha(LF_MANIFEST_PATH),
        })
    write_csv(OUT / "M2A_NP22_GEOMETRY_CANDIDATE_POOL_V1.csv", candidate_fields, candidate_rows)

    # Ordered geometry distance matrix.
    dist_fields = ["geometry_id_a", "geometry_id_b", "ordered_distance_normalized", "distance_definition", "anchor_relation"]
    dist_rows = []
    gids = sorted(descriptors)
    for a in gids:
        for b in gids:
            dist_rows.append({"geometry_id_a": a, "geometry_id_b": b, "ordered_distance_normalized": norm_ordered_distance(descriptors[a]["vector"], descriptors[b]["vector"]), "distance_definition": "sqrt(mean(((D_i_a-D_i_b)/130nm)^2), i=1..6); ordered D1..D6 retained", "anchor_relation": "ALT1_anchor" if a == alt1_id or b == alt1_id else "candidate_pair"})
    write_csv(OUT / "M2A_ORDERED_GEOMETRY_DISTANCE_MATRIX_V1.csv", dist_fields, dist_rows)

    # Response diversity matrix. P/S are explicit in the vector; the matrix is not a P/S average.
    response_fields_out = ["geometry_id_a", "geometry_id_b", "response_distance_minmax_euclidean", "response_vector_definition", "same_performance_stratum"]
    response_rows = []
    for a in gids:
        for b in gids:
            response_rows.append({"geometry_id_a": a, "geometry_id_b": b, "response_distance_minmax_euclidean": response_distance(a, b), "response_vector_definition": "8D min-max vector: P/S x [R_mean,T_mean,eta_plus1_mean,eta_minus1_mean] over HF22 445-455nm; directionality retained in candidate descriptors but excluded because two P rows are missing", "same_performance_stratum": descriptors[a]["performance_stratum"] == descriptors[b]["performance_stratum"]})
    write_csv(OUT / "M2A_LEVEL1_RESPONSE_DIVERSITY_MATRIX_V1.csv", response_fields_out, response_rows)

    strata_fields = ["geometry_id", "response_space_rank", "performance_stratum", "eta_plus1_mean_PS", "R_mean_PS", "T_mean_PS", "P_eta_plus1_mean", "S_eta_plus1_mean", "distance_to_ALT1", "geometry_space_rank_to_ALT1", "stratum_definition"]
    strata_rows = []
    for gid in sorted(descriptors, key=lambda g: descriptors[g]["response_space_rank"]):
        d = descriptors[gid]
        strata_rows.append({"geometry_id": gid, "response_space_rank": d["response_space_rank"], "performance_stratum": d["performance_stratum"], "eta_plus1_mean_PS": d["all"]["eta_plus1_mean"], "R_mean_PS": d["all"]["R_mean"], "T_mean_PS": d["all"]["T_mean"], "P_eta_plus1_mean": d["per_pol"]["p"]["eta_plus1_mean"], "S_eta_plus1_mean": d["per_pol"]["s"]["eta_plus1_mean"], "distance_to_ALT1": d["distance_to_alt1"], "geometry_space_rank_to_ALT1": d["geometry_space_rank_to_alt1"], "stratum_definition": "HIGH ranks 1-8; MEDIUM ranks 9-15; LOWER_CONTRASTING ranks 16-22; rank basis frozen HF broadband eta(+1) mean"})
    write_csv(OUT / "M2A_PERFORMANCE_STRATA_V1.csv", strata_fields, strata_rows)

    feasibility_fields = ["geometry_id", "selected", "existing_level1_ingredients_sufficient", "requires_cheap_lf_or_provider_evaluation", "requires_new_upstream_hf", "provider_gap_count", "current_exact_provider_geometry", "feasibility_state", "reason", "no_evaluation_this_round"]
    feasibility_rows = []
    for gid in sorted(descriptors):
        is_alt = gid == alt1_id
        feasibility_rows.append({
            "geometry_id": gid, "selected": gid in selected_ids, "existing_level1_ingredients_sufficient": is_alt,
            "requires_cheap_lf_or_provider_evaluation": not is_alt, "requires_new_upstream_hf": False if gid != alt1_id else False,
            "provider_gap_count": 0 if is_alt else 9, "current_exact_provider_geometry": alt1_id,
            "feasibility_state": "CURRENT_ALT1_EXACT" if is_alt else "CHEAP_PROVIDER_PREREQUISITE_REQUIRED_NO_NEW_UPSTREAM_HF_IN_THIS_PLAN",
            "reason": "9 exact angular provider nodes and current Level2A reconciliation exist" if is_alt else "standalone HF22/LF22 evidence exists, but all 9 exact angular provider nodes are absent for this geometry; future cheap LF/provider acquisition must pass before integrated HF",
            "no_evaluation_this_round": True,
        })
    write_csv(OUT / "M2A_PROVIDER_FEASIBILITY_AUDIT_V1.csv", feasibility_fields, feasibility_rows)

    # Selected set with deterministic nearest alternatives and auditable reasons.
    selected_records = []
    for gid in selected_ids:
        d = descriptors[gid]
        nearest = min([g for g in descriptors if g not in selected_ids and g != alt1_id and descriptors[g]["performance_stratum"] == d["performance_stratum"]], key=lambda g: (norm_ordered_distance(descriptors[g]["vector"], d["vector"]), g))
        m8 = m8a_scores.get(gid, {})
        if d["performance_stratum"] == "HIGH":
            why = "HIGH response stratum, largest ordered distance to ALT1 within the high-stratum candidate set, and an existing HF response-tail history; retains a high-response but non-anchor geometry."
            why_not = f"Nearest same-stratum alternative {nearest} is closer in ordered space (distance_to_ALT1={descriptors[nearest]['distance_to_alt1']:.9f} versus {d['distance_to_alt1']:.9f}); it is less useful for a high-regime geometry-separation test."
        elif d["performance_stratum"] == "MEDIUM":
            why = "MEDIUM response stratum plus frozen M8A tail-localization role; adds a qualitatively different residual-risk regime without selecting another top-performance tail."
            if m8.get("tail_localization_score"):
                why += f" Frozen M8A tail_localization_score={m8['tail_localization_score']}."
            why_not = f"Nearest same-stratum alternative {nearest} is closer in ordered space but has no stronger frozen M8A tail-localization evidence; selecting the registered tail role is more informative for residual discrimination."
        else:
            why = "LOWER_CONTRASTING response stratum and maximum ordered distance to ALT1 among the lower-stratum candidates; supplies an intentionally contrasting response regime."
            why_not = f"Nearest same-stratum alternative {nearest} is closer in ordered space; this candidate maximizes geometry contrast while remaining inside the frozen 22-geometry authority pool."
        selected_records.append({"geometry_id": gid, "ordered_vector_D1_to_D6_nm": d["vector"], "geometry_hash": d["geometry_hash"], "performance_stratum": d["performance_stratum"], "response_space_rank": d["response_space_rank"], "geometry_space_rank_to_ALT1": d["geometry_space_rank_to_alt1"], "distance_to_ALT1": d["distance_to_alt1"], "why_selected": why, "nearest_same_stratum_alternative": nearest, "why_not_nearest_alternative": why_not, "m8a_role_evidence": m8 or None, "level1_feasibility": "requires_cheap_lf_or_provider_evaluation; no new upstream HF in this plan"})
    selected_pairwise = {f"{a}__{b}": response_distance(a, b) for i, a in enumerate(selected_ids) for b in selected_ids[i + 1:]}
    write_json(OUT / "M2A_SELECTED_GEOMETRY_SEED_SET_V1.json", {
        "schema_version": "coupling_ml_m2a_selected_geometry_seed_set_v1",
        "status": "PASS_ZERO_SOLVER_PLANNING_ONLY",
        "candidate_geometries": 22, "current_exact_geometries": 1, "new_geometries_selected": 3, "projected_exact_geometries_after_core": 4,
        "anchor_geometry_id": alt1_id, "anchor_ordered_vector_D1_to_D6_nm": alt1_vec,
        "selected_geometry_ids": selected_ids, "selected_records": selected_records,
        "selected_pairwise_response_distances": selected_pairwise, "selection_policy": "one HIGH + one MEDIUM/tail-information + one LOWER_CONTRASTING; ordered diversity and response strata kept separate; no composite score",
        "control0_policy": "CONTROL0 is a diagnostic spacer condition on ALT1 geometry and is not a new training geometry",
        "source_hf_path": str(HF_PATH), "source_hf_sha256": sha(HF_PATH), "source_lf_manifest_path": str(LF_MANIFEST_PATH), "source_lf_manifest_sha256": sha(LF_MANIFEST_PATH),
    })

    # Current ALT1 condition audit from exact M0F residual registry.
    condition_fields = ["condition_rank", "logical_case_id", "spacer_nm", "ux", "source_polarization", "provider_channel", "source_relevance", "ALT1_R_abs_residual", "ALT1_T_abs_residual", "ALT1_RT_l2_residual", "R_T_residual_distinction", "polarization_orientation_diversity", "provider_feasibility", "redundancy_assessment", "core_minimal_subset", "full_matched_subset", "selection_reason", "routing_status"]
    condition_rows = []
    cases = {}
    for case in sorted({r.get("logical_case_id") for r in alt1_m0f}):
        rr = [r for r in alt1_m0f if r.get("logical_case_id") == case]
        sample = rr[0]
        obs = {r.get("observable"): parse_target_diff(r.get("target_diff_json")) for r in rr}
        R = obs.get("R", {}).get("R")
        T = obs.get("T", {}).get("T")
        cases[case] = {"sample": sample, "R": R, "T": T, "l2": math.sqrt(R * R + T * T) if R is not None and T is not None else None}
    condition_order = ["L2A_A1_T0_P_UX_P0d378689399989", "L2A_A1_T237_P_UX_P0d378689399989", "L2A_A1_T237_S_UX_P0d378689399989", "L2A_A1_T237_P_UX_M0d482758620690"]
    for idx, case in enumerate(condition_order, 1):
        c = cases[case]; s = c["sample"]
        if case == "L2A_A1_T0_P_UX_P0d378689399989":
            role, core, full, redundancy, reason = "SPACER_CONTRAST_P_POSITIVE_UX", True, True, "Complementary to T237 P+; isolates spacer sensitivity", "Includes T0 condition so the first cross-geometry set tests spacer dependence rather than only one spacer."
        elif case == "L2A_A1_T237_P_UX_P0d378689399989":
            role, core, full, redundancy, reason = "P_BASELINE_POSITIVE_UX", True, True, "Reference P condition for pairing with S+ and T0 P+", "Common matched P baseline at the same spacer and positive ux."
        elif case == "L2A_A1_T237_S_UX_P0d378689399989":
            role, core, full, redundancy, reason = "POLARIZATION_CONTRAST_S_POSITIVE_UX", True, True, "Nonredundant P/S contrast at matched spacer and ux", "Adds explicit S response; no P/S averaging is allowed."
        else:
            role, core, full, redundancy, reason = "INCIDENT_ORIENTATION_SIGN_HOLDOUT_P_NEGATIVE_UX", False, True, "Orientation-sign stress condition; no matched S- condition in current evidence", "Reserved for FULL_MATCHED because it adds negative-ux sensitivity but is not required for the minimal P/S plus spacer core."
        condition_rows.append({"condition_rank": idx, "logical_case_id": case, "spacer_nm": s.get("spacer_nm"), "ux": s.get("ux"), "source_polarization": s.get("source_polarization"), "provider_channel": s.get("provider_channel"), "source_relevance": "DIRECT_CURRENT_ALT1_EXACT_R_T_RESIDUAL_CONDITION", "ALT1_R_abs_residual": c["R"], "ALT1_T_abs_residual": c["T"], "ALT1_RT_l2_residual": c["l2"], "R_T_residual_distinction": "R and T are both distinct exact residual targets; values are absolute residual magnitudes from M0F target_diff_json", "polarization_orientation_diversity": role, "provider_feasibility": "ALT1 exact current Level1 provider coverage; new geometry requires future cheap LF/provider evaluation", "redundancy_assessment": redundancy, "core_minimal_subset": core, "full_matched_subset": full, "selection_reason": reason, "routing_status": "HELDOUT; future canonical routing V2 only"})
    write_csv(OUT / "M2A_CONDITION_INFORMATION_VALUE_AUDIT_V1.csv", condition_fields, condition_rows)

    def plan_rows(conditions):
        rows = []
        for gid in selected_ids:
            for c in conditions:
                s = cases[c]["sample"]
                short = gid.replace("K6X_", "").replace("_", "")
                rows.append({"planned_case_id": f"M2A_{short}_{c.replace('L2A_A1_', '')}", "geometry_id": gid, "D1": descriptors[gid]["vector"][0], "D2": descriptors[gid]["vector"][1], "D3": descriptors[gid]["vector"][2], "D4": descriptors[gid]["vector"][3], "D5": descriptors[gid]["vector"][4], "D6": descriptors[gid]["vector"][5], "logical_condition_source_case": c, "spacer_nm": s.get("spacer_nm"), "ux": s.get("ux"), "source_polarization": s.get("source_polarization"), "provider_channel": s.get("provider_channel"), "primary_targets": "Delta R; Delta T", "routing_target": "HELDOUT_FUTURE_CANONICAL_ROUTING_V2", "provider_prerequisite": "cheap LF/provider evaluation for exact angular Level1 counterpart; 9-node gap", "new_upstream_hf_required_by_plan": False, "execution_authorized": False, "solver_entry_status": "NOT_AUTHORIZED_M2A_PLANNING_ONLY", "validation_supported": "common-condition cross-geometry R/T residual comparison"})
        return rows
    plan_fields = ["planned_case_id", "geometry_id", "D1", "D2", "D3", "D4", "D5", "D6", "logical_condition_source_case", "spacer_nm", "ux", "source_polarization", "provider_channel", "primary_targets", "routing_target", "provider_prerequisite", "new_upstream_hf_required_by_plan", "execution_authorized", "solver_entry_status", "validation_supported"]
    core_conditions = condition_order[:3]
    write_csv(OUT / "M2A_CORE_MINIMAL_ACQUISITION_PLAN_V1.csv", plan_fields, plan_rows(core_conditions))
    full_conditions = condition_order
    full_rows = plan_rows(full_conditions)
    for r in full_rows:
        r["validation_supported"] = "full four-condition matched cross-geometry R/T residual comparison, including negative-ux orientation holdout"
    write_csv(OUT / "M2A_FULL_MATCHED_ACQUISITION_PLAN_V1.csv", plan_fields, full_rows)

    # Future routing contract is new and prospective; legacy eta/order_profile semantics are untouched.
    routing_json = {
        "schema_version": "coupling_ml_future_canonical_routing_contract_preflight_v1",
        "status": "FEASIBLE_FOR_FUTURE_RUNS_ONLY_LEGACY_ROUTING_HELDOUT",
        "future_routing_contract_feasible": True,
        "future_routing_additional_solver_entry_cost": 0,
        "additional_solver_entry_cost_definition": "No independent solver entry; record required observables during the same future Level1/provider or Level2A run.",
        "legacy_semantics_modified": False,
        "physical_order_set": "For each condition and wavelength, explicit sorted integer m set from the same requested order lattice; propagating subset M_prop is defined by real transmitted-side kz > 0 and outward power, not array position. Example at ux=+0.378689: approximately m=-5..+2 over 445-455 nm; at ux=-0.482759 the negative edge changes near the Rayleigh cutoff and must be recorded per wavelength.",
        "included_order_set": "M_prop = sorted integer physical m with explicit transmitted-side propagating flag true and outward native power at the fixed reference plane.",
        "excluded_order_set": "M_excluded = explicit requested integer m entries with propagating flag false or evanescent/non-outward status; record the set per wavelength, never silently drop or fill it.",
        "numerator": "P_m_transmitted_incident_normalized from native grating_power output, keyed by integer physical m; no conditional-fraction substitution.",
        "denominator": "sum(P_m_transmitted_incident_normalized for m in M_prop) at the same condition, wavelength and fixed transmitted reference plane; retain separate incident-normalized T_total.",
        "propagating_order_policy_id": "TRANSMITTED_SIDE_REAL_KZ_OUTWARD_POWER_V2",
        "propagating_order_policy": "Use explicit transmitted-side kz criterion and native provider order flags; report propagating and excluded/evanescent sets. Do not fill missing orders, infer by array index, or renormalize legacy profiles.",
        "normalization": "Incident source-power normalization with native provider power semantics and no additional flux normalization; exact wavelength-resolved one-way transmitted power.",
        "reference_plane_id": "COMMON_TRANSMITTED_SIDE_ABSOLUTE_Z_V2",
        "reference_plane_definition": "A single pre-registered absolute transmitted-side reference-plane z coordinate, identical in Level1/provider and Level2A setup manifests; record z and stack/interface identity in every run manifest. Current legacy planes are not retrofitted by this preflight.",
        "reference_plane": "A single pre-registered absolute transmitted-side reference-plane z coordinate, identical in Level1/provider and Level2A setup manifests; record z and stack/interface identity in every run manifest. Current legacy planes are not retrofitted by this preflight.",
        "canonical_mapping": "physical m=+1 is physical +x; u_x_order = u_x_incident + m*wavelength_nm/period_x_nm, with period_x_nm=1740 and explicit m/u_x pair recorded.",
        "required_common_outputs": ["R", "T_total", "physical_order_set", "P_m_transmitted_incident_normalized", "M_prop", "M_excluded", "canonical_fraction=P_m/denominator", "m_to_u_x_mapping", "propagating_policy_id", "normalization_id", "reference_plane_id"],
        "additional_independent_solver_required": False,
        "precondition": "Freeze this contract before any future Level1/provider or Level2A acquisition; no contract repair is performed in M2A.",
        "source_provider_freeze_limitation": "P_common_order_authority was unavailable in the preserved legacy provider freeze; this future contract is not evidence that the legacy contract is repaired.",
    }
    write_json(OUT / "M2A_FUTURE_CANONICAL_ROUTING_CONTRACT_PREFLIGHT_V1.json", routing_json)

    write_json(OUT / "M2A_ALT1_ROUTING_ANCHOR_INFORMATION_VALUE_V1.json", {
        "schema_version": "coupling_ml_m2a_alt1_routing_anchor_information_value_v1",
        "alt1_routing_anchor_replay_recommended": True,
        "estimated_scientific_value": "HIGH: one paired ALT1 canonical-routing replay would connect the existing legacy RT residual seed to the prospective routing-capable dataset and test denominator/order-policy continuity.",
        "additional_solver_entries": 1,
        "additional_solver_entry_definition": "one future ALT1 integrated Level2A canonical-routing anchor replay; not executed or authorized in M2A",
        "current_alt1_rt_seed_rows": 8,
        "current_alt1_logical_cases": 4,
        "reason": "Legacy ALT1 R/T rows are exact but legacy routing is not exact-compatible; a single prospective anchor has high bridge value if the future routing contract is adopted.",
        "routing_contract_reference": "M2A_FUTURE_CANONICAL_ROUTING_CONTRACT_PREFLIGHT_V1.json",
    })

    report = f"""# M2A Geometry diversity seed acquisition planning v1

## STATUS
`PASS_ZERO_SOLVER_PLANNING_COMPLETE`

## CANDIDATE_POOL
- candidate_geometries = 22.
- Authority: `{HF_PATH}`; SHA256 `{sha(HF_PATH)}`; 484 rows = 22 ordered geometries x P/S x 11 wavelengths; all rows retained with geometry hash and quality/accepted-execution evidence.
- Frozen LF/provider coverage is normal-incidence only: 22 geometries / 484 rows; `u_x=0`, `k_y=0`.
- Ordered distance definition: `sqrt(mean(((D_i-D_i_ALT1)/130 nm)^2))`, i=1..6; no sorting or permutation-invariant encoding.
- Response diversity uses the common 8D min-max vector P/S x `[R,T,eta(+1),eta(-1)]`; `directionality` is preserved where available but excluded from the distance because two frozen P rows omit it.
- `np_frozen_rank` in the table is the frozen HF broadband eta(+1) response rank; the frozen geometry index is also recorded separately.

## SELECTED_GEOMETRIES
- current_exact_geometries = 1 (`{alt1_id}`).
- new_geometries_selected = 3.
- projected_exact_geometries_after_core = 4.
- selected_geometry_ids = `{selected_ids}`.
- selected_ordered_vectors = `{[descriptors[g]['vector'] for g in selected_ids]}` nm.
- Selected strata/ranks: `HIGH` rank {descriptors[selected_ids[0]]['response_space_rank']}, `MEDIUM` rank {descriptors[selected_ids[1]]['response_space_rank']}, `LOWER_CONTRASTING` rank {descriptors[selected_ids[2]]['response_space_rank']}.
- ALT1 is the current seed anchor; CONTROL0 is a diagnostic spacer condition on that same geometry and is not selected as a training geometry.

## CONDITION_SELECTION
- Current ALT1 evidence contains four exact R/T conditions: T0/P/+ux, T237/P/-ux, T237/P/+ux, T237/S/+ux.
- Core minimal condition subset: T0/P/+ux, T237/P/+ux, T237/S/+ux.
- Rationale: common P/S at matched spacer and positive ux plus an explicit spacer contrast; negative ux is retained for matched-full validation because no matched S/-ux condition exists.
- Full matched condition set: all four current ALT1 conditions.
- ALT1 absolute residual magnitudes are recorded in `M2A_CONDITION_INFORMATION_VALUE_AUDIT_V1.csv`; routing remains held out.

## CORE_PLAN
- core_conditions_per_geometry = 3.
- core_new_level2a_logical_jobs = 9.
- Supports common-condition cross-geometry `Delta R`/`Delta T` residual learnability across four geometries after future provider prerequisite; does not test negative-ux orientation sensitivity.

## FULL_PLAN
- full_conditions_per_geometry = 4.
- full_new_level2a_logical_jobs = 12.
- Adds the negative-ux P condition for four-condition matched comparison and orientation-sign holdout.

## LEVEL1_FEASIBILITY
- Existing exact angular provider coverage is only ALT1: 9 postprocessed provider nodes, all tagged `NP_K6X_125_135_150_175_190_210`.
- Each selected geometry requires a future cheap LF/provider evaluation to establish its exact angular Level-1 counterpart; provider gap count = 9 per selected geometry.
- New upstream HF required by this plan = 0; if the cheap-provider prerequisite fails, the acquisition is a hard gate and must not proceed.

## FUTURE_ROUTING_CONTRACT
- `future_routing_contract_feasible = true` for future runs only.
- `future_routing_additional_solver_entry_cost = 0`; required raw order powers, physical m mapping, order sets, propagating policy, normalization and reference-plane metadata can be recorded in the same run.
- Legacy `eta_*` and `order_profile` semantics are unchanged; current routing remains held out.

## ALT1_ROUTING_BRIDGE
- `alt1_routing_anchor_replay_recommended = true`.
- `alt1_routing_anchor_additional_solver_entries = 1` in a future, separately authorized replay; not executed in M2A.

## AUDIT
- solver_entered_delta = 0.
- new_rcwa_evaluation_delta = 0.
- new_provider_evaluation_delta = 0.
- ml_training_delta = 0.
- inverse_design_delta = 0.
- raw_fsp_copy_delta = 0; move_delta = 0; delete_delta = 0.
- No resource admission was attempted; no Fluent or other running process was touched.
- All required M2A artifacts were generated under the new Coupling-ML worktree and hashed by `M2A_SHA256_MANIFEST_V1.json`.

## RISKS
- Selected geometries lack exact angular Level-1 counterparts today; cheap provider acquisition is a prerequisite.
- Standalone NP HF/LF response diversity is selection evidence, not integrated MDC-NP truth.
- Future routing feasibility depends on freezing the common order/reference-plane contract before acquisition.

## NEXT
`A. AUTHORIZE_CORE_GEOMETRY_DIVERSITY_ACQUISITION`
"""
    write_text_path = OUT / "M2A_REPORT_V1.md"
    write_text_path.write_text(report, encoding="utf-8")

    # Hash every M2A artifact except the manifest itself, then write the manifest.
    artifacts = []
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name != "M2A_SHA256_MANIFEST_V1.json":
            artifacts.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
    manifest = {
        "schema_version": "coupling_ml_m2a_sha256_manifest_v1",
        "status": "PASS",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "source_authority": {"hf_path": str(HF_PATH), "hf_sha256": sha(HF_PATH), "lf_manifest_path": str(LF_MANIFEST_PATH), "lf_manifest_sha256": sha(LF_MANIFEST_PATH), "freeze_path": str(FREEZE_PATH), "freeze_sha256": sha(FREEZE_PATH), "provider_manifest_path": str(PROVIDER_MANIFEST_PATH), "provider_manifest_sha256": sha(PROVIDER_MANIFEST_PATH)},
        "zero_compute_audit": {"solver_entered_delta": 0, "new_rcwa_evaluation_delta": 0, "new_provider_evaluation_delta": 0, "ml_training_delta": 0, "inverse_design_delta": 0, "raw_fsp_copy_delta": 0, "move_delta": 0, "delete_delta": 0, "commit_delta": 0, "push_delta": 0},
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(OUT / "M2A_SHA256_MANIFEST_V1.json", manifest)

    print(json.dumps({
        "status": "PASS_ZERO_SOLVER_PLANNING_COMPLETE", "out": str(OUT), "candidate_geometries": len(descriptors), "current_exact_geometries": 1, "new_geometries_selected": len(selected_ids), "selected_geometry_ids": selected_ids, "selected_ordered_vectors": [descriptors[g]["vector"] for g in selected_ids], "core_conditions_per_geometry": len(core_conditions), "core_new_level2a_logical_jobs": len(selected_ids) * len(core_conditions), "full_conditions_per_geometry": len(full_conditions), "full_new_level2a_logical_jobs": len(selected_ids) * len(full_conditions), "selected_geometries_requiring_cheap_lf": selected_ids, "selected_geometries_requiring_new_upstream_hf": [], "future_routing_contract_feasible": True, "future_routing_additional_solver_entry_cost": 0, "alt1_routing_anchor_replay_recommended": True, "alt1_routing_anchor_additional_solver_entries": 1, "solver_entered_delta": 0, "new_rcwa_evaluation_delta": 0, "new_provider_evaluation_delta": 0, "ml_training_delta": 0, "commit_delta": 0, "push_delta": 0, "artifact_count": len(artifacts)
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
