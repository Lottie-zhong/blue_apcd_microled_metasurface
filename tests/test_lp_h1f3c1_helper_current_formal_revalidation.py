import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f3c1_helper_current_formal_revalidation"

def read(name):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))

def test_helper_identity_geometry_and_full_jones_scope():
    prereg = read("preregistration.json")
    geom = read("geometry_audit.json")
    assert prereg["case_order"] == ["H1F3C1_HELPER_H1C1B_V2_015_TRIMER_V1_x", "H1F3C1_HELPER_H1C1B_V2_015_TRIMER_V1_y"]
    assert geom["pass"] is True
    assert min(geom["gaps_nm"][k] for k in ("helper_to_J1", "helper_to_J2", "helper_periodic_image")) >= 60.0
    assert prereg["transfer_rule"]["no_parameter_sweep"] is True

def test_two_serial_cases_entered_once_and_accepted():
    accounting = read("solver_accounting_runtime.json")
    assert accounting["solver_subruns_entered"] == 2
    assert accounting["solver_subruns_accepted"] == 2
    assert accounting["replay_cases"] == []
    assert [row["solver_entered"] for row in accounting["cases"]] == [True, True]
    assert accounting["cases"][0]["polarization"] == "x"
    assert accounting["cases"][1]["polarization"] == "y"

def test_concurrency_trial_does_not_promote_policy_and_deduplicates_mpi():
    obs = read("CONCURRENCY_3_OBSERVATION.json")
    assert obs["classification"] in {"CONCURRENCY_3_PRODUCTION_OBSERVATION_PASS", "CONCURRENCY_3_PRODUCTION_OBSERVATION_DEGRADED", "CONCURRENCY_3_PRODUCTION_OBSERVATION_INCONCLUSIVE"}
    assert obs["peak_simultaneous_real_fdtd_jobs"] == 3
    assert obs["lp_mpi_configuration"]["processes_per_job"] == 4
    assert obs["permanent_policy_promoted"] is False
    assert obs["permanent_global_fdtd_policy"] == 2
    assert obs["mpi_topology"].startswith("2 NP groups x 4 children")

def test_physics_summary_is_separate_from_concurrency_classification():
    summary = read("helper_current_formal_summary.json")
    assert summary["rows"] == 9
    assert summary["x_y_serial_and_accepted"] is True
    assert summary["no_parent_rerun"] is True
    assert summary["projector_pass_count"] == 6
    assert summary["concurrency_observation"] == "CONCURRENCY_3_PRODUCTION_OBSERVATION_PASS"
