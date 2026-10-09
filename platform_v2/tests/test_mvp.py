import concurrent.futures
import multiprocessing
import os
from pathlib import Path
from unittest.mock import patch

import h5py
import numpy as np
import psutil
import pytest
from pydantic import ValidationError

from apcd_gpu_v2.artifacts import archive_pair, bundle_inventory, load_only, sha256
from apcd_gpu_v2.config import CONTRACT_SHA, Config, Request, load_config
from apcd_gpu_v2.coupling import compare_consumer, validate_labels
from apcd_gpu_v2.ledger import Ledger, Refused
from apcd_gpu_v2.native import LoadOnlyReader, NativeBackend, launch_spec
from apcd_gpu_v2.processes import identity, identity_state
from apcd_gpu_v2.worker import FakeBackend, run_offline


def config(root):
    return Config(
        schema_version="APCD_GPU_PLATFORM_V2_OFFLINE_V1",
        mode="offline",
        scientific_enabled=False,
        runtime_root=str(root.resolve()),
        python_executable=os.sys.executable,
        lumerical_version="2025 R1",
        fdtd_executable=r"N:\Program Files\ANSYS Inc\v251\Lumerical\bin\fdtd-solutions.exe",
        lumapi_path=r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py",
        gpu_resource="GPU license audit",
        native_h5_name="run_output.h5",
        physical_contract_sha256=CONTRACT_SHA,
        slots=1,
        per_attempt_entry_limit=1,
        automatic_replays=0,
    )


def request(tmp_path, cfg, suffix="A"):
    source = tmp_path / (suffix + ".fsp")
    source.write_bytes(b"OFFLINE_UNSOLVED_FIXTURE_NOT_NATIVE_FSP")
    return Request(
        schema_version="APCD_GPU_PLATFORM_V2_OFFLINE_REQUEST_V1",
        case_id="OFFLINE_" + suffix,
        attempt_id="attempt_001",
        role="OFFLINE_FIXTURE",
        pre_fsp=str(source),
        pre_fsp_sha256=sha256(source),
        config_sha256=cfg.sha256,
        physical_contract_sha256=CONTRACT_SHA,
        ordered_d_nm=(105, 105, 220, 105, 180, 135),
    )


@pytest.fixture
def setup(tmp_path):
    cfg = config(tmp_path / "runtime")
    req = request(tmp_path, cfg)
    ledger = Ledger(tmp_path / "ledger.sqlite3")
    ledger.register(req, cfg)
    return cfg, req, ledger


def test_end_to_end_preserves_source_and_single_entry(setup):
    cfg, req, ledger = setup
    backend = FakeBackend()
    result = run_offline(cfg, req, ledger, backend)
    audit = ledger.audit()
    assert result == {"state": "DONE_OFFLINE", "fake_calls": 1, "scientific_calls": 0}
    assert audit["integrity"] == "ok" and audit["tasks"][0]["entered"] == 1
    assert (
        audit["slot"]["token"] is None and audit["tasks"][0]["state"] == "DONE_OFFLINE"
    )
    assert sha256(req.pre_fsp) == req.pre_fsp_sha256
    with pytest.raises(Refused, match="NO_REPLAY"):
        run_offline(cfg, req, ledger, backend)
    assert backend.calls == 1


@pytest.mark.parametrize(
    "fault", ["process_exit", "network_disconnect", "missing_h5", "postprocess"]
)
def test_postentry_fault_never_replays_or_releases(setup, fault):
    cfg, req, ledger = setup
    backend = FakeBackend(fault)
    with pytest.raises(Exception):
        run_offline(cfg, req, ledger, backend)
    a = ledger.audit()
    assert (
        a["tasks"][0]["entered"] == 1 and a["tasks"][0]["state"] == "FAILED_POSTENTRY"
    )
    assert a["slot"]["token"] is not None
    assert (
        ledger.reconcile_dead_owner(a["slot"]["token"], lambda _: "dead")
        == "NEEDS_REVIEW_NO_REPLAY"
    )
    assert ledger.audit()["slot"]["token"] is not None
    with pytest.raises(Refused):
        run_offline(cfg, req, ledger, backend)
    assert backend.calls == 1


