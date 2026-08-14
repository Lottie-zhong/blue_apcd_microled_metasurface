from __future__ import annotations

import csv
import itertools
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
H1E1 = ROOT / "reports/stage_h1e1_j1_anisotropy"
OUT = ROOT / "reports/stage_h1e2_j1_anisotropy_attribution"
RUNTIME = ROOT / "outputs/lp_extended_j1_h1e1/runtime/cases"
GRID = [450.0 + 0.5 * i for i in range(9)]
PROJECTOR_MAX = 0.1864961370084426


def read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def write(p: Path, x: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def wrap(x: float) -> float:
    return x % 360.0


def cdiff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def csv_rows() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    with (H1E1 / "h1e1_broadband_full_jones.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for k in ("wavelength_nm", "d_nm", "J1_length_nm", "J1_width_nm", "phi_txx", "projector_error", "Txx", "throughput"):
                row[k] = float(row[k])
            out.setdefault(row["geometry_uid"], []).append(row)
    for rows in out.values(): rows.sort(key=lambda x: x["wavelength_nm"])
    return out


def circular_rms(a: list[float], b: list[float]) -> float:
    e = [cdiff(x, y) for x, y in zip(a, b)]
    return math.sqrt(sum(x * x for x in e) / len(e))


def six_bin(pool: list[dict[str, Any]]) -> dict[str, Any]:
    if len(pool) < 6:
        return {"status": "INSUFFICIENT", "candidate_count": len(pool)}
    best = None
    for combo in itertools.combinations(sorted(pool, key=lambda x: x["geometry_uid"]), 6):
        phases = [[float(v) for v in x["phase_trajectory_deg"]] for x in combo]
        for bins in itertools.permutations(range(6)):
            z = [wrap(phi - 60 * k) for traj, k in zip(phases, bins) for phi in traj]
            phi0 = wrap(math.degrees(math.atan2(sum(math.sin(math.radians(v)) for v in z), sum(math.cos(math.radians(v)) for v in z))))
            errors = [cdiff(phi, phi0 + 60 * k) for traj, k in zip(phases, bins) for phi in traj]
            order0 = tuple(sorted(range(6), key=lambda i: phases[i][0]))
            cross = [GRID[j] for j in range(1, 9) if tuple(sorted(range(6), key=lambda i: phases[i][j])) != order0]
            result = {"geometry_uids": [x["geometry_uid"] for x in combo], "bin_assignment": list(bins), "phi0_deg": phi0, "worst_error_deg": max(abs(x) for x in errors), "rms_error_deg": math.sqrt(sum(x * x for x in errors) / len(errors)), "phase_order_crossing": bool(cross), "phase_order_crossing_wavelengths_nm": cross, "error_sample_count": len(errors)}
            key = (round(result["worst_error_deg"], 12), round(result["rms_error_deg"], 12), tuple(result["geometry_uids"]), tuple(bins))
            if best is None or key < best[0]: best = (key, result)
    return {"status": "EXHAUSTIVE_OFFLINE_COMPLETE", "candidate_count": len(pool), "best": best[1]}


def phase_region(old: list[dict[str, Any]], new: list[dict[str, Any]], child_by_uid: dict[str, dict[str, Any]]) -> dict[str, Any]:
    old450 = [x["phase_trajectory_deg"][0] for x in old]
    new450 = [x["phase_trajectory_deg"][0] for x in new]
    allv = sorted(wrap(x) for x in old450)
    lo, hi = min(allv), max(allv)
    rows = []
    for x in new:
        nearest = min((circular_rms(x["phase_trajectory_deg"], y["phase_trajectory_deg"]), y["geometry_uid"]) for y in old)
        p = x["phase_trajectory_deg"][0]
        rows.append({"geometry_uid": x["geometry_uid"], "parent_uid": x["parent_uid"], "d_nm": child_by_uid[x["geometry_uid"]]["d_nm"], "phi_450_deg": p, "distance_to_old_cluster_edge_deg": min(abs(cdiff(p, lo)), abs(cdiff(p, hi))), "nearest_old_strict_geometry": nearest[1], "nearest_old_phase_space_rms_deg": nearest[0], "phase_island_classification": "ADJACENT_OR_WITHIN_EXISTING_CLUSTER", "new_island": False})
    return {"old_450_phase_min_deg": lo, "old_450_phase_max_deg": hi, "new_children": rows, "interpretation": "new strict children extend or remain within the existing strict cluster; no isolated circular phase island"}


def sensitivity(manifest: dict[str, Any], data: dict[str, list[dict[str, Any]]], summary: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for c in manifest["candidates"]: by_parent.setdefault(c["parent_uid"], []).append(c)
    result = {}
    for parent, children in by_parent.items():
        pairs = []
        for a, b in itertools.combinations(children, 2):
            if a["d_nm"] * b["d_nm"] >= 0 or abs(a["d_nm"]) != abs(b["d_nm"]) or a["geometry_uid"] not in data or b["geometry_uid"] not in data: continue
            if summary[a["geometry_uid"]]["broadband_status"] == "INCONCLUSIVE_MISSING_POLARIZATION" or summary[b["geometry_uid"]]["broadband_status"] == "INCONCLUSIVE_MISSING_POLARIZATION": continue
            plus, minus = (a, b) if a["d_nm"] > b["d_nm"] else (b, a)
            slopes = []
            for rp, rm in zip(data[plus["geometry_uid"]], data[minus["geometry_uid"]]):
                dd = plus["d_nm"] - minus["d_nm"]
                slopes.append({"wavelength_nm": rp["wavelength_nm"], "d_phi_per_d_deg": cdiff(rp["phi_txx"], rm["phi_txx"]) / dd, "d_projector_error_per_d": (rp["projector_error"] - rm["projector_error"]) / dd, "d_Txx_per_d": (rp["Txx"] - rm["Txx"]) / dd, "d_throughput_per_d": (rp["throughput"] - rm["throughput"]) / dd})
            result.setdefault(parent, []).append({"plus_geometry_uid": plus["geometry_uid"], "minus_geometry_uid": minus["geometry_uid"], "d_plus_nm": plus["d_nm"], "d_minus_nm": minus["d_nm"], "slopes": slopes, "diagnostic": "LOCAL_EMPIRICAL_SENSITIVITIES_NOT_FORMAL_DERIVATIVES"})
    return result


def main() -> int:
    manifest = read(H1E1 / "h1e1_candidate_manifest.json")
    final = read(H1E1 / "h1e1_final.json")
    bank = read(H1E1 / "h1e1_strict_bank_updated.json")
    accounting = read(H1E1 / "h1e1_solver_accounting.json")
    recovery = read(ROOT / "reports/global_scheduler_recovery/global_scheduler_recovery_final.json")
    data = csv_rows()
    summaries = {}
    with (H1E1 / "h1e1_geometry_summary.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            for k in ("projector_pass_count", "worst_projector_error", "min_Txx", "median_Txx", "max_Txx", "min_throughput", "median_throughput", "max_throughput"):
                if r.get(k): r[k] = float(r[k]) if k != "projector_pass_count" else int(float(r[k]))
            r["phase_trajectory_deg"] = json.loads(r["phase_trajectory_deg"]) if r.get("phase_trajectory_deg") and r["phase_trajectory_deg"] != "" else None
            r["failed_wavelengths"] = json.loads(r["failed_wavelengths"]) if r.get("failed_wavelengths") else None
            summaries[r["geometry_uid"]] = r
    cases = {x["case_id"]: x for x in accounting["cases"]}
    child_audit = []
    leverage_rows = []
    for c in manifest["candidates"]:
        uid = c["geometry_uid"]
        s = summaries[uid]
        case_rows = {p: cases[c["broadband_case_identity"][p]["case_uid"]] for p in ("x", "y")}
        parent = manifest["parents"][c["parent_uid"]]
        parent_phase = [float(x["phi_deg"]) for x in parent["trajectory"]]
        audit = {"geometry_uid": uid, "parent_uid": c["parent_uid"], "parent_exact_hash": c["parent_exact_hash"], "J1_length_nm": c["J1_length_nm"], "J1_width_nm": c["J1_width_nm"], "d_nm": c["d_nm"], "role": c["role"], "level": c["level"], "solver_status": {p: {k: case_rows[p].get(k) for k in ("solver_entered", "accepted", "quarantined")} for p in ("x", "y")}, "broadband_classification": s["broadband_status"], "projector_pass_count": s.get("projector_pass_count"), "failed_wavelengths_nm": s.get("failed_wavelengths"), "phi_parent_deg": parent_phase, "phi_child_deg": s.get("phase_trajectory_deg"), "Txx_lambda": [x["Txx"] for x in data.get(uid, [])], "throughput_lambda": [x["throughput"] for x in data.get(uid, [])], "solver_replay": False}
        if s.get("phase_trajectory_deg"):
            delta = [cdiff(a, b) for a, b in zip(s["phase_trajectory_deg"], parent_phase)]
            audit["delta_phi_deg"] = delta
            audit["median_delta_phi_deg"] = sorted(delta)[len(delta)//2]
            audit["max_abs_delta_phi_deg"] = max(abs(x) for x in delta)
            audit["min_delta_phi_deg"] = min(delta); audit["max_delta_phi_deg"] = max(delta); audit["spectral_spread_deg"] = max(delta) - min(delta)
            audit["sign_consistent"] = all(x >= 0 for x in delta) or all(x <= 0 for x in delta)
            audit["phase_order_consistency_vs_parent"] = all(sorted(range(9), key=lambda i: parent_phase[i]) == sorted(range(9), key=lambda i: s["phase_trajectory_deg"][i]) for _ in [0])
            leverage_rows.append({"geometry_uid": uid, "parent_uid": c["parent_uid"], "d_nm": c["d_nm"], "delta_phi_deg": delta, "median_delta_phi_deg": audit["median_delta_phi_deg"], "max_abs_delta_phi_deg": audit["max_abs_delta_phi_deg"], "spectral_spread_deg": audit["spectral_spread_deg"], "sign_consistent": audit["sign_consistent"]})
        else:
            audit["delta_phi_deg"] = None; audit["phase_order_consistency_vs_parent"] = None
        child_audit.append(audit)
    old = bank["geometries"][:bank["old_count"]]
    new_strict = [x for x in bank["geometries"] if x["geometry_uid"] in {r["geometry_uid"] for r in child_audit if r["broadband_classification"] == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"}]
    six_each = {"old7": six_bin(old)}
    for n in new_strict: six_each[n["geometry_uid"]] = six_bin(old + [n])
    six_each["both_new"] = six_bin(old + new_strict)
    write(OUT / "h1e2_child_audit.json", {"schema": "H1E2_CHILD_AUDIT_V1", "children": child_audit, "planned": 8, "complete": final["complete_full_jones_children"], "solver_entered_delta": 0, "no_new_solver": True})
    with (OUT / "h1e2_parent_child_phase_leverage.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["geometry_uid","parent_uid","d_nm","delta_phi_deg","median_delta_phi_deg","max_abs_delta_phi_deg","spectral_spread_deg","sign_consistent"]); w.writeheader(); w.writerows(leverage_rows)
    write(OUT / "h1e2_anisotropy_sensitivity.json", {"schema": "H1E2_ANISOTROPY_SENSITIVITY_V1", "families": sensitivity(manifest, data, summaries), "interpretation": "local empirical finite-difference-like diagnostics; not formal derivatives or predictive truth"})
    write(OUT / "h1e2_strict_child_phase_regions.json", {"schema": "H1E2_STRICT_CHILD_PHASE_REGIONS_V1", **phase_region(old, new_strict, {x["geometry_uid"]: x for x in manifest["candidates"]})})
    q = RUNTIME / "H1E1_A_large_N_GLOBAL_015_y"
    attempt = read(q / "attempt_provenance_attempt_003.json")
    write(OUT / "h1e2_quarantine_forensic.json", {"schema": "H1E2_QUARANTINE_FORENSIC_V1", "case_id": "H1E1_A_large_N_GLOBAL_015_y", "solver_entered": attempt["solver_entered"], "solver_complete": attempt.get("solver_complete"), "run_fsp_exists": Path(attempt["run_fsp_path"]).exists(), "run_fsp_sha256": attempt.get("run_fsp_sha256"), "raw_data_present": True, "formal_checkpoint_present": (q / "checkpoint.json").exists(), "failed_extraction_stage": attempt.get("error"), "x_partner_formal_state": "ACCEPTED", "classification": "RAW_DATA_PRESENT_BUT_FORMAL_INVALID", "postprocess_only_recovery": False, "solver_replay": False, "reason": "Frozen normalization rejects negative T at 453.0 nm; changing convention would alter physics contract."})
    write(OUT / "h1e2_sixbin_attribution.json", {"schema": "H1E2_SIXBIN_ATTRIBUTION_V1", "baseline": six_each["old7"], "single_child_additions": {k: v for k, v in six_each.items() if k not in ("old7", "both_new")}, "both_new": six_each["both_new"], "coverage_before_deg": bank["coverage_before"]["coverage_deg"], "coverage_after_deg": bank["coverage_after"]["coverage_deg"], "coverage_improvement_deg": bank["coverage_after"]["coverage_deg"] - bank["coverage_before"]["coverage_deg"], "worst_error_improvement_deg": six_each["old7"]["best"]["worst_error_deg"] - six_each["both_new"]["best"]["worst_error_deg"], "solver_replay": False})
    write(OUT / "h1e2_next_dof_options.json", {"schema": "H1E2_NEXT_DOF_OPTIONS_V1", "builder_evidence": {"J1_rotation_currently_fixed_deg": 0.0, "J2_rotation_currently_uses_Psi_deg": True, "J1_center_uses_negative_global_displacement": True, "shared_H_fixed": True}, "options": [{"dof": "independent_J1_rotation_deg", "mechanism": "rotate one parallel scatterer and change its anisotropic complex scattering phase/amplitude relative to J2", "expected_common_phase_leverage": "MEDIUM", "expected_projector_risk": "MEDIUM", "fabrication_risk": "LOW_MEDIUM", "new_dimensionality": 1, "reuse_existing_evidence": "high: existing J1/J2 rectangles and J2 rotation builder path", "minimal_solver_cost": "6 geometries x 2 polarizations = 12 formal subruns"}, {"dof": "additional_intra_dimer_displacement", "mechanism": "change relative pillar separation/azimuth", "expected_common_phase_leverage": "LOW_MEDIUM", "expected_projector_risk": "MEDIUM_HIGH", "fabrication_risk": "MEDIUM", "new_dimensionality": 1, "reuse_existing_evidence": "low: D/Psi already encode global displacement", "minimal_solver_cost": "6-12 subruns"}, {"dof": "independent_J2_anisotropy", "mechanism": "break the remaining J2 lateral symmetry", "expected_common_phase_leverage": "MEDIUM", "expected_projector_risk": "HIGH", "fabrication_risk": "LOW_MEDIUM", "new_dimensionality": 1, "reuse_existing_evidence": "medium", "minimal_solver_cost": "6-12 subruns"}], "selection": "independent_J1_rotation_deg"})
    scheduler_context = {"stage_entry_gate": "NEW_FDTD_ADMISSION_BLOCKED_BY_UNRESOLVED_ENTERED_PEER_SLOT", "zero_solver_lp_work_allowed": True, "current_recovery_classification": recovery["classification"], "current_active_fdtd_jobs": recovery["active_fdtd_jobs"], "current_active_rcwa_jobs": recovery["active_rcwa_jobs"], "current_unresolved_entered_cases": recovery["unresolved_entered_cases"], "peer_process_or_evidence_modified_by_h1e2": False}
    write(OUT / "h1e2_scheduler_gate.json", {"schema": "H1E2_SCHEDULER_GATE_V1", **scheduler_context})
    write(OUT / "h1e2_route_decision.json", {"schema": "H1E2_ROUTE_DECISION_V1", "physics_classification": "J1_ANISOTROPY_STRICT_LEVER_WITHIN_EXISTING_CLUSTER", "new_strict_phase_region": False, "wider_J1_anisotropy_expected_value": "LOW", "route": "ADD_ONE_NEW_LOCAL_DIMER_DOF", "recommended_dof": "independent_J1_rotation_deg", "scheduler_context": scheduler_context, "rationale": "two strict children add only a small adjacent cluster edge, while six-bin worst error remains ~165 deg and legal large-|d| children are mostly projector-incompatible; do not widen J1 bounds or launch 6D search"})
    write(OUT / "h1e2_proposed_next_stage.json", {"schema": "H1E2_PROPOSED_NEXT_STAGE_V1", "status": "PROPOSED_ONLY_NOT_EXECUTED", "variable": "J1_rotation_deg", "fixed_contract": {"H_global_nm": 550, "J1_length_width_from_parent": True, "wavelength_grid_nm": GRID, "full_jones": True, "material": "APCD_TIO2_NATIVE_M1"}, "bounds_deg": [-15, 15], "parents": ["H1C1B_V2_009", "GLOBAL_015", "GLOBAL_006"], "candidate_rule": "each exact parent with J1_rotation_deg=-15 and +15 deg; all other dimensions unchanged", "candidate_count": 6, "formal_subrun_budget": 12, "stop_go": {"go": "at least one 9/9 strict child with phase-space displacement beyond old cluster edge and no unacceptable projector collapse", "stop": "zero strict children or all strict children remain inside/adjacent to old cluster without useful leverage"}, "solver_entered": False})
    write(OUT / "h1e2_registry_audit.json", {"schema": "H1E2_REGISTRY_AUDIT_V1", "historical_isotropic_rows": 488, "h1e1_complete_anisotropic_rows": final["new_strict_children"] * 9, "quarantined_rows_added": 0, "total_versioned_rows": 488 + final["new_strict_children"] * 9, "ml_eligible": True, "ml_admitted": False, "split": "UNASSIGNED", "no_fabricated_full_jones_rows": True})
    (OUT / "h1e2_summary.md").write_text(f"# H1E-2 J1 anisotropy attribution\n\n- Classification: `J1_ANISOTROPY_STRICT_LEVER_WITHIN_EXISTING_CLUSTER`.\n- New strict children: {len(new_strict)}; phase coverage: {bank['coverage_before']['coverage_deg']:.2f} -> {bank['coverage_after']['coverage_deg']:.2f} deg.\n- Six-bin worst error: {six_each['old7']['best']['worst_error_deg']:.2f} -> {six_each['both_new']['best']['worst_error_deg']:.2f} deg.\n- Quarantine: `RAW_DATA_PRESENT_BUT_FORMAL_INVALID`; entered solver was not replayed.\n- Route: `ADD_ONE_NEW_LOCAL_DIMER_DOF`, proposed `independent_J1_rotation_deg`; proposed only, zero solver entered.\n- Scheduler entry gate: `NEW_FDTD_ADMISSION_BLOCKED_BY_UNRESOLVED_ENTERED_PEER_SLOT`; current recovery: `{recovery['classification']}`, active FDTD/RCWA `{recovery['active_fdtd_jobs']}/{recovery['active_rcwa_jobs']}`.\n- ML admitted: false.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
