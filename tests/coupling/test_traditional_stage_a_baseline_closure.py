from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "reports/coupling/stage_a_frozen_spacer_polarization_angle_broadband_matrix_v1.json"
LOCK = ROOT / "contracts/coupling/traditional_stage_a_baseline_lock_v1.json"
SUMMARY = ROOT / "reports/coupling/traditional_stage_a_baseline_summary_v1.json"
MANIFEST = ROOT / "registries/coupling/traditional_stage_a_baseline_completion_manifest_v1.json"
ASSETS = ROOT / "registries/coupling/traditional_stage_a_asset_registry_v1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_formal_artifacts_and_physical_identity():
    lock = load(LOCK)
    summary = load(SUMMARY)
    manifest = load(MANIFEST)
    assert lock["status"] == "TRADITIONAL_STAGE_A_BASELINE_FROZEN"
    assert lock["closure_state"] == "APCD_MDC_NP_TRADITIONAL_STAGE_A_BASELINE_CLOSED"
    identity = lock["physical_identity"]
    assert identity["mdc_candidate_id"] == "P1_ZL1_ALTERNATIVE_G3_A3"
    assert identity["mdc_layer_count"] == 12
    assert identity["mdc_layer_sequence"] == ["TiO2:44nm", "SiO2:79nm", "TiO2:44nm", "SiO2:79nm", "TiO2:44nm", "SiO2:316nm", "TiO2:44nm", "SiO2:79nm", "TiO2:44nm", "SiO2:79nm", "TiO2:44nm", "SiO2:79nm"]
    assert identity["mdc_total_thickness_nm"] == 975
    assert identity["mdc_top_sio2_nm"] == 79
    assert identity["extra_spacer_nm"] == 237
    assert identity["total_continuous_sio2_separation_nm"] == 316
    assert identity["layer_12_is_79_not_316"] is True
    assert identity["316_is_continuous_separation_not_mdc_layer_12"] is True
    assert identity["np_candidate_id"] == "NP_K6X_125_135_150_175_190_210"
    assert identity["np_K"] == 6
    assert identity["np_period_x_nm"] == 1740
    assert identity["np_period_y_nm"] == 290
    assert identity["np_pillar_height_nm"] == 500
    assert identity["np_diameters_nm"] == [125, 135, 150, 175, 190, 210]
    assert identity["z_coordinates_nm"] == {
        "joint_z_zero": 0,
        "mdc_top": 975,
        "extra_spacer_top_and_pillar_bottom": 1212,
        "pillar_top": 1712,
    }
    assert summary["validated_domain"]["wavelength_nm"] == list(range(445, 456))
    assert summary["validated_domain"]["polarization_branches"] == ["P_XLIKE", "S_YLIKE"]
    assert manifest["closure_state"] == lock["closure_state"]


def test_matrix_identity_completeness_and_no_averaging():
    matrix = load(MATRIX)
    assert sha(MATRIX) == "d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6"
    assert matrix["status"] == "VALIDATED_110_ROWS"
    assert len(matrix["rows"]) == 110
    state_keys = {(row["polarization_branch"], row["theta_air_in_label_deg"]) for row in matrix["rows"]}
    assert state_keys == {(branch, angle) for branch in ("P_XLIKE", "S_YLIKE") for angle in (-10, -5, 0, 5, 10)}
    assert all(sum(1 for row in matrix["rows"] if (row["polarization_branch"], row["theta_air_in_label_deg"]) == key) == 11 for key in state_keys)
    assert {int(round(row["wavelength_nm"])) for row in matrix["rows"]} == set(range(445, 456))
    assert all(row["no_polarization_averaging"] is True for row in matrix["rows"])
    assert all(row["no_interpolation"] is True and row["no_extrapolation"] is True for row in matrix["rows"])
    assert all(row["solver_entered"] is True and row["solver_completed"] is True for row in matrix["rows"])
    assert all(row["identity_audit_pass"] is True for row in matrix["rows"])
    assert {row["source_kind"] for row in matrix["rows"]} == {"new_solver_case", "x0_read_only_reuse"}
    assert all("stage_a_polarization_angle_broadband_445_455_v1" not in row["result_path"] for row in matrix["rows"])
    assert matrix["closure"]["all_rows_no_polarization_averaging"] is True



