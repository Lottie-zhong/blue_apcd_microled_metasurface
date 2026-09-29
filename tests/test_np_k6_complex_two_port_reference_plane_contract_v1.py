import csv, json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "np_k6_complex_two_port_reference_plane_contract_v1"

def j(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))

class TestComplexTwoPortReferencePlaneContract(unittest.TestCase):
    def test_zero_solver_and_scope(self):
        m = j("contract_manifest.json")
        self.assertEqual(m["status"], "NP_COMPLEX_COEFFICIENT_NOT_COMPOSABLE_AS_SCATTERING_STATE")
        self.assertEqual(m["scope"]["hf_geometries"], 22)
        self.assertEqual(m["scope"]["logical_cases"], 44)
        self.assertEqual(m["scope"]["rows"], 484)
        self.assertEqual(m["governance"]["new_solver_calls"], 0)
        self.assertEqual(m["governance"]["coupling_target_reads"], 0)

    def test_coordinates_and_phase_gates(self):
        c = j("coordinate_audit.json")
        self.assertEqual(c["coordinate_values_nm"]["candidate_input_port"], "0^-")
        self.assertEqual(c["coordinate_values_nm"]["candidate_output_port"], "500^+")
        self.assertEqual(c["coordinate_values_nm"]["reflection_monitor_z"], -300.0)
        self.assertEqual(c["coordinate_values_nm"]["transmission_order_monitor_z"], 900.0)
        self.assertEqual(j("incident_phase_audit.json")["status"], "HARD_GATE_INCIDENT_COMPLEX_PHASE_REFERENCE_NOT_RECOVERABLE")
        self.assertEqual(j("deembedding_transform_audit.json")["status"], "CONDITIONAL_ANALYTIC_ONLY_NOT_FROZEN")

    def test_coupling_metadata_only_domain(self):
        d = j("coupling_geometry_domain_audit.json")
        self.assertEqual(d["coupling_case_count"], 20)
        self.assertEqual(d["exact_geometry_overlap_count"], 0)
        self.assertEqual(d["coupling_performance_labels_read"], 0)
        self.assertEqual(d["coupling_h1_errors_read"], 0)
        rows = list(csv.DictReader(open(OUT / "coupling_geometry_domain_audit.csv", encoding="utf-8-sig")))
        self.assertEqual(len(rows), 20)
        self.assertTrue(all(x["classification"] == "extrapolative" for x in rows))

if __name__ == "__main__":
    unittest.main()
