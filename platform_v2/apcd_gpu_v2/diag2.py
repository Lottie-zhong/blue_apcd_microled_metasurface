from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .artifacts import sha256
from .config import CONTRACT_SHA, StrictModel, digest
from .ledger import Refused

DATASET_ID = "APCD_COUPLING_V3_TIME_DIAG2_V1"
BATCH_ID = "K6V3_TIME_DIAG2_V1_BATCH_001"
DIAG2_CASES = ("K6V3_TIME_DIAG2_A1_5NM_6PS", "K6V3_TIME_DIAG2_A2_5NM_6PS")
DIAG2_ROLE = "TIME_CONVERGENCE_DIAGNOSTIC_ONLY"
CASE_SPEC = {
    DIAG2_CASES[0]: {
        "source_case_id": "K6V3_NUM_REPEAT_A1",
        "parent_anchor_case_id": "K6GDP2_DEV_G001",
        "ordered_D_nm": (120, 160, 165, 175, 160, 195),
        "geometry_sha256": "af948f30747ec9bfb5fc0bf2235a10cdb885b069f081fab306726784a787a2b3",
        "source_run_fsp_sha256": "c8969b8234974376763787dd4f1ba5e898581e5853c85d96daed9270bd84568a",
        "source_setup_fsp_sha256": "0e6e522141ddbd0f9a4323cdc470293fd485af9493257a4ccd166383f6a62bb2",
        "pre_fsp_sha256": "7d9f237ca3a57a2240c8a3cd3d753f8fe85f201ca132557b54336622252a3a6c",
    },
    DIAG2_CASES[1]: {
        "source_case_id": "K6V3_NUM_REPEAT_A2",
        "parent_anchor_case_id": "K6GDP2_DEV_G004",
        "ordered_D_nm": (210, 115, 175, 115, 180, 125),
        "geometry_sha256": "cb67af29fad4b5596ec7412b3ddd7ebcea0a5cb585c7919cb04f02e880f0a61b",
        "source_run_fsp_sha256": "9de36dd97397e7215767bfa1df47d380fbaf0525aedfecf05d7b1654e542f8ac",
        "source_setup_fsp_sha256": "540ec80315bcec60619afb85f60dc894d46e40bffd87d5f8c6fb38b48a2651d1",
        "pre_fsp_sha256": "15042dc7d58eeab35ce00a900d1bb979de58c19c182b18723924c184a48c9739",
    },
}


def is_diag2_config(config):
    return getattr(config, "schema_version", None) == "APCD_V2_DIAG2_SERIAL_V1"


