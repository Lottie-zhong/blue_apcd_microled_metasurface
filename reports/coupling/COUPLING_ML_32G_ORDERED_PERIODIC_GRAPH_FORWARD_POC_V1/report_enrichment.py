from pathlib import Path
import json,csv,hashlib,subprocess
root=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
name='COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1'
out=root/'reports'/'coupling'/name
read=lambda n:json.loads((out/n).read_text(encoding='utf-8'))
r=read('results.json');p=read('protocol.json');t=read('pretraining_tests.json');a=read('audit.json')
def f(x):return f'{float(x):.6g}'
lines=['','## Supplement: seed, oracle, tail and training diagnostics','',
'Values below are generated only from persisted results.json, seed_metrics, h2_reconstruction.csv and pretraining_tests.json; no metrics were recomputed and no model or solver was run.','',
'| Arm | seed-state median std | routing Pearson | P_scale Pearson | oracle-aligned state median | oracle common-phase SSE share median |','|---|---:|---:|---:|---:|---:|']
for label in ['G0','C0','HISTORICAL_FULL']:
 x=r['arms'][label];s=x['summary'];lines.append(f"| {label} | {f(x['seed_state_median_std'])} | {f(x['routing_pearson'])} | {f(x['pscale_pearson'])} | {f(s['oracle_common_phase_aligned_state']['median'])} | {f(s['oracle_common_phase_explained_sse_fraction']['median'])} |")
lines+=['','Per-seed medians (state / routing / truth-weighted absolute phase / truth-weighted relative phase):','']
for label in ['G0','C0','HISTORICAL_FULL']:
 for seed,v in r['arms'][label]['per_seed'].items():
  m=v['metrics'];lines.append(f"- {label} seed {seed}: {f(m['state']['median'])} / {f(m['routing']['median'])} / {f(m['phase_weighted_rmse_rad']['median'])} rad / {f(m['relative_phase_truth_weighted_rmse_rad']['median'])} rad.")
lines+=['','Focused tail P_scale and thresholded-relative medians (values are per geometry over the complete 21-wavelength spectrum):','']
for gid,arms in r['tail_attribution'].items():
 g=arms['G0'];c=arms['C0'];lines.append(f"- {gid}: P_scale G0/C0 {f(g['pscale'])}/{f(c['pscale'])}; thresholded-relative {f(g['thresholded_relative'])}/{f(c['thresholded_relative'])}; routing {f(g['routing'])}/{f(c['routing'])}.")
tr=r['training_vs_heldout'];lines.append(f"- Final-fit standardized latent MSE median/q95/worst: {f(tr['G0_final_fit_standardized_latent_mse']['median'])}/{f(tr['G0_final_fit_standardized_latent_mse']['q95'])}/{f(tr['G0_final_fit_standardized_latent_mse']['worst'])}. G0 in-sample state entries repeat across outer fits and are descriptive only.")
lines+=['','The three message rounds define the model receptive field; they do not assert that physical coupling is limited to immediate neighbors. The oracle common-phase values use held-out truth and remain diagnostic only. Prediction-dependent phase weighting also changes when amplitudes change.','']
report=out/f'{name}.md';base=report.read_text(encoding='utf-8').replace('aperiodic graph','ordered periodic graph')
report.write_text(base+'\n'+'\n'.join(lines),encoding='utf-8')
status=subprocess.run(['git','-C',str(root),'status','--short','--untracked-files=all'],capture_output=True,text=True,check=True).stdout.splitlines()
paths=sorted(x[3:].replace('\\','/') for x in status if x[3:].replace('\\','/').startswith('reports/coupling/'+name+'/'))
script=out/'report_enrichment.py'
a['report_enrichment']={'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'metrics_recomputed':False,'source':'persisted results.json, pretraining_tests.json, h2_reconstruction.csv','exact_precommit_allowlist':paths,'precommit_head':p['start_head'],'branch':p['branch'],'preexisting_worktree_status_excluding_task':p['preexisting_worktree_status_excluding_this_task']}
(out/'audit.json').write_text(json.dumps(a,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
hashes={str(x.relative_to(root)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(out.rglob('*')) if x.is_file() and x.name!='artifact_hashes.json'}
(out/'artifact_hashes.json').write_text(json.dumps(hashes,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
print('REPORT_SUPPLEMENT',len(paths),len(hashes),'metrics_recomputed=false')
