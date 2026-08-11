import argparse, hashlib, json, subprocess, tempfile, os
from pathlib import Path
import torch

def sha_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def state_hash(sd):
    h=hashlib.sha256()
    for k in sorted(sd): h.update(k.encode()); h.update(sd[k].detach().cpu().numpy().tobytes())
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-dir',required=True); ap.add_argument('--repo',required=True); ap.add_argument('--runner',required=True); ap.add_argument('--code-commit',default=None); args=ap.parse_args()
    run=Path(args.run_dir); repo=Path(args.repo); runner=Path(args.runner); commit=args.code_commit or subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(); membership=sha_file(run/'formal_membership_and_split_registry.json'); schema=sha_file(run/'v3_input_schema_contract.json')
    repaired=[]
    for result_path in sorted(run.glob('fits/*/fit_result.json')):
        result=json.loads(result_path.read_text()); fit_dir=result_path.parent; ck_path=fit_dir/'best.pt'; ck=torch.load(ck_path,map_location='cpu',weights_only=False); before=state_hash(ck['model']); provenance=dict(ck.get('provenance') or {}); provenance.update({'code_commit':commit,'runner_script_sha256':sha_file(runner),'development_membership_sha256':membership,'schema_sha256':schema,'checkpoint_identity':result['fit_key'],'resume_history':[],'execution_state':'completed'}); ck['provenance']=provenance
        tmp=ck_path.with_suffix('.pt.repair.tmp'); torch.save(ck,tmp); os.replace(tmp,ck_path); after=state_hash(torch.load(ck_path,map_location='cpu',weights_only=False)['model'])
        result.update({'code_commit':commit,'runner_script_sha256':sha_file(runner),'development_membership_sha256':membership,'schema_sha256':schema,'checkpoint_identity':result['fit_key'],'resume_history':[],'execution_state':'completed','model_parameter_sha256_before':before,'model_parameter_sha256_after':after,'checkpoint_sha256':sha_file(ck_path),'provenance_repaired_metadata_only':True}); result_path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding='utf-8'); repaired.append({'fit_key':result['fit_key'],'parameter_hash_before':before,'parameter_hash_after':after,'unchanged':before==after,'checkpoint_sha256':result['checkpoint_sha256']})
    audit={'status':'PASS' if repaired and all(x['unchanged'] for x in repaired) else 'HARD_GATE_PROVENANCE_REPAIR','fit_count':len(repaired),'metadata_only':True,'code_commit':commit,'runner_script_sha256':sha_file(runner),'development_membership_sha256':membership,'repairs':repaired}; (run/'provenance_repair_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8'); print(json.dumps(audit))
if __name__=='__main__': main()

