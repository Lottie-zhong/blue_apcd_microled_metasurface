"""Windows consumer identity. Credentials remain machine-DPAPI protected behind private NTFS ACL, never returned.

The custodian owns credentials and starts only a write-restricted non-admin token.
This isolates ordinary consumers, not a malicious Windows administrator.
"""
import ctypes as C
from ctypes import wintypes as W
import json
import os
import secrets
import subprocess
from pathlib import Path

ACCOUNT = 'apcd_v3_consumer'


class Blob(C.Structure):
    _fields_ = [('size', W.DWORD), ('data', C.POINTER(C.c_ubyte))]


class SidAttributes(C.Structure):
    _fields_ = [('sid', C.c_void_p), ('attributes', W.DWORD)]


class Startup(C.Structure):
    _fields_ = [('cb', W.DWORD), ('reserved', W.LPWSTR), ('desktop', W.LPWSTR),
               ('title', W.LPWSTR), ('x', W.DWORD), ('y', W.DWORD),
               ('xsize', W.DWORD), ('ysize', W.DWORD), ('xchars', W.DWORD),
               ('ychars', W.DWORD), ('fill', W.DWORD), ('flags', W.DWORD),
               ('show', W.WORD), ('reserved2', W.WORD), ('reservedptr', C.c_void_p),
               ('stdin', W.HANDLE), ('stdout', W.HANDLE), ('stderr', W.HANDLE)]


class ProcessInfo(C.Structure):
    _fields_ = [('process', W.HANDLE), ('thread', W.HANDLE),
               ('pid', W.DWORD), ('tid', W.DWORD)]


def dll(name):
    if os.name != 'nt':
        raise RuntimeError('WINDOWS_IDENTITY_REQUIRED')
    return C.WinDLL(name, use_last_error=True)


def check(result):
    if not result:
        raise C.WinError(C.get_last_error())
    return result


def protect(data, *, decrypt=False):
    crypt = dll('crypt32'); kernel = dll('kernel32')
    raw = C.create_string_buffer(data)
    incoming = Blob(len(data), C.cast(raw, C.POINTER(C.c_ubyte)))
    outgoing = Blob()
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    check(fn(C.byref(incoming), None, None, None, None, (1 if decrypt else 5), C.byref(outgoing)))
    try:
        return C.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree.argtypes = [C.c_void_p]
        kernel.LocalFree(outgoing.data)


def token_data(token, info):
    adv = dll('advapi32'); length = W.DWORD()
    adv.GetTokenInformation.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
    adv.GetTokenInformation(token, info, None, 0, C.byref(length))
    buf = C.create_string_buffer(length.value)
    check(adv.GetTokenInformation(token, info, buf, length.value, C.byref(length)))
    return buf


def sid_text(sid):
    adv = dll('advapi32'); text = W.LPWSTR()
    adv.ConvertSidToStringSidW.argtypes = [C.c_void_p, C.POINTER(W.LPWSTR)]
    check(adv.ConvertSidToStringSidW(sid, C.byref(text)))
    try:
        return text.value
    finally:
        k = dll('kernel32'); k.LocalFree.argtypes = [C.c_void_p]; k.LocalFree(text)


def current_token_evidence():
    adv = dll('advapi32'); k = dll('kernel32'); token = W.HANDLE()
    k.GetCurrentProcess.restype = W.HANDLE
    adv.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
    check(adv.OpenProcessToken(k.GetCurrentProcess(), 8, C.byref(token)))
    try:
        user = token_data(token, 1); group = token_data(token, 2)
        sid = C.cast(user, C.POINTER(SidAttributes)).contents.sid
        restricted = token_data(token, 11)
        count = C.cast(restricted, C.POINTER(W.DWORD)).contents.value
        elevation = token_data(token, 20)
        name = C.create_unicode_buffer(256); size = W.DWORD(256)
        check(adv.GetUserNameW(name, C.byref(size)))
        groups = []; n = C.cast(group, C.POINTER(W.DWORD)).contents.value
        offset = C.sizeof(C.c_void_p)
        array = C.cast(C.addressof(group)+offset, C.POINTER(SidAttributes))
        for i in range(n): groups.append(dict(sid=sid_text(array[i].sid), attributes=array[i].attributes))
        integrity = token_data(token, 25)
        integrity_sid = C.cast(integrity, C.POINTER(SidAttributes)).contents.sid
        return dict(user_sid=sid_text(sid), restricted_sid_count=count,
                    elevated=bool(C.cast(elevation, C.POINTER(W.DWORD)).contents.value),
                    identity=name.value, groups=groups, integrity_sid=sid_text(integrity_sid),
                    privileges_raw_hex=token_data(token,3).raw.hex(), pid=os.getpid())
    finally:
        k.CloseHandle.argtypes = [W.HANDLE]; k.CloseHandle(token)


