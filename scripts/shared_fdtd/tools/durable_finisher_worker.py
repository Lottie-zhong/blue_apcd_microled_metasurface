from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.engine.finisher import DurablePostSolverFinisher
from shared_fdtd.engine.process_identity import snapshot
from shared_fdtd.engine.persistence import atomic_json


class LumericalCanaryAdapter:
    def fresh_load_validate(self, native, state):
        import lumapi
        fd = lumapi.FDTD(str(native), hide=True)
        try:
            result = fd.getresult("canary_monitor", "T")
            points = int(len(result.get("T", []))) if isinstance(result, dict) else 0
            return {"passed": True, "mode": "LOAD_ONLY", "monitor": "canary_monitor", "points": points}
        finally:
            fd.close()

    def postprocess(self, root, native, post, raw, state):
        import shutil
        shutil.copyfile(native, post)
        raw.write_text(json.dumps({"status": "CANARY_TRUTH", "load_only": True}) + "\n", encoding="utf-8")
        return {"passed": True, "post": str(post), "raw": str(raw)}

    def validate_truth(self, root, state):
        return {"passed": (root / "post.fsp").is_file() and (root / "raw.json").is_file()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    db = ControlDB(cfg["db"])
    root = Path(cfg["attempt_root"])
    finisher = DurablePostSolverFinisher(
        db=db,
        attempt_root=root,
        invoking_branch=cfg["branch"],
        adapter=LumericalCanaryAdapter(),
        process_probe=lambda state: snapshot(state["logical_case_id"]),
        stability_observations=2,
    )
    started = time.monotonic()
    last = None
    while time.monotonic() - started < args.timeout:
        try:
            last = finisher.run_once()
        except Exception as exc:
            last = {"status": "FINISHER_RETRY", "error": repr(exc), "replay": 0}
        atomic_json(root / "finisher_last.json", last)
        if (root / "terminal.json").is_file():
            terminal = json.loads((root / "terminal.json").read_text(encoding="utf-8"))
            if terminal.get("status") == "HF_TRUTH_VALID" and terminal.get("release_state") == "RELEASED":
                return 0
        time.sleep(1.0)
    atomic_json(root / "finisher_timeout.json", {"last": last, "timestamp_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
    return 3


if __name__ == "__main__":
    raise SystemExit(main())

