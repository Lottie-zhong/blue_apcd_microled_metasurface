from __future__ import annotations

GPU_LAUNCH_INTENT = "GPU_LAUNCH_INTENT"
GPU_RESOURCE_RESOLVED = "GPU_RESOURCE_RESOLVED"
GPU_CHILD_STARTED = "GPU_CHILD_STARTED"
GPU_ENGINE_ENTRY_CONFIRMED = "GPU_ENGINE_ENTRY_CONFIRMED"
GPU_SOLVER_COMPLETED = "GPU_SOLVER_COMPLETED"
GPU_RESOURCE_RESOLUTION_FAILED = "GPU_RESOURCE_RESOLUTION_FAILED"

_NEXT = {
    GPU_LAUNCH_INTENT: {GPU_RESOURCE_RESOLVED, GPU_RESOURCE_RESOLUTION_FAILED},
    GPU_RESOURCE_RESOLVED: {GPU_CHILD_STARTED},
    GPU_CHILD_STARTED: {GPU_ENGINE_ENTRY_CONFIRMED},
    GPU_ENGINE_ENTRY_CONFIRMED: {GPU_SOLVER_COMPLETED},
    GPU_SOLVER_COMPLETED: set(),
    GPU_RESOURCE_RESOLUTION_FAILED: set(),
}


def validate_transition(previous: str | None, current: str) -> bool:
    if previous is None:
        return current == GPU_LAUNCH_INTENT
    return current in _NEXT.get(previous, set())


def require_transition(previous: str | None, current: str) -> str:
    if not validate_transition(previous, current):
        raise ValueError(f"GPU_LEDGER_INVALID_TRANSITION:{previous}->{current}")
    return current
