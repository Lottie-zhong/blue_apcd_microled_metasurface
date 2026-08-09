import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML = ROOT / "outputs/lp_ml_dataset_v1"
PKG = ML / "execution_packages/lp_5d_phase_reachability_probe_v2"
STG = ML / "staging/lp_5d_phase_reachability_probe_v2"
AN = ML / "analysis"
PROTECTED = [
    ROOT / "reports/lp_ml1a3_git_history_geometry_reconstruction.md",
    ROOT / "reports/stage11_4a20_legacy_fsp_object_inventory.md",
]


def j(path):
    return json.loads(path.read_text(encoding="utf8"))


def test_frozen24_manifest_and_roles():
    m = j(PKG / "frozen_execution_manifest_v1.json")
    assert m["candidate_count"] == 24
    assert len(m["candidates"]) == 24
    assert len({r["exact_geometry_hash_sha256"] for r in m["candidates"]}) == 24
    assert m["role_counts"] == {
        "LOW_PHASE_EXTREME": 6,
        "HIGH_PHASE_EXTREME": 6,
        "PHASE_PROJECTOR_TRADEOFF": 4,
        "5D_BOUNDARY_SPARSE_REGION": 4,
        "DISAGREEMENT_PHYSICS_CONTROL": 4,
    }
    assert m["candidate_count"] == len(m["candidate_order"])
    assert all(r["wavelength_nm"] == 450.0 for r in m["candidates"])
    assert m["no_d9"] is True
    assert all(r["checks"]["r1_quarantine_free"] for r in m["candidates"])


def test_execution_contract_and_accounting():
    c = j(PKG / "execution_contract_v1.json")
    a = j(STG / "solver_accounting.json")
    assert c["status"] == "AUTHORIZED_FOR_EXPLICIT_EXECUTION"
    assert c["max_entered"] == 48
    assert c["wavelength_nm_only"] == [450.0]
    assert c["no_replacement"] and c["no_auto_retry_entered"]
    assert a["status"] == "PASS"
    assert a["counts"] == {
        "planned": 48,
        "raw_invocations": 48,
        "successful": 48,
        "accepted": 48,
        "recovered": 0,
        "failed": 0,
        "missing": 0,
        "duplicate_invocation": 0,
        "unauthorized": 0,
        "pre_solver_compatibility_stops": 0,
    }
    assert len(a["subruns"]) == 48
    assert all(r["solver_entered"] and r["accepted"] for r in a["subruns"])
    assert [r["polarization"] for r in a["subruns"][:2]] == ["x", "y"]


def test_formal_xy_and_phase_only_scope():
    with (STG / "formal_subruns.csv").open(encoding="utf8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 48
    assert len({r["formal_subrun_key"] for r in rows}) == 48
    assert {r["input_polarization"] for r in rows} == {"x", "y"}
    phases = list(csv.DictReader((AN / "lp_5d_phase_reachability_probe_x_phase_evidence_v1.csv").open(encoding="utf8", newline="")))
    jones = list(csv.DictReader((AN / "lp_5d_phase_reachability_probe_complete_jones_v1.csv").open(encoding="utf8", newline="")))
    assert len(phases) == 24
    assert len(jones) == 24
    assert {r["phase_evidence_label"] for r in phases} == {"PHASE_ONLY_REACHABILITY_PHYSICS"}
    assert {r["full_jones_label"] for r in jones} == {"FULL_JONES_REACHABILITY_PHYSICS"}
    assert all(float(r["phase_deg"]) >= 0 and float(r["phase_deg"]) < 360 for r in phases)
    checkpoints = list(STG.glob("subruns/*/*/checkpoint.json"))
    assert len(checkpoints) == 48
    for path in checkpoints:
        cp = j(path)
        assert cp["wavelength_nm"] == 450.0
        assert cp["source_T"] > 0.0
        assert cp["normalization_scale"] > 0.0
        assert set(cp["weighted_G0_Ex"]) == {"real", "imag"}
        assert set(cp["weighted_G0_Ey"]) == {"real", "imag"}
        assert not any(k.startswith("predicted_") or k.startswith("model_prediction") for k in cp)


def test_projector_formula_and_physics_scope():
    rows = list(csv.DictReader((AN / "lp_5d_phase_reachability_probe_complete_jones_v1.csv").open(encoding="utf8", newline="")))
    assert all(float(r["projection_error_consistency_abs_error"]) < 1e-10 for r in rows)
    assert all(r["projector_lineage"] == "projector_preserved_from_backbone" for r in rows)
    assert all("predicted" not in r for r in rows for _ in [0])
    d = j(AN / "lp_5d_phase_reachability_probe_level3_evidence_decision_v1.json")
    assert d["solver_calls"] == 48
    assert d["no_d9"] and d["no_new_geometry"] and d["no_retraining"]


def test_envelope_sector_and_boundary_outputs():
    e = j(AN / "lp_5d_phase_reachability_probe_raw_phase_envelope_comparison_v1.json")
    s = j(AN / "lp_5d_phase_reachability_probe_60deg_sector_diagnostic_v1.json")
    b = j(AN / "lp_5d_phase_reachability_probe_boundary_saturation_v1.json")
    assert e["OLD_SUPPORT"]["count"] == 409
    assert e["NEW_PROBE_ONLY"]["count"] == 24
    assert e["COMBINED_SUPPORT"]["count"] == 433
    assert s["phase_only_sector_count"] == 1
    assert s["full_jones_sector_count"] == 1
    assert b["boundary_saturation_detected"] is True


def test_protected_hashes_and_no_heavy_artifacts():
    p = j(STG / "protected_hash_audit.json")
    assert p["unchanged"] is True
    assert all(p["before"][str(x)] == p["after"][str(x)] for x in PROTECTED)
    assert not list(STG.rglob("*.fsp"))
    assert not list(STG.rglob("*.h5"))
    assert not list(STG.rglob("*.mat"))
    assert not list(STG.rglob("*.npy"))


def test_lightweight_hash_manifests():
    package_checks = j(PKG / "content_checksums_v1.json")
    for item in package_checks["files"]:
        h = hashlib.sha256((PKG / item["path"]).read_bytes()).hexdigest()
        assert h == item["sha256"]
    output_checks = j(AN / "lp_5d_phase_reachability_probe_output_checksums_v1.json")
    assert output_checks["status"] == "PASS"
    assert output_checks["solver_calls"] == 48
    for item in output_checks["files"]:
        path = Path(item["path"])
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
