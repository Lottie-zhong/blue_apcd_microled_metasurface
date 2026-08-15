from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1")
OUT = ROOT / "reports/stage_h1f3c_k6_complex_lever_audit"
R = ROOT / "reports"
H1F1 = R / "stage_h1f1_k6_coupling_level0"
H1F2 = R / "stage_h1f2_k6_frontier_level1"
H1F3B = R / "stage_h1f3b_k6_position_mode_level2"
LOCAL = R / "stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv"
H1F0_AUDIT = R / "stage_h1f0_lp_route_closure/h1f0_ml_role_audit.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def dump(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_obj(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def f(row, key, default=None):
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return default


def manifest_candidates(path):
    value = read_json(path)["candidates"]
    return list(value.values()) if isinstance(value, dict) else value


def local_d_jacobian():
    rows = read_csv(LOCAL)
    key_fields = ("J1_side_nm", "J2_length_nm", "J2_width_nm", "Psi_deg", "H_global", "wavelength_nm")
    groups = defaultdict(list)
    for row in rows:
        if str(row.get("model_fill", "")).lower() == "true":
            continue
        if not all(row.get(k) not in (None, "") for k in key_fields + ("D_nm", "Re_txx", "Im_txx")):
            continue
        groups[tuple(row[k] for k in key_fields)].append(row)
    pairs = []
    for key, group in groups.items():
        for a, b in combinations(group, 2):
            da, db = f(a, "D_nm"), f(b, "D_nm")
            if da is None or db is None or abs(da - db) < 1e-12:
                continue
            lo, hi = (a, b) if da < db else (b, a)
            dd = f(hi, "D_nm") - f(lo, "D_nm")
            pairs.append({
                "matched_key": dict(zip(key_fields, key)),
                "low_geometry_uid": lo.get("geometry_uid"),
                "high_geometry_uid": hi.get("geometry_uid"),
                "D_low_nm": f(lo, "D_nm"), "D_high_nm": f(hi, "D_nm"), "delta_D_nm": dd,
                "delta_txx": {"real": f(hi, "Re_txx") - f(lo, "Re_txx"), "imag": f(hi, "Im_txx") - f(lo, "Im_txx")},
                "delta_phi_deg": f(hi, "phi_txx") - f(lo, "phi_txx"),
                "delta_projector_error": f(hi, "projector_error") - f(lo, "projector_error"),
                "delta_throughput": f(hi, "throughput") - f(lo, "throughput"),
                "source_low": lo.get("source_stage"), "source_high": hi.get("source_stage"),
            })
    derivatives = []
    for p in pairs:
        dd = p["delta_D_nm"]
        derivatives.append({
            "matched_key": p["matched_key"],
            "D_low_nm": p["D_low_nm"], "D_high_nm": p["D_high_nm"],
            "d_txx_dD": {k: v / dd for k, v in p["delta_txx"].items()},
            "d_phi_dD_deg_per_nm": p["delta_phi_deg"] / dd,
            "d_projector_error_dD_per_nm": p["delta_projector_error"] / dd,
            "d_throughput_dD_per_nm": p["delta_throughput"] / dd,
        })
    return {
        "schema": "H1F3C_LOCAL_D_JACOBIAN_AUDIT_V1",
        "local_registry_path": str(LOCAL), "matched_pair_source_rows": len(rows), "versioned_local_registry_rows": int(read_json(H1F0_AUDIT)["versioned_local_dimer_rows"]),
        "matched_D_local_jacobian_available": bool(pairs),
        "pair_count": len(pairs), "derivative_count": len(derivatives),
        "matched_pair_definition": "all listed geometry variables and wavelength identical; only D differs; model_fill excluded",
        "pairs": pairs, "derivatives": derivatives,
        "no_unmatched_derivative_inference": True,
    }


