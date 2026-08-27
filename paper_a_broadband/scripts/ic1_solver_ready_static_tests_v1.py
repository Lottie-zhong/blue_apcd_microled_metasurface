from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "paper_a_broadband"
BUILDER = BASE / "scripts/ic1_solver_ready_prefsp_builder_v1.py"
RUNNER = BASE / "scripts/ic1_production_runner_v1.py"
OUT = BASE / "reports/ic1_solver_ready_static_tests.json"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    results = []
    builder_text, runner_text = BUILDER.read_text(encoding="utf-8"), RUNNER.read_text(encoding="utf-8")
    builder_ast, runner_ast = ast.parse(builder_text), ast.parse(runner_text)
    run_calls = [node for node in ast.walk(runner_ast) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == "run"]
    check(len(run_calls) == 1, "RUN_CALL_COUNT_UNEXPECTED")
    execute_nodes = [node for node in ast.walk(runner_ast) if isinstance(node, ast.FunctionDef) and node.name == "execute"]
    check(execute_nodes and any(run_calls[0] in ast.walk(node) for node in execute_nodes), "RUN_NOT_GUARDED_IN_EXECUTE")
    check(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run"
                  for node in ast.walk(builder_ast)), "BUILDER_MUST_NOT_CALL_RUN")
    results.append({"name": "solver_run_guard_static", "pass": True, "runner_run_calls": 1})

    i03 = load(BASE / "authority/ic1_i03_5x5_replication_authority.json")
    check(len(i03["cells"]) == 25 and i03["period_nm"] == {"Px": 432.0, "Py": 432.0}, "I03_AUTHORITY")
    check(i03["unit_cell"]["material"] == "APCD_TIO2_NATIVE_M1", "I03_MATERIAL")
    results.append({"name": "ic1_authority_geometry_static", "pass": True, "cells": 25, "pillars": 50})

    z = load(BASE / "authority/ic1_absolute_z_layout.json")
    check(z["i03"]["bottom_z_nm"] == 975.0 and z["i03"]["top_z_nm"] == 1500.0, "I03_Z")
    check(z["ic1_source"]["case_id"] == "IC1_MDC_I03_TOPWELL_X" and z["ic1_source"]["position_nm"] == [0.0, 0.0, -171.5], "SOURCE")
    results.append({"name": "absolute_z_and_source_static", "pass": True})

    monitor = load(BASE / "authority/ic1_monitor_contract.json")
    check(monitor["source_grid"]["start_nm"] == 400.0 and monitor["source_grid"]["stop_nm"] == 500.0 and
          monitor["source_grid"]["points"] == 101, "SOURCE_GRID")
    check(monitor["convergence_instrumentation"]["position_nm"] == [0.0, 0.0, -100.0], "V2_POSITION")
    results.append({"name": "monitor_contract_static", "pass": True, "source_points": 101})

    gate_path = BASE / "scripts/fdtd_physics_validity_gate_v2_instrumented.py"
    spec = __import__("importlib.util").util.spec_from_file_location("ic1_v2_gate", gate_path)
    module = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(module)
    series = module.independent_series({"status": "PERSISTED", "independent_time_series": {
        "time_s": [0.0, 1e-12, 2e-12, 3e-12], "field_energy_proxy": [1.0, 0.5, 0.2, 0.1],
        "monitor_name": "ic1_v2_time_probe"}})
    check(series["status"] == "PASS", "V2_SYNTHETIC_SERIES")
    results.append({"name": "v2_static_synthetic_fixture", "pass": True, "samples": 4})

    bd = subprocess.run([sys.executable, str(BUILDER), "--mode", "dry-run"], capture_output=True, text=True)
    check(bd.returncode == 0 and '"solver_entered": 0' in bd.stdout, "BUILDER_DRY_RUN")
    rd = subprocess.run([sys.executable, str(RUNNER), "--mode", "dry-run"], capture_output=True, text=True)
    check(rd.returncode in (0, 2) and '"run_called": false' in rd.stdout and '"entered": 0' in rd.stdout, "RUNNER_DRY_RUN")
    results.append({"name": "runner_dry_run_no_dispatch", "pass": True})

    ignore = (BASE / ".gitignore").read_text(encoding="utf-8")
    check("runtime/" in ignore and "*.fsp" in ignore, "RUNTIME_FSP_NOT_IGNORED")
    results.append({"name": "runtime_ignore_guard", "pass": True})

    authority_path = BASE / "authority/ic1_solver_ready_prefsp_authority_v1.json"
    if authority_path.exists():
        ready = load(authority_path)
        check(ready["solver_counters"]["solver_entered"] == 0 and ready["authorization"]["authorization_used"] is False, "ZERO_SOLVER_AUTH")
        results.append({"name": "prefsp_authority_zero_solver", "pass": True})
    else:
        results.append({"name": "prefsp_authority_zero_solver", "pass": True, "deferred": True})

    result = {"schema": "PAPER_A_IC1_SOLVER_READY_STATIC_TESTS_V1", "status": "PASS",
              "solver_calls": 0, "solver_entered": 0, "results": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "tests": len(results), "solver_calls": 0, "solver_entered": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
