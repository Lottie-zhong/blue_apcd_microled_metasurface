# R2-4G3 G4 Candidate Generator Requirements

G4 may generate candidates only. It must not run FDTD.

G4 may output an FDTD shortlist only if proxy v1 shows:
- no hard_reject;
- total_risk_score below the defined gate;
- no D5-like / E1-like / F0_0781-like / F0_0204-like red flags;
- source_position_status = requires_tri_point_FDTD, not pass;
- route family and full structure parameters are present;
- shortlist size <= 1 primary + 1 backup.

If no candidate passes, G4 must output no-pass. It must not force a shortlist from failed routes.
