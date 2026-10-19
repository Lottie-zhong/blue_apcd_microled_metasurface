from pathlib import Path
import sys,runpy,traceback
D=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1')
sys.stdout=open(D/'WORKER_STDOUT.log','a',encoding='utf-8',buffering=1);sys.stderr=open(D/'WORKER_STDERR.log','a',encoding='utf-8',buffering=1)
try:runpy.run_path(str(D/'PREPARE_AND_TRAIN.py'),run_name='__main__')
except Exception:traceback.print_exc();raise
