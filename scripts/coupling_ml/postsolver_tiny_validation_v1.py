"""Authorized vacuum-only infrastructure probes; production M2S is inaccessible here."""
from __future__ import annotations
import argparse,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
import psutil
from postsolver_persistence_v1 import (ArtifactRoles,LifecycleController,PreservationRequired,
                                     atomic_json,sha256_file,zero_solver_recover,inspect_durable_state,validated_completion,compatible_process_snapshot,durable_event)

ML=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
OUT=ML/'outputs/coupling_ml/POSTSOLVER_PERSISTENCE_INFRASTRUCTURE_REPAIR_V1'
API=Path(r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python')
SCHEDULER=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\scripts\coupling\apcd_global_fdtd_slot_v3.py')
sys.path.insert(0,str(API))
CONTRACT=dict(label='TINY_VACUUM_INFRASTRUCTURE_ONLY',source_name='tiny_source',source_z=-0.2e-6,
              monitor_name='tiny_monitor',monitor_z=0.2e-6,wavelength_start=590e-9,wavelength_stop=610e-9,
              x_span=0.6e-6,y_span=0.6e-6,z_span=1e-6,simulation_time=100e-15,frequency_points=3,
              processes=12,threads=1,production_science=False)

def slots():
    spec=importlib.util.spec_from_file_location('repair_canonical_slots',SCHEDULER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.GLOBAL_CAPACITY==3 and module.PROCESSES_PER_JOB==12 and module.THREADS_PER_JOB==1
    return module

def preflight():
    registry=Path(r'D:\project\apcd_global_fdtd_slot_registry_v3.json')
    active=json.loads(registry.read_text(encoding='utf-8-sig'))['active_slots']
    engines=[]
    for p in psutil.process_iter(['pid','name']):
        if (p.info['name'] or '').lower() in ['fdtd-engine-msmpi.exe','fdtd-engine.exe','fdtd-solutions.exe']:
            engines.append(p.info)
    return dict(active_slots=active,fdtd_processes=engines,registry_lock_exists=Path(str(registry)+'.lock').exists(),
                solver_entered_delta=0,manual_registry_edit=False)

def build_setup(root):
    import lumapi
    root.mkdir(parents=True,exist_ok=False)
    path=root/'setup.fsp'
    fd=lumapi.FDTD(hide=True)
    try:
        fd.addfdtd();fd.set('dimension','3D')
        for k in ['x','y','z']:fd.set(k,0)
        for k in ['x span','y span','z span']:fd.set(k,CONTRACT[k.replace(' ','_')])
        fd.set('mesh accuracy',1);fd.set('simulation time',CONTRACT['simulation_time'])
        for k in ['x min bc','x max bc','y min bc','y max bc']:fd.set(k,'Periodic')
        fd.set('z min bc','PML');fd.set('z max bc','PML')
        fd.addplane();fd.set('name','tiny_source');fd.set('injection axis','z-axis');fd.set('direction','Forward')
        fd.set('x',0);fd.set('y',0);fd.set('z',CONTRACT['source_z'])
        fd.set('x span',CONTRACT['x_span']);fd.set('y span',CONTRACT['y_span'])
        fd.set('wavelength start',CONTRACT['wavelength_start']);fd.set('wavelength stop',CONTRACT['wavelength_stop'])
        fd.addpower();fd.set('name','tiny_monitor');fd.set('monitor type','2D Z-normal')
        fd.set('x',0);fd.set('y',0);fd.set('z',CONTRACT['monitor_z'])
        fd.set('x span',CONTRACT['x_span']);fd.set('y span',CONTRACT['y_span'])
        fd.set('override global monitor settings',1);fd.set('frequency points',3)
        fd.save(str(path))
        atomic_json(root/'setup_audit.json',dict(run_called=False,contract=CONTRACT,setup_sha256=sha256_file(path)))
    finally:fd.close()
    return path

def read_arrays(fd):
    values={k:np.asarray(fd.getdata('tiny_monitor',k)) for k in ['x','y','z','f','Ex','Ey','Ez']}
    values['T']=np.asarray(fd.transmission('tiny_monitor'))
    return values

def validate(post,manifest):
    import lumapi
    fd=lumapi.FDTD(str(post),hide=True)
    try:
        values=read_arrays(fd)
        checks={}
        for obj,prop,expected in [('tiny_source','z',CONTRACT['source_z']),('tiny_source','wavelength start',CONTRACT['wavelength_start']),
                                  ('tiny_source','wavelength stop',CONTRACT['wavelength_stop']),('tiny_monitor','z',CONTRACT['monitor_z']),
                                  ('FDTD','x span',CONTRACT['x_span']),('FDTD','y span',CONTRACT['y_span']),('FDTD','z span',CONTRACT['z_span'])]:
            value=float(fd.getnamed(obj,prop));checks[obj+':'+prop]=dict(expected=expected,observed=value,pass_check=bool(np.isclose(value,expected,rtol=1e-8,atol=1e-15)))
        identity=all(c['pass_check'] for c in checks.values()) and manifest['contract']==CONTRACT
        finite=all(v.size>0 and np.isfinite(v).all() for v in values.values())
        shape=values['f'].size==3 and values['T'].size==3 and values['Ex'].size==values['x'].size*values['y'].size*values['z'].size*3
        sanity=finite and bool(np.all((values['T']>.8)&(values['T']<1.2)))
        return dict(ok=identity and shape and sanity,identity_pass=identity,arrays_pass=finite,shape_pass=shape,sanity_pass=sanity,
                    run_called=False,session_id='load-only-pid-'+str(os.getpid()),identity_readback=checks,
                    array_shapes={k:list(v.shape) for k,v in values.items()},T=values['T'].reshape(-1).tolist())
    finally:fd.close()

class Adapter:
    def __init__(self,root,mode):
        self.root,self.mode=Path(root),mode
        self.session_id='worker-'+str(os.getpid())
    def open(self,path):
        import lumapi
        fd=lumapi.FDTD(path,hide=True)
        owned=[p for p in psutil.Process().children() if p.name().lower()=='fdtd-solutions.exe']
        self.session_id='worker-%s/apps-%s'%(os.getpid(),','.join(str(p.pid)+':'+str(p.create_time()) for p in owned))
        fd.setresource('FDTD',1,'processes','12');fd.setresource('FDTD',1,'threads','1')
        readback={k:int(float(fd.getresource('FDTD',1,k))) for k in ['processes','threads']}
        if readback!={'processes':12,'threads':1}:raise RuntimeError('resource readback mismatch')
        atomic_json(self.root/'resource.json',readback)
        atomic_json(self.root/'telemetry.json',compatible_process_snapshot(slots()))
        barrier=self.root.parent/'synchronized_start.json'
        if barrier.is_file():
            expected=json.loads(barrier.read_text())['count']
            atomic_json(self.root/'app_ready.json',dict(pid=os.getpid(),session=self.session_id))
            deadline=time.monotonic()+120
            while len(list(self.root.parent.glob('job_*/app_ready.json')))<expected:
                if time.monotonic()>deadline:
                    fd.close()
                    raise RuntimeError('PRE_ENTRY_APP_READY_BARRIER_TIMEOUT')
                time.sleep(1)
        return fd
    def run(self,fd):fd.run()
    def save(self,fd,path):
        if self.mode=='save_failure' and Path(path).name=='canonical.fsp':
            raise PermissionError('CONTROLLED_SAVE_EXCEPTION_BEFORE_NATIVE_SAVE_IN_SANDBOX')
        fd.save(path)
    def rescue_save(self,fd,path):fd.save(path)
    def live_results_available(self,fd):
        import lumapi
        return bool(lumapi.verifyConnection(fd.handle)) and bool(np.asarray(fd.getdata('tiny_monitor','Ex')).size)
    def load_only(self,path,manifest):
        request=self.root/'validation_request.json';atomic_json(request,manifest)
        output=self.root/'validation_proof.json'
        r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--validate',path,'--manifest',str(request),'--proof',str(output)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        if r.returncode:raise RuntimeError('LOAD-only subprocess failed: '+r.stderr.decode(errors='replace')[-2000:])
        return json.loads(output.read_text())
    def extract_raw(self,fd,post,raw):np.savez_compressed(raw,**read_arrays(fd))
    def extract_raw_from_post(self,post,raw):
        import lumapi
        fd=lumapi.FDTD(post,hide=True)
        try:np.savez_compressed(raw,**read_arrays(fd))
        finally:fd.close()
    def close(self,fd):fd.close()

def derive(raw):
    with np.load(raw,allow_pickle=False) as d:
        values=np.asarray(d['T']).reshape(-1)
        return dict(T=values.tolist(),points=int(values.size),finite=bool(np.isfinite(values).all()))

def audit(d,post,raw):
    return dict(pass_check=d['finite'] and d['points']==3 and all(.8<x<1.2 for x in d['T']),
                **{'pass':d['finite'] and d['points']==3 and all(.8<x<1.2 for x in d['T'])})

def worker(group,job,mode):
    root=OUT/group/job
    if root.exists():raise RuntimeError('existing validation job: no replay')
    s=slots();scheduler=s.GlobalSlotScheduler()
    lease=scheduler.acquire_wait('work/mdc-np-coupling-ml-v1',str(ML),'POSTSOLVER_PERSISTENCE_INFRASTRUCTURE_REPAIR_V1',group+'_'+job,pid=os.getpid(),timeout_s=60,poll_s=2)
    lease.start_heartbeat(interval_s=600)
    root.mkdir(parents=True,exist_ok=False)
    setup=OUT/group/'setup/setup.fsp'
    adapter=Adapter(root,mode)
    roles=ArtifactRoles(root/'frozen.fsp',root/'runtime.fsp',root/'canonical.fsp',root/'recovery.fsp')
    def release(reason):
        # Call the canonical transaction directly: legacy SlotLease sets _released before I/O success.
        scheduler.release(lease,reason)
        lease.stop_heartbeat();lease._released=True
        atomic_json(root/'slot_release.json',dict(slot_id=lease.slot_id,state=reason,canonical=True))
    c=LifecycleController(job_id=job,attempt_id='attempt_001',roles=roles,events_path=root/'events.jsonl',completion_path=root/'completion.json',raw_path=root/'raw.npz',release_slot=release,on_solver_entered=lease.mark_solver_entered,save_timeout_s=60)
    manifest=dict(job_id=job,setup_pre_fsp=str(setup),contract=CONTRACT,
                  runner_sha256=sha256_file(Path(__file__)),helper_sha256=sha256_file(Path(__file__).with_name('postsolver_persistence_v1.py')),
                  scheduler_sha256=sha256_file(SCHEDULER))
    def parser(raw):
        if mode=='parser_failure':raise ValueError('CONTROLLED_DOWNSTREAM_PARSER_FAILURE')
        return derive(raw)
    try:
        result=c.execute(adapter,manifest,adapter.extract_raw,parser,audit)
    except PreservationRequired:
        atomic_json(root/'PRESERVATION_REQUIRED.json',dict(state='RETAIN_SESSION_AND_SLOT',pid=os.getpid()))
        # This process is deliberately retained: automatic process exit would destroy unsaved truth.
        while True:time.sleep(600)
    except ValueError:
        if mode!='parser_failure':raise
        result=zero_solver_recover(job_id=job,attempt_id='attempt_001_zero_solver_recovery',events_path=root/'recovery_events.jsonl',post_fsp=c.persisted_artifact,raw_path=root/'recovered_raw.npz',completion_path=root/'recovered_completion.json',adapter=adapter,manifest=manifest,extract_raw=adapter.extract_raw,derive=derive,audit=audit,expected_post_sha256=c.persisted_sha256,original_solver_returned=c.solver_returned)
    print(json.dumps(dict(job_id=job,status=result['status'],post=result.get('post_fsp')),sort_keys=True),flush=True)
    return 0

def campaign(group,count,mode,synchronize=False):
    if count not in [1,2,3]:raise RuntimeError('only 1/2/3 slots authorized')
    if not group.replace('_','').isalnum():raise RuntimeError('invalid group id')
    root=OUT/group
    if root.exists():raise RuntimeError('campaign output exists')
    root.mkdir(parents=True)
    before=preflight();atomic_json(root/'preflight.json',before)
    if before['active_slots'] or before['fdtd_processes']:raise RuntimeError('existing FDTD activity; no new probe dispatch')
    build_setup(root/'setup')
    if synchronize:atomic_json(root/'synchronized_start.json',dict(count=count))
    running=[]
    for i in range(count):
        job='job_%02d'%(i+1)
        stdout=(root/(job+'.stdout.log')).open('wb');stderr=(root/(job+'.stderr.log')).open('wb')
        p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',job,'--group',group,'--mode',mode],stdout=stdout,stderr=stderr)
        running.append((job,p,stdout,stderr))
    results=[]
    last={};heartbeat=time.monotonic()
    # Observe durable handshakes while workers are alive; never cancel their native calls.
    while any(p.poll() is None for _,p,_,_ in running):
        observed={}
        for job,p,_,_ in running:
            ledger=root/job/'events.jsonl';log=root/job/'runtime_p0.log'
            engine_completed=log.is_file() and 'Simulation completed successfully' in log.read_text(errors='replace')
            state=inspect_durable_state(ledger,worker_alive=p.poll() is None,engine_completed=engine_completed) if ledger.exists() else {'classification':'PRE_ENTRY','complete':False}
            observed[job]=dict(worker_pid=p.pid,worker_alive=p.poll() is None,**state)
            if last.get(job)!=observed[job]:
                durable_event(root/'controller_events.jsonl',job_id=job,attempt_id='attempt_001',worker_pid=p.pid,
                              controller_pid=os.getpid(),state=state['classification'],extra={'worker_alive':p.poll() is None})
        if observed!=last or time.monotonic()-heartbeat>=600:
            atomic_json(root/'controller_status.json',observed);last=observed;heartbeat=time.monotonic()
        time.sleep(1)
    for job,p,stdout,stderr in running:
        code=p.wait();stdout.close();stderr.close()
        state=inspect_durable_state(root/job/'events.jsonl')
        recovery=root/job/'recovered_completion.json'
        accepted=False
        if state['complete']:
            validated_completion(root/job/'events.jsonl',root/job/'completion.json');accepted=True
        if mode=='parser_failure' and recovery.is_file():
            r=json.loads(recovery.read_text());accepted=r['status']=='COMPLETED' and r['run_invocation_count']==0 and sha256_file(r['post_fsp'])==r['post_fsp_sha256']
        passed=code==0 and accepted
        results.append(dict(job_id=job,returncode=code,passed=passed,durable_state=state,zero_solver_recovery=recovery.is_file()))
    after=preflight();atomic_json(root/'final_registry.json',after)
    atomic_json(root/'campaign.json',dict(group=group,count=count,mode=mode,results=results,passed=all(r['passed'] for r in results) and not after['active_slots']))
    print(json.dumps(results),flush=True)
    return 0 if all(r['passed'] for r in results) and not after['active_slots'] else 1

def main():
    p=argparse.ArgumentParser();p.add_argument('--group');p.add_argument('--worker');p.add_argument('--count',type=int,default=1);p.add_argument('--mode',default='normal',choices=['normal','save_failure','parser_failure']);p.add_argument('--validate');p.add_argument('--manifest');p.add_argument('--proof');p.add_argument('--synchronize',action='store_true')
    a=p.parse_args()
    if a.validate:
        atomic_json(a.proof,validate(a.validate,json.loads(Path(a.manifest).read_text())));return 0
    if a.worker:return worker(a.group,a.worker,a.mode)
    return campaign(a.group,a.count,a.mode,a.synchronize)

if __name__=='__main__':raise SystemExit(main())
