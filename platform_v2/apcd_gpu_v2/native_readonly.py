"""Native acceptance access; intentionally no solver, save or layout API."""

import importlib.util
import time
from contextlib import contextmanager
from pathlib import Path

import psutil

from .artifacts import sha256
from .ledger import Refused


READ_COMMANDS = frozenset(
    {
        "getdata",
        "getresult",
        "getnamed",
        "getnamednumber",
        "getglobalmonitor",
        "getglobalsource",
        "getfdtdindex",
        "getindex",
        "getmaterial",
        "getresource",
        "getdevice",
        "grating",
        "gratingm",
        "gratingn",
        "gratingu1",
        "gratingu2",
        "sourcepower",
        "transmission",
        "layoutmode",
        "getlicenseestimate",
        "selectall",
        "getid",
    }
)


def pinned_module(path, expected_sha, name):
    path = Path(path)
    if sha256(path) != expected_sha:
        raise Refused("NATIVE_ACCEPTANCE_SOURCE_SHA_MISMATCH")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ReadOnlySession:
    def __init__(self, session, allowed_loads, events, *, allow_license=False):
        self._session = session
        self._loads = {
            str(Path(p).resolve()): digest for p, digest in allowed_loads.items()
        }
        self._events = events
        self._license = allow_license

    def load(self, path):
        target = str(Path(path).resolve())
        if target not in self._loads or sha256(target) != self._loads[target]:
            raise Refused("UNBOUND_NATIVE_LOAD_FORBIDDEN")
        self._events.append(
            {"api": "load", "path": target, "sha256": self._loads[target]}
        )
        return self._session.load(target)

    def runsystemcheck(self, solver, device):
        if (solver, device) != ("FDTD", "GPU"):
            raise Refused("SYSTEMCHECK_SCOPE_MISMATCH")
        self._events.append(
            {"api": "runsystemcheck", "solver": solver, "device": device}
        )
        return self._session.runsystemcheck(solver, device)

    def eval(self, script):
        if not self._license or script != "checkout('FDTD_Solutions_engine');":
            raise Refused("ARBITRARY_LSF_FORBIDDEN")
        self._events.append({"api": "checkout", "feature": "FDTD_Solutions_engine"})
        return self._session.eval(script)

    def __getattr__(self, name):
        if name not in READ_COMMANDS:
            raise Refused("NATIVE_MUTATION_OR_SOLVER_FORBIDDEN:" + name)
        method = getattr(self._session, name)

        def read(*args, **kwargs):
            self._events.append({"api": name, "args": [str(a)[:200] for a in args]})
            return method(*args, **kwargs)

        return read


def children():
    rows = []
    try:
        descendants = psutil.Process().children(recursive=True)
    except psutil.AccessDenied as exc:
        raise Refused("NATIVE_CHILD_OWNERSHIP_UNKNOWN") from exc
    for p in descendants:
        try:
            if "fdtd" in p.name().lower():
                rows.append(
                    {
                        "pid": p.pid,
                        "creation_time": p.create_time(),
                        "parent_pid": p.ppid(),
                        "executable": p.exe(),
                        "command": p.cmdline(),
                    }
                )
        except psutil.AccessDenied:
            rows.append(
                {"pid": p.pid, "classification": "UNKNOWN", "reason": "ACCESS_DENIED"}
            )
        except psutil.NoSuchProcess:
            pass
    return rows


@contextmanager
def native_session(factory, allowed_loads, receipt, *, allow_license=False):
    before = children()
    receipt.update(
        {"started_unix": time.time(), "events": [], "before_children": before}
    )
    raw = None
    try:
        raw = factory(hide=True)
        receipt["opened_children"] = children()
        yield ReadOnlySession(
            raw, allowed_loads, receipt["events"], allow_license=allow_license
        )
    except BaseException as exc:
        receipt["body_error"] = repr(exc)
        raise
    finally:
        try:
            if raw is not None:
                receipt["close_attempted"] = True
                raw.close()
                receipt["close_called"] = True
        except BaseException as exc:
            receipt["close_error"] = repr(exc)
            raise
        finally:
            receipt["finished_unix"] = time.time()
            receipt["after_children"] = children()
            receipt["scientific_solver_invocations"] = 0
