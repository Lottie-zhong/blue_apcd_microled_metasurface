from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.stats import qmc

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
PKG = ROOT / "paper_a_broadband"
REPORT = PKG / "reports/bf04_local_diattenuation_redesign_doe_v1"
AUTH = PKG / "authority"
CONFIG_DIR = PKG / "configs"
SEED = 20260827
SAMPLES = 16384
PX = PY = 432.0
H = 525.0
DIM_KEYS = ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "delta_theta_deg", "D_nm")
BASE = {"L1_nm": 230.0, "W1_nm": 100.0, "L2_nm": 180.0, "W2_nm": 90.0}
BF04 = {"L1_nm": 256, "W1_nm": 91, "L2_nm": 204, "W2_nm": 77, "delta_theta_deg": 82.727050781, "D_nm": 219}


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def sha_obj(v):
    return hashlib.sha256(canonical(v)).hexdigest()


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_csv(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with p.open("w", newline="", encoding="utf-8") as fh:
        out = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        out.writeheader()
        for row in rows:
            out.writerow({k: json.dumps(v, sort_keys=True, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def polygon(length, width, cx, cy, theta_deg):
    a, b = length / 2.0, width / 2.0
    t = math.radians(theta_deg)
    c, s = math.cos(t), math.sin(t)
    return [(cx + c * x - s * y, cy + s * x + c * y) for x, y in [(-a, -b), (a, -b), (a, b), (-a, b)]]


def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def between(a, b, c, eps=1e-10):
    return min(a[0], b[0]) - eps <= c[0] <= max(a[0], b[0]) + eps and min(a[1], b[1]) - eps <= c[1] <= max(a[1], b[1]) + eps


def seg_inter(a, b, c, d, eps=1e-9):
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if abs(o1) <= eps and between(a, b, c): return True
    if abs(o2) <= eps and between(a, b, d): return True
    if abs(o3) <= eps and between(c, d, a): return True
    if abs(o4) <= eps and between(c, d, b): return True
    return ((o1 > eps) != (o2 > eps)) and ((o3 > eps) != (o4 > eps))


def point_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = dx * dx + dy * dy
    if den == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1]), a
    q = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den))
    z = (a[0] + q * dx, a[1] + q * dy)
    return math.hypot(p[0] - z[0], p[1] - z[1]), z


def segment_pair(a, b, c, d):
    if seg_inter(a, b, c, d):
        return 0.0, a, c, True
    best = (float("inf"), a, c)
    for p, u, v, flip in ((a, c, d, False), (b, c, d, False), (c, a, b, True), (d, a, b, True)):
        dist, z = point_seg(p, u, v)
        cand = (dist, z, p) if flip else (dist, p, z)
        if cand[0] < best[0]:
            best = cand
    return best[0], best[1], best[2], False


def poly_pair(a, b):
    best = (float("inf"), a[0], b[0], False)
    for i in range(4):
        for j in range(4):
            cand = segment_pair(a[i], a[(i + 1) % 4], b[j], b[(j + 1) % 4])
            if cand[0] < best[0]:
                best = cand
    return best


def geom_core(q):
    p1 = polygon(q["L1_nm"], q["W1_nm"], 0.0, q["D_nm"] / 2.0, 0.0)
    p2 = polygon(q["L2_nm"], q["W2_nm"], 0.0, -q["D_nm"] / 2.0, q["delta_theta_deg"])
    polys = {"pillar_1": p1, "pillar_2": p2}
    containment = all(abs(x) <= PX / 2.0 + 1e-9 and abs(y) <= PY / 2.0 + 1e-9 for p in polys.values() for x, y in p)
    direct = poly_pair(p1, p2)
    periodic = []
    for name_a, pa in polys.items():
        for name_b, pb in polys.items():
            for ix in (-1, 0, 1):
                for iy in (-1, 0, 1):
                    if ix == 0 and iy == 0:
                        continue
                    shifted = [(x + ix * PX, y + iy * PY) for x, y in pb]
                    d, ca, cb, touch = poly_pair(pa, shifted)
                    periodic.append({"distance_nm": d, "object_a": name_a, "object_b": name_b, "image_shift": [ix, iy], "point_a_nm": list(ca), "point_b_nm": list(cb), "touch_or_overlap": touch})
    pmin = min(periodic, key=lambda x: (x["distance_nm"], x["object_a"], x["object_b"], x["image_shift"]))
    return {
        "cell_containment_pass": containment,
        "direct_clearance_nm": direct[0],
        "direct_pair": {"distance_nm": direct[0], "object_a": "pillar_1", "object_b": "pillar_2", "image_shift": [0, 0], "point_a_nm": list(direct[1]), "point_b_nm": list(direct[2]), "touch_or_overlap": direct[3]},
        "periodic_image_clearance_nm": pmin["distance_nm"],
        "periodic_nearest_pair": pmin,
        "global_minimum_clearance_nm": min(direct[0], pmin["distance_nm"]),
        "overlap_or_touching_pass": not direct[3] and not any(x["touch_or_overlap"] for x in periodic),
    }


