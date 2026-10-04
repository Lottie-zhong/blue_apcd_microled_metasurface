import json
import shutil
import tempfile
import unittest
from pathlib import Path

from controlled_admission_policy_v1 import (
    DIAGNOSTIC_SOURCE_SCHEMA,
    GEOMETRY_SOURCE_SCHEMA,
    MANIFEST_SCHEMA,
    PREENTRY_LOAD_SCHEMA,
    SETUP_SCHEMA,
    AdmissionError,
    canonical_bytes,
    canonical_sha256,
    file_sha256,
    setup_fingerprint,
    validate_case_admission,
)


HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = REPO_ROOT / "reports/apcd_gpu_production_runner_v1/CONTROLLED_CASE_ADMISSION_DESIGN_V1/CONTROLLED_CASE_ADMISSION_POLICY_V1.json"
LEGACY_CASE_IDS = [
    "K6V1_S21", "K6V1_S42", "K6V1_S36", "K6V1_S31",
    "K6V1_S45", "K6V1_S32", "K6V1_S47", "K6V1_S33",
    "K6V1_S37", "K6V1_S48", "K6V1_S35", "K6V1_S39",
]
PINNED_ADAPTER_SHA256 = "a9cfb11db584bf2ab96049b9066e198415bfba0863f29d0ed278230ffddc8579"
PINNED_RUNNER_SHA256 = "2ac168beb55f1242b646365b5d4cd9b06926c7eb46d0d8df6cdbeb3b59a290fe"
PINNED_CONTROLLED_POLICY_SHA256 = "b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45"
PINNED_CONTROLLED_AUTHORITY_SHA256 = "a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35"
PINNED_K6_V2_BUDGET_SHA256 = "e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c"


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def synthetic_base_setup():
    # Synthetic semantic fixture only. These values are not an APCD science setup.
    contract = {
        "schema": "SYNTHETIC_FIXTURE_ONLY",
        "materials": {"policy": "fixture-materials"},
        "source": {"policy": "fixture-plane-wave"},
        "polarization": ["fixture-a", "fixture-b"],
        "wavelengths_nm": [440, 460],
        "boundary_contract": {"x": "fixture-periodic", "y": "fixture-periodic", "z": "fixture-pml"},
        "mesh_contract": {"policy": "fixture-mesh"},
        "stopping_rule": {"policy": "fixture-stop"},
        "monitors": [{"name": "FIXTURE_EXISTING_MONITOR", "type": "fixture"}],
    }
    return {
        "ordered_D_nm": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
        "physical_contract": contract,
        "physical_contract_sha256": canonical_sha256(contract),
    }


