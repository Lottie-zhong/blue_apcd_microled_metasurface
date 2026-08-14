from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/stage_h1e3b_j2_decoupling_audit"
REPO = ROOT
H1E1 = ROOT / "reports/stage_h1e1_j1_anisotropy"
OLD = ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json"
GRID = [450.0 + 0.5 * i for i in range(9)]


def read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write(p: Path, x: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def valid_j2(row: dict[str, Any]) -> bool:
    try:
        return 100 <= float(row["J2_length_nm"]) <= 114 and 94 <= float(row["J2_width_nm"]) <= 106
    except Exception:
        return False


def json_rows(path: Path) -> list[dict[str, Any]]:
    def walk(x):
        if isinstance(x, dict):
            if "J2_length_nm" in x and "J2_width_nm" in x and valid_j2(x): yield x
            for v in x.values(): yield from walk(v)
        elif isinstance(x, list):
            for v in x: yield from walk(v)
    return list(walk(read(path)))


def csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if valid_j2(r)]


def coverage(rows: list[dict[str, Any]], status_filter=None) -> dict[str, Any]:
    if status_filter: rows = [r for r in rows if r.get("broadband_status") in status_filter]
    L = [float(r["J2_length_nm"]) for r in rows]; W = [float(r["J2_width_nm"]) for r in rows]
    delta = [a-b for a,b in zip(L,W)]; mean = [(a+b)/2 for a,b in zip(L,W)]
    return {"records": len(rows), "J2_L_range_nm": [min(L),max(L)] if L else None, "J2_W_range_nm": [min(W),max(W)] if W else None, "J2_L_minus_J2_W_range_nm": [min(delta),max(delta)] if delta else None, "J2_mean_range_nm": [min(mean),max(mean)] if mean else None, "unique_J2_L": len(set(L)), "unique_J2_W": len(set(W)), "unique_delta": len(set(delta)), "unique_mean": len(set(mean)), "nonzero_delta_records": sum(d != 0 for d in delta), "positive_delta_records": sum(d > 0 for d in delta), "negative_delta_records": sum(d < 0 for d in delta)}


def jones_derivation() -> dict[str, Any]:
    return {"model": "J2(theta)=R(theta) diag(a,b) R(-theta)", "Jxx": "a*cos(theta)^2+b*sin(theta)^2", "Jxy": "(a-b)*sin(theta)*cos(theta)", "Jyx": "(a-b)*sin(theta)*cos(theta)", "Jyy": "a*sin(theta)^2+b*cos(theta)^2", "at_theta_equals_Psi": {"dJxx_d_delta_theta": "(b-a)*sin(2*Psi)", "dJxy_d_delta_theta": "(a-b)*cos(2*Psi)", "dJyx_d_delta_theta": "(a-b)*cos(2*Psi)", "dJyy_d_delta_theta": "(a-b)*sin(2*Psi)"}, "interpretation": "near the LP Psi range of roughly +/-3 degrees, delta_theta primarily changes the J2 off-diagonal/eigenaxis response; it is a projector-selection or compensation lever, not an assumed scalar phase knob"}


