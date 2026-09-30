#!/usr/bin/env python3
"""Zero-solver, fail-closed evidence packager for NP-feature 20G coverage.

This script never trains, reads Shared V3 control state, launches a solver, or
computes held-out errors. It is intentionally a preflight because the frozen NP
LF provider does not cover the current Coupling geometries.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NP_ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
DATASET_PATH = ROOT / r"reports/coupling/PW_K6_20G_DATASET_FREEZE_MANIFEST_V1.json"
BASELINE_PATH = ROOT / r"reports/coupling/PW_K6_STRUCTURED_FORWARD_MODEL_FREEZE_V1.md"
GATE_PATH = ROOT / r"reports/coupling/PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json"
DECODER_PATH = ROOT / r"scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py"
SUPPORT_PATH = NP_ROOT / r"outputs/np_k6_coupling_forward_feature_interface_v1/coupling_20g_domain_support.json"
INTERFACE_PATH = NP_ROOT / r"outputs/np_k6_coupling_forward_feature_interface_v1/interface_manifest.json"
INTERFACE_SOURCE = NP_ROOT / r"scripts/np_k6_coupling_forward_feature_interface_v1.py"
PROVIDER_PATH = NP_ROOT / r"outputs/np_k6_final_freeze_closeout_v1/provider_manifest.json"
NP_PROVENANCE_PATH = NP_ROOT / r"outputs/np_k6_coupling_forward_feature_interface_v1/provenance.json"
OUT_DIR = ROOT / r"reports/coupling/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V1"
REPORT_PATH = ROOT / r"reports/coupling/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V1.md"
WAVELENGTHS = list(range(445, 456))
EXPECTED_CASES = (
    ["K6V1_S02", "K6V1_S03", "K6V1_S04", "K6V1_S05", "K6V1_S15", "K6V1_S16"]
    + [f"K6V1_EXT{i:02d}" for i in range(1, 15)]
)
H1_GATES = {
    "state_relative_rmse": {"median_max": 0.50, "q95_max": 0.80},
    "routing_eta_rmse": {"median_max": 0.05, "q95_max": 0.10, "pearson_min": 0.95},
    "absolute_order_source_normalized_rmse": {"median_max": 0.05, "q95_max": 0.10},
    "thresholded_absolute_order_relative": {
        "median_max": 0.30, "q95_max": 0.75,
        "significance_threshold": 0.0009885656815447454,
    },
    "total_power_relative": {"median_max": 0.15, "q95_max": 0.30, "pearson_min": 0.95},
    "seed_state_median_std_max": 0.03,
    "conjunctive": True,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def lf_order_field(m: int) -> str:
    return f"LF_order_vector[{m:+d}]" if m != 0 else "LF_order_vector[0]"


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def git_authority(root: Path) -> dict:
    return {
        "branch": git(root, "branch", "--show-current"),
        "head": git(root, "rev-parse", "HEAD"),
        "upstream_divergence_left_right": git(root, "rev-list", "--left-right", "--count", "HEAD...@{u}"),
    }


def group_folds(groups: list[str], n_splits: int = 3) -> list[dict]:
    """Use authoritative sklearn GroupKFold, with geometry IDs as indivisible groups."""
    from sklearn.model_selection import GroupKFold
    import numpy as np

    x = np.zeros((len(groups), 1), dtype=float)
    result = []
    for train_i, val_i in GroupKFold(n_splits=n_splits).split(x, groups=groups):
        train = [groups[int(i)] for i in train_i]
        valid = [groups[int(i)] for i in val_i]
        if set(train) & set(valid) or set(train) | set(valid) != set(groups):
            raise AssertionError("inner geometry leakage")
        result.append({"train_geometry_ids": train, "validation_geometry_ids": valid})
    return result


def build_fold_manifest(case_ids: list[str]) -> dict:
    folds = []
    for i, heldout in enumerate(case_ids, 1):
        train = [x for x in case_ids if x != heldout]
        folds.append({
            "outer_fold": i,
            "test_geometry_id": heldout,
            "train_geometry_ids": train,
            "inner_group_folds": group_folds(train, 3),
            "test_metrics_computed": False,
        })
    tests = [f["test_geometry_id"] for f in folds]
    if len(tests) != len(case_ids) or set(tests) != set(case_ids):
        raise AssertionError("LOGO test partition invalid")
    return {
        "schema": "COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_FOLD_MANIFEST_V1",
        "outer_split": "strict leave-one-complete-ordered-geometry-out (20 folds)",
        "inner_split": "3-fold sklearn GroupKFold, geometry IDs are groups",
        "statistical_unit": "one complete ordered geometry; all wavelength rows grouped with it",
        "folds": folds,
        "predictions_generated": False,
        "metrics_computed": False,
    }


def make_32g_contract() -> dict:
    # Deliberately exactly the nine required top-level contract fields.
    return {
        "arms_A0_A1_A2_A3_availability_rules": {
            "A0": "COUPLING_BASELINE; current formal integrated 3D PW inputs only; always required when labels are valid",
            "A1": "NP_LF_PHYSICS; legal only when the frozen provider returns provenance-tagged LF values for every paired geometry×wavelength row; no ordering permutation, interpolation, or fallback",
            "A2": "NP_FROZEN_LEARNED_SCALAR; legal only when provider parity is formally PASS and the frozen interface declares reproducible runtime availability; otherwise SKIP with the exact reason",
            "A3": "NP_LF_AND_LEARNED; legal only when A1 and A2 are both available on the exact A0 rows; compare incrementally against A1",
            "availability_is_not_imputed": True,
        },
        "feature_field_identities": {
            "A0": ["ordered_D1_nm", "ordered_D2_nm", "ordered_D3_nm", "ordered_D4_nm", "ordered_D5_nm", "ordered_D6_nm"],
            "A1": {
                "interface": "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1",
                "provider": "FROZEN_D0_FULL_VECTOR_ARRAY_AUTHORITY",
                "fields_per_wavelength": ["LF order_vector[-3]", "LF order_vector[-2]", "LF order_vector[-1]", "LF order_vector[0]", "LF order_vector[+1]", "LF order_vector[+2]", "LF order_vector[+3]", "LF T_proxy = LF_order_vector[-1] + LF_order_vector[0] + LF_order_vector[+1]"],
                "order": "445,446,...,455 nm; P_XLIKE only for current Coupling branch; ux=0; ky=0",
                "support_metadata_is_feature": False,
            },
            "A2": "only the frozen learned scalar response explicitly declared reproducibly callable by the NP authority",
            "A3": "A1 fields concatenated with the exact A2 scalar field; no other engineered fields",
            "support_diagnostics_not_features": ["exact_HF22_match", "nearest_HF22_distance", "nearest_HF22_geometry_id", "OOD flag", "support warnings"],
        },
        "preprocessing": {
            "baseline_geometry": "D1..D6 ordered; divide by 130 nm; StandardScaler fit on training geometries only",
            "NP_arm_capacity_control": "concatenate only authorized NP features; fit StandardScaler then PCA to six input components on each training fold only, preserving the frozen 6-input width-32 model capacity; no test-fit transformation",
            "state_target": "seven order-local rank-2 PCA bases fitted on training geometries only; inverse transform for scoring",
            "P_scale": "RBF Kernel Ridge with StandardScaler for X/y fit on training geometries only; alpha in {0.1,1,10}, gamma in {0.1,1}; 3-fold grouped inner selection",
            "missing_or_unsupported": "fail closed; no fill, interpolation, extrapolation, sorting, or symmetry substitution",
        },
        "geometry_split_philosophy": {
            "outer": "strict leave-one-complete-ordered-geometry-out",
            "inner": "3-fold geometry-grouped validation inside each outer training set",
            "wavelength_random_split": False,
            "geometry_sorting_or_permutation": False,
            "all_wavelengths_of_heldout_geometry_stay_heldout": True,
        },
        "paired_band_nm": list(WAVELENGTHS),
        "current_target_schema": {
            "authority": "PW_K6_GRATING_TRUTH_V2 + PW_COMPLEX_FLOQUET_STATE_V1",
            "state": "integrated 3D PW POSTNP; original C_PW / C_hat factorization; seven order-local rank-2 spectral latents; deterministic H2 decoder",
            "scale": "POSTNP_TOTAL_POWER_V2 / P_scale; predicted, never oracle substituted",
            "polarization": "P_XLIKE only; no P/S averaging or fabricated S target",
            "domain": "445–455 nm paired rows only",
        },
        "metrics": {
            "state": ["relative/state RMSE by geometry", "median", "q95", "worst geometry"],
            "routing": ["eta/routing RMSE by geometry", "Pearson correlation", "median", "q95", "worst geometry"],
            "absolute_order": ["source-normalized error", "thresholded meaningful-power relative error", "frozen significance threshold 0.0009885656815447454"],
            "total_power": ["relative error", "Pearson correlation", "median", "q95"],
            "stability": ["seed state-median standard deviation"],
            "paired": ["per-geometry delta vs A0", "win/tie/loss for each legal NP arm"],
            "H1_gates": H1_GATES,
        },
        "acceptance_logic": {
            "supported": "at least one legal NP arm improves both state and routing median RMSE by >=5%, wins on >=60% of geometries for both endpoints (12/20 for 20G; 20/32 for 32G), and does not worsen state/routing q95 by >10% or worst-case error by >25%; key absolute-order and total-power medians/q95 must not materially degrade; report OOD strata and seed stability",
            "partial": "measurable but target-specific/small improvement, OOD-stratum sensitivity, or unstable q95/worst-case behavior",
            "not_supported": "no meaningful incremental improvement or consistent degradation",
            "blocked": "formal matched labels/provider values are insufficient or fail integrity/coverage gates",
            "production_H1_is_separate": "all frozen conjunctive H1 gates must pass; feature utility never implies production admission",
            "no_posthoc_threshold_changes": True,
        },
        "ood_analysis_rule": {
            "distance": "sqrt(sum(((D_i-g_i)/130 nm)^2)) over ordered HF22 geometries",
            "strata": "stable sort by (distance, case_id), split nearest/middle/farthest thirds (7/7/6 for 20; analogous thirds for 32)",
            "use": "diagnostics/stratification only; never a model feature",
            "exact_match_and_extrapolation_counts": "report from frozen support authority; no interpolation",
        },
    }


def collect() -> dict:
    coupling_git = git_authority(ROOT)
    np_git = git_authority(NP_ROOT)
    if coupling_git["branch"] != "work/mdc-np-coupling-ml-v1":
        raise RuntimeError(f"unexpected Coupling branch: {coupling_git['branch']}")
    if np_git["branch"] != "work/np-k6-mdc-v1" or not np_git["head"].startswith("f8dad0e8438167ff"):
        raise RuntimeError(f"NP authority changed: {np_git}")
    if OUT_DIR.exists() or REPORT_PATH.exists():
        raise FileExistsError("refuse to overwrite pre-existing ablation output")

    dataset = load_json(DATASET_PATH)
    if dataset.get("schema") != "PW_K6_20G_DATASET_FREEZE_MANIFEST_V1" or dataset.get("status") != "PASS":
        raise RuntimeError("formal 20G dataset manifest is not PASS")
    selected = dataset.get("selected_cases", [])
    by_case = {item["case_id"]: item for item in selected}
    if len(selected) != 20 or set(by_case) != set(EXPECTED_CASES):
        raise RuntimeError("selected geometry set differs from the frozen 20G authority")
    if dataset.get("scientific_entry_total") != 20 or dataset.get("duplicate_scientific_entry_count") != 0 or dataset.get("replay_count") != 0:
        raise RuntimeError("dataset entry/replay counters fail frozen authority")

    baseline_hash = sha256(BASELINE_PATH)
    gate = load_json(GATE_PATH)
    interface_manifest = load_json(INTERFACE_PATH)
    provider_manifest = load_json(PROVIDER_PATH)
    np_provenance = load_json(NP_PROVENANCE_PATH)
    support = load_json(SUPPORT_PATH)
    if interface_manifest.get("interface_name") != "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1":
        raise RuntimeError("unexpected NP interface")
    if interface_manifest.get("provider_components", {}).get("auxiliary_lf", {}).get("status") != "AVAILABLE_READ_ONLY":
        raise RuntimeError("frozen LF component is not declared available")
    if support.get("status") != "PASS" or support.get("coupling_20g_case_count") != 20:
        raise RuntimeError("NP support manifest not valid for 20G")

    case_records = []
    for case_id in EXPECTED_CASES:
        item = by_case[case_id]
        artifact_records = item["artifacts"]
        pre_path = Path(artifact_records["pre"]["path"])
        pre_manifest = load_json(pre_path) if pre_path.is_file() else {}
        hf_manifest = load_json(Path(artifact_records["hf"]["path"]))
        ledger_obj = load_json(Path(artifact_records["ledger"]["path"]))
        checked = {}
        for key in ("ledger", "state", "raw", "projection", "orders", "validation", "pre", "hf", "fsp", "h5"):
            rec = artifact_records[key]
            p = Path(rec["path"])
            if not p.is_file():
                if key == "pre" and rec.get("exists") is False and rec.get("bytes", 0) == 0 and not rec.get("sha256"):
                    checked[key] = {"path": str(p), "status": "ABSENT_IN_FROZEN_MANIFEST; ENTRY_HASH_LINEAGE_VERIFIED_FROM_LEDGER"}
                    continue
                raise FileNotFoundError(f"{case_id} missing {key}: {p}")
            if key == "state":
                # Dataset manifest's state path names the JSON sidecar while its
                # sha256 field is the paired NPZ payload hash; validate both links.
                state_meta_obj = load_json(p)
                paired_npz = p.with_suffix(".npz")
                if not paired_npz.is_file():
                    raise FileNotFoundError(f"{case_id} missing paired state NPZ: {paired_npz}")
                actual_sha = sha256(paired_npz)
                if rec.get("sha256") and actual_sha != rec["sha256"]:
                    raise RuntimeError(f"{case_id} state NPZ sha mismatch")
                if actual_sha != state_meta_obj.get("sha256"):
                    raise RuntimeError(f"{case_id} state sidecar/NPZ sha mismatch")
                checked[key] = {"metadata_path": str(p), "metadata_bytes": p.stat().st_size, "metadata_sha256": sha256(p), "npz_path": str(paired_npz), "npz_bytes": paired_npz.stat().st_size, "npz_sha256": actual_sha}
            elif key == "fsp":
                # The frozen manifest's FSP digest is pre-entry; the post-solver FSP
                # is independently frozen by one of the two archived schema variants.
                actual_sha = sha256(p)
                pre_fsp_sha = (pre_manifest.get("pre_fsp_sha256") or pre_manifest.get("setup_fsp_sha256")
                               or ledger_obj.get("pre_fsp_sha256") or ledger_obj.get("run_fsp_sha256"))
                if rec.get("sha256") != pre_fsp_sha or rec.get("sha256") != ledger_obj.get("run_fsp_sha256"):
                    raise RuntimeError(f"{case_id} pre-entry FSP hash lineage mismatch")
                archive_path_raw = hf_manifest.get("runtime_fsp") or hf_manifest.get("post_fsp")
                archive_sha = hf_manifest.get("runtime_fsp_sha256") or hf_manifest.get("post_fsp_sha256")
                if not archive_path_raw or not archive_sha:
                    raise RuntimeError(f"{case_id} archived runtime/post FSP hash fields missing")
                archive_path = Path(archive_path_raw)
                if not archive_path.is_file() or sha256(archive_path) != archive_sha or actual_sha != archive_sha:
                    raise RuntimeError(f"{case_id} archived runtime FSP hash mismatch")
                checked[key] = {
                    "path": str(p),
                    "bytes": p.stat().st_size,
                    "manifest_sha256_semantics": "pre-entry FSP digest, confirmed by pre_entry_manifest and attempt ledger",
                    "pre_entry_fsp_sha256": rec.get("sha256"),
                    "post_solver_runtime_fsp_sha256": actual_sha,
                    "hf_archive_path": str(archive_path),
                    "hf_archive_runtime_fsp_sha256": archive_sha,
                }
            else:
                actual_sha = sha256(p) if rec.get("sha256") else None
                if rec.get("sha256") and actual_sha != rec["sha256"]:
                    raise RuntimeError(f"{case_id} {key} sha mismatch")
                checked[key] = {"path": str(p), "bytes": p.stat().st_size, "sha256": actual_sha or rec.get("sha256")}
            if p.stat().st_size != rec.get("bytes"):
                raise RuntimeError(f"{case_id} {key} byte-size mismatch")

        state_meta_path = Path(artifact_records["state"]["path"])
        state_meta = load_json(state_meta_path)
        state_npz = state_meta_path.with_suffix(".npz")
        if not state_npz.is_file() or sha256(state_npz) != state_meta.get("sha256"):
            raise RuntimeError(f"{case_id} canonical state NPZ absent or hash mismatch")
        import numpy as np
        with np.load(state_npz, allow_pickle=False) as z:
            expected_keys = {"coefficients_real", "coefficients_imag", "wavelengths_nm", "orders", "propagating_mask", "mode_kz_real", "mode_kz_imag", "basis_condition"}
            if set(z.files) != expected_keys:
                raise RuntimeError(f"{case_id} state schema mismatch: {z.files}")
            shape = list(z["coefficients_real"].shape)
            if shape != [3, 21, 81, 2, 2]:
                raise RuntimeError(f"{case_id} state shape mismatch: {shape}")
            if not np.all(np.isfinite(z["coefficients_real"])) or not np.all(np.isfinite(z["coefficients_imag"])):
                raise RuntimeError(f"{case_id} nonfinite canonical state")
            wavelengths = [float(x) for x in z["wavelengths_nm"]]
            if len(wavelengths) != 21 or not np.allclose(wavelengths, np.arange(440, 461), atol=1e-8, rtol=0):
                raise RuntimeError(f"{case_id} wavelength contract mismatch")
            orders = z["orders"].tolist()

        validation = load_json(Path(artifact_records["validation"]["path"]))
        hf = hf_manifest
        if validation.get("status") != "PASS" or hf.get("status") != "PASS":
            raise RuntimeError(f"{case_id} validation/HF archive not PASS")
        if not item.get("solver_entered") or not item.get("solver_returned") or item.get("run_invocation_count") != 1 or item.get("replay"):
            raise RuntimeError(f"{case_id} entry provenance mismatch")
        ev = item.get("entry_evidence", {})
        if ev.get("entry_count") != 1 or ev.get("replay_entry_count") != 0:
            raise RuntimeError(f"{case_id} entry event count mismatch")
        pre_fsp_sha = (pre_manifest.get("pre_fsp_sha256") or pre_manifest.get("setup_fsp_sha256")
                       or ledger_obj.get("pre_fsp_sha256") or ledger_obj.get("run_fsp_sha256"))
        case_records.append({
            "case_id": case_id,
            "attempt_id": item["attempt_id"],
            "ordered_D_nm": item["ordered_D_nm"],
            "geometry_hash_sha256": item["geometry_hash_sha256"],
            "scientific_entry_count": 1,
            "solver_returned": True,
            "replay": False,
            "scientific_validation": "PASS",
            "hf_archive": "PASS",
            "state_schema": state_meta["schema_version"],
            "state_planes": state_meta["planes"],
            "state_normalization": state_meta["normalization"]["normalization"],
            "state_npz_path": str(state_npz),
            "state_npz_sha256": sha256(state_npz),
            "state_shape": shape,
            "pre_entry_fsp_sha256": pre_fsp_sha,
            "post_solver_runtime_fsp_sha256": hf.get("runtime_fsp_sha256") or hf.get("post_fsp_sha256"),
            "artifact_hashes": checked,
        })

    # Generate auxiliary features through only the read-only LF method; never call request(),
    # which also returns exact HF truth when a geometry overlaps the NP HF table.
    spec = importlib.util.spec_from_file_location("np_k6_coupling_forward_feature_interface_v1", INTERFACE_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen NP adapter")
    adapter_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter_module)
    authority = adapter_module.FrozenAuthority(NP_ROOT)
    support_by_case = {x["case_id"]: x for x in support["cases"]}
    if set(support_by_case) != set(EXPECTED_CASES):
        raise RuntimeError("support manifest case list mismatch")
    lf_rows = []
    support_records = []
    for case_id in EXPECTED_CASES:
        geom = by_case[case_id]["ordered_D_nm"]
        support_row = support_by_case[case_id]
        if support_row["ordered_D_nm"] != geom:
            raise RuntimeError(f"{case_id} support geometry mismatch")
        support_records.append({
            "case_id": case_id,
            "ordered_D_nm": geom,
            "exact_HF22_match": support_row["exact_HF22_match"],
            "normalized_nearest_HF22_distance": support_row["normalized_nearest_HF22_distance"],
            "nearest_HF22_geometry_id": support_row["nearest_HF22_geometry_id"],
            "classification": support_row["classification"],
            "training_domain_warning": support_row["training_domain_warning"],
        })
        for wavelength in WAVELENGTHS:
            lf = authority.lf_features(geom, wavelength, "P")
            lf_rows.append({
                "case_id": case_id,
                "ordered_D_nm": json.dumps(geom, separators=(",", ":")),
                "wavelength_nm": wavelength,
                "polarization": "P_XLIKE",
                "ux": 0.0,
                "ky": 0.0,
                "status": lf.get("status"),
                "reason": lf.get("reason"),
                "provenance": lf.get("provenance"),
                "feature_values_emitted": bool(lf.get("status") == "AVAILABLE"),
            })
    unavailable = sum(row["status"] == "UNAVAILABLE" and row["reason"] == "geometry_not_present_in_frozen_LF_design_space" for row in lf_rows)
    if len(lf_rows) != 220:
        raise RuntimeError(f"expected 220 paired LF requests, got {len(lf_rows)}")
    if unavailable != 220 or any(row["feature_values_emitted"] for row in lf_rows):
        raise RuntimeError("NP LF availability is mixed or unexpectedly available; do not auto-finalize blocked package")

    np_git_status = git(NP_ROOT, "status", "--short")
    coupling_git_status = git(ROOT, "status", "--short")
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "coupling_git": coupling_git,
        "np_git": np_git,
        "coupling_dirty_summary": coupling_git_status.splitlines(),
        "np_dirty_summary": np_git_status.splitlines(),
        "dataset": dataset,
        "dataset_sha256": sha256(DATASET_PATH),
        "dataset_source_hash": sha256(ROOT / dataset["source_provenance_manifest"]),
        "baseline_sha256": baseline_hash,
        "gate_sha256": sha256(GATE_PATH),
        "gate_status": gate.get("status"),
        "gate_values": H1_GATES,
        "decoder_sha256": sha256(DECODER_PATH),
        "interface_sha256": sha256(INTERFACE_PATH),
        "interface_source_sha256": sha256(INTERFACE_SOURCE),
        "provider_manifest_sha256": sha256(PROVIDER_PATH),
        "np_provenance_sha256": sha256(NP_PROVENANCE_PATH),
        "np_provenance_authority_head": np_provenance.get("authority_head"),
        "support_sha256": sha256(SUPPORT_PATH),
        "provider_manifest": provider_manifest,
        "interface_manifest": interface_manifest,
        "support_manifest": support,
        "case_records": case_records,
        "lf_rows": lf_rows,
        "support_records": support_records,
        "lf_unavailable_count": unavailable,
        "lf_row_count": len(lf_rows),
        "adapter_contract": {
            "called_method": "FrozenAuthority.lf_features(ordered_geometry, integer_wavelength_nm, 'P')",
            "called_220_times": True,
            "general_request_method_called": False,
            "coupling_truth_passed_to_adapter": False,
            "unsupported_fields_invented": False,
        },
    }


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_self_test() -> None:
    import tempfile
    ids = EXPECTED_CASES
    fold = build_fold_manifest(ids)
    assert len(fold["folds"]) == 20
    assert {f["test_geometry_id"] for f in fold["folds"]} == set(ids)
    for outer in fold["folds"]:
        train = set(outer["train_geometry_ids"])
        assert outer["test_geometry_id"] not in train and len(train) == 19
        assert len(outer["inner_group_folds"]) == 3
        for inner in outer["inner_group_folds"]:
            assert not set(inner["train_geometry_ids"]) & set(inner["validation_geometry_ids"])
            assert set(inner["train_geometry_ids"]) | set(inner["validation_geometry_ids"]) == train
    contract = make_32g_contract()
    required = {"arms_A0_A1_A2_A3_availability_rules", "feature_field_identities", "preprocessing", "geometry_split_philosophy", "paired_band_nm", "current_target_schema", "metrics", "acceptance_logic", "ood_analysis_rule"}
    assert set(contract) == required and contract["paired_band_nm"] == WAVELENGTHS
    assert lf_order_field(0) == "LF_order_vector[0]" and lf_order_field(1) == "LF_order_vector[+1]"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "empty.csv"
        write_csv(p, ["case_id", "arm"], [])
        assert p.read_text(encoding="utf-8").splitlines() == ["case_id,arm"]
    print("NP_FORWARD_FEATURE_ABLATION_PREFLIGHT_SELF_TEST_PASS")


def write_blocked_package() -> None:
    authority = collect()
    OUT_DIR.mkdir(parents=True, exist_ok=False)
    prereg = {
        "schema": "COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_PREREGISTRATION_V1",
        "study": "COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V1",
        "status": "FROZEN_BEFORE_OUTER_METRICS; ABORTED_AT_MATCHED_FEATURE_COVERAGE_GATE",
        "registered_utc": authority["created_utc"],
        "outer_fold_test_metrics_computed_before_registration": False,
        "outer_fold_test_metrics_computed_at_all": False,
        "dataset": {
            "manifest": "reports/coupling/PW_K6_20G_DATASET_FREEZE_MANIFEST_V1.json",
            "manifest_sha256": authority["dataset_sha256"],
            "source_manifest_sha256": authority["dataset_source_hash"],
            "case_ids_in_frozen_order": EXPECTED_CASES,
            "geometry_count": 20,
            "target_geometry_wavelength_rows": 220,
            "state_order_wavelength_rows": 1540,
            "paired_wavelength_nm": WAVELENGTHS,
            "polarization": "P_XLIKE only",
            "physical_contract_sha256": authority["dataset"]["physical_contract_hash"],
        },
        "target_schema": {
            "baseline_authority": "PW_K6_STRUCTURED_FORWARD_MODEL_V1",
            "baseline_freeze_report_sha256": authority["baseline_sha256"],
            "state": "PW_COMPLEX_FLOQUET_STATE_V1; integrated 3D Coupling truth; POSTNP +z; seven ordered propagating orders; TE/TM complex coordinates over 445–455 nm",
            "state_representation": "original C_PW and C_hat/P_scale factorization; seven order-local rank-2 PCA representations fit only on outer-training geometries",
            "scale": "POSTNP_TOTAL_POWER_V2 / P_scale; frozen RBF Kernel Ridge scale branch; no oracle substitution",
            "decoder": "frozen deterministic H2; source scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py",
            "decoder_sha256": authority["decoder_sha256"],
            "truth_authority": "PW_K6_GRATING_TRUTH_V2",
        },
        "geometry_grouping": {
            "statistical_unit": "complete ordered [D1,D2,D3,D4,D5,D6] geometry",
            "outer": "strict LOGO, 20 folds",
            "inner": "3-fold geometry GroupKFold within the outer training geometries",
            "all_wavelengths_of_a_geometry_stay_together": True,
            "wavelength_random_split": False,
            "geometry_sorting_or_permutation": False,
        },
        "feature_arms": {
            "A0": {"name": "COUPLING_BASELINE", "definition": "six ordered geometry dimensions only", "status": "AVAILABLE_BUT_NOT_TRAINED_BECAUSE_PAIRED_ABLATION_GATE_FAILED"},
            "A1": {"name": "NP_LF_PHYSICS", "definition": "seven LF order-vector scalars plus LF T_proxy at each paired wavelength; P_XLIKE, ux=0, ky=0", "status": "BLOCKED_NO_MATCHED_PROVIDER_VALUES", "provider_authority": "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1", "requested_rows": 220, "available_rows": 0, "unavailable_rows": authority["lf_unavailable_count"]},
            "A2": {"name": "NP_FROZEN_LEARNED_SCALAR", "status": "SKIPPED", "reason": "LEARNED_SCALAR_FEATURE_ARM_NOT_REPRODUCIBLY_AVAILABLE"},
            "A3": {"name": "NP_LF_AND_LEARNED", "status": "SKIPPED", "reason": "A1_AND_A2_NOT_BOTH_AVAILABLE"},
        },
        "preprocessing": {
            "A0_input_scaling": "D1..D6 divided by 130 nm; StandardScaler fit only on each training split",
            "A1_input_capacity_match_if_enabled_in_future": "concatenate six ordered geometry values and 88 LF values; training-fold StandardScaler then training-fold PCA to six inputs before the same width-32 model; no test fold fit",
            "state_pca": "seven order-specific rank-2 PCA transformations fit using training geometries only",
            "P_scale_model": "RBF Kernel Ridge; train-fold X/y StandardScaler; alpha {0.1,1,10}, gamma {0.1,1}; grouped inner selection",
            "support_metadata_as_model_input": False,
        },
        "model_selection": {
            "state_model": "frozen PW_K6_STRUCTURED_FORWARD_MODEL_V1; shared Linear(6,32)-ReLU-Linear(32,32)-ReLU encoder; seven Linear(32,2) order heads; 14→32→14 residual fusion",
            "trainable_parameters": 2684,
            "optimizer": "AdamW",
            "learning_rate": 0.002,
            "weight_decay": 0.0001,
            "gradient_clip_norm": 5.0,
            "maximum_epochs": 320,
            "early_stopping_patience": 45,
            "early_stopping_objective": "normalized MSE on geometry-held inner validation fold",
            "seeds": [0, 1, 2],
            "prediction_aggregation": "mean of the three fixed-seed predictions; no post-hoc seed selection",
        },
        "primary_metrics": ["state-relative RMSE", "routing eta RMSE and Pearson", "absolute-order source-normalized error", "thresholded meaningful-power relative error", "P_scale relative error and Pearson", "per-geometry paired deltas", "win/tie/loss", "median/q95/worst", "seed state-median std"],
        "h1_gate_authority": {"source": "PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json", "source_sha256": authority["gate_sha256"], "gates": H1_GATES, "production_admission_is_separate": True},
        "comparative_acceptance_logic": make_32g_contract()["acceptance_logic"],
        "ood_stratification": "stable sort by normalized nearest HF22 distance then case_id; 7/7/6 nearest/middle/farthest; diagnostics only",
        "feature_coverage_gate": {
            "NP_interface": "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1",
            "interface_manifest_sha256": authority["interface_sha256"],
            "adapter_sha256": authority["interface_source_sha256"],
            "method": authority["adapter_contract"]["called_method"],
            "availability": "0/220 rows; all return UNAVAILABLE / geometry_not_present_in_frozen_LF_design_space",
            "rule": "no sorting, interpolation, synthetic LF extrapolation, HF truth substitution, or missing-value imputation; stop before training",
        },
    }
    # Freeze preregistration before writing any result-like files. This run computes no test metrics.
    prereg_path = OUT_DIR / "preregistration.json"
    write_json(prereg_path, prereg)
    (OUT_DIR / "preregistration.sha256").write_text(sha256(prereg_path) + "  preregistration.json\n", encoding="ascii")

    dataset_authority = {
        "schema": "COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_DATASET_AUTHORITY_V1",
        "status": "PASS_INTEGRATED_LABELS; NP_FEATURE_COVERAGE_BLOCKED",
        "coupling_git": authority["coupling_git"],
        "np_git": authority["np_git"],
        "np_interface_provenance_authority_head": authority["np_provenance_authority_head"],
        "dataset_freeze_manifest": {"path": str(DATASET_PATH.relative_to(ROOT)), "sha256": authority["dataset_sha256"], "status": authority["dataset"]["status"], "physical_contract_sha256": authority["dataset"]["physical_contract_hash"], "scientific_entry_total": authority["dataset"]["scientific_entry_total"], "duplicate_scientific_entry_count": authority["dataset"]["duplicate_scientific_entry_count"], "replay_count": authority["dataset"]["replay_count"]},
        "source_provenance_manifest_sha256": authority["dataset_source_hash"],
        "included_geometry_count": 20,
        "target_geometry_wavelength_rows": 220,
        "target_order_wavelength_rows": 1540,
        "wavelength_grid_full_nm": list(range(440, 461)),
        "paired_wavelength_grid_nm": WAVELENGTHS,
        "polarization": "P_XLIKE only",
        "target_schema": prereg["target_schema"],
        "cases": authority["case_records"],
        "excluded_expansion_cases": authority["dataset"].get("extension_cases", []),
        "exclusion_rule": "Only cases selected as SCIENTIFIC_VALID in the frozen 20G authority with directly verified case-local validation, HF archive, state metadata/NPZ, raw/projection/order truth and FSP/H5 are included; no newer 12G expansion is assumed valid.",
        "model_authorities": {
            "baseline_report_sha256": authority["baseline_sha256"],
            "h1_gate_authority_sha256": authority["gate_sha256"],
            "h1_gate_values": H1_GATES,
            "h2_decoder_sha256": authority["decoder_sha256"],
        },
        "np_interface_authorities": {
            "provider_manifest_sha256": authority["provider_manifest_sha256"],
            "interface_manifest_sha256": authority["interface_sha256"],
            "adapter_source_sha256": authority["interface_source_sha256"],
            "provenance_sha256": authority["np_provenance_sha256"],
            "support_manifest_sha256": authority["support_sha256"],
            "authority_head": authority["np_provenance_authority_head"],
        },
        "no_solver": True,
        "no_shared_v3_control_access": True,
    }
    write_json(OUT_DIR / "dataset_authority.json", dataset_authority)
    write_json(OUT_DIR / "fold_manifest.json", build_fold_manifest(EXPECTED_CASES))
    feature_manifest = {
        "schema": "COUPLING_ML_NP_FORWARD_FEATURE_MANIFEST_V1",
        "paired_rows": 220,
        "arms": {
            "A0": {"name": "COUPLING_BASELINE", "fields": [f"D{i}_nm" for i in range(1, 7)], "status": "AVAILABLE_NOT_RUN"},
            "A1": {"name": "NP_LF_PHYSICS", "provider": "FROZEN_D0_FULL_VECTOR_ARRAY_AUTHORITY", "fields_per_wavelength": [lf_order_field(m) for m in range(-3, 4)] + ["LF_T_proxy=sum(m=-1,0,+1)"], "wavelengths_nm": WAVELENGTHS, "polarization": "P_XLIKE", "ux": 0.0, "ky": 0.0, "status": "BLOCKED", "available_rows": 0, "unavailable_rows": 220, "reason": "geometry_not_present_in_frozen_LF_design_space"},
            "A2": {"status": "SKIPPED", "reason": "LEARNED_SCALAR_FEATURE_ARM_NOT_REPRODUCIBLY_AVAILABLE"},
            "A3": {"status": "SKIPPED", "reason": "A1_AND_A2_NOT_BOTH_AVAILABLE"},
        },
        "support_metadata_used_as_feature": False,
        "feature_generation": authority["adapter_contract"],
    }
    write_json(OUT_DIR / "feature_manifest.json", feature_manifest)
    write_csv(OUT_DIR / "np_lf_features.csv", ["case_id", "ordered_D_nm", "wavelength_nm", "polarization", "ux", "ky", "status", "reason", "provenance", "feature_values_emitted"], authority["lf_rows"])
    write_csv(OUT_DIR / "oof_predictions.csv", ["case_id", "outer_fold", "arm", "wavelength_nm", "order_m", "target_name", "prediction", "truth"], [])
    write_csv(OUT_DIR / "per_geometry_metrics.csv", ["case_id", "arm", "state_relative_rmse", "routing_eta_rmse", "routing_pearson", "absolute_order_source_normalized_rmse", "thresholded_order_relative_error", "P_scale_relative_error", "P_scale_pearson", "status"], [])
    write_json(OUT_DIR / "paired_ablation_metrics.json", {
        "schema": "COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_METRICS_V1",
        "status": "NOT_COMPUTED_BLOCKED_AT_MATCHED_FEATURE_COVERAGE_GATE",
        "outer_fold_test_metrics_computed": False,
        "A0": {"status": "NOT_RUN", "reason": "No legal A1 values; no unpaired A0 scores are reported in this paired ablation package."},
        "A1": {"status": "BLOCKED", "available_rows": 0, "requested_rows": 220},
        "A2": {"status": "SKIPPED", "reason": "LEARNED_SCALAR_FEATURE_ARM_NOT_REPRODUCIBLY_AVAILABLE"},
        "A3": {"status": "SKIPPED", "reason": "A1_AND_A2_NOT_BOTH_AVAILABLE"},
        "paired_geometry_deltas": None,
        "win_tie_loss": None,
    })
    support_records = authority["support_records"]
    ordered = sorted(support_records, key=lambda x: (x["normalized_nearest_HF22_distance"], x["case_id"]))
    strata = {"nearest": ordered[:7], "middle": ordered[7:14], "farthest": ordered[14:]}
    write_json(OUT_DIR / "ood_support_analysis.json", {
        "schema": "COUPLING_ML_NP_FORWARD_FEATURE_OOD_SUPPORT_V1",
        "support_manifest_sha256": authority["support_sha256"],
        "exact_HF22_overlap_count": sum(bool(x["exact_HF22_match"]) for x in support_records),
        "extrapolative_count": sum(x["classification"] == "extrapolation" for x in support_records),
        "stratification": "stable sort by (normalized_nearest_HF22_distance, case_id), 7/7/6",
        "strata": {k: [{"case_id": x["case_id"], "distance": x["normalized_nearest_HF22_distance"]} for x in v] for k, v in strata.items()},
        "diagnostic_only_not_model_input": True,
        "prediction_error_by_stratum": None,
    })
    write_json(OUT_DIR / "leakage_audit.json", {
        "schema": "COUPLING_ML_NP_FORWARD_FEATURE_LEAKAGE_AUDIT_V1",
        "status": "PASS_FOR_COVERAGE_AUDIT; NO_MODEL_FIT_OR_TEST_METRICS",
        "np_feature_generator_called": "FrozenAuthority.lf_features only",
        "np_generator_received_coupling_hf_labels": False,
        "heldout_coupling_targets_used_to_generate_np_features": False,
        "coupling_targets_read": "integrity/schema/hash validation only; not passed to NP adapter and not used for training or metric computation",
        "all_preprocessing_fold_fitted": "specified in preregistration; none executed because blocked",
        "compared_arms_identical_test_rows": "frozen LOGO fold manifest specifies matched case rows; no arms scored",
        "wavelength_leakage": False,
        "repeated_geometry_leakage": False,
        "final_dipole_or_sealed_validation_access": False,
        "support_distance_used_as_model_feature": False,
        "support_distance_use": "diagnostic strata only",
        "shared_v3_sqlite_or_control_access": False,
        "solver_or_gpu_entry": False,
    })
    verdict = {
        "primary_verdict": "COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_BLOCKED",
        "reason": "The frozen NP LF adapter returned UNAVAILABLE / geometry_not_present_in_frozen_LF_design_space for all 220 matched P_XLIKE × 445–455 nm rows; no sanctioned sorting, interpolation, extrapolation, or imputation exists.",
        "labels": "PASS: 20 integrated 3D PW cases are directly verified in the frozen dataset authority.",
        "A1": "BLOCKED: 0/220 matched LF values available.",
        "A2": "SKIPPED: LEARNED_SCALAR_FEATURE_ARM_NOT_REPRODUCIBLY_AVAILABLE.",
        "A3": "SKIPPED: A1 and A2 are not both available.",
        "A0": "NOT_RUN: paired comparison cannot be formed; no unpaired baseline test errors computed.",
        "production_H1": "No new H1 evaluation; production admission remains separate and unchanged.",
        "next": "Obtain a formally frozen NP LF provider that covers the exact ordered Coupling geometries (or a revised interface authority) and rerun this preregistered protocol; no sorting or synthetic extrapolation.",
    }
    write_json(OUT_DIR / "verdict.json", verdict)
    write_json(OUT_DIR / "NP_FEATURE_ABLATION_CONFIRMATORY_CONTRACT_V1.json", make_32g_contract())

    report = f"""# COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V1

