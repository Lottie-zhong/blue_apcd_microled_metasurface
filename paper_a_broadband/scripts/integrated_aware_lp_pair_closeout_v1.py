from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")
import lumapi

UTC = dt.timezone.utc
MONITOR = "ic1_top_near_to_far"
AXIS_CONFIDENCE_DOLP = 0.10


def now():
    return dt.datetime.now(UTC).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{__import__('os').getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"EMPTY_OUTPUT_ROWS:{path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"EMPTY_CSV:{path}")
    return {key: np.asarray([float(row[key]) for row in rows], dtype=float) for key in rows[0]}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stokes_from_fields(ex, ey):
    ex = np.asarray(ex, dtype=np.complex128)
    ey = np.asarray(ey, dtype=np.complex128)
    cxy = 0.5 * ey * np.conj(ex)
    return {"S0": 0.5 * (np.abs(ex) ** 2 + np.abs(ey) ** 2),
            "S1": 0.5 * (np.abs(ex) ** 2 - np.abs(ey) ** 2),
            "S2": 2.0 * np.real(cxy), "S3": -2.0 * np.imag(cxy)}


def metric_arrays(s):
    s0, s1, s2, s3 = (np.asarray(s[k], dtype=float) for k in ("S0", "S1", "S2", "S3"))
    lmag = np.hypot(s1, s2)
    with np.errstate(divide="ignore", invalid="ignore"):
        dolp = lmag / s0
        docp = s3 / s0
    return {**s, "Lmag": lmag, "DoLP": dolp, "DoCP": docp,
            "psi_deg": np.mod(np.degrees(0.5 * np.arctan2(s2, s1)), 180.0),
            "useful_LP_axisfree": 0.5 * (s0 + lmag),
            "useful_LP_over_S0": 0.5 * (1.0 + dolp)}


def scalar_stokes(s):
    m = metric_arrays({k: np.asarray([float(s[k])]) for k in ("S0", "S1", "S2", "S3")})
    return {k: float(m[k][0]) for k in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "useful_LP_axisfree", "useful_LP_over_S0")}


def exact_450(wl):
    indices = np.flatnonzero(np.isclose(wl, 450.0, rtol=0.0, atol=1e-9))
    if len(indices) != 1:
        raise RuntimeError(f"EXACT_450_INDEX_INVALID:{len(indices)}")
    return int(indices[0])


def solid_angle_grid(ux, uy):
    uxg, uyg = np.meshgrid(ux, uy, indexing="ij")
    rho2 = uxg * uxg + uyg * uyg
    disk = rho2 < 1.0 - 1e-12
    jac = np.zeros_like(rho2)
    jac[disk] = 1.0 / np.sqrt(1.0 - rho2[disk])
    du = float(np.median(np.diff(ux))) if len(ux) > 1 else 1.0
    dv = float(np.median(np.diff(uy))) if len(uy) > 1 else 1.0
    domega = jac * abs(du * dv)
    theta = np.full_like(rho2, np.nan)
    theta[disk] = np.degrees(np.arcsin(np.sqrt(rho2[disk])))
    return {"uxg": uxg, "uyg": uyg, "propagating": disk, "domega": domega, "theta_deg": theta}


def integrate(s, grid, mask):
    w = grid["domega"] * mask
    out = {k: float(np.sum(np.asarray(s[k], dtype=float) * w)) for k in ("S0", "S1", "S2", "S3")}
    out["solid_angle_sr"] = float(np.sum(w))
    out["metrics"] = scalar_stokes(out)
    return out


def summary(a):
    a = np.asarray(a, dtype=float)
    finite = a[np.isfinite(a)]
    if not len(finite):
        return {"mean": None, "worst": None, "max": None, "max_min_ripple": None, "coefficient_of_variation": None}
    mean = float(np.mean(finite)); std = float(np.std(finite))
    return {"mean": mean, "worst": float(np.min(finite)), "max": float(np.max(finite)),
            "max_min_ripple": float(np.max(finite) - np.min(finite)),
            "coefficient_of_variation": float(std / abs(mean)) if mean != 0.0 else None}


def finite_on_disk(s, disk):
    return all(bool(np.all(np.isfinite(np.asarray(s[k])[disk]))) for k in ("S0", "S1", "S2", "S3"))


