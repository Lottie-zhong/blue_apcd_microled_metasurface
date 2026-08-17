from __future__ import annotations

import runpy
import sys


# Production Task Scheduler execution is artifact-only: no routine 600 s
# stdout chatter.  Terminal/anomaly artifacts remain authoritative.
sys.argv = ["np_k6_m8a_durable_monitor_v2.py", "--quiet"]
runpy.run_path(
    r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1/scripts/np_k6_m8a_durable_monitor_v2.py",
    run_name="__main__",
)
