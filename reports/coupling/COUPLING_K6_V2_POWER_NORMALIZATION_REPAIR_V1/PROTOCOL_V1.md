# COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1 - frozen intake protocol

Status: frozen for the single first-case audit and explicit label supplement.
Scope is K6LDA1_DEV_D1_M05/attempt_001 only. No other case, historical truth,
or runner artifact may be rewritten by this protocol.

## Frozen quantities

- eta[m,w]: power_fraction_of_monitor_total from the frozen seven-order
  grating result, ordered m=-3..3. It is the order fraction of monitor-total
  transmitted power.
- P_scale[w]: positive total transmitted power normalized to the frozen IN_REF
  incident power per area. Recompute from the full-period POSTNP E/H surface
  integral, divided by the unit-cell area and the frozen IN_REF +z (0,0) TM
  incident power per area.
- V2 absolute order source power is P_scale * eta in that order. The stored
  legacy power_fraction_of_source field is not edited; it is recorded as the
  field being superseded for this one case.
- The frozen normalized complex state C_hat and its reference phase remain
  unchanged. No oracle phase alignment, re-normalization, or H2 change is used.

The Runner's prior T_FDTD value is a zero-order modal transmission proxy.
It is not the total multi-order transmitted fraction. sourcepower, the POSTNP
integrated flux, zero-order modal power, and signed/net modal flux are
reported separately.

## Numerical checks

1. Recompute flux from raw complex Ex/Ey/Hx/Hy on the actual saved x/y
   coordinates using trapezoidal endpoint half weights.
2. Compare integrated flux with current-backend transmission * sourcepower
   and independently measured Runner P_scale.
3. Check sum(eta)=1 at all 21 wavelengths against the frozen importer
   tolerance atol=1e-6; the frozen importer comparison is
   rtol=1e-3, atol=1e-9.
4. Compare normalized C_hat through the unchanged frozen H2 decoder with
   eta and P_scale*eta, using the existing H1 numeric authority
   (authority SHA 8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd).
   This is a one-case label/decoder consistency diagnostic: C_hat and
   P_scale are the truth arrays passed back as diagnostic predictions.
   It is not model performance, a production H1 result, or admission.
5. Separately report the direct surface-flux versus nine-by-nine modal-sum
   residual. No standalone physical-closure tolerance exists in the audit
   evidence; do not claim this residual is zero or independently certified.

## Immutable bindings and access

The supplement must bind case id, attempt, ordered geometry, physical contract,
the original source manifest, state NPZ/metadata, raw NPZ/metadata, and original
orders JSON hashes, plus numeric hashes for recomputed P_scale, eta, and
P_scale*eta. It references an independent physical audit report by path and
SHA. Only the frozen development-local-axis role is eligible. No confirmation
or diagnostic role is accepted. Default ingestion remains fail-closed when
the supplement is omitted.

Historical raw files, rejection record, FSP/H5, orders JSON, old 32G labels,
and EXT02 diagnostic are immutable. The supplement changes only the derived
source-power interpretation for this single development case. It does not
grant model production admission.

## Execution boundary

This repair task adds zero solver entries and zero training fits. The first
case already has one historical solver entry and must never be replayed. Any
remaining 127 frozen development entries require successful fresh live
Runner authority, budget, owner/fence, and startup checks. Confirmation=0,
training=0, P_scale fit=0, replay=0.