def test_license_failure_is_preentry(setup):
    cfg, req, ledger = setup
    backend = FakeBackend("license")
    with pytest.raises(Refused, match="LICENSE"):
        run_offline(cfg, req, ledger, backend)
    assert backend.calls == 0 and ledger.audit()["tasks"][0]["entered"] == 0
    assert ledger.audit()["slot"]["token"] is None


@pytest.mark.parametrize("fault", ["before_backend", "inside_backend"])
def test_uncertain_entry_crash_persists_before_invocation(setup, fault):
    cfg, req, ledger = setup
    backend = FakeBackend("hard_exit" if fault == "inside_backend" else None)

    def die():
        raise SystemExit("crash")

    with pytest.raises(SystemExit):
        run_offline(
            cfg,
            req,
            ledger,
            backend,
            after_entry=die if fault == "before_backend" else None,
        )
    assert ledger.audit()["tasks"][0]["state"] == "ENTRY_UNCERTAIN"
    assert ledger.audit()["tasks"][0]["entered"] == 1
    assert backend.calls == (0 if fault == "before_backend" else 1)
    with pytest.raises(Refused):
        run_offline(cfg, req, ledger, FakeBackend())


def test_committed_budget_visible_from_other_connection(setup):
    cfg, req, ledger = setup
    seen = []

    def inspect():
        seen.append(Ledger(ledger.path).audit()["tasks"][0]["entered"])

    run_offline(cfg, req, ledger, FakeBackend(), after_entry=inspect)
    assert seen == [1]


def test_duplicate_attempt_rejected_even_new_request(setup):
    cfg, req, ledger = setup
    changed = req.model_copy(update={"ordered_d_nm": (110, 105, 220, 105, 180, 135)})
    with pytest.raises(Refused, match="DUPLICATE"):
        ledger.register(changed, cfg)


def test_request_config_mismatch(setup):
    cfg, req, ledger = setup
    changed = cfg.model_copy(update={"gpu_resource": "Other"})
    with pytest.raises(Refused, match="MISMATCH"):
        run_offline(changed, req, ledger, FakeBackend())
    assert ledger.audit()["tasks"][0]["entered"] == 0


def test_ledger_conflicting_config(setup, tmp_path):
    cfg, req, ledger = setup
    changed = cfg.model_copy(update={"gpu_resource": "Other"})
    other = request(tmp_path, changed, "B")
    with pytest.raises(Refused, match="LEDGER_CONFIG_CONFLICT"):
        ledger.register(other, changed)


def claim_in_process(path, req_sha, queue):
    try:
        queue.put(("ok", Ledger(path).claim(req_sha, identity())))
    except Refused as e:
        queue.put(("refused", str(e)))


def test_real_process_race_keeps_one_owner(setup):
    cfg, req, ledger = setup
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    workers = [
        ctx.Process(
            target=claim_in_process, args=(str(ledger.path), req.request_sha256, queue)
        )
        for _ in range(2)
    ]
    for p in workers:
        p.start()
    for p in workers:
        p.join(20)
        assert p.exitcode == 0
    values = [queue.get(timeout=3)[0] for _ in workers]
    assert sorted(values) == ["ok", "refused"]
    assert len([x for x in ledger.audit()["events"] if x["kind"] == "CLAIMED"]) == 1


def test_real_thread_duplicate_case_atomic(setup, tmp_path):
    cfg, req, ledger = setup
    other = request(tmp_path, cfg, "B")

    def register():
        try:
            ledger.register(other, cfg)
            return True
        except Refused:
            return False

    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: register(), range(2)))
    assert sorted(results) == [False, True]


@pytest.mark.parametrize("bad_token", ["", "wrong"])
def test_invalid_fencing_does_not_enter(setup, bad_token):
    cfg, req, ledger = setup
    ledger.claim(req.request_sha256, identity())
    with pytest.raises(Refused, match="FENCING"):
        ledger.enter(req.request_sha256, bad_token, req.pre_fsp_sha256, CONTRACT_SHA)
    assert ledger.audit()["tasks"][0]["entered"] == 0


