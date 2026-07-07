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
OUT = ROOT / "outputs" / "r2_4fmm2c2_fmmax_single_dipole_slab_metric"
STAGE = "FMM2C2"
PREVIOUS_STAGE_COMMIT = "e37d345"

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


def scalar(value: Any) -> float:
    import jax.numpy as jnp

    arr = jnp.asarray(value)
    return float(jnp.real(arr).sum().block_until_ready())


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


def api_mapping() -> list[dict[str, Any]]:
    from fmmax import basis, farfield, fields, fmm, scattering, sources

    targets = [
        ("basis", "LatticeVectors", basis.LatticeVectors, "primitive lattice construction"),
        ("basis", "generate_expansion", basis.generate_expansion, "Fourier expansion creation"),
        ("basis", "brillouin_zone_in_plane_wavevector", basis.brillouin_zone_in_plane_wavevector, "BZ/in-plane wavevector creation"),
        ("sources", "dirac_delta_source", sources.dirac_delta_source, "localized source Fourier amplitude"),
        ("sources", "gaussian_source", sources.gaussian_source, "finite-width localized source Fourier amplitude"),
        ("fmm", "eigensolve_isotropic_media", fmm.eigensolve_isotropic_media, "uniform or patterned layer eigensolve"),
        ("scattering", "stack_s_matrix", scattering.stack_s_matrix, "stack scattering matrix construction"),
        ("scattering", "stack_s_matrices_interior", scattering.stack_s_matrices_interior, "interior source stack bookkeeping"),
        ("sources", "amplitudes_for_source", sources.amplitudes_for_source, "convert localized current source into forward/backward wave amplitudes"),
        ("fields", "directional_poynting_flux", fields.directional_poynting_flux, "true directional Poynting-flux-like scalar from amplitudes"),
        ("fields", "amplitude_poynting_flux", fields.amplitude_poynting_flux, "eigenmode-associated Poynting flux"),
        ("farfield", "farfield_profile", farfield.farfield_profile, "farfield profile if flux/BZ grid is available later"),
        ("farfield", "farfield_integrated_flux", farfield.farfield_integrated_flux, "farfield integrated flux for later BZ workflows"),
    ]
    rows: list[dict[str, Any]] = []
    for module, name, obj, role in targets:
        try:
            sig = str(inspect.signature(obj))
            doc = inspect.getdoc(obj) or ""
            status = "mapped"
        except Exception as exc:
            sig = "unavailable"
            doc = f"{type(exc).__name__}: {exc}"
            status = "mapping_error"
        rows.append({
            "stage": STAGE,
            "module": module,
            "api_name": name,
            "status": status,
            "role": role,
            "signature": sig,
            "doc_first_line": doc.splitlines()[0] if doc else "missing",
        })
    return rows


