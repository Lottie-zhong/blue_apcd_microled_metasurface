from __future__ import annotations

import cmath
import csv
import json
import math
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

OUT = ROOT / "outputs" / "lp_ml1b1_fdtd_smoke_test"
TMP_FDTD = OUT / "fdtd_tmp"
REPORTS = ROOT / "reports"
B0_OUT = ROOT / "outputs" / "lp_ml1b0_runner_planning"
A4_OUT = ROOT / "outputs" / "lp_ml1a4_explicit_geometry_seed_generator"
SMOKE = B0_OUT / "lp_ml1b0_smoke_test_recommendation.csv"
PILOT = B0_OUT / "lp_ml1b0_pilot_queue.csv"
CONFIG = B0_OUT / "lp_ml1b0_runner_config_draft.json"
SCHEMA = B0_OUT / "lp_ml1b0_expected_result_schema.csv"
MANIFEST = A4_OUT / "lp_ml1a4_explicit_seed_manifest.csv"
RESULTS = OUT / "lp_ml1b1_smoke_results.csv"
SUMMARY = OUT / "lp_ml1b1_smoke_summary.json"
FAILURES = OUT / "lp_ml1b1_failure_log.csv"
RUNTIME = OUT / "lp_ml1b1_runtime_manifest.csv"
REPORT = REPORTS / "lp_ml1b1_fdtd_smoke_test.md"
AUDIT = REPORTS / "lp_ml1b1_jones_extraction_audit.md"
PYTHON = r"N:\anaconda_envs\RCP_LCP\python.exe"
EXPECTED = ["LPML1A4_0028_B300_exploration_B300_H600", "LPML1A4_0234_B240_exploration_B240_H600"]
WAVELENGTHS = [450, 450.5, 451, 451.5, 452, 452.5, 453, 453.5, 454]
BINS = [0, 60, 120, 180, 240, 300]
EPS = 1e-12
RESULT_FIELDS = ["candidate_id", "target_bin_deg", "wavelength_nm", "txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im", "selected_Tx", "leakage_xin_to_yout", "leakage_yin_to_xout", "y_direct_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "nearest_bin_deg", "phase_error_deg", "matrix_error", "spectral_pass", "result_status", "error_message"]
FAIL_FIELDS = ["candidate_id", "wavelength_nm", "polarization", "result_status", "error_message", "fsp_path"]
RUN_FIELDS = ["candidate_id", "wavelength_nm", "polarization", "runtime_sec", "result_status", "fsp_path"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k: "" if v is None else v for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def f(value: Any, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def wrap360(value: float) -> float:
    return value % 360.0


def nearest_bin(phase_deg: float) -> int:
    return min(BINS, key=lambda b: abs(wrap180(phase_deg - b)))


def ensure_inputs() -> None:
    if not MANIFEST.exists():
        subprocess.run([PYTHON, str(ROOT / "scripts" / "lp_ml1" / "lp_ml1a4_explicit_geometry_seed_generator.py")], cwd=ROOT, check=True)
    if any(not p.exists() for p in [SMOKE, PILOT, CONFIG, SCHEMA]):
        subprocess.run([PYTHON, str(ROOT / "scripts" / "lp_ml1" / "lp_ml1b0_runner_planning.py")], cwd=ROOT, check=True)


def selected_rows() -> list[dict[str, str]]:
    ensure_inputs()
    ids = [row["candidate_id"] for row in read_csv(SMOKE)]
    if ids != EXPECTED:
        raise ValueError(f"Smoke-test candidates must be exactly {EXPECTED}, got {ids}")
    manifest = {row["candidate_id"]: row for row in read_csv(MANIFEST)}
    rows = [manifest[cid] for cid in EXPECTED]
    for row in rows:
        if row.get("geometry_valid", "").lower() != "true":
            raise ValueError(f"Invalid geometry row: {row['candidate_id']}")
    return rows


def center_value(fdtd: Any, key: str) -> complex:
    value = fdtd.getdata("field_monitor", key)
    if hasattr(value, "squeeze"):
        value = value.squeeze()
    shape = getattr(value, "shape", ())
    if shape:
        cur = value
        for axis_size in [int(s) for s in shape if int(s) != 1]:
            cur = cur[axis_size // 2]
        value = cur
    return complex(value)


def safe_transmission(fdtd: Any) -> float:
    value = fdtd.transmission("T")
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (list, tuple)):
        value = value[0]
    return max(float(value), 0.0)


def normalized_components(fdtd: Any) -> tuple[complex, complex, float]:
    ex = center_value(fdtd, "Ex")
    ey = center_value(fdtd, "Ey")
    total = safe_transmission(fdtd)
    norm = math.sqrt(abs(ex) ** 2 + abs(ey) ** 2)
    if norm <= EPS:
        return 0j, 0j, total
    scale = math.sqrt(total) / norm
    return ex * scale, ey * scale, total


def add_rect(fdtd: Any, name: str, x_nm: float, y_nm: float, length_nm: float, width_nm: float, theta_deg: float, height_nm: float) -> None:
    nm = 1e-9
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("x", x_nm * nm)
    fdtd.set("y", y_nm * nm)
    fdtd.set("x span", length_nm * nm)
    fdtd.set("y span", width_nm * nm)
    fdtd.set("z min", 0)
    fdtd.set("z max", height_nm * nm)
    if abs(theta_deg) > 1e-9:
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", theta_deg)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", 2.6)


def build_model(fdtd: Any, row: dict[str, str], wavelength_nm: float, polarization: str) -> None:
    nm = 1e-9
    px = f(row["period_x_nm"]) * nm
    py = f(row["period_y_nm"]) * nm
    height = f(row["H_nm"]) * nm
    dx = f(row["center_dx_nm"])
    dy = f(row["center_dy_nm"])
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z min", -500 * nm)
    fdtd.set("z max", height + 700 * nm)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", 2)
    fdtd.set("simulation time", 1000e-15)
    add_rect(fdtd, "pillar_1", -0.5 * dx, -0.5 * dy, f(row["L1_nm"]), f(row["W1_nm"]), f(row["theta1_deg"]), f(row["H_nm"]))
    add_rect(fdtd, "pillar_2", 0.5 * dx, 0.5 * dy, f(row["L2_nm"]), f(row["W2_nm"]), f(row["theta2_deg"]), f(row["H_nm"]))
    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", -250 * nm)
    fdtd.set("wavelength start", wavelength_nm * nm)
    fdtd.set("wavelength stop", wavelength_nm * nm)
    fdtd.set("polarization angle", 0 if polarization == "x" else 90)
    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", height + 350 * nm)
    fdtd.addprofile()
    fdtd.set("name", "field_monitor")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", height + 350 * nm)


def run_pol(lumapi: Any, runtime: Any, row: dict[str, str], wl: float, pol: str) -> dict[str, Any]:
    cid = row["candidate_id"]
    case_dir = TMP_FDTD / cid
    case_dir.mkdir(parents=True, exist_ok=True)
    fsp = case_dir / f"{cid}_{str(wl).replace('.', 'p')}_{pol}.fsp"
    start = time.time()
    fdtd = None
    status = "failed"
    note = ""
    ex = ey = 0j
    total = math.nan
    try:
        fdtd = lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        build_model(fdtd, row, wl, pol)
        fdtd.save(str(fsp))
        fdtd.run()
        ex, ey, total = normalized_components(fdtd)
        status = "ok"
    except Exception as exc:
        note = f"{type(exc).__name__}: {exc}\n{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    return {"candidate_id": cid, "wavelength_nm": wl, "polarization": pol, "ex": ex, "ey": ey, "transmission": total, "result_status": status, "error_message": note, "fsp_path": str(fsp), "runtime_sec": time.time() - start}


def pass_level(phase_error: float, tx: float, ratio: float, matrix_error: float) -> str:
    if phase_error <= 15 and ratio >= 6 and tx >= 0.10 and matrix_error <= 0.60:
        return "strict"
    if phase_error <= 25 and ratio >= 3 and tx >= 0.10 and matrix_error <= 1.00:
        return "loose"
    return "fail"


def combine(row: dict[str, str], wl: float, x: dict[str, Any], y: dict[str, Any]) -> dict[str, Any]:
    target = int(float(row["target_bin_deg"]))
    base = {"candidate_id": row["candidate_id"], "target_bin_deg": target, "wavelength_nm": wl}
    if x["result_status"] != "ok" or y["result_status"] != "ok":
        return {**base, "result_status": "failed", "error_message": (x.get("error_message", "") + "; " + y.get("error_message", ""))[:1000]}
    txx = complex(x["ex"])
    tyx = complex(x["ey"])
    txy = complex(y["ex"])
    tyy = complex(y["ey"])
    selected_tx = abs(txx) ** 2
    leak_xin_yout = abs(tyx) ** 2
    leak_yin_xout = abs(txy) ** 2
    y_direct = abs(tyy) ** 2
    ratio = selected_tx / max(leak_yin_xout + y_direct, EPS)
    phase = wrap360(math.degrees(cmath.phase(txx))) if abs(txx) > EPS else math.nan
    near = nearest_bin(phase) if not math.isnan(phase) else ""
    phase_error = abs(wrap180(phase - target)) if not math.isnan(phase) else math.nan
    matrix_error = math.sqrt(leak_xin_yout + leak_yin_xout + y_direct) / max(abs(txx), EPS)
    level = pass_level(phase_error, selected_tx, ratio, matrix_error)
    return {**base, "txx_re": fmt(txx.real), "txx_im": fmt(txx.imag), "txy_re": fmt(txy.real), "txy_im": fmt(txy.imag), "tyx_re": fmt(tyx.real), "tyx_im": fmt(tyx.imag), "tyy_re": fmt(tyy.real), "tyy_im": fmt(tyy.imag), "selected_Tx": fmt(selected_tx), "leakage_xin_to_yout": fmt(leak_xin_yout), "leakage_yin_to_xout": fmt(leak_yin_xout), "y_direct_leakage": fmt(y_direct), "conversion_to_leakage_ratio": fmt(ratio), "selected_phase_deg": fmt(phase), "nearest_bin_deg": near, "phase_error_deg": fmt(phase_error), "matrix_error": fmt(matrix_error), "spectral_pass": level, "result_status": "ok", "error_message": ""}


def write_reports(results: list[dict[str, Any]], failures: list[dict[str, Any]], runtime_rows: list[dict[str, Any]], heavy_files: list[Path]) -> None:
    ok_rows = [r for r in results if r.get("result_status") == "ok"]
    runtime_by_candidate = {cid: sum(float(r.get("runtime_sec", 0) or 0) for r in runtime_rows if r.get("candidate_id") == cid) for cid in EXPECTED}
    REPORT.write_text("\n".join([
        "# LP-ML1B1 FDTD smoke test", "", "Purpose: first controlled LP-ML1B periodic dimer FDTD smoke test for exactly two LP-ML1A4 explicit candidates.", "", "## Candidate list", *[f"- {cid}" for cid in EXPECTED], "", "## Geometry source", f"- {MANIFEST}", "- Explicit LP-ML1A4 numeric geometry was used; no unrecovered legacy FSP was used.", "- Material/template convention: object-defined dielectric index 2.6, matching the existing Stage11 H500 dimer template convention.", "", "## Simulation scope", "- Periodic single dimer unit cell, normal-incidence plane wave, x and y linear inputs.", "- Wavelengths: 450, 450.5, 451, 451.5, 452, 452.5, 453, 453.5, 454 nm.", "- Source propagates +z from below the dimer; top transmission monitor is above the pillars.", "- No K=6, no coverage, no FMM solve, no model training.", "", "## Runtime summary", "- expected result rows: 18", f"- result rows written: {len(results)}", f"- successful result rows: {len(ok_rows)}", f"- failed result rows: {len(results) - len(ok_rows)}", f"- failed polarization runs: {len(failures)}", *[f"- runtime {cid}: {runtime_by_candidate[cid]:.2f} sec" for cid in EXPECTED], "", "## Output paths", f"- {RESULTS}", f"- {SUMMARY}", f"- {FAILURES}", f"- {RUNTIME}", "", "## Heavy files", f"- temporary .fsp files created: {len(heavy_files)}", f"- temporary .fsp folder: {TMP_FDTD}", "- heavy files were not committed", "", "## Recommendation", "- Proceed to LP-ML1B2 36-case pilot only if the Jones values and failure log look physically sane; otherwise fix the template first.", ""]), encoding="utf-8")
    AUDIT.write_text("\n".join(["# LP-ML1B1 Jones extraction audit", "", "Complex extraction method used: complex Ex/Ey field data from a 2D Z-normal profile monitor at the transmitted side, component-normalized by the power monitor transmission.", "farfield3d intensity was not used for phase.", "", "Jones matrix ordering convention: Jt = [[txx, txy], [tyx, tyy]], columns are input polarization and rows are output polarization.", "- txx = x_out from x_in", "- tyx = y_out from x_in", "- txy = x_out from y_in", "- tyy = y_out from y_in", "", "Phase wrapping convention: selected_phase_deg = angle(txx) wrapped to [0, 360); phase_error_deg = absolute wrapped distance to the target bin.", "selected_Tx = |txx|^2; leakage_xin_to_yout = |tyx|^2; leakage_yin_to_xout = |txy|^2; y_direct_leakage = |tyy|^2.", "conversion_to_leakage_ratio = |txx|^2 / max(|txy|^2 + |tyy|^2, eps).", "matrix_error = ||J - txx * |x><x|||_F / max(|txx|, eps).", "", "Caveat: this smoke test uses center-field complex monitor extraction rather than far-field order-resolved extraction; use it as a template sanity check, not final LP library evidence.", "Caveat: material/template convention uses object-defined dielectric index 2.6 from existing LP dimer scripts; update later only with an explicit material audit.", "Next correction needed if values look invalid: replace center-field extraction with validated complex far-field vector extraction, still avoiding intensity-only farfield3d phase.", ""]), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    rows = selected_rows()
    runtime = load_runtime_config("configs/runtime.yaml")
    lumapi = import_lumapi(runtime)
    pol_results: dict[tuple[str, float, str], dict[str, Any]] = {}
    runtime_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        for wl in WAVELENGTHS:
            for pol in ["x", "y"]:
                print(f"running {row['candidate_id']} wl={wl} pol={pol}")
                res = run_pol(lumapi, runtime, row, wl, pol)
                pol_results[(row["candidate_id"], wl, pol)] = res
                runtime_rows.append(res)
                if res["result_status"] != "ok":
                    failures.append(res)
                write_csv(RUNTIME, runtime_rows, RUN_FIELDS)
                write_csv(FAILURES, failures, FAIL_FIELDS)
    results = [combine(row, wl, pol_results[(row["candidate_id"], wl, "x")], pol_results[(row["candidate_id"], wl, "y")]) for row in rows for wl in WAVELENGTHS]
    write_csv(RESULTS, results, RESULT_FIELDS)
    write_csv(FAILURES, failures, FAIL_FIELDS)
    write_csv(RUNTIME, runtime_rows, RUN_FIELDS)
    heavy_files = sorted(TMP_FDTD.rglob("*.fsp")) if TMP_FDTD.exists() else []
    ok_rows = [r for r in results if r.get("result_status") == "ok"]
    summary = {"candidate_ids": EXPECTED, "expected_rows": 18, "result_row_count": len(results), "successful_rows": len(ok_rows), "failed_rows": len(results) - len(ok_rows), "polarization_run_count": len(runtime_rows), "successful_polarization_runs": sum(1 for r in runtime_rows if r.get("result_status") == "ok"), "failed_polarization_runs": len(failures), "temporary_fsp_count": len(heavy_files), "temporary_fsp_dir": str(TMP_FDTD), "no_fmm_solve": True, "no_model_training": True, "no_coverage": True, "no_k6": True, "no_a16g2": True}
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_reports(results, failures, runtime_rows, heavy_files)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
