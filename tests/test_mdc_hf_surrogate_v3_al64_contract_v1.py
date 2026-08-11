"""Metadata-only AL64 contract tests; no solver, labels, or training are used."""
from __future__ import annotations

import csv
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CONTRACTS = REPO / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1"
SCRIPTS = REPO / "scripts"


def rows(name):
    with (CONTRACTS / name).open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def test_al64_manifest_has_frozen_counts_and_strata():
    geoms = rows("v3_al64_geometry_manifest_v1.csv")
    assert len(geoms) == 64
    assert {r["topology_family"] for r in geoms} == {"Explicit", "ZL1", "ZL2"}
    assert all(r["future_case_count"] == "6" for r in geoms)


def test_al64_case_matrix_is_geometry_grouped_six_case_complete():
    cases = rows("v3_al64_future_case_matrix_v1.csv")
    assert len(cases) == 384
    assert len({r["case_uid"] for r in cases}) == 384
    by_geom = {}
    for row in cases:
        by_geom.setdefault(row["geometry_id"], []).append(row)
    assert len(by_geom) == 64
    assert all(len(v) == 6 for v in by_geom.values())
    assert all({r["source_position"] for r in v} == {"top", "centroid", "bottom"} for v in by_geom.values())
    assert all({r["dipole_orientation"] for r in v} == {"x", "z"} for v in by_geom.values())


def test_runner_is_solver_only_and_has_no_training_or_label_reads():
    source = (SCRIPTS / "run_mdc_hf_surrogate_v3_al64_joint_profile_v1.py").read_text(encoding="utf-8")
    assert "model_fits" in source and "optimizer_backward" in source
    assert "HF15_formal_reads" in source and "test40_reads" in source
    assert "V3_Test40" not in source and "v3_test40_labels" not in source.lower()
    assert "solver_entered" in source and "recovery_solver_calls" in source


def test_finalizer_is_extraction_only_and_frozen_aggregation():
    source = (SCRIPTS / "finalize_mdc_hf_surrogate_v3_al64_dataset_v1.py").read_text(encoding="utf-8")
    assert "solver" in source.lower()
    assert "raw x/z average per source position" in source
    assert "normalize after aggregation" in source
    assert "V3_Test40_truth_reads" in source
    assert "HF15_formal_reads" in source


def test_finalizer_uses_frozen_radian_closure_and_emits_audits():
    source = (SCRIPTS / "finalize_mdc_hf_surrogate_v3_al64_dataset_v1.py").read_text(encoding="utf-8")
    assert "np.radians(lam)" in source
    assert "al64_case_quality_audit_v1.json" in source
    assert "al64_manifest_integrity_audit_v1.json" in source
    assert "al64_v3_development_membership_audit_v1.json" in source
