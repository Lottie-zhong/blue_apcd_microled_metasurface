"""Full existing Controller path with real DIAG2 pins and inert test authority.

The only executable is a marker-checked Python H5 fixture; importer/native LOAD
are explicitly simulated ports. No production credential or physics result.
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from apcd_gpu_v2 import serial
from apcd_gpu_v2.artifacts import sha256
from apcd_gpu_v2.general import (Registry, Pin, GeneralBudget, build_requests,
    import_profile_truth, read_json)
from apcd_gpu_v2.ledger import Refused
from apcd_gpu_v2.serial import EquivalentBackend, exclusive
from apcd_gpu_v2.trusted_admission import issue_and_initialize
from test_trusted_admission import packet, issue


@pytest.fixture(autouse=True)
def isolated_census(monkeypatch):
    # Unit/integration fixtures must not collect foreign command lines. All
    # PID/create-time handling of the fixture launcher remains the real code.
    monkeypatch.setattr(serial, 'process_gate', lambda *a: [])


def fixture_validator(cfg):
    def validate(fsp, req, dest):
        import h5py
        import numpy as np
        with h5py.File(fsp.with_suffix('') / cfg.native_h5_name, 'r') as h5:
            for key in ['Ex', 'Ey', 'Ez', 'Hx', 'Hy', 'Hz']:
                data = h5['Monitor1/' + key][...]
                assert data.shape[-1] == 21 and np.iscomplexobj(data)
        obj = SimpleNamespace(case_id=req.case_id, attempt_id=req.attempt_id,
            role=req.role, ordered_D_nm=req.ordered_D_nm,
            c_hat=np.ones((21, 7, 2), dtype=complex), p_scale=np.ones(21))
        def accept(*args, **kwargs):
            return dict(verdict='PASS', outputs=609, scientific_validated=True,
                fixture_only=True, profile_id=cfg.validation_profile,
                physical_contract_sha256=req.physical_contract_sha256,
                case_request_sha256=req.case_request_sha256,
                physics_contract_file_sha256=req.physical_contract.sha256,
                source_manifest_sha256=req.source_manifest.sha256,
                source_acceptance_file_sha256=req.source_acceptance.sha256,
                batch_id=cfg.batch_id, case_id=req.case_id,
                attempt_id=req.attempt_id, role=req.role,
                ordered_D_nm=list(req.ordered_D_nm),
                manifest_file_sha256=cfg.batch_manifest.sha256,
                admission_file_sha256=cfg.science_admission.sha256,
                certification_file_sha256=cfg.platform.profiles[0].certification.sha256)
        importer = SimpleNamespace(load_authorized_runner_case=lambda *a, **k: obj,
            validate_authorized_labels=accept)
        record = dict(case_id=req.case_id, attempt_id=req.attempt_id,
            role=req.role, ordered_D_nm=list(req.ordered_D_nm),
            physical_contract_sha256=req.physical_contract_sha256)
        imported, accepted = import_profile_truth(cfg, req, record, importer)
        assert imported is obj and accepted['outputs'] == 609
        return dict(verdict='PASS', outputs=609, fresh_load_verified=True,
            actual_importer=cfg.importer_entrypoint, fixture_only=True,
            science_profile_acceptance=accepted)
    return validate


def prepared(tmp_path):
    p = packet(tmp_path, real=True)
    ad = Pin(**issue(p)['admission'])
    assert p[1].submit(p[2], ad) == 'SUBMITTED_PAUSED'
    bid = read_json(p[2].path)['batch_id']
    p[1].operate(bid, False)  # isolated operator action, not production start
    backend = EquivalentBackend(Path(p[0].runtime_root) / 'fake.py')
    return p, ad, bid, backend


def run(p, backend, fault=lambda step: None):
    return p[1].drain(backend=backend, validator_factory=fixture_validator, fault=fault)


def test_real_diag2_issued_controller_two_case_full_chain_and_restart(tmp_path):
    p, ad, bid, backend = prepared(tmp_path)
    state = run(p, backend)
    sci = read_json(p[4])
    assert sci['entered_count'] == sci['truth_valid_count'] == sci['labels_valid_count'] == 2
    assert sci['remaining_unentered_count'] == 0 and sci['replay_count'] == 0
    assert all(t['state'] == 'TRUTH_VALID' for t in state['execution']['tasks'])
    assert state['execution']['slot']['token'] is None
    events = state['execution']['events']
    entered = [e['seq'] for e in events if e['kind'] == 'COUPLING_ENTRY_MIRRORED']
    finished = [e['seq'] for e in events if e['kind'] == 'TRUTH_VALID']
    assert entered[0] < finished[0] < entered[1] < finished[1]
    assert len([e for e in events if e['kind'] == 'LAUNCH_REQUESTED']) == 2
    before = p[4].read_bytes()
    restarted = Registry(p[0])
    restarted.drain(backend=backend, validator_factory=fixture_validator)
    assert p[4].read_bytes() == before
    assert restarted.status()['execution']['conservative_scientific_entries'] == 0
    assert issue_and_initialize(p[0], p[2], p[3], fixture_principal=p[5], recover=True)['status'] == 'ALREADY_ACTIVE_NO_MUTATION'


def test_real_diag2_a1_complete_a2_unentered_pause_and_resume(tmp_path):
    p, ad, bid, backend = prepared(tmp_path)
    def pause(step):
        if step == 'solver_returned': p[1].operate(bid, True)
    state = run(p, backend, pause)
    assert read_json(p[4])['entered_count'] == read_json(p[4])['truth_valid_count'] == 1
    assert len(state['execution']['tasks']) == 1 and not state['execution']['slot']['token']
    assert len(read_json(p[4])['remaining_unentered_case_ids']) == 1
    r = Registry(p[0]); r.operate(bid, False)
    r.drain(backend=backend, validator_factory=fixture_validator)
    assert read_json(p[4])['labels_valid_count'] == 2


@pytest.mark.parametrize('point', ['coupling_receipt_committed', 'coupling_ledger_committed',
    'before_local_mirror', 'after_local_mirror', 'launch_requested',
    'process_started', 'solver_returned', 'truth_valid_before_coupling',
    'coupling_truth_before_local'])
def test_real_diag2_interrupted_controller_never_replays_or_advances(tmp_path, point):
    p, ad, bid, backend = prepared(tmp_path)
    def crash(step):
        if step == point: raise RuntimeError('FIXTURE_CONTROLLER_INTERRUPTED')
    with pytest.raises(RuntimeError, match='FIXTURE_CONTROLLER_INTERRUPTED'):
        run(p, backend, crash)
    # A process-start fault can leave only the owned harmless fixture running.
    # It exits by itself; no terminate/kill is used.
    if point == 'process_started':
        import time
        time.sleep(1)
    before = read_json(p[4])
    assert before['entered_count'] <= 1
    assert len(p[1].status()['execution']['tasks']) == 1
    assert p[1].status()['execution']['slot']['token']
    r = Registry(p[0])
    with pytest.raises(Refused): r.drain(backend=backend, validator_factory=fixture_validator)
    assert read_json(p[4]) == before
    assert len(r.status()['execution']['tasks']) == 1


def test_real_diag2_sqlite_entry_mirror_failure_keeps_science_consumed(tmp_path):
    p, ad, bid, backend = prepared(tmp_path)
    with p[1].ledger.transaction() as db:
        db.execute("CREATE TRIGGER fail_entry BEFORE UPDATE OF entered ON tasks WHEN NEW.entered=1 BEGIN SELECT RAISE(ABORT,'fixture entry persist failure'); END")
    with pytest.raises(sqlite3.IntegrityError): run(p, backend)
    assert read_json(p[4])['entered_count'] == 1
    assert read_json(p[4])['remaining_unentered_count'] == 1
    assert p[1].status()['execution']['tasks'][0]['entered'] == 0
    with pytest.raises(Refused): Registry(p[0]).drain(backend=backend, validator_factory=fixture_validator)
    assert read_json(p[4])['entered_count'] == 1


def test_real_diag2_two_controller_competition_actual_os_lock(tmp_path):
    p, ad, bid, backend = prepared(tmp_path)
    child = """import json,sys
