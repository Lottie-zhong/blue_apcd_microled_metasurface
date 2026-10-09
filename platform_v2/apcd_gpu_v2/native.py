"""Verified native invocation specification; scientific execution deliberately unavailable."""

import importlib.util
import json
from pathlib import Path

from .ledger import Refused


def launch_spec(config, fsp, monitors):
    fsp = Path(fsp)
    if fsp.name != "run.fsp" or not monitors or len(set(monitors)) != len(monitors):
        raise Refused("NATIVE_LAUNCH_INPUT_INVALID")
    script = f'run("FDTD","GPU",{json.dumps(config.gpu_resource)});\n'
    for name in monitors:
        for component in ("f", "Ex", "Ey", "Ez", "Hx", "Hy", "Hz"):
            script += f"getdata({json.dumps(name)},{json.dumps(component)});\n"
    script += "save;\n"
    return {
        "command": [
            config.fdtd_executable,
            "-nw",
            "-hide",
            "-trust-script",
            "-run",
            str(fsp.parent / "run_gpu.lsf"),
            str(fsp),
        ],
        "cwd": str(fsp.parent),
        "script": script,
        "scientific_execution_enabled": False,
    }


class NativeBackend:
    scientific = True

    def run(self, *args, **kwargs):
        raise Refused("FORMAL_SCIENTIFIC_AUTHORIZATION_AND_CUTOVER_REQUIRED")


class LoadOnlyReader:
    """Open an existing FSP read-only at API level; no run/save/layout command is exposed."""

    def __init__(self, lumapi_path, monitors, session_factory=None):
        self.lumapi_path, self.monitors, self.session_factory = (
            lumapi_path,
            monitors,
            session_factory,
        )

    def __call__(self, fsp):
        if self.session_factory is None:
            spec = importlib.util.spec_from_file_location(
                "apcd_v2_lumapi", self.lumapi_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            factory = module.FDTD
        else:
            factory = self.session_factory
        results = {}
        with factory(hide=True) as fd:
            fd.load(str(fsp))
            for monitor in self.monitors:
                results[monitor] = {
                    name: fd.getdata(monitor, name)
                    for name in ("f", "Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
                }
        return results
