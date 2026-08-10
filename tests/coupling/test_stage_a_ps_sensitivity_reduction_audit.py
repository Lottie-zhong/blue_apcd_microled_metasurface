import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/coupling/stage_a_ps_sensitivity_reduction_audit_v1.json"
MATRIX = ROOT / "reports/coupling/stage_a_frozen_spacer_polarization_angle_broadband_matrix_v1.json"
EXPECTED_SHA256 = "d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage_a_ps_audit_has_exact_pairs_and_frozen_source():
    report = read(REPORT)
    matrix_hash = hashlib.sha256(MATRIX.read_bytes()).hexdigest()
    assert matrix_hash == EXPECTED_SHA256
    assert report["scope"]["matrix_sha256"] == EXPECTED_SHA256
    assert report["scope"]["pair_count"] == 55
    assert len(report["pair_metrics"]) == 55
    assert set(report["five_angle_summary"]) == {"-10", "-5", "0", "5", "10"}
    assert all(item["pair_count"] == 11 for item in report["five_angle_summary"].values())
    assert all(item["symmetric_relative_difference_defined"] for item in report["pair_metrics"])


def test_stage_a_ps_audit_has_no_averaging_or_equivalence_claim():
    report = read(REPORT)
    assert report["scope"]["polarization_averaging_used"] is False
    assert report["scope"]["np_equivalence_claim"] is False
    assert report["safety"]["formal_tolerance_defined"] is False
    assert report["safety"]["tolerance_added"] is False
    assert report["replay_checks"]["exact_55_ps_pairs"] is True
    assert report["replay_checks"]["no_polarization_averaging"] is True
    assert report["replay_checks"]["no_np_equivalence_claim"] is True
    assert "DESCRIPTIVE_ONLY" in report["decision"]
    assert "NO_FORMAL_TOLERANCE" in report["decision"]


def test_stage_a_ps_audit_delta_formula_is_replayable():
    report = read(REPORT)
    for item in report["pair_metrics"]:
        assert item["delta_eta_plus1"] == item["eta_plus1_P"] - item["eta_plus1_S"]
        assert item["abs_delta_eta_plus1"] == abs(item["delta_eta_plus1"])
        assert item["delta_R"] == item["R_P"] - item["R_S"]
        assert item["delta_T"] == item["T_P"] - item["T_S"]
