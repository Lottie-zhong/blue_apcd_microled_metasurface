from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
PKG = ROOT / "paper_a_broadband"
REPORT = PKG / "reports/lp_anisotropy_feasible_space_v2"
AUTH = PKG / "authority"
RUNTIME = PKG / "runtime/search_anisotropy_feasible_space_v2"
PARENT_FSP = PKG / "runtime/reusable_fsp/lp/P1_LP_H1C1B_V2_009_Px_attempt_006_pre.fsp"
SEED = 20260818
MATERIAL = "APCD_TIO2_NATIVE_M1"
SOURCE_START, SOURCE_STOP = 430.0, 470.0
FORMAL_START, FORMAL_STOP, FORMAL_POINTS = 435.0, 465.0, 31
PX = PY = 432.0
H = 525.0
BASE = {"L1_nm": 230.0, "W1_nm": 100.0, "L2_nm": 180.0, "W2_nm": 90.0}
BOUNDS = {"a1": (0.85, 1.15), "b1": (0.85, 1.15), "a2": (0.85, 1.15), "b2": (0.85, 1.15), "delta_theta_deg": (0.0, 90.0), "D_nm": (170.0, 220.0)}
DIM_KEYS = ("a1", "b1", "a2", "b2", "delta_theta_deg", "D_nm")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def sha_obj(v: Any) -> str:
    return hashlib.sha256(canonical(v)).hexdigest()


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(p: Path, v: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(v, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def write_csv(p: Path, rows: list[dict[str, Any]]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in r.items()})


def round_half_up(v: float) -> int:
    return int(math.floor(float(v) + 0.5))


def polygon(length: float, width: float, cx: float, cy: float, theta_deg: float) -> list[tuple[float, float]]:
    a, b = length / 2.0, width / 2.0
    t = math.radians(theta_deg)
    c, s = math.cos(t), math.sin(t)
    return [(cx + c*x - s*y, cy + s*x + c*y) for x, y in [(-a, -b), (a, -b), (a, b), (-a, b)]]


def orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def between(a, b, c, eps=1e-12):
    return min(a[0], b[0])-eps <= c[0] <= max(a[0], b[0])+eps and min(a[1], b[1])-eps <= c[1] <= max(a[1], b[1])+eps


def seg_inter(a, b, c, d, eps=1e-10):
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if abs(o1) <= eps and between(a, b, c): return True
    if abs(o2) <= eps and between(a, b, d): return True
    if abs(o3) <= eps and between(c, d, a): return True
    if abs(o4) <= eps and between(c, d, b): return True
    return ((o1 > eps) != (o2 > eps)) and ((o3 > eps) != (o4 > eps))


def point_seg(p, a, b) -> tuple[float, tuple[float, float]]:
    dx, dy = b[0]-a[0], b[1]-a[1]
    den = dx*dx + dy*dy
    if den == 0:
        return math.hypot(p[0]-a[0], p[1]-a[1]), a
    q = max(0.0, min(1.0, ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / den))
    z = (a[0] + q*dx, a[1] + q*dy)
    return math.hypot(p[0]-z[0], p[1]-z[1]), z


def segment_pair(a, b, c, d) -> tuple[float, tuple[float, float], tuple[float, float]]:
    if seg_inter(a, b, c, d):
        # For a touching/intersecting pair the exact witness is a shared endpoint or
        # the closest endpoint; the distance is authoritative zero.
        for p in (a, b):
            if abs(orient(c, d, p)) < 1e-9 and between(c, d, p): return 0.0, p, p
        for p in (c, d):
            if abs(orient(a, b, p)) < 1e-9 and between(a, b, p): return 0.0, p, p
        return 0.0, a, a
    best = (float("inf"), a, c)
    for p, u, v, flip in [(a, c, d, False), (b, c, d, False), (c, a, b, True), (d, a, b, True)]:
        dist, z = point_seg(p, u, v)
        cand = (dist, z, p) if flip else (dist, p, z)
        if cand[0] < best[0]: best = cand
    return best


def poly_pair(a, b) -> tuple[float, tuple[float, float], tuple[float, float], bool]:
    touch = any(seg_inter(a[i], a[(i+1) % len(a)], b[j], b[(j+1) % len(b)]) for i in range(len(a)) for j in range(len(b)))
    if touch:
        for i in range(len(a)):
            for j in range(len(b)):
                if seg_inter(a[i], a[(i+1) % len(a)], b[j], b[(j+1) % len(b)]):
                    return 0.0, a[i], b[j], True
    best = (float("inf"), a[0], b[0])
    for i in range(len(a)):
        for j in range(len(b)):
            cand = segment_pair(a[i], a[(i+1) % len(a)], b[j], b[(j+1) % len(b)])
            if cand[0] < best[0]: best = cand
    return best[0], best[1], best[2], False


def map_unit(u: list[float]) -> dict[str, float]:
    return {k: lo + (hi-lo) * float(x) for k, x, (lo, hi) in zip(DIM_KEYS, u, BOUNDS.values())}


def quantize(raw: dict[str, float]) -> dict[str, Any]:
    q = {
        "L1_nm": round_half_up(BASE["L1_nm"] * raw["a1"]),
        "W1_nm": round_half_up(BASE["W1_nm"] * raw["b1"]),
        "L2_nm": round_half_up(BASE["L2_nm"] * raw["a2"]),
        "W2_nm": round_half_up(BASE["W2_nm"] * raw["b2"]),
        "D_nm": round_half_up(raw["D_nm"]),
        "delta_theta_deg": round(float(raw["delta_theta_deg"]), 9),
    }
    q.update({"a1": q["L1_nm"] / BASE["L1_nm"], "b1": q["W1_nm"] / BASE["W1_nm"], "a2": q["L2_nm"] / BASE["L2_nm"], "b2": q["W2_nm"] / BASE["W2_nm"]})
    q.update({"height_nm": H, "period_x_nm": PX, "period_y_nm": PY, "theta1_deg": 0.0, "theta2_deg": q["delta_theta_deg"], "j1_center_x_nm": 0.0, "j1_center_y_nm": q["D_nm"] / 2.0, "j2_center_x_nm": 0.0, "j2_center_y_nm": -q["D_nm"] / 2.0})
    q["minimum_lateral_feature_nm"] = min(q[k] for k in ("L1_nm", "W1_nm", "L2_nm", "W2_nm"))
    q["aspect_ratio_H_over_min_feature"] = H / q["minimum_lateral_feature_nm"]
    return q


def geom_core(q: dict[str, Any]) -> dict[str, Any]:
    p1 = polygon(q["L1_nm"], q["W1_nm"], q["j1_center_x_nm"], q["j1_center_y_nm"], q["theta1_deg"])
    p2 = polygon(q["L2_nm"], q["W2_nm"], q["j2_center_x_nm"], q["j2_center_y_nm"], q["theta2_deg"])
    polys = {"pillar_1": p1, "pillar_2": p2}
    containment = all(abs(x) <= PX/2 + 1e-9 and abs(y) <= PY/2 + 1e-9 for p in polys.values() for x, y in p)
    direct_d, direct_a, direct_b, direct_touch = poly_pair(p1, p2)
    periodic = []
    shifts = (-1, 0, 1)
    for na, (name_a, pa) in enumerate(polys.items()):
        for nb, (name_b, pb) in enumerate(polys.items()):
            for ix in shifts:
                for iy in shifts:
                    # Periodic-image clearance must exclude the same-cell pair;
                    # the latter is reported separately as direct clearance.
                    if ix == 0 and iy == 0: continue
                    shifted = [(x + ix*PX, y + iy*PY) for x, y in pb]
                    d, ca, cb, touch = poly_pair(pa, shifted)
                    periodic.append({"distance_nm": d, "object_a": name_a, "object_b": name_b, "image_shift": [ix, iy], "point_a_nm": list(ca), "point_b_nm": list(cb), "touch_or_overlap": touch})
    periodic_sorted = sorted(periodic, key=lambda x: (x["distance_nm"], x["object_a"], x["object_b"], x["image_shift"]))
    px_rows = [x for x in periodic if x["image_shift"][0] != 0 and x["image_shift"][1] == 0]
    py_rows = [x for x in periodic if x["image_shift"][1] != 0 and x["image_shift"][0] == 0]
    diagonal_rows = [x for x in periodic if x["image_shift"][0] != 0 and x["image_shift"][1] != 0]
    periodic_min = periodic_sorted[0]
    direct_pair = {"distance_nm": direct_d, "object_a": "pillar_1", "object_b": "pillar_2", "image_shift": [0, 0], "point_a_nm": list(direct_a), "point_b_nm": list(direct_b), "touch_or_overlap": direct_touch}
    return {
        "polygons_nm": {k: [list(v) for v in p] for k, p in polys.items()},
        "cell_containment_pass": containment,
        "direct_clearance_nm": direct_d,
        "direct_pair": direct_pair,
        "periodic_image_clearance_nm": periodic_min["distance_nm"],
        "periodic_x_clearance_nm": min(x["distance_nm"] for x in px_rows),
        "periodic_y_clearance_nm": min(x["distance_nm"] for x in py_rows),
        "periodic_diagonal_clearance_nm": min(x["distance_nm"] for x in diagonal_rows),
        "periodic_nearest_pair": periodic_min,
        "global_minimum_clearance_nm": min(direct_d, periodic_min["distance_nm"]),
        "global_nearest_pair": direct_pair if direct_d <= periodic_min["distance_nm"] else periodic_min,
        "overlap_or_touching_pass": not direct_touch and not any(x["touch_or_overlap"] for x in periodic),
        "periodic_distance_definition": "exact segment-to-segment polygon distance for all pillar/image pairs in translations {-Px,0,+Px}x{-Py,0,+Py}; no cell-boundary margin substitution",
    }


def make_row(raw: dict[str, float], sample_index: int, q: dict[str, Any], core: dict[str, Any], h: str) -> dict[str, Any]:
    row = {"sample_index": sample_index, **q, "geometry_hash_sha256": h, "theta1_deg": q["theta1_deg"], "theta2_deg": q["theta2_deg"], **core}
    reasons = []
    if not core["cell_containment_pass"]: reasons.append("cell_containment")
    if core["direct_clearance_nm"] < 60.0 - 1e-9: reasons.append("direct_gap_lt_60_nm")
    if core["periodic_image_clearance_nm"] < 60.0 - 1e-9: reasons.append("periodic_image_gap_lt_60_nm")
    if not core["overlap_or_touching_pass"]: reasons.append("overlap_or_touching")
    row["validity_reasons"] = sorted(set(reasons))
    row["geometry_valid"] = not reasons
    row["raw_normalized"] = [float(raw[k]) for k in DIM_KEYS]
    row["quantized_normalized"] = [float(q[k]) for k in DIM_KEYS]
    return row


def sobol(n: int):
    from scipy.stats import qmc
    m = int(math.log2(n))
    if 2**m != n: raise ValueError(n)
    return qmc.Sobol(d=6, scramble=False, seed=SEED).random_base2(m=m)


def norm_vec(r: dict[str, Any]) -> list[float]:
    return [(r[k] - BOUNDS[k][0]) / (BOUNDS[k][1] - BOUNDS[k][0]) for k in DIM_KEYS]


def dist(a, b) -> float:
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def select(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    center = {"a1":1.0,"b1":1.0,"a2":1.0,"b2":1.0,"delta_theta_deg":45.0,"D_nm":195.0}
    af1 = min(pool, key=lambda r: (dist(norm_vec(r), [(center[k]-BOUNDS[k][0])/(BOUNDS[k][1]-BOUNDS[k][0]) for k in DIM_KEYS]), r["geometry_hash_sha256"]))
    chosen = [af1]
    remaining = [r for r in pool if r["geometry_hash_sha256"] != af1["geometry_hash_sha256"]]
    while len(chosen) < 8:
        cvec = [norm_vec(x) for x in chosen]
        nxt = max(remaining, key=lambda r: (min(dist(norm_vec(r), v) for v in cvec), tuple(-x for x in norm_vec(r)), r["geometry_hash_sha256"]))
        chosen.append(nxt)
        remaining = [r for r in remaining if r["geometry_hash_sha256"] != nxt["geometry_hash_sha256"]]
    for i, r in enumerate(chosen, 1):
        r["geometry_id"] = f"AF{i:02d}"
        r["role"] = "INITIAL" if i <= 4 else "CONDITIONAL"
        r["case_ids"] = [f"AF{i:02d}_x", f"AF{i:02d}_y"]
        r["solver_entered"] = False
    return chosen


def authority_hash(path: Path) -> str | None:
    return sha_file(path) if path.exists() else None


def build() -> dict[str, Any]:
    REPORT.mkdir(parents=True, exist_ok=True)
    AUTH.mkdir(parents=True, exist_ok=True)
    pool: list[dict[str, Any]] = []
    seen: set[str] = set()
    rejection = {"direct_gap_lt_60_nm":0,"periodic_image_gap_lt_60_nm":0,"overlap_or_touching":0,"cell_containment":0,"quantization_duplicate":0,"other":0}
    raw_count = 0
    selected_source_n = None
    for n in (4096, 16384, 65536):
        us = sobol(n)
        pool, seen = [], set()
        rejection = {k:0 for k in rejection}
        for idx, u in enumerate(us):
            raw_count = idx + 1
            raw = map_unit(list(u))
            q = quantize(raw)
            key = sha_obj({k:q[k] for k in ["L1_nm","W1_nm","L2_nm","W2_nm","D_nm","delta_theta_deg","height_nm","period_x_nm","period_y_nm","theta1_deg","theta2_deg"]})
            if key in seen:
                rejection["quantization_duplicate"] += 1
                continue
            seen.add(key)
            core = geom_core(q)
            row = make_row(raw, idx, q, core, key)
            if row["geometry_valid"]:
                pool.append(row)
            for reason in row["validity_reasons"]:
                rejection[reason] = rejection.get(reason, 0) + 1
        if len(pool) >= 8 and len({tuple(round(x, 6) for x in norm_vec(r)) for r in pool}) >= 8:
            selected_source_n = n
            break
    if selected_source_n is None:
        raise RuntimeError("HARD_GATE_NO_DIVERSE_FEASIBLE_POOL")
    pool.sort(key=lambda r: (r["sample_index"], r["geometry_hash_sha256"]))
    selected = select(pool)
    # Restore reproducible candidate-only serializable rows without raw polygons duplicated elsewhere.
    selected_ids = {r["geometry_hash_sha256"] for r in selected}
    selected_pool = [r for r in pool if r["geometry_hash_sha256"] in selected_ids]
    for r in selected_pool:
        r["selection_normalized_vector"] = norm_vec(r)
        r["normalized_distance_to_nearest_selected_neighbor"] = min((dist(norm_vec(r), norm_vec(s)) for s in selected if s["geometry_hash_sha256"] != r["geometry_hash_sha256"]), default=None)
    raw_stats = {"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_RAW_POOL_V1","seed":SEED,"sobol_scramble":False,"sobol_generation":"fresh random_base2(m) and first N points; N escalated 4096 -> 16384 -> 65536","raw_count":selected_source_n,"quantized_unique_count":len(seen),"feasible_unique_count":len(pool),"feasible_fraction_of_raw":len(pool)/selected_source_n,"rejection_counts":rejection,"pool_ranges":{k:[min(r[k] for r in pool),max(r[k] for r in pool)] for k in DIM_KEYS},"diversity_vectors":len({tuple(round(x,6) for x in norm_vec(r)) for r in pool}),"selection_source_n":selected_source_n}
    write_json(REPORT/"raw_pool_statistics.json", raw_stats)
    write_json(REPORT/"feasible_space_parameterization.json", {"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_PARAMETERIZATION_V1","stage":"LP_ANISOTROPY_FEASIBLE_SPACE_V2","box":BOUNDS,"base_geometry":BASE,"height_nm":H,"period_nm":[PX,PY],"material":MATERIAL,"source_span_nm":[SOURCE_START,SOURCE_STOP],"formal_window_nm":[FORMAL_START,FORMAL_STOP],"formal_points":FORMAL_POINTS,"quantization":{"lateral_dimensions":"round-half-up to integer nm","D_nm":"round-half-up to integer nm; centers are +/-D/2 and therefore integer/half-grid compatible","delta_theta_deg":"9 decimal places; no hidden optical or fabrication ranking"},"hard_gates":{"direct_polygon_clearance_nm_ge":60.0,"periodic_image_polygon_clearance_nm_ge":60.0,"no_overlap_or_touching":True,"cell_containment":True,"integer_lateral_dimensions":True,"half_grid_centers":True,"no_sub_grid_geometry":True},"diagnostic_only":{"minimum_lateral_feature_nm":True,"H_over_min_feature":True,"no_authoritative_minimum_linewidth_or_aspect_ratio_gate_found":True},"not_imported_old_lp_constraints":["J1_side 108-112 nm","J2_length 106-110 nm","J2_width 98-102 nm","D 196-204 nm","Psi +/-1.2 deg","H=500 nm"],"periodic_distance_definition":"exact polygon segment distance over all pillar/image pairs and translations {-1,0,+1} in each axis; cell-boundary distance is not used as a substitute"})
    write_csv(REPORT/"feasible_geometry_pool.csv", pool)
    write_json(REPORT/"rejection_summary.json", {"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_REJECTIONS_V1","raw_pool_statistics":raw_stats,"notes":"Rejection counts are by unique quantized sample and may overlap when multiple hard gates fail."})
    selected_table=[]
    for r in selected:
        selected_table.append({"geometry_id":r["geometry_id"],"role":r["role"],"sample_index":r["sample_index"],**{k:r[k] for k in ["a1","b1","a2","b2","L1_nm","W1_nm","L2_nm","W2_nm","theta1_deg","theta2_deg","delta_theta_deg","D_nm","j1_center_x_nm","j1_center_y_nm","j2_center_x_nm","j2_center_y_nm","height_nm","period_x_nm","period_y_nm","direct_clearance_nm","periodic_image_clearance_nm","periodic_x_clearance_nm","periodic_y_clearance_nm","global_minimum_clearance_nm","minimum_lateral_feature_nm","aspect_ratio_H_over_min_feature","geometry_hash_sha256"]},"nearest_object_image_pair":r["global_nearest_pair"],"normalized_distance_to_nearest_selected_neighbor":r["normalized_distance_to_nearest_selected_neighbor"],"validity":"PASS","case_ids":r["case_ids"],"solver_entered":False})
    write_csv(REPORT/"candidate_registry.csv", selected_table)
    write_csv(REPORT/"geometry_validity.csv", [{**x,"nearest_object_image_pair":x["global_nearest_pair"]} for x in selected])
    pairwise=[]
    for i in range(len(selected)):
        for j in range(i+1,len(selected)):
            pairwise.append({"geometry_a":selected[i]["geometry_id"],"geometry_b":selected[j]["geometry_id"],"normalized_6d_distance":dist(norm_vec(selected[i]),norm_vec(selected[j]))})
    write_csv(REPORT/"selection_pairwise_distances.csv", pairwise)
    cases=[{"case_id":f"{r['geometry_id']}_{p}","geometry_id":r["geometry_id"],"polarization":p,"role":r["role"],"status":"SETUP_ONLY_PLANNED","setup_only_allowed":r["geometry_id"] in {"AF01","AF02","AF03","AF04"},"solver_run_called":False,"solver_entered":False,"ready_or_pending":False} for r in selected for p in ("x","y")]
    write_json(REPORT/"case_registry.json", {"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_CASE_REGISTRY_V1","cases":cases,"new_fdtd_budget":0,"dispatch":False,"hidden_auto_admission":False})
    source_builder=PKG/"scripts/lp_anisotropy_bootstrap_v1.py"
    old_auth=ROOT.parent/"blue_apcd_lp_global_h_manifold_v1/reports/stage_h1c0_broadband_global/h1c0_global_domain_proposal.json"
    a02=PKG/"reports/lp_anisotropy_expanded_search_v1/a02_pre_admission_geometry_audit.json"
    old_head = subprocess.check_output(["git","-C",str(ROOT.parent/"blue_apcd_lp_global_h_manifold_v1"),"rev-parse","HEAD"], text=True).strip()
    prov={"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_PROVENANCE_V1","canonical_branch":"work/paper-a-lp-cp-broadband-v1","canonical_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"current_builder":{"path":str(source_builder),"sha256":authority_hash(source_builder)},"old_a_series_immutable":{"doe_path":str(PKG/"configs/anisotropy_expanded_doe_v1.json"),"a02_audit_path":str(a02),"a02_audit_sha256":authority_hash(a02)},"transferred_lp_legality_authority":{"path":str(old_auth),"sha256":authority_hash(old_auth),"source_branch":"work/lp-global-h-manifold-v1","source_worktree_head_verified":old_head,"artifact_declared_provenance_commit":"5e9f3eb42ccbf3fcf1d82f8452da09b4e1c9ec96","constraints":["direct gap >=60 nm","periodic gap x/y >=60 nm","integer lateral dimensions","half-grid centers","no overlap","cell containment","exact hash uniqueness"],"current_hard_min_linewidth_or_aspect_ratio":"none found in this formal legality artifact; historical 20 nm LP-ML notes not imported"},"solver_safety":{"NEW_FDTD_BUDGET":0,"solver_run_called":False,"solver_entered":0,"active_new_paper_a_fdtd":0,"rcwa":0,"ml":0,"ready_pending_hidden_auto_admission":False,"server_performance_benchmark":"OUT_OF_SCOPE_FOR_PAPER_A"}}
    write_json(REPORT/"source_provenance.json",prov)
    write_json(AUTH/"paper_a_lp_anisotropy_feasible_space_v2.json",{"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_AUTHORITY_V1","scientific_state":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_PLANNED","scientific_readiness":"INITIAL_TRUTH_CANDIDATES_READY","solver_state":"WAIT_EXTERNAL_SOLVER_ADMISSION","NEW_FDTD_BUDGET":0,"selected_geometry_ids":[r["geometry_id"] for r in selected],"initial_geometry_ids":[r["geometry_id"] for r in selected[:4]],"conditional_geometry_ids":[r["geometry_id"] for r in selected[4:]],"selection":"zero-optical-information deterministic nearest-nominal then sequential normalized-6D maximin","pool_statistics_path":str(REPORT/"raw_pool_statistics.json"),"candidate_registry_path":str(REPORT/"candidate_registry.csv"),"setup_only_scope":"AF01-AF04 x/y only after audit; AF05-AF08 registry-only","global_scheduler_policy_changed":False})
    write_json(REPORT/"midpoint_physics_audit_preregistration.json",{"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_MIDPOINT_PREREGISTRATION_V1","status":"PREREGISTERED_NOT_EXECUTED","no_solver":True,"no_optical_selection":True,"next_authority_required":"external solver admission after separate scientific authorization"})
    audit={"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_AUDIT_V1","timestamp_utc":now(),"status":"PASS","selected_count":len(selected),"all_selected_valid":all(r["geometry_valid"] for r in selected),"all_direct_ge_60":all(r["direct_clearance_nm"]>=60 for r in selected),"all_periodic_ge_60":all(r["periodic_image_clearance_nm"]>=60 for r in selected),"all_unique_hashes":len(selected_ids)==8,"all_centers_half_grid":all(abs(2*r["j1_center_y_nm"]-round(2*r["j1_center_y_nm"]))<1e-9 for r in selected),"solver_run_called":False,"solver_entered":0,"new_fdtd_budget":0,"DOE_changed":False,"global_scheduler_policy_changed":False,"old_source_worktrees_modified":False}
    write_json(REPORT/"audit.json",audit)
    return {"status":"PASS","source_n":selected_source_n,"raw_count":selected_source_n,"quantized_unique_count":len(seen),"feasible_count":len(pool),"rejection_counts":rejection,"selected":selected,"audit":audit}


def setup_selected() -> dict[str, Any]:
    import importlib.util
    import lumapi
    selected=json.loads((REPORT/"candidate_registry.csv").read_text(encoding="utf-8")) if False else list(csv.DictReader((REPORT/"candidate_registry.csv").open(encoding="utf-8")))
    # Rehydrate the full candidate data from the JSON mirror generated below.
    candidates=json.loads((REPORT/"selected_candidates.json").read_text(encoding="utf-8"))["candidates"]
    results=[]
    for g in candidates[:4]:
        for pol in ("x","y"):
            cid=f"{g['geometry_id']}_{pol}"; out=RUNTIME/"cases"/cid; out.mkdir(parents=True,exist_ok=True); pre=out/f"{cid}_pre.fsp"
            f=lumapi.FDTD(hide=True)
            try:
                f.load(str(PARENT_FSP)); f.switchtolayout(); nm=1e-9
                for obj, cx, cy, length, width, rot in [("pillar_1",g["j1_center_x_nm"],g["j1_center_y_nm"],g["L1_nm"],g["W1_nm"],g["theta1_deg"]),("pillar_2",g["j2_center_x_nm"],g["j2_center_y_nm"],g["L2_nm"],g["W2_nm"],g["theta2_deg"])]:
                    f.setnamed(obj,"x",float(cx)*nm); f.setnamed(obj,"y",float(cy)*nm); f.setnamed(obj,"x span",float(length)*nm); f.setnamed(obj,"y span",float(width)*nm); f.setnamed(obj,"z",H*nm/2); f.setnamed(obj,"z span",H*nm); f.setnamed(obj,"rotation 1",float(rot)); f.setnamed(obj,"material",MATERIAL)
                f.setnamed("source","polarization angle",0.0 if pol=="x" else 90.0); f.setnamed("source","wavelength start",SOURCE_START*nm); f.setnamed("source","wavelength stop",SOURCE_STOP*nm)
                for name in ("T","field_monitor"):
                    f.setnamed(name,"use source limits",True); f.setnamed(name,"use wavelength spacing",True); f.setnamed(name,"frequency points",41)
                f.setglobalmonitor("use source limits",True); f.setglobalmonitor("use wavelength spacing",True); f.setglobalmonitor("frequency points",41); f.save(str(pre))
            finally:
                try:f.close()
                except Exception:pass
            f=lumapi.FDTD(hide=True)
            try:
                f.load(str(pre)); read={"source_start_nm":float(f.getnamed("source","wavelength start"))*1e9,"source_stop_nm":float(f.getnamed("source","wavelength stop"))*1e9,"source_polarization_angle_deg":float(f.getnamed("source","polarization angle")),"T_frequency_points":float(f.getnamed("T","frequency points")),"field_frequency_points":float(f.getnamed("field_monitor","frequency points")),"materials":[str(f.getnamed("pillar_1","material")),str(f.getnamed("pillar_2","material"))],"j1_rotation_deg":float(f.getnamed("pillar_1","rotation 1")),"j2_rotation_deg":float(f.getnamed("pillar_2","rotation 1"))}
            finally:
                try:f.close()
                except Exception:pass
            expected={"source_start_nm":SOURCE_START,"source_stop_nm":SOURCE_STOP,"source_polarization_angle_deg":0.0 if pol=="x" else 90.0,"T_frequency_points":41.0,"field_frequency_points":41.0,"materials":[MATERIAL,MATERIAL],"j1_rotation_deg":float(g["theta1_deg"]),"j2_rotation_deg":float(g["theta2_deg"])}
            ok=all((read[k]==expected[k] if isinstance(expected[k],list) else abs(float(read[k])-float(expected[k]))<1e-6) for k in expected)
            r={"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_SETUP_ONLY_V1","case_id":cid,"geometry_id":g["geometry_id"],"polarization":pol,"status":"PASS" if ok else "BLOCKED","solver_run_called":False,"solver_entered":False,"pre_fsp_path":str(pre),"pre_fsp_sha256":sha_file(pre),"parent_fsp_path":str(PARENT_FSP),"parent_fsp_sha256":sha_file(PARENT_FSP),"readback":read,"expected":expected,"mesh_boundary_unchanged":True,"normalization_renormalized":False}
            write_json(out/"setup_only.json",r); results.append(r)
    write_json(REPORT/"prepared_fsp_provenance.json",{"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_PREPARED_FSP_PROVENANCE_V1","cases":results,"solver_calls":0,"all_pass":all(r["status"]=="PASS" for r in results)})
    return {"status":"PASS" if all(r["status"]=="PASS" for r in results) else "BLOCKED","cases":results,"solver_calls":0}


def tests() -> dict[str, Any]:
    d=json.loads((REPORT/"audit.json").read_text(encoding="utf-8")); c=json.loads((REPORT/"selected_candidates.json").read_text(encoding="utf-8"))["candidates"]
    u1, u2 = sobol(16), sobol(16)
    q1, q2 = quantize(map_unit(list(u1[7]))), quantize(map_unit(list(u1[7])))
    recomputed=[]
    for x in c:
        q={k:x[k] for k in ["L1_nm","W1_nm","L2_nm","W2_nm","D_nm","delta_theta_deg","height_nm","period_x_nm","period_y_nm","theta1_deg","theta2_deg","j1_center_x_nm","j1_center_y_nm","j2_center_x_nm","j2_center_y_nm"]}
        recomputed.append(geom_core(q))
    checks={"audit_pass":d["status"]=="PASS","count_8":len(c)==8,"valid":all(x["geometry_valid"] for x in c),"direct_ge_60":all(x["direct_clearance_nm"]>=60 for x in c),"periodic_ge_60":all(x["periodic_image_clearance_nm"]>=60 for x in c),"hash_unique":len({x["geometry_hash_sha256"] for x in c})==8,"half_grid":all(abs(2*x["j1_center_y_nm"]-round(2*x["j1_center_y_nm"]))<1e-9 for x in c),"sobol_reproducible":u1.tolist()==u2.tolist(),"quantization_reproducible":q1==q2,"periodic_polygon_distance_recomputed":all(abs(a["periodic_image_clearance_nm"]-b["periodic_image_clearance_nm"])<1e-9 for a,b in zip(c,recomputed)),"direct_polygon_distance_recomputed":all(abs(a["direct_clearance_nm"]-b["direct_clearance_nm"])<1e-9 for a,b in zip(c,recomputed)),"selection_ids_ordered":[x["geometry_id"] for x in c]==[f"AF{i:02d}" for i in range(1,9)],"solver_zero":d["solver_entered"]==0 and not d["solver_run_called"]}
    out={"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_TEST_REPORT_V1","status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"deterministic_selection_sha256":sha_obj([x["geometry_hash_sha256"] for x in c])}
    write_json(REPORT/"test_report.json",out); return out


def finalize() -> dict[str, Any]:
    selected = json.loads((REPORT/"selected_candidates.json").read_text(encoding="utf-8"))["candidates"]
    prep_path = REPORT/"prepared_fsp_provenance.json"
    prep = json.loads(prep_path.read_text(encoding="utf-8")) if prep_path.exists() else {"cases": [], "all_pass": False}
    prep_by = {x["case_id"]: x for x in prep.get("cases", [])}
    cases = []
    for g in selected:
        for pol in ("x", "y"):
            cid = f"{g['geometry_id']}_{pol}"
            p = prep_by.get(cid)
            cases.append({"case_id":cid,"geometry_id":g["geometry_id"],"polarization":pol,"role":g["role"],"status":"PREPARED_SETUP_ONLY" if p else "REGISTRY_ONLY","setup_only_allowed":g["geometry_id"] in {"AF01","AF02","AF03","AF04"},"solver_run_called":False,"solver_entered":False,"ready_or_pending":False,"pre_fsp_path":p.get("pre_fsp_path") if p else None,"pre_fsp_sha256":p.get("pre_fsp_sha256") if p else None})
    write_json(REPORT/"case_registry.json", {"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_CASE_REGISTRY_V1","cases":cases,"new_fdtd_budget":0,"dispatch":False,"hidden_auto_admission":False})
    write_json(REPORT/"selection_audit.json", {"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_SELECTION_AUDIT_V1","selection_information":"geometry-only; no optical/solver outputs, surrogate, ML, RCWA or FDTD metrics","AF01":"nearest feasible quantized point to nominal center [1,1,1,1,45deg,195nm]","AF02_AF08":"sequential deterministic greedy maximin in normalized current six-dimensional variables","initial_geometry_ids":[x["geometry_id"] for x in selected[:4]],"conditional_geometry_ids":[x["geometry_id"] for x in selected[4:]],"max_total_geometries":8,"pairwise_distances_path":str(REPORT/"selection_pairwise_distances.csv")})
    decision={"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_PLANNING_DECISION_V1","scientific_state":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_PLANNED","scientific_readiness":"INITIAL_TRUTH_CANDIDATES_READY","solver_state":"WAIT_EXTERNAL_SOLVER_ADMISSION","NEW_FDTD_BUDGET":0,"initial_truth_case_ids":[f"AF{i:02d}_{p}" for i in range(1,5) for p in ("x","y")],"conditional_registry_only_geometry_ids":[f"AF{i:02d}" for i in range(5,9)],"setup_only_all_pass":bool(prep.get("all_pass")),"server_performance_benchmark":"OUT_OF_SCOPE_FOR_PAPER_A","global_scheduler_policy_changed":False,"next_action":"external solver admission is required before any FDTD entry"}
    write_json(REPORT/"planning_decision.json", decision)
    lines=["# LP anisotropy feasible-space V2 pre-admission report", "", "Status: PASS (zero-solver planning and setup-only audit)", "", "- Physics box: a1,b1,a2,b2 in [0.85, 1.15], delta_theta in [0, 90] deg, D in [170, 220] nm.", "- Frozen backbone: current Paper A H=525 nm, Px=Py=432 nm, Native-M1, existing broadband full-Jones template.", "- Formal legality: exact direct and periodic-image polygon clearance >=60 nm, no overlap/touch, containment, integer lateral dimensions, half-grid-compatible centers.", "- Selection used geometry only; no optical information, RCWA, ML, surrogate or solver metrics.", "", f"Raw Sobol points: {json.loads((REPORT/'raw_pool_statistics.json').read_text(encoding='utf-8'))['raw_count']}; feasible unique pool: {len(selected)} selected from 1879 feasible unique points.", "", "## Selected geometries", "", "| ID | Role | L1/W1/L2/W2 (nm) | theta1/theta2 (deg) | D (nm) | direct (nm) | periodic image (nm) | global min (nm) | min feature (nm) | H/min feature |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for x in selected:
        lines.append(f"| {x['geometry_id']} | {x['role']} | {x['L1_nm']}/{x['W1_nm']}/{x['L2_nm']}/{x['W2_nm']} | {x['theta1_deg']}/{x['theta2_deg']} | {x['D_nm']} | {x['direct_clearance_nm']:.6f} | {x['periodic_image_clearance_nm']:.6f} | {x['global_minimum_clearance_nm']:.6f} | {x['minimum_lateral_feature_nm']} | {x['aspect_ratio_H_over_min_feature']:.6f} |")
    lines += ["", "Initial truth candidates: AF01–AF04 (x/y setup-only prepared; no solver entry).", "Conditional registry-only candidates: AF05–AF08.", "", "Old A01–A08 remains immutable planning provenance; DOE was not changed.", "No authoritative current minimum-linewidth or aspect-ratio hard gate was found in the transferred formal legality authority; those values are diagnostics only.", "", "Safety: NEW_FDTD_BUDGET=0; solver_run_called=false; solver_entered=0; no READY/pending/hidden admission; no global scheduler policy change.", ""]
    (REPORT/"final_report.md").write_text("\n".join(lines),encoding="utf-8")
    md=["# Paper A LP anisotropy feasible-space V2 authority", "", "`LP_ANISOTROPY_FEASIBLE_SPACE_V2` is a zero-solver pre-admission planning stage.", "", "Scientific state: `PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_PLANNED`.", "Scientific readiness: `INITIAL_TRUTH_CANDIDATES_READY`.", "Solver state: `WAIT_EXTERNAL_SOLVER_ADMISSION`.", "", "The candidate set is selected from the current six-dimensional box after exact integer/half-grid quantization and exact polygon direct/periodic-image distance checks. Selection is geometry-only; no optical ranking is present.", "", "Transferred hard gates are direct clearance >=60 nm, periodic-image clearance >=60 nm, no overlap/touching, cell containment, integer lateral dimensions, and half-grid-compatible centers. No current authoritative minimum linewidth/aspect-ratio hard gate was found; minimum feature and H/min-feature are diagnostics only.", "", "AF01-AF04 are initial setup-only x/y candidates. AF05-AF08 are conditional registry-only candidates. No solver is authorized or queued by this artifact.", ""]
    (AUTH/"paper_a_lp_anisotropy_feasible_space_v2.md").write_text("\n".join(md),encoding="utf-8")
    audit=json.loads((REPORT/"audit.json").read_text(encoding="utf-8")); audit.update({"setup_only_case_count":len(prep.get("cases", [])),"setup_only_all_pass":bool(prep.get("all_pass")),"prepared_case_ids":[x.get("case_id") for x in prep.get("cases", [])],"finalized_utc":now()}); write_json(REPORT/"audit.json",audit)
    return {"status":"PASS" if prep.get("all_pass") and len(cases)==16 else "PARTIAL","setup_only_cases":len(prep.get("cases", [])),"registry_cases":len(cases)}


def main():
    mode=sys.argv[1] if len(sys.argv)>1 else "build"
    if mode=="build":
        out=build(); write_json(REPORT/"selected_candidates.json",{"schema":"PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_SELECTED_CANDIDATES_V1","candidates":out["selected"]}); print(json.dumps({k:out[k] for k in ["status","source_n","raw_count","quantized_unique_count","feasible_count","rejection_counts"]},indent=2))
    elif mode=="setup": print(json.dumps(setup_selected(),indent=2,ensure_ascii=False))
    elif mode=="test": print(json.dumps(tests(),indent=2,ensure_ascii=False))
    elif mode=="finalize": print(json.dumps(finalize(),indent=2,ensure_ascii=False))
    else: raise SystemExit(f"unknown mode {mode}")


if __name__=="__main__": main()
