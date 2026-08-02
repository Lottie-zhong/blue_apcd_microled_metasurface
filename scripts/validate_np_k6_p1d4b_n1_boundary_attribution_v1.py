import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];O=ROOT/"outputs"/"np_k6_p1d4b_k6x_run3c_n1_boundary_attribution_v1"
def main():
 r=list(csv.DictReader((O/"n1_445_455_closure_shape.csv").open()));x=next(q for q in r if float(q["wavelength_nm"])==449);c=json.loads((O/"diagnostic_decision.json").read_text());p=json.loads((O/"diagnostic_prefsp_checksum.json").read_text())
 assert abs(float(x["residual_signed"]))>0.05
 assert c["status"]=="READY_FOR_RUN3C_N1_MINIMAL_BOUNDARY_DIAGNOSTIC_AUTHORIZATION" and p["sha256"]
 print("PASS boundary validator")
if __name__=="__main__":main()
