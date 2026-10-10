"""Read already durable terminal evidence. No solver, fit, release or ledger writes."""
from pathlib import Path
import json,hashlib,datetime
ROOT=Path('D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1')
OWNER=Path('D:/apcd_runtime/gpu_v2_remaining86_production_20261010_v1')
OUT=ROOT/'reports/coupling/APCD_K6_V2_REMAINING_DEVELOPMENT_PRODUCTION_FINAL_V1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def main():
 if not (OWNER/'FINAL_SUMMARY.json').is_file():raise RuntimeError('PRODUCTION_TERMINAL_NOT_AVAILABLE: do not fake completion or restart the running queue')
 summary=read(OWNER/'FINAL_SUMMARY.json');inv=read(OWNER/'FINAL_SHA_INVENTORY.json')
 assert all(sha(v['path'])==v['sha256'] for v in inv['files'])
 scientific=read(OWNER/'COUPLING_FINAL_SCIENTIFIC_AUDIT.json') if (OWNER/'COUPLING_FINAL_SCIENTIFIC_AUDIT.json').exists() else None
 terminal=read(OWNER/'TERMINAL_AUDIT.json') if (OWNER/'TERMINAL_AUDIT.json').exists() else None
 if summary['status']=='PASS':
  assert scientific and scientific['status']=='PASS' and scientific['complete'] and scientific['completed_new_count']==86
  assert terminal and terminal['verdict']=='PASS' and len(terminal['cases'])==86
  close=read(OWNER/'CLOSED_DISABLED_DENY_READBACK.json');assert close['scientific_release']=='DENY' and close['current_request_count']==0 and not close['task']['after']['enabled']
 OUT.mkdir(exist_ok=True)
 (OUT/'FINAL_OWNER_INPUT_PINS.json').write_text(json.dumps({'summary':{'path':str(OWNER/'FINAL_SUMMARY.json'),'sha256':sha(OWNER/'FINAL_SUMMARY.json')},'inventory':{'path':str(OWNER/'FINAL_SHA_INVENTORY.json'),'sha256':sha(OWNER/'FINAL_SHA_INVENTORY.json')},'verified_owner_files':len(inv['files'])},indent=2)+'\n',encoding='utf-8')
 rows=scientific['all128_status'] if scientific else []
 (OUT/'ALL128_FINAL_CASE_STATUS.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
 lines=['# APCD_K6_V2_REMAINING_DEVELOPMENT_PRODUCTION_FINAL_V1','',summary['status'],'',f"Read-only finalized: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",'','All128 statuses: ALL128_FINAL_CASE_STATUS.json; native timing/SHA table: owner REPORT.md and TERMINAL_AUDIT.json. No raw license context copied.']
 if scientific:lines+=['',json.dumps(scientific['counts']),'',f"New valid: {scientific['completed_new_count']}/86. All128 consumed budgets retain four historical no-truth failures. Confirmation sealed, replay0, fits0."]
 lines+=['','Formal ML readiness: a perfect batch yields124 new valid+32 old=156G, below the frozen160G pool. No replacement/replay or protocol amendment is granted here.','Same-run H2/native-grating consistency is not independent repeatability, cross-height verification or mesh convergence. InteractiveToken still requires logged-inDELL; SSH helper closure is verified, logout/reboot continuity is not.','',f"Owner report: {OWNER/'REPORT.md'}",f"Owner inventory: {OWNER/'FINAL_SHA_INVENTORY.json'}"]
 (OUT/'FINAL_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 (OUT/'CONTINUATION.md').write_text('# Terminal science review\n\nRead FINAL_REPORT.md, ALL128_FINAL_CASE_STATUS.json and FINAL_OWNER_INPUT_PINS.json. Owner terminal artifacts are SHA-verified. No confirmation or new fit authorized. Main Agent must independently inspect final Scheduler/slot/runtime and perform exact allowlist commit/push, preserving foreign staged files. Do not restart/replay consumed attempts.\n',encoding='utf-8')
 (OUT/'SHA_INVENTORY.json').write_text(json.dumps({'files':[{'path':str(p),'sha256':sha(p)} for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='SHA_INVENTORY.json'],'owner_inventory_sha256':sha(OWNER/'FINAL_SHA_INVENTORY.json')},indent=2)+'\n',encoding='utf-8')
 print('TERMINAL_REPORT_READY',OUT,summary['status'])
if __name__=='__main__':main()