def main() -> int:
    canonical = csv_rows(ROOT / "reports/stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv")
    h1c1a = json_rows(ROOT / "reports/stage_h1c1a_broadband_global/lp_hf_authoritative_label_registry_v1.json")
    h1c1b = json_rows(ROOT / "reports/stage_h1c1b_broadband_adaptive/h1c1b_authoritative_label_registry_v1.json")
    h500 = read(ROOT / "reports/stage11_3b4_lp_h500_case_manifest.json")["cases"]
    manifest = read(H1E1 / "h1e1_candidate_manifest.json")
    old = read(OLD)["geometries"]
    write(OUT / "h1e3b_historical_grammar_audit.json", {"schema":"H1E3B_HISTORICAL_GRAMMAR_AUDIT_V1","authoritative_sources":["reports/stage11_3b4_lp_h500_case_manifest.json","reports/stage_h1c1a_broadband_global/lp_hf_authoritative_label_registry_v1.json","reports/stage_h1c1b_broadband_adaptive/h1c1b_authoritative_label_registry_v1.json","reports/stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv","scripts/lp_global_h_h1c1a_broadband_v1.py"],"old_lp_variables":["J1_side_nm","J2_length_nm","J2_width_nm","D_nm","Psi_deg","H_global_nm"],"J2_length_width_independently_assignable":True,"J2_ANISOTROPY_ALREADY_EXISTING_DOF":True,"H550_canonical_registry_rows":len(canonical),"H500_manifest_cases":len(h500),"H500_J2_fields":"j2_length_nm and j2_width_nm independently present; legacy H500 layout is not merged into H550 registry"})
    h500L=[float(x["j2_length_nm"]) for x in h500]; h500W=[float(x["j2_width_nm"]) for x in h500]
    write(OUT / "h1e3b_j2_sampling_coverage.json", {"schema":"H1E3B_J2_SAMPLING_COVERAGE_V1","H550_canonical_registry":coverage(canonical),"H550_strict":coverage(canonical,{"BROADBAND_PROJECTOR_COMPATIBLE_STRICT"}),"H550_near_miss":coverage(canonical,{"CENTER_ONLY_COMPATIBLE","PARTIALLY_COMPATIBLE"}),"H550_all_complete_or_classified":coverage(canonical,{"BROADBAND_PROJECTOR_COMPATIBLE_STRICT","CENTER_ONLY_COMPATIBLE","PARTIALLY_COMPATIBLE","INCOMPATIBLE","450NM_ONLY_NOT_RECOVERABLE"}),"H1C1A_registry":coverage(h1c1a),"H1C1B_registry":coverage(h1c1b),"H500_legacy": {"records":len(h500),"J2_L_range_nm":[min(h500L),max(h500L)],"J2_W_range_nm":[min(h500W),max(h500W)],"unique_J2_L":len(set(h500L)),"unique_J2_W":len(set(h500W)),"unique_pairs":len(set((x["j2_length_nm"],x["j2_width_nm"]) for x in h500)),"J2_rotation_deg_values":sorted(set(float(x["j2_rotation_deg"]) for x in h500))},"constant_mean_direction": {"canonical_delta_values":sorted(set(float(r["J2_length_nm"])-float(r["J2_width_nm"]) for r in canonical)),"canonical_mean_values":sorted(set((float(r["J2_length_nm"])+float(r["J2_width_nm"])) / 2 for r in canonical)),"both_signs_observed": any(float(r["J2_length_nm"])-float(r["J2_width_nm"])<0 for r in canonical) and any(float(r["J2_length_nm"])-float(r["J2_width_nm"])>0 for r in canonical),"classification":"LOCAL_SEARCH_DIRECTION_ALREADY_EXPLORED"}})
    psi = []
    with (ROOT / "reports/stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv").open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try: psi.append({"Psi_deg":float(r["Psi_deg"]),"phase_deg":float(r.get("phi_txx",r.get("phase_deg",0))),"projector_error":float(r.get("projector_error",0)),"status":r.get("broadband_status")})
            except Exception: pass
    by_sign={}
    for r in psi:
        sign="negative" if r["Psi_deg"]<0 else "positive" if r["Psi_deg"]>0 else "zero"
        by_sign.setdefault(sign,{"records":0,"strict":0,"phase":[],"projector_error":[]}); z=by_sign[sign]; z["records"]+=1; z["strict"]+=r["status"]=="BROADBAND_PROJECTOR_COMPATIBLE_STRICT"; z["phase"].append(r["phase_deg"]); z["projector_error"].append(r["projector_error"])
    for z in by_sign.values():
        phases=z.pop("phase"); errors=z.pop("projector_error")
        z["phase_range_deg"]=[min(phases),max(phases)]; z["projector_error_range"]=[min(errors),max(errors)]
    write(OUT / "h1e3b_psi_confounded_semantics.json", {"schema":"H1E3B_PSI_CONFOUNDED_SEMANTICS_V1","source":"reports/stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv","Psi_range_deg":[min(x["Psi_deg"] for x in psi),max(x["Psi_deg"] for x in psi)],"grouped_by_sign":by_sign,"confounding":"every historical Psi change also changes displacement azimuth and theta_J2 because cx=D*cos(Psi)/2, cy=D*sin(Psi)/2, theta_J2=Psi; historical Psi-vs-phase/projector associations cannot identify either mechanism alone","J1_orientation_deg":0.0})
    write(OUT / "h1e3b_j2_orientation_decoupling.json", {"schema":"H1E3B_J2_ORIENTATION_DECOUPLING_V1","current_constraint":"theta_J2=Psi","proposed_constraint":"theta_J2=Psi+delta_theta_J2","displacement_kept":"cx=D*cos(Psi)/2; cy=D*sin(Psi)/2","old_grammar_recovered_at_delta_theta_J2":0.0,"independence":{"D":True,"Psi":True,"J2_length":True,"J2_width":True,"J1_rotation":True,"whole_dimer_transform":True},"new_grammar_dof":True,"physical_hypothesis":"decoupling may let Psi vary spatial coupling/phase while theta_J2 independently preserves or compensates the HWP-like polarization role; not guaranteed"})
    (OUT / "h1e3b_jones_interpretation.md").write_text("# H1E-3B J2 orientation decoupling\n\nThe existing builder uses `theta_J2 = Psi`. For `J2(theta)=R(theta)diag(a,b)R(-theta)`, a decoupled `delta_theta_J2` gives, evaluated at `theta=Psi`,\n\n- `dJxx/d(delta_theta)=(b-a) sin(2 Psi)`\n- `dJxy/d(delta_theta)=(a-b) cos(2 Psi)`\n- `dJyx/d(delta_theta)=(a-b) cos(2 Psi)`\n- `dJyy/d(delta_theta)=(a-b) sin(2 Psi)`\n\nThus the plausible benefit is compensation/selection: spatial coupling can be changed through Psi without being forced to rotate the J2 eigenaxis by the same amount. This is not a claim that delta-theta directly supplies scalar common phase.\n", encoding="utf-8")
    write(OUT / "h1e3b_next_dof_comparison.json", {"schema":"H1E3B_NEXT_DOF_COMPARISON_V1","options":[{"dof":"J2_length/J2_width constant-mean d2","classification":"LOCAL_SEARCH_DIRECTION","new_dimensionality":0,"common_phase_plausibility":"refinement only","projector_risk":"already sampled","builder_complexity":"none","solver_cost":"not a new grammar probe"},{"dof":"delta_theta_J2_deg","classification":"NEW_GRAMMAR_DOF","new_dimensionality":1,"common_phase_plausibility":"indirect compensation via decoupled Psi and J2 axis","projector_risk":"small-angle controllable but must be measured","fabrication_complexity":"low; one local rectangle orientation parameter","builder_complexity":"low; theta_J2=Psi+delta_theta","reuse_existing_data":"high; old rows are delta_theta=0 hypersurface","minimal_solver_cost":"6 geometries / 12 subruns"},{"dof":"independent J1 rotation","classification":"NEW_GRAMMAR_DOF","new_dimensionality":1,"common_phase_plausibility":"low","projector_risk":"first-order dominant","spectral_risk":"high in H1E1 A-small-N","decision":"not first"}],"selection":"delta_theta_J2_deg"})
    parent_rows=[]
    for p in old:
        if len(p.get("trajectory",[]))!=9: continue
        ph=[float(x["phi_deg"]) for x in p["trajectory"]]
        if p["minimum_projector_margin"] >= 0.035 and p["minimum_Txx"] >= 0.5 and max(ph)-min(ph) < 60:
            parent_rows.append({"geometry_uid":p["geometry_uid"],"exact_hash":p["exact_hash"],"coordinates_5d":p["coordinates_5d"],"minimum_projector_margin":p["minimum_projector_margin"],"minimum_Txx":p["minimum_Txx"],"minimum_throughput":p["minimum_throughput"],"phase_range_deg":max(ph)-min(ph),"Psi_deg":p["coordinates_5d"]["Psi_deg"]})
    parent_rows=sorted(parent_rows,key=lambda x:(-x["minimum_projector_margin"],x["phase_range_deg"],x["geometry_uid"]))[:3]
    write(OUT / "h1e3b_angle_scale_review.json", {"schema":"H1E3B_ANGLE_SCALE_REVIEW_V1","candidate_signed_scales_deg":[[-1,1],[-2,2],[-5,5]],"recommended_signed_scale_deg":[-1,1],"reason":"Psi is already a small LP angle (approximately +/-3 deg), decoupling should first probe a small orientation correction; +/-5 deg is deferred until projector margin is demonstrated"})
    variants=[]
    for p in parent_rows:
        for d in (-1,1): variants.append({"parent_uid":p["geometry_uid"],"delta_theta_J2_deg":d,"Psi_deg":p["Psi_deg"],"theta_J2_deg":p["Psi_deg"]+d,"D_nm":p["coordinates_5d"]["D_nm"],"J2_length_nm":p["coordinates_5d"]["J2_length_nm"],"J2_width_nm":p["coordinates_5d"]["J2_width_nm"]})
    write(OUT / "h1e3b_route_decision.json", {"schema":"H1E3B_ROUTE_DECISION_V1","J2_ANISOTROPY_ALREADY_EXISTING_DOF":True,"d2_classification":"LOCAL_SEARCH_DIRECTION","route":"DECOUPLE_J2_ORIENTATION_FROM_DISPLACEMENT_FIRST","recommended_next_dof":"delta_theta_J2_deg","old_grammar_recovered_at_delta_theta":0.0,"registry_rows":506,"ml_admitted":False,"solver_entered_delta":0,"parent_selection_rule":"strict 9/9; minimum Txx >=0.5; phase range <60 deg; then maximum projector margin"})
    write(OUT / "h1e3b_proposed_next_stage.json", {"schema":"LP_J2_ORIENTATION_DECOUPLING_BROADBAND_PROBE_V1","status":"PROPOSED_ONLY_NOT_EXECUTED","variable":"delta_theta_J2_deg","parameterization":"theta_J2=Psi+delta_theta_J2; centers remain D/Psi","parents":parent_rows,"variants":variants,"candidate_count":6,"formal_subrun_budget":12,"fixed_contract":{"H_global_nm":550,"grid_nm":GRID,"full_jones":True,"projector":[[1,0],[0,0]],"material":"APCD_TIO2_NATIVE_M1"},"paired_design_logic":["baseline: Psi, theta_J2=Psi","displacement-only conceptual: Psi+deltaPsi, theta_J2 held fixed","tied historical: Psi+deltaPsi, theta_J2=Psi+deltaPsi","compensated: Psi+deltaPsi, theta_J2 independently adjusted"],"stop_go":{"go":"at least one 9/9 strict child with preserved projector margin and evidence that decoupling changes the Psi response without simply adding cross-polarization","stop":"no strict child or projector risk dominates"},"solver_entered":False})
    (OUT / "h1e3b_summary.md").write_text(f"# H1E-3B J2 orientation-displacement decoupling audit\n\n- J2_length/J2_width were already independent coordinates in the H500/H550 grammar; constant-mean d2 is a local search direction, not a new grammar DOF.\n- Current coupling is `theta_J2=Psi` while centers use D/Psi.\n- Route: `DECOUPLE_J2_ORIENTATION_FROM_DISPLACEMENT_FIRST`.\n- Proposed DOF: `delta_theta_J2_deg`, recommended +/-1 deg, {len(variants)} geometries / 12 formal subruns, proposed only.\n- Registry remains 506; ML admitted false; solver entered delta 0.\n", encoding="utf-8")
    return 0


if __name__ == "__main__": raise SystemExit(main())