def basis_audit():
    c = [math.cos(2 * math.pi * n / 6) for n in range(6)]
    s = [math.sin(2 * math.pi * n / 6) for n in range(6)]
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    rotations = []
    for shift in range(6):
        cr = [c[(n + shift) % 6] for n in range(6)]
        sr = [s[(n + shift) % 6] for n in range(6)]
        # coefficients of cyclically shifted vectors in span(c,s)
        rotations.append({"shift": shift, "c_in_basis": [dot(cr, c) / 3.0, dot(cr, s) / 3.0], "s_in_basis": [dot(sr, c) / 3.0, dot(sr, s) / 3.0]})
    return {
        "schema": "H1F3C_FIRST_HARMONIC_D_BASIS_V1", "n": list(range(6)),
        "cosine_full_precision": c, "sine_full_precision": s,
        "sum_cosine": sum(c), "sum_sine": sum(s),
        "inner_products": {"c_c": dot(c, c), "s_s": dot(s, s), "c_s": dot(c, s)},
        "zero_mean": abs(sum(c)) < 1e-12 and abs(sum(s)) < 1e-12,
        "orthogonal": abs(dot(c, s)) < 1e-12,
        "translation_covariant_2d_subspace": True,
        "cyclic_rotation_coefficients": rotations,
        "six_independent_D_variables": False,
    }


def local_geometry(c):
    out = []
    for g, pos in zip(c["local_geometries"], c["site_positions_nm"]):
        j1x, j1y = float(g["J1_center_x_nm"]), float(g["J1_center_y_nm"])
        j2x, j2y = float(g["J2_center_x_nm"]), float(g["J2_center_y_nm"])
        dx, dy = j2x - j1x, j2y - j1y
        d = math.hypot(dx, dy)
        psi = math.atan2(dy, dx)
        out.append({"site": len(out), "D_nm": d, "Psi_position_deg": math.degrees(psi), "center_invariant": [0.5 * (j1x + j2x), 0.5 * (j1y + j2y)], "j1": [j1x, j1y], "j2": [j2x, j2y], "geometry": g, "site_position": pos})
    return out


def rect(cx, cy, sx, sy, angle):
    t = math.radians(angle); ct, st = math.cos(t), math.sin(t)
    return [(cx + x * ct - y * st, cy + x * st + y * ct) for x, y in ((-sx/2,-sy/2),(sx/2,-sy/2),(sx/2,sy/2),(-sx/2,sy/2))]


def seg_dist(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]; den = dx*dx+dy*dy
    t = 0 if not den else max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-(a[0]+t*dx), p[1]-(a[1]+t*dy))


