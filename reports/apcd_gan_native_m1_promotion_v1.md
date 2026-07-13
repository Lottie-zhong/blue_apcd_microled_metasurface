# APCD GaN Native-M1 promotion v1

- Canonical material: `APCD_GAN_NATIVE_M1` (`project_native_sampled_engineering_reference`).
- Source: `F:\wc_312\MDC_blue_oujizi_m\m_1.fsp`; SHA256 `d7511bb92154152d5050d7ae664cb5b281ad3794a280129008359353b357e26f`; object/material `GaN`/`GaN`.
- Raw table: 500x2 complex, SHA256 `906f2983665a51b748aa85ef85cd095550bb64a8ef77b8796e36a0b765407ef0`. Query response: 601 points, SHA256 `99f8ce329c342ae4f9de055ee750981ce2358acf0a2e1048ebe08d17fa642fa8`.
- 450 nm source query: n=2.414946476353578, k=0.08415346869326513; high-loss warning retained.
- Blank-session raw-table roundtrip: max |dn|=1.776e-15, max |dk|=4.580e-16.
- TMM loader uses original raw epsilon, not a fit of the 601-point query: max |n+ik difference| to the source query=3.954e-04; at 450 nm loader/source delta=1.447e-04.
- The TMM loader evaluates the raw sampled epsilon table by linear interpolation, while Lumerical evaluates its fitted material representation. The observed maximum |Δ(n+ik)| over 420–480 nm is 3.954e-4, including 1.447e-4 at 450 nm. This representation delta is retained as cross-method provenance and is not silently treated as zero.
- Formal FDTD use requires matched reference-plane de-embedding: do not attribute source-to-stack GaN propagation loss to MDC loss; device/reference use the same GaN; bare GaN/Air remains an independent control.
- Legacy `APCD_GAN_LEGACY_N241` (n=2.41,k=0) is historical-only; no constant fallback is permitted.
- No solver run or source-FSP save/modification occurred.
