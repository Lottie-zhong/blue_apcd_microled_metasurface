from pathlib import Path
import sys,runpy
D=Path('D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1\\reports\\coupling\\APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1')
sys.stdout=open(D/'LOCAL_ABLATION_STDOUT.log','a',encoding='utf-8',buffering=1);sys.stderr=open(D/'LOCAL_ABLATION_STDERR.log','a',encoding='utf-8',buffering=1)
sys.argv=[str(D/'AL50_LOCAL_ABLATION.py'),'--stage','44']
runpy.run_path(str(D/'AL50_LOCAL_ABLATION.py'),run_name='__main__')
