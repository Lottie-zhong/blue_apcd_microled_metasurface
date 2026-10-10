# Frozen scientific LOAD-only functions. No execution or resource control exports.

from __future__ import annotations


import json


import hashlib


import subprocess


import threading


import time


from datetime import datetime, timezone


from collections.abc import Mapping


from pathlib import Path


import numpy as np


Z0 = 376.730313668


LAUNCHER_ID = "APCD_PW_PERIODIC_PLANAR_CURRENT_V1"


def now():
    return datetime.now(timezone.utc).isoformat()


_REQUIRED_CONTRACT_FIELDS = (
    "monitors",
    "samples_nm",
    "references_nm",
    "materials",
    "stack_layers",
    "wavelengths_nm",
)


def _semantic_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _resolve_contract(cfg):
    """Resolve the frozen PW contract without supplying scientific defaults.

    Current production payloads store the scientific fields at
    ``pw_contract.contract``. Older valid payloads stored those fields
    directly under ``pw_contract``. The two forms are never merged: when
    both complete forms are present they must be semantically identical.
    """
    if not isinstance(cfg, Mapping) or "pw_contract" not in cfg:
        raise ValueError("PW_CONTRACT_SCHEMA_PATH_ERROR:pw_contract")
    wrapper = cfg["pw_contract"]
    if not isinstance(wrapper, Mapping):
        raise ValueError("PW_CONTRACT_SCHEMA_PATH_ERROR:pw_contract")

    nested_present = "contract" in wrapper
    legacy_keys = [key for key in _REQUIRED_CONTRACT_FIELDS if key in wrapper]
    if nested_present:
        nested = wrapper["contract"]
        if not isinstance(nested, Mapping):
            raise ValueError("PW_CONTRACT_SCHEMA_PATH_ERROR:pw_contract.contract")
        nested_missing = [key for key in _REQUIRED_CONTRACT_FIELDS if key not in nested]
        if nested_missing:
            raise ValueError("SCIENTIFIC_CONTRACT_FIELD_MISSING:" + ",".join(nested_missing))
        if legacy_keys:
            conflicts = [
                key
                for key in legacy_keys
                if _semantic_json(nested[key]) != _semantic_json(wrapper[key])
            ]
            if conflicts:
                raise ValueError("PW_CONTRACT_SCHEMA_CONFLICT:" + ",".join(conflicts))
            return nested, {
                "schema_path": "pw_contract.contract",
                "legacy_schema_present": True,
                "legacy_overlap_fields": legacy_keys,
                "resolution": "canonical_nested_verified_against_legacy_overlap",
            }
        return nested, {
            "schema_path": "pw_contract.contract",
            "legacy_schema_present": False,
            "resolution": "canonical_nested",
        }

    missing = [key for key in _REQUIRED_CONTRACT_FIELDS if key not in wrapper]
    if missing:
        raise ValueError("SCIENTIFIC_CONTRACT_FIELD_MISSING:" + ",".join(missing))
    return {key: wrapper[key] for key in _REQUIRED_CONTRACT_FIELDS}, {
        "schema_path": "pw_contract",
        "legacy_schema_present": True,
        "resolution": "legacy_top_level",
    }


def _contract(cfg):
    return _resolve_contract(cfg)[0]


def contract_resolution_provenance(cfg):
    """Return the accessor decision for audit/reporting without changing cfg."""
    return dict(_resolve_contract(cfg)[1])


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


GPU_COMPLETION_MARKERS = (
    "simulation complete",
    "simulation finished",
    "finished simulation",
    "early shutoff",
    "autoshutoff",
)


def load_only_validate(fd, cfg):
    monitors = _contract(cfg)["monitors"]
    for monitor in (monitors["input"], monitors["pre"], monitors["output"]):
        _ = fd.getdata(monitor, "f")
        for component in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz"):
            _ = fd.getdata(monitor, component)
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


