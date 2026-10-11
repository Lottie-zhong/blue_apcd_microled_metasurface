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
    parser.add_argument('--config')
    parser.add_argument('--plan')
    parser.add_argument('--plan-sha256')
    parser.add_argument('--requests')
    args=parser.parse_args()
    if any(k.startswith('APCD_V2_') for k in os.environ):raise ValueError('ENVIRONMENT_OVERRIDE_FORBIDDEN')
    if args.plan:
        if args.config or args.requests or not args.plan_sha256:raise ValueError('EXCLUSIVE_PINNED_PLAN_ARGUMENTS_REQUIRED')
        from apcd_gpu_v2.v3_plan import Plan,run_plan
        from apcd_gpu_v2.serial import Pin
        plan=Plan.model_validate(Pin(path=args.plan,sha256=args.plan_sha256).read())
        run_plan(plan);return
    if not args.config or not args.requests:raise ValueError('CONFIG_AND_REQUESTS_REQUIRED')
    document=json.loads(Path(args.config).read_text(encoding='utf-8'),object_pairs_hook=unique)
    if document.get('schema_version')=='APCD_V2_REGISTERED_V3_SERIAL_V1':
        from apcd_gpu_v2.v3 import V3Config,V3Request
        config=V3Config.model_validate_json(json.dumps(document));request_type=V3Request
    else:
        config=SerialConfig.model_validate_json(json.dumps(document));request_type=SerialRequest
    if config.mode!='PRODUCTION_GPU':raise ValueError('FORMAL_CONTROLLER_REQUIRES_PRODUCTION_GPU')
    # The reviewed V2 config owns the resource; a stale Legacy environment cannot govern V2.
    os.environ['APCD_GPU_RESOURCE_NAME']=config.gpu_resource
    requests=[request_type.model_validate_json(json.dumps(v)) for v in json.loads(Path(args.requests).read_text(encoding='utf-8'))]
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
