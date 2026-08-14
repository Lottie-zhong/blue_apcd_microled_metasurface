from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


GRID = [450.0 + 0.5 * i for i in range(9)]
GRID_TOL = 1e-9
THRESHOLD = 0.1864961370084426
STAGES = (("H1A", 6), ("H1B1", 5), ("H1B2", 5), ("H1B3", 4))
PROPOSED_BOUNDS = {
    "J1_side_nm": [102.0, 114.0],
    "J2_length_nm": [100.0, 114.0],
    "J2_width_nm": [94.0, 106.0],
    "D_nm": [180.0, 210.0],
    "Psi_deg": [-3.0, 3.0],
}
AXES = tuple(PROPOSED_BOUNDS)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def repository_provenance(repo: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()

    return {
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "upstream_ahead_behind": git("rev-list", "--left-right", "--count", "HEAD...@{u}"),
        "tool_path": str(Path(__file__).resolve()),
        "tool_sha256": sha256(Path(__file__).resolve()),
    }


def number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def circular_diff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def circular_coverage(values: list[float]) -> float:
    vals = sorted({float(v) % 360.0 for v in values})
    if len(vals) < 2:
        return 0.0
    gaps = [b - a for a, b in zip(vals, vals[1:])]
    gaps.append(vals[0] + 360.0 - vals[-1])
    return 360.0 - max(gaps)


def relative_phase_spacing(phases: list[list[float]]) -> list[float]:
    if len(phases) < 2:
        return []
    return [circular_diff(phases[i + 1][0], phases[i][0]) for i in range(len(phases) - 1)]


def common_offset_error(phases: list[list[float]], bin_indices: list[int]) -> float:
    """Return the maximum circular residual after fitting phi0(lambda) freely."""
    if not phases or len(phases) != len(bin_indices):
        raise ValueError("phase vectors and bin indices must have equal nonzero length")
    if len({len(x) for x in phases}) != 1:
        raise ValueError("all phase vectors must use the same wavelength grid")
    residuals = []
    for j in range(len(phases[0])):
        offsets = [(phases[i][j] - 60.0 * bin_indices[i]) % 360.0 for i in range(len(phases))]
        phi0 = offsets[0]
        residuals.extend(abs(circular_diff(x, phi0)) for x in offsets[1:])
    return max(residuals, default=0.0)


def walk_wavelengths(value: Any, out: list[float]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = key.lower()
            if "wavelength" in key_lower and "spacing" not in key_lower:
                if isinstance(child, (int, float)):
                    value_nm = float(child) * 1e9 if abs(float(child)) < 1e-6 else float(child)
                    out.append(value_nm)
                elif isinstance(child, list):
                    for x in child:
                        if isinstance(x, (int, float)):
                            out.append(float(x) * 1e9 if abs(float(x)) < 1e-6 else float(x))
            walk_wavelengths(child, out)
    elif isinstance(value, list):
        for child in value:
            walk_wavelengths(child, out)


def checkpoint_evidence(case_dirs: list[Path]) -> dict[str, Any]:
    pols = []
    for case_dir in sorted(case_dirs):
        cp = case_dir / "checkpoint.json"
        item: dict[str, Any] = {
            "case_dir": str(case_dir),
            "polarization": case_dir.name.rsplit("_H550_", 1)[-1],
            "checkpoint_present": cp.exists(),
            "fsp_files": sorted(p.name for p in case_dir.glob("*.fsp")),
            "fspx_files": sorted(p.name for p in case_dir.glob("*.fspx")),
            "result_dataset_files": sorted(p.name for p in case_dir.glob("*.ldf")),
        }
        if not cp.exists():
            pols.append(item)
            continue
        obj = read_json(cp)
        wavelengths: list[float] = []
        walk_wavelengths(obj, wavelengths)
        rows = obj.get("rows", [])
        grid = obj.get("grid_audit", {})
        item.update(
            {
                "checkpoint_sha256": sha256(cp),
                "status": obj.get("status"),
                "rows_len": len(rows) if isinstance(rows, list) else None,
                "wavelengths_nm_observed": sorted({round(x, 9) for x in wavelengths if x < 10000}),
                "checkpoint_keys": sorted(obj),
                "complex_field_grid_present": bool(grid.get("Ex_shape") and grid.get("Ey_shape")),
                "source_spectrum_present": any("source" in str(k).lower() and "spectrum" in str(k).lower() for k in obj),
                "saved_result_dataset_present": bool(item["result_dataset_files"]),
                "post_fsp_extraction_capability": False,
            }
        )
        pols.append(item)
    observed = sorted({x for p in pols for x in p.get("wavelengths_nm_observed", [])})
    accepted = all(p.get("checkpoint_present") and p.get("status") == "ACCEPTED" for p in pols) and len(pols) == 2
    exact_grid = len(observed) == len(GRID) and all(abs(a - b) < GRID_TOL for a, b in zip(observed, GRID))
    if not pols or not accepted:
        classification = "MISSING_ARTIFACT"
    elif exact_grid and all(p.get("complex_field_grid_present") for p in pols):
        classification = "BROADBAND_FULL_JONES_RECOVERABLE"
    elif observed == [450.0]:
        classification = "450NM_ONLY_NOT_RECOVERABLE"
    else:
        classification = "BROADBAND_PARTIAL_RECOVERABLE"
    return {
        "polarizations": pols,
        "observed_wavelengths_nm": observed,
        "frozen_grid_exactly_present": exact_grid,
        "classification": classification,
        "solver_replay": False,
        "entered_replay_forbidden": True,
    }


def runtime_groups(repo: Path, stage: str) -> dict[str, list[Path]]:
    root = repo / "outputs" / f"lp_global_h_{stage.lower()}" / "runtime" / "cases"
    groups: dict[str, list[Path]] = {}
    if not root.exists():
        return groups
    for d in root.glob("*_H550_P*"):
        if d.is_dir():
            groups.setdefault(d.name.rsplit("_H550_", 1)[0], []).append(d)
    return groups


def h1a_rows(repo: Path) -> list[dict[str, Any]]:
    path = repo / "outputs/lp_global_h_h1a/complete_jones_table.csv"
    rows = read_csv(path)
    carry: dict[str, str] = {}
    out: list[dict[str, Any]] = []
    carry_keys = ("candidate_id", "authoritative_id", "anchor_role", "geometry_hash_sha256", *AXES)
    for row in rows:
        for key in carry_keys:
            if row.get(key):
                carry[key] = row[key]
        if row.get("H_global_nm") == "550.0" and row.get("source") == "H1A_NEW_SOLVER_XY_FORMAL":
            merged = {**carry, **{k: v for k, v in row.items() if v}}
            out.append(merged)
    unique: dict[str, dict[str, Any]] = {}
    for row in out:
        unique[row["geometry_hash_sha256"]] = row
    ranked = sorted(unique.values(), key=lambda x: number(x.get("projection_error_apcd_v1")) or 1e9)
    compatible = {row["geometry_hash_sha256"] for row in ranked[: len(ranked) // 2]}
    for row in ranked:
        row["stage"] = "H1A"
        row["center_projector_compatible"] = row["geometry_hash_sha256"] in compatible
        row["source_path"] = str(path)
    return ranked


def full_jones_rows(repo: Path, stage: str) -> list[dict[str, Any]]:
    path = repo / "outputs" / f"lp_global_h_{stage.lower()}" / f"{stage.lower()}_full_jones.csv"
    rows = read_csv(path)
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        if number(row.get("H_global_nm")) == 550.0:
            unique[row["geometry_hash_sha256"]] = row
    for row in unique.values():
        row["stage"] = stage
        row["center_projector_compatible"] = str(row.get("projector_compatible", "")).lower() == "true"
        row["source_path"] = str(path)
    return list(unique.values())


def get_geometry_from_checkpoint(evidence: dict[str, Any]) -> dict[str, Any]:
    for pol in evidence["polarizations"]:
        cp = Path(pol["case_dir"]) / "checkpoint.json"
        if cp.exists():
            obj = read_json(cp)
            geometry = obj.get("geometry", {})
            if geometry:
                return geometry
    return {}


def candidate_record(row: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    h = row.get("geometry_hash_sha256") or row.get("exact_geometry_hash_sha256")
    phi = number(row.get("phase_wrapped_deg"))
    err = number(row.get("projector_error_apcd_v1"))
    txx = number(row.get("Txx")) or number(row.get("selected_throughput_Txx"))
    geometry = get_geometry_from_checkpoint(evidence)
    legality = geometry.get("legality") or {}
    phase_region = (round((phi or 0.0) / 60.0) * 60.0) % 360.0
    is_c_seed = row.get("candidate_id") == "H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION"
    return {
        "geometry_id": row.get("candidate_id") or row.get("authoritative_id"),
        "exact_hash": h,
        "coordinates_5d": {key: number(row.get(key)) for key in AXES},
        "H_global_nm": number(row.get("H_global_nm")) or 550.0,
        "source_stage": row["stage"],
        "phi_lambda": [],
        "projector_error_lambda": [],
        "Txx_lambda": [],
        "throughput_lambda": [],
        "broadband_compatibility_status": "CENTER_ONLY_COMPATIBLE" if row["center_projector_compatible"] else "INCOMPATIBLE",
        "broadband_data_status": "NOT_RECOVERABLE_FROM_EXISTING_ARTIFACTS",
        "450nm_reference": {"phase_deg": phi, "projector_error": err, "Txx": txx, "projector_compatible": row["center_projector_compatible"]},
        "phase_region_450_reference_only": phase_region,
        "phase_cluster_semantics": "nearest_60deg_label_for_450nm_visualization_only",
        "seed_status": "GLOBAL_SIX_BIN_CANDIDATE_SEED" if is_c_seed else None,
        "candidate_promotion_status": "BROADBAND_SIX_BIN_CANDIDATE_PENDING_AUDIT" if is_c_seed else "NOT_PROMOTED",
        "legality_margins": {
            "direct_gap_nm": legality.get("direct_gap_nm"),
            "periodic_gap_x_nm": legality.get("periodic_gap_x_nm"),
            "periodic_gap_y_nm": legality.get("periodic_gap_y_nm"),
            "checker_pass": legality.get("pass"),
            "evidence": "runtime checkpoint geometry.legality" if legality else "not_present_in_checkpoint",
        },
        "retention": "retain_all_exact_H550_cases_before_extremum_filter; useful_island_discovery_is_not_extremum_only",
        "provenance": {
            "authoritative": True,
            "source_report_or_table": row["source_path"],
            "runtime_case_dirs": [p["case_dir"] for p in evidence["polarizations"]],
            "checkpoint_sha256": [p.get("checkpoint_sha256") for p in evidence["polarizations"]],
            "solver_replay": False,
            "exact_hash_dedup_key": h,
        },
    }


def load_candidates(repo: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage, expected in STAGES:
        stage_rows = h1a_rows(repo) if stage == "H1A" else full_jones_rows(repo, stage)
        assert len(stage_rows) == expected, (stage, len(stage_rows), expected)
        groups = runtime_groups(repo, stage)
        for row in stage_rows:
            geom = row.get("candidate_id") or row.get("authoritative_id")
            prefix = f"{stage}_{geom}" if stage != "H1A" else f"H1A_{geom}"
            matching = groups.get(prefix, [])
            if not matching:
                matching = [d for key, dirs in groups.items() if geom and geom in key for d in dirs]
            evidence = checkpoint_evidence(matching)
            row["evidence"] = evidence
            rows.append(candidate_record(row, evidence))
    return rows


def salvage_audit(repo: Path, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    cases = []
    for candidate in candidates:
        stage = candidate["source_stage"]
        geom = candidate["geometry_id"]
        groups = runtime_groups(repo, stage)
        matching = [d for key, dirs in groups.items() if geom in key for d in dirs]
        evidence = checkpoint_evidence(matching)
        cases.append({
            "geometry_id": geom,
            "stage": stage,
            "exact_hash": candidate["exact_hash"],
            "classification": evidence["classification"],
            "solver_replay": False,
            "entered_replay_forbidden": True,
            "postprocess_only": {
                "attempted": False,
                "success": False,
                "reason": "existing artifacts expose only a single 450 nm row; no frozen 9-point spectral dataset",
            },
            "evidence": evidence,
        })
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["classification"]] = counts.get(case["classification"], 0) + 1
    return {
        "schema": "H1C0_H550_EXISTING_SALVAGE_AUDIT_V1",
        "solver_contract": {"new_fdtd": False, "new_rcwa": False, "new_physics_solver": False},
        "case_count": len(cases),
        "classification_counts": counts,
        "recoverable_full_jones_count": counts.get("BROADBAND_FULL_JONES_RECOVERABLE", 0),
        "postprocess_only_broadband_extraction": {"attempted": False, "success": False, "solver_replay": False},
        "cases": cases,
    }


def domain_proposal(repo: Path, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    hist = read_json(repo / "outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_5d_design_space_contract_v1.json")["ranges"]
    observed = {key: [min(r["coordinates_5d"][key] for r in candidates), max(r["coordinates_5d"][key] for r in candidates)] for key in AXES}
    widths = {key: PROPOSED_BOUNDS[key][1] - PROPOSED_BOUNDS[key][0] for key in AXES}
    observed_widths = {key: observed[key][1] - observed[key][0] for key in AXES}
    return {
        "schema": "H1C0_H550_GLOBAL_LATERAL_SEARCH_DOMAIN_V1",
        "authorization": "PROPOSAL_ONLY_NOT_AUTHORIZED",
        "H_global_nm": 550.0,
        "period_nm": [432.0, 432.0],
        "material": "APCD_TIO2_NATIVE_M1",
        "historical_H500_design_space": hist,
        "H550_explored_range_from_20_exact_cases": observed,
        "proposed_global_range": PROPOSED_BOUNDS,
        "axis_width_expansion_ratio_vs_H550_explored": {key: widths[key] / observed_widths[key] if observed_widths[key] else None for key in AXES},
        "rectangular_envelope_volume_expansion_ratio_vs_H550_explored": math.prod(widths.values()) / math.prod(observed_widths.values()),
        "legality_constraints": {
            "J1_H_equals_J2_H_equals_H_global": True,
            "integer_lateral_dimensions": True,
            "period_432_nm": True,
            "direct_gap_ge_60_nm": True,
            "periodic_gap_x_and_y_ge_60_nm": True,
            "cell_containment": True,
            "no_overlap": True,
            "native_material": True,
            "exact_hash_unique": True,
            "interpretation": "rectangular proposal envelope; every generated point must pass the existing legality checker before any solver authorization",
        },
        "rationale": "expand around the observed disconnected H550 families and preserve room beyond the local edge corridor; do not infer global physics from the envelope",
        "extrapolation": {key: {"below_observed_nm_or_deg": PROPOSED_BOUNDS[key][0] - observed[key][0], "above_observed_nm_or_deg": PROPOSED_BOUNDS[key][1] - observed[key][1]} for key in AXES},
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def build(repo: Path) -> None:
    report = repo / "reports/stage_h1c0_broadband_global"
    report.mkdir(parents=True, exist_ok=True)
    provenance = repository_provenance(repo)
    contract_path = repo / "outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_broadband_smoke_attempt2_execution_contract_v1.json"
    contract = read_json(contract_path)
    threshold_source = repo / "scripts/lp_global_h_h1b3_probe_v1.py"
    broadband_contract = {
        "schema": "H1C0_BROADBAND_CONTRACT_V1",
        "repository_provenance": provenance,
        "solver_contract": {"new_fdtd": False, "new_rcwa": False, "new_physics_solver": False},
        "frozen_wavelength_grid_nm": GRID,
        "wavelength_endpoints_nm": [GRID[0], GRID[-1]],
        "wavelength_step_nm": 0.5,
        "wavelength_count": len(GRID),
        "reference_convention": {
            "material": "APCD_TIO2_NATIVE_M1",
            "period_nm": [432.0, 432.0],
            "monitor_z_nm": 1000.0,
            "observable": "transmission_side_coordinate_weighted_complex_G0",
            "endpoint_convention": "deduplicate_periodic_endpoints_and_reclose_period",
            "normalization": "sqrt(T)/norm(weighted_Ex,weighted_Ey)",
            "phase": "arg(txx)",
            "projector": [[1, 0], [0, 0]],
            "formal_polarizations": ["x", "y"],
        },
        "authoritative_source": str(contract_path),
        "authoritative_source_sha256": sha256(contract_path),
        "projector_compatibility": {
            "center_threshold": THRESHOLD,
            "threshold_source": str(threshold_source),
            "threshold_semantics": "inherited empirical H1A best_50_percent_by_projector_error_among_this_H1A_anchor_slice; no new absolute threshold",
            "broadband_aggregate_semantics": "NOT_FROZEN; Chart review required",
            "proposed_review_definition": "all frozen wavelengths pass the inherited error threshold, while throughput is reported as a robustness metric until a formal throughput gate is approved",
        },
        "450_nm_role": "visualization_reference_and_label_only; never sole broadband acceptance",
    }
    write_json(report / "h1c0_broadband_contract.json", broadband_contract)
    candidates = load_candidates(repo)
    audit = salvage_audit(repo, candidates)
    audit["repository_provenance"] = provenance
    write_json(report / "h1c0_h550_existing_salvage_audit.json", audit)
    bank = {
        "schema": "H550_GLOBAL_SIX_BIN_CANDIDATE_BANK",
        "repository_provenance": provenance,
        "H_global_nm": 550.0,
        "candidate_count": len(candidates),
        "broadband_candidate_promotion": "forbidden_without_frozen_full_jones_all_wavelength_audit",
        "phase_region_assignment": "450_nm_reference_only",
        "candidates": candidates,
        "retained_non_extremal_useful_islands": sum(1 for c in candidates if c["450nm_reference"]["projector_compatible"] and c["source_stage"] in {"H1A", "H1B1", "H1B2"}),
    }
    write_json(report / "h1c0_global_candidate_bank.json", bank)
    domain = domain_proposal(repo, candidates)
    domain["repository_provenance"] = provenance
    write_json(report / "h1c0_global_domain_proposal.json", domain)
    strategy = {
        "schema": "H1C0_SOLVER_STRATEGY_COMPARISON_V1",
        "repository_provenance": provenance,
        "current_runtime_evidence": {"processes_per_job": 4, "threads_per_job": 1, "validated_global_concurrency": 2, "broadband_points_per_run": len(GRID), "per_run_duration_field": "not recorded; do not fabricate wall time"},
        "strategy_A": {"name": "BROADBAND_FULL_JONES_EVERY_GEOMETRY", "subruns_per_geometry": 2, "formal_compatibility": True, "cost_for_72_geometries": 144},
        "strategy_B": {"name": "BROADBAND_X_RECONNAISSANCE_THEN_PHASE_DIVERSE_Y_COMPLETION", "x_subruns_for_72_geometries": 72, "y_subruns_if_50_percent_shortlist": 36, "total_subruns_if_50_percent_shortlist": 108, "formal_compatibility": "only_after_y_completion", "cost_saving_vs_A": "25_percent_subrun reduction in this illustrative shortlist"},
        "recommendation": "STRATEGY_B_WITH_MANDATORY_Y_COMPLETION_GATE",
        "recommendation_reason": "queue pressure makes x reconnaissance a cost optimization, but x-only rows never enter the formal candidate bank; if shortlist reduction is not demonstrated, revert to A because one broadband run already returns the full frozen spectrum",
    }
    write_json(report / "h1c0_solver_strategy_comparison.json", strategy)
    scan = {
        "schema": "H1C0_PROPOSED_GLOBAL_SCAN_V1",
        "repository_provenance": provenance,
        "authorization": "PROPOSED_ONLY_NOT_AUTHORIZED",
        "solver_entered": False,
        "generator": {"type": "deterministic_global_space_filling", "utility": "Sobol_or_equivalent_LHS", "seed": "H1C0_GLOBAL_20260814", "edge_only": False},
        "coarse_global_batch": {"new_geometries": 48, "coverage": "full proposed 5D envelope after legality filtering"},
        "adaptive_phase_gap_filling_batch": {"new_geometries": 24, "selection": "largest circular phase gaps and disconnected compatible-island coverage after broadband audit"},
        "total_new_geometries": 72,
        "strategy_A_formal_x_y_subruns": 144,
        "strategy_B_expected_x_y_subruns_at_50_percent_shortlist": 108,
        "expected_broadband_full_jones_cases": {"A": 72, "B": 36},
        "expected_information_gain": "discover distributed phase islands and quantify relative-spacing/projector robustness; not fit a complete 5D surrogate",
        "constituent_route": "TARGETED_CONSTITUENT_RECONNAISSANCE_DIAGNOSTIC_SIDE_ROUTE_ONLY",
    }
    write_json(report / "h1c0_proposed_global_scan.json", scan)
    lines = [
        "# H1C-0 Broadband Global Phase-Island Search Readiness",
        "",
        "## Status",
        "",
        "- Solver contract: `ZERO NEW FDTD / ZERO NEW RCWA / ZERO NEW PHYSICS SOLVER`.",
        f"- Frozen LP broadband grid: `{GRID[0]:.1f}..{GRID[-1]:.1f} nm`, step `{GRID[1]-GRID[0]:.1f} nm`, count `{len(GRID)}`.",
        "- 450 nm is a reference label only, not broadband acceptance.",
        "",
        "## Salvage closure",
        "",
        f"- Audited exact H550 geometries: `{len(candidates)}` (H1A 6, H1B1 5, H1B2 5, H1B3 4).",
        f"- Full-Jones broadband recoverable: `{audit['recoverable_full_jones_count']}`.",
        "- All 20 existing cases expose only one 450 nm row and pre-FSP artifacts; no postprocess-only broadband extraction was performed.",
        "- Existing 450 nm projector semantics remain empirical H1A best-50%-within-slice, inherited threshold `0.1864961370084426`; broadband aggregate semantics are not frozen.",
        "",
        "## Candidate bank and search",
        "",
        "- Candidate bank retains all 20 exact hashes before any extremum filter; C remains a `GLOBAL_SIX_BIN_CANDIDATE_SEED`, not a broadband promotion.",
        "- Proposed domain is a legality-filtered global 5D envelope, not a solver authorization.",
        f"- Proposed rectangle volume is `{domain['rectangular_envelope_volume_expansion_ratio_vs_H550_explored']:.3f}x` the observed local H550 range envelope.",
        "- Proposed scan: 48 coarse global points plus 24 adaptive phase-gap points; deterministic Sobol/LHS-equivalent coverage, not edge continuation.",
        "- Recommended strategy: x reconnaissance followed by mandatory y completion; x-only never proves projector compatibility.",
        "- Six-bin objective must fit free `phi0(lambda)` and minimize circular relative-spacing error across all nine wavelengths, jointly with projector and throughput robustness.",
        "",
        "## Hard gates",
        "",
        "- `solver_entered` delta: `0`.",
        "- `solver_replay`: `false` for every audited case.",
        "- Constituent reconnaissance remains diagnostic-only; no constituent FDTD was run.",
        "",
        "## Evidence",
        "",
        "- `h1c0_broadband_contract.json`",
        "- `h1c0_h550_existing_salvage_audit.json`",
        "- `h1c0_global_candidate_bank.json`",
        "- `h1c0_global_domain_proposal.json`",
        "- `h1c0_solver_strategy_comparison.json`",
        "- `h1c0_proposed_global_scan.json`",
    ]
    (report / "h1c0_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    build(args.repo.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
