from __future__ import annotations

import csv
import importlib
import inspect
import json
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4fmm2c3_fmmax_dbr_slab_dipole_extraction_table"
STAGE = "FMM2C3"
PREVIOUS_STAGE_COMMIT = "866cc9e"

N_AIR = 1.0
N_SIO2 = 1.426
N_TIO2 = 2.535
N_SOURCE_SLAB = 1.5
WL_UM = 0.453
T_TIO2_UM = 0.045
T_SIO2_UM = 0.079
SOURCE_SLAB_THICKNESS_UM = 0.20
SOURCE_HALF_THICKNESS_UM = SOURCE_SLAB_THICKNESS_UM / 2.0

FORBIDDEN = {
    "fdtd_run_performed": False,
    "h1j4_fsp_opened_or_modified": False,
    "lumerical_rcwa_performed": False,
    "broadband_performed": False,
    "optimization_performed": False,
    "ml_dataset_generated": False,
    "push_performed": False,
}


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


def safe_json(value: Any) -> str:
    try:
        if hasattr(value, "tolist"):
            value = value.tolist()
        return json.dumps(value, default=str)
    except Exception:
        return repr(value)


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"unavailable: {type(exc).__name__}: {exc}"


def module_info(name: str) -> dict[str, Any]:
    row: dict[str, Any] = {"name": name, "import_ok": False, "version": "missing", "path": "missing"}
    try:
        mod = importlib.import_module(name)
        row.update({"import_ok": True, "version": getattr(mod, "__version__", "missing"), "path": getattr(mod, "__file__", "missing")})
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def api_usage() -> list[dict[str, Any]]:
    from fmmax import basis, fields, fmm, scattering, sources

    items = [
        ("basis", "LatticeVectors", basis.LatticeVectors, "unit-cell lattice"),
        ("basis", "generate_expansion", basis.generate_expansion, "minimal Fourier expansion"),
        ("fmm", "eigensolve_isotropic_media", fmm.eigensolve_isotropic_media, "uniform layer eigensolve for air/source/SiO2/TiO2"),
        ("scattering", "stack_s_matrix", scattering.stack_s_matrix, "top/source/bottom stack scattering matrix"),
        ("sources", "gaussian_source", sources.gaussian_source, "single localized source proxy"),
        ("sources", "amplitudes_for_source", sources.amplitudes_for_source, "source current to wave amplitudes"),
        ("fields", "directional_poynting_flux", fields.directional_poynting_flux, "top/bottom directional Poynting-flux-like scalar"),
    ]
    rows = []
    for module, name, obj, role in items:
        rows.append({
            "stage": STAGE,
            "module": module,
            "api_name": name,
            "role": role,
            "signature": str(inspect.signature(obj)),
            "doc_first_line": (inspect.getdoc(obj) or "missing").splitlines()[0],
        })
    return rows


def dbr_layers(pair_count: int) -> tuple[list[str], list[float]]:
    materials: list[str] = []
    thicknesses: list[float] = []
    for _ in range(pair_count):
        materials.extend(["TiO2", "SiO2"])
        thicknesses.extend([T_TIO2_UM, T_SIO2_UM])
    return materials, thicknesses


def case_defs() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "homogeneous_air_reference",
            "structure_type": "homogeneous_air",
            "dbr_pair_count": 0,
            "before_materials": ["air", "air"],
            "before_thicknesses_um": [0.0, 0.0],
            "after_materials": ["air", "air"],
            "after_thicknesses_um": [0.0, 0.0],
            "source_layer_material": "air",
        },
        {
            "case_id": "single_dielectric_slab_reference",
            "structure_type": "single_source_slab_in_air",
            "dbr_pair_count": 0,
            "before_materials": ["air", "source_slab"],
            "before_thicknesses_um": [0.0, SOURCE_HALF_THICKNESS_UM],
            "after_materials": ["source_slab", "air"],
            "after_thicknesses_um": [SOURCE_HALF_THICKNESS_UM, 0.0],
            "source_layer_material": "source_slab",
        },
        *[
            {
                "case_id": f"TiO2_SiO2_{pairs}pair_DBR_tiny" if pairs != 10 else "TiO2_SiO2_10pair_DBR_H1J4_like_tiny",
                "structure_type": "source_slab_with_bottom_dbr_proxy",
                "dbr_pair_count": pairs,
                "before_materials": ["air", "source_slab"],
                "before_thicknesses_um": [0.0, SOURCE_HALF_THICKNESS_UM],
                "after_materials": ["source_slab", *dbr_layers(pairs)[0], "air"],
                "after_thicknesses_um": [SOURCE_HALF_THICKNESS_UM, *dbr_layers(pairs)[1], 0.0],
                "source_layer_material": "source_slab",
            }
            for pairs in [2, 4, 10]
        ],
    ]


