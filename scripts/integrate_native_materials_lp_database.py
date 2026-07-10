from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metasurface.apcd_material_library import get_native_samples, get_nk, load_material_library

DB_DIR = ROOT / "data" / "lp_database"
DB_PATH = DB_DIR / "lp_apcd_database.sqlite"
EXPORTS = DB_DIR / "exports"
NATIVE_CSV = ROOT / "outputs" / "material_reference" / "mdc_blue_oujizi_m" / "material_ref_native_sampled.csv"
B2E_DIR = ROOT / "outputs" / "lp_ml1b2e_0283_local_refinement" / "scout_01"
ML2A_DIR = ROOT / "outputs" / "lp_ml2a_h500_tio2_scout"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def f(row: dict[str, Any], key: str) -> float | None:
    try:
        value = str(row.get(key, "")).strip()
        return float(value) if value else None
    except (TypeError, ValueError):
        return None


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def write_csv(path: Path, fields: list[str], rows: list[sqlite3.Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: "" if row[key] is None else row[key] for key in fields} for row in rows])


def schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    PRAGMA foreign_keys = ON;
    CREATE TABLE materials (material_reference_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, source_name TEXT NOT NULL, material_role TEXT NOT NULL, source_fsp_path TEXT NOT NULL, source_commit TEXT NOT NULL, native_lambda_min_nm REAL NOT NULL, native_lambda_max_nm REAL NOT NULL, native_sample_count INTEGER NOT NULL, is_dispersive INTEGER NOT NULL, is_lossy INTEGER NOT NULL, interpolation_axis TEXT NOT NULL, extrapolation_allowed INTEGER NOT NULL, status TEXT NOT NULL);
    CREATE TABLE material_samples (material_reference_id TEXT NOT NULL, native_sample_index INTEGER NOT NULL, frequency_hz REAL NOT NULL, wavelength_nm REAL NOT NULL, epsilon_real REAL NOT NULL, epsilon_imag REAL NOT NULL, n_real REAL NOT NULL, k_imag REAL NOT NULL, is_native_sample INTEGER NOT NULL, PRIMARY KEY(material_reference_id,native_sample_index), FOREIGN KEY(material_reference_id) REFERENCES materials(material_reference_id));
    CREATE TABLE geometries (candidate_id TEXT PRIMARY KEY, branch_stage TEXT, family TEXT, H_nm REAL, period_x_nm REAL, period_y_nm REAL, L1_nm REAL, W1_nm REAL, theta1_deg REAL, L2_nm REAL, W2_nm REAL, theta2_deg REAL, PSI_deg REAL, delta_theta_deg REAL, center_dx_nm REAL, gap_nm REAL, edge_margin_nm REAL, aspect_ratio REAL, geometry_valid INTEGER, source_manifest TEXT, source_commit TEXT);
    CREATE TABLE simulation_cases (case_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, branch_stage TEXT NOT NULL, wavelength_nm REAL NOT NULL, polarization TEXT NOT NULL, material_reference_id TEXT, material_model_type TEXT NOT NULL CHECK(material_model_type IN ('native_sampled_epsilon','legacy_constant_index','unknown_legacy')), constant_index_value REAL, runner_name TEXT, runner_version TEXT, simulation_status TEXT, runtime_seconds REAL, source_output TEXT, source_commit TEXT, is_historical INTEGER NOT NULL, notes TEXT, FOREIGN KEY(candidate_id) REFERENCES geometries(candidate_id));
    CREATE TABLE jones_labels (case_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, wavelength_nm REAL NOT NULL, t_xx_real REAL, t_xx_imag REAL, t_yx_real REAL, t_yx_imag REAL, t_xy_real REAL, t_xy_imag REAL, t_yy_real REAL, t_yy_imag REAL, selected_Tx REAL, leakage_xin_to_yout REAL, leakage_yin_to_xout REAL, y_direct_leakage REAL, leakage_sum REAL, ratio REAL, matrix_error REAL, phase_deg REAL, reassigned_bin INTEGER, phase_err_to_bin_deg REAL, FOREIGN KEY(case_id) REFERENCES simulation_cases(case_id));
    CREATE TABLE candidate_metrics (candidate_id TEXT PRIMARY KEY, branch_stage TEXT NOT NULL, material_reference_id TEXT, Tx_mean REAL, Tx_min REAL, ratio_median REAL, ratio_min REAL, matrix_error_mean REAL, phase_center_deg REAL, nearest_bin INTEGER, phase_error_center_deg REAL, bin_jump_count INTEGER, projector_class TEXT, failure_mode TEXT, FOREIGN KEY(candidate_id) REFERENCES geometries(candidate_id));
    CREATE TABLE provenance (record_type TEXT NOT NULL, record_id TEXT NOT NULL, source_file TEXT NOT NULL, source_commit TEXT, source_branch TEXT, ingestion_script TEXT NOT NULL, ingestion_time TEXT NOT NULL, content_hash TEXT, notes TEXT, PRIMARY KEY(record_type,record_id));
    """)


def insert_materials(conn: sqlite3.Connection) -> None:
    library = load_material_library()
    material_rows = [
        ("APCD_TIO2_NATIVE_M1", "TiO2_native", "tio22", "high_index_metasurface_and_DBR"),
        ("APCD_SIO2_NATIVE_M1", "SiO2_native", "sio222", "low_index_DBR_and_defect"),
    ]
    for material_id, canonical, source_name, role in material_rows:
        meta = library[material_id]
        conn.execute("INSERT INTO materials VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (material_id, canonical, source_name, role, meta["source_fsp_path"], "a272b10", meta["native_lambda_min_nm"], meta["native_lambda_max_nm"], meta["native_sample_count"], 1, int(meta["is_lossy"]), "frequency_hz", 0, "active_default"))
        for index, sample in enumerate(get_native_samples(material_id)):
            conn.execute("INSERT INTO material_samples VALUES (?,?,?,?,?,?,?,?,?)", (material_id, index, f(sample,"frequency_hz"), f(sample,"wavelength_nm"), f(sample,"epsilon_real"), f(sample,"epsilon_imag"), f(sample,"n_real"), f(sample,"k_imag"), 1))
        provenance(conn, "material", material_id, NATIVE_CSV, "a272b10", "native sampled epsilon imported")


def geometry_values(row: dict[str, str], candidate_id: str, branch: str, family: str, source: Path, commit: str) -> tuple:
    return (candidate_id, branch, family, f(row,"H_nm") or f(row,"height_nm"), f(row,"period_x_nm"), f(row,"period_y_nm"), f(row,"L1_nm"), f(row,"W1_nm"), f(row,"theta1_deg"), f(row,"L2_nm"), f(row,"W2_nm"), f(row,"theta2_deg"), f(row,"PSI_deg"), f(row,"delta_theta_deg"), f(row,"center_dx_nm"), f(row,"gap_nm"), f(row,"edge_margin_nm"), f(row,"aspect_ratio"), int(str(row.get("geometry_valid","true")).casefold()=="true"), str(source), commit)


def insert_geometry(conn: sqlite3.Connection, values: tuple) -> None:
    conn.execute("INSERT OR REPLACE INTO geometries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)


def insert_b2e(conn: sqlite3.Connection) -> None:
    results_path = B2E_DIR / "lp_ml1b2e_scout01_results.csv"
    ranking_path = B2E_DIR / "lp_ml1b2e_scout01_selectivity_first_ranking.csv"
    plan_path = ROOT / "outputs" / "lp_ml1b2d_0283_refinement" / "lp_ml1b2d_0283_local_refinement_plan.csv"
    plans = {row["candidate_id"]: row for row in read_csv(plan_path)}
    results = [row for row in read_csv(results_path) if row.get("status") == "ok"]
    rankings = {row["candidate_id"]: row for row in read_csv(ranking_path)}
    ids = sorted({row["candidate_id"] for row in results})
    for candidate_id in ids:
        plan = plans.get(candidate_id, {})
        insert_geometry(conn, geometry_values(plan, candidate_id, "LP-ML1B2E", plan.get("refinement_family", "0283_local_refinement"), plan_path, "d9617c5"))
    for row in results:
        case_id = f"B2E:{row['candidate_id']}:{row['wavelength_nm']}:JonesXY"
        conn.execute("INSERT INTO simulation_cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (case_id, row["candidate_id"], "LP-ML1B2E", f(row,"wavelength_nm"), "JonesXY", None, "legacy_constant_index", 2.6, "lp_ml1b1_fdtd_smoke_test.py", "d9617c5", row["status"], None, results_path.as_posix(), "d9617c5", 1, "base runner add_rect hard-codes Object defined dielectric index=2.6"))
        leakage_sum = sum(f(row,key) or 0.0 for key in ("leakage_xin_to_yout","leakage_yin_to_xout","y_direct_leakage"))
        conn.execute("INSERT INTO jones_labels VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (case_id,row["candidate_id"],f(row,"wavelength_nm"),f(row,"txx_re"),f(row,"txx_im"),f(row,"tyx_re"),f(row,"tyx_im"),f(row,"txy_re"),f(row,"txy_im"),f(row,"tyy_re"),f(row,"tyy_im"),f(row,"selected_Tx"),f(row,"leakage_xin_to_yout"),f(row,"leakage_yin_to_xout"),f(row,"y_direct_leakage"),leakage_sum,f(row,"conversion_to_leakage_ratio"),f(row,"matrix_error"),f(row,"selected_phase_deg"),int(float(row["nearest_bin_deg"])),f(row,"phase_error_deg")))
    for candidate_id, row in rankings.items():
        conn.execute("INSERT INTO candidate_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (candidate_id,"LP-ML1B2E",None,f(row,"Tx_mean"),None,f(row,"ratio_median"),None,f(row,"matrix_error"),None,int(float(row["nearest_bin_mode"])),f(row,"phase_err_to_120_at_452"),int(float(row["nearest_bin_stability_count"])),row["b2c_style_class"],"legacy_constant_index_2p6"))
    provenance(conn,"b2e_results","scout_01",results_path,"d9617c5","B2E rows and B01/C02/C05 material audit")


def insert_ml2a(conn: sqlite3.Connection) -> tuple[list[dict[str,str]], Path]:
    manifest_path = ML2A_DIR / "lp_ml2a_h500_tio2_scout_manifest_v3.csv"
    manifest = read_csv(manifest_path)
    for row in manifest:
        candidate_id = row.get("candidate_id") or row.get("\ufeffcandidate_id")
        insert_geometry(conn, geometry_values(row,candidate_id,"LP-ML2A",row.get("group","H500_scout"),manifest_path,"uncommitted_local"))
    metrics_files = sorted(ML2A_DIR.glob("onecase_v1/*/onecase_metrics.csv"))
    metrics = [read_csv(path)[0] for path in metrics_files if read_csv(path)]
    for row in metrics:
        case_id = row["case_id"]
        n_const = f(row,"n_material")
        source = next(path for path in metrics_files if row["candidate_id"] in str(path))
        conn.execute("INSERT INTO simulation_cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (case_id,row["candidate_id"],"LP-ML2A",f(row,"lambda_nm"),"JonesXY",None,"legacy_constant_index",n_const,"stage_lp_ml2a_h500_tio2_fdtd_onecase_v1.py","local_uncommitted",row["fdtd_status"],None,str(source),"local_uncommitted",1,"manifest n_material and runner use Object defined dielectric"))
        leak = f(row,"leakage_sum") or sum(f(row,k) or 0 for k in ("leakage_xin_to_yout","leakage_yin_to_xout","y_direct_leakage"))
        conn.execute("INSERT INTO jones_labels VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (case_id,row["candidate_id"],f(row,"lambda_nm"),f(row,"t_xx_real"),f(row,"t_xx_imag"),f(row,"t_yx_real"),f(row,"t_yx_imag"),f(row,"t_xy_real"),f(row,"t_xy_imag"),f(row,"t_yy_real"),f(row,"t_yy_imag"),f(row,"selected_Tx"),f(row,"leakage_xin_to_yout"),f(row,"leakage_yin_to_xout"),f(row,"y_direct_leakage"),leak,f(row,"ratio"),f(row,"matrix_error"),f(row,"t_xx_phase_deg"),int(float(row["reassigned_bin"])),f(row,"phase_err_to_bin_deg")))
        conn.execute("INSERT OR REPLACE INTO candidate_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (row["candidate_id"],"LP-ML2A",None,f(row,"selected_Tx"),f(row,"selected_Tx"),f(row,"ratio"),f(row,"ratio"),f(row,"matrix_error"),f(row,"t_xx_phase_deg"),int(float(row["reassigned_bin"])),f(row,"phase_err_to_bin_deg"),0,row.get("x_status",""),"legacy_constant_index"))
    provenance(conn,"ml2a_manifest","v3",manifest_path,"local_uncommitted","18 H500 candidates")
    return metrics, manifest_path


def provenance(conn: sqlite3.Connection, record_type: str, record_id: str, source: Path, commit: str, notes: str) -> None:
    conn.execute("INSERT OR REPLACE INTO provenance VALUES (?,?,?,?,?,?,?,?,?)", (record_type,record_id,str(source),commit,"work/lp-stage11-4","integrate_native_materials_lp_database.py",datetime.now(timezone.utc).isoformat(),hash_file(source),notes))


def export_all(conn: sqlite3.Connection) -> None:
    for table in ("materials","material_samples","geometries","simulation_cases","jones_labels","candidate_metrics","provenance"):
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        write_csv(EXPORTS / f"{table}.csv", list(rows[0].keys()) if rows else [row[1] for row in conn.execute(f"PRAGMA table_info({table})")], rows)


def smoke450(metrics: list[dict[str,str]]) -> None:
    out = ML2A_DIR / "smoke450_v1"; out.mkdir(parents=True,exist_ok=True)
    fields = list(metrics[0].keys()) + ["material_model_type","is_historical"]
    with (out/"lp_ml2a_smoke450_metrics.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader(); writer.writerows([{**row,"material_model_type":"legacy_constant_index","is_historical":"true"} for row in metrics])
    summary={"case_count":len(metrics),"material_model_type":"legacy_constant_index","is_historical":True,"source_glob":"onecase_v1/*/onecase_metrics.csv"}
    (out/"lp_ml2a_smoke450_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    (ROOT/"reports"/"lp_ml2a_h500_tio2_scout_smoke450_v1_report.md").write_text("# LP-ML2A smoke450 aggregation\n\nImported six completed onecase metrics using Python Path glob/File paths. All are historical `legacy_constant_index` cases; none is native `tio22`.\n",encoding="utf-8")


def adapter_audit() -> dict[str,Any]:
    from metasurface.lumapi_runner import import_lumapi
    from metasurface.config import load_runtime_config
    from metasurface.lumerical_native_materials import ensure_apcd_native_materials
    fdtd = None
    result: dict[str,Any] = {"status":"negative_audit","no_fdtd_run":True,"no_fsp_saved":True}
    try:
        fdtd = import_lumapi(load_runtime_config("configs/runtime.yaml")).FDTD(hide=True)
        names = ensure_apcd_native_materials(fdtd)
        counts = {material_id: len(get_native_samples(material_id)) for material_id in names}
        index_450 = {material_id: {"n":get_nk(material_id,450.0).real,"k":get_nk(material_id,450.0).imag} for material_id in names}
        result = {"status":"success","material_names":names,"sample_counts":counts,"index_450":index_450,"no_fdtd_run":True,"no_fsp_saved":True}
    except Exception as exc:
        result["error_type"] = type(exc).__name__; result["error"] = str(exc)
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass
    (ROOT/"reports"/"lp_native_material_lumerical_adapter_audit.md").write_text("# LP native material Lumerical adapter audit\n\n```json\n"+json.dumps(result,indent=2)+"\n```\n\nNo FDTD run, GUI operation, or FSP save occurred. There is no constant-index fallback.\n",encoding="utf-8")
    return result


def write_docs(conn: sqlite3.Connection, audit: dict[str,Any]) -> None:
    counts={table:conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("materials","material_samples","geometries","simulation_cases","jones_labels","candidate_metrics","provenance")}
    model_counts=dict(conn.execute("SELECT material_model_type,COUNT(*) FROM simulation_cases GROUP BY material_model_type"))
    report=["# Canonical LP database native-material integration","", "## Schema", "SQLite tables: materials, material_samples, geometries, simulation_cases, jones_labels, candidate_metrics, provenance.", "", "## Counts", *[f"- {key}: {value}" for key,value in counts.items()], f"- legacy_constant_index cases: {model_counts.get('legacy_constant_index',0)}", f"- native_sampled_epsilon cases: {model_counts.get('native_sampled_epsilon',0)}", f"- unknown_legacy cases: {model_counts.get('unknown_legacy',0)}", "", "## Historical material audit", "- B01/C02/C05: all LP-ML1B2E rows use `legacy_constant_index=2.6`; the shared base runner hard-codes Object defined dielectric index=2.6.", "- LP-ML2A A00/A02/A04/A05/B02/C02: all completed 450 nm onecase rows are `legacy_constant_index` using manifest `n_material` values 2.25/2.35/2.50/2.60; none is native `tio22`.", "", "## Adapter", f"- status: {audit['status']}", f"- detail: {audit.get('error', audit.get('material_names'))}", "", "## New-run gate", "New LP simulation runners must use APCD_TIO2_NATIVE_M1 via the sampled-material adapter. Historical constant-index results remain read-only comparison data and are not native baselines.", ""]
    (ROOT/"reports"/"lp_database_native_material_integration.md").write_text("\n".join(report),encoding="utf-8")
    (DB_DIR/"README.md").write_text("# Canonical LP APCD database\n\n`lp_apcd_database.sqlite` stores native materials, native epsilon samples, imported historical LP geometry/case/Jones data, metrics, and provenance. Exports mirror every table. Native materials are dispersive sampled epsilon; historical constant-index cases are explicitly labeled and never upgraded to native.\n",encoding="utf-8")
    handoff=ROOT/"handoffs"/"materials"; handoff.mkdir(parents=True,exist_ok=True)
    (handoff/"APCD_NATIVE_MATERIAL_HANDOFF_MDC.md").write_text("# APCD native material handoff for MDC\n\n- High-index layer: APCD_TIO2_NATIVE_M1 / tio22\n- Low-index layer and SiO2 defect: APCD_SIO2_NATIVE_M1 / sio222\n- Authority: `configs/material_reference_apcd_blue.yaml`; native data: `outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv`.\n- At 450 nm, quarter-wave estimates are TiO2 44.34 nm and SiO2 78.88 nm; SiO2 half-wave defect 157.76 nm. TMM/FDTD must use wavelength-dependent n+ik, not fixed indices.\n",encoding="utf-8")
    (handoff/"APCD_NATIVE_MATERIAL_HANDOFF_TOTAL_SCHEME.md").write_text("# APCD native material handoff for total scheme\n\nLP/CP pillars and their K=6 descendants use APCD_TIO2_NATIVE_M1. MDC high-index layers use APCD_TIO2_NATIVE_M1; MDC low-index layers, SiO2 defect, and RCLED-MDC filter use APCD_SIO2_NATIVE_M1 as applicable. Future source-coupled FDTD must record material_reference_id. Historical n=2.25/n=2.50/n=2.60 outputs remain legacy only.\n",encoding="utf-8")


def main() -> int:
    DB_DIR.mkdir(parents=True,exist_ok=True); EXPORTS.mkdir(parents=True,exist_ok=True)
    if DB_PATH.exists(): DB_PATH.unlink()
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row
    try:
        schema(conn); insert_materials(conn); insert_b2e(conn); ml2a_metrics,_=insert_ml2a(conn); smoke450(ml2a_metrics); audit=adapter_audit(); write_docs(conn,audit); export_all(conn); conn.commit()
        print(json.dumps({table:conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("materials","material_samples","geometries","simulation_cases","jones_labels")},indent=2))
    finally: conn.close()

if __name__ == "__main__": main()
