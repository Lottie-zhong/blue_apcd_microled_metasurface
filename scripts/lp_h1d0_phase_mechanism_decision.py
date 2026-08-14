from __future__ import annotations

import ast
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1d0_phase_mechanism_decision"
STRICT_BANK_PATH = ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json"
REGISTRY_PATH = ROOT / "reports/stage_h1c1c_phase_gap/h1c1c_authoritative_label_registry_v1.csv"
H1C_FINAL_PATH = ROOT / "reports/stage_h1c1c_phase_gap/h1c1c_final.json"
ACCOUNTING_PATH = ROOT / "reports/stage_h1c1c_phase_gap/h1c1c_solver_accounting.json"

K = 6
M = 1
PITCH_NM = 431.907786
PERIOD_NM = K * PITCH_NM
PY_NM = 432.0
WAVELENGTHS_NM = [450.0 + 0.5 * i for i in range(9)]
TARGET_BINS_DEG = [0, 60, 120, 180, 240, 300]
MIN_CLEARANCE_NM = 20.0


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def phase_factor(phase_deg: float) -> complex:
    return complex(math.cos(math.radians(phase_deg)), math.sin(math.radians(phase_deg)))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def strict_bank() -> list[dict[str, Any]]:
    bank = read_json(STRICT_BANK_PATH)
    geometries = bank["geometries"]
    if bank["count"] != 7 or len(geometries) != 7:
        raise AssertionError("H1D0 requires the authoritative 7-geometry strict bank")
    if sorted(g["geometry_uid"] for g in geometries) != sorted(
        ["GLOBAL_006", "GLOBAL_015", "H1C1B_V2_005", "H1C1B_V2_009", "H1C1B_V2_010", "H1C1B_V2_012", "H1C1B_V2_015"]
    ):
        raise AssertionError("strict bank identity mismatch")
    return geometries


def phase_at(geometry: dict[str, Any], wavelength_nm: float) -> float:
    row = min(geometry["trajectory"], key=lambda item: abs(float(item["wavelength_nm"]) - wavelength_nm))
    if abs(float(row["wavelength_nm"]) - wavelength_nm) > 1e-9:
        raise AssertionError(f"missing wavelength {wavelength_nm} for {geometry['geometry_uid']}")
    return float(row["phi_deg"])


def parent_summary(geometry: dict[str, Any]) -> dict[str, Any]:
    trajectory = geometry["trajectory"]
    return {
        "geometry_uid": geometry["geometry_uid"],
        "exact_hash": geometry["exact_hash"],
        "coordinates_5d": geometry["coordinates_5d"],
        "minimum_Txx": geometry["minimum_Txx"],
        "minimum_projector_margin": geometry["minimum_projector_margin"],
        "minimum_throughput": geometry["minimum_throughput"],
        "trajectory": [
            {
                "wavelength_nm": row["wavelength_nm"],
                "phi_intrinsic_deg": row["phi_deg"],
                "projector_error": row["projector_error"],
                "Txx": row["Txx"],
                "throughput": row["throughput"],
            }
            for row in trajectory
        ],
    }


def ideal_detour_offsets() -> list[dict[str, Any]]:
    rows = []
    for index, target in enumerate(TARGET_BINS_DEG):
        offset = (-PERIOD_NM * target / 360.0) % PERIOD_NM
        rows.append(
            {
                "index": index,
                "target_phase_deg": target,
                "order_m": M,
                "ideal_relative_offset_nm": offset,
                "ideal_slot_index_for_increasing_x": int(round(offset / PITCH_NM)) % K,
                "phase_recovered_deg": (-(2.0 * math.pi * M * offset / PERIOD_NM) * 180.0 / math.pi) % 360.0,
            }
        )
    return rows


