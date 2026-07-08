from __future__ import annotations

import csv
import inspect
import json
import math
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_defect_450")
OUT = ROOT / "outputs" / "mdc1c2_fmmax_minimal_dipole"
REPORT_DIR = ROOT / "reports" / "mdc_defect_450"
OUT.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAGE = "MDC1C2_FMMAX_minimal_single_dipole"
WAVELENGTH_NM = 450.0
APPROXIMATE_NUM_TERMS = 50
PITCH_NM = 1200.0
DIPOLE_FWHM_NM = 80.0

NIDX = {
    "Air": 1.0,
    "SiO2": 1.426,
    "TiO2": 2.535,
    "GaN": 2.41,
}

CANDIDATES = [
    {
        "candidate_id": "BARE_GaN_Air",
        "role": "bare_reference",
        "design_layers": [],
    },
    {
        "candidate_id": "MDC-A0-INT",
        "role": "rounded_reference",
        "design_layers": [("SiO2",79),("TiO2",44)]*3 + [("SiO2",158)] + [("TiO2",44),("SiO2",79)]*3,
    },
    {
        "candidate_id": "MDC1B_FAB_0126",
        "role": "baseline_fab",
        "design_layers": [("SiO2",79),("TiO2",45)]*3 + [("SiO2",156)] + [("TiO2",45),("SiO2",79)]*3,
    },
    {
        "candidate_id": "MDC1B_PERF_0890",
        "role": "performance_anchor",
        "design_layers": [("SiO2",81),("TiO2",44)]*4 + [("SiO2",157)] + [("TiO2",44),("SiO2",81)]*4,
    },
]

def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"unavailable: {exc}"

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def safe_json(x: Any, limit: int = 6000) -> str:
    try:
        if hasattr(x, "tolist"):
            x = x.tolist()
        text = json.dumps(x, default=str, ensure_ascii=False)
    except Exception:
        text = repr(x)
    return text[:limit]

def scalar_sum(x: Any) -> float:
    import numpy as np
    arr = np.asarray(x)
    if arr.size == 0:
        return float("nan")
    return float(np.real(np.sum(arr)))

def import_fmmax():
    import fmmax
    from fmmax import basis, fmm, scattering, sources, fields
    import jax
    import jax.numpy as jnp
    return fmmax, basis, fmm, scattering, sources, fields, jax, jnp

def make_expansion(basis, jnp):
    lattice = basis.LatticeVectors(
        u=jnp.asarray([PITCH_NM, 0.0]),
        v=jnp.asarray([0.0, PITCH_NM]),
    )

    kwargs = {
        "primitive_lattice_vectors": lattice,
        "approximate_num_terms": APPROXIMATE_NUM_TERMS,
    }

    if hasattr(basis, "Truncation"):
        for name in ["CIRCULAR", "PARALLELOGRAMIC", "CIRCULAR_TRUNCATION"]:
            if hasattr(basis.Truncation, name):
                kwargs["truncation"] = getattr(basis.Truncation, name)
                break

    expansion = basis.generate_expansion(**kwargs)
    return lattice, expansion

def formulation_or_none(fmm):
    if hasattr(fmm, "Formulation"):
        for name in ["JONES_DIRECT", "JONES", "FFT"]:
            if hasattr(fmm.Formulation, name):
                return getattr(fmm.Formulation, name)
    return None

def eigensolve_one(fmm, jnp, mat: str, wavelength_nm, in_plane_wavevector, lattice, expansion, formulation):
    kwargs = {
        "permittivity": jnp.full((1, 1), NIDX[mat] ** 2),
        "wavelength": jnp.asarray(wavelength_nm),
        "in_plane_wavevector": in_plane_wavevector,
        "primitive_lattice_vectors": lattice,
        "expansion": expansion,
    }
    if formulation is not None:
        kwargs["formulation"] = formulation
    return fmm.eigensolve_isotropic_media(**kwargs)

def call_stack(scattering, solve_results, thicknesses):
    """
    FMMAX versions differ. Try the APIs known from previous RCLED work first.
    """
    if hasattr(scattering, "stack_s_matrix"):
        return scattering.stack_s_matrix(solve_results, thicknesses)
    if hasattr(scattering, "stack_s_matrices_interior"):
        out = scattering.stack_s_matrices_interior(solve_results, thicknesses)
        try:
            return out[-1][0]
        except Exception:
            return out
    raise RuntimeError("No supported FMMAX stack matrix API found.")

