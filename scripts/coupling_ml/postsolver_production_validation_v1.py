"""Build tiny inputs, then invoke the existing production controller CLI. No worker/helper execution here."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
import m2s_coupling_source_lateral_robustness_controller_v1 as production
from coupling_fdtd_adapter_v1 import lumapi_module
from postsolver_persistence_v1 import atomic_json,sha256_file

def build_fixture(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    wavelengths=[445,450,455]
    contract=dict(case_id='TINY_DIPOLE_INFRASTRUCTURE',scientific_scope='VACUUM_INFRASTRUCTURE_ONLY',
        domain=dict(x_span_nm=600.,y_span_nm=600.,z_min_nm=-500.,z_max_nm=500.,boundaries={k:'PML' for k in ['x_min','x_max','y_min','y_max','z_min','z_max']}),
        source=dict(position_nm={'x':0.,'y':0.,'z':-150.},theta_deg=90.,phi_deg=0.,amplitude=1.,phase_deg=0.),
        reference_plane=dict(z_nm=150.,x_span_nm=400.,y_span_nm=400.),wavelength_grid_nm=wavelengths)
    contract['physical_contract_hash']=production.digest(contract)
    path=directory/'setup.fsp';fd=lumapi_module().FDTD(hide=True)
    try:
        fd.addfdtd();fd.set('dimension','3D');fd.set('x',0);fd.set('y',0);fd.set('z',0)
        fd.set('x span',600e-9);fd.set('y span',600e-9);fd.set('z span',1000e-9)
        fd.set('mesh accuracy',1);fd.set('simulation time',100e-15)
        for k in contract['domain']['boundaries']:fd.set(k.replace('_',' ')+' bc','PML')
        fd.adddipole()
        for k,v in dict(name='source_dipole',x=0,y=0,z=-150e-9,theta=90,phi=0,amplitude=1,phase=0).items():fd.set(k,v)
        fd.set('wavelength start',445e-9);fd.set('wavelength stop',455e-9)
        fd.addpower()
        for k,v in {'name':'source_interface_complex','monitor type':'2D Z-normal','x':0,'y':0,'z':150e-9,'x span':400e-9,'y span':400e-9,'override global monitor settings':1,'use wavelength spacing':True,'frequency points':3}.items():fd.set(k,v)
        fd.save(str(path))
    finally:fd.close()
    atomic_json(directory/'physical_contract.json',contract)
    atomic_json(directory/'setup_audit.json',dict(run_called=False,setup_sha256=sha256_file(path),physical_contract_sha256=sha256_file(directory/'physical_contract.json')))
    return path,directory/'physical_contract.json',production.production_validation(contract)

def prepare(group,count,mode):
    if not group.replace('_','').isalnum() or count not in [1,2,3]:raise ValueError('invalid group/count')
    stage=production.INTEGRATION;config_path=stage/(group+'.execution.json')
    if config_path.exists() or (stage/group).exists():raise ValueError('existing group: no replay')
    setup,contract,validation=build_fixture(stage/(group+'_fixture'))
    jobs=[dict(job_id='job_%02d'%(i+1),attempt_id='attempt_001',setup_pre_fsp=str(setup),setup_sha256=sha256_file(setup),physical_contract_path=str(contract),physical_contract_sha256=sha256_file(contract),validation=validation) for i in range(count)]
    config=dict(schema='M2S_PERSISTENCE_EXECUTION_V1',purpose='TINY_INFRASTRUCTURE_VALIDATION',campaign_id=group,root=str(stage/group),jobs=jobs,injection=mode,synchronize=count>1,code_sha256=production.code_identity())
    config['manifest_sha256']=production.digest(config);atomic_json(config_path,config)
    return config_path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--group',required=True);parser.add_argument('--count',type=int,default=1);parser.add_argument('--injection',default='none',choices=['none','save_failure','parser_failure','session_loss','telemetry_failure']);args=parser.parse_args()
    config=prepare(args.group,args.count,args.injection)
    # Exactly the production entrypoint; no helper.execute or alternate worker exists in this harness.
    return subprocess.call([sys.executable,str(production.ENTRYPOINT),'--campaign','--manifest',str(config)])

if __name__=='__main__':raise SystemExit(main())