def _surface_poynting_flux(fd, monitor, native_frequencies):
    try:
        from .pw_complex_floquet_state_v1 import PERIOD_X_M, PERIOD_Y_M
    except ImportError:
        from pw_complex_floquet_state_v1 import PERIOD_X_M, PERIOD_Y_M
    x = np.asarray(fd.getdata(monitor, "x"), dtype=float).reshape(-1)
    y = np.asarray(fd.getdata(monitor, "y"), dtype=float).reshape(-1)
    z = np.asarray(fd.getdata(monitor, "z"), dtype=float).reshape(-1)
    frequencies = np.asarray(fd.getdata(monitor, "f"), dtype=float).reshape(-1)
    native_frequencies = np.asarray(native_frequencies, dtype=float).reshape(-1)
    if x.size < 2 or y.size < 2 or z.size != 1:
        raise RuntimeError("OUTPUT_EH_MONITOR_GRID_INVALID")
    if frequencies.size != native_frequencies.size or not np.allclose(
            frequencies, native_frequencies, rtol=0.0, atol=1e-3):
        raise RuntimeError("OUTPUT_EH_FREQUENCY_GRID_MISMATCH")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise RuntimeError("OUTPUT_EH_COORDINATE_NONFINITE")
    dx, dy = np.diff(x), np.diff(y)
    if np.any(dx <= 0.0) or np.any(dy <= 0.0):
        raise RuntimeError("OUTPUT_EH_COORDINATES_NOT_STRICTLY_INCREASING")
    if not np.isclose(x[-1] - x[0], PERIOD_X_M, rtol=0.0, atol=1e-12):
        raise RuntimeError("OUTPUT_EH_X_SPAN_NOT_ONE_PERIOD")
    if not np.isclose(y[-1] - y[0], PERIOD_Y_M, rtol=0.0, atol=1e-12):
        raise RuntimeError("OUTPUT_EH_Y_SPAN_NOT_ONE_PERIOD")

    def field(component):
        value = np.asarray(_field(fd, monitor, component), dtype=complex)
        expected = (x.size, y.size, frequencies.size)
        if value.shape == (x.size, y.size, 1, frequencies.size):
            value = value[:, :, 0, :]
        elif value.shape != expected:
            raise RuntimeError(
                f"OUTPUT_EH_FIELD_SHAPE_MISMATCH:{component}:{value.shape}:expected={expected}")
        if not np.all(np.isfinite(value.real)) or not np.all(np.isfinite(value.imag)):
            raise RuntimeError("OUTPUT_EH_FIELD_NONFINITE:" + component)
        return value

    ex, ey = field("Ex"), field("Ey")
    hx, hy = field("Hx"), field("Hy")
    wx, wy = np.empty_like(x), np.empty_like(y)
    wx[0], wx[-1] = dx[0] / 2.0, dx[-1] / 2.0
    wy[0], wy[-1] = dy[0] / 2.0, dy[-1] / 2.0
    if x.size > 2:
        wx[1:-1] = (dx[:-1] + dx[1:]) / 2.0
    if y.size > 2:
        wy[1:-1] = (dy[:-1] + dy[1:]) / 2.0
    sz = 0.5 * np.real(ex * np.conj(hy) - ey * np.conj(hx))
    flux_w = np.einsum("i,j,ijf->f", wx, wy, sz)
    if not np.all(np.isfinite(flux_w)) or np.any(flux_w <= 0.0):
        raise RuntimeError("OUTPUT_EH_FLUX_NONPOSITIVE_OR_NONFINITE")
    return {
        "flux_W": flux_w,
        "surface_area_m2": float((x[-1] - x[0]) * (y[-1] - y[0])),
        "z_m": float(z[0]),
        "x_span_m": float(x[-1] - x[0]),
        "y_span_m": float(y[-1] - y[0]),
    }


