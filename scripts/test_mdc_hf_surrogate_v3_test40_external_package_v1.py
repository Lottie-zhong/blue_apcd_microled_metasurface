"""Structural regression test for the read-only V3 Test40 audit package."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


REQUIRED = {
    "membership_selection_audit.json", "solver_accounting_audit.json",
    "truth_freeze_audit.json", "physical_grid_aggregation_audit.json",
    "model_identity_audit.json", "ensemble_prediction_audit.json",
    "external_global_metrics.json", "external_topology_metrics.json",
    "external_source_strata_metrics.json", "anti_collapse_external.json",
    "generalization_gap.json", "warning_localization.json",
    "representative_profile_diagnostics.json", "individual_seed_diagnostics.json",
    "capability_synthesis.json", "replay_audit.json",
    "environment_provenance_audit.json", "artifact_sha256_manifest.json",
    "completion_manifest.json", "completion_report.md", "test_report.json",
}


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    args = ap.parse_args()
    root = Path(args.package)
    missing = sorted(name for name in REQUIRED if not (root / name).exists())
    if missing:
        raise AssertionError(f"missing package files: {missing}")
    solver = load(root / "solver_accounting_audit.json")
    truth = load(root / "truth_freeze_audit.json")
    model = load(root / "model_identity_audit.json")
    pred = load(root / "ensemble_prediction_audit.json")
    collapse = load(root / "anti_collapse_external.json")
    completion = load(root / "completion_manifest.json")
    report = load(root / "test_report.json")
    assert solver["phase_a_solver_calls"] == 240
    assert solver["accepted"] == solver["completed"] == 240
    assert solver["solver_replays"] == solver["recovery_solver_calls"] == 0
    assert truth["formal_truth_reads_after_authorization"] == 240
    assert truth["truth_reads_before_authorization"] == 0
    assert model["model_id"] == "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1"
    assert model["architecture"] == "V3-C" and model["final_epoch"] == 117
    assert len(model["checkpoint_sha256"]) == 5
    assert pred["fit_calls"] == pred["backward_calls"] == pred["optimizer_calls"] == 0
    assert pred["fresh_load_replay_match"] is True
    assert collapse["median_latent_variance_ratio"] >= 0.25
    assert collapse["collapsed_component_count"] == 0
    assert collapse["evaluation_scope"] == "case_level_240"
    assert completion["phase_a_solver_calls"] == 240 and completion["phase_c_model_fits"] == 0
    assert completion["hf15_r12_reads"] == 0 and completion["raw_artifacts_unchanged"] is True
    assert report["status"] == "PASS" and all(report["checks"].values())
    manifest = load(root / "artifact_sha256_manifest.json")
    for rel, expected in manifest["files"].items():
        assert digest(root / rel) == expected, rel
    print(json.dumps({"status": "PASS", "required_files": len(REQUIRED), "sha_entries": len(manifest["files"]), "external_collapse_warning": bool(collapse.get("formal_warning"))}, sort_keys=True))


if __name__ == "__main__":
    main()
