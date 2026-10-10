# fdtd-mcp read-only ownership review

Source: https://github.com/plaask/fdtd-mcp ; pinned HEAD e2a92a9367f03b5b8440e9c0e26da9f08fb002db. Source_manifest.json records source SHA, size and immutable URLs. No package or MCP server was installed, no external module imported and no cleanup function executed.

Reviewed [proctree.py](https://github.com/plaask/fdtd-mcp/blob/e2a92a9367f03b5b8440e9c0e26da9f08fb002db/fdtd_mcp/engine/proctree.py), handlers/session.py, bridge.py, tests/test_proctree.py and tests/test_engine_reaping.py.

Classification uses Toolhelp PID/PPID snapshots: direct children are owned/bridge, missing parents orphan, other live parents foreign. Descendant traversal is cycle-bounded. These are structural labels, not verified scientific ownership. No creation-time checks protect classification or remembered PID cleanup; a reused PID is a material APCD incompatibility. Enumeration errors may return empty/partial data, so APCD must preserve query coverage/errors explicitly.

Session launch records engine PIDs and best-effort assigns a kill-on-close Windows Job. Close/reopen/EOF shutdown use reap helpers. This conflicts with preserving legally started work across controller/SSH exit. We only queried existing membership; no Job was created, assigned or modified.

Default proctree CLI (without --kill) is inventory-only. Explicit --kill invokes orphan sweeping; sweep and remembered-PID helpers lack a dry-run argument. Upstream tests inject tables/mock kills, check classification, foreign skipping, remembered PIDs and unsupported Jobs; this is not real Windows lifetime or PID-reuse validation. No killing/sweeping/Job-limit code is reused. APCD's separate evidence-only helper adds creation agreement, self-match/error refusal and positive bound-source/lineage requirements.
