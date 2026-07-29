import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d2_corrected_direction_spotcheck_v1'
def main():
 b=json.loads((O/'solver_budget_audit.json').read_text());p=json.loads((O/'post_fsp_checksums.json').read_text());assert b['exactly_seven'] and len(p)==7;print('SPOTCHECK_RECOVERY_VALIDATION_PASS')
if __name__=='__main__':main()