def build_admission(tmp_root: Path, *, case_class: str, case_id: str,
                    ordered_d=None, contract=None, omit_proof=False,
                    manifest_override=None, mutate_staged_after=False):
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    base = synthetic_base_setup()
    ordered_d = list(ordered_d if ordered_d is not None else base["ordered_D_nm"])
    contract = contract if contract is not None else base["physical_contract"]
    attempt = "attempt_001"
    root = tmp_root / "authority"
    case_dir = root / case_id / attempt
    case_dir.mkdir(parents=True, exist_ok=True)

    contract_bytes = canonical_bytes(contract)
    contract_sha = __import__("hashlib").sha256(contract_bytes).hexdigest()
    contract_path = case_dir / "physical_contract.json"
    contract_path.write_bytes(contract_bytes)

    setup_fp = setup_fingerprint(
        case_class=case_class,
        case_id=case_id,
        attempt_id=attempt,
        ordered_d_nm=[float(x) for x in ordered_d],
        physical_contract_sha256=contract_sha,
        physical_contract_semantic_sha256=canonical_sha256(contract),
    )
    setup_path = case_dir / "resolved_setup.json"
    dump_json(setup_path, {
        "schema": SETUP_SCHEMA,
        "case_id": case_id,
        "attempt_id": attempt,
        "ordered_D_nm": ordered_d,
        "physical_contract_sha256": contract_sha,
        "physical_contract_semantic_sha256": canonical_sha256(contract),
        "setup_contract_fingerprint_sha256": setup_fp,
    })

    source_fsp = case_dir / "source.fsp"
    staged_fsp = case_dir / "staged.fsp"
    source_fsp.write_bytes(b"SYNTHETIC SOURCE FSP BYTES; NOT A LUMERICAL FILE")
    shutil.copyfile(source_fsp, staged_fsp)

    if case_class == "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1":
        provenance = {
            "schema": GEOMETRY_SOURCE_SCHEMA,
            "eligible": True,
            "case_id": case_id,
            "attempt_id": attempt,
            "ordered_D_nm": ordered_d,
            "expansion_manifest_sha256": policy["k6_geometry"]["geometry_source"]["required_expansion_manifest_sha256"],
        }
    else:
        provenance = {
            "schema": DIAGNOSTIC_SOURCE_SCHEMA,
            "case_id": case_id,
            "attempt_id": attempt,
            "proposal_sha256": policy["ext02_diagnostic"]["proposal_reference_sha256"],
            "added_monitor": policy["ext02_diagnostic"]["added_monitor"],
        }
    provenance_path = case_dir / "case_provenance_source.json"
    dump_json(provenance_path, provenance)

    proof_path = case_dir / "pre_entry_setup_load_proof.json"
    if not omit_proof:
        setup_readback = {"ordered_D_nm": ordered_d}
        if case_class == "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1":
            setup_readback["monitor_objects"] = [
                *[m for m in base["physical_contract"]["monitors"]],
                policy["ext02_diagnostic"]["added_monitor"],
            ]
        dump_json(proof_path, {
            "schema": PREENTRY_LOAD_SCHEMA,
            "load_only_pass": True,
            "solver_run_called": False,
            "scientific_entry_count": 0,
            "case_id": case_id,
            "attempt_id": attempt,
            "physical_contract_sha256": contract_sha,
            "physical_contract_semantic_sha256": canonical_sha256(contract),
            "setup_contract_fingerprint_sha256": setup_fp,
            "source_fsp_sha256": file_sha256(source_fsp),
            "staged_fsp_sha256": file_sha256(staged_fsp),
            "setup_readback": setup_readback,
        })

    artifacts = {
        "resolved_setup": {"path": setup_path.name, "sha256": file_sha256(setup_path)},
        "physical_contract": {"path": contract_path.name, "sha256": file_sha256(contract_path)},
        "source_fsp": {"path": source_fsp.name, "sha256": file_sha256(source_fsp)},
        "staged_fsp": {"path": staged_fsp.name, "sha256": file_sha256(staged_fsp)},
        "case_provenance_source": {"path": provenance_path.name, "sha256": file_sha256(provenance_path)},
    }
    if not omit_proof:
        artifacts["pre_entry_setup_load_proof"] = {
            "path": proof_path.name, "sha256": file_sha256(proof_path)
        }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "case_class": case_class,
        "case_id": case_id,
        "attempt_id": attempt,
        "physical_contract_sha256": contract_sha,
        "physical_contract_semantic_sha256": canonical_sha256(contract),
        "setup_contract_fingerprint_sha256": setup_fp,
        "artifacts": artifacts,
    }
    if manifest_override:
        manifest_override(manifest, base, contract_sha)
    manifest_path = case_dir / "source_manifest.json"
    dump_json(manifest_path, manifest)
    if mutate_staged_after:
        staged_fsp.write_bytes(b"MUTATED AFTER MANIFEST HASH")
    return policy, base, root, manifest_path, file_sha256(manifest_path)


