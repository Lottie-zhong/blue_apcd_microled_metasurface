import argparse,json
from pathlib import Path
from np_k6_p1d_contract_v1 import candidate
def main():
 p=argparse.ArgumentParser();p.add_argument('--setup-only',action='store_true');p.add_argument('--extract-only',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--no-rerun-completed',action='store_true');p.add_argument('--candidate-id');p.add_argument('--candidate-ids',nargs='*');p.add_argument('--polarization',default='x');p.add_argument('--output-root');p.add_argument('--runtime-root');a=p.parse_args();ids=([a.candidate_id]if a.candidate_id else a.candidate_ids or []);[candidate(x)for x in ids];assert a.polarization=='x';assert a.setup_only;print(json.dumps({'solver_run_count_this_thread':0,'setup_only':True,'candidate_ids':ids}))
if __name__=='__main__':main()
