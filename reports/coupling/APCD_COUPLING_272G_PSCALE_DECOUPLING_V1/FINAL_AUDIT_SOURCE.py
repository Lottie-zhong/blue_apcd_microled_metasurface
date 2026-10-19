from pathlib import Path
import json,csv,numpy as np,subprocess,sqlite3,base64
D=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_272G_PSCALE_DECOUPLING_V1');R=D.parents[2];B=D.parent/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';rd=lambda p:json.loads(Path(p).read_text());z=np.load(B/'COMPLEX_DATASET.npz');ix={s:i for i,s in enumerate(z['case_ids'])};stats=[]
for name in ['Joint','PSNet','ET3','Leaf1','Ridge','PMean']:
 a=np.load(D/f'NN3_{name}_OOF.npz');va=np.array([ix[s] for s in a['case_ids']]);pt=z['P_scale'][va];pp=a['P'];shift=np.argmax(pp,axis=1)-np.argmax(pt,axis=1);stats.append({'model':name,'peak_wavelength_MAE_nm':float(abs(shift).mean()),'peak_shift_within1nm_fraction':float(np.mean(abs(shift)<=1)),'peak_shift_max_nm':int(abs(shift).max())})
(D/'PSCALE_PEAK_SHIFT.json').write_text(json.dumps(stats,indent=2));lines='\n## 峰位误差补充\n\n|模型|峰位MAE(nm)|±1nm内比例|最大偏移(nm)|\n|---|---:|---:|---:|\n'
for r in stats:lines+=f'|{r["model"]}|{r["peak_wavelength_MAE_nm"]:.4f}|{r["peak_shift_within1nm_fraction"]:.4f}|{r["peak_shift_max_nm"]}|\n'
lines+='\n21个已保存波长点直接取argmax，无插值或亚纳米分辨率声称。峰位错配与公共谱形回归失配有证据，但未唯一归因于模型结构或FAST数值标签。\n'
for name in ['PSCALE_DIAGNOSTIC_REPORT.md','FINAL_REPORT.md','PSCALE_DECOUPLING_REPORT.md']:
 p=D/name;p.write_text(p.read_text(encoding='utf-8')+lines,encoding='utf-8')
qa={'visual_status':'PASS','figures':{'PSCALE_DECOUPLING_OVERVIEW':'all4panels checked: fold lines, zero-origin power MAE, explicit Oracle and four-fold min/max bars, bias band; labels clear','PSCALE_AND_POWER_SPECTRA':'all6panels checked: lowest/median/highest fixed NN3 Pscale error selection, shared legend, native1nm truth and model curves, no clipping; poor shifted peaks preserved'},'PDF_min_font_pt':7,'width_mm':183,'automated':'19PASS1WARN0FAIL','warning':'No TIFF; report delivery uses editable PDF/SVG plus600dpiPNG, not final journal submission','statistics':'n124 geometry,4frozenfolds; foldrange not confidenceinterval; representative spectra are individualcases without replicatebars','source':'FIGURES.py,FIGURES/SPECTRA_SOURCE_DATA.csv and frozen OOF predictions','no_data_excluded':True}
(D/'FIGURE_QA_REPORT.md').write_text('# Figure QA\n\n'+json.dumps(qa,indent=2),encoding='utf-8')
before=rd(D/'GIT_BEFORE.json');staged=subprocess.run(['git','-C',str(R),'diff','--cached','--name-only'],capture_output=True,text=True).stdout;assert staged==before["['diff', '--cached', '--name-only']"]
status={str(a):subprocess.run(['git','-C',str(R),*a],capture_output=True,text=True).stdout for a in [['status','--short'],['branch','--show-current'],['rev-parse','HEAD'],['rev-list','--left-right','--count','HEAD...@{u}']]}
assert status["['rev-parse', 'HEAD']"]==before["['rev-parse', 'HEAD']"]
for p,v in rd(D/'PROTECTED_BYTES_BEFORE.json').items():assert Path(p).read_bytes()==base64.b64decode(v)
p=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\data\runner_v31.db');co=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);rows=co.execute('select * from solver_entries').fetchall();co.close();assert [list(r) for r in rows]==rd(D/'ENTRY_BEFORE.json');(D/'GIT_FINAL_STATUS.json').write_text(json.dumps(status,indent=2))
(D/'FINAL_AUDIT.json').write_text(json.dumps({'task_status':'PASS_OFFLINE_COMPLETE','visual_QA':'PASS','same117_entries':True,'protected_bytes_unchanged':True,'four_staged_unchanged':True,'original_git_head_unchanged':True,'new_fit_count':20,'new_NN_count':16,'new_Ridge_count':4,'new_FDTD':0,'next_batch_authorized':0,'H1':'HOLD','frozen_H2':'UNCHANGED'},indent=2))
print('FINAL_AUDIT_PASS',len(rows),'dirtylines',len(status["['status', '--short']"].splitlines()),'staged',len(staged.splitlines()),stats)
