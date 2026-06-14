from __future__ import annotations

import argparse
import cmath
import csv
import math
import sys
import traceback
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi


OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch"
J1_PLAN = OUT_DIR / "j1_identity_patch_plan_stage11_1d.csv"
J2_PLAN = OUT_DIR / "j2_hwp_patch_plan_stage11_1d.csv"
FDTD_DIR = OUT_DIR / "fdtd_patch"
J1_RESULT = OUT_DIR / "j1_identity_patch_fdtd_results_stage11_1d.csv"
J2_RESULT = OUT_DIR / "j2_hwp_patch_fdtd_results_stage11_1d.csv"
SUMMARY_MD = OUT_DIR / "stage11_1d_fdtd_patch_summary.md"

SUMMARY_FIELDS = ["candidate_id", "role", "polarization", "transmission", "phase_rad", "phase_deg", "status", "fsp", "note"]

J1_FIELDS = [
    "candidate_id", "source_stage", "shape_family", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm",
    "target_bin_deg", "height_class", "tx_amp", "ty_amp", "tx_phase_deg", "ty_phase_deg", "retardance_deg",
    "retardance_abs_to_zero_deg", "amp_balance", "T_mean", "common_phase_deg", "identity_like_score",
    "identity_like_pass_loose", "identity_like_pass_strict", "s1_amp", "s1_phase_deg", "extraction_status",
    "x_result_csv", "y_result_csv", "x_fsp", "y_fsp", "notes",
]

J2_FIELDS = [
    "candidate_id", "source_stage", "base_candidate_id", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm",
    "length_nm", "width_nm", "rotation_deg", "target_bin_deg", "height_class", "tx_amp", "ty_amp",
    "tx_phase_deg", "ty_phase_deg", "retardance_deg", "retardance_abs_to_180_deg", "amp_balance", "T_mean",
    "common_phase_deg", "hwp_like_score", "hwp_like_pass_loose", "hwp_like_pass_strict", "s2_amp", "s2_phase_deg",
    "extraction_status", "x_result_csv", "y_result_csv", "x_fsp", "y_fsp", "notes",
]


def as_float(value: object, default: float = math.nan) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def truth(value: bool) -> str:
    return "true" if value else "false"


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def wrap360(value: float) -> float:
    return value % 360.0


def height_class(height_nm: float) -> str:
    if height_nm <= 500.0 + 1e-6:
        return "fab_main"
    if abs(height_nm - 600.0) <= 1e-6:
        return "fab_compromise"
    return "sim_upper_bound"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_j1_shape(fdtd: object, row: dict[str, str], height: float) -> None:
    nm = 1e-9
    family = row["shape_family"]
    if family == "circle":
        fdtd.addcircle()
        fdtd.set("name", "j1_identity_patch")
        fdtd.set("radius", 0.5 * as_float(row["diameter_nm"]) * nm)
    elif family in {"square", "near_square_rect"}:
        fdtd.addrect()
        fdtd.set("name", "j1_identity_patch")
        span = as_float(row.get("side_nm"))
        fdtd.set("x span", (span if family == "square" else as_float(row["length_nm"])) * nm)
        fdtd.set("y span", (span if family == "square" else as_float(row["width_nm"])) * nm)
    else:
        raise ValueError(f"unsupported Stage11-1D J1 patch shape: {family}")
    fdtd.set("z min", 0)
    fdtd.set("z max", height)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", 2.6)


def add_j2_shape(fdtd: object, row: dict[str, str], height: float) -> None:
    nm = 1e-9
    fdtd.addrect()
    fdtd.set("name", "j2_hwp_patch")
    fdtd.set("x span", as_float(row["length_nm"]) * nm)
    fdtd.set("y span", as_float(row["width_nm"]) * nm)
    fdtd.set("z min", 0)
    fdtd.set("z max", height)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", 2.6)


def build_model(fdtd: object, row: dict[str, str], role: str, polarization: str) -> None:
    nm = 1e-9
    px = as_float(row["p_x_nm"]) * nm
    py = as_float(row["p_y_nm"]) * nm
    height = as_float(row["height_nm"]) * nm
    wavelength = as_float(row["lambda_nm"]) * nm
    source_z = -250 * nm
    monitor_z = height + 350 * nm

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

    if role == "j1":
        add_j1_shape(fdtd, row, height)
    else:
        add_j2_shape(fdtd, row, height)

    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", source_z)
    fdtd.set("wavelength start", wavelength)
    fdtd.set("wavelength stop", wavelength)
    fdtd.set("polarization angle", 0 if polarization == "x" else 90)

    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", monitor_z)

    fdtd.addprofile()
    fdtd.set("name", "phase_monitor")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", px)
    fdtd.set("y span", py)
    fdtd.set("z", monitor_z)