class Pin(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    def read(self):
        if sha256(self.path) != self.sha256:
            raise Refused("DIAG2_PIN_CHANGED:" + self.path)
        try:
            return json.loads(Path(self.path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise Refused("DIAG2_PIN_READ_FAILED:" + self.path) from exc


class Diag2Config(StrictModel):
    schema_version: Literal["APCD_V2_DIAG2_SERIAL_V1"]
    mode: Literal["PRODUCTION_GPU", "PRODUCTION_EQUIVALENT"]
    dataset_id: Literal[DATASET_ID]
    batch_id: Literal[BATCH_ID]
    runtime_root: str
    data_root: str
    coupling_root: str
    coupling_ledger: str
    candidate_fsp_root: str
    registry: Pin
    scientific_admission: Pin
    release: Pin
    fdtd_executable: str
    executable_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    gpu_resource: Literal["GPU license audit"]
    lumerical_version: Literal["2025 R1"] = "2025 R1"
    gpu_device: Literal["NVIDIA GeForce RTX 3080"] = "NVIDIA GeForce RTX 3080"
    native_h5_name: Literal["run_output.h5"]
    physical_contract_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    slots: Literal[1] = 1
    max_new_entries: Literal[2] = 2
    per_case_entry_limit: Literal[1] = 1
    automatic_replays: Literal[0] = 0
    heartbeat_seconds: float = Field(gt=0, le=30)
    truth_toolchain: dict[str, Pin]
    importer_module: str = Field(min_length=3)
    importer_entrypoint: Literal["load_diag2_runner_case"] = "load_diag2_runner_case"
    label_validator_entrypoint: Literal["validate_diag2_labels"] = "validate_diag2_labels"

    @model_validator(mode="after")
    def paths_and_scope(self):
        paths = [
            self.runtime_root, self.data_root, self.coupling_root,
            self.coupling_ledger, self.candidate_fsp_root, self.fdtd_executable,
            self.registry.path, self.scientific_admission.path, self.release.path,
        ]
        if any(not Path(x).is_absolute() for x in paths):
            raise ValueError("DIAG2 absolute paths required")
        runtime = Path(self.runtime_root).resolve()
        coupling = Path(self.coupling_root).resolve()
        if self.mode == "PRODUCTION_GPU":
            canonical = Path("D:/apcd_runtime/gpu_platform_v2_serial_production_v1").resolve()
            if runtime != canonical or runtime not in Path(self.data_root).resolve().parents:
                raise ValueError("DIAG2 canonical V2 runtime/data root required")
            if coupling != Path("D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1").resolve():
                raise ValueError("DIAG2 Coupling authority root mismatch")
            if coupling not in Path(self.coupling_ledger).resolve().parents:
                raise ValueError("DIAG2 independent Coupling ledger must stay in Coupling scope")
            candidate_root = Path(self.candidate_fsp_root).resolve()
            if candidate_root != Path("D:/apcd_runtime/coupling_v3_time_diag2_v1/candidate_setups").resolve():
                raise ValueError("DIAG2 candidate FSP root mismatch")
            if not {"lumapi", "postprocessor", "decoder", "importer", "incident_power_helper"} <= set(self.truth_toolchain):
                raise ValueError("DIAG2 pinned native truth/importer dependencies required")
            forbidden = {
                Path(self.coupling_root) / "reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json",
                Path(self.coupling_root) / "reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json",
            }
            if Path(self.coupling_ledger).resolve() in {p.resolve() for p in forbidden}:
                raise ValueError("DIAG2 may not reuse DOE56 or prior Coupling ledger")
        else:
            if "zero_solver" not in str(runtime).casefold():
                raise ValueError("explicit zero_solver root required")
            for path in [self.data_root, self.coupling_ledger, self.candidate_fsp_root,
                         self.registry.path, self.scientific_admission.path, self.release.path]:
                if runtime not in Path(path).resolve().parents:
                    raise ValueError("zero_solver fixture escaped its root")
        return self

    @property
    def sha256(self):
        return digest(self.model_dump())

    @property
    def binding_sha256(self):
        return digest(self.model_dump(exclude={"release"}))


class Diag2Request(StrictModel):
    schema_version: Literal["APCD_V2_DIAG2_REQUEST_V1"]
    dataset_id: Literal[DATASET_ID]
    batch_id: Literal[BATCH_ID]
    case_id: Literal[DIAG2_CASES[0], DIAG2_CASES[1]]
    attempt_id: Literal["attempt_001"]
    role: Literal[DIAG2_ROLE]
    source_case_id: Literal["K6V3_NUM_REPEAT_A1", "K6V3_NUM_REPEAT_A2"]
    parent_anchor_case_id: Literal["K6GDP2_DEV_G001", "K6GDP2_DEV_G004"]
    ordered_D_nm: tuple[int, int, int, int, int, int]
    geometry_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_run_fsp_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_setup_fsp_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pre_fsp: str
    pre_fsp_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_manifest: Pin
    physical_contract: Pin
    physical_contract_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    simulation_time_s: Literal[6e-12]
    auto_shutoff_min: Literal[1e-6]
    config_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def exact_case_binding(self):
        spec = CASE_SPEC[self.case_id]
        for key in ["source_case_id", "parent_anchor_case_id", "ordered_D_nm",
                    "geometry_sha256", "source_run_fsp_sha256",
                    "source_setup_fsp_sha256", "pre_fsp_sha256"]:
            expected = spec[key]
            actual = tuple(getattr(self, key)) if key == "ordered_D_nm" else getattr(self, key)
            if actual != expected:
                raise ValueError("DIAG2 frozen case binding mismatch: " + key)
        if not Path(self.pre_fsp).is_absolute():
            raise ValueError("DIAG2 pre-FSP absolute path required")
        if self.simulation_time_s != 6e-12 or self.auto_shutoff_min != 1e-6:
            raise ValueError("DIAG2 frozen temporal contract required")
        return self

    @property
    def request_sha256(self):
        return digest(self.model_dump())

    @property
    def admission_sha256(self):
        return digest(self.model_dump(exclude={"config_sha256"}))


def case_storage(config, request):
    return Path(config.data_root) / request.dataset_id / request.batch_id / request.case_id / request.attempt_id


def _registry_case(config, request):
    registry = config.registry.read()
    if registry.get("dataset_id") != DATASET_ID or registry.get("batch_id") != BATCH_ID:
        raise Refused("DIAG2_REGISTRY_IDENTITY_MISMATCH")
    if registry.get("status") not in {"SCIENTIFIC_ADMISSION_PASS", "FORMALLY_REGISTERED"}:
        raise Refused("DIAG2_REGISTRY_NOT_FORMALLY_REGISTERED")
    if registry.get("formal_gpu_registration") not in {True, "PASS", "SCIENTIFIC_ADMISSION_PASS"}:
        raise Refused("DIAG2_GPU_REGISTRATION_NOT_GRANTED")
    cases = registry.get("cases")
    if not isinstance(cases, list) or len(cases) != 2:
        raise Refused("DIAG2_REGISTRY_MUST_CONTAIN_EXACTLY_TWO_CASES")
    exact = [row for row in cases if row.get("case_id") == request.case_id]
    if len(exact) != 1:
        raise Refused("DIAG2_CASE_NOT_UNIQUELY_REGISTERED")
    row = exact[0]
    spec = CASE_SPEC[request.case_id]
    checks = {
        "attempt_id": request.attempt_id,
        "role": DIAG2_ROLE,
        "dataset_id": DATASET_ID,
        "source_manifest_case_id": request.source_case_id,
        "parent_anchor_case_id": request.parent_anchor_case_id,
        "mesh_nm": 5,
        "simulation_time_s": 6e-12,
        "auto_shutoff_min": 1e-6,
        "maximum_entry_count": 1,
        "training_allowed": False,
        "confirmation": False,
        "sealed": False,
        "geometry_sha256": request.geometry_sha256,
        "candidate_pre_fsp_sha256": request.pre_fsp_sha256,
    }
    for key, expected in checks.items():
        if row.get(key) != expected:
            raise Refused("DIAG2_REGISTRY_FIELD_MISMATCH:" + key)
    if row.get("entry_count") != 0 or row.get("replay_count") != 0:
        raise Refused("DIAG2_CASE_ALREADY_CONSUMED_NO_REPLAY")
    if Path(row.get("candidate_pre_fsp_path", "")).resolve() != Path(request.pre_fsp).resolve():
        raise Refused("DIAG2_CANDIDATE_FSP_PATH_MISMATCH")
    setup = row.get("setup_input")
    run_truth = row.get("source_run_truth")
    if not isinstance(setup, dict) or setup.get("source_setup_pre_fsp_sha256") != request.source_setup_fsp_sha256:
        raise Refused("DIAG2_SETUP_SOURCE_SHA_MISMATCH")
    if not isinstance(run_truth, dict) or run_truth.get("source_run_fsp_sha256") != request.source_run_fsp_sha256:
        raise Refused("DIAG2_SOURCE_RUN_SHA_MISMATCH")
    if sha256(request.pre_fsp) != request.pre_fsp_sha256:
        raise Refused("DIAG2_CANDIDATE_FSP_SHA_MISMATCH")
    return registry, row


def _validate_official_diag2_contract(config, request, contract):
    # Physical-contract compatibility only; Admission is validated separately.
    if contract.get("schema") != "APCD_COUPLING_PHYSICS_CONTRACT_V2":
        raise Refused("DIAG2_OFFICIAL_CONTRACT_SCHEMA_MISMATCH")
    if contract.get("status") not in {
        "SCIENCE_OWNER_FROZEN_CONTRACT_ADMISSION_NOT_ISSUED",
        "SCIENTIFIC_ADMISSION_PASS",
        "FORMAL_GPU_CONTRACT",
    }:
        raise Refused("DIAG2_PHYSICAL_CONTRACT_NOT_FORMALLY_ACCEPTED")
    if (contract.get("contract_id") != "APCD_PW_PERIODIC_PLANAR_5NM_GPU_PRODUCTION_V3_DIAG2_6PS"
        or contract.get("dataset_id") != DATASET_ID
        or contract.get("scientific_role") != DIAG2_ROLE):
        raise Refused("DIAG2_PARENT_PHYSICS_CONTRACT_MISMATCH")
    if contract.get("parent_contract_file_sha256") != CONTRACT_SHA:
        raise Refused("DIAG2_PARENT_PHYSICS_CONTRACT_MISMATCH")

    expected_diff = {
        "field": "fdtd.simulation_time_s",
        "from_s": 3e-12,
        "to_s": 6e-12,
    }
    if contract.get("only_allowed_physical_difference") != expected_diff:
        raise Refused("DIAG2_PHYSICAL_DIFF_NOT_EXACT")
    temporal = contract.get("temporal_stop")
    setup = contract.get("shared_6ps_actual_setup_readback")
    fdtd = setup.get("fdtd") if isinstance(setup, dict) else None
    if (not isinstance(temporal, dict) or not isinstance(fdtd, dict)
        or temporal.get("fdtd_simulation_maximum_time_s") != 6e-12
        or temporal.get("fdtd_auto_shutoff_min") != 1e-6
        or temporal.get("scheduler_policy_changed") is not False
        or fdtd.get("simulation_time_s") != 6e-12
        or fdtd.get("auto_shutoff_min") != 1e-6):
        raise Refused("DIAG2_FROZEN_TEMPORAL_CONTRACT_MISMATCH")
    meshes = setup.get("meshes", {})
    np_mesh = meshes.get("NP_DERIVED_BASELINE_N2") if isinstance(meshes, dict) else None
    if not isinstance(np_mesh, dict) or np_mesh.get("step_nm") != [5.0, 5.0, 5.0]:
        raise Refused("DIAG2_FROZEN_MESH_CONTRACT_MISMATCH")

    binding = contract.get("case_geometry_binding")
    rows = binding.get("cases") if isinstance(binding, dict) else None
    if not isinstance(rows, list) or [row.get("case_id") for row in rows] != list(DIAG2_CASES):
        raise Refused("DIAG2_FROZEN_CASE_SET_MISMATCH")
    if request.case_id not in CASE_SPEC or request.attempt_id != "attempt_001":
        raise Refused("DIAG2_CASE_NOT_ALLOWLISTED")
    bound = rows[DIAG2_CASES.index(request.case_id)]
    expected = CASE_SPEC[request.case_id]
    if (bound.get("attempt_id") != request.attempt_id
        or bound.get("anchor_case_id") != request.parent_anchor_case_id
        or bound.get("role") != DIAG2_ROLE
        or bound.get("ordered_D_nm") != list(request.ordered_D_nm)
        or bound.get("geometry_sha256") != request.geometry_sha256
        or expected["parent_anchor_case_id"] != request.parent_anchor_case_id
        or expected["ordered_D_nm"] != tuple(request.ordered_D_nm)
        or expected["geometry_sha256"] != request.geometry_sha256):
        raise Refused("DIAG2_FROZEN_CASE_BINDING_MISMATCH")

    label = contract.get("frozen_609d_label_contract")
    if (not isinstance(label, dict)
        or label.get("profile_id") != "coupling_609d_v1"
        or label.get("outputs") != 609
        or label.get("wavelengths_nm") != list(range(440, 461))
        or label.get("floquet_orders_m") != list(range(-3, 4))
        or label.get("polarizations") != ["TE", "TM"]
        or label.get("reference_plane_nm") != 1722.0):
        raise Refused("DIAG2_FROZEN_LABEL_CONTRACT_MISMATCH")
    identity_rule = contract.get("identity_hash_rule")
    if (not isinstance(identity_rule, dict)
        or identity_rule.get("same_as") != "ingest._canon"
        or identity_rule.get("self_hash_fields_excluded") is not True
        or identity_rule.get("serializer") != "json.dumps(sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')"
        or "physical_contract_sha256" in contract
        or "candidate_contract_sha256_canonical_json" in contract):
        raise Refused("DIAG2_CANONICAL_CONTRACT_RULE_MISMATCH")
    # Official bytes and canonical identity remain pinned; no aliases are written back.
    contract_sha = digest(contract)
    pin_sha = getattr(request.physical_contract, "sha256", None)
    if (contract_sha != config.physical_contract_sha256
        or request.physical_contract_sha256 != config.physical_contract_sha256
        or pin_sha != config.physical_contract_sha256):
        raise Refused("DIAG2_CANONICAL_CONTRACT_SHA_MISMATCH")
    return contract


def validate_diag2_contract(config, request):
    contract = request.physical_contract.read()
    if request.physical_contract_sha256 != config.physical_contract_sha256:
        raise Refused("DIAG2_PHYSICAL_CONTRACT_CONFIG_MISMATCH")
    if contract.get("schema") == "APCD_COUPLING_PHYSICS_CONTRACT_V2":
        return _validate_official_diag2_contract(config, request, contract)
    # Backward compatibility for the former GPU-owned contract schema.
    if contract.get("status") not in {"SCIENTIFIC_ADMISSION_PASS", "FORMAL_GPU_CONTRACT"}:
        raise Refused("DIAG2_PHYSICAL_CONTRACT_NOT_FORMALLY_ACCEPTED")
    if contract.get("dataset_id") != DATASET_ID or contract.get("parent_physical_contract_sha256") != CONTRACT_SHA:
        raise Refused("DIAG2_PARENT_PHYSICS_CONTRACT_MISMATCH")
    temporal = contract.get("temporal_settings", {})
    if temporal.get("maximum_simulation_time_s") != 6e-12 or temporal.get("auto_shutoff_min") != 1e-6:
        raise Refused("DIAG2_FROZEN_TEMPORAL_CONTRACT_MISMATCH")
    expected_diff = {"field": "FDTD.simulation time", "from_s": 3e-12, "to_s": 6e-12}
    if contract.get("only_allowed_physical_difference") != expected_diff:
        raise Refused("DIAG2_PHYSICAL_DIFF_NOT_EXACT")
    canonical = contract.get("physical_contract_sha256") or contract.get("candidate_contract_sha256_canonical_json")
    body = dict(contract)
    body.pop("physical_contract_sha256", None)
    body.pop("candidate_contract_sha256_canonical_json", None)
    if canonical != digest(body) or canonical != config.physical_contract_sha256:
        raise Refused("DIAG2_CANONICAL_CONTRACT_SHA_MISMATCH")
    return contract


def validate_diag2_admission(config, request):
    if not is_diag2_config(config):
        raise Refused("DIAG2_CONFIG_REQUIRED")
    if request.dataset_id != config.dataset_id or request.batch_id != config.batch_id:
        raise Refused("DIAG2_BATCH_IDENTITY_MISMATCH")
    if request.config_sha256 != config.sha256:
        raise Refused("DIAG2_CONFIG_REQUEST_MISMATCH")
    try:
        Path(request.pre_fsp).resolve().relative_to(Path(config.candidate_fsp_root).resolve())
    except ValueError as exc:
        raise Refused("DIAG2_CANDIDATE_FSP_OUTSIDE_PINNED_ROOT") from exc
    if config.mode == "PRODUCTION_GPU":
        admission = config.scientific_admission.read()
        if admission.get("status") != "SCIENTIFIC_ADMISSION_PASS":
            raise Refused("DIAG2_SCIENTIFIC_ADMISSION_NOT_GRANTED")
        if admission.get("dataset_id") != DATASET_ID or admission.get("batch_id") != BATCH_ID:
            raise Refused("DIAG2_ADMISSION_IDENTITY_MISMATCH")
        if admission.get("max_new_entries") != 2 or admission.get("automatic_replays") != 0:
            raise Refused("DIAG2_ADMISSION_BUDGET_MISMATCH")
        release = config.release.read()
        if release.get("schema") != "APCD_GPU_V2_DIAG2_RELEASE_V1" or release.get("science_authorized") is not True:
            raise Refused("DIAG2_FINITE_RELEASE_NOT_AUTHORIZED")
        if release.get("status") != "FINITE_AUTHORIZED" or release.get("expires_unix", 0) < time.time():
            raise Refused("DIAG2_FINITE_RELEASE_EXPIRED_OR_INVALID")
        if release.get("dataset_id") != DATASET_ID or release.get("batch_id") != BATCH_ID:
            raise Refused("DIAG2_RELEASE_IDENTITY_MISMATCH")
        if release.get("max_new_entries") != 2 or release.get("per_case_entry_limit") != 1 or release.get("automatic_replays") != 0:
            raise Refused("DIAG2_RELEASE_BUDGET_MISMATCH")
        if release.get("config_binding_sha256") != config.binding_sha256:
            raise Refused("DIAG2_RELEASE_CONFIG_BINDING_MISMATCH")
        if release.get("scientific_admission_sha256") != config.scientific_admission.sha256:
            raise Refused("DIAG2_RELEASE_ADMISSION_SHA_MISMATCH")
        request_sha_list = release.get("request_admission_sha256s")
        if not isinstance(request_sha_list, list) or request.admission_sha256 not in request_sha_list:
            raise Refused("DIAG2_REQUEST_NOT_IN_FINITE_RELEASE")
    registry, row = _registry_case(config, request)
    if config.mode == "PRODUCTION_GPU":
        admission = config.scientific_admission.read()
        if admission.get("registry_sha256") != config.registry.sha256:
            raise Refused("DIAG2_ADMISSION_REGISTRY_SHA_MISMATCH")
        if admission.get("physical_contract_sha256") != request.physical_contract_sha256:
            raise Refused("DIAG2_ADMISSION_CONTRACT_SHA_MISMATCH")
        case_ids = admission.get("case_ids")
        if case_ids != list(DIAG2_CASES):
            raise Refused("DIAG2_ADMISSION_CASE_SET_MISMATCH")
    manifest = request.source_manifest.read()
    expected = {
        "dataset_id": DATASET_ID,
        "batch_id": BATCH_ID,
        "case_id": request.case_id,
        "attempt_id": "attempt_001",
        "role": DIAG2_ROLE,
        "ordered_D1_D6_nm": list(request.ordered_D_nm),
        "geometry_sha256": request.geometry_sha256,
        "candidate_pre_fsp_sha256": request.pre_fsp_sha256,
        "source_run_fsp_sha256": request.source_run_fsp_sha256,
        "source_setup_fsp_sha256": request.source_setup_fsp_sha256,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise Refused("DIAG2_SOURCE_MANIFEST_FIELD_MISMATCH:" + key)
    validate_diag2_contract(config, request)
    if sha256(config.fdtd_executable) != config.executable_sha256:
        raise Refused("DIAG2_EXECUTABLE_PIN_CHANGED")
    for name, pin in config.truth_toolchain.items():
        if sha256(pin.path) != pin.sha256:
            raise Refused("DIAG2_TOOLCHAIN_PIN_CHANGED:" + name)
    return {"registry": registry, "case": row}


def validate_diag2_batch(config, requests):
    if len(requests) != 2 or [request.case_id for request in requests] != list(DIAG2_CASES):
        raise Refused("DIAG2_EXACT_TWO_CASE_BATCH_REQUIRED")
    if len({request.request_sha256 for request in requests}) != 2:
        raise Refused("DIAG2_DUPLICATE_REQUEST")
    for request in requests:
        validate_diag2_admission(config, request)
    if config.mode == "PRODUCTION_GPU":
        release = config.release.read()
        expected = [request.admission_sha256 for request in requests]
        if release.get("request_admission_sha256s") != expected:
            raise Refused("DIAG2_RELEASE_MUST_BIND_EXACT_ORDERED_CASE_SET")
    return True
