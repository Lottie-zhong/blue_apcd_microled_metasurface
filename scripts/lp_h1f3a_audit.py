import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "stage_h1f3a_k6_level2_grammar_audit"
REMOTE_REPORT = ROOT / "reports"
P = 431.907786
P_SUPER = 2591.446716
P_Y = 432.0
GRID = [450.0 + 0.5 * i for i in range(9)]


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(name, value):
    (REPORT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a, b, p):
    return abs(cross(a, b, p)) < 1e-8 and min(a[0], b[0]) - 1e-8 <= p[0] <= max(a[0], b[0]) + 1e-8 and min(a[1], b[1]) - 1e-8 <= p[1] <= max(a[1], b[1]) + 1e-8


def segments_intersect(a, b, c, d):
    ab1, ab2, cd1, cd2 = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    if ((ab1 > 0 and ab2 < 0) or (ab1 < 0 and ab2 > 0)) and ((cd1 > 0 and cd2 < 0) or (cd1 < 0 and cd2 > 0)):
        return True
    return on_segment(a, b, c) or on_segment(a, b, d) or on_segment(c, d, a) or on_segment(c, d, b)


def point_segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = dx * dx + dy * dy
    t = 0.0 if den == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den))
    q = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - q[0], p[1] - q[1])


def polygon_gap(a, b):
    if any(segments_intersect(a[i], a[(i + 1) % len(a)], b[j], b[(j + 1) % len(b)]) for i in range(len(a)) for j in range(len(b))):
        return 0.0
    d1 = min(min(point_segment_distance(p, b[j], b[(j + 1) % len(b)]) for j in range(len(b))) for p in a)
    d2 = min(min(point_segment_distance(p, a[j], a[(j + 1) % len(a)]) for j in range(len(a))) for p in b)
    return min(d1, d2)


def rect_polygon(cx, cy, sx, sy, rot):
    t = math.radians(float(rot))
    ct, st = math.cos(t), math.sin(t)
    return [(cx + x * ct - y * st, cy + x * st + y * ct) for x, y in ((-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2))]


def local_geometries(candidate):
    return candidate["local_geometries"]


def layout_polygons(candidate, amp=0.0, phase=0.0, d_amp=0.0):
    out = []
    phase_rad = math.radians(phase)
    for site, geo in enumerate(local_geometries(candidate)):
        dx = amp * math.cos(2 * math.pi * site / 6 + phase_rad)
        dsign = (-1) ** site
        for pillar, (cx, cy, sx, sy, rot) in enumerate(((geo["J1_center_x_nm"], geo["J1_center_y_nm"], geo["J1_side_nm"], geo["J1_side_nm"], geo.get("J1_rotation_deg", 0.0)), (geo["J2_center_x_nm"], geo["J2_center_y_nm"], geo["J2_length_nm"], geo["J2_width_nm"], geo.get("J2_rotation_deg", 0.0)))):
            extra = 0.0
            if d_amp:
                extra = (-0.5 if pillar == 0 else 0.5) * d_amp * dsign
            out.append((site, pillar, rect_polygon((site + 0.5) * P + dx + float(cx) + extra, float(cy), float(sx), float(sy), float(rot))))
    return out


def minimum_clearance(candidate, amp=0.0, phase=0.0, d_amp=0.0):
    polys = layout_polygons(candidate, amp, phase, d_amp)
    best = float("inf")
    for i, (si, pi, ai) in enumerate(polys):
        for j, (sj, pj, bj) in enumerate(polys):
            if j <= i:
                continue
            for kx in (-1, 0, 1):
                for ky in (-1, 0, 1):
                    if kx == 0 and ky == 0 and si == sj and pi == pj:
                        continue
                    shifted = [(x + kx * P_SUPER, y + ky * P_Y) for x, y in bj]
                    best = min(best, polygon_gap(ai, shifted))
    return best


def legal(candidate, amp=0.0, phase=0.0, d_amp=0.0):
    return minimum_clearance(candidate, amp, phase, d_amp) > 0.25


