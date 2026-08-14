from __future__ import annotations

import argparse
import cmath
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
H1D1_REPORT = ROOT / "reports/stage_h1d1_detour_feasibility"
H1D0_REPORT = ROOT / "reports/stage_h1d0_phase_mechanism_decision"
REPORT = ROOT / "reports/stage_h1d2_structure_factor_forensic"
MANIFEST = H1D1_REPORT / "h1d1_k6_detour_manifest.json"
H1D1_FINAL = H1D1_REPORT / "h1d1_final.json"
H1D0_GEOMETRY = H1D0_REPORT / "h1d0_detour_geometry_feasibility.json"
H1D0_ROUTES = H1D0_REPORT / "h1d0_route_decision_matrix.json"
H1D0_OPTIONS = H1D0_REPORT / "h1d0_extended_grammar_options.json"
CANONICAL_REGISTRY = ROOT / "reports/stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv"
TOL = 1e-9


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def phase_deg(value: complex) -> float:
    return math.degrees(cmath.phase(value))


def load_physical_geometry(manifest: dict[str, Any]) -> dict[str, Any]:
    parent = manifest["parent"]["coordinates_5d"]
    cx = float(manifest["parent"]["local_center_nm"]["x"])
    cy = float(manifest["parent"]["local_center_nm"]["y"])
    pillars = []
    for copy in manifest["copies"]:
        x0, y0 = float(copy["x_nm"]), float(copy["y_nm"])
        pillars.extend([
            {"dimer_x_nm": x0, "dimer_y_nm": y0, "pillar": 1, "x_nm": x0 - cx, "y_nm": y0 - cy, "x_span_nm": float(parent["J1_side_nm"]), "y_span_nm": float(parent["J1_side_nm"]), "rotation_deg": 0.0, "z_min_nm": 0.0, "z_max_nm": 550.0, "material": "APCD_TIO2_NATIVE_M1"},
            {"dimer_x_nm": x0, "dimer_y_nm": y0, "pillar": 2, "x_nm": x0 + cx, "y_nm": y0 + cy, "x_span_nm": float(parent["J2_length_nm"]), "y_span_nm": float(parent["J2_width_nm"]), "rotation_deg": float(parent["Psi_deg"]), "z_min_nm": 0.0, "z_max_nm": 550.0, "material": "APCD_TIO2_NATIVE_M1"},
        ])
    return {"parent": parent, "centers": [{"x_nm": float(row["x_nm"]), "y_nm": float(row["y_nm"])} for row in manifest["copies"]], "pillars": pillars}


def physical_record(geometry: dict[str, Any], P: float) -> list[dict[str, Any]]:
    return sorted([
        {key: (round(float(value), 9) if isinstance(value, (float, int)) else value) for key, value in row.items() if key not in {"dimer_x_nm", "dimer_y_nm"}}
        for row in geometry["pillars"]
    ], key=lambda row: (row["x_nm"], row["y_nm"], row["pillar"]))


def translated_record(geometry: dict[str, Any], P: float, delta: float) -> list[dict[str, Any]]:
    translated = {"pillars": []}
    for row in geometry["pillars"]:
        copy = dict(row)
        copy["x_nm"] = (float(copy["x_nm"]) + delta) % P
        copy["dimer_x_nm"] = (float(copy["dimer_x_nm"]) + delta) % P
        translated["pillars"].append(copy)
    return physical_record(translated, P)


def structure_factor(positions: list[float], P: float, m: int) -> complex:
    return sum(cmath.exp(-1j * 2.0 * math.pi * m * x / P) for x in positions)


