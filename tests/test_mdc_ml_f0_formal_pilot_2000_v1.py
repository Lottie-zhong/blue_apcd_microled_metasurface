from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_mdc_ml_f0_formal_pilot_2000_v1 as builder
import build_mdc_ml_f0_pilot_candidates_v1 as pre1_builder
import run_mdc_ml_f0_formal_pilot_2000_v1 as runner
import run_mdc_ml_f0_pilot_calibration_v1 as pre1
import run_mdc_ml_f0_smoke_v1 as smoke
from mdc_ml_structure_grammar_v1 import GrammarError, TOPOLOGY_FAMILIES, validate_bounds


class FormalPilot2000ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = builder.load_config()
        cls.first = builder.build_candidates(cls.config)
        cls.second = builder.build_candidates(cls.config)
        cls.records = cls.first["records"]

    def test_01_fixed_seed_and_count(self) -> None:
        self.assertEqual(self.config["formal_seed"], 20260718)
        self.assertEqual(len(self.records), 2000)

    def test_02_two_rebuilds_exact(self) -> None:
        self.assertEqual(self.first["signature"], self.second["signature"])
        self.assertEqual(self.first["records"], self.second["records"])

    def test_03_source_quotas_exact(self) -> None:
        self.assertEqual(Counter(row["source_category"] for row in self.records), Counter(self.config["source_quotas"]))

    def test_04_family_matrix_exact(self) -> None:
        for family in TOPOLOGY_FAMILIES:
            rows = [row for row in self.records if row["topology_family"] == family]
            actual = Counter(row["source_category"] for row in rows)
            expected = self.config["family_quotas"][family]
            self.assertEqual(len(rows), expected["total"])
            for category in builder.CATEGORY_ORDER:
                self.assertEqual(actual[category], expected[category])

    def test_05_formal_canonical_physical_unique(self) -> None:
        self.assertEqual(len({row["canonical_geometry_hash"] for row in self.records}), 2000)
        self.assertEqual(len({row["physical_configuration_hash"] for row in self.records}), 2000)

    def test_06_pre1_overlap_zero(self) -> None:
        self.assertEqual(self.first["audit"]["pre1_canonical_overlap"], 0)
        self.assertEqual(self.first["audit"]["pre1_physical_overlap"], 0)

    def test_07_smoke_overlap_zero(self) -> None:
        self.assertEqual(self.first["audit"]["smoke_canonical_overlap"], 0)
        self.assertEqual(self.first["audit"]["smoke_physical_overlap"], 0)

    def test_08_combined_unique_2512(self) -> None:
        self.assertEqual(self.first["audit"]["combined_pre1_formal_canonical_unique"], 2512)
        self.assertEqual(self.first["audit"]["combined_pre1_formal_physical_unique"], 2512)

    def test_09_anchor_authority_and_distribution(self) -> None:
        self.assertEqual(len(self.first["anchors"]), 3)
        self.assertEqual(self.first["audit"]["anchor_parent_counts"], self.config["anchor_quotas"])
        self.assertTrue(all(anchor["authority_row"] > 1 for anchor in self.first["anchors"]))

    def test_10_anchor_parents_excluded(self) -> None:
        self.assertEqual(self.first["audit"]["anchor_overlap"], 0)
        self.assertTrue(all(row["anchor_parent_excluded_from_formal"] for row in self.records))

    def test_11_illegal_candidate_rejected(self) -> None:
        raw = deepcopy(self.records[0]["raw_structure"])
        raw["left_mirror"][0]["thickness_nm"] = 0
        with self.assertRaises(GrammarError):
            validate_bounds(raw)

    def test_12_deterministic_refill_provenance(self) -> None:
        refilled = [row for row in self.records if row["generation_attempt"] > 0]
        self.assertTrue(refilled)
        self.assertTrue(all(row["collision_refill_provenance"]["accepted_attempt"] == row["generation_attempt"] for row in refilled))

    def test_13_level_b_zero(self) -> None:
        self.assertEqual(sum(row["level"] != "A" for row in self.records), 0)

    def test_14_tolerance_child_zero(self) -> None:
        self.assertEqual(sum(bool(row["tolerance_child"]) for row in self.records), 0)

    def test_15_integer_nm_100_percent(self) -> None:
        self.assertTrue(all(all(isinstance(value, int) and not isinstance(value, bool) for value in row["canonical_thickness_sequence"]) for row in self.records))

    def test_16_response_grids_frozen(self) -> None:
        pre1_config = pre1_builder.load_config()
        self.assertEqual(self.config["grids"], pre1_config["grids"])

    def test_17_quality_mask_post_tmm_only(self) -> None:
        self.assertEqual(self.config["quality"]["quality_mask_contract_id"], pre1.QUALITY_MASK_CONTRACT_ID)
        self.assertFalse(self.config["quality"]["pre_solver_performance_filtering_allowed"])

    @staticmethod
    def _metric_row(**overrides: object) -> dict[str, object]:
        row: dict[str, object] = {
            "sample_id": "FIXTURE", "topology_family": "symmetric_periodic", "source_category": "FAMILY_STRATIFIED_GLOBAL",
            "finite_arrays": True, "schema_valid": True, "artifact_valid": True,
            "T450_unpolarized": 0.8, "normal_band_transmission_proxy": 0.7, "cone5_integral_proxy": 0.2,
            "spectral_fwhm_raw_nm": 3.0, "spectral_fwhm_normal_nm": 3.0, "spectral_fwhm_valid": True, "spectral_boundary_clipped": False,
            "angular_fwhm_raw_deg": 8.0, "angular_fwhm_450_deg": 8.0, "angular_fwhm_valid": True, "angular_boundary_clipped": False,
            "center_is_global_max": True, "maximum_angle_set_deg": [0.0], "secondary_peak_ratio": 0.1, "secondary_peak_count": 1,
        }
        row.update(overrides)
        return row

    def test_18_invalid_fwhm_null_semantics(self) -> None:
        row = self._metric_row(spectral_fwhm_raw_nm=0.0, spectral_fwhm_normal_nm=None, spectral_fwhm_valid=False)
        pre1.apply_quality_masks([row], self.config)
        result = pre1.nominal_pareto([row], self.config)
        self.assertEqual(result["valid_population"], 0)
        self.assertIsNone(row["spectral_fwhm_normal_nm"])

    def test_19_t450_not_clipped(self) -> None:
        row = self._metric_row(T450_unpolarized=1.0000791296228742)
        mask = pre1.quality_mask_fields(row, self.config)
        self.assertEqual(mask["transmission_raw"], 1.0000791296228742)
        self.assertFalse(mask["power_balance_failure"])

    def test_20_anchor_control_records_authoritative(self) -> None:
        controls = runner.anchor_control_records(self.first, self.config)
        self.assertEqual([row["sample_id"] for row in controls], [row["anchor_id"] for row in self.first["anchors"]])

    def test_21_preflight_exact_four_per_family(self) -> None:
        selected = runner.select_preflight(self.records)
        self.assertEqual(len(selected), 32)
        self.assertEqual(Counter(row["topology_family"] for row in selected), Counter({family: 4 for family in TOPOLOGY_FAMILIES}))

    def test_22_run_contract_contains_resume_identity(self) -> None:
        contract = runner.run_contract(self.config, self.first["signature"])
        for key in ("candidate_signature", "config_sha256", "seed", "backend_provenance", "response_grid_ids", "worker_count", "schema_sha256", "expected_candidate_count"):
            self.assertIn(key, contract)

    def test_23_atomic_npz_write(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="formal_atomic_", dir=outputs))
        try:
            path = scratch / "artifact.npz"
            arrays = {"x": np.arange(4, dtype=np.float64)}
            runner._atomic_npz(path, arrays, "fixture")
            self.assertTrue(path.is_file())
            self.assertFalse(list(scratch.glob("*.tmp.npz")))
        finally:
            shutil.rmtree(scratch)

    def test_24_corrupt_checkpoint_rejected(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="formal_corrupt_", dir=outputs))
        try:
            path = scratch / "checkpoint.json"
            path.write_text("{broken", encoding="utf-8")
            checkpoint, reasons = runner.validate_checkpoint(path, self.records[0], runner.run_contract(self.config, self.first["signature"]))
            self.assertIsNone(checkpoint)
            self.assertTrue(reasons[0].startswith("checkpoint_read"))
        finally:
            shutil.rmtree(scratch)

    def test_25_retry_provenance_is_explicit_contract_field(self) -> None:
        self.assertIn("collision_refill_provenance", self.records[0])
        self.assertIn("rejected_before_acceptance", self.records[0]["collision_refill_provenance"])

    def test_26_worker_exception_propagates(self) -> None:
        with self.assertRaises(RuntimeError):
            pre1.synthetic_parallel_signatures(["FAIL"], 2, fail=True)

    def test_27_eight_worker_spawn_safe(self) -> None:
        result = pre1.synthetic_parallel_signatures([f"S{index}" for index in range(8)], 8)
        self.assertEqual(set(result), {"metrics_signature", "array_signature", "ordering_signature"})

    def test_28_artifact_sha_and_array_hash(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="formal_hash_", dir=outputs))
        try:
            path = scratch / "artifact.npz"
            arrays = {"x": np.arange(8, dtype=np.float64)}
            smoke.deterministic_npz(path, arrays)
            entry = smoke.artifact_manifest_entry(path, arrays, runner.grid_ids(self.config))
            self.assertEqual(entry["sha256"], runner.sha256_path(path))
            self.assertEqual(entry["array_content_hash"], pre1._array_content_hash(arrays))
        finally:
            shutil.rmtree(scratch)

    def test_29_schema_validation(self) -> None:
        canonical = smoke.canonical_roundtrip(self.records[0]["raw_structure"])
        self.assertEqual(smoke.validate_json_instance(smoke.make_schema_dummy(canonical), smoke.load_schema()), [])

    def test_30_combined_signature_deterministic(self) -> None:
        rows = [{"dataset_origin": "PRE1", "sample_id": "A"}, {"dataset_origin": "FORMAL_2000", "sample_id": "B"}]
        self.assertEqual(runner.stable_hash(rows), runner.stable_hash(deepcopy(rows)))

    def test_31_combined_contract_references_not_copies(self) -> None:
        self.assertEqual(self.config["pre1_output_directory"], "outputs/mdc_ml_f0_pilot_calibration_v1")
        self.assertNotEqual(self.config["pre1_output_directory"], self.config["output_directory"])

    def test_32_pareto_invalid_target_excluded(self) -> None:
        valid = self._metric_row(sample_id="VALID")
        invalid = self._metric_row(sample_id="INVALID", angular_fwhm_valid=False, angular_fwhm_450_deg=None)
        result = pre1.nominal_pareto([valid, invalid], self.config)
        self.assertEqual(result["valid_population"], 1)

    def test_33_storage_gate_constants(self) -> None:
        self.assertEqual(self.config["soft_output_bytes"], 700 * 1024 * 1024)
        self.assertEqual(self.config["maximum_output_bytes"], 800 * 1024 * 1024)

    def test_34_frozen_files_unchanged(self) -> None:
        self.assertEqual(runner.frozen_file_audit(self.config)["status"], "PASS")

    def test_35_existing_formal_output_validation_when_complete(self) -> None:
        out = ROOT / self.config["output_directory"]
        if not (out / "formal" / "manifest_v1.json").is_file():
            self.skipTest("formal output not complete")
        before = runner.output_fingerprint(out)
        result = runner.validate_existing_outputs(self.config)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(before, runner.output_fingerprint(out))

    def _training_row(self, **overrides: object) -> dict[str, object]:
        row = self._metric_row(solver_valid=True, **overrides)
        row.update(pre1.quality_mask_fields(row, self.config))
        row.update(runner.training_eligibility_fields(row, self.config))
        return row

    def test_36_training_eligibility_contract_and_fixed_tolerance(self) -> None:
        contract = self.config["training_eligibility"]
        self.assertEqual(contract["contract_id"], runner.TRAINING_ELIGIBILITY_CONTRACT_ID)
        self.assertEqual(contract["power_balance_tolerance"], 0.001)
        self.assertEqual(self.config["quality"]["transmission_power_balance_tolerance"], 0.001)

    def test_37_above_unity_within_tolerance_remains_eligible(self) -> None:
        row = self._training_row(T450_unpolarized=1.0000791296228742)
        self.assertTrue(row["transmission_above_unity_flag"])
        self.assertFalse(row["power_balance_failure"])
        self.assertTrue(row["continuous_regression_target_eligible"])
        self.assertTrue(row["nominal_4d_objective_eligible"])
        self.assertEqual(row["transmission_raw"], 1.0000791296228742)

    def test_38_excess_over_tolerance_is_failure_and_retained(self) -> None:
        row = self._training_row(T450_unpolarized=1.0011407212603527)
        self.assertTrue(row["solver_valid"])
        self.assertTrue(row["artifact_valid"])
        self.assertTrue(row["power_balance_failure"])
        self.assertTrue(row["validity_classification_eligible"])
        self.assertFalse(row["validity_classification_label"])
        self.assertFalse(row["continuous_regression_target_eligible"])
        self.assertFalse(row["nominal_4d_objective_eligible"])
        self.assertFalse(row["shortlist_quality_eligible"])
        self.assertTrue(all(value is False for value in row["continuous_regression_target_mask"].values()))

    def test_39_solver_success_is_distinct_from_power_balance_quality(self) -> None:
        row = self._training_row(T450_unpolarized=1.0011407212603527)
        self.assertTrue(row["solver_valid"])
        self.assertTrue(row["power_balance_failure"])

    def test_40_failure_excluded_from_pareto(self) -> None:
        valid = self._training_row(sample_id="VALID")
        failure = self._training_row(sample_id="FAILURE", T450_unpolarized=1.0011407212603527)
        result = runner.training_nominal_pareto([valid, failure], self.config)
        self.assertEqual(result["valid_population"], 1)
        self.assertNotEqual(failure.get("pareto_status"), "non_dominated")

    def test_41_failure_excluded_from_interesting_pool(self) -> None:
        failure = self._training_row(T450_unpolarized=1.0011407212603527)
        self.assertFalse(failure["interesting_candidate_eligible"])
        self.assertFalse(failure["pareto_eligible"])

    def test_42_training_readiness_boolean_semantics(self) -> None:
        readiness = self.config["training_readiness"]
        self.assertIs(readiness["ready_shared_surrogate"], True)
        self.assertIs(readiness["need_5000_before_training"], False)
        self.assertEqual(readiness["recommended_next_stage"], "SHARED_SURROGATE_V1")
        self.assertEqual(readiness["classification_population"], 2512)
        self.assertEqual(readiness["continuous_regression_population"], 737)

    def test_43_path_a_preserves_execution_identity(self) -> None:
        self.assertEqual(self.config["training_eligibility"]["postprocess_path"], "PATH_A")
        self.assertEqual(runner.config_hash(), "b7efde1a5fe76c7dc821f5e6fb276c1ecad2f339dc966a657d2a3184b6bbfa11")
        self.assertEqual(self.first["signature"], "fc8c1798fcc6d5b764f15bf6bb746d141143b49a05edd9e082de0b666ac21119")

    def test_44_existing_signatures_and_output_tree_unchanged(self) -> None:
        out = ROOT / self.config["output_directory"]
        if not (out / "manifest_v1.json").is_file():
            self.skipTest("formal output not complete")
        manifest = json.loads((out / "manifest_v1.json").read_text(encoding="utf-8"))
        formal = json.loads((out / "formal" / "manifest_v1.json").read_text(encoding="utf-8"))
        combined = json.loads((out / "combined" / "combined_2512_manifest_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["candidate_content_signature"], "fc8c1798fcc6d5b764f15bf6bb746d141143b49a05edd9e082de0b666ac21119")
        self.assertEqual(formal["dataset_content_signature"], "daea19d4b12cc704f39584589aa7539c5a36365639c1b745f6ebd8683ea4bc4c")
        self.assertEqual(combined["combined_2512_content_signature"], "d14b0555e488516dcd94443386a283a0cb7d8de119ab069d9ec20b2b93c7591d")
        self.assertEqual(runner.output_fingerprint(out), {
            "file_count": 4031,
            "bytes": 535974017,
            "tree_sha256": "3aa46df2ef99700f41f233b2800bd35b70b51bec1e54a6a714ed7014399a0f00",
        })

    def test_45_actual_failure_is_retained_but_continuous_ineligible(self) -> None:
        out = ROOT / self.config["output_directory"]
        if not (out / "formal" / "metrics_v1.csv").is_file():
            self.skipTest("formal output not complete")
        rows = pre1._read_csv_rows(out / "formal" / "metrics_v1.csv")
        derived = runner.apply_training_eligibility(rows, self.config)
        failures = [row for row in derived if row["power_balance_failure"]]
        self.assertEqual([row["sample_id"] for row in failures], ["F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0033"])
        failure = failures[0]
        self.assertTrue(failure["solver_valid"])
        self.assertFalse(failure["continuous_regression_target_eligible"])
        self.assertFalse(failure["nominal_4d_objective_eligible"])
        self.assertFalse(failure["shortlist_quality_eligible"])

    def test_46_invalid_fwhm_remains_null_under_training_contract(self) -> None:
        row = self._metric_row(spectral_fwhm_raw_nm=0.0, spectral_fwhm_normal_nm=None, spectral_fwhm_valid=False)
        row.update(pre1.quality_mask_fields(row, self.config))
        row.update(runner.training_eligibility_fields(row, self.config))
        self.assertIsNone(row["spectral_fwhm_normal_nm"])
        self.assertFalse(row["continuous_regression_target_eligible"])

    def test_47_classification_uses_all_combined_records(self) -> None:
        contract = self.config["training_eligibility"]
        self.assertTrue(contract["validity_classification_uses_all_combined_records"])
        self.assertTrue(contract["retain_all_legal_records_and_artifacts"])
        self.assertFalse(contract["raw_transmission_clipping_allowed"])


if __name__ == "__main__":
    unittest.main()
