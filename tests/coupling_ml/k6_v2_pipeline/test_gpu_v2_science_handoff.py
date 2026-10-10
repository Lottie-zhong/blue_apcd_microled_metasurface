"""Zero-solver tests for the Coupling/GPU V2 handoff.

The live audit is read-only. Simulated controller runs use the pinned V2 test fixture,
a PRODUCTION_EQUIVALENT runtime under pytest's temporary zero_solver directory, and
a marker-guarded fake process. Imported synthetic records never leave that directory.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest

COUPLING_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
V2_RUNTIME = Path(r"D:\apcd_runtime\gpu_platform_v2_serial_production_v1")
V2_RELEASE = V2_RUNTIME / "releases/e662a92a4485a768ffbebe56c2d759c1e416722a"
V2_PACKAGE = V2_RELEASE / "platform_v2"
V2_TEST_MODULE = V2_PACKAGE / "tests/test_serial.py"
CONTRACT_PATH = COUPLING_ROOT / "outputs/coupling_ml/APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1/K6GDP2_DEV_G027/attempt_001/physical_contract.json"
REAL_LEDGER = COUPLING_ROOT / "reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json"


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _load_modules():
    for path in (str(V2_PACKAGE), str(COUPLING_ROOT / "scripts/coupling_ml")):
        if path not in sys.path:
            sys.path.insert(0, path)
    serial = importlib.import_module("apcd_gpu_v2.serial")
    ingest = importlib.import_module("k6_v2_pipeline.ingest")
    coupling = importlib.import_module("apcd_gpu_v2.coupling")
    assert Path(serial.__file__).resolve() == (V2_PACKAGE / "apcd_gpu_v2/serial.py").resolve()
    return serial, ingest, coupling


def _fixture_importer_record(request, pre_fsp_sha, destination, serial, ingest, coupling):
    """Build synthetic raw/state artifacts and run the actual isolated Coupling importer."""
    folder = Path(destination) / ("fixture_import_" + request.case_id)
    folder.mkdir(parents=True, exist_ok=False)
    pc = json.loads(Path(request.physical_contract.path).read_text(encoding="utf-8"))
    wavelengths = np.arange(440.0, 461.0)
    order_rows = [(m, n) for m in range(-4, 5) for n in range(-4, 5)]
    order_index = {pair: i for i, pair in enumerate(order_rows)}
    state_path = folder / "state.npz"
    state_real = np.ones((3, 21, 81, 2, 2), dtype=np.float64)
    state_imag = np.zeros((3, 21, 81, 2, 2), dtype=np.float64)
    masks = np.zeros((3, 21, 81), dtype=bool)
    kz_values = np.zeros((3, 21, 81), dtype=np.float64)
    h2 = importlib.import_module("apcd_gpu_v2.science.pw_complex_floquet_state_v1")
    for m in range(-3, 4):
        q = order_index[(m, 0)]
        for j, wl in enumerate(wavelengths):
            kz = float(h2._mode(m, 0, float(wl), 1.0, 1, "TE")["kz_rad_m"].real)
            masks[:, j, q] = True
            kz_values[:, j, q] = kz
    np.savez_compressed(
        state_path,
        coefficients_real=state_real,
        coefficients_imag=state_imag,
        wavelengths_nm=wavelengths,
        orders=np.asarray(order_rows, dtype=np.int64),
        propagating_mask=masks,
        mode_kz_real=kz_values,
    )
    state_sha = _sha(state_path)
    state_meta_path = folder / "state_metadata.json"
    state_meta_path.write_text(
        json.dumps(
            {
                "sha256": state_sha,
                "schema_version": "PW_COMPLEX_FLOQUET_STATE_V1",
                "planes": ["IN", "PRENP", "POSTNP"],
                "directions": ["+z", "-z"],
                "polarizations": ["TE", "TM"],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    x = np.linspace(0.0, 1740e-9, 3)
    y = np.linspace(0.0, 290e-9, 3)
    f = 299792458.0 / (wavelengths * 1e-9)
    shape = (len(x), len(y), 1, len(wavelengths))
    zeros = np.zeros(shape, dtype=np.complex128)
    ones = np.ones(shape, dtype=np.complex128)
    raw_path = folder / "raw_fields.npz"
    np.savez_compressed(
        raw_path,
        POSTNP_f=f,
        POSTNP_x=x,
        POSTNP_y=y,
        POSTNP_z=np.asarray([1800e-9]),
        POSTNP_Ex=ones,
        POSTNP_Ey=zeros,
        POSTNP_Ez=zeros,
        POSTNP_Hx=zeros,
        POSTNP_Hy=2.0 * ones,
        POSTNP_Hz=zeros,
    )
    raw_sha = _sha(raw_path)
    raw_meta_path = folder / "raw_metadata.json"
    raw_meta_path.write_text(
        json.dumps(
            {
                "case_id": request.case_id,
                "attempt_id": request.attempt_id,
                "contract": {k: pc[k] for k in ("materials", "monitors", "references_nm", "samples_nm", "stack_layers", "wavelengths_nm")},
                "raw_complex_fields": {
                    "path": str(raw_path),
                    "sha256": raw_sha,
                    "schema": "APCD_PW_RAW_COMPLEX_FIELDS_V1",
                },
                "canonical_state": {
                    "axis_order": ["plane", "wavelength", "order", "direction", "polarization"],
                    "directions": ["+z", "-z"],
                    "polarizations": ["TE", "TM"],
                    "normalization": {
                        "incident_power_per_area": [1.0] * 21,
                        "gauge_phase_rad": [0.0] * 21,
                        "gauge": "single_global_phase_per_wavelength_from_IN_REF_+z_(0,0)_TM",
                    },
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    orders_path = folder / "orders.json"
    order_entries = [
        {
            "order_x": m,
            "order_y": n,
            "power_fraction_of_monitor_total": 1.0 / 7.0,
            "power_fraction_of_source": 1.0 / 7.0,
        }
        for m, n in [(m, 0) for m in range(-3, 4)]
    ]
    orders_path.write_text(
        json.dumps(
            {
                "schema": "APCD_PW_PERIODIC_DIFFRACTION_ORDERS_V1",
                "wavelengths_nm": wavelengths.tolist(),
                "post": [order_entries for _ in wavelengths],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    manifest_path = folder / "source_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "case_id": request.case_id,
                "attempt_id": request.attempt_id,
                "geometry": list(request.ordered_D_nm),
                "physical_contract_sha256": request.physical_contract_sha256,
                "pre_fsp_sha256": pre_fsp_sha,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def desc(path):
        return {"path": str(path), "sha256": _sha(path)}

    record = {
        "case_id": request.case_id,
        "attempt_id": request.attempt_id,
        "role": request.role,
        "ordered_D_nm": list(request.ordered_D_nm),
        "physical_contract_sha256": request.physical_contract_sha256,
        "status": "DONE",
        "solver_invocations": 1,
        "replay_count": 0,
        "source_manifest": desc(manifest_path),
        "state_npz": desc(state_path),
        "state_metadata": desc(state_meta_path),
        "raw_npz": desc(raw_path),
        "raw_metadata": desc(raw_meta_path),
        "orders_json": desc(orders_path),
        "fixture_only": True,
    }
    registration = {
        request.case_id: {
            "role": request.role,
            "effective_role": request.role,
            "attempt_id": request.attempt_id,
            "ordered_D_nm": tuple(request.ordered_D_nm),
            "ordered_geometry_sha256": ingest.geometry_sha(request.ordered_D_nm),
            "physical_contract": {
                "path": str(Path(request.physical_contract.path)),
                "sha256": request.physical_contract.sha256,
            },
        }
    }
    registry = SimpleNamespace(development=registration)
    imported = ingest.load_verified_runner_case(
        record,
        expected_role=request.role,
        root=COUPLING_ROOT,
        registry=registry,
    )
    label_verdict = coupling.validate_labels(
        imported.c_hat,
        imported.p_scale,
        role=request.role,
        physical_contract_sha256=request.physical_contract_sha256,
    )
    label_path = folder / "labels.npz"
    np.savez_compressed(
        label_path,
        C_hat_real=imported.c_hat.real,
        C_hat_imag=imported.c_hat.imag,
        P_scale=imported.p_scale,
        eta=imported.eta,
        absolute_order=imported.absolute_order,
    )
    return {
        "verdict": "PASS",
        "outputs": label_verdict["outputs"],
        "fresh_load_verified": True,
        "actual_importer": "load_verified_runner_case",
        "fixture_only": True,
        "fixture_loader": "h5py read-only fixture check; no Lumerical API",
        "labels_artifact": {"path": str(label_path), "sha256": _sha(label_path)},
        "record": record,
    }


def test_live_g027_submission_candidate_is_read_only_and_denied():
    sys.path.insert(0, str(COUPLING_ROOT / "scripts/coupling_ml/k6_v2_pipeline"))
    from gpu_v2_submission import audit_g027_candidate

    report = audit_g027_candidate()
    assert report["status"] == "G027_SCIENCE_ADMISSION_BLOCKED"
    assert report["budget_eligible"] is True
    assert report["case_record_phase"] == "FAILED_PREENTRY_NO_ENTRY"
    assert report["entry_consumed"] is False
    assert report["release_science_authorized"] is False
    assert report["admission_validated"] is False
    assert report["admission_refusal"] == "FORMAL_SCIENCE_RELEASE_MISSING_OR_UNBOUND"
    assert report["counts"] == {
        "authorized": 128,
        "entered": 38,
        "truth_valid": 34,
        "labels_valid": 34,
        "unentered": 90,
        "automatic_replay": 0,
        "confirmation_response_access": 0,
    }
    assert report["ledger_unchanged"] is True
    assert report["dispatch_performed"] is False
    assert report["solver_entry_performed"] is False


@pytest.mark.parametrize("count", [3, 10])
def test_zero_solver_static_batch_controller_with_isolated_real_importer(tmp_path, monkeypatch, count):
    serial, ingest, coupling = _load_modules()
    if not V2_TEST_MODULE.is_file():
        pytest.fail("pinned installed V2 test fixture is missing")
    fixture_api = runpy.run_path(str(V2_TEST_MODULE))
    config, requests, backend = fixture_api["fixture"](tmp_path, count)
    assert "zero_solver" in str(config.runtime_root).lower()
    assert Path(config.coupling_ledger).resolve().is_relative_to(Path(config.runtime_root).resolve())
    assert Path(config.queue.path).resolve().is_relative_to(Path(config.runtime_root).resolve())
    assert Path(config.release.path).resolve().is_relative_to(Path(config.runtime_root).resolve())
    real_ledger_before = _sha(REAL_LEDGER)

    monkeypatch.setattr(serial, "process_gate", lambda pid: [])
    importer_records = {}

    def fixture_validator(fsp, request, destination):
        h5_path = Path(fsp).with_suffix("") / config.native_h5_name
        with h5py.File(h5_path, "r") as h5:
            assert "Monitor1" in h5
            for name in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz"):
                values = np.asarray(h5["Monitor1"][name])
                assert values.shape == (2, 2, 1, 21)
                assert np.iscomplexobj(values) and np.isfinite(values).all()
        evidence = _fixture_importer_record(
            request,
            request.pre_fsp_sha256,
            destination,
            serial,
            ingest,
            coupling,
        )
        importer_records[request.case_id] = evidence["record"]
        return evidence

    result = serial.controller(config, requests, backend, fixture_validator)
    assert len(result["tasks"]) == count
    assert all(task["state"] == "TRUTH_VALID" and task["entered"] == 1 for task in result["tasks"])
    assert result["slot"]["token"] is None

    coupled = json.loads(Path(config.coupling_ledger).read_text(encoding="utf-8"))
    assert coupled["entered_count"] == count
    assert coupled["truth_valid_count"] == count
    assert coupled["labels_valid_count"] == count
    assert coupled["remaining_unentered_count"] == 0

    events = result["events"]
    for index, request in enumerate(requests):
        receipt = serial.CouplingBudget(config).reconcile(request)
        assert receipt["entered_in_ledger"] is True
        assert receipt["replay_allowed"] is False
        assert receipt["receipt"]["request_sha"] == request.request_sha256
        assert receipt["receipt"]["automatic_replay"] == 0
        archive = Path(config.runtime_root) / "archives" / request.request_sha256
        assert (archive / "run.fsp").is_file()
        h5_path = archive / "run" / config.native_h5_name
        assert h5_path.is_file()
        with h5py.File(h5_path, "r") as h5:
            assert all(name in h5["Monitor1"] for name in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz"))
        assert importer_records[request.case_id]["fixture_only"] is True
        validation = coupled["case_records"][request.case_id]["evidence"]["validation"]
        assert validation["actual_importer"] == "load_verified_runner_case"
        assert validation["fixture_loader"].startswith("h5py read-only fixture")
        assert Path(validation["labels_artifact"]["path"]).is_file()
        assert _sha(validation["labels_artifact"]["path"]) == validation["labels_artifact"]["sha256"]

        truth_index = next(i for i, event in enumerate(events) if event["request_sha"] == request.request_sha256 and event["kind"] == "TRUTH_VALID")
        if index + 1 < count:
            next_request = requests[index + 1]
            next_index = next(i for i, event in enumerate(events) if event["request_sha"] == next_request.request_sha256 and event["kind"] == "REGISTERED")
            assert truth_index < next_index

    assert _sha(REAL_LEDGER) == real_ledger_before

    event_count = len(result["events"])
    second = serial.controller(config, requests, backend, fixture_validator)
    assert len(second["events"]) == event_count
    assert all(task["state"] == "TRUTH_VALID" for task in second["tasks"])
    assert all(serial.CouplingBudget(config).reconcile(request)["replay_allowed"] is False for request in requests)