def _output_source_power_normalization(fd, monitor, native_frequencies, wavelength_order, wavelengths_nm, canonical_state):
    try:
        from .pw_complex_floquet_state_v1 import PERIOD_X_M, PERIOD_Y_M
    except ImportError:
        from pw_complex_floquet_state_v1 import PERIOD_X_M, PERIOD_Y_M
    native_frequencies = np.asarray(native_frequencies, dtype=float).reshape(-1)
    wavelength_order = np.asarray(wavelength_order, dtype=int).reshape(-1)
    wavelengths_nm = np.asarray(wavelengths_nm, dtype=float).reshape(-1)
    if native_frequencies.size != wavelength_order.size or wavelengths_nm.size != wavelength_order.size:
        raise RuntimeError("OUTPUT_POWER_FREQUENCY_SHAPE_MISMATCH")
    if sorted(wavelength_order.tolist()) != list(range(wavelength_order.size)):
        raise RuntimeError("OUTPUT_POWER_WAVELENGTH_ORDER_INVALID")
    expected_wavelengths = 299792458.0 / native_frequencies[wavelength_order] * 1e9
    if not np.allclose(expected_wavelengths, wavelengths_nm, rtol=0.0, atol=1e-7):
        raise RuntimeError("OUTPUT_POWER_WAVELENGTH_ORDER_MISMATCH")
    transmission_native = np.real(np.asarray(fd.transmission(monitor))).reshape(-1)
    result = fd.getresult(monitor, "T")
    result_native = np.real(np.asarray(result["T"])).reshape(-1)
    sourcepower_native = np.real(np.asarray(fd.sourcepower(native_frequencies))).reshape(-1)
    if any(value.size != wavelength_order.size for value in (transmission_native, result_native, sourcepower_native)):
        raise RuntimeError("OUTPUT_POWER_DATA_SHAPE_MISMATCH")
    transmission = transmission_native[wavelength_order]
    result_transmission = result_native[wavelength_order]
    sourcepower = sourcepower_native[wavelength_order]
    if not np.all(np.isfinite(transmission)) or not np.all(np.isfinite(result_transmission)):
        raise RuntimeError("OUTPUT_TRANSMISSION_NONFINITE")
    if not np.allclose(transmission, result_transmission, rtol=1e-10, atol=1e-12):
        raise RuntimeError("OUTPUT_TRANSMISSION_API_PARITY_FAILED")
    state_wavelengths = np.asarray(canonical_state.get("wavelengths_nm", []), dtype=float).reshape(-1)
    normalization = canonical_state.get("normalization", {})
    incident_power_per_area = np.asarray(normalization.get("incident_power_per_area", []), dtype=float).reshape(-1)
    if state_wavelengths.size != wavelength_order.size or incident_power_per_area.size != wavelength_order.size:
        raise RuntimeError("IN_REF_POWER_SHAPE_MISMATCH")
    if not np.allclose(state_wavelengths, wavelengths_nm, rtol=0.0, atol=1e-7):
        raise RuntimeError("IN_REF_POWER_WAVELENGTH_MISMATCH")
    if not np.all(np.isfinite(sourcepower)) or np.any(sourcepower <= 0.0):
        raise RuntimeError("OUTPUT_SOURCEPOWER_NONPOSITIVE_OR_NONFINITE")
    if not np.all(np.isfinite(incident_power_per_area)) or np.any(incident_power_per_area <= 0.0):
        raise RuntimeError("IN_REF_POWER_NONPOSITIVE_OR_NONFINITE")
    if np.any(transmission < 0.0):
        raise RuntimeError("OUTPUT_TRANSMISSION_NEGATIVE")
    surface = _surface_poynting_flux(fd, monitor, native_frequencies)
    surface_flux = np.asarray(surface["flux_W"], dtype=float)[wavelength_order]
    incident_cell_power = PERIOD_X_M * PERIOD_Y_M * incident_power_per_area
    if not np.all(np.isfinite(incident_cell_power)) or np.any(incident_cell_power <= 0.0):
        raise RuntimeError("IN_REF_CELL_POWER_NONPOSITIVE_OR_NONFINITE")
    if not np.allclose(incident_cell_power, surface["surface_area_m2"] * incident_power_per_area,
                       rtol=0.0, atol=1e-24):
        raise RuntimeError("OUTPUT_EH_AREA_DISAGREES_WITH_IN_REF_CELL_AREA")
    monitor_transmitted_power = transmission * sourcepower
    p_scale = surface_flux / incident_cell_power
    if not np.all(np.isfinite(p_scale)) or np.any(p_scale < 0.0):
        raise RuntimeError("OUTPUT_P_SCALE_INVALID")
    monitor_flux_relative_difference = np.abs(monitor_transmitted_power - surface_flux) / np.maximum(
        np.maximum(np.abs(monitor_transmitted_power), np.abs(surface_flux)), 1e-300)
    return {
        "transmission": transmission,
        "sourcepower_W": sourcepower,
        "transmitted_power_W": surface_flux,
        "monitor_transmitted_power_W": monitor_transmitted_power,
        "monitor_flux_relative_difference": monitor_flux_relative_difference,
        "incident_power_per_area_W_m2": incident_power_per_area,
        "incident_cell_power_W": incident_cell_power,
        "surface_area_m2": surface["surface_area_m2"],
        "surface_z_m": surface["z_m"],
        "P_scale": p_scale,
    }


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


