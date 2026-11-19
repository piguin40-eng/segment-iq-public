import os,subprocess,sys,time
from pathlib import Path
import pytest
from dental_lab.processes import owned_session,stop_owned_process


@pytest.mark.skipif(os.name=='nt',reason='POSIX process group behavior')
def test_stop_cleans_child_worker_but_not_unrelated_process(tmp_path):
    heartbeat=tmp_path/'heartbeat'
    child="import signal,time,pathlib;signal.signal(signal.SIGTERM,signal.SIG_IGN);p=pathlib.Path("+repr(str(heartbeat))+");exec('while True:\\n p.write_text(str(time.time()))\\n time.sleep(.05)')"
    parent="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);time.sleep(60)"
    unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],**owned_session())
    process=subprocess.Popen([sys.executable,'-c',parent],**owned_session())
    try:
        deadline=time.monotonic()+10
        while not heartbeat.exists() and time.monotonic()<deadline:time.sleep(.05)
        assert heartbeat.exists()
        stop_owned_process(process)
        time.sleep(.2);stamp=heartbeat.stat().st_mtime_ns
        time.sleep(.2);assert heartbeat.stat().st_mtime_ns==stamp
        assert unrelated.poll() is None
    finally:
        if process.poll() is None:stop_owned_process(process)
        stop_owned_process(unrelated)
