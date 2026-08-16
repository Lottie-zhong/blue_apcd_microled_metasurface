# APCD Global FDTD Scheduling Policy V3

## Current permanent authority

- Policy ID: `APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3`
- Current permanent global FDTD cap: **3**
- Default branch-local maximum active formal FDTD: **3**
- Each formal FDTD job: **4 MPI processes × 1 thread**
- RCWA does **not** consume an FDTD slot.
- The shared scheduler module and registry are the single authority for admission.

The previous global cap of 2 was a validated conservative production setting and is retained only as historical evidence. It is superseded; historical reports are not rewritten.

## Admission

For branch `B`, `launchable_slots = max(0, min(3-global_active_formal_FDTD, 3-branch_active_formal_FDTD))`. Thus NP3, NP2+LP1, NP1+LP1+MDC1, and MDC3 are legal combinations when every job passes the 4/1 resource gate. A fourth formal FDTD always waits, even when CPU, RAM, or license headroom appears available.

Slot acquisition is an atomic check-and-acquire under the shared registry lock. Registry writes are temporary-file plus atomic replace. Each case retains a separate slot/case identity; release is idempotent and race-safe. RCWA remains visible in machine telemetry but is excluded from FDTD slot accounting.

## Fairness and entered protection

Healthy `entered=true` jobs are never killed, paused, suspended, preempted, migrated, or force-released merely for scheduling. New requests queue until a slot naturally releases. The policy changes future admission only. Stale entered slots require explicit completion evidence; blind replay is forbidden.

## Scope and limits

Concurrency 3 has functional-stability production evidence. This is not a claim of hardware maximum or throughput optimum. Concurrency 4 is not authorized; any V4 upgrade requires a separate validation stage.

No FDTD or RCWA benchmark is run by this policy upgrade.