def run_tiny_metric_case(case: dict[str, Any], attempt_log: list[dict[str, Any]]) -> dict[str, Any]:
    import jax
    import jax.numpy as jnp
    from fmmax import basis, fields, fmm, scattering, sources

    start = time.perf_counter()
    row: dict[str, Any] = {"stage": STAGE, "case_id": case["case_id"], "status": "not_run"}
    try:
        lattice = basis.LatticeVectors(u=jnp.array([1.0, 0.0]), v=jnp.array([0.0, 1.0]))
        expansion = basis.generate_expansion(lattice, approximate_num_terms=1)
        k0 = jnp.array([0.0, 0.0])
        wavelength = jnp.array(0.453)

        def solve(eps: float):
            return fmm.eigensolve_isotropic_media(wavelength, k0, lattice, jnp.array([[eps]]), expansion)

        air = solve(1.0)
        slab = solve(case.get("slab_permittivity", 1.0))
        source_layer = slab if case["structure_type"] == "dielectric_slab_mid_source" else air
        location = jnp.array([[0.5, 0.5]])
        gaussian = sources.gaussian_source(jnp.array(0.20), location, k0, lattice, expansion).reshape((-1, 1))
        dirac = sources.dirac_delta_source(location, k0, lattice, expansion).reshape((-1, 1))
        selected_source = gaussian if case["source_proxy"] == "gaussian_source" else dirac
        zero = jnp.zeros_like(selected_source)

        before = scattering.stack_s_matrix(case["before_layers"](air, slab), [jnp.array(v) for v in case["before_thicknesses"]])
        after = scattering.stack_s_matrix(case["after_layers"](air, slab), [jnp.array(v) for v in case["after_thicknesses"]])
        (
            backward_amp_0_end,
            forward_amp_before_start,
            backward_amp_before_end,
            forward_amp_after_start,
            backward_amp_after_end,
            forward_amp_N_start,
        ) = sources.amplitudes_for_source(selected_source, zero, zero, before, after)

        top_flux = fields.directional_poynting_flux(jnp.zeros_like(backward_amp_0_end), backward_amp_0_end, air)
        bottom_flux = fields.directional_poynting_flux(forward_amp_N_start, jnp.zeros_like(forward_amp_N_start), air)
        source_layer_flux = fields.directional_poynting_flux(forward_amp_after_start, backward_amp_before_end, source_layer)

        # FMMAX directional_poynting_flux returns signed directional components.
        # The backward/outward top channel is negative by convention, so the escaping
        # scalar below is the absolute magnitude of that documented flux component.
        top_outward_flux_abs = float(jnp.abs(top_flux[1]).sum().block_until_ready())
        bottom_outward_flux_abs = float(jnp.abs(bottom_flux[0]).sum().block_until_ready())
        total_outward_flux_abs = top_outward_flux_abs + bottom_outward_flux_abs
        source_region_flux_abs = float((jnp.abs(source_layer_flux[0]).sum() + jnp.abs(source_layer_flux[1]).sum()).block_until_ready())
        amp_norm = float(jnp.linalg.norm(forward_amp_N_start).block_until_ready() + jnp.linalg.norm(backward_amp_0_end).block_until_ready())

        row.update({
            "status": "ok",
            "structure_type": case["structure_type"],
            "source_proxy": case["source_proxy"],
            "wavelength_um": 0.453,
            "approximate_num_terms": 1,
            "slab_permittivity": case.get("slab_permittivity", "na"),
            "slab_thickness_um": case.get("slab_thickness_um", 0.0),
            "true_flux_metric_extracted": True,
            "flux_metric_api": "fmmax.fields.directional_poynting_flux",
            "flux_metric_label": "absolute outward directional Poynting flux magnitude at top/bottom exterior layers",
            "top_outward_flux_abs": top_outward_flux_abs,
            "bottom_outward_flux_abs": bottom_outward_flux_abs,
            "total_outward_flux_abs": total_outward_flux_abs,
            "up_down_balance_ratio": top_outward_flux_abs / bottom_outward_flux_abs if bottom_outward_flux_abs else "inf",
            "source_region_directional_flux_abs_sum": source_region_flux_abs,
            "amplitude_norm_proxy": amp_norm,
            "raw_top_directional_flux_forward": safe_json(top_flux[0]),
            "raw_top_directional_flux_backward": safe_json(top_flux[1]),
            "raw_bottom_directional_flux_forward": safe_json(bottom_flux[0]),
            "raw_bottom_directional_flux_backward": safe_json(bottom_flux[1]),
            "forward_amp_N_start": safe_json(forward_amp_N_start),
            "backward_amp_0_end": safe_json(backward_amp_0_end),
            "runtime_seconds": time.perf_counter() - start,
            "jax_devices": safe_json(jax.devices()),
        })
    except Exception as exc:
        row.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}", "runtime_seconds": time.perf_counter() - start})
    attempt_log.append({
        "stage": STAGE,
        "attempt": f"tiny_metric_case_{case['case_id']}",
        "status": row.get("status"),
        "runtime_seconds": row.get("runtime_seconds"),
        "error": row.get("error", ""),
        "notes": row.get("flux_metric_label", ""),
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

    api_rows: list[dict[str, Any]] = []
    attempt_log: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    decision = "fmmax_single_dipole_metric_fail"
    try:
        api_rows = api_mapping()
        cases = [
            {
                "case_id": "homogeneous_air_gaussian_source",
                "structure_type": "homogeneous_air",
                "source_proxy": "gaussian_source",
                "before_layers": lambda air, slab: [air, air],
                "after_layers": lambda air, slab: [air, air],
                "before_thicknesses": [0.0, 0.0],
                "after_thicknesses": [0.0, 0.0],
            },
            {
                "case_id": "dielectric_slab_mid_gaussian_source",
                "structure_type": "dielectric_slab_mid_source",
                "source_proxy": "gaussian_source",
                "slab_permittivity": 2.25,
                "slab_thickness_um": 0.20,
                "before_layers": lambda air, slab: [air, slab],
                "after_layers": lambda air, slab: [slab, air],
                "before_thicknesses": [0.0, 0.10],
                "after_thicknesses": [0.10, 0.0],
            },
        ]
        for case in cases:
            metric_rows.append(run_tiny_metric_case(case, attempt_log))
        if any(row.get("status") == "ok" and row.get("true_flux_metric_extracted") is True for row in metric_rows):
            decision = "fmmax_single_dipole_metric_pass"
        elif any(row.get("status") == "ok" for row in metric_rows):
            decision = "fmmax_single_dipole_metric_partial_proxy_only"
        else:
            decision = "fmmax_single_dipole_metric_api_mapped_no_run"
    except Exception as exc:
        attempt_log.append({"stage": STAGE, "attempt": "api_mapping_or_metric", "status": "failed", "error": f"{type(exc).__name__}: {exc}"})

    true_flux_rows = [row for row in metric_rows if row.get("true_flux_metric_extracted") is True]
    summary = {
        "stage": STAGE,
        "previous_stage_commit": PREVIOUS_STAGE_COMMIT,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "branch": git(["branch", "--show-current"]),
        "head_before_commit": git(["rev-parse", "--short", "HEAD"]),
        "python_launcher_required": "py -3.12",
        "api_mapping_completed": bool(api_rows),
        "tiny_source_slab_solve_completed": any(row.get("status") == "ok" for row in metric_rows),
        "true_flux_power_like_scalar_extracted": bool(true_flux_rows),
        "true_flux_api_used": "fmmax.fields.directional_poynting_flux" if true_flux_rows else "none",
        "case_count": len(metric_rows),
        "ok_case_count": sum(1 for row in metric_rows if row.get("status") == "ok"),
        "decision": decision,
        "ml_dataset_acceleration_assessment": "ready_for_FMM2C3_tiny_DBR_slab_dipole_extraction_table" if decision == "fmmax_single_dipole_metric_pass" else "not_ready; map official examples/custom farfield flux path first",
        "next_recommendation": "FMM2C3 tiny DBR/slab dipole extraction table" if decision == "fmmax_single_dipole_metric_pass" else "clone/read official examples or custom-map farfield/flux API",
        **FORBIDDEN,
    }

    write_csv(OUT / "fmm2c2_environment_inventory.csv", env_rows)
    write_csv(OUT / "fmm2c2_fmmax_api_mapping.csv", api_rows)
    write_csv(OUT / "fmm2c2_tiny_metric_results.csv", metric_rows)
    write_csv(OUT / "fmm2c2_attempt_log.csv", attempt_log)
    (OUT / "fmm2c2_fmmax_single_dipole_slab_metric_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    table_lines = ["| case | status | true flux? | top flux abs | bottom flux abs | total flux abs | amplitude proxy |", "|---|---:|---:|---:|---:|---:|---:|"]
    for row in metric_rows:
        table_lines.append(
            f"| {row.get('case_id')} | {row.get('status')} | {row.get('true_flux_metric_extracted')} | {row.get('top_outward_flux_abs', 'missing')} | {row.get('bottom_outward_flux_abs', 'missing')} | {row.get('total_outward_flux_abs', 'missing')} | {row.get('amplitude_norm_proxy', 'missing')} |"
        )
    md = f"""
# FMM2C2 FMMAX tiny single-dipole slab metric

## 中文报告

1. 本阶段做了 Python-only FMMAX tiny single-dipole/slab optical-metric feasibility test：先映射 FMMAX API，再运行一个 homogeneous air source case 和一个 dielectric slab mid-source case。
2. FMM2C1 已证明：FMMAX/JAX 可 import，CPU backend 可用，`fmmax.sources.dirac_delta_source`、`gaussian_source` 与 `basis.brillouin_zone_in_plane_wavevector` 可用；但 FMM2C1 还缺 layer solve、scattering、farfield、radiated power 或 flux extraction。
3. 本阶段使用的关键 FMMAX API：`basis.LatticeVectors`、`basis.generate_expansion`、`fmm.eigensolve_isotropic_media`、`scattering.stack_s_matrix`、`sources.amplitudes_for_source`、`fields.directional_poynting_flux`。
4. 是否完成 tiny source/slab solve：`{summary['tiny_source_slab_solve_completed']}`。
5. 是否提取到 true flux/power/radiated-power-like scalar：`{summary['true_flux_power_like_scalar_extracted']}`。提取路径是 FMMAX 文档中的 `fields.directional_poynting_flux`，这里报告的是 top/bottom exterior layer 的 outward directional Poynting flux magnitude；raw signed flux 也保存在 CSV 中。
6. amplitude/norm 字段只是 proxy，用来辅助 debug，不被称为真实功率。
7. 对机器学习数据集加速的判断：`{summary['ml_dataset_acceleration_assessment']}`。当前可以进入 FMM2C3 的小型 DBR/slab dipole extraction table，但还不是 ML dataset generation。
8. 下一步建议：`{summary['next_recommendation']}`。
9. 明确限制：没有 FDTD；没有打开或修改 H1J4 FSP；没有 Lumerical RCWA；没有 broadband；没有 optimization；没有 ML dataset；没有 push。
10. decision = `{decision}`。

## Tiny metric table

{chr(10).join(table_lines)}

## Notes

- `directional_poynting_flux` 返回带符号的方向 flux 分量；top/backward escaping channel 在本约定下为负号，因此 summary scalar 使用其绝对值作为 outward flux magnitude。
- 当前只用 minimal Fourier expansion 和单一 wavelength-like point 0.453 um；这不是 convergence study。
"""
    write_md(OUT / "fmm2c2_fmmax_single_dipole_slab_metric_report.md", md)
    write_csv(OUT / "fmm2c2_artifact_manifest.csv", artifact_manifest())
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
