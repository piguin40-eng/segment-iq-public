import hashlib,hmac,secrets,time,json,uuid,tempfile,os,shutil
from pathlib import Path
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
import httpx
from fastapi import FastAPI,Request,UploadFile,File,Form,HTTPException
from fastapi.responses import FileResponse,JSONResponse,Response
from pydantic import BaseModel,Field
from starlette.concurrency import run_in_threadpool
from .auth import verify_password,same_username
from . import __version__
from .config import load
from .store import Store
from .rag import Rag
from .ingest import Ingest,ALLOWED
from .worker import Worker
from . import lab_workflow
from .progress import job_progress,result_file_groups
from .dictation import Dictation,DictationError,DictationBusy,FORMATS,MAX_AUDIO_BYTES

class Ask(BaseModel):question:str=Field(min_length=2,max_length=6000)
class LoginBody(BaseModel):
    username:str=Field(min_length=1,max_length=80)
    password:str=Field(min_length=1,max_length=1024)
class CaseBody(BaseModel):name:str=Field(min_length=1,max_length=120);source_id:str
class GenerationBody(BaseModel):fresh_start:bool=False
class Feedback(BaseModel):
    case_id:str='general'
    author:str=Field(min_length=1,max_length=80)
    text:str=Field(min_length=3,max_length=10000)
    status:str='correction'
    attachment_ids:list[str]=Field(default_factory=list,max_length=20)
    request_plan:bool=False
    request_generation:bool=False