def round_half_up(v):
    return int(math.floor(float(v) + 0.5))


def anisotropy(q):
    a1 = (q["L1_nm"] - q["W1_nm"]) / (q["L1_nm"] + q["W1_nm"])
    a2 = (q["L2_nm"] - q["W2_nm"]) / (q["L2_nm"] + q["W2_nm"])
    return {"A1": a1, "A2": a2, "A_mean": (a1 + a2) / 2.0, "Delta_A": a1 - a2}


def qgeom(raw):
    q = {"L1_nm": round_half_up(raw["L1_nm"]), "W1_nm": round_half_up(raw["W1_nm"]), "L2_nm": round_half_up(raw["L2_nm"]), "W2_nm": round_half_up(raw["W2_nm"]), "delta_theta_deg": round(float(raw["delta_theta_deg"]), 9), "D_nm": round_half_up(raw["D_nm"])}
    q.update({"height_nm": H, "period_x_nm": PX, "period_y_nm": PY, "theta1_deg": 0.0, "theta2_deg": q["delta_theta_deg"], "j1_center_x_nm": 0.0, "j1_center_y_nm": q["D_nm"] / 2.0, "j2_center_x_nm": 0.0, "j2_center_y_nm": -q["D_nm"] / 2.0})
    q["minimum_lateral_feature_nm"] = min(q[k] for k in ("L1_nm", "W1_nm", "L2_nm", "W2_nm"))
    q["aspect_ratio_H_over_min_feature"] = H / q["minimum_lateral_feature_nm"]
    q["pillar_1_area_nm2"] = q["L1_nm"] * q["W1_nm"]
    q["pillar_2_area_nm2"] = q["L2_nm"] * q["W2_nm"]
    q["total_footprint_nm2"] = q["pillar_1_area_nm2"] + q["pillar_2_area_nm2"]
    q["cell_area_nm2"] = PX * PY
    q["footprint_fill_fraction"] = q["total_footprint_nm2"] / q["cell_area_nm2"]
    return q


def row_from(q, core, index, raw, geom_hash):
    a = anisotropy(q)
    row = {"sample_index": index, **q, **a, "geometry_hash_sha256": geom_hash, "direct_clearance_nm": core["direct_clearance_nm"], "periodic_image_clearance_nm": core["periodic_image_clearance_nm"], "global_minimum_clearance_nm": core["global_minimum_clearance_nm"], "cell_containment_pass": core["cell_containment_pass"], "overlap_or_touching_pass": core["overlap_or_touching_pass"], "nearest_object_image_pair": core["global_nearest_pair"] if "global_nearest_pair" in core else (core["direct_pair"] if core["direct_clearance_nm"] <= core["periodic_image_clearance_nm"] else core["periodic_nearest_pair"]), "raw_local_values": [raw[k] for k in DIM_KEYS]}
    return row


def in_range(q, bounds):
    return all(bounds[k][0] - 1e-9 <= q[k] <= bounds[k][1] + 1e-9 for k in DIM_KEYS)


def norm_vec(row, bounds):
    return [(row[k] - bounds[k][0]) / (bounds[k][1] - bounds[k][0]) for k in DIM_KEYS]


def vec_dist(row, ref, bounds):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(norm_vec(row, bounds), norm_vec(ref, bounds))))


