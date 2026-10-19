import json
import sys
import os
import threading
from unittest.mock import patch
import tempfile
import time
from pathlib import Path

try:
    from postsolver_persistence_v1 import (
    ArtifactRoles,
    LifecycleController,
    LifecycleError,
    LifecycleState,
    zero_solver_recover,
    sha256_file,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "coupling_ml"))
    from postsolver_persistence_v1 import (
        ArtifactRoles, LifecycleController, LifecycleError, LifecycleState,
        zero_solver_recover, sha256_file,
    )


class FakeAdapter:
    def __init__(self, mode="ok"):
        self.mode = mode
        self.run_count = 0
        self.close_count = 0
        self.session_id = "fake-session"
        self.live = False

    def open(self, path):
        self.live = True
        return {"path": path}

    def run(self, handle):
        events=Path(handle['path']).parent/'events.jsonl'
        rows=[json.loads(l) for l in events.read_text().splitlines()]
        assert any(r['state']=='SCIENTIFIC_SOLVER_ENTERED' for r in rows), 'entry must precede run'
        assert (events.parent/'events.entered.json').exists()
        self.run_count += 1

    def save(self, handle, path):
        if self.mode == "exception" and path.endswith("canonical.fsp"):
            raise OSError("controlled canonical path failure")
        if self.mode == "timeout" and path.endswith("canonical.fsp"):
            time.sleep(0.15)
            return
        Path(path).write_bytes(b"scientific-result")

    def rescue_save(self, handle, path):
        Path(path).write_bytes(b"scientific-result-rescue")

    def is_alive(self, handle):
        return self.live

    def live_results_available(self,handle):
        return self.live and self.run_count>0

    def load_only(self, path, manifest):
        return {"ok": self.mode != "load-fail", "run_called": False,
                "result_object": True, "manifest_id": manifest["job_id"],
                "identity_pass":True,"arrays_pass":True,"shape_pass":True,"sanity_pass":True,
                "session_id":"independent-fake-session"}

    def extract_raw(self, handle, post, raw):
        Path(raw).write_bytes(Path(post).read_bytes() + b"-raw")

    def extract_raw_from_post(self, post, raw):
        Path(raw).write_bytes(Path(post).read_bytes() + b"-recovered-raw")

    def close(self, handle):
        self.close_count += 1
        self.live = False


def callbacks(root):
    return (
        lambda raw: {"n": len(Path(raw).read_bytes())},
        lambda derived, post, raw: {"pass": True, "post_sha": sha256_file(post)},
    )


def run_case(mode="ok", derive=None, timeout=1, adapter_factory=FakeAdapter, release_override=None):
    root = Path(tempfile.mkdtemp(prefix="postsolver-test-"))
    setup = root / "setup.fsp"
    setup.write_bytes(b"setup")
    roles = ArtifactRoles(root / "frozen.fsp", root / "runtime.fsp",
                          root / "canonical.fsp", root / "recovery.fsp")
    adapter = adapter_factory(mode)
    released = []
    raw_derive, audit = callbacks(root)
    controller = LifecycleController(
        job_id="job-1", attempt_id="attempt-001", roles=roles,
        events_path=root / "events.jsonl", completion_path=root / "completion.json",
        raw_path=root / "raw.bin", release_slot=release_override or released.append,
        save_timeout_s=timeout,
    )
    if derive is None:
        derive = raw_derive
    manifest = {"job_id": "job-1", "setup_pre_fsp": str(setup)}
    try:
        result = controller.execute(adapter, manifest, adapter.extract_raw, derive, audit)
    except Exception as exc:
        result = exc
    return root, roles, adapter, released, controller, result


