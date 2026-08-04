import json, os, unittest
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(os.environ.get("MDC_COMPRESSION_RUN", ROOT / "outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2"))

def read(name):
    return json.loads((RUN / name).read_text(encoding="utf-8"))

class ProfileCompressionTest(unittest.TestCase):
    def test_authorization_and_membership(self):
        a = read("profile_compression_authorization.json")
        self.assertEqual(a["status"], "PASS")
        self.assertTrue(a["compression_fit_authorized"])
        self.assertEqual((a["candidate_count"], a["crossfit_folds"]), (4, 5))
        self.assertFalse(a["neural_training_authorized"])
        self.assertFalse(a["test40_authorized"])
        m = read("profile_compression_membership_audit.json")
        self.assertEqual((m["compression_eligible_geometry_count"], m["compression_eligible_case_count"]), (96, 576))
        self.assertTrue(m["all_six_cases_in_one_fold"])
        self.assertFalse(m["HF15_included"])
        self.assertFalse(m["R12_included"])
        self.assertFalse(m["Pilot4_included"])
        self.assertFalse(m["test40_included"])

    def test_crossfit_candidates_and_selection(self):
        led = pd.read_csv(RUN / "profile_compression_crossfit_ledger.csv")
        self.assertEqual(len(led), 20)
        self.assertEqual(led.fit_count.sum(), 20)
        s = pd.DataFrame(read("profile_compression_crossfit_summary.json"))
        self.assertEqual(set(s.candidate_id), {"NMF16", "NMF32", "PCA16", "PCA32"})
        self.assertTrue(s.all_folds_complete.all())
        self.assertTrue(s.finite_metrics.all())
        self.assertTrue((s.nonfinite_count == 0).all())
        self.assertTrue((s.normalization_closure_max < 1e-12).all())
        self.assertEqual(read("profile_compression_crossfit_manifest.json")["selected_candidate"], "PCA32")
        self.assertEqual(read("profile_compression_selection_policy.json")["status"], "PRE_REGISTERED_BEFORE_FIT")

    def test_replay_and_final_compressor(self):
        r = read("profile_compression_reproducibility_audit.json")
        self.assertEqual(r["status"], "PASS")
        self.assertTrue(r["all_metric_values_exact"])
        self.assertEqual(r["selected_candidate"], "PCA32")
        self.assertEqual((r["crossfit_fits_replay_1"], r["crossfit_fits_replay_2"]), (20, 20))
        fm = read("final_profile_compressor_manifest.json")
        self.assertEqual((fm["compressor_id"], fm["components"], fm["fit_count"]), ("PCA32", 32, 1))
        self.assertTrue(Path(RUN / "final_profile_compressor.joblib").exists())
        self.assertEqual(len(pd.read_parquet(RUN / "final_profile_encoded_case_index.parquet")), 576)
        self.assertEqual(len(pd.read_parquet(RUN / "oof_latent_target_index.parquet")), 576)
        self.assertFalse(read("oof_fold_compressor_registry.json")["final_compressor_used_for_oof"])
        self.assertEqual(read("final_profile_reconstruction_audit.json")["status"], "PASS")

    def test_safety_and_interfaces(self):
        c = read("profile_compression_completion_manifest.json")
        self.assertEqual(c["status"], "MDC_HF_SURROGATE_V2_PROFILE_COMPRESSION_FROZEN_READY_FOR_OOF_MODEL_TRAINING_AUTHORIZATION_REVIEW")
        self.assertEqual(c["replay_status"], "PASS")
        self.assertEqual((c["crossfit_compression_fits"], c["replay_crossfit_compression_fits"], c["final_compressor_fits"]), (20, 40, 1))
        for k in ("neural_model_fits", "neural_optimizer_backward", "solver_calls", "fdtd_lumerical_calls", "TMM_calls", "RCWA_calls", "NP_solver_calls", "HF15_formal_value_reads", "HF15_diagnostics_reads", "R12_incompatible_profile_reads", "test40_reads", "sealed_test_reads", "active_learning_acquisitions"):
            self.assertEqual(c[k], 0, k)
        contract = read("profile_compression_input_contract_resolved.json")
        self.assertTrue(contract["relative_upward_power_excluded_from_profile"])
        self.assertIn("spectral_marginal x angular_marginal", contract["forbidden_inputs"])
        self.assertEqual(read("oof_profile_representation_contract.json")["status"], "PASS")
        self.assertEqual(read("profile_latent_training_interface.json")["status"], "PASS")
        self.assertEqual(read("future_model_output_schema.json")["status"], "PASS")

if __name__ == "__main__":
    unittest.main()
