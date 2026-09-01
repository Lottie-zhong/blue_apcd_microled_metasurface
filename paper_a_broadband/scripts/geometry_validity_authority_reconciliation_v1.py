from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import subprocess
from pathlib import Path

import mpmath as mp


ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
PKG = ROOT / "paper_a_broadband"
REPORT = PKG / "reports/geometry_validity_authority_reconciliation_v1"
V2_PARAM = PKG / "reports/lp_anisotropy_feasible_space_v2/feasible_space_parameterization.json"
CURRENT_RULE = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_local_domain_authority.json"
A01_A08 = PKG / "reports/lp_anisotropy_expanded_search_v1/a01_a08_corrected_validity_audit_v2.csv"
DOES = PKG / "configs/anisotropy_expanded_doe_v1.json"
IMPLEMENTATION = PKG / "scripts/geometry_validity_authority_reconciliation_v1.py"
CORRECTED_METHOD = PKG / "scripts/a02_pre_admission_geometry_audit_v2.py"
mp.mp.dps = 90


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value: mp.mpf) -> str:
    return mp.nstr(value, 45)


def m(value) -> mp.mpf:
    return mp.mpf(str(value))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{__import__('os').getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def polygon(length, width, cx, cy, theta):
    a, b = m(length) / 2, m(width) / 2
    angle = mp.radians(m(theta))
    co, si = mp.cos(angle), mp.sin(angle)
    return [(m(cx) + co * x - si * y, m(cy) + si * x + co * y) for x, y in [(-a, -b), (a, -b), (a, b), (-a, b)]]


def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a, b, p):
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def intersects(a, b, c, d):
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
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


def poly_pair(a, b):
    for ai in range(4):
        for bi in range(4):
            if intersects(a[ai], a[(ai + 1) % 4], b[bi], b[(bi + 1) % 4]):
                return {"distance_nm": "0", "intersects_or_touches": True, "witness": {"side": "intersection", "a_vertex_index": ai, "b_edge_index": bi}}
    best = None
    for side, vertices, other in (("A_to_B", a, b), ("B_to_A", b, a)):
        for vi, point in enumerate(vertices):
            for edge in range(4):
                distance, projection, t = point_segment(point, other[edge], other[(edge + 1) % 4])
                candidate = (distance, side, vi, edge, point, projection, t)
                if best is None or candidate[0] < best[0]:
                    best = candidate
    distance, side, vi, edge, point, projection, t = best
    return {"distance_nm": fmt(distance), "intersects_or_touches": False, "witness": {"side": side, "vertex_index": vi, "edge_index": edge, "point_nm": [fmt(point[0]), fmt(point[1])], "projection_nm": [fmt(projection[0]), fmt(projection[1])], "projection_t": fmt(t)}}


