import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(os.environ.get("MDC_PILOT4_RUN", ROOT / "outputs/mdc_hf_surrogate_v2_pilot4_joint_profile_database_v1/20260803T_pilot4_joint_profile_151bd7c"))

def read(name):
    return json.loads((RUN / name).read_text(encoding="utf-8"))

class Pilot4JointProfileTest(unittest.TestCase):
    def test_authorization_and_solver_counts(self):
        a = read("pilot4_solver_authorization.json")
        m = read("pilot4_solver_run_manifest.json")
        self.assertEqual((a["authorized_tier"], a["authorized_geometry_count"], a["authorized_case_count"]), ("PILOT4", 4, 24))
        self.assertFalse(a["DOE96_authorized"])
        self.assertEqual((m["accepted_cases"], m["completed_unique_physical_cases"], m["total_solver_calls"]), (24, 24, 24))
        self.assertEqual(m["recovery_solver_calls"], 0)
        self.assertEqual(m["DOE96_solver_calls"], 0)

    def test_joint_quality_and_aggregation(self):
        q = read("pilot4_case_quality_audit_v1.json")
        g = read("pilot4_geometry_label_manifest_v1.json")
        agg = read("pilot4_aggregation_audit_v1.json")
        self.assertEqual(q["status"], "PASS")
        self.assertEqual(q["case_count"], 24)
        self.assertEqual(q["shape_set"], [[301, 2000]])
        self.assertEqual(q["min_finite_ratio"], 1.0)
        self.assertEqual(q["max_negative_count"], 0)
        self.assertTrue(q["raw_before_normalization_all"])
        self.assertEqual((g["geometry_count"], g["case_count_consumed"]), (4, 24))
        self.assertEqual(agg["status"], "PASS")
        self.assertTrue(agg["raw_before_normalization"])
        self.assertFalse(agg["case_normalization_before_aggregation"])

    def test_smoke_replays_and_np(self):
        self.assertEqual(read("pilot4_upgrade_smoke_audit.json")["status"], "PASS")
        r = read("pilot4_extraction_reproducibility_audit.json")
        self.assertEqual(r["status"], "PASS")
        self.assertTrue(r["all_exact"])
        self.assertEqual(read("pilot4_np_interface_consumption_test.json")["status"], "PASS")

    def test_final_gate_and_guards(self):
        c = read("pilot4_completion_manifest.json")
        self.assertEqual(c["status"], "MDC_HF_SURROGATE_V2_BULK_DATABASE_READY_AWAITING_96_GEOMETRY_576_CASE_AUTHORIZATION")
        s = c["solver_counters"]
        for k in ("DOE96_solver_calls", "HF15_formal_reads", "HF15_diagnostics_reads", "sealed_test_reads", "TMM_calls", "RCWA_calls", "model_fits", "optimizer_backward", "recovery_solver_calls"):
            self.assertEqual(s[k], 0, k)
        self.assertEqual(s["fdtd_lumerical_calls"], 24)

if __name__ == "__main__":
    unittest.main()
