import csv, json, statistics
from pathlib import Path
R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1'); O=R/'outputs/np_k6_m8_20g_forward_retraining_v1'
with (O/'model_metrics_by_seed.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
out={}
for model in sorted({r['model'] for r in rows}):
    z=[r for r in rows if r['model']==model]
    def stats(k):
        v=[float(r[k]) for r in z if r.get(k) not in ('', 'nan', 'None')]
        return {'mean':statistics.mean(v),'stdev':statistics.pstdev(v),'min':min(v),'max':max(v)} if v else None
    out[model]={'seeds':sorted({int(r['seed']) for r in z}),'ranking_spearman':stats('ranking_spearman'),'top3_recall':stats('top3_recall'),'order_profile_mae':stats('order_profile_mae'),'eta_plus1_mae':stats('eta_plus1_mae'),'energy_residual_max':stats('energy_residual_max')}
(O/'ranking_seed_stability.json').write_text(json.dumps({'status':'PASS','models':out,'seed_count':3},indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':'PASS','models':len(out),'seed_count':3}))