def create_app(settings=None,start_worker=True):
    s=settings or load();db=Store(s.data);rag=Rag(s,db);ingest=Ingest(s,db,rag);worker=Worker(s,db,ingest)
    sessions={};attempts={}
    web_hash=s.password_hash
    @asynccontextmanager
    async def lifespan(app):
        if start_worker:worker.start()
        yield
        worker.stop.set()
    app=FastAPI(title='SEGMENT IQ',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.state.settings=s;app.state.store=db;app.state.rag=rag;app.state.ingest=ingest
    app.state.dictation=Dictation(s)

    @app.middleware('http')
    async def auth(request,call_next):
        public=request.url.path in {'/','/login','/health','/style.css','/app.js','/dictation.js'}
        bearer=request.headers.get('Authorization','').removeprefix('Bearer ')
        if not public:
            valid=hmac.compare_digest(bearer.encode('utf-8'),s.password.encode('utf-8')) if bearer else sessions.get(request.cookies.get('dental_session',''),0)>time.time()
            if not valid:return JSONResponse({'detail':'Inicia sesion'},status_code=401)
        if request.method not in {'GET','HEAD','OPTIONS'}:
            origin=request.headers.get('origin')
            if origin and urlsplit(origin).netloc!=request.headers.get('host'):return JSONResponse({'detail':'Origen no permitido'},status_code=403)
        response=await call_next(request);response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Cache-Control']='no-store'
        return response

    @app.get('/')
    def home():return FileResponse(Path(__file__).parent/'static/index.html')
    @app.get('/style.css')
    def css():return FileResponse(Path(__file__).parent/'static/style.css',media_type='text/css')
    @app.get('/app.js')
    def js():return FileResponse(Path(__file__).parent/'static/app.js',media_type='text/javascript')
    @app.get('/dictation.js')
    def dictation_js():return FileResponse(Path(__file__).parent/'static/dictation.js',media_type='text/javascript')
    @app.get('/health')
    def health():return {'status':'ok','service':'SEGMENT IQ','version':__version__}
    @app.post('/login')
    async def login(request:Request,body:LoginBody):
        key=request.client.host;recent=[t for t in attempts.get(key,[]) if t>time.time()-60];attempts[key]=recent
        if len(recent)>=10:raise HTTPException(429,'Espera un minuto')
        # Reserve an attempt before yielding, so concurrent requests share the limit.
        recent.append(time.time())
        password_ok=await run_in_threadpool(verify_password,body.password,web_hash)
        if not (same_username(body.username,s.username) and password_ok):raise HTTPException(401,'Usuario o contraseña incorrectos')
        sessions.pop(request.cookies.get('dental_session',''),None)
        token=secrets.token_urlsafe(32);sessions[token]=time.time()+12*3600
        result=JSONResponse({'ok':True,'username':s.username});result.set_cookie('dental_session',token,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=43200);return result
    @app.post('/api/logout')
    def logout(request:Request):
        sessions.pop(request.cookies.get('dental_session',''),None);r=JSONResponse({'ok':True});r.delete_cookie('dental_session');return r
    @app.get('/api/status')
    def status():
        from .harness import find_codex
        try:
            r=httpx.get(s.ollama_url+'/api/tags',timeout=2);r.raise_for_status();models=[x['name'] for x in r.json().get('models',[])];llm=s.model in models
        except Exception:models=[];llm=False
        return {'llm_ready':llm,'model':s.model,'sources':db.one('SELECT count(*) n FROM sources')['n'],'chunks':db.one('SELECT count(*) n FROM chunks')['n'],'cases':db.one('SELECT count(*) n FROM cases')['n'],'embedding_warning':rag.last_embedding_error,'inbox':str(s.data/'inbox'),'generation_scope':'Preparación y segmentación automáticas desde STL; propuesta para revisión','blender_present':Path(s.blender).is_file(),
                'agent_harness':s.agent_harness,'codex_installed':bool(find_codex(s)),
                'lab_workflow':lab_workflow.status(s.app,s.agent_harness)}
    @app.get('/api/lab-workflow')
    def required_lab_workflow():
        result=lab_workflow.status(s.app,s.agent_harness)
        source=db.one('SELECT id FROM sources WHERE sha256=?',(lab_workflow.VIDEO_SHA256,))
        result['video_source_id']=source['id'] if source else None
        return result
    @app.get('/api/lab-workflow/download')
    def download_lab_workflow():
        import io,zipfile
        try:workflow=lab_workflow.load_workflow(s.app)
        except RuntimeError as error:raise HTTPException(503,str(error))
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,text in workflow['files'].items():
                archive.writestr(workflow['skill']+'/'+name,text+'\n')
        return Response(buffer.getvalue(),media_type='application/zip',
            headers={'Content-Disposition':'attachment; filename="SEGMENT_IQ_skill_barras_video.zip"'})
    @app.get('/api/sources')
    def sources():return db.rows('SELECT id,name,kind,status,detail,created FROM sources ORDER BY created DESC')
    @app.post('/api/dictation')
    async def dictation(request:Request,format:str='webm'):
        extension=format.lower()
        if extension not in FORMATS:raise HTTPException(400,'Formato de audio no admitido.')
        try:
            length=int(request.headers.get('content-length','0'))
        except ValueError:raise HTTPException(400,'Tamaño de audio no válido.')
        if length>MAX_AUDIO_BYTES:raise HTTPException(413,'La nota de voz supera 20 MB.')
        # Stream the raw body with a byte limit, including chunked requests.
        with tempfile.TemporaryDirectory(prefix='dictation-',dir=s.data) as directory:
            path=Path(directory)/('voz.'+extension);total=0
            with path.open('wb') as output:
                async for chunk in request.stream():
                    total+=len(chunk)
                    if total>MAX_AUDIO_BYTES:raise HTTPException(413,'La nota de voz supera 20 MB.')
                    output.write(chunk)
            if not total:raise HTTPException(400,'No se recibió audio.')
            try:return await run_in_threadpool(app.state.dictation.transcribe,path,extension)
            except DictationError as error:raise HTTPException(422,str(error))
            except DictationBusy as error:raise HTTPException(429,str(error))
            except Exception as error:
                import logging
                logging.getLogger(__name__).exception('Fallo del transcriptor local')
                raise HTTPException(503,'El transcriptor local no ha respondido. Puedes reintentar la nota sin volver a grabarla.') from error
    @app.post('/api/upload')
    async def upload(file:UploadFile=File(...)):
        name=Path((file.filename or 'archivo').replace('\\','/')).name;suffix=Path(name).suffix.lower()
        if suffix not in ALLOWED:raise HTTPException(400,'Formato no admitido')
        fd,path=tempfile.mkstemp(suffix=suffix,dir=s.data);os.close(fd)
        try:
            total=0
            with open(path,'wb') as dest:
                while chunk:=await file.read(1024*1024):
                    total+=len(chunk)
                    if total>8*1024**3:raise HTTPException(413,'Archivo mayor de 8 GB; usar carpeta de entrada')
                    dest.write(chunk)
            source,new=ingest.register(path,name)
            if new:db.job('index',source['id'])
            return {'id':source['id'],'new':new,'name':name}
        finally:Path(path).unlink(missing_ok=True);await file.close()
    @app.post('/api/sources/{id}/reindex')
    def reindex(id:str):
        if not db.one('SELECT id FROM sources WHERE id=?',(id,)):raise HTTPException(404,'Fuente no encontrada')
        return {'job_id':db.job('index',id)}
    @app.get('/api/source/{id}')
    def original(id:str):
        row=db.one('SELECT * FROM sources WHERE id=?',(id,))
        if not row:raise HTTPException(404,'Fuente no encontrada')
        return FileResponse(row['path'])
    @app.get('/api/frame/{id}/{name}')
    def frame(id:str,name:str):
        folder=s.data/'derived'/id;path=(folder/name).resolve()
        if not path.is_relative_to(folder.resolve()) or path.suffix!='.jpg' or not path.is_file():raise HTTPException(404)
        return FileResponse(path)
    @app.get('/api/search')
    def search(q:str):return rag.search(q)
    @app.post('/api/chat')
    def chat(body:Ask):
        try:return rag.chat(body.question)
        except Exception as e:raise HTTPException(503,'El modelo local no ha respondido. La busqueda sigue disponible. '+str(e)[:200])
    @app.get('/api/jobs')
    def jobs():return db.rows('SELECT * FROM jobs ORDER BY created DESC LIMIT 100')
    @app.get('/api/cases')
    def cases():return db.rows('SELECT * FROM cases ORDER BY created DESC')
    @app.post('/api/cases')
    def new_case(body:CaseBody):
        source=db.one('SELECT * FROM sources WHERE id=?',(body.source_id,))
        if not source or Path(source['path']).suffix.lower()!='.stl':raise HTTPException(400,'Elige el STL bruto')
        id=uuid.uuid4().hex
        with db.db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('INSERT INTO cases VALUES(?,?,?,?,?,?)',(id,body.name,body.source_id,None,'queued',time.time()))
            job_id=db.queue_segment(id,connection)
        return {'id':id,'job_id':job_id}
    @app.post('/api/cases/{id}/profile')
    async def profile(id:str,file:UploadFile=File(...)):
        case=db.one('SELECT * FROM cases WHERE id=?',(id,))
        if not case:raise HTTPException(404)
        content=await file.read(100001)
        if len(content)>100000:raise HTTPException(400,'Perfil demasiado grande')
        try:
            data=json.loads(content);import importlib.util
            spec=importlib.util.spec_from_file_location('dental_runner',s.app/'engine/ejecutar.py');engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
            source=db.one('SELECT * FROM sources WHERE id=?',(case['source_id'],));engine.validate_config(data,Path(source['path']))
        except Exception as e:raise HTTPException(400,'Perfil invalido: '+str(e))
        dest=s.data/'profiles'/f'{id}_{uuid.uuid4().hex}.json';dest.write_text(json.dumps(data,indent=2),encoding='utf-8')
        db.execute("UPDATE cases SET profile_path=?,status='ready_to_generate' WHERE id=?",(str(dest),id));return {'ok':True}
    @app.post('/api/cases/{id}/generate')
    def generate(id:str,body:GenerationBody|None=None):
        case=db.one('SELECT * FROM cases WHERE id=?',(id,))
        if not case:raise HTTPException(404,'Caso no encontrado')
        if body and body.fresh_start and s.agent_harness!='codex':
            raise HTTPException(409,'La construcción nueva con revisión requiere activar el agente Codex.')
        try:return {'job_id':db.queue_segment(id,fresh_start=bool(body and body.fresh_start))}
        except ValueError as e:raise HTTPException(409,str(e))
    @app.post('/api/cases/{id}/plan')
    def plan(id:str):
        if not db.one('SELECT id FROM cases WHERE id=?',(id,)):raise HTTPException(404)
        try:return {'job_id':db.queue_plan(id)}
        except ValueError as e:raise HTTPException(409,str(e))
    @app.post('/api/cases/{id}/redesign')
    def redesign(id:str):
        if not db.one('SELECT id FROM cases WHERE id=?',(id,)):raise HTTPException(404,'Caso no encontrado')
        try:
            with db.db() as connection:
                connection.execute('BEGIN IMMEDIATE')
                if not connection.execute("SELECT id FROM feedback WHERE case_id IN (?, 'general') AND status IN ('correction','rejected')",(id,)).fetchone():
                    raise HTTPException(400,'Guarda una corrección del trabajo o un criterio general antes de rediseñar.')
                job_id=db.queue_segment(id,connection)
        except ValueError as e:raise HTTPException(409,str(e))
        return {'job_id':job_id,'case_id':id}
    @app.get('/api/cases/{id}/versions')
    def versions(id:str):
        if not db.one('SELECT id FROM cases WHERE id=?',(id,)):raise HTTPException(404,'Caso no encontrado')
        return db.rows("SELECT * FROM jobs WHERE kind='segment' AND target=? ORDER BY created DESC,id DESC",(id,))
    @app.get('/api/jobs/{id}/files')
    def files(id:str):
        if not db.one('SELECT id FROM jobs WHERE id=?',(id,)):raise HTTPException(404)
        root=s.data/'runs'/id/'outputs'
        checkpoint=root/'Agente/Borrador_no_aprobado.json'
        try:
            saved=json.loads(checkpoint.read_text(encoding='utf-8'))
            selected=saved.get('attempt') if isinstance(saved,dict) else None
            if type(selected) is not int:selected=None
        except (OSError,ValueError):selected=None
        return result_file_groups([{'name':p.name,'path':str(p.relative_to(root)).replace('\\','/'),'size':p.stat().st_size} for p in root.rglob('*') if p.is_file()],selected)
    @app.get('/api/jobs/{id}/progress')
    def progress(id:str):
        job=db.one("SELECT * FROM jobs WHERE id=? AND kind='segment'",(id,))
        if not job:raise HTTPException(404,'Segmentación no encontrada')
        return job_progress(s.data,job)
    @app.get('/api/jobs/{id}/file/{name:path}')
    def result_file(id:str,name:str):
        root=(s.data/'runs'/id/'outputs').resolve();path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise HTTPException(404)
        return FileResponse(path,filename=path.name)
    @app.post('/api/feedback')
    def feedback(body:Feedback):
        if body.status not in {'correction','approved','rejected'}:raise HTTPException(400,'Estado invalido')
        if not body.author.strip() or not body.text.strip():raise HTTPException(400,'Indica el técnico y la corrección')
        if body.case_id!='general' and not db.one('SELECT id FROM cases WHERE id=?',(body.case_id,)):raise HTTPException(404,'Caso no encontrado')
        if body.request_plan and body.request_generation:raise HTTPException(400,'Elige análisis o generación, no ambos')
        if (body.request_plan or body.request_generation) and (body.case_id=='general' or body.status=='approved'):raise HTTPException(400,'La nueva versión requiere una corrección o rechazo de un caso concreto')
        if body.request_generation and db.one("SELECT id FROM jobs WHERE kind='segment' AND target=? AND status IN ('queued','running')",(body.case_id,)):
            raise HTTPException(409,'Ya hay una segmentación en curso. Puedes guardar la observación y generar otra versión cuando termine.')
        attachments=list(dict.fromkeys(body.attachment_ids))
        if any(not db.one('SELECT id FROM sources WHERE id=?',(id,)) for id in attachments):raise HTTPException(400,'Uno de los adjuntos no está registrado; vuelve a subirlo')
        if body.request_plan and db.one("SELECT id FROM jobs WHERE kind='plan' AND target=? AND status IN ('queued','running')",(body.case_id,)):
            raise HTTPException(409,'Ya hay una revisión en curso. Guarda la corrección y pide otra revisión cuando termine.')
        if body.status=='approved':
            latest=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=? ORDER BY created DESC LIMIT 1",(body.case_id,))
            if body.case_id=='general' or not latest or latest['status']!='done':raise HTTPException(400,'Aprobar requiere que la ultima generacion del caso haya terminado')
        else:latest=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=? ORDER BY created DESC LIMIT 1",(body.case_id,))
        recorded=body.text+(('\nEjecucion asociada: '+latest['id']) if latest else '')
        id=uuid.uuid4().hex
        text=f'Tecnico: {body.author}\nAmbito: {body.case_id}\nEstado: {body.status}\nCorreccion aportada por el laboratorio: {recorded}\nNo extrapolar medidas de un caso a otros sin medir.'
        file=s.data/'derived'/f'feedback_{id}.txt';file.write_text(text,encoding='utf-8');source,_=ingest.register(file,'Correccion laboratorio '+id[:8]);chunks=ingest.text_chunks(text,'correccion_tecnico');rag.enrich(chunks);db.add_chunks(source['id'],chunks);db.execute("UPDATE sources SET status='ready',detail='Correccion registrada con autor y ambito' WHERE id=?",(source['id'],))
        plan_id=None
        try:
            with db.db() as connection:
                connection.execute('BEGIN IMMEDIATE')
                connection.execute('INSERT INTO feedback VALUES(?,?,?,?,?,?)',(id,body.case_id,body.author.strip(),recorded,body.status,time.time()))
                connection.executemany('INSERT INTO feedback_attachments VALUES(?,?)',[(id,sid) for sid in attachments])
                if body.request_plan:plan_id=db.queue_plan(body.case_id,connection)
                if body.request_generation:plan_id=db.queue_segment(body.case_id,connection)
                connection.execute('INSERT INTO feedback_details VALUES(?,?,?,?)',(id,source['id'],latest['id'] if latest else None,plan_id))
                if body.case_id!='general':
                    status=body.status if body.status in {'approved','rejected'} else 'changes_requested'
                    # Preserve an active geometry job's state; its result will still require review.
                    connection.execute("UPDATE cases SET status=? WHERE id=? AND status NOT IN ('generating','preparing','queued')",(status,body.case_id))
        except ValueError as e:raise HTTPException(409,str(e))
        return {'id':id,'job_id':plan_id}
    @app.get('/api/feedback')
    def list_feedback():return db.feedback_rows()
    return app
