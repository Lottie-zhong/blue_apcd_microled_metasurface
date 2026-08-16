import subprocess, sys
from pathlib import Path
R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
tests=['tests/test_np_k6_m5_fullk6_forward_v0.py','tests/test_np_k6_m5b_formulation_repair_v1.py','tests/test_np_k6_m7_16g_forward_retraining_v1.py','tests/test_np_k6_m7a_targeted_development_acquisition_design_v1.py','tests/test_np_k6_m8_20g_forward_retraining_v1.py','tests/test_m7a_closeout_source.py']
p=subprocess.run([sys.executable,'-m','pytest','-q',*tests],cwd=R,text=True,capture_output=True)
print(p.stdout); print(p.stderr); raise SystemExit(p.returncode)
