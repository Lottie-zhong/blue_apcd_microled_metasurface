"""No-solver fresh-session verifier for the completed MDC FDTD matrix."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "mdc_fdtd_dipole_tmm_validation_v1" / "fdtd-matrix-20260729T092000Z-602d89c69258"
sys.path.insert(0, str(ROOT / "scripts"))
import lumapi  # type: ignore


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    state_path = OUT / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    rows = []
    failures = []
    for case in state["cases"]:
        post = Path(case["post_fsp"])
        before_sha = sha256(post) if post.exists() else None
        record = {"case_id": case["case_id"], "post_fsp": str(post), "before_sha256": before_sha,
                  "exists": post.exists(), "solver_calls": 0}
        session = None
        try:
            if not post.exists():
                raise FileNotFoundError(post)
            session = lumapi.FDTD(hide=True)
            session.load(str(post))
            objects = session.getnamednumber("FDTD")
            # The frozen builder uses its own source/monitor names.  A post-run
            # FSP may prune inactive objects from named-number lookup, so the
            # authoritative fresh-load checks are the retained monitor datasets.
            source_count = session.getnamednumber("dipole")
            top_flux_count = session.getnamednumber("upward_monitor")
            top_nearfield_count = session.getnamednumber("nearfield_monitor")
            bottom_flux_count = session.getnamednumber("downward_monitor")
            transmission = session.getresult("upward_monitor", "T")
            fields = session.getresult("upward_monitor", "E")
            record.update({
                "fresh_load": "PASS", "fdtd_count": int(objects), "source_count": int(source_count),
                "top_flux_count": int(top_flux_count), "top_nearfield_count": int(top_nearfield_count),
                "bottom_flux_count": int(bottom_flux_count), "T_keys": sorted(str(k) for k in transmission),
                "E_keys": sorted(str(k) for k in fields),
            })
            if not (objects and top_flux_count and transmission.get("T") is not None and fields.get("E") is not None):
                raise RuntimeError("required FDTD/upward-monitor result absent")
        except Exception as exc:  # evidence is retained; a failure stops release.
            record.update({"fresh_load": "FAIL", "error": repr(exc)})
            failures.append(record["case_id"])
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
        record["after_sha256"] = sha256(post) if post.exists() else None
        record["sha_unchanged"] = record["before_sha256"] == record["after_sha256"]
        if not record["sha_unchanged"]:
            record["fresh_load"] = "FAIL"
            failures.append(record["case_id"])
        rows.append(record)
        case["fresh_load_status"] = record["fresh_load"]
        case["fresh_load_readback"] = record
    evidence = {"generated_utc": datetime.now(timezone.utc).isoformat(), "mode": "readback_only",
                "solver_calls": 0, "case_count": len(rows), "passed": len(rows) - len(set(failures)),
                "failed_case_ids": sorted(set(failures)), "cases": rows}
    (OUT / "fresh_load_readback.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    state["fresh_load_readback"] = {"status": "PASS" if not failures else "FAIL", "evidence": "fresh_load_readback.json",
                                    "solver_calls": 0}
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({"status": state["fresh_load_readback"]["status"], "cases": len(rows), "failures": failures}))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
