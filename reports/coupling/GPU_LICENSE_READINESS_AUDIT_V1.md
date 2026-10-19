# GPU License Readiness Audit V1

## Scope

Zero-solver audit only. No `run`, `runjobs`, `runsweep`, engine launch, or license checkout was issued. The existing dirty worktree was not staged, committed, or pushed.

## Software and hardware

- Remote execution identity: `DESKTOP-NNE313K\dell`.
- Ansys Lumerical/FDTD: 2025 R1, build 3999.
- GPU: NVIDIA GeForce RTX 3080; `gpuspecs` returned `deviceSMCount=68`, total VRAM 10,737,418 KiB, available VRAM 9,492,463 KiB at audit time, PCIe link width 16, compute capability 8.6 from the hardware audit.
- The official GPU memory checker for the current MEDIUM setup previously returned a maximum of 622,929,568 bytes and minimum of 531,908,680 bytes; `MEDIUM_GPU_MEMORY_FIT=YES`.

## Effective license model and feature evidence

- User-level `C:\Users\dell\AppData\Roaming\Lumerical\License.ini` contains `domain=0`, which selects Enterprise. No higher-priority product-specific domain file was found in the inspected user/system locations.
- Direct FlexLM `lmstat` against the configured FlexLM endpoint succeeded: license server and `ansyslmd` vendor daemon were UP.
- `lum_fdtd_solve`: no feature entry returned; this is the Standard/Business feature and is not the effective model here.
- `lumerical_solve`: 100 issued, 1 in use, 99 available.
- `anshpc`: 100 issued, 0 in use, 100 available.
- `anshpc_pack`: 100 issued, 2 in use, 98 available.

## GPU license requirement

For one GPU job using all 68 SMs, Enterprise licensing requires:

- `1 lumerical_solve` base solve license, covering 4 SMs;
- `64 anshpc` workgroup increments for the remaining 64 SM-equivalent units;
- or `3 anshpc_pack` increments for the 68-unit single-job tier (the next pack tier above 36 total parallel units).

The CPU side does not increase this requirement for the current 12/13-core resource entries because 68 GPU SMs is the larger resource count. The entitlement is sufficient: 99 `lumerical_solve`, 100 `anshpc`, and 98 `anshpc_pack` are available at audit time.

## Why the earlier license query failed

The observed client paths are different:

- `ANSYSLMD_LICENSE_FILE` and `ansysli_util -printlicpath FLEXLM` identify the FlexLM service on the configured 1055 endpoint; TCP reachability to that endpoint passed.
- `ansysli_util -printavail` and `-printusage` attempted the Ansys Licensing Interconnect endpoint on port 2325; that TCP port was not listening, and the commands returned `Could not connect to license server`.
- `ansysli_util -statli` also reported no local `ansysli_server` process.

Therefore the earlier failure was a client/interconnect status-path mismatch, not a dead FlexLM license manager and not an entitlement shortage. Direct `lmutil lmstat` is the authoritative read-only availability evidence for this host.

## Lumerical estimator status

The current `FDTD Solutions.ini` has four active `Local Host` resources, all `device type=CPU`; no GPU resource is configured. Consequently, `islicensestandard`, `getlicenseestimate`, and `getlicenseestimateallactiveresources` could not return values in the existing profile. A separate temporary profile was used to add a GPU resource and query the same commands; the temporary directory was removed, and the existing resource configuration was not changed. The estimator still failed because the product-side license-domain query uses the unavailable interconnect path. This does not overturn the direct FlexLM feature evidence above.

## Verdict

```text
GPU_HARDWARE_READY                  = YES
GPU_LICENSE_READY                   = YES
CURRENT_MEDIUM_SETUP_GPU_COMPATIBLE = YES
MEDIUM_GPU_MEMORY_FIT               = YES
GPU_CPU_PARITY_CANARY_READY         = NO
```

`GPU_CPU_PARITY_CANARY_READY=NO` is a setup-readiness result only: the current MEDIUM resource table is CPU-only and the product-side estimator path is unresolved. No canary was run and no scientific solver entry was consumed.

## Evidence and references

- Current setup-only FSP: `outputs/coupling_ml/FREEZE_V3_RESOURCE_HARDENING_AND_MEDIUM_PW_PREENTRY_V1/W2H_15294_MEDIUM_PW_SETUP_ONLY_WITH_MON_IN.fsp`
- Existing GPU memory report: `reports/coupling/MEDIUM_PW_GPU_SYSTEMCHECK_V1.json`
- Existing feasibility report: `reports/coupling/GPU_FEASIBILITY_AUDIT_V1.md`
- Branch at audit: `work/mdc-np-coupling-ml-v1`, HEAD `b0ec1ad3f92dd093a87b0945fa4cb1aef24321e2`, dirty; no upstream configured.
- Official references: 
  - https://optics.ansys.com/hc/en-us/articles/34669049884947-gpuspecs-Script-command
  - https://optics.ansys.com/hc/en-us/articles/41005222267923-getlicenseestimate-Script-command
  - https://optics.ansys.com/hc/en-us/articles/41005466140691-islicensestandard-Script-command
  - https://optics.ansys.com/hc/en-us/articles/360058577794-Ansys-optics-solve-accelerator-and-Ansys-HPC-license-consumption
  - https://optics.ansys.com/hc/en-us/articles/5770622400659-How-to-check-license-status-and-availability
  - https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/pdf/Ansys_Inc._Licensing_Guide.pdf
