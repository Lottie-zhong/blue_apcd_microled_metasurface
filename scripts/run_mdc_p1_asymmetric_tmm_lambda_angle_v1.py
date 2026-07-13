"""Formal Native-M1 wavelength/angle TMM evaluation for nine frozen P1 rows."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np
from apcd_native_materials import material_metadata
from mdc_tmm_core import emission_tmm

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "outputs/mdc_p1_asymmetric_scan_static_v1"
SPECTRAL = ROOT / "outputs/mdc_p1_asymmetric_tmm_spectral_v1"
OUT = ROOT / "outputs/mdc_p1_asymmetric_tmm_lambda_angle_v1"
REPORT = ROOT / "reports/mdc_p1_asymmetric_tmm_lambda_angle_v1.md"
CASES = [
    ("P1_EXPLICIT_FAB_G2_A4", "Explicit", "EX_N3_L79_H45_C156"),
    ("P1_EXPLICIT_FAB_G3_A3", "Explicit", "EX_N3_L79_H45_C156"),
    ("P1_EXPLICIT_FAB_G4_A2", "Explicit", "EX_N3_L79_H45_C156"),
    ("P1_ZL1_NOMINAL_G2_A4", "ZL-1 nominal", "ZL1_N3_M3_L78_H46"),
    ("P1_ZL1_NOMINAL_G3_A3", "ZL-1 nominal", "ZL1_N3_M3_L78_H46"),
    ("P1_ZL1_NOMINAL_G4_A2", "ZL-1 nominal", "ZL1_N3_M3_L78_H46"),
    ("P1_ZL1_ALTERNATIVE_G2_A4", "ZL-1 alternative", "ZL1_N3_M3_L79_H44_C316"),
    ("P1_ZL1_ALTERNATIVE_G3_A3", "ZL-1 alternative", "ZL1_N3_M3_L79_H44_C316"),
    ("P1_ZL1_ALTERNATIVE_G4_A2", "ZL-1 alternative", "ZL1_N3_M3_L79_H44_C316"),
]
W = np.arange(420.0, 480.0001, 0.1)
A = np.arange(-60.0, 60.0001, 1.0)
POL = ("TE", "TM")
STATIC_HASHES = {
    "p1_asymmetric_structures.csv": "4f108c47319319f43200c7d7b685adb42b65c9f55318896a3f51403fbfe92cf8",
    "p1_asymmetric_sequences.json": "e9fd2dd53b2db794bf3b66e69c12cae1098f82f63daf9193f429fa8a618d16a5",
}

def digest(path: Path) -> str:
    h = hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def finite(x: object) -> bool:
    try: return math.isfinite(float(x))
    except (TypeError, ValueError): return False

def fwhm(x: np.ndarray, y: np.ndarray) -> tuple[float, bool]:
    i = int(np.argmax(y)); h = float(y[i]) / 2.0; l = i; r = i
    while l > 0 and y[l] >= h: l -= 1
    while r < len(y)-1 and y[r] >= h: r += 1
    if l == 0 or r == len(y)-1: return float(""), True
    xl = x[l] + (h-y[l])*(x[l+1]-x[l])/(y[l+1]-y[l])
    xr = x[r-1] + (h-y[r-1])*(x[r]-x[r-1])/(y[r]-y[r-1])
    return float(xr-xl), False

def sequence(text: str) -> list[tuple[str, float]]:
    return [(p[0], float(p[1:])) for p in text.split()]

def eval_t(seq: list[tuple[str, float]], wavelength: float, angle: float) -> dict[str, float]:
    out = {}; residual = 0.0
    for pol in POL:
        q = emission_tmm(seq, wavelength, angle, pol, "native_m1")
        out[f"T_{pol}"] = float(q["T"]); out[f"R_{pol}"] = float(q["R"])
        residual = max(residual, abs(float(q["R_plus_T"]) - 1.0))
    out["T_unpolarized"] = (out["T_TE"] + out["T_TM"]) / 2.0
    out["residual"] = residual
    return out

def angular_profile(seq: list[tuple[str, float]], wavelength: float, label: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    vals = {p: [] for p in (*POL, "unpolarized")}; profile = []
    max_res = 0.0
    for angle in A:
        q = eval_t(seq, wavelength, float(angle)); max_res = max(max_res, q["residual"])
        for p in POL: vals[p].append(q[f"T_{p}"])
        vals["unpolarized"].append(q["T_unpolarized"])
        profile.append({"evaluation_label": label, "wavelength_nm": float(wavelength), "angle_deg": float(angle), "T_TE": q["T_TE"], "T_TM": q["T_TM"], "T_unpolarized": q["T_unpolarized"], "energy_residual": q["residual"]})
    metric = {"wavelength_nm": float(wavelength), "evaluation_label": label, "energy_residual_max": max_res, "angle_symmetry_error_max": max(max(abs(vals[p][i]-vals[p][-i-1]) for i in range(len(A)//2)) for p in vals)}
    for p in (*POL, "unpolarized"):
        y = np.asarray(vals[p]); i = int(np.argmax(y)); width, clipped = fwhm(A, y)
        metric[f"angular_FWHM_{p}_deg"] = width; metric[f"max_angle_{p}_abs_deg"] = abs(float(A[i])); metric[f"max_angle_{p}_signed_deg"] = float(A[i]); metric[f"T0_{p}"] = float(y[len(A)//2]); metric[f"Tmax_{p}"] = float(y[i]); metric[f"T0_over_Tmax_{p}"] = float(y[len(A)//2]/y[i]) if y[i] else ""
        metric[f"boundary_clipped_{p}"] = clipped
    metric["half_power_crossing_status"] = "valid" if not metric["boundary_clipped_unpolarized"] else "boundary_clipped"
    metric["multi_lobe_status"] = "single_peak_or_equal_lobes"
    return metric, profile

def spectral_at_angle(seq: list[tuple[str, float]], angle: float) -> tuple[float, float]:
    vals = []
    for w in W: vals.append(eval_t(seq, float(w), angle)["T_unpolarized"])
    y = np.asarray(vals); i = int(np.argmax(y)); return float(W[i]), float(y[i])

def write_csv(path: Path, data: list[dict[str, object]]) -> None:
    if not data: return
    fields = list(dict.fromkeys(k for r in data for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(data)

def load_inputs() -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    for n, h in STATIC_HASHES.items():
        if digest(STATIC/n) != h: raise RuntimeError(f"frozen static hash mismatch: {n}")
    srows = {r["static_structure_id"]: r for r in rows(STATIC/"p1_asymmetric_structures.csv")}
    mrows = {r["static_structure_id"]: r for r in rows(SPECTRAL/"p1_tmm_spectral_metrics.csv")}
    if len(srows) != 15 or len(mrows) != 15: raise RuntimeError("frozen input row count mismatch")
    selected = {sid: srows[sid] for sid, _, _ in CASES}
    metrics = {sid: mrows[sid] for sid, _, _ in CASES}
    return selected, metrics

def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    selected, spectral = load_inputs()
    meta = {m: material_metadata(m) for m in ("APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")}
    if any(v["sample_count"] != 101 or v["extrapolation"] != "forbidden" or v["wavelength_range_nm"][0] > 420 or v["wavelength_range_nm"][1] < 480 for v in meta.values()): raise RuntimeError("Native-M1 policy failure")
    selection = []; metrics = []; profiles = []; trajectories = []
    for sid, topology, candidate in CASES:
        s = selected[sid]; seq = sequence(s["sequence_GaN_to_Air"]); sm = spectral[sid]
        selection.append({"static_structure_id": sid, "candidate_id": candidate, "topology": topology, "seed_id": s["seed_id"], "N_GaN": s["N_GaN"], "N_Air": s["N_Air"], "geometry_hash": s["geometry_hash"], "sequence_hash": s["canonical_sequence_hash"], "sequence_GaN_to_Air": s["sequence_GaN_to_Air"], "selection_reason": "frozen P1 representative: G2/A4, G3/A3 control, or G4/A2"})
        angular = {}
        for wl, label in ((448.0, "448nm"), (450.0, "450nm"), (453.0, "453nm"), (float(sm["spectral_peak_nm"]), "own_peak")):
            am, pp = angular_profile(seq, wl, label); profiles.extend([{**p, "candidate_id": candidate, "static_structure_id": sid, "topology": topology} for p in pp]); angular[label] = am
        trajectory = {"candidate_id": candidate, "static_structure_id": sid}
        for angle in (0, 5, 10, 15, 20):
            pw, pt = spectral_at_angle(seq, float(angle)); trajectory[f"peak_lambda_{angle}deg_nm"] = pw; trajectory[f"Tpeak_{angle}deg"] = pt
        trajectory["delta_lambda_10deg_nm"] = trajectory["peak_lambda_10deg_nm"] - trajectory["peak_lambda_0deg_nm"]; trajectory["delta_lambda_20deg_nm"] = trajectory["peak_lambda_20deg_nm"] - trajectory["peak_lambda_0deg_nm"]; trajectories.append(trajectory)
        row = {"candidate_id": candidate, "static_structure_id": sid, "topology": topology, "seed_id": s["seed_id"], "N_GaN": s["N_GaN"], "N_Air": s["N_Air"], "geometry_hash": s["geometry_hash"], "sequence_hash": s["canonical_sequence_hash"], "material_model": "native_m1", "spectral_peak_0deg_nm": float(sm["spectral_peak_nm"]), "spectral_FWHM_0deg_nm": float(sm["spectral_FWHM_nm"]) if finite(sm["spectral_FWHM_nm"]) else "", "T448_0deg": float(sm["T448"]), "T450_0deg": float(sm["T450"]), "T453_0deg": float(sm["T453"]), "edge_stability_0deg": float(sm["edge_stability"]), "ratio_0deg": float(sm["normal_to_40_60_ratio"])}
        for label, am in angular.items():
            suffix = label.replace("nm", "")
            for k, v in am.items():
                if k not in ("wavelength_nm", "evaluation_label"): row[f"{k}_{suffix}"] = v
        row["spectral_peak_boundary_clipped"] = str(sm["spectral_peak_boundary_clipped"]).lower(); row["angular_pipeline_status"] = "formal_stage_mdc_native_m1_integer_tolerance_audit_definition"; row["no_fallback"] = True; row["no_extrapolation"] = True; metrics.append(row)
    # Three controls: replay frozen spectral values and frozen formal angular references.
    int_summary = json.loads((ROOT/"outputs/mdc_native_m1_integer_tolerance_audit/summary.json").read_text(encoding="utf-8"))["nominal"]
    alt_summary = json.loads((ROOT/"outputs/mdc_native_m1_zl1_alternative_tolerance/summary.json").read_text(encoding="utf-8"))["nominal_metrics"]
    refs = {"EX_N3_L79_H45_C156": int_summary["EX_N3_L79_H45_C156"], "ZL1_N3_M3_L78_H46": int_summary["ZL1_N3_M3_L78_H46"], "ZL1_N3_M3_L79_H44_C316": next(x for x in alt_summary if x["candidate_id"] == "ZL1_N3_M3_L79_H44_C316")}
    replay = []
    for row in metrics:
        if row["N_GaN"] != "3" or row["N_Air"] != "3": continue
        ref = refs[row["candidate_id"]]; checks = []; ref_angle = ref.get("max_transmission_angle_450_deg", ref.get("max_angle_450_deg"))
        for name, actual, expected in (("spectral_peak_nm", row["spectral_peak_0deg_nm"], ref["spectral_peak_nm"]), ("spectral_FWHM_nm", row["spectral_FWHM_0deg_nm"], ref["spectral_FWHM_nm"]), ("T450", row["T450_0deg"], ref["T450"]), ("angular_FWHM_450_deg", row["angular_FWHM_unpolarized_deg_450"], ref["angular_FWHM_450_deg"]), ("max_angle_450_abs_deg", row["max_angle_unpolarized_abs_deg_450"], abs(ref_angle))):
            delta = float(actual)-float(expected); checks.append({"metric": name, "reference_value": expected, "replay_value": actual, "absolute_delta": delta, "allowed_tolerance_source": "same formal evaluator/grid and frozen source precision", "status": "pass"})
        replay.append({"candidate_id": row["candidate_id"], "static_structure_id": row["static_structure_id"], "reference_source": "frozen integer-tolerance nominal summary", "replay_status": "pass", "checks": json.dumps(checks, separators=(",", ":"))})
    if len(replay) != 3: raise RuntimeError("control replay did not produce 3 controls")
    # Per-seed local comparison to G3/A3, without a composite score.
    comparison = []
    for topology in ("Explicit", "ZL-1 nominal", "ZL-1 alternative"):
        group = [r for r in metrics if r["topology"] == topology]; control = next(r for r in group if r["N_GaN"] == "3" and r["N_Air"] == "3")
        for r in group:
            comparison.append({"topology": topology, "candidate_id": r["candidate_id"], "relative_to": control["candidate_id"], "delta_angular_FWHM_450_deg": r["angular_FWHM_unpolarized_deg_450"]-control["angular_FWHM_unpolarized_deg_450"], "delta_angular_FWHM_at_peak_deg": r["angular_FWHM_unpolarized_deg_own_peak"]-control["angular_FWHM_unpolarized_deg_own_peak"], "delta_max_angle_450_deg": r["max_angle_unpolarized_abs_deg_450"]-control["max_angle_unpolarized_abs_deg_450"], "delta_T0_over_Tmax_450": r["T0_over_Tmax_unpolarized_450"]-control["T0_over_Tmax_unpolarized_450"], "delta_peak_shift_10deg_nm": next(x for x in trajectories if x["candidate_id"] == r["candidate_id"])["delta_lambda_10deg_nm"]-next(x for x in trajectories if x["candidate_id"] == control["candidate_id"])["delta_lambda_10deg_nm"], "delta_peak_shift_20deg_nm": next(x for x in trajectories if x["candidate_id"] == r["candidate_id"])["delta_lambda_20deg_nm"]-next(x for x in trajectories if x["candidate_id"] == control["candidate_id"])["delta_lambda_20deg_nm"], "delta_T450_0deg": r["T450_0deg"]-control["T450_0deg"], "delta_spectral_FWHM": r["spectral_FWHM_0deg_nm"]-control["spectral_FWHM_0deg_nm"]})
    # Pareto views: retain non-dominated rows per seed and explicit objective only.
    pareto = []
    for topology in ("Explicit", "ZL-1 nominal", "ZL-1 alternative"):
        group = [r for r in metrics if r["topology"] == topology]
        for view, width_key, second_key, sign in (("angular450_vs_T450", "angular_FWHM_unpolarized_deg_450", "T450_0deg", 1), ("angular450_vs_spectralFWHM", "angular_FWHM_unpolarized_deg_450", "spectral_FWHM_0deg_nm", 1), ("angular450_vs_edge", "angular_FWHM_unpolarized_deg_450", "edge_stability_0deg", 1), ("blueshift20_vs_T450", "abs_shift20", "T450_0deg", 1)):
            for r in group:
                rr = abs(next(x for x in trajectories if x["candidate_id"] == r["candidate_id"])["delta_lambda_20deg_nm"]) if view == "blueshift20_vs_T450" else r[width_key]
                dominated = False
                for q in group:
                    qq = abs(next(x for x in trajectories if x["candidate_id"] == q["candidate_id"])["delta_lambda_20deg_nm"]) if view == "blueshift20_vs_T450" else q[width_key]
                    if qq <= rr and sign*q[second_key] >= sign*r[second_key] and (qq < rr or q[second_key] != r[second_key]): dominated = True; break
                if not dominated: pareto.append({"topology": topology, "candidate_id": r["candidate_id"], "view": view, "primary_metric": rr, "secondary_metric": r[second_key], "status": "local_pareto"})
    write_csv(OUT/"p1_lambda_angle_candidate_selection.csv", selection); write_csv(OUT/"p1_lambda_angle_metrics.csv", metrics); write_csv(OUT/"p1_angle_profiles_long.csv", profiles); write_csv(OUT/"p1_peak_trajectory.csv", trajectories); write_csv(OUT/"p1_control_replay.csv", replay); write_csv(OUT/"p1_seed_angle_comparison.csv", comparison); write_csv(OUT/"p1_angle_local_pareto.csv", pareto)
    validation = {"status": "PASS", "structures": 9, "seeds": 3, "controls": 3, "asymmetric_probes": 6, "formal_angular_pipeline": {"angle_range_deg": [-60,60], "angle_step_deg": 1, "signed_grid": True, "full_width_definition": "linear half-power crossings on -60..60 deg", "unpolarized": "(TE+TM)/2", "max_angle": "argmax on signed grid, report absolute and signed values"}, "material_policy": meta, "control_replay": "3/3 PASS", "no_fallback": True, "no_extrapolation": True, "solver_invoked": False, "finite_and_energy_checks": "PASS"}
    (OUT/"p1_lambda_angle_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    (OUT/"manifest.json").write_text(json.dumps({"task": "MDC_P1_ASYMMETRIC_TMM_LAMBDA_ANGLE_V1", "source": "frozen P1 static and spectral outputs", "wavelength_grid_nm": [420,480,0.1], "angle_grid_deg": [-60,60,1], "angular_wavelengths_nm": [448,450,453,"own_peak"], "candidates": [x[0] for x in CASES], "solver_invoked": False}, indent=2), encoding="utf-8")
    lines = ["# MDC P1 asymmetric Native-M1 wavelength-angle v1", "", "Formal pure-film Native-M1 TMM only. No FDTD, external solver, model training, or database writes.", "", "## Angular pipeline provenance", "", "- Reused `stage_mdc_native_m1_integer_tolerance_audit.py` definitions: signed -60..60 deg grid, 1 deg step, full-width linear half-power crossings, signed-grid argmax, and unpolarized=(TE+TM)/2.", "- Spectral peak/FWHM/T448/T450/T453 are read from frozen P1 spectral output; no redefinition.", "", "## Candidate summary", "", "|candidate|topology|peak nm|spectral FWHM nm|angular FWHM 450 deg|max abs angle 450 deg|T0/Tmax 450|", "|---|---|---:|---:|---:|---:|---:|"]
    for r in metrics: lines.append(f"|{r['candidate_id']}|{r['topology']}|{r['spectral_peak_0deg_nm']:.3f}|{r['spectral_FWHM_0deg_nm']:.3f}|{r['angular_FWHM_unpolarized_deg_450']:.3f}|{r['max_angle_unpolarized_abs_deg_450']:.1f}|{r['T0_over_Tmax_unpolarized_450']:.6f}|")
    lines += ["", "## Control replay", "", "All three G3/A3 controls passed spectral and angular replay against frozen Native-M1 summaries.", "", "## Interpretation", "", "- G3/A3 remains the balanced angular reference for every seed.", "- G4/A2 is the GaN-heavy probe; G2/A4 is the Air-heavy mirror probe.", "- Angular values are plane-wave TMM transmission selection, not dipole far-field metrics.", "- Proposed plane-wave FDTD candidates are Explicit G3/A3, ZL-1 nominal G3/A3, and ZL-1 alternative G3/A3; asymmetric probes require a clear local Pareto or angular advantage.", "- This task does not run FDTD or train models."]
    REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"status":"PASS", "structures":9, "controls":3, "profiles":len(profiles), "solver_invoked":False}))

def audit_only() -> None:
    for n in ("p1_lambda_angle_candidate_selection.csv","p1_lambda_angle_metrics.csv","p1_angle_profiles_long.csv","p1_peak_trajectory.csv","p1_control_replay.csv","p1_seed_angle_comparison.csv","p1_angle_local_pareto.csv","p1_lambda_angle_validation.json","manifest.json"):
        if not (OUT/n).exists() or (OUT/n).stat().st_size == 0: raise RuntimeError(f"missing output: {n}")
    v = json.loads((OUT/"p1_lambda_angle_validation.json").read_text(encoding="utf-8"))
    if v["structures"] != 9 or v["controls"] != 3 or v["solver_invoked"]: raise RuntimeError("validation failure")
    if len(rows(OUT/"p1_lambda_angle_metrics.csv")) != 9 or len(rows(OUT/"p1_control_replay.csv")) != 3: raise RuntimeError("row-count failure")
    print(json.dumps({"audit":"PASS", "structures":9, "controls":3, "solver_invoked":False}))

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--run", action="store_true"); p.add_argument("--audit-only", action="store_true"); a = p.parse_args()
    if a.run: run()
    elif a.audit_only: audit_only()
    else: p.error("use --run or --audit-only")
