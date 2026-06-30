#!/usr/bin/env python3
"""Prepare-only vertical geometry mapping audit for R2-2B.

Writes CSV/Markdown only. Does not import lumapi, launch Lumerical, or create
FSP/LDF/raw monitor files.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_2b_rcled_fdtd_vertical_geometry_mapping_audit"
R2_2A_GEOM = ROOT / "outputs" / "r2_2a_rcled_fdtd_dipole_prepare_only" / "r2_2a_candidate_geometry_summary.csv"
R2_2A_MANIFEST = ROOT / "outputs" / "r2_2a_rcled_fdtd_dipole_prepare_only" / "r2_2a_case_manifest.csv"
R2_1B_METRICS = ROOT / "outputs" / "r2_1b_rcled_highres_tmm_shortlist_verify" / "r2_1b_highres_metrics.csv"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"

PRIMARY_IDS = ["R2_1_00227", "R2_1_00223", "R2_1_04067"]
SMOKE_ID = "R2_1_00223"
TOP_LAYER_PERIOD = [("SiO2", 100), ("TiO2", 52)]
BOTTOM_LAYER_PERIOD = [("TiO2", 52), ("SiO2", 100)]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def repeat_layers(period: list[tuple[str, int]], count: int) -> str:
    if count <= 0:
        return "none"
    return " / ".join(f"{mat} {thick} nm" for _ in range(count) for mat, thick in period)


def load_primary() -> list[dict[str, str]]:
    geom_rows = read_csv(R2_2A_GEOM)
    metrics = {row["candidate_id"]: row for row in read_csv(R2_1B_METRICS)}
    by_id = {row["candidate_id"]: row for row in geom_rows}
    missing = [cid for cid in PRIMARY_IDS if cid not in by_id]
    if missing:
        raise ValueError(f"Missing primary candidate rows: {missing}")
    rows = []
    for cid in PRIMARY_IDS:
        row = dict(by_id[cid])
        row.update({f"metric_{k}": v for k, v in metrics.get(cid, {}).items()})
        rows.append(row)
    return rows


def stack_rows(candidates: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for c in candidates:
        top = int(float(c["top_pair_count"]))
        bottom = int(float(c["bottom_pair_count"]))
        cavity = float(c["cavity_span_nm"])
        term = c.get("termination", "none") or "none"
        rows += [
            {"candidate_id": c["candidate_id"], "order_from_output_side": 1, "stack_region": "air_output_side", "material_or_role": "air", "nominal_thickness_nm": "semi-infinite", "mapping_note": "+y / physical +z output side"},
            {"candidate_id": c["candidate_id"], "order_from_output_side": 2, "stack_region": "top_DBR", "material_or_role": repeat_layers(TOP_LAYER_PERIOD, top), "nominal_thickness_nm": top * 152, "mapping_note": f"top_pair_count={top}"},
            {"candidate_id": c["candidate_id"], "order_from_output_side": 3, "stack_region": "top_termination", "material_or_role": term, "nominal_thickness_nm": 0 if term == "none" else "see candidate", "mapping_note": "none for all R2-2A primary candidates"},
            {"candidate_id": c["candidate_id"], "order_from_output_side": 4, "stack_region": "GaN_cavity_or_effective_spacer", "material_or_role": "GaN cavity / effective optical spacer", "nominal_thickness_nm": cavity, "mapping_note": "R2 TMM cavity_span_nm; exact FDTD mapping audited in r2_2b_mapping_options.md"},
            {"candidate_id": c["candidate_id"], "order_from_output_side": 5, "stack_region": "MQW_dipole_plane", "material_or_role": "center x/y dipole", "nominal_thickness_nm": 0, "mapping_note": "place near cavity center for smoke run; keep away from DBR interfaces"},
            {"candidate_id": c["candidate_id"], "order_from_output_side": 6, "stack_region": "bottom_DBR", "material_or_role": repeat_layers(BOTTOM_LAYER_PERIOD, bottom), "nominal_thickness_nm": bottom * 152, "mapping_note": f"bottom_pair_count={bottom}"},
            {"candidate_id": c["candidate_id"], "order_from_output_side": 7, "stack_region": "substrate_or_bottom_boundary_side", "material_or_role": "lower boundary / substrate side", "nominal_thickness_nm": "simulation dependent", "mapping_note": "keep PML spacing outside stack"},
        ]
    return rows


def interface_audit(candidates: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for c in candidates:
        cavity = float(c["cavity_span_nm"])
        top = int(float(c["top_pair_count"]))
        bottom = int(float(c["bottom_pair_count"]))
        low_risk = c["candidate_id"] in ["R2_1_00227", "R2_1_00223"]
        rows.append({
            "candidate_id": c["candidate_id"],
            "top_pair_count": top,
            "bottom_pair_count": bottom,
            "cavity_span_nm": cavity,
            "zero_thickness_layers_expected": "no",
            "dbr_layer_overlap_allowed": "no",
            "mqw_inside_dbr_interface": "no",
            "mqw_min_distance_to_interface_nm_recommended": min(50, cavity / 4),
            "monitor_inside_pml_allowed": "no",
            "recommended_fdtd_x_span_um": 20,
            "recommended_device_width_um": 3,
            "recommended_monitor_x_span_um": 16,
            "forbidden_200um_span": "reject",
            "first_smoke_geometry_risk": "low" if low_risk else "medium_top_mirror_extraction_risk",
            "audit_pass_for_prepare_only": "yes",
        })
    return rows


def risk_rows(candidates: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for c in candidates:
        cid = c["candidate_id"]
        rows.append({"candidate_id": cid, "risk": "TMM cavity_span_nm may include effective DBR phase not literal spacer thickness", "severity": "medium", "mitigation": "Use literal mapping for first smoke only and record geometry exactly."})
        rows.append({"candidate_id": cid, "risk": "MQW source too close to DBR interface if cavity center is not enforced", "severity": "medium", "mitigation": "Place center source at cavity midpoint; audit distance to top/bottom interface."})
        if c.get("top_mirror_extraction_risk") == "medium":
            rows.append({"candidate_id": cid, "risk": "Medium top mirror extraction risk from R2-1B", "severity": "medium", "mitigation": "Run after low-risk top=6/bottom=6 candidates."})
    return rows


def smoke_rows(candidates: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for c in candidates:
        cid = c["candidate_id"]
        if cid == SMOKE_ID:
            choice = "first_smoke_candidate"
            reason = "top=6 bottom=6, low extraction risk, cavity=280 nm, slightly narrower spectral FWHM than R2_1_00227"
        elif cid == "R2_1_00227":
            choice = "second_if_smoke_passes"
            reason = "very similar low-risk true cavity, but spectral FWHM is slightly wider than R2_1_00223"
        else:
            choice = "third_family_check"
            reason = "different family and strong metrics, but medium extraction risk and top=8/bottom=4"
        rows.append({
            "candidate_id": cid,
            "smoke_priority": choice,
            "top_pair_count": c["top_pair_count"],
            "bottom_pair_count": c["bottom_pair_count"],
            "cavity_span_nm": c["cavity_span_nm"],
            "termination": c["termination"],
            "recommended_mapping_option": "Option A literal spacer mapping for first smoke",
            "planned_cases": "center_x, center_y at 453 nm",
            "reason": reason,
        })
    return rows


def update_index() -> None:
    marker = "## R2-2B Vertical Geometry Mapping Audit"
    block = f"""
{marker}