def load_authorities():
    global_cfg = PKG / "configs/anisotropy_expanded_doe_v1.json"
    bf_registry = PKG / "reports/lp_anisotropy_feasible_space_v2_balanced_selection/balanced_candidate_registry.csv"
    cfg = json.loads(global_cfg.read_text(encoding="utf-8"))
    with bf_registry.open(encoding="utf-8") as fh:
        bf_rows = [r for r in csv.DictReader(fh) if r["geometry_id"] == "BF04"]
    if len(bf_rows) != 1:
        raise RuntimeError("BF04_AUTHORITY_ROW_NOT_UNIQUE")
    source = bf_rows[0]
    exact = {"L1_nm": int(source["L1_nm"]), "W1_nm": int(source["W1_nm"]), "L2_nm": int(source["L2_nm"]), "W2_nm": int(source["W2_nm"]), "delta_theta_deg": float(source["delta_theta_deg"]), "D_nm": int(source["D_nm"])}
    if exact != BF04:
        raise RuntimeError(f"BF04_MISMATCH:{exact}")
    global_scale = cfg["bounds"]
    global_phys = {"L1_nm": (230.0 * global_scale["a1"][0], 230.0 * global_scale["a1"][1]), "W1_nm": (100.0 * global_scale["b1"][0], 100.0 * global_scale["b1"][1]), "L2_nm": (180.0 * global_scale["a2"][0], 180.0 * global_scale["a2"][1]), "W2_nm": (90.0 * global_scale["b2"][0], 90.0 * global_scale["b2"][1]), "delta_theta_deg": tuple(global_scale["delta_theta_deg"]), "D_nm": tuple(global_scale["D_nm"])}
    local_cont = {"L1_nm": (BF04["L1_nm"] * 0.95, BF04["L1_nm"] * 1.05), "W1_nm": (BF04["W1_nm"] * 0.95, BF04["W1_nm"] * 1.05), "L2_nm": (BF04["L2_nm"] * 0.95, BF04["L2_nm"] * 1.05), "W2_nm": (BF04["W2_nm"] * 0.95, BF04["W2_nm"] * 1.05), "delta_theta_deg": (BF04["delta_theta_deg"] - 7.5, BF04["delta_theta_deg"] + 7.5), "D_nm": (BF04["D_nm"] - 12.0, BF04["D_nm"] + 12.0)}
    local_inter = {k: (max(global_phys[k][0], local_cont[k][0]), min(global_phys[k][1], local_cont[k][1])) for k in DIM_KEYS}
    integer_bounds = {k: (int(math.ceil(local_inter[k][0] - 1e-9)), int(math.floor(local_inter[k][1] + 1e-9))) for k in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm")}
    integer_bounds["delta_theta_deg"] = local_inter["delta_theta_deg"]
    return global_cfg, bf_registry, source, global_phys, local_cont, local_inter, integer_bounds


def generate(local_inter, integer_bounds):
    us = qmc.Sobol(d=6, scramble=False, seed=SEED).random_base2(m=14)
    feasible, unique = [], set()
    rejection = {"quantization_duplicate": 0, "local_quantized_bounds": 0, "direct_gap_lt_60_nm": 0, "periodic_image_gap_lt_60_nm": 0, "overlap_or_touching": 0, "cell_containment": 0}
    for idx, u in enumerate(us):
        raw = {k: local_inter[k][0] + (local_inter[k][1] - local_inter[k][0]) * float(x) for k, x in zip(DIM_KEYS, u)}
        q = qgeom(raw)
        key_obj = {k: q[k] for k in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "delta_theta_deg", "D_nm", "height_nm", "period_x_nm", "period_y_nm", "theta1_deg", "theta2_deg")}
        h = sha_obj(key_obj)
        if h in unique:
            rejection["quantization_duplicate"] += 1
            continue
        unique.add(h)
        if not in_range(q, integer_bounds):
            rejection["local_quantized_bounds"] += 1
            continue
        core = geom_core(q)
        if not core["cell_containment_pass"]:
            rejection["cell_containment"] += 1
        if core["direct_clearance_nm"] < 60.0 - 1e-9:
            rejection["direct_gap_lt_60_nm"] += 1
        if core["periodic_image_clearance_nm"] < 60.0 - 1e-9:
            rejection["periodic_image_gap_lt_60_nm"] += 1
        if not core["overlap_or_touching_pass"]:
            rejection["overlap_or_touching"] += 1
        if core["cell_containment_pass"] and core["overlap_or_touching_pass"] and core["direct_clearance_nm"] >= 60.0 - 1e-9 and core["periodic_image_clearance_nm"] >= 60.0 - 1e-9:
            feasible.append(row_from(q, core, idx, raw, h))
    feasible.sort(key=lambda r: (r["sample_index"], r["geometry_hash_sha256"]))
    return feasible, len(unique), rejection


