import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

from extract_controlled_monitor_load_only_v1 import (
    COMPONENTS,
    EXPECTED_WAVELENGTH_NM,
    MonitorExtractionError,
    find_h5_monitor_group,
    validate_lumerical_results,
)


def _results(nx=3, ny=2, nz=1):
    x = np.linspace(-0.87e-6, 0.87e-6, nx)
    y = np.linspace(-0.145e-6, 0.145e-6, ny)
    z = np.array([2.002e-6] * nz)
    wavelength = EXPECTED_WAVELENGTH_NM * 1e-9
    frequency = 299792458.0 / wavelength
    values = np.ones((nx, ny, nz, len(wavelength), 3), dtype=np.complex128)
    e = {"x": x, "y": y, "z": z, "lambda": wavelength, "f": frequency, "E": values}
    h = {"x": x, "y": y, "z": z, "lambda": wavelength, "f": frequency, "H": values * 2}
    return e, h


def _write_h5(path, e_result, omit=None, wrong_shape=False):
    with h5py.File(path, "w") as h5:
        group = h5.create_group("Monitor4")
        for key in ("x", "y", "z"):
            group.create_dataset(key, data=np.asarray(e_result[key]) * 1e6)
        nx, ny, nz = (len(e_result[k]) for k in ("x", "y", "z"))
        nf = len(e_result["f"])
        shape = (nz, ny, nx, 2 * nf)
        if wrong_shape:
            shape = (nz, ny, nx, nf)
        for component in COMPONENTS:
            if component == omit:
                continue
            group.create_dataset(component, data=np.ones(shape, dtype=np.float32))


class ControlledMonitorExtractionTests(unittest.TestCase):
    def test_six_complex_components_validate_and_keep_actual_coordinates(self):
        e, h = _results()
        normalized = validate_lumerical_results(e, h)
        self.assertEqual(sorted(normalized["fields"]), sorted(COMPONENTS))
        self.assertEqual(normalized["fields"]["Ex"].shape, (3, 2, 1, 21))
        self.assertEqual(normalized["coordinates_m"]["z"].tolist(), [2.002e-6])
        self.assertTrue(np.iscomplexobj(normalized["fields"]["Hx"]))

    def test_h5_bundle_matches_named_monitor_grid(self):
        e, h = _results()
        normalized = validate_lumerical_results(e, h)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run_output.h5"
            _write_h5(path, e)
            self.assertEqual(find_h5_monitor_group(path, normalized), "Monitor4")

    def test_h5_missing_component_fails_closed(self):
        e, h = _results()
        normalized = validate_lumerical_results(e, h)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run_output.h5"
            _write_h5(path, e, omit="Hz")
            with self.assertRaisesRegex(MonitorExtractionError, "H5_MATCHED_MONITOR_SCHEMA_INVALID"):
                find_h5_monitor_group(path, normalized)

    def test_h5_component_shape_mismatch_fails_closed(self):
        e, h = _results()
        normalized = validate_lumerical_results(e, h)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run_output.h5"
            _write_h5(path, e, wrong_shape=True)
            with self.assertRaisesRegex(MonitorExtractionError, "H5_MATCHED_MONITOR_SCHEMA_INVALID"):
                find_h5_monitor_group(path, normalized)

    def test_h5_corruption_and_coordinate_mismatch_fail_closed(self):
        e, h = _results()
        normalized = validate_lumerical_results(e, h)
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "corrupt.h5"
            bad.write_bytes(b"not hdf5")
            with self.assertRaisesRegex(MonitorExtractionError, "H5_BUNDLE_CORRUPT_OR_UNREADABLE"):
                find_h5_monitor_group(bad, normalized)
            mismatch = Path(temp) / "mismatch.h5"
            _write_h5(mismatch, e)
            with h5py.File(mismatch, "r+") as h5:
                h5["Monitor4/z"][0] += 0.1
            with self.assertRaisesRegex(MonitorExtractionError, "H5_MONITOR_GRID_MATCH_COUNT:0"):
                find_h5_monitor_group(mismatch, normalized)

    def test_e_h_grid_and_spectrum_mismatch_fail_closed(self):
        e, h = _results()
        h["z"] = np.array([2.003e-6])
        with self.assertRaisesRegex(MonitorExtractionError, "E_H_COORDINATE_MISMATCH:z"):
            validate_lumerical_results(e, h)
        e, h = _results()
        e["lambda"] = np.linspace(440e-9, 459e-9, 20)
        e["f"] = 299792458.0 / e["lambda"]
        e["E"] = np.ones((3, 2, 1, 20, 3), dtype=np.complex128)
        h["lambda"] = e["lambda"]
        h["f"] = e["f"]
        h["H"] = np.ones((3, 2, 1, 20, 3), dtype=np.complex128)
        with self.assertRaisesRegex(MonitorExtractionError, "MONITOR_SPECTRUM_LENGTH_MISMATCH"):
            validate_lumerical_results(e, h)


if __name__ == "__main__":
    unittest.main()
