#!/usr/bin/env python
"""Generate geometry-only K6 global DOE proposals. No truth, solver, FSP or model access."""
import csv, hashlib, json, math, platform, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import qmc

EXPECTED = {
    "protocol": "e18ea780917107c437d425293ff1da5628241221197e889cc22696e90d242abd",
    "domain": "93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f",
    "dataset_authority": "0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e",
    "truth_npz": "fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28",
    "expansion": "4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f",
    "exclusion": "78f48a4400d5ab469a2054a8ad849d5cae16cb4bee042e2b542529a78973bb80",
    "local_manifest": "66fef2027885ac5c479072da3af78b6a5f975b53ef1dc1f6894751c96ee73cd4",
    "eligible_pool": "387112fda12b2fbee0b2e6e4185014e0fad4bbb825b2d9e6cded865b4988073d",
    "source_pool_csv": "a623d61b1d5e0fdec7ee7cbd006b816ad00f4a8a35298cd12bb0e41afccbd2a1",
}
ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reports" / "coupling"
OUT = BASE / "COUPLING_ML_K6_GLOBAL_DATASET_AND_LEARNING_PROTOCOL_V1"

def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def require_sha(path, expected, label):
    got = file_sha(path)
    if got != expected:
        raise RuntimeError(f"{label} SHA mismatch: {got} != {expected}")
    return got

def ordered_hash(v):
    return hashlib.sha256(",".join(str(int(x)) for x in v).encode("ascii")).hexdigest()

def load_unique(rows):
    out = []
    seen = set()
    for row in rows:
        t = tuple(int(x) for x in row)
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def quantize_sobol(seed, m=15):
    engine = qmc.Sobol(d=6, scramble=True, seed=seed)
    u = engine.random_base2(m=m)
    idx = np.minimum(26, np.floor(u * 27).astype(np.int16))
    arr = 100 + 5 * idx
    return [tuple(int(x) for x in row) for row in arr]

def geometry_metrics(v):
    x = np.asarray(v, dtype=np.float64)
    gaps = 290.0 - (x + np.roll(x, -1)) / 2.0
    return float(np.min(gaps)), float(145.0 - np.max(x) / 2.0)

def stats(vals):
    a = np.asarray(vals, dtype=np.float64)
    if a.size == 0:
        return {"n": 0}
    qs = np.quantile(a, [0, .05, .25, .5, .75, .95, 1])
    return {"n": int(a.size), "min": float(qs[0]), "q05": float(qs[1]),
            "q25": float(qs[2]), "median": float(qs[3]), "q75": float(qs[4]),
            "q95": float(qs[5]), "max": float(qs[6]), "mean": float(np.mean(a))}

def distances(a, b):
    A = np.asarray(a, dtype=np.float64).reshape((-1, 6))
    B = np.asarray(b, dtype=np.float64).reshape((-1, 6))
    if len(A) == 0 or len(B) == 0:
        return np.empty((len(A), len(B)), dtype=np.float64)
    return np.sqrt(np.sum((A[:, None, :] - B[None, :, :]) ** 2, axis=2)) / 130.0

def nn_summary(a, b, same=False):
    D = distances(a, b)
    if same:
        np.fill_diagonal(D, np.inf)
    return stats(np.min(D, axis=1)) if D.size else {"n": 0}

def unique_quantized(rows):
    seen = set()
    out = []
    duplicate_count = 0
    for row in rows:
        if row in seen:
            duplicate_count += 1
        else:
            seen.add(row)
            out.append(row)
    return out, duplicate_count

def approx_cover_probe(seed, refs):
    probe, dup = unique_quantized(quantize_sobol(seed, m=15))
    R = np.asarray(refs, dtype=np.float64)
    P = np.asarray(probe, dtype=np.float64)
    result = []
    for start in range(0, len(P), 1024):
        chunk = P[start:start+1024]
        ds = np.sqrt(np.sum((chunk[:, None, :] - R[None, :, :]) ** 2, axis=2)) / 130.0
        result.extend(np.min(ds, axis=1).tolist())
    return {"seed": seed, "sobol_n": 32768, "quantized_unique_n": len(probe),
            "quantization_duplicates": dup, "nearest_to_reference": stats(result)}

