from pathlib import Path
import sys,json,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');sys.path.insert(0,str(R));O=R/'reports/coupling/APCD_COUPLING_V3_NUMERICAL_GATE_FAILURE_FORENSIC_V1';D=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1'
from scripts.coupling_ml.k6_v2_pipeline import h1
from scripts.coupling_ml.k6_v2_pipeline import v3_numerical_core as C
print('H1',h1.__file__)
L=json.loads((D/'v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json').read_text());out={}
for cid in L['entered_case_ids']:
 z=np.load(L['case_records'][cid]['evidence']['validation']['labels_artifact']['path']);c=z['C_hat_real']+1j*z['C_hat_imag'];ps=z['P_scale'];h=h1.reconstruct_h2(c,ps,h1.load_h2_decoder());print('KEYS',list(h));q=np.sqrt(1-(np.arange(-3,4)[None,:]*np.arange(440,461)[:,None]*1e-9/1740e-9)**2); eta=q*np.sum(abs(c)**2,axis=2); out[cid]={'independent_eta_vs_frozen_H2_max_abs':float(np.max(abs(eta-h['eta']))),'independent_absolute_vs_frozen_H2_max_abs':float(np.max(abs(eta*ps[:,None]-h['absolute_order']))),'H2_total_vs_P_scale_max_abs':float(np.max(abs(h['total_power']-ps))),'native_eta_vs_H2_max_abs':float(np.max(abs(z['eta']-h['eta'])))}
(O/'FROZEN_H2_INTERFACE_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