def extract_angular_pair(x_post: Path, y_post: Path, x_sourcepower, y_sourcepower, wl):
    fx = lumapi.FDTD(hide=True); fy = lumapi.FDTD(hide=True)
    try:
        fx.load(str(x_post)); fy.load(str(y_post))
        rows = []
        anchor = None
        for i, wavelength in enumerate(wl):
            ux = np.asarray(fx.farfieldux(MONITOR, i + 1), dtype=float).reshape(-1)
            uy = np.asarray(fx.farfielduy(MONITOR, i + 1), dtype=float).reshape(-1)
            ux_y = np.asarray(fy.farfieldux(MONITOR, i + 1), dtype=float).reshape(-1)
            uy_y = np.asarray(fy.farfielduy(MONITOR, i + 1), dtype=float).reshape(-1)
            if not np.array_equal(ux, ux_y) or not np.array_equal(uy, uy_y):
                raise RuntimeError(f"ANGULAR_GRID_MISMATCH:{wavelength}")
            vx = np.asarray(fx.farfieldvector3d(MONITOR, i + 1), dtype=np.complex128)
            vy = np.asarray(fy.farfieldvector3d(MONITOR, i + 1), dtype=np.complex128)
            ix = np.asarray(fx.farfield3d(MONITOR, i + 1), dtype=float)
            iy = np.asarray(fy.farfield3d(MONITOR, i + 1), dtype=float)
            if vx.ndim != 3 or vy.ndim != 3 or vx.shape[-1] < 2 or vy.shape[-1] < 2 or vx.shape != vy.shape or vx.shape[:2] != ix.shape or vy.shape[:2] != iy.shape:
                raise RuntimeError(f"ANGULAR_VECTOR_SHAPE_INVALID:{wavelength}:{vx.shape}:{vy.shape}:{ix.shape}:{iy.shape}")
            grid = solid_angle_grid(ux, uy)
            sx = stokes_from_fields(vx[:, :, 0], vx[:, :, 1])
            sy = stokes_from_fields(vy[:, :, 0], vy[:, :, 1])
            if not finite_on_disk(sx, grid["propagating"]) or not finite_on_disk(sy, grid["propagating"]):
                raise RuntimeError(f"ANGULAR_NONFINITE:{wavelength}")
            spx = float(x_sourcepower[i]); spy = float(y_sourcepower[i])
            if not math.isfinite(spx) or not math.isfinite(spy) or spx <= 0.0 or spy <= 0.0:
                raise RuntimeError(f"SOURCEPOWER_INVALID:{wavelength}")
            ax = {k: sx[k] / spx for k in ("S0", "S1", "S2", "S3")}
            ay = {k: sy[k] / spy for k in ("S0", "S1", "S2", "S3")}
            ap = metric_arrays({k: 0.5 * (ax[k] + ay[k]) for k in ("S0", "S1", "S2", "S3")})
            mask = grid["propagating"]
            full = integrate(ap, grid, mask)
            local_l = float(np.sum(ap["Lmag"] * grid["domega"] * mask))
            c_angular = float(np.hypot(full["S1"], full["S2"]) / local_l) if local_l > 0.0 else float("nan")
            local_dolp = float(local_l / full["S0"]) if full["S0"] > 0.0 else float("nan")
            cone_values = {}
            for degrees in (5.0, 10.0, 20.0):
                cone = integrate(ap, grid, mask & (grid["theta_deg"] <= degrees + 1e-9))
                cone_values[str(int(degrees))] = cone["metrics"]["DoLP"]
            row = {
                "wavelength_nm": float(wavelength),
                "angular_local_DoLP_powerweighted": local_dolp,
                "C_angular": c_angular,
                "full_angle_pair_DoLP": full["metrics"]["DoLP"],
                "full_angle_pair_DoCP": full["metrics"]["DoCP"],
                "full_angle_pair_useful_LP_axisfree": full["metrics"]["useful_LP_axisfree"],
                "full_angle_upward_source_normalized_power": float(np.sum(0.5 * (ix / spx + iy / spy) * grid["domega"] * mask)),
                "normal_5deg_DoLP": cone_values["5"], "normal_10deg_DoLP": cone_values["10"], "normal_20deg_DoLP": cone_values["20"],
                "angular_grid_points": int(ux.size * uy.size), "propagating_pixels": int(np.count_nonzero(mask)),
            }
            rows.append(row)
            if abs(float(wavelength) - 450.0) < 1e-9:
                anchor = {"row": row, "grid": grid, "pair": ap, "intensity_pair": 0.5 * (ix / spx + iy / spy)}
        if anchor is None:
            raise RuntimeError("ANGULAR_450_ANCHOR_MISSING")
        return rows, anchor
    finally:
        fx.close(); fy.close()