def logon(secret_path):
    data = json.loads(protect(Path(secret_path).read_bytes(), decrypt=True))
    if data.get('account') != ACCOUNT or not isinstance(data.get('password'),str):
        raise RuntimeError('OWNED_CONSUMER_CREDENTIAL_IDENTITY_MISMATCH')
    adv = dll('advapi32'); token = W.HANDLE()
    adv.LogonUserW.argtypes = [W.LPCWSTR, W.LPCWSTR, W.LPCWSTR, W.DWORD, W.DWORD, C.POINTER(W.HANDLE)]
    check(adv.LogonUserW(data['account'], '.', data['password'], 2, 0, C.byref(token)))
    data.clear()
    return token


def provision(secret_path):
    """Exactly one named account; caller must preprotect the private directory."""
    path = Path(secret_path)
    if path.exists():
        token = logon(path)
        user = token_data(token, 1)
        sid = sid_text(C.cast(user, C.POINTER(SidAttributes)).contents.sid)
        k = dll('kernel32'); k.CloseHandle.argtypes = [W.HANDLE]; k.CloseHandle(token)
        return dict(account=ACCOUNT, sid=sid, existing_owned_credential=True)
    # Refuse adopting any unrelated existing account with this name.
    net = dll('netapi32'); ptr = C.c_void_p()
    net.NetUserGetInfo.argtypes = [W.LPCWSTR, W.LPCWSTR, W.DWORD, C.POINTER(C.c_void_p)]
    status = net.NetUserGetInfo(None, ACCOUNT, 0, C.byref(ptr))
    if status == 0:
        net.NetApiBufferFree(ptr)
        raise RuntimeError('EXISTING_ACCOUNT_NOT_OWNED')
    if status != 2221:
        raise RuntimeError('ACCOUNT_QUERY_FAILED:' + str(status))
    password = secrets.token_urlsafe(40) + 'aA!9'
    # DPAPI write-ahead; never expose plaintext in argv, PowerShell, stdout or logs.
    with path.open('xb') as f:
        f.write(protect(json.dumps(dict(account=ACCOUNT, password=password)).encode()))
        f.flush(); os.fsync(f.fileno())
    class User(C.Structure):
        _fields_ = [('name', W.LPWSTR), ('password', W.LPWSTR), ('age', W.DWORD),
                   ('priv', W.DWORD), ('home', W.LPWSTR), ('comment', W.LPWSTR),
                   ('flags', W.DWORD), ('script', W.LPWSTR)]
    value = User(ACCOUNT, password, 0, 1, None, 'APCD V3 restricted development consumer',
                 1 | 0x10000 | 0x40, None)
    error = W.DWORD()
    net.NetUserAdd.argtypes = [W.LPCWSTR, W.DWORD, C.c_void_p, C.POINTER(W.DWORD)]
    status = net.NetUserAdd(None, 1, C.byref(value), C.byref(error))
    value.password = None; password = None
    if status:
        raise RuntimeError('ACCOUNT_CREATION_FAILED:' + str(status))
    token = logon(path); user = token_data(token, 1)
    sid = sid_text(C.cast(user, C.POINTER(SidAttributes)).contents.sid)
    k = dll('kernel32'); k.CloseHandle.argtypes = [W.HANDLE]; k.CloseHandle(token)
    return dict(account=ACCOUNT, sid=sid, existing_owned_credential=False)


