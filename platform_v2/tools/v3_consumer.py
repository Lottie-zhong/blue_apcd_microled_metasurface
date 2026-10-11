"""Custodian broker for ordinary development workflows; actual child is non-admin."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apcd_gpu_v2.v3_identity import run_consumer
ROOT=Path('D:/apcd_runtime/gpu_platform_v2_serial_production_v1/v3_data')
def main():
 p=argparse.ArgumentParser();p.add_argument('--script',required=True);p.add_argument('args',nargs='*');a=p.parse_args()
 script=Path(a.script).resolve()
 if (ROOT/'CONSUMER_CODE').resolve() not in script.parents:raise RuntimeError('CONTROLLED_CONSUMER_CODE_REQUIRED')
 result=run_consumer(ROOT/'PRODUCTION_CUSTODIAN_PRIVATE/consumer_credential.dpapi',sys.executable,[str(script)]+a.args,ROOT/'CONSUMER_SCRATCH',timeout=3600)
 print(json.dumps(result));raise SystemExit(result['exitcode'])
if __name__=='__main__':main()
