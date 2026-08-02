import csv,json,hashlib
from pathlib import Path
def main():
 r=Path(__file__).resolve().parents[1]; e=r/"outputs"/"np_k6_p1d4b_k6x_run3c_n1_conformal_variant1_diagnostic_v1"
 ck=json.loads((e/"conformal_v1_post_fsp_checksum.json").read_text()); assert ck["independent_readonly_reload"] and len(ck["sha256"])==64
 led=json.loads((e/"entered_ledger.json").read_text()); assert led["entered"] and led["engine_completed"] and led["post_saved"] and led["controller_returned"]
 pre=json.loads((e/"conformal_v1_diagnostic_preflight.json").read_text()); assert pre["checks"]["preflight_pass"] and pre["checks"]["only_mesh_refinement_changed"]
 cls=json.loads((e/"conformal_variant1_diagnostic_classification.json").read_text()); assert cls["classification"]=="CONFORMAL_VARIANT1_NO_EFFECT" and cls["next_setup_only_sha256"]
 rows=list(csv.DictReader((e/"conformal_v0_vs_v1_spectral_metrics.csv").open())); assert len(rows)==11 and max(abs(float(x["delta_T"])) for x in rows)<=1e-12 and max(abs(float(x["delta_R"])) for x in rows)<=1e-12
 print("PASS conformal variant1 validator")
if __name__=="__main__": main()
