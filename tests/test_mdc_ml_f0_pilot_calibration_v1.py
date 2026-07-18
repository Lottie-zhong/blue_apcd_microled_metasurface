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

import build_mdc_ml_f0_pilot_candidates_v1 as builder
import run_mdc_ml_f0_pilot_calibration_v1 as runner
import run_mdc_ml_f0_smoke_v1 as smoke
from mdc_ml_structure_grammar_v1 import DEFAULT_BOUNDS, GrammarError, TOPOLOGY_FAMILIES, validate_bounds


class F0PilotCalibrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = builder.load_config()
        cls.first = builder.build_candidates(cls.config)
        cls.second = builder.build_candidates(cls.config)
        cls.records = cls.first["records"]

    def test_fixed_seed_generates_512(self) -> None:
        self.assertEqual(self.config["seed"], 20260716)
        self.assertEqual(len(self.records), 512)

    def test_two_rebuilds_are_identical(self) -> None:
        self.assertEqual(self.first["signature"], self.second["signature"])
        self.assertEqual([row["sample_id"] for row in self.records], [row["sample_id"] for row in self.second["records"]])
        self.assertEqual([row["canonical_geometry_hash"] for row in self.records], [row["canonical_geometry_hash"] for row in self.second["records"]])

    def test_source_category_quotas(self) -> None:
        counts = Counter(row["source_category"] for row in self.records)
        self.assertEqual(counts, Counter({"FAMILY_STRATIFIED_GLOBAL": 320, "ANCHOR_NEIGHBORHOOD": 96, "FAMILY_CHALLENGE": 64, "RARE_CROSS_FAMILY": 32}))

    def test_family_quotas(self) -> None:
        for family in TOPOLOGY_FAMILIES:
            rows = [row for row in self.records if row["topology_family"] == family]
            counts = Counter(row["source_category"] for row in rows)
            self.assertEqual(counts["FAMILY_STRATIFIED_GLOBAL"], 40)
            self.assertEqual(counts["FAMILY_CHALLENGE"], 8)
            self.assertEqual(counts["RARE_CROSS_FAMILY"], 4)
            self.assertGreaterEqual(len(rows), 52)

    def test_512_canonical_and_physical_unique(self) -> None:
        self.assertEqual(len({row["canonical_geometry_hash"] for row in self.records}), 512)
        self.assertEqual(len({row["physical_configuration_hash"] for row in self.records}), 512)

    def test_illegal_structure_is_rejected(self) -> None:
        raw = deepcopy(self.records[0]["raw_structure"])
        raw["left_mirror"][0]["thickness_nm"] = 0
        with self.assertRaises(GrammarError):
            validate_bounds(raw)

    def test_duplicate_refill_is_deterministic(self) -> None:
        raw_a = builder.propose_family_structure(self.config["seed"], "FAMILY_STRATIFIED_GLOBAL", "off_center_defect", 0, 0)
        raw_duplicate = builder.propose_family_structure(self.config["seed"], "FAMILY_STRATIFIED_GLOBAL", "off_center_defect", 0, 0)
        raw_refill = builder.propose_family_structure(self.config["seed"], "FAMILY_STRATIFIED_GLOBAL", "off_center_defect", 0, 1)
        hash_a = validate_bounds(raw_a)["canonical_geometry_hash"]
        self.assertEqual(hash_a, validate_bounds(raw_duplicate)["canonical_geometry_hash"])
        self.assertNotEqual(hash_a, validate_bounds(raw_refill)["canonical_geometry_hash"])

    def test_mirror_reversal_is_not_deduplicated(self) -> None:
        raw = builder.propose_family_structure(self.config["seed"], "RARE_CROSS_FAMILY", "off_center_defect", 2, 0)
        mirrored = deepcopy(raw)
        mirrored["left_mirror"] = list(reversed(deepcopy(raw["right_mirror"])))
        mirrored["defect_region"] = list(reversed(deepcopy(raw["defect_region"])))
        mirrored["right_mirror"] = list(reversed(deepcopy(raw["left_mirror"])))
        mirrored["parameters"]["defect_offset_layers"] *= -1
        self.assertNotEqual(validate_bounds(raw)["canonical_geometry_hash"], validate_bounds(mirrored)["canonical_geometry_hash"])

    def test_anchor_authority_reads_three_tracked_rows(self) -> None:
        anchors = builder.load_anchor_authority(self.config)
        self.assertEqual([item["anchor_id"] for item in anchors], [item["id"] for item in self.config["anchors"]["preferred"]])
        self.assertTrue(all(item["authority_row"] > 1 for item in anchors))
        self.assertTrue(all(len(item["material_sequence"]) == len(item["thickness_sequence_nm"]) for item in anchors))

    def test_anchor_shortage_fails(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="f0_pre1_anchor_test_", dir=outputs))
        try:
            path = scratch / "empty.csv"
            path.write_text("static_structure_id,sequence_GaN_to_Air,effective_center_nm,C_nm\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                builder.load_anchor_authority(self.config, path)
        finally:
            shutil.rmtree(scratch)

    def test_level_b_and_tolerance_counts_are_zero(self) -> None:
        self.assertEqual(sum(row["level"] != "A" for row in self.records), 0)
        self.assertEqual(sum(row["tolerance_child"] for row in self.records), 0)

    def test_integer_nm_is_100_percent(self) -> None:
        self.assertTrue(all(all(isinstance(value, int) and not isinstance(value, bool) for value in row["canonical_thickness_sequence"]) for row in self.records))

    def test_all_bounds_and_media_are_frozen(self) -> None:
        for row in self.records:
            self.assertTrue(DEFAULT_BOUNDS["layer_count"][0] <= row["layer_count"] <= DEFAULT_BOUNDS["layer_count"][1])
            self.assertTrue(DEFAULT_BOUNDS["total_thickness_nm"][0] <= row["total_thickness_nm"] <= DEFAULT_BOUNDS["total_thickness_nm"][1])
            self.assertEqual(row["source_medium"], "APCD_GAN_NATIVE_M1")
            self.assertEqual(row["exit_medium"], "AIR")

    def test_static_gate_passes(self) -> None:
        gate = builder.validate_static_gate(self.first)
        self.assertEqual(gate["status"], "PASS", gate)

    def test_response_grids_are_frozen(self) -> None:
        self.assertEqual(self.config["frozen_commit"], self.config["spec_freeze_anchor"])
        grids = self.config["grids"]
        self.assertEqual((grids["spectral"]["wavelength_start_nm"], grids["spectral"]["wavelength_stop_nm"], grids["spectral"]["wavelength_step_nm"]), (420.0, 480.0, 0.1))
        self.assertEqual((grids["angular"]["angle_start_deg"], grids["angular"]["angle_stop_deg"], grids["angular"]["angle_step_deg"]), (-60.0, 60.0, 1.0))
        self.assertEqual((grids["apcd_ready"]["wavelength_start_nm"], grids["apcd_ready"]["wavelength_stop_nm"], grids["apcd_ready"]["wavelength_step_nm"]), (448.0, 453.0, 0.5))

    def test_workers_1_2_4_8_have_identical_synthetic_hashes(self) -> None:
        sample_ids = [row["sample_id"] for row in self.records[:8]]
        signatures = [runner.synthetic_parallel_signatures(sample_ids, workers) for workers in (1, 2, 4, 8)]
        self.assertEqual(len({json.dumps(value, sort_keys=True) for value in signatures}), 1)

    def test_windows_spawn_safe(self) -> None:
        result = runner.synthetic_parallel_signatures(["SPAWN_A", "SPAWN_B"], 2)
        self.assertEqual(set(result), {"metrics_signature", "array_signature", "ordering_signature"})

    def test_worker_exception_propagates(self) -> None:
        with self.assertRaises(RuntimeError):
            runner.synthetic_parallel_signatures(["FAIL_A"], 2, fail=True)

    def test_artifact_sha_and_array_content_hash(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="f0_pre1_artifact_test_", dir=outputs))
        try:
            arrays = {"x": np.arange(8, dtype=np.float64), "z": np.arange(4, dtype=np.complex128)}
            path = scratch / "artifact.npz"
            smoke.deterministic_npz(path, arrays)
            manifest = smoke.artifact_manifest_entry(path, arrays, {"test": "grid"})
            self.assertEqual(manifest["sha256"], runner.sha256_path(path))
            with np.load(path, allow_pickle=False) as loaded:
                reloaded = {name: loaded[name] for name in loaded.files}
            self.assertEqual(manifest["array_content_hash"], runner._array_content_hash(reloaded))
        finally:
            shutil.rmtree(scratch)

    def test_schema_dummy_validates(self) -> None:
        canonical = smoke.canonical_roundtrip(self.records[0]["raw_structure"])
        record = smoke.make_schema_dummy(canonical)
        self.assertEqual(smoke.validate_json_instance(record, smoke.load_schema()), [])

    def test_f0_baseline_cross_fidelity(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="f0_pre1_cross_test_", dir=outputs))
        try:
            result = runner.f0_cross_fidelity(self.config, scratch)
            self.assertEqual(result["status"], "PASS", result)
        finally:
            shutil.rmtree(scratch)

    def test_pareto_excludes_invalid_metrics(self) -> None:
        valid = {"sample_id": "VALID", "spectral_fwhm_valid": True, "angular_fwhm_valid": True, "spectral_boundary_clipped": False, "angular_boundary_clipped": False, "schema_valid": True, "artifact_valid": True, "angular_fwhm_450_deg": 10.0, "spectral_fwhm_normal_nm": 3.0, "cone5_integral_proxy": 0.2, "normal_band_transmission_proxy": 0.5, "topology_family": "symmetric_periodic", "source_category": "FAMILY_STRATIFIED_GLOBAL"}
        invalid = dict(valid, sample_id="INVALID", spectral_fwhm_valid=False, spectral_fwhm_normal_nm=0.0)
        result = runner.nominal_pareto([valid, invalid])
        self.assertEqual(result["valid_population"], 1)
        self.assertEqual(invalid["pareto_status"], "ineligible_invalid_metric_or_boundary")

    def test_pareto_rejects_zero_fwhm_even_if_mislabeled_valid(self) -> None:
        row = {"sample_id": "ZERO", "spectral_fwhm_valid": True, "angular_fwhm_valid": True, "spectral_boundary_clipped": False, "angular_boundary_clipped": False, "schema_valid": True, "artifact_valid": True, "angular_fwhm_450_deg": 10.0, "spectral_fwhm_normal_nm": 0.0, "cone5_integral_proxy": 0.2, "normal_band_transmission_proxy": 0.5, "topology_family": "symmetric_periodic", "source_category": "FAMILY_STRATIFIED_GLOBAL"}
        result = runner.nominal_pareto([row])
        self.assertEqual(result["valid_population"], 0)
        self.assertEqual(row["pareto_status"], "ineligible_invalid_metric_or_boundary")

    def test_pareto_reports_frozen_directions_and_correlations(self) -> None:
        base = {"spectral_fwhm_valid": True, "angular_fwhm_valid": True, "spectral_boundary_clipped": False, "angular_boundary_clipped": False, "schema_valid": True, "artifact_valid": True, "topology_family": "symmetric_periodic", "source_category": "FAMILY_STRATIFIED_GLOBAL"}
        rows = [
            dict(base, sample_id="A", angular_fwhm_450_deg=1.0, spectral_fwhm_normal_nm=4.0, cone5_integral_proxy=0.1, normal_band_transmission_proxy=0.2),
            dict(base, sample_id="B", angular_fwhm_450_deg=2.0, spectral_fwhm_normal_nm=3.0, cone5_integral_proxy=0.2, normal_band_transmission_proxy=0.4),
            dict(base, sample_id="C", angular_fwhm_450_deg=3.0, spectral_fwhm_normal_nm=2.0, cone5_integral_proxy=0.3, normal_band_transmission_proxy=0.6),
        ]
        result = runner.nominal_pareto(rows)
        self.assertEqual(result["objective_directions"]["angular_fwhm_450_deg"], "minimize")
        self.assertEqual(result["objective_directions"]["spectral_fwhm_normal_nm"], "minimize")
        self.assertEqual(result["objective_directions"]["cone5_integral_proxy"], "maximize")
        self.assertAlmostEqual(result["valid_population_pearson_correlations"]["angular_fwhm_450_deg"]["cone5_integral_proxy"], 1.0)
        self.assertIn("pareto_objective_ranges", result)

    @staticmethod
    def _quality_row(**overrides: object) -> dict[str, object]:
        row: dict[str, object] = {
            "sample_id": "QUALITY",
            "topology_family": "symmetric_periodic",
            "source_category": "FAMILY_STRATIFIED_GLOBAL",
            "finite_arrays": True,
            "schema_valid": True,
            "artifact_valid": True,
            "T450_unpolarized": 0.80,
            "normal_band_transmission_proxy": 0.70,
            "cone5_integral_proxy": 0.20,
            "spectral_fwhm_raw_nm": 3.0,
            "spectral_fwhm_normal_nm": 3.0,
            "spectral_fwhm_valid": True,
            "spectral_boundary_clipped": False,
            "angular_fwhm_450_deg": 8.0,
            "angular_fwhm_valid": True,
            "angular_boundary_clipped": False,
            "center_is_global_max": True,
            "maximum_angle_set_deg": [0.0],
            "secondary_peak_ratio": 0.10,
            "secondary_peak_count": 1,
        }
        row.update(overrides)
        return row

    def test_quality_mask_is_post_tmm_and_fields_are_independent(self) -> None:
        self.assertFalse(self.config["quality"]["pre_solver_performance_filtering_allowed"])
        row = self._quality_row(
            center_is_global_max=False,
            maximum_angle_set_deg=[-3.0, 3.0],
            T450_unpolarized=0.01,
            normal_band_transmission_proxy=0.02,
            secondary_peak_ratio=0.75,
        )
        mask = runner.quality_mask_fields(row, self.config)
        self.assertTrue(mask["nominal_4d_objective_eligible"])
        self.assertFalse(mask["shortlist_quality_eligible"])
        self.assertFalse(mask["peak_angle_zero_compatible"])
        self.assertTrue(mask["low_t450_flag"])
        self.assertTrue(mask["low_band_proxy_flag"])
        self.assertTrue(mask["strong_secondary_peak_flag"])

    def test_zero_width_serializes_null_and_is_pareto_ineligible(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="f0_pre1_zero_width_test_", dir=outputs))
        try:
            row = self._quality_row(
                sample_id="ZERO_WIDTH",
                spectral_fwhm_raw_nm=0.0,
                spectral_fwhm_normal_nm=None,
                spectral_fwhm_valid=False,
            )
            runner.apply_quality_masks([row], self.config)
            pareto = runner.nominal_pareto([row], self.config)
            self.assertEqual(pareto["valid_population"], 0)
            self.assertEqual(row["pareto_status"], "ineligible_invalid_metric_or_boundary")
            csv_path = scratch / "metrics.csv"
            json_path = scratch / "metrics.json"
            jsonl_path = scratch / "metrics.jsonl"
            runner.write_csv(csv_path, [row])
            runner.write_json(json_path, {"spectral_fwhm_normal_nm": row["spectral_fwhm_normal_nm"]})
            runner.write_jsonl(jsonl_path, [{"spectral_fwhm_normal_nm": row["spectral_fwhm_normal_nm"]}])
            self.assertIsNone(runner._read_csv_rows(csv_path)[0]["spectral_fwhm_normal_nm"])
            self.assertIsNone(json.loads(json_path.read_text(encoding="utf-8"))["spectral_fwhm_normal_nm"])
            self.assertIsNone(json.loads(jsonl_path.read_text(encoding="utf-8").strip())["spectral_fwhm_normal_nm"])
        finally:
            shutil.rmtree(scratch)

    def test_transmission_above_unity_is_retained_and_tolerance_diagnosed(self) -> None:
        row = self._quality_row(T450_unpolarized=1.0000791296228742)
        mask = runner.quality_mask_fields(row, self.config)
        self.assertEqual(mask["transmission_raw"], 1.0000791296228742)
        self.assertTrue(mask["transmission_above_unity_flag"])
        self.assertAlmostEqual(mask["transmission_above_unity_excess"], 7.912962287415226e-05)
        self.assertFalse(mask["power_balance_failure"])
        failure = runner.quality_mask_fields(self._quality_row(T450_unpolarized=1.002), self.config)
        self.assertTrue(failure["power_balance_failure"])
        self.assertEqual(failure["transmission_raw"], 1.002)

    def test_derived_quality_fields_do_not_change_core_signature_row(self) -> None:
        row = self._quality_row()
        before = runner.stable_hash(runner._signature_row(row))
        runner.apply_quality_masks([row], self.config)
        after = runner.stable_hash(runner._signature_row(row))
        self.assertEqual(before, after)

    def test_storage_accounting_uses_complete_calibration_not_whole_pre1(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="f0_pre1_storage_test_", dir=outputs))
        try:
            calibration = scratch / "calibration"
            artifacts = calibration / "artifacts"
            workers = scratch / "benchmark" / "workers_8"
            artifacts.mkdir(parents=True)
            workers.mkdir(parents=True)
            (calibration / "metadata.json").write_bytes(b"m" * 20)
            (artifacts / "sample.npz").write_bytes(b"a" * 30)
            (scratch / "candidate_manifest_v1.json").write_bytes(b"c" * 10)
            (workers / "repeat.npz").write_bytes(b"b" * 40)
            accounting = runner.storage_accounting(scratch, structure_count=2)
            self.assertEqual(accounting["categories"]["calibration_complete"]["bytes"], 50)
            self.assertEqual(accounting["formal_pilot_bytes_per_structure"], 25.0)
            self.assertEqual(accounting["formal_estimates"]["2000"]["base_bytes"], 50_000.0)
            self.assertGreater(accounting["whole_pre1_naive_bytes_per_structure"], 25.0)
        finally:
            shutil.rmtree(scratch)

    def test_objective_redundancy_warns_but_keeps_frozen_four_dimensions(self) -> None:
        rows = [
            self._quality_row(sample_id=f"R{index}", angular_fwhm_450_deg=float(index + 1), spectral_fwhm_normal_nm=float(5 - index), cone5_integral_proxy=float(index + 1), normal_band_transmission_proxy=float(index + 1) * 2.0)
            for index in range(4)
        ]
        runner.apply_quality_masks(rows, self.config)
        result = runner.nominal_pareto(rows, self.config)["objective_redundancy"]
        self.assertTrue(result["effective_redundancy_warning"])
        self.assertTrue(result["frozen_nominal_4d_retained"])
        self.assertTrue(result["recompute_each_formal_pilot"])

    def test_formal_2000_expectation_is_projection_not_guarantee(self) -> None:
        rows = []
        for index in range(8):
            row = self._quality_row(sample_id=f"E{index}", topology_family="symmetric_periodic" if index < 4 else "off_center_defect")
            row["nominal_4d_objective_eligible"] = index < 3
            rows.append(row)
        result = runner.formal_2000_expectation(rows)
        self.assertEqual(result["expected_four_objective_eligible"], 750.0)
        self.assertIn("not formal guarantees", result["statistical_limitation"])
        self.assertEqual(set(result["family_projection_at_observed_mix"]), {"off_center_defect", "symmetric_periodic"})

    def test_existing_outputs_validate_read_only_when_present(self) -> None:
        out = ROOT / self.config["output_directory"]
        if not (out / "calibration" / "manifest_v1.json").is_file():
            self.skipTest("PRE1 evidence bundle is not present")
        before = runner.output_tree_fingerprint(out)
        result = runner.validate_existing_outputs(self.config)
        after = runner.output_tree_fingerprint(out)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(before, after)
        self.assertEqual(result["quality_audit"]["nominal_4d_objective_eligible_count"], 157)
        self.assertEqual(result["zero_width_contract"]["raw_zero_count"], 9)
        self.assertTrue(result["legacy_storage_reconciliation"]["2000"]["matches_artifact_only"])

    def test_output_size_gate(self) -> None:
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="f0_pre1_size_test_", dir=outputs))
        try:
            (scratch / "small.bin").write_bytes(b"1234")
            self.assertEqual(runner.enforce_output_limit(scratch, 4), 4)
            with self.assertRaises(RuntimeError):
                runner.enforce_output_limit(scratch, 3)
        finally:
            shutil.rmtree(scratch)

    def test_frozen_files_are_unchanged(self) -> None:
        audit = runner.frozen_file_audit(self.config)
        self.assertEqual(audit["status"], "PASS", audit)

    def test_power_semantics_names_are_preserved(self) -> None:
        self.assertIn("A_stack", smoke.POWER_FIELDS)
        self.assertIn("far_field_balance_offset", smoke.POWER_FIELDS)
        self.assertNotIn("absorption", smoke.POWER_FIELDS)


if __name__ == "__main__":
    unittest.main()
