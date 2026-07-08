from pathlib import Path
import json
from datetime import datetime

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_defect_450")
summary_path = ROOT / "outputs" / "mdc1c1_rcwa_property_probe" / "mdc1c1_rcwa_property_probe_summary.json"
REPORT_DIR = ROOT / "reports" / "mdc_defect_450"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

if summary_path.exists():
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
else:
    summary = {
        "decision": "not_available_in_this_run",
        "rcwa_object_created": "unknown",
        "can_set_gaN_air_media": "unknown",
        "set_ok_properties": [],
    }

md = []
md.append("# MDC1C1 RCWA media-control negative probe\n")
md.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n")
md.append("## Scope\n")
md.append("Blank-project Lumerical RCWA property probe. No RCWA run, no FDTD, no FSP open/save.\n")
md.append("## Result\n")
md.append(f"- decision: `{summary.get('decision')}`")
md.append(f"- rcwa_object_created: `{summary.get('rcwa_object_created')}`")
md.append(f"- can_set_gaN_air_media: `{summary.get('can_set_gaN_air_media')}`")
md.append(f"- set_ok_properties: `{summary.get('set_ok_properties')}`\n")
md.append("## Decision\n")
md.append("Do not use the current Lumerical RCWA template for GaN -> MDC -> Air physical parity. The old axis-z RCWA route remains trusted for air/stack/air 1D stacks, but this probe did not identify reliable upper/lower GaN/Air medium controls.\n")
md.append("## Next\n")
md.append("Use FMMAX only as a minimal single-dipole sanity/closure check, then use 2D FDTD for center/side incoherent averaging.\n")

out = REPORT_DIR / "mdc1c1_rcwa_media_control_negative_decision.md"
out.write_text("\n".join(md), encoding="utf-8")
print(out)