def run_case(case: dict[str, Any], attempt_log: list[dict[str, Any]]) -> dict[str, Any]:
    import jax
    import jax.numpy as jnp
    from fmmax import basis, fields, fmm, scattering, sources

    start = time.perf_counter()
    row: dict[str, Any] = {"stage": STAGE, "case_id": case["case_id"], "status": "not_run"}
    try:
        lattice = basis.LatticeVectors(u=jnp.array([1.0, 0.0]), v=jnp.array([0.0, 1.0]))
        expansion = basis.generate_expansion(lattice, approximate_num_terms=1)
        k0 = jnp.array([0.0, 0.0])
        wavelength = jnp.array(WL_UM)
        eps_by_material = {
            "air": N_AIR**2,
            "SiO2": N_SIO2**2,
            "TiO2": N_TIO2**2,
            "source_slab": N_SOURCE_SLAB**2,
        }
        solve_cache: dict[str, Any] = {}

        def solve(material: str):
            if material not in solve_cache:
                solve_cache[material] = fmm.eigensolve_isotropic_media(
                    wavelength, k0, lattice, jnp.array([[eps_by_material[material]]]), expansion
                )
            return solve_cache[material]

        source = sources.gaussian_source(jnp.array(0.20), jnp.array([[0.5, 0.5]]), k0, lattice, expansion).reshape((-1, 1))
        zero = jnp.zeros_like(source)
        before_layers = [solve(m) for m in case["before_materials"]]
        after_layers = [solve(m) for m in case["after_materials"]]
        before = scattering.stack_s_matrix(before_layers, [jnp.array(v) for v in case["before_thicknesses_um"]])
        after = scattering.stack_s_matrix(after_layers, [jnp.array(v) for v in case["after_thicknesses_um"]])
        (
            backward_amp_0_end,
            _forward_amp_before_start,
            backward_amp_before_end,
            forward_amp_after_start,
            _backward_amp_after_end,
            forward_amp_N_start,
        ) = sources.amplitudes_for_source(source, zero, zero, before, after)

        air = solve("air")
        source_layer = solve(case["source_layer_material"])
        top_flux_raw = fields.directional_poynting_flux(jnp.zeros_like(backward_amp_0_end), backward_amp_0_end, air)
        bottom_flux_raw = fields.directional_poynting_flux(forward_amp_N_start, jnp.zeros_like(forward_amp_N_start), air)
        source_flux_raw = fields.directional_poynting_flux(forward_amp_after_start, backward_amp_before_end, source_layer)
        top_flux = float(jnp.abs(top_flux_raw[1]).sum().block_until_ready())
        bottom_flux = float(jnp.abs(bottom_flux_raw[0]).sum().block_until_ready())
        total_flux = top_flux + bottom_flux
        amp_norm = float(jnp.linalg.norm(forward_amp_N_start).block_until_ready() + jnp.linalg.norm(backward_amp_0_end).block_until_ready())
        source_norm = float(jnp.linalg.norm(source).block_until_ready())
        row.update({
            "status": "ok",
            "structure_type": case["structure_type"],
            "wavelength_um": WL_UM,
            "source_proxy": "gaussian_source",
            "source_position_convention": "FMMAX in-plane gaussian at normalized cell location (0.5,0.5); z-location represented by interface between before/after source_slab half-stacks",
            "source_layer_material": case["source_layer_material"],
            "source_slab_n": N_SOURCE_SLAB,
            "n_air": N_AIR,
            "n_SiO2": N_SIO2,
            "n_TiO2": N_TIO2,
            "TiO2_thickness_um": T_TIO2_UM,
            "SiO2_thickness_um": T_SIO2_UM,
            "dbr_pair_count": case["dbr_pair_count"],
            "before_materials": ";".join(case["before_materials"]),
            "after_materials": ";".join(case["after_materials"]),
            "top_flux": top_flux,
            "bottom_flux": bottom_flux,
            "total_outward_flux": total_flux,
            "top_fraction": top_flux / total_flux if total_flux > 0 else "missing",
            "bottom_fraction": bottom_flux / total_flux if total_flux > 0 else "missing",
            "top_bottom_ratio": top_flux / bottom_flux if bottom_flux > 0 else "inf",
            "source_norm_debug_proxy": source_norm,
            "amplitude_norm_debug_proxy": amp_norm,
            "source_region_directional_flux_abs_sum": float((jnp.abs(source_flux_raw[0]).sum() + jnp.abs(source_flux_raw[1]).sum()).block_until_ready()),
            "true_flux_metric_extracted": True,
            "flux_metric_api": "fmmax.fields.directional_poynting_flux",
            "raw_top_directional_flux_forward": safe_json(top_flux_raw[0]),
            "raw_top_directional_flux_backward": safe_json(top_flux_raw[1]),
            "raw_bottom_directional_flux_forward": safe_json(bottom_flux_raw[0]),
            "raw_bottom_directional_flux_backward": safe_json(bottom_flux_raw[1]),
            "runtime_seconds": time.perf_counter() - start,
            "jax_devices": safe_json(jax.devices()),
            "warning": "Poynting-flux-like scalar is useful as a tiny label prototype but is not absolute physical calibration or convergence-validated.",
        })
    except Exception as exc:
        row.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}", "runtime_seconds": time.perf_counter() - start})
    attempt_log.append({
        "stage": STAGE,
        "attempt": f"tiny_dbr_slab_case_{case['case_id']}",
        "status": row.get("status"),
        "runtime_seconds": row.get("runtime_seconds"),
        "error": row.get("error", ""),
        "notes": row.get("warning", ""),
    })
    return row


