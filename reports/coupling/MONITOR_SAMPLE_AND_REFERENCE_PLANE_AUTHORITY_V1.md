# Monitor Sample and Reference Plane Authority V1

Physical field monitors and canonical reference planes are distinct. The V3 setup keeps raw E/H at `MON_IN=-100 nm`, `MON_PRENP=1150 nm`, and `MON_POSTNP=1800 nm`; the Floquet state is projected/de-embedded to `IN_REF=-50 nm`, `PRENP_REF=1202 nm`, and `POSTNP_REF=1722 nm`. `MON_REFLECTION=-400 nm` remains R-only signed-Poynting truth.

The previous `1200/2212 nm` PRENP/POSTNP values were stale monitor-contract wiring, not the V3 physical setup. They are rejected by the role-aware validator. Mesh coordinates such as the legitimate `1202..1222 nm` spacer/interface region are unrelated geometry values and remain unchanged.
