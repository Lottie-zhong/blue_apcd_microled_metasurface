from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_m10a_angular_handoff_preparation_v1"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scaffold():
    path = ROOT / "scripts" / "np_k6_m10a_angular_provider_scaffold_v1.py"
    spec = importlib.util.spec_from_file_location("m10a_scaffold_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_prereg_hash_and_scope():
    prereg = load("NP_ANGULAR_HF_SELECTION_METHOD_PREREG_V1.json")
    digest = hashlib.sha256((OUT / "NP_ANGULAR_HF_SELECTION_METHOD_PREREG_V1.json").read_bytes()).hexdigest()
    assert digest == load("selection_preregistration_sha256.json")["sha256"]
    assert "no absolute promotion threshold" in prereg["threshold_policy"]
    assert prereg["solver_policy"]["FDTD"] == 0


def test_unique_key_and_residual_join(scaffold):
    fields = {"geometry_hash": "g", "u_x_identity": "ux0", "polarization": "P", "wavelength_contract": "445-455", "physics_contract_id": "pc"}
    rcwa = {**fields, "eta_plus1": 0.2, "eta_0": 0.3, "eta_minus1": 0.1, "R_total": 0.1, "T_total": 0.6}
    fdtd = {**fields, "eta_plus1": 0.25, "eta_0": 0.28, "eta_minus1": 0.12, "R_total": 0.11, "T_total": 0.58}
    rows = scaffold.build_residual_rows([rcwa], [fdtd])
    assert len(rows) == 1 and rows[0]["delta_eta_plus1"] == pytest.approx(0.05)


def test_weighted_metric_and_margin(scaffold):
    truth = {"eta_plus1": 0.2, "T_total": 0.8, "eta_m+1": 0.2}
    pred = {"eta_plus1": 0.3, "T_total": 0.7, "eta_m+1": 0.25}
    metric = scaffold.E_MDC_weighted({"eta_plus1": 2.0, "T_total": 1.0}, truth, pred)
    assert metric["weighted_eta_plus1_error"] == pytest.approx(0.2)
    assert metric["weighted_T_error"] == pytest.approx(0.1)
    assert scaffold.provider_error_to_candidate_margin_ratio(0.1, 0.0) is None
    assert scaffold.provider_error_to_candidate_margin_ratio(0.1, 0.2) == pytest.approx(0.5)


def test_registry_is_normal_only_and_unresolved_0224():
    registry = load("NP_EXISTING_NONZERO_UX_HF_PROVENANCE_REGISTRY_V1.json")
    assert registry["nonzero_u_x_formal_cases"] == []
    audit = registry["reported_plus_0224_audit"]
    assert audit["classification"] == "NOT_FOUND_IN_NP_AUTHORITY"
    assert audit["reusable_for_future_angular_calibration"] == "no"
    assert all(row["exact_u_x"] == 0.0 for row in registry["rows"])


def test_future_batch_template_empty():
    with (OUT / "NP_COUPLING_RELEVANT_ANGULAR_HF_PRIMARY_BATCH_TEMPLATE_V1.csv").open(newline="", encoding="utf-8") as f:
        assert list(csv.DictReader(f)) == []


def test_solver_zero_and_coupling_untouched():
    solver = load("solver_zero_audit.json")
    assert all(solver[k] == 0 for k in ("FDTD", "RCWA", "TMM", "BFAST", "new_HF", "external_HF", "ML_training", "inverse", "replay"))
    assert solver["coupling_B_read"] == solver["coupling_B_polling"] == solver["coupling_worktree_writes"] == 0
    prov = load("provenance_audit.json")
    assert prov["coupling_B_read"] is False and prov["coupling_B_polled"] is False


def test_readiness_blocks_until_coupling_b():
    checklist = load("NP_ANGULAR_PROVIDER_HANDOFF_READINESS_CHECKLIST_V1.json")
    assert checklist["current_status"] == "WAIT_COUPLING_B_TERMINAL_EVIDENCE"
    assert checklist["gates"]["B_coupling_relevant_angular_support_known"] == "WAIT_COUPLING_B"
    assert checklist["gates"]["J_supported_extrapolation_domain_frozen"] == "PASS_NORMAL_ONLY"
