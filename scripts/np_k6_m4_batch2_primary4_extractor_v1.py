"""Independent read-only extraction for one completed M4 Primary4 case."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")
import lumapi  # type: ignore


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1"
WAVELENGTHS = list(range(445, 456))
PLANES = ["N1_DIAG_PML_LOWER", "N1_DIAG_LOWER_OUTSIDE", "N1_DIAG_LOWER_INSIDE", "N1_DIAG_UPPER_INSIDE", "N1_DIAG_UPPER_OUTSIDE", "N1_DIAG_PML_UPPER"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def flat(value) -> np.ndarray:
    return np.asarray(value).reshape(-1)


def finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def result(fd, name: str) -> dict:
    try:
        data = fd.getresult(name, "T")
        return {"keys": list(data.keys()), **{key: flat(value) for key, value in data.items() if hasattr(value, "__len__")}}
    except Exception:
        try:
            return {"keys": ["transmission"], "T": flat(fd.transmission(name))}
        except Exception as exc:
            raise RuntimeError(f"result unavailable for {name}: {exc}")


def orders(fd, name: str, index: int) -> dict[str, np.ndarray | None]:
    result: dict[str, np.ndarray | None] = {}
    for field, function in (("fraction", "grating"), ("order", "gratingn"), ("u_x", "gratingu1")):
        try:
            result[field] = flat(getattr(fd, function)(name, index + 1))
        except Exception:
            result[field] = None
    return result


def named(fd, name: str, prop: str):
    try:
        value = fd.getnamed(name, prop)
        return value.tolist() if hasattr(value, "tolist") else value
    except Exception:
        return None


def runtime_log(run_dir: Path) -> dict:
    files = [p for p in run_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".log", ".txt", ".out", ".err"}]
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files)
    auto = [float(x) for x in re.findall(r"(?:Auto Shutoff|auto shutoff)[^0-9]*([0-9]+(?:\.[0-9]*)?(?:[eE][+-]?[0-9]+)?)", text)]
    elapsed = [float(x) for x in re.findall(r"(?:Elapsed simulation time|elapsed simulation time)[^0-9]*([0-9]+(?:\.[0-9]*)?)", text)]
    stop_reason = "auto_shutoff" if auto else ("engine_completed_without_auto_shutoff_readback" if text else "runtime_log_unavailable")
    return {"log_paths": [str(p) for p in files], "final_auto_shutoff": auto[-1] if auto else None, "final_elapsed_simulation_time_s": elapsed[-1] if elapsed else None, "stop_reason": stop_reason, "auto_shutoff_threshold": 1e-5, "log_tail": text[-5000:]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    args = parser.parse_args()
    case_id = args.case
    case_dir = OUT / "cases" / case_id
    run_dir = OUT / "runtime_runs" / case_id / "attempt_001"
    ledger = read_json(run_dir / "entered_ledger.json")
    contract = read_json(case_dir / "setup_contract.json")
    post = Path(ledger.get("post_fsp_path", ""))
    if not (ledger.get("entered") and ledger.get("run_invocation_count") == 1 and ledger.get("engine_completed") and ledger.get("post_saved") and post.exists()):
        raise RuntimeError("lifecycle incomplete; independent extraction refused")
    post_sha = sha256(post)
    if post_sha != ledger.get("post_fsp_sha256"):
        raise RuntimeError("post-FSP SHA mismatch")
    fd = lumapi.FDTD(str(post), hide=True)
    try:
        tr = result(fd, "transmission_monitor")
        rr = result(fd, "reflection_monitor")
        wavelengths = np.rint(np.real(tr.get("lambda", np.asarray(WAVELENGTHS) * 1e-9)) * 1e9).astype(int).tolist()
        if wavelengths != WAVELENGTHS:
            raise RuntimeError(f"exact wavelength mismatch: {wavelengths}")
        t = np.real(tr["T"])
        r_signed = np.real(rr["T"])
        if len(t) != 11 or len(r_signed) != 11:
            raise RuntimeError("T/R row count is not 11")
        freq = np.real(tr.get("f", np.asarray([299792458.0 / (w * 1e-9) for w in WAVELENGTHS])))
        tx_rows: list[dict] = []
        rx_rows: list[dict] = []
        metrics: list[dict] = []
        direct_mismatches: list[float] = []
        raw_t = None
        raw_r = None
        try:
            raw_t = np.real(flat(fd.getdata("transmission_monitor", "power")))
            raw_r = np.real(flat(fd.getdata("reflection_monitor", "power")))
        except Exception:
            pass
        for index, wavelength in enumerate(WAVELENGTHS):
            T = float(np.real(t[index]))
            R_signed = float(np.real(r_signed[index]))
            R = abs(R_signed)
            tx = orders(fd, "transmission_monitor", index)
            if any(tx[key] is None for key in ("fraction", "order", "u_x")):
                raise RuntimeError("transmitted order API incomplete")
            fractions = np.real(tx["fraction"]); order_numbers = np.rint(np.real(tx["order"])).astype(int); ux = np.real(tx["u_x"])
            absolute = T * fractions
            eta = {int(n): float(absolute[j]) for j, n in enumerate(order_numbers)}
            plus = eta.get(1, float("nan")); zero = eta.get(0, float("nan")); minus = eta.get(-1, float("nan"))
            angle = float("nan")
            plus_index = np.flatnonzero(order_numbers == 1)
            if len(plus_index):
                angle = float(np.degrees(np.arcsin(np.clip(ux[plus_index[0]], -1.0, 1.0))))
            for j, number in enumerate(order_numbers):
                tx_rows.append({"case_id": case_id, "wavelength_nm": wavelength, "order_n": int(number), "u_x": float(ux[j]), "angle_deg": float(np.degrees(np.arcsin(np.clip(ux[j], -1.0, 1.0)))), "transmitted_fraction": float(fractions[j]), "absolute_efficiency": float(absolute[j])})
            rx = orders(fd, "reflection_monitor", index)
            if rx["fraction"] is not None and rx["order"] is not None:
                rfrac = np.real(rx["fraction"]); rord = np.rint(np.real(rx["order"])).astype(int); rux = np.real(rx["u_x"]) if rx["u_x"] is not None else np.full(len(rord), np.nan)
                for j, number in enumerate(rord):
                    rx_rows.append({"case_id": case_id, "wavelength_nm": wavelength, "order_n": int(number), "u_x": float(rux[j]), "angle_deg": float(np.degrees(np.arcsin(np.clip(rux[j], -1.0, 1.0)))) if finite(rux[j]) else float("nan"), "reflected_fraction": float(rfrac[j]), "absolute_efficiency": float(R * rfrac[j])})
            sourcepower = float(fd.sourcepower(float(freq[index])))
            raw_tx = float(raw_t[index]) if raw_t is not None and len(raw_t) > index else float("nan")
            raw_rx = float(raw_r[index]) if raw_r is not None and len(raw_r) > index else float("nan")
            if finite(raw_tx) and finite(raw_rx) and sourcepower:
                direct_mismatches.extend([abs(raw_tx / sourcepower - T), abs(raw_rx / sourcepower - R_signed)])
            metrics.append({"case_id": case_id, "geometry_id": contract["geometry_id"], "geometry_hash": contract["geometry_hash"], "polarization": contract["polarization"], "wavelength_nm": wavelength, "frequency_hz": float(freq[index]), "T_total": T, "R_total": R, "R_signed_monitor": R_signed, "closure": T + R, "signed_closure_residual": 1.0 - T - R, "sourcepower_W": sourcepower, "raw_transmitted_power_W": raw_tx, "raw_reflected_power_W": raw_rx, "transmitted_order_sum": float(np.sum(absolute)), "transmitted_order_sum_mismatch": float(np.sum(absolute) - T), "eta_plus1": plus, "eta_0": zero, "eta_minus1": minus, "non_target_efficiency": float(T - plus) if finite(plus) else float("nan"), "directionality": float(plus / (plus + minus)) if finite(plus) and finite(minus) and plus + minus else float("nan"), "eta_plus1_over_minus1": float(plus / minus) if finite(plus) and finite(minus) and minus else float("nan"), "plus1_transmitted_fraction": float(plus / T) if finite(plus) and T else float("nan"), "plus1_air_side_angle_deg": angle, "transmitted_order_count": int(len(order_numbers)), "plus1_u_x": float(ux[plus_index[0]]) if len(plus_index) else float("nan")})
        plane_inventory = []
        plane_values: dict[tuple[str, int], float] = {}
        for name in PLANES:
            plane = result(fd, name)
            values = np.real(plane["T"])
            z = named(fd, name, "z")
            plane_inventory.append({"monitor": name, "z_m": float(z) if z is not None else None, "result_keys": plane.get("keys", []), "actual_order": None})
            for index, wavelength in enumerate(WAVELENGTHS):
                plane_values[(name, wavelength)] = float(values[index]) if len(values) > index else float("nan")
        plane_inventory.sort(key=lambda row: row["z_m"] if row["z_m"] is not None else float("inf"))
        for index, row in enumerate(plane_inventory, 1):
            row["actual_order"] = index
        boundary_rows = [{"case_id": case_id, "monitor": row["monitor"], "z_m": row["z_m"], "wavelength_nm": wavelength, "signed_normalized_flux": plane_values[(row["monitor"], wavelength)]} for row in plane_inventory for wavelength in WAVELENGTHS]
        interval_rows = []
        for first, second in zip(plane_inventory, plane_inventory[1:]):
            for wavelength in WAVELENGTHS:
                fa = plane_values[(first["monitor"], wavelength)]; fb = plane_values[(second["monitor"], wavelength)]
                interval_rows.append({"case_id": case_id, "from_monitor": first["monitor"], "to_monitor": second["monitor"], "wavelength_nm": wavelength, "flux_a": fa, "flux_b": fb, "delta_F": fb - fa, "abs_delta_F": abs(fb - fa)})
        structure_rows = [row for row in interval_rows if row["from_monitor"] == "N1_DIAG_LOWER_INSIDE" and row["to_monitor"] == "N1_DIAG_UPPER_INSIDE"]
        structure_anomaly = max((abs(float(row["delta_F"])) for row in structure_rows), default=float("nan"))
        fdtd = {prop: named(fd, "FDTD", prop) for prop in ("simulation time", "auto shutoff min", "mesh accuracy", "x span", "y span", "z span")}
        mesh = {prop: named(fd, "RUN3C_FIXED_NESTED_N2", prop) for prop in ("x", "y", "z", "x span", "y span", "z span", "dx", "dy", "dz")}
        materials = {}
        for name in ("APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            materials[name] = {"type": str(fd.getmaterial(name, "type"))}
            try:
                sampled = fd.getmaterial(name, "sampled data")
                materials[name]["sampled_rows"] = len(sampled)
            except Exception:
                materials[name]["sampled_rows"] = 0
        runtime = runtime_log(run_dir)
        closure_max = max(abs(float(row["signed_closure_residual"])) for row in metrics)
        order_max = max(abs(float(row["transmitted_order_sum_mismatch"])) for row in metrics)
        normalization_max = max(direct_mismatches) if direct_mismatches else float("nan")
        finite_metrics = all(finite(row[key]) for row in metrics for key in ("T_total", "R_total", "signed_closure_residual", "eta_plus1", "eta_0", "directionality"))
        quality = bool(finite_metrics and closure_max <= 0.01 and finite(structure_anomaly) and structure_anomaly <= 0.01 and order_max <= 1e-8 and finite(normalization_max) and normalization_max <= 1e-8)
        dominant = max(tx_rows, key=lambda row: row["absolute_efficiency"])["order_n"] if tx_rows else None
        manifest = {"schema_version": "np_k6_m4_batch2_primary4_extraction_manifest_v1", "case_id": case_id, "attempt_id": "attempt_001", "geometry_id": contract["geometry_id"], "geometry_hash": contract["geometry_hash"], "polarization": contract["polarization"], "post_fsp_path": str(post), "post_fsp_sha256": post_sha, "readonly_reload": True, "run_called": False, "save_called": False, "exact_11_points": wavelengths == WAVELENGTHS, "wavelengths_nm": WAVELENGTHS, "all_finite": finite_metrics, "max_abs_closure_residual": closure_max, "structure_interval_anomaly_max": structure_anomaly, "structure_anomaly_448": next((abs(float(row["delta_F"])) for row in structure_rows if row["wavelength_nm"] == 448), float("nan")), "order_sum_mismatch_max": order_max, "direct_raw_sourcepower_mismatch_max": normalization_max, "gate_closure_pass": closure_max <= 0.01, "gate_structure_pass": finite(structure_anomaly) and structure_anomaly <= 0.01, "gate_order_sum_pass": order_max <= 1e-8, "gate_direct_normalization_pass": finite(normalization_max) and normalization_max <= 1e-8, "quality_gate_pass": quality, "dominant_order": dominant, "runtime": runtime, "fdtd_readback": fdtd, "fixed_mesh_readback": mesh, "materials": materials, "boundary_monitor_inventory": plane_inventory, "provenance_complete": True}
        write_csv(case_dir / "hf_observations_long.csv", metrics)
        write_csv(case_dir / "hf_transmitted_orders_long.csv", tx_rows)
        write_csv(case_dir / "hf_reflected_orders_long.csv", rx_rows)
        write_csv(case_dir / "boundary_plane_flux_spectrum.csv", boundary_rows)
        write_csv(case_dir / "boundary_interval_flux_balance.csv", interval_rows)
        write_json(case_dir / "post_fsp_checksum.json", {"path": str(post), "sha256": post_sha, "size_bytes": post.stat().st_size, "sha_stable": sha256(post) == post_sha})
        write_json(case_dir / "runtime_readback.json", {"post_fsp_sha256": post_sha, "fdtd": fdtd, "fixed_mesh": mesh, "materials": materials, "runtime": runtime, "readonly_reload": True, "run_called": False, "save_called": False})
        write_json(case_dir / "extraction_manifest.json", manifest)
        ledger.update({"status": "quality_adjudicated", "extracted": True, "extraction_completed": True, "quality_gate_pass": quality, "training_label": quality, "candidate_performance_label": quality, "diagnostic_only": False, "extraction_manifest_path": str(case_dir / "extraction_manifest.json"), "max_abs_closure_residual": closure_max, "structure_interval_anomaly_max": structure_anomaly, "order_sum_mismatch_max": order_max, "direct_raw_sourcepower_mismatch_max": normalization_max, "dominant_order": dominant})
        write_json(case_dir / "attempt_ledger.json", ledger)
        write_json(run_dir / "entered_ledger.json", ledger)
        write_json(run_dir / "extraction_completion.json", {"case_id": case_id, "attempt_id": "attempt_001", "quality_gate_pass": quality, "extracted_timestamp_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
        print(json.dumps(manifest, indent=2, sort_keys=True, default=str))
    finally:
        fd.close()


if __name__ == "__main__":
    main()
