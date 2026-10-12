# V2.1 CLI (candidate only)

Use the formal interpreter and a SHA-pinned, installer-owned platform config.
No CLI creates a science admission or budget. `submit` is paused by default.

```powershell
& $python $general_runner --platform $config --platform-sha256 $configSHA submit --manifest $manifest --manifest-sha256 $manifestSHA --admission $admission --admission-sha256 $admissionSHA
& $python $general_runner --platform $config --platform-sha256 $configSHA status
& $python $general_runner --platform $config --platform-sha256 $configSHA pause --batch $batch
& $python $general_runner --platform $config --platform-sha256 $configSHA resume --batch $batch
```

After approved migration and an explicit Chat start instruction, wake the one existing task.
Its Action becomes `serial_controller.py --platform <canonical config> --platform-sha256 <SHA>`.
No per-batch Scheduler. No automatic daily trigger. Controller exits after current eligible queue.
`pause` never terminates an admitted solver. `resume` checks science control and cannot lift HOLD.
At a race after durable entry, retain the consumed/uncertain entry and stop; never refund.
Unknown profiles, extra JSON keys, arbitrary script paths, mismatched hashes and duplicate case IDs refuse.
Current examples are intentionally DENY/draft, not runnable science releases.

Manifest SHA is the canonical digest of normalized JSON excluding `manifest_sha`; admission separately pins exact manifest bytes.
All contract/source file pins use raw file SHA256. If scientific authority uses a canonical contract digest,
that digest must be explicitly mapped by its independently certified source acceptance/profile; do not silently reinterpret it.
The generic native-LOAD acceptance envelope binds source FSP, raw physics SHA, mesh, simulation time and shutoff.
The Coupling ledger is never created by this CLI; the Scientific Owner must provide the compatible existing authority.
