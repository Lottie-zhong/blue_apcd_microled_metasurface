"""Standalone validator for NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V2."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from np_k6_coupling_forward_feature_interface_v2 import NP_LF_FEATURE_PROVIDER_V2_Runtime, WAVELENGTHS_NM, _sha


def validate(root: Path | None = None) -> dict:
    root = (root or Path(__file__).resolve().parents[1]).resolve()
    out = root / "outputs/np_k6_coupling_forward_runtime_coverage_v2"
    manifest = json.loads((out / "interface_manifest.json").read_text(encoding="utf-8"))
    gate = json.loads((out / "coverage_gate.json").read_text(encoding="utf-8"))
    leak = json.loads((out / "leakage_audit.json").read_text(encoding="utf-8"))
    domains = json.loads((out / "geometry_domain_audit.json").read_text(encoding="utf-8"))
    a1 = json.loads((out / "a1_lf_provider_audit.json").read_text(encoding="utf-8"))
    a2 = json.loads((out / "a2_learned_provider_audit.json").read_text(encoding="utf-8"))
    complex_audit = json.loads((out / "complex_provider_runtime_audit.json").read_text(encoding="utf-8"))
    future = json.loads((out / "future_stage1_geometry_metadata_audit.json").read_text(encoding="utf-8"))
    cache_path = root / gate["cache_path"]
    cache = [json.loads(line) for line in cache_path.read_text(encoding="utf-8").splitlines() if line]
    provider = NP_LF_FEATURE_PROVIDER_V2_Runtime(root)

    expected_pairs = {(case["source_case_id"], int(w)) for case in domains["cases"] for w in WAVELENGTHS_NM}
    observed_pairs = {(record["source_case_id"], int(record["wavelength_nm"])) for record in cache}
    assert len(domains["cases"]) == 20
    assert expected_pairs == observed_pairs and len(cache) == 220
    assert len(observed_pairs) == len(cache)
    assert all(record["provider_id"] == "NP_LF_FEATURE_PROVIDER_V2" for record in cache)
    assert all(record["polarization"] == "P_XLIKE" for record in cache)
    assert all(record["ood"] is True for record in cache)
    assert all(record["provenance_hash"] == provider.provenance_hash for record in cache)
    assert all(record["geometry_id"] == "K6X_" + "_".join(f"D{d}" for d in record["ordered_D_nm"]) for record in cache)

    # Recompute every query.  This verifies the runtime API, not just a saved lookup.
    for record in cache:
        recomputed = provider.infer(record["ordered_D_nm"], record["wavelength_nm"], record["polarization"])
        assert recomputed["features"] == record["features"]
        assert recomputed["support_status"] == record["support_status"]
        assert recomputed["geometry_hash"] == record["geometry_hash"]
        assert math.isclose(sum(record["features"]["eta_m_proxy"].values()), 1.0, rel_tol=0, abs_tol=2e-7)

    cache_sha = _sha(cache_path)
    assert cache_sha == gate["cache_sha256"] == manifest["query_cache"]["sha256"]
    assert gate["status"] == "PASS" and gate["coverage"] == 1.0
    assert gate["runtime_supported_geometries"] == 20
    assert gate["valid_feature_records"] == gate["expected_query_points"] == 220
    assert domains["physical_valid_count"] == 20
    assert domains["runtime_supported_count"] == 20
    assert domains["exact_hf22_overlap"] == 0
    assert domains["ood_vs_hf22_exact_support"] == 20
    assert domains["positionwise_extrapolative_count"] == 20
    assert a1["hf22_lf_parity"]["pass"] is True and a1["hf22_lf_parity"]["rows"] == 242
    assert a1["v1_interface_audit"]["classification"] == "B_EXECUTABLE_PROVIDER_BUT_DOMAIN_GUARD_BLOCKS_COUPLING_GEOMETRIES"
    assert a1["v1_interface_audit"]["coupling_v1_exact_lf_query_coverage"] == "0/220"
    assert a2["runtime_model_available"] is False
    assert complex_audit["COMPLEX_PROVIDER_RUNTIME_READY"] == "NO"
    assert future["ordered_geometry_identities_found"] == [] and future["stage1_labels_read"] is False
    assert all(leak[k] is False for k in ["coupling_target_labels_read", "coupling_prediction_errors_read", "integrated_C_PW_read", "routing_truth_read", "H1_errors_read", "heldout_target_errors_read", "final_dipole_validation_read", "sealed_hf_targets_read"])
    assert leak["new_hf_or_fdtd"] == leak["new_training"] == leak["new_rcwa"] == leak["inverse_design"] == 0
    assert leak["old_confirmatory_contract"]["expected_sha256"] == "b8e156432c8ebd3b3087386b2dd768a177b6e0ef912f8eba4f1e40d3843e255c"
    contract_path = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V1\NP_FEATURE_ABLATION_CONFIRMATORY_CONTRACT_V1.json")
    assert _sha(contract_path) == leak["old_confirmatory_contract"]["expected_sha256"]

    checks = json.loads((out / "checksum_manifest.json").read_text(encoding="utf-8"))
    for name, entry in checks["files"].items():
        assert _sha(out / name) == entry["sha256"]
    external_checks = checks.get("external_files", {})
    for entry in external_checks.values():
        external_path = root / entry["path"]
        assert _sha(external_path) == entry["sha256"]
        assert external_path.stat().st_size == entry["size_bytes"]
    assert manifest["report"]["path"] in [entry["path"] for entry in external_checks.values()]
    assert manifest["status"] == "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V2_READY"
    report = {
        "status": "PASS",
        "interface_id": manifest["interface_id"],
        "runtime_coverage": "20/20 geometries; 220/220 wavelength queries",
        "hf22_empirical_support": "0/20 exact; all 20 OOD",
        "hf22_lf_parity": a1["hf22_lf_parity"],
        "cache_sha256": cache_sha,
        "adapter_provenance_hash": provider.provenance_hash,
        "zero_solver": True,
        "target_leakage": False,
        "immutable_v1_contract_sha256": _sha(contract_path),
        "checksum_manifest_entries_verified": len(checks["files"]) + len(external_checks) + (0 if "validation_report.json" in checks["files"] else 1),
        "markdown_report_sha256": manifest["report"]["sha256"],
    }
    validation_path = out / "validation_report.json"
    validation_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checks["files"]["validation_report.json"] = {"sha256": _sha(validation_path), "size_bytes": validation_path.stat().st_size}
    (out / "checksum_manifest.json").write_text(json.dumps(checks, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return report


if __name__ == "__main__":
    validate()
