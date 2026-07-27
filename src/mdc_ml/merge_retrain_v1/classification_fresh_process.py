from __future__ import annotations

import argparse, hashlib, json, os, tempfile
from pathlib import Path
import joblib
import numpy as np


def _safe(root: Path) -> None:
    root=root.resolve(); temp=Path(tempfile.gettempdir()).resolve()
    if os.path.commonpath([str(root).lower(),str(temp).lower()]) != str(temp).lower(): raise ValueError('FRESH_PROCESS_ROOT_MUST_BE_SYSTEM_TEMP')
    if 'worktrees' in str(root).lower() or 'merge_retrain' in str(root).lower(): raise ValueError('FRESH_PROCESS_FORBIDDEN_ROOT')


def sig(value: np.ndarray) -> str: return hashlib.sha256(np.ascontiguousarray(np.round(value,12)).tobytes()).hexdigest()


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--fixture-root',type=Path,required=True); p.add_argument('--fold-artifact',type=Path,required=True); p.add_argument('--input-npz',type=Path,required=True); p.add_argument('--expected-json',type=Path,required=True); p.add_argument('--result-json',type=Path,required=True); a=p.parse_args(); _safe(a.fixture_root)
    bundle=joblib.load(a.fold_artifact); X=np.load(a.input_npz)['X']; expected=json.loads(a.expected_json.read_text())
    scaler=bundle['scaler']; values=scaler.transform(X); material=tuple(range(0,125,5)); values[:,material]=X[:,material]
    raw=np.column_stack([m.predict_proba(values)[:,list(m.classes_).index(1)] if 1 in m.classes_ else np.zeros(len(X)) for m in bundle['models']])
    calibrated=np.column_stack([c.predict(raw[:,j]) if bundle['methods'][j]=='isotonic' else c.predict_proba(np.log(np.clip(raw[:,j],1e-6,1-1e-6)/np.clip(1-raw[:,j],1e-6,1-1e-6)).reshape(-1,1))[:,1] for j,c in enumerate(bundle['calibrators'])])
    labels=np.column_stack([calibrated[:,j]>=bundle['thresholds'][j]['threshold'] for j in range(4)]).astype(int)
    actual={'raw_probability_signature':sig(raw),'calibrated_probability_signature':sig(calibrated),'predicted_label_signature':sig(labels),'artifact_sha256':hashlib.sha256(a.fold_artifact.read_bytes()).hexdigest()}
    result={'worker_pid':os.getpid(),'parent_pid':expected['parent_pid'],'distinct_process':os.getpid()!=expected['parent_pid'],'fold_id':bundle['fold_id'],**actual,'expected_signatures':expected,'all_match':all(actual[k]==expected[k] for k in actual),'sealed_test_target_reads':0,'sealed_test_prediction_calls':0,'formal_output_write_count':0,'status':'PASS'}
    if not result['all_match'] or not result['distinct_process']: result['status']='FAIL'
    tmp=a.result_json.with_suffix('.tmp'); tmp.write_text(json.dumps(result,sort_keys=True,indent=2)); os.replace(tmp,a.result_json); print(json.dumps(result,sort_keys=True)); raise SystemExit(0 if result['status']=='PASS' else 1)
if __name__=='__main__': main()
