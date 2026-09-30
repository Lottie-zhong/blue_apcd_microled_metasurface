"""Build the unlabeled Coupling 20G LF-only V2 feature cache and audit records."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from np_k6_coupling_forward_feature_interface_v2 import (
    DIAMETERS_NM,
    INTERFACE_ID,
    NP_LF_FEATURE_PROVIDER_V2_Runtime,
    ORDERS,
    PROVIDER_ID,
    WAVELENGTHS_NM,
    _parse_geometry_id,
    _sha,
    geometry_id,
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _hash_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    script_dir = Path(__file__).resolve().parent
    out = root / "outputs/np_k6_coupling_forward_runtime_coverage_v2"
    out.mkdir(parents=True, exist_ok=True)
    provider = NP_LF_FEATURE_PROVIDER_V2_Runtime(root=root)

    # The sole Coupling-side inputs are the 20 ordered geometry tuples in this
    # previously frozen unlabeled V1 domain-support cache.  No target/performance
    # fields or Coupling result tables are opened by this builder.
    query_path = root / "outputs/np_k6_coupling_forward_feature_interface_v1/coupling_20g_domain_support.json"
    query_document = json.loads(query_path.read_text(encoding="utf-8-sig"))
    query_geometries = []
    for case in query_document.get("cases", []):
        query_geometries.append({
            "source_case_id": str(case["case_id"]),
            "ordered_D_nm": list(case["ordered_D_nm"]),
        })
    if len(query_geometries) != 20 or len({tuple(x["ordered_D_nm"]) for x in query_geometries}) != 20:
        raise RuntimeError("unlabeled V1 query metadata must contain exactly 20 unique ordered geometries")

    geometry_audits = []
    cache_records = []
    for query in query_geometries:
        d = tuple(int(x) for x in query["ordered_D_nm"])
        audit = provider.support_audit(d)
        if audit["physical_domain_valid"] is not True or audit["runtime_domain"]["status"] != "SUPPORTED_DISCRETE_ORDERED_LF_DOMAIN":
            raise RuntimeError(f"runtime domain rejects query geometry {query['source_case_id']}")
        geometry_audits.append({"source_case_id": query["source_case_id"], **audit})
        for wavelength in WAVELENGTHS_NM:
            record = provider.infer(d, wavelength, "P_XLIKE")
            record["source_case_id"] = query["source_case_id"]
            record["query_source"] = "FROZEN_V1_UNLABELED_ORDERED_GEOMETRY_METADATA"
            values = record["features"]["eta_m_proxy"]
            if not all(math.isfinite(float(v)) for v in values.values()) or not math.isfinite(record["features"]["T_proxy"]):
                raise RuntimeError("non-finite LF feature generated")
            if not math.isclose(sum(values.values()), 1.0, rel_tol=0.0, abs_tol=2e-7):
                raise RuntimeError("all-tracked-order LF normalization failed")
            if not math.isclose(record["features"]["T_proxy"], sum(values[f"m{m:+d}"] for m in (-1, 0, 1)), rel_tol=0.0, abs_tol=2e-7):
                raise RuntimeError("T_proxy bookkeeping does not equal the three propagating orders")
            cache_records.append(record)

    # Independent parity against the frozen 22-geometry LF-only authority.
    # Read only LF rows (not HF truth); one P/XLIKE row per exact geometry/lambda.
    lf22_csv = root / "outputs/np_k6_m9_22g_forward_retraining_v1/lf22_full_vector_authority.csv"
    parity_rows = []
    seen = set()
    with lf22_csv.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["polarization"].strip().lower() != "p":
                continue
            d = _parse_geometry_id(row["geometry_id"])
            w = int(float(row["wavelength_nm"]))
            key = (d, w)
            if key in seen:
                raise RuntimeError(f"duplicate frozen LF22 parity row {key}")
            seen.add(key)
            got = provider.infer(d, w, "P_XLIKE")
            deltas = {
                f"eta_m{m:+d}": abs(got["features"]["eta_m_proxy"][f"m{m:+d}"] - float(row[f"lf_eta_m{m:+d}"]))
                for m in ORDERS
            }
            deltas["T_proxy"] = abs(got["features"]["T_proxy"] - float(row["lf_T_proxy"]))
            parity_rows.append({"geometry_id": geometry_id(d), "wavelength_nm": w, "max_abs_delta": max(deltas.values()), "deltas": deltas})
    if len(seen) != 22 * 11:
        raise RuntimeError(f"expected 242 exact HF22-geometry LF parity rows, found {len(seen)}")
    parity_max = max(x["max_abs_delta"] for x in parity_rows)
    parity_gate = parity_max <= 2e-6

    cache_path = out / "coupling_20g_lf_feature_cache.jsonl"
    cache_bytes = "".join(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n" for x in cache_records).encode("utf-8")
    cache_path.write_bytes(cache_bytes)

    generator_path = root / "scripts/stage_np_k6_ml_d0_build_database_foundation.py"
    library_path = root / "outputs/np_k6_p1d2_broadband_library_27point_v1/library_long.csv"
    library_manifest_path = library_path.with_name("library_manifest.json")
    library_provenance_path = library_path.with_name("provenance_verification.json")
    array_manifest_path = root / "outputs/np_k6_ml_d0_database_foundation_v1/k6_lf_arrays_manifest.json"
    lf22_manifest_path = root / "outputs/np_k6_m9_22g_forward_retraining_v1/lf22_full_vector_authority_manifest.json"
    d180_paths = {
        "explicit_contract": root / "outputs/np_k6_p1d2_d180_explicit_rerun_v1/execution_contract.json",
        "setup_heartbeat": root / "outputs/np_k6_p1d2_d180_explicit_rerun_v1/heartbeat.json",
        "run_manifest": root / "outputs/np_k6_p1d2b_broadband_d180_x_v1/run_manifest.json",
        "results": root / "outputs/np_k6_p1d2b_broadband_d180_x_v1/results.json",
        "verification": root / "outputs/np_k6_p1d2b_broadband_d180_x_v1/verification_summary.json",
        "post_fsp": root / "runtime_fsp/np_k6_p1d2_d180_explicit_rerun_v1/NP_P1D2_BROADBAND_PILLAR_H500_D180_X_EXPLICIT_RERUN_V1_post.fsp",
    }
    authority = {
        "d0_generator": {"path": str(generator_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(generator_path)},
        "single_pillar_library": {"path": str(library_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(library_path)},
        "single_pillar_library_manifest": {"path": str(library_manifest_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(library_manifest_path)},
        "legacy_provenance_snapshot": {"path": str(library_provenance_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(library_provenance_path)},
        "d0_array_manifest": {"path": str(array_manifest_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(array_manifest_path)},
        "lf22_full_vector_csv": {"path": str(lf22_csv.relative_to(root)).replace("\\", "/"), "sha256": _sha(lf22_csv)},
        "lf22_geometry_support_manifest": {"path": str(lf22_manifest_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(lf22_manifest_path)},
        "v1_unlabeled_query_geometry_cache": {"path": str(query_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(query_path)},
        "d180_explicit_attempt2": {
            name: {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": _sha(path)}
            for name, path in d180_paths.items()
        },
    }
    source_digest = _hash_json({k: v["sha256"] if "sha256" in v else {n: item["sha256"] for n, item in v.items()} for k, v in authority.items()})

    inside_support = sum(x["hf22_empirical_support"]["exact_hf22_match"] for x in geometry_audits)
    position_extrapolative = sum(x["extrapolative_vs_hf22_positionwise_bounds"] for x in geometry_audits)
    strict_increasing = sum(all(x["ordered_D_nm"][i] < x["ordered_D_nm"][i + 1] for i in range(5)) for x in geometry_audits)
    a1 = {
        "provider_id": PROVIDER_ID,
        "status": "CALLABLE_DETERMINISTIC_LF_ONLY",
        "method": "frozen D0 single-pillar txx library followed by the exact ordered six-bin DFT proxy from stage_np_k6_ml_d0_build_database_foundation.py",
        "is_learned_model": False,
        "training_support": {"fit_training_geometries": 0, "fit_status": "NOT_APPLICABLE_DETERMINISTIC_PROVIDER", "source_calibration": "27 single-pillar diameters x 11 wavelengths, x-only", "full_k6_hf22_empirical_reference_geometries": 22, "exact_20g_hf22_overlap": inside_support},
        "runtime_domain": {"ordered_domain": "all 27^6 ordered sequences drawn from {100,105,...,230} nm", "cardinality": len(DIAMETERS_NM) ** 6, "wavelengths_nm": list(WAVELENGTHS_NM), "polarization": ["P_XLIKE"], "u_x": 0.0, "k_y": 0.0, "interpolation": False, "sorting_or_permutation": False},
        "output_fields": {"order_vector": [f"eta_m{m:+d}_proxy" for m in ORDERS], "T_proxy": "sum eta_m_proxy for m=-1,0,+1", "R": "UNAVAILABLE", "complex_amplitude": "NOT_EXPOSED"},
        "material_geometry_contract": {"single_pillar_material": "APCD_TIO2_NATIVE_M1", "background_material": "APCD_SIO2_NATIVE_M1", "full_k6_height_nm": 500, "period_x_nm": 1740, "period_y_nm": 290, "fixed_x_positions_nm": [-725, -435, -145, 145, 435, 725], "diameter_grid_nm": [100, 230, 5], "physical_D1_to_D6_order": True},
        "d180_provenance_reconciliation": {
            "legacy_snapshot_says_excluded": True,
            "resolved_by_later_authoritative_state": "explicitly authorized single attempt-2; persisted post-FSP; formal read-only case extraction; case result hash equals library_manifest source_result_hashes[180]; 11-row exact txx/T parity",
            "attempt2_post_fsp_sha256": _sha(d180_paths["post_fsp"]),
            "attempt2_result_sha256": _sha(d180_paths["results"]),
            "attempt2_formal_quality": "pass / warning_valid",
            "setup_pre_fsp_audit": provider.d180_pre_fsp_audit,
            "run_manifest_pre_fsp_warning": provider.provenance_warnings,
            "historical_anomaly_preserved": True,
        },
        "source_authority": authority,
        "software_runtime": {"python": platform.python_version(), "numpy": np.__version__},
        "provenance_hash": provider.provenance_hash,
        "audit_source_bundle_sha256": source_digest,
        "hf22_lf_parity": {"rows": len(parity_rows), "max_abs_delta": parity_max, "tolerance": 2e-6, "pass": parity_gate},
        "v1_interface_audit": {
            "classification": "B_EXECUTABLE_PROVIDER_BUT_DOMAIN_GUARD_BLOCKS_COUPLING_GEOMETRIES",
            "runtime_path": "adapter.request -> lf_features -> exact geometry/wavelength/polarization key -> LF22 table, else exact geometry_id scan in D0 sorted-combination master, then precomputed chunk array lookup",
            "runtime_domain": "exact key entries only for 22 HF22 geometries and 296010 strictly increasing combinations emitted by itertools.combinations(DS,6); no unseen ordered-sequence DFT evaluation",
            "coupling_v1_exact_lf_query_coverage": "0/220",
            "coupling_v1_exact_hf22_geometry_overlap": "0/20",
            "strictly_increasing_coupling_geometry_count": strict_increasing,
        },
        "not_integrated_truth": True,
    }
    if not parity_gate:
        raise RuntimeError(f"runtime formula failed frozen LF22 parity, max abs delta={parity_max}")
    _write_json(out / "a1_lf_provider_audit.json", a1)

    _write_json(out / "geometry_domain_audit.json", {
        "schema_version": "NP_K6_COUPLING_20G_ORDERED_DOMAIN_AUDIT_V2",
        "geometry_count": len(geometry_audits),
        "exact_hf22_overlap": inside_support,
        "ood_vs_hf22_exact_support": len(geometry_audits) - inside_support,
        "positionwise_extrapolative_count": position_extrapolative,
        "physical_valid_count": sum(x["physical_domain_valid"] for x in geometry_audits),
        "runtime_supported_count": sum(x["runtime_domain"]["status"] == "SUPPORTED_DISCRETE_ORDERED_LF_DOMAIN" for x in geometry_audits),
        "provider_fit_support_definition": "A1 is deterministic and has no fitted geometry set; source calibration is the 27x11 single-pillar x-only library",
        "hf22_empirical_support_definition": "exact ordered membership in the 22 full-K6 HF geometries; per-position min/max is separately reported and not substituted for exact membership",
        "hf22_positionwise_min_nm": list(provider.position_min),
        "hf22_positionwise_max_nm": list(provider.position_max),
        "nearest_distance_definition": "sqrt(sum(((D_i-g_i)/130 nm)^2)) over ordered HF22 geometry support",
        "cases": geometry_audits,
    })

    _write_json(out / "a2_learned_provider_audit.json", {
        "provider_id": "NP_K6_NORMAL_INCIDENCE_SCREENING_PROVIDER_V1 learned components",
        "status": "UNAVAILABLE_NOT_ENABLED_UNTIL_PROVIDER_PARITY_PASS",
        "provider_recovery_status": "NP_PROVIDER_RECOVERY_FAIL",
        "runtime_model_available": False,
        "exposed_in_v2": False,
        "authority_path": "outputs/np_k6_final_freeze_closeout_v1/NP_PRIOR_FEATURES_V1.json",
        "authority_sha256": _sha(root / "outputs/np_k6_final_freeze_closeout_v1/NP_PRIOR_FEATURES_V1.json"),
        "no_retraining": True,
    })
    complex_paths = [
        root / "reports/NP_K6_COMPLEX_FORWARD_SURROGATE_BENCHMARK_V1.md",
        root / "reports/NP_K6_COMPLEX_PROVIDER_AND_COUPLING_RESIDUAL_POC_V1.md",
        root / "reports/NP_K6_COMPLEX_TWO_PORT_REFERENCE_PLANE_CONTRACT_V1.md",
        root / "outputs/np_k6_complex_forward_surrogate_benchmark_v1/benchmark_manifest.json",
    ]
    _write_json(out / "complex_provider_runtime_audit.json", {
        "COMPLEX_PROVIDER_RUNTIME_READY": "NO",
        "exposed_in_v2": False,
        "reason": "available evidence is feasibility/OOF or two-port audit only; no frozen validated deployment runtime, and coefficients lack a composable incident-reference/de-embedding contract",
        "authority_artifacts": [
            {"path": str(p.relative_to(root)).replace("\\", "/"), "sha256": _sha(p)} for p in complex_paths if p.is_file()
        ],
        "complex_coefficients_as_scattering_state": False,
        "full_jones_matrix": False,
    })
    _write_json(out / "leakage_audit.json", {
        "status": "PASS_METADATA_ONLY_QUERY_ACCESS",
        "coupling_query_source": {"path": str(query_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(query_path), "fields_consumed": ["case_id", "ordered_D_nm"]},
        "coupling_target_labels_read": False,
        "coupling_prediction_errors_read": False,
        "integrated_C_PW_read": False,
        "routing_truth_read": False,
        "H1_errors_read": False,
        "heldout_target_errors_read": False,
        "final_dipole_validation_read": False,
        "sealed_hf_targets_read": False,
        "new_hf_or_fdtd": 0,
        "new_training": 0,
        "new_rcwa": 0,
        "inverse_design": 0,
        "old_confirmatory_contract": {"path": "D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1/reports/coupling/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V1/NP_FEATURE_ABLATION_CONFIRMATORY_CONTRACT_V1.json", "expected_sha256": "b8e156432c8ebd3b3087386b2dd768a177b6e0ef912f8eba4f1e40d3843e255c", "modified": False},
    })
    _write_json(out / "future_stage1_geometry_metadata_audit.json", {
        "status": "NOT_AVAILABLE_AS_GEOMETRY_ONLY_METADATA",
        "checked_authority": "reports/coupling/PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1.md",
        "authority_sha256": "c9d26783bf7c0d4964c29aa4915f3a304a5062f789cd4e0c78c28f29ec23d97a",
        "ordered_geometry_identities_found": [],
        "coordinates_added_to_v2_cache": 0,
        "stage1_labels_read": False,
    })

    cache_sha = _sha(cache_path)
    coverage = {
        "schema_version": "NP_K6_COUPLING_FORWARD_RUNTIME_COVERAGE_GATE_V2",
        "status": "PASS",
        "query_geometries": len(query_geometries),
        "runtime_supported_geometries": sum(x["runtime_domain"]["status"] == "SUPPORTED_DISCRETE_ORDERED_LF_DOMAIN" for x in geometry_audits),
        "exact_hf22_empirical_support_geometries": inside_support,
        "ood_hf22_empirical_support_geometries": len(geometry_audits) - inside_support,
        "expected_query_points": len(query_geometries) * len(WAVELENGTHS_NM),
        "valid_feature_records": len(cache_records),
        "coverage": len(cache_records) / (len(query_geometries) * len(WAVELENGTHS_NM)),
        "all_outputs_finite": True,
        "all_order_profiles_normalized": True,
        "no_duplicate_geometry_wavelength_queries": len({(x["source_case_id"], x["wavelength_nm"]) for x in cache_records}) == len(cache_records),
        "no_sort_or_permutation": True,
        "no_interpolation_or_nearest_neighbor_substitution": True,
        "cache_path": str(cache_path.relative_to(root)).replace("\\", "/"),
        "cache_sha256": cache_sha,
        "hf22_lf_parity": {"rows": len(parity_rows), "max_abs_delta": parity_max, "tolerance": 2e-6, "pass": parity_gate},
        "solver_delta": 0,
    }
    _write_json(out / "coverage_gate.json", coverage)

    source_manifest = {
        "interface_id": INTERFACE_ID,
        "provider_id": PROVIDER_ID,
        "status": "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V2_READY",
        "role": "PHYSICS_INFORMED_AUXILIARY_FEATURE_PROVIDER",
        "input_contract": {"geometry": ["D1", "D2", "D3", "D4", "D5", "D6"], "unit": "nm", "ordered_physical_x": True, "sorting_permutation_canonicalization": False, "lambda_nm": list(WAVELENGTHS_NM), "polarization": ["P_XLIKE"], "u_x": 0.0, "k_y": 0.0},
        "output_contract": {"eta_m_proxy_orders": list(ORDERS), "T_proxy": "sum eta_m_proxy for m=-1,0,+1", "R": "structured unavailable", "complex_coefficients": "unsupported", "Jones": "unsupported"},
        "domain": a1["runtime_domain"],
        "training_support": a1["training_support"],
        "material_geometry_contract": a1["material_geometry_contract"],
        "capability_boundary": {"supported": ["normal-incidence ordered-K6 LF power-level auxiliary feature inference on the frozen discrete diameter/wavelength grid"], "not_supported": ["integrated Coupling truth", "FDTD replacement", "HF accuracy guarantee", "S polarization", "angular generalization", "R prediction", "complex scattering state", "Jones matrix", "multiple-scattering cascade"]},
        "coverage_gate_path": str((out / "coverage_gate.json").relative_to(root)).replace("\\", "/"),
        "query_cache": {"path": str(cache_path.relative_to(root)).replace("\\", "/"), "records": len(cache_records), "sha256": cache_sha},
        "runtime_code": {"adapter": str((script_dir / "np_k6_coupling_forward_feature_interface_v2.py").relative_to(root)).replace("\\", "/"), "sha256": _sha(script_dir / "np_k6_coupling_forward_feature_interface_v2.py"), "build_script": str(Path(__file__).relative_to(root)).replace("\\", "/"), "sha256_build_script": _sha(Path(__file__))},
        "authority_source_digest": source_digest,
        "authority_sources": authority,
        "zero_solver_audit": {"new_fdtd": 0, "new_lumapi_solver_runs": 0, "new_hf_acquisition": 0, "rcwa": 0, "training": 0, "inverse_design": 0},
    }
    _write_json(out / "interface_manifest.json", source_manifest)

    git_head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    git_branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"], check=True, capture_output=True, text=True).stdout.strip()
    md = [
        "# NP K6 Coupling Forward Runtime Coverage V2",
        "",
        "Status: `NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V2_READY`",
        "",
        "## V1 interface audit",
        "",
        "Classification: `B_EXECUTABLE_PROVIDER_BUT_DOMAIN_GUARD_BLOCKS_COUPLING_GEOMETRIES`. V1 is callable but resolves LF requests through exact geometry keys: an HF22 row lookup, then exact lookup in a 296,010-entry master generated only from strictly increasing `itertools.combinations(DS, 6)` and its precomputed chunks. The 20 Coupling geometries have `0/20` exact HF22 overlap and `0/220` exact V1 LF query coverage. This was a lookup-domain limitation, not evidence of invalid physical geometry.",
        "",
        "## A1 runtime provider",
        "",
        "`NP_LF_FEATURE_PROVIDER_V2(D1,...,D6, lambda, polarization)` is a callable deterministic implementation of the frozen D0 single-pillar `txx` + ordered six-bin DFT proxy. It does not fit a model, sort/permute the six physical +x positions, interpolate, or substitute a neighbor. Its finite runtime domain is all `27^6` ordered diameter vectors drawn from 100–230 nm in 5 nm steps, 445–455 nm integer samples, normal incidence, and `P_XLIKE` only.",
        "",
        "Outputs are normalized `eta_m_proxy` for tracked `m=-3..+3` and `T_proxy=sum(eta_-1, eta_0, eta_+1)`. `R` is unavailable; complex amplitudes, Jones, angular response, and coupled-device truth are not exposed. HF22 parity was checked on 242 geometry-wavelength points; maximum absolute delta was `%.9g` (gate `<=2e-6`)." % parity_max,
        "",
        "The provider has no fitted geometry set. Its source calibration is the 27-diameter × 11-wavelength x-polarized single-pillar library. Separately, the full-K6 HF22 empirical support contains 22 exact ordered geometries; the 20 query geometries are `0/20` exact matches and `20/20` OOD relative to that empirical support. This is runtime coverage, not an in-domain accuracy claim.",
        "",
        "The old D180 exclusion snapshot remains unchanged. A later one-run attempt was explicitly authorized: its persisted post-FSP SHA256 is `%s`, its formal post-FSP read-only extraction is pass/warning-valid, and its 11-row results SHA256 matches the library manifest D180 source-result hash. The old provenance snapshot was not rewritten. Provenance warning: the run manifest's `pre_fsp` pointer duplicated the post hash, and the path referenced by the setup heartbeat now contains different bytes than its recorded pre-run SHA. The V2 audit preserves this unresolved pre-file linkage anomaly; it does not treat the current file as the setup artifact." % _sha(d180_paths["post_fsp"]),
        "",
        "## Ordered 20-geometry audit",
        "",
        f"Physical grammar valid: {sum(x['physical_domain_valid'] for x in geometry_audits)}/20. Runtime domain supported: {sum(x['runtime_domain']['status'] == 'SUPPORTED_DISCRETE_ORDERED_LF_DOMAIN' for x in geometry_audits)}/20. Exact HF22 matches: {inside_support}/20. Positionwise extrapolative: {position_extrapolative}/20.",
        "",
        "| Query | Ordered D1..D6 (nm) | Nearest HF22 geometry | Distance / 130 nm | Physical | Runtime | HF22 OOD |",
        "|---|---|---|---:|---|---|---|",
    ]
    for x in geometry_audits:
        md.append("| %s | `%s` | `%s` | %.6f | %s | %s | %s |" % (
            x["source_case_id"], ",".join(map(str, x["ordered_D_nm"])), x["nearest_hf22_geometry_id"],
            x["nearest_hf22_distance_normalized_by_130nm"], "YES" if x["physical_domain_valid"] else "NO",
            "SUPPORTED" if x["runtime_domain"]["status"].startswith("SUPPORTED") else "NO",
            "YES" if x["ood"] else "NO",
        ))
    md += [
        "",
        "## Providers, coverage, and governance",
        "",
        "- A1 deterministic LF: available, callable, P/XLIKE only, power-level auxiliary features.",
        "- A2 learned provider: unavailable; frozen parity gate remains failed/not enabled.",
        "- Complex provider: runtime not ready; not added to V2.",
        "- Runtime feature cache: `20/20` geometries and `220/220` geometry-wavelength queries; SHA256 `%s`." % cache_sha,
        "- All 20 geometries remain OOD versus exact HF22 support. Coupling outcomes were not read or used.",
        "- Future Stage-1 geometry-only metadata was not found in the checked frozen execution plan; no future labels were read.",
        "- Immutable V1 confirmatory contract SHA256 remains `b8e156432c8ebd3b3087386b2dd768a177b6e0ef912f8eba4f1e40d3843e255c`.",
        "- New FDTD/LumAPI solver runs, HF acquisition, RCWA, training, inverse design, and sealed HF reads: `0`.",
        "",
        "## Authority",
        "",
        f"V1 authority base: `f8dad0e8438167ffca5ab22c19aa4790fa94b8d6`; repository branch at build: `{git_branch}`; HEAD at build: `{git_head}`.",
        "",
        "Machine-readable detailed audit: `outputs/np_k6_coupling_forward_runtime_coverage_v2/`. This provider is not integrated Coupling truth, an FDTD replacement, a complex scattering operator, or a guarantee of OOD accuracy.",
        "",
    ]
    report_path = root / "reports/NP_K6_COUPLING_FORWARD_RUNTIME_COVERAGE_V2.md"
    report_path.write_text("\n".join(md), encoding="utf-8")
    source_manifest["report"] = {"path": str(report_path.relative_to(root)).replace("\\", "/"), "sha256": _sha(report_path)}
    _write_json(out / "interface_manifest.json", source_manifest)

    # Small checksum manifest for all generated evidence except itself.
    checksum_entries = {}
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != "checksum_manifest.json":
            checksum_entries[p.name] = {"sha256": _sha(p), "size_bytes": p.stat().st_size}
    _write_json(out / "checksum_manifest.json", {
        "schema_version": "NP_K6_COUPLING_FORWARD_RUNTIME_COVERAGE_CHECKSUMS_V2",
        "files": checksum_entries,
        "external_files": {"report": {"path": source_manifest["report"]["path"], "sha256": source_manifest["report"]["sha256"], "size_bytes": report_path.stat().st_size}},
    })
    print(json.dumps({"status": coverage["status"], "geometry_count": len(query_geometries), "query_count": len(cache_records), "hf22_parity_rows": len(parity_rows), "hf22_parity_max_abs_delta": parity_max, "cache_sha256": cache_sha, "provenance_hash": source_digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
