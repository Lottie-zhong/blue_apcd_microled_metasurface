import csv
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = ROOT / "outputs/lp_ml_dataset_v1"
P = O / "plans/lp_ml_six_bin_inverse_search_v1"
QID = "LPML_R1_GLOBAL_SOBOL_054"


def j(name):
    return json.loads((P / name).read_text(encoding="utf-8"))


def csvrows(name):
    with (P / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_execution_manifest_is_frozen_and_offline():
    m = j("lp_ml_six_bin_inverse_execution_manifest_v1.json")
    assert m["solver_authorized"] is False
    assert m["solver_calls"] == 0
    assert m["candidate_generation"] is True
    assert m["new_physics"] is False
    assert m["frozen_test_used_for_tuning"] is False
    assert m["geometry_054_rows"] == 0
    assert m["selected_blend_alpha"] == 0.95


def test_candidate_pool_has_six_bins_and_unique_surrogate_hashes():
    rows = csvrows("lp_ml_six_bin_candidate_pool_v1.csv")
    assert len(rows) > 0
    assert {int(r["target_bin"]) for r in rows} == set(range(6))
    assert len({r["candidate_id"] for r in rows}) == len(rows)
    assert len({r["exact_surrogate_hash"] for r in rows}) == len(rows)
    assert len({r["canonical_surrogate_hash"] for r in rows}) == len(rows)
    assert len({r["symmetry_surrogate_hash"] for r in rows}) == len(rows)
    assert not any(r["candidate_id"] == QID for r in rows)
    assert all(r["physics_origin"] == "SURROGATE_PREDICTION_NOT_PHYSICS" for r in rows)
    assert all(r["hash_status"] == "PLANNED_SURROGATE_IDENTITY_NOT_FORMAL_GEOMETRY_HASH" for r in rows)
    assert all(r["manufacturing_pass"] == "True" for r in rows)


def test_search_coverage_and_risk_audit_are_explicit():
    risk = j("lp_ml_six_bin_model_consensus_risk_audit_v1.json")
    assert set(risk["per_bin"]) == {str(i) for i in range(6)}
    assert risk["test_guided"] is False
    assert risk["threshold_source"] == "train/validation-only model disagreement scales"
    assert sum(v["count"] for v in risk["per_bin"].values()) == risk["candidate_count"]
    # High-risk bins must remain visible; they cannot be silently promoted.
    assert any(v["high"] > 0 for v in risk["per_bin"].values())


def test_gradient_and_derivative_free_coverage():
    g = j("lp_ml_six_bin_gradient_search_summary_v1.json")
    d = j("lp_ml_six_bin_derivative_free_search_summary_v1.json")
    assert g["coarse_initializations_per_offset_bin"] == 128
    assert len(g["summary"]) == 72
    assert g["test_guided"] is False
    assert d["starts_per_bin"] == 32
    assert d["bins"] == 6
    assert d["solver_calls"] == 0


def test_tuple_front_and_future_budget_are_planning_only():
    t = j("lp_ml_six_tuple_pareto_front_v1.json")
    b = j("lp_ml_six_bin_future_fdtd_shortlist_proposal_v1.json")
    r = j("lp_ml_six_bin_round3_need_assessment_v1.json")
    assert t["tuple_count"] > 0
    assert t["best_tuple"]["all_bins_covered"] is True
    assert b["authorization"] == "NOT_AUTHORIZED_BY_THIS_TASK"
    assert b["solver_calls"] == 0
    assert r["round3_execution"] == "NOT_RUN_AND_NOT_AUTHORIZED"


def test_known_control_library_is_separate_and_complete():
    rows = csvrows("lp_ml_six_bin_known_physics_control_library_v1.csv")
    assert len(rows) == 2871
    assert len({r["candidate_id"] for r in rows}) == 319
    counts = {}
    for r in rows:
        counts[r["candidate_id"]] = counts.get(r["candidate_id"], 0) + 1
        assert r["control_status"] == "KNOWN_PHYSICS_CONTROL"
        assert r["physics_origin"] != "SURROGATE_PREDICTION_NOT_PHYSICS"
        for field in ("spectral_drift_deg", "spectral_slope_rad_per_sample", "spectral_curvature_rad_per_sample2", "throughput_variation"):
            assert field in r
    assert set(counts.values()) == {9}


def test_no_solver_or_heavy_solver_artifacts():
    manifest = j("lp_ml_six_bin_inverse_execution_manifest_v1.json")
    assert manifest["solver_calls"] == 0
    assert not any(p.suffix.lower() in {".fsp", ".fspx", ".ldf", ".h5", ".mat", ".npy", ".npz"} for p in P.rglob("*"))
    assert not any("solver" in p.name.lower() and p.suffix.lower() not in {".json", ".csv"} for p in P.rglob("*"))


def test_output_checksum_manifest_is_complete():
    c = j("lp_ml_six_bin_inverse_search_checksums_v1.json")
    m = j("lp_ml_six_bin_inverse_execution_manifest_v1.json")
    assert c["solver_calls"] == 0
    assert c["physics_dataset_modified"] is False
    assert c["model_checkpoint_modified"] is False
    assert len(c["artifact_sha256"]) >= 17
    for rel, digest in c["artifact_sha256"].items():
        path = ROOT / rel
        assert path.exists(), rel
        assert len(digest) == 64
    assert m["checksums_manifest"].endswith("lp_ml_six_bin_inverse_search_checksums_v1.json")