class ControlledAdmissionPolicyTests(unittest.TestCase):
    def invoke(self, fixture, case_class):
        policy, base, root, manifest_path, manifest_sha = fixture
        return validate_case_admission(
            policy,
            case_class=case_class,
            base_setup=base,
            authority_root=root,
            manifest_path=manifest_path,
            expected_manifest_sha256=manifest_sha,
        )

    def test_legal_k6_geometry_change_has_its_own_setup_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = build_admission(
                Path(td),
                case_class="K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
                case_id="K6V1_SYNTHETIC_NEW01",
                ordered_d=[101, 111, 121, 131, 141, 151],
            )
            result = self.invoke(fixture, "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1")
            self.assertTrue(result["accepted"])
            self.assertEqual(result["physical_contract_sha256"], fixture[1]["physical_contract_sha256"])
            self.assertNotEqual(result["setup_contract_fingerprint_sha256"], fixture[1]["physical_contract_sha256"])
            self.assertFalse(result["solver_entry_performed"])

    def test_legal_ext02_monitor_overlay_has_new_contract_hash(self):
        with tempfile.TemporaryDirectory() as td:
            base = synthetic_base_setup()
            policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
            contract = dict(base["physical_contract"])
            contract["monitors"] = [
                *base["physical_contract"]["monitors"],
                policy["ext02_diagnostic"]["added_monitor"],
            ]
            fixture = build_admission(
                Path(td), case_class="EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1",
                case_id=policy["ext02_diagnostic"]["case_id"], contract=contract,
            )
            result = self.invoke(fixture, "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1")
            self.assertTrue(result["accepted"])
            self.assertNotEqual(result["physical_contract_sha256"], fixture[1]["physical_contract_sha256"])

    def test_k6_rejects_any_non_geometry_physics_change(self):
        with tempfile.TemporaryDirectory() as td:
            contract = synthetic_base_setup()["physical_contract"]
            contract["source"] = {"policy": "unauthorized-source-change"}
            fixture = build_admission(
                Path(td), case_class="K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
                case_id="K6V1_SYNTHETIC_NEW02", ordered_d=[102, 112, 122, 132, 142, 152],
                contract=contract,
            )
            with self.assertRaisesRegex(AdmissionError, "K6_PHYSICAL_CONTRACT_CHANGED"):
                self.invoke(fixture, "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1")

    def test_diagnostic_rejects_any_change_besides_the_one_declared_monitor(self):
        with tempfile.TemporaryDirectory() as td:
            base = synthetic_base_setup()
            policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
            contract = dict(base["physical_contract"])
            contract["wavelengths_nm"] = [441, 460]
            contract["monitors"] = [
                *base["physical_contract"]["monitors"],
                policy["ext02_diagnostic"]["added_monitor"],
            ]
            fixture = build_admission(
                Path(td), case_class="EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1",
                case_id=policy["ext02_diagnostic"]["case_id"], contract=contract,
            )
            with self.assertRaisesRegex(AdmissionError, "DIAGNOSTIC_CONTRACT_FIELDS_CHANGED:wavelengths_nm"):
                self.invoke(fixture, "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1")

    def test_diagnostic_rejects_reuse_of_old_contract_hash(self):
        with tempfile.TemporaryDirectory() as td:
            base = synthetic_base_setup()
            policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
            contract = dict(base["physical_contract"])
            contract["monitors"] = [
                *base["physical_contract"]["monitors"],
                policy["ext02_diagnostic"]["added_monitor"],
            ]

            def claim_old_hash(manifest, old_setup, actual_sha):
                manifest["physical_contract_sha256"] = old_setup["physical_contract_sha256"]

            fixture = build_admission(
                Path(td), case_class="EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1",
                case_id=policy["ext02_diagnostic"]["case_id"], contract=contract,
                manifest_override=claim_old_hash,
            )
            with self.assertRaisesRegex(AdmissionError, "PHYSICAL_CONTRACT_FILE_HASH_MISMATCH"):
                self.invoke(fixture, "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1")

    def test_staged_fsp_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = build_admission(
                Path(td), case_class="K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
                case_id="K6V1_SYNTHETIC_NEW03", ordered_d=[103, 113, 123, 133, 143, 153],
                mutate_staged_after=True,
            )
            with self.assertRaisesRegex(AdmissionError, "ARTIFACT_HASH_MISMATCH:staged_fsp"):
                self.invoke(fixture, "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1")

    def test_provenance_path_outside_authority_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = build_admission(
                Path(td), case_class="K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
                case_id="K6V1_SYNTHETIC_NEW06", ordered_d=[106, 116, 126, 136, 146, 156],
            )
            policy, base, root, manifest_path, _ = fixture
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            case_dir = manifest_path.parent
            source = case_dir / manifest["artifacts"]["case_provenance_source"]["path"]
            foreign = Path(td) / "outside-authority.json"
            shutil.copyfile(source, foreign)
            manifest["artifacts"]["case_provenance_source"]["path"] = str(foreign)
            dump_json(manifest_path, manifest)
            new_fixture = (policy, base, root, manifest_path, file_sha256(manifest_path))
            with self.assertRaisesRegex(AdmissionError, "CASE_PROVENANCE_SOURCE_PATH_OUTSIDE_AUTHORITY"):
                self.invoke(new_fixture, "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1")

    def test_new_case_requires_preentry_load_but_not_historical_truth_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = build_admission(
                Path(td), case_class="K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
                case_id="K6V1_SYNTHETIC_NEW04", ordered_d=[104, 114, 124, 134, 144, 154],
            )
            result = self.invoke(fixture, "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1")
            self.assertTrue(result["accepted"])
            self.assertFalse((fixture[3].parent / "post_entry_truth_recovery.json").exists())
            self.assertFalse(result["post_entry_truth_recovery_required_for_admission"])

    def test_new_case_without_preentry_load_proof_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = build_admission(
                Path(td), case_class="K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
                case_id="K6V1_SYNTHETIC_NEW05", ordered_d=[105, 115, 125, 135, 145, 155],
                omit_proof=True,
            )
            with self.assertRaisesRegex(AdmissionError, "SOURCE_MANIFEST_ARTIFACT_SET_INVALID"):
                self.invoke(fixture, "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1")

    def test_pinned_twelve_case_authority_and_production_route_files_are_current(self):
        authority_path = REPO_ROOT / "APCD_GPU_PRODUCTION_RUNNER_V1_AUTHORITY.json"
        adapter_path = REPO_ROOT / "scripts/shared_fdtd/gpu_runner_v1/adapter.py"
        runner_path = REPO_ROOT / "scripts/shared_fdtd/gpu_runner_v1/runner.py"
        controlled_dir = REPO_ROOT / "scripts/shared_fdtd/gpu_runner_v1"
        policy_path = controlled_dir / "controlled_admission_policy_v1.json"
        route_path = controlled_dir / "controlled_admission_authority_v1.json"
        budget_path = controlled_dir / "k6_v2_development_solver_budget_v1.json"
        authority = json.loads(authority_path.read_text(encoding="utf-8"))
        self.assertEqual(authority["approved_stage1_case_ids"], LEGACY_CASE_IDS)
        self.assertEqual(file_sha256(adapter_path), PINNED_ADAPTER_SHA256)
        self.assertEqual(file_sha256(runner_path), PINNED_RUNNER_SHA256)
        self.assertEqual(file_sha256(policy_path), PINNED_CONTROLLED_POLICY_SHA256)
        self.assertEqual(file_sha256(route_path), PINNED_CONTROLLED_AUTHORITY_SHA256)
        self.assertEqual(file_sha256(budget_path), PINNED_K6_V2_BUDGET_SHA256)
        adapter_text = adapter_path.read_text(encoding="utf-8")
        runner_text = runner_path.read_text(encoding="utf-8")
        # The adapter's new controlled route is opt-in. Legacy run manifests do
        # not carry this context; the V1 execution core remains route-agnostic.
        self.assertIn('controlled_context = manifest.pop("_controlled_admission", None)', adapter_text)
        self.assertIn("if controlled_context is not None:", adapter_text)
        self.assertNotIn("controlled_admission_policy_v1", runner_text)


if __name__ == "__main__":
    unittest.main()