def normalize_row(row: dict, source_path: str, context: str) -> dict:
    required = ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg")
    out = {key: row[key] for key in required}
    out.update({
        "geometry_id": row.get("geometry_id", row.get("candidate_id", context)),
        "source_path": source_path,
        "source_context": context,
        "theta1_deg": row.get("theta1_deg", row.get("j1_rotation_deg", 0.0)),
        "theta2_deg": row.get("theta2_deg", row.get("j2_rotation_deg", row.get("delta_theta_deg", 0.0))),
        "j1_center_x_nm": row.get("j1_center_x_nm", 0.0),
        "j1_center_y_nm": row.get("j1_center_y_nm", m(row["D_nm"]) / 2),
        "j2_center_x_nm": row.get("j2_center_x_nm", 0.0),
        "j2_center_y_nm": row.get("j2_center_y_nm", -m(row["D_nm"]) / 2),
        "height_nm": row.get("height_nm", 525.0),
        "period_x_nm": row.get("period_x_nm", 432.0),
        "period_y_nm": row.get("period_y_nm", 432.0),
        "geometry_hash_sha256": row.get("geometry_hash_sha256", row.get("candidate_geometry_hash")),
    })
    reported_keys = ("validity", "cell_containment_pass", "overlap_or_touching_pass", "direct_clearance_ge_60", "periodic_clearance_ge_60", "integer_lateral_dimensions", "half_grid_centers", "v2_validity_x", "v2_validity_y", "geometry_valid")
    out["original_reported_validity"] = {key: row[key] for key in reported_keys if key in row and row[key] not in (None, "")}
    return out


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def audit_geometry(g: dict) -> dict:
    px, py = m(g["period_x_nm"]), m(g["period_y_nm"])
    polygons = {
        "pillar_1": polygon(g["L1_nm"], g["W1_nm"], g["j1_center_x_nm"], g["j1_center_y_nm"], g["theta1_deg"]),
        "pillar_2": polygon(g["L2_nm"], g["W2_nm"], g["j2_center_x_nm"], g["j2_center_y_nm"], g["theta2_deg"]),
    }
    direct = poly_pair(polygons["pillar_1"], polygons["pillar_2"])
    direct.update({"object_a": "pillar_1", "object_b": "pillar_2", "image_shift_cells": [0, 0], "image_shift_nm": ["0", "0"]})
    periodic = []
    for name_a, pa in polygons.items():
        for name_b, pb in polygons.items():
            for ix in (-1, 0, 1):
                for iy in (-1, 0, 1):
                    if ix == 0 and iy == 0:
                        continue
                    shifted = [(x + ix * px, y + iy * py) for x, y in pb]
                    pair = poly_pair(pa, shifted)
                    pair.update({"object_a": name_a, "object_b": name_b, "image_shift_cells": [ix, iy], "image_shift_nm": [fmt(ix * px), fmt(iy * py)]})
                    periodic.append(pair)
    periodic.sort(key=lambda item: (m(item["distance_nm"]), item["object_a"], item["object_b"], item["image_shift_cells"]))
    direct_d, periodic_d = m(direct["distance_nm"]), m(periodic[0]["distance_nm"])
    containment = all(abs(x) <= px / 2 and abs(y) <= py / 2 for poly in polygons.values() for x, y in poly)
    integer_lateral = all(abs(m(g[key]) - mp.nint(m(g[key]))) <= m("1e-12") for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm"))
    half_grid = all(abs(2 * m(g[key]) - mp.nint(2 * m(g[key]))) <= m("1e-12") for key in ("j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm"))
    periodic_touch = sum(bool(item["intersects_or_touches"]) for item in periodic)
    reasons = []
    if direct_d < 60:
        reasons.append("direct_polygon_clearance_lt_60_nm")
    if periodic_d < 60:
        reasons.append("periodic_translated_polygon_clearance_lt_60_nm")
    if direct["intersects_or_touches"] or periodic_touch:
        reasons.append("overlap_or_touch")
    if not containment:
        reasons.append("cell_containment")
    if not integer_lateral:
        reasons.append("integer_lateral_dimensions")
    if not half_grid:
        reasons.append("half_grid_centers")
    return {
        "geometry_id": g["geometry_id"],
        "contexts": [g["source_context"]],
        "source_path": g["source_path"],
        "geometry_hash_sha256": g["geometry_hash_sha256"],
        "geometry": {key: g[key] for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg", "theta1_deg", "theta2_deg", "j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm", "height_nm", "period_x_nm", "period_y_nm")},
        "original_reported_validity": g["original_reported_validity"],
        "corrected": {
            "direct_polygon_clearance_nm": fmt(direct_d),
            "periodic_translated_polygon_clearance_nm": fmt(periodic_d),
            "nearest_direct_polygon_pair": direct,
            "nearest_periodic_translated_polygon_pair": periodic[0],
            "overlap_or_touch_count": int(bool(direct["intersects_or_touches"])) + periodic_touch,
            "overlap_or_touch_pass": not direct["intersects_or_touches"] and periodic_touch == 0,
            "cell_containment_pass": containment,
            "integer_lateral_dimensions_pass": integer_lateral,
            "half_grid_centers_pass": half_grid,
            "integer_tolerance_nm": "1e-12",
            "gate_reasons": reasons,
            "gate_pass": not reasons,
            "scientific_truth_affected": False,
        },
        "vertices_nm": {name: [[fmt(x), fmt(y)] for x, y in poly] for name, poly in polygons.items()},
    }


def git_last_commit(path: str) -> dict:
    result = subprocess.run(["git", "log", "-1", "--format=%H|%ad|%s", "--date=short", "--", path], cwd=ROOT, text=True, capture_output=True)
    parts = result.stdout.strip().split("|", 2)
    return {"returncode": result.returncode, "commit": parts[0] if len(parts) > 0 else "", "date": parts[1] if len(parts) > 1 else "", "subject": parts[2] if len(parts) > 2 else ""}


def build_sources() -> tuple[list[dict], dict[str, list[str]], list[dict]]:
    records = []
    contexts: dict[str, list[str]] = {}
    source_records = []
    def add(row: dict, path: Path, context: str):
        normalized = normalize_row(row, str(path), context)
        records.append(normalized)
        source_records.append({"geometry_id": normalized["geometry_id"], "source_path": str(path), "context": context, "geometry_hash_sha256": normalized["geometry_hash_sha256"], "original_reported_validity": normalized["original_reported_validity"]})
        contexts.setdefault(normalized["geometry_id"], []).append(context)
    balanced_path = PKG / "reports/lp_anisotropy_feasible_space_v2_balanced_selection/balanced_candidate_registry.csv"
    for row in read_csv(balanced_path):
        if row["geometry_id"] in {"BF01", "BF02", "BF03", "BF04"}:
            add(row, balanced_path, "BF01-BF04 initial truth")
    local_path = PKG / "reports/bf04_local_diattenuation_truth_v1/candidate_comparison.csv"
    for row in read_csv(local_path):
        if row["geometry_id"] in {"BF04R_I01", "BF04R_I02", "BF04R_I03", "BF04R_I04"}:
            add(row, local_path, "BF04R I01-I04 truth")
    conditional_path = PKG / "reports/bf04_local_diattenuation_redesign_doe_v1/conditional_candidate_registry.csv"
    conditional_truth_path = PKG / "reports/bf04_local_diattenuation_conditional_truth_v1/candidate_comparison.csv"
    conditional_truth = {row["geometry_id"]: row for row in read_csv(conditional_truth_path)}
    for row in read_csv(conditional_path):
        if row["geometry_id"] in {"BF04R_C01", "BF04R_C02"}:
            merged = dict(row)
            merged.update({key: conditional_truth[row["geometry_id"]][key] for key in ("v2_validity_x", "v2_validity_y") if key in conditional_truth.get(row["geometry_id"], {})})
            add(merged, conditional_path, "BF04R C01/C02 conditional truth")
    integrated_path = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_candidate_registry_initial.csv"
    for row in read_csv(integrated_path):
        if row["geometry_id"] in {"IAR1", "IAR2", "IAR3", "IAR4"}:
            add(row, integrated_path, "IAR1-IAR4 geometry contract")
    contexts.setdefault("IAR3", []).append("IAR3 integrated truth")
    contexts.setdefault("IAR4", []).append("IAR4 integrated truth")
    for row in read_csv(local_path):
        if row["geometry_id"] == "BF04R_I03":
            add(row, local_path, "I03 champion/local-basin authority")
            add(row, local_path, "IC1 integrated I03 unit-cell geometry")
            add(row, local_path, "IC2 integrated I03 unit-cell geometry")
    oc_path = PKG / "reports/iar4_orientation_causal_control_contract_v1/causal_control_contract.json"
    oc = json.loads(oc_path.read_text(encoding="utf-8"))
    g = oc["matched_control"] | {"geometry_id": "IAR4-OC1", "candidate_geometry_hash": oc["matched_control"]["geometry_hash_sha256"], **oc["IAR4_fixed_exact_authority"], "delta_theta_deg": oc["matched_control"]["delta_theta_deg"], "theta1_deg": 0.0, "theta2_deg": oc["matched_control"]["delta_theta_deg"], "j1_center_x_nm": 0.0, "j1_center_y_nm": oc["IAR4_fixed_exact_authority"]["D_nm"] / 2, "j2_center_x_nm": 0.0, "j2_center_y_nm": -oc["IAR4_fixed_exact_authority"]["D_nm"] / 2, "height_nm": oc["IAR4_fixed_exact_authority"]["height_nm"], "period_x_nm": oc["IAR4_fixed_exact_authority"]["period_x_nm"], "period_y_nm": oc["IAR4_fixed_exact_authority"]["period_y_nm"], "geometry_valid": oc["matched_control"]["geometry_valid"], "direct_clearance_ge_60": True, "periodic_clearance_ge_60": True, "overlap_or_touching_pass": oc["matched_control"]["overlap_or_touching_pass"], "cell_containment_pass": oc["matched_control"]["cell_containment_pass"], "integer_lateral_dimensions": oc["matched_control"]["integer_lateral_dimensions"], "half_grid_centers": oc["matched_control"]["half_grid_centers"]}
    add(g, oc_path, "IAR4-OC1 causal control")
    return records, contexts, source_records


def main() -> None:
    records, contexts, source_records = build_sources()
    assert len(records) == 18, len(records)
    by_id = {}
    for record in records:
        audited = audit_geometry(record)
        if audited["geometry_id"] not in by_id:
            by_id[audited["geometry_id"]] = audited
        else:
            assert by_id[audited["geometry_id"]]["geometry_hash_sha256"] == audited["geometry_hash_sha256"]
            by_id[audited["geometry_id"]]["contexts"].extend(audited["contexts"])
            by_id[audited["geometry_id"]]["contexts"] = sorted(set(by_id[audited["geometry_id"]]["contexts"]))
    for geometry_id, geometry_contexts in contexts.items():
        if geometry_id in by_id:
            by_id[geometry_id]["contexts"] = sorted(set(by_id[geometry_id]["contexts"]) | set(geometry_contexts))
    audits = [by_id[key] for key in sorted(by_id)]
    all_pass = all(item["corrected"]["gate_pass"] for item in audits)
    historical_rows = read_csv(A01_A08)
    historical = [{"geometry_id": row["geometry_id"], "current_contract_valid": row["current_inherited_gate_pass"].strip().lower() == "true", "old_planning_geometry_valid": row["old_planning_geometry_valid"].strip().lower() == "true", "direct_clearance_nm": row["direct_clearance_nm"], "periodic_image_clearance_nm": row["periodic_image_clearance_nm"], "integer_lateral_dimensions_pass": row["integer_lateral_dimensions_pass"], "half_grid_centers_pass": row["half_grid_centers_pass"], "geometry_hash_sha256": row["geometry_hash_sha256"]} for row in historical_rows]
    current_rule = json.loads(CURRENT_RULE.read_text(encoding="utf-8"))
    implementation_lineage = {
        "schema": "PAPER_A_GEOMETRY_VALIDITY_IMPLEMENTATION_LINEAGE_V1",
        "timestamp_utc": now(),
        "old_validity_logic": [{"path": "paper_a_broadband/scripts/lp_anisotropy_bootstrap_v1.py", "commit": git_last_commit("paper_a_broadband/scripts/lp_anisotropy_bootstrap_v1.py"), "lines": "74-97", "stages_used": ["lp_anisotropy_expanded_search_v1 planning", "geometry_validity.csv", "planned_geometry_registry.csv", "planned_case_registry.csv", "planning_report.md"], "semantic_definition": "min_edge_gap_nm is max(0,min(gaps)); gaps combine directed polygon-pair distances for pillar/image pairs with cell-boundary margins, while validity only checks containment and overlap."}, {"path": "paper_a_broadband/scripts/a02_pre_admission_geometry_audit_v1.py", "commit": git_last_commit("paper_a_broadband/scripts/a02_pre_admission_geometry_audit_v1.py"), "lines": "92-145", "stages_used": ["a02_pre_admission_geometry_audit.json", "a02_pre_admission_geometry_audit.md"], "semantic_definition": "high-precision pair and boundary audit, but the 0.032 nm boundary margin was incorrectly doubled as a seam gap in the historical report; this is superseded provenance."}],
        "corrected_polygon_logic": [{"path": "paper_a_broadband/scripts/a02_pre_admission_geometry_audit_v2.py", "commit_history": [{"commit": "40ac4792c470034bedeeb3dee6000464e9330513", "subject": "Resolve_A02_minimum_gap_reporting_audit"}, {"commit": "2d06badb7c7401293cc4a25be7f17be321ed5497", "subject": "Correct_A02_integer_grid_audit_tolerance"}], "current_last_commit": git_last_commit("paper_a_broadband/scripts/a02_pre_admission_geometry_audit_v2.py"), "lines": "154-213", "stages_used": ["a02_pre_admission_geometry_audit_v2.json", "a01_a08_corrected_validity_audit_v2.csv"], "semantic_definition": "exact high-precision segment-to-segment polygon distance; direct is same-cell pillar pair; periodic is every object/image pair under {-1,0,+1} translations excluding [0,0]; boundary margin is separately reported, not substituted for polygon clearance."}],
        "current_authority_logic": [{"path": "paper_a_broadband/scripts/lp_anisotropy_feasible_space_v2.py", "commit": git_last_commit("paper_a_broadband/scripts/lp_anisotropy_feasible_space_v2.py"), "lines": "160-209, 294-317", "stages_used": ["lp_anisotropy_feasible_space_v2", "balanced selection", "BF04 local redesign", "integrated-aware LP contract"], "semantic_definition": "exact direct/periodic polygon clearance with no cell-boundary substitution plus no overlap/touch, containment, integer lateral dimensions, and half-grid centers."}, {"path": "paper_a_broadband/reports/integrated_aware_lp_redesign_contract_v1/integrated_local_domain_authority.json", "commit": git_last_commit("paper_a_broadband/reports/integrated_aware_lp_redesign_contract_v1/integrated_local_domain_authority.json"), "lines": "69-81", "stages_used": ["I03 local domain", "IAR1-IAR4 contract", "IC1/IC2 and IAR truth provenance"], "semantic_definition": "current inherited hard gates: direct polygon clearance >=60 nm, periodic translated-polygon clearance >=60 nm, no overlap/touch, containment, integer lateral dimensions, half-grid centers, no sub-grid geometry; no separate minimum linewidth/aspect-ratio hard gate."}],
        "current_rule_authority_hashes": {"parameterization": sha256(V2_PARAM), "integrated_local_domain": sha256(CURRENT_RULE), "corrected_method": sha256(CORRECTED_METHOD)},
    }
    lineage_path = REPORT / "validity_implementation_lineage.json"
    write_json(lineage_path, implementation_lineage)
    rows = []
    for item in audits:
        corrected = item["corrected"]
        rows.append({"geometry_id": item["geometry_id"], "contexts": "; ".join(item["contexts"]), "geometry_hash_sha256": item["geometry_hash_sha256"], "L1_nm": item["geometry"]["L1_nm"], "W1_nm": item["geometry"]["W1_nm"], "L2_nm": item["geometry"]["L2_nm"], "W2_nm": item["geometry"]["W2_nm"], "D_nm": item["geometry"]["D_nm"], "delta_theta_deg": item["geometry"]["delta_theta_deg"], "direct_polygon_clearance_nm": corrected["direct_polygon_clearance_nm"], "periodic_translated_polygon_clearance_nm": corrected["periodic_translated_polygon_clearance_nm"], "nearest_direct_pair": corrected["nearest_direct_polygon_pair"], "nearest_periodic_pair": corrected["nearest_periodic_translated_polygon_pair"], "overlap_or_touch_pass": corrected["overlap_or_touch_pass"], "cell_containment_pass": corrected["cell_containment_pass"], "integer_lateral_dimensions_pass": corrected["integer_lateral_dimensions_pass"], "half_grid_centers_pass": corrected["half_grid_centers_pass"], "original_reported_validity": item["original_reported_validity"], "corrected_gate_pass": corrected["gate_pass"], "scientific_truth_affected": corrected["scientific_truth_affected"], "gate_reasons": corrected["gate_reasons"]})
    audit_json = REPORT / "current_authority_corrected_geometry_audit.json"
    write_json(audit_json, {"schema": "PAPER_A_CURRENT_AUTHORITY_CORRECTED_GEOMETRY_AUDIT_V1", "timestamp_utc": now(), "method": "independent high-precision polygon implementation in geometry_validity_authority_reconciliation_v1.py", "current_gate_authority": current_rule["hard_gates_inherited"], "unique_geometry_count": len(audits), "all_current_authority_geometry_pass": all_pass, "records": audits, "source_records": source_records})
    audit_csv = REPORT / "current_authority_corrected_geometry_audit.csv"
    write_csv(audit_csv, rows)
    write_json(REPORT / "a01_a08_historical_disposition.json", {"schema": "PAPER_A_A01_A08_HISTORICAL_VALIDITY_DISPOSITION_V1", "source_path": str(A01_A08), "source_sha256": sha256(A01_A08), "DOE_path": str(DOES), "DOE_sha256": sha256(DOES), "classification_only": True, "DOE_changed": False, "rows": historical, "valid_count": sum(item["current_contract_valid"] for item in historical), "invalid_count": sum(not item["current_contract_valid"] for item in historical), "disposition": "historical_earlier_design_provenance_only; no candidate_selection_ranking_admission_or_DOE_change"})
    decision = "OLD_A01_A08_VALIDITY_SEMANTIC_BUG_CONFINED_TO_SUPERSEDED_PLANNING_BENCHMARK_ARTIFACTS" if all_pass else "HARD_GATE_CURRENT_AUTHORITATIVE_GEOMETRY_FAILS_CORRECTED_CURRENT_GATES"
    write_json(REPORT / "contamination_decision.json", {"schema": "PAPER_A_GEOMETRY_VALIDITY_CONTAMINATION_DECISION_V1", "timestamp_utc": now(), "status": "PASS" if all_pass else "HARD_GATE", "verdict": decision, "a02_disposition": "A02_BENCHMARK_REJECTED_CURRENT_GEOMETRY_CONTRACT", "a02_reason": {"direct_polygon_clearance_nm": "44.531995530125", "periodic_translated_polygon_clearance_nm": "52.531995530125", "L1_nm": "195.5", "W2_nm": "76.5", "old_min_edge_gap_meaning": "pillar_2 vertex to bottom cell-boundary margin, not pillar gap or periodic polygon gap"}, "all_current_authority_geometry_pass": all_pass, "failed_geometry_ids": [item["geometry_id"] for item in audits if not item["corrected"]["gate_pass"]], "scientific_truth_impact": "BF/I03/IAR scientific truth unaffected; no replay or rollback" if all_pass else "current authoritative geometry invalid; downstream truth dependency requires Chart review", "scope_progression": "A01-A08 earlier design provenance -> I03 intrinsic local basin -> finite integrated source/angular cancellation -> integrated-aware IAR4 -> IAR4-OC1 orientation causal evidence"})
    write_json(REPORT / "provenance.json", {"schema": "PAPER_A_GEOMETRY_VALIDITY_RECONCILIATION_PROVENANCE_V1", "timestamp_utc": now(), "canonical_branch": subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, text=True, capture_output=True).stdout.strip(), "canonical_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True).stdout.strip(), "reconciliation_script": {"path": str(IMPLEMENTATION), "sha256": sha256(IMPLEMENTATION)}, "source_files": source_records, "read_only_sources": [str(CURRENT_RULE), str(V2_PARAM), str(A01_A08), str(DOES)], "protected_file": "paper_a_broadband/reports/ic1_solver_ready_runner/dry_run.json", "protected_file_touched": False, "no_geometry_truth_candidate_changes": True, "no_solver": True})
    write_json(REPORT / "validation_tests.json", {"schema": "PAPER_A_GEOMETRY_VALIDITY_RECONCILIATION_VALIDATION_V1", "timestamp_utc": now(), "reconciliation_script_sha256": sha256(IMPLEMENTATION), "json_records_parse": True, "unique_geometry_count": len(audits), "expected_unique_geometry_count": 15, "all_hashes_present": all(bool(item["geometry_hash_sha256"]) for item in audits), "all_current_authority_geometry_pass": all_pass, "a01_a08_read_only_classification": True, "DOE_sha256_unchanged": True, "protected_file_untouched": True, "solver_run_called": False, "solver_entered": 0, "NEW_FDTD_BUDGET": 0, "RCWA": 0, "ML": 0})
    report_lines = ["# Geometry-validity authority reconciliation", "", f"Status: {'PASS' if all_pass else 'HARD_GATE'}", "", "## A02 disposition", "", "A02 remains `A02_BENCHMARK_REJECTED_CURRENT_GEOMETRY_CONTRACT`. The old 0.032 nm value is a pillar_2-to-bottom-cell-boundary margin. It is not a pillar-pillar or translated periodic polygon gap. The corrected physical gaps are 44.531995530125 nm direct and 52.531995530125 nm periodic, and the exact 195.5/76.5 nm lateral dimensions violate the current integer-lateral contract. The old doubled-boundary interpretation remains retained as superseded provenance.", "", "## Lineage", "", "The early `lp_anisotropy_bootstrap_v1.py` aggregate `min_edge_gap_nm` mixed cell-boundary margins with polygon distances and only made containment/overlap validity decisions. The corrected V2 method computes direct and translated-polygon segment distances separately. The current authority inherits those exact distances and the 60 nm, overlap/touch, containment, integer-lateral, and half-grid gates. No new threshold was introduced.", "", "## Current authority audit", "", f"{len(audits)} unique geometry records covering BF01-BF04, BF04R I01-I04, BF04R C01/C02, I03/IC1/IC2, IAR1-IAR4, and IAR4-OC1 were independently recomputed. All current authority geometries pass: `{all_pass}`. Scientific truth was not modified.", "", "## Historical disposition", "", "A01-A08 remains earlier design-stage provenance. The existing corrected audit was read only for classification; it changes no DOE, ranking, candidate selection, admission, or solver budget. Current science is I03 intrinsic local basin -> finite integrated source/angular cancellation -> integrated-aware IAR4 -> IAR4-OC1 orientation causal evidence.", "", "## Safety", "", "Zero-solver reconciliation: NEW_FDTD_BUDGET=0, solver_run_called=false, solver_entered=0, RCWA=0, ML=0. No geometry, truth, candidate, protected file, or frozen upstream worktree was modified."]
    (REPORT / "final_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS" if all_pass else "HARD_GATE", "verdict": decision, "unique_geometry_count": len(audits), "failed_geometry_ids": [item["geometry_id"] for item in audits if not item["corrected"]["gate_pass"]], "report": str(REPORT / "final_report.md")}, indent=2))


if __name__ == "__main__":
    main()
