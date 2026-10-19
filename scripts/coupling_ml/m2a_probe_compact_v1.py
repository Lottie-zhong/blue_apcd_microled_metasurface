import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

NP = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
COUPLING = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def read_csv(p):
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def mean(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return sum(xs) / len(xs) if xs else None


def flatten_strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k), v
            yield from flatten_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_strings(v)


def geometry_vector(gid):
    vals = [float(x) for x in re.findall(r"D(\d+(?:\.\d+)?)", gid or "")]
    return vals if len(vals) == 6 else None


def main():
    hf_path = NP / r"outputs\np_k6_m8a_primary2_closeout_v1\hf22_formal_development_484rows.csv"
    hf = read_csv(hf_path)
    groups = defaultdict(list)
    for row in hf:
        groups[row.get("geometry_id")].append(row)
    hf_table = []
    for gid, rows in sorted(groups.items()):
        vec = geometry_vector(gid)
        def av(k): return mean([num(r.get(k)) for r in rows])
        hf_table.append({
            "geometry_id": gid,
            "geometry_hash": rows[0].get("geometry_hash"),
            "D1": vec[0] if vec else None, "D2": vec[1] if vec else None, "D3": vec[2] if vec else None,
            "D4": vec[3] if vec else None, "D5": vec[4] if vec else None, "D6": vec[5] if vec else None,
            "rows": len(rows), "polarizations": sorted({r.get("polarization") for r in rows}),
            "T_mean": av("T_total"), "R_mean": av("R_total"), "eta_plus1_mean": av("eta_plus1"),
            "plus1_fraction_mean": av("plus1_transmitted_fraction"), "directionality_mean": av("directionality"),
            "eta_minus1_mean": av("eta_minus1"), "closure_worst": min([num(r.get("closure")) for r in rows if num(r.get("closure")) is not None], default=None),
            "all_quality_gate_pass": all(str(r.get("quality_gate_pass")).lower() == "true" for r in rows),
            "all_accepted_execution": all(str(r.get("accepted_execution")).lower() == "true" for r in rows),
            "case_ids": sorted({r.get("case_id") for r in rows}),
        })
    # Transparent strata on HF observed plus-1 transmitted fraction, with fixed 8/7/7 split.
    ranked = sorted(hf_table, key=lambda r: (-(r["plus1_fraction_mean"] or -1), r["geometry_id"]))
    for i, row in enumerate(ranked):
        row["hf_response_rank_plus1_fraction"] = i + 1
        row["performance_stratum"] = "HIGH" if i < 8 else ("MEDIUM" if i < 15 else "LOWER_CONTRASTING")
    rank_lookup = {r["geometry_id"]: r for r in ranked}
    for row in hf_table:
        row.update({"hf_response_rank_plus1_fraction": rank_lookup[row["geometry_id"]]["hf_response_rank_plus1_fraction"], "performance_stratum": rank_lookup[row["geometry_id"]]["performance_stratum"]})

    score_path = NP / r"outputs\np_k6_m8a_final_targeted_acquisition_design_v1\candidate_selection_scores.csv"
    score_rows = read_csv(score_path)
    score_by = {r.get("geometry_id"): r for r in score_rows}
    score_fields = ["geometry_id", "tail_localization_score", "ranking_disambiguation_score", "redundancy_score", "performance_score", "predicted_ps_contrast", "nearest_hf20_geometry", "nearest_hf20_distance", "ordered_D1_D6", "acquisition_role", "selection_tier", "backup_rank", "backup_queue"]
    score_table = [{k: score_by.get(row["geometry_id"], {}).get(k) for k in score_fields} for row in hf_table]

    lf_manifest_path = NP / r"outputs\np_k6_m9_22g_forward_retraining_v1\lf22_full_vector_authority_manifest.json"
    m9_pre_path = NP / r"outputs\np_k6_m9_22g_forward_retraining_v1\NP_K6_M9_22G_FORWARD_RETRAINING_PREREG_V1.json"
    key_json = {}
    for name, p in [("lf_manifest", lf_manifest_path), ("m9_prereg", m9_pre_path), ("freeze", NP / r"outputs\np_k6_final_freeze_closeout_v1\freeze_manifest.json"), ("provider_manifest", NP / r"outputs\np_k6_final_freeze_closeout_v1\provider_manifest.json"), ("coupling_handoff", NP / r"outputs\np_k6_final_freeze_closeout_v1\coupling_handoff.json")]:
        if p.exists():
            obj = read_json(p)
            key_json[name] = {"path": str(p), "sha256": sha(p), "keys": list(obj) if isinstance(obj, dict) else None, "data": obj}

    m0f = read_csv(ML / r"outputs\coupling_ml\M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1\M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION\M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1\M0F_FINAL_RECONCILED_LEVEL1_NUMERICAL_REGISTRY_V1.csv")
    alt_paths = sorted({r.get("level2_authoritative_raw_path") for r in m0f if r.get("candidate") == "ALT1" and r.get("level2_authoritative_raw_path")})
    raw_meta = []
    for sp in alt_paths:
        p = Path(sp)
        if not p.exists():
            raw_meta.append({"path": sp, "missing": True})
            continue
        obj = read_json(p)
        top = {k: obj.get(k) for k in ["case_id", "candidate", "geometry_id", "geometry_hash", "spacer_nm", "ux", "source_polarization", "polarization", "wavelengths_nm", "zero_solver", "normalization_contract", "interface_stack_id"] if k in obj}
        strings = sorted({str(v) for _, v in flatten_strings(obj) if isinstance(v, str) and ("K6X" in v or "D1" in v or "geometry" in v.lower())})
        raw_meta.append({"path": sp, "sha256": sha(p), "top": top, "matching_strings": strings[:80], "keys": list(obj)[:80]})

    provider_root = COUPLING / r"outputs\coupling\rcwa_component_benchmark_v1\runtime_runs\RCWA_LEVEL1_ANGULAR_ACQUISITION_9JOB_V1"
    provider_meta = []
    for p in sorted(provider_root.glob("*_postprocessed.json")):
        obj = read_json(p)
        strings = sorted({str(v) for _, v in flatten_strings(obj) if isinstance(v, str) and ("K6X" in v or "D1" in v or "geometry" in v.lower())})
        provider_meta.append({"path": str(p), "sha256": sha(p), "keys": list(obj)[:50], "matching_strings": strings[:80]})

    out = {"hf_path": str(hf_path), "hf_sha256": sha(hf_path), "hf_rows": len(hf), "geometry_count": len(hf_table), "hf_table": hf_table, "m8a_score_table": score_table, "key_json": key_json, "alt1_raw_meta": raw_meta, "provider_count": len(provider_meta), "provider_meta": provider_meta}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
