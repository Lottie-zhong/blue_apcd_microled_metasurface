"""Static P1 asymmetric-mirror structure compiler; deliberately solver-free."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from build_mdc_ml_database_v1 import canonical_hash, parse_seq, seq_string

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "outputs" / "mdc_design_space_coverage_audit_v1"
DB = ROOT / "datasets" / "mdc_ml_database_v1"
OUT = ROOT / "outputs" / "mdc_p1_asymmetric_scan_static_v1"
REPORT = ROOT / "reports" / "mdc_p1_asymmetric_scan_static_v1.md"
SPLITS = ((1, 5), (2, 4), (3, 3), (4, 2), (5, 1))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sequence_hash(seq: list[tuple[str, int]]) -> str:
    """Stable layer-only fingerprint; geometry_hash remains the repository canonical hash."""
    return hashlib.sha256(json.dumps(seq, separators=(",", ":")).encode()).hexdigest()


def explicit_compile(h: int, l: int, c: int, n_gan: int, n_air: int) -> list[tuple[str, int]]:
    """GaN -> stack -> Air: (LH)^N_GaN / L_C / (HL)^N_Air."""
    return [("L", l), ("H", h)] * n_gan + [("L", c)] + [("H", h), ("L", l)] * n_air


def zl1_compile(h: int, l: int, m: int, n_gan: int, n_air: int) -> list[tuple[str, int]]:
    """GaN -> stack -> Air, merging left-terminal L with inserted L^M."""
    if n_gan < 1 or n_air < 1:
        raise ValueError("P1 requires at least one mirror pair on both sides")
    effective = (m + 1) * l
    return [("H", h), ("L", l)] * (n_gan - 1) + [("H", h), ("L", effective)] + [("H", h), ("L", l)] * n_air


def material_adjacent_ok(seq: list[tuple[str, int]]) -> bool:
    return all(a[0] != b[0] for a, b in zip(seq, seq[1:]))


def topology_from_matrix() -> list[dict[str, str]]:
    rows = [r for r in read_csv(AUDIT / "proposed_scan_matrix_v1.csv") if r["scan_stage"] == "P1_asymmetric_mirror"]
    if len(rows) != 15:
        raise RuntimeError(f"expected 15 P1 rows, got {len(rows)}")
    return rows


def geometry_lookup() -> dict[str, dict[str, str]]:
    return {r["geometry_hash"]: r for r in read_csv(DB / "geometry_master.csv")}


def canonical_tmm_hashes() -> set[str]:
    return {r["geometry_hash"] for r in read_csv(DB / "tmm_nominal_metrics.csv")}


def parse_matrix_sequence(value: str) -> list[tuple[str, int]]:
    payload = json.loads(value)
    seq = parse_seq(" ".join(payload)) if payload and isinstance(payload[0], str) else parse_seq(payload)
    # Matrix notation C156 denotes the Explicit SiO2 defect; the physical compiler stores it as L156.
    return [("L" if material == "C" else material, thickness) for material, thickness in seq]


def compile_from_seed(seed: dict[str, object], n_gan: int, n_air: int) -> list[tuple[str, int]]:
    if seed["topology"] == "Explicit":
        return explicit_compile(seed["H_nm"], seed["L_nm"], seed["C_nm"], n_gan, n_air)
    return zl1_compile(seed["H_nm"], seed["L_nm"], seed["M"], n_gan, n_air)


def resolve_seeds() -> tuple[list[dict[str, object]], dict[tuple[str, int, int], dict[str, str]]]:
    matrix = topology_from_matrix()
    by_key = {(r["seed_candidate"], int(r["N_GaN"]), int(r["N_Air"])): r for r in matrix}
    if len(by_key) != 15:
        raise RuntimeError("P1 matrix has duplicate seed/split rows")
    expected = [
        {"seed_id": "explicit_fab", "candidate": "EX_N3_L79_H45_C156", "topology": "Explicit", "H_nm": 45, "L_nm": 79, "C_nm": 156, "M": "", "control_status": "existing_canonical_control"},
        {"seed_id": "zl1_nominal", "candidate": "ZL1_N3_M3_L78_H46", "topology": "ZL-1", "H_nm": 46, "L_nm": 78, "C_nm": "", "M": 3, "control_status": "existing_canonical_control"},
        {"seed_id": "zl1_alternative", "candidate": "ZL1_N3_M3_L79_H44", "historical_reference": "ZL1_N3_M3_L79_H44_C316", "topology": "ZL-1", "H_nm": 44, "L_nm": 79, "C_nm": "", "M": 3, "control_status": "existing_historical_reference_control"},
    ]
    seen = set()
    for seed in expected:
        for n_gan, n_air in SPLITS:
            key = (seed["candidate"], n_gan, n_air)
            source = by_key.get(key)
            if source is None:
                raise RuntimeError(f"P1 matrix missing {key}")
            if source["topology"] != seed["topology"]:
                raise RuntimeError(f"topology mismatch for {key}")
            for name in ("H_nm", "L_nm", "C_nm", "M"):
                want = seed[name]
                got = source.get(name, "")
                if str(want) != str(got):
                    raise RuntimeError(f"matrix parameter mismatch {key}: {name}={got!r}, expected {want!r}")
            compiled = compile_from_seed(seed, n_gan, n_air)
            matrix_seq = parse_matrix_sequence(source["layer_sequence"])
            if compiled != matrix_seq:
                raise RuntimeError(f"compiler/matrix sequence mismatch for {key}")
        seen.add(seed["candidate"])
    if len(seen) != 3:
        raise RuntimeError("seed resolution is not unique")
    return expected, by_key


def build_rows() -> tuple[list[dict[str, object]], dict[str, object]]:
    seeds, matrix = resolve_seeds()
    geos = geometry_lookup()
    tmm_hashes = canonical_tmm_hashes()
    rows = []
    seed_resolution = []
    for seed in seeds:
        control_seq = compile_from_seed(seed, 3, 3)
        control_hash = canonical_hash(control_seq)
        geo = geos.get(control_hash)
        if geo is None:
            raise RuntimeError(f"symmetric control has no exact geometry_master identity: {seed['candidate']}")
        if seed["seed_id"] != "zl1_alternative" and control_hash not in tmm_hashes:
            raise RuntimeError(f"canonical symmetric control missing from tmm_nominal_metrics: {seed['candidate']}")
        if seed["seed_id"] == "zl1_alternative" and seed["historical_reference"] not in geo.get("candidate_aliases", ""):
            raise RuntimeError("alternative historical reference identity does not resolve to exact symmetric geometry")
        seed_resolution.append({
            "seed_id": seed["seed_id"], "requested_candidate": seed["candidate"], "historical_reference": seed.get("historical_reference", ""),
            "resolved_geometry_hash": control_hash, "resolved_geometry_id": geo["geometry_id"],
            "resolved_candidate_primary": geo["candidate_id_primary"], "resolved_candidate_aliases": geo["candidate_aliases"],
            "symmetric_sequence": seq_string(control_seq), "symmetric_hash_replay": "pass",
        })
        for n_gan, n_air in SPLITS:
            seq = compile_from_seed(seed, n_gan, n_air)
            gh = canonical_hash(seq)
            expected_matrix = matrix[(seed["candidate"], n_gan, n_air)]
            is_control = (n_gan, n_air) == (3, 3)
            status = seed["control_status"] if is_control else "proposed_novel"
            effective = (int(seed["M"]) + 1) * int(seed["L_nm"]) if seed["topology"] == "ZL-1" else ""
            added = int(seed["M"]) * int(seed["L_nm"]) if seed["topology"] == "ZL-1" else ""
            thickness = sum(t for _, t in seq)
            required_layers = 13 if seed["topology"] == "Explicit" else 12
            expected_thickness = 900 if seed["seed_id"] == "explicit_fab" else (978 if seed["seed_id"] == "zl1_nominal" else 975)
            if len(seq) != required_layers or thickness != expected_thickness or not material_adjacent_ok(seq):
                raise RuntimeError(f"compile validation failed for {seed['candidate']} {n_gan}/{n_air}")
            if is_control and gh != control_hash:
                raise RuntimeError("symmetric replay hash mismatch")
            rows.append({
                "static_structure_id": f"P1_{seed['seed_id'].upper()}_G{n_gan}_A{n_air}", "seed_id": seed["seed_id"],
                "topology": seed["topology"], "N_GaN": n_gan, "N_Air": n_air, "H_nm": seed["H_nm"], "L_nm": seed["L_nm"],
                "C_nm": seed["C_nm"], "M": seed["M"], "added_defect_nm": added, "effective_center_nm": effective,
                "layer_count": len(seq), "total_thickness_nm": thickness, "sequence_GaN_to_Air": seq_string(seq),
                "sequence_Air_to_GaN": seq_string(list(reversed(seq))), "canonical_sequence_hash": sequence_hash(seq), "geometry_hash": gh,
                "existing_geometry_status": status, "source_identity": geo["geometry_id"] if is_control else expected_matrix["sequence_hash"],
                "validation_status": "pass",
            })
    if len(rows) != 15 or len({r["canonical_sequence_hash"] for r in rows}) != 15 or len({r["geometry_hash"] for r in rows}) != 15:
        raise RuntimeError("P1 static uniqueness/count validation failed")
    if Counter(r["seed_id"] for r in rows) != {"explicit_fab": 5, "zl1_nominal": 5, "zl1_alternative": 5}:
        raise RuntimeError("P1 seed split counts invalid")
    summary = {"total_rows": len(rows), "seed_count": len(seeds), "symmetric_existing_controls": sum(r["existing_geometry_status"] != "proposed_novel" for r in rows),
               "proposed_novel_geometries": sum(r["existing_geometry_status"] == "proposed_novel" for r in rows), "sequence_hash_unique": len({r["canonical_sequence_hash"] for r in rows}),
               "geometry_hash_unique": len({r["geometry_hash"] for r in rows}), "solver_invoked": False}
    return rows, {"seed_resolution": seed_resolution, "summary": summary}


FIELDS = ["static_structure_id", "seed_id", "topology", "N_GaN", "N_Air", "H_nm", "L_nm", "C_nm", "M", "added_defect_nm", "effective_center_nm", "layer_count", "total_thickness_nm", "sequence_GaN_to_Air", "sequence_Air_to_GaN", "canonical_sequence_hash", "geometry_hash", "existing_geometry_status", "source_identity", "validation_status"]


def write_outputs(rows: list[dict[str, object]], audit: dict[str, object]) -> None:
    OUT.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "p1_asymmetric_structures.csv", rows, FIELDS)
    (OUT / "p1_asymmetric_sequences.json").write_text(json.dumps([{k: r[k] for k in ("static_structure_id", "sequence_GaN_to_Air", "sequence_Air_to_GaN", "canonical_sequence_hash", "geometry_hash")} for r in rows], indent=2), encoding="utf-8")
    (OUT / "p1_seed_resolution.json").write_text(json.dumps(audit["seed_resolution"], indent=2), encoding="utf-8")
    validation = {"status": "pass", **audit["summary"], "all_total_mirror_pairs": 6, "no_adjacent_same_material": True,
                  "direction": "GaN -> stack -> Air", "no_solver_import_or_invocation": True}
    (OUT / "p1_static_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    lines = ["# MDC P1 asymmetric scan static build v1", "", "Static compilation only; no TMM, FDTD, solver, runtime, or performance metric was run/created.", "",
             "## Direction and grammar", "", "Canonical calculation direction: GaN -> stack -> Air. Reverse display is Air -> stack -> GaN only.", "", "- Explicit: `(LH)^N_GaN / L_C / (HL)^N_Air`; C=156 nm, 13 physical layers, 900 nm total.", "- ZL-1: the left-terminal L merges with inserted L^M into L_(M+1); no adjacent independent L layers remain.", "- Nominal: M=3, L=78, added=234 nm, effective center=312 nm, 12 layers, 978 nm total.", "- Alternative: M=3, L=79, added=237 nm, effective center=316 nm, 12 layers, 975 nm total. `C316` is a historical effective-center identity, not an added independent C layer.", "",
             "## Counts", "", f"- 15 structures: 3 existing symmetric controls and 12 proposed novel asymmetric structures.", "- Each seed has splits (1,5), (2,4), (3,3), (4,2), (5,1); total mirror pairs remain 6.", "- Canonical sequence hashes and geometry hashes are unique; all symmetric control hash replays pass.", "", "## Structures", "", "|id|seed|split|layers|thickness nm|status|", "|---|---|---|---:|---:|---|"]
    lines += [f"|{r['static_structure_id']}|{r['seed_id']}|({r['N_GaN']},{r['N_Air']})|{r['layer_count']}|{r['total_thickness_nm']}|{r['existing_geometry_status']}|" for r in rows]
    REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")


def audit_existing() -> None:
    rows = read_csv(OUT / "p1_asymmetric_structures.csv")
    if len(rows) != 15: raise RuntimeError("audit rows != 15")
    if len({r["canonical_sequence_hash"] for r in rows}) != 15 or len({r["geometry_hash"] for r in rows}) != 15: raise RuntimeError("audit duplicate hash")
    for row in rows:
        seq = parse_seq(row["sequence_GaN_to_Air"])
        if not material_adjacent_ok(seq) or int(row["N_GaN"]) + int(row["N_Air"]) != 6: raise RuntimeError("audit topology failure")
    print(json.dumps({"audit": "PASS", "rows": len(rows), "solver_invoked": False}))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--audit-only", action="store_true"); args = parser.parse_args()
    if args.audit_only: audit_existing(); return
    rows, audit = build_rows(); write_outputs(rows, audit)
    print(json.dumps({"static_build": "PASS", **audit["summary"]}))


if __name__ == "__main__":
    main()