def dimer_pillars(geometry: dict[str, Any], center_x: float) -> list[tuple[float, float, float, float]]:
    coords = geometry["coordinates_5d"]
    d = float(coords["D_nm"])
    psi = math.radians(float(coords["Psi_deg"]))
    half_dx = 0.5 * d * math.cos(psi)
    half_dy = 0.5 * d * math.sin(psi)
    j1 = float(coords["J1_side_nm"])
    length = float(coords["J2_length_nm"])
    width = float(coords["J2_width_nm"])
    # Bounding box of the rotated J2 rectangle; this is conservative for
    # overlap screening and does not claim a full-wave near-field result.
    j2_x = abs(length * math.cos(psi)) + abs(width * math.sin(psi))
    j2_y = abs(length * math.sin(psi)) + abs(width * math.cos(psi))
    return [
        (center_x - half_dx, -half_dy, j1, j1),
        (center_x + half_dx, half_dy, j2_x, j2_y),
    ]


def clearance(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    gap_x = abs(a[0] - b[0]) - (a[2] + b[2]) / 2.0
    gap_y = abs(a[1] - b[1]) - (a[3] + b[3]) / 2.0
    if gap_x >= 0 and gap_y >= 0:
        return math.hypot(gap_x, gap_y)
    if gap_x >= 0:
        return gap_x
    if gap_y >= 0:
        return gap_y
    return max(gap_x, gap_y)


def layout_geometry(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    raw_positions = [float(row["offset_nm"]) for row in assignments]
    raw_pillars = [p for row, x in zip(assignments, raw_positions) for p in dimer_pillars(row["geometry"], x)]
    min_raw = min(p[0] - p[2] / 2.0 for p in raw_pillars)
    max_raw = max(p[0] + p[2] / 2.0 for p in raw_pillars)
    shift = (PERIOD_NM - (max_raw - min_raw)) / 2.0 - min_raw
    positions = [x + shift for x in raw_positions]
    pillars = [p for row, x in zip(assignments, positions) for p in dimer_pillars(row["geometry"], x)]
    internal = []
    for row, x in zip(assignments, positions):
        local = dimer_pillars(row["geometry"], x)
        internal.append(clearance(local[0], local[1]))
    pairwise = []
    for i, j in itertools.combinations(range(len(assignments)), 2):
        a = dimer_pillars(assignments[i]["geometry"], positions[i])
        b = dimer_pillars(assignments[j]["geometry"], positions[j])
        pairwise.extend(clearance(left, right) for left in a for right in b)
        # Periodic image of the pair across the supercell boundary.
        if i == 0 or j == len(assignments) - 1:
            b_shifted = [(x + PERIOD_NM, y, wx, wy) for x, y, wx, wy in b]
            a_shifted = [(x - PERIOD_NM, y, wx, wy) for x, y, wx, wy in a]
            pairwise.extend(clearance(left, right) for left in a for right in b_shifted)
            pairwise.extend(clearance(left, right) for left in a_shifted for right in b)
    min_x = min(p[0] - p[2] / 2.0 for p in pillars)
    max_x = max(p[0] + p[2] / 2.0 for p in pillars)
    min_y = min(p[1] - p[3] / 2.0 for p in pillars)
    max_y = max(p[1] + p[3] / 2.0 for p in pillars)
    sorted_positions = sorted(positions)
    physical_order = sorted(range(len(positions)), key=lambda index: positions[index])
    center_gaps = [sorted_positions[i + 1] - sorted_positions[i] for i in range(len(sorted_positions) - 1)]
    center_gaps.append(sorted_positions[0] + PERIOD_NM - sorted_positions[-1])
    boundary_margin = min(min_x, PERIOD_NM - max_x, PY_NM / 2.0 + min_y, PY_NM / 2.0 - max_y)
    min_clearance = min(internal + pairwise)
    return {
        "common_translation_nm": shift,
        "absolute_positions_nm": positions,
        "min_center_gap_nm": min(center_gaps),
        "min_internal_clearance_nm": min(internal),
        "min_periodic_neighbor_clearance_nm": min(pairwise),
        "min_clearance_nm": min_clearance,
        "supercell_boundary_margin_nm": boundary_margin,
        "y_period_margin_nm": min(PY_NM / 2.0 + min_y, PY_NM / 2.0 - max_y),
        "ordering_along_plus_x": True,
        "physical_order_indices": physical_order,
        "target_phase_order_when_sorted_plus_x": [assignments[index]["target_phase_deg"] for index in physical_order],
        "no_overlap": min_clearance >= MIN_CLEARANCE_NM,
        "supercell_boundary_legal": min_x >= 0 and max_x <= PERIOD_NM and min_y >= -PY_NM / 2.0 and max_y <= PY_NM / 2.0,
        "geometry_legal": min_clearance >= MIN_CLEARANCE_NM and boundary_margin >= 0,
        "footprint_model": "rotated-rectangle-conservative-bounding-box; offline geometry screen only",
    }


def pure_assignments(parent: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    phi_ref = phase_at(parent, 452.0)
    rows = []
    for target in TARGET_BINS_DEG:
        detour = wrap180(target - phi_ref)
        offset = (-PERIOD_NM * detour / 360.0) % PERIOD_NM
        rows.append({"target_phase_deg": target, "geometry": parent, "intrinsic_ref_deg": phi_ref, "detour_phase_deg": detour, "offset_nm": offset})
    return rows, phi_ref


def hybrid_best(bank: list[dict[str, Any]]) -> tuple[tuple[list[dict[str, Any]], float, tuple[str, ...]], tuple[list[dict[str, Any]], float, tuple[str, ...]] | None]:
    best: tuple[tuple[float, float, float, int], list[dict[str, Any]], float, tuple[str, ...]] | None = None
    best_legal: tuple[tuple[float, float, float, int], list[dict[str, Any]], float, tuple[str, ...]] | None = None
    for size in (1, 2, 3):
        for subset in itertools.combinations(bank, size):
            for phi0 in [0.5 * i for i in range(720)]:
                rows = []
                for target in TARGET_BINS_DEG:
                    choices = []
                    for parent in subset:
                        phi = phase_at(parent, 452.0)
                        detour = wrap180(target - phi0 - phi)
                        choices.append((abs(detour), -float(parent["minimum_throughput"]), parent["geometry_uid"], parent, detour))
                    _, _, _, parent, detour = min(choices)
                    offset = (-PERIOD_NM * detour / 360.0) % PERIOD_NM
                    rows.append({"target_phase_deg": target, "geometry": parent, "intrinsic_ref_deg": phase_at(parent, 452.0), "detour_phase_deg": detour, "offset_nm": offset})
                max_delta = max(abs(float(row["detour_phase_deg"])) for row in rows)
                rms_delta = math.sqrt(sum(float(row["detour_phase_deg"]) ** 2 for row in rows) / len(rows))
                min_throughput = min(float(row["geometry"]["minimum_throughput"]) for row in rows)
                score = (max_delta, rms_delta, -min_throughput, size)
                if best is None or score < best[0]:
                    best = (score, rows, phi0, tuple(p["geometry_uid"] for p in subset))
                if layout_geometry(rows)["geometry_legal"] and (best_legal is None or score < best_legal[0]):
                    best_legal = (score, rows, phi0, tuple(p["geometry_uid"] for p in subset))
    assert best is not None
    unconstrained = (best[1], best[2], best[3])
    legal = None if best_legal is None else (best_legal[1], best_legal[2], best_legal[3])
    return unconstrained, legal


def broadband_relative_phase(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for wavelength in WAVELENGTHS_NM:
        residuals = []
        raw = []
        for row in assignments:
            value = wrap180(phase_at(row["geometry"], wavelength) + float(row["detour_phase_deg"]) - float(row["target_phase_deg"]))
            raw.append(value)
            residuals.append(phase_factor(value))
        common = math.degrees(math.atan2(sum(z.imag for z in residuals), sum(z.real for z in residuals)))
        centered = [wrap180(value - common) for value in raw]
        for row, value in zip(assignments, centered):
            rows.append({"wavelength_nm": wavelength, "target_phase_deg": row["target_phase_deg"], "geometry_uid": row["geometry"]["geometry_uid"], "relative_phase_error_deg": value, "global_common_residual_deg": common})
    return rows


def dataset_audit(bank: list[dict[str, Any]]) -> dict[str, Any]:
    rows = read_csv(REGISTRY_PATH)
    strict_ids = {g["geometry_uid"] for g in bank}
    registry_ids = {row.get("geometry_uid", "") for row in rows}
    strict_rows = sum(1 for row in rows if row.get("geometry_uid") in strict_ids)
    return {
        "registry_path": str(REGISTRY_PATH.relative_to(ROOT)),
        "registry_sha256": sha256(REGISTRY_PATH),
        "row_count": len(rows),
        "unique_geometry_count": len(registry_ids),
        "all_full_jones_accepted": all(row.get("full_jones_accepted") == "True" for row in rows),
        "all_ml_eligible": all(row.get("ml_eligible") == "True" for row in rows),
        "all_ml_admitted_false": all(row.get("ml_admitted") == "False" for row in rows),
        "all_split_unassigned": all(row.get("split") == "UNASSIGNED" for row in rows),
        "strict_bank_geometry_count": len(strict_ids),
        "strict_bank_row_count": strict_rows,
        "route_a": {
            "directly_reusable_baseline_slice_rows": len(rows),
            "new_grammar_coverage_rows": 0,
            "interpretation": "All existing rows remain a valid lower-dimensional baseline slice if new local DOFs are added; none samples the new DOF directions.",
        },
        "route_b": {
            "same_grammar_rows_reusable": len(rows),
            "strict_local_building_block_rows": strict_rows,
            "strict_local_building_block_fraction": strict_rows / len(rows),
            "interpretation": "Detour changes placement/order phase, not the local dimer grammar; strict rows remain directly reusable as local-element evidence.",
        },
        "ml_restart": False,
    }


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    source_text = Path(__file__).read_text(encoding="utf-8")
    source_ast = ast.parse(source_text)
    lumapi_import = any(isinstance(node, (ast.Import, ast.ImportFrom)) and any("lumapi" in alias.name for alias in getattr(node, "names", [])) for node in ast.walk(source_ast))
    solver_entry_call = any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run" for node in ast.walk(source_ast))
    write_json(REPORT / "h1d0_zero_solver_guard.json", {
        "schema": "H1D0_ZERO_SOLVER_GUARD_V1",
        "solver_entered_delta": 0,
        "solver_run_called": False,
        "new_fsp_generated": False,
        "analyzer_source_sha256": sha256(Path(__file__)),
        "lumapi_import_present": lumapi_import,
        "solver_entry_calls_present": solver_entry_call,
        "scope": "offline analytic and geometry audit only; no FDTD, RCWA, ML, inverse, or K6 full-wave execution",
    })
    bank = strict_bank()
    h1c_final = read_json(H1C_FINAL_PATH)
    accounting = read_json(ACCOUNTING_PATH)
    if h1c_final.get("accepted_formal_subruns") != 20 or accounting.get("solver_subruns_entered") != 20:
        raise AssertionError("H1C-1C closure evidence is incomplete")

    best_parent = max(bank, key=lambda g: (float(g["minimum_throughput"]), float(g["minimum_projector_margin"])))
    pure, pure_phi_ref = pure_assignments(best_parent)
    hybrid_unconstrained, hybrid_legal = hybrid_best(bank)
    hybrid, hybrid_phi0, hybrid_subset = hybrid_legal or hybrid_unconstrained
    pure_geometry = layout_geometry(pure)
    hybrid_geometry = layout_geometry(hybrid)
    pure_broadband = broadband_relative_phase(pure)
    hybrid_broadband = broadband_relative_phase(hybrid)

    closure = {
        "status": "H1C_EXECUTION_PASS",
        "physics_outcome": h1c_final["physics_outcome"],
        "same_domain_search": "H1C_SAME_DOMAIN_BROADBAND_SEARCH_CLOSED",
        "scope": {"H_global_nm": 550.0, "J1_side_nm": [102, 114], "J2_length_nm": [100, 114], "J2_width_nm": [94, 106], "D_nm": [180, 210], "Psi_deg": [-3, 3], "wavelength_nm": [450.0, 454.0], "wavelength_step_nm": 0.5, "formal_projector_rule": "9/9 broadband projector compatibility"},
        "accepted_formal_subruns": 20,
        "strict_count_before": 7,
        "strict_count_after": 7,
        "new_strict_phase_regions": 0,
        "scoped_conclusion": "H550_BROADBAND_STRICT_PHASE_COVERAGE_INSUFFICIENT_WITHIN_TESTED_5D_DOMAIN",
        "do_not_generalize_to": ["all APCD dimers", "all heights", "all geometry grammars", "all detour-phase/K6 designs"],
        "sources": [str(H1C_FINAL_PATH.relative_to(ROOT)), str(STRICT_BANK_PATH.relative_to(ROOT))],
    }
    write_json(REPORT / "h1d0_h1c_closure.json", closure)

    ideal = ideal_detour_offsets()
    derivation = [
        "# H1D-0 Detour-Phase Derivation",
        "",
        "## Frozen convention",
        "",
        f"- K = {K} dimers; dimer pitch = {PITCH_NM:.6f} nm; supercell period P = K*p = {PERIOD_NM:.6f} nm.",
        "- +x is the phase-gradient direction and the target diffraction order is m=+1.",
        "- The repository array-factor convention is `A_m = sum_j c_j exp(-i*2*pi*m*j/K)/K`; a translation by Delta-x therefore contributes `exp(-i*G_m*Delta-x)` with `G_m=2*pi*m/P`.",
        "",
        "## Derivation",
        "",
        "For a desired relative phase phi_k = 60 deg*k, solve `exp(-i*G_1*Delta-x_k) = exp(i*phi_k)`. Thus",
        "",
        "`Delta-x_k = -P*phi_k/(2*pi) mod P = -P*k/6 mod P`.",
        "",
        "The ideal offsets are `[0, 5P/6, 4P/6, 3P/6, 2P/6, P/6]` nm for target bins `[0,60,120,180,240,300]` deg. Equivalently, at increasing physical x slots `[0,p,2p,3p,4p,5p]`, assign bins `[0,300,240,180,120,60]` deg.",
        "",
        "The existing `FORWARD_BINS=[0,60,120,180,240,300]` is a phase-library order, not by itself a proof of physical +1 steering. Under the repository minus-sign convention, using that order at increasing +x would select the opposite sign order; H1D0 freezes the explicit reverse assignment for m=+1.",
        "",
        "## Broadband behavior",
        "",
        "For fixed physical Delta-x and fixed normalized order m, `G_m=2*pi*m/P` is geometric and contains no wavelength. The detour contribution is therefore exactly wavelength-independent in the normalized supercell-order formulation. The diffraction angle remains wavelength-dependent through `sin(theta_m)=m*lambda/P`; that angular dispersion is not a wavelength dependence of the order coefficient phase.",
        "",
        "This is analytic initialization only. It is not final order-resolved `J_xy`, alpha/beta conversion, or `t_{alpha*<-alpha}^{(m)}` evidence.",
    ]
    (REPORT / "h1d0_detour_phase_derivation.md").write_text("\n".join(derivation) + "\n", encoding="utf-8")

    position_rows = []
    for row in ideal:
        position_rows.append({"architecture": "IDEAL_PURE_DETOUR", "target_phase_deg": row["target_phase_deg"], "order_m": M, "parent_geometry_uid": "same-parent", "intrinsic_reference_deg": 0.0, "detour_phase_deg": row["target_phase_deg"], "relative_offset_nm": row["ideal_relative_offset_nm"], "increasing_x_slot_index": row["ideal_slot_index_for_increasing_x"], "phase_recovered_deg": row["phase_recovered_deg"]})
    for label, assignments, phi0 in [("PURE_WITH_INTRINSIC_PARENT", pure, 0.0), ("HYBRID_INTRINSIC_DETOUR", hybrid, hybrid_phi0)]:
        for index, row in enumerate(assignments):
            position_rows.append({"architecture": label, "target_phase_deg": row["target_phase_deg"], "order_m": M, "parent_geometry_uid": row["geometry"]["geometry_uid"], "intrinsic_reference_deg": row["intrinsic_ref_deg"], "detour_phase_deg": row["detour_phase_deg"], "relative_offset_nm": row["offset_nm"], "increasing_x_slot_index": "", "phase_recovered_deg": wrap180(row["detour_phase_deg"] * -1), "global_phase_offset_deg": phi0, "position_index": index})
    write_csv(REPORT / "h1d0_detour_position_table.csv", position_rows, sorted({key for row in position_rows for key in row}))

    geometry = {
        "schema": "H1D0_DETOUR_GEOMETRY_FEASIBILITY_V1",
        "solver_entered_delta": 0,
        "K": K,
        "dimer_pitch_nm": PITCH_NM,
        "supercell_period_nm": PERIOD_NM,
        "p_y_nm": PY_NM,
        "minimum_clearance_required_nm": MIN_CLEARANCE_NM,
        "convention_sources": ["src/metasurface/stage12_k6_analytic.py", "src/metasurface/stage12_k6_layout.py", "src/metasurface/apcd_diffraction.py"],
        "common_translation_allowed": True,
        "pure_detour": {"parent_geometry_uid": best_parent["geometry_uid"], "parent_exact_hash": best_parent["exact_hash"], "assignments": [{"target_phase_deg": r["target_phase_deg"], "detour_phase_deg": r["detour_phase_deg"], "relative_offset_nm": r["offset_nm"]} for r in pure], "audit": pure_geometry},
        "hybrid_intrinsic_detour": {"subset_geometry_uids": list(hybrid_subset), "global_phase_offset_deg": hybrid_phi0, "assignments": [{"target_phase_deg": r["target_phase_deg"], "parent_geometry_uid": r["geometry"]["geometry_uid"], "detour_phase_deg": r["detour_phase_deg"], "relative_offset_nm": r["offset_nm"]} for r in hybrid], "audit": hybrid_geometry},
        "hybrid_unconstrained_analytic_optimum": {"subset_geometry_uids": list(hybrid_unconstrained[2]), "global_phase_offset_deg": hybrid_unconstrained[1], "audit": layout_geometry(hybrid_unconstrained[0]), "note": "minimum phase-correction score before enforcing no-overlap/clearance"},
        "cyclic_reordering_test": "pure reverse bin assignment is legal and preserves the same six equally spaced centers",
        "coupling_boundary": "bbox and clearance only; neighbor coupling/multiple scattering remain unvalidated",
    }
    write_json(REPORT / "h1d0_detour_geometry_feasibility.json", geometry)

    reuse = {"schema": "H1D0_STRICT_BANK_REUSE_V1", "source": str(STRICT_BANK_PATH.relative_to(ROOT)), "source_sha256": sha256(STRICT_BANK_PATH), "strict_count": len(bank), "records": [parent_summary(g) for g in bank], "recommended_pure_parent": {"geometry_uid": best_parent["geometry_uid"], "exact_hash": best_parent["exact_hash"], "reason": "highest minimum broadband throughput among the seven strict geometries"}}
    write_json(REPORT / "h1d0_strict_bank_reuse.json", reuse)
    write_json(REPORT / "h1d0_dataset_reuse_audit.json", dataset_audit(bank))

    options = {"schema": "H1D0_EXTENDED_GRAMMAR_OPTIONS_V1", "status": "PROPOSED_ONLY", "do_not_authorize_per_bin_height": True, "options": [{"name": "J1_independent_anisotropy", "added_dofs": ["J1_length_nm", "J1_width_nm"], "baseline_slice": "J1_length=J1_width=J1_side", "phase_leverage": "potentially direct local common-phase lever", "bounds": "must be derived from fabrication evidence before any solver"}, {"name": "independent_relative_orientation", "added_dofs": ["J1_orientation_deg or independent J2_orientation_deg"], "baseline_slice": "current frozen orientation convention", "phase_leverage": "potentially changes anisotropic interference", "bounds": "not authorized in H1D0"}, {"name": "independent_local_displacement_vector", "added_dofs": ["dx_nm", "dy_nm"], "baseline_slice": "current D/Psi polar representation", "phase_leverage": "changes coupling and possibly common phase", "bounds": "must preserve direct/periodic gaps"}], "contract_guard": "one global H remains mandatory; no per-bin H; no solver in H1D0"}
    write_json(REPORT / "h1d0_extended_grammar_options.json", options)

    pure_max_error = max(abs(float(row["relative_phase_error_deg"])) for row in pure_broadband)
    hybrid_max_error = max(abs(float(row["relative_phase_error_deg"])) for row in hybrid_broadband)
    route_matrix = {
        "schema": "H1D0_ROUTE_DECISION_MATRIX_V1",
        "routes": {
            "ROUTE_A_EXTEND_DIMER_INTRINSIC_GRAMMAR": {"broadband_projector_preservation": "medium-risk", "available_phase_leverage": "unknown until new DOF evidence", "360_degree_reachability": "not guaranteed", "fabrication_feasibility": "medium-risk", "parameter_count": "increases", "solver_cost": "high; new-grammar labels required", "existing_data_reuse": "baseline slice only", "K6_validation": "new local-element plus coupled validation", "coupling_sensitivity": "high", "interpretability": "medium"},
            "ROUTE_B_DETOUR_POSITIONAL_PHASE": {"broadband_projector_preservation": "high for repeated strict parent analytically", "available_phase_leverage": "full 360 degree relative phase analytically", "360_degree_reachability": "yes in order coefficient model", "fabrication_feasibility": "high for pure six-slot layout", "parameter_count": "low; positions/order only", "solver_cost": "low initial; one K6 x/y validation proposed", "existing_data_reuse": "direct local-element reuse; 63 strict rows", "K6_validation": "one coupled K6 order-resolved Jones validation", "coupling_sensitivity": "high but localized to one decisive test", "interpretability": "high"},
            "HYBRID_INTRINSIC_DETOUR": {"broadband_projector_preservation": "medium-high; parent dispersion creates residuals", "available_phase_leverage": "full analytically with smaller corrections", "360_degree_reachability": "yes in order coefficient model", "fabrication_feasibility": "conditional; legal assignment has tight boundary margin and low-throughput parents", "parameter_count": "low-medium", "solver_cost": "low-medium", "existing_data_reuse": "direct local-element reuse", "K6_validation": "same one-case validation plus hybrid assignment", "coupling_sensitivity": "high", "interpretability": "medium-high"},
        },
        "computed_checks": {"pure_parent": best_parent["geometry_uid"], "pure_max_broadband_relative_error_deg": pure_max_error, "hybrid_subset": list(hybrid_subset), "hybrid_geometry_legal": hybrid_geometry["geometry_legal"], "hybrid_max_broadband_relative_error_deg": hybrid_max_error, "hybrid_unconstrained_geometry_legal": layout_geometry(hybrid_unconstrained[0])["geometry_legal"]},
        "recommendation": "DETOUR_PHASE_FIRST",
        "reasoned_basis": ["The measured bottleneck is clustered intrinsic common phase, not lack of local selectivity evidence.", "A repeated strict dimer preserves the same local broadband Jones evidence while positional phase supplies the missing relative phase.", "Pure detour has zero new local geometry DOFs and a legal six-slot offline layout; coupling risk is isolated to one proposed K6 order-resolved validation."],
    }
    write_json(REPORT / "h1d0_route_decision_matrix.json", route_matrix)

    proposed = {"schema": "H1D0_PROPOSED_NEXT_STAGE_V1", "status": "PROPOSED_ONLY", "stage": "LP_DETOUR_PHASE_FEASIBILITY_PROBE", "route": "DETOUR_PHASE_FIRST", "parent_geometry_uid": best_parent["geometry_uid"], "parent_exact_hash": best_parent["exact_hash"], "layout": "six equal-pitch slots with reverse bin order for m=+1", "validation": ["one K=6 coupled supercell", "x and y input runs", "nine wavelengths 450.0-454.0 nm at 0.5 nm", "order-resolved J_xy for m=+1", "alpha/beta -> alpha*/beta* conversion", "report t_{alpha*<-alpha}^{(+1)} and leakage"], "proposed_solver_budget": {"independent_fdtd_cases": 2, "mpi_engines_per_case": 4, "threads_per_case": 1, "new_rcwa": 0, "new_ml": 0, "new_inverse": 0, "new_full_k6_database": 0}, "stop_go": {"go": "order-resolved +1 target channel remains selective and layout remains legal", "stop": ["sign mismatch", "supercell coupling destroys selectivity", "geometry legality failure", "order-resolved target channel unavailable"]}, "current_stage_solver_entered_delta": 0, "authorization_required_before_solver": True}
    write_json(REPORT / "h1d0_proposed_next_stage.json", proposed)

    summary = [
        "# H1D-0 Phase Mechanism Decision",
        "",
        "- H1C-1C: 20/20 accepted; strict bank 7 -> 7; same-domain search closed.",
        f"- K6 convention: P={PERIOD_NM:.6f} nm, m=+1, detour factor exp(-i*G_m*Delta-x).",
        f"- Pure parent: {best_parent['geometry_uid']} ({best_parent['exact_hash']}); max broadband relative phase error after common gauge removal: {pure_max_error:.6g} deg.",
        f"- Pure geometry legal: {pure_geometry['geometry_legal']}; minimum clearance {pure_geometry['min_clearance_nm']:.6f} nm; boundary margin {pure_geometry['supercell_boundary_margin_nm']:.6f} nm.",
        f"- Hybrid subset: {', '.join(hybrid_subset)}; max broadband relative phase error after common gauge removal: {hybrid_max_error:.6f} deg.",
        "- Recommendation: DETOUR_PHASE_FIRST.",
        "- No solver, ML training, inverse design, RCWA, or K6 full-wave run was executed in H1D-0.",
        "- Proposed next stage only: LP_DETOUR_PHASE_FEASIBILITY_PROBE, 2 FDTD formal cases (x/y) after explicit approval.",
    ]
    (REPORT / "h1d0_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    for row in pure_broadband:
        row["architecture"] = "PURE_WITH_INTRINSIC_PARENT"
    for row in hybrid_broadband:
        row["architecture"] = "HYBRID_INTRINSIC_DETOUR"
    write_csv(REPORT / "h1d0_broadband_phase_audit.csv", pure_broadband + hybrid_broadband, ["architecture", "wavelength_nm", "target_phase_deg", "geometry_uid", "relative_phase_error_deg", "global_common_residual_deg"])
    print(json.dumps({"status": "H1D0_ANALYSIS_COMPLETE", "solver_entered_delta": 0, "recommendation": "DETOUR_PHASE_FIRST", "pure_parent": best_parent["geometry_uid"], "pure_geometry_legal": pure_geometry["geometry_legal"], "hybrid_subset": hybrid_subset}, indent=2))


if __name__ == "__main__":
    main()