## Status

**BLOCKED at the matched-feature coverage gate; no model was trained and no outer-fold test metric was computed.** This is not a solver failure and does not alter the Coupling scientific truth or H1 admission.

## Authority and matched labels

- Coupling: `{authority['coupling_git']['branch']}` at `{authority['coupling_git']['head']}`; upstream divergence `{authority['coupling_git']['upstream_divergence_left_right']}`.
- Frozen 20G manifest SHA256: `{authority['dataset_sha256']}`; status PASS; 20 selected cases, 20 scientific entries, zero duplicate entries, zero replay entries.
- All 20 selected cases have direct case-local `scientific_validation.json=PASS`, `HF_ARCHIVE_MANIFEST.json=PASS`, ledger entry/return evidence, canonical state JSON+NPZ with matching SHA, and existing FSP/H5 artifacts. The authoritative state schema is `PW_COMPLEX_FLOQUET_STATE_V1` with 3 planes × 21 wavelengths × 81 orders × 2 directions × 2 polarizations; the paired band contains 220 geometry-wavelength rows and 1,540 order-wavelength rows.
- The 20G manifest's `fsp.sha256` records the pre-entry/setup FSP digest (verified against the applicable pre-entry/setup manifest or attempt ledger); the saved post-solver FSP has a different digest, independently matching the archived V2 `runtime_fsp_sha256` or legacy `post_fsp_sha256`. S16's pre-entry sidecar is explicitly absent in the frozen manifest, so its ledger supplies the entry hash; its archived post-FSP hash and path verify. State sidecar hash fields refer to the paired NPZ payload; both links were verified. No hash mismatch was waived.
- Paired domain is exactly 445–455 nm at 1 nm spacing, P/XLIKE only. The 12G expansion is not substituted for the frozen 20G authority.
- Frozen baseline report SHA256 `{authority['baseline_sha256']}` identifies `PW_K6_STRUCTURED_FORWARD_MODEL_V1` (width 32, 2,684 parameters); H1 gate source SHA256 `{authority['gate_sha256']}`. H2 decoder source SHA256 `{authority['decoder_sha256']}`.

