"""Read-only scientific metadata report. No FSP/H5/NPZ open or response export."""
import argparse,json,sqlite3,sys,time,subprocess,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apcd_gpu_v2.v3 import V3Config,morning_report
from apcd_gpu_v2.serial import replace_json

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 cfg=V3Config.model_validate_json(Path(a.config).read_text())
 with sqlite3.connect('file:'+str(Path(cfg.runtime_root)/'ledger.sqlite3')+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  snapshot=dict(slot=dict(db.execute('select token from slot where id=1').fetchone()),tasks=[dict(x) for x in db.execute('select case_id,state from tasks')])
 script="$s=New-Object -ComObject Schedule.Service;$s.Connect();$t=$s.GetFolder('\\').GetTask('APCD_GPU_V2_SERIAL_CONTROLLER');@{enabled=$t.Enabled;state=$t.State;demand_start=$t.Definition.Settings.AllowDemandStart;last_task_result=$t.LastTaskResult}|ConvertTo-Json"
 proc=subprocess.run(['powershell','-NoProfile','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],capture_output=True,text=True,check=True,timeout=30)
 snapshot['controller']=json.loads(proc.stdout)
 report=morning_report(cfg,snapshot)
 # Only the approved public metadata directory is an output destination.
 expected=Path(cfg.v3_data_root)/'V3_AUDIT_METADATA'
 target=Path(a.output).resolve()
 if expected.resolve() not in target.parents:raise RuntimeError('MORNING_OUTPUT_BOUNDARY')
 replace_json(target,report)
if __name__=='__main__':main()
