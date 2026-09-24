# Shared V3 GPU Resource Resolution V1

The resolver queries the installed FDTD resource table and accepts only active GPU resources with a positive process count. Exactly one candidate is required; zero or multiple candidates block pre-entry unless an explicit frozen resource name identifies one candidate. Selection is independent of case, campaign, branch, and display names.

Every attempt freezes the exact resource name and device provenance before launch. The irreversible scientific boundary is `GPU_ENGINE_ENTRY_CONFIRMED`, supported by an observed `fdtd-engine-msmpi.exe -gpu` process or authoritative solver-start evidence. A resource-name rejection before engine creation is a pre-entry failure and does not weaken the no-replay rule after a confirmed engine entry.

The V2 historical attempt remains unchanged and is classified as `GPU_RESOURCE_NAME_RESOLUTION_FAILURE_BEFORE_ENGINE_ENTRY`; its conservative no-replay ledger is retained as historical evidence.
