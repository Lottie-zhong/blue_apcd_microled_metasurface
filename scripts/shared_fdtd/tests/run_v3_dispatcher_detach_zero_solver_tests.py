from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "tools" / "v3_dispatcher_service.py"


def load_module():
    spec = importlib.util.spec_from_file_location("v3_dispatcher_service_under_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def child(marker: pathlib.Path):
    marker.write_text(json.dumps({"pid": os.getpid()}) + "\n", encoding="utf-8")
    time.sleep(8)


def parent(result: pathlib.Path, marker: pathlib.Path):
    module = load_module()
    command = f'"{sys.executable}" "{pathlib.Path(__file__).resolve()}" --child "{marker}"'
    pid = module.launch_process(command)
    result.write_text(json.dumps({"pid": pid}) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--child")
    parser.add_argument("--parent", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if args.child:
        child(pathlib.Path(args.child))
        return
    if not args.parent:
        with tempfile.TemporaryDirectory(prefix="v3_detach_test_") as raw:
            root = pathlib.Path(raw)
            result = root / "result.json"
            marker = root / "child.marker"
            completed = subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).resolve()), "--parent", str(result), str(marker)],
                check=False,
                capture_output=True,
                text=True,
            )
            assert completed.returncode == 0, completed.stderr or completed.stdout
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not marker.exists():
                time.sleep(0.1)
            assert marker.exists(), "breakaway child did not survive parent exit"
            pid = json.loads(result.read_text(encoding="utf-8"))["pid"]
            assert pid > 0
            print("PASS: dispatcher child survived launcher exit without solver entry")
            return
    if len(args.paths) != 2:
        raise AssertionError("invalid parent invocation")
    parent(pathlib.Path(args.paths[0]), pathlib.Path(args.paths[1]))


if __name__ == "__main__":
    main()