from pathlib import Path
from apcd_gpu_v2.general import Platform,Registry
from apcd_gpu_v2.serial import EquivalentBackend
from apcd_gpu_v2.ledger import Refused
p=Platform.model_validate_json(sys.stdin.read())
try: Registry(p).drain(backend=EquivalentBackend(Path(p.runtime_root)/'fake.py'))
except Refused as e:
 print(str(e));sys.exit(42)
raise SystemExit(99)
"""
    with exclusive(Path(p[0].runtime_root) / '.v2_controller.lock'):
        result = subprocess.run([sys.executable, '-c', child],
            input=p[0].model_dump_json(), text=True, capture_output=True, timeout=20)
        assert result.returncode == 42 and 'OWNER_LOCK' in result.stdout
    assert read_json(p[4])['entered_count'] == 0
    assert not p[1].status()['execution']['tasks']


def test_real_diag2_controller_process_exit_recovers_truth_only_then_pauses(tmp_path):
    p, ad, bid, backend = prepared(tmp_path)
    child = """import json,os,sys
from pathlib import Path
from apcd_gpu_v2.general import Platform,Registry
from apcd_gpu_v2.serial import EquivalentBackend
from apcd_gpu_v2 import serial
serial.process_gate=lambda *a:[]
p=Platform.model_validate_json(sys.stdin.read());r=Registry(p)
def stop(step):
 if step=='solver_returned':os._exit(74)
