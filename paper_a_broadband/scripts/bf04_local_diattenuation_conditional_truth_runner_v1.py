from __future__ import annotations

import os
import runpy
import sys


os.environ["BF04_RUN_SCOPE"] = "conditional"
sys.argv[0] = r"D:\project\worktrees\blue_apcd_paper_a_lp_cp_broadband_v1\paper_a_broadband\scripts\bf04_local_diattenuation_conditional_truth_runner_v1.py"
runpy.run_path(
    r"D:\project\worktrees\blue_apcd_paper_a_lp_cp_broadband_v1\paper_a_broadband\scripts\bf04_local_diattenuation_truth_runner_v1.py",
    run_name="__main__",
)
