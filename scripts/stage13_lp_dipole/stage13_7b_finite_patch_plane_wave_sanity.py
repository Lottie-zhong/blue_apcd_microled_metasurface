from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi
from metasurface.stage13_4_center_dipole import build_patch_inventory, build_setup, load_approved_plan, resolved_setup
from metasurface.stage13_7b_finite_patch_plane_wave_sanity import (
    CASE_ID, DECISION_FIELDS, ORDER_FIELDS, OUTPUT_DIR_NAME, PEAK_FIELDS, PLANE_SOURCE,
    add_plane_wave, build_notes, build_order_rows, build_peak_rows, build_summary, extract_fields,
    run_with_heartbeat, sanity_decision, save_map, source_preflight, write_csv,
)

CONFIG = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_config.json"
CASES = REPO_ROOT / "outputs/stage13_3_lp_first_dipole_manual_config/stage13_3_first_no_dbr_minimal_cases.csv"
LAYOUT = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv"


def parse_args():
    parser=argparse.ArgumentParser(); parser.add_argument("--run",action="store_true"); parser.add_argument("--runtime",default=str(REPO_ROOT/"configs/runtime.yaml")); parser.add_argument("--show-gui",action="store_true"); return parser.parse_args()


def main() -> int:
    args=parse_args(); output=REPO_ROOT/"outputs"/OUTPUT_DIR_NAME; output.mkdir(parents=True,exist_ok=True); (output/"_saved_fsp").mkdir(exist_ok=True)
    plan=load_approved_plan(CONFIG,CASES,LAYOUT); inventory=build_patch_inventory(plan); setup=resolved_setup(plan,inventory)
    print(f"case_id={CASE_ID} patch={setup['patch_option_id']} {setup['Nx']}x{setup['Ny']} geometry={len(inventory)} pillars",flush=True)
    print("source_type=plane_wave injection_axis=z direction=Forward propagation=+z polarization=x-LP source_z_nm=-250",flush=True)
    print(f"monitor={setup['monitor_direction']} DBR={setup['DBR']} RCLED={setup['RCLED']} grid={setup['farfield_grid']}",flush=True)
    if not args.run: print("run_fdtd=false",flush=True); return 0
    runtime=load_runtime_config(args.runtime); lumapi=import_lumapi(runtime); setup_fsp=output/"_saved_fsp/stage13_7b_A_small_xlp_plane_wave_setup.fsp"; result_fsp=output/"_saved_fsp/stage13_7b_a_small_xlp_plane_wave_plusz.fsp"
    state={"case_id":CASE_ID,"lifecycle":[]}; fdtd=None
    try:
        fdtd=lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui); build_setup(fdtd,setup,inventory); add_plane_wave(fdtd,setup)
        errors=source_preflight(fdtd,setup); state["setup_preflight_errors"]=errors
        if errors: raise RuntimeError("plane-wave direction/source ambiguity: "+" | ".join(errors))
        fdtd.save(str(setup_fsp.resolve())); state["lifecycle"] += ["build_setup","verify_plane_wave_plusz","save_setup","close_setup"]
    except Exception as exc:
        state.update({"status":"setup_failed","error":f"{type(exc).__name__}: {exc}"}); (output/"stage13_7b_runtime_state.json").write_text(json.dumps(state,indent=2),encoding="utf-8"); print(json.dumps(state,indent=2),flush=True); return 1
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass
    fdtd=None; start=time.perf_counter()
    try:
        fdtd=lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui); fdtd.setresource("FDTD",1,"processes",str(int(setup["solver_processes"]))); fdtd.load(str(setup_fsp.resolve())); state["lifecycle"].append("load_setup")
        errors=source_preflight(fdtd,setup); state["run_preflight_errors"]=errors
        if errors: raise RuntimeError("plane-wave direction/source ambiguity after reload: "+" | ".join(errors))
        fdtd.save(str(result_fsp.resolve())); state["lifecycle"].append("save_configured_case")
        run_with_heartbeat(fdtd,CASE_ID); state["lifecycle"].append("run")
        fdtd.save(str(result_fsp.resolve())); state["lifecycle"].append("save_with_results")
        fields,debug=extract_fields(fdtd,setup); state["lifecycle"].append("extract_complex_vector"); state["extraction_debug"]=debug
        runtime_minutes=(time.perf_counter()-start)/60.0; peaks=build_peak_rows(fields["maps"],fields["xx"],fields["yy"]); orders=build_order_rows(fields["maps"],fields["xx"],fields["yy"]); decision=sanity_decision(peaks,orders)
        write_csv(output/"stage13_7b_peak_metrics.csv",peaks,PEAK_FIELDS); write_csv(output/"stage13_7b_order_cone_metrics.csv",orders,ORDER_FIELDS); write_csv(output/"stage13_7b_sanity_decision.csv",[decision],DECISION_FIELDS)
        raw_peaks={row["component"]:row for row in peaks}
        save_map(output/"stage13_7b_Ex2_map.png",f"{CASE_ID}: Ex target",fields["maps"]["Ex_target"],fields["xx"],fields["yy"],raw_peaks["Ex_target"])
        save_map(output/"stage13_7b_Ey2_map.png",f"{CASE_ID}: Ey leakage",fields["maps"]["Ey_leakage"],fields["xx"],fields["yy"],raw_peaks["Ey_leakage"])
        save_map(output/"stage13_7b_transverse_total_map.png",f"{CASE_ID}: transverse total",fields["maps"]["transverse_total"],fields["xx"],fields["yy"],raw_peaks["transverse_total"])
        state.update({"status":"ok","runtime_minutes":runtime_minutes,"decision":decision})
        (output/"stage13_7b_run_summary.md").write_text(build_summary(setup,peaks,decision,runtime_minutes),encoding="utf-8"); (output/"stage13_7b_extraction_notes.md").write_text(build_notes(setup,state),encoding="utf-8"); (output/"README.md").write_text("# Stage13-7B A_small finite-patch plane-wave sanity\n\nOne x-LP plane-wave +z case only. Complex-vector extraction; no raw arrays.\n",encoding="utf-8"); (output/"stage13_7b_runtime_state.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
        print(json.dumps(state,indent=2),flush=True); return 0
    except Exception as exc:
        state.update({"status":"failed","error":f"{type(exc).__name__}: {exc}"}); (output/"stage13_7b_runtime_state.json").write_text(json.dumps(state,indent=2),encoding="utf-8"); print(json.dumps(state,indent=2),flush=True); return 1
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass


if __name__=="__main__": raise SystemExit(main())
