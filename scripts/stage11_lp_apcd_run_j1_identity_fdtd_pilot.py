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


IN_CSV = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_pilot_cases.csv"
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan"
PILOT_DIR = OUT_DIR / "fdtd_pilot"
RESULT_CSV = OUT_DIR / "j1_identity_fdtd_results_pilot.csv"
SUMMARY_MD = OUT_DIR / "j1_identity_fdtd_summary_pilot.md"

RESULT_FIELDS = [
    "candidate_id",
    "shape_family",
    "material",
    "lambda_nm",
    "p_x_nm",
    "p_y_nm",
    "height_nm",
    "tx_amp",
    "ty_amp",
    "tx_phase_deg",
    "ty_phase_deg",
    "retardance_deg",
    "retardance_abs_to_zero_deg",
    "amp_balance",
    "T_mean",
    "common_phase_deg",
    "identity_like_score",
    "identity_like_pass_loose",
    "identity_like_pass_strict",
    "extraction_status",
    "x_result_csv",
    "y_result_csv",
    "x_fsp",
    "y_fsp",
    "notes",
]

SUMMARY_FIELDS = [
    "candidate_id",
    "polarization",
    "transmission",
    "phase_rad",
    "phase_deg",
    "status",
    "fsp",
    "note",
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


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def wrap360(value: float) -> float:
    return value % 360.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_model(fdtd: object, row: dict[str, str], polarization: str) -> None:
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

    add_shape(fdtd, row, height)

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


def add_shape(fdtd: object, row: dict[str, str], height: float) -> None:
    nm = 1e-9
    family = row["shape_family"]
    material_index = 2.6
    if family in {"square", "near_square_rect"}:
        fdtd.addrect()
        fdtd.set("name", "j1_pillar")
        fdtd.set("x span", as_float(row.get("side_nm")) * nm if family == "square" else as_float(row["length_nm"]) * nm)
        fdtd.set("y span", as_float(row.get("side_nm")) * nm if family == "square" else as_float(row["width_nm"]) * nm)
    elif family in {"circle", "near_circle_ellipse"}:
        fdtd.addcircle()
        fdtd.set("name", "j1_pillar")
        if family == "circle":
            fdtd.set("radius", 0.5 * as_float(row["diameter_nm"]) * nm)
        else:
            # Lumerical circle supports x/y radius in recent versions; if not, this case will fail honestly.
            fdtd.set("x radius", 0.5 * as_float(row["length_nm"]) * nm)
            fdtd.set("y radius", 0.5 * as_float(row["width_nm"]) * nm)
    elif family in {"regular_hexagon", "regular_octagon"}:
        sides = 6 if family == "regular_hexagon" else 8
        radius = 0.5 * as_float(row["diameter_nm"]) * nm
        vertices = [
            [radius * math.cos(2 * math.pi * i / sides), radius * math.sin(2 * math.pi * i / sides)]
            for i in range(sides)
        ]
        fdtd.addpoly()
        fdtd.set("name", "j1_pillar")
        fdtd.set("vertices", vertices)
    else:
        raise ValueError(f"unsupported shape_family: {family}")
    fdtd.set("z min", 0)
    fdtd.set("z max", height)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", material_index)


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


def run_one(lumapi: object, runtime: object, row: dict[str, str], polarization: str) -> dict[str, object]:
    case_dir = PILOT_DIR / row["candidate_id"]
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
        build_model(fdtd, row, polarization)
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


def score_result(retardance_abs: float, amp_balance: float, t_mean: float) -> float:
    return 100.0 * (
        0.45 * max(0.0, 1.0 - retardance_abs / 45.0)
        + 0.35 * min(max(amp_balance, 0.0), 1.0)
        + 0.20 * min(t_mean / 0.5, 1.0)
    )


def combine_result(row: dict[str, str], x: dict[str, object], y: dict[str, object]) -> dict[str, object]:
    notes = []
    if x["status"] != "ok":
        notes.append("x extraction failed")
    if y["status"] != "ok":
        notes.append("y extraction failed")
    if x["status"] != "ok" or y["status"] != "ok":
        return {
            **{k: row.get(k, "") for k in ["candidate_id", "shape_family", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm"]},
            "tx_amp": "",
            "ty_amp": "",
            "tx_phase_deg": "",
            "ty_phase_deg": "",
            "retardance_deg": "",
            "retardance_abs_to_zero_deg": "",
            "amp_balance": "",
            "T_mean": "",
            "common_phase_deg": "",
            "identity_like_score": "",
            "identity_like_pass_loose": "false",
            "identity_like_pass_strict": "false",
            "extraction_status": "failed",
            "x_result_csv": x.get("summary_path", ""),
            "y_result_csv": y.get("summary_path", ""),
            "x_fsp": x.get("fsp", ""),
            "y_fsp": y.get("fsp", ""),
            "notes": "; ".join(notes + [str(x.get("note", ""))[:500], str(y.get("note", ""))[:500]]),
        }
    tx_amp = math.sqrt(max(as_float(x["transmission"]), 0.0))
    ty_amp = math.sqrt(max(as_float(y["transmission"]), 0.0))
    tx_phase_deg = math.degrees(as_float(x["phase_rad"]))
    ty_phase_deg = math.degrees(as_float(y["phase_rad"]))
    tx_complex = tx_amp * cmath.exp(1j * math.radians(tx_phase_deg))
    ty_complex = ty_amp * cmath.exp(1j * math.radians(ty_phase_deg))
    retardance = wrap180(ty_phase_deg - tx_phase_deg)
    retardance_abs = abs(retardance)
    amp_balance = min(tx_amp, ty_amp) / max(tx_amp, ty_amp) if max(tx_amp, ty_amp) > 0 else math.nan
    t_mean = (tx_amp * tx_amp + ty_amp * ty_amp) / 2.0
    common = (tx_complex + ty_complex) / 2.0
    common_phase = wrap360(math.degrees(cmath.phase(common))) if abs(common) > 1e-12 else math.nan
    score = score_result(retardance_abs, amp_balance, t_mean)
    loose = retardance_abs <= 25 and amp_balance >= 0.75 and t_mean >= 0.15
    strict = retardance_abs <= 12 and amp_balance >= 0.85 and t_mean >= 0.25
    return {
        **{k: row.get(k, "") for k in ["candidate_id", "shape_family", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm"]},
        "tx_amp": fmt(tx_amp),
        "ty_amp": fmt(ty_amp),
        "tx_phase_deg": fmt(wrap180(tx_phase_deg)),
        "ty_phase_deg": fmt(wrap180(ty_phase_deg)),
        "retardance_deg": fmt(retardance),
        "retardance_abs_to_zero_deg": fmt(retardance_abs),
        "amp_balance": fmt(amp_balance),
        "T_mean": fmt(t_mean),
        "common_phase_deg": fmt(common_phase),
        "identity_like_score": fmt(score),
        "identity_like_pass_loose": str(loose).lower(),
        "identity_like_pass_strict": str(strict).lower(),
        "extraction_status": "ok",
        "x_result_csv": x.get("summary_path", ""),
        "y_result_csv": y.get("summary_path", ""),
        "x_fsp": x.get("fsp", ""),
        "y_fsp": y.get("fsp", ""),
        "notes": "Stage11 formula: common_phase_deg = angle((tx_complex + ty_complex) / 2); not an arithmetic phase average",
    }


def write_summary(results: list[dict[str, object]], dry_run: bool) -> None:
    ok = [r for r in results if r.get("extraction_status") == "ok"]
    failed = [r for r in results if r.get("extraction_status") == "failed"]
    loose = [r for r in ok if r.get("identity_like_pass_loose") == "true"]
    strict = [r for r in ok if r.get("identity_like_pass_strict") == "true"]
    top = sorted(ok, key=lambda r: -as_float(r.get("identity_like_score")),)[:10]
    lines = [
        "# Stage11-1A J1 Identity-Like FDTD Pilot Summary",
        "",
        f"mode = {'dry_run_no_lumerical' if dry_run else 'real_lumerical_fdtd_pilot'}",
        f"result_count = {len(results)}",
        f"successfully_extracted_count = {len(ok)}",
        f"failed_count = {len(failed)}",
        "skipped_count = 0",
        f"loose_pass_count = {len(loose)}",
        f"strict_pass_count = {len(strict)}",
        "",
        "Score definition:",
        "`identity_like_score = 100 * (0.45 * max(0, 1 - retardance_abs_to_zero_deg/45) + 0.35 * amp_balance + 0.20 * min(T_mean/0.5, 1))`.",
        "",
        "Common phase definition:",
        "`common_phase_deg = angle((tx_amp*exp(i*tx_phase) + ty_amp*exp(i*ty_phase)) / 2)`.",
        "",
        "Evidence boundary: this is J1 single-pillar pilot extraction only. No K=6 full FDTD, no dimer FDTD, and no LP steering proof.",
        "",
        "## Top 10",
        "",
        "| candidate_id | shape_family | height_nm | tx_amp | ty_amp | retardance_deg | amp_balance | T_mean | common_phase_deg | identity_like_score |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in top:
        lines.append(
            f"| {r['candidate_id']} | {r['shape_family']} | {r['height_nm']} | {r['tx_amp']} | {r['ty_amp']} | {r['retardance_deg']} | {r['amp_balance']} | {r['T_mean']} | {r['common_phase_deg']} | {r['identity_like_score']} |"
        )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(IN_CSV))
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--max-cases", type=int, default=24)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = read_csv(Path(args.input))[: args.max_cases]
    print(f"selected_case_count={len(rows)}")
    for row in rows:
        print(f"case={row['candidate_id']} shape={row['shape_family']} height={row['height_nm']} x/y")
    if args.dry_run:
        dry_rows = [
            {
                **{k: row.get(k, "") for k in ["candidate_id", "shape_family", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm"]},
                "tx_amp": "",
                "ty_amp": "",
                "tx_phase_deg": "",
                "ty_phase_deg": "",
                "retardance_deg": "",
                "retardance_abs_to_zero_deg": "",
                "amp_balance": "",
                "T_mean": "",
                "common_phase_deg": "",
                "identity_like_score": "",
                "identity_like_pass_loose": "false",
                "identity_like_pass_strict": "false",
                "extraction_status": "dry_run",
                "x_result_csv": "",
                "y_result_csv": "",
                "x_fsp": "",
                "y_fsp": "",
                "notes": "dry-run only; Lumerical not imported",
            }
            for row in rows
        ]
        write_summary(dry_rows, dry_run=True)
        return 0

    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    results: list[dict[str, object]] = []
    for row in rows:
        print(f"running={row['candidate_id']} x")
        x = run_one(lumapi, runtime, row, "x")
        print(f"running={row['candidate_id']} y")
        y = run_one(lumapi, runtime, row, "y")
        combined = combine_result(row, x, y)
        results.append(combined)
        write_csv(RESULT_CSV, results, RESULT_FIELDS)
        write_summary(results, dry_run=False)
        print(f"done={row['candidate_id']} status={combined['extraction_status']}")
    print(f"result_csv={RESULT_CSV}")
    print(f"successfully_extracted_count={sum(1 for r in results if r['extraction_status'] == 'ok')}")
    print(f"failed_count={sum(1 for r in results if r['extraction_status'] == 'failed')}")
    print("skipped_count=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