def center_phase(fdtd: object, polarization: str) -> float:
    key = "Ex" if polarization == "x" else "Ey"
    value = fdtd.getdata("phase_monitor", key)
    if hasattr(value, "squeeze"):
        value = value.squeeze()
    shape = getattr(value, "shape", ())
    if shape:
        cur = value
        for axis_size in [int(s) for s in shape if int(s) != 1]:
            cur = cur[axis_size // 2]
        value = cur
    return float(cmath.phase(complex(value)))


def safe_transmission(fdtd: object) -> float:
    value = fdtd.transmission("T")
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (list, tuple)):
        value = value[0]
    return float(value)


def run_one(lumapi: object, runtime: object, row: dict[str, str], role: str, polarization: str) -> dict[str, object]:
    case_dir = FDTD_DIR / role / row["candidate_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    fsp_path = case_dir / f"{row['candidate_id']}_{polarization}.fsp"
    summary_path = case_dir / f"{row['candidate_id']}_{polarization}_summary.csv"
    status = "error"
    note = ""
    transmission = math.nan
    phase_rad = math.nan
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        build_model(fdtd, row, role, polarization)
        fdtd.save(str(fsp_path))
        fdtd.close()
        fdtd = None

        fdtd = lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        fdtd.load(str(fsp_path))
        fdtd.run()
        transmission = safe_transmission(fdtd)
        phase_rad = center_phase(fdtd, polarization)
        status = "ok"
    except Exception as exc:
        note = f"{type(exc).__name__}: {exc}\n{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    summary = {
        "candidate_id": row["candidate_id"],
        "role": role,
        "polarization": polarization,
        "transmission": fmt(transmission),
        "phase_rad": fmt(phase_rad),
        "phase_deg": fmt(math.degrees(phase_rad) if not math.isnan(phase_rad) else math.nan),
        "status": status,
        "fsp": str(fsp_path),
        "note": note,
    }
    write_csv(summary_path, [summary], SUMMARY_FIELDS)
    return {**summary, "summary_path": str(summary_path)}


def score_result(err: float, amp_balance: float, t_mean: float) -> float:
    return 100.0 * (
        0.45 * max(0.0, 1.0 - err / 45.0)
        + 0.35 * min(max(amp_balance, 0.0), 1.0)
        + 0.20 * min(t_mean / 0.5, 1.0)
    )


def fail_row(row: dict[str, str], role: str, x: dict[str, object], y: dict[str, object]) -> dict[str, object]:
    base_keys = J1_FIELDS if role == "j1" else J2_FIELDS
    out = {key: row.get(key, "") for key in base_keys}
    out.update(
        {
            "height_class": height_class(as_float(row.get("height_nm"))),
            "extraction_status": "failed",
            "x_result_csv": x.get("summary_path", ""),
            "y_result_csv": y.get("summary_path", ""),
            "x_fsp": x.get("fsp", ""),
            "y_fsp": y.get("fsp", ""),
            "notes": (str(x.get("note", "")) + "; " + str(y.get("note", "")))[:1000],
        }
    )
    if role == "j1":
        out["identity_like_pass_loose"] = "false"
        out["identity_like_pass_strict"] = "false"
    else:
        out["hwp_like_pass_loose"] = "false"
        out["hwp_like_pass_strict"] = "false"
    return out


