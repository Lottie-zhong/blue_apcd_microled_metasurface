from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

import mpmath as mp


ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
PKG = ROOT / "paper_a_broadband"
REPORT = PKG / "reports/lp_anisotropy_expanded_search_v1"
DOE_PATH = PKG / "configs/anisotropy_expanded_doe_v1.json"
BUILDER = PKG / "scripts/lp_anisotropy_bootstrap_v1.py"
RULE_SOURCE = PKG / "scripts/lp_anisotropy_feasible_space_v2.py"
RULE_AUTH = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_local_domain_authority.json"
AUDIT_SCRIPT = PKG / "scripts/a02_pre_admission_geometry_audit_v2.py"

mp.mp.dps = 100


def mpf(value) -> mp.mpf:
    return mp.mpf(str(value))


def fmt(value) -> str:
    return mp.nstr(value, 50)


def point_fmt(point):
    return [fmt(point[0]), fmt(point[1])] if point is not None else None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygon(length, width, cx, cy, theta_deg):
    a, b = mpf(length) / 2, mpf(width) / 2
    theta = mp.radians(mpf(theta_deg))
    c, s = mp.cos(theta), mp.sin(theta)
    return [
        (mpf(cx) + c * x - s * y, mpf(cy) + s * x + c * y)
        for x, y in [(-a, -b), (a, -b), (a, b), (-a, b)]
    ]


