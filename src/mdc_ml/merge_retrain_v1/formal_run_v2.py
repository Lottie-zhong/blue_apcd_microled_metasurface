from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

from .contracts import ROOT

FORMAL_OUTPUT_ROOT = Path(os.environ.get("MDC_ML_FORMAL_OUTPUT_ROOT", r"C:\Users\DELL\AppData\Local\mdc_ml_formal_runs_v2"))

def commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()

def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2)+"\n", encoding="utf8"); os.replace(tmp,path)

def allocate(stage: str, *, output_root: Path | None = None, nonce: str | None = None) -> tuple[str, Path]:
    root=(output_root or FORMAL_OUTPUT_ROOT).resolve(); short=commit()[:12]
    run_id=f"{stage}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{short}" + (f"-{nonce}" if nonce else "")
    path=root/run_id
    if path.exists(): raise RuntimeError("FORMAL_RUN_COLLISION:"+str(path))
    path.mkdir(parents=True)
    for name,value in (("run_contract.json", {"run_id":run_id,"execution_code_commit":commit()}),("execution_state.json",{"status":"INITIALIZED","execution_code_commit":commit()}),("input_snapshot.json",{}),("authorization.json",{}),("artifact_manifest.json",{})):
        atomic_json(path/name,value)
    (path/"execution_events.jsonl").write_text("",encoding="utf8"); (path/"failure_registry.jsonl").write_text("",encoding="utf8")
    return run_id,path