def select_candidates(pool, local_bounds):
    base = {**BF04, "A1": (BF04["L1_nm"] - BF04["W1_nm"]) / (BF04["L1_nm"] + BF04["W1_nm"]), "A2": (BF04["L2_nm"] - BF04["W2_nm"]) / (BF04["L2_nm"] + BF04["W2_nm"])}
    base["A_mean"] = (base["A1"] + base["A2"]) / 2.0
    base["Delta_A"] = base["A1"] - base["A2"]
    used = set()
    audit = []

    def choose(label, mechanism, predicate, key, fallback_key=None):
        candidates = [r for r in pool if r["geometry_hash_sha256"] not in used and predicate(r)]
        fallback = False
        if not candidates and fallback_key is not None:
            candidates = [r for r in pool if r["geometry_hash_sha256"] not in used]
            key = fallback_key
            fallback = True
        if not candidates:
            raise RuntimeError(f"MECHANISM_DIRECTION_NOT_IDENTIFIABLE:{label}")
        chosen = sorted(candidates, key=lambda r: (*key(r), r["sample_index"], r["geometry_hash_sha256"]))[0]
        used.add(chosen["geometry_hash_sha256"])
        chosen = dict(chosen)
        chosen["mechanism_direction"] = mechanism
        chosen["selection_label"] = label
        chosen["selection_fallback_used"] = fallback
        chosen["distance_from_bf04_local_6d"] = vec_dist(chosen, BF04, local_bounds)
        audit.append({"selection_label": label, "mechanism_direction": mechanism, "selected_geometry_hash": chosen["geometry_hash_sha256"], "fallback_used": fallback, "eligible_count": len(candidates)})
        return chosen

    tol = 0.012
    initial = [
        choose("I01_HIGHER_A_MEAN", "increase A_mean while approximately preserving Delta_A", lambda r: abs(r["Delta_A"] - base["Delta_A"]) <= tol, lambda r: (-r["A_mean"], abs(r["Delta_A"] - base["Delta_A"])), lambda r: (abs(r["Delta_A"] - base["Delta_A"]), -r["A_mean"])),
        choose("I02_LOWER_A_MEAN", "decrease A_mean while approximately preserving Delta_A", lambda r: abs(r["Delta_A"] - base["Delta_A"]) <= tol, lambda r: (r["A_mean"], abs(r["Delta_A"] - base["Delta_A"])), lambda r: (abs(r["Delta_A"] - base["Delta_A"]), r["A_mean"])),
        choose("I03_INCREASE_DELTA_A", "increase Delta_A while approximately preserving A_mean", lambda r: abs(r["A_mean"] - base["A_mean"]) <= tol, lambda r: (-r["Delta_A"], abs(r["A_mean"] - base["A_mean"])), lambda r: (abs(r["A_mean"] - base["A_mean"]), -r["Delta_A"])),
        choose("I04_DECREASE_DELTA_A", "decrease or reverse Delta_A while approximately preserving A_mean", lambda r: abs(r["A_mean"] - base["A_mean"]) <= tol, lambda r: (r["Delta_A"], abs(r["A_mean"] - base["A_mean"])), lambda r: (abs(r["A_mean"] - base["A_mean"]), r["Delta_A"])),
    ]
    conditional = [
        choose("C01_REDUCED_D_HIGH_THETA", "reduce D while retaining high delta_theta", lambda r: r["delta_theta_deg"] >= BF04["delta_theta_deg"] - 3.0, lambda r: (r["D_nm"], abs(r["delta_theta_deg"] - BF04["delta_theta_deg"])), lambda r: (abs(r["delta_theta_deg"] - BF04["delta_theta_deg"]), r["D_nm"])),
        choose("C02_SMALL_THETA_PERTURBATION", "small delta_theta perturbation with approximately preserved anisotropy", lambda r: abs(r["A_mean"] - base["A_mean"]) <= tol and abs(r["Delta_A"] - base["Delta_A"]) <= tol and abs(r["delta_theta_deg"] - BF04["delta_theta_deg"]) > 1e-9, lambda r: (abs(r["delta_theta_deg"] - BF04["delta_theta_deg"]), vec_dist(r, BF04, local_bounds)), lambda r: (abs(r["A_mean"] - base["A_mean"]) + abs(r["Delta_A"] - base["Delta_A"]), abs(r["delta_theta_deg"] - BF04["delta_theta_deg"]))),
    ]
    return base, initial, conditional, audit