def test_evidence_and_provenance_registry():
    summary = load(SUMMARY)
    assets = load(ASSETS)
    current_b3 = sha(ROOT / "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1/results/result.json")
    asset_map = {item["asset_id"]: item for item in assets["assets"]}
    assert asset_map["B3"]["sha256"] == current_b3
    assert current_b3 == "933113684ba0713c5dfe2fb7d63c8fbb54aabafa95461b63ce7a4d2b6f186fb8"
    assert "933113684ba0713c5dfe2fb7d63c8fbb54aabafa95461b63ce7a4d2b6f186fb8" in (
        ROOT / "registries/coupling/stage_a_result_registry_v1.json"
    ).read_text(encoding="utf-8")
    control_registry = load(ROOT / "registries/coupling/stage_a_control_groups_result_registry_v1.json")
    assert control_registry["cases"]["B3"]["result_sha256"] == "ed791f2319f8f643c19f834a8083a40269dbddea53b9b82d6d07e617eece2814"
    assert control_registry["cases"]["B3"]["post_fsp_sha256"] == "cfda69e11338ec90ac3a13cc185710c9910567e3dc8fcac0216699925c6b0269"
    assert summary["historical_provenance"]["excluded_from_final_matrix"] is True
    assert summary["historical_provenance"]["replay_protection_preserved"] is True
    assert "XP5" in summary["historical_provenance"]["invalid_historical_output_root"]


def test_spacer_and_level_boundaries():
    summary = load(SUMMARY)
    rows = summary["evidence"]["spacer_sensitivity_450nm"]["rows"]
    assert set(rows) == {"t_extra_0_B3", "t_extra_79", "t_extra_158", "t_extra_237"}
    assert summary["evidence"]["spacer_sensitivity_450nm"]["selection"]["frozen_spacer_nm"] == 237
    assert summary["evidence"]["spacer_sensitivity_450nm"]["non_monotonic"] is True
    assert summary["level_1_preparation"]["numerical_result"] == "NOT_RUN"
    assert summary["future_ml_handoff"]["checkpoint_loaded"] is False
    assert summary["future_ml_handoff"]["inference_run"] is False
    assert all(value == "NOT_ACTIVATED_IN_THIS_TASK" for key, value in summary["future_ml_handoff"].items() if key.endswith("PROVIDER"))


def test_reusable_framework_and_completion_checks():
    lock = load(LOCK)
    manifest = load(MANIFEST)
    assets = load(ASSETS)
    framework = lock["framework"]
    for key in ("mdc_provider", "np_provider", "interface_provider", "incident_state_provider", "joint_builder", "solver_runner", "order_extractor", "result_schema", "broadband_result_schema", "comparison_engine", "provenance_registry", "replay_registry"):
        assert framework[key]["status"] == "FROZEN_REUSABLE_FRAMEWORK"
        assert Path(framework[key]["path"]).exists()
    assert lock["framework"]["provider_contract"]["traditional_mdc_provider"] == "ZL1"
    assert lock["framework"]["provider_contract"]["traditional_np_provider"] == "RUN3A"
    assert all(manifest["required_checks"].values())
    assert manifest["replay_protection"]["enabled"] is True
    assert manifest["replay_protection"]["historical_failure_retained"] is True
    assert assets["large_artifact_policy"]["fsp_committed"] is False
    assert assets["large_artifact_policy"]["raw_monitor_arrays_committed"] is False


def test_safety_zero_solver_and_fresh_process_sha():
    summary = load(SUMMARY)
    safety = summary["safety"]
    assert all(value == 0 for value in safety.values())
    probe = "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path(r'reports/coupling/stage_a_frozen_spacer_polarization_angle_broadband_matrix_v1.json').read_bytes()).hexdigest())"
    result = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, check=True, capture_output=True, text=True)
    assert result.stdout.strip() == "d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6"
