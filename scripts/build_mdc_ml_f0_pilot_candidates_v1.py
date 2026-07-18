"""Build the deterministic, solver-free 512-candidate F0 pilot calibration set."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mdc_ml_structure_grammar_v1 import (  # noqa: E402
    DEFAULT_BOUNDS,
    MATERIAL_PROVENANCE,
    TOPOLOGY_FAMILIES,
    GrammarError,
    simulation_provenance_hash,
    validate_bounds,
)

CONFIG_PATH = ROOT / "configs" / "mdc_ml_f0_pilot_calibration_v1.yaml"
CATEGORY_ORDER = (
    "FAMILY_STRATIFIED_GLOBAL",
    "ANCHOR_NEIGHBORHOOD",
    "FAMILY_CHALLENGE",
    "RARE_CROSS_FAMILY",
)
CATEGORY_PREFIX = {
    "FAMILY_STRATIFIED_GLOBAL": "GLOBAL",
    "ANCHOR_NEIGHBORHOOD": "ANCHOR",
    "FAMILY_CHALLENGE": "CHALLENGE",
    "RARE_CROSS_FAMILY": "RARE",
}
CANDIDATE_REQUIRED_FIELDS = {
    "sample_id", "source_category", "topology_family", "generation_seed",
    "generation_attempt", "bucket_index", "anchor_parent_id", "anchor_parent_hash",
    "raw_grammar_parameters", "raw_structure", "canonical_material_sequence",
    "canonical_thickness_sequence", "layer_count", "total_thickness_nm",
    "defect_indices", "defect_thickness_nm", "termination",
    "canonical_geometry_hash", "physical_configuration_hash",
    "simulation_provenance_hash", "split_group_hash", "collision_refill_provenance",
    "legality_status", "level", "tolerance_child", "source_medium", "exit_medium",
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return ""
    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{key: _csv_value(row.get(key)) for key in keys} for row in rows])


def _layer(token: str, thickness: int, *, defect: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"material_token": token, "thickness_nm": int(thickness)}
    if defect:
        result["is_defect"] = True
    return result


def _alternating(count: int, start: str, h_nm: int, l_nm: int, offsets: list[int] | None = None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    offsets = offsets or [0]
    for index in range(count):
        token = start if index % 2 == 0 else ("L" if start == "H" else "H")
        base = h_nm if token == "H" else l_nm
        result.append(_layer(token, base + offsets[index % len(offsets)]))
    return result


def _seeded_rng(seed: int, *parts: Any) -> random.Random:
    digest = stable_hash([seed, *parts])
    return random.Random(int(digest[:16], 16))


def _parameter_draw(seed: int, category: str, family: str, index: int, attempt: int) -> tuple[int, int, int, int]:
    rng = _seeded_rng(seed, category, family, index, attempt)
    if category == "FAMILY_STRATIFIED_GLOBAL":
        stratum = index // 10
        pair_options = ((2, 3), (3, 4), (5, 6), (2, 4, 6))[stratum]
        pair = pair_options[(index + attempt) % len(pair_options)]
    elif category == "FAMILY_CHALLENGE":
        pair = (2, 6, 2, 5, 3, 4, 5, 3)[index % 8]
    else:
        pair = (2, 5, 3, 6)[index % 4]
    if pair <= 2:
        h_nm, l_nm, defect_nm = rng.randint(40, 85), rng.randint(65, 140), rng.randint(130, 480)
    elif pair <= 4:
        h_nm, l_nm, defect_nm = rng.randint(32, 68), rng.randint(55, 108), rng.randint(125, 400)
    else:
        h_nm, l_nm, defect_nm = rng.randint(25, 54), rng.randint(40, 84), rng.randint(120, 300)
    if category == "FAMILY_CHALLENGE":
        if index == 2:
            family_offset = TOPOLOGY_FAMILIES.index(family)
            pair, h_nm, l_nm, defect_nm = 2, 45 + family_offset + attempt % 5, 50 + 2 * family_offset + attempt % 7, 120
        elif index == 3:
            family_offset = TOPOLOGY_FAMILIES.index(family)
            pair, h_nm, l_nm, defect_nm = 5, 54 + family_offset + attempt % 4, 90 + 2 * family_offset + attempt % 6, 360 + family_offset + attempt
            if family == "dual_defect":
                h_nm, l_nm, defect_nm = 40 + attempt % 4, 65 + attempt % 6, 400 + attempt % 20
        elif index == 4:
            defect_nm = 120
        elif index == 5:
            defect_nm = 500
    return pair, h_nm, l_nm, defect_nm


def propose_family_structure(seed: int, category: str, family: str, index: int, attempt: int) -> dict[str, Any]:
    pair, h_nm, l_nm, defect_nm = _parameter_draw(seed, category, family, index, attempt)
    rng = _seeded_rng(seed, "family", category, family, index, attempt)
    parameters: dict[str, Any] = {
        "sampling_category": category,
        "sampling_profile": index // 10 if category == "FAMILY_STRATIFIED_GLOBAL" else index,
    }
    if family == "symmetric_periodic":
        left = _alternating(2 * pair, "H", h_nm, l_nm)
        defect = [_layer("H", defect_nm)]
        right = list(reversed(deepcopy(left)))
    elif family in ("asymmetric_pair_count", "off_center_defect"):
        left_pairs = max(2, min(5, pair - 1 if pair >= 5 else pair))
        right_pairs = min(6, left_pairs + 1)
        left = _alternating(2 * left_pairs, "H", h_nm, l_nm)
        defect = [_layer("H", defect_nm)]
        right = list(reversed(_alternating(2 * right_pairs, "H", h_nm, l_nm)))
        if family == "off_center_defect":
            parameters["defect_offset_layers"] = len(left) - len(right)
    elif family == "grouped_chirped":
        amplitude = 2 + (index + attempt) % 7
        offsets = [-amplitude, 0, amplitude]
        left = _alternating(2 * pair, "H", h_nm, l_nm, offsets)
        defect = [_layer("H", defect_nm)]
        right = list(reversed(deepcopy(left)))
        parameters["chirp_parameters"] = {"groups": ["outer", "middle", "inner"], "offset_nm": offsets}
    elif family == "dual_defect":
        pair = min(pair, 5)
        left = _alternating(2 * pair, "H", h_nm, l_nm)
        second = max(120, min(500, defect_nm + ((index + attempt) % 9) - 4))
        defect = [_layer("H", defect_nm, defect=True), _layer("L", l_nm), _layer("H", second, defect=True)]
        right = list(reversed(deepcopy(left)))
        parameters["defect_spacing_layers"] = 1
    elif family == "termination_reversed":
        left = _alternating(2 * pair, "L", h_nm, l_nm)
        defect = [_layer("L", defect_nm)]
        right = list(reversed(deepcopy(left)))
        parameters["termination_reversed"] = True
    elif family == "locally_aperiodic":
        amplitude = 2 + (index + attempt) % 8
        offsets = [0, amplitude, 0, -amplitude]
        left = _alternating(2 * pair, "H", h_nm, l_nm, offsets)
        defect = [_layer("H", defect_nm)]
        right = list(reversed(_alternating(2 * pair, "H", h_nm, l_nm, list(reversed(offsets)))))
        parameters["local_aperiodic_indices"] = [1, min(3, len(left) - 1)]
    elif family == "hybrid_periodic_aperiodic":
        amplitude = 3 + (index + attempt) % 7
        offsets = [0, 0, amplitude, -amplitude]
        left = _alternating(2 * pair, "H", h_nm, l_nm, offsets)
        defect = [_layer("H", defect_nm)]
        right = list(reversed(_alternating(2 * pair, "H", h_nm, l_nm)))
        parameters.update({"hybrid_components": ["periodic", "locally_aperiodic"], "local_aperiodic_indices": [2, 3]})
    else:  # pragma: no cover - frozen enum controls this branch
        raise GrammarError(f"unsupported topology family: {family}")
    parameters["family_specific_strength"] = rng.randint(1, 9)
    if family == "asymmetric_pair_count":
        parameters["left_right_pair_difference"] = (len(right) - len(left)) // 2
    return {
        "sample_id": "PROPOSAL",
        "topology_family": family,
        "left_mirror": left,
        "defect_region": defect,
        "right_mirror": right,
        "parameters": parameters,
    }


def _parse_sequence(text: str) -> list[dict[str, Any]]:
    layers = []
    for item in text.split():
        if len(item) < 2 or item[0] not in "HL":
            raise RuntimeError(f"invalid authoritative layer token: {item!r}")
        layers.append(_layer(item[0], int(item[1:])))
    return layers


def load_anchor_authority(config: dict[str, Any], authority_path: Path | None = None) -> list[dict[str, Any]]:
    settings = config["anchors"]
    path = authority_path or ROOT / settings["authority_file"]
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    indexed = {row["static_structure_id"]: (line, row) for line, row in enumerate(rows, start=2)}
    anchors: list[dict[str, Any]] = []
    for requested in settings["preferred"]:
        anchor_id = requested["id"]
        if anchor_id not in indexed:
            continue
        line, row = indexed[anchor_id]
        layers = _parse_sequence(row["sequence_GaN_to_Air"])
        center_text = row.get("effective_center_nm") or row.get("C_nm")
        if not center_text:
            raise RuntimeError(f"authority row lacks center thickness: {anchor_id}")
        center = int(float(center_text))
        matches = [index for index, layer in enumerate(layers) if layer["thickness_nm"] == center]
        if len(matches) != 1:
            raise RuntimeError(f"authority row center is ambiguous: {anchor_id}")
        defect_index = matches[0]
        family = requested["family"]
        parameters: dict[str, Any] = {"authority_anchor_id": anchor_id}
        if family == "off_center_defect":
            parameters["defect_offset_layers"] = defect_index - (len(layers) - defect_index - 1)
        raw = {
            "sample_id": anchor_id,
            "topology_family": family,
            "left_mirror": deepcopy(layers[:defect_index]),
            "defect_region": deepcopy(layers[defect_index:defect_index + 1]),
            "right_mirror": deepcopy(layers[defect_index + 1:]),
            "parameters": parameters,
        }
        canonical = validate_bounds(raw)
        anchors.append({
            "anchor_id": anchor_id,
            "topology_family": family,
            "authority_file": settings["authority_file"],
            "authority_row": line,
            "authority_legacy_geometry_hash": row.get("geometry_hash"),
            "canonical_geometry_hash": canonical["canonical_geometry_hash"],
            "physical_configuration_hash": canonical["physical_configuration_hash"],
            "source_medium": canonical["source_medium"],
            "exit_medium": canonical["exit_medium"],
            "material_sequence": [layer["material_id"] for layer in canonical["layers"]],
            "thickness_sequence_nm": canonical["thickness_nm"],
            "raw_structure": raw,
        })
    if len(anchors) < 2:
        missing = [item["id"] for item in settings["preferred"] if item["id"] not in indexed]
        raise RuntimeError(f"fewer than two authoritative anchors found; missing={missing}")
    return anchors


def propose_anchor_structure(anchor: dict[str, Any], index: int, attempt: int, seed: int) -> dict[str, Any]:
    raw = deepcopy(anchor["raw_structure"])
    rng = _seeded_rng(seed, "anchor", anchor["anchor_id"], index, attempt)
    deltas = (-16, -12, -8, -5, -3, 3, 5, 8, 12, 16)
    dh = deltas[(index + attempt + rng.randrange(len(deltas))) % len(deltas)]
    dl = deltas[(2 * index + attempt + rng.randrange(len(deltas))) % len(deltas)]
    dd = deltas[(3 * index + attempt + rng.randrange(len(deltas))) % len(deltas)] * (1 + index // 16)
    for section in ("left_mirror", "right_mirror"):
        for layer in raw[section]:
            change = dh if layer["material_token"] == "H" else dl
            layer["thickness_nm"] += change
    for layer in raw["defect_region"]:
        layer["thickness_nm"] += dd
    raw["sample_id"] = "PROPOSAL"
    raw["parameters"].update({
        "anchor_parent_id": anchor["anchor_id"],
        "anchor_parent_hash": anchor["canonical_geometry_hash"],
        "nominal_neighborhood_deltas_nm": {"H": dh, "L": dl, "defect": dd},
        "neighborhood_scale": ("small", "medium", "large", "mixed")[index // 8],
    })
    return raw


def _record_candidate(
    raw: dict[str, Any], canonical: dict[str, Any], config: dict[str, Any], *,
    category: str, family: str, bucket_index: int, attempt: int,
    anchor: dict[str, Any] | None, rejected_before: int,
) -> dict[str, Any]:
    physics = config["physics"]
    combined_wavelength_id = config["grids"]["spectral"]["id"] + "+" + config["grids"]["apcd_ready"]["id"]
    combined_angle_id = config["grids"]["angular"]["id"] + "+" + config["grids"]["apcd_ready"]["id"]
    provenance = simulation_provenance_hash(
        physical_configuration_hash_value=canonical["physical_configuration_hash"],
        wavelength_grid_id=combined_wavelength_id,
        angle_grid_id=combined_angle_id,
        angle_convention_id=physics["angle_convention_id"],
        solver_id=physics["solver_id"],
        solver_version=physics["solver_version"],
        polarization_contract_id=physics["polarization_contract_id"],
        numerical_settings_contract_id=physics["numerical_settings_contract_id"],
    )
    sample_id = f"F0_PRE1_{CATEGORY_PREFIX[category]}_{family.upper()}_{bucket_index:03d}"
    raw_public = deepcopy(raw)
    raw_public["sample_id"] = sample_id
    return {
        "sample_id": sample_id,
        "source_category": category,
        "topology_family": family,
        "generation_seed": int(config["seed"]),
        "generation_attempt": attempt,
        "bucket_index": bucket_index,
        "anchor_parent_id": None if anchor is None else anchor["anchor_id"],
        "anchor_parent_hash": None if anchor is None else anchor["canonical_geometry_hash"],
        "raw_grammar_parameters": deepcopy(raw.get("parameters", {})),
        "raw_structure": raw_public,
        "canonical_material_sequence": [layer["material_id"] for layer in canonical["layers"]],
        "canonical_material_tokens": canonical["material_tokens"],
        "canonical_thickness_sequence": canonical["thickness_nm"],
        "layer_count": canonical["layer_count"],
        "total_thickness_nm": canonical["total_thickness_nm"],
        "defect_indices": canonical["defect_indices"],
        "defect_count": canonical["defect_count"],
        "defect_thickness_nm": canonical["defect_thickness_nm"],
        "termination": canonical["termination"],
        "canonical_geometry_hash": canonical["canonical_geometry_hash"],
        "physical_configuration_hash": canonical["physical_configuration_hash"],
        "simulation_provenance_hash": provenance,
        "split_group_hash": canonical["split_group_hash"],
        "sequence_hash": canonical["sequence_hash"],
        "collision_refill_provenance": {"rejected_before_acceptance": rejected_before, "accepted_attempt": attempt},
        "legality_status": "PASS",
        "level": "A",
        "tolerance_child": False,
        "nominal": True,
        "source_medium": canonical["source_medium"],
        "exit_medium": canonical["exit_medium"],
        "material_policy_id": MATERIAL_PROVENANCE["material_policy_id"],
    }


def _quantiles(values: list[int | float]) -> dict[str, float]:
    ordered = sorted(float(value) for value in values)
    def at(q: float) -> float:
        position = q * (len(ordered) - 1)
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = position - lower
        return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
    return {"min": ordered[0], "p10": at(0.10), "p25": at(0.25), "p50": at(0.50), "p75": at(0.75), "p90": at(0.90), "max": ordered[-1]}


def build_candidates(config: dict[str, Any]) -> dict[str, Any]:
    seed = int(config["seed"])
    anchors = load_anchor_authority(config)
    max_attempts = int(config["proposal_limits"]["maximum_refills_per_target"])
    total_limit = int(config["proposal_limits"]["maximum_total_proposals"])
    records: list[dict[str, Any]] = []
    seen_geometry: set[str] = set()
    seen_physical: set[str] = set()
    stats: Counter[str] = Counter()
    for name in ("raw_proposals", "valid_proposals", "invalid_rejections", "duplicate_rejections", "canonical_collisions", "refills"):
        stats[name] = 0
    family_stats: dict[str, Counter[str]] = defaultdict(Counter)
    category_stats: dict[str, Counter[str]] = defaultdict(Counter)

    jobs: list[tuple[str, str, int, dict[str, Any] | None, Callable[[int], dict[str, Any]]]] = []
    for family in TOPOLOGY_FAMILIES:
        for index in range(40):
            jobs.append(("FAMILY_STRATIFIED_GLOBAL", family, index, None, lambda attempt, f=family, i=index: propose_family_structure(seed, "FAMILY_STRATIFIED_GLOBAL", f, i, attempt)))
    for anchor in anchors:
        for index in range(32 if len(anchors) == 3 else 48):
            jobs.append(("ANCHOR_NEIGHBORHOOD", anchor["topology_family"], index, anchor, lambda attempt, a=anchor, i=index: propose_anchor_structure(a, i, attempt, seed)))
    for family in TOPOLOGY_FAMILIES:
        for index in range(8):
            jobs.append(("FAMILY_CHALLENGE", family, index, None, lambda attempt, f=family, i=index: propose_family_structure(seed, "FAMILY_CHALLENGE", f, i, attempt)))
    for family in TOPOLOGY_FAMILIES:
        for index in range(4):
            jobs.append(("RARE_CROSS_FAMILY", family, index, None, lambda attempt, f=family, i=index: propose_family_structure(seed, "RARE_CROSS_FAMILY", f, i, attempt)))

    bucket_counters: Counter[tuple[str, str]] = Counter()
    for category, family, local_index, anchor, factory in jobs:
        accepted = False
        rejected_before = 0
        for attempt in range(max_attempts):
            stats["raw_proposals"] += 1
            family_stats[family]["raw_proposals"] += 1
            category_stats[category]["raw_proposals"] += 1
            if stats["raw_proposals"] > total_limit:
                raise RuntimeError("total proposal limit exceeded")
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
            if geometry in seen_geometry or physical in seen_physical:
                stats["duplicate_rejections"] += 1
                stats["canonical_collisions"] += int(geometry in seen_geometry)
                family_stats[family]["duplicate_rejections"] += 1
                category_stats[category]["duplicate_rejections"] += 1
                rejected_before += 1
                continue
            bucket_index = bucket_counters[(category, family)]
            bucket_counters[(category, family)] += 1
            record = _record_candidate(raw, canonical, config, category=category, family=family,
                                       bucket_index=bucket_index, attempt=attempt, anchor=anchor,
                                       rejected_before=rejected_before)
            records.append(record)
            seen_geometry.add(geometry)
            seen_physical.add(physical)
            stats["valid_proposals"] += 1
            stats["refills"] += attempt
            family_stats[family]["valid_proposals"] += 1
            category_stats[category]["valid_proposals"] += 1
            accepted = True
            break
        if not accepted:
            raise RuntimeError(f"unable to fill candidate bucket: {category}/{family}/{local_index}")

    records.sort(key=lambda row: (
        CATEGORY_ORDER.index(row["source_category"]),
        TOPOLOGY_FAMILIES.index(row["topology_family"]),
        row["bucket_index"],
        row["canonical_geometry_hash"],
    ))
    source_counts = Counter(row["source_category"] for row in records)
    topology_counts: dict[str, dict[str, int]] = {}
    for family in TOPOLOGY_FAMILIES:
        by_source = Counter(row["source_category"] for row in records if row["topology_family"] == family)
        topology_counts[family] = {category: by_source[category] for category in CATEGORY_ORDER}
        topology_counts[family]["total"] = sum(by_source.values())
    signature_payload = [{key: row[key] for key in sorted(row)} for row in records]
    signature = stable_hash(signature_payload)
    schema_errors = [row["sample_id"] for row in records if not CANDIDATE_REQUIRED_FIELDS.issubset(row)]
    audit = {
        "status": "PASS",
        "seed": seed,
        **dict(stats),
        "final_unique_count": len(records),
        "unique_canonical_hashes": len(seen_geometry),
        "unique_physical_hashes": len(seen_physical),
        "candidate_content_signature": signature,
        "candidate_schema_status": "PASS" if not schema_errors else "FAIL",
        "candidate_schema_errors": schema_errors,
        "source_category_counts": dict(source_counts),
        "topology_counts": topology_counts,
        "family_acceptance": {family: {**dict(counts), "acceptance_rate": counts["valid_proposals"] / counts["raw_proposals"]} for family, counts in family_stats.items()},
        "source_category_acceptance": {category: {**dict(counts), "acceptance_rate": counts["valid_proposals"] / counts["raw_proposals"]} for category, counts in category_stats.items()},
        "level_b_count": sum(row["level"] != "A" for row in records),
        "tolerance_child_count": sum(bool(row["tolerance_child"]) for row in records),
        "integer_thickness_rate": sum(all(isinstance(value, int) and not isinstance(value, bool) for value in row["canonical_thickness_sequence"]) for row in records) / len(records),
        "legality_rate": sum(row["legality_status"] == "PASS" for row in records) / len(records),
        "source_material_rate": sum(row["source_medium"] == "APCD_GAN_NATIVE_M1" for row in records) / len(records),
        "exit_material_rate": sum(row["exit_medium"] == "AIR" for row in records) / len(records),
    }
    coverage = {
        "layer_count": _quantiles([row["layer_count"] for row in records]),
        "total_thickness_nm": _quantiles([row["total_thickness_nm"] for row in records]),
        "defect_thickness_nm": _quantiles([value for row in records for value in row["defect_thickness_nm"]]),
        "defect_count_distribution": dict(Counter(str(row["defect_count"]) for row in records)),
        "defect_position_distribution": dict(Counter(",".join(map(str, row["defect_indices"])) for row in records)),
        "termination_distribution": dict(Counter(f"{row['termination']['gan_side']}->{row['termination']['air_side']}" for row in records)),
        "anchor_parent_distribution": dict(Counter(str(row["anchor_parent_id"]) for row in records if row["anchor_parent_id"])),
    }
    return {"records": records, "anchors": anchors, "audit": audit, "coverage": coverage, "signature": signature}


def validate_static_gate(result: dict[str, Any]) -> dict[str, Any]:
    records, audit = result["records"], result["audit"]
    source = audit["source_category_counts"]
    checks: dict[str, bool] = {
        "total_candidates_512": len(records) == 512,
        "canonical_unique_512": audit["unique_canonical_hashes"] == 512,
        "physical_unique_512": audit["unique_physical_hashes"] == 512,
        "global_320": source.get("FAMILY_STRATIFIED_GLOBAL") == 320,
        "anchor_96": source.get("ANCHOR_NEIGHBORHOOD") == 96,
        "challenge_64": source.get("FAMILY_CHALLENGE") == 64,
        "rare_32": source.get("RARE_CROSS_FAMILY") == 32,
        "anchor_authority_at_least_2": len(result["anchors"]) >= 2,
        "level_b_zero": audit["level_b_count"] == 0,
        "tolerance_child_zero": audit["tolerance_child_count"] == 0,
        "integer_nm_100_percent": audit["integer_thickness_rate"] == 1.0,
        "legality_100_percent": audit["legality_rate"] == 1.0,
        "source_material_100_percent": audit["source_material_rate"] == 1.0,
        "exit_material_100_percent": audit["exit_material_rate"] == 1.0,
        "candidate_schema_pass": audit["candidate_schema_status"] == "PASS",
    }
    for family in TOPOLOGY_FAMILIES:
        counts = audit["topology_counts"][family]
        checks[f"{family}_global_40"] = counts["FAMILY_STRATIFIED_GLOBAL"] == 40
        checks[f"{family}_challenge_8"] = counts["FAMILY_CHALLENGE"] == 8
        checks[f"{family}_rare_4"] = counts["RARE_CROSS_FAMILY"] == 4
        checks[f"{family}_total_at_least_52"] = counts["total"] >= 52
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def write_candidate_outputs(result: dict[str, Any], config: dict[str, Any]) -> None:
    out = ROOT / config["output_directory"]
    out.mkdir(parents=True, exist_ok=True)
    public_anchors = [{key: value for key, value in anchor.items() if key != "raw_structure"} for anchor in result["anchors"]]
    manifest = {
        "contract_id": config["contract_id"],
        "expected_head": config["expected_head"],
        "candidate_count": len(result["records"]),
        "candidate_content_signature": result["signature"],
        "anchors": public_anchors,
        "static_gate": validate_static_gate(result),
        "schema": {"id": "mdc_ml_f0_pilot_candidate_manifest_v1", "required_fields": sorted(CANDIDATE_REQUIRED_FIELDS)},
    }
    write_json(out / "candidate_manifest_v1.json", manifest)
    write_jsonl(out / "candidate_records_v1.jsonl", result["records"])
    summary_rows = [{key: value for key, value in row.items() if key not in ("raw_structure", "raw_grammar_parameters", "collision_refill_provenance")} for row in result["records"]]
    write_csv(out / "candidate_summary_v1.csv", summary_rows)
    write_json(out / "candidate_generation_audit_v1.json", {**result["audit"], "coverage": result["coverage"]})
    (out / "candidate_content_signature_v1.txt").write_text(result["signature"] + "\n", encoding="ascii", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    first = build_candidates(config)
    second = build_candidates(config)
    deterministic = (
        first["signature"] == second["signature"]
        and [row["sample_id"] for row in first["records"]] == [row["sample_id"] for row in second["records"]]
        and [row["canonical_geometry_hash"] for row in first["records"]] == [row["canonical_geometry_hash"] for row in second["records"]]
    )
    gate = validate_static_gate(first)
    if not deterministic or gate["status"] != "PASS":
        raise RuntimeError(f"candidate static gate failed: deterministic={deterministic}, gate={gate}")
    first["audit"]["deterministic_rebuild"] = "PASS"
    first["audit"]["second_rebuild_signature"] = second["signature"]
    if not args.no_write:
        write_candidate_outputs(first, config)
    print(json.dumps({
        "status": "PASS", "candidate_count": len(first["records"]),
        "candidate_content_signature": first["signature"], "deterministic_rebuild": deterministic,
        "static_gate": gate, "generation": first["audit"], "coverage": first["coverage"],
        "anchors": [{key: value for key, value in anchor.items() if key != "raw_structure"} for anchor in first["anchors"]],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