def test_old_fence_after_new_owner(setup, tmp_path):
    cfg, req, ledger = setup
    token = ledger.claim(req.request_sha256, identity())
    ledger.reconcile_dead_owner(token, lambda _: "dead")
    other = request(tmp_path, cfg, "B")
    ledger.register(other, cfg)
    new_token = ledger.claim(other.request_sha256, identity())
    assert new_token != token and ledger.audit()["slot"]["generation"] == 2
    with pytest.raises(Refused, match="FENCING"):
        ledger.enter(req.request_sha256, token, req.pre_fsp_sha256, CONTRACT_SHA)


@pytest.mark.parametrize("state", ["live", "unknown"])
def test_unknown_or_live_owner_never_stolen(setup, state):
    cfg, req, ledger = setup
    token = ledger.claim(req.request_sha256, identity())
    with pytest.raises(Refused, match="OWNER"):
        ledger.reconcile_dead_owner(token, lambda _: state)
    assert ledger.audit()["slot"]["token"] == token


def test_identity_real_self_and_pid_reuse():
    row = identity()
    assert identity_state(row) == "live"
    assert (
        identity_state({**row, "creation_time": row["creation_time"] - 10}) == "reused"
    )
    assert identity_state({"pid": row["pid"]}) == "unknown"


def test_identity_access_denied_unknown():
    with patch(
        "apcd_gpu_v2.processes.psutil.Process", side_effect=psutil.AccessDenied(1)
    ):
        assert (
            identity_state({"pid": 1, "creation_time": 1.0, "executable": "python"})
            == "unknown"
        )


def test_hash_changed_preentry(setup):
    cfg, req, ledger = setup
    Path(req.pre_fsp).write_bytes(b"changed")
    b = FakeBackend()
    with pytest.raises(Refused, match="SHA"):
        run_offline(cfg, req, ledger, b)
    assert b.calls == 0 and ledger.audit()["tasks"][0]["entered"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("slots", 2),
        ("scientific_enabled", True),
        ("automatic_replays", 1),
        ("lumerical_version", "2026 R1"),
        ("unknown", 0),
    ],
)
def test_strict_config_conflicts(tmp_path, field, value):
    body = config(tmp_path).model_dump()
    body[field] = value
    with pytest.raises(ValidationError):
        Config.model_validate(body)


def test_duplicate_json_and_environment_conflicts(tmp_path):
    p = tmp_path / "cfg.json"
    cfg = config(tmp_path)
    p.write_text(cfg.model_dump_json())
    with pytest.raises(ValueError, match="legacy"):
        load_config(p, {"APCD_GPU_RESOURCE_NAME": "wrong"})
    with pytest.raises(ValueError, match="override"):
        load_config(p, {"APCD_V2_MODE": "native"})
    p.write_text('{"mode":"offline","mode":"offline"}')
    with pytest.raises(ValueError, match="duplicate"):
        load_config(p, {})


@pytest.mark.parametrize("role", ["SEALED_CONFIRMATION_GLOBAL", "DEVELOPMENT_GLOBAL"])
def test_production_or_confirmation_request_forbidden(setup, role):
    cfg, req, ledger = setup
    body = req.model_dump()
    body["role"] = role
    with pytest.raises(ValidationError):
        Request.model_validate(body)


def native_fixture(tmp_path):
    fsp = tmp_path / "run.fsp"
    fsp.write_bytes(b"OFFLINE_NATIVE_PAIR_FIXTURE")
    FakeBackend().run(fsp, "run_output.h5")
    return fsp


def test_archive_keeps_native_names_and_all_files(tmp_path):
    fsp = native_fixture(tmp_path)
    (tmp_path / "run" / "extra.txt").write_text("retain")
    receipt = archive_pair(fsp, tmp_path / "archive", "run_output.h5")
    assert set(receipt["files"]) == {"run.fsp", "run/run_output.h5", "run/extra.txt"}
    assert bundle_inventory(fsp, "run_output.h5") == bundle_inventory(
        tmp_path / "archive/run.fsp", "run_output.h5"
    )
    with pytest.raises(Refused, match="EXISTS"):
        archive_pair(fsp, tmp_path / "archive", "run_output.h5")