def top_to_bottom_layers(candidate: dict[str, Any]):
    """
    FMM stack top-to-bottom:
        Air / design-side MDC / GaN_source_layer / GaN_substrate

    The source is placed in the GaN source layer just below MDC.
    """
    return [("Air", math.inf)] + candidate["design_layers"] + [("GaN", 120.0), ("GaN", math.inf)]

def thickness_array(jnp, layers):
    """
    This FMMAX version requires:
        len(layer_solve_results) == len(layer_thicknesses)

    Therefore every layer gets one thickness value.
    Semi-infinite bounding layers are represented by 0 thickness.
    Finite interior layers keep their physical thickness in nm.
    """
    vals = []
    for _mat, th in layers:
        vals.append(0.0 if math.isinf(th) else float(th))
    return jnp.asarray(vals)

def simulate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    fmmax, basis, fmm, scattering, sources, fields, jax, jnp = import_fmmax()

    lattice, expansion = make_expansion(basis, jnp)
    formulation = formulation_or_none(fmm)

    try:
        in_plane_wavevector = basis.brillouin_zone_in_plane_wavevector(
            (1, 1),
            lattice,
        )
    except TypeError:
        in_plane_wavevector = basis.brillouin_zone_in_plane_wavevector(
            grid_shape=(1, 1),
            primitive_lattice_vectors=lattice,
        )

    layers = top_to_bottom_layers(candidate)
    solve_results = tuple(
        eigensolve_one(fmm, jnp, mat, WAVELENGTH_NM, in_plane_wavevector, lattice, expansion, formulation)
        for mat, _th in layers
    )
    thicknesses = thickness_array(jnp, layers)

    s_matrix = call_stack(scattering, solve_results, thicknesses)

    # Try to build a Gaussian x-dipole-like localized current source.
    gaussian = sources.gaussian_source(
        fwhm=jnp.asarray(DIPOLE_FWHM_NM),
        location=jnp.asarray([(PITCH_NM / 2.0, PITCH_NM / 2.0)]),
        in_plane_wavevector=in_plane_wavevector,
        primitive_lattice_vectors=lattice,
        expansion=expansion,
    )

    zeros = jnp.zeros_like(gaussian)

    # FMMAX requires jx, jy, and jz to have matching shapes.
    # gaussian_source already returns the source-amplitude array.
    # For a minimal single x-oriented dipole-like source:
    #   jx = gaussian
    #   jy = 0
    #   jz = 0
    jx = gaussian
    jy = zeros
    jz = zeros

    # Because FMMAX versions differ in exact source-stack interface,
    # this block tries the known amplitudes_for_source pattern.
    try:
        result = sources.amplitudes_for_source(
            jx=jx,
            jy=jy,
            jz=jz,
            s_matrix_before_source=s_matrix,
            s_matrix_after_source=s_matrix,
        )
    except TypeError as exc:
        return {
            "candidate_id": candidate["candidate_id"],
            "role": candidate["role"],
            "status": "api_failed",
            "stage": "amplitudes_for_source",
            "error": str(exc),
        }

    result_repr = safe_json(result)
    numeric_score = None

    # Best-effort scalar diagnostic: sum absolute values of returned amplitudes.
    try:
        import numpy as np
        flat_total = 0.0
        if isinstance(result, (tuple, list)):
            for item in result:
                flat_total += float(np.sum(np.abs(np.asarray(item))))
        else:
            flat_total = float(np.sum(np.abs(np.asarray(result))))
        numeric_score = flat_total
    except Exception:
        numeric_score = None

    return {
        "candidate_id": candidate["candidate_id"],
        "role": candidate["role"],
        "status": "ok",
        "wavelength_nm": WAVELENGTH_NM,
        "dipole_model": "gaussian_x_dipole_like_source",
        "approximate_num_terms": APPROXIMATE_NUM_TERMS,
        "pitch_nm": PITCH_NM,
        "dipole_fwhm_nm": DIPOLE_FWHM_NM,
        "layer_count_design": len(candidate["design_layers"]),
        "amplitude_abs_sum_diagnostic": numeric_score,
        "result_repr_head": result_repr,
    }

