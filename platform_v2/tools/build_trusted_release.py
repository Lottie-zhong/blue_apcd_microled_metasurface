"""Build/verify a frozen Disabled candidate. This tool has no install operation."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

RUNTIME = Path('D:/apcd_runtime/gpu_platform_v2_serial_production_v1')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2), encoding='utf-8')


def isolated_destination(path):
    path = Path(path).resolve()
    canonical = RUNTIME.resolve()
    if path == canonical or canonical in path.parents or path in canonical.parents:
        raise ValueError('CANDIDATE_BUILD_CANNOT_WRITE_PRODUCTION')
    if path.exists():
        raise ValueError('IMMUTABLE_CANDIDATE_ALREADY_EXISTS')
    return path


def safe_relative(root, name):
    path = (root / name).resolve()
    if Path(name).is_absolute() or path == root.resolve() or root.resolve() not in path.parents:
        raise ValueError('PACKAGE_PATH_ESCAPE')
    return path


def verify_tree(root, expected_manifest_sha):
    root = Path(root)
    manifest = root / 'PACKAGE_MANIFEST.json'
    if sha(manifest) != expected_manifest_sha:
        raise ValueError('PACKAGE_MANIFEST_SHA_CHANGED')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if (data.get('schema') != 'APCD_GPU_V21_TRUSTED_ADMISSION_DISABLED_CANDIDATE_V1'
        or data.get('deployment_authorized') is not False
        or data.get('solver_entry_authorized') is not False):
        raise ValueError('DISABLED_CANDIDATE_REQUIRED')
    for name, pin in data['files'].items():
        path = safe_relative(root, name)
        if sha(path) != pin['sha256'] or path.stat().st_size != pin['bytes']:
            raise ValueError('PACKAGE_FILE_CHANGED:' + name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(data['files']) | {'PACKAGE_MANIFEST.json'}:
        raise ValueError('UNDECLARED_PACKAGE_FILE')
    platform = json.loads((root / 'DISABLED_PLATFORM.json').read_text(encoding='utf-8'))
    if platform.get('profiles') != [] or platform.get('mode') != 'PRODUCTION_GPU':
        raise ValueError('DEFAULT_DENY_PLATFORM_REQUIRED')
    return data


def zip_tree(root, output):
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(Path(root).rglob('*')):
            if not p.is_file():
                continue
            row = zipfile.ZipInfo(p.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            row.compress_type = zipfile.ZIP_DEFLATED
            row.external_attr = 0o100644 << 16
            z.writestr(row, p.read_bytes())


def build(source, destination, platform_pin, expected_head):
    source = Path(source).resolve()
    destination = isolated_destination(destination)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
    if git('rev-parse', 'HEAD') != expected_head:
        raise ValueError('SOURCE_HEAD_CHANGED')
    names = git('ls-files', '--', 'platform_v2/apcd_gpu_v2',
        'platform_v2/tools/general_runner.py', 'platform_v2/tools/serial_controller.py',
        'platform_v2/tools/build_trusted_release.py').splitlines()
    if not names or 'platform_v2/apcd_gpu_v2/trusted_admission.py' not in names:
        raise ValueError('COMMITTED_TRUSTED_ADMISSION_SOURCE_REQUIRED')
    committed = {}
    for name in names:
        data = subprocess.check_output(['git', '-C', str(source), 'show', expected_head + ':' + name])
        if (source / name).read_bytes() != data:
            raise ValueError('DIRTY_RELEASE_SOURCE:' + name)
        committed[name] = data
    if sha(platform_pin['path']) != platform_pin['sha256']:
        raise ValueError('PLATFORM_SHA_CHANGED')
    platform = json.loads(Path(platform_pin['path']).read_text(encoding='utf-8'))
    if platform.get('profiles') != [] or platform.get('mode') != 'PRODUCTION_GPU':
        raise ValueError('DEFAULT_DENY_PLATFORM_REQUIRED')
    destination.mkdir(parents=True, exist_ok=False)
    release_name = 'v21_trusted_admission_' + expected_head[:12]
    for name, data in committed.items():
        path = safe_relative(destination, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    rows = {n:dict(sha256=sha(destination/n), bytes=(destination/n).stat().st_size) for n in names}
    write(destination/'CODE_SHA256.json', dict(code_root=str(RUNTIME/'releases'/release_name), files=rows))
    (destination/'DISABLED_PLATFORM.json').write_bytes(Path(platform_pin['path']).read_bytes())
    payload_names = names + ['CODE_SHA256.json', 'DISABLED_PLATFORM.json']
    manifest = dict(schema='APCD_GPU_V21_TRUSTED_ADMISSION_DISABLED_CANDIDATE_V1',
        source_head=expected_head, release_name=release_name,
        deployment_authorized=False, solver_entry_authorized=False,
        production_credential_ready=False, science_owner_endorsement='PENDING',
        original_platform_pin=platform_pin,
        files={n:dict(sha256=sha(destination/n), bytes=(destination/n).stat().st_size) for n in payload_names})
    write(destination/'PACKAGE_MANIFEST.json', manifest)
    manifest_sha = sha(destination/'PACKAGE_MANIFEST.json')
    verify_tree(destination, manifest_sha)
    archive = destination.with_name(destination.name + '.zip')
    zip_tree(destination, archive)
    return dict(release_name=release_name, source_head=expected_head,
        package_root=str(destination), archive=str(archive), archive_sha256=sha(archive),
        package_manifest_sha256=manifest_sha, code_inventory_sha256=sha(destination/'CODE_SHA256.json'),
        deployment_authorized=False, solver_entry_authorized=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    cmd = sub.add_parser('build')
    for name in ['source', 'destination', 'platform', 'platform-sha256', 'source-head']:
        cmd.add_argument('--' + name, required=True)
    cmd = sub.add_parser('verify')
    cmd.add_argument('--package', required=True)
    cmd.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args(argv)
    if args.operation == 'build':
        result = build(args.source, args.destination,
            dict(path=args.platform, sha256=args.platform_sha256), args.source_head)
    else:
        result = verify_tree(args.package, args.manifest_sha256)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
