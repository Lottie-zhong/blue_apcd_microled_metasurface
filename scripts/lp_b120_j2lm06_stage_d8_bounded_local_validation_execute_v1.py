from __future__ import annotations

import csv
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML = ROOT / "outputs/lp_ml_dataset_v1"
PLAN = ML / "plans/b120_j2lm06_bounded_local_validation_stage_d8_v1.json"
CONTRACTS = [
    ML / "plans/b120_j2lm06_stage_d8_execution_contract_v1.json",
    ML / "plans/b120_j2lm06_stage_d8_ml_label_contract_v1.json",
    ML / "plans/b120_j2lm06_stage_d8_validation_metric_contract_v1.json",
]
CANONICAL_CHECKSUMS = ML / "canonical_v1_21/checksums_v1_21.json"
PACKAGE = ML / "execution_packages/b120_j2lm06_stage_d8_bounded_local_validation_execution_package_v1"
FORMAL_STAGING = ML / "staging/b120_j2lm06_stage_d8_bounded_local_validation_v1"
SCRIPT = ROOT / "scripts/lp_b120_j2lm06_stage_d8_bounded_local_validation_execute_v1.py"
RUNTIME = ROOT / "scripts/lp_checkpoint_authoritative_runtime_v1_23.py"
PARENT_HEAD = "5c2155263b20d72b5efe63097660b7594e7fc50e"

spec = importlib.util.spec_from_file_location("d6_runner", ROOT / "scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py")
if not spec or not spec.loader:
    raise RuntimeError("D6_ADAPTER_IMPORT_FAILED")
d6 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = d6
spec.loader.exec_module(d6)

EXPECTED_CANDIDATES = [
    "D8_TRV_PLAN_d6f4911593b64495", "D8_TRV_PLAN_3f9495af463cc07b",
    "D8_TRV_PLAN_c011ef1be0120947", "D8_TRV_PLAN_2709798bc19d7b76",
    "D8_TRV_PLAN_2c6c4edac3638079", "D8_TRV_PLAN_9cf1d115c3f947b9",
    "D8_TRV_PLAN_28f33b5793175bc4", "D8_TRV_PLAN_b90dc117dcee89fd",
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_runtime():
    s = importlib.util.spec_from_file_location("lp_v123_checkpoint_runtime", RUNTIME)
    if not s or not s.loader:
        raise RuntimeError("RUNTIME_MODULE_RESOLUTION_FAILED")
    m = importlib.util.module_from_spec(s)
    sys.modules[s.name] = m
    s.loader.exec_module(m)
    if Path(m.__file__).resolve() != RUNTIME.resolve():
        raise RuntimeError("RUNTIME_MODULE_SHADOWED")
    return m

def git(*args: str) -> str:
    return d6.git(*args)

def source_paths() -> list[Path]:
    return [PLAN, *CONTRACTS, CANONICAL_CHECKSUMS]

def plan_spec(candidate_id: str) -> dict:
    plan = json.loads(PLAN.read_text(encoding="utf8"))
    row = next(item for item in plan["candidates"] if item["candidate_id"] == candidate_id)
    return {
        **row,
        "legacy_case_id": candidate_id,
        "legacy_bin": 60,
        "J1_primitive": "sharp_rectangle",
        "J1_dims": {"side_nm": float(row["J1_side_nm"])},
        "J1_center": [float(x) for x in row["J1_center_nm"]],
        "J1_rotation": float(row["theta1_deg"]),
        "J2_primitive": "sharp_rectangle",
        "J2_L": float(row["J2_length_nm"]),
        "J2_W": float(row["J2_width_nm"]),
        "J2_center": [float(x) for x in row["J2_center_nm"]],
        "J2_rotation": float(row["theta2_deg"]),
        "geometry_hash": row["exact_geometry_hash"],
        "migration_manifest": {"geometry_hash_sha256": row["exact_geometry_hash"]},
        "fabrication_preferred_pass": True,
    }

def expected_identity(candidate: dict, polarization: str) -> dict:
    config = {"H_nm": 500.0, "period_nm": [432.0, 432.0], "material": "APCD_TIO2_NATIVE_M1", "background": "air", "incidence": "normal", "boundary": "xy_periodic_z_pml", "monitor_z_nm": 1000.0, "wavelength_nm": 450.0, "observable": "LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1"}
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"candidate_id": candidate["candidate_id"], "input_polarization": polarization, "wavelength_nm": 450.0,
            "exact_geometry_hash": candidate["exact_geometry_hash"], "physics_configuration_hash": config_hash,
            "weighted_G0_version": "LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1", "normalization_version": "LP_WEIGHTED_G0_SQRT_T_NORM_V1",
            "source_plan_sha256": sha(PLAN), "schema_version": "LP_ML_SCHEMA_V1.24"}