def combine_j1(row: dict[str, str], x: dict[str, object], y: dict[str, object]) -> dict[str, object]:
    if x["status"] != "ok" or y["status"] != "ok":
        return fail_row(row, "j1", x, y)
    tx_amp = math.sqrt(max(as_float(x["transmission"]), 0.0))
    ty_amp = math.sqrt(max(as_float(y["transmission"]), 0.0))
    tx_phase_deg = math.degrees(as_float(x["phase_rad"]))
    ty_phase_deg = math.degrees(as_float(y["phase_rad"]))
    tx = tx_amp * cmath.exp(1j * math.radians(tx_phase_deg))
    ty = ty_amp * cmath.exp(1j * math.radians(ty_phase_deg))
    retardance = wrap180(ty_phase_deg - tx_phase_deg)
    err0 = abs(retardance)
    amp_balance = min(tx_amp, ty_amp) / max(tx_amp, ty_amp) if max(tx_amp, ty_amp) > 0 else math.nan
    t_mean = (tx_amp * tx_amp + ty_amp * ty_amp) / 2.0
    s1 = (tx + ty) / 2.0
    s1_amp = abs(s1)
    s1_phase = wrap360(math.degrees(cmath.phase(s1))) if s1_amp > 1e-12 else math.nan
    score = score_result(err0, amp_balance, t_mean)
    loose = err0 <= 25 and amp_balance >= 0.75 and t_mean >= 0.15
    strict = err0 <= 12 and amp_balance >= 0.85 and t_mean >= 0.25
    return {
        **{k: row.get(k, "") for k in ["candidate_id", "source_stage", "shape_family", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm", "target_bin_deg"]},
        "height_class": height_class(as_float(row["height_nm"])),
        "tx_amp": fmt(tx_amp),
        "ty_amp": fmt(ty_amp),
        "tx_phase_deg": fmt(wrap180(tx_phase_deg)),
        "ty_phase_deg": fmt(wrap180(ty_phase_deg)),
        "retardance_deg": fmt(retardance),
        "retardance_abs_to_zero_deg": fmt(err0),
        "amp_balance": fmt(amp_balance),
        "T_mean": fmt(t_mean),
        "common_phase_deg": fmt(s1_phase),
        "identity_like_score": fmt(score),
        "identity_like_pass_loose": truth(loose),
        "identity_like_pass_strict": truth(strict),
        "s1_amp": fmt(s1_amp),
        "s1_phase_deg": fmt(s1_phase),
        "extraction_status": "ok",
        "x_result_csv": x.get("summary_path", ""),
        "y_result_csv": y.get("summary_path", ""),
        "x_fsp": x.get("fsp", ""),
        "y_fsp": y.get("fsp", ""),
        "notes": "Stage11-1D J1 formula: s1/common_phase = angle((tx_complex + ty_complex) / 2)",
    }


def combine_j2(row: dict[str, str], x: dict[str, object], y: dict[str, object]) -> dict[str, object]:
    if x["status"] != "ok" or y["status"] != "ok":
        return fail_row(row, "j2", x, y)
    tx_amp = math.sqrt(max(as_float(x["transmission"]), 0.0))
    ty_amp = math.sqrt(max(as_float(y["transmission"]), 0.0))
    tx_phase_deg = math.degrees(as_float(x["phase_rad"]))
    ty_phase_deg = math.degrees(as_float(y["phase_rad"]))
    tx = tx_amp * cmath.exp(1j * math.radians(tx_phase_deg))
    ty = ty_amp * cmath.exp(1j * math.radians(ty_phase_deg))
    retardance = wrap180(ty_phase_deg - tx_phase_deg)
    err180 = abs(abs(retardance) - 180.0)
    amp_balance = min(tx_amp, ty_amp) / max(tx_amp, ty_amp) if max(tx_amp, ty_amp) > 0 else math.nan
    t_mean = (tx_amp * tx_amp + ty_amp * ty_amp) / 2.0
    s2 = (tx - ty) / 2.0
    s2_amp = abs(s2)
    s2_phase = wrap360(math.degrees(cmath.phase(s2))) if s2_amp > 1e-12 else math.nan
    score = score_result(err180, amp_balance, t_mean)
    loose = err180 <= 25 and amp_balance >= 0.65 and t_mean >= 0.10
    strict = err180 <= 12 and amp_balance >= 0.75 and t_mean >= 0.20
    return {
        **{k: row.get(k, "") for k in ["candidate_id", "source_stage", "base_candidate_id", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm", "length_nm", "width_nm", "rotation_deg", "target_bin_deg"]},
        "height_class": height_class(as_float(row["height_nm"])),
        "tx_amp": fmt(tx_amp),
        "ty_amp": fmt(ty_amp),
        "tx_phase_deg": fmt(wrap180(tx_phase_deg)),
        "ty_phase_deg": fmt(wrap180(ty_phase_deg)),
        "retardance_deg": fmt(retardance),
        "retardance_abs_to_180_deg": fmt(err180),
        "amp_balance": fmt(amp_balance),
        "T_mean": fmt(t_mean),
        "common_phase_deg": fmt(s2_phase),
        "hwp_like_score": fmt(score),
        "hwp_like_pass_loose": truth(loose),
        "hwp_like_pass_strict": truth(strict),
        "s2_amp": fmt(s2_amp),
        "s2_phase_deg": fmt(s2_phase),
        "extraction_status": "ok",
        "x_result_csv": x.get("summary_path", ""),
        "y_result_csv": y.get("summary_path", ""),
        "x_fsp": x.get("fsp", ""),
        "y_fsp": y.get("fsp", ""),
        "notes": "Stage11-1D J2 formula: s2/common_phase = angle((tx_complex - ty_complex) / 2)",
    }


def write_summary(j1_rows: list[dict[str, object]], j2_rows: list[dict[str, object]], dry_run: bool) -> None:
    def count(rows: list[dict[str, object]], key: str, value: str) -> int:
        return sum(1 for r in rows if str(r.get(key, "")) == value)
    lines = [
        "# Stage11-1D Targeted Patch FDTD Summary",
        "",
        f"mode = {'dry_run_no_lumerical' if dry_run else 'real_single_pillar_fdtd_patch'}",
        f"J1 result_count = {len(j1_rows)}",
        f"J1 success = {count(j1_rows, 'extraction_status', 'ok')}",
        f"J1 failed = {count(j1_rows, 'extraction_status', 'failed')}",
        f"J1 loose_pass = {count(j1_rows, 'identity_like_pass_loose', 'true')}",
        f"J1 strict_pass = {count(j1_rows, 'identity_like_pass_strict', 'true')}",
        f"J2 result_count = {len(j2_rows)}",
        f"J2 success = {count(j2_rows, 'extraction_status', 'ok')}",
        f"J2 failed = {count(j2_rows, 'extraction_status', 'failed')}",
        f"J2 loose_pass = {count(j2_rows, 'hwp_like_pass_loose', 'true')}",
        f"J2 strict_pass = {count(j2_rows, 'hwp_like_pass_strict', 'true')}",
        "",
        "Evidence boundary: Stage11-1D ran only single-pillar x/y normal-incidence extraction. No dimer FDTD and no K=6 full FDTD are run here.",
        "No H700 cases are in the targeted patch plan.",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def dry_rows(rows: list[dict[str, str]], role: str) -> list[dict[str, object]]:
    fields = J1_FIELDS if role == "j1" else J2_FIELDS
    out = []
    for row in rows:
        d = {key: row.get(key, "") for key in fields}
        d["height_class"] = height_class(as_float(row.get("height_nm")))
        d["extraction_status"] = "dry_run"
        d["notes"] = "dry-run only; Lumerical not imported"
        if role == "j1":
            d["identity_like_pass_loose"] = "false"
            d["identity_like_pass_strict"] = "false"
        else:
            d["hwp_like_pass_loose"] = "false"
            d["hwp_like_pass_strict"] = "false"
        out.append(d)
    return out


def run_role(lumapi: object, runtime: object, rows: list[dict[str, str]], role: str, result_path: Path, fields: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for row in rows:
        if height_class(as_float(row.get("height_nm"))) == "sim_upper_bound":
            raise RuntimeError(f"H700/sim_upper_bound case is not allowed in Stage11-1D patch: {row['candidate_id']}")
        print(f"running={role}:{row['candidate_id']} x")
        x = run_one(lumapi, runtime, row, role, "x")
        print(f"running={role}:{row['candidate_id']} y")
        y = run_one(lumapi, runtime, row, role, "y")
        combined = combine_j1(row, x, y) if role == "j1" else combine_j2(row, x, y)
        results.append(combined)
        write_csv(result_path, results, fields)
        print(f"done={role}:{row['candidate_id']} status={combined['extraction_status']}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--j1-plan", default=str(J1_PLAN))
    parser.add_argument("--j2-plan", default=str(J2_PLAN))
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--max-j1", type=int, default=72)
    parser.add_argument("--max-j2", type=int, default=96)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    j1_rows = read_csv(Path(args.j1_plan))[: args.max_j1]
    j2_rows = read_csv(Path(args.j2_plan))[: args.max_j2]
    print(f"selected_j1_count={len(j1_rows)}")
    print(f"selected_j2_count={len(j2_rows)}")
    print(f"selected_H700_count={sum(1 for r in j1_rows + j2_rows if height_class(as_float(r.get('height_nm'))) == 'sim_upper_bound')}")
    for row in (j1_rows[:6] + j2_rows[:6]):
        print(f"case={row['candidate_id']} H={row['height_nm']} target_bin={row.get('target_bin_deg', '')}")

    if args.dry_run:
        j1_dry = dry_rows(j1_rows, "j1")
        j2_dry = dry_rows(j2_rows, "j2")
        write_summary(j1_dry, j2_dry, dry_run=True)
        return 0

    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    j1_results = run_role(lumapi, runtime, j1_rows, "j1", J1_RESULT, J1_FIELDS)
    j2_results = run_role(lumapi, runtime, j2_rows, "j2", J2_RESULT, J2_FIELDS)
    write_summary(j1_results, j2_results, dry_run=False)
    print(f"j1_result_csv={J1_RESULT}")
    print(f"j2_result_csv={J2_RESULT}")
    print(f"j1_success={sum(1 for r in j1_results if r['extraction_status'] == 'ok')}")
    print(f"j2_success={sum(1 for r in j2_results if r['extraction_status'] == 'ok')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
