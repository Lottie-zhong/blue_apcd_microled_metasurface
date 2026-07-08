from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_defect_450")
OUT = ROOT / "outputs" / "mdc1d0_fdtd_2d_plan"
REPORT_DIR = ROOT / "reports" / "mdc_defect_450"
OUT.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAGE = "MDC1D0_FDTD_2D_incoherent_average_plan"
WAVELENGTHS_NM = [450.0]
SOURCE_X_NM = [0.0, -500.0, 500.0]
DIPOLES = ["x"]  # first FDTD probe only; z/y can be added after smoke pass

NIDX = {
    "Air": 1.0,
    "SiO2": 1.426,
    "TiO2": 2.535,
    "GaN": 2.41,
}

CANDIDATES = [
    {
        "candidate_id": "BARE_GaN_Air",
        "role": "bare_reference",
        "design_layers": [],
        "priority": 0,
    },
    {
        "candidate_id": "MDC1B_FAB_0126",
        "role": "baseline_fab_primary",
        "design_layers": [("SiO2",79),("TiO2",45)]*3 + [("SiO2",156)] + [("TiO2",45),("SiO2",79)]*3,
        "priority": 1,
    },
    {
        "candidate_id": "MDC-A0-INT",
        "role": "rounded_reference",
        "design_layers": [("SiO2",79),("TiO2",44)]*3 + [("SiO2",158)] + [("TiO2",44),("SiO2",79)]*3,
        "priority": 2,
    },
    {
        "candidate_id": "MDC1B_PERF_0890",
        "role": "performance_anchor",
        "design_layers": [("SiO2",81),("TiO2",44)]*4 + [("SiO2",157)] + [("TiO2",44),("SiO2",81)]*4,
        "priority": 3,
    },
]

SEARCH_PATTERNS = [
    "addfdtd",
    "adddipole",
    "dipole",
    "frequency domain field",
    "farfield",
    "transmission",
    "getresult",
    "run(",
    "runanalysis",
    "power",
    "monitor",
    "FDTD 2D",
    "dimension",
    "mesh accuracy",
    "PML",
    "setglobalmonitor",
    "setnamed",
]

def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"unavailable: {exc}"

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

def layer_string(layers: list[tuple[str, int]]) -> str:
    if not layers:
        return "bare GaN/Air"
    return " / ".join(f"{mat}:{th}nm" for mat, th in layers)

def physical_emission_stack(layers: list[tuple[str, int]]) -> str:
    if not layers:
        return "GaN -> Air"
    return "GaN -> " + " -> ".join(f"{mat}:{th}nm" for mat, th in reversed(layers)) + " -> Air"

def search_templates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    search_roots = [ROOT / "scripts", ROOT / "reports"]
    for base in search_roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() not in [".py", ".lsf", ".md", ".txt"]:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            low = text.lower()
            matched = [p for p in SEARCH_PATTERNS if p.lower() in low]
            if matched:
                # Keep only compact snippets.
                snippets = []
                lines = text.splitlines()
                for i, line in enumerate(lines, 1):
                    ll = line.lower()
                    if any(p.lower() in ll for p in matched):
                        snippets.append(f"L{i}: {line.strip()[:220]}")
                    if len(snippets) >= 8:
                        break
                rows.append({
                    "path": str(path.relative_to(ROOT)),
                    "suffix": path.suffix,
                    "matched_terms": ";".join(matched),
                    "snippet": " | ".join(snippets),
                })
    return rows