def run(args):
    x_stokes = load_csv(args.x_dir / "source_stokes.csv")
    y_stokes = load_csv(args.y_dir / "source_stokes.csv")
    x_flux = load_csv(args.x_dir / "source_closed_flux.csv")
    y_flux = load_csv(args.y_dir / "source_closed_flux.csv")
    x_far = args.x_dir / "source_farfield_metrics.csv"; y_far = args.y_dir / "source_farfield_metrics.csv"
    if not x_far.exists() or not y_far.exists():
        raise RuntimeError("SOURCE_FARFIELD_METRICS_MISSING")
    wl = x_stokes["wavelength_nm"]
    if len(wl) != 101 or not np.all(np.isfinite(wl)) or not np.all(np.diff(wl) > 0.0) or not np.array_equal(wl, y_stokes["wavelength_nm"]):
        raise RuntimeError("PAIR_SPECTRAL_GRID_INVALID_OR_MISMATCH")
    for data in (x_flux, y_flux):
        if not np.array_equal(wl, data["wavelength_nm"]):
            raise RuntimeError("PAIR_FLUX_GRID_MISMATCH")
    for label, data in (("x", x_stokes), ("y", y_stokes)):
        required = ["sourcepower_normalized_S0", "sourcepower_normalized_S1", "sourcepower_normalized_S2", "sourcepower_normalized_S3"]
        if any(k not in data for k in required):
            raise RuntimeError(f"STOKES_COLUMNS_MISSING:{label}")
    sx = {k: x_stokes[f"sourcepower_normalized_{k}"] for k in ("S0", "S1", "S2", "S3")}
    sy = {k: y_stokes[f"sourcepower_normalized_{k}"] for k in ("S0", "S1", "S2", "S3")}
    pair = metric_arrays({k: 0.5 * (sx[k] + sy[k]) for k in ("S0", "S1", "S2", "S3")})
    mx = metric_arrays({k: sx[k] for k in sx}); my = metric_arrays({k: sy[k] for k in sy})
    lx = np.column_stack([sx["S1"], sx["S2"]]); ly = np.column_stack([sy["S1"], sy["S2"]])
    lxmag = np.linalg.norm(lx, axis=1); lymag = np.linalg.norm(ly, axis=1)
    c_source = np.divide(np.linalg.norm(lx + ly, axis=1), lxmag + lymag, out=np.full_like(lxmag, np.nan), where=(lxmag + lymag) > 0.0)
    angle_source = np.degrees(np.arccos(np.clip(np.divide(np.sum(lx * ly, axis=1), lxmag * lymag, out=np.full_like(lxmag, np.nan), where=(lxmag * lymag) > 0.0), -1.0, 1.0)))
    s0_ratio = np.divide(sx["S0"], sy["S0"], out=np.full_like(sx["S0"], np.nan), where=sy["S0"] != 0.0)
    nx = np.column_stack([mx[k] / mx["S0"] for k in ("S1", "S2", "S3")])
    ny = np.column_stack([my[k] / my["S0"] for k in ("S1", "S2", "S3")])
    poincare_sep = np.degrees(np.arccos(np.clip(np.sum(nx * ny, axis=1), -1.0, 1.0)))
    axis_confident = (mx["DoLP"] >= AXIS_CONFIDENCE_DOLP) & (my["DoLP"] >= AXIS_CONFIDENCE_DOLP)

    rows = []
    for i, wavelength in enumerate(wl):
        rows.append({
            "wavelength_nm": float(wavelength),
            "S0_x_sourcepower_normalized": float(sx["S0"][i]), "S1_x_sourcepower_normalized": float(sx["S1"][i]), "S2_x_sourcepower_normalized": float(sx["S2"][i]), "S3_x_sourcepower_normalized": float(sx["S3"][i]),
            "S0_y_sourcepower_normalized": float(sy["S0"][i]), "S1_y_sourcepower_normalized": float(sy["S1"][i]), "S2_y_sourcepower_normalized": float(sy["S2"][i]), "S3_y_sourcepower_normalized": float(sy["S3"][i]),
            "S0_pair_sourcepower_normalized": float(pair["S0"][i]), "S1_pair_sourcepower_normalized": float(pair["S1"][i]), "S2_pair_sourcepower_normalized": float(pair["S2"][i]), "S3_pair_sourcepower_normalized": float(pair["S3"][i]),
            "DoLP_pair": float(pair["DoLP"][i]), "DoCP_pair": float(pair["DoCP"][i]), "psi_pair_deg": float(pair["psi_deg"][i]), "psi_axis_ill_conditioned": bool(pair["DoLP"][i] < AXIS_CONFIDENCE_DOLP),
            "useful_LP_axisfree_pair": float(pair["useful_LP_axisfree"][i]), "useful_LP_over_S0_pair": float(pair["useful_LP_over_S0"][i]),
            "upward_source_normalized_power_pair": float(0.5 * (x_flux["top_W"][i] / x_flux["sourcepower_W"][i] + y_flux["top_W"][i] / y_flux["sourcepower_W"][i])),
            "x_y_S0_ratio": float(s0_ratio[i]), "C_source": float(c_source[i]), "source_linear_Stokes_angle_deg": float(angle_source[i]),
            "Poincare_separation_deg": float(poincare_sep[i]), "individual_axis_confident": bool(axis_confident[i]),
        })
    write_csv(args.output_dir / "pair_wavelength_metrics.csv", rows)
    write_csv(args.output_dir / "source_cancellation_metrics.csv", [{"wavelength_nm": float(wl[i]), "C_source": float(c_source[i]), "source_linear_Stokes_angle_deg": float(angle_source[i]), "x_y_S0_ratio": float(s0_ratio[i]), "source_cancellation_fraction": float(1.0 - c_source[i])} for i in range(len(wl))])
    write_csv(args.output_dir / "pair_stokes.csv", [{"wavelength_nm": float(wl[i]), **{k: float(pair[k][i]) for k in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "useful_LP_axisfree", "useful_LP_over_S0")}} for i in range(len(wl))])

    angular_rows, angular_anchor = extract_angular_pair(args.x_post_fsp, args.y_post_fsp, x_flux["sourcepower_W"], y_flux["sourcepower_W"], wl)
    write_csv(args.output_dir / "angular_cancellation_metrics.csv", angular_rows)
    np.savez_compressed(args.output_dir / "pair_angular_450nm.npz", ux=angular_anchor["grid"]["uxg"][:, 0], uy=angular_anchor["grid"]["uyg"][0, :], propagating=angular_anchor["grid"]["propagating"], domega=angular_anchor["grid"]["domega"], S0=angular_anchor["pair"]["S0"], S1=angular_anchor["pair"]["S1"], S2=angular_anchor["pair"]["S2"], S3=angular_anchor["pair"]["S3"], DoLP=angular_anchor["pair"]["DoLP"], intensity_pair=angular_anchor["intensity_pair"])

    i450 = exact_450(wl)
    angular450 = angular_rows[i450]
    anchor = {"wavelength_nm": float(wl[i450]), "pair": scalar_stokes({k: pair[k][i450] for k in ("S0", "S1", "S2", "S3")}), "x": scalar_stokes({k: sx[k][i450] for k in ("S0", "S1", "S2", "S3")}), "y": scalar_stokes({k: sy[k][i450] for k in ("S0", "S1", "S2", "S3")}), "upward_source_normalized_power_pair": rows[i450]["upward_source_normalized_power_pair"], "x_y_S0_ratio": rows[i450]["x_y_S0_ratio"], "C_source": rows[i450]["C_source"], "source_linear_Stokes_angle_deg": rows[i450]["source_linear_Stokes_angle_deg"], "Poincare_separation_deg": rows[i450]["Poincare_separation_deg"], "angular": angular450}
    write_json(args.output_dir / "pair_450nm_anchor.json", anchor)

    broad = {
        "spectral_grid_nm": {"start": float(wl[0]), "stop": float(wl[-1]), "points": int(len(wl)), "spacing": float(np.median(np.diff(wl)))},
        "pair_DoLP": summary(pair["DoLP"]), "pair_useful_LP_axisfree": summary(pair["useful_LP_axisfree"]), "pair_useful_LP_over_S0": summary(pair["useful_LP_over_S0"]),
        "pair_DoCP": summary(pair["DoCP"]), "upward_source_normalized_power": summary(np.asarray([r["upward_source_normalized_power_pair"] for r in rows])),
        "C_source": summary(c_source), "source_linear_Stokes_angle_deg": summary(angle_source), "x_y_S0_ratio": summary(s0_ratio),
        "Poincare_separation_deg": summary(poincare_sep), "individual_axis_confident_points": int(np.count_nonzero(axis_confident)),
        "angular_local_DoLP_powerweighted": summary(np.asarray([r["angular_local_DoLP_powerweighted"] for r in angular_rows])), "C_angular": summary(np.asarray([r["C_angular"] for r in angular_rows])),
        "full_angle_pair_DoLP": summary(np.asarray([r["full_angle_pair_DoLP"] for r in angular_rows])), "normal_cone_DoLP": {f"{angle}_deg": summary(np.asarray([r[f"normal_{angle}deg_DoLP"] for r in angular_rows])) for angle in (5, 10, 20)},
        "no_single_point_support": True,
    }
    write_json(args.output_dir / "pair_broadband_summary.json", broad)
    statuses = {"x": load_json(args.x_dir / "validity_gate_v2.json").get("status"), "y": load_json(args.y_dir / "validity_gate_v2.json").get("status")}
    status = "PASS" if all(value == "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH" for value in statuses.values()) and all(np.isfinite(pair[k]).all() for k in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "useful_LP_axisfree")) and all(np.isfinite(r["C_angular"]) for r in angular_rows) else "HARD_GATE"
    result = {"schema": "PAPER_A_INTEGRATED_AWARE_LP_PAIR_CLOSEOUT_V1", "status": status, "candidate_id": args.candidate_id, "x_case": args.x_case, "y_case": args.y_case, "source_validity": statuses, "anchor_450nm": anchor, "broadband": broad, "combination": "S_i_pair=0.5*S_i_x+0.5*S_i_y; incoherent power/coherency; no field addition; no DoLP/psi averaging", "axis_confidence_definition": "psi_axis_ill_conditioned when pair DoLP < 0.10; raw psi retained", "W_emit": "UNRESOLVED_FOR_PRODUCTION_CLOSURE", "solver_accounting": {"postprocess_solver_run_called": False, "postprocess_solver_entered": 0, "new_solver": 0}, "timestamp_utc": now()}
    write_json(args.output_dir / "pair_summary.json", result)
    audit = {"schema": "PAPER_A_INTEGRATED_AWARE_LP_PAIR_AUDIT_V1", "status": status, "inputs": {str(path): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in (args.x_dir / "source_stokes.csv", args.y_dir / "source_stokes.csv", args.x_dir / "source_closed_flux.csv", args.y_dir / "source_closed_flux.csv", x_far, y_far, args.x_dir / "validity_gate_v2.json", args.y_dir / "validity_gate_v2.json")}, "tests": {"spectral_101_points": len(wl) == 101, "exact_450": True, "stokes_incoherent_combination": True, "angular_grid_full_wavelength": True, "finite_pair_metrics": status == "PASS", "no_new_solver": True}, "outputs": {str(path.name): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in args.output_dir.iterdir() if path.is_file()}, "timestamp_utc": now()}
    write_json(args.output_dir / "pair_audit.json", audit)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True); parser.add_argument("--x-case", required=True); parser.add_argument("--y-case", required=True)
    parser.add_argument("--x-dir", type=Path, required=True); parser.add_argument("--y-dir", type=Path, required=True)
    parser.add_argument("--x-post-fsp", type=Path, required=True); parser.add_argument("--y-post-fsp", type=Path, required=True); parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True); print(json.dumps(run(args), ensure_ascii=False, indent=2, default=str)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
