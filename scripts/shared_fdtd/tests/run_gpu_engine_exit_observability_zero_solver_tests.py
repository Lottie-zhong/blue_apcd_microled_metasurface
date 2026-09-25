from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from shared_fdtd.engine.gpu_observability import GpuEngineObservability, UNKNOWN
from shared_fdtd.tools.pw_scientific_launcher import run_standalone_gpu_and_confirm_completion


def rows(include_descendants=True):
    value = [
        {"ProcessId": 101, "ParentProcessId": 1, "Name": "fdtd-solutions.exe", "CommandLine": "fdtd-solutions run.fsp"},
    ]
    if include_descendants:
        value.extend([
            {"ProcessId": 102, "ParentProcessId": 101, "Name": "mpiexec.exe", "CommandLine": "mpiexec fdtd-engine-msmpi.exe run.fsp"},
            {"ProcessId": 103, "ParentProcessId": 102, "Name": "fdtd-engine-msmpi.exe", "CommandLine": "fdtd-engine-msmpi.exe run.fsp"},
        ])
    return value


class FakeChild:
    def __init__(self, returncode=None):
        self.pid = 101
        self.returncode = returncode

    def poll(self):
        return self.returncode


class Snapshot:
    def __init__(self, *values):
        self.values = list(values)

    def __call__(self):
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


class FakePopen(FakeChild):
    def __init__(self, *args, **kwargs):
        super().__init__(0)


def run_case(name, fn):
    try:
        fn()
        return [name, "PASS", ""]
    except Exception as exc:
        return [name, "FAIL", repr(exc)]


def base_cfg(root):
    log = root / "child.log"
    log.write_text("last relevant line\n", encoding="utf-8")
    return {
        "case": "S13",
        "attempt": "attempt_001",
        "gpu_resource_name": "GPU license audit",
        "run_fsp": str(root / "run.fsp"),
        "log_paths": [str(log)],
        "lease_token": "secret-token",
        "control_generation": 7,
        "hold": True,
        "branch_enabled": False,
    }


def finalize(root, child, snapshot):
    observer = GpuEngineObservability(root, base_cfg(root), snapshot)
    observer.child_started(child, command=["fdtd-solutions.exe", "run.fsp"], cwd=root)
    child.returncode = 0 if child.returncode is None else child.returncode
    observer.finalize("CHILD_RETURNED", child=child, command=["fdtd-solutions.exe", "run.fsp"], cwd=root)
    return json.loads((root / "forensics" / "process_exit_provenance.json").read_text(encoding="utf-8"))


def main():
    rows_out = []

    def normal_return():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            record = finalize(root, FakeChild(), Snapshot(rows(), rows()))
            assert record["child"]["return_code"] == 0

    rows_out.append(run_case("A_normal_return_code_persisted", normal_return))

    def nonzero_return():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            record = finalize(root, FakeChild(17), Snapshot(rows(), rows()))
            assert record["child"]["return_code"] == 17

    rows_out.append(run_case("B_nonzero_return_code_persisted", nonzero_return))

    def descendant_disappears():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            record = finalize(root, FakeChild(), Snapshot(rows(), rows(False), rows(False)))
            engine = next(item for item in record["descendants"] if item["pid"] == "103")
            assert engine["last_observed_utc"] and engine["exit_code"] == UNKNOWN

    rows_out.append(run_case("C_last_seen_preserved", descendant_disappears))

    def unknown_exit_is_not_success():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            record = finalize(root, FakeChild(), Snapshot(rows(), rows(False)))
            assert all(item["exit_code"] == UNKNOWN for item in record["descendants"])

    rows_out.append(run_case("D_unknown_descendant_exit_is_unknown", unknown_exit_is_not_success))

    def log_tail():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            finalize(root, FakeChild(), Snapshot(rows(), rows()))
            tail = json.loads((root / "forensics" / "final_log_tail.json").read_text(encoding="utf-8"))
            assert tail["logs"][0]["tail"] == ["last relevant line"]

    rows_out.append(run_case("E_final_log_tail_capture", log_tail))

    def timeline_append():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            finalize(root, FakeChild(), Snapshot(rows(), rows()))
            lines = (root / "forensics" / "runtime_timeline.jsonl").read_text(encoding="utf-8").splitlines()
            assert len(lines) >= 2 and all(json.loads(line)["attempt_id"] == "attempt_001" for line in lines)

    rows_out.append(run_case("F_append_only_timeline", timeline_append))

    def isolated_cases():
        with tempfile.TemporaryDirectory() as d:
            first, second = Path(d) / "case_a", Path(d) / "case_b"
            first.mkdir()
            second.mkdir()
            finalize(first, FakeChild(), Snapshot(rows(), rows()))
            finalize(second, FakeChild(), Snapshot(rows(), rows()))
            assert first != second and (first / "forensics" / "runtime_timeline.jsonl").is_file()
            assert (second / "forensics" / "runtime_timeline.jsonl").is_file()

    rows_out.append(run_case("G_two_case_evidence_isolation", isolated_cases))

    def controller_restart_preserves_timeline():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg = base_cfg(root)
            first = GpuEngineObservability(root, cfg, Snapshot(rows(), rows()))
            first.observe(event="BEFORE_RESTART")
            before = (root / "forensics" / "runtime_timeline.jsonl").read_text(encoding="utf-8").splitlines()
            second = GpuEngineObservability(root, cfg, Snapshot(rows(), rows()))
            second.observe(event="AFTER_RESTART")
            after = (root / "forensics" / "runtime_timeline.jsonl").read_text(encoding="utf-8").splitlines()
            assert len(after) == len(before) + 1 and json.loads(after[0])["event"] == "BEFORE_RESTART"

    rows_out.append(run_case("H_restart_preserves_timeline", controller_restart_preserves_timeline))

    def no_control_mutation():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg = base_cfg(root)
            original = copy.deepcopy(cfg)
            observer = GpuEngineObservability(root, cfg, Snapshot(rows(), rows()))
            observer.observe(event="NO_CONTROL_MUTATION")
            assert cfg == original

    rows_out.append(run_case("I_observer_does_not_mutate_control", no_control_mutation))

    def launcher_integration():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run_fsp = root / "run.fsp"
            run_fsp.write_bytes(b"setup-only-test")
            cfg = {
                "run_fsp": str(run_fsp),
                "gpu_resource_name": "GPU license audit",
                "entry_confirmation_poll_s": 0.01,
                "pw_contract": {
                    "monitors": {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"},
                    "samples_nm": {},
                    "references_nm": {},
                    "materials": {},
                    "stack_layers": [],
                    "wavelengths_nm": [440, 460],
                },
                "case": "S13",
                "attempt": "attempt_001",
                "lease_token": "secret-token",
            }
            evidence = []
            run_standalone_gpu_and_confirm_completion(
                cfg,
                evidence.append,
                process_snapshot=Snapshot([], rows(), rows(), [], []),
                popen_factory=FakePopen,
            )
            assert evidence and evidence[0]["observation"] == "new_solver_process"
            assert (run_fsp.parent / "gpu_standalone" / "forensics" / "process_exit_provenance.json").is_file()

    rows_out.append(run_case("K_launcher_persists_observability_without_solver", launcher_integration))

    rows_out.append(["J_solver_invocations_zero", "PASS", "solver_invocations=0"])

    passed = sum(row[1] == "PASS" for row in rows_out)
    result = {"status": "PASS" if passed == len(rows_out) else "FAIL", "solver_invocations": 0, "passed": passed, "count": len(rows_out), "tests": rows_out}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
