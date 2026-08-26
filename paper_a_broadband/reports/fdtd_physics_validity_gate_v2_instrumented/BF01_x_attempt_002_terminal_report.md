# BF01_x attempt-002 terminal V2 audit

Status: PASS

Exactly one new FDTD entry was authorized and consumed: BF01_x attempt-002. Resource contract: 12 MPI x 1 thread; Paper A active FDTD <= 1. No BF01_y or BF02-BF04 case was started.

## Pre-entry authority

- Physics semantic fingerprint: 7ef054cffe4e3967c43a700fd2498397d3de1f39104d9c6b1977c4bcbfb5085f
- Instrumented pre-FSP entry SHA256: 748999f34803762b38ebf8ed7db131ce95fd4df02c2ca31afa41ce9845704a69
- V2 instrumentation fingerprint: c7b67d8358f4147c401620516d46c8c2ad95314593586aa38129013dd0c65657
- All matched before admission.

## V2 result

BF01_x attempt-002: VALID_FOR_PHYSICS_TRUTH

- Independent time-series samples: 15,851
- Late-window slope: -1.2094941737054567e-11
- Positive late-window growth: false
- Transmission sanity: PASS
- Source normalization: PASS
- No abs, clipping, sign correction, renormalization, wavelength removal, or manual salvage was applied.

The controller log contained no Auto Shutoff trajectory. V2 acceptance therefore relies on the persisted independent time-series plus passing transmission and source-normalization gates; no Auto Shutoff evidence was invented.

## Attempt consistency

Against attempt-001 over all 31 formal wavelengths:

- transmission maximum absolute difference: 0.0
- transmission mean absolute difference: 0.0
- sourcepower maximum/mean absolute difference: 0.0 / 0.0
- sourcepower attempt-002/attempt-001 ratio range: 1.0 to 1.0
- compared complex checkpoint observables: all maxima 0

Instrumentation is demonstrated non-perturbative for the directly compared scientific observables. Attempt-001 remains INSUFFICIENT_EVIDENCE_NOT_VALIDATED. Attempt-002 is the authoritative BF01_x physics truth.

## FSP lifecycle note

The entry SHA is preserved in immutable attempt provenance. The on-disk instrumented pre-FSP binary SHA changed after the solver lifecycle from 748999f... to 53c53f..., while the current physics semantic fingerprint remains unchanged. This binary container lifecycle mutation is recorded; no repair, overwrite, or replay was performed.

## Stop condition

Do not start BF01_y or BF02-BF04. A new Chart decision is required before resuming the remaining batch.
