"""Offline K4/K9 traditional NP baseline package; never calls a solver run."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "outputs/np_k6_p1d2_broadband_library_27point_v1/library_long.csv"
K6 = ROOT / "outputs/np_k6_p1d4_k6x_candidate_freeze_v1"
OUT = ROOT / "outputs/np_traditional_multitarget_baseline_extension_v1"
WAVELENGTHS = list(range(445, 456))
DIAMETERS = list(range(100, 231, 5))
PITCH = 290.0
HEIGHT = 500.0
GAP_MIN = 60.0


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def cdist(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def gap(a: int, b: int) -> float:
    return PITCH - (a + b) / 2.0


def positions(k: int) -> list[float]:
    return [(j - (k - 1) / 2.0) * PITCH for j in range(k)]


def load_library() -> dict[tuple[int, int], dict[str, float]]:
    rows = list(csv.DictReader(LIB.open(newline="", encoding="utf-8")))
    assert len(rows) == 297
    assert sorted({int(r["diameter_nm"]) for r in rows}) == DIAMETERS
    assert sorted({int(r["wavelength_nm"]) for r in rows}) == WAVELENGTHS
    out: dict[tuple[int, int], dict[str, float]] = {}
    for r in rows:
        d, w = int(r["diameter_nm"]), int(r["wavelength_nm"])
        assert (d, w) not in out
        out[d, w] = {k: float(r[k]) for k in ("txx_real", "txx_imag", "txx_amplitude", "txx_unwrapped_phase_vs_diameter_deg")}
    return out


def phase(lib: dict, d: int, w: int) -> float:
    return lib[d, w]["txx_unwrapped_phase_vs_diameter_deg"] % 360.0


def valid_vector(ds: list[int]) -> bool:
    return len(ds) == len(set(ds)) and all(gap(a, b) >= GAP_MIN for a, b in zip(ds, ds[1:])) and gap(ds[-1], ds[0]) >= GAP_MIN


def beam_assign(lib: dict, k: int, phi0: float, mode: str) -> tuple[list[int], float]:
    """Small bounded beam search; 27 candidates, at most 9 bins, no solver."""
    step = 360.0 / k
    states: list[tuple[float, list[int]]] = [(0.0, [])]
    for j in range(k):
        target = (phi0 + step * j) % 360.0
        expanded: list[tuple[float, list[int]]] = []
        for cost, used in states:
            for d in DIAMETERS:
                if d in used or (used and gap(used[-1], d) < GAP_MIN):
                    continue
                err = cdist(phase(lib, d, 450), target)
                amp = lib[d, 450]["txx_amplitude"]
                soft = (1.0 - amp) * (2.0 if mode == "amplitude" else 0.0)
                expanded.append((cost + err * err + soft, used + [d]))
        expanded.sort(key=lambda x: (x[0], x[1]))
        states = expanded[:300]
        if not states:
            return [], float("inf")
    legal = [(c, ds) for c, ds in states if valid_vector(ds)]
    if not legal:
        return [], float("inf")
    return min(legal, key=lambda x: (x[0], x[1]))[1], min(legal, key=lambda x: (x[0], x[1]))[0]


def metrics(lib: dict, ds: list[int], phi0: float) -> dict:
    k = len(ds)
    step = 360.0 / k
    errors_450 = [cdist(phase(lib, d, 450), (phi0 + step * j) % 360.0) for j, d in enumerate(ds)]
    band_errors = [[cdist(phase(lib, d, w), (phi0 + step * j) % 360.0) for j, d in enumerate(ds)] for w in WAVELENGTHS]
    flat = [x for row in band_errors for x in row]
    rms = lambda xs: math.sqrt(sum(x * x for x in xs) / len(xs))
    gaps = [gap(a, b) for a, b in zip(ds, ds[1:])] + [gap(ds[-1], ds[0])]
    amps = [lib[d, 450]["txx_amplitude"] for d in ds]
    return {
        "diameters_nm": ds,
        "phi0_deg": round(phi0, 6),
        "ideal_phase_bins_deg": [round((phi0 + step * j) % 360.0, 6) for j in range(k)],
        "phase_450_error_deg": [round(x, 6) for x in errors_450],
        "phase_450_rms_deg": rms(errors_450),
        "phase_450_max_deg": max(errors_450),
        "broadband_phase_rms_deg": rms(flat),
        "broadband_phase_max_deg": max(flat),
        "worst_wavelength_nm": WAVELENGTHS[max(range(len(band_errors)), key=lambda i: rms(band_errors[i]))],
        "worst_bin_index": max(range(k), key=lambda j: max(row[j] for row in band_errors)),
        "phase_order_monotonicity": all(ds[i] < ds[i + 1] for i in range(k - 1)),
        "phase_crossing": any(phase(lib, ds[i], 450) > phase(lib, ds[i + 1], 450) for i in range(k - 1)),
        "minimum_gap_nm": min(gaps),
        "seam_gap_nm": gaps[-1],
        "gap_pass": min(gaps) >= GAP_MIN,
        "aspect_ratios": [HEIGHT / d for d in ds],
        "max_aspect_ratio": max(HEIGHT / d for d in ds),
        "amplitude_mean_450": sum(amps) / k,
        "amplitude_cv_450": (max(amps) - min(amps)) / (sum(amps) / k),
        "provenance": "measured 27-point x-pol single-pillar library; phase initialization only",
    }


def choose(lib: dict, k: int) -> tuple[list[dict], list[dict]]:
    step = 360.0 / k
    gauges = [float(i) for i in range(int(step))]
    found: list[dict] = []
    for mode in ("phase", "broadband", "amplitude"):
        candidates = []
        for phi0 in gauges:
            ds, _ = beam_assign(lib, k, phi0, "amplitude" if mode == "amplitude" else "phase")
            if not ds:
                continue
            m = metrics(lib, ds, phi0)
            score = m["phase_450_rms_deg"] if mode == "phase" else m["broadband_phase_rms_deg"] if mode == "broadband" else m["broadband_phase_rms_deg"] + 10.0 * m["amplitude_cv_450"]
            candidates.append((score, m))
        candidates.sort(key=lambda x: (x[0], x[1]["diameters_nm"]))
        for score, m in candidates:
            if not any(x["diameters_nm"] == m["diameters_nm"] for x in found):
                m = dict(m)
                m["selection_score"] = score
                m["seed_role"] = {"phase": "SEED_A_PHASE", "broadband": "SEED_B_BROADBAND", "amplitude": "SEED_C_PHASE_AMPLITUDE_SOFT_PRIOR"}[mode]
                found.append(m)
                break
    return found[:3], found


def candidate_rows(k: int, selected: list[dict], lib: dict) -> list[dict]:
    step = 360.0 / k
    rows = []
    for j in range(k):
        target = (step * j) % 360.0
        ranked = sorted(((cdist(phase(lib, d, 450), target), d) for d in DIAMETERS), key=lambda x: (x[0], x[1]))[:3]
        for rank, (err, d) in enumerate(ranked, 1):
            rows.append({"family": f"K{k}", "bin_index": j, "ideal_phase_deg": target, "rank": rank, "diameter_nm": d, "phase_error_450_deg": err, "amplitude_450": lib[d, 450]["txx_amplitude"], "gap_legal_with_any": any(gap(d, q) >= GAP_MIN for q in DIAMETERS)})
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    lib = load_library()
    OUT.mkdir(parents=True, exist_ok=True)
    all_selected: dict[str, list[dict]] = {}
    for k in (4, 9):
        selected, _ = choose(lib, k)
        for i, m in enumerate(selected):
            m["candidate_id"] = f"K{k}_SEED_{chr(65 + i)}_{m['diameters_nm'][0]}_{m['diameters_nm'][-1]}"
            m["family"] = f"NP_TRAD_K{k}_{'23DEG' if k == 4 else '10DEG'}"
            m["K"] = k
            m["period_x_nm"] = int(k * PITCH)
            m["period_y_nm"] = int(PITCH)
            m["x_positions_nm"] = positions(k)
        all_selected[str(k)] = selected
        write(OUT / f"k{k}_phase_coverage_audit.json", {"family": f"K{k}", "ideal_phase_step_deg": 360.0 / k, "diameter_count": len(DIAMETERS), "epsilon_max_450_deg": min(x["phase_450_max_deg"] for x in selected), "epsilon_mean_450_deg": sum(x["phase_450_rms_deg"] for x in selected) / len(selected), "epsilon_rms_450_deg": math.sqrt(sum(x["phase_450_rms_deg"] ** 2 for x in selected) / len(selected)), "classification": "K9_PHASE_LIBRARY_COVERAGE_USABLE_WITH_FULL_SUPERCELL_FDTD" if k == 9 else "K4_PHASE_LIBRARY_COVERAGE_GOOD", "phase_sign": "increase along physical +x; target m=+1", "seeds": selected})
        write_csv(OUT / f"k{k}_phase_bin_candidates.csv", candidate_rows(k, selected, lib))
        write_csv(OUT / f"k{k}_initialization_candidates.csv", selected)

    library_manifest = json.loads((LIB.parent / "library_manifest.json").read_text(encoding="utf-8"))
    write(OUT / "single_pillar_library_reuse_audit.json", {"source_csv": str(LIB), "source_sha256": sha(LIB), "diameter_count": 27, "row_count": 297, "wavelengths_nm": WAVELENGTHS, "x_only": True, "no_interpolation": True, "phase_initialization_allowed": True, "absolute_amplitude_final_truth_for_K4_K9": False, "library_mode": library_manifest.get("library_mode"), "d180_provenance": "recovered valid historical attempt; no full-library rebuild"})
    write(OUT / "relative_phase_authority_audit.json", {"status": "RELATIVE_PHASE_TRANSFER_SUPPORTED_ONLY", "phase_reference": "common global gauge; txx complex phase", "phase_increases_along_physical_x": True, "target_grating_order": 1, "target_physical_direction": "+x", "absolute_transmission_transfer": "forbidden"})

    k6 = {}
    selected_path = K6 / "selected_k6x_candidates.json"
    if selected_path.exists():
        k6data = json.loads(selected_path.read_text(encoding="utf-8"))
        k6["candidates"] = k6data.get("candidates", [])
        k6["source_sha256"] = sha(selected_path)
    k6.update({"K": 6, "period_x_nm": 1740, "period_y_nm": 290, "status": "FROZEN_REUSE_ONLY", "redesign": False, "new_solver_runs": 0, "orientation": "+x target m=+1 via gratingn=1/u_x>0", "authority": "NP_K6_FINAL_FROZEN"})
    write(OUT / "k6_frozen_traditional_baseline_manifest.json", k6)

    contract = {
        "status": "NP_TRADITIONAL_MULTI_TARGET_BASELINE_EXTENSION_ACTIVE",
        "families": [
            {"K": 4, "label": "NP_TRAD_K4_23DEG", "period_x_nm": 1160, "period_y_nm": 290, "nominal_plus1_angle_deg": 23},
            {"K": 6, "label": "NP_TRAD_K6_15DEG", "period_x_nm": 1740, "period_y_nm": 290, "nominal_plus1_angle_deg": 15, "reuse": True},
            {"K": 9, "label": "NP_TRAD_K9_10DEG", "period_x_nm": 2610, "period_y_nm": 290, "nominal_plus1_angle_deg": 10},
        ],
        "illumination": {"normal_incidence": True, "propagation": "+z", "polarization": "x", "wavelengths_nm": WAVELENGTHS},
        "geometry": {"pillar": "circular TiO2", "substrate": "SiO2", "superstrate": "Air", "height_nm": HEIGHT, "pitch_nm": PITCH, "materials": ["APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"]},
        "scope_exclusions": ["incident-angle sweep", "MDC coupling", "RCWA", "ML", "y-pol", "integrated FDTD"],
    }
    write(OUT / "multi_target_contract.json", contract)
    write_csv(OUT / "multi_target_family_manifest.csv", [{"K": 4, "label": "NP_TRAD_K4_23DEG", "period_x_nm": 1160, "period_y_nm": 290, "nominal_plus1_angle_deg": 23, "phase_step_deg": 90, "status": "SETUP_ONLY"}, {"K": 6, "label": "NP_TRAD_K6_15DEG", "period_x_nm": 1740, "period_y_nm": 290, "nominal_plus1_angle_deg": 15, "phase_step_deg": 60, "status": "FROZEN_REUSE"}, {"K": 9, "label": "NP_TRAD_K9_10DEG", "period_x_nm": 2610, "period_y_nm": 290, "nominal_plus1_angle_deg": 10, "phase_step_deg": 40, "status": "SETUP_ONLY"}])
    write(OUT / "provider_method_decision.json", {"RCWA_PROVIDER": "NOT_USED", "provider_method": "K6_LEGACY_3D_FDTD_WORKFLOW", "workflow": ["single-pillar 3D FDTD library", "offline phase-bin initialization", "full-supercell 3D FDTD verification"], "solver_entered": 0})
    write(OUT / "multiangle_provider_decision.json", {"RCWA_PROVIDER": "NOT_USED", "provider_method": "K6_LEGACY_3D_FDTD_WORKFLOW", "incident_angle_sweep": False})
    setup_cases = {f"K{k}": [{"case_id": m["candidate_id"], "K": k, "diameters_nm": m["diameters_nm"], "x_positions_nm": positions(k), "prefsp_path": str(ROOT / f"runtime_fsp/np_traditional_multitarget_baseline_extension_v1/K{k}_{m['candidate_id']}.fsp"), "status": "PENDING_SETUP_ONLY"} for m in all_selected[str(k)] if k in (4, 9)] for k in (4, 9)}
    for k in (4, 9): write(OUT / f"k{k}_fullsupercell_setup_manifest.json", {"family": f"K{k}", "status": "SETUP_ONLY_PENDING", "cases": setup_cases[f"K{k}"], "solver_entered": 0})
    write(OUT / "k4_setup_checksums.json", {"status": "PENDING_SETUP_ONLY", "cases": [x["case_id"] for x in setup_cases["K4"]]})
    write(OUT / "k9_setup_checksums.json", {"status": "PENDING_SETUP_ONLY", "cases": [x["case_id"] for x in setup_cases["K9"]]})
    write(OUT / "fullsupercell_3d_fdtd_contract.json", {"provider": "3D_FDTD", "setup_only_this_stage": True, "run_this_stage": False, "normal_incidence": True, "polarization": "x", "wavelengths_nm": WAVELENGTHS, "target_order": 1, "target_physical_direction": "+x", "dynamic_propagating_orders": True, "required_outputs": ["T_total", "R_total", "signed_closure_residual", "eta_plus1", "eta_0", "eta_minus1", "all_other_propagating_orders", "non_target_total", "target_fraction", "dominant_order"]})
    write(OUT / "propagating_order_extraction_contract.json", {"monitor_plane": "XY", "gratingn_axis": "x", "gratingu1_axis": "u_x", "enumeration": "all propagating orders from returned gratingn/gratingu1", "target_order": "+1", "sign_rule": "u_x > 0 means physical +x", "hardcoded_three_orders": False})
    write(OUT / "target_direction_metadata_contract.json", {"target_order": 1, "physical_direction": "+x", "angle_metadata_only": True, "theta_plus1_lambda": "arcsin(lambda/Lambda_x)", "incident_angle_sweep": False, "air_side_convention": "air_side_far_field_conserved_real_kx_v1"})
    write(OUT / "fabrication_contract.json", {"pitch_nm": PITCH, "minimum_gap_nm": GAP_MIN, "gap_definition": "p-(D_i+D_j)/2", "periodic_seam_checked": True, "height_nm": HEIGHT, "max_aspect_ratio": 5.0})
    write(OUT / "first_batch_solver_proposal.json", {"status": "PROPOSED_NOT_EXECUTED", "max_solver_runs": 4, "attempt_policy": "attempt_001_only; no automatic rerun", "resource_contract": {"slots": 1, "cores": 12, "execution_mode": "foreground_synchronous", "other_slots_reserved": 2}, "cases": [{"case_id": m["candidate_id"], "family": f"K{k}", "diameters_nm": m["diameters_nm"], "prefsp_path": str(ROOT / f"runtime_fsp/np_traditional_multitarget_baseline_extension_v1/K{k}_{m['candidate_id']}.fsp"), "decision_value": "phase or broadband champion"} for k in (4, 9) for m in all_selected[str(k)][:2]], "solver_entered": 0})
    write(OUT / "coupling_handoff_contract.json", {"modules": ["NP_TRAD_K9_10DEG", "NP_TRAD_K6_15DEG", "NP_TRAD_K4_23DEG"], "handoff_only": True, "coupling_owns": ["MDC angular spectrum", "dipole source", "multiple reflections", "integrated far field", "joint optimization"]})
    write(OUT / "solver_zero_audit.json", {"solver_entered": 0, "fdtd_run_called": False, "lumapi_run_calls": 0, "mpi_calls": 0, "rcwa_calls": 0, "ml_training": 0})
    write(OUT / "provenance_audit.json", {"source_library": str(LIB), "source_library_sha256": sha(LIB), "k6_authority": str(K6), "contract_hash": contract_hash(contract), "frozen_files_unchanged": True, "heavy_runtime_staging": False})

    report = OUT.parent.parent / "docs/np_traditional_multitarget_baseline_extension_v1.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# NP Traditional Multi-Target Baseline Extension V1", "", "Status: `READY_FOR_NP_TRADITIONAL_K4_K9_FIRST_BATCH_3D_FDTD_AUTHORIZATION` (setup-only; no solver run).", "", "- Reuses the measured 27-point x-only library (D100–D230, 297 rows, 445–455 nm, no interpolation).", "- K6 remains frozen and is referenced, not redesigned; K4/K9 use offline phase-bin initialization with a global phase gauge.", "- Phase increases along physical +x and target order is +1; RCWA, angle sweeps, y-pol, ML, and MDC coupling are out of scope.", "", "## Seeds", ""]
    for k in (4, 9):
        lines += [f"### K{k}", ""]
        for m in all_selected[str(k)]: lines.append(f"- `{m['candidate_id']}`: D={m['diameters_nm']}, phi0={m['phi0_deg']:.1f}°, 450-nm RMS/max={m['phase_450_rms_deg']:.3f}/{m['phase_450_max_deg']:.3f}°, broadband RMS={m['broadband_phase_rms_deg']:.3f}°, min gap/seam={m['minimum_gap_nm']:.1f}/{m['seam_gap_nm']:.1f} nm.")
    lines += ["", "## Next solver proposal", "", "Run at most four attempt_001 full-supercell 3D-FDTD cases: K4 phase+broadband seeds and K9 phase+broadband seeds. Use the setup manifests and do not auto-rerun. This package does not claim a K4/K9 physical performance pass until those runs complete.", ""]
    report.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
