from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'src'))
from apcd_coupling.comparison_engine import row_from_result, standalone_row, build_spacer_comparison

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--fixture-registry',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); args=ap.parse_args(); cfg=read(args.fixture_registry); baseline_path=ROOT/'outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1/results/result.json'; baseline_result=read(baseline_path); baseline_result['control_group']='B3'; baseline_result['interface_id']='SUPPORT_NONE'; baseline_result['spacer_nm']=0.0; baseline_result['total_sio2_separation_nm']=79.0; baseline_result['loss_or_residual']=baseline_result['power_closure']['residual_1_minus_R_minus_T']; baseline_result['theta_plus1']=baseline_result['theta_out_plus1_deg']; baseline=row_from_result(baseline_result,'B3_TEXTRA0'); spacer_rows=[]
 for item in cfg['controls']:
  result_path=ROOT/'outputs/coupling'/f"stage_a_s{item['spacer_nm']}_450nm_xpol_normal_v1/results/result.json"; result=read(result_path); result['result_path']=str(result_path.resolve()); spacer_rows.append(row_from_result(result,item['control_group']))
 ref_cfg=cfg['standalone_reference']; ref_path=Path(ref_cfg['path']); full=read(ref_path); ref=full['at_450_nm']; ref['plus1_angle_450_deg']=full.get('plus1_angle_450_deg'); standalone=standalone_row(ref,str(ref_path),ref_cfg['source_commit'],sha(ref_path)); artifact=build_spacer_comparison(spacer_rows,baseline,standalone); artifact['result_paths']={'B3':str(baseline_path.resolve()),**{row['control_group']:row['result_path'] for row in spacer_rows}}; artifact['baseline_result_sha256']=sha(baseline_path); args.output_dir.mkdir(parents=True,exist_ok=True); p=args.output_dir/'spacer_matrix.json'; p.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps({'path':str(p),'candidate_decision':artifact['candidate_decision'],'rows':[row['comparison_id'] for row in artifact['rows']]},indent=2))
if __name__=='__main__': main()
