from __future__ import annotations

import ast
import csv
import importlib
import inspect
import json
import os
import platform
import pkgutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4fmm2c1_fmmax_dipole_bz_smoke"
STAGE = "FMM2C1"
KEYWORDS = ["dipole", "metal_dipole", "source", "brillouin", "bz", "gaussian", "crystal", "amplitude", "flux", "poynting"]
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


def safe_str(value: Any, limit: int = 2000) -> str:
    try:
        if hasattr(value, "tolist"):
            value = value.tolist()
        text = json.dumps(value, default=str) if isinstance(value, (dict, list, tuple)) else str(value)
    except Exception:
        text = repr(value)
    return text[:limit]


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"unavailable: {exc}"


def import_info(name: str) -> dict[str, Any]:
    row = {"name": name, "import_ok": False, "version": "missing", "path": "missing"}
    try:
        mod = importlib.import_module(name)
        row.update({"import_ok": True, "version": getattr(mod, "__version__", "missing"), "path": getattr(mod, "__file__", "missing")})
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def ast_symbols(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(node.name)
    return out


def module_inventory(fmmax_pkg) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mod in pkgutil.iter_modules(fmmax_pkg.__path__):
        full = f"fmmax.{mod.name}"
        row = {"module": full, "is_package": mod.ispkg, "import_ok": False}
        try:
            imported = importlib.import_module(full)
            row.update({"import_ok": True, "path": getattr(imported, "__file__", "missing")})
            callables = []
            for name, value in vars(imported).items():
                if name.startswith("_") or not callable(value):
                    continue
                try:
                    sig = str(inspect.signature(value))
                except Exception:
                    sig = "signature_unavailable"
                callables.append(f"{name}{sig}")
            row["public_callables_preview"] = " | ".join(callables[:12])
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return rows


def keyword_search(package_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(package_root.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lower = text.lower()
        hits = [kw for kw in KEYWORDS if kw.lower() in lower]
        if not hits:
            continue
        symbols = ast_symbols(path)
        matched_symbols = [s for s in symbols if any(kw.lower() in s.lower() for kw in KEYWORDS)]
        rows.append({
            "file": str(path),
            "relative_file": str(path.relative_to(package_root.parent)),
            "keywords": ";".join(hits),
            "matched_symbol_names": ";".join(matched_symbols[:20]),
            "symbol_count": len(symbols),
        })
    return rows


def tiny_smoke(log_rows: list[dict[str, Any]]) -> dict[str, Any]:
    row: dict[str, Any] = {"stage": STAGE, "attempt": "localized_source_bz_api_smoke", "status": "not_run"}
    start = time.perf_counter()
    try:
        import jax
        import jax.numpy as jnp
        from fmmax import basis, sources

        lattice = basis.LatticeVectors(u=jnp.array([1.0, 0.0]), v=jnp.array([0.0, 1.0]))
        expansion = basis.generate_expansion(lattice, approximate_num_terms=1)
        k_bz = basis.brillouin_zone_in_plane_wavevector((1, 1), lattice)
        k0 = jnp.array([0.0, 0.0])
        location = jnp.array([[0.25, 0.25]])
        dirac = sources.dirac_delta_source(location, k0, lattice, expansion)
        gaussian = sources.gaussian_source(jnp.array(0.20), location, k0, lattice, expansion)
        dirac_norm = float(jnp.linalg.norm(dirac).block_until_ready())
        gaussian_norm = float(jnp.linalg.norm(gaussian).block_until_ready())
        bz_norm = float(jnp.linalg.norm(k_bz).block_until_ready())
        row.update({
            "status": "ok",
            "runtime_seconds": time.perf_counter() - start,
            "expansion_term_count": int(expansion.basis_coefficients.shape[0]),
            "brillouin_grid_shape": safe_str(k_bz.shape),
            "dirac_source_shape": safe_str(dirac.shape),
            "gaussian_source_shape": safe_str(gaussian.shape),
            "dirac_source_norm": dirac_norm,
            "gaussian_source_norm": gaussian_norm,
            "brillouin_wavevector_norm": bz_norm,
            "scalar_result_type": "source_amplitude_norm_and_bz_wavevector_norm",
            "radiated_power_or_flux_computed": False,
            "notes": "Tiny API smoke only: localized source Fourier amplitudes and BZ wavevector construction, not full radiated-power solve.",
        })
    except Exception as exc:
        row.update({"status": "failed", "runtime_seconds": time.perf_counter() - start, "error": f"{type(exc).__name__}: {exc}"})
    log_rows.append(row)
    return row


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}; current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)

    env_rows = [
        {"name": "sys.executable", "value": sys.executable},
        {"name": "sys.version", "value": sys.version.replace("\n", " ")},
        {"name": "platform", "value": platform.platform()},
    ]
    for name in ["numpy", "scipy", "jax", "jaxlib", "fmmax"]:
        info = import_info(name)
        env_rows.append({"name": name, **info})
    jax_devices = "missing"
    fmmax_path = "missing"
    fmmax_version = "missing"
    module_rows: list[dict[str, Any]] = []
    keyword_rows: list[dict[str, Any]] = []
    try:
        import jax
        jax_devices = safe_str(jax.devices())
    except Exception as exc:
        jax_devices = f"failed: {type(exc).__name__}: {exc}"
    try:
        import fmmax
        fmmax_path = str(Path(fmmax.__file__).parent)
        fmmax_version = getattr(fmmax, "__version__", "missing")
        module_rows = module_inventory(fmmax)
        keyword_rows = keyword_search(Path(fmmax_path))
    except Exception as exc:
        keyword_rows.append({"file": "fmmax_import", "keywords": "", "error": f"{type(exc).__name__}: {exc}"})
    env_rows.extend([
        {"name": "jax.devices", "value": jax_devices},
        {"name": "fmmax_import_path", "value": fmmax_path},
        {"name": "fmmax_version", "value": fmmax_version},
    ])

    smoke_rows: list[dict[str, Any]] = []
    smoke = tiny_smoke(smoke_rows)
    relevant_api_found = any(any(k in r.get("keywords", "") for k in ["dipole", "source", "brillouin", "gaussian"]) for r in keyword_rows)
    imports_ok = any(r.get("name") == "fmmax" and r.get("import_ok") is True for r in env_rows)
    if imports_ok and relevant_api_found and smoke.get("status") == "ok":
        decision = "fmmax_dipole_bz_smoke_pass"
    elif imports_ok and relevant_api_found:
        decision = "fmmax_dipole_bz_api_mapped_no_run"
    elif imports_ok:
        decision = "fmmax_backend_import_only"
    else:
        decision = "fmmax_backend_fail"

    summary = {
        "stage": STAGE,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "branch": git(["branch", "--show-current"]),
        "head": git(["rev-parse", "--short", "HEAD"]),
        "python_launcher_required": "py -3.12",
        "fmmax_import_ok": imports_ok,
        "fmmax_version": fmmax_version,
        "fmmax_path": fmmax_path,
        "jax_devices": jax_devices,
        "dipole_or_localized_source_or_bz_api_found": relevant_api_found,
        "tiny_smoke_status": smoke.get("status"),
        "tiny_smoke_scalar_outputs": {k: smoke.get(k) for k in ["dirac_source_norm", "gaussian_source_norm", "brillouin_wavevector_norm", "runtime_seconds"]},
        "decision": decision,
        "next_recommendation": "FMM2C2 tiny single-dipole slab metric" if decision == "fmmax_dipole_bz_smoke_pass" else "clone/read official examples or write custom minimal source-to-flux implementation before dataset work",
        **FORBIDDEN,
    }

    write_csv(OUT / "fmm2c1_environment_inventory.csv", env_rows)
    write_csv(OUT / "fmm2c1_fmmax_module_inventory.csv", module_rows)
    write_csv(OUT / "fmm2c1_fmmax_keyword_search.csv", keyword_rows)
    write_csv(OUT / "fmm2c1_tiny_smoke_attempt_log.csv", smoke_rows)
    write_csv(OUT / "fmm2c1_artifact_manifest.csv", [])
    (OUT / "fmm2c1_fmmax_dipole_bz_smoke_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    matched_files = sorted({Path(r["relative_file"]).as_posix() for r in keyword_rows if "relative_file" in r})
    lines = [
        "# FMM2C1 FMMAX localized-dipole / BZ smoke",
        "",
        "## 中文报告",
        "",
        "1. 本阶段做了 Python-only FMMAX/JAX 环境检查、fmmax 包 API inventory、关键词扫描，以及一个最小 localized-source/BZ API smoke。",
        f"2. FMMAX/JAX 当前环境是否可用：`{imports_ok}`；fmmax version=`{fmmax_version}`；JAX devices=`{jax_devices}`。",
        f"3. 是否找到 dipole/localized source/Brillouin-zone API 或 example 路径：`{relevant_api_found}`。关键模块包括 `fmmax.sources`, `fmmax.basis`, `fmmax.fields`, `fmmax.scattering`。",
        f"4. 是否跑了 tiny smoke test：`{smoke.get('status') == 'ok'}`。",
        f"5. tiny 结果：runtime={smoke.get('runtime_seconds')} s, dirac_source_norm={smoke.get('dirac_source_norm')}, gaussian_source_norm={smoke.get('gaussian_source_norm')}, bz_wavevector_norm={smoke.get('brillouin_wavevector_norm')}。该 smoke 只验证 source/BZ API 和轻量标量，不是完整辐射功率求解。",
        f"6. 若未完整 power/flux：原因是当前只调用 pip package 中最小 source/BZ API；radiated/extracted power 需要下一步构造 layer solve + scattering/source amplitude 链路。",
        f"7. 对 ML dataset 加速判断：`{summary['next_recommendation']}`。",
        "8. 明确限制：没有 FDTD；没有 H1J4 FSP；没有 Lumerical RCWA；没有 optimization；没有 ML dataset；没有 push。",
        f"9. decision = `{decision}`。",
        "",
        "## Matched files preview",
        "",
    ]
    for f in matched_files[:30]:
        lines.append(f"- `{f}`")
    write_md(OUT / "fmm2c1_fmmax_dipole_bz_smoke_report.md", "\n".join(lines))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
