# K6 ledger reconciliation (read-only)

**Decision: RECONCILED_READ_ONLY.** No authoritative ledger, manifest, runner database, or runtime file was edited in this review.

## Identity and budget

- Frozen queue manifest: 128 ordered unique Case IDs; `authorized_development_case_count` is 128; each manifest entry declares `attempt_001` and a maximum of one Solver Entry.
- The manifest separates 3 already-entered initial IDs from 125 prepared queue IDs: 3+125=128. This explains the old “remaining 127” directory name and the 125-item prepared queue; it is not an over-budget entry.
- Current ledger: 128 unique entered IDs, all in the frozen manifest; 0 automatic replays; 0 remaining unentered. The prior committed checkpoint had 36 entered IDs, all still present in the current entered set.
- Execution crosswalk: 3 historical entry receipts resolve to 3 distinct Runner run IDs; 35 later legacy rows resolve to 35 distinct Runner run IDs; 90 further rows resolve to 90 distinct case/attempt-verified V2 entry receipt SHA records. No duplicate reference occurs within any class. The 90 V2 receipts all match their manifest Case ID, `attempt_001`, and `solver_entered=true`.
- Eight legacy ledger rows omit `attempt_id` in the record itself. Their unique Case IDs and run IDs match the single `attempt_001` record in the frozen manifest. The crosswalk preserves this source gap instead of rewriting the ledger.
- Final case-status snapshot has 128 unique IDs exactly equal to the manifest, all 128 entered, 124 truth-valid and label-valid, and zero unentered.

## Consumed failures

Four entries remain consumed without valid truth/labels: K6GDP2_DEV_G023, K6GDP2_DEV_G024, K6GDP2_DEV_G026, K6LDA1_DEV_D6_M05. They were not replayed or replaced. This is consistent with 128 entries and 124 valid labels; it does not imply four unauthorized cases.

The full per-case crosswalk is `K6_CASE_EXECUTION_RECONCILIATION.csv`. It distinguishes native Runner run IDs from immutable V2 receipt SHA references instead of inventing a common execution-ID format.