r.drain(backend=EquivalentBackend(Path(p.runtime_root)/'fake.py'),fault=stop)
"""
    result = subprocess.run([sys.executable, '-c', child], input=p[0].model_dump_json(),
        text=True, capture_output=True, timeout=35)
    assert result.returncode == 74, result.stderr
    assert read_json(p[4])['entered_count'] == 1 and read_json(p[4])['labels_valid_count'] == 0
    r = Registry(p[0]); r.operate(bid, True)
    class NeverRun:
        def execute(self, *a, **k): pytest.fail('recovery tried executable')
    r.drain(backend=NeverRun(), validator_factory=fixture_validator)
    assert read_json(p[4])['entered_count'] == 1 and read_json(p[4])['labels_valid_count'] == 1
    assert not r.status()['execution']['slot']['token']
    assert len(r.status()['execution']['tasks']) == 1
    # New entry remains under an independent operator action; no recovery replay.
    r.operate(bid, False); r.drain(backend=backend, validator_factory=fixture_validator)
    assert read_json(p[4])['entered_count'] == read_json(p[4])['labels_valid_count'] == 2


def test_real_diag2_accepted_science_resource_hold_before_budget(tmp_path, monkeypatch):
    p, ad, bid, backend = prepared(tmp_path)
    def resource_hold(*a): raise Refused('LIVE_GPU_RESOURCE_HOLD_FIXTURE')
    monkeypatch.setattr(serial, 'process_gate', resource_hold)
    with pytest.raises(Refused, match='LIVE_GPU_RESOURCE_HOLD_FIXTURE'): run(p, backend)
    assert read_json(p[4])['entered_count'] == 0
    assert not list(p[4].parent.glob('V21_ENTRY_EVIDENCE_*'))
    assert p[1].status()['execution']['slot']['token']  # no unsafe automatic reset


def test_real_diag2_wrong_fencing_rejects_before_entry(tmp_path):
    p, ad, bid, backend = prepared(tmp_path)
    _, pairs = build_requests(p[0], p[2], ad); cfg, req = pairs[0]
    p[1].ledger.register(req, cfg)
    token = p[1].ledger.claim(req.request_sha256, serial.identity())
    with pytest.raises(Refused, match='FENCING_MISMATCH'):
        p[1].ledger.note(req, token + 'wrong', 'FORGED', {})
    assert read_json(p[4])['entered_count'] == 0

