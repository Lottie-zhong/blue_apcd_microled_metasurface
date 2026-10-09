import shutil
from pathlib import Path

import h5py
import numpy as np

from .artifacts import archive_pair, load_only, sha256
from .coupling import validate_labels
from .ledger import Refused
from .processes import identity


class FakeBackend:
    scientific = False

    def __init__(self, fault=None):
        self.fault, self.calls = fault, 0

    def preflight(self):
        if self.fault == "license":
            raise Refused("FIXTURE_LICENSE_ERROR")

    def run(self, fsp, h5_name):
        self.calls += 1
        if self.fault in {"process_exit", "network_disconnect"}:
            raise ConnectionError(self.fault)
        if self.fault == "hard_exit":
            raise SystemExit("FIXTURE_ABRUPT_EXIT")
        if self.fault == "missing_h5":
            return
        fsp = Path(fsp)
        fsp.write_bytes(b"OFFLINE_SOLVED_FIXTURE_NOT_NATIVE_FSP")
        folder = fsp.with_suffix("")
        folder.mkdir()
        with h5py.File(folder / h5_name, "w") as h5:
            h5.attrs["offline_fixture"] = True
            for name in ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz"):
                h5.create_dataset(
                    "Monitor1/" + name, data=np.ones((2, 2, 1, 21), dtype=np.complex128)
                )

    def read(self, fsp):
        if self.fault == "postprocess":
            raise Refused("FIXTURE_POSTPROCESS_ERROR")
        return np.ones((21, 7, 2), dtype=np.complex128), np.full(21, 0.5)


def run_offline(
    config, request, ledger, backend, *, after_entry=None, archive=archive_pair
):
    if (
        config.scientific_enabled
        or config.mode != "offline"
        or not isinstance(backend, FakeBackend)
    ):
        raise Refused("OFFLINE_BACKEND_REQUIRED")
    if request.config_sha256 != config.sha256:
        raise Refused("CONFIG_REQUEST_MISMATCH")
    token = ledger.claim(request.request_sha256, identity())
    entered = False
    try:
        backend.preflight()
        if sha256(request.pre_fsp) != request.pre_fsp_sha256:
            raise Refused("PRE_FSP_SHA_MISMATCH")
        with Path(request.pre_fsp).open("rb") as stream:
            if not stream.read(64).startswith(b"OFFLINE_"):
                raise Refused("OFFLINE_FIXTURE_SOURCE_REQUIRED")
        run_dir = Path(config.runtime_root) / "attempts" / request.request_sha256
        run_dir.mkdir(parents=True, exist_ok=False)
        fsp = run_dir / "run.fsp"
        shutil.copyfile(request.pre_fsp, fsp)
        staged_sha = sha256(fsp)
        if staged_sha != request.pre_fsp_sha256:
            raise Refused("STAGED_FSP_SHA_MISMATCH")
        ledger.enter(
            request.request_sha256, token, staged_sha, request.physical_contract_sha256
        )
        entered = True
        if after_entry:
            after_entry()  # crash injection after durable budget commit, before any backend call
        backend.run(fsp, config.native_h5_name)
        bundle = archive(
            fsp,
            Path(config.runtime_root) / "archives" / request.request_sha256,
            config.native_h5_name,
        )
        archived_fsp = Path(bundle["path"]) / fsp.name
        c_hat, p_scale = load_only(archived_fsp, config.native_h5_name, backend.read)
        labels = validate_labels(
            c_hat,
            p_scale,
            role=request.role,
            physical_contract_sha256=request.physical_contract_sha256,
        )
        ledger.finish(
            request.request_sha256, token, "DONE_OFFLINE", bundle=bundle, labels=labels
        )
        return {
            "state": "DONE_OFFLINE",
            "fake_calls": backend.calls,
            "scientific_calls": 0,
        }
    except Exception as exc:
        ledger.finish(
            request.request_sha256,
            token,
            "FAILED_POSTENTRY" if entered else "FAILED_PREENTRY",
            error=repr(exc),
        )
        raise