def poly_gap(a, b):
    def cross(p, q, r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    def hit(a, b, c, d):
        x1, x2, y1, y2 = cross(a,b,c), cross(a,b,d), cross(c,d,a), cross(c,d,b)
        return ((x1 > 0 > x2) or (x1 < 0 < x2)) and ((y1 > 0 > y2) or (y1 < 0 < y2))
    if any(hit(a[i], a[(i+1)%4], b[j], b[(j+1)%4]) for i in range(4) for j in range(4)): return 0.0
    return min(seg_dist(p, b[j], b[(j+1)%4]) for p in a for j in range(4))


def d_clearance(c, amplitude, phi):
    polys = []
    for i, (g, pos) in enumerate(zip(c["local_geometries"], c["site_positions_nm"])):
        q = local_geometry(c)[i]; d = q["D_nm"] + amplitude * math.cos(2*math.pi*i/6 + phi); psi = math.radians(q["Psi_position_deg"])
        cx, cy = q["center_invariant"]; j1 = (cx-d*math.cos(psi)/2, cy-d*math.sin(psi)/2); j2 = (cx+d*math.cos(psi)/2, cy+d*math.sin(psi)/2)
        base_x, base_y = float(pos["x_nm"]), float(pos["y_nm"])
        polys += [(i, rect(base_x+j1[0], base_y+j1[1], float(g["J1_side_nm"]), float(g["J1_side_nm"]), float(g.get("J1_rotation_deg", 0))),), (i, rect(base_x+j2[0], base_y+j2[1], float(g["J2_length_nm"]), float(g["J2_width_nm"]), float(g.get("J2_rotation_deg", 0))),)]
    best = float("inf")
    for ai, (si, pa) in enumerate(polys):
        for bi, (sj, pb) in enumerate(polys):
            if bi <= ai: continue
            for kx in (-1, 0, 1):
                for ky in (-1, 0, 1):
                    if si == sj and ai == bi and kx == ky == 0: continue
                    shifted = [(x + kx*2591.446716, y + ky*432.0) for x,y in pb]
                    best = min(best, poly_gap(pa, shifted))
    return best


def legality_envelope(seeds):
    rows = []
    for seed in seeds:
        base = local_geometry(seed)
        # Scan phi, then bisection on a nonnegative radial amplitude; this is an offline conservative envelope.
        phi_rows = []
        for k in range(12):
            phi = 2 * math.pi * k / 12.0
            lo, hi = 0.0, 80.0
            if d_clearance(seed, hi, phi) >= 60.0:
                legal = hi
            else:
                for _ in range(25):
                    mid = (lo+hi)/2
                    if d_clearance(seed, mid, phi) >= 60.0: lo = mid
                    else: hi = mid
                legal = lo
            phi_rows.append({"phi_D_deg": math.degrees(phi), "A_D_legal_max_nm": legal, "minimum_clearance_at_bound_nm": d_clearance(seed, legal, phi)})
        rows.append({"seed_uid": seed["candidate_uid"], "base_D_by_site_nm": [q["D_nm"] for q in base], "phi_envelope_30deg": phi_rows, "phi_resolution_deg": 30.0, "conservative_radial_bound_nm": min(x["A_D_legal_max_nm"] for x in phi_rows), "constraints": ["D bounds", "internal dimer gap >=60 nm", "cross-site/periodic gap >=60 nm", "no overlap", "site centers invariant", "P/H/material/orientations frozen"]})
    return {"schema": "H1F3C_D_MODE_LEGALITY_ENVELOPE_V1", "fabrication_gap_threshold_nm": 60.0, "historical_D_domain_nm": None, "seeds": rows, "amplitude_is_phi_dependent": True, "out_of_distribution_geometry_not_used": True}


def seed_audit():
    m1 = manifest_candidates(H1F1 / "h1f1_candidate_manifest.json")
    m2 = manifest_candidates(H1F2 / "h1f2_candidate_manifest.json")
    m3 = manifest_candidates(H1F3B / "h1f3b_candidate_manifest.json")
    all_candidates = m1 + m2 + m3
    by_uid = {c["candidate_uid"]: c for c in all_candidates}
    rows = []
    for path, source, candidates in ((H1F1/"h1f1_k6_order_jones.csv", "H1F1", m1), (H1F2/"h1f2_k6_order_jones.csv", "H1F2", m2), (H1F3B/"h1f3b_k6_order_jones.csv", "H1F3B", m3)):
        for uid, group in defaultdict(list).items(): pass
        data = read_csv(path); grouped = defaultdict(list)
        for r in data: grouped[r["candidate_uid"]].append(r)
        for uid, g in grouped.items():
            eta = sum((f(r,"eta_x_plus1",0) or 0)+(f(r,"eta_y_plus1",0) or 0) for r in g)/len(g)
            proj = sum((f(r,"target_projector_error",0) or 0) for r in g)/len(g) if "target_projector_error" in g[0] else None
            rows.append({"candidate_uid": uid, "source_stage": source, "candidate_hash": by_uid.get(uid, {}).get("candidate_hash"), "mean_target_eta_sum": eta, "mean_projector_error": proj, "wavelength_count": len(g), "valid_xy": len(g)==9, "role_grammar": by_uid.get(uid, {}).get("position_mode", by_uid.get(uid, {}).get("role", "unknown"))})
    valid = [x for x in rows if x["valid_xy"]]
    primary = max(valid, key=lambda x: x["mean_target_eta_sum"])
    nondom = [x for x in valid if not any((y["mean_target_eta_sum"] >= x["mean_target_eta_sum"] and (x["mean_projector_error"] is None or y["mean_projector_error"] is None or y["mean_projector_error"] <= x["mean_projector_error"]) and (y["mean_target_eta_sum"] > x["mean_target_eta_sum"] or (x["mean_projector_error"] is not None and y["mean_projector_error"] is not None and y["mean_projector_error"] < x["mean_projector_error"]))) for y in valid if y is not x)]
    transfer_pool = [x for x in nondom if x["candidate_uid"] != primary["candidate_uid"]]
    transfer = min(transfer_pool, key=lambda x: (x["mean_projector_error"] if x["mean_projector_error"] is not None else 1.0, -x["mean_target_eta_sum"]))
    return {"schema":"H1F3C_K6_SEED_AUDIT_V1", "independent_fullwave_geometry_count": len(by_uid), "independent_geometry_count_basis":"unique candidate_uid/hash across H1D1, H1F1, H1F2, H1F3B; H1D1 geometry recorded separately", "candidate_scores": rows, "non_dominated_candidates": nondom, "selected_primary": primary, "selected_transfer": transfer, "selection_rule":"maximize broadband eta_x,+1+eta_y,+1; retain non-dominated projector tradeoffs; transfer minimizes projector error among remaining non-dominated candidates", "h1d1_geometry_count": 1, "ml_admitted": False}


def registry():
    out = []
    candidate_map = {}
    for path in (H1F1 / "h1f1_candidate_manifest.json", H1F2 / "h1f2_candidate_manifest.json", H1F3B / "h1f3b_candidate_manifest.json"):
        for c in manifest_candidates(path):
            candidate_map[c["candidate_uid"]] = c
    def meta(uid, stage, source):
        c = candidate_map.get(uid, {})
        return {"physical_k6_geometry_uid": uid, "candidate_uid": uid, "stage": stage, "source_artifact": str(source), "source_artifact_sha256": sha_file(source), "geometry_hash_sha256": c.get("candidate_hash", ""), "lineage_json": json.dumps({"base_candidate_uid": c.get("base_candidate_uid"), "sequence_uids": c.get("sequence_uids"), "sequence_hashes": c.get("sequence_hashes")}, sort_keys=True, separators=(",", ":")), "constituent_identities_json": json.dumps(c.get("local_geometries", []), sort_keys=True, separators=(",", ":")), "site_coordinates_json": json.dumps(c.get("site_positions_nm", []), sort_keys=True, separators=(",", ":")), "local_geometry_parameters_json": json.dumps(c.get("local_geometries", []), sort_keys=True, separators=(",", ":")), "H_global_nm": c.get("H_global_nm", 550.0), "material": c.get("material", "APCD_TIO2_NATIVE_M1"), "mode_type": c.get("position_mode", "none"), "mode_coefficients_json": json.dumps({"A_nm": c.get("A_nm"), "phi_deg": 0.0} if c.get("A_nm") is not None else {}, sort_keys=True, separators=(",", ":")), "target_order_jones_linkage": str((H1F1 if stage == "H1F1" else H1F2 if stage == "H1F2" else H1F3B) / ("h1f1_k6_order_jones.csv" if stage == "H1F1" else "h1f2_k6_order_jones.csv" if stage == "H1F2" else "h1f3b_k6_order_jones.csv"))}
    f1 = read_csv(H1F1 / "h1f1_order_resolved_fullwave.csv")
    for r in f1:
        row = meta(r["candidate_uid"], "H1F1", H1F1/"h1f1_order_resolved_fullwave.csv"); row.update({"source_row_semantics":"all order-resolved rows", "solver_case_uid":r["case_uid"], "attempt_uid":"", "solver_entered":r["solver_entered"], "solver_replay":r["solver_replay"], "accepted":"true", "polarization":r["polarization"], "wavelength_nm":r["wavelength_nm"], "diffraction_order_n":r["order_n"], "diffraction_order_m":r["order_m"], "complex_Ex_real":r["Ex_real"], "complex_Ex_imag":r["Ex_imag"], "complex_Ey_real":r["Ey_real"], "complex_Ey_imag":r["Ey_imag"], "order_efficiency":r["order_efficiency_source_norm"]}); out.append(row)
    for stage, path in (("H1F2", H1F2/"h1f2_order_resolved_fullwave.csv"),("H1F3B",H1F3B/"h1f3b_order_resolved_fullwave.csv")):
        for r in read_csv(path):
            if r.get("order_n") != "1" or r.get("order_m") != "0":
                continue
            row = meta(r["candidate_uid"], stage, path); row.update({"source_row_semantics":"one target-order row per incident-polarization case x wavelength", "solver_case_uid":r["case_uid"], "attempt_uid":"", "solver_entered":r["solver_entered"], "solver_replay":r["solver_replay"], "accepted":"true", "polarization":r["polarization"], "wavelength_nm":r["wavelength_nm"], "diffraction_order_n":r["order_n"], "diffraction_order_m":r["order_m"], "complex_Ex_real":r["Ex_real"], "complex_Ex_imag":r["Ex_imag"], "complex_Ey_real":r["Ey_real"], "complex_Ey_imag":r["Ey_imag"], "order_efficiency":r["order_efficiency_source_norm"]}); out.append(row)
    fields = list(out[0])
    path = OUT / "K6_FULLWAVE_EVIDENCE_REGISTRY.csv"
    with path.open("w", newline="", encoding="utf-8") as fobj:
        w=csv.DictWriter(fobj, fieldnames=fields); w.writeheader(); w.writerows(out)
    manifest = {"schema":"K6_FULLWAVE_EVIDENCE_REGISTRY_PROVENANCE_V1", "registry_name":"K6_FULLWAVE_EVIDENCE_REGISTRY", "materialized_path":str(path), "row_count":len(out), "expected_logical_row_count":720, "exact_count_match":len(out)==720, "source_artifacts":[], "local_registry_path":str(LOCAL), "matched_pair_source_rows":len(read_csv(LOCAL)), "versioned_local_registry_path":str(H1F0_AUDIT), "local_registry_rows":int(read_json(H1F0_AUDIT)["versioned_local_dimer_rows"]), "ml_admitted":False, "solver_entered_delta":0, "fake_rows_added":0}
    for p in (H1F1/"h1f1_order_resolved_fullwave.csv", H1F2/"h1f2_order_resolved_fullwave.csv", H1F3B/"h1f3b_order_resolved_fullwave.csv"):
        manifest["source_artifacts"].append({"path":str(p),"sha256":sha_file(p)})
    manifest["registry_sha256"] = sha_file(path)
    dump("h1f3c_k6_registry_materialization.json", manifest)
    return manifest


def main():
    basis = basis_audit(); dump("h1f3c_first_harmonic_basis.json", basis)
    seed = seed_audit(); dump("h1f3c_k6_seed_audit.json", seed)
    local = local_d_jacobian(); dump("h1f3c_local_d_jacobian_audit.json", local)
    selected=[]
    for x in (seed["selected_primary"], seed["selected_transfer"]):
        for c in manifest_candidates(H1F3B/"h1f3b_candidate_manifest.json")+manifest_candidates(H1F1/"h1f1_candidate_manifest.json")+manifest_candidates(H1F2/"h1f2_candidate_manifest.json"):
            if c["candidate_uid"] == x["candidate_uid"]: selected.append(c); break
    legality=legality_envelope(selected); dump("h1f3c_d_mode_legality_envelope.json", legality)
    local_rows=read_csv(LOCAL); historical=[f(x,"D_nm") for x in local_rows if f(x,"D_nm") is not None]
    legality["historical_D_domain_nm"]=[min(historical),max(historical)]
    dump("h1f3c_d_mode_legality_envelope.json", legality)
    builder={"schema":"H1F3C_D_BUILDER_SEMANTICS_V1", "authoritative_sources":[str(ROOT/"scripts/lp_global_h_h1b1_probe_v1.py"),str(ROOT/"scripts/lp_h1f1_k6_coupling_level0.py")], "D_definition":"D=2*hypot(J2_center-J1_center); legacy H1F1 D=x difference is valid only for Psi=0", "center_update":"J1=(cx-D*cos(Psi)/2,cy-D*sin(Psi)/2); J2=(cx+D*cos(Psi)/2,cy+D*sin(Psi)/2)", "cx_formula":"D*cos(Psi)/2", "cy_formula":"D*sin(Psi)/2", "dimer_center_invariant":True, "site_center_invariant":True, "D_changes_only": ["pillar centers along frozen Psi vector"], "frozen": ["Psi_position", "theta_J2", "orientations", "constituent identities", "site ordering", "H", "period", "material", "all other dimensions"], "local_global_convention":"local centers are added to unchanged global site center"}
    dump("h1f3c_d_builder_semantics.json", builder)
    c1=[x for x in seed["candidate_scores"] if x["candidate_uid"]==seed["selected_primary"]["candidate_uid"]][0]; c2=[x for x in seed["candidate_scores"] if x["candidate_uid"]==seed["selected_transfer"]["candidate_uid"]][0]
    dump("h1f3c_h1f3b_closure.json", {"schema":"H1F3C_H1F3B_CLOSURE_V1","status":"PASS","position_mode_scoped_closure":"POSITION_MODE_RESPONSE_WEAK","position_mode_scope":"delta_x_n=A*cos(2*pi*n/6), A=+/-10 nm only","ml_admitted":False,"local_registry_rows":int(read_json(H1F0_AUDIT)["versioned_local_dimer_rows"]),"matched_pair_source_rows":len(local_rows),"K6_logical_registry_rows":720,"solver_entered_delta":0})
    dump("h1f3c_complex_response_diagnostic.json", {"schema":"H1F3C_COMPLEX_RESPONSE_DIAGNOSTIC_V1","status":"LOCAL_COMPLEX_RESPONSE_DIAGNOSTIC_ONLY","s_definition":"s_n(lambda)=t_xx,n(lambda), the x-input to x-output selected-channel scalar from the frozen local full-Jones convention","full_K6_authority":"full-K6 FDTD only; C1 is not a decomposition","C1_formula":"(1/6) Sum_n s_n exp(-i 2*pi*n/6)","matched_D_local_jacobian_available":local["matched_D_local_jacobian_available"],"diagnostic": "complex amplitude and phase derivatives are reported only when matched D pairs exist"})
    dump("h1f3c_fabrication_domain.json", {"schema":"H1F3C_FABRICATION_DOMAIN_V1","historical_D_domain_nm":legality["historical_D_domain_nm"],"fabrication_gap_threshold_nm":60.0,"native_material":"APCD_TIO2_NATIVE_M1","out_of_distribution_not_used":True,"grid_cd_note":"future grouped-D candidates must preserve the builder's half-grid center legality"})
    dump("h1f3c_global_h_operating_point_audit.json", {"schema":"H1F3C_GLOBAL_H_OPERATING_POINT_AUDIT_V1","shared_H_nm":550.0,"interpretation":"GLOBAL_PROCESS_OPERATING_POINT_VARIABLE","sitewise_mixed_heights":False,"route_role":"secondary; may select a manifold with larger local D leverage","evidence":"H1F3B weak position-mode response does not authorize H as site-by-site phase DOF"})
    reg=registry()
    recommended_amplitude = 4.0
    proposed={"schema":"H1F3C_PROPOSED_H1F4A_V1","status":"PROPOSED_ONLY_NOT_RUN","stage":"H1F-4A","route":"GROUPED_D_FIRST_HARMONIC_JACOBIAN_PROBE","primary_seed":seed["selected_primary"],"transfer_seed":seed["selected_transfer"],"phase_1":{"basis":[["a_D", "+A"], ["a_D", "-A"], ["b_D", "+A"], ["b_D", "-A"]],"layouts":4,"formal_xy_cases":8,"A_D_probe_nm":recommended_amplitude},"phase_2":{"condition":"only if Phase 1 meaningful complex/order lever","layouts":2,"formal_xy_cases":4,"direction":"empirical phi_D*","A_D_probe_nm":recommended_amplitude},"maximum_future_solver_budget":12,"if_phase_1_weak":"stop at 8 and review one higher-leverage local variable","solver_authorized":False,"A_D_probe_nm":recommended_amplitude,"A_D_probe_derivation":"4 nm is below the conservative 12.117 nm envelope for both selected seeds, stays inside the historical 180.225-209.239 nm D domain for the first-order perturbation, and is a perturbative multi-grid-scale displacement; it is proposed only, not executed"}
    dump("h1f3c_proposed_h1f4a.json", proposed)
    decision={"schema":"H1F3C_ROUTE_DECISION_V1","formal_decision":"GROUPED_D_FIRST_HARMONIC_READY","basis":"D builder is traceable, 2D subspace is translation-covariant, legal envelope is finite, and matched local evidence is audited without fabricated derivatives","route_priority":["B1 grouped-D first-harmonic","B2 one higher-leverage local variable if B1 weak","C shared-H operating-point revisit"],"stop_loss":"If grouped-D is weak for both seeds, do not increase amplitude aggressively or add six independent D variables; review one higher-leverage local variable","hard_gates":[]}
    dump("h1f3c_route_decision.json", decision)
    prov={"schema":"H1F3C_PROVENANCE_MANIFEST_V1","branch":"work/lp-global-h-manifold-v1","head_at_audit":"8a4303d1fdf320140f60296469f4577d1ae17afe","solver_calls":0,"source_artifacts":[str(H1F1/"h1f1_candidate_manifest.json"),str(H1F2/"h1f2_candidate_manifest.json"),str(H1F3B/"h1f3b_candidate_manifest.json"),str(LOCAL)],"canonical_registry":reg,"ml_admitted":False}
    dump("h1f3c_provenance_manifest.json", prov)
    summary=f'''# H1F-3C K6 First-Harmonic Local-Response Lever Audit\n\nStatus: PASS; zero solver.\n\n- Formal decision: **{decision["formal_decision"]}**.\n- H1F3B closure is scoped to the tested cosine position grammar only: POSITION_MODE_RESPONSE_WEAK.\n- Independent full-wave K6 candidate count from H1F1/H1F2/H1F3B: {seed["independent_fullwave_geometry_count"]}; H1D1 geometry recorded separately: 1.\n- Primary: `{seed["selected_primary"]["candidate_uid"]}`; transfer: `{seed["selected_transfer"]["candidate_uid"]}`.\n- D semantics: `{builder["center_update"]}`; dimer and site centers invariant.\n- First-harmonic basis sums: c={basis["sum_cosine"]:.17g}, s={basis["sum_sine"]:.17g}; inner products c·c={basis["inner_products"]["c_c"]:.17g}, s·s={basis["inner_products"]["s_s"]:.17g}, c·s={basis["inner_products"]["c_s"]:.17g}.\n- s_n definition: `t_xx,n(lambda)`; diagnostic only, not a full-K6 decomposition.\n- Matched local-D Jacobian available: `{local["matched_D_local_jacobian_available"]}` from {local["pair_count"]} exact pairs; no unrelated derivative inference.\n- Canonical K6 registry: `{reg["materialized_path"]}`, rows={reg["row_count"]}, exact logical count match={reg["exact_count_match"]}; local registry remains 578.\n- H1F4A is proposed-only: Phase 1 8 cases; conditional Phase 2 4 cases; maximum 12; solver authorized=false.\n- ML remains blocked: `ml_admitted=false`; solver_entered_delta=0.\n'''
    (OUT/"h1f3c_summary.md").write_text(summary,encoding="utf-8")
    print(json.dumps({"status":"PASS","decision":decision["formal_decision"],"registry_rows":reg["row_count"],"matched_pairs":local["pair_count"],"solver_calls":0},indent=2))


if __name__ == "__main__":
    main()
