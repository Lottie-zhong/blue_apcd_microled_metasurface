import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "apcd_global_fdtd_slot_v1.py"
if not MODULE_PATH.exists():
    MODULE_PATH = Path(__file__).resolve().parents[1] / "_remote_slot.py"
spec = importlib.util.spec_from_file_location("solver_slot", MODULE_PATH)
solver_slot = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(solver_slot)


def group(case_path, branch_path, start_pid):
    rows = [{"pid": start_pid, "ppid": 0, "name": "mpiexec.exe", "cmdline": f"mpiexec -n 4 fdtd-engine-msmpi.exe D:/{branch_path}/{case_path}.fsp", "path": "mpiexec.exe"}]
    for i in range(4):
        rows.append({"pid": start_pid + i + 1, "ppid": start_pid, "name": "fdtd-engine-msmpi.exe", "cmdline": f"fdtd-engine-msmpi.exe D:/{branch_path}/{case_path}.fsp -t 1", "path": "fdtd-engine-msmpi.exe"})
    return rows


def fake_registry(path):
    path.write_text(json.dumps(solver_slot.default_registry()), encoding="utf-8")


class SolverTypeAwareSchedulerTests(unittest.TestCase):
    def test_a_np_fdtd_admits_lp(self):
        rows = group("a", "project/blue_apcd_np_k6", 100)
        snap = solver_slot.live_job_snapshot(lambda: rows)
        self.assertEqual(snap["active_fdtd_jobs"], 1)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "registry.json"
            fake_registry(path)
            lease = solver_slot.GlobalSlotScheduler(path, lambda: rows).acquire("work/lp-global-h-manifold-v1", "lp", "task", "case")
            lease.release("TEST_RELEASE")

    def test_b_rcwa_does_not_block_lp(self):
        rows = group("a", "project/blue_apcd_np_k6", 200) + group("b", "project/blue_apcd_mdc_np_coupling_v1", 300)
        snap = solver_slot.live_job_snapshot(lambda: rows)
        self.assertEqual(snap["active_fdtd_jobs"], 1)
        self.assertEqual(snap["active_rcwa_jobs"], 1)

    def test_c_two_fdtd_plus_rcwa_blocks_new_fdtd(self):
        rows = group("a", "project/blue_apcd_np_k6", 400) + group("b", "project/blue_apcd_np_k6", 500) + group("c", "project/blue_apcd_mdc_np_coupling_v1", 600)
        snap = solver_slot.live_job_snapshot(lambda: rows)
        self.assertEqual(snap["active_fdtd_jobs"], 2)
        self.assertEqual(snap["active_rcwa_jobs"], 1)

    def test_d_lp_active_blocks_same_branch_only(self):
        rows = group("a", "project/blue_apcd_np_k6", 700) + group("b", "project/blue_apcd_lp_global_h_manifold_v1", 800) + group("c", "project/blue_apcd_mdc_np_coupling_v1", 900)
        snap = solver_slot.live_job_snapshot(lambda: rows)
        self.assertEqual(snap["active_fdtd_jobs"], 2)
        self.assertEqual(snap["active_rcwa_jobs"], 1)

    def test_e_four_engines_are_one_case(self):
        snap = solver_slot.live_job_snapshot(lambda: group("a", "project/blue_apcd_np_k6", 1000))
        self.assertEqual(snap["active_fdtd_jobs"], 1)
        self.assertEqual(snap["fdtd_engine_process_count"], 4)

    def test_f_rcwa_delta_is_zero(self):
        snap = solver_slot.live_job_snapshot(lambda: group("a", "project/blue_apcd_mdc_np_coupling_v1", 1100))
        self.assertEqual(snap["active_fdtd_jobs"], 0)
        self.assertEqual(snap["active_rcwa_jobs"], 1)

    def test_g_unknown_is_not_silently_fdtd(self):
        snap = solver_slot.live_job_snapshot(lambda: group("a", "project/unknown_solver", 1200))
        self.assertEqual(snap["active_fdtd_jobs"], 0)
        self.assertEqual(len(snap["unknown_solver_jobs"]), 1)


if __name__ == "__main__":
    unittest.main()
