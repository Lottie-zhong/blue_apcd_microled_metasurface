"""Lightweight regression checks for the read-only V3 OOF synthesis package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True, type=Path)
    args = ap.parse_args()
    p = args.package
    cand = load(p / "candidate_A_B_C_comparison.json")
    assert [x["candidate_id"] for x in cand["rows"]] == ["V3-A", "V3-B", "V3-C"]
    assert cand["selection"]["evaluation_level"] == "geometry"
    assert cand["selection"]["case_level_metrics_override_geometry_level"] is False
    assert cand["composite_definition"].startswith("promotion_result")
    assert all(x["eligibility"]["fit_matrix"]["observed"] == 15 for x in cand["rows"])
    topo = load(p / "topology_comparison.json")
    assert {x["topology"] for x in topo["rows"]} == {"Explicit", "ZL1", "ZL2"}
    assert {x["geometry_count"] for x in topo["rows"]} == {13, 14}
    assert max(topo["rows"], key=lambda x: x["profile_composite"])["topology"] == "ZL2"
    strata = load(p / "strata_comparison.json")
    assert len(strata["topology_orientation"]) >= 6
    assert len(strata["topology_source_position"]) >= 9
    assert strata["weighted_L1_comparability"] == "NOT_DIRECTLY_COMPARABLE_TO_FROZEN_V2_REFERENCE"
    epochs = load(p / "epoch_distribution.json")["summary"]
    assert epochs["count"] == 15 and epochs["count_at_50"] == 0 and epochs["count_eq_400"] == 0
    assert epochs["authoritative_E_final"] == 117
    v2v3 = load(p / "v2_vs_v3_failure_mechanism_table.json")["v3_c"]
    assert v2v3["weighted_L1"]["status"] == "NOT_DIRECTLY_COMPARABLE"
    assert v2v3["collapsed_components"]["v3_c"] == "0/32"
    warnings = load(p / "warning_localization.json")
    assert all(x["weighted_L1_comparability"] == "NOT_DIRECTLY_COMPARABLE" for x in warnings["all_policy_records"])
    capability = load(p / "capability_synthesis.json")
    assert "absolute power prediction" in capability["not_yet_supported"]
    decision = load(p / "v3_test40_decision_support.json")
    assert decision["recommendation_scope"].startswith("decision_support_only")
    assert load(p / "provenance.json")["test40_truth_reads_in_this_script"] == 0
    manifest = load(p / "artifact_sha256_manifest.json")
    for row in manifest["files"]:
        h = hashlib.sha256((p / row["path"]).read_bytes()).hexdigest()
        assert h == row["sha256"], row["path"]
    print(json.dumps({"status": "PASS", "checks": 18}, indent=2))


if __name__ == "__main__":
    main()
