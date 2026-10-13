# Test Results

- Full suite: N:/anaconda_envs/RCP_LCP/python.exe -m pytest -q platform_v2/tests
- Result: **252 passed, 0 failed, 0 skipped** in 372.99 seconds.
- Warnings: 13 model/deprecation warnings (Pydantic field-name shadowing and numpy.trapz deprecation); no failure.
- Focused validator/profile/resource suite: **60 passed, 0 failed, 0 skipped** in 80.19 seconds.
- Full raw output: FULL_REGRESSION.log (SHA-256 4fe595db71a98a0f90a1f8bf1275c51aa93592bc99de2d4624905714eee9dfab).

Coverage added or directly exercised:
- Real frozen A1/A2 contract bytes, raw/canonical SHA equality, identity, 5 nm mesh, 6 ps maximum, 1e-6 shutoff, 609D schema, no-rewrite behavior.
- Default-deny empty profile; absent Science Admission denial; wrong physical-contract SHA and wrong case geometry denial.
- Generic 609D B/C offline adapter/importer path, fixture-only authority isolation, ledger no-entry invariants.
- WDDM global resource gate, third-party activity with N/A memory, PID reuse, missing/invalid evidence, and prelaunch gate placement.

No real Lumerical FDTD/FMM/RCWA solver, ML fit, scientific entry, replay, or production Admission was executed. Synthetic fixtures in the regression are not scientific truth.
