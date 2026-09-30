from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from np_k6_coupling_forward_feature_interface_v2 import (
    NP_LF_FEATURE_PROVIDER_V2_Runtime,
    UnsupportedRequest,
    WAVELENGTHS_NM,
    _parse_geometry_id,
    _sha,
    geometry_id,
    validate_geometry,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def provider():
    return NP_LF_FEATURE_PROVIDER_V2_Runtime(ROOT)


def test_order_is_preserved_without_sorting(provider):
    geometry = (215, 105, 215, 230, 105, 130)
    assert validate_geometry(geometry) == geometry
    result = provider.infer(geometry, 450, "P_XLIKE")
    assert result["ordered_D_nm"] == list(geometry)
    assert result["geometry_id"] == "K6X_D215_D105_D215_D230_D105_D130"
    sorted_result = provider.infer(tuple(sorted(geometry)), 450, "P_XLIKE")
    assert result["geometry_id"] != sorted_result["geometry_id"]
    assert result["features"]["eta_m_proxy"] != sorted_result["features"]["eta_m_proxy"]


def test_power_schema_and_bookkeeping(provider):
    result = provider.infer((215, 105, 215, 230, 105, 130), 450, "P")
    eta = result["features"]["eta_m_proxy"]
    assert list(eta) == [f"m{m:+d}" for m in range(-3, 4)]
    assert math.isclose(sum(eta.values()), 1.0, rel_tol=0, abs_tol=2e-7)
    assert math.isclose(result["features"]["T_proxy"], sum(eta[f"m{m:+d}"] for m in (-1, 0, 1)), rel_tol=0, abs_tol=2e-7)
    assert result["features"]["R"]["status"] == "UNAVAILABLE"
    assert "complex" not in result["features"]
    assert result["provenance_hash"]


def test_20g_domain_coverage_is_separate_from_hf22_support(provider):
    support_path = ROOT / "outputs/np_k6_coupling_forward_feature_interface_v1/coupling_20g_domain_support.json"
    cases = json.loads(support_path.read_text(encoding="utf-8-sig"))["cases"]
    assert len(cases) == 20
    for case in cases:
        audit = provider.support_audit(case["ordered_D_nm"])
        assert audit["physical_domain_valid"] is True
        assert audit["provider_fit_support"]["status"] == "NOT_APPLICABLE_DETERMINISTIC_PROVIDER"
        assert audit["hf22_empirical_support"]["exact_hf22_match"] is False
        assert audit["runtime_domain"]["status"] == "SUPPORTED_DISCRETE_ORDERED_LF_DOMAIN"
        assert math.isfinite(audit["nearest_hf22_distance_normalized_by_130nm"])


def test_220_cached_queries_are_complete_and_unique(provider):
    cache_path = ROOT / "outputs/np_k6_coupling_forward_runtime_coverage_v2/coupling_20g_lf_feature_cache.jsonl"
    assert cache_path.is_file()
    records = [json.loads(x) for x in cache_path.read_text(encoding="utf-8").splitlines() if x]
    assert len(records) == 220
    assert len({(x["source_case_id"], x["wavelength_nm"]) for x in records}) == 220
    assert {x["wavelength_nm"] for x in records} == set(WAVELENGTHS_NM)
    assert {x["polarization"] for x in records} == {"P_XLIKE"}
    for row in records:
        got = provider.infer(row["ordered_D_nm"], row["wavelength_nm"], row["polarization"])
        assert got["features"] == row["features"]
        assert got["geometry_hash"] == row["geometry_hash"]
        assert got["provenance_hash"] == row["provenance_hash"]


def test_unsupported_conditions_fail_closed(provider):
    geometry = (215, 105, 215, 230, 105, 130)
    with pytest.raises(UnsupportedRequest):
        provider.infer(geometry, 450, "S")
    with pytest.raises(UnsupportedRequest):
        provider.infer(geometry, 450, "P", u_x=0.1)
    with pytest.raises(ValueError):
        provider.infer(geometry, 450.5, "P")
    with pytest.raises(ValueError):
        validate_geometry((215, 105, 215, 230, 105, 132))


def test_d180_provenance_reconciles_explicit_attempt2(provider):
    audit = json.loads((ROOT / "outputs/np_k6_coupling_forward_runtime_coverage_v2/a1_lf_provider_audit.json").read_text(encoding="utf-8"))
    d180 = audit["d180_provenance_reconciliation"]
    assert d180["legacy_snapshot_says_excluded"] is True
    assert d180["historical_anomaly_preserved"] is True
    assert d180["attempt2_formal_quality"] == "pass / warning_valid"
    result_path = ROOT / "outputs/np_k6_p1d2b_broadband_d180_x_v1/results.json"
    manifest = json.loads((ROOT / "outputs/np_k6_p1d2_broadband_library_27point_v1/library_manifest.json").read_text(encoding="utf-8-sig"))
    assert manifest["source_result_hashes"]["180"] == _sha(result_path)


def test_deterministic_runtime_matches_frozen_lf22_authority(provider):
    path = ROOT / "outputs/np_k6_m9_22g_forward_retraining_v1/lf22_full_vector_authority.csv"
    seen = set()
    max_delta = 0.0
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["polarization"].strip().lower() != "p":
                continue
            d = _parse_geometry_id(row["geometry_id"])
            wavelength = int(float(row["wavelength_nm"]))
            key = (d, wavelength)
            assert key not in seen
            seen.add(key)
            got = provider.infer(d, wavelength, "P_XLIKE")["features"]
            for m in range(-3, 4):
                max_delta = max(max_delta, abs(got["eta_m_proxy"][f"m{m:+d}"] - float(row[f"lf_eta_m{m:+d}"])))
            max_delta = max(max_delta, abs(got["T_proxy"] - float(row["lf_T_proxy"])))
    assert len(seen) == 242
    assert max_delta <= 2e-6
