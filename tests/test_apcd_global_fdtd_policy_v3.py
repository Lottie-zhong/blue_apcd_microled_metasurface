import importlib.util
import json
import os
import threading
from pathlib import Path
import pytest

MOD_PATH = Path(r'D:/project/worktrees/blue_apcd_lp_global_h_manifold_v1/scripts/apcd_global_fdtd_slot_v1.py')
SPEC = importlib.util.spec_from_file_location('policy_v3_slot', MOD_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)

def acquire(path, branch, provider=lambda: []):
    return MOD.GlobalSlotScheduler(path, provider).acquire(branch, str(path.parent), 'policy-v3-test', f'{branch}-{id(path)}', pid=os.getpid())

def test_policy_identity_and_resource_contract():
    assert MOD.POLICY_ID == 'APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3'
    assert MOD.CURRENT_PRODUCTION_FDTD_SCHEDULING_CAP == 3
    assert MOD.DEFAULT_MAX_ACTIVE_FDTD_PER_BRANCH == 3
    assert MOD.GLOBAL_CAPACITY == 3
    assert MOD.MAX_ACTIVE_FDTD_PER_BRANCH == 3
    assert (MOD.PROCESSES_PER_JOB, MOD.THREADS_PER_JOB) == (4, 1)
    assert MOD.RCWA_CONSUMES_FDTD_SLOT is False

def test_a_np_requests_three_then_fourth_waits(tmp_path):
    p = tmp_path/'a.json'; leases = [acquire(p, 'NP') for _ in range(3)]
    try:
        with pytest.raises(MOD.SlotUnavailable, match='WAIT_(GLOBAL_FDTD_CAPACITY|BRANCH_ACTIVE_FDTD)'):
            acquire(p, 'NP')
    finally:
        for x in leases: x.release('TEST_RELEASE')

def test_b_lp_one_then_np_two_only(tmp_path):
    p=tmp_path/'b.json'; leases=[acquire(p,'LP'),acquire(p,'NP'),acquire(p,'NP')]
    try:
        with pytest.raises(MOD.SlotUnavailable): acquire(p,'NP')
    finally:
        for x in leases: x.release('TEST_RELEASE')

def test_c_lp_mdc_then_np_one_only(tmp_path):
    p=tmp_path/'c.json'; leases=[acquire(p,'LP'),acquire(p,'MDC'),acquire(p,'NP')]
    try:
        with pytest.raises(MOD.SlotUnavailable): acquire(p,'NP')
    finally:
        for x in leases: x.release('TEST_RELEASE')

def test_d_global_three_blocks_fourth(tmp_path):
    p=tmp_path/'d.json'; leases=[acquire(p,'LP'),acquire(p,'MDC'),acquire(p,'NP')]
    try:
        with pytest.raises(MOD.SlotUnavailable, match='WAIT_GLOBAL_FDTD_CAPACITY'): acquire(p,'Coupling')
    finally:
        for x in leases: x.release('TEST_RELEASE')

def test_e_same_branch_three_allowed(tmp_path):
    p=tmp_path/'e.json'; leases=[acquire(p,'NP') for _ in range(3)]
    try: assert len(json.loads(p.read_text())['active_slots']) == 3
    finally:
        for x in leases: x.release('TEST_RELEASE')

def test_f_rcwa_does_not_consume_fdtd_slot(tmp_path):
    rcwa=[{'pid':901,'ppid':0,'name':'python.exe','cmdline':'python rcwa_runner.py --run --coupling'}]
    snap=MOD.live_job_snapshot(lambda: rcwa)
    assert snap['active_fdtd_jobs']==0 and snap['active_rcwa_jobs']==1
    p=tmp_path/'f.json'; leases=[acquire(p,'NP') for _ in range(3)]
    try:
        with pytest.raises(MOD.SlotUnavailable): acquire(p,'LP')
    finally:
        for x in leases: x.release('TEST_RELEASE')

def test_g_simultaneous_acquisition_never_exceeds_three(tmp_path):
    p=tmp_path/'g.json'; results=[]; leases=[]; lock=threading.Lock()
    def attempt(i):
        try:
            x=acquire(p,f'branch-{i}')
            with lock: leases.append(x); results.append(True)
        except MOD.SlotUnavailable:
            with lock: results.append(False)
    ts=[threading.Thread(target=attempt,args=(i,)) for i in range(4)]
    for t in ts:t.start()
    for t in ts:t.join()
    try:
        assert sum(results)==3
        assert len(json.loads(p.read_text())['active_slots'])<=3
    finally:
        for x in leases:x.release('TEST_RELEASE')

def test_h_release_unblocks_queue(tmp_path):
    p=tmp_path/'h.json'; leases=[acquire(p,f'b{i}') for i in range(3)]
    leases[0].release('TEST_RELEASE')
    x=acquire(p,'queued'); x.release('TEST_RELEASE')
    for y in leases[1:]: y.release('TEST_RELEASE')

def test_i_entered_job_is_not_changed_by_new_admission(tmp_path):
    p=tmp_path/'i.json'; x=acquire(p,'NP'); x.mark_solver_entered('2026-08-16T00:00:00+00:00')
    try:
        data=json.loads(p.read_text()); assert data['active_slots'][0]['entered'] is True
        assert data['active_slots'][0]['entered_solver'] is True
        with pytest.raises(MOD.SlotUnavailable):
            [acquire(p,'NP') for _ in range(3)]
    finally: x.release('TEST_RELEASE')

def test_j_rcwa_constant_and_no_oversubscription():
    assert MOD.RCWA_CONSUMES_FDTD_SLOT is False
    assert MOD.GLOBAL_CAPACITY == 3
    assert MOD.PROCESSES_PER_JOB == 4 and MOD.THREADS_PER_JOB == 1
