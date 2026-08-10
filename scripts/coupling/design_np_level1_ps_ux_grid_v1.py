"""Design the zero-solver NP Level-1 P/S ux pilot grid.

This script reads the committed coupling provider and the frozen NP source
artifacts.  It never imports lumapi, starts a solver, writes the NP source
worktree, or copies FSP/raw arrays into the coupling worktree.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
NP_SOURCE_ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
PROVIDER_PATH = ROOT / "reports" / "coupling" / "traditional_zl1_mdc_level1_provider_v1.json"
SOURCE_SCOPE_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_formal_source_scope_v1" / "formal_source_scope_v1.json"
SOURCE_HANDOFF_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_formal_source_scope_v1" / "coupling_handoff_manifest_v1.json"
SOURCE_FREEZE_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_formal_source_scope_v1" / "freeze_manifest.json"
PILOT_MANIFEST_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_hf_p0_label_generator_recovery_v1" / "pilot_generator_manifest.json"
TASK_REGISTRY_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1" / "hf_task_registry.csv"
QUALITY_REGISTRY_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1" / "label_quality_registry.csv"
OBSERVATIONS_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1" / "hf_observations_long.csv"
SOURCE_LINEAGE_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_hf_p0_label_generator_recovery_v1" / "source_lineage_audit.json"
ANCHOR_DOC_PATH = NP_SOURCE_ROOT / "docs" / "np_k6_hf_pilot_anchor_dataset_v1.md"
RUN3A_ORDER_AXIS_PATH = NP_SOURCE_ROOT / "outputs" / "np_k6_p1d4b_k6x_phase_candidate_run3a_freeze_v1" / "order_axis_mapping.json"
RUN3A_POST_FSP_ROOT = NP_SOURCE_ROOT / "outputs" / "np_k6_p0_remaining_five_anchors_execution_v1" / "runtime_runs"
LAMBDA_X_NM = 1740.0
WAVELENGTHS_NM = list(range(445, 456))
FRACTIONS = (0.80, 0.90, 0.95, 0.99)
MERGE_TOLERANCE = 0.02
CASE_IDS = {"P": "RUN3A_P_PILOT_HF_V1", "S": "RUN3A_S_PILOT_HF_V1"}
EXPECTED_GEOMETRY_ID = "K6X_D125_D135_D150_D175_D190_D210"
EXPECTED_STACK_ID = "NP_K6_INDEPENDENT_STACK_PILOT_V1"
EXPECTED_GENERATOR_ID = "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_git(*args: str) -> str:
    completed = subprocess.run(["git", "-C", str(NP_SOURCE_ROOT), *args], check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def git_exists(commit: str, relative_path: str) -> bool:
    completed = subprocess.run(["git", "-C", str(NP_SOURCE_ROOT), "cat-file", "-e", f"{commit}:{relative_path}"], capture_output=True)
    return completed.returncode == 0


def git_commit_present(commit: str) -> bool:
    completed = subprocess.run(["git", "-C", str(NP_SOURCE_ROOT), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True)
    return completed.returncode == 0


def git_commit_ancestor(commit: str) -> bool:
    completed = subprocess.run(["git", "-C", str(NP_SOURCE_ROOT), "merge-base", "--is-ancestor", commit, "HEAD"], capture_output=True)
    return completed.returncode == 0


def theta_edges(theta_rad: np.ndarray) -> np.ndarray:
    edges = np.empty(theta_rad.size + 1, dtype=float)
    edges[1:-1] = 0.5 * (theta_rad[:-1] + theta_rad[1:])
    edges[0] = theta_rad[0] - 0.5 * (theta_rad[1] - theta_rad[0])
    edges[-1] = theta_rad[-1] + 0.5 * (theta_rad[-1] - theta_rad[-2])
    return edges


def trap_weights(values: np.ndarray) -> np.ndarray:
    weights = np.empty(values.size, dtype=float)
    weights[0] = 0.5 * (values[1] - values[0])
    weights[-1] = 0.5 * (values[-1] - values[-2])
    weights[1:-1] = 0.5 * (values[2:] - values[:-2])
    return weights


def quantile_from_mass(values: np.ndarray, weights: np.ndarray, fraction: float) -> float:
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    cumulative = np.cumsum(weights[order])
    index = int(np.searchsorted(cumulative, fraction * float(cumulative[-1]), side="left"))
    return float(sorted_values[min(index, sorted_values.size - 1)])


def minimum_contiguous_interval(edges: np.ndarray, mass: np.ndarray, fraction: float) -> dict:
    prefix = np.concatenate(([0.0], np.cumsum(mass)))
    best = None
    for start in range(mass.size):
        required = prefix[start] + fraction
        end = int(np.searchsorted(prefix, required, side="left"))
        if end <= start or end > mass.size:
            continue
        candidate = (float(edges[end] - edges[start]), start, end)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise RuntimeError("no_contiguous_interval_for_fraction")
    width, start, end = best
    return {"ux_min": float(edges[start]), "ux_max": float(edges[end]), "width": width, "captured_mass": float(prefix[end] - prefix[start])}


def symmetric_support(edges: np.ndarray, mass: np.ndarray, fraction: float) -> dict:
    edge_abs = np.maximum(np.abs(edges[:-1]), np.abs(edges[1:]))
    for upper in sorted(set(edge_abs.tolist())):
        captured = float(np.sum(mass[edge_abs <= upper + 1e-15]))
        if captured >= fraction:
            return {"u_abs": float(upper), "captured_mass": captured}
    return {"u_abs": float(edge_abs.max()), "captured_mass": float(mass.sum())}


def side_quantiles(centers: np.ndarray, mass: np.ndarray, near_mask: np.ndarray, sign: int) -> dict:
    if sign < 0:
        mask = (centers < 0) & ~near_mask
    else:
        mask = (centers > 0) & ~near_mask
    values = np.abs(centers[mask])
    weights = mass[mask]
    total = float(weights.sum())
    if total <= 0:
        return {str(int(fraction * 100)): None for fraction in FRACTIONS}
    weights = weights / total
    return {str(int(fraction * 100)): quantile_from_mass(values, weights, fraction) for fraction in FRACTIONS}


def analyze_branch(path: Path, branch: str, provider: dict) -> dict:
    with np.load(path, allow_pickle=False) as data:
        wavelength = np.asarray(data["wavelength_nm"], dtype=float)
        theta_deg = np.asarray(data["angle_deg"], dtype=float)
        ux_edges = np.asarray(data["ux_edges"], dtype=float)
        ux_centers = np.asarray(data["ux_centers"], dtype=float)
        raw_joint = np.asarray(data["raw_joint"], dtype=float)
    if raw_joint.shape[0] != 301 or raw_joint.shape[1] != theta_deg.size:
        raise RuntimeError(f"{branch}_aggregate_shape_mismatch:{raw_joint.shape}")
    mask = (wavelength >= 445.0 - 1e-9) & (wavelength <= 455.0 + 1e-9)
    if wavelength[mask].size < 2 or abs(float(wavelength[mask][0]) - 445.0) > 1e-9 or abs(float(wavelength[mask][-1]) - 455.0) > 1e-9:
        raise RuntimeError(f"{branch}_wavelength_scope_mismatch")
    theta_weight = np.diff(theta_edges(np.radians(theta_deg)))
    ux_widths = np.diff(ux_edges)
    lambda_weight = trap_weights(wavelength)
    weighted_theta = raw_joint[mask] * lambda_weight[mask, None] * theta_weight[None, :]
    raw_band_mass = weighted_theta.sum(axis=0)
    ux_density = np.sum(weighted_theta / ux_widths[None, :], axis=0)
    ux_mass = ux_density * ux_widths
    denominator = float(raw_band_mass.sum())
    angular_mass = ux_mass / denominator
    if not np.isfinite(denominator) or denominator <= 0:
        raise RuntimeError(f"{branch}_nonpositive_denominator")
    if abs(float(angular_mass.sum()) - 1.0) > 1e-12:
        raise RuntimeError(f"{branch}_ux_mass_closure_failed")
    nearest_negative = int(np.where(ux_centers < 0)[0][np.argmin(np.abs(ux_centers[ux_centers < 0]))])
    nearest_positive = int(np.where(ux_centers > 0)[0][np.argmin(np.abs(ux_centers[ux_centers > 0]))])
    near_indices = sorted({nearest_negative, nearest_positive} | set(np.where(np.isclose(ux_centers, 0.0, atol=1e-15))[0].tolist()))
    near_mask = np.zeros(ux_centers.size, dtype=bool)
    near_mask[near_indices] = True
    near_low = float(np.min(ux_edges[np.array(near_indices)]))
    near_high = float(np.max(ux_edges[np.array(near_indices) + 1]))
    negative_mask = (ux_centers < near_low) & ~near_mask
    positive_mask = (ux_centers > near_high) & ~near_mask
    supports = {str(int(fraction * 100)): symmetric_support(ux_edges, angular_mass, fraction) for fraction in FRACTIONS}
    asymmetric = {str(int(fraction * 100)): minimum_contiguous_interval(ux_edges, angular_mass, fraction) for fraction in FRACTIONS}
    negative_mass = float(angular_mass[negative_mask].sum())
    near_mass = float(angular_mass[near_mask].sum())
    positive_mass = float(angular_mass[positive_mask].sum())
    return {
        "branch": branch,
        "aggregate_path": str(path),
        "aggregate_sha256": sha_file(path),
        "wavelength_scope_nm": WAVELENGTHS_NM,
        "wavelength_selection_policy": "inclusive 445-455 nm band; floating-point endpoint tolerance 1e-9; no interpolation or extrapolation",
        "native_band_sample_count": int(wavelength[mask].size),
        "native_tensor_shape": [int(value) for value in raw_joint.shape],
        "ux_bin_count": int(ux_centers.size),
        "raw_band_integral": denominator,
        "ux_mass_closure": float(angular_mass.sum()),
        "mean_ux": float(np.sum(angular_mass * ux_centers)),
        "symmetric_support": supports,
        "asymmetric_minimum_width_intervals": asymmetric,
        "near_zero_definition": "the two ux bins whose centers are nearest zero, plus any exact-zero center bin",
        "near_zero_bin_indices": near_indices,
        "near_zero_interval": [near_low, near_high],
        "mass_by_side": {"negative_ux": negative_mass, "near_zero_ux": near_mass, "positive_ux": positive_mass, "closure": negative_mass + near_mass + positive_mass},
        "negative_side_quantiles_abs_ux": side_quantiles(ux_centers, angular_mass, near_mask, -1),
        "positive_side_quantiles_abs_ux": side_quantiles(ux_centers, angular_mass, near_mask, 1),
        "ux_edges_sha256": hashlib.sha256(ux_edges.tobytes()).hexdigest(),
    }


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def audit_reuse() -> dict:
    scope = read_json(SOURCE_SCOPE_PATH)
    handoff = read_json(SOURCE_HANDOFF_PATH)
    freeze = read_json(SOURCE_FREEZE_PATH)
    manifest = read_json(PILOT_MANIFEST_PATH)
    lineage = read_json(SOURCE_LINEAGE_PATH)
    task_rows = {row["case_id"]: row for row in load_csv(TASK_REGISTRY_PATH)}
    quality_rows = {row["case_id"]: row for row in load_csv(QUALITY_REGISTRY_PATH)}
    observation_rows = load_csv(OBSERVATIONS_PATH)
    source_head = run_git("rev-parse", "HEAD")
    source_status = run_git("status", "--porcelain")
    formal_commit = scope["source_commit"]
    formal_commit_present = git_commit_present(formal_commit)
    formal_commit_ancestor = git_commit_ancestor(formal_commit)
    results = {}
    for branch, case_id in CASE_IDS.items():
        task = task_rows.get(case_id, {})
        quality = quality_rows.get(case_id, {})
        observations = [row for row in observation_rows if row.get("case_id") == case_id]
        post_dir = RUN3A_POST_FSP_ROOT / case_id / "attempt_001"
        post_path = post_dir / f"{case_id}_attempt_001_post.fsp"
        completion_path = post_dir / "completion.json"
        entered_path = post_dir / "entered_ledger.json"
        completion = read_json(completion_path) if completion_path.exists() else {}
        entered = read_json(entered_path) if entered_path.exists() else {}
        post_sha = sha_file(post_path) if post_path.exists() else None
        expected_sha = task.get("post_sha256")
        gates = {
            "case_present_in_formal_p0_registry": case_id in task_rows,
            "quality_gate_pass": quality.get("quality_gate_pass", "").lower() == "true" and task.get("quality_gate_pass", "").lower() == "true",
            "exact_11_point_wavelength_rows": len(observations) == 11 and sorted(int(float(row["wavelength_nm"])) for row in observations) == WAVELENGTHS_NM,
            "ux_zero": float(manifest["u_x"]) == 0.0 and scope["kx_over_k0_scope"]["allowed_values"] == [0.0],
            "same_run3a_candidate_geometry": task.get("geometry_id") == EXPECTED_GEOMETRY_ID and scope["candidate_id"] == "NP_K6X_125_135_150_175_190_210",
            "same_native_m1_material_scope": set(lineage.get("material_readback", {})) >= {"APCD_SIO2_NATIVE_M1", "APCD_TIO2_NATIVE_M1"} and manifest["interface_stack_id"] == EXPECTED_STACK_ID,
            "same_standalone_stack": task.get("interface_stack_id") == EXPECTED_STACK_ID and scope["interface_stack_scope"]["standalone_np_only"] is True,
            "post_fsp_exists": post_path.exists(),
            "post_fsp_sha_matches_registry": post_sha == expected_sha and task.get("source_post_sha256") == expected_sha,
            "completion_provenance": bool(completion) and all(bool(completion.get(key, True)) for key in ("entered", "engine_completed", "controller_returned", "post_saved")),
            "result_artifact_exists": OBSERVATIONS_PATH.exists(),
            "result_rows_quality_pass": bool(observations) and all(row.get("quality_gate_pass", "").lower() == "true" for row in observations),
            "order_sign_convention": read_json(RUN3A_ORDER_AXIS_PATH)["u_x_positive_is_plus1"] is True and "+x" in scope["response_scope"]["sign_convention"],
            "formal_scope_commit_present": formal_commit_present and formal_commit_ancestor,
        }
        reuse = all(gates.values())
        results[branch] = {
            "case_id": case_id,
            "polarization": branch,
            "reuse_decision": "REUSABLE_LEVEL1_NP_ANCHOR" if reuse else "HARD_GATE_P0_REUSE_AUDIT_FAILED",
            "reuse_scope": "ux=0 central anchor only; standalone NP scope; no quantitative joint MDC-NP power claim",
            "gates": gates,
            "candidate_id": scope["candidate_id"],
            "geometry_id": task.get("geometry_id"),
            "geometry_hash": task.get("geometry_hash"),
            "canonical_run3a_geometry_hash": scope["geometry_scope"]["canonical_geometry_hash"],
            "polarization": task.get("polarization"),
            "ux": 0.0,
            "wavelengths_nm": WAVELENGTHS_NM,
            "reference_stack": scope["interface_stack_scope"]["stack"],
            "interface_stack_id": task.get("interface_stack_id"),
            "incident_medium": "APCD_SIO2_NATIVE_M1",
            "output_medium": "Air",
            "material_ids": sorted(lineage.get("material_readback", {}).keys()),
            "post_fsp_path": str(post_path),
            "post_fsp_sha256": post_sha,
            "result_artifact_path": str(OBSERVATIONS_PATH),
            "result_artifact_sha256": sha_file(OBSERVATIONS_PATH),
            "result_row_selector": {"case_id": case_id, "wavelength_nm": WAVELENGTHS_NM},
            "source_branch": scope["source_branch"],
            "source_checkout_head": source_head,
            "source_checkout_dirty": bool(source_status),
            "source_commit": formal_commit,
            "source_package_locked_commit": scope["source_package_locked_commit"],
            "scope_id": scope["scope_id"],
            "package_id": scope["package_id"],
            "package_sha256": scope["package_sha256"],
            "generator_id": task.get("generator_id"),
            "completion": completion,
            "entered_ledger": entered,
            "legacy_p0_failure_records_are_not_selected": True,
        }
    return {
        "schema_version": "np_level1_cross_branch_reuse_registry_v1",
        "status": "PASS" if all(item["reuse_decision"] == "REUSABLE_LEVEL1_NP_ANCHOR" for item in results.values()) else "HARD_GATE_P0_REUSE_AUDIT_FAILED",
        "source_worktree": str(NP_SOURCE_ROOT),
        "source_branch": scope["source_branch"],
        "source_checkout_head": source_head,
        "source_checkout_dirty": bool(source_status),
        "source_checkout_status_lines": source_status.splitlines(),
        "formal_source_commit": formal_commit,
        "formal_source_commit_present": formal_commit_present,
        "formal_source_commit_ancestor_of_checkout": formal_commit_ancestor,
        "formal_scope_files_present_in_current_checkout": all(path.exists() for path in (SOURCE_SCOPE_PATH, SOURCE_HANDOFF_PATH, TASK_REGISTRY_PATH)),
        "formal_scope_artifact_path": str(SOURCE_SCOPE_PATH),
        "formal_scope_artifact_sha256": sha_file(SOURCE_SCOPE_PATH),
        "handoff_artifact_path": str(SOURCE_HANDOFF_PATH),
        "handoff_artifact_sha256": sha_file(SOURCE_HANDOFF_PATH),
        "freeze_manifest_path": str(SOURCE_FREEZE_PATH),
        "freeze_manifest_sha256": sha_file(SOURCE_FREEZE_PATH),
        "p0_anchor_dataset_status": "NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY",
        "m2_angular_reuse_count": 0,
        "m2_non_substitution_verdict": "PASS: M2 geometry HF coverage is not used as RUN3A angular data",
        "np_source_writes": 0,
        "cases": results,
    }


def threshold_registry() -> dict:
    rows = []
    for wavelength in WAVELENGTHS_NM:
        for order in range(-3, 4):
            shift = order * wavelength / LAMBDA_X_NM
            for boundary_sign in (-1, 1):
                ux = -shift + boundary_sign
                if -1.0 - 1e-15 <= ux <= 1.0 + 1e-15:
                    rows.append({
                        "m": order,
                        "lambda_nm": wavelength,
                        "ux_transition": float(ux),
                        "opening_closing": "opening" if boundary_sign < 0 else "closing",
                        "sign": "negative" if boundary_sign < 0 else "positive",
                        "u_out_at_transition": boundary_sign,
                        "ux_increasing_behavior": "open_after_crossing" if boundary_sign < 0 else "close_after_crossing",
                    })
    return {
        "schema_version": "np_level1_order_threshold_registry_v1",
        "registry_id": "NP_LEVEL1_ORDER_THRESHOLD_REGISTRY_V1",
        "period_x_nm": LAMBDA_X_NM,
        "wavelength_scope_nm": WAVELENGTHS_NM,
        "formula": "u_out_m = u_in + m*lambda/Lambda_x; transition when abs(u_out_m)=1",
        "orders_considered": list(range(-3, 4)),
        "threshold_rows": rows,
        "threshold_rows_at_450_nm": [row for row in rows if row["lambda_nm"] == 450],
        "selection_rule": "retain transitions inside -1<=ux<=1; opening is crossing u_out=-1 with increasing ux; closing is crossing u_out=+1",
    }


def order_threshold_nodes(thresholds: dict, branch: str, support_fraction: float, branch_analysis: dict) -> list[dict]:
    support = branch_analysis["symmetric_support"][str(int(support_fraction * 100))]["u_abs"]
    nodes = []
    for row in thresholds["threshold_rows_at_450_nm"]:
        if row["m"] == 0 or abs(row["ux_transition"]) >= 1.0 or abs(row["ux_transition"]) > support + 1e-12:
            continue
        nodes.append({
            "ux": row["ux_transition"],
            "selection_reason": "ORDER_THRESHOLD",
            "order_threshold_refs": [row["m"], row["lambda_nm"], row["opening_closing"]],
            "threshold_support_fraction": support_fraction,
            "branch": branch,
        })
    return nodes


def quantile_nodes(branch_analysis: dict, branch: str, fractions: tuple[float, ...]) -> list[dict]:
    nodes = []
    for side, values in (("negative", branch_analysis["negative_side_quantiles_abs_ux"]), ("positive", branch_analysis["positive_side_quantiles_abs_ux"])):
        for fraction in fractions:
            value = values[str(int(fraction * 100))]
            if value is None:
                continue
            nodes.append({"ux": -value if side == "negative" else value, "selection_reason": "MASS_QUANTILE", "mass_quantile": fraction, "side": side, "branch": branch})
    return nodes


def merge_nodes(raw_nodes: list[dict], branch: str) -> list[dict]:
    priority = {"CENTRAL_ANCHOR": 0, "ORDER_THRESHOLD": 1, "MASS_QUANTILE": 2, "GRAZING_SUPPORT": 3}
    ordered = sorted(raw_nodes, key=lambda item: (float(item["ux"]), priority.get(item["selection_reason"], 9), json.dumps(item, sort_keys=True)))
    merged: list[dict] = []
    for candidate in ordered:
        if not merged or abs(float(candidate["ux"]) - float(merged[-1]["ux"])) > MERGE_TOLERANCE:
            merged.append({**candidate, "merged_candidates": [candidate], "merge_reason": "no_merge"})
            continue
        previous = merged[-1]
        all_candidates = previous["merged_candidates"] + [candidate]
        representative = min(all_candidates, key=lambda item: (priority.get(item["selection_reason"], 9), abs(float(item["ux"])), float(item["ux"])))
        previous.update({**representative, "branch": branch, "merged_candidates": all_candidates, "merge_reason": f"abs_ux_difference<= {MERGE_TOLERANCE}"})
    for node in merged:
        node["ux"] = float(node["ux"])
        node["ux_abs_lt_one_gate"] = abs(node["ux"]) < 1.0
    return merged


def design_branch(branch: str, analysis: dict, thresholds: dict, reuse: dict) -> dict:
    minimum = [{"ux": 0.0, "selection_reason": "CENTRAL_ANCHOR", "branch": branch, "source_asset_id": reuse["case_id"]}]
    minimum += quantile_nodes(analysis, branch, (0.95,))
    minimum += order_threshold_nodes(thresholds, branch, 0.95, analysis)
    recommended = [{"ux": 0.0, "selection_reason": "CENTRAL_ANCHOR", "branch": branch, "source_asset_id": reuse["case_id"]}]
    recommended += quantile_nodes(analysis, branch, FRACTIONS)
    recommended += order_threshold_nodes(thresholds, branch, 0.99, analysis)
    if branch == "P" and analysis["symmetric_support"]["99"]["u_abs"] > 0.95:
        recommended.extend([
            {"ux": -0.98, "selection_reason": "GRAZING_SUPPORT", "branch": branch, "captured_mass_note": "strictly below grazing; ux=+/-1 forbidden"},
            {"ux": 0.98, "selection_reason": "GRAZING_SUPPORT", "branch": branch, "captured_mass_note": "strictly below grazing; ux=+/-1 forbidden"},
        ])
    minimum_merged = merge_nodes(minimum, branch)
    recommended_merged = merge_nodes(recommended, branch)
    return {
        "branch": branch,
        "minimum": {"raw_candidates": minimum, "merged_nodes": minimum_merged, "final_proposed_nodes": minimum_merged, "new_solver_nodes": [node for node in minimum_merged if abs(node["ux"]) > 1e-15], "new_solver_count": sum(abs(node["ux"]) > 1e-15 for node in minimum_merged)},
        "recommended": {"raw_candidates": recommended, "merged_nodes": recommended_merged, "final_proposed_nodes": recommended_merged, "new_solver_nodes": [node for node in recommended_merged if abs(node["ux"]) > 1e-15], "new_solver_count": sum(abs(node["ux"]) > 1e-15 for node in recommended_merged)},
        "merge_tolerance": MERGE_TOLERANCE,
        "uniform_grid_shortcut": False,
    }


def node_table(designs: dict) -> list[dict[str, object]]:
    rows = []
    for level in ("minimum", "recommended"):
        for branch in ("P", "S"):
            for node in designs[branch][level]["final_proposed_nodes"]:
                ux = float(node["ux"])
                reusable = abs(ux) <= 1e-15
                rows.append({
                    "grid_level": level,
                    "polarization": branch,
                    "ux": ux,
                    "selection_reason": node["selection_reason"],
                    "existing_asset": CASE_IDS[branch] if reusable else "",
                    "reusable": reusable,
                    "needs_new_solver": not reusable,
                    "source_asset_id": CASE_IDS[branch] if reusable else "",
                    "order_threshold_refs": json.dumps(node.get("order_threshold_refs", []), separators=(",", ":")),
                })
    return rows


def make_contract(provider: dict, reuse: dict, branches: dict, thresholds: dict, analyses: dict, test_summary: str) -> dict:
    min_p = branches["P"]["minimum"]["new_solver_count"]
    min_s = branches["S"]["minimum"]["new_solver_count"]
    rec_p = branches["P"]["recommended"]["new_solver_count"]
    rec_s = branches["S"]["recommended"]["new_solver_count"]
    return {
        "schema_version": "np_level1_ps_ux_grid_design_v1",
        "design_id": "NP_LEVEL1_PS_UX_GRID_DESIGN_V1",
        "status": "PASS" if reuse["status"] == "PASS" else "HARD_GATE_P0_REUSE_AUDIT_FAILED",
        "solver_authorization": {"this_task_solver_entries": 0, "NP_FDTD": 0, "MDC_FDTD": 0, "integrated_FDTD": 0, "TMM": 0, "RCWA": 0, "FEM": 0, "training": 0, "ML_inference": 0},
        "authoritative_mdc_provider": {"path": str(PROVIDER_PATH), "sha256": sha_file(PROVIDER_PATH), "provider_id": provider["provider_id"], "status": provider["status"], "native_grid": provider["grid"], "formal_band_nm": [445, 455]},
        "cross_branch_reuse_registry": {"path": str(ROOT / "registries" / "coupling" / "np_level1_cross_branch_reuse_registry_v1.json"), "status": reuse["status"], "P": reuse["cases"]["P"], "S": reuse["cases"]["S"], "M2_angular_reuse_count": 0},
        "mass_analysis": analyses,
        "order_threshold_registry": {"registry_id": thresholds["registry_id"], "path": str(ROOT / "registries" / "coupling" / "np_level1_order_threshold_registry_v1.json"), "sha256": None, "lambda_x_nm": LAMBDA_X_NM},
        "node_design": branches,
        "solver_budget": {"minimum": {"P_required_nodes": 1 + min_p, "P_reusable_nodes": 1, "P_new_solver_cases": min_p, "S_required_nodes": 1 + min_s, "S_reusable_nodes": 1, "S_new_solver_cases": min_s, "TOTAL_NEW_NP_3D_BROADBAND_CASES": min_p + min_s}, "recommended": {"P_required_nodes": 1 + rec_p, "P_reusable_nodes": 1, "P_new_solver_cases": rec_p, "S_required_nodes": 1 + rec_s, "S_reusable_nodes": 1, "S_new_solver_cases": rec_s, "TOTAL_NEW_NP_3D_BROADBAND_CASES": rec_p + rec_s}, "wavelength_contract": "one 445-455 nm exact 1 nm broadband physical solve per polarization x ux node", "P0_S0_rerun": 0},
        "np_surrogate_status": "NP_ANGULAR_SURROGATE_CAPABILITY_NOT_ESTABLISHED",
        "m2_non_substitution": "M2 angular reuse count = 0; M2 is not RUN3A angular data",
        "tests": test_summary,
    }


def write_report(path: Path, contract: dict, reuse: dict, thresholds: dict) -> None:
    p = contract["mass_analysis"]["P"]["symmetric_support"]
    s = contract["mass_analysis"]["S"]["symmetric_support"]
    min_budget = contract["solver_budget"]["minimum"]
    rec_budget = contract["solver_budget"]["recommended"]
    lines = [
        "# NP Level-1 P/S ux grid design v1",
        "",
        "### 状态",
        "",
        f"{contract['status']}；this design task solver=0（NP/MDC/integrated FDTD/TMM/RCWA/FEM/training/ML 均为 0）。",
        "",
        "### Cross-branch reuse",
        "",
        f"RUN3A-P: `{reuse['cases']['P']['reuse_decision']}`；RUN3A-S: `{reuse['cases']['S']['reuse_decision']}`。两者均只作为 ux=0 standalone NP central anchor，不扩展为 quantitative joint MDC-NP power。",
        f"formal source commit: `{reuse['formal_source_commit']}`；formal scope: `{reuse['formal_scope_artifact_path']}`；M2 angular reuse count: `0`。",
        "",
        "### MDC-weighted ux grid",
        "",
        f"P support 80/90/95/99%: `{p['80']['u_abs']:.8f}`, `{p['90']['u_abs']:.8f}`, `{p['95']['u_abs']:.8f}`, `{p['99']['u_abs']:.8f}`。",
        f"S support 80/90/95/99%: `{s['80']['u_abs']:.8f}`, `{s['90']['u_abs']:.8f}`, `{s['95']['u_abs']:.8f}`, `{s['99']['u_abs']:.8f}`。",
        f"P minimum nodes: `{[node['ux'] for node in contract['node_design']['P']['minimum']['final_proposed_nodes']]}`；S minimum nodes: `{[node['ux'] for node in contract['node_design']['S']['minimum']['final_proposed_nodes']]}`。",
        f"P recommended nodes: `{[node['ux'] for node in contract['node_design']['P']['recommended']['final_proposed_nodes']]}`；S recommended nodes: `{[node['ux'] for node in contract['node_design']['S']['recommended']['final_proposed_nodes']]}`。",
        f"Order thresholds: `{len(thresholds['threshold_rows'])}` rows for m=-3..+3, lambda=445..455 nm; node selection uses deterministic 450 nm representatives and retains P/S separately.",
        "",
        "### Exact future solver budget",
        "",
        f"MINIMUM_PILOT_GRID: P new=`{min_budget['P_new_solver_cases']}`, S new=`{min_budget['S_new_solver_cases']}`, total=`{min_budget['TOTAL_NEW_NP_3D_BROADBAND_CASES']}`；P0/S0 rerun=`0`。",
        f"RECOMMENDED_PILOT_GRID: P new=`{rec_budget['P_new_solver_cases']}`, S new=`{rec_budget['S_new_solver_cases']}`, total=`{rec_budget['TOTAL_NEW_NP_3D_BROADBAND_CASES']}`；exact 445–455 nm 1 nm broadband per polarization×ux node。",
        "",
        "### Tests / Git / 下一步",
        "",
        f"Test evidence: `{contract['tests']}`。FSP/raw arrays remain external; only paths/SHA/source commit/scope are recorded.",
        "下一步：`REQUEST_NP_LEVEL1_MINIMUM_PS_UX_PILOT_SOLVER_AUTHORIZATION`。",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-summary", default="not_run")
    args = parser.parse_args()
    provider = read_json(PROVIDER_PATH)
    if provider["status"] != "PASS" or not all(provider["quality_gates"].values()):
        raise RuntimeError("authoritative_mdc_provider_not_pass")
    p_path = Path(provider["W_MDC_P_lambda_ux"]["path"])
    s_path = Path(provider["W_MDC_S_lambda_ux"]["path"])
    analyses = {"P": analyze_branch(p_path, "P", provider), "S": analyze_branch(s_path, "S", provider)}
    reuse = audit_reuse()
    thresholds = threshold_registry()
    branches = {branch: design_branch(branch, analyses[branch], thresholds, reuse["cases"][branch]) for branch in ("P", "S")}
    contract = make_contract(provider, reuse, branches, thresholds, analyses, args.test_summary)
    threshold_path = ROOT / "registries" / "coupling" / "np_level1_order_threshold_registry_v1.json"
    write_json(threshold_path, thresholds)
    contract["order_threshold_registry"]["sha256"] = sha_file(threshold_path)
    reuse_path = ROOT / "registries" / "coupling" / "np_level1_cross_branch_reuse_registry_v1.json"
    write_json(reuse_path, reuse)
    contract_path = ROOT / "contracts" / "coupling" / "np_level1_ps_ux_grid_design_v1.json"
    write_json(contract_path, contract)
    table_path = ROOT / "reports" / "coupling" / "np_level1_ps_ux_grid_nodes_v1.csv"
    table_path.parent.mkdir(parents=True, exist_ok=True)
    with table_path.open("w", encoding="utf-8", newline="") as stream:
        rows = node_table(branches)
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report_path = ROOT / "reports" / "coupling" / "np_level1_ps_ux_grid_design_v1.md"
    write_report(report_path, contract, reuse, thresholds)
    print(json.dumps({"status": contract["status"], "solver_entries": 0, "P_new_minimum": contract["solver_budget"]["minimum"]["P_new_solver_cases"], "S_new_minimum": contract["solver_budget"]["minimum"]["S_new_solver_cases"], "total_new_minimum": contract["solver_budget"]["minimum"]["TOTAL_NEW_NP_3D_BROADBAND_CASES"], "P_new_recommended": contract["solver_budget"]["recommended"]["P_new_solver_cases"], "S_new_recommended": contract["solver_budget"]["recommended"]["S_new_solver_cases"], "total_new_recommended": contract["solver_budget"]["recommended"]["TOTAL_NEW_NP_3D_BROADBAND_CASES"], "reuse": {branch: reuse["cases"][branch]["reuse_decision"] for branch in ("P", "S")}, "outputs": [str(contract_path), str(reuse_path), str(threshold_path), str(table_path), str(report_path)]}, sort_keys=True))


if __name__ == "__main__":
    main()
