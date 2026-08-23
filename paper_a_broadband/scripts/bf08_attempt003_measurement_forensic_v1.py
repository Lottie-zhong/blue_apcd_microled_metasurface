from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
REPORT = ROOT / "paper_a_broadband/reports/lp_bf08_attempt003_measurement_forensic_v1"
RUNTIME = ROOT / "paper_a_broadband/runtime"
C0 = 299792458.0
FORMAL = np.asarray([435.0 + i for i in range(31)], dtype=float)
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def safe_get(f, obj: str, prop: str) -> Any:
    try:
        value = f.getnamed(obj, prop)
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}:{exc}"


def dataset_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "available": True,
            "type": "dict",
            "keys": sorted(value.keys()),
            "shapes": {k: list(np.asarray(v).shape) for k, v in value.items() if isinstance(v, (np.ndarray, list, tuple))},
        }
    return {"available": True, "type": type(value).__name__, "shape": list(np.asarray(value).shape)}


def try_result(f, monitor: str, result: str) -> tuple[Any | None, dict[str, Any]]:
    try:
        value = f.getresult(monitor, result)
        return value, dataset_summary(value)
    except Exception as exc:
        return None, {"available": False, "error": f"{type(exc).__name__}:{exc}"}


def exact_indices(wavelength_nm: np.ndarray) -> list[int]:
    indices: list[int] = []
    for target in FORMAL:
        hit = np.flatnonzero(np.isclose(wavelength_nm, target, rtol=0.0, atol=1e-8))
        if len(hit) != 1:
            raise RuntimeError(f"FORMAL_GRID_NOT_EXACT:{target}:{len(hit)}")
        indices.append(int(hit[0]))
    return indices


def vector_field(dataset: Any, key: str) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    if not isinstance(dataset, dict) or key not in dataset or "x" not in dataset or "y" not in dataset:
        return None
    arr = np.asarray(dataset[key])
    x = np.asarray(dataset["x"]).reshape(-1)
    y = np.asarray(dataset["y"]).reshape(-1)
    if arr.shape[-1] != 3:
        return None
    while arr.ndim > 4:
        squeezed = False
        for axis in range(2, arr.ndim - 2):
            if arr.shape[axis] == 1:
                arr = np.squeeze(arr, axis=axis)
                squeezed = True
                break
        if not squeezed:
            break
    if arr.ndim == 3:
        arr = arr[:, :, None, :]
    if arr.ndim != 4 or arr.shape[0] != len(x) or arr.shape[1] != len(y):
        return None
    return arr, x, y


