from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1")
REPORT = ROOT / "reports/stage_h1f3b_k6_position_mode_level2"
H1F1 = ROOT / "reports/stage_h1f1_k6_coupling_level0"
H1F2 = ROOT / "reports/stage_h1f2_k6_frontier_level1"
P = 431.907786
P_SUPER = 2591.446716
P_Y = 432.0
H = 550.0
GRID = [450.0 + 0.5 * i for i in range(9)]
AMP = 10.0


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(name: str, value):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def candidates(manifest):
    value = manifest["candidates"]
    return list(value.values()) if isinstance(value, dict) else value


def rect(cx, cy, sx, sy, rot):
    t = math.radians(float(rot))
    ct, st = math.cos(t), math.sin(t)
    return [(cx + x * ct - y * st, cy + x * st + y * ct) for x, y in ((-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2))]


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a, b, p):
    return abs(cross(a, b, p)) < 1e-8 and min(a[0], b[0]) - 1e-8 <= p[0] <= max(a[0], b[0]) + 1e-8 and min(a[1], b[1]) - 1e-8 <= p[1] <= max(a[1], b[1]) + 1e-8


def intersects(a, b, c, d):
    ab1, ab2, cd1, cd2 = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    if ((ab1 > 0 > ab2) or (ab1 < 0 < ab2)) and ((cd1 > 0 > cd2) or (cd1 < 0 < cd2)):
        return True
    return on_segment(a, b, c) or on_segment(a, b, d) or on_segment(c, d, a) or on_segment(c, d, b)


def point_segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = dx * dx + dy * dy
    t = 0.0 if den == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den))
    q = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - q[0], p[1] - q[1])


def polygon_gap(a, b):
    if any(intersects(a[i], a[(i + 1) % len(a)], b[j], b[(j + 1) % len(b)]) for i in range(len(a)) for j in range(len(b))):
        return 0.0
    return min(min(point_segment_distance(p, b[j], b[(j + 1) % len(b)]) for j in range(len(b))) for p in a) if a else 0.0


def polygons(candidate, amp):
    out = []
    for site, (geo, pos) in enumerate(zip(candidate["local_geometries"], candidate["site_positions_nm"])):
        dx = amp * math.cos(2 * math.pi * site / 6)
        xbase = float(pos["x_nm"]) + dx - P_SUPER / 2.0
        for pillar, (cx, cy, sx, sy, rot) in enumerate(((geo["J1_center_x_nm"], geo["J1_center_y_nm"], geo["J1_side_nm"], geo["J1_side_nm"], geo.get("J1_rotation_deg", 0.0)), (geo["J2_center_x_nm"], geo["J2_center_y_nm"], geo["J2_length_nm"], geo["J2_width_nm"], geo.get("J2_rotation_deg", 0.0)))):
            out.append((site, pillar, rect(xbase + float(cx), float(pos["y_nm"]) + float(cy), float(sx), float(sy), float(rot))))
    return out


def minimum_clearance(candidate, amp):
    polys = polygons(candidate, amp)
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
                    best = min(best, polygon_gap(ai, shifted), polygon_gap(shifted, ai))
    return best


def physical_payload(candidate):
    return {
        "H_global_nm": candidate["H_global_nm"],
        "P_supercell_nm": candidate["P_supercell_nm"],
        "P_y_nm": candidate["P_y_nm"],
        "material": candidate.get("material", "APCD_TIO2_NATIVE_M1"),
        "local_geometries": candidate["local_geometries"],
        "site_positions_nm": candidate["site_positions_nm"],
    }


def cyclic_payload(candidate, shift):
    rows = []
    for i, (geo, pos) in enumerate(zip(candidate["local_geometries"], candidate["site_positions_nm"])):
        x = (float(pos["x_nm"]) + shift * P) % P_SUPER
        rows.append({"geo": geo, "x_nm": round(x, 12), "y_nm": float(pos["y_nm"])})
    return {"H_global_nm": candidate["H_global_nm"], "P_supercell_nm": P_SUPER, "P_y_nm": P_Y, "rows": sorted(rows, key=lambda r: (r["x_nm"], canonical(r["geo"]))) }


