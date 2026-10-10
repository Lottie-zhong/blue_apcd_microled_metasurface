"""Single durable controller process; Scheduler may launch this, never decide entry."""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apcd_gpu_v2.serial import SerialConfig,SerialRequest,ProductionNativeBackend,NativeTruthValidator,controller


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('DUPLICATE_CONFIG_KEY:'+key)
        result[key]=value
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--requests',required=True)
    args=parser.parse_args()
    if any(k.startswith('APCD_V2_') for k in os.environ):raise ValueError('ENVIRONMENT_OVERRIDE_FORBIDDEN')
    document=json.loads(Path(args.config).read_text(encoding='utf-8'),object_pairs_hook=unique)
    config=SerialConfig.model_validate_json(json.dumps(document))
    if config.mode!='PRODUCTION_GPU':raise ValueError('FORMAL_CONTROLLER_REQUIRES_PRODUCTION_GPU')
    # The reviewed V2 config owns the resource; a stale Legacy environment cannot govern V2.
    os.environ['APCD_GPU_RESOURCE_NAME']=config.gpu_resource
    requests=[SerialRequest.model_validate_json(json.dumps(v)) for v in json.loads(Path(args.requests).read_text(encoding='utf-8'))]
    root=Path(config.runtime_root);root.mkdir(parents=True,exist_ok=True)
    with (root/'controller.log').open('a',encoding='utf-8',buffering=1) as stream:
        try:
            stream.write('CONTROLLER_START '+config.sha256+'\n')
            controller(config,requests,ProductionNativeBackend(),NativeTruthValidator(config))
            stream.write('CONTROLLER_COMPLETED\n')
        except BaseException:
            stream.write(traceback.format_exc());stream.flush();os.fsync(stream.fileno())
            raise
        finally:
            stream.flush();os.fsync(stream.fileno())


if __name__=='__main__':main()