def run_consumer(secret_path, executable, arguments, scratch, *, timeout=120):
    """Use a distinct non-admin token; restricting SID additionally restricts writes.

    Caller-owned scratch has a specific consumer SID allow ACE; shared runtime does
    not, so WRITE_RESTRICTED denies modification despite broad inherited group ACEs.
    No process termination on timeout: return UNKNOWN and preserve process evidence.
    """
    adv = dll('advapi32'); k = dll('kernel32')
    primary = logon(secret_path); limited = W.HANDLE(); pi = ProcessInfo()
    handles = [primary]
    station = desktop = sd = None
    groups = token_data(primary,2)
    n = C.cast(groups,C.POINTER(W.DWORD)).contents.value
    members = C.cast(C.addressof(groups)+C.sizeof(C.c_void_p),C.POINTER(SidAttributes))
    if any(sid_text(members[i].sid)=='S-1-5-32-544' for i in range(n)):
        k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle(primary)
        raise RuntimeError('CONSUMER_ADMINISTRATOR_MEMBERSHIP_FORBIDDEN')
    if C.cast(token_data(primary,20),C.POINTER(W.DWORD)).contents.value:
        k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle(primary)
        raise RuntimeError('CONSUMER_ELEVATION_FORBIDDEN')
    try:
        user = token_data(primary, 1)
        sid = C.cast(user, C.POINTER(SidAttributes)).contents.sid
        restriction = SidAttributes(sid, 0)
        adv.CreateRestrictedToken.argtypes = [W.HANDLE, W.DWORD, W.DWORD, C.c_void_p,
            W.DWORD, C.c_void_p, W.DWORD, C.POINTER(SidAttributes), C.POINTER(W.HANDLE)]
        check(adv.CreateRestrictedToken(primary, 1 | 8, 0, None, 0, None, 1,
                                       C.byref(restriction), C.byref(limited)))
        handles.append(limited)
        si = Startup(); si.cb = C.sizeof(si)
        class SecurityAttributes(C.Structure):
            _fields_ = [('length', W.DWORD), ('descriptor', C.c_void_p), ('inherit', W.BOOL)]
        security = SecurityAttributes(C.sizeof(SecurityAttributes), None, True)
        log = Path(scratch)/('consumer_process_' + secrets.token_hex(8) + '.log')
        k.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, C.POINTER(SecurityAttributes), W.DWORD, W.DWORD, W.HANDLE]
        k.CreateFileW.restype = W.HANDLE
        output = k.CreateFileW(str(log), 0x40000000, 3, C.byref(security), 1, 128, None)
        if output == C.c_void_p(-1).value: raise C.WinError(C.get_last_error())
        handles.append(output); si.flags = 0x100; si.stdout = output; si.stderr = output
        # Dedicated private noninteractive station: the consumer must not depend on
        # SSH/DELL's inaccessible desktop when scientific Python loads user32 DLLs.
        user32 = dll('user32'); sd = C.c_void_p()
        adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [W.LPCWSTR,W.DWORD,C.POINTER(C.c_void_p),C.c_void_p]
        sddl = 'D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GA;;;S-1-5-21-2958591235-2706656562-1210676212-1001)(A;;GA;;;' + sid_text(sid) + ')'
        check(adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,C.byref(sd),None))
        access = SecurityAttributes(C.sizeof(SecurityAttributes),sd,False)
        station_name = 'APCD_V3_CONSUMER_' + secrets.token_hex(6)
        user32.CreateWindowStationW.argtypes = [W.LPCWSTR,W.DWORD,W.DWORD,C.POINTER(SecurityAttributes)]
        user32.CreateWindowStationW.restype = W.HANDLE
        station = user32.CreateWindowStationW(station_name,0,0x37f,C.byref(access));check(station)
        user32.GetProcessWindowStation.restype = W.HANDLE
        original_station = user32.GetProcessWindowStation()
        user32.SetProcessWindowStation.argtypes = [W.HANDLE]
        check(user32.SetProcessWindowStation(station))
        try:
            user32.CreateDesktopW.argtypes = [W.LPCWSTR,C.c_void_p,C.c_void_p,W.DWORD,W.DWORD,C.POINTER(SecurityAttributes)]
            user32.CreateDesktopW.restype = W.HANDLE
            desktop = user32.CreateDesktopW('Default',None,None,0,0x1ff,C.byref(access));check(desktop)
        finally:
            check(user32.SetProcessWindowStation(original_station))
        # Dedicated handles remain live until this specific child exits; never touch foreign desktops.
        si.desktop = station_name + '\\Default'
        command = C.create_unicode_buffer(subprocess.list2cmdline([str(executable)] + list(arguments)))
        environment = dict(SystemRoot=os.environ['SystemRoot'], WINDIR=os.environ['SystemRoot'],
            PATH=str(Path(executable).parent) + ';' + str(Path(executable).parent/'Library/bin') + ';' + os.environ['SystemRoot'] + '\\System32',
            TEMP=str(scratch), TMP=str(scratch), PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
        env = C.create_unicode_buffer('\0'.join(k+'='+v for k,v in sorted(environment.items()))+'\0\0')
        adv.CreateProcessWithTokenW.argtypes = [W.HANDLE, W.DWORD, W.LPCWSTR, W.LPWSTR,
            W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(Startup), C.POINTER(ProcessInfo)]
        check(adv.CreateProcessWithTokenW(limited, 0, str(executable), command,
              0x08000000 | 0x400, env, str(scratch), C.byref(si), C.byref(pi)))
        handles.extend([pi.process, pi.thread])
        k.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
        wait = k.WaitForSingleObject(pi.process, int(timeout*1000))
        if wait != 0:
            raise RuntimeError('CONSUMER_EXIT_UNKNOWN_PID:' + str(pi.pid))
        code = W.DWORD(); k.GetExitCodeProcess.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
        check(k.GetExitCodeProcess(pi.process, C.byref(code)))
        return dict(pid=pi.pid, exitcode=code.value, write_restricted=True, log=str(log))
    finally:
        k.CloseHandle.argtypes = [W.HANDLE]
        for handle in handles:
            k.CloseHandle(handle)
        if desktop:
            user32.CloseDesktop.argtypes=[W.HANDLE];user32.CloseDesktop(desktop)
        if station:
            user32.CloseWindowStation.argtypes=[W.HANDLE];user32.CloseWindowStation(station)
        if sd:
            k.LocalFree.argtypes=[C.c_void_p];k.LocalFree(sd)
