# G025 Ansys License Interconnect Port Conflict Fix

Status: PARTIAL; G025 formal setup preflight is ready for Coupling handoff.

## Diagnosis

The failed G025 Lumerical preflight could not connect to the Ansys Licensing Client proxy on TCP/61208, then attempted to start ansyscl.exe on that same port. The licensing-client log records the bind failure at 2026-10-08 13:48:30. At the final read-only check, PID 8448 owned 0.0.0.0:61208; it is an Ansys 2025 R1 ansyscl.exe process launched beneath an older Lumerical API inventory process tree. Eight existing fdtd-solutions.exe API clients had established loopback connections to that proxy. This is a shared, live licensing component and was left running.

The failure was a proxy-reuse/startup collision: the new client treated the expected proxy as unavailable and tried a second bind at its occupied default port. The evidence does not attribute PID 8448 to the current G025 worker.

## Minimal change and verification

adapter.py now applies the documented Ansys ANSYS_LICENSING_DESKTOP_PORT_RANGE=6200:6299 default to the Runner process before opening a Lumerical API session, while preserving an explicit operator value. No machine/user environment, registry, ansyslmd.ini, license-server configuration, or other process was changed. The focused Runner tests passed: 25 passed.

The official production preflight-setup route passed once for K6GDP2_DEV_G025 / attempt_001. The result records zero solver calls, zero invocations, and zero scientific entries. Its Lumerical licensing debug log shows connections through the pre-existing 61208@127.0.0.1 proxy. Therefore this run confirms that G025 is formally loadable now, but does not demonstrate a fresh ACL process choosing a port in 6200-6299.

The original Ansys logs are live and can grow while other API clients remain connected. The relevant bind/connect records were frozen in LICENSE_LOG_EXCERPTS_V1.txt and SHA-inventoried; raw log hashes in the diagnosis JSON are capture-time references only.

## Handoff

G025 may be returned to Coupling for its existing controlled recovery flow. This task did not call controller start/resume, launch a queue, enter a solver, or retry any scientific case. Coupling should retain the process-scoped range setting and monitor the next naturally required ACL startup; do not terminate the current shared proxy as part of handoff.
