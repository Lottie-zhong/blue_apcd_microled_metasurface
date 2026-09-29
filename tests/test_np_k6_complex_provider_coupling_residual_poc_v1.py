import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
POC=ROOT/"outputs"/"np_k6_complex_provider_coupling_residual_poc_v1"
def j(n):return json.loads((POC/n).read_text(encoding="utf-8"))
class TestComplexProviderCouplingResidualPOC(unittest.TestCase):
    def test_zero_solver_reference_plane_gate(self):
        m=j("poc_manifest.json");r=j("reference_plane_audit.json");p=j("provider_interface_contract.json")
        self.assertTrue(m["zero_solver"]);self.assertEqual(m["status"],"COMPLEX_COMPONENT_COMPOSITION_BLOCKED_REFERENCE_PLANE")
        self.assertFalse(r["composition_allowed"]);self.assertFalse(r["deterministic_transform_available"]);self.assertEqual(p["governance"]["new_solver"],0)
    def test_domain_and_masks(self):
        d=j("matched_domain_audit.json")
        self.assertEqual(d["np_domain"]["potential_rows"],484);self.assertEqual(d["coupling_domain"]["potential_metadata_rows"],440)
        self.assertEqual(d["row_accounting"]["valid_C_component_rows"],0);self.assertEqual(d["geometry_identity"]["overlap_count"],0)
        self.assertFalse(d["leakage_and_selection"]["sealed_hf_target_read"])
    def test_provider_capability_boundary(self):
        f=j("provider_interface_contract.json")["capability_flags"]
        self.assertTrue(f["NORMAL_INCIDENCE_ONLY"]);self.assertFalse(f["FULL_2x2_JONES_MATRIX"]);self.assertFalse(f["PRODUCTION_APPROVED"])
if __name__=="__main__":unittest.main()
