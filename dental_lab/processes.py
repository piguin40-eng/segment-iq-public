"""Own-process-group cleanup for native macOS/Linux geometry workers."""
import os
import signal
import subprocess


def owned_session():
    return {'start_new_session':True} if os.name!='nt' else {}


def stop_owned_process(process):
    """Only call for processes spawned with owned_session(). Never match by name."""
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name=='nt':process.kill()
        else:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        process.wait(timeout=10)
    if os.name!='nt':
        # The parent may exit immediately while Blender ignores TERM.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