## NP interface coverage

- NP worktree: `{authority['np_git']['branch']}` at `{authority['np_git']['head']}`; the frozen interface provenance records authority HEAD `{authority['np_provenance_authority_head']}`.
- Interface: `NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1`; adapter SHA256 `{authority['interface_source_sha256']}`, interface manifest SHA256 `{authority['interface_sha256']}`.
- The allowed A1 fields are the frozen LF order vector m=−3…+3 and `T_proxy=sum(m=−1,0,+1)`, queried only through `FrozenAuthority.lf_features(ordered geometry, wavelength, P)`. All 20 Coupling geometries are absent from the frozen LF geometry master; all **220/220** requests returned `UNAVAILABLE / geometry_not_present_in_frozen_LF_design_space`.
- The support manifest independently reports exact HF22 overlap 0/20 and all 20 extrapolative. It was used for diagnostics only. Geometry sorting, permutation, interpolation, hand-filled LF values, HF truth substitution, and support metadata as model inputs were not used.
- A2 skipped: `LEARNED_SCALAR_FEATURE_ARM_NOT_REPRODUCIBLY_AVAILABLE`. A3 skipped because A1 and A2 are not both available.

## Preregistration and scores

`preregistration.json` was frozen before any outer-fold score calculation. The 20-fold LOGO/3-fold grouped inner split manifest was generated, but no fitting or scoring was started because A1 had zero matched values. A0 is marked NOT_RUN in this paired package; no unpaired baseline errors are presented. OOF and per-geometry CSV files contain headers only. See `paired_ablation_metrics.json` for explicit null/not-computed status.

