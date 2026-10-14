# Bounded GPU resource closeout

Sample: 2026-10-14T11:00:16.917357+00:00; lineage follow-up: 2026-10-14T11:19:26.092028+00:00.
RTX 3080: NVIDIA GeForce RTX 3080, 610.60, 1, 1932, 10240. NVIDIA enumerated 29
contexts, with WDDM per-process memory N/A. Three sets of 1561 WDDM counters had
no observed active engine. This is bounded inactivity, not a reservation.

No fdtd-engine was observed. Eight fdtd-solutions images point to historical NP/
surrogate working directories; none appeared in NVIDIA GPU contexts. They are
GUI/API image observations, not evidence of current FDTD GPU science. License
and job service images are not scientific engine launch evidence.

EDT PIDs 43840/43460 have stable creation times, the exact v251 AnsysEM image,
another project's cwd, and only ansyscl license-client descendants. They are GPU
contexts but no activity or science engine was observed. Command/GUI role and
an exclusive reservation are not fully proven; this audit does not call them
active solvers merely because they are Ansys processes.

PID 18936 is in a stable cmd -> Python -> SSH 40664 lineage, with only that SSH
descendant. Neither PID is a GPU context; no local science descendant or V2 slot
ownership was observed. Historical stdin business purpose remains unknown and
was not investigated. It is not by itself a reason to block this offline work.

Other GPU contexts include desktop Office/Photos/remote/security applications.
The existing qualified-idle catalog does not cover every such image. The actual
live gate can still reject an unattributed context, irrespective of memory N/A
or utilization 0. CURRENT_GPU_CONFLICT=UNKNOWN; LIVE_GPU_RESOURCE_READY=false.
No confirmed active scientific compute conflict was established by this sample.

No stdin, argv, environment, credentials or license-context payload was read in
the resource investigation. No handle/process was closed, suspended, killed or
released. The composed historical argv-collecting gate was not invoked here;
do not equate this metadata audit with that gate's live PASS. Offline regression
stubbed environmental foreign census to avoid sensitive collection; dedicated
resource-mechanism negative tests used explicit isolated inputs.

Future fresh pre-entry must run under the existing single Controller/slot lock:
reverify formal Admission/profile/case budget/no-replay and current DOE56 HOLD;
verify PID/create_time, owner/fencing, current GPU engine/context evidence and
resource gate; perform the approved exact-case/license precheck; then revalidate
at the native prelaunch fence before launch-once. A sample is not permanent.
The existing native_preflight reports API_LICENSE_AVAILABLE separately from
GPU_ENGINE_LICENSE_NOT_TESTED. No new license checkout/native session occurred
here, and licensing service presence is not feature availability proof.

Minimum remaining resource action: the owners/user must establish a controlled
GPU window or provide approved non-sensitive qualification for the residual
contexts, then GPU Owner must obtain a fresh passing gate adjacent to launch.
Do not arbitrarily close GUI work or ignore contexts. Arbitrary same-user/admin
manual launching cannot be excluded by an application-level snapshot or source
retirement; it remains outside the supported-automatic-ingress trust boundary.