def analyze(fd, cfg, canonical_state=None):
    contract = _contract(cfg)
    monitors = contract["monitors"]
    samples = {str(k): float(v) for k, v in contract["samples_nm"].items()}
    references = {str(k): float(v) for k, v in contract["references_nm"].items()}
    materials = contract["materials"]
    from .mdc_tmm_complex_incident_power_v1 import normal_stack_power

    native_frequencies = _freq(fd, monitors["output"])
    native_wavelengths = 299792458.0 / native_frequencies * 1e9
    order = np.argsort(native_wavelengths)
    frequencies, wavelengths = native_frequencies[order], native_wavelengths[order]
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
    if canonical_state is None:
        try:
            from .pw_complex_floquet_state_v1 import canonical_state_from_fdtd
        except ImportError:
            from pw_complex_floquet_state_v1 import canonical_state_from_fdtd
        canonical_state = canonical_state_from_fdtd(fd, contract)
    output_normalization = _output_source_power_normalization(
        fd, monitors["output"], native_frequencies, order, wavelengths, canonical_state)
    a_fdtd, closures = 1.0 - r_fdtd - t_fdtd, np.abs(1.0 - (r_fdtd + t_fdtd + (1.0 - r_fdtd - t_fdtd)))
    tmm_rows = []
    for i, wl in enumerate(wavelengths):
        layers = [(complex(n_tio2[i]) if material == materials["mdc_tio2"] else complex(n_sio2[i]), float(thickness)) for material, thickness in contract["stack_layers"]]
        tmm = normal_stack_power(complex(n_gan[i]), 1.0 + 0j, layers, float(wl))
        tmm_rows.append({"wavelength_nm": float(wl), "R": float(tmm["R"]), "T": float(tmm["T"]), "A": float(1.0 - tmm["R"] - tmm["T"]), "A_stack_normalized": float(tmm["A_stack"] / tmm["power_entering"]), "power_entering": float(tmm["power_entering"]), "incident_interference_offset": float(tmm["incident_interference_offset"])})
    r_tmm = np.array([row["R"] for row in tmm_rows])
    t_tmm = np.array([row["T"] for row in tmm_rows])
    a_tmm = np.array([row["A"] for row in tmm_rows])
    orders_post = [_orders(fd, monitors["output"], int(original_index) + 1, float(output_normalization["P_scale"][i])) for i, original_index in enumerate(order)]
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

    for i, row in enumerate(rows):
        row.update({
            "output_sourcepower_W": float(output_normalization["sourcepower_W"][i]),
            "output_transmitted_power_W": float(output_normalization["transmitted_power_W"][i]),
            "output_monitor_transmitted_power_W": float(output_normalization["monitor_transmitted_power_W"][i]),
            "output_monitor_vs_EH_flux_relative_difference": float(output_normalization["monitor_flux_relative_difference"][i]),
            "output_incident_power_per_area_W_m2": float(output_normalization["incident_power_per_area_W_m2"][i]),
            "output_incident_cell_power_W": float(output_normalization["incident_cell_power_W"][i]),
            "output_P_scale_IN_REF": float(output_normalization["P_scale"][i]),
            "output_power_fraction_basis": "POSTNP_EH_surface_flux_over_IN_REF_incident_cell_power",
        })

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


