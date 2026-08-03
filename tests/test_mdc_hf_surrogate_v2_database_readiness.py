import csv
import json
import unittest
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
CONTRACTS = ROOT / "contracts" / "mdc_hf_surrogate_v2"
OUT = ROOT / "outputs" / "mdc_hf_surrogate_v2_database_readiness_v1" / "20260803T_fixed_v2_readiness_3c7fc18"


def load(name):
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


class FixedV2ReadinessTests(unittest.TestCase):
    def test_branch_provenance_and_fixed_v1_boundary(self):
        p = load("fixed_v2_branch_provenance.json")
        self.assertEqual(p["new_branch"], "work/mdc-hf-surrogate-v2")
        self.assertEqual(p["parent_commit"], "3c7fc182ac5f49e5c42b40b121d3a6e72ee0a4ad")
        self.assertFalse(p["solver_authorized"])
        self.assertFalse(p["training_authorized"])
        self.assertFalse(p["fixed_v1_outputs_moved"])

    def test_historical_roles_and_zero_reads(self):
        h = load("fixed_v2_historical_hf_data_registry.json")
        self.assertEqual(h["historical_geometries"], 27)
        self.assertEqual(h["historical_cases"], 162)
        self.assertEqual(h["datasets"]["HF15"]["status"], "EXPOSED_DEVELOPMENT_ONLY")
        self.assertEqual(h["datasets"]["replacement_R12"]["status"], "CONSUMED_EXTERNAL_DEVELOPMENT_ONLY")
        self.assertEqual(h["formal_label_value_reads"], 0)
        self.assertEqual(h["diagnostics_value_reads"], 0)
        self.assertFalse(h["datasets"]["replacement_R12"]["independent_test"])

    def test_profile_capability_is_b_and_joint_is_absent(self):
        a = load("existing_fsp_profile_capability_audit.json")
        self.assertEqual(a["classification"], "ONLY_SEPARATE_SPECTRAL_AND_SINGLE_WAVELENGTH_ANGULAR_AVAILABLE")
        self.assertEqual(a["checks"]["joint_wavelength_angle_power_distribution"]["status"], "ABSENT")
        self.assertTrue(a["upgrade_required_before_pilot"])
        self.assertEqual(a["new_solver_calls"], 0)

    def test_case_aggregation_and_np_contract(self):
        c = load("fixed_v2_case_label_schema.json")
        self.assertEqual(c["case_count_per_geometry"], 6)
        self.assertTrue(c["raw_before_normalization"])
        a = load("fixed_v2_aggregation_contract.json")
        self.assertEqual(a["position_aggregation"], "raw_position = 0.5 * raw_x + 0.5 * raw_z for each source position")
        n = load("fixed_v2_np_coupling_label_view_contract.json")
        self.assertEqual(n["target_order"], "+1")
        self.assertTrue(n["no_eta_up_r12_substitution"])

    def test_candidate_counts_and_no_overlap(self):
        p = load("fixed_v2_pilot4_candidate_manifest.json")
        d = load("fixed_v2_initial_doe96_candidate_manifest.json")
        t = load("fixed_v2_external_test_registry.json")
        self.assertEqual((p["candidate_count"], p["case_count"]), (4, 24))
        self.assertEqual((d["candidate_count"], d["case_count"]), (96, 576))
        self.assertEqual((t["geometry_count"], t["case_count"]), (40, 240))
        hashes = [x["geometry_hash"] for x in p["candidates"] + d["candidates"]]
        self.assertEqual(len(hashes), len(set(hashes)))
        self.assertEqual(load("fixed_v2_initial_doe_selection_audit.json")["duplicate_hash_collision_count"], 0)
        self.assertFalse(t["solver_authorized"])
        with (CONTRACTS / "fixed_v2_pilot4_case_matrix.csv").open(newline="", encoding="utf-8") as f:
            self.assertEqual(sum(1 for _ in csv.DictReader(f)), 24)
        with (CONTRACTS / "fixed_v2_initial_doe96_case_matrix.csv").open(newline="", encoding="utf-8") as f:
            self.assertEqual(sum(1 for _ in csv.DictReader(f)), 576)

    def test_compression_training_and_loss_are_frozen_without_fit(self):
        comp = load("profile_compression_candidate_contract.json")
        self.assertEqual([(x["method"], x["components"]) for x in comp["candidates"]], [("NMF", 16), ("NMF", 32), ("PCA", 16), ("PCA", 32)])
        tr = load("fixed_v2_training_contract.json")
        self.assertEqual(tr["model"]["initial_learning_rate"], 3e-4)
        self.assertEqual(tr["model"]["batch_definition"], "16 geometry groups = 96 case records; six cases of a geometry never cross split")
        self.assertFalse(tr["model"]["training_authorized"])
        loss = load("fixed_v2_loss_contract.json")
        self.assertEqual(loss["weights"]["profile"], 0.35)
        self.assertEqual(loss["smooth_l1_beta"], 1.0)
        self.assertTrue(loss["fwhm_cone_not_primary"])

    def test_readiness_and_safety(self):
        r = load("fixed_v2_database_readiness_manifest.json")
        self.assertEqual(r["status"], "MDC_HF_SURROGATE_V2_DATABASE_PILOT_REQUIRED_FOR_PROFILE_CONTRACT")
        self.assertFalse(r["bulk_authorized"])
        self.assertFalse(r["solver_authorized"])
        self.assertFalse(r["training_authorized"])
        self.assertTrue(all(v == 0 for v in r["safety_counts"].values()))
        self.assertTrue(OUT.joinpath("completion_manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