def test_save_interruption_preserves_source_and_no_completed_archive(tmp_path):
    fsp = native_fixture(tmp_path)
    source_hash = sha256(fsp)

    def interrupted(src, dst):
        Path(dst).write_bytes(b"partial")
        raise OSError("save interrupted")

    with pytest.raises(OSError):
        archive_pair(fsp, tmp_path / "archive", "run_output.h5", copy=interrupted)
    assert not (tmp_path / "archive").exists() and sha256(fsp) == source_hash
    assert list(tmp_path.glob("archive.partial.*"))


@pytest.mark.parametrize(
    "kind", ["missing_fsp", "missing_h5", "corrupt_h5", "missing_EH", "nonfinite"]
)
def test_bundle_integrity_fail_closed(tmp_path, kind):
    fsp = native_fixture(tmp_path)
    h5 = tmp_path / "run/run_output.h5"
    if kind == "missing_fsp":
        fsp.unlink()
    elif kind == "missing_h5":
        h5.unlink()
    elif kind == "corrupt_h5":
        h5.write_bytes(b"corrupt")
    else:
        with h5py.File(h5, "r+") as handle:
            if kind == "missing_EH":
                del handle["Monitor1/Hx"]
            else:
                handle["Monitor1/Ex"][0, 0, 0, 0] = np.nan
    with pytest.raises((Refused, OSError)):
        bundle_inventory(fsp, "run_output.h5")


def test_load_only_mutation_detected(tmp_path):
    fsp = native_fixture(tmp_path)

    def reader(path):
        path.write_bytes(b"changed")

    with pytest.raises(Refused, match="MUTATED"):
        load_only(fsp, "run_output.h5", reader)


def test_native_load_reader_exposes_only_load_getdata_close(tmp_path):
    calls = []

    class Session:
        def __init__(self, **kw):
            calls.append("open")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            calls.append("close")

        def load(self, path):
            calls.append("load")

        def getdata(self, *args):
            calls.append("getdata")
            return np.ones(21)

    reader = LoadOnlyReader("unused", ["MON_POSTNP"], Session)
    result = reader(tmp_path / "run.fsp")
    assert len(result["MON_POSTNP"]) == 7
    assert calls == ["open", "load"] + ["getdata"] * 7 + ["close"]


def test_native_spec_matches_official_call_but_execution_disabled(tmp_path):
    cfg = config(tmp_path)
    spec = launch_spec(cfg, tmp_path / "run.fsp", ["MON_IN", "MON_POSTNP"])
    assert spec["script"].startswith('run("FDTD","GPU","GPU license audit");')
    assert spec["script"].endswith("save;\n") and "switchtolayout" not in spec["script"]
    assert spec["command"][1:5] == ["-nw", "-hide", "-trust-script", "-run"]
    with pytest.raises(Refused, match="AUTHORIZATION"):
        NativeBackend().run()


def test_backend_cannot_be_native_in_worker(setup):
    cfg, req, ledger = setup
    with pytest.raises(Refused, match="OFFLINE_BACKEND"):
        run_offline(cfg, req, ledger, NativeBackend())
    assert ledger.audit()["tasks"][0]["entered"] == 0


@pytest.mark.parametrize(
    "bad", ["shape", "real", "negative", "nonfinite", "sealed", "contract"]
)
def test_label_contract_refuses_bad_truth(bad):
    c, p = np.ones((21, 7, 2), complex), np.ones(21)
    role, contract = "OFFLINE_FIXTURE", CONTRACT_SHA
    if bad == "shape":
        c = c[:20]
    if bad == "real":
        c = c.real
    if bad == "negative":
        p[0] = -1
    if bad == "nonfinite":
        c[0, 0, 0] = np.nan
    if bad == "sealed":
        role = "SEALED_CONFIRMATION_GLOBAL"
    if bad == "contract":
        contract = "0" * 64
    with pytest.raises(Refused):
        validate_labels(c, p, role=role, physical_contract_sha256=contract)


