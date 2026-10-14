"""One general user operation CLI; only serial_controller owns execution."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apcd_gpu_v2.general import Registry, Pin, load_platform, require_operator


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--platform',required=True)
    p.add_argument('--platform-sha256',required=True)
    sub=p.add_subparsers(dest='operation',required=True)
    submit=sub.add_parser('submit')
    for name in ['manifest','manifest-sha256','admission','admission-sha256']: submit.add_argument('--'+name,required=True)
    sub.add_parser('status')
    for name in ['pause','resume']:
        cmd=sub.add_parser(name);cmd.add_argument('--batch',required=True)
    a=p.parse_args()
    platform=load_platform(Pin(path=a.platform,sha256=a.platform_sha256))
    if a.operation!='status':require_operator(platform)
    registry=Registry(platform)
    if a.operation=='submit':
        result=registry.submit(Pin(path=a.manifest,sha256=a.manifest_sha256),Pin(path=a.admission,sha256=a.admission_sha256))
    elif a.operation in ['pause','resume']:
        registry.operate(a.batch,a.operation=='pause');result=registry.public_status()
    else:result=registry.public_status()
    print(json.dumps(result,ensure_ascii=True,sort_keys=True))


if __name__=='__main__':main()
