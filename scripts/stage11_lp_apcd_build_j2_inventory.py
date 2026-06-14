from __future__ import annotations

import argparse
import cmath
import csv
import json
import math
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_pairing"

BASELINE_WAVELENGTH_NM = 450.0
BASELINE_PX_NM = 431.907786
BASELINE_PY_NM = 432.0
BASELINE_HEIGHTS_NM = {500.0, 600.0, 700.0}
BASELINE_MATERIAL_TOKENS = {"n260", "n2p6", "dielectric_n2p6_blue_baseline", "gan"}

FIELDNAMES = [
    "candidate_id",
    "source",
    "geometry_params",
    "material",
    "lambda_nm",
    "p_x_nm",
    "p_y_nm",
    "height_nm",
    "tx_amp",
    "ty_amp",
    "tx_phase_deg",
    "ty_phase_deg",
    "retardance_to_hwp_deg",
    "amp_balance",
    "T_mean",
    "common_phase_deg",
    "hwp_like_score",
    "source_result_csv",
    "reusable_status",
    "reason",
]

STAGE11_1B_RESULT = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_fdtd_results_pilot.csv"
STAGE11_1B_INVENTORY = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_pairing" / "j2_reuse_inventory_stage11_1b.csv"


def wrap180(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def wrap360(x: float) -> float:
    return x % 360.0


def as_float(value: object) -> float:
    if value is None:
        return math.nan
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


def first_value(row: dict[str, str], names: list[str]) -> str:
    lower = {k.lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lower and str(lower[name.lower()]).strip():
            return str(lower[name.lower()]).strip()
    return ""


def read_csv(path: Path, max_rows: int = 200) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = []
            for i, row in enumerate(csv.DictReader(f)):
                if i >= max_rows:
                    break
                rows.append({str(k): "" if v is None else str(v) for k, v in row.items()})
            return rows
    except Exception:
        return []


def infer_from_text(path: Path, row: dict[str, str]) -> dict[str, float | str]:
    text = (str(path).lower() + " " + " ".join(str(v).lower() for v in row.values())).replace("\\", "/")
    length = first_value(row, ["length_nm", "L_nm", "L", "pillar_L_nm"])
    width = first_value(row, ["width_nm", "W_nm", "W", "pillar_W_nm"])
    height = first_value(row, ["height_nm", "H_nm", "H"])
    material = first_value(row, ["material", "index_label", "n_label", "metasurface_index"])
    p_x = first_value(row, ["p_x_nm", "px_nm", "period_x_nm", "period_nm", "pitch_nm"])
    p_y = first_value(row, ["p_y_nm", "py_nm", "period_y_nm"])
    lam = first_value(row, ["lambda_nm", "wavelength_nm"])

    patterns = {
        "length_nm": r"l(\d+(?:p\d+)?)",
        "width_nm": r"w(\d+(?:p\d+)?)",
        "height_nm": r"h(\d+(?:p\d+)?)",
    }
    inferred: dict[str, float | str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            inferred[key] = float(match.group(1).replace("p", "."))
    if "p348" in text:
        inferred["p_x_nm"] = 348.0
        inferred["p_y_nm"] = 348.0
    if "p518" in text:
        inferred["p_x_nm"] = 518.0
        inferred["p_y_nm"] = 518.0
    if "p432" in text or "blue10k6" in text:
        inferred.setdefault("p_x_nm", BASELINE_PX_NM)
        inferred.setdefault("p_y_nm", BASELINE_PY_NM)
    if "450" in text or "blue" in text:
        inferred.setdefault("lambda_nm", BASELINE_WAVELENGTH_NM)
    if "633" in text or "red" in text:
        inferred.setdefault("lambda_nm", 633.0)
    if "n260" in text:
        inferred["material"] = "n260"
    elif "tio2" in text:
        inferred["material"] = "TiO2"
    elif material:
        inferred["material"] = material
    else:
        inferred["material"] = "unknown"
    if length:
        inferred["length_nm"] = as_float(length)
    if width:
        inferred["width_nm"] = as_float(width)
    if height:
        inferred["height_nm"] = as_float(height)
    if p_x:
        inferred["p_x_nm"] = as_float(p_x)
    if p_y:
        inferred["p_y_nm"] = as_float(p_y)
    if lam:
        inferred["lambda_nm"] = as_float(lam)
    return inferred


def compute_metrics(row: dict[str, str]) -> dict[str, float]:
    tx_amp = as_float(first_value(row, ["tx_amp", "t_x_amp", "amp_x", "Ex_amp", "x_amp", "abs_tx"]))
    ty_amp = as_float(first_value(row, ["ty_amp", "t_y_amp", "amp_y", "Ey_amp", "y_amp", "abs_ty"]))
    tx_phase = as_float(first_value(row, ["tx_phase_deg", "t_x_phase_deg", "phase_x_deg", "x_phase_deg", "arg_tx_deg"]))
    ty_phase = as_float(first_value(row, ["ty_phase_deg", "t_y_phase_deg", "phase_y_deg", "y_phase_deg", "arg_ty_deg"]))

    phase_delay = as_float(first_value(row, ["phase_delay_deg", "retardance_deg", "delta_phase_deg", "ty_minus_tx_deg"]))
    tx_phase_rad = as_float(first_value(row, ["phase_x_rad", "tx_phase_rad", "t_x_phase_rad"]))
    ty_phase_rad = as_float(first_value(row, ["phase_y_rad", "ty_phase_rad", "t_y_phase_rad"]))
    phase_delay_rad = as_float(first_value(row, ["phase_delay_rad", "retardance_rad", "delta_phase_rad"]))
    if math.isnan(tx_phase) and not math.isnan(tx_phase_rad):
        tx_phase = math.degrees(tx_phase_rad)
    if math.isnan(ty_phase) and not math.isnan(ty_phase_rad):
        ty_phase = math.degrees(ty_phase_rad)
    if math.isnan(phase_delay) and not math.isnan(phase_delay_rad):
        phase_delay = math.degrees(phase_delay_rad)
    if math.isnan(ty_phase) or math.isnan(tx_phase):
        if not math.isnan(phase_delay):
            tx_phase = 0.0
            ty_phase = phase_delay

    if math.isnan(tx_amp):
        tx_power = as_float(first_value(row, ["T_x", "Tx", "x_power", "transmission_x"]))
        tx_amp = math.sqrt(max(tx_power, 0.0)) if not math.isnan(tx_power) else math.nan
    if math.isnan(ty_amp):
        ty_power = as_float(first_value(row, ["T_y", "Ty", "y_power", "transmission_y"]))
        ty_amp = math.sqrt(max(ty_power, 0.0)) if not math.isnan(ty_power) else math.nan

    retardance_to_hwp = math.nan
    amp_balance = math.nan
    t_mean = math.nan
    common_phase = math.nan
    hwp_score = math.nan

    if not math.isnan(tx_phase) and not math.isnan(ty_phase):
        retardance_to_hwp = abs(wrap180((ty_phase - tx_phase) - 180.0))
    if not math.isnan(tx_amp) and not math.isnan(ty_amp) and max(tx_amp, ty_amp) > 0:
        amp_balance = min(tx_amp, ty_amp) / max(tx_amp, ty_amp)
        t_mean = (tx_amp * tx_amp + ty_amp * ty_amp) / 2.0
    if all(not math.isnan(v) for v in [tx_amp, ty_amp, tx_phase, ty_phase]):
        tx = tx_amp * cmath.exp(1j * math.radians(tx_phase))
        ty = ty_amp * cmath.exp(1j * math.radians(ty_phase))
        common = (tx + ty) / 2.0
        if abs(common) > 1e-12:
            common_phase = wrap360(math.degrees(cmath.phase(common)))
    if not math.isnan(retardance_to_hwp) and not math.isnan(amp_balance) and not math.isnan(t_mean):
        hwp_score = 100.0 * (
            0.45 * max(0.0, 1.0 - retardance_to_hwp / 45.0)
            + 0.35 * amp_balance
            + 0.20 * min(t_mean / 0.5, 1.0)
        )
    return {
        "tx_amp": tx_amp,
        "ty_amp": ty_amp,
        "tx_phase_deg": tx_phase,
        "ty_phase_deg": ty_phase,
        "retardance_to_hwp_deg": retardance_to_hwp,
        "amp_balance": amp_balance,
        "T_mean": t_mean,
        "common_phase_deg": common_phase,
        "hwp_like_score": hwp_score,
    }


def classify(meta: dict[str, float | str], metrics: dict[str, float], path: Path) -> tuple[str, str]:
    missing = []
    for key in ["tx_amp", "ty_amp", "tx_phase_deg", "ty_phase_deg"]:
        if math.isnan(metrics[key]):
            missing.append(key)
    if missing:
        return "incompatible", "missing key optical fields: " + ",".join(missing)

    lam = float(meta.get("lambda_nm", math.nan))
    p_x = float(meta.get("p_x_nm", math.nan))
    p_y = float(meta.get("p_y_nm", math.nan))
    height = float(meta.get("height_nm", math.nan))
    material = str(meta.get("material", "unknown")).lower()
    reasons = []
    if math.isnan(lam) or abs(lam - BASELINE_WAVELENGTH_NM) > 1e-6:
        reasons.append("wavelength not frozen 450 nm")
    if math.isnan(p_x) or abs(p_x - BASELINE_PX_NM) > 0.2:
        reasons.append("p_x not frozen 431.907786 nm")
    if math.isnan(p_y) or abs(p_y - BASELINE_PY_NM) > 0.2:
        reasons.append("p_y not frozen 432 nm")
    if math.isnan(height) or height not in BASELINE_HEIGHTS_NM:
        reasons.append("height not in Stage11 J1 baseline set")
    if not any(token in material for token in BASELINE_MATERIAL_TOKENS):
        reasons.append("material not confirmed compatible")

    convention_clear = any(token in str(path).lower() for token in ["phase_delay", "jones_role", "jones", "xy_sweep"])
    if not convention_clear:
        reasons.append("extraction convention unclear")

    if reasons:
        return "reusable_seed_only", "; ".join(reasons)
    return "reusable_final", "matches 450 nm px/py height material and has parseable x/y optical fields"


def candidate_rows() -> list[dict[str, str]]:
    paths = sorted(
        list((REPO_ROOT / "outputs").glob("**/*.csv"))
        + list((REPO_ROOT / "configs").glob("**/*.csv"))
    )
    rows: list[dict[str, str]] = []
    for path in paths:
        low = str(path).lower()
        if "blue10k6_cp_apcd_selection" in low:
            continue
        if "blue10k6_lp_apcd_j2_hwp_scan" in low:
            continue
        if not any(token in low for token in ["phase_delay", "jones", "xy_sweep", "hwp", "stage10b1", "stage10b2", "nanofin"]):
            continue
        for idx, source_row in enumerate(read_csv(path, max_rows=120)):
            meta = infer_from_text(path, source_row)
            metrics = compute_metrics(source_row)
            status, reason = classify(meta, metrics, path)
            source_id = first_value(source_row, ["candidate_id", "case_id", "name", "id"]) or f"{path.stem}_{idx+1}"
            geometry = {
                "source_id": source_id,
                "length_nm": meta.get("length_nm", ""),
                "width_nm": meta.get("width_nm", ""),
                "height_nm": meta.get("height_nm", ""),
            }
            row = {
                "candidate_id": f"J2_{len(rows)+1:05d}",
                "source": str(path.relative_to(REPO_ROOT)),
                "geometry_params": json.dumps(geometry, ensure_ascii=False, sort_keys=True),
                "material": str(meta.get("material", "unknown")),
                "lambda_nm": fmt(meta.get("lambda_nm", math.nan)),
                "p_x_nm": fmt(meta.get("p_x_nm", math.nan)),
                "p_y_nm": fmt(meta.get("p_y_nm", math.nan)),
                "height_nm": fmt(meta.get("height_nm", math.nan)),
                "tx_amp": fmt(metrics["tx_amp"]),
                "ty_amp": fmt(metrics["ty_amp"]),
                "tx_phase_deg": fmt(metrics["tx_phase_deg"]),
                "ty_phase_deg": fmt(metrics["ty_phase_deg"]),
                "retardance_to_hwp_deg": fmt(metrics["retardance_to_hwp_deg"]),
                "amp_balance": fmt(metrics["amp_balance"]),
                "T_mean": fmt(metrics["T_mean"]),
                "common_phase_deg": fmt(metrics["common_phase_deg"]),
                "hwp_like_score": fmt(metrics["hwp_like_score"]),
                "source_result_csv": str(path.relative_to(REPO_ROOT)),
                "reusable_status": status,
                "reason": reason,
            }
            rows.append(row)
            if len(rows) >= 500:
                return rows
    if not rows:
        rows.append(
            {
                "candidate_id": "J2_NONE_00001",
                "source": "outputs/configs search",
                "geometry_params": "{}",
                "material": "unknown",
                "lambda_nm": "",
                "p_x_nm": "",
                "p_y_nm": "",
                "height_nm": "",
                "tx_amp": "",
                "ty_amp": "",
                "tx_phase_deg": "",
                "ty_phase_deg": "",
                "retardance_to_hwp_deg": "",
                "amp_balance": "",
                "T_mean": "",
                "common_phase_deg": "",
                "hwp_like_score": "",
                "source_result_csv": "",
                "reusable_status": "incompatible",
                "reason": "no parseable HWP-like source CSV found; do not fabricate J2 results",
            }
        )
    return rows


def stage11_1b_rows() -> list[dict[str, str]]:
    if not STAGE11_1B_RESULT.exists():
        return []
    rows: list[dict[str, str]] = []
    for source_row in read_csv(STAGE11_1B_RESULT, max_rows=1000):
        if source_row.get("extraction_status") != "ok":
            status = "incompatible"
            reason = "Stage11-1B J2 row extraction_status is not ok"
        else:
            status = "reusable_final"
            reason = "real Stage11-1B J2 FDTD at frozen 450 nm px/py, n=2.6 material convention, x/y extraction"
        geometry = {
            "source_id": source_row.get("candidate_id", ""),
            "shape_family": source_row.get("shape_family", ""),
            "length_nm": source_row.get("length_nm", ""),
            "width_nm": source_row.get("width_nm", ""),
            "height_nm": source_row.get("height_nm", ""),
            "rotation_deg": source_row.get("rotation_deg", ""),
        }
        rows.append(
            {
                "candidate_id": source_row.get("candidate_id", f"J2_STAGE11_1B_{len(rows)+1:05d}"),
                "source": str(STAGE11_1B_RESULT.relative_to(REPO_ROOT)),
                "geometry_params": json.dumps(geometry, ensure_ascii=False, sort_keys=True),
                "material": source_row.get("material", "dielectric_n2p6_blue_baseline"),
                "lambda_nm": source_row.get("lambda_nm", ""),
                "p_x_nm": source_row.get("p_x_nm", ""),
                "p_y_nm": source_row.get("p_y_nm", ""),
                "height_nm": source_row.get("height_nm", ""),
                "tx_amp": source_row.get("tx_amp", ""),
                "ty_amp": source_row.get("ty_amp", ""),
                "tx_phase_deg": source_row.get("tx_phase_deg", ""),
                "ty_phase_deg": source_row.get("ty_phase_deg", ""),
                "retardance_to_hwp_deg": source_row.get("retardance_abs_to_180_deg", ""),
                "amp_balance": source_row.get("amp_balance", ""),
                "T_mean": source_row.get("T_mean", ""),
                "common_phase_deg": source_row.get("common_phase_deg", ""),
                "hwp_like_score": source_row.get("hwp_like_score", ""),
                "source_result_csv": str(STAGE11_1B_RESULT.relative_to(REPO_ROOT)),
                "reusable_status": status,
                "reason": reason,
            }
        )
    return rows


def fmt(value: object) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "" if value is None else str(value)
    if math.isnan(x):
        return ""
    return f"{x:.6f}"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage11-1b", action="store_true", help="include real Stage11-1B J2 pilot rows and write stage11_1b inventory")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    rows = candidate_rows()
    output = OUT_DIR / "j2_reuse_inventory.csv"
    if args.stage11_1b:
        rows = stage11_1b_rows() + rows
        output = STAGE11_1B_INVENTORY
    if args.output:
        output = Path(args.output)
    write_csv(output, rows)
    counts = {"reusable_final": 0, "reusable_seed_only": 0, "incompatible": 0}
    for row in rows:
        counts[row["reusable_status"]] = counts.get(row["reusable_status"], 0) + 1
    print("j2_inventory_count=" + str(len(rows)))
    print("j2_inventory_counts=" + json.dumps(counts, sort_keys=True))
    print(f"output={output}")
    print("mode=inventory_only_no_lumerical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
