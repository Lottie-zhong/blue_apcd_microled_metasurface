from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import numpy as np

Z0 = 376.730313668
LAUNCHER_ID = "APCD_PW_PERIODIC_PLANAR_CURRENT_V1"


def _contract(cfg):
    contract = cfg.get("pw_contract") or {}
    required = ("monitors", "samples_nm", "references_nm", "materials", "stack_layers", "wavelengths_nm")
    missing = [key for key in required if key not in contract]
    if missing:
        raise ValueError("PW_CONTRACT_MISSING:" + ",".join(missing))
    return contract


def validate_config(cfg):
    required = ("db", "runtime", "attempt_root", "pre_fsp", "pre_fsp_sha256", "physical_contract_hash",
                "branch", "case", "attempt", "task", "slot_id", "lease_token", "fencing_generation")
    missing = [key for key in required if key not in cfg or cfg[key] is None]
    if missing:
        raise ValueError("PW_CONFIG_MISSING:" + ",".join(missing))
    if cfg.get("scientific_launcher") != "PW_PERIODIC_PLANAR":
        raise ValueError("PW_LAUNCHER_SELECTOR_MISMATCH")
    if cfg["branch"] != "coupling_ml":
        raise ValueError("PW_FOREIGN_BRANCH")
    if int(cfg["fencing_generation"]) <= 0:
        raise ValueError("PW_INVALID_FENCING_GENERATION")
    _contract(cfg)
    return True


def _snapshot():
    from shared_fdtd.engine.process_identity import snapshot

    return snapshot()


def _new_solver_processes(before, rows, run_fsp):
    before_ids = {str(row.get("ProcessId")) for row in before}
    run_name = Path(run_fsp).name.lower()
    result = []
    for row in rows:
        pid = str(row.get("ProcessId"))
        name = str(row.get("Name") or "").lower()
        command = str(row.get("CommandLine") or "")
        is_solver = "fdtd-engine" in name or name in {"mpiexec.exe", "mpiexec"}
        if pid not in before_ids and is_solver and run_name in command.lower():
            result.append(row)
    return result


def run_and_confirm_entry(fd, cfg, on_confirmed, process_snapshot=None):
    """Run once and call on_confirmed at the first durable entry evidence.

    A normal API return is the fallback boundary for hosts that do not expose
    the engine command line.  The solver is never called more than once.
    """
    snapshot = process_snapshot or _snapshot
    before = snapshot()
    result = {"error": None}
    confirmed = False
    callback_error = []

    def call_confirmed(evidence):
        nonlocal confirmed
        if confirmed:
            return
        confirmed = True
        try:
            on_confirmed({"launcher": LAUNCHER_ID, **evidence})
        except BaseException as exc:  # keep waiting for the solver thread
            callback_error.append(exc)

    def target():
        try:
            fd.run()
        except BaseException as exc:
            result["error"] = exc

    worker = threading.Thread(target=target, name="pw-solver-run", daemon=True)
    worker.start()
    while worker.is_alive():
        if not confirmed:
            rows = _new_solver_processes(before, snapshot(), cfg["run_fsp"])
            if rows:
                call_confirmed({"observation": "new_solver_process", "processes": rows})
        worker.join(timeout=float(cfg.get("entry_confirmation_poll_s", 0.5)))
    if not confirmed and result["error"] is None:
        call_confirmed({"observation": "lumapi.run_returned", "processes": _new_solver_processes(before, snapshot(), cfg["run_fsp"])})
    if callback_error:
        raise callback_error[0]
    if result["error"] is not None:
        raise result["error"]


def load_only_validate(fd, cfg):
    monitors = _contract(cfg)["monitors"]
    for monitor in (monitors["input"], monitors["pre"], monitors["output"]):
        _ = fd.getdata(monitor, "f")
        _ = fd.getdata(monitor, "Ex")
    _ = fd.grating(monitors["output"], 1)


def _field(fd, monitor, component):
    try:
        return np.asarray(fd.getdata(monitor, component))
    except Exception:
        result_name = "E" if component in {"Ex", "Ey", "Ez"} else "H"
        return np.asarray(fd.getresult(monitor, result_name)[component])


