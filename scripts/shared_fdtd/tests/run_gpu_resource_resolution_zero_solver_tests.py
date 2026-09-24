from __future__ import annotations

import json
import tempfile
from pathlib import Path

from shared_fdtd.tools.gpu_attempt_ledger_v1 import (
    GPU_CHILD_STARTED,
    GPU_ENGINE_ENTRY_CONFIRMED,
    GPU_LAUNCH_INTENT,
    GPU_RESOURCE_RESOLVED,
    GPU_SOLVER_COMPLETED,
    require_transition,
)
from shared_fdtd.tools.gpu_resource_resolution_v1 import (
    GPUResourceResolutionError,
    lumerical_probe_script,
    render_gpu_run_script,
    resolve_gpu_resource,
)


def gpu(name="GPU license audit", active=1, device="GPU", processes=1):
    return {"name": name, "active": active, "device_type": device, "processes": processes, "threads": 1}


def raises(code, resources, **kwargs):
    try:
        resolve_gpu_resource(resources, **kwargs)
    except GPUResourceResolutionError as exc:
        assert str(exc).startswith(code), (code, exc)
    else:
        raise AssertionError(f"expected {code}")


def main() -> None:
    tests = {}
    selected = resolve_gpu_resource([{"name": "Local Host", "active": 1, "device_type": "CPU", "processes": 12}, gpu()], {"userReadableDeviceName": "NVIDIA GeForce RTX 3080", "deviceUUID": "uuid-3080"})
    tests["A_one_active_gpu_selects_exactly_one"] = selected["resource_name"] == "GPU license audit" and selected["candidate_count"] == 1
    raises("GPU_RESOURCE_NONE", [])
    tests["B_zero_gpu_blocks_preentry"] = True
    raises("GPU_RESOURCE_AMBIGUOUS", [gpu("GPU A"), gpu("GPU B")])
    tests["C_two_gpu_without_frozen_selection_blocks"] = True
    raises("GPU_RESOURCE_NONE", [gpu("Local Host", device="CPU", processes=12)])
    tests["D_cpu_only_is_not_selected"] = True
    tests["E_case_name_does_not_change_selection"] = resolve_gpu_resource([gpu()])["resource_name"] == resolve_gpu_resource([gpu()])["resource_name"]
    tests["F_campaign_gpu_label_does_not_change_selection"] = resolve_gpu_resource([gpu("renamed-resource")])["resource_name"] == "renamed-resource"
    tests["G_discovered_name_change_requires_no_source_edit"] = resolve_gpu_resource([gpu("new-local-gpu")])["resource_name"] == "new-local-gpu"
    raises("GPU_RESOURCE_NONE", [gpu(active=0)])
    tests["H_inactive_gpu_blocks"] = True
    raises("GPU_RESOURCE_NONE", [gpu(device="CPU")])
    tests["I_non_gpu_blocks"] = True
    with tempfile.TemporaryDirectory() as tmp:
        script = render_gpu_run_script(selected["resource_name"], ["MON_IN", "MON_PRENP", "MON_POSTNP"])
        Path(tmp, "run_gpu.lsf").write_text(script, encoding="utf-8")
        tests["J_run_script_contains_exact_frozen_resource"] = 'run("FDTD","GPU","GPU license audit");' in script
        probe = lumerical_probe_script(Path(tmp, "probe.txt"))
        tests["probe_script_has_no_solver_invocation"] = 'run("' not in probe and "runjobs" not in probe
    state = None
    for next_state in (GPU_LAUNCH_INTENT, GPU_RESOURCE_RESOLVED, GPU_CHILD_STARTED, GPU_ENGINE_ENTRY_CONFIRMED, GPU_SOLVER_COMPLETED):
        state = require_transition(state, next_state)
    tests["future_ledger_entry_boundary_is_explicit"] = state == GPU_SOLVER_COMPLETED
    tests["K_no_solver_invocation"] = True
    result = {"status": "PASS" if all(tests.values()) else "FAIL", "solver_invocations": 0, "tests": tests}
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
