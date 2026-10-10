# UNKNOWN process closure and cutover readiness V1

Task: APCD_GPU_V2_UNKNOWN_PROCESS_CLOSURE_AND_CUTOVER_READINESS_V1. Client date 2026-10-10 Asia/Shanghai. Verified starting HEAD 05fa4f6d51535386635fee0a6b0cedcf496faa49, clean and 0/0. Verdict **BLOCKED_WITH_IDENTIFIED_OWNER_RISK**. Science calls=0, native API opens=0, Scheduler changes=0, process termination=0, foreign handle closure=0. V1 code and existing physics/truth preserved; V2 architecture and scientific dispatch remain unchanged.

## A. Exactly 16 original identities

All 16 original PID/create_time identities remain live in both independent snapshots. CIM/psutil creation times agree within 2 ms; all recorded parents are alive and older than their children. No original PID reuse was detected. Every target has DELL owner, session 0; cwd, file handles, socket endpoints, ancestry, descendants, handle count and read-only Job membership were obtained. All are members of a Job, but IsProcessInJob does not identify its controlling owner, limits or close behavior. No Job assignment or modification was attempted.

| PID | Creation UTC | PPID @ create_time | Command / evidence | Classification |
|---:|---|---|---|---|
| 16572 | 09-28 14:55:48.8926280Z | 26976 @ 1790607348.807479 | missing result_meta body; child/API other-branch cwd | UNRESOLVED |
| 17436 | 09-28 14:44:21.6947750Z | 33316 @ 1790606660.4175227 | API scope unresolved; branch cwd + live GUI-license connection | UNRESOLVED |
| 17576 | 09-28 14:57:30.8102880Z | 28420 @ 1790607449.9801545 | API scope unresolved; branch cwd + live GUI-license connection | UNRESOLVED |
| 18080 | 09-28 14:56:43.3519840Z | 21640 @ 1790607403.2741394 | missing result_meta body; child/API other-branch cwd | UNRESOLVED |
| 18936 | 10-07 15:13:30.4462510Z | 45704 @ 1791386010.225937 | stdin body/launch receipt missing | UNRESOLVED |
| 24800 | 09-28 14:54:27.8853250Z | 24336 @ 1790607267.8003948 | missing result_meta body; child/API other-branch cwd | UNRESOLVED |
| 26372 | 09-28 14:55:01.2214860Z | 27248 @ 1790607300.4211576 | API scope unresolved; branch cwd + live GUI-license connection | UNRESOLVED |
| 27248 | 09-28 14:55:00.4211570Z | 26540 @ 1790607300.333854 | missing result_meta body; child/API other-branch cwd | UNRESOLVED |
| 28420 | 09-28 14:57:29.9801540Z | 31524 @ 1790607449.8801565 | missing result_meta body; child/API other-branch cwd | UNRESOLVED |
| 29236 | 09-28 14:32:09.3682110Z | 10796 @ 1790605929.1418755 | stdin body/launch receipt missing | UNRESOLVED |
| 29816 | 09-28 14:54:28.6805900Z | 24800 @ 1790607267.885326 | API scope unresolved; branch cwd + live GUI-license connection | UNRESOLVED |
| 31844 | 09-28 14:56:44.2256020Z | 18080 @ 1790607403.3519845 | API scope unresolved; branch cwd + live GUI-license connection | UNRESOLVED |
| 31848 | 09-28 14:30:01.1656560Z | 30336 @ 1790605798.418521 | bound inventory + parent 30336 + matching held JSON | CONFIRMED_OTHER_ACTIVITY |
| 32256 | 09-28 14:55:49.8376620Z | 16572 @ 1790607348.8926282 | API scope unresolved; branch cwd + live GUI-license connection | UNRESOLVED |
| 33316 | 09-28 14:44:20.4175220Z | 26492 @ 1790606660.14974 | stdin body/launch receipt missing | UNRESOLVED |
| 33824 | 09-28 14:32:10.7656140Z | 29236 @ 1790605929.368212 | API scope unresolved; branch cwd + live GUI-license connection | UNRESOLVED |

The complete 16-row machine-readable table is reports/unknown_closure_v1/process_evidence_16.json; CSV includes all requested fields. UNRESOLVED is not OTHER simply because V1 PID does not match. Metadata helper names, other-branch cwd, no present engine, no GPU listing and low/unchanged CPU are insufficient to establish a read-only instruction scope. Missing parents would not be kill authorization, and PID reuse would clear only the original identity, not its replacement.

PID 31848 is CONFIRMED_OTHER_ACTIVITY because its live parent 30336/create_time 1790605798.418521 is consistent with the earlier archived identity; current inventory source SHA 61651099bc6415f15a8b54d5bd9ff24ae666f5c0ed91131f766abb6d04a3b7d4 equals the archived source hash. The reviewed source loads historical surrogate-case FSPs, reads objects/results, writes an inventory to stdout and closes its API; it contains no solver call. API cwd and the held inventory JSON match that source and parent launch redirection. This classification does not authorize terminating it. A source hash from the instant of its September launch is unavailable; the classification rests on consistent source/archive/lineage/cwd/held-output evidence, not a filename alone.