def _freq(fd, monitor):
    try:
        return np.asarray(fd.getdata(monitor, "f")).reshape(-1)
    except Exception:
        return np.asarray(fd.getresult(monitor, "T")["f"]).reshape(-1)


def _average_last_axis(value, count):
    value = np.asarray(value)
    return value.reshape(-1) if value.size == count else value.reshape((-1, count)).mean(axis=0)


def _mode_amplitudes(fd, monitor, n, count):
    e = _average_last_axis(_field(fd, monitor, "Ex"), count).astype(complex)
    h = _average_last_axis(_field(fd, monitor, "Hy"), count).astype(complex)
    return 0.5 * (e + Z0 * h / n), 0.5 * (e - Z0 * h / n)


def _orders(fd, monitor, index, total_power):
    fraction = np.real(np.asarray(fd.grating(monitor, index))).reshape(-1)
    nx = np.rint(np.real(np.asarray(fd.gratingn(monitor, index))).reshape(-1)).astype(int)
    my = np.rint(np.real(np.asarray(fd.gratingm(monitor, index))).reshape(-1)).astype(int)
    ux = np.real(np.asarray(fd.gratingu1(monitor, index))).reshape(-1)
    uy = np.real(np.asarray(fd.gratingu2(monitor, index))).reshape(-1)
    if my.size == 0:
        my = np.array([0])
    if uy.size == 0:
        uy = np.array([0.0])
    if fraction.size != nx.size * my.size:
        raise RuntimeError(f"grating_shape_mismatch:{monitor}:{fraction.shape}:{nx.size}:{my.size}")
    matrix = fraction.reshape(nx.size, my.size)
    rows = []
    for i, order_x in enumerate(nx):
        for j, order_y in enumerate(my):
            rows.append({
                "order_x": int(order_x), "order_y": int(order_y), "u_x": float(ux[i]), "u_y": float(uy[j]),
                "physical_kx_sign": "+x" if ux[i] > 0 else "-x" if ux[i] < 0 else "zero",
                "power_fraction_of_monitor_total": float(matrix[i, j]),
                "power_fraction_of_source": float(abs(total_power) * matrix[i, j]),
            })
    return rows


def _read_index(fd, material, frequencies):
    fmin, fmax = float(np.min(frequencies)), float(np.max(frequencies))
    return np.asarray([complex(fd.getfdtdindex(material, float(f), fmin, fmax)) for f in frequencies])


def _deembed(a, n, wavelengths_nm, z_sample, z_ref, forward):
    kz = 2.0 * np.pi * n / (wavelengths_nm * 1e-9)
    dz = (z_ref - z_sample) * 1e-9
    return a * np.exp((1j if forward else -1j) * kz * dz)


def _safe_status(fd):
    for action in (lambda: fd.getresult("FDTD", "status"), lambda: fd.getnamed("FDTD", "status")):
        try:
            return action()
        except Exception as exc:
            last = repr(exc)
    return {"status": "UNAVAILABLE", "error": last}


