from __future__ import annotations

import csv
import json
from pathlib import Path

OUT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_m11b_control0_neg0378_p_marginal_closure_forensic_v1")
W = list(range(445, 456))


def j(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def c(name):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_marginal_profile_and_no_new_solver():
    a = j("closure_profile_audit.json")
    assert a["CONTROL0_pass_count"] == 10
    assert a["CONTROL0_fail_count"] == 1
    assert a["ALT1_pass_count"] == 11
    assert a["ALT1_fail_count"] == 0
    assert a["CONTROL0_worst_wavelength"] == 453
    assert [int(r["wavelength_nm"]) for r in c("closure_profile_11points.csv")] == W
    b = j("solver_budget_audit.json")
    assert all(b[k] == 0 for k in ("new_solver_calls", "new_rcwa_calls", "control0_s_entered", "attempt_002_started"))


def test_contract_readback_gap_is_not_positive_difference():
    d = j("matched_numerical_contract_diff.json")
    assert d["formal_setup_unexpected_differences"] == []
    assert d["all_common_numeric_fields_equal"] is True
    assert d["non_geometry_difference_found"] is False
    assert set(d["unreliable_fields_skipped"]) == {"angle theta", "injection axis"}
    assert d["readback_incomplete_but_no_positive_contract_difference"] is True


def test_cutoff_and_termination_audits():
    d = j("order_cutoff_audit.json")
    assert d["order_set_changes"] is False
    assert d["exact_crossings_in_band"] is False
    for case in ("CONTROL0", "ALT1"):
        assert d["cases"][case]["open_order_sets"] == [[-1, 0, 1, 2, 3, 4, 5]]
        assert d["cases"][case]["min_air_cutoff_distance"] > 0
    t = j("termination_and_shutoff_audit.json")
    assert all(t[k]["early_termination"] and t[k]["completion_recorded"] for k in ("CONTROL0", "ALT1"))


def test_handoff_and_no_fsp_artifact():
    assert j("attempt002_value_decision.json")["no_auto_run"] is True
    assert j("attempt002_value_decision.json")["solver_authorized_now"] is False
    assert j("control0_s_status.json")["status"] == "NOT_ENTERED_REMAINS_BLOCKED"
    assert j("np_handoff_value_decision.json")["alt1_h1"] == "NP_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY"
    assert not list(OUT.rglob("*.fsp"))
