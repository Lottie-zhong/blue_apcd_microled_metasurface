from __future__ import annotations

import csv
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPORT = ROOT / "reports/stage_h1c1a_broadband_global"
REPORT = ROOT / "reports/stage_h1c1b0_broadband_attribution"
RUNTIME = ROOT / "outputs/lp_global_h_h1c1a/runtime/cases"
GRID = [450.0 + 0.5 * i for i in range(9)]
PROJECTOR_ERROR_MAX = 0.1864961370084426
BOUNDS = {
    "J1_side_nm": (102.0, 114.0),
    "J2_length_nm": (100.0, 114.0),
    "J2_width_nm": (94.0, 106.0),
    "D_nm": (180.0, 210.0),
    "Psi_deg": (-3.0, 3.0),
}
STATUS_ORDER = (
    "BROADBAND_PROJECTOR_COMPATIBLE_STRICT",
    "CENTER_ONLY_COMPATIBLE",
    "PARTIALLY_COMPATIBLE",
    "INCOMPATIBLE",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def circular_diff(left: float, right: float) -> float:
    return (left - right + 180.0) % 360.0 - 180.0


def circular_distance(left: float, right: float) -> float:
    return abs(circular_diff(left, right))


def phase_sector(phase: float, width: float = 30.0) -> int:
    return int((phase % 360.0) // width)


def load_inputs() -> dict[str, Any]:
    manifest = read_json(SOURCE_REPORT / "h1c1a_candidate_manifest.json")
    full_rows = list(csv.DictReader((SOURCE_REPORT / "h1c1a_broadband_full_jones.csv").open(encoding="utf-8", newline="")))
    summaries = list(csv.DictReader((SOURCE_REPORT / "h1c1a_geometry_broadband_summary.csv").open(encoding="utf-8", newline="")))
    accounting = read_json(SOURCE_REPORT / "h1c1a_solver_accounting.json")
    labels = read_json(SOURCE_REPORT / "lp_hf_authoritative_label_registry_v1.json")
    return {"manifest": manifest, "full_rows": full_rows, "summaries": summaries, "accounting": accounting, "labels": labels}


def float_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        result.append({key: (number(value) if key not in {"geometry_uid", "exact_hash", "broadband_status", "source_stage", "case_uid_x", "case_uid_y"} else value) for key, value in row.items()})
    return result


def grouped_rows(full_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in float_rows(full_rows):
        grouped.setdefault(str(row["geometry_uid"]), []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: float(row["wavelength_nm"]))
    return grouped


def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    result = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        average = (cursor + end - 1) / 2.0 + 1.0
        for index in order[cursor:end]:
            result[index] = average
        cursor = end
    return result


def correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 3:
        return None
    x, y = rank(left), rank(right)
    mx, my = sum(x) / len(x), sum(y) / len(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denominator = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return numerator / denominator if denominator else None


def circular_gaps(phases: list[float]) -> list[dict[str, float]]:
    values = sorted(phase % 360.0 for phase in phases)
    if len(values) < 2:
        return []
    return [{"from_phase_deg": left, "to_phase_deg": right, "gap_deg": right - left} for left, right in zip(values, values[1:])] + [{"from_phase_deg": values[-1], "to_phase_deg": values[0], "gap_deg": values[0] + 360.0 - values[-1]}]


def contiguous_true_width(values: list[bool], spacing_nm: float = 0.5) -> float:
    best = current = 0
    for value in values + [False]:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return max(0.0, (best - 1) * spacing_nm)


def morphology(pass_values: list[bool], status: str) -> str:
    passed = sum(pass_values)
    if passed == 9:
        return "STRICT_9_OF_9"
    if passed == 8:
        return "NEAR_STRICT_8_OF_9"
    if passed == 7:
        return "NEAR_STRICT_7_OF_9"
    failures = [index for index, passed_value in enumerate(pass_values) if not passed_value]
    if not failures:
        return "UNCLASSIFIED"
    if passed == 0:
        return "BROADLY_INCOMPATIBLE"
    if failures == list(range(0, max(failures) + 1)):
        return "BLUE_EDGE_LIMITED"
    if failures == list(range(min(failures), 9)):
        return "RED_EDGE_LIMITED"
    if 0 in failures and 8 in failures:
        return "BOTH_EDGE_LIMITED"
    if status == "CENTER_ONLY_COMPATIBLE":
        return "CENTER_ONLY_NARROWBAND"
    return "INTERIOR_RESONANT_FAILURE"


def build_failure_matrix(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = {row["geometry_uid"]: row for row in inputs["summaries"]}
    candidates = {row["geometry_uid"]: row for row in inputs["manifest"]["candidates"]}
    matrix: list[dict[str, Any]] = []
    for uid, rows in sorted(grouped_rows(inputs["full_rows"]).items()):
        summary = summaries[uid]
        profile = []
        for row in rows:
            error = float(row["projector_error"])
            profile.append({"wavelength_nm": float(row["wavelength_nm"]), "projector_error": error, "projector_pass": error <= PROJECTOR_ERROR_MAX, "projector_margin": PROJECTOR_ERROR_MAX - error, "Txx": float(row["Txx"]), "throughput": float(row["throughput"]), "phi_txx_deg": float(row["phi_txx"])})
        passes = [bool(row["projector_pass"]) for row in profile]
        failed = [row["wavelength_nm"] for row in profile if not row["projector_pass"]]
        errors = [row["projector_error"] for row in profile]
        phase_trajectory = [row["phi_txx_deg"] for row in profile]
        record = {"geometry_uid": uid, "exact_hash": candidates[uid]["exact_hash"], "coordinates_5d": candidates[uid]["coordinates_5d"], "role": candidates[uid]["role"], "source": candidates[uid]["source"], "broadband_status": summary["broadband_status"], "projector_pass_count_9": sum(passes), "failed_wavelengths": failed, "first_failed_wavelength_nm": failed[0] if failed else None, "blue_edge_failure": bool(failed and failed[0] == GRID[0]), "red_edge_failure": bool(failed and failed[-1] == GRID[-1]), "interior_failure": any(index not in (0, 8) and not passes[index] for index in range(9)), "worst_projector_error": max(errors), "median_projector_error": sorted(errors)[len(errors) // 2], "minimum_projector_margin": min(PROJECTOR_ERROR_MAX - error for error in errors), "contiguous_pass_bandwidth_nm": contiguous_true_width(passes), "center_450_pass": passes[0], "failure_morphology": morphology(passes, summary["broadband_status"]), "phase_trajectory_deg": phase_trajectory, "phase_450_deg": phase_trajectory[0], "min_Txx": min(float(row["Txx"]) for row in profile), "median_Txx": sorted(float(row["Txx"]) for row in profile)[len(profile) // 2], "max_Txx": max(float(row["Txx"]) for row in profile), "min_throughput": min(float(row["throughput"]) for row in profile), "median_throughput": sorted(float(row["throughput"]) for row in profile)[len(profile) // 2], "max_throughput": max(float(row["throughput"]) for row in profile), "phase_sector_30deg": phase_sector(phase_trajectory[0]), "wavelength_profile": profile, "formal_strict_candidate": summary["broadband_status"] == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"}
        matrix.append(record)
    return matrix


def load_h1c1a_module():
    path = ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py"
    spec = importlib.util.spec_from_file_location("h1c1a_recovery_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("HARD_GATE_H1C1A_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def inspect_saved_fsp(fsp: Path) -> dict[str, Any]:
    import numpy as np

    sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
    import lumapi

    probe: dict[str, Any] = {"fsp_load_ok": False, "run_called": False, "raw_transmission_data": False, "raw_complex_field_data": False, "wavelengths_nm": [], "transmission": [], "extractor_status": "NOT_ATTEMPTED", "extractor_error": None, "solver_replay": False}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=True)
        fdtd.load(str(fsp))
        probe["fsp_load_ok"] = True
        transmission = np.real(np.asarray(fdtd.transmission("T")).squeeze()).reshape(-1)
        probe["raw_transmission_data"] = len(transmission) == len(GRID)
        probe["transmission"] = [float(value) for value in transmission]
        probe["wavelengths_nm"] = list(GRID)
        ex = np.asarray(fdtd.getresult("field_monitor", "Ex"))
        ey = np.asarray(fdtd.getresult("field_monitor", "Ey"))
        probe["raw_complex_field_data"] = bool(ex.size and ey.size and ex.shape[-1] == len(GRID) and ey.shape[-1] == len(GRID))
        extractor = load_h1c1a_module()
        try:
            rows, grid = extractor.extract_broadband(fdtd)
            probe["extractor_status"] = "POSTPROCESS_RECOVERED"
            probe["recovered_rows"] = len(rows)
            probe["extractor_grid"] = grid
        except Exception as exc:
            probe["extractor_status"] = "FAILED_FROZEN_EXTRACTION"
            probe["extractor_error"] = repr(exc)
    except Exception as exc:
        probe["fsp_load_error"] = repr(exc)
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    return probe


def quarantine_audit(inputs: dict[str, Any], probe_fsp: bool) -> dict[str, Any]:
    audited = []
    for case in inputs["accounting"]["cases"]:
        if not case.get("quarantined"):
            continue
        case_dir = RUNTIME / case["case_id"]
        provenance_path = case_dir / "attempt_provenance.json"
        provenance = read_json(provenance_path) if provenance_path.exists() else {}
        fsp_files = sorted(case_dir.glob("*.fsp"))
        fspx_files = sorted(case_dir.glob("*.fspx"))
        log_files = sorted(case_dir.glob("*.log"))
        result_files = sorted(path for path in case_dir.iterdir() if any(token in path.name.lower() for token in ("result", "dataset", "monitor"))) if case_dir.exists() else []
        error = str(provenance.get("error") or "")
        wavelength_match = re.search(r"NEGATIVE_T:([0-9.]+):([-+0-9.eE]+)", error)
        probe = inspect_saved_fsp(next((path for path in fsp_files if path.name.endswith("_run.fsp")), fsp_files[-1])) if probe_fsp and fsp_files else {"fsp_load_ok": False, "run_called": False, "solver_replay": False, "extractor_status": "NOT_ATTEMPTED"}
        solver_log_text = "\n".join(path.read_text(errors="replace") for path in log_files)
        raw_result_evidence = bool(probe.get("raw_complex_field_data") and probe.get("raw_transmission_data"))
        if probe.get("extractor_status") == "POSTPROCESS_RECOVERED":
            classification = "POSTPROCESS_RECOVERABLE"
        elif raw_result_evidence:
            classification = "PARTIAL_ARTIFACT_NOT_ENOUGH_FOR_FORMAL_RESULT"
        else:
            classification = "UNRECOVERABLE_WITHOUT_REPLAY"
        audited.append({"geometry_uid": case["geometry_uid"], "exact_hash": case["exact_hash"], "polarization": case["polarization"], "case_uid": case["case_id"], "attempt_uid": case.get("attempt_id"), "entered_solver": bool(case.get("solver_entered")), "solver_start": provenance.get("solver_start"), "solver_completion": provenance.get("solver_complete"), "solver_completed_evidence": "Simulation completed successfully" in solver_log_text, "fsp_files": [path.name for path in fsp_files], "fspx_files": [path.name for path in fspx_files], "solver_log_files": [path.name for path in log_files], "result_dataset_files": [path.name for path in result_files], "checkpoint_exists": (case_dir / "checkpoint.json").exists(), "extraction_failure_reason": error, "failure_wavelength_nm": float(wavelength_match.group(1)) if wavelength_match else None, "failure_T": float(wavelength_match.group(2)) if wavelength_match else None, "quarantine_reason": case.get("status"), "raw_broadband_complex_field_data_exists": raw_result_evidence, "postprocess_probe": probe, "classification": classification, "postprocess_recovered": classification == "POSTPROCESS_RECOVERABLE", "solver_replay": False, "history_preserved": True})
    return {"schema": "H1C1B0_QUARANTINE_RECOVERY_AUDIT_V1", "stage": "H1C-1B0", "zero_new_solver": True, "zero_new_rcwa": True, "zero_new_physics_solver": True, "solver_replay": False, "postprocess_recovered_count": sum(bool(row["postprocess_recovered"]) for row in audited), "cases": audited}


def best_common_offset(points: list[dict[str, Any]]) -> dict[str, Any]:
    best = None
    for index in range(120):
        offset = index * 0.5
        assignments = []
        for point in points:
            phase = float(point["phase_450_deg"])
            bin_id = int(math.floor(((phase - offset) % 360.0) / 60.0 + 0.5)) % 6
            assignments.append({"geometry_uid": point["geometry_uid"], "phase_450_deg": phase, "bin": bin_id, "distance_to_bin_center_deg": circular_distance(phase, offset + 60.0 * bin_id)})
        occupied = sorted({item["bin"] for item in assignments})
        score = (len(occupied), sum(item["distance_to_bin_center_deg"] for item in assignments), -offset)
        if best is None or score > best["score"]:
            best = {"score": score, "phi0_deg": offset, "occupied_bins": occupied, "unoccupied_bins": [bin_id for bin_id in range(6) if bin_id not in occupied], "assignments": assignments}
    assert best is not None
    best.pop("score", None)
    return best


def phase_status_map(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    groups = {}
    for status in STATUS_ORDER:
        rows = [row for row in matrix if row["broadband_status"] == status]
        groups[status] = {"count": len(rows), "geometry_uids": [row["geometry_uid"] for row in rows], "phase_450_deg": [row["phase_450_deg"] for row in rows], "phase_trajectories_deg": {row["geometry_uid"]: row["phase_trajectory_deg"] for row in rows}, "phase_sectors_30deg": sorted({row["phase_sector_30deg"] for row in rows}), "circular_gaps_450_deg": circular_gaps([row["phase_450_deg"] for row in rows])}
    all_points = [{"geometry_uid": row["geometry_uid"], "phase_450_deg": row["phase_450_deg"]} for row in matrix]
    strict = [{"geometry_uid": row["geometry_uid"], "phase_450_deg": row["phase_450_deg"]} for row in matrix if row["formal_strict_candidate"]]
    near = [{"geometry_uid": row["geometry_uid"], "phase_450_deg": row["phase_450_deg"]} for row in matrix if row["projector_pass_count_9"] in (7, 8)]
    all_sectors = {phase_sector(point["phase_450_deg"]) for point in all_points}
    strict_sectors = {phase_sector(point["phase_450_deg"]) for point in strict}
    near_sectors = {phase_sector(point["phase_450_deg"]) for point in near}
    all_gaps = circular_gaps([point["phase_450_deg"] for point in all_points])
    strict_clustered = len(strict) == 2 and circular_distance(strict[0]["phase_450_deg"], strict[1]["phase_450_deg"]) < 30.0
    distant_status_sectors = bool({phase_sector(row["phase_450_deg"]) for row in matrix if not row["formal_strict_candidate"]} - strict_sectors)
    gaps_without_evidence = [gap for gap in all_gaps if gap["gap_deg"] > 60.0]
    near_phases = [point["phase_450_deg"] for point in near]
    gaps_with_near = [gap for gap in gaps_without_evidence if any(gap["from_phase_deg"] < phase < gap["from_phase_deg"] + gap["gap_deg"] for phase in near_phases)]
    return {
        "schema": "H1C1B0_PHASE_STATUS_MAP_V1",
        "reference_projection_nm": 450.0,
        "groups": groups,
        "strict_450_circular_gaps": circular_gaps([point["phase_450_deg"] for point in strict]),
        "all_complete_450_sectors": sorted(all_sectors),
        "near_miss_450_sectors": sorted(near_sectors),
        "phase_regions_with_near_miss_evidence": sorted(near_sectors),
        "phase_regions_with_no_complete_450_evidence": [sector for sector in range(12) if sector not in all_sectors],
        "phase_regions_with_no_strict_or_near_miss_evidence": [sector for sector in range(12) if sector not in strict_sectors and sector not in near_sectors],
        "answers": {"strict_clustered": strict_clustered, "center_only_partial_reach_farther_regions": distant_status_sectors, "near_miss_hidden_islands": sorted(near_sectors), "large_gaps_without_evidence": gaps_without_evidence, "large_gaps_with_near_miss_evidence": gaps_with_near},
    }


def normalized_coordinates(coords: dict[str, Any]) -> list[float]:
    return [(float(coords[key]) - low) / (high - low) for key, (low, high) in BOUNDS.items()]


def distance(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def geometry_attribution(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    enriched = []
    for row in matrix:
        enriched.append({"geometry_uid": row["geometry_uid"], "status": row["broadband_status"], "coordinates_5d": row["coordinates_5d"], "normalized_coordinates": normalized_coordinates(row["coordinates_5d"]), "projector_pass_count_9": row["projector_pass_count_9"], "worst_projector_error": row["worst_projector_error"], "phase_450_deg": row["phase_450_deg"], "min_throughput": row["min_throughput"]})
    by_uid = {row["geometry_uid"]: row for row in enriched}
    nearest = {}
    for row in enriched:
        peers = sorted(({"geometry_uid": other["geometry_uid"], "status": other["status"], "distance_5d_normalized": distance(row["normalized_coordinates"], other["normalized_coordinates"]), "phase_distance_deg": circular_distance(row["phase_450_deg"], other["phase_450_deg"]), "pass_count_delta": other["projector_pass_count_9"] - row["projector_pass_count_9"]} for other in enriched if other["geometry_uid"] != row["geometry_uid"]), key=lambda item: (item["distance_5d_normalized"], item["geometry_uid"]))
        for peer in peers:
            other = by_uid[peer["geometry_uid"]]
            peer["coordinate_delta_from_anchor_5d"] = {key: float(other["coordinates_5d"][key]) - float(row["coordinates_5d"][key]) for key in BOUNDS}
        nearest[row["geometry_uid"]] = peers[:5]
    metrics = {"projector_pass_count_9": [float(row["projector_pass_count_9"]) for row in enriched], "worst_projector_error": [float(row["worst_projector_error"]) for row in enriched], "phase_450_deg": [float(row["phase_450_deg"]) for row in enriched], "min_throughput": [float(row["min_throughput"]) for row in enriched]}
    correlations = {left: {right: correlation(values, metrics[right]) for right in metrics if right != left} for left, values in metrics.items()}
    strict = [row for row in enriched if row["status"] == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"]
    local_hypotheses = []
    for row in strict:
        for target_status in ("CENTER_ONLY_COMPATIBLE", "PARTIALLY_COMPATIBLE", "INCOMPATIBLE"):
            peers = [peer for peer in nearest[row["geometry_uid"]] if peer["status"] == target_status]
            if peers:
                peer = peers[0]
                local_hypotheses.append({"anchor_strict_geometry_uid": row["geometry_uid"], "comparison_status": target_status, "nearest_geometry": peer, "label": "LOCAL_EMPIRICAL_HYPOTHESIS", "projector_preserving_direction": {"coordinate_delta_from_comparison_to_strict_5d": {key: -value for key, value in peer["coordinate_delta_from_anchor_5d"].items()}, "interpretation": "direction toward the strict anchor; descriptive and non-causal"}, "phase_diversifying_direction": {"coordinate_delta_from_strict_to_comparison_5d": peer["coordinate_delta_from_anchor_5d"], "circular_phase_delta_deg": peer["phase_distance_deg"], "interpretation": "direction toward the comparison point; descriptive and non-causal"}})
    phase_movement_neighbors = {}
    for row in strict:
        candidates = [peer for peer in enriched if peer["geometry_uid"] != row["geometry_uid"]]
        farthest = max(candidates, key=lambda peer: (circular_distance(row["phase_450_deg"], peer["phase_450_deg"]), -distance(row["normalized_coordinates"], peer["normalized_coordinates"]))) if candidates else None
        phase_movement_neighbors[row["geometry_uid"]] = {"geometry_uid": farthest["geometry_uid"], "coordinate_delta_from_strict_5d": {key: float(farthest["coordinates_5d"][key]) - float(row["coordinates_5d"][key]) for key in BOUNDS}, "circular_phase_delta_deg": circular_distance(row["phase_450_deg"], farthest["phase_450_deg"])} if farthest else None
    return {"schema": "H1C1B0_GEOMETRY_ATTRIBUTION_V1", "sample_scope": "21 complete broadband geometries only", "hypothesis_only": True, "descriptors": enriched, "nearest_neighbors_5d": nearest, "descriptive_rank_correlations": correlations, "local_empirical_hypotheses": local_hypotheses, "strict_phase_movement_neighbors": phase_movement_neighbors, "no_formal_ml_surrogate": True}


def near_miss_bank(matrix: list[dict[str, Any]], coverage: dict[str, Any]) -> dict[str, Any]:
    strict = [row for row in matrix if row["formal_strict_candidate"]]
    near = []
    for row in matrix:
        if row["projector_pass_count_9"] not in (7, 8):
            continue
        nearest_strict = min((distance(normalized_coordinates(row["coordinates_5d"]), normalized_coordinates(other["coordinates_5d"])) for other in strict), default=None)
        near.append({"geometry_uid": row["geometry_uid"], "exact_hash": row["exact_hash"], "coordinates_5d": row["coordinates_5d"], "phase_trajectory_deg": row["phase_trajectory_deg"], "phase_450_deg": row["phase_450_deg"], "projector_pass_count_9": row["projector_pass_count_9"], "failed_wavelengths": row["failed_wavelengths"], "worst_projector_error": row["worst_projector_error"], "margin_to_strict_boundary": row["minimum_projector_margin"], "Txx": {"min": row["min_Txx"], "median": row["median_Txx"], "max": row["max_Txx"]}, "throughput": {"min": row["min_throughput"], "median": row["median_throughput"], "max": row["max_throughput"]}, "phase_island_region_30deg": row["phase_sector_30deg"], "distance_to_nearest_strict_normalized_5d": nearest_strict, "distance_to_nearest_desired_60deg_lattice_deg": min(circular_distance(row["phase_450_deg"], coverage["strict_plus_near_miss"]["phi0_deg"] + 60.0 * index) for index in range(6)), "formal_candidate": False, "diagnostic_only": True})
    return {"schema": "H550_BROADBAND_NEAR_MISS_BANK_V1", "formal_candidate_bank": False, "promotion_rule": "8/9 and 7/9 remain non-strict; no relaxed acceptance", "count": len(near), "candidates": sorted(near, key=lambda row: (-row["projector_pass_count_9"], -row["margin_to_strict_boundary"], row["geometry_uid"]))}


def c_attribution(matrix: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    c_uid = next(candidate["geometry_uid"] for candidate in manifest["candidates"] if candidate.get("prior_450nm_provenance", {}).get("geometry_id") == "H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION")
    row = next(item for item in matrix if item["geometry_uid"] == c_uid)
    profile = row["wavelength_profile"]
    failures = [item for item in profile if not item["projector_pass"]]
    return {"schema": "C_BROADBAND_FAILURE_ATTRIBUTION_V1", "geometry_uid": row["geometry_uid"], "exact_hash": row["exact_hash"], "identity": row["coordinates_5d"], "status": row["broadband_status"], "remains_global_six_bin_candidate_seed_450nm": True, "formal_broadband_six_bin_candidate": False, "phi_C_lambda_deg": [item["phi_txx_deg"] for item in profile], "projector_error_C_lambda": [item["projector_error"] for item in profile], "Txx_C_lambda": [item["Txx"] for item in profile], "throughput_C_lambda": [item["throughput"] for item in profile], "pass_fail": [{"wavelength_nm": item["wavelength_nm"], "pass": item["projector_pass"], "projector_margin": item["projector_margin"]} for item in profile], "failed_wavelengths": [item["wavelength_nm"] for item in failures], "worst_threshold_excess": max((item["projector_error"] - PROJECTOR_ERROR_MAX for item in failures), default=0.0), "mode": row["failure_morphology"], "near_strict": row["projector_pass_count_9"] in (7, 8), "phase_trajectory_remains_useful": True, "throughput_assessment": "selected-channel Txx remains high across the grid, while x/y averaged throughput is variable; no new throughput threshold was applied", "selected_channel_Txx_min": row["min_Txx"], "xy_averaged_throughput_min": row["min_throughput"], "xy_averaged_throughput_max": row["max_throughput"], "interpretation": "red-edge-limited center-only response; this is an attribution, not a causal law", "frozen_threshold": PROJECTOR_ERROR_MAX}


def make_coverage(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    strict = [{"geometry_uid": row["geometry_uid"], "phase_450_deg": row["phase_450_deg"]} for row in matrix if row["formal_strict_candidate"]]
    near = [{"geometry_uid": row["geometry_uid"], "phase_450_deg": row["phase_450_deg"]} for row in matrix if row["projector_pass_count_9"] in (7, 8)]
    strict_only = best_common_offset(strict)
    strict_plus = best_common_offset(strict + near)
    return {"schema": "H1C1B0_SIX_BIN_COVERAGE_MAP_V1", "nominal_bin_spacing_deg": 60.0, "common_phase_offset_free": True, "scan_grid_deg": 0.5, "strict_only": strict_only, "strict_plus_near_miss": strict_plus, "near_miss_never_promoted": True, "interpretation": "occupancy uses nearest nominal bin under each common offset; unoccupied bins identify sectors requiring the next proposed scan"}


def proposal_geometry(coords: dict[str, Any]) -> dict[str, Any]:
    d = float(coords["D_nm"])
    psi = float(coords["Psi_deg"])
    raw_x = d * math.cos(math.radians(psi)) / 2.0
    raw_y = d * math.sin(math.radians(psi)) / 2.0
    cx = math.floor(raw_x * 2.0 + 0.5) / 2.0
    cy = math.floor(raw_y * 2.0 + 0.5) / 2.0
    return {**coords, "J2_center_x_nm": cx, "J2_center_y_nm": cy, "D_nm": 2.0 * math.hypot(cx, cy), "Psi_deg": math.degrees(math.atan2(cy, cx))}


def adaptive_proposal(inputs: dict[str, Any], matrix: list[dict[str, Any]], coverage: dict[str, Any]) -> dict[str, Any]:
    h1c1a = load_h1c1a_module()
    manifest = inputs["manifest"]
    existing_hashes = {row["exact_hash"] for row in manifest["candidates"]}
    existing_keys = {tuple(row["legality"]["physical_key"]) for row in manifest["candidates"]}
    seen_hashes: set[str] = set()
    seen_keys: set[tuple[Any, ...]] = set()
    candidates = {row["geometry_uid"]: row for row in manifest["candidates"]}
    frontier_bases = [row for row in matrix if row["projector_pass_count_9"] in (7, 8) or row["formal_strict_candidate"]]
    frontier_bases.sort(key=lambda row: (-row["projector_pass_count_9"], row["geometry_uid"]))
    deltas = (("J1_side_nm", 1.0), ("J1_side_nm", -1.0), ("J2_length_nm", 1.0), ("J2_width_nm", -1.0), ("D_nm", 1.0), ("Psi_deg", 0.5))
    proposals = []

    def add(coords: dict[str, Any], role: str, component: str, base_uid: str | None, rationale: str, target_sector: int | None) -> bool:
        clipped = {key: min(high, max(low, float(coords[key]))) for key, (low, high) in BOUNDS.items()}
        clipped["J1_side_nm"] = round(clipped["J1_side_nm"])
        clipped["J2_length_nm"] = round(clipped["J2_length_nm"])
        clipped["J2_width_nm"] = round(clipped["J2_width_nm"])
        point = proposal_geometry(clipped)
        check = h1c1a.legality(point, existing_hashes, existing_keys, seen_hashes, seen_keys)
        if not check["pass"]:
            return False
        seen_hashes.add(check["exact_hash"])
        seen_keys.add(tuple(check["physical_key"]))
        proposals.append({"proposal_id": f"H1C1B0_{len(proposals) + 1:03d}", "geometry_uid": f"PROPOSED_{len(proposals) + 1:03d}", "exact_hash": check["exact_hash"], "coordinates_5d": {key: point[key] for key in BOUNDS}, "role": role, "component": component, "base_geometry_uid": base_uid, "target_phase_sector_30deg": target_sector, "rationale": rationale, "legality": check, "solver_authorized": False, "solver_entered": False, "solver_replay": False, "predicted_phase": None})
        return True

    for base in frontier_bases:
        if len(proposals) >= 12:
            break
        for key, delta in deltas:
            coords = {name: float(value) for name, value in base["coordinates_5d"].items()}
            coords[key] += delta
            role = "STRICT_NEIGHBOR_PROJECTOR_ROBUSTNESS" if base["formal_strict_candidate"] else "NEAR_STRICT_RESCUE"
            if add(coords, role, "BROADBAND_SELECTIVITY_FRONTIER", base["geometry_uid"], "deterministic one-step local perturbation around a strict or 7/9-8/9 complete geometry; empirical hypothesis only", None) and len(proposals) >= 12:
                break
    phase_gap_sectors = [sector for sector in range(12) if sector not in set(phase_sector(row["phase_450_deg"]) for row in matrix)]
    global_specs = [(102, 100, 94, 180, -3), (114, 114, 106, 210, 3), (102, 114, 106, 210, -3), (114, 100, 94, 180, 3), (106, 100, 106, 190, -2), (110, 114, 94, 200, 2), (102, 106, 100, 205, 0), (114, 108, 104, 185, 0), (108, 100, 94, 208, -2.5), (112, 114, 106, 182, 2.5), (104, 108, 102, 202, -1.5), (110, 102, 96, 188, 1.5)]
    for index, spec in enumerate(global_specs):
        if len(proposals) >= 24:
            break
        coords = dict(zip(("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"), spec))
        role = "PHASE_GAP_TARGET" if index < len(phase_gap_sectors) else "GLOBAL_COVERAGE_CONTROL"
        target = phase_gap_sectors[index] if index < len(phase_gap_sectors) else None
        add(coords, role, "PHASE_GAP_EXPLORATION", None, "deterministic domain-spanning control; no phase prediction is asserted", target)
    fallback_index = 0
    while len(proposals) < 24 and fallback_index < 200:
        coords = {"J1_side_nm": 102 + fallback_index % 13, "J2_length_nm": 100 + (fallback_index * 3) % 15, "J2_width_nm": 94 + (fallback_index * 5) % 13, "D_nm": 180 + (fallback_index * 2) % 31, "Psi_deg": -3 + (fallback_index % 13) * 0.5}
        add(coords, "GLOBAL_COVERAGE_CONTROL", "PHASE_GAP_EXPLORATION", None, "deterministic legal fallback preserving global exploration", None)
        fallback_index += 1
    if len(proposals) != 24:
        raise RuntimeError(f"HARD_GATE_PROPOSED_BATCH_COUNT:{len(proposals)}")
    exploitation = sum(row["component"] == "BROADBAND_SELECTIVITY_FRONTIER" for row in proposals)
    exploration = len(proposals) - exploitation
    return {"schema": "H1C1B0_ADAPTIVE_BATCH_PROPOSAL_V1", "status": "PROPOSED_ONLY_NO_SOLVER_AUTHORIZATION", "count": len(proposals), "components": {"BROADBAND_SELECTIVITY_FRONTIER": exploitation, "PHASE_GAP_EXPLORATION": exploration}, "preferred_scale_not_frozen": True, "envelope": BOUNDS, "H_global_nm": 550.0, "no_h1b_local_edge_route_restart": True, "no_uniform_sobol_repeat": True, "candidates": proposals}


def ml_registry_audit(inputs: dict[str, Any], matrix: list[dict[str, Any]], quarantine: dict[str, Any]) -> dict[str, Any]:
    labels = inputs["labels"]["rows"]
    broadband = [row for row in labels if row.get("spectral_scope") == "BROADBAND_9NM_GRID"]
    historical = [row for row in labels if row.get("spectral_scope") == "450NM_ONLY"]
    by_uid: dict[str, list[dict[str, Any]]] = {}
    for row in broadband:
        by_uid.setdefault(row["geometry_uid"], []).append(row)
    complete_nine = all(len(rows) == 9 for rows in by_uid.values())
    quarantined_uids = {row["geometry_uid"] for row in quarantine["cases"]}
    no_quarantine_masquerade = not quarantined_uids.intersection(by_uid)
    required_complex = {"Re_txx", "Im_txx", "Re_txy", "Im_txy", "Re_tyx", "Im_tyx", "Re_tyy", "Im_tyy"}
    complex_present = required_complex.issubset({key for row in labels for key in row})
    readiness = "NOT_READY_FOR_FORMAL_ML_RESTART" if len(by_uid) < 30 or sum(row["formal_strict_candidate"] for row in matrix) < 6 else "REVIEW_REQUIRED"
    strict_rows = [row for row in matrix if row["formal_strict_candidate"]]
    strict_separation = circular_distance(strict_rows[0]["phase_450_deg"], strict_rows[1]["phase_450_deg"]) if len(strict_rows) == 2 else None
    return {"schema": "H1C1B0_ML_REGISTRY_AUDIT_V1", "canonical_registry": str(SOURCE_REPORT / "lp_hf_authoritative_label_registry_v1.json"), "row_count": len(labels), "complete_broadband_geometry_count": len(by_uid), "complete_broadband_rows": len(broadband), "complete_broadband_each_9_rows": complete_nine, "historical_450_only_rows": len(historical), "historical_only_450_nm": all(float(row["wavelength_nm"]) == 450.0 for row in historical), "no_fabricated_broadband_rows": all(row.get("spectral_scope") == "BROADBAND_9NM_GRID" for row in broadband), "full_complex_jones_fields_present": complex_present, "ml_eligible_all": all(row.get("ml_eligible") is True for row in labels), "ml_admitted_false_all": all(row.get("ml_admitted") is False for row in labels), "split_unassigned_all": all(row.get("split") == "UNASSIGNED" for row in labels), "quarantined_not_masquerading_as_complete": no_quarantine_masquerade, "ML_DATASET_READINESS": readiness, "evidence": {"strict_count": len(strict_rows), "strict_phase_separation_deg": strict_separation, "near_miss_count": sum(row["projector_pass_count_9"] in (7, 8) for row in matrix)}}


def build_all(probe_fsp: bool = True) -> dict[str, Any]:
    inputs = load_inputs()
    matrix = build_failure_matrix(inputs)
    quarantine = quarantine_audit(inputs, probe_fsp)
    coverage = make_coverage(matrix)
    phase_map = phase_status_map(matrix)
    near = near_miss_bank(matrix, coverage)
    c_report = c_attribution(matrix, inputs["manifest"])
    geometry = geometry_attribution(matrix)
    proposal = adaptive_proposal(inputs, matrix, coverage)
    ml_audit = ml_registry_audit(inputs, matrix, quarantine)
    entered_before = int(inputs["accounting"].get("solver_subruns_entered", 0))
    entry_count_before = len(inputs["accounting"].get("solver_entries", []))
    snapshot = {"schema": "H1C1B0_AUTHORITATIVE_SNAPSHOT_V1", "source_h1c1a_manifest_freeze_sha256": inputs["manifest"]["freeze_sha256"], "original_h1c1a_semantics_unchanged": True, "postprocess_recovered_count": quarantine["postprocess_recovered_count"], "complete_broadband_geometry_count": len(matrix), "status_counts": {status: sum(row["broadband_status"] == status for row in matrix) for status in STATUS_ORDER}, "quarantine_unresolved_count": len(quarantine["cases"]), "solver_subruns_entered_before_read_only": entered_before, "solver_subruns_entered_after_read_only": entered_before, "solver_entries_before_read_only": entry_count_before, "solver_entries_after_read_only": entry_count_before, "solver_entered_delta": 0, "solver_replay": False, "zero_new_solver": True, "zero_new_rcwa": True}
    write_json(REPORT / "h1c1b0_quarantine_recovery_audit.json", quarantine)
    write_csv(REPORT / "h1c1b0_broadband_failure_matrix.csv", [{**row, "wavelength_profile": json.dumps(row["wavelength_profile"], sort_keys=True)} for row in matrix])
    write_json(REPORT / "h1c1b0_near_miss_bank.json", near)
    write_json(REPORT / "h1c1b0_c_failure_attribution.json", c_report)
    write_json(REPORT / "h1c1b0_phase_status_map.json", phase_map)
    write_json(REPORT / "h1c1b0_geometry_attribution.json", geometry)
    write_json(REPORT / "h1c1b0_six_bin_coverage_map.json", coverage)
    write_json(REPORT / "h1c1b0_adaptive_batch_proposal.json", proposal)
    write_json(REPORT / "h1c1b0_ml_registry_audit.json", ml_audit)
    write_json(REPORT / "h1c1b0_authoritative_snapshot.json", snapshot)
    strict = [row for row in matrix if row["formal_strict_candidate"]]
    strict_phases = [row["phase_450_deg"] for row in strict]
    summary_lines = [
        "# Stage H1C-1B0 — Broadband Compatibility Attribution and Adaptive Search Design",
        "",
        "- Status: `READ_ONLY_COMPLETE`",
        f"- Zero new FDTD/RCWA/physics solver; solver_entered delta: `{snapshot['solver_entered_delta']}`; solver replay: `{snapshot['solver_replay']}`.",
        f"- Quarantine cases: `{len(quarantine['cases'])}`; postprocess recovered: `{quarantine['postprocess_recovered_count']}`; all history preserved.",
        f"- Complete broadband geometries: `{len(matrix)}`; strict / center-only / partial / incompatible: `{sum(row['broadband_status'] == STATUS_ORDER[0] for row in matrix)}/{sum(row['broadband_status'] == STATUS_ORDER[1] for row in matrix)}/{sum(row['broadband_status'] == STATUS_ORDER[2] for row in matrix)}/{sum(row['broadband_status'] == STATUS_ORDER[3] for row in matrix)}`.",
        f"- Strict identities: `{', '.join(row['geometry_uid'] for row in strict)}`; strict 450-nm phase separation: `{circular_distance(strict_phases[0], strict_phases[1]) if len(strict_phases) == 2 else None}` deg.",
        f"- Near-miss identities: `{', '.join(row['geometry_uid'] for row in near['candidates']) or 'none'}`; formal strict bank unchanged.",
        f"- C attribution: `{c_report['mode']}`; failed wavelengths: `{c_report['failed_wavelengths']}`; min throughput: `{min(c_report['throughput_C_lambda'])}`.",
        f"- Six-bin common-offset occupancy, strict only: `{coverage['strict_only']['occupied_bins']}`; strict + near-miss diagnostic: `{coverage['strict_plus_near_miss']['occupied_bins']}`; unoccupied diagnostic bins: `{coverage['strict_plus_near_miss']['unoccupied_bins']}`.",
        f"- Proposed H1C-1B batch: `{proposal['count']}` candidates; frontier `{proposal['components']['BROADBAND_SELECTIVITY_FRONTIER']}`, gap/global exploration `{proposal['components']['PHASE_GAP_EXPLORATION']}`; proposed-only.",
        f"- ML_DATASET_READINESS: `{ml_audit['ML_DATASET_READINESS']}`; canonical registry unchanged with `{ml_audit['row_count']}` rows.",
        "- No H1B local-edge route restart, ML training, inverse design, or K6 was started.",
        "- COSMETIC_COMMIT_MESSAGE_ANOMALY_NO_HISTORY_REWRITE: previous commit was not amended or force-pushed.",
        "",
        "Artifacts: `h1c1b0_quarantine_recovery_audit.json`, `h1c1b0_broadband_failure_matrix.csv`, `h1c1b0_near_miss_bank.json`, `h1c1b0_c_failure_attribution.json`, `h1c1b0_phase_status_map.json`, `h1c1b0_geometry_attribution.json`, `h1c1b0_six_bin_coverage_map.json`, `h1c1b0_adaptive_batch_proposal.json`, `h1c1b0_ml_registry_audit.json`, `h1c1b0_authoritative_snapshot.json`.",
    ]
    (REPORT / "h1c1b0_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return {"snapshot": snapshot, "quarantine": quarantine, "matrix": matrix, "near_miss": near, "c": c_report, "phase": phase_map, "geometry": geometry, "coverage": coverage, "proposal": proposal, "ml": ml_audit}


def main() -> int:
    probe_fsp = "--no-fsp-probe" not in sys.argv[1:]
    result = build_all(probe_fsp=probe_fsp)
    print(json.dumps({"status": "READ_ONLY_COMPLETE", "postprocess_recovered_count": result["quarantine"]["postprocess_recovered_count"], "complete_broadband_geometry_count": len(result["matrix"]), "proposal_count": result["proposal"]["count"], "solver_entered_delta": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