def test_normal_and_gate():
    root, roles, adapter, released, controller, result = run_case()
    assert result["status"] == "COMPLETED"
    assert result["state"] == "SLOT_RELEASED"
    assert adapter.run_count == 1 and adapter.close_count == 1
    assert released == ["COMPLETED"]
    assert roles.frozen_pre.read_bytes() == b"setup"
    states = roles.event_order(root / "events.jsonl")
    assert states.index("SOLVER_RETURNED") < states.index("POST_FSP_SAVE_REQUESTED") < states.index("POST_FSP_LOAD_ONLY_VALIDATED") < states.index("COMPLETED") < states.index("SLOT_RELEASED")
    assert "COMPLETED" not in states[:states.index("POST_FSP_LOAD_ONLY_VALIDATED")]


def test_illegal_direct_completion():
    root = Path(tempfile.mkdtemp())
    controller = LifecycleController(job_id="j", attempt_id="a", roles=ArtifactRoles(root / "a", root / "b", root / "c", root / "d"), events_path=root / "e", completion_path=root / "c.json", raw_path=root / "r", release_slot=lambda _: None)
    controller.transition(LifecycleState.APP_OPEN_REQUESTED)
    try:
        controller.transition(LifecycleState.COMPLETED)
    except LifecycleError:
        return
    raise AssertionError("illegal transition accepted")


def test_save_rescue_and_timeout():
    for mode in ("exception", "timeout"):
        root, roles, adapter, released, controller, result = run_case(mode, timeout=0.01)
        assert result["status"] == "COMPLETED", result
        assert result["post_fsp"].endswith("recovery.fsp")
        assert adapter.run_count == 1
        assert released == ["COMPLETED"]
        assert roles.recovery_post.is_file()


def test_load_only_failure_blocks_completion():
    root, roles, adapter, released, controller, result = run_case("load-fail")
    assert isinstance(result, LifecycleError)
    assert result.args
    assert not (root / "completion.json").exists()
    assert released == []
    assert adapter.live and adapter.close_count == 0


def test_parser_failure_zero_solver_recovery():
    root, roles, adapter, released, controller, result = run_case(derive=lambda raw: (_ for _ in ()).throw(ValueError("parser")))
    assert isinstance(result, ValueError)
    assert roles.canonical_post.is_file()
    fixed = FakeAdapter()
    recovered = zero_solver_recover(
        job_id="job-1", attempt_id="attempt-002", events_path=root / "recovery-events.jsonl",
        post_fsp=roles.canonical_post, raw_path=root / "recovered.raw", completion_path=root / "recovered.json",
        adapter=fixed, manifest={"job_id": "job-1"}, extract_raw=fixed.extract_raw,
        derive=lambda raw: {"n": len(Path(raw).read_bytes())}, audit=lambda d, p, r: {"pass": True},
        expected_post_sha256=sha256_file(roles.canonical_post),
        original_solver_returned=True,
    )
    assert recovered["solver_rerun"] is False and recovered["run_invocation_count"] == 0
    assert fixed.run_count == 0


def test_runtime_rescue_does_not_invent_native_return():
    root,roles,_,_,_,_=run_case()
    fixed=FakeAdapter()
    recovered=zero_solver_recover(job_id='job-1',attempt_id='runtime-rescue',events_path=root/'runtime-rescue.jsonl',
        post_fsp=roles.canonical_post,raw_path=root/'rescue.raw',completion_path=root/'rescue.json',
        adapter=fixed,manifest={'job_id':'job-1'},extract_raw=fixed.extract_raw,derive=lambda r:{},audit=lambda d,p,r:{'pass':True},
        expected_post_sha256=sha256_file(roles.canonical_post),original_solver_returned=False)
    assert recovered['solver_returned'] is False and recovered['run_invocation_count']==0 and fixed.run_count==0


def test_solver_entry_precedes_native_run():
    _,_,adapter,_,_,result=run_case()
    assert adapter.run_count==1 and result['status']=='COMPLETED'


def test_premature_session_loss_retains_owner_and_slot():
    class Dead(FakeAdapter):
        def save(self,h,p):
            self.live=False
            raise RuntimeError('session disconnected')
    root,roles,a,released,c,result=run_case(adapter_factory=Dead)
    assert isinstance(result,LifecycleError) and not released and a.close_count==0
    assert not (root/'completion.json').exists()


