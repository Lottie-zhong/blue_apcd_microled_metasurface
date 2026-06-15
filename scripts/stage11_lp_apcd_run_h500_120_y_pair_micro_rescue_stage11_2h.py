from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_2A = REPO_ROOT / "scripts/stage11_lp_apcd_run_h500_dimer_fdtd_stage11_2a.py"
OUT_DIR = REPO_ROOT / "outputs/stage11_2h_h500_120_y_pair_micro_rescue"
PLAN = OUT_DIR / "h500_120_y_pair_micro_rescue_plan_stage11_2h.csv"
RESULT = OUT_DIR / "h500_120_y_pair_micro_rescue_fdtd_results_stage11_2h.csv"
SUMMARY = OUT_DIR / "h500_120_y_pair_micro_rescue_fdtd_summary_stage11_2h.md"
FDTD_DIR = OUT_DIR / "fdtd_h500_120_y_pair_micro_rescue"


def load_runner():
    spec = importlib.util.spec_from_file_location("stage11_2a_runner", RUNNER_2A)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def map_row(row: dict[str, str]) -> dict[str, str]:
    return {
        **row,
        "bin_deg": "120",
        "static_output_phase_deg": "120",
        "static_predicted_ratio": "",
        "static_phase_error_deg": "",
        "static_target_x_power": "",
        "static_leak_y_power": "",
    }


def write_summary(rows: list[dict[str, str]], dry: bool = False) -> None:
    ok = [row for row in rows if row.get("fdtd_status") == "ok"]
    failed = [row for row in rows if row.get("fdtd_status") == "failed"]
    lines = [
        "# Stage11-2H H500 120 y-pair micro-rescue FDTD summary",
        "",
        f"mode = {'dry_run_no_lumerical' if dry else 'real_h500_120_y_pair_micro_rescue_fdtd'}",
        f"result_count = {len(rows)}",
        f"success = {len(ok)}",
        f"failed = {len(failed)}",
        "skipped = 0",
        "",
        "Only H500 dimer x/y normal-incidence FDTD. No K=6, no metagrating, no H600/H700.",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default=str(PLAN))
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    mod = load_runner()
    mod.FDTD_DIR = FDTD_DIR
    mod.RESULT_CSV = RESULT
    mod.SUMMARY_MD = SUMMARY
    rows = [map_row(row) for row in mod.read_csv(Path(args.plan)) if row.get("geometry_legal") == "true"][: args.max_cases]
    print(f"selected_legal_h500_120_micro_rescue_count={len(rows)}")
    for row in rows[: min(12, len(rows))]:
        print(
            f"case={row['dimer_case_id']} target=120 placement={row['placement_type']} "
            f"swap={row.get('swap_order', '')} gap={row.get('gap_nm', '')} "
            f"offset={row.get('local_offset_nm', '')} x/y"
        )
    if args.dry_run:
        dry_rows = [{**{key: row.get(key, "") for key in mod.RESULT_FIELDS}, "fdtd_status": "dry_run"} for row in rows]
        write_summary(dry_rows, True)
        return 0

    existing = mod.read_csv(RESULT) if RESULT.exists() else []
    done = {row.get("dimer_case_id") for row in existing if row.get("fdtd_status") == "ok"}
    results = list(existing)
    runtime = mod.load_runtime_config(args.runtime)
    lumapi = mod.import_lumapi(runtime)
    for row in rows:
        cid = row["dimer_case_id"]
        if cid in done:
            print("skip_existing=" + cid)
            continue
        print(f"running={cid} x")
        x_result = mod.run_one(lumapi, runtime, row, "x")
        print(f"running={cid} y")
        y_result = mod.run_one(lumapi, runtime, row, "y")
        combined = mod.combine(row, x_result, y_result)
        results.append(combined)
        mod.write_csv(RESULT, results, mod.RESULT_FIELDS)
        write_summary(results, False)
        print(f"done={cid} status={combined['fdtd_status']}")

    print(f"result_csv={RESULT}")
    print(f"success={sum(1 for row in results if row['fdtd_status'] == 'ok')}")
    print(f"failed={sum(1 for row in results if row['fdtd_status'] == 'failed')}")
    print("skipped=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