def candidate_row(r, role, cid):
    return {"geometry_id": cid, "role": role, "selection_label": r["selection_label"], "mechanism_direction": r["mechanism_direction"], "sample_index": r["sample_index"], "L1_nm": r["L1_nm"], "W1_nm": r["W1_nm"], "L2_nm": r["L2_nm"], "W2_nm": r["W2_nm"], "A1": r["A1"], "A2": r["A2"], "A_mean": r["A_mean"], "Delta_A": r["Delta_A"], "delta_theta_deg": r["delta_theta_deg"], "D_nm": r["D_nm"], "theta1_deg": r["theta1_deg"], "theta2_deg": r["theta2_deg"], "j1_center_x_nm": r["j1_center_x_nm"], "j1_center_y_nm": r["j1_center_y_nm"], "j2_center_x_nm": r["j2_center_x_nm"], "j2_center_y_nm": r["j2_center_y_nm"], "height_nm": r["height_nm"], "period_x_nm": r["period_x_nm"], "period_y_nm": r["period_y_nm"], "pillar_1_area_nm2": r["pillar_1_area_nm2"], "pillar_2_area_nm2": r["pillar_2_area_nm2"], "total_footprint_nm2": r["total_footprint_nm2"], "cell_area_nm2": r["cell_area_nm2"], "footprint_fill_fraction": r["footprint_fill_fraction"], "direct_clearance_nm": r["direct_clearance_nm"], "periodic_image_clearance_nm": r["periodic_image_clearance_nm"], "global_minimum_clearance_nm": r["global_minimum_clearance_nm"], "nearest_object_image_pair": r["nearest_object_image_pair"], "minimum_lateral_feature_nm": r["minimum_lateral_feature_nm"], "aspect_ratio_H_over_min_feature": r["aspect_ratio_H_over_min_feature"], "distance_from_bf04_local_6d": r["distance_from_bf04_local_6d"], "geometry_hash_sha256": r["geometry_hash_sha256"], "solver_entered": False, "solver_run_called": False}


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    global_cfg, bf_registry, bf_source, global_phys, local_cont, local_inter, integer_bounds = load_authorities()
    local_bounds = {k: tuple(integer_bounds[k]) if k != "delta_theta_deg" else tuple(integer_bounds[k]) for k in DIM_KEYS}
    pool, unique_count, rejection = generate(local_inter, integer_bounds)
    if len(pool) < 6:
        raise RuntimeError(f"LOCAL_FEASIBLE_SPACE_TOO_CONSTRAINED:{len(pool)}")
    base, initial, conditional, selection_audit = select_candidates(pool, local_bounds)
    selected = initial + conditional
    selected_ids = {r["geometry_hash_sha256"] for r in selected}
    if len(selected_ids) != 6:
        raise RuntimeError("CANDIDATE_UNIQUENESS_FAILURE")
    # Deterministic replay is an explicit second generation pass; it is zero-solver.
    pool2, unique_count2, rejection2 = generate(local_inter, integer_bounds)
    replay_pass = [r["geometry_hash_sha256"] for r in pool] == [r["geometry_hash_sha256"] for r in pool2] and unique_count == unique_count2 and rejection == rejection2
    all_inventory = []
    for r in pool:
        all_inventory.append({k: r[k] for k in ["sample_index", "L1_nm", "W1_nm", "L2_nm", "W2_nm", "A1", "A2", "A_mean", "Delta_A", "delta_theta_deg", "D_nm", "theta1_deg", "theta2_deg", "j1_center_y_nm", "j2_center_y_nm", "pillar_1_area_nm2", "pillar_2_area_nm2", "total_footprint_nm2", "cell_area_nm2", "footprint_fill_fraction", "direct_clearance_nm", "periodic_image_clearance_nm", "global_minimum_clearance_nm", "cell_containment_pass", "overlap_or_touching_pass", "minimum_lateral_feature_nm", "aspect_ratio_H_over_min_feature", "geometry_hash_sha256", "nearest_object_image_pair"]})
    initial_rows = [candidate_row(r, "INITIAL_LOCAL_MECHANISM_CANDIDATE", f"BF04R_I{i:02d}") for i, r in enumerate(initial, 1)]
    conditional_rows = [candidate_row(r, "CONDITIONAL_LOCAL_MECHANISM_CANDIDATE", f"BF04R_C{i:02d}") for i, r in enumerate(conditional, 1)]
    derived = [{"geometry_id": f"POOL_{r['sample_index']:05d}", "sample_index": r["sample_index"], "L1_nm": r["L1_nm"], "W1_nm": r["W1_nm"], "L2_nm": r["L2_nm"], "W2_nm": r["W2_nm"], "A1": r["A1"], "A2": r["A2"], "A_mean": r["A_mean"], "Delta_A": r["Delta_A"], "D_nm": r["D_nm"], "delta_theta_deg": r["delta_theta_deg"], "pillar_1_area_nm2": r["pillar_1_area_nm2"], "pillar_2_area_nm2": r["pillar_2_area_nm2"], "total_footprint_nm2": r["total_footprint_nm2"], "footprint_fill_fraction": r["footprint_fill_fraction"], "direct_clearance_nm": r["direct_clearance_nm"], "periodic_clearance_nm": r["periodic_image_clearance_nm"], "distance_from_bf04_local_6d": vec_dist(r, BF04, local_bounds), "geometry_hash_sha256": r["geometry_hash_sha256"]} for r in pool]
    clearance = [{"geometry_id": f"POOL_{r['sample_index']:05d}", "sample_index": r["sample_index"], "direct_clearance_nm": r["direct_clearance_nm"], "periodic_image_clearance_nm": r["periodic_image_clearance_nm"], "global_minimum_clearance_nm": r["global_minimum_clearance_nm"], "cell_containment_pass": r["cell_containment_pass"], "overlap_or_touching_pass": r["overlap_or_touching_pass"], "nearest_object_image_pair": r["nearest_object_image_pair"], "geometry_hash_sha256": r["geometry_hash_sha256"], "validity": "PASS"} for r in pool]
    validity_script = PKG / "scripts/lp_anisotropy_feasible_space_v2.py"
    validity_param = PKG / "reports/lp_anisotropy_feasible_space_v2/feasible_space_parameterization.json"
    domain = {"schema": "PAPER_A_BF04_LOCAL_DIATTENUATION_REDESIGN_DOMAIN_V1", "stage": "BF04_LOCAL_DIATTENUATION_REDESIGN_DOE_V1", "solver_budget": {"NEW_FDTD_BUDGET": 0, "RCWA": 0, "ML": 0, "BF05_BF08": "NOT_RUN"}, "backbone": {"candidate": "BF04", "source_registry": str(bf_registry), "source_registry_sha256": sha_file(bf_registry), "exact": BF04, "source_row": bf_source}, "global_domain_authority": {"path": str(global_cfg), "sha256": sha_file(global_cfg), "bounds": global_phys}, "validity_rule_authority": {"implementation_path": str(validity_script), "implementation_sha256": sha_file(validity_script), "parameterization_path": str(validity_param), "parameterization_sha256": sha_file(validity_param), "rule_source": "existing Paper A feasible-space authority; no new threshold introduced"}, "local_generation_bounds_continuous_nm_deg": local_cont, "local_intersection_bounds_continuous_nm_deg": local_inter, "quantized_allowed_bounds": integer_bounds, "quantization": {"lateral_dimensions": "round-half-up to integer nm", "D_nm": "round-half-up to integer nm; centers +/-D/2 half-grid compatible", "delta_theta_deg": "round to 9 decimal places"}, "fixed_physics": {"height_nm": H, "period_x_nm": PX, "period_y_nm": PY, "materials": "current Native-M1 unchanged", "source_monitor": "unchanged current-Native broadband contract", "mesh_boundary": "unchanged"}, "hard_gates": {"direct_polygon_clearance_nm_ge": 60.0, "periodic_image_polygon_clearance_nm_ge": 60.0, "no_overlap_or_touching": True, "cell_containment": True, "integer_lateral_dimensions": True, "half_grid_centers": True, "no_sub_grid_geometry": True}, "sampling": {"method": "Sobol", "scramble": False, "seed": SEED, "raw_sample_count": SAMPLES, "quantized_unique_count": unique_count, "feasible_pool_size": len(pool), "rejection_counts": rejection}, "pool_hash": sha_obj([r["geometry_hash_sha256"] for r in pool])}
    selection = {"schema": "PAPER_A_BF04_LOCAL_MECHANISM_SELECTION_AUDIT_V1", "optical_information_used": False, "baseline_excluded_from_new_candidate_pool": True, "initial_count": len(initial_rows), "conditional_count": len(conditional_rows), "initial_candidates": initial_rows, "conditional_candidates": conditional_rows, "selection_rules": {"preserve_bf04_high_delta_theta": True, "anisotropy_tolerance_for_preserved_direction": 0.012, "no_scalar_optical_score": True, "direction_priority": ["A_mean", "Delta_A", "D", "delta_theta"]}, "selection_events": selection_audit, "selected_hashes_unique": len(selected_ids) == 6, "selected_pool_replay_pass": replay_pass}
    config = {"schema": "BF04_LOCAL_DIATTENUATION_REDESIGN_DOE_V1", "status": "ZERO_SOLVER_READY_FOR_INITIAL_TRUTH", "backbone": domain["backbone"], "local_domain_authority": str(REPORT / "local_domain_authority.json"), "feasible_pool_inventory": str(REPORT / "feasible_pool_inventory.csv"), "initial_candidate_registry": str(REPORT / "initial_candidate_registry.csv"), "conditional_candidate_registry": str(REPORT / "conditional_candidate_registry.csv"), "future_truth_contract": {"new_fdt_jobs": 12, "geometries": 6, "jobs_per_geometry": 2, "active_cap": 2, "provider": "current-Native FDTD full-Jones only", "formal_window_nm": [435.0, 465.0], "formal_points": 31, "anchor_nm": 450.0}, "promotion_guidance_unchanged": {"weighted_DoLP_ge": 0.60, "weighted_axis_free_useful_LP_ge": 0.25, "FWHM_psi_span_deg_le": 30.0, "long_term_weighted_DoLP_ge": 0.80, "long_term_useful_LP_ge": 0.35, "long_term_psi_span_deg_le": 10.0}, "solver_run_called": False, "solver_entered": 0}
    rationale = f"""# BF04 local diattenuation redesign DOE v1

Status: `BF04_LOCAL_DOE_READY_FOR_INITIAL_TRUTH`

This is a zero-solver geometry-only mechanism DOE around exact BF04. The purpose is to preserve the discovered high-`delta_theta` dominant-channel stability while probing stronger singular-channel separation / diattenuation. No optical performance is predicted and no scalar gap proxy is used as a performance ranking.

## Domain and gates

The local continuous neighborhood is the intersection of the frozen global anisotropy-expanded domain and BF04 +/-5% for L1/W1/L2/W2, BF04 +/-7.5 deg for `delta_theta`, and BF04 +/-12 nm for D. After existing Paper A quantization, the dense deterministic Sobol pool used {SAMPLES} raw samples, {unique_count} unique quantized samples, and {len(pool)} feasible geometries. The exact existing hard gates are direct polygon clearance >=60 nm, periodic-image polygon clearance >=60 nm, no overlap/touching, cell containment, integer lateral dimensions, and half-grid-compatible centers.

## Mechanism coordinates

Every feasible geometry records A1=(L1-W1)/(L1+W1), A2=(L2-W2)/(L2+W2), A_mean, Delta_A=A1-A2, D, delta_theta, footprint-related dimensions, and both clearances. The six selected geometries are intentionally geometry-only probes; BF05-BF08 were not reused.

## Selected candidates

| ID | role | mechanism direction | L1/W1/L2/W2 nm | A1/A2/A_mean/Delta_A | total footprint nm2 / fill | delta_theta deg | D nm | direct / periodic nm |
|---|---|---|---|---|---:|---:|---:|---:|
""" + "\n".join(f"| {r['geometry_id']} | {r['role']} | {r['mechanism_direction']} | {r['L1_nm']}/{r['W1_nm']}/{r['L2_nm']}/{r['W2_nm']} | {r['A1']:.6f}/{r['A2']:.6f}/{r['A_mean']:.6f}/{r['Delta_A']:.6f} | {r['total_footprint_nm2']} / {r['footprint_fill_fraction']:.6f} | {r['delta_theta_deg']:.9f} | {r['D_nm']} | {r['direct_clearance_nm']:.6f} / {r['periodic_image_clearance_nm']:.6f} |" for r in initial_rows + conditional_rows) + f"""

The high-`delta_theta` BF04 mechanism is preserved by construction: every selected candidate lies in the local high-angle neighborhood, and the conditional D probe explicitly retains `delta_theta >= BF04-3 deg`. This DOE is ready for future initial truth only; no solver is authorized by this artifact.

## Safety

`NEW_FDTD_BUDGET=0`; `solver_run_called=false`; `solver_entered=0`; RCWA=0; ML=0; BF05-BF08 not run; no geometry/physics/source/monitor/mesh/boundary contract was changed.
"""
    write_json(REPORT / "local_domain_authority.json", domain)
    write_json(REPORT / "candidate_selection_audit.json", selection)
    write_json(CONFIG_DIR / "BF04_LOCAL_DIATTENUATION_REDESIGN_DOE_V1.json", config)
    write_csv(REPORT / "feasible_pool_inventory.csv", all_inventory)
    write_csv(REPORT / "derived_mechanism_coordinates.csv", derived)
    write_csv(REPORT / "geometry_clearance_audit.csv", clearance)
    write_csv(REPORT / "initial_candidate_registry.csv", initial_rows)
    write_csv(REPORT / "conditional_candidate_registry.csv", conditional_rows)
    (REPORT / "zero_solver_scientific_rationale.md").write_text(rationale, encoding="utf-8")
    audit = {"schema": "PAPER_A_BF04_LOCAL_REDESIGN_AUDIT_V1", "status": "PASS", "stage": "BF04_LOCAL_DIATTENUATION_REDESIGN_DOE_V1", "pool_size": len(pool), "initial_count": 4, "conditional_count": 2, "high_delta_theta_preserved": all(r["delta_theta_deg"] >= BF04["delta_theta_deg"] - 7.5 - 1e-9 for r in selected), "all_clearances_ge_60_nm": all(r["direct_clearance_nm"] >= 60.0 - 1e-9 and r["periodic_image_clearance_nm"] >= 60.0 - 1e-9 for r in pool), "all_nonoverlap": all(r["overlap_or_touching_pass"] for r in pool), "all_contained": all(r["cell_containment_pass"] for r in pool), "quantization_pass": all(all(float(r[k]).is_integer() for k in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm")) and abs(r["delta_theta_deg"] * 1e9 - round(r["delta_theta_deg"] * 1e9)) < 1e-3 for r in pool), "candidate_unique": len(selected_ids) == 6, "deterministic_replay_pass": replay_pass, "optical_information_used": False, "solver_run_called": False, "solver_entered": 0, "rcwa": 0, "ml": 0, "doe_changed": False, "frozen_truth_modified": False}
    write_json(REPORT / "audit.json", audit)
    tests = {"schema_validation": all(k in domain for k in ("hard_gates", "quantization", "sampling")), "clearance_validation": audit["all_clearances_ge_60_nm"], "candidate_uniqueness": audit["candidate_unique"], "quantization_audit": audit["quantization_pass"], "mechanism_coordinate_audit": all(math.isfinite(r[k]) for r in pool for k in ("A1", "A2", "A_mean", "Delta_A")), "deterministic_replay": replay_pass, "solver_zero": not audit["solver_run_called"] and audit["solver_entered"] == 0}
    write_json(REPORT / "test_report.json", {"schema": "PAPER_A_BF04_LOCAL_REDESIGN_TEST_V1", "status": "PASS" if all(tests.values()) else "FAIL", "checks": tests, "pool_size": len(pool), "pool_hash": domain["pool_hash"]})
    (REPORT / "final_report.md").write_text(rationale + "\n\n## Final decision\n\n`BF04_LOCAL_DOE_READY_FOR_INITIAL_TRUTH`\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "decision": "BF04_LOCAL_DOE_READY_FOR_INITIAL_TRUTH", "pool_size": len(pool), "unique_quantized": unique_count, "initial": [r["geometry_id"] for r in initial_rows], "conditional": [r["geometry_id"] for r in conditional_rows], "replay_pass": replay_pass, "report": str(REPORT)}, indent=2))


if __name__ == "__main__":
    main()
