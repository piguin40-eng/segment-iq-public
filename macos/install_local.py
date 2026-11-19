"""Per-user Apple Silicon installation. No Windows host, admin access or shared keys."""
import argparse,getpass,hashlib,json,os,platform,plistlib,shutil,sqlite3,subprocess,sys,tarfile,tempfile,time,urllib.request
from pathlib import Path

ROOT_SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT_SOURCE))
from dental_lab.platform_paths import install_root,environment_python


def run(args,**kwargs):
    return subprocess.run([str(a) for a in args],check=True,**kwargs)


def sha256(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def download(record,cache):
    name=record['url'].rsplit('/',1)[-1];dest=cache/name
    if dest.is_file() and sha256(dest)==record['sha256']:return dest
    temporary=dest.with_suffix(dest.suffix+'.part')
    print('Descargando '+name,flush=True)
    run(['/usr/bin/curl','--fail','--location','--retry','3','--proto','=https','--tlsv1.2',record['url'],'-o',temporary])
    if sha256(temporary)!=record['sha256']:raise RuntimeError('SHA-256 incorrecto: '+name)
    temporary.replace(dest);return dest


def extract(archive,destination):
    destination.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive) as package:package.extractall(destination,filter='data')


def no_active_jobs(data):
    db=Path(data)/'knowledge.sqlite3'
    if not db.exists():return
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        if conn.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running') LIMIT 1").fetchone():
            raise RuntimeError('Hay trabajos activos. Termínalos antes de actualizar esta instalación.')


def launch_agent(label,arguments,working,environment,logs):
    return {'Label':label,'ProgramArguments':[str(a) for a in arguments],
            'WorkingDirectory':str(working),'EnvironmentVariables':environment,
            'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':10,
            'ProcessType':'Interactive','LimitLoadToSessionType':'Aqua',
            'StandardOutPath':str(Path(logs)/(label+'.log')),
            'StandardErrorPath':str(Path(logs)/(label+'.err.log'))}


