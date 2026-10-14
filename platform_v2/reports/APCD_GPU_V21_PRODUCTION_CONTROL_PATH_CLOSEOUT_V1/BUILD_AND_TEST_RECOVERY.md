# Ordinary engineering failures retained and resolved

Initial new integration run omitted APCD_TEST_COUPLING_ROOT (16 setup failures).
After setting the existing formal read-only fixture root, five tests exposed an
incomplete simulated importer record. Adding the exact identity fields to the
fixture produced 16/16 PASS; no scientific contract or production guard changed.
Raw first/intermediate logs and XML are retained separately.

git diff --check found a final blank line in the new test; a separate normal
commit normalized it (no amend/reset). The first candidate builder compared
canonical Git LF blob bytes with legitimate CRLF worktree bytes. It now verifies
identity with Git's own clean filter (hash-object --path) and packages precisely
the tested worktree bytes. A real isolated Git CRLF/dirty-source test was added;
the six release-tool tests pass.

The candidate-origin assertion intentionally rejected a first pytest startup
that imported the worktree rather than the candidate because of cwd precedence.
Running from the candidate and explicitly pinning its module search path fixed
the harness. The successful complete run records origins for all three groups:
309 PASS / 0 FAIL / 0 SKIP. No assertion or production guard was removed to pass.
