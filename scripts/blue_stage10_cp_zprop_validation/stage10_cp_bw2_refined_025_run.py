from __future__ import annotations
import csv, json, math, sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
ROOT0 = HERE.parents[2]
sys.path.insert(0, str(ROOT0 / "src"))
sys.path.insert(0, str(HERE.parent))
import stage10_cp_bw2_core15_run as core

ROOT = core.ROOT
OUT = core.OUT
DENSE_SAVE = OUT / "_saved_fsp_dense_lite"
SAVE = OUT / "_saved_fsp_refined_025"
LOG = OUT / "stage10_cp_bw2_refined_025_runner.log"
WLS = [447.0 + 0.25 * i for i in range(29)]
DENSE_WLS = {447.0, 447.5, 448.0, 448.5, 449.0, 449.5, 450.0, 450.5, 451.0, 451.5, 452.0, 452.5, 453.0, 453.5, 454.0}
CANDIDATES = [
    "BW2_J1J2_D194_T90_PSI97_H525",
    "BW2_J1J2_D194_T90_PSI99_H525",
    "BW2_J1J2_D196_T90_PSI98_H525",
]
ROLES = {
    "BW2_J1J2_D194_T90_PSI97_H525": "B4INT baseline reference",
    "BW2_J1J2_D194_T90_PSI99_H525": "best all-band robust / simple psi +2 shift",
    "BW2_J1J2_D196_T90_PSI98_H525": "best red-shifted / RCLED-weighted candidate",
}
core.CORE15 = CANDIDATES
core.WLS = WLS
core.SAVE = SAVE
core.LOG = LOG


def token(wl: float) -> str:
    return str(wl).replace(".", "p") if abs(wl - round(wl)) > 1e-9 else str(int(wl))


def dense_path(candidate_id: str, wl: float, lin: str) -> Path:
    return DENSE_SAVE / candidate_id / f"{candidate_id}_{token(wl)}NM_{lin.upper()}IN.fsp"


def refined_path(candidate_id: str, wl: float, lin: str) -> Path:
    return SAVE / candidate_id / f"{candidate_id}_{token(wl)}NM_{lin.upper()}IN.fsp"


def fsp_path(candidate_id: str, wl: float, lin: str) -> Path:
    dp = dense_path(candidate_id, wl, lin)
    if wl in DENSE_WLS and core.fsp_complete(dp):
        return dp
    return refined_path(candidate_id, wl, lin)

core.fsp_path = fsp_path


def fnum(x: float) -> str:
    return f"{x:.12g}"


def weight(wl: float, center: float, fwhm: float) -> float:
    return math.exp(-4.0 * math.log(2.0) * ((wl - center) / fwhm) ** 2)


def weighted(vals: dict[float, dict[str, Any]], center: float, fwhm: float, num_key: str, den_key: str | None = None) -> float:
    num = den = 0.0
    for wl, row in vals.items():
        w = weight(wl, center, fwhm)
        num += w * float(row[num_key])
        den += w * (float(row[den_key]) if den_key else 1.0)
    return num / den if den else float("inf")


def weighted_ratio(vals: dict[float, dict[str, Any]], center: float, fwhm: float) -> float:
    return weighted(vals, center, fwhm, "target_cp_power", "same_spin_leakage_power")


def hidden_notch(vals: dict[float, dict[str, Any]], expected_strict: bool) -> bool:
    ws = sorted(vals)
    for i, wl in enumerate(ws):
        ratio = float(vals[wl]["conversion_to_leakage_ratio"])
        lfrac = float(vals[wl]["L_fraction_under_R_in"])
        if expected_strict and ratio < 15:
            return True
        if lfrac < 0.90:
            return True
        if 0 < i < len(ws) - 1:
            left = float(vals[ws[i - 1]]["conversion_to_leakage_ratio"])
            right = float(vals[ws[i + 1]]["conversion_to_leakage_ratio"])
            if ratio < 0.5 * left and ratio < 0.5 * right:
                return True
    return False


def build_and_run(lumapi: Any, runtime: Any, cid: str, params: dict[str, float], wl: float, lin: str, sim_fs: float, mesh: int, show_gui: bool) -> dict[str, Any]:
    dp = dense_path(cid, wl, lin)
    if wl in DENSE_WLS and core.fsp_complete(dp):
        return {"candidate_id": cid, "wavelength_nm": wl, "linear_input": lin, "fdtd_status": "reused_dense_lite", "result_fsp": str(dp), "runtime_s": 0.0}
    return core.build_and_run(lumapi, runtime, cid, params, wl, lin, sim_fs, mesh, show_gui)