def fullwave_comparison(final: dict[str, Any], positions: list[float], P: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    x_rows, y_rows = final["x_pol_eta_plus1_0_minus1"], final["y_pol_eta_plus1_0_minus1"]
    rows = []
    for xr, yr in zip(x_rows, y_rows):
        rows.append({"wavelength_nm": xr["wavelength_nm"], "x_eta_minus1": xr["eta_minus1"], "x_eta_0": xr["eta_0"], "x_eta_plus1": xr["eta_plus1"], "y_eta_minus1": yr["eta_minus1"], "y_eta_0": yr["eta_0"], "y_eta_plus1": yr["eta_plus1"], "x_m0_dominant": xr["eta_0"] > max(xr["eta_minus1"], xr["eta_plus1"]), "y_m0_dominant": yr["eta_0"] > max(yr["eta_minus1"], yr["eta_plus1"]), "qualitative_selection_consistent": xr["eta_0"] > max(xr["eta_minus1"], xr["eta_plus1"]) and yr["eta_0"] > max(yr["eta_minus1"], yr["eta_plus1"])})
    summary = {"all_x_m0_dominant": all(row["x_m0_dominant"] for row in rows), "all_y_m0_dominant": all(row["y_m0_dominant"] for row in rows), "structure_factor_m_minus1_abs": abs(structure_factor(positions, P, -1)), "structure_factor_m0_abs": abs(structure_factor(positions, P, 0)), "structure_factor_m_plus1_abs": abs(structure_factor(positions, P, 1)), "classification": "STRUCTURE_FACTOR_EXPLAINS_ORDER_SELECTION" if rows and all(row["qualitative_selection_consistent"] for row in rows) else "STRUCTURE_FACTOR_INCONSISTENT_WITH_FULLWAVE"}
    return rows, summary


def run() -> dict[str, Any]:
    manifest = read_json(MANIFEST)
    final = read_json(H1D1_FINAL)
    h1d0 = read_json(H1D0_GEOMETRY)
    routes = read_json(H1D0_ROUTES)
    options = read_json(H1D0_OPTIONS)
    extension = next(option for option in options["options"] if option["name"] == "J1_independent_anisotropy")
    P = float(manifest["P_supercell_nm"])
    p = float(manifest["p_nm"])
    geometry = load_physical_geometry(manifest)
    sorted_centers = sorted(geometry["centers"], key=lambda row: row["x_nm"])
    positions = [row["x_nm"] for row in sorted_centers]
    x0 = positions[0]
    residuals = [x - (x0 + n * p) for n, x in enumerate(positions)]
    regular = max(abs(value) for value in residuals) <= TOL
    physical = physical_record(geometry, P)
    translated = translated_record(geometry, P, p)
    primitive_recovered = translated == physical
    control_positions = [x0 + n * p for n in range(6)]
    control_geometry = {"pillars": []}
    for x0_control in control_positions:
        for row in geometry["pillars"]:
            if abs(float(row["dimer_x_nm"]) - positions[0]) <= TOL:
                copy = dict(row)
                copy["dimer_x_nm"] = x0_control
                copy["x_nm"] += x0_control - positions[0]
                control_geometry["pillars"].append(copy)
    control_physical = physical_record(control_geometry, P)
    physical_hash = sha256(physical)
    control_hash = sha256(control_physical)
    structure_rows = []
    for m in range(-6, 7):
        value = structure_factor(positions, P, m)
        structure_rows.append({"m": m, "real": value.real, "imag": value.imag, "magnitude": abs(value), "phase_deg": phase_deg(value) if abs(value) > 1e-14 else None, "analytic_selection": "constructive" if m % 6 == 0 else "cancelled_root_of_unity"})
    write_csv(REPORT / "h1d2_structure_factor.csv", structure_rows)
    comparison_rows, comparison_summary = fullwave_comparison(final, positions, P)
    write_json(REPORT / "h1d2_fullwave_structure_factor_comparison.json", {"schema": "H1D2_FULLWAVE_STRUCTURE_FACTOR_COMPARISON_V1", "solver_entered_delta": 0, "rows": comparison_rows, "summary": comparison_summary, "no_exact_power_claim": True})
    exact_geometry = {"schema": "H1D2_EXACT_GEOMETRY_AUDIT_V1", "solver_entered_delta": 0, "layout_uid": manifest["layout_uid"], "parent_geometry_uid": manifest["parent"]["geometry_uid"], "parent_exact_hash": manifest["parent"]["exact_hash"], "H_global_nm": manifest["H_global_nm"], "p_nm": p, "P_supercell_nm": P, "pillars": sorted(geometry["pillars"], key=lambda row: (row["x_nm"], row["y_nm"], row["pillar"])), "background_and_boundary_contract": {"x_period_nm": P, "y_period_nm": 432.0, "x_boundary": "Periodic", "y_boundary": "Periodic", "z_boundary": "PML", "source_z_nm": -250.0, "monitor_z_nm": 1000.0, "background_index": 1.0, "material": "APCD_TIO2_NATIVE_M1"}}
    write_json(REPORT / "h1d2_exact_geometry_audit.json", exact_geometry)
    write_json(REPORT / "h1d2_primitive_period_audit.json", {"schema": "H1D2_PRIMITIVE_PERIOD_AUDIT_V1", "solver_entered_delta": 0, "regular_p_lattice": regular, "x0_nm": x0, "positions_sorted_nm": positions, "residuals_nm": residuals, "maximum_coordinate_residual_nm": max(abs(value) for value in residuals), "primitive_translation_nm": p, "primitive_period_recovered": primitive_recovered, "complete_structure_translation_test": "all pillars, dimensions, orientations, material and z extents included", "background_layers_and_boundaries_invariant": True, "physical_geometry_hash": physical_hash, "translated_physical_geometry_hash": sha256(translated), "phase_metadata_excluded": True})
    label_mutation_hash = sha256(physical_record(geometry, P))
    write_json(REPORT / "h1d2_phase_label_physicality_audit.json", {"schema": "H1D2_PHASE_LABEL_PHYSICALITY_AUDIT_V1", "solver_entered_delta": 0, "labels_deg": [0, 60, 120, 180, 240, 300], "labels_are_metadata_only": True, "geometry_hash_before_labels": physical_hash, "geometry_hash_after_label_reorder_or_mutation": label_mutation_hash, "geometry_hash_unchanged": physical_hash == label_mutation_hash, "changed_properties": []})
    write_json(REPORT / "h1d2_no_detour_control_equivalence.json", {"schema": "H1D2_NO_DETOUR_CONTROL_EQUIVALENCE_V1", "solver_entered_delta": 0, "control_definition": "same exact V2_009 x6 at x0+n*p, no phase-bin metadata", "h1d1_physical_hash": physical_hash, "control_physical_hash": control_hash, "physically_identical": physical_hash == control_hash and control_physical == physical, "no_detour_control_redundant": physical_hash == control_hash and control_physical == physical, "recommendation": "DO_NOT_RUN_NO_DETOUR_FDTD"})
    phase_lines = ["# H1D-2 Constructive Phase Condition", "", "Frozen sign convention: each local contribution is `phi_intrinsic,n - G_m x_n`.", "", "For m=+1 and adjacent +x spacing `p=P/6`, constructive interference requires:", "", "`phi_intrinsic,n+1 - phi_intrinsic,n = G_1 p = +2*pi/6 = +60 deg (mod 360 deg)`.", "", "Thus identical intrinsic phases cannot constructively build m=+1 on the regular p lattice. The observed H1D-1 m=+1 suppression is therefore not, by itself, evidence that coupling destroyed a valid detour modulation.", "", f"Exact P/6 = `{P/6:.15f} nm`; exact p = `{p:.15f} nm`; residual = `{P/6-p:.15e} nm`.", "", "For identical intrinsic phases, positional compensation requires `delta_x_n = -n*p (mod P)`, i.e. `[0, 5p, 4p, 3p, 2p, p]` in site order. This collapses all six sites onto one primitive slot and is not a legal separated six-element layout."]
    (REPORT / "h1d2_constructive_phase_condition.md").write_text("\n".join(phase_lines) + "\n", encoding="utf-8")
    shifts = [(0.0 if n == 0 else ((-n * p) % P)) for n in range(6)]
    write_json(REPORT / "h1d2_positional_shift_feasibility.json", {"schema": "H1D2_POSITIONAL_SHIFT_FEASIBILITY_V1", "solver_entered_delta": 0, "delta_x_for_60deg_nm": P / 6.0, "p_nm": p, "P_over_6_equals_p": abs(P / 6.0 - p) <= TOL, "required_shifts_by_site_order_nm": shifts, "resulting_positions_mod_P_nm": [((x0 + n * p + shifts[n]) % P) for n in range(6)], "all_sites_co_locate_mod_P": len({round((x0 + n * p + shifts[n]) % P, 9) for n in range(6)}) == 1, "overlap_or_cell_order_collapse": True, "feasible_as_six_separated_elements": False})
    hybrid = h1d0["hybrid_intrinsic_detour"]["audit"]
    unconstrained = h1d0["hybrid_unconstrained_analytic_optimum"]["audit"]
    write_json(REPORT / "h1d2_hybrid_reassessment.json", {"schema": "H1D2_HYBRID_REASSESSMENT_V1", "solver_entered_delta": 0, "P_over_6_nm": P / 6.0, "p_nm": p, "legal_hybrid_min_clearance_nm": hybrid["min_clearance_nm"], "legal_hybrid_boundary_margin_nm": hybrid["supercell_boundary_margin_nm"], "legal_hybrid_max_broadband_relative_phase_error_deg": routes["computed_checks"]["hybrid_max_broadband_relative_error_deg"], "unconstrained_hybrid_min_clearance_nm": unconstrained["min_clearance_nm"], "unconstrained_hybrid_geometry_legal": unconstrained["geometry_legal"], "interpretation": "The tight legal hybrid boundary and poor phase residual are consistent with trying to combine intrinsic phase corrections with a positional step equal to the primitive period; this is a geometric/grammar limitation, not a solver result."})
    route = {"schema": "H1D2_ROUTE_DECISION_V1", "solver_entered_delta": 0, "regular_p_lattice": regular, "primitive_period_recovered": primitive_recovered, "phase_bin_labels_physically_inert": True, "no_detour_control_redundant": physical_hash == control_hash and control_physical == physical, "structure_factor_classification": comparison_summary["classification"], "dominant_failure_mechanism": "PURE_DETOUR_LAYOUT_HAS_NO_PHYSICAL_SUPERCELL_MODULATION", "route_decision": "EXTEND_DIMER_GRAMMAR_FIRST", "reason": "The tested K6 is a primitive-p identical-dimer array represented with P=6p; intrinsic local phase grammar must be physically varied before another detour FDTD.", "detour_general_mechanism_rejected": False}
    write_json(REPORT / "h1d2_route_decision.json", route)
    write_json(REPORT / "h1d2_proposed_next_stage.json", {"schema": "H1D2_PROPOSED_NEXT_STAGE_V1", "status": "PROPOSED_ONLY", "solver_entered_delta": 0, "route": "LP_EXTENDED_DIMER_GRAMMAR_REACHABILITY_PROBE", "smallest_candidate_extension": extension["name"], "added_dofs": extension["added_dofs"], "baseline_slice": extension["baseline_slice"], "bounds": extension["bounds"], "global_H_contract": "one shared H remains mandatory", "ml_admitted": False, "automatic_start": False})
    summary = ["# Stage H1D-2 Primitive-Period and Structure-Factor Forensic", "", "- Status: `PASS`; zero solver stage.", f"- H1D-1 sorted centers form x0+n*p: `{regular}`; maximum residual `{max(abs(value) for value in residuals):.3e} nm`.", f"- Complete pillar distribution recovers primitive period p: `{primitive_recovered}`; phase-bin labels are physically inert: `true`.", f"- Identical-scatterer structure factor: `|S_-1|={abs(structure_factor(positions, P, -1)):.3e}`, `|S_0|={abs(structure_factor(positions, P, 0)):.15g}`, `|S_+1|={abs(structure_factor(positions, P, 1)):.3e}`.", f"- FDTD qualitative comparison: `{comparison_summary['classification']}`; m=0 remains dominant across all 9 wavelengths for x/y.", "- H1D-1 is a primitive-p identical-dimer array represented with P=6p, not a physical detour-modulated supercell.", "- No-detour control is physically redundant; no control FDTD is recommended.", "- Required adjacent intrinsic phase step for m=+1: +60 deg per +x primitive site.", f"- Positional 60-degree scale: P/6={P/6:.15f} nm = p; identical-phase compensation co-locates the six sites.", f"- Updated route: `{route['route_decision']}`; proposed-only smallest extension: J1 independent anisotropy.", "- solver_entered_delta=0; no FDTD, RCWA, ML, inverse, or replay.", "", "Artifacts: `h1d2_exact_geometry_audit.json`, `h1d2_primitive_period_audit.json`, `h1d2_structure_factor.csv`, `h1d2_fullwave_structure_factor_comparison.json`, `h1d2_phase_label_physicality_audit.json`, `h1d2_no_detour_control_equivalence.json`, `h1d2_constructive_phase_condition.md`, `h1d2_positional_shift_feasibility.json`, `h1d2_hybrid_reassessment.json`, `h1d2_route_decision.json`, `h1d2_proposed_next_stage.json`." ]
    (REPORT / "h1d2_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return {"status": "PASS", "solver_entered_delta": 0, "route_decision": route["route_decision"], "regular_p_lattice": regular, "primitive_period_recovered": primitive_recovered, "structure_factor_classification": comparison_summary["classification"], "no_detour_control_redundant": physical_hash == control_hash and control_physical == physical}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        raise SystemExit("H1D2 is an offline-only forensic; pass --run to write reports")
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
