from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOE = Path("outputs/coupling_ml/APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1/K6_V1_64G_DOE_CANDIDATES.csv")
M2A = Path("outputs/coupling_ml/M2A_GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING_V1/M2A_NP22_GEOMETRY_CANDIDATE_POOL_V1.csv")
PW = Path("outputs/coupling_ml/APCD_COUPLING_PW_PERIODIC_ZERO_MODEL_AUDIT_V1/PW_PERIODIC_PILOT_GEOMETRY_MANIFEST.csv")
MANIFEST = Path("reports/coupling/PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST.json")
REPORT = Path("reports/coupling/PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST_AUTHORITY_V1.md")
CORE = {
    "W2H_15294": [155, 105, 195, 150, 180, 145],
    "W2H_06824": [135, 210, 200, 105, 210, 165],
    "W2H_19451": [205, 220, 100, 125, 170, 110],
    "W2H_10588": [160, 170, 135, 130, 130, 220],
}
CORE_ROLES = {
    "W2H_15294": "Core4 existing valid seed; no rerun",
    "W2H_06824": "Core4 mandatory new production case",
    "W2H_19451": "Core4 mandatory new production case",
    "W2H_10588": "Core4 mandatory new production case",
}
CONTRACT = {
    "monitors": {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"},
    "samples_nm": {"MON_IN": -100.0, "MON_PRENP": 1150.0, "MON_POSTNP": 1800.0},
    "references_nm": {"MON_IN": -50.0, "MON_PRENP": 1202.0, "MON_POSTNP": 1722.0},
    "materials": {"substrate": "APCD_GAN_NATIVE_M1", "mdc_tio2": "APCD_TIO2_NATIVE_M1", "mdc_sio2": "APCD_SIO2_NATIVE_M1", "superstrate": "Air"},
    "stack_layers": [["APCD_TIO2_NATIVE_M1", 44.0], ["APCD_SIO2_NATIVE_M1", 79.0], ["APCD_TIO2_NATIVE_M1", 44.0], ["APCD_SIO2_NATIVE_M1", 79.0], ["APCD_TIO2_NATIVE_M1", 44.0], ["APCD_SIO2_NATIVE_M1", 316.0], ["APCD_TIO2_NATIVE_M1", 44.0], ["APCD_SIO2_NATIVE_M1", 79.0], ["APCD_TIO2_NATIVE_M1", 44.0], ["APCD_SIO2_NATIVE_M1", 79.0], ["APCD_TIO2_NATIVE_M1", 44.0], ["APCD_SIO2_NATIVE_M1", 79.0]],
    "wavelengths_nm": list(range(440, 461)),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def h(values):
    return hashlib.sha256(",".join(str(int(float(x))) for x in values).encode("ascii")).hexdigest()

def rows(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def vec(row, names):
    return [int(float(row[name])) for name in names]

def source(rel):
    p = ROOT / rel
    return {"relative_path": rel.as_posix(), "absolute_path": str(p), "sha256": sha(p)}

def build():
    doe, m2a, pw = rows(ROOT / DOE), rows(ROOT / M2A), rows(ROOT / PW)
    space = [r for r in doe if r["design_family"] == "SPACE_FILLING"]
    expected = [f"K6V1_S{i:02d}" for i in range(1, 49)]
    if [r["geometry_id"] for r in space] != expected:
        raise RuntimeError("FROZEN_48_MAXIMIN_ORDER_MISSING_OR_CHANGED")
    if any(r["origin"] != "deterministic_halton_maximin_on_observed_candidate_grid" for r in space):
        raise RuntimeError("MAXIMIN_PROVENANCE_CHANGED")
    pw_by_id = {r["case_id"]: r for r in pw}
    entries = []
    for index, case_id in enumerate(CORE, 1):
        row = pw_by_id.get(case_id)
        values = CORE[case_id]
        if row is None or [int(x) for x in row["ordered_diameters_nm"].split(",")] != values:
            raise RuntimeError("CORE4_ORDER_MISMATCH:" + case_id)
        entries.append({
            "manifest_index": index, "case_id": case_id, "ordered_D_nm": values,
            "K": 6, "p_nm": 290, "Lambda_x_nm": 1740, "Lambda_y_nm": 290, "H_nm": 500, "spacer_nm": 237,
            "canonical_serialization": ",".join(map(str, values)), "geometry_hash_sha256": h(values),
            "source_dataset": "PW_PERIODIC_PILOT_GEOMETRY_MANIFEST", "source_row": pw.index(row) + 2,
            "historical_role": CORE_ROLES[case_id], "selection_authority": "Core4 mandatory order",
            "selection_rank": index, "duplicate_status": "UNIQUE_IN_MANIFEST",
            "solver_action": "NO_RERUN" if case_id == "W2H_15294" else "NEW_PRODUCTION_ENTRY",
        })
    for rank, row in enumerate(space[:16], 1):
        values = vec(row, tuple(f"D{i}_nm" for i in range(1, 7)))
        entries.append({
            "manifest_index": 4 + rank, "case_id": row["geometry_id"], "ordered_D_nm": values,
            "K": 6, "p_nm": 290, "Lambda_x_nm": 1740, "Lambda_y_nm": 290, "H_nm": 500, "spacer_nm": 237,
            "canonical_serialization": ",".join(map(str, values)), "geometry_hash_sha256": h(values),
            "source_dataset": "K6_V1_64G_DOE_CANDIDATES", "source_row": doe.index(row) + 2,
            "historical_role": "16-case diversity/maximin production candidate",
            "selection_authority": "Frozen 48-maximin CSV order; first eligible unique after Core4",
            "selection_rank": rank, "duplicate_status": "UNIQUE_IN_MANIFEST",
            "solver_action": "NEW_PRODUCTION_ENTRY", "source_declared_hash_sha256": row["geometry_fingerprint_sha256"],
        })
    vectors = [tuple(e["ordered_D_nm"]) for e in entries]
    hashes = [e["geometry_hash_sha256"] for e in entries]
    selected_conflicts = []
    selected_set = set(vectors)
    source_rows = []
    for r in doe:
        v = tuple(vec(r, tuple(f"D{i}_nm" for i in range(1, 7))))
        if v in selected_set: source_rows.append(("64G", r["geometry_id"], v))
    for r in m2a:
        v = tuple(vec(r, tuple(f"D{i}" for i in range(1, 7))))
        if v in selected_set: source_rows.append(("M2A", r["geometry_id"], v))
    for r in pw:
        v = tuple(int(x) for x in r["ordered_diameters_nm"].split(","))
        if v in selected_set: source_rows.append(("PW", r["case_id"], v))
    for v in selected_set:
        ids = {item[1] for item in source_rows if item[2] == v}
        if len(ids) > 1: selected_conflicts.append({"D": list(v), "ids": sorted(ids)})
    m2a_legacy_mismatch = sum(r.get("geometry_hash") != h(vec(r, tuple(f"D{i}" for i in range(1, 7)))) for r in m2a)
    audit = {
        "status": "PASS_ZERO_SOLVER", "manifest_entry_count": len(entries), "core4_count": 4, "diversity_count": 16,
        "unique_geometry_hash_count": len(set(hashes)), "w2h_15294_count": sum(e["case_id"] == "W2H_15294" for e in entries),
        "blind_selected_count": 0, "permutations_or_sorted_vectors_used": 0,
        "physical_order_preserved": all(e["canonical_serialization"] == ",".join(map(str, e["ordered_D_nm"])) for e in entries),
        "integrated_pw_labels_used_for_selection": False, "selected_identity_conflict_count": len(selected_conflicts),
        "selected_identity_conflicts": selected_conflicts, "m2a_legacy_hash_semantics_mismatch_count": m2a_legacy_mismatch,
        "solver_invocations": 0, "queue_entries_created": 0, "new_production_entries": 19,
    }
    if audit["manifest_entry_count"] != 20 or audit["unique_geometry_hash_count"] != 20 or audit["selected_identity_conflict_count"] != 0:
        raise RuntimeError("MANIFEST_AUDIT_FAILED")
    contract_hash = hashlib.sha256(json.dumps(CONTRACT, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
    manifest = {
        "schema": "PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST_AUTHORITY", "status": "FROZEN_ZERO_SOLVER",
        "authority_case": "CASE_A_FROZEN_48_MAXIMIN_CSV_ORDER",
        "selection_policy": "Core4 indices 01-04, then first 16 eligible unique rows of frozen S01-S48 order; no reranking",
        "target_G": 20, "valid_G_before_queue": 1, "new_production_entries": 19,
        "physical_contract": {
            "contract_id": "APCD_PW_PERIODIC_PLANAR_5NM_GPU_PRODUCTION_V3", "contract_sha256": contract_hash,
            "K": 6, "p_nm": 290, "Lambda_x_nm": 1740, "Lambda_y_nm": 290, "H_nm": 500, "spacer_nm": 237,
            "source": "GaN to air +z normal-incidence X-pol", "wavelengths_nm": list(range(440, 461)),
            "boundary_contract": {"x": "Periodic", "y": "Periodic", "z_min": "PML", "z_max": "PML"},
            "modal_normalization": "PW_COMPLEX_FLOQUET_STATE_V1 complex lossy local-medium forward/backward amplitudes",
            "energy_accounting": "R/T/A with complex incident-power proxy and existing admitted 5nm production TMM stack",
            "mesh_convergence": "5NM_GPU_PRODUCTION_SCHEMA_V3 admitted seed contract; no contract changes",
            "contract": CONTRACT,
        },
        "source_authority_files": {
            "primary_64G_doe": source(DOE), "m2a_cross_check_only": source(M2A), "pw_core4_cross_check": source(PW),
            "deterministic_generator_source": source(Path("scripts/coupling_ml/apcd_database_authority_audit_v1.py")),
        },
        "entries": entries, "audit": audit,
    }
    return manifest

def report(m):
    a = m["audit"]
    lines = [
        "# PW_K6_SEED_DB_V1 geometry manifest authority", "",
        "Status: FROZEN_ZERO_SOLVER", "",
        "Selection authority: CASE_A_FROZEN_48_MAXIMIN_CSV_ORDER.",
        "The primary 64G DOE S01-S48 order is consumed as frozen; no new distance metric, seed, normalization, integrated PW label, or manual shortlist was used.", "",
        "## Contract", "",
        "- K=6; p=290 nm; Lambda_x=1740 nm; Lambda_y=290 nm; H=500 nm; spacer=237 nm.",
        "- x/y Periodic; z min/max PML; GaN to air, +z, normal-incidence X polarization; 440:1:460 nm.",
        "- Existing admitted 5 nm GPU production monitor/post-processing contract is reused unchanged.", "",
        "## Zero-solver audit", "",
        f"- Entries: {a['manifest_entry_count']} = {a['core4_count']} Core4 + {a['diversity_count']} diversity.",
        f"- Unique ordered geometry hashes: {a['unique_geometry_hash_count']}; W2H_15294 count: {a['w2h_15294_count']}.",
        f"- Blind selected: {a['blind_selected_count']}; sorted/permuted selection: {a['permutations_or_sorted_vectors_used']}.",
        f"- Physical order preserved: {a['physical_order_preserved']}; integrated PW labels used: {a['integrated_pw_labels_used_for_selection']}.",
        f"- Selected cross-source identity conflicts: {a['selected_identity_conflict_count']}.",
        f"- Solver invocations: {a['solver_invocations']}; queue entries created by manifest build: {a['queue_entries_created']}.",
        f"- M2A legacy source-hash mismatches, cross-check only: {a['m2a_legacy_hash_semantics_mismatch_count']}.", "",
        "## Entries", "", "| index | case_id | D1..D6 nm | role | hash | source |", "|---:|---|---|---|---|---|",
    ]
    for e in m["entries"]:
        lines.append(f"| {e['manifest_index']:02d} | {e['case_id']} | {','.join(map(str,e['ordered_D_nm']))} | {e['historical_role']} | {e['geometry_hash_sha256']} | {e['source_dataset']} row {e['source_row']} |")
    lines += ["", "## Queue authorization", "", "After this manifest is committed and the zero-solver audit passes, enqueue exactly the 19 entries with NEW_PRODUCTION_ENTRY. W2H_15294 is already valid and is not enqueued or rerun.", "Shared V3 limits remain GPU physical cap=3, Global=3, Traditional=1, Coupling-ML=2, slot-local autofill, and no cohort barrier.", ""]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    m = build()
    if args.write:
        p = ROOT / MANIFEST
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(m, indent=2, ensure_ascii=True) + "\n", encoding='utf-8')
        (ROOT / REPORT).write_text(report(m), encoding='utf-8')
        print(json.dumps({'status': 'PASS', 'entries': 20, 'solver_invocations': 0, 'manifest': str(p), 'report': str(ROOT / REPORT)}))
    else:
        print(json.dumps({'status': 'PASS', 'entries': len(m['entries']), 'solver_invocations': 0}))

if __name__ == '__main__':
    main()
