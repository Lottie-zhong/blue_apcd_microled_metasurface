import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(os.environ.get("MDC_DOE96_RUN", ROOT / "outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2"))

def read(name):
    return json.loads((RUN / name).read_text(encoding="utf-8"))

class DOE96JointProfileTest(unittest.TestCase):
    def test_authorization_and_solver_counts(self):
        a = read("doe96_solver_authorization.json")
        m = read("doe96_solver_run_manifest.json")
        self.assertEqual((a["authorized_tier"], a["authorized_geometry_count"], a["authorized_case_count"]), ("DOE96", 96, 576))
        self.assertTrue(a["DOE96_authorized"])
        self.assertFalse(a["external_test40_authorized"])
        self.assertFalse(a["model_training_authorized"])
        self.assertFalse(a["profile_compression_fit_authorized"])
        self.assertEqual((m["accepted_cases"], m["completed_unique_physical_cases"], m["total_solver_calls"]), (576, 576, 576))
        self.assertEqual(m["recovery_solver_calls"], 0)
        self.assertEqual(m["DOE96_solver_calls"], 576)

    def test_joint_quality_aggregation_and_grid(self):
        q = read("doe96_case_quality_audit_v1.json")
        g = read("doe96_geometry_label_manifest_v1.json")
        agg = read("doe96_aggregation_audit_v1.json")
        self.assertEqual(q["status"], "PASS")
        self.assertEqual(q["case_count"], 576)
        self.assertEqual(q["shape_set"], [[301, 2000]])
        self.assertEqual(q["min_finite_ratio"], 1.0)
        self.assertEqual(q["max_negative_count"], 0)
        self.assertTrue(q["raw_before_normalization_all"])
        self.assertEqual((g["geometry_count"], g["case_count_consumed"]), (96, 576))
        self.assertEqual(agg["status"], "PASS")
        self.assertTrue(agg["raw_before_normalization"])
        self.assertFalse(agg["case_normalization_before_aggregation"])
        self.assertEqual(read("doe96_joint_profile_quality_audit.json")["status"], "PASS")
        self.assertEqual(read("doe96_grid_consistency_audit.json")["status"], "PASS")

    def test_inheritance_replays_np_and_split_readiness(self):
        self.assertEqual(read("doe96_inherited_contract_audit.json")["status"], "PASS")
        lock = read("doe96_monitor_grid_lock.json")
        self.assertEqual((lock["wavelength_points"], lock["tensor_shape"]), (301, [301, 2000]))
        r = read("doe96_extraction_reproducibility_audit.json")
        self.assertEqual(r["status"], "PASS")
        self.assertTrue(r["all_exact"])
        self.assertEqual(read("doe96_np_interface_consumption_test.json")["status"], "PASS")
        self.assertEqual(read("doe96_np_interface_manifest_v1.json")["status"], "PASS")
        s = read("fixed_v2_grouped_split_readiness_audit.json")
        self.assertEqual(s["status"], "PASS")
        self.assertEqual((s["development_geometry_count"], s["development_case_count"]), (123, 738))
        self.assertTrue(s["exact_doe96_case_group_counts"]["all_six_cases"])
        self.assertEqual(s["exact_doe96_case_group_counts"]["duplicate_case_hash_count"], 0)
        self.assertTrue(s["test40_isolated"])

    def test_completion_guards(self):
        c = read("doe96_completion_manifest.json")
        self.assertEqual(c["status"], "MDC_HF_SURROGATE_V2_DOE96_DATABASE_COMPLETE_READY_FOR_PROFILE_COMPRESSION_AND_OOF_TRAINING_AUTHORIZATION_REVIEW")
        self.assertEqual(c["tier"], "DOE96")
        self.assertEqual((c["geometry_count"], c["accepted_cases"], c["joint_tensor_case_count"]), (96, 576, 576))
        s = c["solver_counters"]
        for k in ("HF15_formal_reads", "HF15_diagnostics_reads", "sealed_test_reads", "test40_reads", "TMM_calls", "RCWA_calls", "model_fits", "optimizer_backward", "recovery_solver_calls", "NP_solver_calls", "compression_fits", "active_learning_acquisitions"):
            self.assertEqual(s[k], 0, k)
        self.assertEqual(s["fdtd_lumerical_calls"], 576)
        self.assertEqual(read("regression_artifact_immutability_audit.json")["status"], "PASS")
        self.assertEqual(read("doe96_data_role_registry.json")["status"], "PASS")

if __name__ == "__main__":
    unittest.main()
