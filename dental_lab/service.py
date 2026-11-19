"""Local service entry point for Task Scheduler or a per-user macOS LaunchAgent."""
import argparse,faulthandler,os,sys,traceback,subprocess,time
from datetime import datetime
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',required=True)
    parser.add_argument('--host',default='0.0.0.0')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--serve-only',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    data=Path(args.data).resolve();logs=data/'logs';logs.mkdir(parents=True,exist_ok=True)
    os.environ['DENTAL_LAB_DATA']=str(data)
    # pythonw has no console streams. Own the log handles for the full lifetime;
    # neither an opening terminal nor a desktop shortcut owns the server.
    sys.stdout=open(logs/'service.log','a',encoding='utf-8',buffering=1)
    sys.stderr=open(logs/'service.err.log','a',encoding='utf-8',buffering=1)
    faulthandler.enable(file=sys.stderr)
    role='SERVER' if args.serve_only else 'SUPERVISOR'
    print(f'{datetime.now().isoformat()} {role} START pid={os.getpid()}',flush=True)
    if not args.serve_only:
        failures=0
        while failures<10:
            started=time.monotonic()
            command=[sys.executable,'-m','dental_lab.service','--serve-only','--data',str(data),'--host',args.host,'--port',str(args.port)]
            child=subprocess.Popen(command,cwd=Path(__file__).resolve().parents[1],
                stdout=sys.stdout,stderr=sys.stderr,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:code=child.wait()
            finally:
                if child.poll() is None:child.terminate();child.wait()
            failures=1 if time.monotonic()-started>=120 else failures+1
            delay=min(60,5*2**min(failures-1,4))
            print(f'{datetime.now().isoformat()} SERVER EXIT pid={child.pid} code={code}; retry in {delay}s',flush=True)
            time.sleep(delay)
        raise RuntimeError('El servidor ha fallado diez veces seguidas. Revisar service.err.log.')
    try:
        import uvicorn
        from .config import load
        from .server import create_app
        uvicorn.run(create_app(load()),host=args.host,port=args.port)
    except BaseException:
        traceback.print_exc();raise
    finally:
        print(f'{datetime.now().isoformat()} EXIT pid={os.getpid()}',flush=True)


if __name__=='__main__':main()
