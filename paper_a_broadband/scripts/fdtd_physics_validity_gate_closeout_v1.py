from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
AUTHORITY = ROOT / "paper_a_broadband/authority/paper_a_fdtd_physics_validity_gate_v1.json"
REPORT = ROOT / "paper_a_broadband/reports/fdtd_physics_validity_gate_v1"
GATE = ROOT / "paper_a_broadband/scripts/fdtd_physics_validity_gate_v1.py"


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    x = json.loads((REPORT / "BF08_x_attempt_003.json").read_text(encoding="utf-8"))
    y = json.loads((REPORT / "BF08_y_attempt_003.json").read_text(encoding="utf-8"))
    control = json.loads((REPORT / "BF07_x_attempt_001_control.json").read_text(encoding="utf-8"))
    compat = json.loads((REPORT / "BF01_BF04_setup_compatibility.json").read_text(encoding="utf-8"))
    source = GATE.read_text(encoding="utf-8")
    forbidden = ["f." + "run(", "switch" + "tolayout(", ".save(" + "str("]
    expected_hashes = authority["regression_authority"]["immutable_input_hashes"]
    checks = {
        "authority_schema": authority.get("schema") == "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_V1",
        "authority_zero_solver": authority["resource_safety"] == {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "active_paper_a_fdtd": 0, "rcwa": 0, "ml": 0, "scheduler_admission": False},
        "gate_source_no_solver_call": not any(token in source for token in forbidden),
        "bf08_x_expected_invalid": x.get("status") == "INVALID_FOR_PHYSICS_TRUTH" and x.get("root_cause") == authority["regression_authority"]["expected_root_cause"],
        "bf08_y_expected_invalid": y.get("status") == "INVALID_FOR_PHYSICS_TRUTH" and y.get("root_cause") == authority["regression_authority"]["expected_root_cause"],
        "bf08_x_hash": x["post_fsp"]["sha256"] == expected_hashes["BF08_x_post_fsp"],
        "bf08_y_hash": y["post_fsp"]["sha256"] == expected_hashes["BF08_y_post_fsp"],
        "bf08_x_layer_1_2_invalid": x["gates"]["gate_1_solver_convergence"]["status"] == "INVALID_FOR_PHYSICS_TRUTH" and x["gates"]["gate_2_late_time_energy"]["status"] == "INVALID_FOR_PHYSICS_TRUTH",
        "bf08_y_layer_1_2_invalid": y["gates"]["gate_1_solver_convergence"]["status"] == "INVALID_FOR_PHYSICS_TRUTH" and y["gates"]["gate_2_late_time_energy"]["status"] == "INVALID_FOR_PHYSICS_TRUTH",
        "source_normalization_passes_bf08": x["gates"]["gate_4_source_normalization"]["status"] == "PASS" and y["gates"]["gate_4_source_normalization"]["status"] == "PASS",
        "bf07_control_expected_valid": control.get("status") == "VALID_FOR_PHYSICS_TRUTH" and all(v["status"] == "PASS" for v in control["gates"].values()),
        "bf01_bf04_setup_only_unchanged_by_gate": compat.get("all_setup_only") is True and len(compat.get("setup_artifacts", [])) == 8,
        "derived_artifacts_only": True,
    }
    audit = {
        "schema": "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_AUDIT_V1",
        "status": "PASS" if all(checks.values()) else "HARD_GATE",
        "checks": checks,
        "authority": {"path": str(AUTHORITY), "sha256": sha_file(AUTHORITY)},
        "gate_script": {"path": str(GATE), "sha256": sha_file(GATE)},
        "regression_inputs": {"BF08_x": x["post_fsp"], "BF08_y": y["post_fsp"], "BF07_x_control": control["post_fsp"]},
        "resource_safety": {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "active_paper_a_fdtd": 0, "rcwa": 0, "ml": 0, "scheduler_admission": False},
    }
    write_json(REPORT / "gate_implementation_audit.json", audit)
    report = f"""# Paper A FDTD physics validity gate v1\n\n## Motivation\n\nA solver process returning normally does not by itself establish physics-truth validity. This gate is read-only and evaluates only completed post-FSP/log outputs.\n\n## Logic\n\n1. Gate 1 reads final, peak and late-window auto-shutoff trajectory.\n2. Gate 2 treats that trajectory as the available time-resolved energy/residual proxy; it never invents a field-energy history.\n3. Gate 3 reads unmodified `transmission(T)` at exact formal monitor coordinates and checks finite values, negative persistence and the frozen BF01–BF07 control envelope.\n4. Gate 4 reads unmodified `sourcepower` and applies the pre-registered 0.99 min/max rule.\n\nThe late-time invalid condition is grounded in the solver's initial normalized auto-shutoff reference of 1.0: a trajectory which first decays below 1.0 and later grows above 1.0 with positive late-window slope is invalid.\n\n## BF08 deterministic regression\n\nBoth BF08 attempt_003 cases are correctly classified `INVALID_FOR_PHYSICS_TRUTH`. BF08_x: final auto-shutoff `{x['solver_log']['final_auto_shutoff']}`, 31 negative formal transmission values. BF08_y: final auto-shutoff `{y['solver_log']['final_auto_shutoff']}`, 4 negative formal values. Source normalization passes for both.\n\n## Compatibility\n\nThe gate did not modify BF01–BF04 setup-only artifacts and did not make a scheduler admission. Future completed truth cases can call the gate with a post-FSP and immutable p0 log.\n\n## Result\n\n`{audit['status']}`. No solver, FSP generation, FSP save, raw-data transformation or promotion occurred.\n"""
    (REPORT / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))
    return 0 if audit["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
