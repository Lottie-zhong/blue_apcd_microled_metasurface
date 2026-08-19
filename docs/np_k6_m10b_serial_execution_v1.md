# NP K6 M10B serial angular HF anchor execution v1

Status: `STOP_BATCH_FOR_REVIEW_P_QUALITY_GATE_FAIL`.

## Contract

- Task-local active FDTD cap: 1; P then S exact serial order.
- Per-job resource readback: 12 MPI processes x 1 thread.
- Global scheduler: V3, cap 3; registry direct edits were not used.
- Durable monitor: one server-side controller, file-only routine state, 600 s monitor interval / 3600 s summary contract.

## P attempt

- Case: `NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE`, attempt `attempt_001`; entered/run/engine/post/controller = `1/1/1/1`.
- Slot: `GLOBAL_SLOT_1`; acquire `2026-08-19T05:07:15.138115+00:00`; release `2026-08-19T05:08:06.716407+00:00`.
- Post-FSP SHA256: `60c6f668b0f9fdc64b00b10fa00699314d4f377ac711ed6142290ac7020e67fc`.
- 11-point read-only extraction: finite and exact wavelengths = `True/True`.
- max |1-T-R| = `0.0214212198722` (gate <= 0.01: FAIL).
- max order-sum/T mismatch = `1.11022302463e-16` (PASS); max normalization mismatch = `2.22044604925e-16` (PASS).

## S gate

- S attempt_001 was not started; S entered/run count remains 0.
- Because P failed the frozen closure gate, the batch stopped for review; no automatic continuation or replay was performed.

## Resource audit

- policy = `APCD_GLOBAL_FDTD_PRODUCTION_RESOURCE_POLICY_V4`; per-job = `12 MPI x 1 thread`; local cap = `1`; peak = `1`.
- P/S overlap = `0` s; global cap = `3`; active slots after release = `0`.

## Evidence

- `outputs/np_k6_m10b_serial_execution_v1/`
- `scripts/np_k6_m10b_serial_controller_v1.py`
- `scripts/apcd_global_fdtd_slot_v4_resource.py`
- `scripts/validate_np_k6_m10b_serial_execution_v1.py`

This is an angular HF anchor result, not a training-label promotion. The failed P closure gate is preserved as the terminal adjudication; S remains pending explicit review/authorization.
