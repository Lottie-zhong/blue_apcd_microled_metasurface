"""Offline semantic and provenance gates for the traditional NP final freeze."""
from __future__ import annotations

import ast
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "np_traditional_multitarget_final_freeze_v1"
LIB = ROOT / "outputs" / "np_traditional_multitarget_first_batch_3d_fdtd_v1"
SCRIPT = ROOT / "scripts" / "finalize_np_traditional_multitarget_final_freeze_v1.py"


def read(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_family_champions_are_family_scoped_and_global_is_descriptive():
    k4 = read("k4_final_decision.json")
    k9 = read("k9_final_decision.json")
    summary = read("traditional_multitarget_global_summary.json")
    assert k4["family"] == "K4" and all(c["family"] == "K4" for c in k4["candidates"])
    assert k9["family"] == "K9" and all(c["family"] == "K9" for c in k9["candidates"])
    assert k4["champion"]["candidate_id"] == "K4_SEED_B_100_175"
    assert k9["champion"]["candidate_id"] == "K9_SEED_B_205_185"
    assert summary["family_champions"]["K4"]["candidate_id"] == k4["champion"]["candidate_id"]
    assert summary["family_champions"]["K9"]["candidate_id"] == k9["champion"]["candidate_id"]
    assert summary["global_descriptive_winner"]["candidate_id"] == "K9_SEED_B_205_185"


def test_candidates_have_complete_valid_11_point_evidence():
    expected_post = {
        "K4_SEED_A_190_155": "762f77937becac506ada73a91922f025178aa75de75eac68706cd84eda45efd7",
        "K4_SEED_B_100_175": "64a9ebdc46039edca33ea511104e44beb8f55ff2c8c46a78d2a6bdd2d7ffa95d",
        "K9_SEED_A_195_180": "34c0506c6c0e1dbfc27e39ea29961220dd034d0d103240566235743550bddd51",
        "K9_SEED_B_205_185": "1fe9ddd28d4ab2eb9a1d9da5f06c3a12ae8bdb7e53d4d7eefd28e074159807fb",
    }
    for name in ("k4_final_comparison.csv", "k9_final_comparison.csv"):
        with (OUT / name).open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert all(row["valid_label"] == "True" and row["x_polarization"] == "True" for row in rows)
        assert all(float(row["eta_plus1_band_mean"]) > 0 for row in rows)
    for cid in ("K4_SEED_A_190_155", "K4_SEED_B_100_175", "K9_SEED_A_195_180", "K9_SEED_B_205_185"):
        assert len((LIB / cid / "spectral_metrics.csv").read_text(encoding="utf-8").splitlines()) == 12
        ledger = json.loads((LIB / cid / "entered_ledger.json").read_text(encoding="utf-8"))
        assert ledger["post_fsp_sha256"] == expected_post[cid]


def test_k6_identity_is_existing_frozen_authority():
    k6 = read("k6_traditional_final_manifest.json")["champion"]
    assert k6["source_candidate_id"] == "NP_K6X_125_135_150_175_190_210"
    assert k6["diameter_vector_nm"] == [125, 135, 150, 175, 190, 210]
    assert k6["geometry_hash"] == "aaaa5bfab2f727cca9c07754e4449cbadf70b91cdac90e6fbdd87f136a6e4b80"
    assert k6["k6_no_new_solver"] is True
    assert read("solver_zero_audit.json")["new_solver_entered"] == 0


def test_handoff_has_three_modular_control_providers():
    h = read("np_traditional_multi_target_coupling_handoff_v1.json")
    assert h["role"] == "traditional modular control provider"
    assert [(p["provider_id"], p["K"], p["Lambda_x_nm"]) for p in h["providers"]] == [
        ("NP_TRAD_K9_10DEG", 9, 2610.0),
        ("NP_TRAD_K6_15DEG", 6, 1740.0),
        ("NP_TRAD_K4_23DEG", 4, 1160.0),
    ]
    assert h["integrated_winner"] is False and h["joint_optimum"] is False
    assert read("second_batch_decision.json")["second_batch_required"] is False


def test_offline_finalizer_cannot_start_solver_or_touch_runtime():
    source = SCRIPT.read_text(encoding="utf-8")
    ast.parse(source)
    lowered = source.lower()
    assert "import lumapi" not in lowered
    assert "fdtd.run" not in lowered and ".run(" not in lowered
    assert "mpiexec" not in lowered and "start-process" not in lowered
    assert "runtime_fsp" not in lowered and "runtime_logs" not in lowered


def test_semantic_audit_and_scope_exclusions_are_explicit():
    audit = read("family_champion_semantic_audit.json")
    assert audit["issue_confirmed"] is True
    assert audit["global_does_not_overwrite_family"] is True
    p = read("provenance_audit.json")
    assert p["fsp_staged"] is False and p["runtime_staged"] is False and p["logs_staged"] is False


def test_heavy_runtime_files_are_not_staged():
    names = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    forbidden = (".fsp", "runtime_fsp", "runtime_logs", "stdout", "stderr", "exitcode", "__pycache__", ".npz")
    assert not [name for name in names if any(token in name.lower() for token in forbidden)]
