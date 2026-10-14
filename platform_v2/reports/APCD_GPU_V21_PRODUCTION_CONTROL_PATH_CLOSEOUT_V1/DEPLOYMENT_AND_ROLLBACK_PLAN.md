# Disabled patch deployment / rollback plan - NOT EXECUTED

Source release `44bee753f34cb01b308dc8975a84537b8cfead35`; target release directory:
`D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_trusted_admission_44bee753f34c`.
Archive SHA `42026ee620d26abb8f06394374d0657b80d1cf03f55b9ce476d755df0b576542`; package manifest SHA
`8244f26ad29d9b508bd19e353510b2a7ac930ed5133595838904bf18942ad8e1`; code inventory SHA `08c1a1009d873a0903577e7c13e233413cce879ddb05bdcf3d9c57d793288330`.
This package intentionally carries the current profiles=[] Disabled platform.
It grants no Admission. The installed release remains b9abe87058d6.

## First: independently approve missing authority operations

Science Owner reviews the issuer/genesis protocol and profile/source enrollment.
User separately authorizes Disabled code/pointer/task rebinding and a precise
distinct Science principal + DACL + Coupling ledger-writer capability plan. Do
not guess a SID, grant rights, rotate keys, or run older Apply installers with
stale package/owner pins. No new trust root is needed by the proposed ACL adapter;
requiring cryptographic trust would be a separate root/key decision.

## Exact candidate verification command (read-only)

```powershell
$py = 'N:\anaconda_envs\RCP_LCP\python.exe'
$r = 'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1\platform_v2\reports\APCD_GPU_V21_PRODUCTION_CONTROL_PATH_CLOSEOUT_V1'
& $py "$r\RELEASE_CANDIDATE\platform_v2\tools\build_trusted_release.py" verify --package "$r\RELEASE_CANDIDATE" --manifest-sha256 '8244f26ad29d9b508bd19e353510b2a7ac930ed5133595838904bf18942ad8e1'
if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_VERIFY_FAILED' }
```

## Authorized installer transaction requirements

1. Recheck the pinned installed code/config/task XML, empty slot and no active or
   incomplete production transaction. Keep all three audited tasks Disabled.
   Take the existing controller OS lock; do not stop a foreign process. Abort on
   owner/version drift. GUI presence alone need not block a zero-solver patch.
2. Create a new immutable installation backup, using existing controlled patch
   conventions. Save exact task XML; all current installation-pointer JSON,
   platform/config/binding/DENY files and code inventories; runtime ACL SDDL;
   SQLite online backup and relevant immutable science-ledger snapshots. Verify
   backup SHA and rollback target before modifying any pointer. Do not commit
   production databases or credentials to Git.
3. Verify candidate manifest/files, then copy its inventoried source files and
   CODE_SHA256.json into the NEW release directory, with create-new/no-overwrite
   semantics. Preserve the existing release. Reject unknown package files and
   partial copies. Verify all copied bytes against the frozen inventory.
4. Rebind only APCD_GPU_V2_SERIAL_CONTROLLER to the prepared
   CANDIDATE_DISABLED_TASK.xml, after validating its baseline XML pin. Its only
   planned diff is the release path in Arguments. Interpreter/cwd/account remain
   unchanged; Enabled=false, demand=false, zero triggers. The corresponding
   future registration operation is:

```powershell
Register-ScheduledTask -TaskName 'APCD_GPU_V2_SERIAL_CONTROLLER' -Xml ([IO.File]::ReadAllText("$r\CANDIDATE_DISABLED_TASK.xml")) -Force | Out-Null
```

5. Atomically update only audited installation-pointer/code-inventory metadata
   to this new directory/source/inventory identity. Keep Science binding DENY,
   no profiles/Admission and Controller Disabled. Preserve ACLs; any identity/
   ACL/profile enrollment is a separately approved, exact before/after operation.
6. Validate installed module origins and inventory, issuer check/default DENY,
   real contract compatibility with non-production fixtures, Disabled task XML,
   empty slot, unchanged science/execution counts, bindings and ACLs. Do not
   call Registry/drain against production merely to smoke-test imports. Do not
   run old unparameterized installers or make generated fixture authority live.

BASELINE_DISABLED_TASK.xml and CANDIDATE_DISABLED_TASK.xml are generated/staged
only; DISABLED_BINDING_DIFF.json records their exact SHA and changed argument.
The current platform pin is 575f3e853f3799d5db62574f73d21e69f7f871f5fe5a9ceb158e14beaad19e09.
An approved role/profile enrollment changes this pin and requires a newly
generated matching Disabled task binding; never use this old XML after drift.

## Rollback boundary

Rollback was NOT executed. On a patch error retain Disabled/DENY first. After
confirming no entry/owner/state change, restore only backed-up pointer metadata
and the saved Disabled task action, and verify the old immutable inventory.
The baseline inventory is ea92f62348f6d32c15bb46a992d1ca370a159c7f645808a472ae4013a6a756e1.
The future task restore operation uses the verified backup's Disabled XML:

```powershell
# Only under separately approved rollback authority, with the backup pin verified:
Register-ScheduledTask -TaskName 'APCD_GPU_V2_SERIAL_CONTROLLER' -Xml ([IO.File]::ReadAllText($VerifiedBackupTaskXml)) -Force | Out-Null
```

Never restore a database snapshot over an advanced ledger, refund entry, remove
receipts/truth, enable a legacy task, weaken ACLs, or delete an immutable release.
If rollback safety cannot be proven, stay Disabled/DENY and preserve evidence.

## Then, separately: formal issuance and entry

After actual approved role/profile enrollment and installed code verification,
Science Owner supplies a genuine protected manifest/OwnerIntent and invokes
check -> issue -> verify (or exact-input recover). GPU Owner registers PAUSED.
User/Chat separately authorizes actual entry, with a fresh resource/license and
fencing gate. Existing two-entry budget stays 2; A1 first, then accepted/reconciled
truth/labels and slot release before A2. DOE56 remains HOLD. No step here grants
actual install, credentials, Admission or scientific start authorization.
