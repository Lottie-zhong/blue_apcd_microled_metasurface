from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
H1E1 = ROOT / "reports/stage_h1e1_j1_anisotropy"
H1E2 = ROOT / "reports/stage_h1e2_j1_anisotropy_attribution"
OUT = ROOT / "reports/stage_h1e3a_j1_rotation_audit"
GRID = [450.0 + 0.5 * i for i in range(9)]


def read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def write(p: Path, x: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def cabs(re: float, im: float) -> float:
    return math.hypot(float(re), float(im))


def read_jones() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    with (H1E1 / "h1e1_broadband_full_jones.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            for k in ("wavelength_nm", "Re_txx", "Im_txx", "Re_txy", "Im_txy", "Re_tyx", "Im_tyx", "Re_tyy", "Im_tyy", "projector_error", "Txx", "throughput"):
                r[k] = float(r[k])
            out.setdefault(r["geometry_uid"], []).append(r)
    for rows in out.values(): rows.sort(key=lambda x: x["wavelength_nm"])
    return out


def rotated(a: complex, b: complex, theta_rad: float) -> list[list[complex]]:
    c, s = math.cos(theta_rad), math.sin(theta_rad)
    return [[a*c*c + b*s*s, (a-b)*s*c], [(a-b)*s*c, a*s*s + b*c*c]]


def jones_checks() -> dict[str, Any]:
    a, b = 1.7 + 0.2j, 0.6 - 0.1j
    eps = 1e-7
    j0 = rotated(a, b, 0.0)
    jp = rotated(a, b, eps); jm = rotated(a, b, -eps)
    dxx = (jp[0][0] - jm[0][0]) / (2*eps)
    dxy = (jp[0][1] - jm[0][1]) / (2*eps)
    return {"identity_at_zero": [[j0[0][0] == a, j0[0][1] == 0], [j0[1][0] == 0, j0[1][1] == b]], "analytic_Jxx": "a cos^2(theta)+b sin^2(theta)", "analytic_Jxy": "(a-b) sin(theta) cos(theta)", "analytic_Jyx": "(a-b) sin(theta) cos(theta)", "analytic_Jyy": "a sin^2(theta)+b cos^2(theta)", "dJxx_dtheta_at_zero": "0", "dJxy_dtheta_at_zero": "a-b", "finite_difference_dJxx": [dxx.real, dxx.imag], "finite_difference_dJxy": [dxy.real, dxy.imag], "derivative_check": abs(dxx) < 1e-12 and abs(dxy - (a-b)) < 1e-8}


def main() -> int:
    manifest = read(H1E1 / "h1e1_candidate_manifest.json")
    oldbank = read(ROOT / "reports/stage_h1e3a_j1_rotation_audit/oldbank.json") if (ROOT / "reports/stage_h1e3a_j1_rotation_audit/oldbank.json").exists() else None
    if oldbank is None:
        oldbank = read(ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json")
    h1e2_options = read(H1E2 / "h1e2_next_dof_options.json")
    data = read_jones()
    by_old = {x["geometry_uid"]: x for x in oldbank["geometries"]}
    source = ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py"
    write(OUT / "h1e3a_geometry_semantics.json", {"schema": "H1E3A_GEOMETRY_SEMANTICS_V1", "source": str(source), "source_provenance": {"bounds": "lines 34-40", "Psi_to_centers": "lines 265-266 and 301-302", "geometry_identity": "lines 154-162", "Lumerical_build": "lines 454-457"}, "Psi_semantics": "coupled displacement azimuth and J2 local rotation parameter", "displacement": {"cx_nm": "D*cos(Psi)/2 with half-grid rounding", "cy_nm": "D*sin(Psi)/2 with half-grid rounding", "pillar_centers": "J1=(-cx,-cy), J2=(cx,cy)"}, "current_orientations": {"J1_rotation_deg": 0.0, "J2_rotation_deg": "Psi_deg", "whole_dimer_transform": False}, "Lumerical_rotation_1": {"code_value": "J1=0; J2=Psi", "sign_convention": "positive value passed directly; Ansys documentation describes ROTATION 1 as clockwise about the axis", "source": "https://optics.ansys.com/hc/en-us/articles/360034382434-Structure-Groups-Simulation-object"}, "independent_J1_rotation": {"independent_of_Psi": True, "independent_of_D": True, "independent_of_J2_rotation": True, "independent_of_whole_dimer_transform": True, "reason": "it changes only pillar_1 rotation while centers and pillar_2 rotation remain unchanged"}, "duplicate_dof": False})
    (OUT / "h1e3a_rotation_jones_derivation.md").write_text("# Rotated anisotropic J1 Jones model\n\nFor `J1(theta)=R(theta) diag(a,b) R(-theta)` with `R=[[cos,-sin],[sin,cos]]`,\n\n- `Jxx = a cos^2(theta) + b sin^2(theta)`\n- `Jxy = Jyx = (a-b) sin(theta) cos(theta)`\n- `Jyy = a sin^2(theta) + b cos^2(theta)`\n\nAt theta=0:\n\n- `dJxx/dtheta = 0`\n- `dJxy/dtheta = dJyx/dtheta = a-b`\n- `dJyy/dtheta = 0`\n\nTherefore a non-isotropic J1 rotation is first-order projector-basis mixing, while its diagonal common-phase response starts at second order. It is not assumed to be a PB/geometric phase knob. The response becomes dependent on near-isotropy only when `a-b` is itself small; near an anisotropic resonance, cross-polarization risk can dominate.\n", encoding="utf-8")
    write(OUT / "h1e3a_rotation_jones_checks.json", {"schema": "H1E3A_ROTATION_JONES_CHECKS_V1", **jones_checks()})
    child_rows = {x["geometry_uid"]: x for x in manifest["candidates"]}
    risk = []
    for uid, rows in data.items():
        c = child_rows.get(uid)
        if not c: continue
        l, w = float(c["J1_length_nm"]), float(c["J1_width_nm"])
        eta = abs(l-w)/(l+w)
        max_cross = max(max(cabs(r["Re_txy"],r["Im_txy"]), cabs(r["Re_tyx"],r["Im_tyx"])) for r in rows)
        max_ratio = max(max(cabs(r["Re_txy"],r["Im_txy"]), cabs(r["Re_tyx"],r["Im_tyx"])) / max(cabs(r["Re_txx"],r["Im_txx"]), 1e-12) for r in rows)
        risk.append({"geometry_uid": uid, "parent_uid": c["parent_uid"], "d_nm": c["d_nm"], "geometry_anisotropy_proxy_abs_L_minus_W_over_sum": eta, "max_full_dimer_cross_term_abs": max_cross, "max_cross_to_txx_abs_ratio": max_ratio, "projector_error_max": max(r["projector_error"] for r in rows), "rotation_risk_proxy_at_2deg": eta*math.radians(2), "rotation_risk_proxy_at_5deg": eta*math.radians(5), "rotation_risk_proxy_at_10deg": eta*math.radians(10), "rotation_risk_proxy_at_15deg": eta*math.radians(15), "interpretation": "geometry-level first-order tendency only; not constituent a-b and not a full-dimer prediction"})
    write(OUT / "h1e3a_rotation_projector_risk.json", {"schema": "H1E3A_ROTATION_PROJECTOR_RISK_V1", "metric": "|L-W|/(L+W) times |theta| as a geometry-only proxy for |a-b|*theta", "rows": risk, "diagnosis": "PROJECTOR_MIXING_DOMINANT_FIRST_ORDER; common-phase is not first-order", "fixed_projector": [[1,0],[0,0]], "pb_phase_assumption": False})
    stability = []
    for r in risk:
        uid = r["geometry_uid"]
        if uid not in data: continue
        phases = [float(x["phi_txx"]) for x in data[uid]]
        stability.append({"geometry_uid": uid, "parent_uid": r["parent_uid"], "d_nm": r["d_nm"], "phase_range_unwrapped_deg": max(phases)-min(phases), "max_cross_to_txx_abs_ratio": r["max_cross_to_txx_abs_ratio"], "projector_error_max": r["projector_error_max"], "spectral_risk_rank_key": [r["max_cross_to_txx_abs_ratio"], max(phases)-min(phases), r["projector_error_max"]]})
    stability.sort(key=lambda x: tuple(x["spectral_risk_rank_key"]), reverse=True)
    write(OUT / "h1e3a_parent_spectral_risk.json", {"schema": "H1E3A_PARENT_SPECTRAL_RISK_V1", "ranked_complete_h1e1_children": stability, "special_warning": {"geometry_uid": "H1E1_A_small_N_GLOBAL_015", "delta_phi_spectral_spread_deg": 91.42365814184984, "do_not_select_automatically": True}, "strict_children": [x for x in stability if x["geometry_uid"] in {"H1E1_A_small_N_GLOBAL_015","H1E1_C_large_P_GLOBAL_006"}]})
    alternatives = [{"dof": "independent_J1_rotation_deg", "implemented_now": False, "duplicate_with_Psi_D": False, "common_phase_leverage": "LOW_TO_MEDIUM", "projector_risk": "HIGH_FIRST_ORDER", "spectral_risk": "HIGH_ON_A_SMALL_N; UNKNOWN_ELSEWHERE", "decision": "reject as first next probe"}, {"dof": "independent_J2_orientation", "implemented_now": False, "duplicate_with_Psi": True, "common_phase_leverage": "not separately identifiable", "projector_risk": "not separable from current Psi", "decision": "reject as duplicate"}, {"dof": "additional_intra_dimer_displacement_component", "implemented_now": False, "duplicate_with_Psi_D": True, "common_phase_leverage": "not a new coordinate under current (D,Psi) polar representation", "projector_risk": "unknown", "decision": "reject as duplicate"}, {"dof": "independent_J2_anisotropy_d_nm", "implemented_now": True, "builder_support": "J2_length_nm and J2_width_nm are separate geometry fields and are used independently by addrect", "common_phase_leverage": "MEDIUM plausible because J2 is HWP-like contributor", "projector_risk": "MEDIUM_HIGH", "spectral_risk": "requires minimal probe", "decision": "preferred alternative"}]
    write(OUT / "h1e3a_next_dof_comparison.json", {"schema": "H1E3A_NEXT_DOF_COMPARISON_V1", "options": alternatives, "selection_rule": "prefer plausible common-phase leverage while avoiding first-order projector mixing, duplicated coordinates, and known spectral instability", "selected": "independent_J2_anisotropy_d_nm"})
    angle_rows = []
    for a in (2,5,10,15):
        angle_rows.append({"angle_set_deg": [-a,a], "max_geometry_proxy_A_small_abs": 0.01834862385321101*math.radians(a), "max_geometry_proxy_C_large_abs": 0.008849557522123894*math.radians(a), "assessment": "smallest meaningful first probe" if a == 2 else "candidate scale"})
    write(OUT / "h1e3a_angle_range_review.json", {"schema": "H1E3A_ANGLE_RANGE_REVIEW_V1", "candidate_sets": angle_rows, "recommended_J1_rotation_first_scale_deg": [-2,2], "fifteen_degree_justified": False, "reason": "rotation is first-order cross-polarization mixing under fixed Px; H1E1 strict A child already has 91.424 deg phase spectral spread and weak projector margin"})
    selected = []
    for uid in ("H1C1B_V2_009","GLOBAL_015","GLOBAL_006"):
        p = by_old[uid]; c = p["coordinates_5d"]; mean=(float(c["J2_length_nm"])+float(c["J2_width_nm"]))/2
        selected.append({"geometry_uid": uid, "exact_hash": p["exact_hash"], "coordinates_5d": c, "strict_9_of_9": len(p["trajectory"]) == 9, "worst_projector_error": p["worst_projector_error"], "minimum_projector_margin": p["minimum_projector_margin"], "J2_mean_nm": mean, "proposed_d2_nm": [-1,1]})
    variants=[]
    for p in selected:
        c=p["coordinates_5d"]
        for d2 in (-1,1): variants.append({"parent_uid":p["geometry_uid"],"d2_nm":d2,"J2_length_nm":int(float(c["J2_length_nm"])+d2),"J2_width_nm":int(float(c["J2_width_nm"])-d2),"J1_side_nm":int(float(c["J1_side_nm"])),"D_nm":c["D_nm"],"Psi_deg":c["Psi_deg"],"bounds_pass":100 <= int(float(c["J2_length_nm"])+d2) <= 114 and 94 <= int(float(c["J2_width_nm"])-d2) <= 106})
    write(OUT / "h1e3a_proposed_next_stage.json", {"schema":"LP_J2_ANISOTROPY_BROADBAND_PROBE_PROPOSED_V1","status":"PROPOSED_ONLY_NOT_EXECUTED","variable":"J2_anisotropy_d_nm","parameterization":"J2_length=L2_mean+d2; J2_width=L2_mean-d2","parents":selected,"variants":variants,"candidate_count":6,"formal_subrun_budget":12,"fixed_contract":{"H_global_nm":550,"grid_nm":GRID,"full_jones":True,"projector":[[1,0],[0,0]],"material":"APCD_TIO2_NATIVE_M1"},"stop_go":{"go":"at least one 9/9 strict child with phase displacement beyond old cluster and preserved projector margin","stop":"zero strict children or projector degradation dominates without new strict phase reachability"},"solver_entered":False})
    write(OUT / "h1e3a_route_decision.json", {"schema":"H1E3A_ROUTE_DECISION_V1","j1_rotation_classification":"J1_ROTATION_PROJECTOR_RISK_DOMINANT","recommended_next_dof":"independent_J2_anisotropy_d_nm","j1_rotation_independent":True,"j1_rotation_common_phase_lever":False,"j1_rotation_probe_approved":False,"reason":"rotated anisotropic J1 has zero first-order diagonal response but nonzero first-order off-diagonal response a-b; current target is fixed Px and H1E1 shows spectral/projector risk","registry_rows":506,"ml_admitted":False,"solver_entered_delta":0})
    (OUT / "h1e3a_summary.md").write_text("# H1E-3A J1 rotation audit\n\n- Psi is a coupled displacement azimuth and J2 rotation parameter; it is not a whole-dimer rotation.\n- J1 rotation is implementation-independent of Psi/D/J2 orientation, but its analytic first-order response is off-diagonal Jones mixing: dJxx/dtheta=0 and dJxy/dtheta=a-b at theta=0.\n- Rotation classification: `J1_ROTATION_PROJECTOR_RISK_DOMINANT`; +/-15 deg is not justified.\n- Recommended first J1 angle scale if ever revisited: +/-2 deg, but no J1 rotation probe is approved here.\n- Preferred alternative: `independent_J2_anisotropy_d_nm`, proposed only as 6 geometries / 12 subruns.\n- Registry remains 506 rows; ML remains not admitted; solver_entered_delta=0.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