def main():
    if scipy.__version__ != "1.15.3":
        raise RuntimeError(f"Frozen sampler requires scipy 1.15.3; found {scipy.__version__}")
    protocol_path = OUT / "PREREGISTERED_PROTOCOL_V1.json"
    require_sha(protocol_path, EXPECTED["protocol"], "protocol")
    domain_path = BASE / "PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json"
    dataset_auth_path = BASE / "PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1" / "PW_K6_32G_DATASET_AUTHORITY_V1.json"
    truth_npz_path = BASE / "PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1" / "dataset_truth_32g.npz"
    expansion_path = BASE / "PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json"
    exclusion_path = BASE / "PW_K6_GEOMETRY_EXCLUSION_REGISTRY_V1.json"
    pool_path = BASE / "PW_K6_EXTENSION_ELIGIBLE_CANDIDATE_POOL_V1.json"
    local_path = BASE / "COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1" / "CANDIDATE_MANIFEST_V1.json"
    source_expected = {
        domain_path: EXPECTED["domain"], dataset_auth_path: EXPECTED["dataset_authority"],
        truth_npz_path: EXPECTED["truth_npz"], expansion_path: EXPECTED["expansion"],
        exclusion_path: EXPECTED["exclusion"], pool_path: EXPECTED["eligible_pool"],
        local_path: EXPECTED["local_manifest"],
    }
    for p, h in source_expected.items():
        require_sha(p, h, p.name)
    domain = read_json(domain_path)
    source_csv = Path(domain["source_artifacts"]["primary_candidate_pool"]["path"])
    require_sha(source_csv, EXPECTED["source_pool_csv"], "primary candidate source pool CSV")
    expansion = read_json(expansion_path)
    exclusion = read_json(exclusion_path)
    pool_auth = read_json(pool_path)
    local = read_json(local_path)
    local_rows = local["cases"]
    if len(local_rows) != 16:
        raise RuntimeError(f"Expected 16 frozen local DOE points, got {len(local_rows)}")
    local12 = [tuple(row["ordered_D_nm"]) for row in local_rows if row["role"] == "DEVELOPMENT_AXIS"]
    local4 = [tuple(row["ordered_D_nm"]) for row in local_rows if row["role"] == "SEALED_CONFIRMATION_COMBINATION"]
    if len(local12) != 12 or len(local4) != 4:
        raise RuntimeError("Frozen local point roles do not match 12+4")
    with np.load(truth_npz_path, allow_pickle=False) as z:
        old_ids = [str(v) for v in z["case_ids"].tolist()]
        old32 = [tuple(int(x) for x in row) for row in z["ordered_D_nm"].tolist()]
    if len(old32) != 32 or len(set(old32)) != 32:
        raise RuntimeError("32G geometry source does not contain 32 unique ordered geometry groups")
    reserves = [tuple(int(x) for x in row["ordered_D_nm"]) for row in expansion["prospective_reserve_only"]]
    protected = [tuple(int(x) for x in row["ordered_D_nm"]) for row in exclusion["entries"]]
    pool48 = [tuple(int(x) for x in row["ordered_D_nm"]) for row in pool_auth["entries"]]
    if (len(reserves), len(protected), len(pool48)) != (6, 25, 48):
        raise RuntimeError("Reserve/protected/candidate-pool counts differ from frozen authority")
    categories = {"existing32": old32, "local16": [*local12, *local4],
                  "reserve6": reserves, "protected25": protected, "source_pool48": pool48}
    overlaps = {}
    for name, rows in categories.items():
        overlaps[name] = int(sum(tuple(v) in set(rows) for v in categories["local16"])) if name != "local16" else 0
    if set(local12) & set(local4) or len(set(local12 + local4)) != 16:
        raise RuntimeError("Frozen local point duplicates found")
    if set(local12 + local4) & set(old32):
        raise RuntimeError("Frozen local points overlap existing 32G")
    if set(local12 + local4) & set(reserves) or set(local12 + local4) & set(protected):
        raise RuntimeError("Frozen local points overlap reserve/protected geometry")

    raw = quantize_sobol(seed=20261004, m=15)
    unique, duplicate_count = unique_quantized(raw)
    base_set = set()
    for rows in categories.values():
        base_set.update(tuple(v) for v in rows)
    base = sorted(base_set)
    reason_counts = {}
    for name, rows in categories.items():
        s = set(rows)
        reason_counts[name] = sum(v in s for v in unique)
    valid = []
    invalid_range_grid = invalid_clearance = invalid_margin = 0
    for v in unique:
        if len(v) != 6 or any(x < 100 or x > 230 or (x - 100) % 5 for x in v):
            invalid_range_grid += 1
            continue
        gap, margin = geometry_metrics(v)
        if gap <= 0:
            invalid_clearance += 1
            continue
        if margin < 30:
            invalid_margin += 1
            continue
        if v in base_set:
            continue
        valid.append(v)
    if len(valid) < 144:
        raise RuntimeError(f"Only {len(valid)} unique feasible candidates available; need 144")
    candidates = np.asarray(valid, dtype=np.float64)
    ref = np.asarray(base, dtype=np.float64)
    min_sq = np.min(np.sum((candidates[:, None, :] - ref[None, :, :]) ** 2, axis=2), axis=1) / (130.0 ** 2)
    chosen = []
    chosen_distances = []
    selected = np.zeros(len(candidates), dtype=bool)
    for _ in range(144):
        scores = np.where(selected, -np.inf, min_sq)
        j = int(np.argmax(scores))
        if not np.isfinite(scores[j]):
            raise RuntimeError("Maximin candidate pool exhausted")
        chosen.append(tuple(int(x) for x in candidates[j]))
        chosen_distances.append(float(math.sqrt(max(0.0, scores[j]))))
        selected[j] = True
        delta = candidates - candidates[j]
        d2 = np.sum(delta * delta, axis=1) / (130.0 ** 2)
        min_sq = np.minimum(min_sq, d2)
    if len(set(chosen)) != 144 or set(chosen) & base_set:
        raise RuntimeError("Global maximin list contains duplicate/excluded points")
    global_dev, global_conf = [], []
    for i, v in enumerate(chosen, start=1):
        if i <= 140 and i % 5 == 0:
            global_conf.append((i, v))
        else:
            global_dev.append((i, v))
    if len(global_dev) != 116 or len(global_conf) != 28:
        raise RuntimeError(f"Wrong global role counts {len(global_dev)}/{len(global_conf)}")

    records = []
    for row in local_rows:
        role = "DEVELOPMENT_LOCAL_AXIS" if row["role"] == "DEVELOPMENT_AXIS" else "SEALED_LOCAL_COMBINATION"
        v = tuple(int(x) for x in row["ordered_D_nm"])
        gap, margin = geometry_metrics(v)
        records.append({"case_id":row["case_id"],"role":role,"cohort":"FROZEN_LOCAL_DOE",
                        "global_selection_index":"","ordered_D_nm":v,"clearance":gap,"margin":margin})
    for n, (idx, v) in enumerate(global_dev, start=1):
        gap, margin = geometry_metrics(v)
        records.append({"case_id":f"K6GDP1_DEV_G{n:03d}","role":"DEVELOPMENT_GLOBAL",
                        "cohort":"GLOBAL_MAXIMIN","global_selection_index":idx,
                        "ordered_D_nm":v,"clearance":gap,"margin":margin})
    for n, (idx, v) in enumerate(global_conf, start=1):
        gap, margin = geometry_metrics(v)
        records.append({"case_id":f"K6GDP1_CONF_G{n:03d}","role":"SEALED_CONFIRMATION_GLOBAL",
                        "cohort":"GLOBAL_MAXIMIN","global_selection_index":idx,
                        "ordered_D_nm":v,"clearance":gap,"margin":margin})
    if len(records) != 160 or len({r["case_id"] for r in records}) != 160:
        raise RuntimeError("New point set is not exactly 160 unique IDs")
    if len({r["ordered_D_nm"] for r in records}) != 160:
        raise RuntimeError("New point set repeats an ordered geometry")
    if any(tuple(r["ordered_D_nm"]) in set(old32) for r in records):
        raise RuntimeError("New point repeats existing 32G")
    fields = ["case_id","role","cohort","global_selection_index",
              "D1_nm","D2_nm","D3_nm","D4_nm","D5_nm","D6_nm",
              "min_periodic_neighbor_gap_nm","min_half_cell_lateral_margin_nm",
              "ordered_geometry_sha256","source_authority_enrolled","runner_approved",
              "fsp_created_by_this_task","solver_authorized"]
    points_path = OUT / "GLOBAL_DATASET_CANDIDATES_V1.csv"
    with points_path.open("w",encoding="utf-8",newline="") as f:
        w = csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader()
        for r in records:
            v = r["ordered_D_nm"]
            item = {k:r[k] for k in ["case_id","role","cohort","global_selection_index"]}
            item.update({f"D{i+1}_nm":int(v[i]) for i in range(6)})
            item.update({"min_periodic_neighbor_gap_nm":f"{r['clearance']:.6f}",
                         "min_half_cell_lateral_margin_nm":f"{r['margin']:.6f}",
                         "ordered_geometry_sha256":ordered_hash(v),
                         "source_authority_enrolled":"false","runner_approved":"false",
                         "fsp_created_by_this_task":"false","solver_authorized":"false"})
            w.writerow(item)

    new_dev = [r["ordered_D_nm"] for r in records if r["role"].startswith("DEVELOPMENT_")]
    new_conf = [r["ordered_D_nm"] for r in records if r["role"].startswith("SEALED_")]
    global_dev_vec = [v for _,v in global_dev]
    global_conf_vec = [v for _,v in global_conf]
    all_new = [r["ordered_D_nm"] for r in records]
    dev_data = old32 + new_dev
    # Four group-only development folds; local axial cases cycle by case ID, global points by selection index.
    fold_rows = []
    local_dev_records = sorted([r for r in records if r["role"]=="DEVELOPMENT_LOCAL_AXIS"],key=lambda r:r["case_id"])
    for i,r in enumerate(local_dev_records):
        fold_rows.append((r["case_id"],(i%4)+1,r["role"],r["ordered_D_nm"]))
    for r in records:
        if r["role"]=="DEVELOPMENT_GLOBAL":
            idx=int(r["global_selection_index"])
            fold_rows.append((r["case_id"],((idx-1)%4)+1,r["role"],r["ordered_D_nm"]))
    folds_path=OUT/"DEVELOPMENT_FOLD_MANIFEST_V1.csv"
    with folds_path.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(["case_id","outer_fold","role","D1_nm","D2_nm","D3_nm","D4_nm","D5_nm","D6_nm","all_21_wavelengths_grouped"])
        for cid,fold,role,v in sorted(fold_rows,key=lambda x:(x[1],x[0])):
            w.writerow([cid,fold,role,*v,"true"])
    fold_counts={}
    for _,fold,role,_ in fold_rows:
        x=fold_counts.setdefault(str(fold),{"geometry_groups":0,"local_axial":0,"global":0})
        x["geometry_groups"]+=1
        x["local_axial" if role=="DEVELOPMENT_LOCAL_AXIS" else "global"]+=1

    def coord_coverage(rows):
        a=np.asarray(rows,dtype=int)
        return {f"D{i+1}":{"min_nm":int(a[:,i].min()),"max_nm":int(a[:,i].max()),
                           "unique_levels":int(len(np.unique(a[:,i]))),
                           "levels_nm":[int(x) for x in sorted(np.unique(a[:,i]).tolist())],
                           "at_100":int(np.sum(a[:,i]==100)),"at_230":int(np.sum(a[:,i]==230)),
                           "within_10_of_face":int(np.sum((a[:,i]<=110)|(a[:,i]>=220)))}
                for i in range(6)}
    def boundary(rows):
        a=np.asarray(rows,dtype=int)
        face=((a==100)|(a==230))
        near=((a<=110)|(a>=220))
        return {"any_exact_face_count":int(np.sum(np.any(face,axis=1))),
                "any_exact_face_fraction":float(np.mean(np.any(face,axis=1))),
                "any_within_10nm_face_count":int(np.sum(np.any(near,axis=1))),
                "any_within_10nm_face_fraction":float(np.mean(np.any(near,axis=1)))}
    def group_summary(rows):
        a=np.asarray(rows,dtype=int)
        clear=[geometry_metrics(v)[0] for v in rows]
        margin=[geometry_metrics(v)[1] for v in rows]
        return {"count":len(rows),"coordinate_coverage":coord_coverage(rows),
                "boundary_coverage":boundary(rows),
                "within_set_nearest_neighbor_distance":nn_summary(rows,rows,same=True),
                "minimum_periodic_neighbor_clearance_nm":stats(clear),
                "minimum_half_cell_margin_nm":stats(margin)}
    raw_set=set(unique)
    exclusion_union=sum(v in base_set for v in unique)
    # Pair-role and source-distance evidence.
    coverage = {
      "sampler":{"method":"scrambled_sobol_6d_quantized_27_levels","seed":20261004,
        "raw_draws":len(raw),"unique_quantized":len(unique),"quantization_duplicates":duplicate_count,
        "excluded_identity_union_count":int(exclusion_union),"valid_new_candidate_pool":len(valid),
        "overlap_counts_by_reference_set_nonexclusive":reason_counts,
        "invalid_range_grid":invalid_range_grid,"invalid_nonoverlap":invalid_clearance,
        "invalid_lateral_margin":invalid_margin,"greedy_selected_global":len(chosen),
        "global_confirmation_sequence_indices":[i for i,_ in global_conf],
        "source_pool_excluded_from_global":True,"selected_global_overlaps_source_pool":0},
      "frozen_local_overlap_with":{"existing32":overlaps["existing32"],"reserve6":overlaps["reserve6"],
        "protected25":overlaps["protected25"],"source_pool48":overlaps["source_pool48"]},
      "counts":{"new_total":len(all_new),"development_total":len(new_dev),"development_local_axis":len(local12),
        "development_global":len(global_dev),"confirmation_total":len(new_conf),"confirmation_local_combo":len(local4),
        "confirmation_global":len(global_conf),"existing32_development_only":len(old32),
        "total_development_available_after_new_HF":len(dev_data)},
      "sets":{"new_all":group_summary(all_new),"new_development":group_summary(new_dev),
        "new_confirmation":group_summary(new_conf),"global_144":group_summary(chosen),
        "global_development":group_summary(global_dev_vec),"global_confirmation":group_summary(global_conf_vec),
        "existing32":group_summary(old32),"combined_development_160":group_summary(dev_data)},
      "distance_to_existing32":{"all_new":nn_summary(all_new,old32),"global_development":nn_summary(global_dev_vec,old32),
        "global_confirmation":nn_summary(global_conf_vec,old32)},
      "distance_to_local16":{"global_development":nn_summary(global_dev_vec,[*local12,*local4]),
        "global_confirmation":nn_summary(global_conf_vec,[*local12,*local4])},
      "development_confirmation_separation":{"new_confirm_to_new_dev":nn_summary(new_conf,new_dev),
        "global_confirm_to_global_dev":nn_summary(global_conf_vec,global_dev_vec),
        "local_combo_to_local_axis":nn_summary(local4,local12)},
      "maximin_selection_min_distance_to_prior_at_selection":stats(chosen_distances),
      "approximate_joint_coverage_probe":{
        "reference_existing32":approx_cover_probe(20261005,old32),
        "reference_existing32_plus_new_development":approx_cover_probe(20261005,dev_data),
        "reference_existing32_plus_all_new":approx_cover_probe(20261005,old32+all_new)},
      "outer_development_folds":{"folds":fold_counts,"grouping":"Each geometry carries all 21 wavelengths; old32 never scored as new confirmation."},
      "constraint_summary":{"all_160_in_range_grid_unique":True,"minimum_gap_nm":min(geometry_metrics(r["ordered_D_nm"])[0] for r in records),
        "minimum_lateral_half_cell_margin_nm":min(geometry_metrics(r["ordered_D_nm"])[1] for r in records),
        "manufacturing_authority":"UNRESOLVED; no manufacturing acceptance inferred.",
        "geometry_authority_enrollment":"None of the proposed global vectors is enrolled; source-authority amendment is required before future HF."},
      "response_blindness":{"candidate_generation_reads_truth_values":False,"used_model_error_or_response":False,
        "used_routing_or_target_efficiency":False,"used_P_scale_for_selection":False},
      "execution_counts":{"solver_entries":0,"training_fits":0,"P_scale_fits":0,"new_FSPs":0,"Runner_invocations":0}
    }
    audit = {
      "schema":"COUPLING_ML_K6_GLOBAL_DATASET_AND_LEARNING_PROTOCOL_V1_SAMPLING_AUDIT",
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "generator":{"path":"reports/coupling/COUPLING_ML_K6_GLOBAL_DATASET_AND_LEARNING_PROTOCOL_V1/generate_global_dataset_design_v1.py",
        "sha256":file_sha(__file__),"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},
      "frozen_protocol_sha256":file_sha(protocol_path),
      "input_authority_sha256":{str(p.relative_to(ROOT)).replace("\\","/"):h for p,h in source_expected.items()},
      "primary_candidate_pool_csv_sha256":file_sha(source_csv),
      "coverage":coverage
    }
    audit_path=OUT/"SAMPLING_COVERAGE_AUDIT_V1.json"
    audit_path.write_text(json.dumps(audit,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")
    print(json.dumps({"pointset_csv":str(points_path),"pointset_sha256":file_sha(points_path),
      "fold_manifest":str(folds_path),"fold_manifest_sha256":file_sha(folds_path),
      "audit":str(audit_path),"audit_sha256":file_sha(audit_path),
      "counts":coverage["counts"],"folds":fold_counts,
      "nearest_neighbor_new":coverage["sets"]["new_all"]["within_set_nearest_neighbor_distance"],
      "dev_confirm":coverage["development_confirmation_separation"],
      "constraints":coverage["constraint_summary"],"exclusions":coverage["sampler"]},ensure_ascii=False))
if __name__=="__main__":
    main()
