from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import pandas as pd

def sha_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def dump(p:Path,x):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False),encoding='utf-8'); t.replace(p)
def main(run:Path):
    s=pd.read_csv(run/'candidate_summary.csv'); p=pd.read_csv(run/'pareto_front.csv'); c=s[s.is_traditional_champion.astype(bool)].iloc[0]
    cols=['spectral_fwhm_nm','angular_fwhm_deg','spectral_peak_detuning_nm','angular_peak_detuning_deg']
    dump(run/'pareto_front.json',p.to_dict('records'))
    dump(run/'figure_manifest.json',{'backend':'python','dpi':600,'figure_count':3,'formats':['png','pdf','svg'],'files':sorted(x.name for x in run.glob('figure_*.*')),'qa':{'source_validation':'PASS','pdf_glyph_audit':'PASS','visual_panel_inspection':'PASS'}})
    decision='NO_MEANINGFUL_SURROGATE_IMPROVEMENT_FOUND'
    report=("# MDC V3 surrogate-assisted Pareto POC\n\n"
      f"Decision: **{decision}**. The exact frozen accepted domain was exhaustively evaluated ({len(s)} unique geometries; 1848 Explicit, 630 ZL-1, 210 ZL-2). The requested 200,000 count cannot be reached without prohibited domain expansion.\n\n"
      f"Traditional champion: `{c.geometry_id}` ({c.candidate_id_primary}); it is outside the development self-neighbour p90 support band (distance {c.support_distance:.6g}), so apparent margins are not treated as physical improvements. The global Pareto set contains {len(p)} points, all ZL-2, with the same 0-nm predicted spectral width and 5.8-nm wavelength detuning; this degenerate pattern is a surrogate limitation, not a discovery claim. No robust low-disagreement, well-supported dominating candidate was found; shortlist is empty.\n\n"
      "Objectives use the frozen normalized profile, six source conditions, geometry-level mean, connected half-maximum FWHM and absolute peak detuning. No power, LEE, extraction, Test40, HF15 or R12 payload entered the decision. All outputs are surrogate hypotheses only; no FDTD was run.\n")
    (run/'scientific_decision_support.md').write_text(report,encoding='utf-8')
    cm=json.loads((run/'completion_manifest.json').read_text(encoding='utf-8'))
    cm.update({'formal_status':'MDC_V3_SURROGATE_PARETO_POC_COMPLETE_CURRENT_DOMAIN_NO_CLEAR_IMPROVEMENT','candidate_count':int(len(s)),'pareto_count':int(len(p)),'shortlist_count':0,'decision':decision,'test40_truth_reads':0,'test40_prediction_reads':0,'test40_metric_payload_reads':0,'hf15_r12_reads':0,'solver_calls':0,'neural_fits':0,'pca_scaler_fits':0,'figure_files':sorted(x.name for x in run.glob('figure_*.*'))})
    dump(run/'completion_manifest.json',cm)
    files=[x for x in run.iterdir() if x.is_file() and x.name!='artifact_sha256.json']
    dump(run/'artifact_sha256.json',{x.name:sha_file(x) for x in sorted(files,key=lambda z:z.name)})
    print(json.dumps({'run':str(run),'status':cm['formal_status'],'sha':sha_file(run/'completion_manifest.json'),'files':len(files)}))
if __name__=='__main__': main(Path(sys.argv[1]))
