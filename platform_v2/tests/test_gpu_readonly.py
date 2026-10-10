from copy import deepcopy

import pytest

from apcd_gpu_v2.gpu_readonly import EDT, LICENSE, evaluate_idle_edt
from apcd_gpu_v2.ledger import Refused


def evidence():
    record=dict(pid=123,creation_time=1.,executable=str(EDT))
    return [record,[str(EDT),'N:/other/project.aedt'],[dict(executable=str(LICENSE))],[[dict(name='pid_123_luid_0_engtype_Compute',utilization=0)] for _ in range(3)]]


def test_positive_idle_gui():
    assert evaluate_idle_edt(*evidence())['classification']=='VERIFIED_IDLE_EDT_GUI'


@pytest.mark.parametrize('fault',['compute','render','pid','sample','child','command','image','malformed'])
def test_idle_exception_requires_complete_evidence(fault):
    args=deepcopy(evidence())
    if fault in ['compute','render']:args[3][1][0].update(name='pid_123_luid_0_engtype_'+('Compute' if fault=='compute' else '3D'),utilization=1)
    if fault=='pid':args[3][0][0]['name']='pid_999_luid_0_engtype_Compute'
    if fault=='sample':args[3].pop()
    if fault=='child':args[2][0]['executable']='N:/solver.exe'
    if fault=='command':args[1].append('-BatchSolve')
    if fault=='image':args[0]['executable']='N:/untrusted/ansysedt.exe'
    if fault=='malformed':args[3][1][0]['utilization']=None
    with pytest.raises(Refused):evaluate_idle_edt(*args)
