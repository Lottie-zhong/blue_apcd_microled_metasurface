import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('trusted_release_builder',Path(__file__).parents[1]/'tools/build_trusted_release.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


def fixture(tmp_path):
    root=tmp_path/'candidate';root.mkdir()
    (root/'DISABLED_PLATFORM.json').write_text(json.dumps(dict(mode='PRODUCTION_GPU',profiles=[])))
    data=dict(schema='APCD_GPU_V21_TRUSTED_ADMISSION_DISABLED_CANDIDATE_V1',
        deployment_authorized=False,solver_entry_authorized=False,
        files={'DISABLED_PLATFORM.json':dict(sha256=builder.sha(root/'DISABLED_PLATFORM.json'),bytes=(root/'DISABLED_PLATFORM.json').stat().st_size)})
    builder.write(root/'PACKAGE_MANIFEST.json',data)
    return root,builder.sha(root/'PACKAGE_MANIFEST.json')


def test_candidate_package_verify_and_deterministic_zip(tmp_path):
    root,pin=fixture(tmp_path)
    assert builder.verify_tree(root,pin)['solver_entry_authorized'] is False
    a=tmp_path/'a.zip';b=tmp_path/'b.zip';builder.zip_tree(root,a);builder.zip_tree(root,b)
    assert a.read_bytes()==b.read_bytes()


@pytest.mark.parametrize('fault',['file','extra','manifest'])
def test_candidate_package_drift_fails_closed(tmp_path,fault):
    root,pin=fixture(tmp_path)
    if fault=='file':(root/'DISABLED_PLATFORM.json').write_text('{}')
    if fault=='extra':(root/'UNREVIEWED.py').write_text('')
    if fault=='manifest':(root/'PACKAGE_MANIFEST.json').write_text('{}')
    with pytest.raises(ValueError):builder.verify_tree(root,pin)


def test_builder_rejects_production_destination_and_existing_release(tmp_path):
    with pytest.raises(ValueError,match='CANNOT_WRITE_PRODUCTION'):
        builder.isolated_destination(builder.RUNTIME/'releases/new')
    with pytest.raises(ValueError,match='ALREADY_EXISTS'):
        builder.isolated_destination(tmp_path)
    with pytest.raises(ValueError,match='PATH_ESCAPE'):
        builder.safe_relative(tmp_path,'../outside')


def test_builder_preserves_tested_crlf_bytes_and_detects_dirty_git_source(tmp_path):
    source=tmp_path/'source';source.mkdir()
    def git(*args):return subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
    git('init');git('config','user.name','ISOLATED_OFFLINE_TEST');git('config','user.email','offline-test@invalid.example')
    git('config','core.autocrlf','true');git('config','commit.gpgsign','false')
    rel='platform_v2/apcd_gpu_v2/trusted_admission.py';p=source/rel;p.parent.mkdir(parents=True)
    raw=b'# harmless isolated source fixture\r\n'
    p.write_bytes(raw);git('add','--',rel);git('commit','-m','offline fixture')
    cfg=tmp_path/'platform.json';builder.write(cfg,dict(mode='PRODUCTION_GPU',profiles=[]))
    pin=dict(path=str(cfg),sha256=builder.sha(cfg));head=git('rev-parse','HEAD')
    result=builder.build(source,tmp_path/'good',pin,head)
    assert (tmp_path/'good'/rel).read_bytes()==raw
    assert builder.verify_tree(tmp_path/'good',result['package_manifest_sha256'])['source_head']==head
    p.write_bytes(b'# changed without review\r\n')
    with pytest.raises(ValueError,match='DIRTY_RELEASE_SOURCE'):
        builder.build(source,tmp_path/'dirty_rejected',pin,head)
    assert not (tmp_path/'dirty_rejected').exists()