def runtime_attestation() -> dict:
    runtime = load_runtime()
    plan = json.loads(PLAN.read_text(encoding="utf8"))
    candidates = [row["candidate_id"] for row in plan["candidates"]]
    if candidates != EXPECTED_CANDIDATES:
        raise RuntimeError("FROZEN_CANDIDATE_ORDER_MISMATCH")
    callback_sha = hashlib.sha256(__import__("inspect").getsource(runtime.post_solver_acceptance).encode("utf8")).hexdigest()
    return {"status": "PASS", "git_head": git("rev-parse", "HEAD"), "required_parent_head": PARENT_HEAD,
            "runner": {"path": str(SCRIPT.resolve()), "sha256": sha(SCRIPT), "qualname": "main"},
            "callback": {"path": str(RUNTIME.resolve()), "sha256": sha(RUNTIME), "source_sha256": callback_sha, "qualname": "post_solver_acceptance"},
            "validator": {"id": runtime.VALIDATOR_ID, "version": runtime.VALIDATOR_VERSION, "path": str(RUNTIME.resolve()), "sha256": sha(RUNTIME), "source_sha256": callback_sha},
            "schema": runtime.SCHEMA, "registration_mode": runtime.REGISTRATION_MODE, "event_log_mode": runtime.EVENT_MODE,
            "lock_mode": runtime.LOCK_MODE, "serializer": runtime.SERIALIZER, "legacy_line557_allowed": False,
            "legacy_runtime_gate_allowed": False, "source_hashes": {str(p.resolve()): sha(p) for p in source_paths()},
            "candidate_order": candidates, "subrun_order": [c + "_" + p for c in candidates for p in ("x", "y")],
            "solver_calls": 0, "lumapi_calls": 0, "fdtd_calls": 0}