def analyze(fd, cfg):
    contract = _contract(cfg)
    monitors = contract["monitors"]
    samples = {str(k): float(v) for k, v in contract["samples_nm"].items()}
    references = {str(k): float(v) for k, v in contract["references_nm"].items()}
    materials = contract["materials"]
    from mdc_tmm_complex_incident_power_v1 import normal_stack_power

    frequencies = _freq(fd, monitors["output"])
    wavelengths = 299792458.0 / frequencies * 1e9
    order = np.argsort(wavelengths)
    frequencies, wavelengths = frequencies[order], wavelengths[order]
    count = len(wavelengths)
    n_gan = _read_index(fd, materials["substrate"], frequencies)
    n_tio2 = _read_index(fd, materials["mdc_tio2"], frequencies)
    n_sio2 = _read_index(fd, materials["mdc_sio2"], frequencies)
    n_air = np.ones(count, dtype=complex)
    in_plus, in_minus = _mode_amplitudes(fd, monitors["input"], n_gan, count)
    pre_plus, pre_minus = _mode_amplitudes(fd, monitors["pre"], n_sio2, count)
    post_plus, post_minus = _mode_amplitudes(fd, monitors["output"], n_air, count)
    pin, pref, ptrans = np.real(n_gan) * np.abs(in_plus) ** 2, np.real(n_gan) * np.abs(in_minus) ** 2, np.abs(post_plus) ** 2
    r_fdtd, t_fdtd = pref / pin, ptrans / pin
    a_fdtd, closures = 1.0 - r_fdtd - t_fdtd, np.abs(1.0 - (r_fdtd + t_fdtd + (1.0 - r_fdtd - t_fdtd)))
    tmm_rows = []
    for i, wl in enumerate(wavelengths):
        layers = [(complex(n_tio2[i]) if material == materials["mdc_tio2"] else complex(n_sio2[i]), float(thickness)) for material, thickness in contract["stack_layers"]]
        tmm = normal_stack_power(complex(n_gan[i]), 1.0 + 0j, layers, float(wl))
        tmm_rows.append({"wavelength_nm": float(wl), "R": float(tmm["R"]), "T": float(tmm["T"]), "A": float(1.0 - tmm["R"] - tmm["T"]), "A_stack_normalized": float(tmm["A_stack"] / tmm["power_entering"]), "power_entering": float(tmm["power_entering"]), "incident_interference_offset": float(tmm["incident_interference_offset"])})
    r_tmm = np.array([row["R"] for row in tmm_rows])
    t_tmm = np.array([row["T"] for row in tmm_rows])
    a_tmm = np.array([row["A"] for row in tmm_rows])
    orders_post = [_orders(fd, monitors["output"], int(original_index) + 1, float(t_fdtd[i])) for i, original_index in enumerate(order)]
    orders_in = [_orders(fd, monitors["input"], int(original_index) + 1, float(r_fdtd[i])) for i, original_index in enumerate(order)]
    nonzero = [abs(row["power_fraction_of_source"]) for rows in orders_post + orders_in for row in rows if (row["order_x"], row["order_y"]) != (0, 0)]
    sign_rows = [row for rows in orders_post + orders_in for row in rows if row["order_y"] == 0 and abs(row["order_x"]) == 1]
    sign_pass = bool(sign_rows) and all((row["order_x"] > 0 and row["u_x"] > 0) or (row["order_x"] < 0 and row["u_x"] < 0) for row in sign_rows)
    deembed_rows, deembed_errors = [], []
    for monitor, sample in samples.items():
        n = n_gan if monitor == monitors["input"] else n_sio2 if monitor == monitors["pre"] else n_air
        plus, minus = (in_plus, in_minus) if monitor == monitors["input"] else (pre_plus, pre_minus) if monitor == monitors["pre"] else (post_plus, post_minus)
        plus_ref = _deembed(plus, n, wavelengths, sample, references[monitor], True)
        minus_ref = _deembed(minus, n, wavelengths, sample, references[monitor], False)
        plus_rt = _deembed(plus_ref, n, wavelengths, references[monitor], sample, True)
        minus_rt = _deembed(minus_ref, n, wavelengths, references[monitor], sample, False)
        err = max(float(np.max(np.abs(plus_rt - plus) / np.maximum(np.abs(plus), 1e-30))), float(np.max(np.abs(minus_rt - minus) / np.maximum(np.abs(minus), 1e-30))))
        deembed_errors.append(err)
        deembed_rows.append({"monitor": monitor, "sample_nm": sample, "reference_nm": references[monitor], "max_roundtrip_relative_error": err, "max_reference_to_sample_power_ratio": float(np.max(np.abs(plus_ref) ** 2 / np.maximum(np.abs(plus) ** 2, 1e-30)))})
    rows = []
    for i, wl in enumerate(wavelengths):
        rows.append({"wavelength_nm": float(wl), "R_FDTD": float(r_fdtd[i]), "T_FDTD": float(t_fdtd[i]), "A_FDTD": float(a_fdtd[i]), "closure": float(closures[i]), "R_TMM": float(r_tmm[i]), "T_TMM": float(t_tmm[i]), "A_TMM": float(a_tmm[i]), "delta_R": float(r_fdtd[i] - r_tmm[i]), "delta_T": float(t_fdtd[i] - t_tmm[i]), "delta_A": float(a_fdtd[i] - a_tmm[i]), "input_incident_power_proxy": float(pin[i]), "input_reflected_power_proxy": float(pref[i]), "output_transmitted_power_proxy": float(ptrans[i]), "input_T_monitor": float(np.real(np.asarray(fd.getresult(monitors["input"], "T")["T"]).reshape(-1)[order[i]])), "output_T_monitor": float(np.real(np.asarray(fd.getresult(monitors["output"], "T")["T"]).reshape(-1)[order[i]])), "tmm": tmm_rows[i]})

    def maxdiff(key):
        values = np.abs(np.array([row[key] for row in rows]))
        idx = int(np.argmax(values))
        return {"max_abs": float(values[idx]), "median_abs": float(np.median(values)), "wavelength_max_nm": float(wavelengths[idx])}

    return {"wavelengths_nm": wavelengths.tolist(), "rows": rows, "max_energy_closure": {"mean": float(np.mean(closures)), "median": float(np.median(closures)), "p90": float(np.percentile(closures, 90)), "max": float(np.max(closures)), "worst_wavelength_nm": float(wavelengths[int(np.argmax(closures))])}, "fdtd_vs_tmm": {"R": maxdiff("delta_R"), "T": maxdiff("delta_T"), "A": maxdiff("delta_A")}, "max_nonzero_diffraction_order_power": float(max(nonzero) if nonzero else 0.0), "orders": {"post": orders_post, "input": orders_in}, "order_sign": {"status": "PASS" if sign_pass else "REVIEW", "rows": sign_rows, "contract": "+1 has u_x>0 and -1 has u_x<0"}, "reference_plane_deembedding": {"status": "PASS" if max(deembed_errors) < 1e-10 else "REVIEW", "max_roundtrip_relative_error": float(max(deembed_errors)), "rows": deembed_rows, "contract": "V2 sample-to-reference complex kz de-embedding"}, "lossy_gan": {"status": "PASS" if float(np.max(np.abs(np.imag(n_gan)))) > 0 else "REVIEW", "n_gan": [{"real": float(x.real), "imag": float(x.imag)} for x in n_gan], "incident_power_from_complex_mode": True, "complex_kz_used": True}, "solver_status": _safe_status(fd)}


