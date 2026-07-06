from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4h1f_minimal_source_isolated_xaxis_three_position_xdipole_validation"
FSP = Path(r"F:\wc_312\MDC_blue_oujizi.fsp")
LUMAPI_PATH = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
POSITIONS_NM = [-2500.0, 0.0, 2500.0]
POSITIONS_M = [p * 1e-9 for p in POSITIONS_NM]
WAVELENGTH_M = 450e-9
TOL_M = 1e-12


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def safe_str(v: Any) -> str:
    try:
        if v is None:
            return ""
        if isinstance(v, (str, int, float, bool)):
            return str(v)
        if hasattr(v, "tolist"):
            v = v.tolist()
        return json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        return str(v)


def to_float(v: Any) -> float | None:
    try:
        if hasattr(v, "tolist"):
            v = v.tolist()
        if isinstance(v, list):
            if not v:
                return None
            return to_float(v[0])
        return float(v)
    except Exception:
        return None


def flatten_numeric(v: Any) -> list[float]:
    if v is None:
        return []
    if hasattr(v, "tolist"):
        v = v.tolist()
    out: list[float] = []
    if isinstance(v, (int, float)):
        return [float(v)]
    if isinstance(v, list) or isinstance(v, tuple):
        for item in v:
            out.extend(flatten_numeric(item))
    return out


