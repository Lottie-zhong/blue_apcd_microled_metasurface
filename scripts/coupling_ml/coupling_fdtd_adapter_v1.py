"""FDTD adapter used by the M2S production worker for every execution profile."""
from __future__ import annotations
import json,os,subprocess,sys,threading,time
from pathlib import Path
import numpy as np
import psutil
from postsolver_persistence_v1 import atomic_json,durable_event,sha256_file,LifecycleError

API=Path(r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python')
FIELDS=('Ex','Ey','Ez','Hx','Hy','Hz')
COORDINATES=('x','y','z','f')

class AppSessionFailure(LifecycleError):
    error_class='APP_SESSION_FAILURE'

def lumapi_module():
    if str(API) not in sys.path:sys.path.insert(0,str(API))
    import lumapi
    return lumapi

def identity_readback(fd,spec):
    checks=[]
    for obj,prop,expected in spec['identity']:
        value=fd.getnamed(obj,prop)
        if isinstance(expected,str):value=str(value);passed=value==expected
        else:
            value=float(np.asarray(value).reshape(-1)[0])
            passed=bool(np.isclose(value,expected,rtol=1e-8,atol=1e-15))
        checks.append(dict(object=obj,property=prop,expected=expected,observed=value,passed=passed))
    return checks

def read_arrays(fd,spec):
    arrays={k:np.asarray(fd.getdata(spec['monitor'],k)) for k in COORDINATES+FIELDS}
    frequency=np.asarray(arrays['f']).reshape(-1)
    arrays['dipolepower']=np.asarray(fd.dipolepower(frequency))
    try:arrays['sourcepower']=np.asarray(fd.sourcepower(frequency))
    except Exception:pass
    return arrays

def array_audit(arrays,spec):
    sizes=[arrays[k].size for k in COORDINATES]
    finite=all(arrays[k].size and np.isfinite(arrays[k]).all() for k in COORDINATES+FIELDS+('dipolepower',))
    shape=sizes[-1]==spec['frequency_points'] and sizes[2]==1 and all(arrays[k].size==int(np.prod(sizes)) for k in FIELDS)
    frequencies=arrays['f'].reshape(-1)
    wavelength_ok=bool(np.allclose(299792458./frequencies*1e9,spec['wavelengths_nm'],rtol=1e-7,atol=1e-6))
    power=arrays['dipolepower'].reshape(-1)
    sanity=bool(finite and power.size==sizes[-1] and np.all(power>0) and any(np.any(np.abs(arrays[k])>0) for k in FIELDS[:3]) and wavelength_ok)
    return dict(arrays_pass=bool(finite),shape_pass=bool(shape),sanity_pass=sanity,
                array_shapes={k:list(v.shape) for k,v in arrays.items()},wavelengths_nm=(299792458./frequencies*1e9).tolist())

def validate_file(post,manifest):
    """Independent process, new session, LOAD only; this function has no run path."""
    lumapi=lumapi_module();fd=lumapi.FDTD(str(post),hide=True)
    try:
        checks=identity_readback(fd,manifest['validation'])
        results=array_audit(read_arrays(fd,manifest['validation']),manifest['validation'])
        identity=bool(checks) and all(c['passed'] for c in checks)
        return dict(ok=identity and all(results[k] for k in ['arrays_pass','shape_pass','sanity_pass']),
                    identity_pass=identity,run_called=False,session_id='load-only-pid-'+str(os.getpid()),
                    identity_readback=checks,post_sha256=sha256_file(post),**results)
    finally:fd.close()

class FDTDAdapter:
    def __init__(self,root,manifest,entrypoint):
        self.root=Path(root);self.manifest=manifest;self.entrypoint=Path(entrypoint)
        self.mode=manifest.get('injection','none');self.owner_thread=threading.get_ident()
        self.session_id=None;self.app_processes=[];self.loss_injected=False
    def event(self,state,**kwargs):
        durable_event(self.root/'adapter_events.jsonl',job_id=self.manifest['job_id'],attempt_id=self.manifest['attempt_id'],
                      session_id=self.session_id,state=state,**kwargs)
    def connected(self,fd):
        if threading.get_ident()!=self.owner_thread:raise AppSessionFailure('native API called outside owner thread')
        if fd is None or not lumapi_module().verifyConnection(fd.handle):raise AppSessionFailure('application connection unavailable')
    def open(self,path):
        fd=lumapi_module().FDTD(path,hide=True)
        self.app_processes=[dict(pid=p.pid,created=p.create_time()) for p in psutil.Process().children() if p.name().lower()=='fdtd-solutions.exe']
        if len(self.app_processes)!=1:
            fd.close();raise AppSessionFailure('worker application ownership is not unique')
        self.session_id='worker-%s/app-%s@%s'%(os.getpid(),self.app_processes[0]['pid'],self.app_processes[0]['created'])
        # A failed setup check closes only this pre-entry session.
        try:
            self.connected(fd)
            fd.setresource('FDTD',1,'processes','12');fd.setresource('FDTD',1,'threads','1')
            resource={k:int(float(fd.getresource('FDTD',1,k))) for k in ['processes','threads']}
            if resource!={'processes':12,'threads':1}:raise LifecycleError('production resource readback mismatch')
            checks=identity_readback(fd,self.manifest['validation'])
            if not checks or not all(c['passed'] for c in checks):raise LifecycleError('setup identity readback mismatch')
            if self.manifest['purpose']=='TINY_INFRASTRUCTURE_VALIDATION':
                if any(float(fd.getnamed('FDTD',k))>2e-6 for k in ['x span','y span','z span']) or float(fd.getnamed('FDTD','simulation time'))>1e-12:
                    raise LifecycleError('tiny sandbox physical size/time ceiling exceeded')
            atomic_json(self.root/'app_identity.json',dict(worker_pid=os.getpid(),session_id=self.session_id,apps=self.app_processes,resource=resource,setup_identity=checks,lumapi_path=str(API/'lumapi.py'),lumapi_sha256=sha256_file(API/'lumapi.py')))
            self.event('APP_OWNER_BOUND')
            if self.manifest.get('barrier_count',1)>1:
                atomic_json(self.root/'ready.json',dict(worker_pid=os.getpid(),session_id=self.session_id))
                deadline=time.monotonic()+120
                while len(list(self.root.parent.glob('*/ready.json')))<self.manifest['barrier_count']:
                    if time.monotonic()>deadline:raise LifecycleError('pre-entry barrier timeout')
                    time.sleep(1)
            return fd
        except BaseException:
            fd.close();raise
    def run(self,fd):
        self.connected(fd);fd.run()
        if self.mode=='session_loss':
            self.event('INJECTED_PRE_PERSISTENCE_SESSION_LOSS',recovery_action='explicit sandbox fail-safe test')
            fd.close();self.loss_injected=True
    def save(self,fd,path):
        self.connected(fd)
        if self.mode=='save_failure' and Path(path).name=='canonical.fsp':
            raise PermissionError('CONTROLLED_CANONICAL_SAVE_FAILURE_BEFORE_NATIVE_CALL')
        fd.save(path)
    def rescue_save(self,fd,path):self.connected(fd);fd.save(path)
    def live_results_available(self,fd):
        self.connected(fd)
        return bool(np.asarray(fd.getdata(self.manifest['validation']['monitor'],'Ex')).size)
    def load_only(self,path,manifest):
        request=self.root/'validation_request.json';proof=self.root/'validation_proof.json'
        atomic_json(request,manifest)
        command=[sys.executable,str(self.entrypoint),'--load-only',str(path),'--job-manifest',str(request),'--proof',str(proof)]
        r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        if r.returncode:raise LifecycleError('independent LOAD-only failed: '+r.stderr.decode(errors='replace')[-1500:])
        return json.loads(proof.read_text())
    def extract_raw(self,fd,post,raw):
        self.connected(fd);arrays=read_arrays(fd,self.manifest['validation'])
        np.savez_compressed(raw,**arrays)
        atomic_json(Path(raw).with_suffix('.metadata.json'),dict(monitor=self.manifest['validation']['monitor'],array_shapes={k:list(v.shape) for k,v in arrays.items()},unmodified_complex_arrays=True,no_interpolation=True,dipolepower_authoritative=True,post_fsp=str(post),post_sha256=sha256_file(post),raw_sha256=sha256_file(raw)))
    def extract_raw_from_post(self,post,raw):
        fd=lumapi_module().FDTD(post,hide=True)
        try:self.extract_raw(fd,post,raw)
        finally:fd.close()
    def close(self,fd):
        self.event('APP_CLOSE_REQUESTED');fd.close();self.event('APP_CLOSE_COMPLETED')
    def processes_absent(self):
        for row in self.app_processes:
            try:
                if abs(psutil.Process(row['pid']).create_time()-row['created'])<.01:return False
            except psutil.NoSuchProcess:pass
        # Engine launchers can be outside the Python child tree on Windows MPI.
        runtime=str(self.root/'runtime.fsp').lower()
        for p in psutil.process_iter(['name','cmdline']):
            if (p.info['name'] or '').lower() in ['fdtd-engine-msmpi.exe','fdtd-engine.exe'] and runtime in ' '.join(p.info['cmdline'] or []).lower():return False
        return bool(self.app_processes)

def derive_raw(raw,spec):
    with np.load(raw,allow_pickle=False) as data:
        arrays={k:data[k] for k in data.files};check=array_audit(arrays,spec)
        if not all(check[k] for k in ['arrays_pass','shape_pass','sanity_pass']):raise LifecycleError('raw scientific shape/sanity validation failed')
        shape=tuple(arrays[k].size for k in COORDINATES)
        field={k:arrays[k].reshape(shape) for k in FIELDS}
        pz=.5*np.real(field['Ex']*np.conj(field['Hy'])-field['Ey']*np.conj(field['Hx']))[:,:,0,:]
        flux=np.trapz(np.trapz(pz,arrays['y'].reshape(-1),axis=1),arrays['x'].reshape(-1),axis=0)
        ratio=flux/arrays['dipolepower'].reshape(-1)
        return dict(**check,plane_flux_over_dipolepower=ratio.tolist(),finite_derived=bool(np.isfinite(ratio).all()),
                    scientific_scope='source-plane numerical serialization and direct Poynting integral; no Bloch projection')

def audit_raw(derived,post,raw):
    return {'pass':all(derived[k] for k in ['arrays_pass','shape_pass','sanity_pass','finite_derived']),
            'post_exists':Path(post).is_file(),'raw_exists':Path(raw).is_file()}
