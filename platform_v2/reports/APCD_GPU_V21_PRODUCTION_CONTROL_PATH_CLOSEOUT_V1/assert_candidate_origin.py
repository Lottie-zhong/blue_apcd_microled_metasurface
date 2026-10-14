import importlib,json,os,sys
from pathlib import Path
import pytest
def pytest_configure(config):
 expected=Path(os.environ['APCD_CANDIDATE_ROOT']).resolve()
 sys.path.insert(0,str(expected))
 modules={}
 for name in ['apcd_gpu_v2','apcd_gpu_v2.general','apcd_gpu_v2.serial','apcd_gpu_v2.trusted_admission','apcd_gpu_v2.gpu_readonly']:
  p=Path(importlib.import_module(name).__file__).resolve();p.relative_to(expected);modules[name]=str(p)
 Path(os.environ['APCD_ORIGIN_OUTPUT']).write_text(json.dumps(modules,indent=2),encoding='utf-8')
 def guard(event,args):
  if event=='subprocess.Popen':
   exe=Path(str(args[0])).name.lower()
   if any(tag in exe for tag in ['fdtd','ansys','hfss','maxwell','rcwa','fmm']):
    raise RuntimeError('SCIENTIFIC_EXECUTABLE_PROHIBITED_IN_OFFLINE_TEST')
 sys.addaudithook(guard)
@pytest.fixture(autouse=True)
def no_foreign_commandline_collection(monkeypatch):
 from apcd_gpu_v2 import serial
 # Explicit environmental fixture: do not read any foreign stdin/argv. Resource
 # mechanism negative tests inject their own inputs; native launcher identity
 # still runs for owned harmless executable children. Never a live clearance.
 monkeypatch.setattr(serial,'process_gate',lambda *a:[])
