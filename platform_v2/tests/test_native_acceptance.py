import json
from pathlib import Path

import pytest

from apcd_gpu_v2.artifacts import sha256
from apcd_gpu_v2.ledger import Refused
from apcd_gpu_v2.native_readonly import ReadOnlySession, native_session, pinned_module


class Dummy:
    def __init__(self):
        self.closed = False
        self.calls = []

    def load(self, path):
        self.calls.append(("load", path))

    def getdata(self, *args):
        self.calls.append(("getdata", args))
        return [1 + 2j]

    def runsystemcheck(self, *args):
        self.calls.append(("runsystemcheck", args))
        return {"memory": 123}

    def close(self):
        self.closed = True

    def eval(self, script):
        self.calls.append(("eval", script))


@pytest.mark.parametrize(
    "name", ["run", "runjobs", "runsweep", "save", "switchtolayout", "setnamed", "putv"]
)
def test_native_guard_forbids_science_and_mutation(name):
    raw = Dummy()
    guarded = ReadOnlySession(raw, {}, [])
    with pytest.raises(Refused, match="FORBIDDEN"):
        getattr(guarded, name)()
    assert raw.calls == []


def test_arbitrary_eval_forbidden_even_in_license_scope():
    raw = Dummy()
    guarded = ReadOnlySession(raw, {}, [], allow_license=True)
    with pytest.raises(Refused, match="ARBITRARY"):
        guarded.eval("run;")
    guarded.eval("checkout('FDTD_Solutions_engine');")
    assert raw.calls == [("eval", "checkout('FDTD_Solutions_engine');")]


def test_session_closes_on_load_error(tmp_path):
    fsp = tmp_path / "copy.fsp"
    fsp.write_bytes(b"fixture")
    raw = Dummy()
    receipt = {}
    with pytest.raises(RuntimeError, match="read error"):
        with native_session(lambda **kw: raw, {str(fsp): sha256(fsp)}, receipt) as fd:
            fd.load(fsp)
            raise RuntimeError("read error")
    assert raw.closed and receipt["close_called"]
    assert receipt["scientific_solver_invocations"] == 0


def test_unbound_or_changed_fsp_never_loaded(tmp_path):
    fsp = tmp_path / "copy.fsp"
    fsp.write_bytes(b"fixture")
    raw = Dummy()
    guarded = ReadOnlySession(raw, {str(fsp): sha256(fsp)}, [])
    fsp.write_bytes(b"changed")
    with pytest.raises(Refused, match="UNBOUND"):
        guarded.load(fsp)
    assert raw.calls == []


def test_systemcheck_scope_is_gpu_only():
    raw = Dummy()
    guarded = ReadOnlySession(raw, {}, [])
    with pytest.raises(Refused, match="SCOPE"):
        guarded.runsystemcheck("FDTD", "CPU")
    assert guarded.runsystemcheck("FDTD", "GPU") == {"memory": 123}


def test_pinned_native_source_mismatch_never_imported(tmp_path):
    p = tmp_path / "source.py"
    sentinel = tmp_path / "should_not_exist"
    p.write_text('raise RuntimeError("must not import")')
    with pytest.raises(Refused, match="SHA"):
        pinned_module(p, "0" * 64, "native_mismatch")
    assert not sentinel.exists()


def test_existing_formal_precheck_checkout_failure_closes_and_writes_failure(tmp_path):
    source = Path(
        r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1\scripts\shared_fdtd\gpu_runner_v1\license_preflight_v1.py"
    )
    if not source.exists():
        pytest.skip("remote formal precheck source required")
    mod = pinned_module(source, sha256(source), "native_acceptance_test_formal_license")
    api = tmp_path / "lumapi.py"
    api.write_text("# injected formal API fixture")

    class Module:
        __file__ = str(api)

    class Denied:
        closed = False

        def eval(self, script):
            raise RuntimeError("LICENSE_CHECKOUT_DENIED_INJECTION")

        def close(self):
            self.closed = True

    raw = Denied()
    from unittest.mock import patch

    # This tests the actual formal precheck's failure path; no native API opens.
    with (
        patch.object(mod.importlib, "import_module", return_value=Module()),
        patch.dict(mod.os.environ),
    ):
        with pytest.raises(RuntimeError, match="DENIED"):
            mod.run_lumerical_license_preflight(
                tmp_path,
                api,
                sha256(api),
                tmp_path / "temp",
                session_factory=lambda **kw: raw,
            )
    evidence = json.loads((tmp_path / "license_api_preflight_v1.json").read_text())
    assert raw.closed and evidence["result"] == "FAIL"
    assert evidence["solver_invocations"] == 0 and not evidence["solver_run_called"]


def test_close_failure_retains_complete_evidence_and_fails_closed():
    class FailedClose(Dummy):
        def close(self):
            raise RuntimeError("CLOSE_FAILED")

    receipt = {}
    with pytest.raises(RuntimeError, match="CLOSE_FAILED"):
        with native_session(lambda **kw: FailedClose(), {}, receipt):
            raise ValueError("READ_FAILED")
    assert "READ_FAILED" in receipt["body_error"]
    assert "CLOSE_FAILED" in receipt["close_error"]
    assert receipt["close_attempted"] and not receipt.get("close_called")
    assert "after_children" in receipt and "finished_unix" in receipt


def test_native_open_failure_records_failure_without_false_close():
    def factory(**kw):
        raise RuntimeError("API_OPEN_FAILED")

    receipt = {}
    with pytest.raises(RuntimeError, match="API_OPEN_FAILED"):
        with native_session(factory, {}, receipt):
            pytest.fail("must not enter session")
    assert "API_OPEN_FAILED" in receipt["body_error"]
    assert (
        not receipt.get("close_called")
        and receipt["scientific_solver_invocations"] == 0
    )


def test_child_access_denied_is_unknown_not_cleared(monkeypatch):
    import psutil
    from apcd_gpu_v2 import native_readonly as nr

    class Child:
        pid = 4242

        def name(self):
            raise psutil.AccessDenied(self.pid)

    class Parent:
        def children(self, recursive):
            return [Child()]

    monkeypatch.setattr(nr.psutil, "Process", Parent)
    assert nr.children() == [
        {"pid": 4242, "classification": "UNKNOWN", "reason": "ACCESS_DENIED"}
    ]


def test_child_enumeration_access_denied_fails_closed(monkeypatch):
    import psutil
    from apcd_gpu_v2 import native_readonly as nr

    class Parent:
        def children(self, recursive):
            raise psutil.AccessDenied(4242)

    monkeypatch.setattr(nr.psutil, "Process", Parent)
    with pytest.raises(Refused, match="OWNERSHIP_UNKNOWN"):
        nr.children()
