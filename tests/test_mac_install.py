import io
import json
import plistlib
import tarfile
from pathlib import Path

import pytest
from dental_lab.platform_paths import install_root,environment_python,blender_default,codex_candidates
from dental_lab.auth import verify_password
from dental_lab.store import Store
from macos.install_local import configure,extract,launch_agent,no_active_jobs,write_plist


def test_mac_paths_are_native_and_windows_paths_preserved(tmp_path):
    root=install_root('darwin',tmp_path)
    assert root==tmp_path/'Library/Application Support/SEGMENT IQ'
    assert environment_python(root,platform='darwin')==root/'runtime/python/bin/python'
    assert str(blender_default('darwin',tmp_path)).endswith('Blender.app/Contents/MacOS/Blender')
    assert install_root('win32',tmp_path)==tmp_path/'Documents/DentalLabAgent'
    assert str(environment_python(tmp_path,platform='win32')).endswith('Scripts/python.exe')
    assert any('SEGMENT IQ' in str(p) for p in codex_candidates(platform='darwin',home=tmp_path))


def test_plist_retains_space_paths_without_shell_or_secrets(tmp_path):
    args=['/Users/A Name/runtime/python/bin/python','-m','dental_lab.service']
    file=tmp_path/'service.plist'
    write_plist(file,launch_agent('com.segmentiq.local',args,tmp_path,{'DENTAL_LAB_DATA':str(tmp_path)},tmp_path))
    result=plistlib.loads(file.read_bytes())
    assert result['ProgramArguments']==args and result['KeepAlive']
    assert 'password' not in file.read_text() and 'sh -c' not in file.read_text()


def test_config_update_keeps_local_login_and_private_preferences(tmp_path):
    app=Path(__file__).resolve().parents[1]
    first=configure(tmp_path,app,tmp_path/'Blender',tmp_path/'codex',ci=True)
    path=tmp_path/'data/config.local.json'
    first['frame_seconds']=42
    path.write_text(json.dumps(first))
    second=configure(tmp_path,app,tmp_path/'New Blender',tmp_path/'codex',ci=True)
    assert second['password_hash']==first['password_hash']
    assert second['password']==first['password'] and second['frame_seconds']==42
    assert second['agent_harness']=='codex' and second['b4d_root']==''
    assert second['ollama_url']=='http://127.0.0.1:11435'
    assert not verify_password(second['password'],second['password_hash'])


def test_update_refuses_to_interrupt_queued_or_running_work(tmp_path):
    store=Store(tmp_path)
    no_active_jobs(tmp_path)
    job=store.job('segment','synthetic')
    with pytest.raises(RuntimeError,match='trabajos activos'):no_active_jobs(tmp_path)
    store.update_job(job,'running')
    with pytest.raises(RuntimeError,match='trabajos activos'):no_active_jobs(tmp_path)
    store.update_job(job,'done');no_active_jobs(tmp_path)


def test_archive_cannot_write_outside_runtime(tmp_path):
    archive=tmp_path/'bad.tar.gz'
    with tarfile.open(archive,'w:gz') as package:
        item=tarfile.TarInfo('../escaped');item.size=4;package.addfile(item,io.BytesIO(b'nope'))
    with pytest.raises(tarfile.TarError):extract(archive,tmp_path/'runtime')
    assert not (tmp_path/'escaped').exists()
