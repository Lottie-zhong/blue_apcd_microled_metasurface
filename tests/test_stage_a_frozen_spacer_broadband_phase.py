from __future__ import annotations

import hashlib
import json
import math
import pytest
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / "registries/coupling/stage_a_frozen_spacer_broadband_phase_registry_v1.json"
CONFIG = ROOT / "configs/coupling/stage_a_polarization_angle_broadband_445_455_v1.json"
SETUP_ROOT = ROOT / "outputs/coupling/stage_a_frozen_spacer_445_455_polarization_angle_broadband_v1"
SETUP_ONLY_ROOT = ROOT / "outputs/coupling/stage_a_polarization_angle_broadband_445_455_calibrated_setup_only_v2"
X0 = ROOT / "outputs/coupling/stage_a_nb_t237_445_455_xpol_normal_v1"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_frozen_spacer_phase_registry_is_explicit_and_ordered():
    phase = read(PHASE)
    config = read(CONFIG)
    assert phase["authorized"] is True
    assert phase["budget"] == 9
    assert phase["entered"] == len(phase["entered_case_ids"])
    assert phase["completed"] == len(phase["completed_case_ids"])
    assert phase["completed"] <= phase["entered"]
    assert phase["replay_forbidden"] is True
    assert phase["case_order"] == config["new_solver_case_order"]
    assert phase["frozen_spacer_nm"] == 237.0
    assert phase["wavelength_grid_nm"] == list(range(445, 456))


def test_all_nine_fresh_setup_manifests_pass_without_solver_entry():
    phase = read(PHASE)
    assert len(phase["case_order"]) == 9
    for case_id in phase["case_order"]:
        manifest = read(SETUP_ONLY_ROOT / case_id / "setup_manifest.json")
        assert manifest["case_id"] == case_id
        assert manifest["setup_gate"]["pass"] is True
        assert manifest["case"]["spacer_nm"] == 237.0
        assert manifest["case"]["coordinates"]["total_sio2_separation_nm"] == 316.0
        assert manifest["solver_entered"] is False
        assert manifest["solver_completed"] is False
        assert manifest["pre_fsp_sha256"] == sha256(Path(manifest["pre_fsp_path"]))
        rows = manifest["readback"]["per_wavelength_source_targets"]
        assert [row["wavelength_nm"] for row in rows] == [float(x) for x in range(445, 456)]
        ux = float(manifest["state"]["ux"])
        assert all(abs(float(row["target_ux"]) - ux) <= 1e-15 for row in rows)
        assert all(abs(float(row["target_real_kx"]) - 2.0 * math.pi / (float(row["wavelength_nm"]) * 1e-9) * ux) <= 1e-6 for row in rows)


def test_x0_is_read_only_reuse_and_not_part_of_phase():
    phase = read(PHASE)
    x0_setup = read(X0 / "setup_manifest.json")
    x0_result = read(X0 / "results/result.json")
    x0_extract = read(X0 / "results/extraction_manifest.json")
    x0_identity = read(X0 / "post_fsp_identity_audit.json")
    assert phase["x0_reuse_case_id"] == x0_setup["case_id"]
    assert phase["x0_reuse_rerun"] is False
    assert x0_setup["case"]["spacer_nm"] == 237.0
    assert x0_setup["case"]["kx_over_k0"] == 0.0
    assert len(x0_result["rows"]) == 11
    assert x0_extract["all_rows_valid"] is True
    assert x0_identity["pass"] is True


def test_phase_runner_dry_run_does_not_enter_solver():
    phase = read(PHASE)
    if len(phase["entered_case_ids"]) >= len(phase["case_order"]):
        pytest.skip("phase is fully entered; no next dry-run case")
    case_id = phase["case_order"][len(phase["entered_case_ids"])]
    case_dir = SETUP_ROOT / case_id
    proc = subprocess.run(
        [sys.executable, "scripts/coupling/run_control_group_case.py", "--output-dir", str(case_dir), "--attempt-id", "dry_run_test", "--phase-registry", str(PHASE), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["authorization_pass"] is True
    assert payload["solver_entered"] is False
    assert payload["phase_id"] == read(PHASE)["phase_id"]


def test_xp5_readback_closes_fixed_ux_with_scaled_real_kx_tolerance():
    phase = read(PHASE)
    if "STAGE_A_BB_XP5_445_455NM_P_XLIKE" not in phase["completed_case_ids"]:
        pytest.skip("X_P5 has not completed yet")
    result = read(SETUP_ROOT / "STAGE_A_BB_XP5_445_455NM_P_XLIKE/results/result.json")
    assert result["rows"]
    assert all(row["source_kx_contract"]["pass"] is True for row in result["rows"])
    assert max(abs(float(row["source_kx_contract"]["ux_residual"])) for row in result["rows"]) < 1e-6
    assert all(float(row["source_kx_contract"]["real_kx_tolerance"]) > 0.0 for row in result["rows"])