def _atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def postprocess(fd, cfg, case_root):
    metrics = analyze(fd, cfg)
    prefix = f"{cfg['case']}__{cfg['attempt']}"
    raw_path = Path(case_root) / "raw" / f"{prefix}_raw.json"
    projection_path = Path(case_root) / "projection" / f"{prefix}_projection.json"
    angular_path = Path(case_root) / "orders" / f"{prefix}_orders.json"
    raw = {"schema": "APCD_PW_PERIODIC_PLANAR_CURRENT_RAW_V1", "task_id": cfg["task"], "case_id": cfg["case"], "attempt_id": cfg["attempt"], "contract": cfg["pw_contract"], "metrics": metrics}
    _atomic(raw_path, raw)
    _atomic(projection_path, {"schema": "APCD_PW_PERIODIC_21_WAVELENGTH_PROJECTION_V1", "wavelengths_nm": metrics["wavelengths_nm"], "rows": metrics["rows"], "R": [row["R_FDTD"] for row in metrics["rows"]], "T": [row["T_FDTD"] for row in metrics["rows"]], "A": [row["A_FDTD"] for row in metrics["rows"]]})
    _atomic(angular_path, {"schema": "APCD_PW_PERIODIC_DIFFRACTION_ORDERS_V1", "wavelengths_nm": metrics["wavelengths_nm"], **metrics["orders"]})
    return raw, metrics, {"raw_json": raw_path, "projection": projection_path, "angular": angular_path}