def _save_raw_complex_fields(fd, cfg, case_root, prefix):
    try:
        from .pw_complex_floquet_state_v1 import read_fdtd_plane
    except ImportError:
        from pw_complex_floquet_state_v1 import read_fdtd_plane
    contract = _contract(cfg)
    monitor_by_plane = {"IN": contract["monitors"]["input"], "PRENP": contract["monitors"]["pre"], "POSTNP": contract["monitors"]["output"]}
    field_names = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
    arrays = {}
    plane_metadata = {}
    for plane, monitor in monitor_by_plane.items():
        raw = read_fdtd_plane(fd, monitor)
        for axis in ("x", "y", "z", "f"):
            arrays[f"{plane}_{axis}"] = np.asarray(raw[axis])
        fields = {}
        for name in field_names:
            key = f"{plane}_{name}"
            value = np.asarray(raw[name], dtype=complex)
            arrays[key] = value
            fields[name] = {"array_key": key, "shape": list(value.shape), "dtype": str(value.dtype), "complex": bool(np.iscomplexobj(value))}
        plane_metadata[plane] = {"monitor": monitor, "sample_nm": float(np.asarray(raw["z"]).reshape(-1)[0] * 1e9), "fields": fields}
    path = Path(case_root) / "raw" / f"{prefix}_raw_complex_fields.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    return {"schema": "APCD_PW_RAW_COMPLEX_FIELDS_V1", "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "planes": plane_metadata, "field_names": list(field_names), "frequency_order": "native_monitor_order"}


def postprocess(fd, cfg, case_root):
    try:
        from .pw_complex_floquet_state_v1 import canonical_state_from_fdtd, save_state_npz, state_metadata
    except ImportError:
        from pw_complex_floquet_state_v1 import canonical_state_from_fdtd, save_state_npz, state_metadata
    state = canonical_state_from_fdtd(fd, _contract(cfg))
    metrics = analyze(fd, cfg, state)
    prefix = f"{cfg['case']}__{cfg['attempt']}"
    raw_fields = _save_raw_complex_fields(fd, cfg, case_root, prefix)
    raw_path = Path(case_root) / "raw" / f"{prefix}_raw.json"
    projection_path = Path(case_root) / "projection" / f"{prefix}_projection.json"
    angular_path = Path(case_root) / "orders" / f"{prefix}_orders.json"
    state_path = Path(case_root) / "state" / f"{prefix}_pw_complex_floquet_state.npz"
    state_metadata_path = Path(case_root) / "state" / f"{prefix}_pw_complex_floquet_state.json"
    save_state_npz(state_path, state)
    state_meta = state_metadata(state, str(state_path))
    state_meta["sha256"] = hashlib.sha256(state_path.read_bytes()).hexdigest()
    _atomic(state_metadata_path, state_meta)
    raw = {"schema": "APCD_PW_PERIODIC_PLANAR_CURRENT_RAW_V1", "task_id": cfg["task"], "case_id": cfg["case"], "attempt_id": cfg["attempt"], "contract": cfg["pw_contract"], "metrics": metrics, "raw_complex_fields": raw_fields, "canonical_state": state_meta}
    _atomic(raw_path, raw)
    _atomic(projection_path, {"schema": "APCD_PW_PERIODIC_21_WAVELENGTH_PROJECTION_V1", "wavelengths_nm": metrics["wavelengths_nm"], "rows": metrics["rows"], "R": [row["R_FDTD"] for row in metrics["rows"]], "T": [row["T_FDTD"] for row in metrics["rows"]], "A": [row["A_FDTD"] for row in metrics["rows"]]})
    _atomic(angular_path, {"schema": "APCD_PW_PERIODIC_DIFFRACTION_ORDERS_V1", "wavelengths_nm": metrics["wavelengths_nm"], **metrics["orders"]})
    return raw, metrics, {"raw_json": raw_path, "raw_fields": Path(raw_fields["path"]), "projection": projection_path, "angular": angular_path, "state_npz": state_path, "state_metadata": state_metadata_path}