def make_candidate(seed, seed_label, sign):
    amp = float(sign) * AMP
    c = json.loads(json.dumps(seed))
    c["candidate_uid"] = f"{seed_label}_POS_{'PLUS' if sign > 0 else 'MINUS'}10"
    c["base_candidate_uid"] = seed["candidate_uid"]
    c["base_candidate_hash"] = seed["candidate_hash"]
    c["base_site_positions_nm"] = json.loads(json.dumps(seed["site_positions_nm"]))
    c["position_mode"] = "delta_x_n=A*cos(2*pi*n/6), phi=0"
    c["A_nm"] = amp
    c["site_positions_nm"] = [{**pos, "x_nm": float(pos["x_nm"]) + amp * math.cos(2 * math.pi * i / 6)} for i, pos in enumerate(seed["site_positions_nm"])]
    payload = physical_payload(c)
    c["candidate_hash"] = sha(payload)
    c["physical_canonical_hash"] = c["candidate_hash"]
    c["solver_case_uids"] = [f"H1F3B_{c['candidate_uid']}_{pol}" for pol in ("x", "y")]
    return c


def main():
    m1 = load(H1F1 / "h1f1_candidate_manifest.json")
    m2 = load(H1F2 / "h1f2_candidate_manifest.json")
    c1 = {c["candidate_uid"]: c for c in candidates(m1)}
    c2 = m2["candidates"]
    seed_a, seed_b = c1["K6_L0_A"], c2["K6_L1_C"]
    seeds = {"K6_L0_A": seed_a, "K6_L1_C": seed_b}
    layouts = [make_candidate(seed, label, sign) for label, seed in seeds.items() for sign in (1, -1)]
    by_uid = {c["candidate_uid"]: c for c in layouts}
    seed_selection = {
        "schema": "H1F3B_SEED_SELECTION_V1",
        "fallback_used": False,
        "selected_seeds": [{"seed_uid": s["candidate_uid"], "candidate_hash": s["candidate_hash"], "source_manifest": str(H1F1 / "h1f1_candidate_manifest.json" if s is seed_a else H1F2 / "h1f2_candidate_manifest.json"), "sequence_uids": s["sequence_uids"], "sequence_hashes": s["sequence_hashes"], "original_site_positions_nm": s["site_positions_nm"], "ordered_local_geometries": s["local_geometries"], "fullwave_evidence": str(H1F1 / "h1f1_final.json" if s is seed_a else H1F2 / "h1f2_final.json")} for s in (seed_a, seed_b)],
        "fallback_rule": "use K6_L0_B only if K6_L1_C +/-10 are physically cyclic-equivalent",
        "fallback_audit": {"K6_L1_C_plus_minus_cyclic_equivalent": False, "reason": "exact canonical cyclic audit below"},
    }
    equivalence = {"schema": "H1F3B_PHYSICAL_EQUIVALENCE_AUDIT_V1", "ignore_fields": ["case_uid", "metadata", "position_mode", "A_nm"], "seeds": {}}
    for label, seed in seeds.items():
        base_hash = sha(physical_payload(seed))
        plus, minus = by_uid[f"{label}_POS_PLUS10"], by_uid[f"{label}_POS_MINUS10"]
        cyclic = {"plus_vs_minus": [], "plus_vs_base": [], "minus_vs_base": []}
        for shift in range(6):
            shifted_plus = sha(cyclic_payload(plus, shift)); shifted_minus = sha(cyclic_payload(minus, shift)); shifted_base = sha(cyclic_payload(seed, shift))
            cyclic["plus_vs_minus"].append(shifted_plus == sha(cyclic_payload(minus, 0)))
            cyclic["plus_vs_base"].append(shifted_plus == sha(cyclic_payload(seed, 0)))
            cyclic["minus_vs_base"].append(shifted_minus == sha(cyclic_payload(seed, 0)))
        equivalence["seeds"][label] = {"base_hash": base_hash, "plus_hash": plus["physical_canonical_hash"], "minus_hash": minus["physical_canonical_hash"], "all_three_distinct": len({base_hash, plus["physical_canonical_hash"], minus["physical_canonical_hash"]}) == 3, "cyclic_equivalence": cyclic, "cyclic_redundancy_detected": any(cyclic["plus_vs_minus"] + cyclic["plus_vs_base"] + cyclic["minus_vs_base"])}
    if equivalence["seeds"]["K6_L1_C"]["cyclic_redundancy_detected"]:
        raise RuntimeError("HARD_GATE_SEED_B_CYCLIC_REDUNDANCY")
    legality = {"schema": "H1F3B_GEOMETRY_LEGALITY_V1", "period": {"p_nm": P, "P_supercell_nm": P_SUPER, "P_y_nm": P_Y, "fundamental_period_6P": True, "translations_p_2p_3p_equal": False}, "layouts": {}}
    for c in layouts:
        clearance = minimum_clearance(c, 0.0)
        base_clearance = minimum_clearance(seeds[c["base_candidate_uid"]], 0.0)
        legality["layouts"][c["candidate_uid"]] = {"candidate_hash": c["candidate_hash"], "A_nm": c["A_nm"], "minimum_clearance_nm": clearance, "base_minimum_clearance_nm": base_clearance, "no_overlap": clearance > 0.25, "no_y_motion": all(float(a["y_nm"]) == float(b["y_nm"]) for a, b in zip(c["site_positions_nm"], seeds[c["base_candidate_uid"]]["site_positions_nm"])), "P_unchanged": c["P_supercell_nm"] == P_SUPER, "H_unchanged": c["H_global_nm"] == H, "native_material": all(g.get("material_contract") == "APCD_TIO2_NATIVE_M1" for g in c["local_geometries"]), "local_geometry_unchanged": c["local_geometries"] == seeds[c["base_candidate_uid"]]["local_geometries"], "pass": clearance > 0.25}
    if not all(x["pass"] for x in legality["layouts"].values()):
        raise RuntimeError("HARD_GATE_ILLEGAL_POSITION_LAYOUT")
    freeze_payload = {"seeds": seed_selection, "layouts": layouts, "legality": legality, "mode": {"formula": "delta_x_n=A*cos(2*pi*n/6)", "phi_deg": 0.0, "amplitudes_nm": [-10.0, 10.0], "zero_mean": True, "no_y_motion": True}, "solver_plan": {"new_layouts": 4, "formal_cases": 8, "processes": 4, "threads": 1, "polarizations": ["x", "y"], "wavelength_grid_nm": GRID, "sequential_within_lp": True, "max_active_fdtd_per_branch": 1, "global_max_active_fdtd": 2, "ml_admitted": False}}
    freeze_hash = sha(freeze_payload)
    manifest = {"schema": "H1F3B_CANDIDATE_MANIFEST_V1", "status": "FROZEN_READY_FOR_SOLVER", "branch": "work/lp-global-h-manifold-v1", "worktree": str(ROOT), "freeze_sha256": freeze_hash, "candidate_count": 4, "max_new_formal_cases": 8, "processes": 4, "threads": 1, "wavelength_grid_nm": GRID, "ml_admitted": False, "p_nm": P, "P_supercell_nm": P_SUPER, "P_y_nm": P_Y, "H_global_nm": H, "fundamental_period_6P": True, "position_mode": {"formula": "delta_x_n=A*cos(2*pi*n/6)", "phi_deg": 0.0, "zero_mean": True, "A_nm": [-10.0, 10.0]}, "selected_seeds": seed_selection["selected_seeds"], "candidates": layouts, "baseline_references": {"K6_L0_A": str(H1F1 / "h1f1_order_resolved_fullwave.csv"), "K6_L1_C": str(H1F2 / "h1f2_order_resolved_fullwave.csv")}, "legality": legality, "physical_equivalence_audit": equivalence, "solver_plan": freeze_payload["solver_plan"]}
    accounting = {"schema": "H1F3B_SOLVER_ACCOUNTING_V1", "planned_formal_cases": 8, "entered_formal_cases": 0, "accepted_formal_cases": 0, "quarantine_cases": 0, "replay_cases": 0, "max_global_active_fdtd_jobs": 2, "max_lp_active_fdtd_jobs": 1, "processes_per_case": 4, "threads_per_case": 1, "ml_admitted": False, "cases": []}
    dump("h1f3b_seed_selection.json", seed_selection)
    dump("h1f3b_candidate_manifest.json", manifest)
    dump("h1f3b_physical_equivalence_audit.json", equivalence)
    dump("h1f3b_geometry_legality.json", legality)
    dump("h1f3b_solver_accounting.json", accounting)
    print(json.dumps({"freeze_sha256": freeze_hash, "candidate_uids": list(by_uid), "legality": legality, "equivalence": equivalence}, indent=2))


if __name__ == "__main__":
    main()