def artifact_manifest() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(OUT.glob("*")):
        if path.is_file():
            rows.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "committable": True})
    return rows


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}; current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)

    env_rows: list[dict[str, Any]] = [
        {"name": "sys.executable", "value": sys.executable},
        {"name": "sys.version", "value": sys.version.replace("\n", " ")},
        {"name": "platform", "value": platform.platform()},
    ]
    for module in ["numpy", "scipy", "jax", "jaxlib", "fmmax"]:
        env_rows.append(module_info(module))

    attempt_log: list[dict[str, Any]] = []
    api_rows: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    try:
        api_rows = api_usage()
        for case in case_defs():
            results.append(run_case(case, attempt_log))
    except Exception as exc:
        attempt_log.append({"stage": STAGE, "attempt": "api_or_case_setup", "status": "failed", "error": f"{type(exc).__name__}: {exc}"})

    ok_ids = {r.get("case_id") for r in results if r.get("status") == "ok" and r.get("true_flux_metric_extracted") is True}
    required_ok = {"homogeneous_air_reference", "single_dielectric_slab_reference"}
    dbr_ok = any(str(cid).startswith("TiO2_SiO2_") for cid in ok_ids)
    if required_ok.issubset(ok_ids) and dbr_ok:
        decision = "fmmax_dbr_slab_dipole_table_pass"
    elif required_ok.issubset(ok_ids):
        decision = "fmmax_dbr_slab_dipole_table_partial"
    else:
        decision = "fmmax_dbr_slab_dipole_table_fail"

    summary = {
        "stage": STAGE,
        "previous_stage_commit": PREVIOUS_STAGE_COMMIT,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "branch": git(["branch", "--show-current"]),
        "head_before_commit": git(["rev-parse", "--short", "HEAD"]),
        "python_launcher_required": "py -3.12",
        "api_chain_reused_from_fmm2c2": "basis -> fmm.eigensolve_isotropic_media -> scattering.stack_s_matrix -> sources.amplitudes_for_source -> fields.directional_poynting_flux",
        "wavelength_um": WL_UM,
        "case_count": len(results),
        "ok_case_count": sum(1 for r in results if r.get("status") == "ok"),
        "dbr_case_count": sum(1 for r in results if str(r.get("case_id", "")).startswith("TiO2_SiO2_")),
        "dbr_ok_case_count": sum(1 for r in results if str(r.get("case_id", "")).startswith("TiO2_SiO2_") and r.get("status") == "ok"),
        "decision": decision,
        "ml_label_embryo_assessment": "yes_tiny_scalar_label_embryo_not_dataset" if decision == "fmmax_dbr_slab_dipole_table_pass" else "not_ready",
        "next_recommendation": "FMM2C4 tiny source-position/orientation averaging" if decision == "fmmax_dbr_slab_dipole_table_pass" else "reduce DBR complexity or clone official example/custom flux path",
        **FORBIDDEN,
    }

    write_csv(OUT / "fmm2c3_fmmax_api_usage.csv", api_rows)
    write_csv(OUT / "fmm2c3_tiny_extraction_results.csv", results)
    write_csv(OUT / "fmm2c3_attempt_log.csv", attempt_log)
    (OUT / "fmm2c3_fmmax_dbr_slab_dipole_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    table_lines = [
        "| case | status | top_flux | bottom_flux | total_outward_flux | top_fraction | top/bottom | runtime_s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        table_lines.append(
            f"| {row.get('case_id')} | {row.get('status')} | {row.get('top_flux', 'missing')} | {row.get('bottom_flux', 'missing')} | {row.get('total_outward_flux', 'missing')} | {row.get('top_fraction', 'missing')} | {row.get('top_bottom_ratio', 'missing')} | {row.get('runtime_seconds', 'missing')} |"
        )
    dbr_note = "missing"
    refs = {r["case_id"]: r for r in results if r.get("status") == "ok"}
    if "single_dielectric_slab_reference" in refs:
        slab_top = float(refs["single_dielectric_slab_reference"]["top_fraction"])
        dbrs = [r for r in results if str(r.get("case_id", "")).startswith("TiO2_SiO2_") and r.get("status") == "ok"]
        if dbrs:
            max_top = max(float(r["top_fraction"]) for r in dbrs)
            dbr_note = f"DBR-like cases changed top fraction from slab reference {slab_top:.4f} to max {max_top:.4f}."
    md = f"""
# FMM2C3 FMMAX tiny DBR/slab dipole extraction table

## 中文报告

1. 本阶段做了 Python-only FMMAX tiny DBR/slab dipole extraction table：固定 453 nm-like wavelength、单个 Gaussian localized source proxy、minimal Fourier expansion，只跑 5 个 tiny fixed cases。
2. 沿用了 FMM2C2 validated API chain：`basis` -> `fmm.eigensolve_isotropic_media` -> `scattering.stack_s_matrix` -> `sources.amplitudes_for_source` -> `fields.directional_poynting_flux`。
3. 跑的 tiny stack cases：homogeneous air、single dielectric slab、TiO2/SiO2 2-pair DBR、4-pair DBR、10-pair H1J4-like tiny DBR。
4. `directional_poynting_flux` 输出被标记为 FMMAX Poynting-flux-like scalar；这里不声称绝对物理校准，也没有做 convergence study。
5. DBR-like stack 是否改变通量分配：{dbr_note}
6. 是否具备 ML label 雏形：`{summary['ml_label_embryo_assessment']}`。它只是 tiny scalar-label prototype，还不是 ML dataset generation。
7. 下一步建议：`{summary['next_recommendation']}`。
8. 明确限制：没有 FDTD；没有打开或修改 H1J4 FSP；没有 Lumerical RCWA；没有 broadband；没有 optimization；没有 ML dataset；没有 push。
9. decision = `{decision}`。

## Top/bottom flux table

{chr(10).join(table_lines)}

## Source placement convention

- In-plane Gaussian source proxy location is normalized unit-cell `(0.5, 0.5)`.
- z placement is represented by the source interface between the top half and bottom half of the source slab stack.
- DBR cases place TiO2/SiO2 pairs below the central source slab, so the table tests whether a simple bottom DBR proxy redirects FMMAX directional Poynting flux upward.
"""
    write_md(OUT / "fmm2c3_fmmax_dbr_slab_dipole_report.md", md)
    write_csv(OUT / "fmm2c3_artifact_manifest.csv", artifact_manifest())
    write_csv(OUT / "fmm2c3_environment_inventory.csv", env_rows)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