def extract_pair(lumapi: Any, runtime: Any, cid: str, wl: float, show_gui: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    metric, dbg = core.extract_pair(lumapi, runtime, cid, wl, show_gui)
    metric["candidate_role"] = ROLES[cid]
    metric["reused_from_dense_lite"] = str(wl in DENSE_WLS and all(core.fsp_complete(dense_path(cid, wl, lin)) for lin in ("x", "y"))).lower()
    return metric, dbg


def rank_refined(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        if r.get("extraction_ok") == "true":
            by.setdefault(r["candidate_id"], []).append(r)
    base = {float(r["wavelength_nm"]): r for r in by.get(CANDIDATES[0], [])}
    rows = []
    for cid, rs in by.items():
        vals = {float(r["wavelength_nm"]): r for r in rs}
        ratios = [float(r["conversion_to_leakage_ratio"]) for r in rs]
        lfracs = [float(r["L_fraction_under_R_in"]) for r in rs]
        red = [float(vals[w]["conversion_to_leakage_ratio"]) for w in vals if 450.0 <= w <= 454.0]
        mid = [float(vals[w]["conversion_to_leakage_ratio"]) for w in vals if 448.0 <= w <= 454.0]
        red_l = [float(vals[w]["L_fraction_under_R_in"]) for w in vals if 450.0 <= w <= 454.0]
        no_flip = all(float(r["L_fraction_under_R_in"]) >= 0.5 for r in rs)
        power_ratios = []
        total_ratios = []
        for r in rs:
            wl = float(r["wavelength_nm"])
            b = base.get(wl)
            if b and float(b["target_cp_power"]) > 0:
                power_ratios.append(float(r["target_cp_power"]) / float(b["target_cp_power"]))
            if b and float(b["total_power"]) > 0:
                total_ratios.append(float(r["total_power"]) / float(b["total_power"]))
        target_collapse = (min(power_ratios) < 0.6) if power_ratios else False
        total_collapse = (min(total_ratios) < 0.6) if total_ratios else False
        notch = hidden_notch(vals, expected_strict=(cid != CANDIDATES[0]))
        if not no_flip or min(ratios) < 8 or notch or target_collapse or total_collapse:
            klass = "reject"
        elif min(ratios) >= 20 and min(lfracs) >= 0.95:
            klass = "refined_strict_pass"
        elif min(red) >= 20 and min(mid) >= 10 and min(lfracs) >= 0.90:
            klass = "refined_useful_pass"
        else:
            klass = "borderline"
        row = {
            "candidate_id": cid,
            "candidate_role": ROLES[cid],
            "min_ratio_447_454": fnum(min(ratios)),
            "min_ratio_448_454": fnum(min(mid)),
            "min_ratio_450_454": fnum(min(red)),
            "min_L_fraction_447_454": fnum(min(lfracs)),
            "min_L_fraction_450_454": fnum(min(red_l)),
            "no_cp_flip_all": str(no_flip).lower(),
            "hidden_notch_flag": str(notch).lower(),
            "target_power_collapse_flag": str(target_collapse or total_collapse).lower(),
            "dense_refined_class": klass,
            "rank_reason": klass,
        }
        for center in [450.0, 452.0, 452.5, 453.0]:
            for fwhm in ([2.0, 3.0, 5.0, 6.0] if center == 453.0 else [2.0, 3.0, 5.0]):
                row[f"weighted_ratio_center{token(center).lower()}_FWHM{int(fwhm)}"] = fnum(weighted_ratio(vals, center, fwhm))
        row["weighted_L_fraction_center453_FWHM3"] = fnum(weighted(vals, 453.0, 3.0, "L_fraction_under_R_in"))
        row["weighted_target_power_center453_FWHM3"] = fnum(weighted(vals, 453.0, 3.0, "target_cp_power"))
        for wl in [447.0,447.25,447.5,447.75,448.0,448.25,448.5,448.75,450.0,452.0,452.5,453.0,453.5,454.0]:
            row[f"ratio_{token(wl).lower()}"] = vals[wl]["conversion_to_leakage_ratio"]
        row["target_power_448"] = vals[448.0]["target_cp_power"]
        row["target_power_452p5"] = vals[452.5]["target_cp_power"]
        row["target_power_453"] = vals[453.0]["target_cp_power"]
        rows.append(row)
    rows.sort(key=lambda r: (r["rank_reason"] == "reject", -float(r["weighted_ratio_center453_FWHM3"]), -float(r["min_ratio_447_454"])))
    return rows


def write_report(ranking: list[dict[str, Any]], runs: list[dict[str, Any]], results: list[dict[str, Any]]) -> None:
    completed = sum(r.get("fdtd_status") in {"ok", "reused", "reused_dense_lite"} for r in runs)
    reused = sum(r.get("fdtd_status") == "reused_dense_lite" for r in runs)
    newly = sum(r.get("fdtd_status") in {"ok", "reused"} for r in runs) - sum(r.get("fdtd_status") == "reused" for r in runs)
    failed = len(runs) - completed
    top_min = max(ranking, key=lambda r: float(r["min_ratio_447_454"]))
    top_453 = max(ranking, key=lambda r: float(r["weighted_ratio_center453_FWHM3"]))
    top_4525 = max(ranking, key=lambda r: float(r["weighted_ratio_center452p5_FWHM3"]))
    psi99 = next(r for r in ranking if r["candidate_id"] == "BW2_J1J2_D194_T90_PSI99_H525")
    d196 = next(r for r in ranking if r["candidate_id"] == "BW2_J1J2_D196_T90_PSI98_H525")
    base = {float(r["wavelength_nm"]): r for r in results if r["candidate_id"] == CANDIDATES[0]}
    hidden = [r["candidate_id"] for r in ranking if r["candidate_id"] != CANDIDATES[0] and r["hidden_notch_flag"] == "true"]
    rec = sorted([r for r in ranking if r["rank_reason"] != "reject"], key=lambda r: (-float(r["weighted_ratio_center453_FWHM3"]), -float(r["min_ratio_447_454"])))
    lines = [
        "# Stage10-CP-BW2 refined 0.25 nm spectral validation\n\n",
        "- Scope: Stage10 CP 450 nm metasurface-only periodic plane-wave. No DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13.\n",
        "- Target: `R_in -> L_out`; leakage: `R_in -> R_out`; negative `DoCP_RminusL` means desired L-output dominance.\n\n",
        f"- Completed/reused FDTD cases: {completed}/{len(runs)}\n",
        f"- Reused dense-lite cases: {reused}\n",
        f"- Newly run or locally reused refined cases: {newly}\n",
        f"- Failed/missing cases: {failed}\n",
        f"- Extracted wavelength rows: {len(results)}/87\n\n",
        "## Required answers\n\n",
        f"- Top candidate by min_ratio_447_454: `{top_min['candidate_id']}` ({top_min['min_ratio_447_454']}).\n",
        f"- Top candidate by weighted_ratio_center453_FWHM3: `{top_453['candidate_id']}` ({top_453['weighted_ratio_center453_FWHM3']}).\n",
        f"- Top candidate by weighted_ratio_center452p5_FWHM3: `{top_4525['candidate_id']}` ({top_4525['weighted_ratio_center452p5_FWHM3']}).\n",
        f"- PSI99 remains best all-band/simple-shift candidate: {psi99['rank_reason']} min_ratio={psi99['min_ratio_447_454']}.\n",
        f"- D196_PSI98 remains best red/RCLED-weighted candidate: {d196['rank_reason']} weighted453_FWHM3={d196['weighted_ratio_center453_FWHM3']}.\n",
        f"- Baseline notch reproduction: ratio_447p75={base[447.75]['conversion_to_leakage_ratio']}, ratio_448={base[448.0]['conversion_to_leakage_ratio']}.\n",
        f"- Hidden notch in PSI99/D196_PSI98: {hidden if hidden else 'none'}.\n",
        "- Recommended candidate(s) for RCLED spectral convolution: " + ", ".join(f"`{r['candidate_id']}`" for r in rec[:2]) + ".\n\n",
        "## Ranking\n\n",
        "| candidate_id | class | min_ratio_447_454 | weighted453_FWHM3 | weighted452p5_FWHM3 | hidden_notch | collapse |\n",
        "|---|---|---:|---:|---:|---|---|\n",
    ]
    for r in ranking:
        lines.append(f"| {r['candidate_id']} | {r['rank_reason']} | {r['min_ratio_447_454']} | {r['weighted_ratio_center453_FWHM3']} | {r['weighted_ratio_center452p5_FWHM3']} | {r['hidden_notch_flag']} | {r['target_power_collapse_flag']} |\n")
    (OUT / "stage10_cp_bw2_refined_025_report.md").write_text("".join(lines), encoding="utf-8")


def maybe_plot(results: list[dict[str, Any]], ranking: list[dict[str, Any]]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    by: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        by.setdefault(r["candidate_id"], []).append(r)
    plots = [
        ("conversion_to_leakage_ratio", "ratio", "stage10_cp_bw2_refined_025_ratio_vs_wavelength.png"),
        ("L_fraction_under_R_in", "L fraction", "stage10_cp_bw2_refined_025_L_fraction_vs_wavelength.png"),
        ("target_cp_power", "target power", "stage10_cp_bw2_refined_025_target_power_vs_wavelength.png"),
    ]
    for key, ylabel, name in plots:
        plt.figure(figsize=(8, 5))
        for cid, rows in by.items():
            rows = sorted(rows, key=lambda r: float(r["wavelength_nm"]))
            plt.plot([float(r["wavelength_nm"]) for r in rows], [float(r[key]) for r in rows], marker=".", label=cid.replace("BW2_J1J2_", ""))
        plt.xlabel("wavelength (nm)")
        plt.ylabel(ylabel)
        plt.legend(fontsize=7)
        plt.tight_layout()
        plt.savefig(OUT / name, dpi=160)
        plt.close()
    plt.figure(figsize=(8, 4.5))
    xs = range(len(ranking))
    plt.bar(xs, [float(r["weighted_ratio_center453_FWHM3"]) for r in ranking], label="453 FWHM3")
    plt.bar(xs, [float(r["weighted_ratio_center452p5_FWHM3"]) for r in ranking], alpha=0.55, label="452.5 FWHM3")
    plt.xticks(list(xs), [r["candidate_id"].replace("BW2_J1J2_", "") for r in ranking], rotation=20, ha="right", fontsize=7)
    plt.ylabel("weighted ratio")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "stage10_cp_bw2_refined_025_weighted_ratio_summary.png", dpi=160)
    plt.close()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime", default="configs/runtime.yaml")
    ap.add_argument("--mesh-accuracy", type=int, default=3)
    ap.add_argument("--simulation-time-fs", type=float, default=core.b4.SIM_TIME_FS)
    ap.add_argument("--show-gui", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    SAVE.mkdir(parents=True, exist_ok=True)
    runtime = core.load_runtime_config(args.runtime)
    lumapi = core.import_lumapi(runtime)
    manifest = core.read_manifest()
    runs: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    debug: dict[str, Any] = {"scope_guard": "Stage10 CP 450 nm explicit override; refined 0.25 nm metasurface-only periodic plane-wave"}
    total = len(CANDIDATES) * len(WLS) * 2
    n = 0
    for cid in CANDIDATES:
        params = {"d_nm": float(manifest[cid]["d_nm"]), "theta_deg": float(manifest[cid]["theta_deg"]), "psi_deg": float(manifest[cid]["psi_deg"])}
        for wl in WLS:
            for lin in ("x", "y"):
                n += 1
                core.log(f"REFINED_025 RUN {n}/{total} {cid} {wl:g}nm {lin}")
                row = build_and_run(lumapi, runtime, cid, params, wl, lin, args.simulation_time_fs, args.mesh_accuracy, args.show_gui)
                runs.append(row)
                core.write_csv(OUT / "stage10_cp_bw2_refined_025_run_table.csv", runs)
            metric, dbg = extract_pair(lumapi, runtime, cid, wl, args.show_gui)
            results.append(metric)
            debug[f"{cid}_{wl:g}"] = dbg
            core.write_csv(OUT / "stage10_cp_bw2_refined_025_results.csv", results)
    ranking = rank_refined(results)
    core.write_csv(OUT / "stage10_cp_bw2_refined_025_candidate_ranking.csv", ranking)
    summary = {
        "completed_reused_case_count": sum(r.get("fdtd_status") in {"ok", "reused", "reused_dense_lite"} for r in runs),
        "reused_dense_lite_case_count": sum(r.get("fdtd_status") == "reused_dense_lite" for r in runs),
        "failed_missing_case_count": sum(r.get("fdtd_status") not in {"ok", "reused", "reused_dense_lite"} for r in runs),
        "extracted_wavelength_rows": len(results),
        "candidate_count": len(CANDIDATES),
        "fdtd_case_count": total,
        "top_by_min_ratio_447_454": max(ranking, key=lambda r: float(r["min_ratio_447_454"])),
        "top_by_weighted_ratio_center453_FWHM3": max(ranking, key=lambda r: float(r["weighted_ratio_center453_FWHM3"])),
        "top_by_weighted_ratio_center452p5_FWHM3": max(ranking, key=lambda r: float(r["weighted_ratio_center452p5_FWHM3"])),
    }
    (OUT / "stage10_cp_bw2_refined_025_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "stage10_cp_bw2_refined_025_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    write_report(ranking, runs, results)
    maybe_plot(results, ranking)
    core.log(f"REFINED_025 DONE completed={summary['completed_reused_case_count']} reused_dense={summary['reused_dense_lite_case_count']} failed={summary['failed_missing_case_count']} rows={len(results)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