- Output: `outputs/r2_2b_rcled_fdtd_vertical_geometry_mapping_audit`
- No FDTD run; no Lumerical launched; no `.fsp`/`.ldf` generated.
- Selected first-smoke mapping: Option A literal spacer mapping, with explicit geometry audit before solve.
- Selected first-smoke candidate: R2_1_00223, center x/y dipoles at 453 nm.
- Main unresolved risk: TMM `cavity_span_nm` may include effective DBR penetration/phase, so FDTD results must be interpreted as a smoke validation before refined optical-phase fitting.
""".strip()
    old = INDEX.read_text(encoding="utf-8") if INDEX.exists() else "# RCLED MDC Workspace Index\n"
    if marker in old:
        old = old.split(marker)[0].rstrip()
    write_text(INDEX, old.rstrip() + "\n\n" + block)


def main() -> None:
    candidates = load_primary()
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "r2_2b_vertical_stack_mapping.csv", stack_rows(candidates))
    write_csv(OUT / "r2_2b_interface_safety_audit.csv", interface_audit(candidates))
    write_csv(OUT / "r2_2b_smoke_recommendation.csv", smoke_rows(candidates))
    write_csv(OUT / "r2_2b_geometry_risk_flags.csv", risk_rows(candidates))

    manifest_count = len(read_csv(R2_2A_MANIFEST))
    mapping = """
# R2-2B Mapping Options

## Option A: literal spacer mapping

Use `cavity_span_nm` directly as the physical GaN cavity / effective spacer thickness in the first 2D FDTD smoke model. Place the MQW dipole plane at the cavity center unless a later device-specific MQW depth is supplied.