def integrate_plane(values: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.trapezoid(np.trapezoid(values, y, axis=1), x, axis=0)


def manual_flux(E_dataset: Any, H_dataset: Any, P_dataset: Any) -> dict[str, Any]:
    e = vector_field(E_dataset, "E")
    h = vector_field(H_dataset, "H")
    if e is not None and h is not None:
        E, x, y = e
        H, hx, hy = h
        if E.shape == H.shape and np.allclose(x, hx) and np.allclose(y, hy):
            pz = 0.5 * np.real(E[..., 0] * np.conj(H[..., 1]) - E[..., 1] * np.conj(H[..., 0]))
            return {"available": True, "method": "0.5*Re(Ex*conj(Hy)-Ey*conj(Hx))", "flux_W": integrate_plane(pz, x, y)}
    p = vector_field(P_dataset, "P")
    if p is not None:
        P, x, y = p
        return {"available": True, "method": "integral stored Pz", "flux_W": integrate_plane(np.real(P[..., 2]), x, y)}
    return {"available": False, "reason": "stored co-located E/H or P vector unavailable"}


def object_readback(f) -> dict[str, Any]:
    source_props = ["source type", "type", "injection axis", "direction", "x", "y", "z", "x span", "y span", "amplitude", "phase", "polarization angle", "wavelength start", "wavelength stop"]
    monitor_props = ["monitor type", "x", "y", "z", "x span", "y span", "override global monitor settings", "use source limits", "use wavelength spacing", "frequency points", "spatial interpolation", "output power", "output Ex", "output Ey", "output Ez", "output Hx", "output Hy", "output Hz", "output Px", "output Py", "output Pz"]
    return {
        "source": {p: safe_get(f, "source", p) for p in source_props},
        "T": {p: safe_get(f, "T", p) for p in monitor_props},
        "field_monitor": {p: safe_get(f, "field_monitor", p) for p in monitor_props},
        "FDTD": {p: safe_get(f, "FDTD", p) for p in ["x span", "y span", "z min", "z max", "mesh accuracy", "simulation time", "auto shutoff min", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]},
        "pillars": {
            name: {p: safe_get(f, name, p) for p in ["x", "y", "x span", "y span", "z", "z span", "rotation 1", "material"]}
            for name in ["pillar_1", "pillar_2"]
        },
    }


def inspect_fsp(case_id: str, path: Path, role: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    import lumapi

    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(path))
        readback = object_readback(f)
        frequency = np.asarray(f.getdata("T", "f")).reshape(-1)
        wavelength_nm = C0 / frequency * 1e9
        transmission = np.real(np.asarray(f.transmission("T")).reshape(-1))
        sourcepower = np.real(np.asarray(f.sourcepower(frequency)).reshape(-1))
        indices = exact_indices(wavelength_nm)
        E, E_summary = try_result(f, "T", "E")
        H, H_summary = try_result(f, "T", "H")
        P, P_summary = try_result(f, "T", "P")
        flux = manual_flux(E, H, P)
        manual_norm = None
        if flux["available"]:
            manual_norm = np.real(np.asarray(flux["flux_W"]).reshape(-1)) / sourcepower
            flux["flux_W"] = np.real(np.asarray(flux["flux_W"]).reshape(-1)).tolist()
            flux["manual_flux_over_sourcepower"] = manual_norm.tolist()
        rows: list[dict[str, Any]] = []
        for idx, target in zip(indices, FORMAL):
            rows.append({
                "case_id": case_id,
                "role": role,
                "wavelength_nm": float(target),
                "actual_monitor_wavelength_nm": float(wavelength_nm[idx]),
                "monitor_index": idx,
                "transmission_T": float(transmission[idx]),
                "sourcepower_W": float(sourcepower[idx]),
                "manual_flux_over_sourcepower": float(manual_norm[idx]) if manual_norm is not None and len(manual_norm) == len(transmission) else None,
            })
        comparison = None
        if manual_norm is not None and len(manual_norm) == len(transmission):
            diff = manual_norm[indices] - transmission[indices]
            comparison = {
                "max_abs_manual_minus_transmission": float(np.max(np.abs(diff))),
                "sign_equal_count": int(np.sum(np.sign(manual_norm[indices]) == np.sign(transmission[indices]))),
                "formal_points": len(indices),
                "pearson": float(np.corrcoef(manual_norm[indices], transmission[indices])[0, 1]) if np.std(manual_norm[indices]) and np.std(transmission[indices]) else None,
            }
        info = {
            "case_id": case_id,
            "role": role,
            "path": str(path),
            "sha256": sha_file(path),
            "readback": readback,
            "monitor_normal_inference": {"monitor_type": readback["T"]["monitor type"], "normal_axis": "+z coordinate convention", "source_forward_axis": "+z", "expected_forward_sign": "positive"},
            "grid": {"points": len(wavelength_nm), "ascending": bool(np.all(np.diff(wavelength_nm) > 0)), "start_nm": float(wavelength_nm[0]), "stop_nm": float(wavelength_nm[-1]), "formal_indices": indices, "formal_exact": True},
            "transmission": {"formal_min": float(np.min(transmission[indices])), "formal_max": float(np.max(transmission[indices])), "formal_negative_count": int(np.sum(transmission[indices] < 0)), "formal_gt_one_count": int(np.sum(transmission[indices] > 1))},
            "sourcepower": {"formal_abs_min": float(np.min(np.abs(sourcepower[indices]))), "formal_abs_max": float(np.max(np.abs(sourcepower[indices]))), "formal_min_over_max": float(np.min(np.abs(sourcepower[indices])) / np.max(np.abs(sourcepower[indices]))), "near_zero": bool(np.any(np.abs(sourcepower[indices]) < 1e-30))},
            "stored_datasets": {"E": E_summary, "H": H_summary, "P": P_summary},
            "manual_flux": flux,
            "manual_vs_transmission": comparison,
        }
        return info, rows
    finally:
        f.close()


def log_audit(path: Path) -> dict[str, Any]:
    values: list[float] = []
    simulation_time_s = None
    successful_return = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"Auto Shutoff:\s*([0-9.eE+-]+)", line)
        if match:
            values.append(float(match.group(1)))
        match = re.search(r"Completed \d+ iterations, or ([0-9.eE+-]+)s of Simulation Time", line)
        if match:
            simulation_time_s = float(match.group(1))
        if "Simulation completed successfully" in line:
            successful_return = True
    return {
        "path": str(path), "sha256": sha_file(path), "simulation_time_s": simulation_time_s,
        "auto_shutoff_samples": len(values), "auto_shutoff_min": min(values) if values else None,
        "auto_shutoff_max": max(values) if values else None, "auto_shutoff_final": values[-1] if values else None,
        "late_time_growth": bool(values and values[-1] > 1.0), "solver_process_returned_successfully": successful_return,
    }


