from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

NP = Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
CP = Path(r"D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_v1")
OUT = NP / "outputs" / "np_k6_m10_angular_hf_anchor_design_v1"
PKG = CP / "outputs" / "coupling" / "COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1"


def j(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_package_pin_and_recheck():
    pin = j("NP_CONSUMED_COUPLING_B_TERMINAL_PACKAGE_PIN_V1.json")
    recheck = j("NP_CONSUMED_COUPLING_B_TERMINAL_PACKAGE_RECHECK_V1.json")
    assert pin["source_branch"] == "work/mdc-np-coupling-v1"
    assert pin["source_head"].startswith("92ccb154")
    assert pin["package_file_count"] == 17
    assert pin["validator_status"] == "PASS_HASH_STABLE_AFTER_READ"
    assert recheck["stable"] is True and recheck["changed_files"] == []
    for item in pin["artifacts"]:
        h = hashlib.sha256((PKG / item["relative_path"]).read_bytes()).hexdigest()
        assert h == item["sha256"]


def test_exact_identities_and_scope():
    manifest = json.loads((PKG / "COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1.json").read_text(encoding="utf-8"))
    assert manifest["identities"]["ALT1"]["diameters_nm"] == [100, 115, 130, 145, 155, 185]
    assert manifest["identities"]["CONTROL0"]["diameters_nm"] == [125, 135, 150, 175, 190, 210]
    assert manifest["exact_wavelengths_nm"] == list(range(445, 456))
    assert j("exact_geometry_identity_audit.json")["identity_match"] is True


def test_existing_hf_and_unresolved_p():
    existing = j("NP_M10_EXISTING_HF_3OF4_AUDIT_V1.json")
    assert existing["coverage"] == "3/4"
    assert existing["P_plus_0224"]["status"] == "UNRESOLVED_AFTER_TWO_ENTERED_FAILURES"
    assert existing["P_plus_0224"]["attempt_003"] is False
    assert sum(r["reusable"] for r in existing["rows"]) == 3


def test_mdc_missingness_no_fill():
    mass = j("NP_M10_MDC_MISSINGNESS_AUDIT_V1.json")
    assert mass["formal_available_nodes"] == 4 and mass["missing_nodes"] == 5
    assert all(r["fill_policy"] == "NO_FILL" for r in mass["rows"])
    assert any(r["MDC_IMPORTANCE"] == "UNKNOWN" for r in mass["rows"])


def test_primary_batch_is_two_new_paired_cases():
    batch = j("NP_COUPLING_RELEVANT_ANGULAR_HF_PRIMARY_BATCH_V1.json")
    new = [r for r in batch["rows"] if r["existing_or_new"] == "new"]
    assert len(new) == 2
    assert {(round(float(r["ux_exact"]), 12), r["polarization"]) for r in new} == {(round(-0.48275862068965514, 12), "P_XLIKE"), (round(-0.48275862068965514, 12), "S_YLIKE")}
    assert batch["P_plus_0224_not_queued"] is True
    assert batch["new_solver_invocation_count"] <= 6
    assert batch["preferred_batch_reduced_from_4_by_exact_existing_HF_reuse"] is True


def test_selection_and_decision_gate_pre_registered():
    selection = j("NP_K6_M10_COUPLING_RELEVANT_ANGULAR_HF_SELECTION_PREREG_V1.json")
    digest = hashlib.sha256((OUT / "NP_K6_M10_COUPLING_RELEVANT_ANGULAR_HF_SELECTION_PREREG_V1.json").read_bytes()).hexdigest()
    assert digest == j("selection_preregistration_sha256.json")["sha256"]
    assert selection["created_after_package_pin"] is True
    gate = j("NP_M10_DECISION_STABILITY_GATE_PREREG_V1.json")
    assert gate["created_before_new_HF"] is True
    assert gate["categories"]["DECISION_STABLE"] == "ratio < 0.5"


def test_zero_solver_and_readiness():
    zero = j("solver_zero_audit.json")
    assert all(zero[k] == 0 for k in ("FDTD", "RCWA", "TMM", "BFAST", "ML_training", "new_HF", "external_HF", "inverse", "replay"))
    assert zero["coupling_intermediate_read"] == 0 and zero["coupling_worktree_writes"] == 0
    assert j("decision.json")["solver_authorized"] is False
    assert j("NP_M10_PROVIDER_EVIDENCE_AUDIT_V1.json")["Level2_integrated_truth"] == "NOT_AVAILABLE"


def test_no_solver_artifacts_and_csv_manifest():
    assert not list(OUT.rglob("*.fsp"))
    assert not list(OUT.rglob("*.npz"))
    with (OUT / "NP_COUPLING_RELEVANT_ANGULAR_HF_PRIMARY_BATCH_V1.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 8
