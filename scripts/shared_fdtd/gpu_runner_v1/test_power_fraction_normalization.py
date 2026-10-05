# -*- coding: utf-8 -*-
import json
import sys
import unittest
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(HERE))
import adapter as runner_adapter
from shared_fdtd.tools import pw_complex_floquet_state_v1 as state_module
from shared_fdtd.tools import pw_scientific_launcher as launcher

class FakeMonitor:
    def __init__(self, wavelengths_nm, transmission, result_transmission=None,
                 sourcepower=None, surface_flux_w=None):
        self.native_wavelengths = np.asarray(wavelengths_nm, dtype=float)
        self.frequencies = 299792458.0 / (self.native_wavelengths * 1e-9)
        self.transmission_values = np.asarray(transmission, dtype=float)
        self.result_transmission = np.asarray(
            result_transmission if result_transmission is not None else transmission, dtype=float)
        self.sourcepower_values = np.asarray(sourcepower, dtype=float)
        self.surface_flux_w = np.asarray(surface_flux_w, dtype=float)
        self.sourcepower_frequencies = None
        self.x = np.asarray([-state_module.PERIOD_X_M/2, state_module.PERIOD_X_M/2])
        self.y = np.asarray([-state_module.PERIOD_Y_M/2, state_module.PERIOD_Y_M/2])
        self.z = np.asarray([1.8e-6])
        area = state_module.PERIOD_X_M * state_module.PERIOD_Y_M
        ex_amplitude = np.sqrt(2.0 * 376.730313668 * self.surface_flux_w / area)
        self.fields = {
            "Ex": np.broadcast_to(ex_amplitude.reshape(1,1,1,-1), (2,2,1,len(ex_amplitude))).copy().astype(complex),
            "Ey": np.zeros((2,2,1,len(ex_amplitude)), dtype=complex),
            "Hx": np.zeros((2,2,1,len(ex_amplitude)), dtype=complex),
            "Hy": np.broadcast_to((ex_amplitude/376.730313668).reshape(1,1,1,-1), (2,2,1,len(ex_amplitude))).copy().astype(complex),
        }
    def transmission(self, monitor):
        return self.transmission_values
    def getresult(self, monitor, name):
        return {"T": self.result_transmission}
    def sourcepower(self, frequencies):
        self.sourcepower_frequencies = np.asarray(frequencies)
        return self.sourcepower_values
    def getdata(self, monitor, component):
        if component == "x": return self.x
        if component == "y": return self.y
        if component == "z": return self.z
        if component == "f": return self.frequencies
        if component in self.fields: return self.fields[component]
        raise KeyError(component)

class FakeGrating:
    def grating(self, monitor, index):
        return np.asarray([0.25, 0.75])
    def gratingn(self, monitor, index):
        return np.asarray([-1, 0])
    def gratingm(self, monitor, index):
        return np.asarray([0])
    def gratingu1(self, monitor, index):
        return np.asarray([-0.2, 0.0])
    def gratingu2(self, monitor, index):
        return np.asarray([0.0])

class OutputPowerNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.native_wavelengths = np.asarray([450.0, 440.0])
        self.native_frequencies = 299792458.0 / (self.native_wavelengths * 1e-9)
        self.order = np.argsort(self.native_wavelengths)
        self.wavelengths = self.native_wavelengths[self.order]
        self.incident = np.asarray([4.0, 10.0])
        # T_monitor * sourcepower is deliberately different from the field integral.
        self.fd = FakeMonitor(self.native_wavelengths, [0.3, 0.2],
                              sourcepower=[5e-15, 2e-15],
                              surface_flux_w=[6e-16, 8e-16])
        self.state = {"wavelengths_nm": self.wavelengths,
                      "normalization": {"incident_power_per_area": self.incident}}
    def test_uses_postnp_eh_flux_not_zero_order_or_monitor_power_and_reorders(self):
        result = launcher._output_source_power_normalization(
            self.fd, "OUT", self.native_frequencies, self.order, self.wavelengths, self.state)
        area = state_module.PERIOD_X_M * state_module.PERIOD_Y_M
        expected = np.asarray([8e-16/(area*4.0), 6e-16/(area*10.0)])
        np.testing.assert_allclose(result["P_scale"], expected, rtol=1e-14, atol=0.0)
        np.testing.assert_allclose(result["transmitted_power_W"], [8e-16, 6e-16], rtol=1e-14)
        np.testing.assert_allclose(result["monitor_transmitted_power_W"], [4e-16, 1.5e-15], rtol=1e-14)
        np.testing.assert_allclose(self.fd.sourcepower_frequencies, self.native_frequencies)
        self.assertTrue(np.all(result["monitor_flux_relative_difference"] > 0.0))
    def test_order_source_fraction_scales_from_measured_physical_factor(self):
        scale = launcher._output_source_power_normalization(
            self.fd, "OUT", self.native_frequencies, self.order, self.wavelengths, self.state)["P_scale"][0]
        rows = launcher._orders(FakeGrating(), "OUT", 1, float(scale))
        self.assertAlmostEqual(sum(row["power_fraction_of_monitor_total"] for row in rows), 1.0)
        self.assertAlmostEqual(sum(row["power_fraction_of_source"] for row in rows), float(scale))
        np.testing.assert_allclose([row["power_fraction_of_source"] for row in rows],
                                   np.asarray([0.25, 0.75]) * scale, rtol=1e-14, atol=0.0)
    def test_rejects_transmission_api_disagreement(self):
        fd = FakeMonitor(self.native_wavelengths, [0.3, 0.2],
                         result_transmission=[0.31, 0.2],
                         sourcepower=[5e-15, 2e-15], surface_flux_w=[6e-16,8e-16])
        with self.assertRaisesRegex(RuntimeError, "OUTPUT_TRANSMISSION_API_PARITY_FAILED"):
            launcher._output_source_power_normalization(
                fd, "OUT", self.native_frequencies, self.order, self.wavelengths, self.state)
    def test_rejects_misaligned_or_nonpositive_in_ref_normalization(self):
        bad = {"wavelengths_nm": self.wavelengths,
               "normalization": {"incident_power_per_area": [4.0, 0.0]}}
        with self.assertRaisesRegex(RuntimeError, "IN_REF_POWER_NONPOSITIVE_OR_NONFINITE"):
            launcher._output_source_power_normalization(
                self.fd, "OUT", self.native_frequencies, self.order, self.wavelengths, bad)
        wrong_wavelengths = {"wavelengths_nm": [441.0, 450.0],
                             "normalization": {"incident_power_per_area": self.incident}}
        with self.assertRaisesRegex(RuntimeError, "IN_REF_POWER_WAVELENGTH_MISMATCH"):
            launcher._output_source_power_normalization(
                self.fd, "OUT", self.native_frequencies, self.order, self.wavelengths, wrong_wavelengths)
    def test_production_adapter_loads_the_pinned_versioned_launcher(self):
        loaded = runner_adapter.load_pinned_launcher()
        self.assertTrue(callable(loaded._output_source_power_normalization))
        self.assertTrue(callable(loaded._surface_poynting_flux))
    def test_actual_first_case_fsp_audit_fixture_has_distinct_power_scales(self):
        report = REPO / "reports" / "gpu_runner_v1_power_fraction_normalization_v1" / "INDEPENDENT_PHYSICAL_POWER_AUDIT.json"
        self.assertTrue(report.is_file(), "archived first-case FSP physical audit fixture missing")
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(data["run_id"], "K6V2_D1M05_20261004T175055Z_449c4f94")
        rows = data["wavelength_rows"]
        self.assertEqual(len(rows), 21)
        self.assertGreater(max(order["grating_eta_monitor_total"]
                               for row in rows for order in row["orders"]
                               if order["order_mn"] != [0,0]), 0.0)
        self.assertLess(max(row["monitor_flux_vs_EH_integral_relative_difference"] for row in rows), 1e-12)
        self.assertTrue(any(abs(row["sourcepower_W"]/row["IN_REF_incident_cell_power_W"]-1.0)>0.1
                            for row in rows))
        self.assertGreater(abs(rows[10]["runner_total_T_monitor"]-
                               rows[10]["runner_zero_order_T_FDTD_mode_proxy"]), 0.5)

if __name__ == "__main__":
    unittest.main()
