from __future__ import annotations
import argparse, importlib.util
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
RUNNER_2A=REPO_ROOT/'scripts'/'stage11_lp_apcd_run_h500_dimer_fdtd_stage11_2a.py'
OUT_DIR=REPO_ROOT/'outputs'/'blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin'
PATCH_PLAN=OUT_DIR/'h500_dimer_placement_patch_plan_stage11_2b.csv'; RESULT_CSV=OUT_DIR/'h500_dimer_placement_patch_fdtd_results_stage11_2b.csv'; SUMMARY_MD=OUT_DIR/'h500_dimer_placement_patch_fdtd_summary_stage11_2b.md'; FDTD_DIR=OUT_DIR/'fdtd_h500_dimer_placement_patch'
def load_runner_2a():
    spec=importlib.util.spec_from_file_location('stage11_2a_runner',RUNNER_2A); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def map_row(row): return {**row,'dimer_case_id':row['dimer_patch_id'],'bin_deg':row['target_actual_bin_deg'],'static_output_phase_deg':row['target_actual_bin_deg'],'static_predicted_ratio':'','static_phase_error_deg':'','static_target_x_power':'','static_leak_y_power':''}
def write_summary(rows,dry_run=False):
    ok=[r for r in rows if r.get('fdtd_status')=='ok']; failed=[r for r in rows if r.get('fdtd_status')=='failed']
    lines=['# Stage11-2B Revised H500 Dimer Placement Patch FDTD Summary','',f"mode = {'dry_run_no_lumerical' if dry_run else 'real_h500_dimer_placement_patch_fdtd'}",f'result_count = {len(rows)}',f'success = {len(ok)}',f'failed = {len(failed)}','skipped = 0','','Full Jones matrix components t_xx, t_yx, t_xy, t_yy are exported for revised projection-matrix diagnostics.','Evidence boundary: H500 dimer placement patch only. No K=6, no phase-gradient supercell, no H600/H700.']
    SUMMARY_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--plan',default=str(PATCH_PLAN)); ap.add_argument('--runtime',default='configs/runtime.yaml'); ap.add_argument('--max-cases',type=int,default=24); ap.add_argument('--dry-run',action='store_true'); args=ap.parse_args()
    mod=load_runner_2a(); mod.FDTD_DIR=FDTD_DIR; mod.RESULT_CSV=RESULT_CSV; mod.SUMMARY_MD=SUMMARY_MD
    rows=[map_row(r) for r in mod.read_csv(Path(args.plan)) if r.get('geometry_legal')=='true'][:args.max_cases]
    print(f'selected_legal_patch_count={len(rows)}')
    for row in rows[:min(12,len(rows))]: print(f"case={row['dimer_case_id']} target_actual_bin={row['bin_deg']} placement={row['placement_type']} swap={row.get('swap_order','')} gap={row.get('gap_nm','')} x/y")
    if args.dry_run:
        dry=[{**{k:r.get(k,'') for k in mod.RESULT_FIELDS},'fdtd_status':'dry_run'} for r in rows]; write_summary(dry,True); return 0
    runtime=mod.load_runtime_config(args.runtime); lumapi=mod.import_lumapi(runtime); results=[]
    for row in rows:
        print(f"running={row['dimer_case_id']} x"); x=mod.run_one(lumapi,runtime,row,'x')
        print(f"running={row['dimer_case_id']} y"); y=mod.run_one(lumapi,runtime,row,'y')
        c=mod.combine(row,x,y); results.append(c); mod.write_csv(RESULT_CSV,results,mod.RESULT_FIELDS); write_summary(results,False); print(f"done={row['dimer_case_id']} status={c['fdtd_status']}")
    print(f'result_csv={RESULT_CSV}'); print(f"success={sum(1 for r in results if r['fdtd_status']=='ok')}"); print(f"failed={sum(1 for r in results if r['fdtd_status']=='failed')}"); print('skipped=0')
if __name__=='__main__': main()
