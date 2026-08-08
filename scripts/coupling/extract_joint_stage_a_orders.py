from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from apcd_coupling.result_schema import validate_result

OUTPUT = ROOT / "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1"
NP_ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
REF_PATH = NP_ROOT / "outputs/np_k6_p1d4b_k6x_phase_candidate_run3a_audit_v1/run3a_order_sign_audit.json"
REF_SOURCE_COMMIT = "7a8588f6b5a1c96d88813f60406d418b488135fd"
CLOSURE_TOLERANCE = 0.02


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def arr(value: Any) -> np.ndarray:
    return np.asarray(value).reshape(-1)


def order_rows(fdtd: Any, monitor: str, index: int, total_power: float, direction: str) -> list[dict[str, Any]]:
    fraction = np.real(np.asarray(fdtd.grating(monitor, index)))
    n = np.rint(np.real(arr(fdtd.gratingn(monitor, index)))).astype(int)
    m = np.rint(np.real(arr(fdtd.gratingm(monitor, index)))).astype(int)
    ux = np.real(arr(fdtd.gratingu1(monitor, index)))
    uy = np.real(arr(fdtd.gratingu2(monitor, index)))
    if m.size == 0:
        m = np.asarray([0], dtype=int)
    if uy.size == 0:
        uy = np.asarray([0.0])
    if ux.size != n.size or uy.size != m.size:
        raise RuntimeError(f"order-axis mismatch for {monitor}: n={n.size}, m={m.size}, ux={ux.size}, uy={uy.size}")
    if fraction.size != n.size * m.size:
        raise RuntimeError(f"grating fraction shape mismatch for {monitor}: fraction={fraction.shape}, n={n.size}, m={m.size}")
    fraction = fraction.reshape((n.size, m.size))
    rows = []
    for i, order_x in enumerate(n):
        for j, order_y in enumerate(m):
            direction_cosine = float(ux[i])
            rows.append({
                "m": int(order_x),
                "m_y": int(order_y),
                "physical_kx_sign": "+x" if direction_cosine > 0 else "-x" if direction_cosine < 0 else "zero",
                "physical_propagation_direction": direction,
                "u_x": direction_cosine,
                "u_y": float(uy[j]),
                "theta_out_deg": float(np.degrees(np.arcsin(np.clip(direction_cosine, -1.0, 1.0)))),
                "power_fraction_of_monitor_total": float(fraction[i, j]),
                "power_fraction_of_source": float(total_power * fraction[i, j]),
            })
    if not rows:
        raise RuntimeError(f"no open diffraction orders returned by {monitor} at frequency index {index}")
    return rows

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    setup = json.loads((args.output_dir / "setup_manifest.json").read_text(encoding="utf-8"))
    runtime = json.loads((args.output_dir / "runtime/attempt_001/run_state.json").read_text(encoding="utf-8"))
    if not runtime.get("solver_completed"):
        raise RuntimeError("post-FSP extraction requires solver_completed=true")
    post = Path(runtime["post_fsp_path"])
    if sha256(post) != runtime["post_fsp_sha256"]:
        raise RuntimeError("post-FSP hash mismatch before extraction")
    import lumapi
    fdtd = lumapi.FDTD(str(post), hide=True)
    try:
        tr = fdtd.getresult("transmission_monitor", "T")
        rr = fdtd.getresult("reflection_monitor", "T")
        wavelengths = arr(tr["lambda"]) * 1e9
        T = np.real(arr(tr["T"]))
        R_signed = np.real(arr(rr["T"]))
        R = np.abs(R_signed)
        if len(wavelengths) != 1 or abs(float(wavelengths[0]) - 450.0) > 1e-6:
            raise RuntimeError(f"unexpected wavelength axis: {wavelengths.tolist()}")
        transmitted = order_rows(fdtd, "transmission_monitor", 1, float(T[0]), "+z")
        reflected = order_rows(fdtd, "reflection_monitor", 1, float(R[0]), "-z")
    finally:
        fdtd.close()
    transmitted_sum = sum(row["power_fraction_of_source"] for row in transmitted)
    reflected_sum = sum(row["power_fraction_of_source"] for row in reflected)
    by_t = {row["m"]: row for row in transmitted}
    by_r = {row["m"]: row for row in reflected}
    for order in (1, 0, -1):
        if order not in by_t or order not in by_r:
            raise RuntimeError(f"required order {order} missing from both transmitted/reflected extraction")
    plus = by_t[1]
    minus = by_t[-1]
    zero = by_t[0]
    directionality = float(plus["power_fraction_of_source"] / (plus["power_fraction_of_source"] + minus["power_fraction_of_source"]))
    closure_residual = float(1.0 - float(T[0]) - float(R[0]))
    order_t_residual = float(transmitted_sum - float(T[0]))
    order_r_residual = float(reflected_sum - float(R[0]))
    reference = json.loads(REF_PATH.read_text(encoding="utf-8"))["at_450_nm"]
    reference_values = {"eta_plus1": float(reference["plus1_absolute_efficiency"]), "eta_zero": float(reference["zero_absolute_efficiency"]), "eta_minus1": float(reference["minus1_absolute_efficiency"]), "directionality": float(reference["directionality"])}
    result = {
        "schema_version": "joint_stage_a_result_v1",
        "case_id": "STAGE_A_450NM_X_UX0_TEXTRA0",
        "mdc_candidate_id": setup["case"]["mdc_candidate"]["candidate_id"],
        "mdc_geometry_hash": setup["case"]["mdc_geometry_hash"],
        "np_candidate_id": setup["case"]["np_candidate"]["candidate_id"],
        "np_geometry_hash": setup["case"]["np_geometry_hash"],
        "joint_stack_id": "APCD_MDC_NP_COUPLING_V1_STAGE_A_DIRECT_FULLWAVE_BASELINE",
        "joint_geometry_hash": setup["case"]["joint_geometry_hash"],
        "spacer_nm": 0,
        "wavelength_nm": 450,
        "polarization": "x",
        "kx_over_k0": 0.0,
        "R_total": float(R[0]),
        "T_total": float(T[0]),
        "eta_t_orders": transmitted,
        "eta_r_orders": reflected,
        "eta_plus1": float(plus["power_fraction_of_source"]),
        "eta_zero": float(zero["power_fraction_of_source"]),
        "eta_minus1": float(minus["power_fraction_of_source"]),
        "theta_out_plus1_deg": float(plus["theta_out_deg"]),
        "directionality": directionality,
        "power_closure": {"R_total_plus_T_total": float(R[0] + T[0]), "residual_1_minus_R_minus_T": closure_residual, "estimated_native_material_absorption": closure_residual, "formal_R_plus_T_tolerance": CLOSURE_TOLERANCE, "formal_R_plus_T_pass": abs(closure_residual) <= CLOSURE_TOLERANCE, "absorption_accounted": closure_residual >= 0.0, "pass": closure_residual >= 0.0 and closure_residual <= 1.0, "interpretation": "APCD_GAN_NATIVE_M1 is lossy; R+T is not forced to 1. The residual is reported as the native-material absorption term under the project convention."},
        "order_closure": {"transmitted_order_sum": transmitted_sum, "reflected_order_sum": reflected_sum, "transmitted_residual": order_t_residual, "reflected_residual": order_r_residual, "tolerance": 1e-8, "pass": abs(order_t_residual) <= 1e-8 and abs(order_r_residual) <= 1e-8},
        "source_contract_id": setup["case"]["source_contract_id"],
        "material_contract_id": setup["case"]["material_contract_id"],
        "coordinate_contract_id": setup["case"]["coordinate_contract_id"],
        "mesh_contract_id": "RUN3A_NATIVE_M1_FDTD_SETTINGS_INHERITED_V1",
        "pre_fsp_path": setup["pre_fsp_path"],
        "pre_fsp_sha256": setup["pre_fsp_sha256"],
        "post_fsp_path": str(post),
        "post_fsp_sha256": runtime["post_fsp_sha256"],
        "solver_entered": True,
        "solver_completed": True,
        "source_commits": setup["source_commits"],
        "coupling_commit": setup["coupling_commit"],
        "raw_monitor_extraction_reference": {"post_fsp_path": str(post), "readonly_session": True, "api": ["getresult(T)", "grating", "gratingn", "gratingm", "gratingu1", "gratingu2"]},
        "standalone_reference": {"path": str(REF_PATH), "source_commit": REF_SOURCE_COMMIT, "path_sha256": sha256(REF_PATH), "values": reference_values},
        "standalone_delta": {"eta_plus1": float(plus["power_fraction_of_source"] - reference_values["eta_plus1"]), "eta_zero": float(zero["power_fraction_of_source"] - reference_values["eta_zero"]), "eta_minus1": float(minus["power_fraction_of_source"] - reference_values["eta_minus1"]), "directionality": float(directionality - reference_values["directionality"])},
        "sign_audit": {"m_plus_1": int(plus["m"]), "m_plus_1_u_x": float(plus["u_x"]), "m_plus_1_physical_kx_sign": plus["physical_kx_sign"], "contract": "m=+1 equals physical +x", "pass": plus["m"] == 1 and plus["u_x"] > 0},
    }
    validate_result(result)
    args.output_dir.joinpath("results").mkdir(parents=True, exist_ok=True)
    (args.output_dir / "results/result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "results/transmitted_orders.json").write_text(json.dumps(transmitted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "results/reflected_orders.json").write_text(json.dumps(reflected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "results/standalone_comparison.json").write_text(json.dumps({"reference": result["standalone_reference"], "delta": result["standalone_delta"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "results/order_spectrum.csv").open("w", newline="", encoding="utf-8") as handle:
        rows = [{**row, "channel": "transmitted"} for row in transmitted] + [{**row, "channel": "reflected"} for row in reflected]
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    manifest = {"schema_version": "joint_stage_a_extraction_manifest_v1", "case_id": result["case_id"], "post_fsp_path": str(post), "post_fsp_sha256": runtime["post_fsp_sha256"], "result_path": str(args.output_dir / "results/result.json"), "readonly_session": True, "run_called": False, "save_called": False, "order_sign_pass": result["sign_audit"]["pass"], "power_closure_pass": result["power_closure"]["pass"], "order_closure_pass": result["order_closure"]["pass"]}
    (args.output_dir / "results/extraction_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
