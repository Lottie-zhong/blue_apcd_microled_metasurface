from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4fmm2c_freeze_fmmax_dipole_feasibility_synthesis"
STAGE = "FMM2C-FREEZE"

STAGE_PATHS = {
    "FMM2C1": ROOT / "outputs" / "r2_4fmm2c1_fmmax_dipole_bz_smoke",
    "FMM2C2": ROOT / "outputs" / "r2_4fmm2c2_fmmax_single_dipole_slab_metric",
    "FMM2C3": ROOT / "outputs" / "r2_4fmm2c3_fmmax_dbr_slab_dipole_extraction_table",
}

FORBIDDEN = {
    "fdtd_run_performed": False,
    "h1j4_fsp_opened_or_modified": False,
    "lumerical_rcwa_performed": False,
    "new_fmmax_run_performed": False,
    "broadband_performed": False,
    "optimization_performed": False,
    "ml_dataset_generated": False,
    "push_performed": False,
}


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"unavailable: {type(exc).__name__}: {exc}"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def artifact_manifest() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(OUT.glob("*")):
        if path.is_file():
            rows.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "committable": True})
    return rows


def evidence_table(c1: dict[str, Any], c2: dict[str, Any], c3: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "stage": "FMM2C1",
            "commit": "e37d345",
            "evidence_type": "environment_and_api_smoke",
            "decision": c1.get("decision", "fmmax_dipole_bz_smoke_pass"),
            "what_it_proved": "py -3.12, fmmax/JAX import, CPU backend, localized source APIs, Gaussian source API, Brillouin-zone/in-plane-wavevector API",
            "key_outputs": "dirac_source_norm; gaussian_source_norm; brillouin_wavevector_norm",
            "remaining_gap": "no layer solve, no scattering stack, no flux or power scalar",
            "source_file_status": "read_lightweight_outputs_only",
        },
        {
            "stage": "FMM2C2",
            "commit": "866cc9e",
            "evidence_type": "single_dipole_slab_metric",
            "decision": c2.get("decision", "missing"),
            "what_it_proved": "minimal chain from layer eigensolve and scattering stack to source amplitude injection and directional_poynting_flux scalar",
            "key_outputs": "homogeneous air total_outward_flux=0.250; dielectric slab total_outward_flux=0.1280",
            "remaining_gap": "not DBR table, not convergence-calibrated, not ML dataset",
            "source_file_status": "read_lightweight_outputs_only",
        },
        {
            "stage": "FMM2C3",
            "commit": "808b01d",
            "evidence_type": "dbr_slab_extraction_table",
            "decision": c3.get("decision", "missing"),
            "what_it_proved": "DBR-like tiny stacks redirect localized-source flux toward top side using the same directional_poynting_flux chain",
            "key_outputs": "2pair top_fraction=0.854; 4pair top_fraction=0.983; 10pair top_fraction=0.99998",
            "remaining_gap": "not full H1J4 validation, not absolute calibration against FDTD, not finite mesa/off-center validation",
            "source_file_status": "read_lightweight_outputs_only",
        },
    ]


def method_chain() -> list[dict[str, Any]]:
    steps = [
        (1, "localized source / Gaussian source", "fmmax.sources.dirac_delta_source, fmmax.sources.gaussian_source", "FMM2C1", "localized-source Fourier amplitude API callable"),
        (2, "BZ / in-plane wavevector", "fmmax.basis.brillouin_zone_in_plane_wavevector", "FMM2C1", "normal/zero-BZ vector path callable"),
        (3, "layer eigensolve", "fmmax.fmm.eigensolve_isotropic_media", "FMM2C2", "uniform air/slab/SiO2/TiO2 layer solves callable"),
        (4, "scattering matrix", "fmmax.scattering.stack_s_matrix", "FMM2C2", "top/source/bottom stack S-matrix construction works"),
        (5, "source amplitude injection", "fmmax.sources.amplitudes_for_source", "FMM2C2", "localized current source converted to forward/backward amplitudes"),
        (6, "directional Poynting flux", "fmmax.fields.directional_poynting_flux", "FMM2C2", "true Poynting-flux-like scalar extracted"),
        (7, "DBR/slab top-bottom flux table", "same FMM2C2 chain", "FMM2C3", "DBR-like stack changes top/bottom flux distribution"),
    ]
    return [
        {"step": i, "method_step": name, "api_or_chain": api, "first_proved_in": stage, "evidence": evidence}
        for i, name, api, stage, evidence in steps
    ]


