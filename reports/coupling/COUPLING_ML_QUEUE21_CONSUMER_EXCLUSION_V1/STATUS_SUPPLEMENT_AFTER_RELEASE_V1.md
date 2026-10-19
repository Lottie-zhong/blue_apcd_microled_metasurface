# Queue21 status supplement — hold release and EXT02 route refresh

**Append-only update; the V1 registry, report, and V1 inventory remain unchanged.**

## Queue21 disposition and hold

The historical identity remains `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`, events 1499 and 1506, with physical solver-entry count **UNKNOWN**. The Coupling consumer-exclusion registry remains at SHA-256 `01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261`; its creation-time Runner HEAD/active-hold fields are historical snapshot fields and are not rewritten.

The current Runner controlled authority records the exact queue21 hold-release authority SHA `7b2412e3271aa518fe67deb9b6cd8b74cf7da99e1c8331bee948e493aad0b7d2`, event 4, generation 27. A fresh read-only call to the Runner's official global-entry-control snapshot returned health PASS, control generation 27, no active global holds, and `new_entry_hold=0`. It did not modify the database. This update does not relax the case quarantine or make queue21 truth eligible for any consumer.

## EXT02 route refresh — paused before new proof

The current Runner source tree is at committed HEAD `5532a130439fa18f67986628ca74c4355a132b43`, but its working tree currently has uncommitted changes to the controlled-admission authority and adapter. The authority working-copy SHA at capture was `cc44603accaa173bf879ce7ae36f5400a4cea378c7aa07564def64336d26ac3f`; the adapter working-copy SHA was `688be69e978b3b9e43e7a09c846aaa6e0448b1250a3e9a18098d4e3bf6df6308`, and its local authority pin matched that working-copy SHA. These are uncommitted working-state hashes, not a committed route handoff.

The preceding authority snapshot had an internal text/boolean conflict between the EXT02 one-entry authorization and `identity_enrollment.approval_basis`. The Runner working copy now has wording aligned with the one-entry flags, but the Runner owner has not yet supplied a committed, test-verified successor handoff. No source manifest, proof, or envelope was rebound to either the earlier `476547...` authority or this uncommitted working-copy hash.

The Coupling setup files were only hashed/read as bytes; no fresh Lumerical LOAD or monitor readback was performed in this update. The existing source/staged FSP hashes remain `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`, and the physical contract remains `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68`. Prior route-bound proofs are preserved and remain historical: top-level proof authority `d2b35c...`; route-refresh-v1 proof authority `15377a...`. Neither is evidence for the successor authority.

A new route-bound source manifest, LOAD-only proof, or envelope is **not yet issued**. Resume only after the Runner owner provides the committed successor authority/adapter hashes and successful test status. Then perform a fresh actual LOAD against the unchanged base/source/staged FSPs, capture its readback, bind a new manifest/proof/envelope to that committed route, and return those hashes for the Runner owner’s formal preflight and FINAL_LAUNCH_REVALIDATION. This is not solver authorization. No solver entry, formal preflight, FINAL_LAUNCH_REVALIDATION, FDTD run, or confirmation-response access occurred in this update.
