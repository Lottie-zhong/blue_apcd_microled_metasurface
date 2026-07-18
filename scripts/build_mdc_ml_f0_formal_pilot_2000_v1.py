"""Build the deterministic 2,000-structure F0 formal Native-M1 pilot."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_mdc_ml_f0_pilot_candidates_v1 as pre1  # noqa: E402
from mdc_ml_structure_grammar_v1 import DEFAULT_BOUNDS, GrammarError, TOPOLOGY_FAMILIES, validate_bounds  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "mdc_ml_f0_formal_pilot_2000_v1.yaml"
CATEGORY_ORDER = tuple(pre1.CATEGORY_ORDER)
CANDIDATE_REQUIRED_FIELDS = {
    "sample_id", "formal_batch_id", "source_category", "topology_family",
    "generation_seed", "generation_attempt", "bucket_index", "anchor_parent_id",
    "anchor_parent_hash", "authority_file", "authority_row", "raw_grammar_parameters",
    "canonical_material_sequence", "canonical_thickness_sequence", "layer_count",
    "total_thickness_nm", "defect_indices", "termination", "canonical_geometry_hash",
    "physical_configuration_hash", "simulation_provenance_hash", "split_group_hash",
    "pre1_canonical_collision", "pre1_physical_collision", "smoke_canonical_collision",
    "smoke_physical_collision", "collision_refill_provenance", "legality_status",
    "level", "tolerance_child", "source_medium", "exit_medium", "raw_structure",
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    return pre1.stable_hash(value)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_exclusions(config: dict[str, Any]) -> dict[str, Any]:
    pre1_dir = ROOT / config["pre1_output_directory"]
    smoke_dir = ROOT / config["smoke_output_directory"]
    pre1_rows = read_jsonl(pre1_dir / "candidate_records_v1.jsonl")
    with (smoke_dir / "smoke_structures_v1.csv").open(newline="", encoding="utf-8") as handle:
        smoke_rows = list(csv.DictReader(handle))
    anchors = pre1.load_anchor_authority(config)
    values = {
        "pre1_records": pre1_rows,
        "smoke_records": smoke_rows,
        "anchors": anchors,
        "pre1_canonical": {row["canonical_geometry_hash"] for row in pre1_rows},
        "pre1_physical": {row["physical_configuration_hash"] for row in pre1_rows},
        "smoke_canonical": {row["canonical_geometry_hash"] for row in smoke_rows},
        "smoke_physical": {row["physical_configuration_hash"] for row in smoke_rows},
        "anchor_canonical": {row["canonical_geometry_hash"] for row in anchors},
        "anchor_physical": {row["physical_configuration_hash"] for row in anchors},
    }
    if len(pre1_rows) != 512 or len(values["pre1_canonical"]) != 512 or len(values["pre1_physical"]) != 512:
        raise RuntimeError("frozen PRE1 exclusion inventory mismatch")
    if len(smoke_rows) != 17 or len(values["smoke_canonical"]) != 17:
        raise RuntimeError("frozen smoke exclusion inventory mismatch")
    if len(anchors) != 3:
        raise RuntimeError("exactly three authoritative anchors are required")
    return values


def _formal_record(
    raw: dict[str, Any], canonical: dict[str, Any], config: dict[str, Any], *,
    category: str, family: str, bucket_index: int, target_index: int,
    attempt: int, anchor: dict[str, Any] | None, rejected_before: int,
) -> dict[str, Any]:
    record = pre1._record_candidate(
        raw, canonical, config, category=category, family=family,
        bucket_index=bucket_index, attempt=attempt, anchor=anchor,
        rejected_before=rejected_before,
    )
    sample_id = f"F0_FORMAL_{pre1.CATEGORY_PREFIX[category]}_{family.upper()}_{bucket_index:04d}"
    record["sample_id"] = sample_id
    record["raw_structure"]["sample_id"] = sample_id
    record.update({
        "formal_batch_id": config["formal_batch_id"],
        "formal_target_index": target_index,
        "generation_seed": int(config["formal_seed"]),
        "authority_file": None if anchor is None else anchor["authority_file"],
        "authority_row": None if anchor is None else anchor["authority_row"],
        "pre1_canonical_collision": False,
        "pre1_physical_collision": False,
        "smoke_canonical_collision": False,
        "smoke_physical_collision": False,
        "anchor_parent_excluded_from_formal": True,
    })
    record["collision_refill_provenance"] = {
        "rejected_before_acceptance": rejected_before,
        "accepted_attempt": attempt,
        "target_index": target_index,
    }
    return record


def _jobs(config: dict[str, Any], anchors: list[dict[str, Any]]) -> list[tuple[str, str, int, dict[str, Any] | None, Callable[[int], dict[str, Any]]]]:
    seed = int(config["formal_seed"])
    jobs: list[tuple[str, str, int, dict[str, Any] | None, Callable[[int], dict[str, Any]]]] = []
    by_anchor = {row["anchor_id"]: row for row in anchors}
    for category in CATEGORY_ORDER:
        if category == "ANCHOR_NEIGHBORHOOD":
            for anchor_id, count in config["anchor_quotas"].items():
                anchor = by_anchor[anchor_id]
                for index in range(int(count)):
                    base_index = index % 32
                    cycle = index // 32
                    jobs.append((category, anchor["topology_family"], index, anchor,
                                 lambda attempt, a=anchor, i=base_index, c=cycle: pre1.propose_anchor_structure(a, i, attempt + c * 101, seed)))
            continue
        for family in TOPOLOGY_FAMILIES:
            count = int(config["family_quotas"][family][category])
            for index in range(count):
                base_index = index % 40 if category == "FAMILY_STRATIFIED_GLOBAL" else index
                cycle = index // 40 if category == "FAMILY_STRATIFIED_GLOBAL" else 0
                jobs.append((category, family, index, None,
                             lambda attempt, f=family, i=base_index, c=cycle, cat=category: pre1.propose_family_structure(seed, cat, f, i, attempt + c * 101)))
    return jobs


def build_candidates(config: dict[str, Any]) -> dict[str, Any]:
    exclusions = load_exclusions(config)
    max_attempts = int(config["proposal_limits"]["maximum_refills_per_target"])
    total_limit = int(config["proposal_limits"]["maximum_total_proposals"])
    seen_geometry: set[str] = set()
    seen_physical: set[str] = set()
    records: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    family_stats: dict[str, Counter[str]] = defaultdict(Counter)
    category_stats: dict[str, Counter[str]] = defaultdict(Counter)
    bucket_counters: Counter[tuple[str, str]] = Counter()

    for category, family, target_index, anchor, factory in _jobs(config, exclusions["anchors"]):
        accepted = False
        rejected_before = 0
        for attempt in range(max_attempts):
            stats["raw_proposals"] += 1
            family_stats[family]["raw_proposals"] += 1
            category_stats[category]["raw_proposals"] += 1
            if stats["raw_proposals"] > total_limit:
                raise RuntimeError("formal total proposal limit exceeded")
            raw = factory(attempt)
            try:
                canonical = validate_bounds(raw)
            except (GrammarError, ValueError):
                stats["invalid_rejections"] += 1
                family_stats[family]["invalid_rejections"] += 1
                category_stats[category]["invalid_rejections"] += 1
                rejected_before += 1
                continue
            geometry = canonical["canonical_geometry_hash"]
            physical = canonical["physical_configuration_hash"]
            collision = None
            if geometry in exclusions["pre1_canonical"] or physical in exclusions["pre1_physical"]:
                collision = "pre1"
            elif geometry in exclusions["smoke_canonical"] or physical in exclusions["smoke_physical"]:
                collision = "smoke"
            elif geometry in exclusions["anchor_canonical"] or physical in exclusions["anchor_physical"]:
                collision = "anchor"
            elif geometry in seen_geometry or physical in seen_physical:
                collision = "formal_duplicate"
            if collision:
                stats[f"{collision}_collisions"] += 1
                family_stats[family][f"{collision}_collisions"] += 1
                category_stats[category][f"{collision}_collisions"] += 1
                rejected_before += 1
                continue
            bucket_index = bucket_counters[(category, family)]
            bucket_counters[(category, family)] += 1
            record = _formal_record(
                raw, canonical, config, category=category, family=family,
                bucket_index=bucket_index, target_index=target_index,
                attempt=attempt, anchor=anchor, rejected_before=rejected_before,
            )
            records.append(record)
            seen_geometry.add(geometry)
            seen_physical.add(physical)
            stats["valid_proposals"] += 1
            stats["refill_count"] += attempt
            family_stats[family]["valid_proposals"] += 1
            category_stats[category]["valid_proposals"] += 1
            accepted = True
            break
        if not accepted:
            raise RuntimeError(f"unable to fill formal bucket: {category}/{family}/{target_index}")

    records.sort(key=lambda row: (
        CATEGORY_ORDER.index(row["source_category"]),
        TOPOLOGY_FAMILIES.index(row["topology_family"]),
        row["bucket_index"], row["canonical_geometry_hash"],
    ))
    source_counts = Counter(row["source_category"] for row in records)
    family_matrix = {
        family: {
            **{category: sum(row["source_category"] == category and row["topology_family"] == family for row in records) for category in CATEGORY_ORDER},
            "total": sum(row["topology_family"] == family for row in records),
        }
        for family in TOPOLOGY_FAMILIES
    }
    signature = stable_hash([{key: row[key] for key in sorted(row)} for row in records])
    audit = {
        "status": "PASS", "seed": int(config["formal_seed"]), **dict(stats),
        "final_unique_count": len(records),
        "unique_canonical_hashes": len(seen_geometry),
        "unique_physical_hashes": len(seen_physical),
        "candidate_content_signature": signature,
        "candidate_schema_status": "PASS" if all(CANDIDATE_REQUIRED_FIELDS.issubset(row) for row in records) else "FAIL",
        "source_category_counts": dict(source_counts),
        "topology_counts": family_matrix,
        "anchor_parent_counts": dict(Counter(row["anchor_parent_id"] for row in records if row["anchor_parent_id"])),
        "family_acceptance": {key: {**dict(value), "acceptance_rate": value["valid_proposals"] / value["raw_proposals"]} for key, value in family_stats.items()},
        "source_category_acceptance": {key: {**dict(value), "acceptance_rate": value["valid_proposals"] / value["raw_proposals"]} for key, value in category_stats.items()},
        "pre1_canonical_overlap": len(seen_geometry & exclusions["pre1_canonical"]),
        "pre1_physical_overlap": len(seen_physical & exclusions["pre1_physical"]),
        "smoke_canonical_overlap": len(seen_geometry & exclusions["smoke_canonical"]),
        "smoke_physical_overlap": len(seen_physical & exclusions["smoke_physical"]),
        "anchor_overlap": len(seen_geometry & exclusions["anchor_canonical"]),
        "combined_pre1_formal_canonical_unique": len(seen_geometry | exclusions["pre1_canonical"]),
        "combined_pre1_formal_physical_unique": len(seen_physical | exclusions["pre1_physical"]),
        "level_b_count": sum(row["level"] != "A" for row in records),
        "tolerance_child_count": sum(bool(row["tolerance_child"]) for row in records),
        "integer_thickness_rate": sum(all(isinstance(value, int) and not isinstance(value, bool) for value in row["canonical_thickness_sequence"]) for row in records) / len(records),
        "legality_rate": sum(row["legality_status"] == "PASS" for row in records) / len(records),
        "source_material_rate": sum(row["source_medium"] == "APCD_GAN_NATIVE_M1" for row in records) / len(records),
        "exit_material_rate": sum(row["exit_medium"] == "AIR" for row in records) / len(records),
    }
    return {"records": records, "anchors": exclusions["anchors"], "audit": audit, "signature": signature}


def validate_static_gate(result: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    audit = result["audit"]
    checks: dict[str, bool] = {
        "formal_count_2000": len(result["records"]) == 2000,
        "formal_canonical_unique_2000": audit["unique_canonical_hashes"] == 2000,
        "formal_physical_unique_2000": audit["unique_physical_hashes"] == 2000,
        "pre1_canonical_overlap_zero": audit["pre1_canonical_overlap"] == 0,
        "pre1_physical_overlap_zero": audit["pre1_physical_overlap"] == 0,
        "smoke_overlap_zero": audit["smoke_canonical_overlap"] == 0 and audit["smoke_physical_overlap"] == 0,
        "anchor_overlap_zero": audit["anchor_overlap"] == 0,
        "combined_canonical_unique_2512": audit["combined_pre1_formal_canonical_unique"] == 2512,
        "combined_physical_unique_2512": audit["combined_pre1_formal_physical_unique"] == 2512,
        "candidate_schema_pass": audit["candidate_schema_status"] == "PASS",
        "integer_nm_100_percent": audit["integer_thickness_rate"] == 1.0,
        "legality_100_percent": audit["legality_rate"] == 1.0,
        "source_100_percent": audit["source_material_rate"] == 1.0,
        "exit_100_percent": audit["exit_material_rate"] == 1.0,
        "level_b_zero": audit["level_b_count"] == 0,
        "tolerance_child_zero": audit["tolerance_child_count"] == 0,
        "anchor_distribution_exact": audit["anchor_parent_counts"] == config["anchor_quotas"],
    }
    for category, expected in config["source_quotas"].items():
        checks[f"source_{category}_{expected}"] = audit["source_category_counts"].get(category) == expected
    for family in TOPOLOGY_FAMILIES:
        actual = audit["topology_counts"][family]
        expected = config["family_quotas"][family]
        checks[f"family_{family}_exact"] = actual == expected and actual["total"] >= 200
    for row in result["records"]:
        checks.setdefault("layer_count_bounds", True)
        checks.setdefault("total_thickness_bounds", True)
        checks.setdefault("defect_count_bounds", True)
        checks["layer_count_bounds"] &= DEFAULT_BOUNDS["layer_count"][0] <= row["layer_count"] <= DEFAULT_BOUNDS["layer_count"][1]
        checks["total_thickness_bounds"] &= DEFAULT_BOUNDS["total_thickness_nm"][0] <= row["total_thickness_nm"] <= DEFAULT_BOUNDS["total_thickness_nm"][1]
        checks["defect_count_bounds"] &= 1 <= len(row["defect_indices"]) <= 2
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def write_candidate_outputs(result: dict[str, Any], config: dict[str, Any]) -> None:
    out = ROOT / config["output_directory"]
    out.mkdir(parents=True, exist_ok=True)
    public_anchors = [{key: value for key, value in row.items() if key != "raw_structure"} for row in result["anchors"]]
    pre1.write_json(out / "candidate_manifest_v1.json", {
        "contract_id": config["contract_id"], "formal_batch_id": config["formal_batch_id"],
        "expected_head": config["expected_head"], "candidate_count": len(result["records"]),
        "candidate_content_signature": result["signature"], "anchors": public_anchors,
        "static_gate": validate_static_gate(result, config),
        "schema": {"id": "mdc_ml_f0_formal_candidate_manifest_v1", "required_fields": sorted(CANDIDATE_REQUIRED_FIELDS)},
    })
    pre1.write_jsonl(out / "candidate_records_v1.jsonl", result["records"])
    pre1.write_csv(out / "candidate_summary_v1.csv", [{key: value for key, value in row.items() if key not in ("raw_structure", "raw_grammar_parameters")} for row in result["records"]])
    pre1.write_json(out / "candidate_generation_audit_v1.json", result["audit"])
    (out / "candidate_content_signature_v1.txt").write_text(result["signature"] + "\n", encoding="ascii", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    first = build_candidates(config)
    second = build_candidates(config)
    deterministic = first["signature"] == second["signature"] and first["records"] == second["records"]
    first["audit"]["deterministic_rebuild"] = "PASS" if deterministic else "FAIL"
    first["audit"]["second_rebuild_signature"] = second["signature"]
    gate = validate_static_gate(first, config)
    gate["checks"]["deterministic_rebuild"] = deterministic
    gate["status"] = "PASS" if all(gate["checks"].values()) else "FAIL"
    if gate["status"] != "PASS":
        raise RuntimeError(f"formal candidate static gate failed: {gate}")
    if not args.no_write:
        write_candidate_outputs(first, config)
    print(json.dumps({"status": "PASS", "signature": first["signature"], "audit": first["audit"], "static_gate": gate}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