def test_no_concurrent_api_calls_during_timeout():
    class Slow(FakeAdapter):
        def open(self,p):
            self.owner=threading.get_ident()
            return super().open(p)
        def save(self,h,p):
            assert threading.get_ident()==self.owner
            time.sleep(.04)
            super().save(h,p)
    root,_,a,_,_,result=run_case(adapter_factory=Slow,timeout=.005)
    assert result['status']=='COMPLETED'
    text=(root/'events.jsonl').read_text()
    assert 'SAVE_TIMEOUT_RECOVERY_REQUIRED' in text and 'TIMED_OUT_SAVE_CALL_RETURNED' in text


def test_no_release_before_validation():
    observed=[]
    def release(reason):observed.append(reason)
    root,roles,a,_,c,result=run_case('load-fail',release_override=release)
    assert not observed and c.handle is not None


def test_frozen_pre_replay_and_overwrite_rejected():
    root,roles,_,_,_,_=run_case()
    before=sha256_file(roles.frozen_pre)
    try:roles.prepare(root/'setup.fsp')
    except LifecycleError:pass
    else:raise AssertionError('replay accepted')
    assert sha256_file(roles.frozen_pre)==before
    if os.name=='nt':
        try:roles.frozen_pre.write_bytes(b'mutation')
        except PermissionError:pass
        else:raise AssertionError('frozen file writable')


def test_artifact_role_alias_rejected():
    root=Path(tempfile.mkdtemp());setup=root/'setup';setup.write_bytes(b'setup')
    roles=ArtifactRoles(root/'a',root/'a',root/'c',root/'d')
    try:roles.prepare(setup)
    except LifecycleError:return
    raise AssertionError('aliased roles accepted')


def test_append_only_event_order_and_crash_audit():
    from postsolver_persistence_v1 import inspect_durable_state,durable_event
    root,roles,_,_,_,_=run_case()
    path=root/'events.jsonl';before=path.read_bytes()
    assert inspect_durable_state(path)['complete']
    durable_event(path,job_id='job-1',attempt_id='attempt-001',state='READ_ONLY_AUDIT')
    assert path.read_bytes().startswith(before)
    rows=[json.loads(l) for l in before.decode().splitlines()]
    crash=root/'crash.jsonl'
    states=[r['state'] for r in rows]
    n=states.index('SOLVER_RETURNED')
    crash.write_text('\n'.join(json.dumps(r) for r in rows[:n+1]))
    value=inspect_durable_state(crash,worker_alive=False)
    assert not value['complete'] and value['classification']=='FAILED_AFTER_ENTRY_WITHOUT_VALIDATED_PERSISTENCE'


def test_controller_requires_validated_post_not_exit_code():
    from postsolver_persistence_v1 import inspect_durable_state
    root,_,_,_,_,_=run_case('load-fail')
    assert not inspect_durable_state(root/'events.jsonl')['complete']


def test_controller_engine_footer_is_not_native_return_or_completion():
    from postsolver_persistence_v1 import inspect_durable_state
    root,_,_,_,_,_=run_case('load-fail')
    rows=[json.loads(l) for l in (root/'events.jsonl').read_text().splitlines()]
    entered=next(i for i,r in enumerate(rows) if r['state']=='SCIENTIFIC_SOLVER_ENTERED')
    probe=root/'pending-native-return.jsonl'
    probe.write_text('\n'.join(json.dumps(r) for r in rows[:entered+1])+'\n')
    state=inspect_durable_state(probe,worker_alive=True,engine_completed=True)
    assert state['classification']=='ENGINE_COMPLETED_NATIVE_RETURN_PENDING' and not state['complete']


def test_parser_taxonomy_after_persistence():
    root,_,_,_,_,_=run_case(derive=lambda p: (_ for _ in ()).throw(ValueError('injected parser')))
    data=json.loads((root/'completion.json').read_text())
    assert data['error_class']=='PARSER_FAILURE' and data['solver_returned']


