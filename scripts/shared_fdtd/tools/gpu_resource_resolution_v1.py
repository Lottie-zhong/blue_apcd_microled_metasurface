from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

RESOLVER_VERSION = "SHARED_V3_GPU_RESOURCE_RESOLUTION_V1"


class GPUResourceResolutionError(RuntimeError):
    """Raised when a unique active FDTD GPU resource cannot be frozen."""


def _field(row: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return default


def _active(row: Mapping[str, Any]) -> bool:
    value = _field(row, "active", "enabled", default=False)
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}


def _positive_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def _gpu_specs(specs: Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    if not specs:
        return None, None
    return (
        _field(specs, "userReadableDeviceName", "gpu_model", "model", default=None),
        _field(specs, "deviceUUID", "gpu_uuid", "uuid", default=None),
    )


def resolve_gpu_resource(
    resources: Sequence[Mapping[str, Any]],
    gpu_specs: Mapping[str, Any] | None = None,
    *,
    frozen_resource_name: str | None = None,
    resolved_at_utc: str | None = None,
) -> dict[str, Any]:
    """Resolve one active, usable FDTD GPU resource without first-row selection."""
    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(resources, start=1):
        solver = str(_field(row, "solver", default="FDTD")).strip().lower()
        device_type = str(_field(row, "device_type", "device type", default="")).strip().upper()
        name = str(_field(row, "resource_name", "name", default="")).strip()
        processes = _positive_int(_field(row, "processes", "process_count", default=None))
        if solver not in {"fdtd", "fdtd solver"} or not _active(row):
            continue
        if device_type != "GPU" or not name or processes is None:
            continue
        candidates.append({
            "index": index,
            "resource_name": name,
            "solver": "FDTD",
            "hostname": str(_field(row, "hostname", "host", default="")),
            "active": True,
            "device_type": "GPU",
            "processes": processes,
            "threads": _positive_int(_field(row, "threads", default=1)) or 1,
        })

    if frozen_resource_name is not None:
        wanted = str(frozen_resource_name).strip()
        matches = [item for item in candidates if item["resource_name"] == wanted]
        if len(matches) != 1:
            raise GPUResourceResolutionError(
                "GPU_RESOURCE_FROZEN_NAME_NOT_UNIQUE:" + (wanted or "<empty>")
            )
        selected = matches[0]
    elif len(candidates) == 0:
        raise GPUResourceResolutionError("GPU_RESOURCE_NONE")
    elif len(candidates) != 1:
        raise GPUResourceResolutionError(f"GPU_RESOURCE_AMBIGUOUS:{len(candidates)}")
    else:
        selected = candidates[0]

    model, uuid = _gpu_specs(gpu_specs)
    return {
        **selected,
        "gpu_model": model,
        "gpu_uuid": uuid,
        "candidate_count": len(candidates),
        "resolver_version": RESOLVER_VERSION,
        "resolved_at_utc": resolved_at_utc or datetime.now(timezone.utc).isoformat(),
    }


def parse_resource_probe(path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse the line-oriented zero-solver getresource/gpuspecs probe output."""
    resources: dict[int, dict[str, Any]] = {}
    specs: dict[str, Any] = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("GPU_NAME="):
            specs["userReadableDeviceName"] = line.split("=", 1)[1]
        elif line.startswith("GPU_UUID="):
            specs["deviceUUID"] = line.split("=", 1)[1]
        elif line.startswith("I="):
            try:
                index = int(line.split("=", 1)[1])
            except ValueError:
                continue
            resources.setdefault(index, {})
        elif "=" in line and resources:
            key, value = line.split("=", 1)
            row = resources[max(resources)]
            names = {"NAME": "name", "HOST": "hostname", "ACTIVE": "active", "DEVICE": "device_type", "PROCESSES": "processes", "THREADS": "threads"}
            row[names.get(key, key)] = value
    for row in resources.values():
        for key in ("active", "processes", "threads"):
            if key in row:
                try:
                    row[key] = int(row[key])
                except ValueError:
                    pass
    return list(resources.values()), specs


def lumerical_probe_script(output_path: str | Path) -> str:
    """Return a zero-solver LSF resource probe; it never calls run/runjobs."""
    target = json.dumps(str(output_path).replace("\\", "/"), ensure_ascii=True)
    lines = [
        f'write({target}, "GPU_RESOURCE_PROBE_V1");',
        'for(i=1; i<=getresource("FDTD"); i=i+1) {',
        f'write({target}, "I="+num2str(i));',
        f'write({target}, "NAME="+getresource("FDTD",i,"name"));',
        f'write({target}, "HOST="+getresource("FDTD",i,"hostname"));',
        f'write({target}, "ACTIVE="+getresource("FDTD",i,"active"));',
        f'write({target}, "DEVICE="+getresource("FDTD",i,"device type"));',
        f'write({target}, "PROCESSES="+getresource("FDTD",i,"processes"));',
        f'write({target}, "THREADS="+getresource("FDTD",i,"threads"));',
        '}',
    ]
    return "\n".join(lines) + "\n"


def render_gpu_run_script(resource_name: str, monitor_names: Sequence[str]) -> str:
    lines = [f'run("FDTD","GPU",{json.dumps(str(resource_name), ensure_ascii=True)});']
    lines.extend(f'getdata({json.dumps(str(name), ensure_ascii=True)},"f");' for name in monitor_names)
    lines.append("save;")
    return "\n".join(lines) + "\n"
