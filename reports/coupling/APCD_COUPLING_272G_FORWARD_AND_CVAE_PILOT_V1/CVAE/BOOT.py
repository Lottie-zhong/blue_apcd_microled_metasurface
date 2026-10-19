import sys,runpy
f=open('D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1\\reports\\coupling\\APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1\\CVAE\\worker.log','a',buffering=1,encoding='utf-8');sys.stdout=f;sys.stderr=f
print('BOOT',flush=True)
runpy.run_path('D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1\\reports\\coupling\\APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1\\CVAE\\TRAIN.py',run_name='__main__')