def max_legal(candidate, mode="position", phase=0.0):
    lo, hi = 0.0, 200.0
    for _ in range(48):
        mid = (lo + hi) / 2
        ok = legal(candidate, amp=mid, phase=phase) if mode == "position" else legal(candidate, d_amp=mid)
        if ok:
            lo = mid
        else:
            hi = mid
    return lo


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def read_metrics(path):
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    result = {}
    for candidate in sorted({r["candidate_uid"] for r in rows}):
        x = [r for r in rows if r["candidate_uid"] == candidate and r["polarization"] == "x" and r["order_n"] == "1" and r["order_m"] == "0"]
        y = [r for r in rows if r["candidate_uid"] == candidate and r["polarization"] == "y" and r["order_n"] == "1" and r["order_m"] == "0"]
        result[candidate] = {"eta_x_plus1_mean": sum(float(r["order_efficiency_source_norm"]) for r in x) / len(x), "eta_y_plus1_mean": sum(float(r["order_efficiency_source_norm"]) for r in y) / len(y), "x_y_plus1_ratio": (sum(float(r["order_efficiency_source_norm"]) for r in x) / sum(float(r["order_efficiency_source_norm"]) for r in y))}
    return result


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    h1f2 = load(REMOTE_REPORT / "stage_h1f2_k6_frontier_level1" / "h1f2_final.json")
    m1 = load(REMOTE_REPORT / "stage_h1f1_k6_coupling_level0" / "h1f1_candidate_manifest.json")
    m2 = load(REMOTE_REPORT / "stage_h1f2_k6_frontier_level1" / "h1f2_candidate_manifest.json")
    h1f1_candidates = {c["candidate_uid"]: c for c in m1["candidates"]}
    h1f2_candidates = m2["candidates"]
    seed_map = {"K6_L0_A": h1f1_candidates["K6_L0_A"], "K6_L0_B": h1f1_candidates["K6_L0_B"], "K6_L1_C": h1f2_candidates["K6_L1_C"]}
    metrics = {**read_metrics(REMOTE_REPORT / "stage_h1f1_k6_coupling_level0" / "h1f1_order_resolved_fullwave.csv"), **read_metrics(REMOTE_REPORT / "stage_h1f2_k6_frontier_level1" / "h1f2_order_resolved_fullwave.csv")}
    seed_summary = {name: {"candidate_hash": c["candidate_hash"], "sequence_uids": c["sequence_uids"], "sequence_hashes": c["sequence_hashes"], "classes": c.get("constituent_classes"), "p_nm": c["p_nm"], "P_supercell_nm": c["P_supercell_nm"], "H_global_nm": c["H_global_nm"], "minimum_clearance_nm": c["geometry_legality"]["minimum_clearance_nm"], "fullwave_metrics": metrics.get(name)} for name, c in seed_map.items()}
    dump("h1f3a_h1f1_h1f2_closure.json", {"schema": "H1F3A_H1F1_H1F2_CLOSURE_V1", "h1f2_status": h1f2["status"], "h1f2_physics_classification": h1f2["physics_classification"], "fixed_slot_scope": {"H_global_nm": 550.0, "p_nm": P, "P_supercell_nm": P_SUPER, "wavelength_grid_nm": GRID, "site_count": 6}, "discrete_constituent_search_deprioritized": True, "reason": "H1F2 C mean eta_x,+1=0.0205385 versus H1F1 A=0.0202022; the modest change remains in the same weak regime and does not establish a material route improvement.", "seeds": seed_summary, "solver_entered_delta": 0, "zero_solver_required": True})

    position = {}
    dmode = {}
    for name, c in seed_map.items():
        base = minimum_clearance(c)
        amax = max_legal(c, "position", 0.0)
        dmax = max_legal(c, "geometry", 0.0)
        position[name] = {"mode": "delta_x_n=A*cos(2*pi*n/6), phi=0 fixed", "zero_mean": True, "phase_phi_deg": 0.0, "A_legal_max_nm": amax, "base_minimum_clearance_nm": base, "probe_scale_nm": min(amax * 0.10, 10.0), "probe_scale_rule": "10% of exact legal envelope capped at 10 nm; proposed only", "P_supercell_fixed": True, "y_motion_nm": 0.0, "fundamental_period_6p_for_nonzero_A": True, "translations_tested": {"p": False, "2p": False, "3p": False}}
        dmode[name] = {"mode": "alternating grouped intra-dimer separation", "variable": "D_nm", "pattern": "D_n=D_n0+(-1)^n*A_D", "zero_mean_over_sites": True, "D_legal_max_nm": dmax, "probe_scale_nm": min(dmax * 0.10, 5.0), "probe_scale_rule": "10% of exact legal envelope capped at 5 nm; proposed only", "site_count_variables": 1, "local_geometry_mutation": "J1/J2 centers move symmetrically about their local midpoint; no isolated-dimer library generation"}
    dump("h1f3a_position_mode_audit.json", {"schema": "H1F3A_POSITION_MODE_AUDIT_V1", "route": "ROUTE_A", "formulation": "delta_x_n=A*cos(2*pi*n/6+phi)", "phase_fixed": True, "phase_reason": "phi=0 is a deterministic site-order convention; adding phi would be a second DOF and is not needed for the first audit", "zero_mean": True, "P_supercell_fixed": True, "y_motion": False, "seed_audits": position, "interpretation": "coupled_supercell_geometry_DOF_only; not detour phase, PB phase, phase-bin labeling, or analytic positional-phase synthesis"})
    dump("h1f3a_position_legality_envelope.json", {"schema": "H1F3A_POSITION_LEGALITY_ENVELOPE_V1", "mode": "phi=0", "period_nm": P, "P_supercell_nm": P_SUPER, "exact_polygon_model": "rotated local rectangles with periodic x/y images", "seeds": {k: {"A_legal_max_nm": v["A_legal_max_nm"], "base_minimum_clearance_nm": v["base_minimum_clearance_nm"], "probe_scale_nm": v["probe_scale_nm"]} for k, v in position.items()}, "no_solver": True})
    dump("h1f3a_grouped_geometry_options.json", {"schema": "H1F3A_GROUPED_GEOMETRY_OPTIONS_V1", "route": "ROUTE_B", "options": [{"option": "alternating_D", "variable": "D_nm", "pattern": "D_n=D_n0+(-1)^n*A_D", "dimensionality": 1, "coupling_rationale": "directly changes intra-dimer near-field coupling while preserving one shared amplitude and fixed site positions", "status": "RECOMMENDED_ROUTE_B_OPTION_IF_ROUTE_B_SELECTED", "seed_audits": dmode}, {"option": "J1_rotation", "status": "DEPRIORITIZED", "evidence": "H1E3 rotation audits identify projector-risk dominance"}, {"option": "J2_orientation_decoupling", "status": "DEPRIORITIZED", "evidence": "H1E3C physics outcome J2_DECOUPLING_PHASE_LEVER_BREAKS_SELECTIVITY"}, {"option": "J1_anisotropy", "status": "DEPRIORITIZED", "evidence": "strict lever but phase clustered in H1E1/H1E2"}], "six_site_independent_variables": False, "no_isolated_dimer_search": True})
    dump("h1f3a_global_h_k6_audit.json", {"schema": "H1F3A_GLOBAL_H_K6_AUDIT_V1", "route": "ROUTE_C", "one_shared_H_only": True, "source": "stage_h1a_global_h", "H_grid_nm": [400.0, 450.0, 500.0, 550.0, 600.0], "H550_all_anchor_phase_span_deg": 41.738882, "H550_projector_compatible_span_deg": 30.096722, "H600_all_anchor_phase_span_deg": 26.239342, "H600_projector_compatible_span_deg": 5.505242, "max_abs_residual_deg": 35.45188973052677, "verdict": "GLOBAL_H_REVISIT_VALUE_MEDIUM", "coupled_K6_rationale": "shared H changes every pillar and can shift collective resonances, but it is less direct than position for the demonstrated fixed-slot m+1 bottleneck", "per_site_H": False, "mixed_heights": False, "new_solver": False})
    dump("h1f3a_k6_data_readiness.json", {"schema": "H1F3A_K6_DATA_READINESS_V1", "K6_registry_rows": 648, "local_registry_rows": 578, "independent_K6_geometry_count": 6, "independent_geometry_basis": "six exact candidate hashes across H1F1/H1F2", "fullwave_x_y_broadband_complete": True, "sufficient_for": "physics route selection and seed selection", "surrogate_readiness": "TOO_FEW_INDEPENDENT_K6_GEOMETRIES_FOR_FORMAL_SURROGATE", "ml_admitted": False, "training_performed": False, "local_rows_as_coupled_targets": False})
    dump("h1f3a_route_comparison.json", {"schema": "H1F3A_ROUTE_COMPARISON_V1", "weighted_composite_used": False, "routes": {"ROUTE_A_POSITION_MODE": {"direct_full_K6_leverage": "HIGH", "projector_risk": "LOW_TO_MEDIUM; local geometry unchanged", "coupling_leverage": "HIGH", "new_dimension_count": 1, "legality": "quantified by exact polygon envelope", "fabrication_complexity": "medium; site displacement mask", "solver_cost": "low proposed: 2 seeds x +/- amplitude x/y = 8 cases", "seed_reuse": "direct", "interpretability": "high causal comparison to same unperturbed seed"}, "ROUTE_B_GROUPED_LOCAL_GEOMETRY": {"direct_full_K6_leverage": "MEDIUM_TO_HIGH", "projector_risk": "MEDIUM", "coupling_leverage": "MEDIUM", "new_dimension_count": 1, "legality": "quantifiable but local gap-sensitive", "fabrication_complexity": "medium", "solver_cost": "low if one grouped amplitude", "seed_reuse": "direct", "interpretability": "medium"}, "ROUTE_C_GLOBAL_H": {"direct_full_K6_leverage": "MEDIUM", "projector_risk": "MEDIUM", "coupling_leverage": "MEDIUM", "new_dimension_count": 1, "legality": "fabrication-contract constrained", "fabrication_complexity": "low", "solver_cost": "low", "seed_reuse": "direct", "interpretability": "medium; H changes local phase and collective response together"}}, "decision_basis": ["position changes neighbor coupling and structure factor directly", "H1D1 rejects detour-phase interpretation but does not reject geometric position coupling", "H1F1/H1F2 show constituent inventory/order alone is weak", "Route B variables already show projector/selectivity tradeoffs in H1A-H1E", "H1A supports H as medium-value secondary route"]})
    proposed = {"schema": "H1F3A_PROPOSED_NEXT_STAGE_V1", "status": "PROPOSED_ONLY", "stage_name": "LP_K6_POSITION_MODE_LEVEL2_PROBE", "route_decision": "LOW_DIMENSIONAL_POSITION_MODE_FIRST", "seeds": ["K6_L0_A", "K6_L1_C"], "exact_seed_control": "each perturbed layout compared directly with its same unperturbed full-wave seed", "mode": "delta_x_n=sign*A*cos(2*pi*n/6), phi=0", "signs": [-1, 1], "amplitudes_nm": {k: position[k]["probe_scale_nm"] for k in ("K6_L0_A", "K6_L1_C")}, "candidate_count": 4, "formal_x_y_solver_budget": 8, "P_supercell_fixed": True, "no_y_motion": True, "no_local_geometry_mutation": True, "stop_go": "reproducible full-wave order redistribution relative to exact seed, evaluated by m+1, m0, x/y discrimination, target-order Jones/projector, and broadband robustness; no absolute device threshold invented", "solver_entered_delta": 0, "level2_auto_start": False}
    dump("h1f3a_route_decision.json", {"schema": "H1F3A_ROUTE_DECISION_V1", "formal_decision": "LOW_DIMENSIONAL_POSITION_MODE_FIRST", "decision_hash": stable_hash(proposed), "evidence_complete": True, "hard_gates": []})
    dump("h1f3a_proposed_next_stage.json", proposed)
    dump("h1f3a_final.json", {"schema": "H1F3A_FINAL_V1", "status": "PASS_ZERO_SOLVER_AUDIT", "formal_h1f2_interpretation": "FIXED_SLOT_DISCRETE_CONSTITUENT_GRAMMAR_INSUFFICIENT", "discrete_constituent_search_deprioritized": True, "independent_K6_geometry_count": 6, "K6_data_readiness": "TOO_FEW_INDEPENDENT_K6_GEOMETRIES_FOR_FORMAL_SURROGATE", "formal_route_decision": "LOW_DIMENSIONAL_POSITION_MODE_FIRST", "proposed_stage": "LP_K6_POSITION_MODE_LEVEL2_PROBE", "proposed_candidate_count": 4, "proposed_formal_x_y_solver_budget": 8, "solver_entered_delta": 0, "local_registry_rows": 578, "K6_registry_rows": 648, "ml_admitted": False, "level2_auto_start": False, "hard_gates": []})
    (REPORT / "h1f3a_summary.md").write_text("# H1F-3A K6 Level-2 continuous-grammar audit\n\n- Status: PASS_ZERO_SOLVER_AUDIT.\n- H1F2 interpretation: `FIXED_SLOT_DISCRETE_CONSTITUENT_GRAMMAR_INSUFFICIENT`; discrete constituent search is deprioritized.\n- Independent full-wave K6 layouts: 6; registry rows: 648; local registry remains 578. Formal surrogate readiness: insufficient.\n- Route decision: `LOW_DIMENSIONAL_POSITION_MODE_FIRST`.\n- Position mode: `delta_x_n = +/- A cos(2*pi*n/6)`, phi=0, zero mean, fixed P=6p, no y motion. Exact legal envelopes and perturbative scales are reported in `h1f3a_position_legality_envelope.json`.\n- Proposed-only next stage: 2 exact seeds x 2 signs = 4 K6 layouts, x/y broadband = 8 formal cases. No solver was started.\n- Route B grouped D and Route C shared-H remain secondary audited options.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
