# Cyclic label-transform tests

All checks were run against the frozen production projector and frozen H2 decoder on the existing 272G dataset. They are zero-solver numerical/software tests; no FDTD, Runner, sealed data, or ledger write was used.

| Test | Result | Evidence |
|---|---|---|
| `T^6(D)=D` geometry identity | PASS | exact max diameter difference 0.0 nm |
| stabilizer-aware view deduplication | PASS | 1-, 2-, 3-, and 6-period test vectors yield 1, 2, 3, and 6 unique views |
| complex `T^6` for 21 λ × 7 orders × TE/TM | PASS | max abs 3.768e-15; relative L2 9.202e-16 |
| magnitude invariance / zero-order phase | PASS | max magnitude error 8.882e-16; zero-order max complex error 0.000e+00 |
| production Fourier-projector sign | PASS | six shifts, max abs 1.310e-15; max relative L2 1.167e-15 |
| frozen H2 invariance over 272 × 21 × 7 × 2 | PASS | η max error 3.331e-16; absolute order max error 3.331e-16; P_scale exact |

The randomized algebra check includes all wavelengths 440–460 nm, all seven orders `m=-3…+3`, and both polarizations. The synthetic projector fixture uses the same projection function as the production 609D extractor; it verifies the sign convention, not the electromagnetic accuracy of a fabricated field.

Reproduction code: `test_cyclic_label_transform.py`. Machine-readable results: `CYCLIC_LABEL_TRANSFORM_TESTS.json`. H2 decoder expected identity: `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15`.