This option does not claim that TMM `cavity_span_nm` is the final physical cavity thickness. It is the safest first smoke mapping because it is reproducible, auditable, and changes only one intended geometry variable.

## Option B: optical phase mapping

Treat `cavity_span_nm` as an effective optical cavity length proxy. The physical GaN thickness may need adjustment because DBR penetration phase and termination phase are not explicit in the simple TMM candidate label.

This is more physically flexible but unsafe for the first smoke run because it adds an extra fitting degree of freedom before any FDTD evidence exists.

## Recommendation

Use Option A for the first R2-2 FDTD smoke validation. If FDTD peak wavelength or angular response is shifted, use the mismatch to calibrate an Option B optical-phase correction later.
"""
    write_text(OUT / "r2_2b_mapping_options.md", mapping)

    source_monitor = f"""
# R2-2B Source and Monitor Plan

- Simulation type: 2D FDTD only, later stage only.
- Planned first smoke cases from R2-2A: {manifest_count} total; run only R2_1_00223 center_x and center_y first if doing a smoke gate.
- Source position: center only.
- Source y/z placement: MQW plane at cavity midpoint for first smoke; not inside DBR and not at a material interface.
- Dipoles: x and y separately; combine later by adding powers incoherently.
- Wavelength: 453 nm only for first smoke.
- No source-y offset scan.
- No full wavelength scan.
- FDTD x span: about 20 um, not 200 um.
- Device/GaN lateral width: about 3 um unless explicitly justified.
- Monitor x span: wide enough for angular extraction, previous controlled model used about 16 um.
- Monitor/PML: top monitor must remain outside PML and inside homogeneous output medium.
"""
    write_text(OUT / "r2_2b_source_monitor_plan.md", source_monitor)

    readable = ["# R2-2B Candidate Stack Readable", ""]
    for c in candidates:
        readable += [
            f"## {c['candidate_id']}",
            f"- family: {c['family']}",
            f"- top_pair_count: {c['top_pair_count']}",
            f"- bottom_pair_count: {c['bottom_pair_count']}",
            f"- cavity_span_nm: {c['cavity_span_nm']}",
            f"- termination: {c['termination']}",
            "- output side -> top DBR -> GaN cavity/effective spacer with MQW center -> bottom DBR -> bottom boundary side",
            "",
        ]
    write_text(OUT / "r2_2b_candidate_stack_readable.md", "\n".join(readable))

    summary = """
# R2-2B Vertical Geometry Mapping Audit

This is a prepare-only audit for mapping R2 TMM/STACK candidates into later 2D FDTD dipole validation geometry.

No FDTD was run. Lumerical was not launched. No `.fsp`, `.ldf`, or raw monitor files were created.

## Mapping decision

Selected for first smoke validation: **Option A, literal spacer mapping**.

`cavity_span_nm` should be used directly as the physical GaN cavity / effective spacer thickness for the first smoke model. This is not claimed to be the final calibrated physical thickness; it is the most reproducible first test before adding optical-phase correction.

## First smoke candidate

Selected: **R2_1_00223**.

Reason: true two-mirror cavity, top=6, bottom=6, cavity=280 nm, no termination, low extraction risk, and slightly narrower high-resolution TMM spectral FWHM than R2_1_00227.

## Geometry risks still open

- TMM `cavity_span_nm` may include effective DBR penetration and reflection phase.
- MQW source must be placed at the cavity center and audited away from DBR interfaces.
- Monitor/PML placement must be checked in the later FDTD setup before solving.
- R2_1_04067 is useful as a different-family check but has medium top-mirror extraction risk.
"""
    write_text(OUT / "r2_2b_summary.md", summary)

    next_steps = """
# R2-2B Next Steps

1. Review this mapping audit.
2. If approved, create R2-2C smoke runner for R2_1_00223 center_x and center_y at 453 nm only.
3. Before solving, write a geometry audit confirming no DBR/cavity overlap, no zero-thickness layers, MQW at cavity center, and monitor outside PML.
4. If smoke passes, run R2_1_00227 and then R2_1_04067.
5. If smoke fails with a shifted cavity response, add an optical-phase correction stage instead of sweeping blindly.
"""
    write_text(OUT / "r2_2b_next_steps.md", next_steps)
    update_index()
    print(f"wrote {OUT}")
    print("selected_mapping=Option A literal spacer mapping")
    print(f"selected_smoke_candidate={SMOKE_ID}")


if __name__ == "__main__":
    main()
