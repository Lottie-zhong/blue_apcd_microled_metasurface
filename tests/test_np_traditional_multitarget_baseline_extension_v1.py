import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/np_traditional_multitarget_baseline_extension_v1"
LIB = ROOT / "outputs/np_k6_p1d2_broadband_library_27point_v1/library_long.csv"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_library_exact_integrity():
    rows = list(csv.DictReader(LIB.open(newline="", encoding="utf-8")))
    assert len(rows) == 297
    assert sorted({int(r["diameter_nm"]) for r in rows}) == list(range(100, 231, 5))
    assert sorted({int(r["wavelength_nm"]) for r in rows}) == list(range(445, 456))
    assert len({(r["diameter_nm"], r["wavelength_nm"]) for r in rows}) == 297


def test_family_contract_and_positions():
    c = read("multi_target_contract.json")
    assert [(x["K"], x["period_x_nm"]) for x in c["families"]] == [(4, 1160), (6, 1740), (9, 2610)]
    for k, expected in ((4, [-435, -145, 145, 435]), (9, [-1160, -870, -580, -290, 0, 290, 580, 870, 1160])):
        for seed in read(f"k{k}_phase_coverage_audit.json")["seeds"]:
            assert seed["x_positions_nm"] == expected
            assert seed["gap_pass"] and seed["minimum_gap_nm"] >= 60
            assert seed["max_aspect_ratio"] <= 5


def test_phase_audits_and_k6_freeze():
    k4, k9 = read("k4_phase_coverage_audit.json"), read("k9_phase_coverage_audit.json")
    assert k4["classification"] == "K4_PHASE_LIBRARY_COVERAGE_GOOD"
    assert k9["classification"].startswith("K9_PHASE_LIBRARY_COVERAGE_")
    assert len(k4["seeds"]) == len(k9["seeds"]) == 3
    assert all(x["period_x_nm"] == x["K"] * 290 for x in k4["seeds"] + k9["seeds"])
    frozen = read("k6_frozen_traditional_baseline_manifest.json")
    assert frozen["status"] == "FROZEN_REUSE_ONLY" and frozen["redesign"] is False and frozen["new_solver_runs"] == 0
    assert len(frozen["candidates"]) == 3


def test_setup_only_save_reload_and_zero_solver():
    for k in (4, 9):
        m = read(f"k{k}_fullsupercell_setup_manifest.json")
        assert m["status"] == "SETUP_ONLY_SAVED_RELOADED"
        assert m["solver_entered"] == 0 and len(m["cases"]) == 3
        assert all(x["reload_pass"] and not x["semantic_diff"].get("run_called", False) for x in m["cases"])
        checks = read(f"k{k}_setup_checksums.json")
        assert checks["status"] == "PASS" and checks["solver_entered"] == 0
        assert len(checks["cases"]) == 3
    zero = read("solver_zero_audit.json")
    assert zero["solver_entered"] == 0 and zero["fdtd_run_called"] is False and zero["mpi_calls"] == 0


def test_provider_scope_and_orders():
    p = read("provider_method_decision.json")
    assert p["RCWA_PROVIDER"] == "NOT_USED" and p["provider_method"] == "K6_LEGACY_3D_FDTD_WORKFLOW"
    assert read("multiangle_provider_decision.json")["incident_angle_sweep"] is False
    o = read("propagating_order_extraction_contract.json")
    assert o["hardcoded_three_orders"] is False and o["target_order"] == "+1"
    assert read("coupling_handoff_contract.json")["handoff_only"] is True
    r = read("first_batch_solver_proposal.json")["resource_contract"]
    assert r == {"slots": 1, "cores": 12, "execution_mode": "foreground_synchronous", "other_slots_reserved": 2}


def test_source_code_has_no_solver_run_or_ml_rcwa():
    for name in ("build_np_traditional_multitarget_baseline_extension_v1.py", "build_np_traditional_multitarget_prefsp_v1.py"):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8").lower()
        assert ".run(" not in text
        assert "import rcwa" not in text and "rcwa(" not in text
        assert "train(" not in text
