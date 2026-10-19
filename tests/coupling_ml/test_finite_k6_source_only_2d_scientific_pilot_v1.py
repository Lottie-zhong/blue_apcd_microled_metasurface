import importlib.util
import json
import tempfile
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("source_only_pilot", HERE.parent.parent / "scripts" / "coupling_ml" / "finite_k6_source_only_2d_scientific_pilot_v1.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def monitor_payload(prefix, coord_axis, coord, f, sign):
    nf = len(f)
    n = len(coord)
    fields = {
        "Ex": np.ones((n, nf), dtype=complex),
        "Ey": np.zeros((n, nf), dtype=complex),
        "Ez": np.zeros((n, nf), dtype=complex),
        "Hx": np.zeros((n, nf), dtype=complex),
        "Hy": np.zeros((n, nf), dtype=complex),
        "Hz": np.full((n, nf), sign, dtype=complex),
    }
    out = {
        f"{prefix}_coord_axis": np.array(coord_axis),
        f"{prefix}_x": np.asarray(coord if coord_axis == "x" else [0.0]),
        f"{prefix}_y": np.asarray(coord if coord_axis == "y" else [0.0]),
        f"{prefix}_f": f,
        f"{prefix}_T": np.ones(nf),
    }
    out.update({f"{prefix}_{key}": value for key, value in fields.items()})
    return out


def test_zero_solver_source_only_contract_and_derived_audits():
    source = Path(MODULE.__file__).read_text(encoding="utf-8")
    assert "addfdtd" not in source
    assert "adddipole" not in source
    assert source.count("fd.run()") == 1
    assert MODULE.FDTD_SPAN_UM == 19.0
    assert MODULE.MONITOR_SPAN_UM == 15.0
    assert MODULE.WLS.tolist() == list(range(445, 456))

    with tempfile.TemporaryDirectory() as td:
        MODULE.OUT = Path(td)
        f = 299792458.0 / (MODULE.WLS * 1e-9)
        raw = {}
        raw.update(monitor_payload("upward_monitor", "x", np.linspace(-7.5e-6, 7.5e-6, 5), f, -1.0))
        raw.update(monitor_payload("downward_monitor", "x", np.linspace(-7.5e-6, 7.5e-6, 5), f, 1.0))
        for name, axis in (("source_box_top", "x"), ("source_box_bottom", "x"), ("source_box_left", "y"), ("source_box_right", "y")):
            raw.update(monitor_payload(name, axis, np.linspace(-0.5e-6, 0.5e-6, 3), f, 1.0))
        raw.update({
            "wavelength_nm": MODULE.WLS,
            "frequency_hz": f,
            "source_dipolepower": np.ones(11),
            "source_sourcepower": np.ones(11),
            "post_fsp": np.array("post.fsp"),
            "post_fsp_sha256": np.array("sha"),
            "run_telemetry_json": np.array(json.dumps({"status": 2, "wall_time_s": 1.0})),
            "farfield_e2": np.ones((MODULE.N_FARFIELD, 11)),
            "farfield_theta_deg": np.tile(np.linspace(-90, 90, MODULE.N_FARFIELD)[:, None], (1, 11)),
            "farfield_polar_complex": np.array([]),
        })
        raw_path = MODULE.OUT / "SOURCE_ONLY_RAW_TRUTH.npz"
        np.savez_compressed(raw_path, **raw)
        derived = MODULE.derive_raw(raw_path)
        assert derived["finite"] is True
        assert derived["farfield"]["at_450_nm"]["F_0_60_fraction"] > 0
        assert (MODULE.OUT / "SOURCE_ONLY_POWER_ACCOUNTING.csv").is_file()
        assert (MODULE.OUT / "SOURCE_ONLY_APERTURE_CONVERGENCE.csv").is_file()
        assert (MODULE.OUT / "SOURCE_ONLY_EDGE_CAPTURE_AUDIT.csv").is_file()
        assert (MODULE.OUT / "SOURCE_ONLY_FARFIELD.npz").is_file()
