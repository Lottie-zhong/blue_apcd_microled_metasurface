"""One durable controller entry; Scheduler starts it and never decides science entry."""
import argparse
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apcd_gpu_v2.general import Registry, Pin, load_platform


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--platform',required=True)
    parser.add_argument('--platform-sha256',required=True)
    args=parser.parse_args()
    if any(k.startswith('APCD_V2_') for k in os.environ):raise ValueError('ENVIRONMENT_OVERRIDE_FORBIDDEN')
    platform=load_platform(Pin(path=args.platform,sha256=args.platform_sha256))
    if platform.mode!='PRODUCTION_GPU':raise ValueError('FORMAL_CONTROLLER_REQUIRES_PRODUCTION_GPU')
    os.environ['APCD_GPU_RESOURCE_NAME']=platform.gpu_resource
    root=Path(platform.runtime_root)
    with (root/'controller.log').open('a',encoding='utf-8',buffering=1) as stream:
        try:
            stream.write('V21_CONTROLLER_START '+platform.sha256+'\n')
            Registry(platform).drain()
            stream.write('V21_CONTROLLER_IDLE_OR_COMPLETED\n')
        except BaseException:
            stream.write(traceback.format_exc())
            raise
        finally:
            stream.flush();os.fsync(stream.fileno())


if __name__=='__main__':main()
