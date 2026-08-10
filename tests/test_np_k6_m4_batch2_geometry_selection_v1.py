"""Stage-specific tests for NP K6 M4 zero-solver selection evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_geometry_selection_v1"
VALIDATOR = ROOT / r"scripts\validate_np_k6_m4_batch2_geometry_selection_v1.py"


def read_json(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8-sig"))


def test_policy_hash_is_frozen_and_shared() -> None:
    policy = read_json("m4_selection_policy.json")
    body = {key: value for key, value in policy.items() if key != "policy_hash"}
    expected = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert policy["policy_hash"] == expected
    assert policy["uncertainty_role"].startswith("relative_context_only")
    assert read_json("m4_selection_manifest.json")["policy_hash"] == expected


def test_selection_excludes_hf_and_sealed_and_preserves_d0_d5() -> None:
    manifest = read_json("m4_selection_manifest.json")
    foundation = json.loads((ROOT / r"outputs\np_k6_ml_d0_database_foundation_v1\k6_hf_pilot_geometry_manifest.json").read_text(encoding="utf-8-sig"))
    dev = {row["geometry_hash"] for row in foundation["rows"] if row["pilot_role"] == "development_pilot"}
    sealed = {row["geometry_hash"] for row in foundation["rows"] if row["pilot_role"] == "sealed_test_pilot"}
    with (ROOT / r"outputs\np_k6_m3_pilot_retraining_v1\development_hf_v2_training_view.csv").open(encoding="utf-8-sig", newline="") as handle:
        hf = {row["geometry_hash"] for row in csv.DictReader(handle)}
    selected = manifest["primary4"] + manifest["backups_ranked"]
    assert len(manifest["primary4"]) == 4
    assert len(manifest["backups_ranked"]) >= 8
    assert all(row["geometry_hash"] in dev and row["geometry_hash"] not in sealed and row["geometry_hash"] not in hf for row in selected)
    assert all(len(row["geometry_id"].split("_")) >= 2 and row["geometry_id"].startswith("K6X_") for row in selected)


def test_prediction_profiles_are_exactly_p_s_and_11_wavelengths() -> None:
    with (OUT / "m4_candidate_prediction_profiles_long.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    keys = {(row["geometry_id"], row["wavelength_nm"], row["polarization"]) for row in rows}
    assert len(rows) == 39 * 11 * 2
    assert len(keys) == len(rows)
    assert {int(row["wavelength_nm"]) for row in rows} == set(range(445, 456))
    assert {row["polarization"] for row in rows} == {"p", "s"}


def test_cost_package_and_zero_solver_audit() -> None:
    cost = read_json("m4_solver_cost_decision_package.json")
    assert cost["solver_authorization"] is False
    assert cost["solver_run_invocations"] == 0
    assert {row["paired_ps_case_count"] for row in cost["batches"]} == {8, 12, 16}
    zero = read_json("m4_solver_zero_audit.json")
    assert zero == {
        "batch2_started": False,
        "fdtd_run_invocations": 0,
        "lumerical_imported": False,
        "lumapi_run_invocations": 0,
        "sealed_target_reads": 0,
        "schema_version": "np_k6_m4_solver_zero_audit_v1",
    }


def test_independent_validator_report_passes() -> None:
    sys.path.insert(0, str(VALIDATOR.parent))
    import validate_np_k6_m4_batch2_geometry_selection_v1 as validator

    assert validator.main() == 0
    assert read_json("m4_standalone_validator_report.json")["status"] == "PASS"
