from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "reports/stage11_3b0_lp_h500_spectral_data_inventory.md"
PHASE_BINS = [0, 60, 120, 180, 240, 300]
FIRST_PASS = [449, 450, 451]
OPTIONAL_WINDOW = [448, 449, 450, 451, 452]
EXCLUDED = ["outputs/", "*.fsp", "*.ldf", "*.log", "*monitor*", "*farfield*", "*far_field*", "*fielddump*", "*dump*"]
SEARCH_ROOTS = ["reports", "docs", "scripts", "tests", "tracked lightweight *.csv/*.json/*.md/*.py outside excluded paths"]
CANDIDATE_RE = re.compile(r"H500DIMER[A-Za-z0-9_\-]+")
FROZEN_LINE_RE = re.compile(r"(?P<bin>0|60|120|180|240|300)\s*(?:deg|°)\s*:\s*[^\n]*?(?P<cid>H500DIMER[A-Za-z0-9_\-]+)", re.I)
WL_RE = re.compile(r"(?:WL|wavelength[_\s-]*nm\D{0,8}|lambda[_\s-]*nm\D{0,8}|\b)(44[7-9]|45[0-6])\s*(?:NM|nm)?", re.I)
METRIC_RE = re.compile(r"\b(ratio|Tx|phase|matrix|leakage)\b", re.I)


@dataclass
class CandidateInventory:
    phase_bin_deg: int
    candidate_id: str
    available_wavelengths_nm: set[int] = field(default_factory=set)
    source_files: set[str] = field(default_factory=set)
    status_notes: set[str] = field(default_factory=set)
    evidence_order: int = 0

    def row(self) -> dict[str, str]:
        available = sorted(self.available_wavelengths_nm)
        missing_first = [w for w in FIRST_PASS if w not in self.available_wavelengths_nm]
        missing_optional = [w for w in OPTIONAL_WINDOW if w not in self.available_wavelengths_nm]
        if len(available) > 1:
            status = "confirmed multi-wavelength data exists"
        elif available == [450]:
            status = "only 450 nm single-point data exists"
        else:
            status = "no usable spectral data found"
        return {
            "phase_bin_deg": str(self.phase_bin_deg),
            "candidate_id": self.candidate_id,
            "available_wavelengths_nm": ";".join(map(str, available)) if available else "none",
            "missing_449_450_451_nm": ";".join(map(str, missing_first)) if missing_first else "none",
            "missing_448_449_450_451_452_nm": ";".join(map(str, missing_optional)) if missing_optional else "none",
            "source_files": "; ".join(sorted(self.source_files)),
            "status": status,
        }


def run_git_ls_files() -> list[Path]:
    proc = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    paths: list[Path] = []
    for line in proc.stdout.splitlines():
        path = Path(line)
        text = path.as_posix().lower()
        if text.startswith("outputs/"):
            continue
        if not (text.startswith(("reports/", "docs/", "scripts/", "tests/")) or path.suffix.lower() in {".csv", ".json", ".md", ".py"}):
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md", ".py"}:
            continue
        if any(token in text for token in [".fsp", ".ldf", ".log", "monitor", "farfield", "far_field", "fielddump", "dump"]):
            continue
        paths.append(REPO_ROOT / path)
    return paths


def infer_wavelengths_from_line(line: str, default_450_when_measured: bool = False) -> set[int]:
    found = {int(m.group(1)) for m in WL_RE.finditer(line)}
    # Stage11 frozen dimer report lines carry measured ratio/Tx/phase but usually omit wavelength;
    # in this project context those are the 450 nm center-point data, not spectral data.
    if not found and default_450_when_measured and (METRIC_RE.search(line) or "usable" in line.lower()):
        found.add(450)
    return found


def parse_phase_bin(line: str, candidate: str) -> int | None:
    frozen = FROZEN_LINE_RE.search(line)
    if frozen and frozen.group("cid") == candidate:
        return int(frozen.group("bin"))
    around = re.search(r"(?:bin|phase_bin|target|nearest)[_\s-]*(?:deg)?\D{0,10}(0|60|120|180|240|300)", line, re.I)
    if around:
        return int(around.group(1))
    embedded = re.search(r"_B(0|60|120|180|240|300)_", candidate)
    if embedded:
        return int(embedded.group(1))
    return None


