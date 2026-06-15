from __future__ import annotations
import argparse,importlib.util
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
RUNNER_2A=REPO_ROOT/'scripts/stage11_lp_apcd_run_h500_dimer_fdtd_stage11_2a.py'
OUT_DIR=REPO_ROOT/'outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull'
PLAN=OUT_DIR/'h500_dimer_240_fine_pull_plan_stage11_2e.csv'; RESULT=OUT_DIR/'h500_dimer_240_fine_pull_fdtd_results_stage11_2e.csv'; SUMMARY=OUT_DIR/'h500_dimer_240_fine_pull_fdtd_summary_stage11_2e.md'; FDTD_DIR=OUT_DIR/'fdtd_h500_dimer_240_fine_pull'
def load_runner():
    spec=importlib.util.spec_from_file_location('stage11_2a_runner',RUNNER_2A); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def map_row(r): return {**r,'bin_deg':r['target_actual_bin_deg'],'static_output_phase_deg':r['target_actual_bin_deg'],'static_predicted_ratio':'','static_phase_error_deg':'','static_target_x_power':'','static_leak_y_power':''}
def write_summary(rows,dry=False):
    ok=[r for r in rows if r.get('fdtd_status')=='ok']; failed=[r for r in rows if r.get('fdtd_status')=='failed']
    lines=['# Stage11-2E H500 240 Fine Pull FDTD Summary','',f"mode = {'dry_run_no_lumerical' if dry else 'real_h500_240_fine_pull_fdtd'}",f'result_count = {len(rows)}',f'success = {len(ok)}',f'failed = {len(failed)}','skipped = 0','','Only H500 dimer x/y normal-incidence FDTD. No K=6, no H600/H700.']
    SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--plan',default=str(PLAN)); ap.add_argument('--runtime',default='configs/runtime.yaml'); ap.add_argument('--max-cases',type=int,default=36); ap.add_argument('--dry-run',action='store_true'); args=ap.parse_args()
    mod=load_runner(); mod.FDTD_DIR=FDTD_DIR; mod.RESULT_CSV=RESULT; mod.SUMMARY_MD=SUMMARY
    rows=[map_row(r) for r in mod.read_csv(Path(args.plan)) if r.get('geometry_legal')=='true'][:args.max_cases]
    print(f'selected_legal_240_fine_pull_count={len(rows)}')
    for r in rows[:min(12,len(rows))]: print(f"case={r['dimer_case_id']} target={r['bin_deg']} placement={r['placement_type']} swap={r.get('swap_order','')} gap={r.get('gap_nm','')} offset={r.get('local_offset_nm','')} x/y")
    if args.dry_run:
        dry=[{**{k:r.get(k,'') for k in mod.RESULT_FIELDS},'fdtd_status':'dry_run'} for r in rows]; write_summary(dry,True); return 0
    existing=mod.read_csv(RESULT) if RESULT.exists() else []; done={r.get('dimer_case_id') for r in existing if r.get('fdtd_status')=='ok'}; results=list(existing)
    runtime=mod.load_runtime_config(args.runtime); lumapi=mod.import_lumapi(runtime)
    for r in rows:
        cid=r['dimer_case_id']
        if cid in done: print('skip_existing='+cid); continue
        print(f'running={cid} x'); x=mod.run_one(lumapi,runtime,r,'x')
        print(f'running={cid} y'); y=mod.run_one(lumapi,runtime,r,'y')
        c=mod.combine(r,x,y); results.append(c); mod.write_csv(RESULT,results,mod.RESULT_FIELDS); write_summary(results,False); print(f"done={cid} status={c['fdtd_status']}")
    print(f'result_csv={RESULT}'); print(f"success={sum(1 for r in results if r['fdtd_status']=='ok')}"); print(f"failed={sum(1 for r in results if r['fdtd_status']=='failed')}"); print('skipped=0')
if __name__=='__main__': main()