## H1 and scientific boundary

The frozen conjunctive H1 numerical gates remain unchanged. No new H1 score was computed; NP auxiliary-feature utility is not equivalent to production admission. No complex cascade, Jones matrix, or MDC+spacer+NP composition was constructed.

## Leakage and execution

The LF adapter received only ordered geometry, wavelength, and P polarization; it was called through `lf_features`, not the general request path. Coupling state artifacts were integrity/schema checked only and never passed to the NP feature generator or an ML fit. Fold IDs keep complete geometries together. No solver, GPU entry, Shared V3 control/SQLite, final dipole data, or sealed validation was accessed.

## Outcome

`COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_BLOCKED`. The matching Coupling labels exist; the frozen NP provider does not cover their exact ordered geometry domain. Resume only after a formal NP provider/interface authority supplies exact values for all matched rows without sorting or synthetic extrapolation. The 32G confirmatory contract is frozen at `NP_FEATURE_ABLATION_CONFIRMATORY_CONTRACT_V1.json` and must not be tuned from this 20G result.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")

    # Inventory generated evidence after preregistration and non-score artifacts are written.
    generated = {}
    for p in sorted(OUT_DIR.iterdir()):
        if p.is_file(): generated[p.name] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    generated[REPORT_PATH.name] = {"path": str(REPORT_PATH.relative_to(ROOT)), "bytes": REPORT_PATH.stat().st_size, "sha256": sha256(REPORT_PATH)}
    generated[Path(__file__).name] = {"path": str(Path(__file__).relative_to(ROOT)), "bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}
    write_json(OUT_DIR / "artifact_hashes.json", generated)
    print("STATUS COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_BLOCKED")
    print("VALID_GEOMETRIES 20")
    print("PAIRED_ROWS 220")
    print("NP_LF_AVAILABLE 0/220")
    print("OOF_TEST_METRICS 0")
    print("PACKAGE", OUT_DIR)
    print("REPORT", REPORT_PATH)


def verify_package() -> None:
    if not OUT_DIR.is_dir() or not REPORT_PATH.is_file():
        raise FileNotFoundError("blocked package not found")
    expected_verdict = load_json(OUT_DIR / "verdict.json")
    if expected_verdict["primary_verdict"] != "COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_BLOCKED":
        raise AssertionError("verdict mismatch")
    prereg = load_json(OUT_DIR / "preregistration.json")
    if prereg["outer_fold_test_metrics_computed_at_all"] is not False:
        raise AssertionError("unexpected metric-computation flag")
    fold = load_json(OUT_DIR / "fold_manifest.json")
    if fold["metrics_computed"] or len(fold["folds"]) != 20:
        raise AssertionError("fold manifest mismatch")
    features = load_json(OUT_DIR / "feature_manifest.json")
    if features["arms"]["A1"]["available_rows"] != 0 or features["arms"]["A1"]["unavailable_rows"] != 220:
        raise AssertionError("feature availability mismatch")
    with (OUT_DIR / "np_lf_features.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 220 or any(r["status"] != "UNAVAILABLE" or r["feature_values_emitted"] != "False" for r in rows):
        raise AssertionError("LF audit rows mismatch")
    with (OUT_DIR / "oof_predictions.csv").open(newline="", encoding="utf-8") as f:
        if list(csv.DictReader(f)):
            raise AssertionError("unexpected OOF predictions")
    print("NP_FORWARD_FEATURE_ABLATION_BLOCKED_PACKAGE_VERIFY_PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--write-blocked-package", action="store_true")
    group.add_argument("--verify-package", action="store_true")
    args = ap.parse_args()
    if args.self_test: run_self_test()
    elif args.write_blocked_package: write_blocked_package()
    else: verify_package()


if __name__ == "__main__":
    main()
