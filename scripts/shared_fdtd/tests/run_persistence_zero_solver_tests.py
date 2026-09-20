from __future__ import annotations

import tempfile
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from shared_fdtd.engine.persistence import (
    PersistencePreflightError,
    ensure_persistence_dirs,
    persistence_failure_status,
    persistence_path_preflight,
    save_and_verify,
)


class FakeSaveHandle:
    def save(self, path):
        Path(path).write_bytes(b"durable-truth")


def main():
    with tempfile.TemporaryDirectory(prefix="v3-persistence-") as temporary:
        root = Path(temporary)

        result = persistence_path_preflight(root / "attempt", root / "runtime")
        assert result["status"] == "PASS"
        assert all(Path(row["path"]).is_dir() for row in result["directories"])

        target = root / "attempt" / "post" / "missing" / "truth.fsp"
        record = save_and_verify(FakeSaveHandle(), target)
        assert target.is_file() and record["size_bytes"] == len(b"durable-truth")

        shutil.rmtree(root / "attempt" / "post")
        recovered = root / "attempt" / "post" / "recovered" / "truth.fsp"
        save_and_verify(FakeSaveHandle(), recovered)
        assert recovered.is_file()

        blocked = root / "blocked"
        blocked.write_bytes(b"not-a-directory")
        try:
            persistence_path_preflight(root / "attempt-2", blocked / "runtime")
        except PersistencePreflightError:
            pass
        else:
            raise AssertionError("non-writable pre-entry path was accepted")

        assert persistence_failure_status(True) == "SOLVER_COMPLETED_TRUTH_PERSISTENCE_FAILED"
        assert persistence_failure_status(False) == "FAILED_PREENTRY"

    print("shared V3 persistence zero-solver tests: PASS")


if __name__ == "__main__":
    main()