def test_real_coupling_contract_readonly_roundtrip():
    root = os.environ.get("APCD_TEST_COUPLING_ROOT")
    if not root:
        pytest.skip("live read-only consumer source not supplied")
    p = Path(root) / "scripts/coupling_ml/k6_v2_pipeline/contracts.py"
    before = sha256(p)
    result = compare_consumer(
        p,
        before,
        np.full((21, 7, 2), 1 + 2j),
        np.linspace(0.1, 0.9, 21),
        role="DEVELOPMENT_GLOBAL",
    )
    assert result["outputs"] == 609 and sha256(p) == before


def test_cannot_refund_budget_after_entry(setup):
    cfg, req, ledger = setup
    token = ledger.claim(req.request_sha256, identity())
    ledger.enter(req.request_sha256, token, req.pre_fsp_sha256, CONTRACT_SHA)
    with pytest.raises(Refused, match="REFUND"):
        ledger.finish(req.request_sha256, token, "FAILED_PREENTRY")


def test_done_requires_truth(setup):
    cfg, req, ledger = setup
    token = ledger.claim(req.request_sha256, identity())
    ledger.enter(req.request_sha256, token, req.pre_fsp_sha256, CONTRACT_SHA)
    with pytest.raises(Refused, match="TRUTH_REQUIRED"):
        ledger.finish(req.request_sha256, token, "DONE_OFFLINE")


def abrupt_entry_process(cfg_body, req_body, ledger_path):
    cfg = Config.model_validate(cfg_body)
    req = Request.model_validate(req_body)
    run_offline(
        cfg, req, Ledger(ledger_path), FakeBackend(), after_entry=lambda: os._exit(73)
    )


def test_real_process_abrupt_exit_preserves_committed_budget(setup):
    cfg, req, ledger = setup
    child = multiprocessing.get_context("spawn").Process(
        target=abrupt_entry_process,
        args=(cfg.model_dump(), req.model_dump(), str(ledger.path)),
    )
    child.start()
    child.join(20)
    assert child.exitcode == 73
    audit = Ledger(ledger.path).audit()
    assert audit["integrity"] == "ok"
    assert audit["tasks"][0]["state"] == "ENTRY_UNCERTAIN"
    assert audit["tasks"][0]["entered"] == 1
    assert audit["slot"]["token"] is not None
    with pytest.raises(Refused, match="NO_REPLAY"):
        run_offline(cfg, req, ledger, FakeBackend())


def test_reader_exception_does_not_skip_mutation_detection(tmp_path):
    fsp = native_fixture(tmp_path)

    def reader(path):
        path.write_bytes(b"changed")
        raise RuntimeError("reader crash")

    with pytest.raises(Refused, match="MUTATED"):
        load_only(fsp, "run_output.h5", reader)


@pytest.mark.parametrize(
    "root",
    [
        r"D:\apcd_runtime\gpu_production_runner_v1",
        r"D:\project\blue_apcd_microled_metasurface",
        r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1",
        r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1",
    ],
)
def test_production_paths_cannot_be_offline_runtime(tmp_path, root):
    body = config(tmp_path).model_dump()
    body["runtime_root"] = root
    with pytest.raises(ValidationError, match="production runtime forbidden"):
        Config.model_validate(body)


def test_nonfixture_source_refused_before_entry(setup):
    cfg, req, ledger = setup
    source = Path(req.pre_fsp)
    source.write_bytes(b"NATIVE_FSP_NOT_OFFLINE_FIXTURE")
    altered = req.model_copy(update={"pre_fsp_sha256": sha256(source)})
    fresh = Ledger(ledger.path.parent / "new.sqlite3")
    fresh.register(altered, cfg)
    backend = FakeBackend()
    with pytest.raises(Refused, match="FIXTURE_SOURCE"):
        run_offline(cfg, altered, fresh, backend)
    assert backend.calls == 0 and fresh.audit()["tasks"][0]["entered"] == 0