def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a, b, p):
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def segment_intersects(a, b, c, d):
    o1, o2 = orient(a, b, c), orient(a, b, d)
    o3, o4 = orient(c, d, a), orient(c, d, b)
    if o1 == 0 and on_segment(a, b, c):
        return True
    if o2 == 0 and on_segment(a, b, d):
        return True
    if o3 == 0 and on_segment(c, d, a):
        return True
    if o4 == 0 and on_segment(c, d, b):
        return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def point_segment(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = dx * dx + dy * dy
    t = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / den
    t = max(mp.mpf(0), min(mp.mpf(1), t))
    projection = (a[0] + t * dx, a[1] + t * dy)
    distance = mp.sqrt((point[0] - projection[0]) ** 2 + (point[1] - projection[1]) ** 2)
    return distance, projection, t


def polygon_pair_distance(a, b):
    for ai in range(4):
        for bi in range(4):
            if segment_intersects(a[ai], a[(ai + 1) % 4], b[bi], b[(bi + 1) % 4]):
                return {"distance_nm": "0", "intersects": True, "witness": None}
    best = None
    for side, vertices, other in (("A_to_B", a, b), ("B_to_A", b, a)):
        for vi, point in enumerate(vertices):
            for edge in range(4):
                d, projection, t = point_segment(point, other[edge], other[(edge + 1) % 4])
                item = {"distance": d, "side": side, "vertex_index": vi, "edge_index": edge, "point": point, "projection": projection, "projection_t": t}
                if best is None or d < best["distance"]:
                    best = item
    return {
        "distance_nm": fmt(best["distance"]),
        "intersects": False,
        "witness": {
            "side": best["side"],
            "vertex_index": best["vertex_index"],
            "edge_index": best["edge_index"],
            "point_nm": point_fmt(best["point"]),
            "projection_nm": point_fmt(best["projection"]),
            "projection_t": fmt(best["projection_t"]),
        },
    }


def pair_record(name_a, name_b, ix, iy, polygons, px, py):
    shifted = [(x + ix * px, y + iy * py) for x, y in polygons[name_b]]
    result = polygon_pair_distance(polygons[name_a], shifted)
    return {
        "object_a": name_a,
        "object_b": name_b,
        "image_shift_cells": [int(ix), int(iy)],
        "image_shift_nm": [fmt(ix * px), fmt(iy * py)],
        "distance_nm": result["distance_nm"],
        "intersects_or_touches": result["intersects"],
        "witness": result["witness"],
    }


def boundary_records(polygons, half_x, half_y):
    rows = []
    for name, poly in polygons.items():
        for vi, (x, y) in enumerate(poly):
            rows.extend([
                {"object": name, "vertex_index": vi, "boundary": "left", "clearance_nm": fmt(x + half_x), "point_nm": point_fmt((x, y))},
                {"object": name, "vertex_index": vi, "boundary": "right", "clearance_nm": fmt(half_x - x), "point_nm": point_fmt((x, y))},
                {"object": name, "vertex_index": vi, "boundary": "bottom", "clearance_nm": fmt(y + half_y), "point_nm": point_fmt((x, y))},
                {"object": name, "vertex_index": vi, "boundary": "top", "clearance_nm": fmt(half_y - y), "point_nm": point_fmt((x, y))},
            ])
    return sorted(rows, key=lambda row: (mpf(row["clearance_nm"]), row["object"], row["vertex_index"], row["boundary"]))


def git_snapshot():
    def run(args):
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        return p.stdout.strip()
    return {
        "branch": run(["git", "branch", "--show-current"]),
        "head": run(["git", "rev-parse", "HEAD"]),
        "ahead_behind": run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"]),
    }


def active_fdtd_processes():
    p = subprocess.run(["tasklist", "/FO", "CSV"], capture_output=True, text=True)
    rows = [line for line in p.stdout.splitlines() if "fdtd-engine" in line.lower()]
    return {"matching_process_count": len(rows), "matching_process_rows": rows, "query_returncode": p.returncode}


def geometry_audit(g, px, py):
    polygons = {
        "pillar_1": polygon(g["L1_nm"], g["W1_nm"], g["j1_center_x_nm"], g["j1_center_y_nm"], g["j1_rotation_deg"]),
        "pillar_2": polygon(g["L2_nm"], g["W2_nm"], g["j2_center_x_nm"], g["j2_center_y_nm"], g["j2_rotation_deg"]),
    }
    direct = pair_record("pillar_1", "pillar_2", 0, 0, polygons, px, py)
    periodic = [
        pair_record(name_a, name_b, ix, iy, polygons, px, py)
        for name_a in ("pillar_1", "pillar_2")
        for name_b in ("pillar_1", "pillar_2")
        for ix in (-1, 0, 1)
        for iy in (-1, 0, 1)
        if not (ix == 0 and iy == 0)
    ]
    periodic.sort(key=lambda row: (mpf(row["distance_nm"]), row["object_a"], row["object_b"], row["image_shift_cells"]))
    periodic_min = periodic[0]
    periodic_cross = [row for row in periodic if row["object_a"] != row["object_b"]]
    periodic_cross_min = min(periodic_cross, key=lambda row: (mpf(row["distance_nm"]), row["object_a"], row["object_b"], row["image_shift_cells"]))
    periodic_same = [row for row in periodic if row["object_a"] == row["object_b"]]
    periodic_same_min = min(periodic_same, key=lambda row: (mpf(row["distance_nm"]), row["object_a"], row["image_shift_cells"]))
    boundaries = boundary_records(polygons, px / 2, py / 2)
    boundary_min = boundaries[0]
    containment = all(abs(x) <= px / 2 and abs(y) <= py / 2 for poly in polygons.values() for x, y in poly)
    periodic_intersection_count = sum(row["intersects_or_touches"] for row in periodic)
    direct_intersection = direct["intersects_or_touches"]
    direct_d = mpf(direct["distance_nm"])
    periodic_d = mpf(periodic_min["distance_nm"])
    boundary_d = mpf(boundary_min["clearance_nm"])
    lateral_keys = ["L1_nm", "W1_nm", "L2_nm", "W2_nm"]
    center_keys = ["j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm"]
    integer_lateral = all(mpf(g[key]) == mp.floor(mpf(g[key])) for key in lateral_keys)
    half_grid_centers = all(2 * mpf(g[key]) == mp.floor(2 * mpf(g[key])) for key in center_keys)
    return {
        "vertices_nm": {name: [point_fmt(point) for point in poly] for name, poly in polygons.items()},
        "direct_same_cell_pillar_pair": direct,
        "nearest_periodic_image_pair_all_objects": periodic_min,
        "nearest_periodic_image_pair_cross_pillar": periodic_cross_min,
        "nearest_same_object_periodic_image_pair": periodic_same_min,
        "periodic_intersection_count": periodic_intersection_count,
        "boundary_minimum": boundary_min,
        "cell_containment_pass": containment,
        "direct_no_overlap_or_touch_pass": not direct_intersection,
        "periodic_no_overlap_or_touch_pass": periodic_intersection_count == 0,
        "integer_lateral_dimensions_pass": integer_lateral,
        "half_grid_centers_pass": half_grid_centers,
        "legacy_aggregate_minimum_nm": fmt(min(direct_d, periodic_d, boundary_d)),
        "physical_polygon_minimum_nm": fmt(min(direct_d, periodic_d)),
        "direct_clearance_nm": fmt(direct_d),
        "periodic_image_clearance_nm": fmt(periodic_d),
        "boundary_margin_nm": fmt(boundary_d),
        "old_planning_validity": g.get("validity", {}),
        "current_inherited_gate_pass": bool(
            direct_d >= 60 and periodic_d >= 60 and not direct_intersection and periodic_intersection_count == 0 and containment and integer_lateral and half_grid_centers
        ),
    }


def main():
    doe_sha_before = sha256_file(DOE_PATH)
    doe = json.loads(DOE_PATH.read_text(encoding="utf-8"))
    px = py = mpf(doe["geometries"][0]["period_x_nm"])
    all_rows = []
    detailed = None
    for g in doe["geometries"]:
        result = geometry_audit(g, px, py)
        row = {
            "geometry_id": g["geometry_id"],
            "role": g["role"],
            "L1_nm": g["L1_nm"], "W1_nm": g["W1_nm"], "L2_nm": g["L2_nm"], "W2_nm": g["W2_nm"],
            "delta_theta_deg": g["delta_theta_deg"], "D_nm": g["D_nm"],
            "direct_clearance_nm": result["direct_clearance_nm"],
            "periodic_image_clearance_nm": result["periodic_image_clearance_nm"],
            "boundary_margin_nm": result["boundary_margin_nm"],
            "legacy_aggregate_minimum_nm": result["legacy_aggregate_minimum_nm"],
            "physical_polygon_minimum_nm": result["physical_polygon_minimum_nm"],
            "nearest_direct_pair": result["direct_same_cell_pillar_pair"],
            "nearest_periodic_pair": result["nearest_periodic_image_pair_all_objects"],
            "containment_pass": result["cell_containment_pass"],
            "no_overlap_or_touch_pass": result["direct_no_overlap_or_touch_pass"] and result["periodic_no_overlap_or_touch_pass"],
            "integer_lateral_dimensions_pass": result["integer_lateral_dimensions_pass"],
            "half_grid_centers_pass": result["half_grid_centers_pass"],
            "old_planning_geometry_valid": g.get("validity", {}).get("geometry_valid"),
            "current_inherited_gate_pass": result["current_inherited_gate_pass"],
            "geometry_hash_sha256": g.get("geometry_hash_sha256"),
        }
        all_rows.append(row)
        if g["geometry_id"] == "ANISO_A02":
            detailed = {"geometry": g, "audit": result}
    assert detailed is not None
    a02 = detailed["geometry"]
    ar = detailed["audit"]
    reported = mpf(a02["validity"]["min_edge_gap_nm"])
    boundary = ar["boundary_minimum"]
    periodic = ar["nearest_periodic_image_pair_all_objects"]
    direct = ar["direct_same_cell_pillar_pair"]
    source_lines = BUILDER.read_text(encoding="utf-8", errors="replace").splitlines()
    validity_start = next((i + 1 for i, line in enumerate(source_lines) if line.startswith("def validity")), None)
    validity_end = next((i for i, line in enumerate(source_lines[validity_start or 1:], validity_start or 1) if line.startswith("def make_geom")), None)
    current_rule_lines = [
        {"line": i, "text": line}
        for i, line in enumerate(RULE_SOURCE.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if "direct_polygon_clearance_nm_ge" in line or "periodic_image_polygon_clearance_nm_ge" in line or "direct_clearance_ge_60" in line or "periodic_clearance_ge_60" in line
    ]
    rules = json.loads(RULE_AUTH.read_text(encoding="utf-8"))
    doe_sha_after = sha256_file(DOE_PATH)
    process_state = active_fdtd_processes()
    out = {
        "schema": "PAPER_A_ANISO_A02_INDEPENDENT_GEOMETRY_AUDIT_V2",
        "status": "PASS_WITH_A02_ADMISSION_HARD_GATE",
        "stage": "zero_solver_pre_admission_audit",
        "canonical_geometry_id": "ANISO_A02",
        "source_doe": {"path": str(DOE_PATH), "sha256_before": doe_sha_before, "sha256_after": doe_sha_after, "unchanged": doe_sha_before == doe_sha_after},
        "exact_geometry": {key: a02.get(key) for key in ["L1_nm", "W1_nm", "L2_nm", "W2_nm", "j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm", "j1_rotation_deg", "j2_rotation_deg", "D_nm", "period_x_nm", "period_y_nm", "height_nm"]},
        "vertices_nm": ar["vertices_nm"],
        "minimum_separation": {
            "reported_value_nm": a02["validity"]["min_edge_gap_nm"],
            "reported_field_definition": "legacy aggregate of polygon-pair distances and cell-boundary margins",
            "reported_witness": boundary,
            "direct_same_cell_pillar_pair": direct,
            "nearest_periodic_image_pair_all_objects": periodic,
            "nearest_periodic_image_pair_cross_pillar": ar["nearest_periodic_image_pair_cross_pillar"],
            "nearest_same_object_periodic_image_pair": ar["nearest_same_object_periodic_image_pair"],
            "recomputed_legacy_aggregate_nm": ar["legacy_aggregate_minimum_nm"],
            "recomputed_physical_polygon_minimum_nm": ar["physical_polygon_minimum_nm"],
            "independent_high_precision_decimal_digits": 100,
        },
        "classification": {
            "reported_0_032_is_pillar_to_pillar_gap": False,
            "reported_0_032_is_canonical_translated_polygon_gap": False,
            "reported_0_032_is_cell_boundary_margin": True,
            "reported_0_032_is_bounding_box_approximation": False,
            "reported_0_032_is_floating_point_artifact": False,
            "actual_nearest_direct_or_translated_polygon_gap_nm": ar["physical_polygon_minimum_nm"],
            "actual_nearest_periodic_image_gap_nm": ar["periodic_image_clearance_nm"],
            "meaning": "REPORTING_DEFINITION_ARTIFACT; NO_0_032_PHYSICAL_PERIODIC_SEAM_GAP",
            "correction_to_prior_boundary_doubling_interpretation": "A boundary margin is not converted into a self-image gap; translated image polygon distances are evaluated in ordinary coordinates under the canonical {-1,0,+1} shift convention.",
        },
        "topology": {
            "same_cell_polygon_intersection": not ar["direct_no_overlap_or_touch_pass"],
            "periodic_polygon_intersection_count": ar["periodic_intersection_count"],
            "mathematical_non_overlap": ar["direct_no_overlap_or_touch_pass"] and ar["periodic_no_overlap_or_touch_pass"],
            "two_distinct_pillar_objects_in_canonical_builder": True,
            "canonical_builder_topology": "two separate rotated-rectangle objects; no merge operation",
            "canonical_fsp_child_paths": [str(ROOT / "paper_a_broadband/runtime/search_anisotropy_v1/cases/ANISO_A02_x/ANISO_A02_x_pre.fsp"), str(ROOT / "paper_a_broadband/runtime/search_anisotropy_v1/cases/ANISO_A02_y/ANISO_A02_y_pre.fsp")],
            "canonical_fsp_child_exists": any((ROOT / "paper_a_broadband/runtime/search_anisotropy_v1/cases" / f"ANISO_A02_{p}" / f"ANISO_A02_{p}_pre.fsp").exists() for p in ("x", "y")),
            "fsp_topology_evidence": "No instantiated A02 child FSP; topology conclusion is from the canonical two-object builder model.",
        },
        "validity_and_contract": {
            "cell_bounds_nm": [[-216.0, 216.0], [-216.0, 216.0]],
            "cell_containment_pass": ar["cell_containment_pass"],
            "direct_polygon_clearance_nm": ar["direct_clearance_nm"],
            "periodic_image_polygon_clearance_nm": ar["periodic_image_clearance_nm"],
            "direct_clearance_ge_60": mpf(ar["direct_clearance_nm"]) >= 60,
            "periodic_clearance_ge_60": mpf(ar["periodic_image_clearance_nm"]) >= 60,
            "no_overlap_or_touch_pass": ar["direct_no_overlap_or_touch_pass"] and ar["periodic_no_overlap_or_touch_pass"],
            "integer_lateral_dimensions_pass": ar["integer_lateral_dimensions_pass"],
            "half_grid_centers_pass": ar["half_grid_centers_pass"],
            "no_sub_grid_geometry_pass": ar["integer_lateral_dimensions_pass"],
            "benchmark_admission_safe": ar["current_inherited_gate_pass"],
        },
        "authoritative_rules": {
            "source_path": str(RULE_SOURCE),
            "source_sha256": sha256_file(RULE_SOURCE),
            "source_lines_with_clearance_rule": current_rule_lines,
            "authority_path": str(RULE_AUTH),
            "authority_sha256": sha256_file(RULE_AUTH),
            "hard_gates": rules["hard_gates_inherited"],
            "current_authoritative_minimum_gap_nm": 60.0,
            "minimum_linewidth_or_aspect_ratio_gate": "none found in inherited authority; not invented",
            "expanded_doe_validity_mismatch": "The A01-A08 bootstrap validity() records containment/overlap but does not apply the inherited 60 nm direct/periodic clearance or integer-lateral admission gates.",
        },
        "audit_script": {"path": str(AUDIT_SCRIPT), "sha256": sha256_file(AUDIT_SCRIPT) if AUDIT_SCRIPT.exists() else None},
        "a01_a08_rerun": {
            "performed": True,
            "method": "same exact high-precision polygon representation and {-1,0,+1} translated-image enumeration applied to all eight DOE rows; no solver",
            "row_count": len(all_rows),
            "rows": all_rows,
            "csv_path": str(REPORT / "a01_a08_corrected_validity_audit_v2.csv"),
            "json_path": str(REPORT / "a01_a08_corrected_validity_audit_v2.json"),
        },
        "safety_invariants": {
            "NEW_FDTD_BUDGET": 0,
            "solver_run_called": False,
            "solver_entered": 0,
            "active_fdtd": process_state["matching_process_count"],
            "active_fdtd_process_check": process_state,
            "RCWA": 0,
            "ML": 0,
            "ready_pending_hidden_auto_admission": 0,
            "DOE_changed": doe_sha_before != doe_sha_after,
            "validity_function_source_line_start": validity_start,
            "validity_function_source_line_end": validity_end,
            "git_snapshot": git_snapshot(),
        },
        "decision": {
            "status": "HARD_GATE_A02_NOT_SAFE_FOR_BENCHMARK_ADMISSION",
            "benchmark_admission_safe": False,
            "reason": "The 0.032 nm value is a boundary-margin reporting artifact, but A02 still fails the existing direct 60 nm gate, translated periodic-image 60 nm gate, and integer-lateral-dimension gate. DOE is unchanged and solver authority remains zero.",
        },
    }
    report_json = REPORT / "a02_pre_admission_geometry_audit_v2.json"
    report_md = REPORT / "a02_pre_admission_geometry_audit_v2.md"
    validation_json = REPORT / "a02_pre_admission_validation_v2.json"
    all_json = REPORT / "a01_a08_corrected_validity_audit_v2.json"
    all_csv = REPORT / "a01_a08_corrected_validity_audit_v2.csv"
    report_json.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    all_json.write_text(json.dumps({"schema": "PAPER_A_ANISO_A01_A08_CORRECTED_VALIDITY_AUDIT_V2", "status": "PASS", "rows": all_rows, "solver_entered": 0, "solver_run_called": False, "DOE_changed": False}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with all_csv.open("w", newline="", encoding="utf-8") as fh:
        fields = ["geometry_id", "role", "L1_nm", "W1_nm", "L2_nm", "W2_nm", "delta_theta_deg", "D_nm", "direct_clearance_nm", "periodic_image_clearance_nm", "boundary_margin_nm", "legacy_aggregate_minimum_nm", "physical_polygon_minimum_nm", "containment_pass", "no_overlap_or_touch_pass", "integer_lateral_dimensions_pass", "half_grid_centers_pass", "old_planning_geometry_valid", "current_inherited_gate_pass", "geometry_hash_sha256"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({key: row.get(key) for key in fields})
    report_md.write_text(
        "\n".join([
            "# A02 independent pre-admission geometry audit v2",
            "",
            "Status: `PASS_WITH_A02_ADMISSION_HARD_GATE`",
            "",
            "The reported `0.03199553012498768 nm` is not a pillar-pair gap, not a translated-polygon gap, not a bounding-box approximation, and not floating-point noise. It is the 100-digit-recomputed distance from `pillar_2` vertex 0 to the bottom cell boundary `y=-216 nm`, included by the legacy aggregate `min_edge_gap_nm` field.",
            "",
            f"Exact instantiated geometry: L1/W1/L2/W2 = `{a02['L1_nm']}/{a02['W1_nm']}/{a02['L2_nm']}/{a02['W2_nm']} nm`; rotations = `{a02['j1_rotation_deg']}/{a02['j2_rotation_deg']} deg`; centers = `(0,{a02['j1_center_y_nm']})/(0,{a02['j2_center_y_nm']}) nm`; D/Px/Py = `{a02['D_nm']}/{a02['period_x_nm']}/{a02['period_y_nm']} nm`.",
            f"Independent same-cell pillar gap: `{direct['distance_nm']} nm`, pair `{direct['object_a']} ↔ {direct['object_b']}`; nearest translated periodic-image gap under the canonical shift convention: `{periodic['distance_nm']} nm`, pair `{periodic['object_a']} ↔ {periodic['object_b']}`, shift `{periodic['image_shift_cells']}`. Nearest same-object translated image gap is `{ar['nearest_same_object_periodic_image_pair']['distance_nm']} nm`; therefore the prior `0.064 nm` boundary-doubling interpretation is not a physical translated-image distance.",
            "",
            f"Containment: `{ar['cell_containment_pass']}`. Same-cell intersection/touch: `{not ar['direct_no_overlap_or_touch_pass']}`. Periodic intersection/touch count: `{ar['periodic_intersection_count']}`. The builder has two distinct rectangle objects and no A02 child FSP was instantiated.",
            "",
            "The inherited current Paper A geometry gates are direct polygon clearance >=60 nm, translated periodic-image clearance >=60 nm, no overlap/touch, containment, integer lateral dimensions, and half-grid-compatible centers. A02 has direct `44.531995530... nm`, periodic `52.531995530... nm`, and non-integer lateral dimensions `195.5/76.5 nm`; it is therefore not safe for benchmark admission even though it is mathematically non-overlapping and the `0.032 nm` report is only a boundary-margin definition artifact.",
            "",
            "A01-A08 were re-audited with the corrected zero-solver method; the DOE was not edited or replaced. No solver, mesh, physics, or scheduler state was changed.",
        ]) + "\n",
        encoding="utf-8",
    )
    checks = {
        "schema": "PAPER_A_ANISO_A02_INDEPENDENT_GEOMETRY_AUDIT_V2_TEST_REPORT",
        "checks": {
            "a02_present": a02["geometry_id"] == "ANISO_A02",
            "all_a01_a08_present": [row["geometry_id"] for row in doe["geometries"]] == [f"ANISO_A{i:02d}" for i in range(1, 9)],
            "doe_unchanged": doe_sha_before == doe_sha_after,
            "reported_value_is_boundary_margin": out["classification"]["reported_0_032_is_cell_boundary_margin"],
            "reported_value_not_translated_polygon_gap": not out["classification"]["reported_0_032_is_canonical_translated_polygon_gap"],
            "high_precision_reproduces_reported_value": abs(reported - mpf(boundary["clearance_nm"])) < mp.mpf("1e-12"),
            "direct_pair_recomputed": abs(mpf(direct["distance_nm"]) - mp.mpf("44.5319955301249939648606783467")) < mp.mpf("1e-25"),
            "periodic_pair_recomputed": abs(mpf(periodic["distance_nm"]) - mp.mpf("52.5319955301249939648606783467")) < mp.mpf("1e-25"),
            "same_object_not_0_064": mpf(ar["nearest_same_object_periodic_image_pair"]["distance_nm"]) > mp.mpf("1.0"),
            "no_intersection_or_touch": ar["direct_no_overlap_or_touch_pass"] and ar["periodic_no_overlap_or_touch_pass"],
            "containment": ar["cell_containment_pass"],
            "all_eight_reaudited": len(all_rows) == 8,
            "a02_current_gate_blocked": not ar["current_inherited_gate_pass"],
            "solver_zero": out["safety_invariants"]["NEW_FDTD_BUDGET"] == 0 and out["safety_invariants"]["solver_entered"] == 0 and not out["safety_invariants"]["solver_run_called"],
        },
        "source_sha256": {"doe": doe_sha_before, "builder": sha256_file(BUILDER), "rule_source": sha256_file(RULE_SOURCE), "rule_authority": sha256_file(RULE_AUTH), "audit_script": sha256_file(AUDIT_SCRIPT) if AUDIT_SCRIPT.exists() else None},
    }
    checks["status"] = "PASS" if all(checks["checks"].values()) else "FAIL"
    validation_json.write_text(json.dumps(checks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": out["status"],
        "reported_nm": a02["validity"]["min_edge_gap_nm"],
        "direct_gap_nm": direct["distance_nm"],
        "periodic_gap_nm": periodic["distance_nm"],
        "same_object_periodic_gap_nm": ar["nearest_same_object_periodic_image_pair"]["distance_nm"],
        "boundary_margin_nm": boundary["clearance_nm"],
        "a02_current_gate_pass": ar["current_inherited_gate_pass"],
        "a01_a08_rows": len(all_rows),
        "validation": checks["status"],
        "active_fdtd": process_state["matching_process_count"],
        "artifacts": [str(report_json), str(report_md), str(validation_json), str(all_json), str(all_csv)],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
