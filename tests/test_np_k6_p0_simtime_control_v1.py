import json
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); STAGE=ROOT/'outputs/np_k6_p0_simulation_time_extension_control_v1'; CASE='RUN3C_P_PILOT_HF_SIMTIME_2PS_CONTROL_V1'; CDIR=STAGE/'cases'/CASE
def test_setup_single_variable_and_zero_before_run_artifacts():
 c=json.loads((CDIR/'setup_contract.json').read_text()); a=json.loads((CDIR/'setup_readback_audit.json').read_text()); l=json.loads((CDIR/'attempt_ledger.json').read_text())
 assert c['simulation_time_s']==2e-12; assert c['auto_shutoff_min']==1e-5; assert c['unexpected_differences']==[]; assert a['single_variable_pass']; assert c['setup_only']
 assert l['entered'] is True or l['entered'] is False
def test_old_stage_immutable_post_sha():
 p=ROOT/'outputs/np_k6_hf_p0_label_generator_recovery_v1/runtime_runs/RUN3C_P_PILOT_HF_V1/attempt_001/RUN3C_P_PILOT_HF_V1_attempt_001_post.fsp'; assert p.exists(); import hashlib
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 assert h.hexdigest()=='d45634ef54359c80cd38f88d6353845cf60315c4cac35c5381ee1a9dd2c60b56'