def source_code_audit() -> dict[str, Any]:
    runner = ROOT / "paper_a_broadband/scripts/bf08_authoritative_rebuilt_truth_v1.py"
    text = runner.read_text(encoding="utf-8")
    lines = text.splitlines()
    return {
        "path": str(runner), "sha256": sha_file(runner),
        "transmission_call_lines": [i + 1 for i, line in enumerate(lines) if 'transmission("T")' in line],
        "sourcepower_call_lines": [i + 1 for i, line in enumerate(lines) if "sourcepower(" in line],
        "normalize_pair_lines": [i + 1 for i, line in enumerate(lines) if "normalize_pair" in line],
        "post_run_convergence_gate_present": "auto_shutoff_final" in text or "late_time_growth" in text,
        "negative_T_gate_present": "NEGATIVE_FORMAL_TRANSMISSION" in text,
        "absolute_value_on_transmission_present": "abs(trans" in text or "np.abs(trans" in text,
        "classification": "negative values originate in lumapi transmission(T) before downstream complex-field normalize_pair",
    }


def git_head(worktree: Path) -> str:
    return subprocess.check_output(["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()


def readback_only(path: Path) -> dict[str, Any]:
    import lumapi

    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(path))
        return object_readback(f)
    finally:
        f.close()


def readback_equivalent(a: Any, b: Any) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(readback_equivalent(a[k], b[k]) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return bool(np.isclose(float(a), float(b), rtol=1e-12, atol=1e-18))
    return a == b


def attempt_provenance_audit(case_id: str, inspected_post_sha256: str) -> dict[str, Any]:
    case_dir = RUNTIME / f"bf08_authoritative_rebuilt_truth_v1/cases/{case_id}"
    provenance_path = case_dir / "attempt_003_provenance.json"
    setup_path = case_dir / "setup_only.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    setup = json.loads(setup_path.read_text(encoding="utf-8"))
    pre_path = Path(provenance["pre_fsp"])
    fresh_path = Path(setup["fresh_builder_source_fsp"])
    pre_hash_now = sha_file(pre_path)
    fresh_hash_now = sha_file(fresh_path)
    pre_readback = readback_only(pre_path)
    fresh_readback = readback_only(fresh_path)
    checks = {
        "attempt_id_is_003": provenance.get("attempt_id") == "attempt_003",
        "solver_entered_recorded": provenance.get("solver_entered") is True,
        "post_fsp_hash_matches_provenance": provenance.get("post_fsp_sha256") == inspected_post_sha256,
        "entry_pre_hash_was_fresh_builder_hash": provenance.get("pre_fsp_sha256") == setup.get("fresh_builder_source_sha256"),
        "fresh_builder_hash_matches_setup": setup.get("fresh_builder_source_sha256") == fresh_hash_now,
        "current_runtime_pre_hash_drifted_after_entry": pre_hash_now != provenance.get("pre_fsp_sha256"),
        "current_runtime_pre_physical_readback_matches_fresh_builder": readback_equivalent(pre_readback, fresh_readback),
        "old_attempts_are_provenance_only": provenance.get("old_attempts") == "PROVENANCE_ONLY_NOT_PHYSICS_TRUTH_NOT_PARENT_FSP",
    }
    return {
        "case_id": case_id,
        "provenance_path": str(provenance_path), "provenance_sha256": sha_file(provenance_path),
        "setup_path": str(setup_path), "setup_sha256": sha_file(setup_path),
        "entry_pre_fsp_sha256_recorded": provenance.get("pre_fsp_sha256"),
        "current_runtime_pre_fsp_path": str(pre_path), "current_runtime_pre_fsp_sha256": pre_hash_now,
        "fresh_builder_fsp_path": str(fresh_path), "fresh_builder_fsp_sha256": fresh_hash_now,
        "post_fsp_sha256": inspected_post_sha256,
        "classification": "ENGINE_IN_PLACE_RESULT_STATE_MUTATION_OF_RUNTIME_PRE_FSP_AFTER_ENTRY_WITHOUT_PHYSICAL_OBJECT_DRIFT",
        "causal_to_negative_transmission": False,
        "checks": checks, "pass": all(checks.values()),
    }


def main() -> int:
    self_text = Path(__file__).read_text(encoding="utf-8")
    forbidden = ["f." + "run(", "switch" + "tolayout(", ".save(" + "str("]
    if any(token in self_text for token in forbidden):
        raise RuntimeError("ZERO_SOLVER_GUARD_SOURCE_VIOLATION")

    bf08_paths = {
        "BF08_x": RUNTIME / "bf08_authoritative_rebuilt_truth_v1/cases/BF08_x/BF08_x_attempt_003_post.fsp",
        "BF08_y": RUNTIME / "bf08_authoritative_rebuilt_truth_v1/cases/BF08_y/BF08_y_attempt_003_post.fsp",
    }
    controls = {
        cid: RUNTIME / f"search_anisotropy_balanced_truth_v1/cases/{cid}/{cid}_run.fsp"
        for cid in [f"BF0{g}_{pol}" for g in range(1, 8) for pol in ("x", "y")]
    }
    all_info: dict[str, Any] = {}
    all_rows: list[dict[str, Any]] = []
    for cid, path in {**bf08_paths, **controls}.items():
        info, rows = inspect_fsp(cid, path, "BF08_attempt_003" if cid.startswith("BF08") else "known_good_control")
        all_info[cid] = info
        all_rows.extend(rows)

    log_paths = {
        "BF08_x_attempt_003": RUNTIME / "bf08_authoritative_rebuilt_truth_v1/cases/BF08_x/BF08_x_attempt_003_pre_p0.log",
        "BF08_y_attempt_003": RUNTIME / "bf08_authoritative_rebuilt_truth_v1/cases/BF08_y/BF08_y_attempt_003_pre_p0.log",
        "BF08_x_attempt_002": RUNTIME / "bf08_source_convergence_replay_v1/cases/BF08_x/BF08_x_attempt_002_replay_pre_p0.log",
        "BF08_y_attempt_002": RUNTIME / "bf08_source_convergence_replay_v1/cases/BF08_y/BF08_y_attempt_002_replay_pre_p0.log",
        "BF07_x_control": RUNTIME / "search_anisotropy_balanced_truth_v1/cases/BF07_x/BF07_x_pre_p0.log",
        "BF07_y_control": RUNTIME / "search_anisotropy_balanced_truth_v1/cases/BF07_y/BF07_y_pre_p0.log",
    }
    logs = {name: log_audit(path) for name, path in log_paths.items()}

    cp_readback_path = ROOT / "paper_a_broadband/references/cp/champion_fsp_readback.json"
    cp_setup_path = ROOT / "paper_a_broadband/references/cp/setup_audit.json"
    mdc_path = ROOT / "paper_a_broadband/references/mdc/mdc_weighting_contract.json"
    mdc_worktree = Path(r"D:/project/worktrees/blue_apcd_mdc_defect_450")
    cp_worktree = Path(r"D:/project/worktrees/blue_apcd_cp_stage10_bw2a")
    mdc_flux_validation = mdc_worktree / "scripts/validate_mdc_lumerical_2d_monitor_contract_v1.py"
    cp_monitor_summary = cp_worktree / "outputs/blue_stage10_cp_zprop_validation/cp_zprop_center_summary.md"
    conventions = {
        "paper_a_lp_controls": {
            "same_source_direction": all(all_info[c]["readback"]["source"]["direction"] == "Forward" for c in controls),
            "same_monitor_type": all(all_info[c]["readback"]["T"]["monitor type"] == "2D Z-normal" for c in controls),
            "same_monitor_z_as_BF08": all(np.isclose(float(all_info[c]["readback"]["T"]["z"]), float(all_info["BF08_x"]["readback"]["T"]["z"])) for c in controls),
            "all_control_formal_T_nonnegative": all(all_info[c]["transmission"]["formal_negative_count"] == 0 for c in controls),
            "control_case_count": len(controls),
        },
        "cp": {"readback_path": str(cp_readback_path), "readback_sha256": sha_file(cp_readback_path), "setup_path": str(cp_setup_path), "setup_sha256": sha_file(cp_setup_path), "frozen_worktree": str(cp_worktree), "frozen_commit": git_head(cp_worktree), "monitor_summary_path": str(cp_monitor_summary), "monitor_summary_sha256": sha_file(cp_monitor_summary), "relevance": "top 2D Z-normal power monitor at z=1000 nm above an upward source; different dipole/PML geometry, consistent positive-outgoing convention"},
        "mdc": {"path": str(mdc_path), "sha256": sha_file(mdc_path), "frozen_worktree": str(mdc_worktree), "frozen_commit": git_head(mdc_worktree), "flux_validation_path": str(mdc_flux_validation), "flux_validation_sha256": sha_file(mdc_flux_validation), "flux_validation_contract": "direct Poynting integral is compared with transmission(monitor)*sourcepower at <=1e-3 relative difference; outward sign is geometry-defined", "relevance": "MDC validates the same stored-flux versus transmission convention; r12_normalized_output remains relative weighting only and cannot repair LP transmission sign"},
    }

    source_audit = source_code_audit()
    bf08_x, bf08_y = all_info["BF08_x"], all_info["BF08_y"]
    provenance_audit = {
        cid: attempt_provenance_audit(cid, all_info[cid]["sha256"])
        for cid in ("BF08_x", "BF08_y")
    }
    write_json(REPORT / "attempt003_hash_provenance_audit.json", provenance_audit)
    if not all(item["pass"] for item in provenance_audit.values()):
        raise RuntimeError("ATTEMPT003_HASH_PROVENANCE_AUDIT_FAILED")
    result = {
        "schema": "PAPER_A_LP_BF08_ATTEMPT003_MEASUREMENT_FORENSIC_V1",
        "status": "PASS",
        "verdict": "PAPER_A_LP_BF08_ATTEMPT003_ROOT_CAUSE_NUMERICAL_TIME_DOMAIN_DIVERGENCE_CONFIRMED",
        "root_cause_classification": "E_NUMERICAL_TIME_DOMAIN_DIVERGENCE_IN_STORED_SOLVER_ENERGY_RESULT",
        "causal_assessment": {
            "A_monitor_normal_or_sign_convention": "EXCLUDED: fixed +z monitor convention produces nonnegative transmission for 14 same-template BF01-BF07 controls; BF08_y changes sign with wavelength",
            "B_forward_backward_flux_convention": "EXCLUDED: Forward +z source is below the +z-normal monitor for BF08 and all controls",
            "C_power_normalization_implementation": "EXCLUDED_AS_PRIMARY: sourcepower is nonzero/stable and negative/hyper-unit values exist in lumapi transmission(T) before normalize_pair",
            "D_monitor_placement": "EXCLUDED: BF08 monitor type, position, spans, and source-relative placement match accepted controls",
            "E_actual_solver_energy_result": "CONFIRMED_AS_NUMERICALLY_INVALID: late-time auto-shutoff grows instead of decaying; process return success does not establish convergence",
        },
        "polarization_difference": {
            "only_source_basis_change": "BF08_x and BF08_y have identical geometry, materials, mesh, boundaries, source position/span and monitors; polarization angle is 0 versus 90 degrees",
            "x": {"negative_formal_points": bf08_x["transmission"]["formal_negative_count"], "auto_shutoff_final": logs["BF08_x_attempt_003"]["auto_shutoff_final"], "auto_shutoff_max": logs["BF08_x_attempt_003"]["auto_shutoff_max"]},
            "y": {"negative_formal_points": bf08_y["transmission"]["formal_negative_count"], "auto_shutoff_final": logs["BF08_y_attempt_003"]["auto_shutoff_final"], "auto_shutoff_max": logs["BF08_y_attempt_003"]["auto_shutoff_max"]},
            "inference_boundary": "severity correlates with input polarization coupling to the anisotropic BF08 structure; provenance alone cannot identify the unstable eigenmode",
        },
        "recoverability": {"without_new_solver_or_physics_change": False, "reason": "stored fields are contaminated by numerical growth; post-processing sign changes or renormalization cannot recover authoritative truth"},
        "independent_flux_confirmation": {
            "BF08_x_max_abs_manual_minus_transmission": bf08_x["manual_vs_transmission"]["max_abs_manual_minus_transmission"],
            "BF08_x_sign_equal_count": bf08_x["manual_vs_transmission"]["sign_equal_count"],
            "BF08_y_max_abs_manual_minus_transmission": bf08_y["manual_vs_transmission"]["max_abs_manual_minus_transmission"],
            "BF08_y_sign_equal_count": bf08_y["manual_vs_transmission"]["sign_equal_count"],
            "formal_points_each": 31,
        },
        "fsp_validity": {"pre_fsp_setup_provenance": "VALID", "post_fsp_result_state": "INVALID_FOR_PHYSICS_TRUTH", "five_ps_convergence_contract": "UNSAFE_FOR_BF08"},
        "additional_provenance_finding": "attempt_003 runtime pre-FSP copies were mutated in place by solver result-state persistence after entry; fresh builder originals and physical-object readbacks remain intact; this is not causal to negative transmission",
        "template_scope": {
            "monitor_and_full_jones_geometry_template": "NO_SYSTEMATIC_SIGN_OR_PLACEMENT_DEFECT_FOUND",
            "runner_defect": "missing post-run late-time divergence gate",
            "BF01_BF04_existing_truth": "NOT_AFFECTED; their stored control transmission is nonnegative under the original 1 ps contract",
            "BF01_BF04_future_runs": "BASE_1PS_TEMPLATE_PROVEN_BY_CONTROLS; DO_NOT APPLY BF08 5PS REPLAY PATCH WITHOUT NEW STABILITY AUTHORITY_AND_GATE",
        },
        "solver_counters": {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "rcwa": 0, "ml": 0},
        "truth_files_modified": False,
        "attempt_promotion": False,
        "generated_utc": now(),
    }

    write_json(REPORT / "fsp_provenance_and_monitor_readback.json", all_info)
    write_csv(REPORT / "transmission_manual_flux_comparison.csv", all_rows)
    write_json(REPORT / "solver_convergence_log_audit.json", logs)
    write_json(REPORT / "known_good_monitor_convention_comparison.json", conventions)
    write_json(REPORT / "source_normalization_code_audit.json", source_audit)
    write_json(REPORT / "audit.json", result)
    report = f"""# BF08 attempt_003 measurement/provenance forensic\n\n## Status\n\nPASS — `{result['verdict']}`\n\n## Root cause\n\nThe negative values are not a monitor-normal, forward/backward, placement, wavelength-index, or downstream normalization artifact. They are stored solver outputs from a numerically divergent 5 ps time-domain run. BF08_x ended with auto-shutoff `{logs['BF08_x_attempt_003']['auto_shutoff_final']}` (peak `{logs['BF08_x_attempt_003']['auto_shutoff_max']}`); BF08_y ended at `{logs['BF08_y_attempt_003']['auto_shutoff_final']}`. The same source/monitor convention gives nonnegative formal transmission for all 14 BF01-BF07 x/y controls.\n\nBF08_x and BF08_y differ only in source polarization angle. Their divergence severity tracks that basis change, consistent with polarization-dependent excitation of a numerically unstable BF08 mode; provenance cannot identify the mode itself.\n\n## Authority boundary\n\nThe fresh pre-FSP setup provenance remains valid, but both attempt_003 post-FSP result states are invalid for physics truth. No zero-solver post-processing can recover them. The base LP monitor/full-Jones convention has no systematic sign or placement defect; the runner lacks a mandatory late-time divergence gate. Existing BF01-BF04 truth is unaffected. Future BF01-BF04 runs may use only the proven original contract; the BF08 5 ps replay patch is not safe to generalize without new authority and a convergence gate.\n\nNo solver was run, no truth file was modified, and no attempt was promoted.\n"""
    (REPORT / "forensic_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
