# -*- coding: utf-8 -*-
"""Synthetic offline tests for the production versioned controlled-admission route."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter
import controlled_admission_v1 as controlled
import runner


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return Path(path)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _policy():
    return {
        "schema": controlled.POLICY_SCHEMA,
        "route_version": controlled.ROUTE_VERSION,
        "case_classes": {
            "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1": {
                "case_id": "K6V1_EXT02",
                "attempt_id": "attempt_001",
                "monitor_contract_key": "diagnostic",
                "monitor_name": "EXT02_POSTNP_DIAG_Z2000",
                "nominal_sample_z_nm": 2000.0,
                "reference_plane_nm": 1722.0,
                "span_nm": {"x": 1740.0, "y": 290.0},
                "monitor_type": "2D Z-normal",
                "components": ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"],
                "wavelengths_nm": {"start": 440, "stop": 460, "step": 1, "points": 21},
                "sampling": {
                    "spatial_interpolation": "nearest mesh cell",
                    "down_sample": {"x": 1, "y": 1, "z": 1},
                    "use_source_limits": True,
                    "override_global_monitor_settings": True,
                    "use_wavelength_spacing": True,
                    "wavelength_center_nm": 450.0,
                    "wavelength_span_nm": 20.0,
                    "output_power": True,
                },
                "actual_sampled_z_status": "UNAVAILABLE_BEFORE_SOLVER",
                "proposal_protocol_sha256": "a" * 64,
                "forbidden": ["replace", "move", "delete", "extra"],
            }
        }
    }


class ControlledAdmissionSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.case_root = self.root / "setup_root"
        self.trust = self.root / "trusted"
        self.policy = _policy()
        self.case_id = "K6V1_EXT02"
        self.attempt_id = "attempt_001"
        self.case_class = "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1"
        self.geometry = [220, 120, 155, 100, 105, 110]
        self.geometry_sha = "b" * 64
        self.expansion_sha = "c" * 64
        self.mesh_sha = "d" * 64
        self.monitor_sha = "e" * 64
        self.policy_sha = controlled.canonical_sha256(self.policy)
        self.authority_sha = "f" * 64
        self.case_dir = self.case_root / self.case_id / self.attempt_id
        self.case_dir.mkdir(parents=True)
        self.trust.mkdir()
        (self.case_dir / "setup").mkdir()

        self.base_fsp = self.trust / "base.fsp"
        self.base_fsp.write_bytes(b"synthetic base setup bytes")
        self.source_fsp = self.case_dir / "setup" / "source.fsp"
        self.staged_fsp = self.case_dir / "setup" / "runtime.fsp"
        self.source_fsp.write_bytes(b"synthetic diagnostic setup bytes")
        self.staged_fsp.write_bytes(self.source_fsp.read_bytes())
        self.base_fsp_sha = _sha(self.base_fsp)
        self.fsp_sha = _sha(self.staged_fsp)

        self.base_contract = {
            "monitors": {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"},
            "samples_nm": {"MON_IN": -100.0, "MON_PRENP": 1150.0, "MON_POSTNP": 1800.0},
            "references_nm": {"MON_IN": -50.0, "MON_PRENP": 1202.0, "MON_POSTNP": 1722.0},
            "materials": {"substrate": "Native-GaN", "pillar": "Native-TiO2"},
            "stack_layers": [["Native-TiO2", 44.0], ["Native-SiO2", 79.0]],
            "source": {"profile": "plane-wave-x-forward", "polarization_deg": 0.0},
            "mesh": {"authority": "5nm", "step_nm": 5.0},
            "boundaries": {"x": "Periodic", "y": "Periodic", "z": "PML"},
            "pml": {"axis": "z", "layers": 8},
            "stopping_rule": {"simulation_time_s": 3e-12, "auto_shutoff_min": 1e-6},
            "wavelengths_nm": [440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450,
                               451, 452, 453, 454, 455, 456, 457, 458, 459, 460],
        }
        self.base_contract_path = _write_json(self.trust / "base_contract.json", self.base_contract)
        self.base_contract_sha = _sha(self.base_contract_path)
        self.protocol_path = _write_json(self.trust / "protocol.json", {"frozen": True})
        self.geometry_source_path = _write_json(self.trust / "geometry_identity.json", {
            "case_id": self.case_id, "attempt_id": self.attempt_id,
            "ordered_D_nm": self.geometry, "geometry_hash_sha256": self.geometry_sha,
        })
        self.protocol_sha = _sha(self.protocol_path)
        self.geometry_source_sha = _sha(self.geometry_source_path)

        ext = self.policy["case_classes"][self.case_class]
        ext["proposal_protocol_sha256"] = self.protocol_sha
        self.policy_sha = controlled.canonical_sha256(self.policy)
        self.monitor = controlled._expected_monitor(self.policy)
        self.contract = copy.deepcopy(self.base_contract)
        self.contract["monitors"]["diagnostic"] = self.monitor["contract_entry"]
        self.contract_path = _write_json(self.case_dir / "physical_contract.json", self.contract)
        self.contract_sha = _sha(self.contract_path)
        self.semantic_sha = controlled.canonical_sha256(self.contract)

        self.provenance = {
            "schema": controlled.DIAGNOSTIC_SOURCE_SCHEMA,
            "case_id": self.case_id, "attempt_id": self.attempt_id,
            "proposal_sha256": self.protocol_sha,
            "base_setup_fsp_path": str(self.base_fsp),
            "base_setup_fsp_sha256": self.base_fsp_sha,
            "geometry_source_manifest_path": str(self.geometry_source_path),
            "geometry_source_manifest_sha256": self.geometry_source_sha,
            "ordered_D_nm": self.geometry,
            "geometry_hash_sha256": self.geometry_sha,
        }
        self.provenance_path = _write_json(self.case_dir / "case_provenance_source.json", self.provenance)
        base_pw = {"contract": copy.deepcopy(self.base_contract)}
        self.spec = {
            "case_id": self.case_id, "attempt_id": self.attempt_id,
            "ordered_D_nm": self.geometry, "geometry_hash_sha256": self.geometry_sha,
            "physical_contract_hash": self.base_contract_sha,
            "extension_manifest_sha256": self.expansion_sha,
            "mesh_contract_sha256": self.mesh_sha,
            "monitor_contract_sha256": self.monitor_sha,
            "pw_contract": base_pw,
        }
        self.spec_path = _write_json(self.case_dir / "five_nm_case_spec.json", self.spec)
        self.spec_sha = _sha(self.spec_path)
        self.fingerprint = controlled.setup_fingerprint(
            case_class=self.case_class, case_id=self.case_id, attempt_id=self.attempt_id,
            ordered_D_nm=self.geometry, physical_contract_sha256=self.contract_sha,
            physical_contract_semantic_sha256=self.semantic_sha)
        self.proof_path = self.case_dir / "pre_entry_setup_load_proof.json"
        existing = {name: {"base": {"same": True}, "source": {"same": True}, "staged": {"same": True}}
                    for name in ("MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION")}
        proof = {
            "schema": controlled.PROOF_SCHEMA, "result": "PASS", "load_only_pass": True,
            "route_version": controlled.ROUTE_VERSION, "case_class": self.case_class,
            "case_id": self.case_id, "attempt_id": self.attempt_id,
            "route_policy_sha256": self.policy_sha, "route_authority_sha256": self.authority_sha,
            "physical_contract_sha256": self.contract_sha,
            "physical_contract_semantic_sha256": self.semantic_sha,
            "setup_contract_fingerprint_sha256": self.fingerprint,
            "source_fsp_sha256": self.fsp_sha, "staged_fsp_sha256": self.fsp_sha,
            "solver_run_called": False, "scientific_entry_count": 0,
            "post_entry_truth_proved": False, "post_entry_truth_required_after_solver": True,
            "setup_readback": {
                "five_nm_validator_status": "PASS",
                "source_staged_semantic_parity": "PASS",
                "ordered_D_nm": self.geometry,
                "staged_fsp_readback": {"object_names": []},
                "added_monitor": {
                    "name": self.monitor["name"], "type": "DFTMonitor",
                    "monitor_type": self.monitor["monitor_type"],
                    "z_nm": self.monitor["nominal_z_nm"],
                    "actual_sampled_z_nm": None,
                    "actual_sampled_z_status": "UNAVAILABLE_BEFORE_SOLVER",
                },
                "existing_monitor_readbacks": existing,
            },
        }
        _write_json(self.proof_path, proof)
        self.setup_path = self.case_dir / "resolved_setup.json"
        _write_json(self.setup_path, {
            "schema": controlled.SETUP_SCHEMA, "route_version": controlled.ROUTE_VERSION,
            "case_class": self.case_class, "case_id": self.case_id, "attempt_id": self.attempt_id,
            "ordered_D_nm": self.geometry, "geometry_hash_sha256": self.geometry_sha,
            "physical_contract_sha256": self.contract_sha,
            "physical_contract_semantic_sha256": self.semantic_sha,
            "setup_contract_fingerprint_sha256": self.fingerprint,
            "base_setup_fsp_sha256": self.base_fsp_sha,
            "five_nm_case_spec_sha256": self.spec_sha,
        })
        self.source_manifest_path = self.case_dir / "source_manifest.json"
        self.source_manifest = {
            "schema": controlled.SOURCE_MANIFEST_SCHEMA, "route_version": controlled.ROUTE_VERSION,
            "case_class": self.case_class, "case_id": self.case_id, "attempt_id": self.attempt_id,
            "route_policy_sha256": self.policy_sha, "route_authority_sha256": self.authority_sha,
            "physical_contract_sha256": self.contract_sha,
            "physical_contract_semantic_sha256": self.semantic_sha,
            "setup_contract_fingerprint_sha256": self.fingerprint,
            "artifacts": {
                "resolved_setup": {"path": "resolved_setup.json", "sha256": _sha(self.setup_path)},
                "physical_contract": {"path": "physical_contract.json", "sha256": self.contract_sha},
                "source_fsp": {"path": "setup/source.fsp", "sha256": self.fsp_sha},
                "staged_fsp": {"path": "setup/runtime.fsp", "sha256": self.fsp_sha},
                "pre_entry_setup_load_proof": {"path": "pre_entry_setup_load_proof.json", "sha256": _sha(self.proof_path)},
                "case_provenance_source": {"path": "case_provenance_source.json", "sha256": _sha(self.provenance_path)},
                "five_nm_case_spec": {"path": "five_nm_case_spec.json", "sha256": self.spec_sha},
            },
        }
        _write_json(self.source_manifest_path, self.source_manifest)
        self.source_manifest_sha = _sha(self.source_manifest_path)
        self.authority = {
            "schema": controlled.AUTHORITY_SCHEMA, "route_version": controlled.ROUTE_VERSION,
            "policy_sha256": self.policy_sha, "setup_root": str(self.case_root),
            "base_contract_path": str(self.base_contract_path),
            "base_contract_sha256": self.base_contract_sha,
            "expansion_manifest_sha256": self.expansion_sha,
            "mesh_contract_sha256": self.mesh_sha, "monitor_contract_sha256": self.monitor_sha,
            "ext02": {
                "case_id": self.case_id, "attempt_id": self.attempt_id,
                "ordered_D_nm": self.geometry, "geometry_hash_sha256": self.geometry_sha,
                "protocol_sha256": self.protocol_sha,
                "base_setup_fsp_path": str(self.base_fsp),
                "base_setup_fsp_sha256": self.base_fsp_sha,
                "geometry_source_manifest_path": str(self.geometry_source_path),
                "geometry_source_manifest_sha256": self.geometry_source_sha,
                "protocol_path": str(self.protocol_path),
            },
            "k6_geometry_authorities": [],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def call_pack(self, **override):
        values = {
            "route_version": controlled.ROUTE_VERSION, "case_class": self.case_class,
            "case_id": self.case_id, "attempt_id": self.attempt_id,
            "geometry": self.geometry, "expansion_sha256": self.expansion_sha,
            "pre_fsp_path": str(self.staged_fsp), "pre_fsp_sha256": self.fsp_sha,
            "physical_contract_path": str(self.contract_path),
            "physical_contract_sha256": self.contract_sha,
            "source_manifest_path": str(self.source_manifest_path),
            "source_manifest_sha256": _sha(self.source_manifest_path),
            "policy": self.policy, "authority": self.authority,
            "policy_sha256": self.policy_sha, "authority_sha256": self.authority_sha,
            "case_root": self.case_root, "base_contract": self.base_contract,
            "base_contract_sha256": self.base_contract_sha,
        }
        values.update(override)
        return controlled.validate_case_pack(**values)

    def test_legal_ext02_pack_is_admitted_by_production_validator(self):
        result = self.call_pack()
        self.assertTrue(result["accepted"])
        self.assertEqual(result["physical_contract_sha256"], self.contract_sha)
        self.assertNotEqual(result["physical_contract_sha256"], self.base_contract_sha)
        self.assertFalse(result["solver_entry_performed"])
        self.assertFalse(result["post_entry_truth_proved"])
        self.assertTrue(result["post_entry_truth_required_after_solver"])

    def test_legacy_twelve_must_use_unchanged_route(self):
        for case_id in controlled.LEGACY_CASE_IDS:
            with self.subTest(case_id=case_id), self.assertRaisesRegex(
                    controlled.ControlledAdmissionError, "LEGACY_CASE_MUST_USE_ORIGINAL_ROUTE"):
                self.call_pack(case_id=case_id)

    def test_legal_k6_geometry_vector_and_five_nm_grid(self):
        self.assertEqual(controlled.validate_geometry([100, 105, 110, 115, 120, 125]),
                         [100, 105, 110, 115, 120, 125])
        for invalid in ([100, 105, 110, 115, 120, 126],
                        [95, 105, 110, 115, 120, 125],
                        [100, 105, 110, 115, 120],
                        [100.0, 105, 110, 115, 120, 125]):
            with self.subTest(invalid=invalid), self.assertRaises(
                    controlled.ControlledAdmissionError):
                controlled.validate_geometry(invalid)

    def test_k6_geometry_requires_exact_source_enrollment(self):
        g = [100, 105, 110, 115, 120, 125]
        base = self.trust / "k6_base.fsp"
        base.write_bytes(b"authorized per-geometry base")
        source_path = self.trust / "k6_geometry_authority.json"
        source = {
            "schema": controlled.GEOMETRY_SOURCE_SCHEMA, "eligible": True,
            "case_id": "K6V1_NEW001", "attempt_id": "attempt_001",
            "ordered_D_nm": g, "geometry_hash_sha256": "1" * 64,
            "expansion_manifest_sha256": self.expansion_sha,
            "base_setup_fsp_path": str(base), "base_setup_fsp_sha256": _sha(base),
        }
        _write_json(source_path, source)
        source_sha = _sha(source_path)
        authority = {
            "expansion_manifest_sha256": self.expansion_sha,
            "k6_geometry_authorities": [{
                "case_id": "K6V1_NEW001", "attempt_id": "attempt_001",
                "path": str(source_path), "sha256": source_sha,
            }],
        }
        provenance = {
            "schema": controlled.GEOMETRY_SOURCE_SCHEMA,
            "authority_path": str(source_path), "authority_sha256": source_sha,
            "ordered_D_nm": g, "geometry_hash_sha256": source["geometry_hash_sha256"],
            "expansion_manifest_sha256": self.expansion_sha,
        }
        selected = controlled._trusted_k6_geometry(
            provenance, authority, "K6V1_NEW001", "attempt_001", g)
        self.assertEqual(selected["ordered_D_nm"], g)
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "K6_GEOMETRY_NOT_AUTHORIZED_BY_SOURCE"):
            controlled._trusted_k6_geometry(
                {**provenance, "ordered_D_nm": [100, 105, 110, 115, 120, 130]},
                authority, "K6V1_NEW001", "attempt_001", [100, 105, 110, 115, 120, 130])

    def test_ext02_monitor_delta_must_be_one_exact_append(self):
        controlled._compare_ext02_contract(self.base_contract, self.contract, self.policy)
        for change in ("replace", "move", "delete", "extra"):
            candidate = copy.deepcopy(self.contract)
            if change == "replace":
                candidate["monitors"]["output"] = "EXT02_POSTNP_DIAG_Z2000"
            elif change == "move":
                candidate["monitors"]["diagnostic"]["nominal_sample_z_nm"] = 1995.0
            elif change == "delete":
                del candidate["monitors"]["diagnostic"]
            else:
                candidate["monitors"]["unlisted"] = {"name": "UNLISTED"}
            with self.subTest(change=change), self.assertRaisesRegex(
                    controlled.ControlledAdmissionError,
                    "EXT02_UNDECLARED_PHYSICAL_CONTRACT_DELTA"):
                controlled._compare_ext02_contract(self.base_contract, candidate, self.policy)

    def test_ext02_contract_rejects_source_material_mesh_boundary_pml_and_stop_deltas(self):
        for key, changed in (
                ("materials", {"substrate": "different"}),
                ("stack_layers", [["different", 999.0]]),
                ("wavelengths_nm", [440, 445, 450]),
                ("samples_nm", {"MON_POSTNP": 1995.0}),
                ("references_nm", {"MON_POSTNP": 1722.0, "MON_IN": 0.0}),
                ("source", {"profile": "different"}),
                ("mesh", {"authority": "10nm", "step_nm": 10.0}),
                ("boundaries", {"x": "Absorbing", "y": "Periodic", "z": "PML"}),
                ("pml", {"axis": "z", "layers": 4}),
                ("stopping_rule", {"simulation_time_s": 9e-12, "auto_shutoff_min": 1e-9})):
            candidate = copy.deepcopy(self.contract)
            candidate[key] = changed
            with self.subTest(field=key), self.assertRaisesRegex(
                    controlled.ControlledAdmissionError,
                    "EXT02_UNDECLARED_PHYSICAL_CONTRACT_DELTA"):
                controlled._compare_ext02_contract(self.base_contract, candidate, self.policy)

    def _real_readback_fixture(self, delta=None, added_monitor_z=2000.0,
                               alter_existing=False, extra_object=False,
                               remove_existing=False):
        geometry = [220, 120, 155, 100, 105, 110]
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        base = root / "base.fsp"
        source = root / "source.fsp"
        staged = root / "staged.fsp"
        for path in (base, source, staged):
            path.write_bytes(b"same fake setup bytes")
        digest = _sha(staged)
        policy = _policy()
        monitor_policy = controlled._expected_monitor(policy)
        base_semantics = {"geometry": geometry, "materials": "Native-M1",
                          "source": "PW-X", "mesh": "5nm", "pml": "z-PML-8"}
        candidate_semantics = copy.deepcopy(base_semantics)
        if delta:
            candidate_semantics.update(delta)
        base_names = ["MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION"]
        candidate_names = list(base_names)
        if not remove_existing:
            candidate_names.append(monitor_policy["name"])
        else:
            candidate_names.remove("MON_POSTNP")
        if extra_object:
            candidate_names.append("UNDECLARED_MONITOR")
        rows = {}
        for path in (base, source, staged):
            row = {
                "ordered_D_nm": geometry,
                "geometry_hash_sha256": "b" * 64,
                "object_names": list(base_names if path == base else candidate_names),
                "object_types": {name: "DFTMonitor" for name in (base_names if path == base else candidate_names)},
                "semantic_state": copy.deepcopy(base_semantics if path == base else candidate_semantics),
                "fdtd": {}, "stack": {}, "sources": {}, "monitors": {}, "meshes": {}, "materials": {},
            }
            rows[str(path.resolve())] = row
        if not remove_existing:
            rows[str(source.resolve())]["object_types"][monitor_policy["name"]] = "DFTMonitor"
            rows[str(staged.resolve())]["object_types"][monitor_policy["name"]] = "DFTMonitor"
        if extra_object:
            rows[str(source.resolve())]["object_types"]["UNDECLARED_MONITOR"] = "DFTMonitor"
            rows[str(staged.resolve())]["object_types"]["UNDECLARED_MONITOR"] = "DFTMonitor"
        proof_path = root / "proof.json"
        diagnostic = {
            "name": monitor_policy["name"], "type": "DFTMonitor", "monitor_type": "2D Z-normal",
            "z_nm": added_monitor_z, "x_span_nm": 1740.0, "y_span_nm": 290.0,
            "frequency_points": 21, "components": ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"],
            "spatial_interpolation": "nearest mesh cell", "down_sample": {"x": 1, "y": 1, "z": 1},
            "actual_sampled_z_nm": None, "actual_sampled_z_status": "UNAVAILABLE_BEFORE_SOLVER",
        }
        _write_json(proof_path, {"setup_readback": {
            "added_monitor": diagnostic,
            "staged_fsp_readback": rows[str(staged.resolve())],
        }})
        context = {
            "route_version": controlled.ROUTE_VERSION,
            "case_class": "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1",
            "case_id": "K6V1_EXT02", "attempt_id": "attempt_001",
            "physical_contract_sha256": "1" * 64,
            "physical_contract_semantic_sha256": "2" * 64,
            "setup_contract_fingerprint_sha256": "3" * 64,
            "route_policy_sha256": "4" * 64, "route_authority_sha256": "5" * 64,
            "source_manifest_sha256": "6" * 64,
            "source_fsp_path": str(source), "staged_fsp_path": str(staged),
            "source_fsp_sha256": digest, "staged_fsp_sha256": digest,
            "base_setup_fsp_path": str(base), "base_setup_fsp_sha256": digest,
            "five_nm_case_spec_path": str(root / "spec.json"),
            "pre_entry_setup_load_proof_path": str(proof_path),
            "pre_entry_setup_load_proof_sha256": _sha(proof_path),
            "policy": policy,
            "authority": {"ext02": {"geometry_hash_sha256": "b" * 64}},
        }
        _write_json(root / "spec.json", {"synthetic": True})
        class FakeValidator:
            @staticmethod
            def inspect_fsp(path, _spec):
                return copy.deepcopy(rows[str(Path(path).resolve())])
            @staticmethod
            def validate_expected(_row, _spec):
                return {"status": "PASS", "errors": []}
            @staticmethod
            def compare_semantics(left, right):
                ok = left["semantic_state"] == right["semantic_state"]
                return {"status": "PASS" if ok else "FAIL", "mismatches": [] if ok else ["synthetic delta"]}
        def read_monitor(path, expected):
            name = expected["name"]
            if name == monitor_policy["name"]:
                return dict(diagnostic)
            row = {"name": name, "value": 1}
            if alter_existing and name == "MON_POSTNP" and Path(path).resolve() == source.resolve():
                row["value"] = 2
            return row
        manifest = {"case_id": "K6V1_EXT02", "attempt_id": "attempt_001",
                    "geometry": geometry, "pre_fsp_path": str(staged)}
        try:
            result = controlled.validate_real_readback(
                context, case_authority=context, source_fsp=source, staged_fsp=staged,
                manifest=manifest, setup_validator=FakeValidator,
                monitor_readback=read_monitor)
        except Exception:
            temp.cleanup()
            raise
        return temp, result

    def test_real_readback_synthetic_rejects_geometry_material_source_mesh_and_pml_changes(self):
        for key, changed in (("geometry", [220, 120, 155, 100, 105, 115]),
                             ("materials", "wrong material"), ("source", "wrong source"),
                             ("mesh", "10nm"), ("pml", "different pml")):
            with self.subTest(field=key), self.assertRaisesRegex(
                    controlled.ControlledAdmissionError, "UNDECLARED_BASE_SETUP_DELTA"):
                self._real_readback_fixture({key: changed})

    def test_real_readback_synthetic_accepts_only_declared_monitor_append(self):
        temp, result = self._real_readback_fixture()
        try:
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["setup_readback"]["base_object_delta"], {
                "added": ["EXT02_POSTNP_DIAG_Z2000"], "removed": []})
            self.assertFalse(result["solver_run_called"])
            self.assertEqual(result["solver_invocations"], 0)
        finally:
            temp.cleanup()

    def test_real_readback_synthetic_rejects_monitor_move_replace_extra_and_existing_change(self):
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "EXT02_DIAGNOSTIC_MONITOR_SETTINGS_MISMATCH"):
            self._real_readback_fixture(added_monitor_z=1995.0)
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "EXT02_SETUP_OBJECT_DELTA_INVALID"):
            self._real_readback_fixture(extra_object=True)
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "EXT02_SETUP_OBJECT_DELTA_INVALID"):
            self._real_readback_fixture(remove_existing=True)
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "EXISTING_MONITOR_CHANGED:MON_POSTNP"):
            self._real_readback_fixture(alter_existing=True)

    def test_route_contract_path_and_hash_mismatches_fail_closed(self):
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "RUNNER_PHYSICAL_CONTRACT_BINDING_MISMATCH"):
            self.call_pack(physical_contract_path=str(self.case_dir / "wrong.json"))
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "RUNNER_PHYSICAL_CONTRACT_BINDING_MISMATCH"):
            self.call_pack(physical_contract_sha256="0" * 64)
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "CONTROLLED_ROUTE_VERSION_UNSUPPORTED"):
            self.call_pack(route_version=controlled.ROUTE_VERSION + "_BAD")
        with self.assertRaises(controlled.ControlledAdmissionError):
            self.call_pack(case_id="K6V1_OTHER")

    def test_fsp_byte_hash_mismatch_rejected(self):
        self.staged_fsp.write_bytes(b"tampered staged bytes")
        with self.assertRaises(controlled.ControlledAdmissionError):
            self.call_pack()

    def test_missing_load_only_proof_rejected(self):
        self.proof_path.unlink()
        with self.assertRaises((controlled.ControlledAdmissionError, OSError)):
            self.call_pack()

    def test_mismatched_setup_load_proof_rejected(self):
        proof = json.loads(self.proof_path.read_text(encoding="utf-8"))
        proof["scientific_entry_count"] = 1
        _write_json(self.proof_path, proof)
        self.source_manifest["artifacts"]["pre_entry_setup_load_proof"]["sha256"] = _sha(self.proof_path)
        _write_json(self.source_manifest_path, self.source_manifest)
        with self.assertRaisesRegex(controlled.ControlledAdmissionError,
                                    "PREENTRY_LOAD_PROOF_MISMATCH"):
            self.call_pack()


class ControlledPreflightAdapterTests(unittest.TestCase):
    def test_preflight_command_calls_structural_load_only_and_never_run_one(self):
        with tempfile.TemporaryDirectory() as temp:
            envelope_path = Path(temp) / "envelope.json"
            envelope_path.write_text("{}", encoding="utf-8")
            contract_path = Path(temp) / "contract.json"
            contract_path.write_text("{}", encoding="utf-8")
            core = {"case_id": "K6V1_EXT02", "attempt_id": "attempt_001"}
            context = {
                "route_version": controlled.ROUTE_VERSION,
                "case_class": "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1",
                "case_id": core["case_id"], "attempt_id": core["attempt_id"],
                "source_fsp_path": str(Path(temp) / "source.fsp"),
                "staged_fsp_path": str(Path(temp) / "staged.fsp"),
                "source_manifest_path": str(Path(temp) / "source_manifest.json"),
                "source_manifest_sha256": "a" * 64,
                "physical_contract_sha256": "b" * 64,
                "setup_contract_fingerprint_sha256": "c" * 64,
                "pre_entry_setup_load_proof_path": str(Path(temp) / "proof.json"),
                "pre_entry_setup_load_proof_sha256": "d" * 64,
                "post_entry_truth_proved": False,
                "post_entry_truth_required_after_solver": True,
            }
            class FakeAdapter:
                postprocess_dependency_preflight = {"result": "PASS"}
                def setup_structural_validate(self, manifest, source, staged, authority):
                    self.calls = (manifest, source, staged, authority)
                    return {"result": "PASS", "solver_run_called": False}
            fake = FakeAdapter()
            with patch.object(controlled, "validate_controlled_envelope",
                              return_value=(core, contract_path, context)), \
                 patch.object(adapter, "run_one", side_effect=AssertionError("run_one forbidden")):
                result = adapter.preflight_setup_cli(
                    envelope_path, adapter_factory=lambda *args, **kwargs: fake)
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["solver_invocations"], 0)
            self.assertEqual(result["scientific_entry_count"], 0)
            self.assertFalse(result["post_entry_truth_proved"])
            self.assertTrue(result["post_entry_truth_required_after_solver"])
            self.assertEqual(fake.calls[0], core)


class ControlledStartRevalidationTests(unittest.TestCase):
    def _context(self, preflight_only=False):
        return {
            "route_version": controlled.ROUTE_VERSION,
            "case_class": "EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1",
            "route_policy_sha256": "a" * 64,
            "route_authority_sha256": "b" * 64,
            "source_manifest_path": "D:/case/source_manifest.json",
            "source_manifest_sha256": "c" * 64,
            "physical_contract_path": "D:/case/contract.json",
            "physical_contract_sha256": "d" * 64,
            "physical_contract_semantic_sha256": "e" * 64,
            "setup_contract_fingerprint_sha256": "f" * 64,
            "source_fsp_path": "D:/case/source.fsp",
            "staged_fsp_path": "D:/case/staged.fsp",
            "staged_fsp_sha256": "1" * 64,
            "pre_entry_setup_load_proof_path": "D:/case/proof.json",
            "pre_entry_setup_load_proof_sha256": "2" * 64,
            "preflight_only": preflight_only,
        }

    def _native_adapter(self, snapshot):
        native = adapter.NativeAdapter.__new__(adapter.NativeAdapter)
        native._controlled_monitor_sessions = {}
        native._controlled_monitor_cache = {}
        native.gpu_snapshot = Mock(return_value=snapshot)
        return native

    def _call_setup_validation(self, native, contexts, manifest=None):
        manifest = manifest or {
            "case_id": "K6V1_EXT02", "attempt_id": "attempt_001",
            "run_id": "RUN-EXT02-START-REVALIDATION",
        }
        structural = {"result": "PASS", "solver_run_called": False,
                      "solver_invocations": 0, "scientific_entry_performed": False}
        with patch.object(native, "_revalidate_controlled_setup_context",
                          side_effect=contexts) as revalidate, \
             patch.object(controlled, "validate_real_readback", return_value=structural), \
             patch.object(adapter, "load_pinned_setup_validator", return_value=object()):
            result = native.setup_structural_validate(
                manifest, "D:/case/source.fsp", "D:/case/staged.fsp", contexts[0])
        return result, revalidate

    def test_setup_context_is_revalidated_after_load_and_current_gpu_quota_is_recorded(self):
        before = self._context()
        after = self._context()
        native = self._native_adapter({"free_mib": runner.MIN_GPU_FREE_MIB + 1})
        result, revalidate = self._call_setup_validation(native, [before, after])
        self.assertEqual(revalidate.call_count, 2)
        self.assertTrue(result["start_time_revalidation"]["checked_after_setup_load"])
        self.assertEqual(result["start_time_revalidation"]["result"], "PASS")
        self.assertEqual(result["start_time_revalidation"]["gpu_quota_minimum_free_mib"],
                         runner.MIN_GPU_FREE_MIB)
        self.assertEqual(result["start_time_gpu_snapshot"]["free_mib"], runner.MIN_GPU_FREE_MIB + 1)
        self.assertEqual(result["solver_invocations"], 0)
        native.gpu_snapshot.assert_called_once_with()

    def test_control_generation_change_during_load_rejects_start(self):
        before = self._context()
        after = self._context()
        after["pre_entry_setup_load_proof_sha256"] = "9" * 64
        native = self._native_adapter({"free_mib": runner.MIN_GPU_FREE_MIB + 1})
        with self.assertRaisesRegex(runner.RunnerError,
                                    "CONTROL_GENERATION_CHANGED_DURING_SETUP_LOAD"):
            self._call_setup_validation(native, [before, after])
        native.gpu_snapshot.assert_not_called()

    def test_current_gpu_quota_loss_rejects_start(self):
        before = self._context()
        native = self._native_adapter({"free_mib": runner.MIN_GPU_FREE_MIB - 1})
        with self.assertRaisesRegex(runner.RunnerError,
                                    "CONTROLLED_START_GPU_QUOTA_UNAVAILABLE"):
            self._call_setup_validation(native, [before, self._context()])

    def test_setup_preflight_revalidates_context_without_claiming_gpu_slot(self):
        before = self._context(preflight_only=True)
        native = self._native_adapter({})
        manifest = {"case_id": "K6V1_EXT02", "attempt_id": "attempt_001"}
        result, revalidate = self._call_setup_validation(native, [before, self._context(True)], manifest)
        self.assertEqual(revalidate.call_count, 2)
        self.assertTrue(result["start_time_revalidation"]["preflight_only"])
        self.assertIsNone(result["start_time_gpu_snapshot"])
        native.gpu_snapshot.assert_not_called()

    def test_changed_control_context_aborts_runner_before_solver_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.fsp"
            source.write_bytes(b"synthetic pre-solver setup")
            manifest = {
                "case_id": "K6V1_EXT02", "attempt_id": "attempt_001",
                "run_id": "RUN-EXT02-CONTROL-CHANGE",
                "geometry": [220, 120, 155, 100, 105, 110],
                "physical_contract_sha256": runner.CONTRACT_SHA256,
                "expansion_manifest_sha256": runner.EXPANSION_SHA256,
                "pre_fsp_path": str(source), "pre_fsp_sha256": _sha(source),
            }
            solver = Mock(side_effect=AssertionError("solver must not be called"))
            with self.assertRaisesRegex(runner.RunnerError,
                                        "CONTROL_GENERATION_CHANGED_DURING_SETUP_LOAD"):
                runner.run_one(
                    manifest, Path(temp) / "runner", solver,
                    fresh_load_validate=lambda *_: (_ for _ in ()).throw(AssertionError("truth load must not run")),
                    gpu_snapshot=lambda: {"free_mib": runner.MIN_GPU_FREE_MIB + 1},
                    runner_owner_probe=lambda _root: False,
                    setup_structural_validate=lambda *_: (_ for _ in ()).throw(
                        runner.RunnerError("CONTROL_GENERATION_CHANGED_DURING_SETUP_LOAD")),
                )
            solver.assert_not_called()
            status = json.loads((Path(temp) / "runner" / "runs" / "K6V1_EXT02" /
                                 "attempt_001" / manifest["run_id"] / "status.json").read_text())
            self.assertEqual(status["state"], "FAILED_PREENTRY")
            self.assertIs(status["solver_entered"], False)
            self.assertEqual(status["solver_invocations"], 0)


if __name__ == "__main__":
    unittest.main()
