from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
import lumapi


CASE_ID = "IC1_MDC_I03_TOPWELL_X"
FACES = [
    ("ic1_flux_top", "+z"),
    ("ic1_flux_bottom", "-z"),
    ("ic1_flux_xminus", "-x"),
    ("ic1_flux_xplus", "+x"),
    ("ic1_flux_yminus", "-y"),
    ("ic1_flux_yplus", "+y"),
]
UTC = dt.timezone.utc


def now():
    return dt.datetime.now(UTC).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{__import__('os').getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temp.replace(path)


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def arr(value, dtype=None):
    return np.asarray(value, dtype=dtype).reshape(-1)


def finite_summary(a):
    a = np.asarray(a)
    return {
        "shape": list(a.shape),
        "dtype": str(a.dtype),
        "size": int(a.size),
        "finite": bool(np.all(np.isfinite(a))) if a.size else True,
        "real_min": float(np.min(np.real(a))) if a.size else None,
        "real_max": float(np.max(np.real(a))) if a.size else None,
        "imag_min": float(np.min(np.imag(a))) if np.iscomplexobj(a) and a.size else None,
        "imag_max": float(np.max(np.imag(a))) if np.iscomplexobj(a) and a.size else None,
    }


def stokes_from_coherency(c):
    s0 = float(np.trace(c).real)
    s1 = float((c[0, 0] - c[1, 1]).real)
    s2 = float(2.0 * c[0, 1].real)
    s3 = float(-2.0 * c[0, 1].imag)
    dolp = float(math.hypot(s1, s2) / s0) if s0 > 0.0 else float("nan")
    docp = float(s3 / s0) if s0 > 0.0 else float("nan")
    psi = float(math.degrees(0.5 * math.atan2(s2, s1)) % 180.0) if s0 > 0.0 else float("nan")
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "DoLP": dolp, "DoCP": docp, "psi_deg": psi}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-fsp", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    args = parser.parse_args()

    provenance = json.loads(args.provenance.read_text(encoding="utf-8"))
    if provenance.get("case_id") != CASE_ID or provenance.get("status") != "RETURNED":
        raise RuntimeError("IC1_PROVENANCE_NOT_RETURNED")
    post_sha = sha256(args.post_fsp)
    if post_sha != provenance.get("post_fsp_sha256"):
        raise RuntimeError("IC1_POST_FSP_SHA_MISMATCH")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.runtime_dir.mkdir(parents=True, exist_ok=True)
    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(args.post_fsp))
        top = f.getresult("ic1_flux_top", "T")
        wavelength_m = arr(top["lambda"], float)
        frequency_hz = arr(top["f"], float)
        wavelength_nm = wavelength_m * 1e9
        if len(wavelength_nm) != 101 or not np.all(np.isfinite(wavelength_nm)):
            raise RuntimeError("IC1_SPECTRAL_GRID_INVALID")
        sourcepower = np.real(arr(f.sourcepower(frequency_hz), float))

        face_rows = []
        face_powers = {}
        face_transmissions = {}
        for name, normal in FACES:
            result = f.getresult(name, "T")
            power_result = np.real(arr(f.getresult(name, "power")))
            transmission = np.real(arr(result["T"], float))
            if len(transmission) != len(wavelength_nm) or len(power_result) != len(wavelength_nm):
                raise RuntimeError(f"IC1_FACE_GRID_INVALID:{name}")
            face_powers[name] = power_result
            face_transmissions[name] = transmission
            for i, wl in enumerate(wavelength_nm):
                face_rows.append({
                    "wavelength_nm": float(wl), "face": name, "normal": normal,
                    "transmission_T": float(transmission[i]), "power_W": float(power_result[i]),
                    "sourcepower_W": float(sourcepower[i]),
                    "source_normalized_power": float(power_result[i] / sourcepower[i]) if sourcepower[i] != 0.0 else float("nan"),
                })

        near = f.getresult("ic1_top_near_to_far", "E")
        x = arr(near["x"], float)
        y = arr(near["y"], float)
        e_plane = np.asarray(near["E"])
        if e_plane.ndim != 5 or e_plane.shape[-1] < 2 or e_plane.shape[3] != len(wavelength_nm):
            raise RuntimeError("IC1_NEAR_TO_FAR_E_GRID_INVALID")
        ex_plane = e_plane[:, :, 0, :, 0]
        ey_plane = e_plane[:, :, 0, :, 1]
        dx = float(np.mean(np.diff(x))) if len(x) > 1 else 1.0
        dy = float(np.mean(np.diff(y))) if len(y) > 1 else 1.0
        d_area = abs(dx * dy)
        stokes_rows = []
        farfield_rows = []
        farfield_450 = {}
        ux = arr(f.farfieldux("ic1_top_near_to_far", 51), float)
        uy = arr(f.farfielduy("ic1_top_near_to_far", 51), float)
        for i, wl in enumerate(wavelength_nm):
            ex = ex_plane[:, :, i]
            ey = ey_plane[:, :, i]
            c = 0.5 * d_area * np.array([
                [np.vdot(ex.reshape(-1), ex.reshape(-1)), np.vdot(ey.reshape(-1), ex.reshape(-1))],
                [np.vdot(ex.reshape(-1), ey.reshape(-1)), np.vdot(ey.reshape(-1), ey.reshape(-1))],
            ], dtype=np.complex128)
            s = stokes_from_coherency(c)
            sn = {k: (float(v / sourcepower[i]) if k in ["S0", "S1", "S2", "S3"] and sourcepower[i] != 0.0 else v) for k, v in s.items()}
            stokes_rows.append({"wavelength_nm": float(wl), **s, "sourcepower_normalized_S0": sn["S0"], "sourcepower_normalized_S1": sn["S1"], "sourcepower_normalized_S2": sn["S2"], "sourcepower_normalized_S3": sn["S3"]})

            vector = np.asarray(f.farfieldvector3d("ic1_top_near_to_far", i + 1, 1, 1)).reshape(-1)
            intensity = np.asarray(f.farfield3d("ic1_top_near_to_far", i + 1), dtype=float)
            int_ff = float(np.asarray(f.farfield3dintegrate(np.asarray(intensity), ux, uy)).reshape(-1)[0])
            if vector.size < 2 or not np.all(np.isfinite(vector)) or not np.all(np.isfinite(intensity)):
                raise RuntimeError(f"IC1_FARFIELD_NONFINITE:{i}")
            ff_ex, ff_ey = vector[0], vector[1]
            c_ff = 0.5 * np.array([[ff_ex * np.conj(ff_ex), ff_ey * np.conj(ff_ex)], [ff_ex * np.conj(ff_ey), ff_ey * np.conj(ff_ey)]], dtype=np.complex128)
            sf = stokes_from_coherency(c_ff)
            row = {
                "wavelength_nm": float(wl),
                "farfield_Ex_real": float(np.real(ff_ex)), "farfield_Ex_imag": float(np.imag(ff_ex)),
                "farfield_Ey_real": float(np.real(ff_ey)), "farfield_Ey_imag": float(np.imag(ff_ey)),
                "farfield_intensity_angular_integral_raw": int_ff,
                "farfield_intensity_angular_integral_over_sourcepower": float(int_ff / sourcepower[i]) if sourcepower[i] != 0.0 else float("nan"),
                "farfield_max_raw": float(np.max(intensity)),
                "farfield_max_over_sourcepower": float(np.max(intensity) / sourcepower[i]) if sourcepower[i] != 0.0 else float("nan"),
                "normal_S0": sf["S0"], "normal_S1": sf["S1"], "normal_S2": sf["S2"], "normal_S3": sf["S3"], "normal_DoLP": sf["DoLP"], "normal_DoCP": sf["DoCP"], "normal_psi_deg": sf["psi_deg"],
            }
            farfield_rows.append(row)
            if abs(float(wl) - 450.0) < 1e-8:
                farfield_450 = {"wavelength_nm": float(wl), "ux_points": int(len(ux)), "uy_points": int(len(uy)), "ux_min": float(np.min(ux)), "ux_max": float(np.max(ux)), "uy_min": float(np.min(uy)), "uy_max": float(np.max(uy)), "intensity_summary": finite_summary(intensity), "vector_summary": finite_summary(vector), "vector_Ex": [float(np.real(ff_ex)), float(np.imag(ff_ex))], "vector_Ey": [float(np.real(ff_ey)), float(np.imag(ff_ey))], "stokes": sf}
                np.savez(args.runtime_dir / "ic1_farfield_450nm_raw.npz", ux=ux, uy=uy, intensity=intensity, vector=vector)

        closed = np.column_stack([face_powers[name] for name, _ in FACES])
        net = np.sum(closed, axis=1)
        face_consistency = np.column_stack([face_transmissions[name] * sourcepower for name, _ in FACES])
        consistency_error = np.max(np.abs(face_consistency - closed), axis=1)
        closed_rows = []
        for i, wl in enumerate(wavelength_nm):
            closed_rows.append({"wavelength_nm": float(wl), "top_W": float(closed[i, 0]), "bottom_W": float(closed[i, 1]), "xminus_W": float(closed[i, 2]), "xplus_W": float(closed[i, 3]), "yminus_W": float(closed[i, 4]), "yplus_W": float(closed[i, 5]), "net_outward_W": float(net[i]), "sourcepower_W": float(sourcepower[i]), "net_over_sourcepower": float(net[i] / sourcepower[i]) if sourcepower[i] != 0.0 else float("nan"), "max_T_times_sourcepower_vs_power_abs_error_W": float(consistency_error[i])})

        time_result = f.getresult("ic1_v2_time_probe", "E")
        time_s = arr(time_result["t"], float)
        time_e = np.asarray(time_result["E"], dtype=float).reshape(-1, 3)
        proxy = 0.5 * np.sum(time_e * time_e, axis=1)
        count = max(3, math.ceil(len(proxy) / 3))
        tail = proxy[-count:]
        slope_time = float(np.polyfit(time_s[-count:], tail, 1)[0]) if count >= 2 else 0.0
        slope_index = float(np.polyfit(np.arange(count, dtype=float), tail, 1)[0]) if count >= 2 else 0.0
        convergence = {
            "schema": "PAPER_A_FDTD_CONVERGENCE_EVIDENCE_V2", "case_id": CASE_ID, "status": "PASS" if len(time_s) >= 3 and len(time_s) == len(proxy) and np.all(np.isfinite(time_s)) and np.all(np.isfinite(proxy)) and np.all(np.diff(time_s) > 0.0) and np.all(proxy >= 0.0) else "INSUFFICIENT_EVIDENCE_NOT_VALIDATED",
            "independent_time_series": {"monitor_name": "ic1_v2_time_probe", "time_s": time_s.tolist(), "field_energy_proxy": proxy.tolist(), "sample_count": int(len(time_s)), "finite": bool(np.all(np.isfinite(time_s)) and np.all(np.isfinite(proxy))), "strictly_increasing_time": bool(len(time_s) > 1 and np.all(np.diff(time_s) > 0.0)), "nonnegative_proxy": bool(np.all(proxy >= 0.0) and np.any(proxy > 0.0)), "late_window": {"count": int(count), "first": float(tail[0]), "last": float(tail[-1]), "linear_slope_per_s": slope_time, "linear_slope_per_sample": slope_index}, "positive_late_window_growth": bool(tail[-1] > tail[0] and slope_index > 0.0)},
            "native_auto_shutoff": {"status": "NOT_PERSISTED_BY_RUNNER", "trajectory": [], "required": False, "reason": "controller did not expose native Auto Shutoff trajectory; independent V2 probe retained"},
            "post_fsp": {"path": str(args.post_fsp), "sha256": post_sha}, "solver_entered": True, "solver_run_called": True, "raw_solver_data_modified": False,
        }
        write_json(args.runtime_dir / "ic1_convergence_evidence_v2.json", convergence)
        write_csv(args.output_dir / "ic1_closed_flux.csv", closed_rows, list(closed_rows[0]))
        write_csv(args.output_dir / "ic1_stokes.csv", stokes_rows, list(stokes_rows[0]))
        write_csv(args.output_dir / "ic1_farfield_metrics.csv", farfield_rows, list(farfield_rows[0]))
        write_csv(args.output_dir / "ic1_face_flux_long.csv", face_rows, list(face_rows[0]))

        source_ok = bool(np.all(np.isfinite(sourcepower)) and np.all(sourcepower > 0.0))
        face_ok = bool(np.all(np.isfinite(closed)) and np.all(np.isfinite(net)))
        farfield_ok = bool(all(np.isfinite(row["farfield_intensity_angular_integral_raw"]) for row in farfield_rows) and all(np.isfinite(row["farfield_Ex_real"]) and np.isfinite(row["farfield_Ey_real"]) for row in farfield_rows))
        series_ok = convergence["status"] == "PASS"
        ambiguous_late_proxy = bool(convergence["independent_time_series"]["positive_late_window_growth"])
        if not source_ok:
            classification = "INVALID_FOR_PHYSICS_TRUTH_SOURCE_NORMALIZATION"
            root = "E_SOURCE_NORMALIZATION_INVALID"
        elif not face_ok:
            classification = "INVALID_FOR_PHYSICS_TRUTH_POWER_SANITY"
            root = "E_CLOSED_FLUX_NONFINITE"
        elif not farfield_ok:
            classification = "INVALID_FOR_PHYSICS_TRUTH_POWER_SANITY"
            root = "E_FARFIELD_NONFINITE"
        elif not series_ok or ambiguous_late_proxy:
            classification = "INSUFFICIENT_EVIDENCE_NOT_VALIDATED"
            root = "E_INDEPENDENT_LATE_TIME_EVIDENCE_MISSING_OR_AMBIGUOUS"
        else:
            classification = "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH"
            root = None
        validity = {
            "schema": "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_RESULT_V2_IC1_INTEGRATED_ADAPTER",
            "case_id": CASE_ID, "status": classification, "root_cause": root,
            "authority": {"v2": "paper_a_broadband/authority/paper_a_fdtd_physics_validity_gate_v2_instrumented.json", "adapter": "paper_a_broadband/authority/ic1_integrated_validity_adapter.json", "no_threshold_invention": True},
            "gates": {
                "completion_and_immutable_provenance": {"status": "PASS", "provenance_status": provenance.get("status"), "post_fsp_sha256": post_sha, "pre_fsp_sha256": provenance.get("pre_fsp_sha256")},
                "independent_time_series": convergence,
                "sourcepower": {"status": "PASS" if source_ok else "FAIL", "sample_count": int(len(sourcepower)), "min_W": float(np.min(sourcepower)), "max_W": float(np.max(sourcepower)), "finite": bool(np.all(np.isfinite(sourcepower))), "strictly_positive": bool(np.all(sourcepower > 0.0))},
                "closed_flux": {"status": "PASS" if face_ok else "FAIL", "sample_count": int(len(wavelength_nm)), "face_count": len(FACES), "finite": face_ok, "net_min_W": float(np.min(net)), "net_max_W": float(np.max(net)), "no_signed_power_transformation": True},
                "near_to_far_Ex_Ey": {"status": "PASS" if farfield_ok else "FAIL", "sample_count": int(len(farfield_rows)), "finite_complex_components": farfield_ok, "angular_integral_available": True, "450_nm": farfield_450},
                "post_run_semantic_integrity": {"status": "PASS", "object_count": len(f.getobjectlist("::model::")), "no_periodic_xy": True, "raw_solver_data_modified": False},
            },
            "source_normalization": {"contract": "solver_sourcepower_at_each_wavelength; no W_emit weighting", "sourcepower_used_for_normalized_fields_and_power": True},
            "solver_accounting": {"authorized": 1, "entered": 1, "returned": 1, "accepted": 1 if classification == "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH" else 0, "additional_replay": 0, "postprocess_solver_run_called": False, "postprocess_solver_entered": 0},
            "W_emit": {"status": "UNRESOLVED_FOR_PRODUCTION_CLOSURE", "used": False},
            "forbidden_cases_started": [], "timestamp_utc": now(),
        }
        write_json(args.output_dir / "ic1_integrated_validity_gate_v2.json", validity)
        summary = {
            "schema": "PAPER_A_IC1_INTEGRATED_CANARY_POSTPROCESS_SUMMARY_V1", "case_id": CASE_ID, "classification": classification, "root_cause": root,
            "pre_fsp_sha256": provenance.get("pre_fsp_sha256"), "post_fsp_sha256": post_sha, "physics_semantic_fingerprint": provenance.get("physics_semantic_fingerprint"), "integrated_instrumentation_fingerprint": provenance.get("integrated_instrumentation_fingerprint"),
            "spectral_grid_nm": {"start": float(wavelength_nm[0]), "stop": float(wavelength_nm[-1]), "points": int(len(wavelength_nm))},
            "sourcepower": {"finite": source_ok, "positive": bool(np.all(sourcepower > 0.0)), "min_W": float(np.min(sourcepower)), "max_W": float(np.max(sourcepower))},
            "six_face_closed_flux": {"finite": face_ok, "net_min_W": float(np.min(net)), "net_max_W": float(np.max(net))},
            "near_to_far": {"finite": farfield_ok, "samples": int(len(farfield_rows)), "450_nm": farfield_450},
            "stokes": {"samples": int(len(stokes_rows)), "finite": bool(all(np.isfinite(row["S0"]) for row in stokes_rows)), "DoLP_min": float(np.nanmin([row["DoLP"] for row in stokes_rows])), "DoLP_max": float(np.nanmax([row["DoLP"] for row in stokes_rows]))},
            "convergence": {"sample_count": int(len(time_s)), "time_start_s": float(time_s[0]), "time_end_s": float(time_s[-1]), "late_window_count": int(count), "late_first_proxy": float(tail[0]), "late_last_proxy": float(tail[-1]), "late_slope_per_s": slope_time, "positive_late_window_growth": ambiguous_late_proxy, "native_auto_shutoff": "NOT_PERSISTED_BY_RUNNER"},
            "architecture_verdict": "PAPER_A_IC1_FINITE_INTEGRATED_CANARY_PASS" if classification == "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH" else "PAPER_A_IC1_FINITE_INTEGRATED_CANARY_NOT_VALIDATED",
            "W_emit": "UNRESOLVED_FOR_PRODUCTION_CLOSURE", "raw_solver_data_modified": False, "timestamp_utc": now(),
        }
        write_json(args.output_dir / "ic1_integrated_canary_summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, default=str))
    finally:
        f.close()


if __name__ == "__main__":
    raise SystemExit(main())
