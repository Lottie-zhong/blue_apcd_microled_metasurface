# MDC-ML P0-C repository freeze contract audit

## Scope

P0-C replaces the obsolete exact-HEAD assertion with an immutable freeze-anchor
contract. It does not alter the frozen physics specification, dataset schema,
structure grammar, frozen reports, TMM implementation, or F0 smoke files.

## Repository contract

- Freeze anchor: `ba361fa39a5c04cccbaa55ad1d89b328c5a8d91b`.
- HEAD policy: `descendant_or_equal`.
- Ancestry predicate: `git merge-base --is-ancestor <anchor> HEAD`.
- Root of trust: the audit source fixes the anchor identity and requires the
  manifest to name the same anchor.
- Backward compatibility: `verify_head=True` means verify the full repository
  freeze contract. It no longer means exact commit equality.

## Immutable payload

The manifest is `configs/mdc_ml_spec_freeze_manifest_v1.json`. Every expected
SHA-256 was calculated from `git show <anchor>:<path>`, then checked against both
the manifest and current working-tree bytes.

| Path | SHA-256 |
|---|---|
| `configs/mdc_ml_inverse_design_spec_v1.yaml` | `77fb2d136e7e235b829c9493b1a3eddcbedd9aa68a5a77f2ca2e86c5a32d5045` |
| `configs/mdc_ml_dataset_schema_v1.json` | `af86d7a3ca77f6c25101eef9182ca5ec1c0b5d458bda7502fbcbea89b8d0aadf` |
| `scripts/mdc_ml_structure_grammar_v1.py` | `289293e2edc7d12378c71eb92e16872115f067c857b0e69ac694ba16ee170064` |
| `reports/mdc_ml_inverse_design_spec_v1.md` | `6a50737005e525b73de2bd7c8d444b11a2239bd833bc4a3a3e2382d7f83bdaab` |
| `reports/mdc_ml_inverse_design_spec_v1_p0_contract_audit.md` | `191add9010d6ca33dbb8e50652a2cc5cbb39b4e3ab70507f74b67d1d2e6f2824` |
| `reports/mdc_ml_inverse_design_spec_v1_p0b_hash_objective_audit.md` | `06a85261087fb2e32d557159f94b5e32a99ed3214b6093a757dd7556d9031b38` |

The audit implementation and tests remain explicitly mutable maintenance tools.
Adding wavelength-grid or smoke files does not change the immutable payload
inventory or any payload hash.

## Validation design

Tests cover anchor equality, legal descendants, missing anchors, unrelated Git
history, byte mutation of one payload, exclusion of smoke/grid maintenance files,
anchor-derived hashes, and the legacy argument's new ancestry semantics. Formal
remote results:

- `py_compile`: PASS.
- Formal `--audit-only` with default repository verification: PASS.
- Freeze anchor exists: true.
- Anchor is ancestor of current HEAD: true.
- Immutable payload count: 6; drift count: 0.
- Full relevant lightweight pytest: 37 passed.
- F0 smoke regression tests: PASS without regenerating smoke data.
- No TMM, FDTD, Lumerical, model training, or pilot generation was run.

## Old-contract diagnosis

The obsolete behavior was implemented in
`scripts/audit_mdc_ml_inverse_design_spec_v1.py`: `FROZEN_COMMIT` held
`40dedf...` and the formal audit compared `git rev-parse HEAD` to that value.
`tests/test_mdc_ml_inverse_design_spec_v1.py` called the formal audit and thus
inherited the false failure at the legitimate spec-freeze commit. The old hash
still appears as `source_frozen_commit` provenance inside the immutable spec and
as `SPEC_SOURCE_FROZEN_COMMIT` in the maintenance audit; neither occurrence is a
HEAD predicate. The new anchor was not substituted as another exact-HEAD check.