def collect_inventory(paths: list[Path]) -> dict[tuple[int, str], CandidateInventory]:
    inventory: dict[tuple[int, str], CandidateInventory] = {}
    order = 0
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        for line in text.splitlines():
            order += 1
            lowered = line.lower()
            if any(token in lowered for token in ["outputs/", "outputs\\", ".fsp", ".ldf", ".log", "monitor", "farfield", "far_field", "fielddump", "dump"]):
                continue
            if "H500DIMER" not in line:
                continue
            for candidate in CANDIDATE_RE.findall(line):
                phase_bin = parse_phase_bin(line, candidate)
                if phase_bin not in PHASE_BINS:
                    continue
                key = (phase_bin, candidate)
                item = inventory.setdefault(key, CandidateInventory(phase_bin, candidate))
                item.source_files.add(rel)
                item.available_wavelengths_nm.update(infer_wavelengths_from_line(line, default_450_when_measured=True))
                item.evidence_order = max(item.evidence_order, order)
                if "stage11_lp_apcd_status_summary" in rel:
                    item.status_notes.add("frozen library/status report evidence")
                else:
                    item.status_notes.add("tracked lightweight text evidence")
    return inventory


def select_frozen_six(inventory: dict[tuple[int, str], CandidateInventory]) -> list[CandidateInventory]:
    rows = list(inventory.values())
    selected: list[CandidateInventory] = []
    for bin_deg in PHASE_BINS:
        candidates = [r for r in rows if r.phase_bin_deg == bin_deg]
        # Prefer explicit status report lines because outputs are intentionally excluded.
        candidates.sort(key=lambda r: ("frozen library/status report evidence" not in r.status_notes, -r.evidence_order, r.candidate_id))
        if candidates:
            selected.append(candidates[0])
        else:
            selected.append(CandidateInventory(bin_deg, "NOT_FOUND"))
    return selected


def markdown_table(rows: list[dict[str, str]]) -> str:
    headers = ["phase_bin_deg", "candidate_id", "available_wavelengths_nm", "missing_449_450_451_nm", "missing_448_449_450_451_452_nm", "source_files", "status"]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row[h].replace("|", "/") for h in headers) + " |")
    return "\n".join(lines)


def conclusion(rows: list[dict[str, str]]) -> str:
    statuses = {row["status"] for row in rows}
    if statuses == {"only 450 nm single-point data exists"}:
        return "Only single-wavelength 450 nm LP H500 data is available; true narrow-spectrum robustness cannot be concluded yet."
    if "confirmed multi-wavelength data exists" in statuses:
        return "Some tracked lightweight evidence indicates multi-wavelength data exists, but missing wavelengths still need inspection before claiming spectral robustness."
    return "No usable tracked lightweight spectral data was found; true narrow-spectrum robustness cannot be concluded yet."


def write_report(rows: list[dict[str, str]], file_count: int) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Stage11-3B0 LP H500 Spectral Data Inventory

## Scope
- Repo root inspected: `{REPO_ROOT}`
- Tracked lightweight files inspected: {file_count}
- Files/directories searched: {', '.join(SEARCH_ROOTS)}
- Files/directories intentionally excluded: {', '.join(EXCLUDED)}
- `outputs/` was not read or written in this Stage11-3B0 inventory.

## Frozen Six-bin Candidate Inventory
{markdown_table(rows)}

## Available Wavelength Table
{markdown_table(rows)}

## Missing Wavelength Table
{markdown_table(rows)}

## Minimal Rerun Plan
- First pass: periodic plane-wave Jones extraction at 449, 450, 451 nm.
- Second pass if needed: add 448 and 452 nm.
- Extended pass only after first-pass review: add 447 and 453 nm, or 450-456 nm if a deliberate long-wavelength-tail check is needed.

## Conclusion
{conclusion(rows)}

No FDTD was run, no `.fsp`/`.ldf` files were created, and no K=6/metagrating work was touched.
"""
    REPORT_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    paths = run_git_ls_files()
    inventory = collect_inventory(paths)
    selected = select_frozen_six(inventory)
    rows = [item.row() for item in selected]
    write_report(rows, len(paths))
    print(f"tracked_lightweight_files_inspected={len(paths)}")
    print(f"report={REPORT_PATH}")
    for row in rows:
        print(f"bin={row['phase_bin_deg']} candidate={row['candidate_id']} available={row['available_wavelengths_nm']} status={row['status']}")
    print(conclusion(rows))


if __name__ == "__main__":
    main()