def main() -> int:
    started = time.time()
    api = {
        "stage": STAGE,
        "created": datetime.now().isoformat(timespec="seconds"),
        "branch": git(["branch", "--show-current"]),
        "head": git(["rev-parse", "--short", "HEAD"]),
        "scope": "minimal FMMAX single x-dipole-like gaussian source closure; no Lumerical/FSP/FDTD",
        "settings": {
            "wavelength_nm": WAVELENGTH_NM,
            "approximate_num_terms": APPROXIMATE_NUM_TERMS,
            "pitch_nm": PITCH_NM,
            "dipole_fwhm_nm": DIPOLE_FWHM_NM,
        },
    }

    try:
        fmmax, basis, fmm, scattering, sources, fields, jax, jnp = import_fmmax()
        api["fmmax_version"] = getattr(fmmax, "__version__", "unknown")
        api["jax_version"] = getattr(jax, "__version__", "unknown")
        api["jax_devices"] = [str(d) for d in jax.devices()]
        api["signatures"] = {
            "basis.generate_expansion": str(inspect.signature(basis.generate_expansion)),
            "fmm.eigensolve_isotropic_media": str(inspect.signature(fmm.eigensolve_isotropic_media)),
            "sources.gaussian_source": str(inspect.signature(sources.gaussian_source)),
            "sources.amplitudes_for_source": str(inspect.signature(sources.amplitudes_for_source)),
            "fields.directional_poynting_flux": str(inspect.signature(fields.directional_poynting_flux)),
        }
        if hasattr(scattering, "stack_s_matrix"):
            api["signatures"]["scattering.stack_s_matrix"] = str(inspect.signature(scattering.stack_s_matrix))
        if hasattr(scattering, "stack_s_matrices_interior"):
            api["signatures"]["scattering.stack_s_matrices_interior"] = str(inspect.signature(scattering.stack_s_matrices_interior))
    except Exception:
        api["status"] = "import_failed"
        api["traceback"] = traceback.format_exc()
        (OUT / "mdc1c2_fmmax_api_info.json").write_text(json.dumps(api, indent=2, ensure_ascii=False), encoding="utf-8")
        print("FMMAX import failed")
        print(api["traceback"])
        return 1

    rows = []
    for cand in CANDIDATES:
        t0 = time.time()
        try:
            row = simulate_candidate(cand)
            row["runtime_seconds"] = time.time() - t0
            rows.append(row)
            print(f"{row['status']} {cand['candidate_id']} time={row['runtime_seconds']:.2f}s")
        except Exception:
            err = traceback.format_exc()
            print(f"failed {cand['candidate_id']}")
            print(err)
            rows.append({
                "candidate_id": cand["candidate_id"],
                "role": cand["role"],
                "status": "failed",
                "error": err[-3000:],
                "runtime_seconds": time.time() - t0,
            })

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    api_failed_rows = [r for r in rows if r.get("status") == "api_failed"]
    fail_rows = [r for r in rows if r.get("status") not in ["ok", "api_failed"]]

    api["ok_rows"] = len(ok_rows)
    api["api_failed_rows"] = len(api_failed_rows)
    api["failed_rows"] = len(fail_rows)
    api["runtime_seconds_total"] = time.time() - started
    api["status"] = "minimal_closure_ok" if len(ok_rows) >= 1 else "minimal_closure_not_completed"

    results_csv = OUT / "mdc1c2_fmmax_minimal_dipole_results.csv"
    write_csv(results_csv, rows)
    (OUT / "mdc1c2_fmmax_api_info.json").write_text(json.dumps(api, indent=2, ensure_ascii=False), encoding="utf-8")

    compact_csv = REPORT_DIR / "mdc1c2_fmmax_minimal_dipole_compact_results.csv"
    compact_rows = []
    for r in rows:
        compact_rows.append({
            "candidate_id": r.get("candidate_id"),
            "role": r.get("role"),
            "status": r.get("status"),
            "wavelength_nm": r.get("wavelength_nm", WAVELENGTH_NM),
            "amplitude_abs_sum_diagnostic": r.get("amplitude_abs_sum_diagnostic", ""),
            "runtime_seconds": r.get("runtime_seconds", ""),
            "error_or_stage": r.get("stage", r.get("error", ""))[:300] if isinstance(r.get("error", ""), str) else r.get("stage", ""),
        })
    write_csv(compact_csv, compact_rows)

    md = []
    md.append("# MDC1C2 FMMAX minimal single-dipole closure\n")
    md.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n")
    md.append("## Scope\n")
    md.append("This stage is a minimal FMMAX single x-dipole-like gaussian source closure probe for MDC. Uniform layer permittivity is represented as a 1x1 spatial grid, as required by FMMAX. Layer thickness arrays include one entry per layer, with semi-infinite bounding layers represented by zero thickness. The minimal source uses matching jx/jy/jz shapes, with only jx nonzero. It does not use Lumerical, does not open/save FSP, and does not run FDTD.\n")
    md.append("It is intentionally not the final noncoherent position average. Center/side incoherent averaging is deferred to 2D FDTD.\n")
    md.append("## Settings\n")
    md.append(f"- wavelength: {WAVELENGTH_NM} nm")
    md.append(f"- approximate_num_terms: {APPROXIMATE_NUM_TERMS}")
    md.append(f"- pitch: {PITCH_NM} nm")
    md.append(f"- source: gaussian x-dipole-like source, FWHM {DIPOLE_FWHM_NM} nm\n")
    md.append("## Candidate set\n")
    md.append("- `BARE_GaN_Air`: bare reference")
    md.append("- `MDC-A0-INT`: rounded quarter-wave reference")
    md.append("- `MDC1B_FAB_0126`: fabrication-friendly baseline")
    md.append("- `MDC1B_PERF_0890`: performance anchor\n")
    md.append("## Result summary\n")
    md.append(f"- status: `{api['status']}`")
    md.append(f"- ok_rows: `{api['ok_rows']}`")
    md.append(f"- api_failed_rows: `{api['api_failed_rows']}`")
    md.append(f"- failed_rows: `{api['failed_rows']}`\n")
    md.append("| candidate | status | diagnostic amplitude abs sum | runtime s |")
    md.append("|---|---|---:|---:|")
    for r in rows:
        md.append(f"| {r.get('candidate_id')} | {r.get('status')} | {r.get('amplitude_abs_sum_diagnostic','')} | {r.get('runtime_seconds','')} |")
    md.append("\n## Interpretation\n")
    if api["ok_rows"] >= 1:
        md.append("FMMAX import, basis generation, stack construction, gaussian source creation, and source-amplitude call completed for at least one candidate. This closes the minimal single-dipole FMM loop.")
    else:
        md.append("The minimal FMM loop did not complete. Use the saved API signatures and error rows to revise the FMMAX source-stack interface.")
    md.append("\n## Next\n")
    md.append("Do not use this as final device evidence. Next physical validation should be 2D FDTD with center/side source positions and noncoherent averaging.")
    md.append("\n## Local raw outputs\n")
    md.append("- `outputs/mdc1c2_fmmax_minimal_dipole/mdc1c2_fmmax_minimal_dipole_results.csv`")
    md.append("- `outputs/mdc1c2_fmmax_minimal_dipole/mdc1c2_fmmax_api_info.json`\n")
    md.append("## Tracked lightweight outputs\n")
    md.append("- `reports/mdc_defect_450/mdc1c2_fmmax_minimal_dipole_report.md`")
    md.append("- `reports/mdc_defect_450/mdc1c2_fmmax_minimal_dipole_compact_results.csv`\n")

    report_md = REPORT_DIR / "mdc1c2_fmmax_minimal_dipole_report.md"
    report_md.write_text("\n".join(md), encoding="utf-8")

    print("")
    print("MDC1C2 minimal FMMAX single-dipole stage complete")
    print("status=", api["status"])
    print("ok_rows=", api["ok_rows"])
    print("api_failed_rows=", api["api_failed_rows"])
    print("failed_rows=", api["failed_rows"])
    print("raw_results=", results_csv)
    print("compact_results=", compact_csv)
    print("report=", report_md)
    print("")
    print("COMPACT RESULTS:")
    for r in compact_rows:
        print(r)

    return 0 if api["ok_rows"] >= 1 else 2

if __name__ == "__main__":
    raise SystemExit(main())
