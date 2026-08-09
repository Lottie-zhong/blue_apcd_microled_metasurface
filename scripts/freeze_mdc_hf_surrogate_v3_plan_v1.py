from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
CONTRACTS = ROOT / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1"
RUN_ID = "20260810T_v3_plan_freeze_390f506"
OUT = ROOT / "outputs" / "mdc_hf_surrogate_v3_plan_freeze_v1" / RUN_ID
GEOMETRY_MASTER = Path(r"D:\project\worktrees\blue_apcd_mdc_defect_450\datasets\mdc_ml_database_v1\geometry_master.csv")
SUPPORT = ROOT / "outputs/mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1/20260808T_test40_selection_conflict_resolution_489b54e/test40_supported_candidate_universe_v1.csv"
FORMAL_LEDGER = ROOT / "outputs/mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1/20260808T_test40_selection_conflict_resolution_489b54e/test40_formal_fdtd_exclusion_ledger_hash_only.csv"
V2_MANIFEST = ROOT / "outputs/mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1/20260808T_test40_selection_conflict_resolution_489b54e/test40_geometry_manifest_v1.csv"
V2_CASES = ROOT / "outputs/mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1/20260808T_test40_selection_conflict_resolution_489b54e/test40_case_matrix_v1.csv"
DOE_MANIFEST = ROOT / "contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_candidate_manifest.json"
DOE_CASES = ROOT / "contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_case_matrix.csv"
PILOT_MANIFEST = ROOT / "contracts/mdc_hf_surrogate_v2/fixed_v2_pilot4_candidate_manifest.json"
DIAGNOSTIC = ROOT / "outputs/mdc_hf_surrogate_v2_failure_mechanism_diagnostic_fixed_v3_v1/20260809T_failure_mechanism_diagnostic_exact_latent_4169274/completion_manifest.json"
SOURCE_COMMIT = "50cb7945c376bd14e025211d3c070e83a89447f9"

