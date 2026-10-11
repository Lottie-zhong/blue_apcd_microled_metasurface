import json,time
from pathlib import Path
import pytest
from apcd_gpu_v2.artifacts import sha256
from apcd_gpu_v2.serial import Pin
from apcd_gpu_v2.ledger import Refused
from apcd_gpu_v2.v3_plan import Plan,run_plan,deadline,finite_phase,remaining_phase
from apcd_gpu_v2.gpu_readonly import evaluate_idle_desktop,KNOWN_DESKTOP_PINS
from test_v3_registered import fixture,validator,put


def test_full56_one_controller_fake_phases(tmp_path):
 cfg,rs,backend=fixture(tmp_path)
 code=Path(cfg.runtime_root)/'code';code.mkdir();source=code/'fixture.txt';source.write_text('not a solver')
 inventory=put(Path(cfg.runtime_root)/'inventory.json',dict(code_root=str(code),files={'fixture.txt':{'sha256':sha256(source)}}))
 evaluator=Path(cfg.runtime_root)/'evaluator.json';put(evaluator,{'fixture_only':True})
 template=put(Path(cfg.runtime_root)/'template.json',cfg.model_dump())
 plan=Plan(template_config=template,code_inventory=inventory,diagnostic_evaluator=dict(path=str(evaluator),sha256=sha256(evaluator)),schema='APCD_V3_FINITE_PHASE_PLAN_V1',expires_unix=time.time()+3*86400)
 calls=[]
 def gate(p,c,folder):
  d=json.loads(Path(c.coupling_ledger).read_text());assert d['labels_valid_count']==4;calls.append('FOUR_VALID')
  return c.diagnostic_gate
 assert run_plan(plan,backend=backend,validator_factory=lambda c:validator,gate_runner=gate)=='COMPLETE'
 d=json.loads(Path(cfg.coupling_ledger).read_text());assert d['entered_count']==d['truth_valid_count']==d['labels_valid_count']==56
 assert calls==['FOUR_VALID'];assert len(list((Path(cfg.v3_data_root)/'V3_DEVELOPMENT/published').glob('*/labels.npz')))==44
 assert len(list((Path(cfg.v3_data_root)/'V3_SEALED_EVALUATION').glob('**/synthetic_labels.npz')))==8
 # Same immutable identities are skipped on later finite windows, not replayed.
 assert run_plan(plan,backend=backend,validator_factory=lambda c:validator,gate_runner=lambda p,c,f:c.diagnostic_gate)=='COMPLETE'
 assert json.loads(Path(cfg.coupling_ledger).read_text())['entered_count']==56


def test_receipt_only_crash_blocks_other_case(tmp_path):
 cfg,rs,_=fixture(tmp_path)
 from apcd_gpu_v2.v3 import V3Budget
 b=V3Budget(cfg)
 def fault(k):
  if k=='coupling_receipt_committed':raise RuntimeError('crash')
 with pytest.raises(RuntimeError):b.prepare_entry(rs[0],'token',fault)
 with pytest.raises(Refused,match='RECEIPT_UNCERTAIN'):b.validate(rs[1])
 with pytest.raises(Refused,match='UNCERTAIN'):remaining_phase(cfg,'DIAGNOSTIC')


def test_exact_next_ten_am_deadline():
 from datetime import datetime,timezone,timedelta
 tz=timezone(timedelta(hours=8));before=datetime(2026,10,11,9,59,tzinfo=tz).timestamp();after=before+120
 assert deadline(before)==datetime(2026,10,11,10,tzinfo=tz).timestamp()
 assert deadline(after)==datetime(2026,10,12,10,tzinfo=tz).timestamp()


@pytest.mark.parametrize('case',['pin','command','activity','missing','child','short'])
def test_idle_desktop_fail_closed(monkeypatch,case):
 from apcd_gpu_v2 import gpu_readonly as g
 monkeypatch.setattr(g,'known_desktop',lambda row:case!='pin')
 record={'pid':11,'ppid':10,'creation_time':123,'executable':KNOWN_DESKTOP_PINS[0]['path']}
 command=[record['executable'],'--type=gpu-process'];children=[];samples=[[{'name':'pid_11_eng_0','utilization':0}]]*3
 if case=='command':command=[record['executable'],'--type=unknown']
 if case=='activity':samples=[[{'name':'pid_11_eng_0','utilization':1}]]*3
 if case=='missing':samples=[[{'name':'pid_12_eng_0','utilization':0}]]*3
 if case=='child':children=[{'executable':'C:/evil.exe','ppid':11,'creation_time':124}]
 if case=='short':samples=samples[:2]
 with pytest.raises(Refused):evaluate_idle_desktop(record,command,children,samples)


def test_idle_desktop_requires_all_zero(monkeypatch):
 from apcd_gpu_v2 import gpu_readonly as g
 monkeypatch.setattr(g,'known_desktop',lambda row:True)
 record={'pid':11,'ppid':10,'creation_time':123,'executable':KNOWN_DESKTOP_PINS[0]['path']}
 result=evaluate_idle_desktop(record,[record['executable'],'--utility-sub-type=on_device_model.mojom.OnDeviceModelService'],[],[[{'name':'pid_11_eng_0','utilization':0}]]*3)
 assert result['classification']=='VERIFIED_IDLE_DESKTOP'