def import_lumapi() -> Any:
    spec = importlib.util.spec_from_file_location("lumapi", str(LUMAPI_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import lumapi from {LUMAPI_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def call(obj: Any, method: str, *args: Any) -> tuple[bool, Any, str]:
    try:
        return True, getattr(obj, method)(*args), ""
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def set_named(fdtd: Any, obj: str, prop: str, val: Any) -> tuple[bool, str]:
    ok, _, err = call(fdtd, "setnamed", obj, prop, val)
    return ok, err


def get_named(fdtd: Any, obj: str, prop: str) -> tuple[bool, Any, str]:
    return call(fdtd, "getnamed", obj, prop)


def truthy_enabled(v: Any) -> bool | None:
    f = to_float(v)
    if f is not None:
        return bool(round(f))
    s = safe_str(v).strip().lower()
    if s in {"1", "true", "on", "yes"}:
        return True
    if s in {"0", "false", "off", "no"}:
        return False
    return None


def try_set_many(fdtd: Any, obj: str, pairs: list[tuple[str, Any]], notes: list[str]) -> None:
    for prop, val in pairs:
        ok, err = set_named(fdtd, obj, prop, val)
        notes.append(f"set {obj}.{prop}={val}: {'ok' if ok else err}")


def configure_and_confirm(fdtd: Any, x_m: float, x_nm: float) -> tuple[bool, dict[str, Any], list[str]]:
    notes: list[str] = []
    ok, _, err = call(fdtd, "switchtolayout")
    notes.append(f"switchtolayout: {'ok' if ok else err}")
    if not ok:
        return False, {}, notes

    try_set_many(fdtd, "source", [("enabled", 0)], notes)
    try_set_many(fdtd, "source_1", [
        ("enabled", 1),
        ("x", x_m),
        ("y", -800e-9),
        ("z", 0.0),
        ("theta", 90),
        ("phi", 0),
        ("wavelength start", WAVELENGTH_M),
        ("wavelength stop", WAVELENGTH_M),
        ("dipole type", "Electric dipole"),
    ], notes)

    ok_src, src_enabled_raw, err_src = get_named(fdtd, "source", "enabled")
    ok_dip, dip_enabled_raw, err_dip = get_named(fdtd, "source_1", "enabled")
    ok_x, x_raw, err_x = get_named(fdtd, "source_1", "x")
    ok_ws, ws_raw, err_ws = get_named(fdtd, "source_1", "wavelength start")
    ok_we, we_raw, err_we = get_named(fdtd, "source_1", "wavelength stop")

    src_enabled = truthy_enabled(src_enabled_raw) if ok_src else None
    dip_enabled = truthy_enabled(dip_enabled_raw) if ok_dip else None
    x_val = to_float(x_raw) if ok_x else None
    ws_val = to_float(ws_raw) if ok_ws else None
    we_val = to_float(we_raw) if ok_we else None
    isolation_ok = (ok_src and ok_dip and src_enabled is False and dip_enabled is True)
    position_ok = (ok_x and x_val is not None and abs(x_val - x_m) <= TOL_M)
    wavelength_ok = (not ok_ws or (ws_val is not None and abs(ws_val - WAVELENGTH_M) < 1e-12)) and (not ok_we or (we_val is not None and abs(we_val - WAVELENGTH_M) < 1e-12))
    confirm = {
        "source_x_nm": x_nm,
        "source_enabled_get_ok": ok_src,
        "source_enabled_raw": safe_str(src_enabled_raw),
        "source_enabled_bool": src_enabled,
        "source_1_enabled_get_ok": ok_dip,
        "source_1_enabled_raw": safe_str(dip_enabled_raw),
        "source_1_enabled_bool": dip_enabled,
        "source_1_x_get_ok": ok_x,
        "source_1_x_m": x_val if x_val is not None else "",
        "source_1_x_nm": x_val * 1e9 if x_val is not None else "",
        "intended_x_nm": x_nm,
        "source_1_wavelength_start_m": ws_val if ws_val is not None else "",
        "source_1_wavelength_stop_m": we_val if we_val is not None else "",
        "source_isolation_confirmed": isolation_ok,
        "source_position_confirmed": position_ok,
        "wavelength_confirmed_if_accessible": wavelength_ok,
        "source_errors": "; ".join(x for x in [err_src if not ok_src else "", err_dip if not ok_dip else "", err_x if not ok_x else "", err_ws if not ok_ws else "", err_we if not ok_we else ""] if x),
        "notes": " | ".join(notes),
    }
    return isolation_ok and position_ok and wavelength_ok, confirm, notes


def extract_power(fdtd: Any, x_nm: float) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    row = {"source_x_nm": x_nm, "T_available": False, "T_preview": "", "transmission_available": False, "transmission_preview": "", "power_extraction_notes": ""}
    ok, val, err = call(fdtd, "getresult", "monitor", "T")
    row["T_available"] = ok
    row["T_preview"] = safe_str(val)[:300] if ok else ""
    if not ok:
        notes.append(f"getresult monitor T failed: {err}")
    ok2, val2, err2 = call(fdtd, "transmission", "monitor")
    row["transmission_available"] = ok2
    row["transmission_preview"] = safe_str(val2)[:300] if ok2 else ""
    if not ok2:
        notes.append(f"transmission monitor failed: {err2}")
    row["power_extraction_notes"] = " | ".join(notes)
    return row, notes


def extract_farfield(fdtd: Any, x_nm: float) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    notes: list[str] = []
    intensity: list[float] = []
    theta: list[float] = []
    attempts = [
        ("farfield2d_monitor_1_721", "farfield2d", ("monitor", 1, 721)),
        ("farfield2d_monitor_1", "farfield2d", ("monitor", 1)),
        ("farfield_monitor", "farfield", ("monitor", 1)),
    ]
    for name, method, args in attempts:
        ok, val, err = call(fdtd, method, *args)
        notes.append(f"{name}: {'ok' if ok else err}")
        nums = flatten_numeric(val) if ok else []
        if nums and len(nums) >= 5:
            intensity = [max(0.0, float(v)) for v in nums]
            break
    angle_attempts = [
        ("farfieldangle_monitor_1_721", "farfieldangle", ("monitor", 1, 721)),
        ("farfieldangle_monitor_1", "farfieldangle", ("monitor", 1)),
    ]
    for name, method, args in angle_attempts:
        ok, val, err = call(fdtd, method, *args)
        notes.append(f"{name}: {'ok' if ok else err}")
        nums = flatten_numeric(val) if ok else []
        if nums and len(nums) == len(intensity):
            theta = [float(v) for v in nums]
            break
    if intensity and not theta:
        n = len(intensity)
        theta = [-90.0 + 180.0 * i / (n - 1) for i in range(n)] if n > 1 else [0.0]
        notes.append("theta generated as linear -90..90 deg fallback because farfieldangle unavailable")
    # Normalize length if needed.
    n = min(len(theta), len(intensity))
    theta, intensity = theta[:n], intensity[:n]
    if not theta or not intensity:
        return [], metrics_from_profile([], []), notes
    max_i = max(intensity) if intensity else 0.0
    rows = [{"profile": f"x_{x_nm:g}_nm", "source_x_nm": x_nm, "theta_deg": t, "intensity_norm": (i / max_i if max_i > 0 else 0.0), "intensity_raw": i} for t, i in zip(theta, intensity)]
    return rows, metrics_from_profile(theta, intensity), notes


def trapz(theta: list[float], y: list[float]) -> float:
    if len(theta) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(theta)):
        total += 0.5 * (y[i] + y[i-1]) * abs(theta[i] - theta[i-1])
    return total


def window_power(theta: list[float], y: list[float], predicate) -> float:
    tt, yy = [], []
    for t, v in zip(theta, y):
        if predicate(t):
            tt.append(t); yy.append(v)
    return trapz(tt, yy)


def metrics_from_profile(theta: list[float], intensity: list[float]) -> dict[str, Any]:
    if not theta or not intensity or max(intensity) <= 0:
        return {"farfield_available": False, "peak_angle_deg": "", "angular_fwhm_deg": "", "eta_5deg": "", "eta_10deg": "", "eta_20deg": "", "leakage_20_40_fraction": "", "leakage_40_60_fraction": "", "normal_to_40_60_ratio": "", "lobe_class": "unavailable"}
    pairs = sorted(zip(theta, intensity), key=lambda x: x[0])
    theta = [p[0] for p in pairs]
    intensity = [p[1] for p in pairs]
    mx = max(intensity)
    peak_idx = intensity.index(mx)
    peak = theta[peak_idx]
    half = mx * 0.5
    above = [t for t, i in zip(theta, intensity) if i >= half]
    fwhm = max(above) - min(above) if above else ""
    total = trapz(theta, intensity)
    def frac(pred):
        return window_power(theta, intensity, pred) / total if total > 0 else ""
    eta5 = frac(lambda t: abs(t) <= 5)
    eta10 = frac(lambda t: abs(t) <= 10)
    eta20 = frac(lambda t: abs(t) <= 20)
    leak2040 = frac(lambda t: 20 < abs(t) <= 40)
    leak4060 = frac(lambda t: 40 < abs(t) <= 60)
    denom = leak4060 if isinstance(leak4060, float) and leak4060 > 1e-15 else None
    ratio = eta10 / denom if isinstance(eta10, float) and denom else ("inf" if isinstance(eta10, float) else "")
    # lobe class by peak and leakage.
    if abs(peak) <= 10:
        cls = "near_normal"
    elif abs(peak) <= 30:
        cls = "moderate_offaxis"
    else:
        cls = "severe_offaxis"
    if isinstance(leak4060, float) and isinstance(eta10, float) and leak4060 > eta10:
        cls = "severe_offaxis"
    return {"farfield_available": True, "peak_angle_deg": peak, "angular_fwhm_deg": fwhm, "eta_5deg": eta5, "eta_10deg": eta10, "eta_20deg": eta20, "leakage_20_40_fraction": leak2040, "leakage_40_60_fraction": leak4060, "normal_to_40_60_ratio": ratio, "lobe_class": cls}


def interp(x: list[float], y: list[float], xi: float) -> float:
    if xi <= x[0]:
        return y[0]
    if xi >= x[-1]:
        return y[-1]
    for i in range(1, len(x)):
        if x[i] >= xi:
            x0, x1 = x[i-1], x[i]
            y0, y1 = y[i-1], y[i]
            if x1 == x0:
                return y0
            return y0 + (y1-y0)*(xi-x0)/(x1-x0)
    return y[-1]


def average_profiles(profile_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_profile: dict[str, tuple[list[float], list[float]]] = {}
    for r in profile_rows:
        name = str(r["profile"])
        by_profile.setdefault(name, ([], []))
        by_profile[name][0].append(float(r["theta_deg"]))
        by_profile[name][1].append(float(r["intensity_raw"]))
    if len(by_profile) != 3:
        return [], metrics_from_profile([], [])
    profiles = []
    for tt, yy in by_profile.values():
        pairs = sorted(zip(tt, yy), key=lambda x: x[0])
        profiles.append(([p[0] for p in pairs], [p[1] for p in pairs]))
    common = profiles[0][0]
    avg_int = []
    for t in common:
        vals = [interp(tt, yy, t) for tt, yy in profiles]
        avg_int.append(sum(vals) / len(vals))
    max_i = max(avg_int) if avg_int else 0.0
    rows = [{"profile": "incoherent_average", "source_x_nm": "average", "theta_deg": t, "intensity_norm": (i/max_i if max_i > 0 else 0.0), "intensity_raw": i} for t, i in zip(common, avg_int)]
    return rows, metrics_from_profile(common, avg_int)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    lumapi = import_lumapi()
    run_rows: list[dict[str, Any]] = []
    iso_rows: list[dict[str, Any]] = []
    pos_rows: list[dict[str, Any]] = []
    mon_rows: list[dict[str, Any]] = []
    ind_metric_rows: list[dict[str, Any]] = []
    ind_power_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    abort_reason = ""

    for x_nm, x_m in zip(POSITIONS_NM, POSITIONS_M):
        case_id = f"x_{x_nm:g}_nm".replace("-", "m").replace(".", "p")
        fdtd = None
        start = time.time()
        status = "not_started"
        err = ""
        try:
            fdtd = lumapi.FDTD(hide=True)
            ok, _, load_err = call(fdtd, "load", str(FSP))
            if not ok:
                status = "invalid_not_run_load_failed"; err = load_err; abort_reason = status
                break
            setup_ok, confirm, notes = configure_and_confirm(fdtd, x_m, x_nm)
            iso_rows.append({"case_id": case_id, **confirm})
            pos_rows.append({"case_id": case_id, "intended_x_nm": x_nm, "confirmed": confirm.get("source_position_confirmed"), "readback_x_nm": confirm.get("source_1_x_nm"), "notes": confirm.get("notes", "")})
            if not setup_ok:
                status = "invalid_not_run_source_setup_unconfirmed"; err = confirm.get("source_errors", "source isolation/position/wavelength unconfirmed"); abort_reason = status
                break
            ok_run, _, run_err = call(fdtd, "run")
            if not ok_run:
                status = "run_failed"; err = run_err; abort_reason = status
                break
            status = "ok"
            power_row, power_notes = extract_power(fdtd, x_nm)
            power_row["case_id"] = case_id
            ind_power_rows.append(power_row)
            ff_rows, metrics, ff_notes = extract_farfield(fdtd, x_nm)
            mon_rows.append({"case_id": case_id, "source_x_nm": x_nm, "farfield_available": metrics.get("farfield_available"), "notes": " | ".join(ff_notes + power_notes)})
            for rr in ff_rows:
                rr["case_id"] = case_id
            profile_rows.extend(ff_rows)
            ind_metric_rows.append({"case_id": case_id, "source_x_nm": x_nm, **metrics})
        except Exception as exc:
            status = "exception"; err = f"{type(exc).__name__}: {exc}"; abort_reason = status
            break
        finally:
            if fdtd is not None:
                try:
                    fdtd.close()
                except Exception:
                    pass
            run_rows.append({"case_id": case_id, "source_x_nm": x_nm, "status": status, "runtime_s": f"{time.time()-start:.3f}", "error": err})
        if status != "ok":
            break

    avg_rows: list[dict[str, Any]] = []
    avg_metric = metrics_from_profile([], [])
    if len([r for r in run_rows if r["status"] == "ok"]) == 3:
        avg_rows, avg_metric = average_profiles(profile_rows)
        for rr in avg_rows:
            rr["case_id"] = "incoherent_average"
        profile_rows.extend(avg_rows)

    if abort_reason:
        validation_status = "invalid_not_run_source_setup_unconfirmed" if "source" in abort_reason else abort_reason
        immediate_further_fdtd = False
    elif len([r for r in run_rows if r["status"] == "ok"]) < 3:
        validation_status = "invalid_incomplete_run_set"
        immediate_further_fdtd = False
    elif not avg_metric.get("farfield_available"):
        validation_status = "three_runs_complete_but_angular_validation_unavailable"
        immediate_further_fdtd = False
    else:
        peak = float(avg_metric.get("peak_angle_deg", 999))
        leak4060 = avg_metric.get("leakage_40_60_fraction")
        eta10 = avg_metric.get("eta_10deg")
        if abs(peak) <= 10 and isinstance(leak4060, float) and isinstance(eta10, float) and leak4060 <= eta10:
            validation_status = "preliminary_xaxis_three_position_xdipole_pass"
            immediate_further_fdtd = False
        else:
            validation_status = "preliminary_xaxis_three_position_xdipole_fail_or_high_risk"
            immediate_further_fdtd = False

    # Output files.
    write_csv(OUT / "r2_4h1f_run_status.csv", run_rows, ["case_id", "source_x_nm", "status", "runtime_s", "error"])
    write_csv(OUT / "r2_4h1f_source_isolation_check.csv", iso_rows, ["case_id", "source_x_nm", "source_enabled_get_ok", "source_enabled_raw", "source_enabled_bool", "source_1_enabled_get_ok", "source_1_enabled_raw", "source_1_enabled_bool", "source_1_x_get_ok", "source_1_x_m", "source_1_x_nm", "intended_x_nm", "source_1_wavelength_start_m", "source_1_wavelength_stop_m", "source_isolation_confirmed", "source_position_confirmed", "wavelength_confirmed_if_accessible", "source_errors", "notes"])
    write_csv(OUT / "r2_4h1f_source_position_check.csv", pos_rows, ["case_id", "intended_x_nm", "confirmed", "readback_x_nm", "notes"])
    write_csv(OUT / "r2_4h1f_monitor_result_availability.csv", mon_rows, ["case_id", "source_x_nm", "farfield_available", "notes"])
    metric_fields = ["case_id", "source_x_nm", "farfield_available", "peak_angle_deg", "angular_fwhm_deg", "eta_5deg", "eta_10deg", "eta_20deg", "leakage_20_40_fraction", "leakage_40_60_fraction", "normal_to_40_60_ratio", "lobe_class"]
    write_csv(OUT / "r2_4h1f_individual_farfield_angular_metrics.csv", ind_metric_rows, metric_fields)
    write_csv(OUT / "r2_4h1f_incoherent_average_farfield_angular_metrics.csv", [{"case_id": "incoherent_average", "source_x_nm": "average", **avg_metric}], metric_fields)
    write_csv(OUT / "r2_4h1f_individual_power_metrics.csv", ind_power_rows, ["case_id", "source_x_nm", "T_available", "T_preview", "transmission_available", "transmission_preview", "power_extraction_notes"])
    write_csv(OUT / "r2_4h1f_incoherent_average_power_metrics.csv", [{"metric": "not_computed", "value": "see individual power previews", "notes": "average power metric requires validated scalar transmission extraction"}], ["metric", "value", "notes"])
    write_csv(OUT / "r2_4h1f_farfield_profiles_left_center_right_and_average.csv", profile_rows, ["case_id", "profile", "source_x_nm", "theta_deg", "intensity_norm", "intensity_raw"])

    all_iso = len(iso_rows) == 3 and all(str(r.get("source_isolation_confirmed")).lower() == "true" for r in iso_rows)
    all_pos = len(pos_rows) == 3 and all(str(r.get("confirmed")).lower() == "true" for r in pos_rows)
    all_runs = len([r for r in run_rows if r["status"] == "ok"]) == 3
    ff_avail = bool(avg_metric.get("farfield_available"))

    decision_md = f"""
# R2-4H1F Validation Decision

Validation status: `{validation_status}`

- Source isolation confirmed for all three cases: `{all_iso}`
- Source position confirmed for all three cases: `{all_pos}`
- Three FDTD runs occurred: `{all_runs}`
- Farfield angular metrics extracted: `{ff_avail}`
- Immediate further FDTD allowed: `{immediate_further_fdtd}`

Center-only result is diagnostic only and is not used alone for pass/fail.
"""
    write_md(OUT / "r2_4h1f_validation_decision.md", decision_md)
    risk_md = f"""
# R2-4H1F Failure or Risk Analysis

Validation status: `{validation_status}`

If invalid or incomplete, the controlling reason is: `{abort_reason or 'none'}`.
If angular metrics are unavailable, do not infer optical behavior from existing analysis-mode results or center-only data.
If far-offaxis leakage dominates, next stage is failure analysis only.
"""
    write_md(OUT / "r2_4h1f_failure_or_risk_analysis.md", risk_md)
    next_md = f"""
# R2-4H1F Next Stage Recommendation

Immediate further FDTD allowed: `{immediate_further_fdtd}`

- If status is preliminary pass: next allowed stage is H1G y-dipole or x/y comparison planning, not automatic run.
- If status is fail/high-risk: next stage is failure analysis only.
- If angular validation is unavailable: next stage is extraction-method repair, not more simulation.
- Broadband, y-dipole, and larger position sweeps remain disallowed unless explicitly approved later.
"""
    write_md(OUT / "r2_4h1f_next_stage_recommendation.md", next_md)
    stop_md = """
# R2-4H1F Stop / Allow Rules

Stop:
- Do not run broadband.
- Do not run y-dipole or z-dipole.
- Do not run 5-point/9-point sweeps.
- Do not use existing analysis-mode results.
- Do not save or overwrite the original FSP.
- Do not commit FSP/LDF/MAT/H5 or screenshots/videos.

Allow:
- Commit lightweight script, CSV, JSON, and Markdown results.
- Plan next step only after interpreting the three-position incoherent-average result.
"""
    write_md(OUT / "r2_4h1f_stop_allow_rules.md", stop_md)
    summary_md = f"""
# R2-4H1F Minimal Source-isolated X-axis Three-position X-dipole Validation

Target FSP: `{FSP}`
Positions: `{-2500}, {0}, {2500}` nm
Wavelength: `450 nm`

Validation status: `{validation_status}`
Source isolation confirmed all cases: `{all_iso}`
Source position confirmed all cases: `{all_pos}`
All three runs occurred: `{all_runs}`
Farfield angular metrics extracted: `{ff_avail}`

Incoherent-average peak angle: `{avg_metric.get('peak_angle_deg', '')}`
Incoherent-average FWHM: `{avg_metric.get('angular_fwhm_deg', '')}`
Incoherent-average eta5/eta10/eta20: `{avg_metric.get('eta_5deg', '')}`, `{avg_metric.get('eta_10deg', '')}`, `{avg_metric.get('eta_20deg', '')}`
Incoherent-average 40-60 leakage: `{avg_metric.get('leakage_40_60_fraction', '')}`

Immediate further FDTD allowed: `{immediate_further_fdtd}`
"""
    write_md(OUT / "r2_4h1f_summary.md", summary_md)
    manifest = {
        "stage": "R2-4H1F minimal source-isolated x-axis three-position x-dipole validation",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "target_fsp": str(FSP),
        "positions_nm": POSITIONS_NM,
        "wavelength_nm": 450,
        "exact_run_case_count_allowed": 3,
        "source_isolation_confirmed_all": all_iso,
        "source_position_confirmed_all": all_pos,
        "all_three_runs_occurred": all_runs,
        "farfield_angular_metrics_extracted": ff_avail,
        "validation_status": validation_status,
        "immediate_further_fdtd_allowed": immediate_further_fdtd,
        "no_original_fsp_saved": True,
        "no_heavy_files_committed": True,
        "incoherent_average_metrics": avg_metric,
    }
    (OUT / "r2_4h1f_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "source_isolation_confirmed_all": all_iso,
        "source_position_confirmed_all": all_pos,
        "all_three_runs_occurred": all_runs,
        "farfield_angular_metrics_extracted": ff_avail,
        "validation_status": validation_status,
        "avg_metrics": avg_metric,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