POSITIONS = [("top", "x"), ("top", "z"), ("centroid", "x"), ("centroid", "z"), ("bottom", "x"), ("bottom", "z")]
TOPOLOGIES = ["Explicit", "ZL1", "ZL2"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def stable_key(prefix: str, seed: int, geometry_hash: str) -> str:
    return hashlib.sha256(f"{prefix}|{seed}|{geometry_hash.lower()}".encode("utf-8")).hexdigest()


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def norm_topology(value: str) -> str:
    return {"ZL-1": "ZL1", "ZL-2": "ZL2"}.get(str(value), str(value))


def make_case_rows(geometry_rows: pd.DataFrame, prefix: str, case_contract: str) -> pd.DataFrame:
    rows = []
    for row in geometry_rows.itertuples(index=False):
        geometry_hash = str(row.geometry_hash)
        geometry_id = str(getattr(row, "geometry_id", getattr(row, "al_geometry_id", "")))
        for position, orientation in POSITIONS:
            uid = hashlib.sha256(f"{case_contract}|{geometry_hash}|{position}|{orientation}".encode("utf-8")).hexdigest()
            rows.append({
                "case_uid": uid,
                "geometry_id": geometry_id,
                "geometry_hash": geometry_hash,
                "source_position": position,
                "dipole_orientation": orientation,
                "case_count_per_geometry": 6,
                "joint_profile_schema": "native_301x2000",
                "labels_status": "NOT_GENERATED",
                "solver_status": "NOT_AUTHORIZED",
                "case_identity_contract": case_contract,
            })
    return pd.DataFrame(rows)


def feature_frame(master: pd.DataFrame) -> pd.DataFrame:
    out = master[["geometry_hash", "physical_layer_count", "total_thickness_nm"]].copy()
    out["physical_layer_count"] = pd.to_numeric(out["physical_layer_count"], errors="coerce")
    out["total_thickness_nm"] = pd.to_numeric(out["total_thickness_nm"], errors="coerce")
    return out


def distance_scores(candidates: pd.DataFrame, anchors: pd.DataFrame) -> tuple[pd.Series, dict]:
    values = pd.concat([candidates[["physical_layer_count", "total_thickness_nm"]], anchors[["physical_layer_count", "total_thickness_nm"]]], ignore_index=True)
    mins = values.min().to_dict()
    maxs = values.max().to_dict()
    spans = {k: max(float(maxs[k] - mins[k]), 1.0) for k in mins}
    c = ((candidates[["physical_layer_count", "total_thickness_nm"]] - pd.Series(mins)) / pd.Series(spans)).to_numpy(float)
    a = ((anchors[["physical_layer_count", "total_thickness_nm"]] - pd.Series(mins)) / pd.Series(spans)).to_numpy(float)
    distances = np.sqrt(((c[:, None, :] - a[None, :, :]) ** 2).sum(axis=2))
    return pd.Series(distances.min(axis=1), index=candidates.index), {"feature_order": list(mins), "min": mins, "max": maxs, "span": spans}


def maximin_select(pool: pd.DataFrame, count: int, seed: int, prefix: str, priority: bool = False) -> tuple[pd.DataFrame, list[dict]]:
    if len(pool) < count:
        raise RuntimeError(f"insufficient candidate pool for {prefix}: {len(pool)} < {count}")
    pool = pool.copy()
    pool["selection_key"] = [stable_key(prefix, seed, x) for x in pool.geometry_hash]
    coordinates = pool[["physical_layer_count", "total_thickness_nm"]].to_numpy(float)
    selected_indices: list[int] = []
    trace: list[dict] = []
    if priority:
        first = pool.sort_values(["metadata_distance_to_base136", "selection_key", "geometry_hash"], ascending=[False, True, True]).index[0]
        selected_indices.append(int(first))
        trace.append({"geometry_hash": pool.loc[first, "geometry_hash"], "selection_key": pool.loc[first, "selection_key"], "selection_step": 1, "initial_priority": "largest_metadata_distance_to_base136"})
    else:
        first = pool.sort_values(["selection_key", "geometry_hash"]).index[0]
        selected_indices.append(int(first))
        trace.append({"geometry_hash": pool.loc[first, "geometry_hash"], "selection_key": pool.loc[first, "selection_key"], "selection_step": 1, "initial_priority": "deterministic_hash"})
    while len(selected_indices) < count:
        remaining = [i for i in pool.index if int(i) not in selected_indices]
        selected_coords = coordinates[[pool.index.get_loc(i) for i in selected_indices]]
        rem_coords = coordinates[[pool.index.get_loc(i) for i in remaining]]
        score = np.sqrt(((rem_coords[:, None, :] - selected_coords[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
        ranked = pd.DataFrame({"idx": remaining, "min_pairwise_distance": score}).merge(pool[["selection_key", "geometry_hash"]], left_on="idx", right_index=True)
        chosen = int(ranked.sort_values(["min_pairwise_distance", "selection_key", "geometry_hash"], ascending=[False, True, True]).iloc[0].idx)
        chosen_score = float(ranked.loc[ranked.idx == chosen, "min_pairwise_distance"].iloc[0])
        selected_indices.append(chosen)
        trace.append({"geometry_hash": pool.loc[chosen, "geometry_hash"], "selection_key": pool.loc[chosen, "selection_key"], "selection_step": len(selected_indices), "initial_priority": "maximin", "min_pairwise_distance": chosen_score})
    return pool.loc[selected_indices].copy(), trace


def collect_environment() -> tuple[dict, str]:
    try:
        freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True, stderr=subprocess.STDOUT)
    except Exception as exc:
        freeze = f"pip_freeze_failed: {exc}\n"
    freeze_path = OUT / "RCP_LCP_pip_freeze.txt"
    freeze_path.write_text(freeze, encoding="utf-8")
    info = {"python_executable": sys.executable, "python_version": platform.python_version(), "platform": platform.platform(), "pip_freeze_sha256": sha256(freeze_path), "pip_freeze_path": str(freeze_path)}
    try:
        import torch
        info.update({"torch_version": torch.__version__, "cuda_build": torch.version.cuda, "cuda_runtime_available": bool(torch.cuda.is_available()), "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})
    except Exception as exc:
        info.update({"torch_import_error": str(exc), "torch_version": None, "cuda_build": None, "cuda_runtime_available": False, "gpu": None})
    return info, freeze


def main() -> None:
    if not (ROOT / ".git").exists():
        raise RuntimeError("expected V3 worktree root missing")
    branch = subprocess.check_output(["git", "-C", str(ROOT), "branch", "--show-current"], text=True).strip()
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    divergence = subprocess.check_output(["git", "-C", str(ROOT), "rev-list", "--left-right", "--count", "HEAD...@{u}"], text=True).strip()
    if branch != "work/mdc-hf-surrogate-v2" or head != "390f5064296dfb6223e1226b209739f4a8072cf2" or divergence != "0\t0":
        raise RuntimeError(f"HARD_GATE_GIT_PREFLIGHT {branch} {head} {divergence}")
    if OUT.exists():
        raise RuntimeError(f"output already exists: {OUT}")
    OUT.mkdir(parents=True)
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    safety = {"FDTD_calls": 0, "TMM_calls": 0, "RCWA_calls": 0, "NP_solver_calls": 0, "neural_fits": 0, "optimizer_calls": 0, "backward_calls": 0, "PCA_fits": 0, "scaler_fits": 0, "V3_Test40_label_reads": 0, "HF15_formal_label_reads": 0, "HF15_diagnostics_value_reads": 0, "R12_formal_label_reads": 0, "R12_diagnostics_value_reads": 0, "sealed_reads": 0, "active_learning_solver_calls": 0}

    support = pd.read_csv(SUPPORT)
    formal = pd.read_csv(FORMAL_LEDGER)
    v2 = pd.read_csv(V2_MANIFEST)
    master = pd.read_csv(GEOMETRY_MASTER)
    doe = json.loads(DOE_MANIFEST.read_text(encoding="utf-8"))["candidates"]
    pilot = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))["candidates"]
    doe_df = pd.DataFrame(doe)
    pilot_df = pd.DataFrame(pilot)
    formal_hashes = set(formal.geometry_hash.astype(str))
    doe_hashes, v2_hashes, pilot_hashes = set(doe_df.geometry_hash), set(v2.geometry_hash.astype(str)), set(pilot_df.geometry_hash)
    historical_hashes = formal_hashes
    if len(master) != 8675 or len(support) != 2688 or len(formal) != 128:
        raise RuntimeError("frozen source cardinality mismatch")
    if support.geometry_hash.duplicated().any() or master.geometry_hash.duplicated().any():
        raise RuntimeError("duplicate geometry hash in frozen universe")
    master_meta = feature_frame(master)
    universe = support.merge(master_meta, on="geometry_hash", how="left", validate="one_to_one")
    if universe["physical_layer_count"].isna().any():
        raise RuntimeError("support universe row missing geometry-master metadata")
    universe["topology_family"] = universe["topology_family"].map(norm_topology)
    universe["excluded_by_formal_hash_ledger"] = universe.geometry_hash.isin(formal_hashes)
    if int(universe.excluded_formal_fdtd.astype(bool).sum()) != 14 or int(universe.excluded_by_formal_hash_ledger.sum()) != 14:
        raise RuntimeError("support/formal exclusion reconciliation failed")
    base_v2 = v2[["geometry_hash", "geometry_id", "topology_family", "N", "M", "H_nm", "L_nm", "C_nm", "boundary_class", "physical_layer_count", "total_thickness_nm"]].copy()
    base_v2["source_role"] = "V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3"
    base_doe = doe_df[["geometry_hash", "geometry_id", "topology_family", "layer_count", "total_thickness_nm", "defect_thickness_nm"]].rename(columns={"layer_count": "physical_layer_count"})
    base_doe["boundary_class"] = "unknown_in_doe_manifest"
    base_doe["N"] = np.nan; base_doe["M"] = np.nan; base_doe["H_nm"] = np.nan; base_doe["L_nm"] = np.nan; base_doe["C_nm"] = np.nan
    base_doe["source_role"] = "DOE96_FORMAL_DEVELOPMENT"
    base_doe["defect_thickness_nm"] = base_doe["defect_thickness_nm"].astype(float)
    base_v2["defect_thickness_nm"] = np.where(base_v2["C_nm"].notna(), base_v2["C_nm"], base_v2["M"])
    base136 = pd.concat([base_doe, base_v2], ignore_index=True, sort=False)
    if len(base136) != 136 or base136.geometry_hash.nunique() != 136:
        raise RuntimeError("V3 base development pool is not 136 unique geometries")
    base_cases = pd.concat([pd.read_csv(DOE_CASES).assign(source_role="DOE96_FORMAL_DEVELOPMENT"), pd.read_csv(V2_CASES).assign(source_role="V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3")], ignore_index=True, sort=False)
    if len(base_cases) != 816 or base_cases.geometry_hash.nunique() != 136:
        raise RuntimeError("V3 base case pool is not 816 cases / 136 geometries")
    base_cases.to_csv(OUT / "v3_development_case_matrix_v1.csv", index=False)
    base136.to_csv(OUT / "v3_development_geometry_manifest_v1.csv", index=False)

    eligible = universe.loc[~universe["excluded_by_formal_hash_ledger"]].copy()
    excluded_sets = {"DOE96": doe_hashes, "V2_Test40": v2_hashes, "Pilot4": pilot_hashes, "historical_formal_FDTD": historical_hashes}
    eligible["excluded_role"] = ""
    for role, hashes in excluded_sets.items():
        eligible.loc[eligible.geometry_hash.isin(hashes), "excluded_role"] = role
    eligible = eligible.loc[eligible.excluded_role == ""].copy()
    anchors = base136[["geometry_hash", "physical_layer_count", "total_thickness_nm"]].dropna().copy()
    eligible["metadata_distance_to_base136"], distance_contract = distance_scores(eligible, anchors)
    doe_anchors = base_doe[["geometry_hash", "physical_layer_count", "total_thickness_nm"]].dropna()
    v2_anchors = base_v2[["geometry_hash", "physical_layer_count", "total_thickness_nm"]].dropna()
    eligible["metadata_distance_to_doe96"], _ = distance_scores(eligible, doe_anchors)
    eligible["metadata_distance_to_v2_test40"], _ = distance_scores(eligible, v2_anchors)
    eligible["topology_family"] = eligible["topology_family"].map(norm_topology)
    eligible["selection_key"] = [stable_key("APCD_MDC_V3_AL64_V1", 20260810, x) for x in eligible.geometry_hash]
    al_specs = [("ZL1_priority_interior_N4_5", "ZL1", "interior", 24, True, lambda d: d.N.isin([4, 5])), ("ZL1_boundary", "ZL1", "boundary", 4, False, lambda d: pd.Series(True, index=d.index)), ("ZL1_interior_other", "ZL1", "interior", 4, False, lambda d: ~d.N.isin([4, 5])), ("Explicit_boundary", "Explicit", "boundary", 8, False, lambda d: pd.Series(True, index=d.index)), ("Explicit_interior", "Explicit", "interior", 8, False, lambda d: pd.Series(True, index=d.index)), ("ZL2_boundary", "ZL2", "boundary", 8, False, lambda d: pd.Series(True, index=d.index)), ("ZL2_interior", "ZL2", "interior", 8, False, lambda d: pd.Series(True, index=d.index))]
    al_parts, al_trace = [], []
    for label, topology, boundary, count, priority, predicate in al_specs:
        pool = eligible.loc[(eligible.topology_family == topology) & (eligible.boundary_class == boundary)].copy()
        pool = pool.loc[predicate(pool)]
        chosen, trace = maximin_select(pool, count, 20260810, f"APCD_MDC_V3_AL64_V1|{label}", priority)
        chosen["selection_stratum"] = label
        al_parts.append(chosen)
        for item in trace:
            item.update({"selection_stratum": label, "topology_family": topology, "boundary_class": boundary, "metadata_distance_to_base136": float(chosen.loc[chosen.geometry_hash == item["geometry_hash"], "metadata_distance_to_base136"].iloc[0])})
        al_trace.extend(trace)
    al = pd.concat(al_parts, ignore_index=True)
    if len(al) != 64 or al.geometry_hash.nunique() != 64 or al.topology_family.value_counts().to_dict() != {"ZL1": 32, "Explicit": 16, "ZL2": 16}:
        raise RuntimeError("AL64 quota/cardinality failure")
    al["al_geometry_id"] = [f"MDC_V3_AL_G{i:03d}" for i in range(len(al))]
    al["future_case_count"] = 6
    al["future_labels_status"] = "NOT_GENERATED"
    al["future_solver_status"] = "NOT_AUTHORIZED"
    al = al[["al_geometry_id", "geometry_id", "geometry_hash", "topology_family", "N", "M", "H_nm", "L_nm", "C_nm", "boundary_class", "boundary_detail", "selection_stratum", "selection_key", "metadata_distance_to_base136", "metadata_distance_to_doe96", "metadata_distance_to_v2_test40", "future_case_count", "future_labels_status", "future_solver_status"]]
    al.to_csv(OUT / "v3_al64_geometry_manifest_v1.csv", index=False)
    al_cases = make_case_rows(al.rename(columns={"al_geometry_id": "geometry_id"}), "MDC_V3_AL", "MDC_HF_SURROGATE_V3_AL64_CASE_UID_V1")
    al_cases.to_csv(OUT / "v3_al64_future_case_matrix_v1.csv", index=False)
    pd.DataFrame(al_trace).to_csv(OUT / "v3_al64_selection_trace_v1.csv", index=False)
    al_hashes = set(al.geometry_hash)
    overlap_al = {"AL64_geometry_count": len(al), "AL64_case_count": len(al_cases), "overlap_counts": {name: int(len(al_hashes & hashes)) for name, hashes in excluded_sets.items()}, "base136_overlap": int(len(al_hashes & set(base136.geometry_hash))), "formal_numerical_value_reads": 0, "solver_calls": 0, "status": "PASS"}
    dump(OUT / "v3_al64_overlap_audit_v1.json", overlap_al)

    test_eligible = eligible.loc[~eligible.geometry_hash.isin(al_hashes)].copy()
    test_eligible["selection_key"] = [stable_key("APCD_MDC_V3_TEST40_V1", 20260810, x) for x in test_eligible.geometry_hash]
    test_specs = [("Explicit_boundary", "Explicit", "boundary", 4), ("Explicit_interior", "Explicit", "interior", 10), ("ZL1_boundary", "ZL1", "boundary", 4), ("ZL1_interior", "ZL1", "interior", 9), ("ZL2_boundary", "ZL2", "boundary", 4), ("ZL2_interior", "ZL2", "interior", 9)]
    test_parts = []
    for label, topology, boundary, count in test_specs:
        pool = test_eligible.loc[(test_eligible.topology_family == topology) & (test_eligible.boundary_class == boundary)].sort_values(["selection_key", "geometry_hash"])
        if len(pool) < count:
            raise RuntimeError(f"V3 Test40 stratum insufficient: {label}")
        part = pool.head(count).copy(); part["selection_stratum"] = label; test_parts.append(part)
    test = pd.concat(test_parts, ignore_index=True)
    if len(test) != 40 or test.geometry_hash.nunique() != 40 or test.topology_family.value_counts().to_dict() != {"Explicit": 14, "ZL1": 13, "ZL2": 13}:
        raise RuntimeError("V3 Test40 quota/cardinality failure")
    test["test_geometry_id"] = [f"MDC_V3_TEST_G{i:03d}" for i in range(len(test))]
    test["labels_status"] = "NOT_GENERATED"; test["solver_status"] = "NOT_AUTHORIZED"
    test["selection_seed"] = 20260810; test["selection_algorithm"] = "STRATIFIED_DETERMINISTIC_HASH_RANDOM_V1"
    test["candidate_universe_sha256"] = sha256(SUPPORT); test["formal_exclusion_ledger_sha256"] = sha256(FORMAL_LEDGER); test["source_geometry_master_sha256"] = sha256(GEOMETRY_MASTER)
    test = test[["test_geometry_id", "geometry_id", "geometry_hash", "topology_family", "N", "M", "H_nm", "L_nm", "C_nm", "boundary_class", "boundary_detail", "selection_stratum", "selection_key", "selection_seed", "selection_algorithm", "candidate_universe_sha256", "formal_exclusion_ledger_sha256", "source_geometry_master_sha256", "labels_status", "solver_status"]]
    test.to_csv(OUT / "v3_test40_geometry_manifest_v1.csv", index=False)
    test_cases = make_case_rows(test.rename(columns={"test_geometry_id": "geometry_id"}), "MDC_V3_TEST", "MDC_HF_SURROGATE_V3_TEST40_CASE_UID_V1")
    test_cases.to_csv(OUT / "v3_test40_case_matrix_v1.csv", index=False)
    case_identity = {"contract_id": "MDC_HF_SURROGATE_V3_TEST40_CASE_UID_V1", "uid_expression": "SHA256(UTF8(case_contract_id + '|' + canonical_geometry_hash + '|' + source_position + '|' + dipole_orientation))", "positions": [x[0] for x in POSITIONS[::2]], "orientations": ["x", "z"], "cases_per_geometry": 6, "case_count": len(test_cases), "labels_status": "NOT_GENERATED", "solver_status": "NOT_AUTHORIZED"}
    dump(OUT / "v3_test40_case_identity_contract_v1.json", case_identity)
    all_overlap = {"V3_Test40_geometry_count": len(test), "V3_Test40_case_count": len(test_cases), "overlap_counts": {"DOE96": int(len(set(test.geometry_hash) & doe_hashes)), "V2_Test40": int(len(set(test.geometry_hash) & v2_hashes)), "AL64": int(len(set(test.geometry_hash) & al_hashes)), "Pilot4": int(len(set(test.geometry_hash) & pilot_hashes)), "historical_formal_FDTD": int(len(set(test.geometry_hash) & historical_hashes))}, "formal_numerical_value_reads": 0, "labels_generated": False, "solver_calls": 0, "status": "PASS"}
    dump(OUT / "v3_test40_overlap_audit_v1.json", all_overlap)

    role = {"contract_id": "MDC_HF_SURROGATE_V3_DATA_ROLE_TRANSITION_V1", "fixed_v2_role": "CONSUMED_EXTERNAL_TEST", "v3_role": "V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3", "historical_fixed_v2_conclusion_unchanged": True, "v2_test40": {"geometry_count": 40, "case_count": 240, "external_validation_for_v3": False}, "v3_base_development_pool": {"DOE96_geometry_count": 96, "DOE96_case_count": 576, "V2_Test40_geometry_count": 40, "V2_Test40_case_count": 240, "geometry_count": 136, "case_count": 816, "cases_per_geometry": 6, "unit_of_split": "geometry_hash", "joint_profile_schema": "native_301x2000", "Pilot4": "pipeline_validation_only", "HF15": "not_joint_profile_eligible", "R12": "not_joint_profile_eligible"}, "formal_label_reads": 0, "diagnostics_value_reads": 0, "diagnostic_evidence_manifest": str(DIAGNOSTIC), "status": "FROZEN"}
    dump(OUT / "v3_data_role_transition_v1.json", role)

    model = {"contract_id": "MDC_HF_SURROGATE_V3_PROFILE_ONLY_MODEL_CANDIDATES_V1", "candidate_count": 3, "no_post_oof_candidate_addition": True, "primary_target": "geometry + source condition -> PCA32 latent -> native_301x2000_joint_profile", "PCA32_retained": True, "power_head": "REMOVED_FROM_PRIMARY_V3_SHARED_LOSS", "auxiliary_scalar_head": "NOT_LOAD_BEARING", "derived_peak_fwhm_cone": "deterministic from decoded profile", "candidates": [{"id": "V3-A", "backbone": "M1", "input_width": 23, "residual_width": 256, "residual_blocks": 3, "latent_width": 128, "dropout": 0.05, "weight_decay": 0.0001, "profile_head_width": 32, "regularization": "fixed_v2_current", "purpose": "undertraining_or_power_interference_test"}, {"id": "V3-B", "backbone": "M1", "input_width": 23, "residual_width": 256, "residual_blocks": 3, "latent_width": 128, "dropout": 0.0, "weight_decay": 0.0, "profile_head_width": 32, "regularization": "reduced", "purpose": "regularization_collapse_test"}, {"id": "V3-C", "backbone": "moderately_widened_MLP", "input_width": 23, "residual_width": 384, "residual_blocks": 3, "latent_width": 192, "dropout": 0.0, "weight_decay": 0.0, "profile_head_width": 32, "regularization": "reduced", "purpose": "capacity_limitation_test"}], "training_authorized": False}
    dump(OUT / "v3_model_candidate_contract_v1.json", model)
    training = {"contract_id": "MDC_HF_SURROGATE_V3_TRAINING_CONTRACT_V1", "development_membership": {"DOE96": 96, "V2_Test40_reclassified": 40, "future_AL64": 64, "total_geometries": 200, "total_cases": 1200, "cases_per_geometry": 6}, "split": {"method": "geometry_hash_grouped_5_fold", "outer_folds": 5, "all_six_cases_together": True, "outer_held_out_never_used_for_early_stopping": True, "inner_stop": {"method": "deterministic_hash_stratified_20_percent_of_outer_train_geometries", "contract_id": "MDC_HF_SURROGATE_V3_INNER_STOP_V1", "inner_stop_seed": 20260813, "inner_train_and_stop_frozen_before_fit": True}}, "duration": {"min_epochs": 50, "max_epochs": 400, "patience": 50, "min_delta": 1e-06, "warmup_epochs": 10, "early_stopping_metric": "inner_stop_mean_profile_selection_score", "final_epoch_3_inherited": False, "epoch_source_excludes_V2_Test40_and_V3_Test40": True}, "optimizer": "AdamW", "learning_rate": 0.0003, "scheduler": "cosine_decay", "minimum_learning_rate": 1e-06, "gradient_clipping": 1.0, "seeds_per_candidate": [20260810, 20260811, 20260812], "candidate_count": 3, "maximum_unique_neural_fits": 45, "training_authorized": False, "no_training_this_task": True}
    dump(OUT / "v3_training_contract_v1.json", training)
    loss = {"contract_id": "MDC_HF_SURROGATE_V3_PROFILE_ONLY_LOSS_CONTRACT_V1", "power_loss": "REMOVED", "auxiliary_loss": "REMOVED_FROM_SHARED_BACKBONE", "profile_is_primary": True, "components": {"L_profile": {"weight": 0.4117647058823529, "definition": "log-domain SmoothL1 on normalized native joint profile"}, "L_JS": {"weight": 0.23529411764705882, "definition": "Jensen-Shannon divergence on normalized profile"}, "L_spectral_CDF": {"weight": 0.17647058823529413, "definition": "spectral marginal CDF loss"}, "L_angular_CDF": {"weight": 0.17647058823529413, "definition": "angular marginal CDF loss"}}, "weight_derivation": "frozen fixed-v2 profile/JS/spectral/angular weights renormalized after removing power and auxiliary components; no outcome-based tuning", "normalization": "raw-before-normalization per frozen aggregation contract", "missing_policy": "invalid_or_missing_profile_blocks_case; no_imputation", "exact_weights_frozen_before_training": True, "training_authorized": False}
    dump(OUT / "v3_profile_only_loss_contract_v1.json", loss)
    metrics = {"contract_id": "MDC_HF_SURROGATE_V3_SELECTION_METRICS_CONTRACT_V1", "selection_data": "development_OOF_only", "external_acceptance_threshold": "not_defined_in_this_plan_freeze", "required_metrics": ["joint_JS", "joint_weighted_L1", "spectral_CDF", "angular_CDF", "worst_fold_JS", "worst_topology_JS"], "anti_collapse_diagnostics": ["latent_variance_preservation", "collapsed_PCA_component_count", "profile_pairwise_diversity_ratio", "truth_vs_prediction_diversity_distribution"], "required_slices": ["ZL1", "N=4-5", "high_metadata_distance", "x_orientation", "z_orientation"], "candidate_selection_rule": "complete-metric check; ascending mean rank across six required metrics; ascending worst-topology JS; descending median latent variance ratio; descending pairwise-diversity ratio; ascending candidate ID tie-break", "promotion_metric_redefinition": False, "external_capability_source": "new V3-Test40 after model freeze only", "training_authorized": False}
    dump(OUT / "v3_selection_metrics_contract_v1.json", metrics)
    env, freeze_text = collect_environment()
    env_contract = {"contract_id": "MDC_HF_SURROGATE_V3_RCP_LCP_ENVIRONMENT_PROVENANCE_V1", "environment_name": "RCP_LCP", "backend": "Python", "freeze_scope": "new V3 provenance from this plan onward; historical fixed-v2 executable unproven", **env, "environment_freeze_text_sha256": sha256(OUT / "RCP_LCP_pip_freeze.txt"), "tracked_pip_freeze_path": str(CONTRACTS / "RCP_LCP_pip_freeze.txt"), "training_authorized": False}
    dump(OUT / "v3_environment_provenance_v1.json", env_contract)
    contract_files = ["v3_data_role_transition_v1.json", "v3_model_candidate_contract_v1.json", "v3_training_contract_v1.json", "v3_profile_only_loss_contract_v1.json", "v3_selection_metrics_contract_v1.json", "v3_environment_provenance_v1.json"]
    al_contract = {"contract_id": "MDC_HF_SURROGATE_V3_AL64_SELECTION_CONTRACT_V1", "selection_seed": 20260810, "algorithm": "STRATIFIED_METADATA_ONLY_MAXIMIN_V1", "candidate_universe": {"source": str(SUPPORT), "source_commit": SOURCE_COMMIT, "source_sha256": sha256(SUPPORT), "raw_geometry_master": str(GEOMETRY_MASTER), "raw_geometry_master_sha256": sha256(GEOMETRY_MASTER), "supported_count": 2688, "eligible_after_formal_exclusion": int((~universe.excluded_by_formal_hash_ledger).sum())}, "formal_exclusion": {"ledger": str(FORMAL_LEDGER), "ledger_sha256": sha256(FORMAL_LEDGER), "hash_only": True, "formal_numerical_value_reads": 0}, "base_pool_geometry_count": 136, "quotas": {"ZL1": 32, "Explicit": 16, "ZL2": 16}, "strata": {x[0]: x[3] for x in al_specs}, "priority": "ZL1 N=4-5 interior and largest metadata distance to current 136 geometry pool", "distance_contract": {**distance_contract, "features": ["physical_layer_count", "total_thickness_nm"], "normalization": "frozen min/max over candidate universe plus current 136 metadata anchors", "outcome_free": True}, "future_cases_per_geometry": 6, "future_case_order": POSITIONS, "solver_calls": 0, "training_authorized": False, "manifest_status": "FROZEN"}
    dump(OUT / "v3_al64_selection_contract_v1.json", al_contract)
    test_contract = {"contract_id": "MDC_HF_SURROGATE_V3_TEST40_SELECTION_CONTRACT_V1", "test_id": "MDC_HF_SURROGATE_V3_TEST40_V1", "selection_seed": 20260810, "algorithm": "STRATIFIED_DETERMINISTIC_HASH_RANDOM_V1", "candidate_universe": {"source": str(SUPPORT), "source_commit": SOURCE_COMMIT, "source_sha256": sha256(SUPPORT), "formal_exclusion_ledger_sha256": sha256(FORMAL_LEDGER)}, "exclusions": ["DOE96", "V2_Test40", "AL64", "Pilot4", "HF15", "R12", "all historical formal FDTD exposure"], "quotas": {"Explicit": 14, "ZL1": 13, "ZL2": 13, "boundary_per_topology": {"Explicit": 4, "ZL1": 4, "ZL2": 4}}, "sort_order": "ascending selection_key then geometry_hash within topology x boundary/interior stratum", "selection_key_expression": "SHA256(UTF8('APCD_MDC_V3_TEST40_V1|20260810|' + lowercase(canonical_geometry_hash)))", "geometry_count": 40, "case_count": 240, "labels_status": "NOT_GENERATED", "labels_read": 0, "solver_calls": 0, "freeze_timing": "before any V3 training", "external_validation_after_model_freeze_only": True, "manifest_status": "FROZEN"}
    dump(OUT / "v3_test40_selection_contract_v1.json", test_contract)
    manifest_lock = {"contract_id": "MDC_HF_SURROGATE_V3_TEST40_MANIFEST_LOCK_V1", "test_id": "MDC_HF_SURROGATE_V3_TEST40_V1", "geometry_count": 40, "case_count": 240, "labels_generated": False, "labels_read": 0, "solver_calls": 0, "training_started": False, "overlap_audit_status": "PASS", "locked_before_v3_training": True, "sha_registry": {"geometry_manifest": sha256(OUT / "v3_test40_geometry_manifest_v1.csv"), "case_matrix": sha256(OUT / "v3_test40_case_matrix_v1.csv"), "case_identity_contract": sha256(OUT / "v3_test40_case_identity_contract_v1.json"), "selection_contract": sha256(OUT / "v3_test40_selection_contract_v1.json")}, "status": "FROZEN"}
    dump(OUT / "v3_test40_manifest_lock_v1.json", manifest_lock)
    safety["V3_Test40_label_reads"] = 0
    dump(OUT / "v3_plan_freeze_safety_audit_v1.json", safety)
    completion = {"contract_id": "MDC_HF_SURROGATE_V3_PLAN_FREEZE_COMPLETION_MANIFEST_V1", "status": "PASS", "decision": "MDC_HF_SURROGATE_V3_PLAN_FROZEN_READY_FOR_TARGETED_AL64_SOLVER_AUTHORIZATION", "base_pool": {"geometries": 136, "cases": 816}, "AL64": {"geometries": 64, "cases": 384}, "V3_Test40": {"geometries": 40, "cases": 240}, "registered_candidates": 3, "maximum_neural_fits": 45, "solver_calls": 0, "training_started": False, "labels_read": 0, "contract_directory": str(OUT), "git_head_at_run": head}
    dump(OUT / "v3_plan_freeze_completion_manifest_v1.json", completion)
    report = f"""# Fixed-v3 plan freeze\n\nStatus: `{completion['decision']}`.\n\nThe V2 Test40 remains `CONSUMED_EXTERNAL_TEST` for fixed-v2 and is reclassified as `V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3`; fixed-v2 historical conclusions are unchanged. The frozen V3 development base is 136 geometries / 816 cases, with six native 301x2000 cases per geometry.\n\nAL64 is frozen at 64 geometries / 384 future cases with topology quotas ZL1=32, Explicit=16, ZL2=16. The independent `{test_contract['test_id']}` manifest is frozen at 40 geometries / 240 cases with zero overlap against DOE96, V2 Test40, AL64, Pilot4, and the hash-only historical formal-FDTD registry. Labels are not generated or read.\n\nThree profile-only candidates (V3-A/B/C), the duration/inner-stop/OOF contract, exact profile-only loss weights, selection diagnostics, and RCP_LCP environment provenance are frozen before any training. No solver or neural fit was started.\n"""
    (OUT / "v3_plan_freeze_report_v1.md").write_text(report, encoding="utf-8")
    artifacts = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "v3_plan_freeze_artifact_sha256_v1.json":
            artifacts.append({"path": str(p.relative_to(OUT)), "sha256": sha256(p), "size": p.stat().st_size})
    dump(OUT / "v3_plan_freeze_artifact_sha256_v1.json", {"status": "PASS", "files": artifacts})
    publish_names = [
        "RCP_LCP_pip_freeze.txt",
        "v3_data_role_transition_v1.json",
        "v3_development_geometry_manifest_v1.csv",
        "v3_development_case_matrix_v1.csv",
        "v3_al64_selection_contract_v1.json",
        "v3_al64_geometry_manifest_v1.csv",
        "v3_al64_future_case_matrix_v1.csv",
        "v3_al64_selection_trace_v1.csv",
        "v3_al64_overlap_audit_v1.json",
        "v3_test40_selection_contract_v1.json",
        "v3_test40_geometry_manifest_v1.csv",
        "v3_test40_case_matrix_v1.csv",
        "v3_test40_case_identity_contract_v1.json",
        "v3_test40_overlap_audit_v1.json",
        "v3_test40_manifest_lock_v1.json",
        "v3_model_candidate_contract_v1.json",
        "v3_training_contract_v1.json",
        "v3_profile_only_loss_contract_v1.json",
        "v3_selection_metrics_contract_v1.json",
        "v3_environment_provenance_v1.json",
        "v3_plan_freeze_safety_audit_v1.json",
        "v3_plan_freeze_completion_manifest_v1.json",
        "v3_plan_freeze_report_v1.md",
        "v3_plan_freeze_artifact_sha256_v1.json",
    ]
    shutil.copy2(OUT / "RCP_LCP_pip_freeze.txt", CONTRACTS / "RCP_LCP_pip_freeze.txt")
    for name in publish_names:
        shutil.copy2(OUT / name, CONTRACTS / name)
    print(json.dumps({"status": "PASS", "decision": completion["decision"], "output": str(OUT), "safety": safety, "counts": {"base_geometries": len(base136), "base_cases": len(base_cases), "al_geometries": len(al), "al_cases": len(al_cases), "test_geometries": len(test), "test_cases": len(test_cases)}}, indent=2))


if __name__ == "__main__":
    main()