def canonical_scheduler():
    import importlib.util
    p=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\scripts\coupling\apcd_global_fdtd_slot_v3.py')
    spec=importlib.util.spec_from_file_location('repair_test_slots',p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module._impl._branch_cap = lambda branch: (3, "TEST_FIXTURE")
    return module


def test_registry_collision_retry_and_short_lock():
    s=canonical_scheduler();root=Path(tempfile.mkdtemp());path=root/'test_registry.json'
    scheduler=s.GlobalSlotScheduler(path,process_provider=lambda:[])
    original=s._impl.os.replace;calls=[]
    def collide(*args):
        calls.append(args)
        if len(calls)==1:raise PermissionError(32,'controlled test collision')
        return original(*args)
    with patch.object(s._impl.os,'replace',collide):
        lease=scheduler.acquire('test',str(root),'repair-test','collision',pid=os.getpid())
    assert len(calls)==2 and not Path(str(path)+'.lock').exists()
    lease.release('TEST_NO_SOLVER')
    assert json.loads(path.read_text())['active_slots']==[]


def test_registry_stale_lock_and_preentry_orphan():
    s=canonical_scheduler();root=Path(tempfile.mkdtemp());path=root/'test_registry.json'
    lock=Path(str(path)+'.lock');lock.write_text(json.dumps({'pid':99999999,'created_utc':'2000-01-01T00:00:00Z'}))
    os.utime(lock,(time.time()-1000,time.time()-1000))
    scheduler=s.GlobalSlotScheduler(path,process_provider=lambda:[])
    first=scheduler.acquire('test',str(root),'repair-test','orphan',pid=99999999)
    second=scheduler.acquire('test',str(root),'repair-test','next',pid=os.getpid())
    data=json.loads(path.read_text())
    assert data['history'][-1]['completion_release_state']=='STALE_RECOVERED_PRE_ENTRY'
    assert not lock.exists()
    second.release('TEST_NO_SOLVER')


def test_registry_entered_orphan_requires_evidence():
    s=canonical_scheduler();root=Path(tempfile.mkdtemp());path=root/'test_registry.json'
    scheduler=s.GlobalSlotScheduler(path,process_provider=lambda:[])
    lease=scheduler.acquire('test',str(root),'repair-test','entered-orphan',pid=99999999)
    lease.mark_solver_entered()
    try:
        second=scheduler.acquire('test',str(root),'repair-test','next',pid=os.getpid())
    except s.StaleEnteredSlot:
        second=None
    else:
        second.release('TEST_NO_SOLVER')
    # Only a disposable test registry is mutated; no live registry is used by tests.
    assert json.loads(path.read_text())['active_slots'][0]['case_uid']=='entered-orphan'


def test_telemetry_fallback_and_degradation_are_not_scientific_gates():
    from postsolver_persistence_v1 import compatible_process_snapshot
    s=canonical_scheduler()
    assert compatible_process_snapshot(s)['quality']=='AVAILABLE_COMPATIBILITY_FALLBACK'
    s._ps_snapshot=lambda: (_ for _ in ()).throw(RuntimeError('telemetry unavailable'))
    assert compatible_process_snapshot(s)['quality']=='DEGRADED_TELEMETRY'
    assert run_case()[5]['status']=='COMPLETED'


def test_controller_rehash_rejects_post_mutation():
    from postsolver_persistence_v1 import validated_completion
    root,roles,_,_,_,_=run_case()
    assert validated_completion(root/'events.jsonl',root/'completion.json')['status']=='COMPLETED'
    roles.canonical_post.write_bytes(b'corrupted-after-worker-exit')
    try:validated_completion(root/'events.jsonl',root/'completion.json')
    except LifecycleError:return
    raise AssertionError('controller accepted mutated post')


def main():
    for name in sorted(globals()):
        if name.startswith("test_"):
            globals()[name]()
    print("postsolver zero-solver tests: PASS")


if __name__ == "__main__":
    main()
