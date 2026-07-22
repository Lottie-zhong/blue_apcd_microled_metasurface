from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "mdc_ml_shared_surrogate_v1.yaml"
FORBIDDEN_EXACT = {
    "sample_id", "candidate_id", "canonical_geometry_hash", "physical_configuration_hash",
    "simulation_provenance_hash", "split_group_hash", "artifact_path", "artifact_sha256",
    "array_content_hash", "dataset_origin", "source_category", "anchor_parent_id",
    "authority_row", "generation_seed", "generation_attempt", "bucket_index",
}
FORBIDDEN_SUBSTRINGS = ("fwhm", "cone", "band", "transmission", "pareto", "valid", "quality", "hash", "artifact", "sample_id")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_group_hash(canonical_geometry_hash: str) -> str:
    return sha_text(canonical_json({"version": "mdc_split_group_hash_v1", "parent_canonical_geometry_hash": canonical_geometry_hash}))


def formal_output_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    files = 0
    size = 0
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = item.relative_to(path).as_posix()
        data = item.read_bytes()
        digest.update(rel.encode() + b"\0" + hashlib.sha256(data).digest())
        files += 1
        size += len(data)
    return {"file_count": files, "bytes": size, "tree_sha256": digest.hexdigest()}


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_source(rows: list[dict[str, Any]], manifest: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    assert len(rows) == cfg["expected_total"] == 2512
    assert manifest["combined_2512_content_signature"] == cfg["combined_signature"]
    assert Counter(r["dataset_origin"] for r in rows) == {"PRE1": 512, "FORMAL_2000": 2000}
    assert len({r["canonical_geometry_hash"] for r in rows}) == 2512
    assert len({r["physical_configuration_hash"] for r in rows}) == 2512
    assert len({r["source_artifact_relative_path"] for r in rows}) == 2512
    eligible = [r for r in rows if r["nominal_4d_objective_eligible"]]
    assert len(eligible) == cfg["expected_regression"] == 737
    assert sum(bool(r["shortlist_quality_eligible"]) for r in rows) == 131
    failures = [r for r in rows if r["power_balance_failure"]]
    assert len(failures) == 1 and not failures[0]["nominal_4d_objective_eligible"]
    targets = cfg["regression_targets"]
    assert all(all(r[t] is not None and np.isfinite(float(r[t])) for t in targets) for r in eligible)
    invalid_null = {
        "spectral": all((r["spectral_fwhm_normal_nm"] is None) for r in rows if not r["spectral_fwhm_valid"]),
        "angular": all((r["angular_fwhm_450_deg"] is None) for r in rows if not r["angular_fwhm_valid"]),
    }
    assert all(invalid_null.values())
    return {"origin_counts": dict(Counter(r["dataset_origin"] for r in rows)), "invalid_fwhm_null": invalid_null, "failure_sample": failures[0]["sample_id"]}


def feature_schema(cfg: dict[str, Any]) -> dict[str, Any]:
    names: list[str] = []
    groups: dict[str, list[str]] = {"sequence": [], "global": [], "family": []}
    for i in range(cfg["max_layers"]):
        for suffix in ("material_token", "thickness_nm", "present_mask", "defect_mask", "position_normalized"):
            name = f"layer_{i:02d}_{suffix}"
            names.append(name); groups["sequence"].append(name)
    globals_ = [
        "layer_count", "total_thickness_nm", "defect_count", "first_defect_position_normalized",
        "second_defect_position_normalized", "first_defect_thickness_nm", "second_defect_thickness_nm",
        "tio2_layer_count", "sio2_layer_count", "tio2_total_thickness_nm", "sio2_total_thickness_nm",
        "layer_thickness_mean_nm", "layer_thickness_std_nm", "layer_thickness_min_nm",
        "layer_thickness_max_nm", "gan_side_tio2", "air_side_tio2",
    ]
    names.extend(globals_); groups["global"].extend(globals_)
    family_names = [f"family__{f}" for f in cfg["families"]]
    names.extend(family_names); groups["family"].extend(family_names)
    assert len(names) == 150 and len(names) == len(set(names))
    leakage = [n for n in names if n in FORBIDDEN_EXACT or any(s in n for s in FORBIDDEN_SUBSTRINGS)]
    assert not leakage
    return {
        "contract_id": "physical_structure_feature_allowlist_v1", "max_layers": cfg["max_layers"],
        "feature_count": len(names), "feature_names": names, "groups": groups,
        "material_tokens": cfg["material_tokens"], "families": cfg["families"],
        "forbidden_exact": sorted(FORBIDDEN_EXACT), "leakage_hits": leakage,
    }


def encode_row(row: dict[str, Any], cfg: dict[str, Any]) -> list[float]:
    mats = row["canonical_material_sequence"]
    th = [float(v) for v in row["canonical_thickness_sequence"]]
    defects = set(int(v) for v in row["defect_indices"])
    n = len(mats); assert n == len(th) == int(row["layer_count"]) and n <= cfg["max_layers"]
    token_map = cfg["material_tokens"]
    out: list[float] = []
    for i in range(cfg["max_layers"]):
        present = i < n
        out.extend([
            float(token_map[mats[i]] if present else token_map["PAD"]),
            th[i] if present else 0.0,
            float(present), float(i in defects), float(i / max(n - 1, 1)) if present else 0.0,
        ])
    defect_list = sorted(defects)
    def dpos(k: int) -> float:
        return defect_list[k] / max(n - 1, 1) if len(defect_list) > k else -1.0
    def dth(k: int) -> float:
        return th[defect_list[k]] if len(defect_list) > k else 0.0
    tio2 = token_map["APCD_TIO2_NATIVE_M1"]
    material_ids = [token_map[m] for m in mats]
    tio_mask = [v == tio2 for v in material_ids]
    out.extend([
        float(n), float(sum(th)), float(len(defects)), dpos(0), dpos(1), dth(0), dth(1),
        float(sum(tio_mask)), float(n - sum(tio_mask)), float(sum(v for v, m in zip(th, tio_mask) if m)),
        float(sum(v for v, m in zip(th, tio_mask) if not m)), float(np.mean(th)), float(np.std(th)),
        float(np.min(th)), float(np.max(th)), float(mats[0] == "APCD_TIO2_NATIVE_M1"),
        float(mats[-1] == "APCD_TIO2_NATIVE_M1"),
    ])
    out.extend(float(row["topology_family"] == f) for f in cfg["families"])
    assert len(out) == 150 and all(np.isfinite(out))
    return out


def stratification_keys(row: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("family", row["topology_family"]), ("origin", row["dataset_origin"]),
        ("eligible", str(bool(row["nominal_4d_objective_eligible"]))),
        ("spectral", str(bool(row["spectral_fwhm_valid"]))),
        ("angular", str(bool(row["angular_fwhm_valid"]))),
        ("shortlist", str(bool(row["shortlist_quality_eligible"]))),
        ("source", row["source_category"]),
    ]


def deterministic_split(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, str]:
    names = list(cfg["split_fractions"])
    fractions = cfg["split_fractions"]
    total = len(rows)
    targets = {s: int(math.floor(total * fractions[s])) for s in names}
    for s in sorted(names, key=lambda x: (-((total * fractions[x]) % 1), names.index(x))):
        if sum(targets.values()) < total: targets[s] += 1
    category_totals = Counter(key for r in rows for key in stratification_keys(r))
    assigned_total = Counter(); assigned_cat: dict[str, Counter] = {s: Counter() for s in names}
    ordered = sorted(rows, key=lambda r: (min(category_totals[k] for k in stratification_keys(r)), sha_text(f"{cfg['split_seed']}|{split_group_hash(r['canonical_geometry_hash'])}")))
    result: dict[str, str] = {}
    for row in ordered:
        keys = stratification_keys(row)
        candidates = [s for s in names if assigned_total[s] < targets[s]]
        def score(s: str) -> tuple[float, str]:
            total_pressure = (assigned_total[s] + 1) / targets[s]
            balance = sum((assigned_cat[s][k] + 1) / max(category_totals[k] * fractions[s], 1.0) for k in keys)
            tie = sha_text(f"{cfg['split_seed']}|{row['canonical_geometry_hash']}|{s}")
            return total_pressure * 2.0 + balance, tie
        chosen = min(candidates, key=score)
        result[row["canonical_geometry_hash"]] = chosen
        assigned_total[chosen] += 1
        assigned_cat[chosen].update(keys)
    assert assigned_total == Counter(targets)
    return result


def split_summary(rows: list[dict[str, Any]], assignment: dict[str, str], cfg: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for split in cfg["split_fractions"]:
        part = [r for r in rows if assignment[r["canonical_geometry_hash"]] == split]
        summary[split] = {
            "total": len(part), "eligible_4d": sum(bool(r["nominal_4d_objective_eligible"]) for r in part),
            "shortlist": sum(bool(r["shortlist_quality_eligible"]) for r in part),
            "families": dict(sorted(Counter(r["topology_family"] for r in part).items())),
            "regression_families": dict(sorted(Counter(r["topology_family"] for r in part if r["nominal_4d_objective_eligible"]).items())),
            "origins": dict(Counter(r["dataset_origin"] for r in part)),
        }
        assert len(summary[split]["families"]) == 8 and summary[split]["eligible_4d"] > 0
    assert all(len(summary[s]["regression_families"]) == 8 for s in ("calibration", "test"))
    return summary


def leakage_audit(rows: list[dict[str, Any]], assignment: dict[str, str], schema: dict[str, Any]) -> dict[str, Any]:
    audits = {}
    for field in ("canonical_geometry_hash", "physical_configuration_hash"):
        owners: dict[str, set[str]] = defaultdict(set)
        for r in rows: owners[r[field]].add(assignment[r["canonical_geometry_hash"]])
        audits[field] = sum(len(v) > 1 for v in owners.values())
    groups: dict[str, set[str]] = defaultdict(set)
    for r in rows: groups[split_group_hash(r["canonical_geometry_hash"])].add(assignment[r["canonical_geometry_hash"]])
    audits["split_group_hash"] = sum(len(v) > 1 for v in groups.values())
    audits["forbidden_feature_hits"] = schema["leakage_hits"]
    audits["pass"] = not any(audits[k] for k in ("canonical_geometry_hash", "physical_configuration_hash", "split_group_hash")) and not audits["forbidden_feature_hits"]
    return audits


def near_neighbor_audit(rows: list[dict[str, Any]], assignment: dict[str, str], cfg: dict[str, Any]) -> dict[str, Any]:
    train = [r for r in rows if assignment[r["canonical_geometry_hash"]] == "train"]
    test = [r for r in rows if assignment[r["canonical_geometry_hash"]] == "test"]
    def vectors(part: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        th = np.zeros((len(part), cfg["max_layers"])); mat = np.zeros_like(th)
        for i, r in enumerate(part):
            vals = r["canonical_thickness_sequence"]; mats = r["canonical_material_sequence"]
            th[i, :len(vals)] = vals; mat[i, :len(mats)] = [cfg["material_tokens"][m] for m in mats]
        return th, mat
    tr_th, tr_mat = vectors(train); te_th, te_mat = vectors(test)
    scale = np.std(tr_th, axis=0); scale[scale < 1e-12] = 1.0
    nearest = []
    for i in range(len(test)):
        d_th = np.sqrt(np.mean(((tr_th - te_th[i]) / scale) ** 2, axis=1))
        mismatch = np.sum(tr_mat != te_mat[i], axis=1)
        composite = d_th + mismatch / cfg["max_layers"]
        j = int(np.argmin(composite))
        nearest.append({"sample_id": test[i]["sample_id"], "train_sample_id": train[j]["sample_id"], "distance": float(composite[j]), "thickness_distance": float(d_th[j]), "material_mismatch_count": int(mismatch[j])})
    parent_splits: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r.get("anchor_parent_id"): parent_splits[r["anchor_parent_id"]].add(assignment[r["canonical_geometry_hash"]])
    distances = np.array([x["distance"] for x in nearest])
    return {
        "test_count": len(test), "distance_min": float(distances.min()), "distance_median": float(np.median(distances)),
        "distance_p90": float(np.quantile(distances, .9)), "extreme_neighbor_threshold": cfg["extreme_neighbor_distance"],
        "extreme_neighbor_count": int(np.sum(distances < cfg["extreme_neighbor_distance"])),
        "anchor_parents_cross_split": sum(len(v) > 1 for v in parent_splits.values()),
        "origin_ratio_by_split": {s: dict(Counter(r["dataset_origin"] for r in rows if assignment[r["canonical_geometry_hash"]] == s)) for s in cfg["split_fractions"]},
        "nearest_examples": sorted(nearest, key=lambda x: x["distance"])[:20],
    }


def build(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    cfg = load_json(config_path); source = ROOT / cfg["source_registry"]; manifest_path = ROOT / cfg["source_manifest"]
    output = ROOT / cfg["output_root"]; data_dir = output / "dataset"; split_dir = output / "splits"; diag_dir = output / "diagnostics"
    formal_root = ROOT / "outputs" / "mdc_ml_f0_formal_pilot_2000_v1"
    before = formal_output_fingerprint(formal_root)
    rows = load_records(source); source_audit = validate_source(rows, load_json(manifest_path), cfg)
    rows = sorted(rows, key=lambda r: r["canonical_geometry_hash"])
    schema = feature_schema(cfg); X = np.asarray([encode_row(r, cfg) for r in rows], dtype=np.float64)
    y_cls = np.asarray([[float(bool(r[t])) for t in cfg["classification_targets"]] for r in rows], dtype=np.float64)
    reg_mask = np.asarray([bool(r["nominal_4d_objective_eligible"]) for r in rows])
    y_reg = np.full((len(rows), len(cfg["regression_targets"])), np.nan)
    for i, r in enumerate(rows):
        if reg_mask[i]: y_reg[i] = [float(r[t]) for t in cfg["regression_targets"]]
    assignment = deterministic_split(rows, cfg)
    summary = split_summary(rows, assignment, cfg); leakage = leakage_audit(rows, assignment, schema)
    assert leakage["pass"]
    neighbor = near_neighbor_audit(rows, assignment, cfg)
    train_idx = np.array([assignment[r["canonical_geometry_hash"]] == "train" for r in rows])
    stats = {"fit_split": "train", "mean": X[train_idx].mean(axis=0).tolist(), "std": X[train_idx].std(axis=0).tolist(), "feature_names": schema["feature_names"]}
    stats["std"] = [v if v > 1e-12 else 1.0 for v in stats["std"]]
    content_sig = sha_text(canonical_json({"schema": schema, "rows": [{"canonical_geometry_hash": r["canonical_geometry_hash"], "features": X[i].tolist()} for i, r in enumerate(rows)]}))
    split_rows = [{"sample_id": r["sample_id"], "canonical_geometry_hash": r["canonical_geometry_hash"], "physical_configuration_hash": r["physical_configuration_hash"], "split_group_hash": split_group_hash(r["canonical_geometry_hash"]), "split": assignment[r["canonical_geometry_hash"]], "topology_family": r["topology_family"], "dataset_origin": r["dataset_origin"], "source_category": r["source_category"], "anchor_parent_id": r.get("anchor_parent_id"), "nominal_4d_objective_eligible": bool(r["nominal_4d_objective_eligible"]), "shortlist_quality_eligible": bool(r["shortlist_quality_eligible"])} for r in rows]
    split_sig = sha_text(canonical_json(split_rows))
    split_manifest = {"contract_id": "mdc_ml_four_way_split_v1", "seed": cfg["split_seed"], "fractions": cfg["split_fractions"], "content_signature": split_sig, "test_sealed": True, "test_use_policy": "final_evaluation_once_after_validation_selection_and_calibration_selection", "enumeration_order_independent": True}
    dataset_manifest = {"contract_id": cfg["contract_id"], "combined_signature": cfg["combined_signature"], "total": len(rows), "classification_population": len(rows), "regression_population": int(reg_mask.sum()), "feature_count": X.shape[1], "feature_content_signature": content_sig, "source_audit": source_audit, "formal_output_fingerprint_before": before}
    atomic_text(data_dir / "feature_schema_v1.json", json.dumps(schema, indent=2, sort_keys=True))
    atomic_text(data_dir / "feature_statistics_v1.json", json.dumps(stats, indent=2, sort_keys=True))
    atomic_text(data_dir / "feature_content_signature_v1.txt", content_sig + "\n")
    atomic_text(data_dir / "dataset_manifest_v1.json", json.dumps(dataset_manifest, indent=2, sort_keys=True))
    data_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(data_dir / "dataset_v1.npz", X=X, y_classification=y_cls, y_regression=y_reg, regression_mask=reg_mask, sample_ids=np.asarray([r["sample_id"] for r in rows]), canonical_hashes=np.asarray([r["canonical_geometry_hash"] for r in rows]), families=np.asarray([r["topology_family"] for r in rows]), origins=np.asarray([r["dataset_origin"] for r in rows]), source_categories=np.asarray([r["source_category"] for r in rows]), anchor_parents=np.asarray([r.get("anchor_parent_id") or "" for r in rows]))
    atomic_text(split_dir / "split_manifest_v1.json", json.dumps(split_manifest, indent=2, sort_keys=True))
    atomic_text(split_dir / "split_summary_v1.json", json.dumps(summary, indent=2, sort_keys=True))
    atomic_text(split_dir / "split_content_signature_v1.txt", split_sig + "\n")
    split_dir.mkdir(parents=True, exist_ok=True)
    with (split_dir / "split_records_v1.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(split_rows[0])); writer.writeheader(); writer.writerows(split_rows)
    atomic_text(diag_dir / "feature_leakage_audit_v1.json", json.dumps(leakage, indent=2, sort_keys=True))
    atomic_text(diag_dir / "near_neighbor_audit_v1.json", json.dumps(neighbor, indent=2, sort_keys=True))
    after = formal_output_fingerprint(formal_root); assert after == before
    result = {"status": "PASS", "dataset": dataset_manifest, "split": summary, "split_signature": split_sig, "leakage": leakage, "near_neighbor": neighbor, "existing_outputs_unchanged": True}
    print(json.dumps(result, indent=2, sort_keys=True)); return result


def shared_surrogate_contract(cfg):
    return {k:cfg[k] for k in ("test_seal_contract","split_role_contract","champion_artifact_contract","active_learning_contract")}

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG); parser.add_argument("--validate-existing-only", action="store_true")
    args = parser.parse_args()
    if args.validate_existing_only:
        cfg = load_json(args.config); out = ROOT / cfg["output_root"]
        manifest = load_json(out / "dataset" / "dataset_manifest_v1.json"); split_manifest = load_json(out / "splits" / "split_manifest_v1.json")
        assert manifest["combined_signature"] == cfg["combined_signature"] and manifest["total"] == 2512 and manifest["regression_population"] == 737
        assert split_manifest["test_sealed"] and load_json(out / "diagnostics" / "feature_leakage_audit_v1.json")["pass"]
        print(json.dumps({"status": "PASS", "dataset": manifest, "split_manifest": split_manifest}, indent=2, sort_keys=True))
    else: build(args.config)


if __name__ == "__main__": main()