def main() -> int:
    job_rows: list[dict[str, Any]] = []
    job_id = 0
    for cand in CANDIDATES:
        for wl in WAVELENGTHS_NM:
            for sx in SOURCE_X_NM:
                for dip in DIPOLES:
                    job_id += 1
                    job_rows.append({
                        "stage": STAGE,
                        "job_id": f"MDC1D0_JOB_{job_id:03d}",
                        "candidate_id": cand["candidate_id"],
                        "role": cand["role"],
                        "priority": cand["priority"],
                        "wavelength_nm": wl,
                        "source_x_nm": sx,
                        "source_y_or_z_note": "to be placed inside GaN below MDC; exact 2D coordinate decided by FDTD template",
                        "dipole": dip,
                        "design_side_layers": layer_string(cand["design_layers"]),
                        "physical_emission_stack": physical_emission_stack(cand["design_layers"]),
                        "noncoherent_average_group": f"{cand['candidate_id']}_{wl:.1f}nm_{dip}dipole",
                        "planned_metrics": "upward_power;angular_spectrum;cone_20deg_power;large_angle_40_60deg_leakage;normal_to_large_angle_ratio;center_side_sensitivity",
                        "run_status": "planned_not_run",
                    })

    template_rows = search_templates()

    summary = {
        "stage": STAGE,
        "created": datetime.now().isoformat(timespec="seconds"),
        "branch": git(["branch", "--show-current"]),
        "head": git(["rev-parse", "--short", "HEAD"]),
        "scope": "2D FDTD noncoherent averaging execution plan and local template audit only",
        "forbidden_confirmed": {
            "fsp_opened": False,
            "fdtd_run_performed": False,
            "runanalysis_performed": False,
            "commit_before_user_review": False,
        },
        "num_candidates": len(CANDIDATES),
        "num_planned_jobs": len(job_rows),
        "wavelengths_nm": WAVELENGTHS_NM,
        "source_x_nm": SOURCE_X_NM,
        "dipoles": DIPOLES,
        "primary_candidate": "MDC1B_FAB_0126",
        "template_match_count": len(template_rows),
        "decision": "ready_for_user_review_before_MDC1D1_FDTD_smoke",
    }

    write_csv(OUT / "mdc1d0_fdtd_2d_job_manifest.csv", job_rows)
    write_csv(OUT / "mdc1d0_fdtd_template_audit.csv", template_rows)
    (OUT / "mdc1d0_fdtd_2d_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Tracked lightweight copies.
    write_csv(REPORT_DIR / "mdc1d0_fdtd_2d_job_manifest.csv", job_rows)
    write_csv(REPORT_DIR / "mdc1d0_fdtd_template_audit.csv", template_rows)

    md = []
    md.append("# MDC1D0 2D FDTD noncoherent-average plan\n")
    md.append(f"Generated: {summary['created']}\n")
    md.append("## Scope\n")
    md.append("This stage prepares the 2D FDTD validation plan for MDC. It does not open FSP, does not run Lumerical/FDTD, and does not perform runanalysis.\n")
    md.append("## Physical goal\n")
    md.append("Validate the MDC source-module using 2D FDTD with lateral source-position averaging:\n")
    md.append("```text\ncenter source + left source + right source -> incoherent power average\n```\n")
    md.append("This is needed because FMM/TMM treat the MDC as laterally uniform, while 2D FDTD can later include finite window, source placement, and angular-spectrum extraction.\n")
    md.append("## Planned candidate set\n")
    for cand in CANDIDATES:
        md.append(f"- `{cand['candidate_id']}` ({cand['role']}): {layer_string(cand['design_layers'])}")
    md.append("\n## Planned source set\n")
    md.append(f"- wavelengths: `{WAVELENGTHS_NM}` nm")
    md.append(f"- source x positions: `{SOURCE_X_NM}` nm")
    md.append(f"- first dipole set: `{DIPOLES}`")
    md.append(f"- planned jobs: `{len(job_rows)}`\n")
    md.append("## Metrics to extract in MDC1D1+\n")
    md.append("- upward power")
    md.append("- angular spectrum")
    md.append("- 20° cone power")
    md.append("- 40–60° large-angle leakage")
    md.append("- normal-to-large-angle ratio")
    md.append("- center/side sensitivity")
    md.append("- noncoherent averaged metrics\n")
    md.append("## Template audit\n")
    md.append(f"- matched local script/report files: `{len(template_rows)}`")
    md.append("- See `reports/mdc_defect_450/mdc1d0_fdtd_template_audit.csv`.\n")
    md.append("## Decision\n")
    md.append("Next safe stage is `MDC1D1`: build a minimal 2D FDTD smoke script for one case first, preferably `BARE_GaN_Air` and then `MDC1B_FAB_0126`, before launching all 12 planned jobs.\n")
    md.append("## Tracked lightweight outputs\n")
    md.append("- `reports/mdc_defect_450/mdc1d0_fdtd_2d_plan.md`")
    md.append("- `reports/mdc_defect_450/mdc1d0_fdtd_2d_job_manifest.csv`")
    md.append("- `reports/mdc_defect_450/mdc1d0_fdtd_template_audit.csv`\n")

    (REPORT_DIR / "mdc1d0_fdtd_2d_plan.md").write_text("\n".join(md), encoding="utf-8")

    print("MDC1D0 FDTD 2D plan generated")
    print("decision=", summary["decision"])
    print("num_planned_jobs=", len(job_rows))
    print("template_match_count=", len(template_rows))
    print("manifest=", REPORT_DIR / "mdc1d0_fdtd_2d_job_manifest.csv")
    print("template_audit=", REPORT_DIR / "mdc1d0_fdtd_template_audit.csv")
    print("report=", REPORT_DIR / "mdc1d0_fdtd_2d_plan.md")

    print("\nTOP TEMPLATE MATCHES:")
    for row in template_rows[:12]:
        print(f"- {row['path']} :: {row['matched_terms']}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
