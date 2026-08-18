from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python')
import lumapi

def inspect(path, expected):
    f=None
    try:
        f=lumapi.FDTD(hide=True)
        f.load(str(path))
        objects=f.getobjectlist('::model::')
        missing=[x for x in expected if x not in objects]
        if missing: raise RuntimeError('MISSING_OBJECTS:'+','.join(missing))
        return {'path':str(path),'object_count':len(objects),'required_objects':expected,'pass':True}
    finally:
        if f is not None:f.close()

def main():
    lp=ROOT/'runtime/reusable_fsp/lp/P1_LP_H1C1B_V2_009_Px_attempt_006_pre.fsp'
    cp=ROOT/'runtime/reusable_fsp/cp/CP_NATIVE_M1_CENTER_XY_setup_prepared_not_run.fsp'
    results={
      'LP':inspect(lp,['::model::FDTD::','::model::pillar_1','::model::pillar_2','::model::source','::model::T','::model::field_monitor']),
      'CP':inspect(cp,['::model::FDTD::','::model::GaN_continuous_block_zprop_extends_into_bottom_PML','::model::route_b2_x_dipole_zprop','::model::route_b2_y_dipole_zprop','::model::top_field_monitor_zprop','::model::top_power_monitor_zprop'])
    }
    out=ROOT/'reports/lumerical_template_load_inspect.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'status':'PASS','mode':'LOAD_INSPECT_ONLY','solver_run_called':False,'results':results},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','solver_run_called':False,'templates':list(results)}))
if __name__=='__main__':main()
