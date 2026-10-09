import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path

import h5py
import numpy as np

from .ledger import Refused


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def durable_json(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())


def bundle_inventory(fsp, h5_name, settle_seconds=0.05):
    fsp = Path(fsp)
    if fsp.suffix.lower() != ".fsp" or not fsp.is_file() or fsp.stat().st_size == 0:
        raise Refused("NATIVE_FSP_MISSING")
    folder = fsp.with_suffix("")
    h5 = folder / h5_name
    if not h5.is_file() or h5.stat().st_size == 0:
        raise Refused("NATIVE_H5_MISSING")
    files = [fsp] + sorted(p for p in folder.rglob("*") if p.is_file())
    if fsp.is_symlink() or any(p.is_symlink() for p in folder.rglob("*")):
        raise Refused("BUNDLE_SYMLINK_FORBIDDEN")
    before = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in files}
    time.sleep(settle_seconds)
    with h5py.File(h5, "r") as handle:
        monitors = [
            g
            for g in handle
            if g.startswith("Monitor") and isinstance(handle[g], h5py.Group)
        ]
        if not monitors:
            raise Refused("NATIVE_MONITOR_GROUP_MISSING")
        for group in monitors:
            for name in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz"):
                ds = handle[group].get(name)
                if (
                    not isinstance(ds, h5py.Dataset)
                    or ds.size == 0
                    or not np.issubdtype(ds.dtype, np.number)
                ):
                    raise Refused("NATIVE_EH_MISSING_OR_INVALID")
                # Stream every dataset slab to avoid duplicating full monitor fields in RAM.
                for index in range(ds.shape[0] if ds.ndim else 1):
                    if not np.isfinite(ds[index] if ds.ndim else ds[()]).all():
                        raise Refused("NATIVE_EH_NONFINITE")
    result = {}
    for p in files:
        result[p.relative_to(fsp.parent).as_posix()] = {
            "sha256": sha256(p),
            "bytes": p.stat().st_size,
        }
    after = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in files}
    final_files = [fsp] + sorted(p for p in folder.rglob("*") if p.is_file())
    if before != after or final_files != files:
        raise Refused("BUNDLE_CHANGED_DURING_VALIDATION")
    return result


def archive_pair(fsp, destination, h5_name, copy=shutil.copy2):
    fsp, destination = Path(fsp), Path(destination)
    source = bundle_inventory(fsp, h5_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise Refused("ARCHIVE_ALREADY_EXISTS")
    stage = destination.parent / (destination.name + ".partial." + uuid.uuid4().hex)
    stage.mkdir()
    for relative in source:
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        copy(fsp.parent / relative, target)
        with target.open("r+b") as stream:
            os.fsync(stream.fileno())
    archived = bundle_inventory(stage / fsp.name, h5_name)
    if source != archived or source != bundle_inventory(fsp, h5_name):
        raise Refused("ARCHIVE_SHA_OR_SOURCE_CHANGED")
    durable_json(
        stage / "bundle_receipt.json",
        {"schema": "APCD_V2_NATIVE_PAIR_V1", "files": source, "source_fsp": str(fsp)},
    )
    # Directory publish only after all bytes and receipt are durable; partials remain evidence.
    os.rename(stage, destination)
    return {
        "path": str(destination),
        "files": source,
        "receipt_sha256": sha256(destination / "bundle_receipt.json"),
    }


def load_only(fsp, h5_name, reader):
    before = bundle_inventory(fsp, h5_name)
    try:
        return reader(Path(fsp))
    finally:
        if before != bundle_inventory(fsp, h5_name):
            raise Refused("LOAD_ONLY_MUTATED_NATIVE_TRUTH")