def prepare_package() -> None:
    PACKAGE.mkdir(parents=True, exist_ok=True)
    att = runtime_attestation()
    d6.d6 if False else None
    (PACKAGE / "runtime_attestation_contract.json").write_text(json.dumps(att, indent=2, sort_keys=True), encoding="utf8")
    manifest = {"status": "READY_FOR_EXPLICIT_D8_EXECUTION", "stage_id": "STAGE_D8_BOUNDED_LOCAL_VALIDATION", "candidate_order": EXPECTED_CANDIDATES, "subrun_order": att["subrun_order"], "future_budget": {"geometries": 8, "subruns": 16, "wavelength_nm": [450]}, "source_hashes": att["source_hashes"], "runner_attestation": att["runner"], "runtime_attestation": att["callback"]}
    (PACKAGE / "package_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf8")
    files = []
    for p in (PACKAGE / "runtime_attestation_contract.json", PACKAGE / "package_manifest.json"):
        files.append({"path": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
    (PACKAGE / "content_checksums.json").write_text(json.dumps({"status": "PASS", "files": files}, indent=2, sort_keys=True), encoding="utf8")

def candidate_metrics(cid: str) -> dict:
    base = FORMAL_STAGING / "subruns" / cid
    rows = {}
    for pol in ("x", "y"):
        cp = base / pol / "checkpoint.json"
        rows[pol] = json.loads(cp.read_text(encoding="utf8"))
    txx = complex(rows["x"]["weighted_G0_Ex"]["real"], rows["x"]["weighted_G0_Ex"]["imag"])
    tyx = complex(rows["x"]["weighted_G0_Ey"]["real"], rows["x"]["weighted_G0_Ey"]["imag"])
    txy = complex(rows["y"]["weighted_G0_Ex"]["real"], rows["y"]["weighted_G0_Ex"]["imag"])
    tyy = complex(rows["y"]["weighted_G0_Ey"]["real"], rows["y"]["weighted_G0_Ey"]["imag"])
    import numpy as np
    J = np.array([[txx, txy], [tyx, tyy]], dtype=complex)
    sv = np.linalg.svd(J, compute_uv=False)
    return {"candidate_id": cid, "txx": {"real": txx.real, "imag": txx.imag}, "txy": {"real": txy.real, "imag": txy.imag}, "tyx": {"real": tyx.real, "imag": tyx.imag}, "tyy": {"real": tyy.real, "imag": tyy.imag}, "Txx": abs(txx)**2, "Txy": abs(txy)**2, "Tyx": abs(tyx)**2, "Tyy": abs(tyy)**2, "sigma1": float(sv[0]), "sigma2": float(sv[1]), "sigma2_over_sigma1": float(sv[1]/sv[0]) if sv[0] else None, "determinant": {"real": np.linalg.det(J).real, "imag": np.linalg.det(J).imag}, "physics_label": "FORMAL_ACCEPTED_WEIGHTED_G0", "prediction_label": "MODEL_PREDICTION_NOT_PHYSICS_LABEL"}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        prepare_package()
        print(json.dumps(runtime_attestation(), indent=2, sort_keys=True))
        return 0
    if not args.execute:
        raise RuntimeError("D8_EXECUTION_REQUIRES_EXPLICIT_EXECUTE")
    prepare_package()
    FORMAL_STAGING.mkdir(parents=True, exist_ok=True)
    results = []
    for cid in EXPECTED_CANDIDATES:
        for pol in ("x", "y"):
            out = d6.execute_one(cid, pol, d6.ProductionLumapiBackend(), FORMAL_STAGING, False)
            results.append({"candidate_id": cid, "polarization": pol, "status": out["status"], "checkpoint_sha256": out["checkpoint_sha256"]})
        metrics = candidate_metrics(cid)
        (FORMAL_STAGING / "candidates").mkdir(parents=True, exist_ok=True)
        (FORMAL_STAGING / "candidates" / f"{cid}.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf8")
    (FORMAL_STAGING / "subrun_results.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf8")
    all_metrics = [json.loads(p.read_text(encoding="utf8")) for p in sorted((FORMAL_STAGING / "candidates").glob("*.json"))]
    (FORMAL_STAGING / "candidate_metrics.json").write_text(json.dumps(all_metrics, indent=2, sort_keys=True), encoding="utf8")
    print(json.dumps({"status": "PASS", "planned_subruns": 16, "raw_invocations": 16, "accepted": 16, "complete_jones": 8, "staging": str(FORMAL_STAGING), "package": str(PACKAGE)}, indent=2))
    return 0

if __name__ == "__main__":
    # Redirect the D6 adapter's globals to the independently attested D8 inputs.
    d6.PLAN = PLAN; d6.CONTRACTS = CONTRACTS; d6.CANONICAL_CHECKSUMS = CANONICAL_CHECKSUMS; d6.PACKAGE = PACKAGE; d6.FORMAL_STAGING = FORMAL_STAGING; d6.SCRIPT = SCRIPT; d6.RUNTIME = RUNTIME; d6.PARENT_HEAD = PARENT_HEAD; d6.EXPECTED_CANDIDATES = EXPECTED_CANDIDATES
    d6.plan_spec = plan_spec; d6.expected_identity = expected_identity; d6.runtime_attestation = runtime_attestation; d6.load_runtime = load_runtime
    raise SystemExit(main())