def write_plist(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as stream:plistlib.dump(value,stream)
    path.chmod(0o600)


def build_launcher(app,applications):
    applications.mkdir(parents=True,exist_ok=True)
    script='do shell script "/bin/bash " & quoted form of '+json.dumps(str(app/'macos/Start-Mac.sh'))+' & " --browser"'
    with tempfile.TemporaryDirectory(prefix='segment-iq-launcher-') as temp:
        target=Path(temp)/'SEGMENT IQ Local.app'
        run(['/usr/bin/osacompile','-o',target,'-e',script])
        run(['/usr/bin/ditto',target,applications/'SEGMENT IQ Local.app'])


def wait_health(url,seconds=60):
    for _ in range(seconds):
        try:
            with urllib.request.urlopen(url,timeout=2) as response:return json.load(response)
        except (OSError,ValueError):time.sleep(1)
    raise RuntimeError('No responde el servicio local: '+url)


def configure(root,app,blender,codex,ci=False):
    data=root/'data';data.mkdir(parents=True,exist_ok=True);data.chmod(0o700)
    path=data/'config.local.json'
    # Import from the copied app only after the environments have been installed.
    sys.path.insert(0,str(app))
    from dental_lab.auth import hash_password
    from dental_lab.config import write_config
    import secrets
    existing=json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    values=dict(existing)
    if not existing:
        if ci:username='installation-test';password=secrets.token_urlsafe(24)
        else:
            username=input('Usuario para SEGMENT IQ [admin]: ').strip() or 'admin'
            while True:
                password=getpass.getpass('Crea tu contraseña local (mínimo 10 caracteres): ')
                if len(password)>=10 and password==getpass.getpass('Repite la contraseña: '):break
                print('No coinciden o son demasiado cortas. Vuelve a introducirlas.')
        values.update(username=username,password=secrets.token_urlsafe(32),password_hash=hash_password(password))
    values.update(blender=str(blender),geometry_python=str(environment_python(root,'geometry-python','darwin')),
                  codex_executable=str(codex),agent_harness='codex',live_blender=not ci,
                  ollama_url='http://127.0.0.1:11435')
    values.setdefault('b4d_root','')
    write_config(path,values);path.chmod(0o600)
    return values


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=ROOT_SOURCE)
    parser.add_argument('--root',type=Path,default=install_root('darwin'))
    parser.add_argument('--ci',action='store_true',help='Install/test without account login, model downloads or persistent LaunchAgents.')
    args=parser.parse_args()
    if sys.platform!='darwin' or platform.machine()!='arm64':raise RuntimeError('Se necesita un Mac Apple Silicon nativo.')
    if int(platform.mac_ver()[0].split('.')[0])<14:raise RuntimeError('Se necesita macOS 14 o posterior.')
    root=args.root.expanduser().resolve();source=args.source.resolve()
    if root==Path.home().resolve() or root==source or source.is_relative_to(root/'app') or root.is_relative_to(source):
        raise RuntimeError('Destino de instalación no válido.')
    root.mkdir(parents=True,exist_ok=True);root.chmod(0o700)
    no_active_jobs(root/'data')
    if not args.ci:
        # Stop only our own idle services before replacing code or dependencies.
        for label in ('com.segmentiq.local','com.segmentiq.ollama'):
            subprocess.run(['/bin/launchctl','bootout',f'gui/{os.getuid()}/{label}'],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    runtime=root/'runtime';cache=runtime/'downloads';cache.mkdir(parents=True,exist_ok=True)
    app=root/'app'
    ignored=shutil.ignore_patterns('.git','.venv','__pycache__','.pytest_cache','node_modules','dist','data','backups','.env')
    shutil.copytree(source,app,ignore=ignored,dirs_exist_ok=True)
    manifest=json.loads((app/'macos/downloads.json').read_text())
    uv=runtime/'uv/uv'
    env={**os.environ,'UV_PYTHON_INSTALL_DIR':str(runtime/'python-managed')}
    for name,requirements in [('python','requirements-lock.txt'),('geometry-python','requirements-geometry.txt')]:
        python=environment_python(root,name,'darwin')
        if not python.exists():run([uv,'venv','--python',sys.executable,'--seed',python.parent.parent],env=env)
        print('Instalando dependencias de '+name,flush=True)
        run([uv,'pip','install','--python',python,'-r',app/requirements],env=env)
    python=environment_python(root,platform='darwin')
    blender=runtime/'Blender.app/Contents/MacOS/Blender'
    if not blender.exists():
        dmg=download(manifest['blender'],cache)
        with tempfile.TemporaryDirectory(prefix='segment-iq-mount-') as temp:
            mount=Path(temp)/'volume';mount.mkdir()
            run(['/usr/bin/hdiutil','attach',dmg,'-nobrowse','-readonly','-mountpoint',mount])
            try:
                candidates=list(mount.glob('Blender*.app'))
                if len(candidates)!=1:raise RuntimeError('El disco no contiene una sola aplicación Blender.')
                run(['/usr/bin/ditto',candidates[0],runtime/'Blender.app'])
            finally:run(['/usr/bin/hdiutil','detach',mount])
    for key in ['codex','ollama']:
        folder=runtime/key;archive=download(manifest[key],cache);extract(archive,folder)
    codex_candidates=[p for p in (runtime/'codex').rglob('codex*') if p.is_file() and not p.suffix]
    if not codex_candidates:raise RuntimeError('No se encuentra el ejecutable de Codex.')
    codex=runtime/'codex/codex'
    candidate=next((p for p in codex_candidates if p.name=='codex-aarch64-apple-darwin'),None)
    if candidate is not None and candidate!=codex:shutil.copy2(candidate,codex)
    if not codex.exists():raise RuntimeError('El paquete de Codex no contiene el binario esperado.')
    codex.chmod(0o755)
    ollama=next((p for p in (runtime/'ollama').rglob('ollama') if p.is_file()),None)
    if ollama is None:raise RuntimeError('No se encuentra el ejecutable de Ollama.')
    ollama.chmod(0o755)
    values=configure(root,app,blender,codex,args.ci)
    data=root/'data';logs=data/'logs';logs.mkdir(exist_ok=True)
    env.update(DENTAL_LAB_DATA=str(data),PYTHONUTF8='1',PYTHONIOENCODING='utf-8',
               PATH=os.pathsep.join([str(codex.parent),str(ollama.parent),str(python.parent),os.environ.get('PATH','/usr/bin:/bin')]))
    with (logs/'blender-compatibility.log').open('w') as log:
        run([blender,'--background','--factory-startup','--disable-autoexec','--python-exit-code','1',
             '--python',app/'macos/probe_blender.py','--',data/'blender-compatibility.json'],stdout=log,stderr=subprocess.STDOUT)
    run([codex,'--version'])
    help_text=subprocess.check_output([codex,'exec','--help'],text=True)
    for flag in ['--ignore-user-config','--ephemeral','--output-schema']:
        if flag not in help_text:raise RuntimeError('Codex no admite la opción requerida '+flag)
    label='com.segmentiq.local';ollama_label='com.segmentiq.ollama'
    agents=root/'launchagents' if args.ci else Path.home()/'Library/LaunchAgents'
    common={'DENTAL_LAB_DATA':str(data),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','PATH':env['PATH']}
    write_plist(agents/(label+'.plist'),launch_agent(label,[python,'-m','dental_lab.service','--serve-only',
         '--data',data,'--host','127.0.0.1','--port','8765'],app,common,logs))
    write_plist(agents/(ollama_label+'.plist'),launch_agent(ollama_label,[ollama,'serve'],app,
         {**common,'OLLAMA_HOST':'127.0.0.1:11435','OLLAMA_MODELS':str(data/'models/ollama')},logs))
    installation={'version':'0.6.0','root':str(root),'app':str(app),'data':str(data),
      'blender':str(blender),'codex':str(codex),'ollama':str(ollama),'host':'127.0.0.1',
      'b4d':'not_configured' if not values.get('b4d_root') else 'configured_requires_validation',
      'mode':'native_mac_own_engine','account_and_models':'pending' if args.ci else 'preparing'}
    (root/'INSTALLATION.json').write_text(json.dumps(installation,indent=2),encoding='utf-8')
    if args.ci:
        build_launcher(app,root/'launcher-validation')
        print('MAC_NATIVE_DEPENDENCIES_READY (CI: no account/model validation)',flush=True);return
    uid=os.getuid()
    for name in [ollama_label,label]:
        subprocess.run(['/bin/launchctl','bootout',f'gui/{uid}/{name}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        run(['/bin/launchctl','bootstrap',f'gui/{uid}',agents/(name+'.plist')])
    wait_health('http://127.0.0.1:11435/api/version')
    health=wait_health('http://127.0.0.1:8765/health')
    if health.get('service')!='SEGMENT IQ':raise RuntimeError('El puerto local pertenece a otro servicio.')
    print('Preparando voz, búsqueda y modelo visual local. Puede tardar varios minutos.',flush=True)
    run([python,app/'scripts/prepare_models.py'],env=env,cwd=app)
    # Index reusable protocol documents locally; no private laboratory corpus is downloaded.
    run([python,app/'macos/seed_knowledge.py'],env=env,cwd=app)
    print('Inicia sesión en tu propia cuenta de Codex para activar el agente de correcciones.',flush=True)
    if subprocess.run([codex,'login','status'],env=env).returncode:run([codex,'login'],env=env)
    run([codex,'login','status'],env=env)
    build_launcher(app,Path.home()/'Applications')
    installation['account_and_models']='ready'
    (root/'INSTALLATION.json').write_text(json.dumps(installation,indent=2),encoding='utf-8')
    run(['/usr/bin/open','http://127.0.0.1:8765'])
    print('SEGMENT IQ local preparado. Inicia sesión con el usuario que has creado. Blender y el RAG trabajan en este Mac.',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('INSTALACION INCOMPLETA: '+str(error),file=sys.stderr,flush=True);raise SystemExit(1)
