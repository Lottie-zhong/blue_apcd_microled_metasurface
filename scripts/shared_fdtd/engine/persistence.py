from __future__ import annotations
import getpass
import hashlib, json, os, shutil, socket, uuid
from pathlib import Path


class PersistencePreflightError(RuntimeError):
    pass

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def atomic_json(path,value):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+f".{os.getpid()}.tmp")
    t.write_text(json.dumps(value,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8"); os.replace(t,p)


def ensure_parent(path):
    parent = Path(path).parent
    parent.mkdir(parents=True, exist_ok=True)
    return parent


def ensure_persistence_dirs(attempt_root, runtime_root):
    root = Path(attempt_root)
    paths = {
        "runtime_root": Path(runtime_root),
        "native": root / "native",
        "post": root / "post",
        "raw": root / "results",
        "logs": root / "logs",
        "archive_staging": root / "archive_staging",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _probe_directory(path):
    path = Path(path)
    token = uuid.uuid4().hex
    temporary = path / (".persistence_probe_" + token + ".tmp")
    durable = path / (".persistence_probe_" + token)
    payload = (token + "\n").encode("ascii")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, durable)
        if durable.read_bytes() != payload:
            raise PersistencePreflightError("persistence probe readback mismatch: " + str(path))
    finally:
        for candidate in (temporary, durable):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass


def persistence_path_preflight(attempt_root, runtime_root):
    try:
        paths = ensure_persistence_dirs(attempt_root, runtime_root)
    except Exception as exc:
        raise PersistencePreflightError(repr(exc)) from exc
    checked = []
    try:
        for name, path in paths.items():
            _probe_directory(path)
            checked.append({"name": name, "path": str(path), "status": "PASS"})
    except Exception as exc:
        raise PersistencePreflightError(repr(exc)) from exc
    return {
        "status": "PASS",
        "PERSISTENCE_PATH_PREFLIGHT": "PASS",
        "identity": {
            "user": getpass.getuser(),
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
        },
        "directories": checked,
        "probe": "create_write_flush_fsync_rename_read_delete",
    }


def save_and_verify(handle, path):
    path = Path(path)
    ensure_parent(path)
    handle.save(str(path))
    if not path.is_file() or path.stat().st_size <= 0:
        raise IOError("artifact was not durably saved: " + str(path))
    return {"path": str(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def persistence_failure_status(solver_returned):
    return "SOLVER_COMPLETED_TRUTH_PERSISTENCE_FAILED" if solver_returned else "FAILED_PREENTRY"

def persist_and_verify(source,destination):
    source=Path(source); destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,destination); a=sha256_file(source); b=sha256_file(destination)
    if a!=b: raise IOError("archive SHA mismatch")
    return {"path":str(destination),"sha256":b,"size":destination.stat().st_size}
