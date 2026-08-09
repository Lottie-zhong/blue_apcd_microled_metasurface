from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from apcd_coupling.broadband_source_contract import EXACT_WAVELENGTH_GRID_NM, fixed_absolute_kx_is_not_fixed_ux, validate_fixed_ux_rows

OUTPUT_ROOT = ROOT / "outputs/coupling/stage_a_polarization_angle_broadband_445_455_v1"
CONFIG = ROOT / "configs/coupling/stage_a_polarization_angle_broadband_445_455_v1.json"
CONTRACT = ROOT / "configs/coupling/broadband_fixed_ux_source_contract_v1.json"
REPORT = ROOT / "reports/coupling/stage_a_polarization_angle_broadband_hard_gate_v1.json"
REGISTRY = ROOT / "registries/coupling/solver_budget_registry.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_grid_and_fixed_ux_contract():
    config = read(CONFIG)
    contract = read(CONTRACT)
    assert tuple(config["exact_wavelength_grid_nm"]) == EXACT_WAVELENGTH_GRID_NM
    assert tuple(contract["wavelength_grid_nm"]) == EXACT_WAVELENGTH_GRID_NM
    ux = math.sin(math.radians(5.0))
    rows = [{"wavelength_nm": wavelength, "ux": ux, "real_kx": 2.0 * math.pi / (wavelength * 1e-9) * ux} for wavelength in EXACT_WAVELENGTH_GRID_NM]
    assert validate_fixed_ux_rows(rows, ux)
    fixed_kx = 2.0 * math.pi / (450.0e-9) * ux
    assert fixed_absolute_kx_is_not_fixed_ux(fixed_kx, ux)


def test_all_nine_setup_gates_pass_without_solver_entry_for_unentered_cases():
    registry = read(REGISTRY)
    assert len(registry["authorized_broadband_polarization_angle_case_order"]) == 9
    for case_id in registry["authorized_broadband_polarization_angle_case_order"]:
        setup = read(OUTPUT_ROOT / case_id / "setup_manifest.json")
        assert setup["setup_gate"]["pass"] is True
        assert setup["case"]["control_group"] == "POL_ANGLE_BROADBAND"
        assert setup["case"]["spacer_nm"] == 237.0
        assert setup["case"]["coordinates"]["total_sio2_separation_nm"] == 316.0
    for case_id in registry["broadband_polarization_angle"]["unentered_case_ids"]:
        assert not (OUTPUT_ROOT / case_id / "runtime/attempt_001/run_state.json").exists()


def test_y0_valid_11_row_result():
    payload = read(OUTPUT_ROOT / "STAGE_A_BB_Y0_445_455NM_S_YLIKE_UX0/results/result.json")
    assert payload["summary"]["rows"] == 11
    assert payload["summary"]["source_kx_closure_all_pass"] is True
    assert payload["summary"]["order_equation_all_pass"] is True
    assert payload["summary"]["power_closure_all_pass"] is True
    assert payload["summary"]["order_closure_all_pass"] is True
    assert payload["summary"]["no_polarization_averaging"] is True


def test_xp5_hard_gate_preserves_original_and_consumes_only_authorized_replay():
    registry = read(REGISTRY)
    report = read(REPORT)
    assert registry["broadband_polarization_angle"]["status"] == "HARD_GATE"
    assert registry["broadband_authorization_status"] == "HARD_GATE_XP5_REPLAY_ENGINE_FAILURE"
    assert registry["xp5_replay"]["authorized"] is True
    assert registry["xp5_replay"]["budget"] == 1
    assert registry["xp5_replay"]["entered"] == 1
    assert registry["xp5_replay"]["completed"] == 0
    assert report["decision"] == "HARD_GATE_BROADBAND_FIXED_UX_IMPLEMENTATION_UNRESOLVED"
    assert report["source_kx_closure_pass"] is False
    assert report["replay"] is False
    assert len(list((OUTPUT_ROOT / "STAGE_A_BB_XP5_445_455NM_P_XLIKE/runtime").glob("attempt_*"))) == 1
    replay_runtime = OUTPUT_ROOT / "STAGE_A_BB_XP5_REPLAY1_445_455NM_P_XLIKE/runtime/REPLAY1"
    assert (replay_runtime / "entered_ledger.json").exists()
    assert (replay_runtime / "run_failure.json").exists()
    assert not list(replay_runtime.glob("*post.fsp"))
    assert report["next_authorization_action"].startswith("REQUEST_BROADBAND_XP5_REPLAY_AUTHORIZATION")


def test_xp5_fixed_ux_diagnosis_and_corrected_setup_provenance():
    diagnosis = read(ROOT / "reports/coupling/stage_a_xp5_fixed_ux_diagnosis_v1.json")
    assert diagnosis["residual_decomposition"]["rows"] and len(diagnosis["residual_decomposition"]["rows"]) == 11
    assert diagnosis["original_evidence"]["source_residual_range"] < 1e-15
    assert diagnosis["corrected_setup_evidence"]["setup_gate"]["pass"] is True
    assert diagnosis["replay_gate"]["setup_only_source_ux_pass"] is True
    assert diagnosis["replay_gate"]["setup_only_boundary_ux_pass"] is True
    assert diagnosis["replay_gate"]["source_boundary_consistency_pass"] is True
    replay_setup = read(OUTPUT_ROOT / "STAGE_A_BB_XP5_REPLAY1_445_455NM_P_XLIKE/setup_manifest.json")
    assert replay_setup["replay_id"] == "XP5_REPLAY1"
    assert replay_setup["solver_entered"] is True