Five result_meta helpers have missing source bodies. Their matching API children point to a historical surrogate case; two other API children point to NP_K6_M4_B2_G01_S under an earlier NP worktree and have stdin parents 29236/33316. PID 18936 is a later stdin interpreter without a script/body/launch receipt. Its matching descendant SSH process 40664/create_time 1791386010.7581801 remains live, with zero TCP connections listed at inspection; that does not establish its stdin execution scope or clear owner risk. Transport/authentication arguments are retained only in private raw evidence, with a commandline SHA in the committed tree. These 15 remain UNRESOLVED; full provenance was not reconstructed.

## B–C. Owner and concurrency qualification

Two snapshots end at 2026-10-10T03:20:44.995978+00:00 and 2026-10-10T03:22:34.366779+00:00 and agree on identities, V1 task definitions/state, markers, registry SHA, request inventory, counters and truth hashes. Neither observes a running V1 Controller/Worker or FDTD scientific engine. V1 active_run and runner/worker lock files are absent; no current scheduled request lacks a terminal result. Controller remains STOPPED_RECONCILED. V1 scientific owner absence is **not proven** because unresolved executable instruction scope persists.

Known current restart exposure is distinct and positively evidenced: global admission row is new_entry_hold=0, generation=27, health=PASS, with no active GLOBAL hold. Thus global admission is not durably closed. Both installed V1 tasks are Enabled/Ready with COM AllowDemandStart=true (task_demand_start_readback.json), have no timed triggers and use the DELL InteractiveToken principal. IgnoreNew applies per task, not across V1/V2 independent owners. Demand/manual invocation and old CLI/envelope entry remain unfenced by V2. Terminal request receipts exist, but this is not a proof of cross-platform anti-revival enforcement. No installed task, gate or request was changed to hide this gap.

Eight API servers have ESTABLISHED loopback connections to ansyscl.exe PID 8448/create_time 1790605802.3483458, ACL port 61208. License logs correlate launch-time PID and lumerical_gui checkout, with ongoing client records. Their API log files are empty. License connectivity does not prove or exclude scientific ownership or GPU engine entitlement. The 16 targets were not listed by the compute-app query; WDDM reporting is incomplete and this is not zero GPU-use proof.

Security is readable (administrator identity), but retained records begin 2026-10-08T05:54:01Z, after all original target launches, and no 4688 records were returned. Auditpol Process Creation reports No Auditing. Scheduler Operational is disabled/empty; Sysmon log does not exist. No logging policy was enabled. Handle.exe is not installed. psutil exposes file handles and count, not a complete native named-pipe/Job handle table; full handle ownership remains a gap. Query errors/unsupported surfaces are preserved and never interpreted as inactivity. Bounded source searches found historical inventories and duplicate snapshots, not missing stdin/result_meta launch bodies.

## D–E. Transaction and V2 remaining scope

The separate CUTOVER_READINESS_TRANSACTION_V1.md is reviewable and reversible before science entry, but **not executable now**. First establish the old admission hold, then inhibit new V1 dispatch, then prove old-owner absence, then transfer authority under a single fencing generation. A closed gate must span Scheduler/SQLite/filesystem steps; there is no asserted cross-system ACID transaction.

Read-only V2 offline-ledger inspection shows SQLite integrity=ok and empty slot owner PID/create_time/request with generation 1 in both existing fixture ledgers. Offline ownership tests pass, but no production V2 science owner or trusted production ingress/migration exists. The existing native dispatcher still refuses scientific run. A WMI-based independent OFFLINE launch and persistent logs were previously accepted; no new service/task was installed or launch test repeated. Production launcher qualification, exact trusted receipts/Coupling compatibility and imported 38-entry budget remain prerequisites. Disabling two tasks alone cannot inhibit all old manual CLI paths.

G027 attempt_001 has two FAILED_PREENTRY registry/status records, solver_entered=false. Coupling's accepted evidence explicitly records entry_consumed=false, solver_invocations=0, runner_slot_entry=false. Counts remain **38 entered / 34 truth-valid / 34 labels-valid / 90 unentered**, replay=0, confirmation-response access=0. G025 original FSP/H5 hashes equal the prior acceptance in both snapshots. Prior native LOAD/importer/systemcheck/license and independent fixture receipts were hash-verified and reused; no native acceptance was rerun. GPU engine license remains NOT_TESTED.

## F–G. Changes, checks and next operation

Only offline evidence classifier/collector, decision records and their regression tests were added. No automatic cleanup or third-party MCP was copied, imported or installed. Tests cover PID reuse, missing parents, missing/invalid creation, provider disagreement, access failure, self-match and insufficient cwd/name inference; 89 tests PASS and lint PASS. Original 78 tests are retained. Full process snapshots/source searches remain in isolated runtime D:\apcd_runtime\gpu_v2_unknown_closure_20261010_v1, with a SHA manifest; committed reports contain the target table, two curated snapshots and evidence digests. Final Git receipt is outside Git in that runtime.

Next formal operation is owner/source reconciliation of the remaining 15 identities, especially stdin PID 18936. Then obtain approval for the staged closed-admission cutover transaction; do not disable tasks, transfer production authority or launch G027 on the strength of this BLOCKED report.

Full private snapshots include unredacted descendant commandlines; committed snapshots/CSV redact only SSH transport/authentication arguments, retaining PID/create_time and command SHA. This protects connection information and is not a deletion of ownership evidence.