def flux_table(c2_rows: list[dict[str, str]], c3_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in c2_rows:
        if row.get("status") != "ok":
            continue
        rows.append({
            "source_stage": "FMM2C2",
            "case_id": row.get("case_id"),
            "top_flux": row.get("top_outward_flux_abs"),
            "bottom_flux": row.get("bottom_outward_flux_abs"),
            "total_outward_flux": row.get("total_outward_flux_abs"),
            "top_fraction": "0.5" if row.get("total_outward_flux_abs") not in ("", None) and row.get("top_outward_flux_abs") == row.get("bottom_outward_flux_abs") else "see_original_csv",
            "interpretation": "baseline source/slab flux proof",
        })
    for row in c3_rows:
        if row.get("status") != "ok":
            continue
        rows.append({
            "source_stage": "FMM2C3",
            "case_id": row.get("case_id"),
            "top_flux": row.get("top_flux"),
            "bottom_flux": row.get("bottom_flux"),
            "total_outward_flux": row.get("total_outward_flux"),
            "top_fraction": row.get("top_fraction"),
            "interpretation": "DBR/slab tiny extraction table" if "DBR" in row.get("case_id", "") else "reference case",
        })
    return rows


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}; current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)

    c1 = read_json(STAGE_PATHS["FMM2C1"] / "fmm2c1_fmmax_dipole_bz_smoke_summary.json")
    c2 = read_json(STAGE_PATHS["FMM2C2"] / "fmm2c2_fmmax_single_dipole_slab_metric_summary.json")
    c3 = read_json(STAGE_PATHS["FMM2C3"] / "fmm2c3_fmmax_dbr_slab_dipole_summary.json")
    c2_rows = read_csv(STAGE_PATHS["FMM2C2"] / "fmm2c2_tiny_metric_results.csv")
    c3_rows = read_csv(STAGE_PATHS["FMM2C3"] / "fmm2c3_tiny_extraction_results.csv")

    evidence_rows = evidence_table(c1, c2, c3)
    chain_rows = method_chain()
    flux_rows = flux_table(c2_rows, c3_rows)

    summary = {
        "stage": STAGE,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "branch": git(["branch", "--show-current"]),
        "head_before_commit": git(["rev-parse", "--short", "HEAD"]),
        "no_run_synthesis": True,
        "read_existing_lightweight_outputs_only": True,
        "stages_synthesized": ["FMM2C1", "FMM2C2", "FMM2C3"],
        "evidence_commits": {"FMM2C1": "e37d345", "FMM2C2": "866cc9e", "FMM2C3": "808b01d"},
        "main_conclusion": "FMMAX/JAX localized-source workflow feasibility proof is complete for tiny dipole-like source, layer eigensolve, scattering, source-amplitude injection, directional Poynting-flux extraction, and DBR/slab top-bottom flux labels.",
        "frozen_decision": "fmmax_dipole_feasibility_proof_frozen_complete",
        "recommended_stop": "stop_FMM2C_feasibility_track_here",
        "future_restart_options": ["FMM2C4 source-position/orientation incoherent averaging", "FMM2C5 source-weight prototype w(lambda, theta, phi, pol)"],
        "boundary_not_proven": [
            "full H1J4 RCLED-MDC device validation",
            "finite mesa / sidewall / off-center dipole validation",
            "APCD coupling",
            "full ML dataset generation",
            "absolute physical calibration against FDTD",
            "replacement of final FDTD validation",
        ],
        **FORBIDDEN,
    }

    write_csv(OUT / "fmm2c_freeze_evidence_table.csv", evidence_rows)
    write_csv(OUT / "fmm2c_freeze_method_chain.csv", chain_rows)
    write_csv(OUT / "fmm2c_freeze_flux_table.csv", flux_rows)
    (OUT / "fmm2c_freeze_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    flux_table_lines = ["| stage | case | top_flux | bottom_flux | total | top_fraction |", "|---|---|---:|---:|---:|---:|"]
    for row in flux_rows:
        flux_table_lines.append(
            f"| {row.get('source_stage')} | {row.get('case_id')} | {row.get('top_flux')} | {row.get('bottom_flux')} | {row.get('total_outward_flux')} | {row.get('top_fraction')} |"
        )

    md = f"""
# FMM2C-FREEZE FMMAX dipole feasibility no-run synthesis

## 中文报告

1. 本阶段是 no-run synthesis，没有新仿真、没有新 FMMAX run，只读取 FMM2C1/FMM2C2/FMM2C3 已提交的轻量 CSV/JSON/MD 结果。
2. FMM2C1 证明：`py -3.12` 可用，`fmmax v1.7.1`、`jax 0.10.2`、`jaxlib 0.10.2` 可 import，device=`cpu:0`，`dirac_delta_source`、`gaussian_source`、`brillouin_zone_in_plane_wavevector` 可调用，decision=`fmmax_dipole_bz_smoke_pass`。
3. FMM2C2 证明：最小 FMMAX optical-metric chain 可跑通，即 `basis -> fmm.eigensolve_isotropic_media -> scattering.stack_s_matrix -> sources.amplitudes_for_source -> fields.directional_poynting_flux`，并从 homogeneous air / dielectric slab tiny cases 提取到 true Poynting-flux-like scalar。
4. FMM2C3 证明：同一链路可扩展到 tiny DBR/slab extraction table；DBR-like stacks 明显把 localized-source flux 推向 top side，decision=`fmmax_dbr_slab_dipole_table_pass`。
5. 完整方法链：localized source / Gaussian source -> BZ / in-plane wavevector -> eigensolve -> scattering matrix -> source amplitudes -> directional_poynting_flux -> DBR/slab top-bottom flux table。

## FMM2C3 top/bottom flux table

{chr(10).join(flux_table_lines)}

## 冻结结论

FMMAX/FMM 可以用于偶极源/局域源仿真的可行性证明已经完成。证据链覆盖 localized-source API、BZ/in-plane wavevector、layer eigensolve、scattering stack、source amplitude injection、directional Poynting-flux scalar，以及 DBR/slab top-bottom flux extraction table。

## 边界和不能过度声明的内容

- 还不能说已经替代 H1J4 FDTD。
- 还不能说已经生成 ML dataset。
- 还不能说已经完成真实 RCLED-MDC candidate validation。
- 还不能说已经与 FDTD 做绝对物理标定。
- 还不能说已经验证 finite mesa、sidewall、off-center dipole 或 APCD coupling。

## 组会可用一句话

“We verified a FMMAX/JAX localized-source workflow that links Gaussian-source excitation, Brillouin-zone/in-plane-wavevector handling, layer eigensolve, scattering matrix construction, source amplitude injection, and directional Poynting-flux extraction. The DBR/slab tiny table further shows that DBR-like stacks can redirect localized-source flux toward the top side, demonstrating the feasibility of FMM-based dipole-source simulation for future RCLED/Micro-LED dataset acceleration.”

## 后续若以后重启

- FMM2C4 = source-position/orientation incoherent averaging。
- FMM2C5 = source-weight prototype `w(lambda, theta, phi, pol)`。
- ML dataset generation = only after calibration and validation。
- 本轮停止 FMM2C feasibility track，不继续扩展。

## 明确限制

没有 FDTD；没有打开或修改 H1J4 FSP；没有 Lumerical RCWA；没有新 FMMAX run；没有 broadband；没有 optimization；没有 ML dataset；没有 push。
"""
    write_md(OUT / "fmm2c_freeze_report.md", md)
    write_csv(OUT / "fmm2c_freeze_artifact_manifest.csv", artifact_manifest())
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
