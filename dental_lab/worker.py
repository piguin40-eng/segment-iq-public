import subprocess,threading,time,json,uuid,traceback,shutil,os
from pathlib import Path
from .ingest import ALLOWED
from .revisions import compare_profiles,engine_digest,compare_meshes
from . import lab_workflow

BACKGROUND_PROCESS={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}

class NoGeometryChange(RuntimeError):
    pass

class DraftNeedsReview(RuntimeError):
    """A measured draft exists, but the design has not been accepted."""
    pass

class Worker:
    def __init__(self,s,db,ingest):self.s=s;self.db=db;self.ingest=ingest;self.stop=threading.Event();self.thread=None;self.seen={};self.indexed={};self.scan_at=0

    def start(self):
        self.db.execute("UPDATE jobs SET status='interrupted',detail='El servicio se reinicio durante el trabajo' WHERE status='running'")
        self.db.execute("UPDATE cases SET status='interrupted' WHERE status IN ('preparing','generating') AND id IN (SELECT target FROM jobs WHERE kind='segment' AND status='interrupted')")
        self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()

    def loop(self):
        while not self.stop.is_set():
            if time.time()>self.scan_at:
                try:self.scan()
                except Exception:traceback.print_exc()
                self.scan_at=time.time()+15
            job=self.db.one("SELECT * FROM jobs WHERE status='queued' ORDER BY CASE WHEN kind='segment' THEN 0 ELSE 1 END,created LIMIT 1")
            if not job:self.stop.wait(1);continue
            self.db.update_job(job['id'],'running')
            try:
                if job['kind']=='index':detail=self.ingest.process(job['target'])
                elif job['kind']=='segment':detail=self.segment(job)
                elif job['kind']=='plan':detail=self.plan(job)
                else:raise ValueError('Tipo de trabajo desconocido')
                self.db.update_job(job['id'],'done',detail)
            except NoGeometryChange as e:
                self.db.update_job(job['id'],'unchanged',str(e))
            except DraftNeedsReview as e:
                self.db.update_job(job['id'],'needs_review',str(e))
                self.db.execute("UPDATE cases SET status='needs_review' WHERE id=?",(job['target'],))
            except Exception as e:
                self.db.update_job(job['id'],'failed',str(e))
                if job['kind']=='segment':self.db.execute("UPDATE cases SET status='failed' WHERE id=?",(job['target'],))
                traceback.print_exc()

    def scan(self):
        # Observe stable size/mtime across scans so incomplete network copies are not indexed.
        for p in (self.s.data/'inbox').rglob('*'):
            if not p.is_file() or p.suffix.lower() not in ALLOWED:continue
            st=p.stat();signature=(st.st_size,st.st_mtime_ns);key=str(p)
            previous=self.seen.get(key);self.seen[key]=signature
            if previous!=signature or self.indexed.get(key)==signature:continue
            source,new=self.ingest.register(p)
            if new:self.db.job('index',source['id'])
            self.indexed[key]=signature

    def plan(self,job):
        case=self.db.one('SELECT * FROM cases WHERE id=?',(job['target'],))
        source=self.db.one('SELECT * FROM sources WHERE id=?',(case['source_id'],))
        if not self.s.geometry_python:raise ValueError('Python de geometria no configurado')
        folder=self.s.data/'runs'/job['id']/'outputs';folder.mkdir(parents=True)
        workflow=lab_workflow.load_workflow(self.s.app)
        lab_workflow.snapshot(workflow,folder/'Protocolo_obligatorio','analysis_only')
        measures=folder/'Medidas_STL.json'
        subprocess.run([self.s.geometry_python,str(self.s.app/'engine/inspect_stl.py'),source['path'],str(measures)],check=True,timeout=300,**BACKGROUND_PROCESS)
        text=measures.read_text(encoding='utf-8')
        question='Preparar segmentacion del caso '+case['name']+'. Medidas reales del STL: '+text+'. Recupera el patron del laboratorio y plantea las etapas y mediciones locales que faltan. Da prioridad a altura, profundidad, cobertura distal y conexiones. No inventes valores ni afirmes que estas medidas bastan para fabricar. No generes codigo ejecutable.'
        evidence,history=self.plan_evidence(job)
        (folder/'Historial_de_la_revision.json').write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
        if history['feedback']:
            question+=' En las fuentes se incluyen las correcciones de este caso y criterios generales existentes al solicitar esta revisión, con autor y fecha. Explica qué ajustar según las indicaciones más recientes y qué falta medir. Si hay contradicciones, indícalas. Los adjuntos son referencias para comparar, nunca geometrías para copiar. Esta revisión prepara un plan: no modifica aún el STL ni el perfil.'
        question+=' Protocolo obligatorio del laboratorio, que debes considerar por etapas sin afirmar ejecución: '+\
            workflow['files']['SKILL.md']
        response=self.ingest.rag.chat(question,case_sources=evidence)
        (folder/'Plan_del_agente.md').write_text(response['answer'],encoding='utf-8');(folder/'Fuentes_del_plan.json').write_text(json.dumps(response['citations'],indent=2),encoding='utf-8')
        if response['mode']!='RAG local':raise ValueError('El resumen del modelo no ha superado los controles; medidas y fuentes conservadas para revisar.')
        return 'Análisis y fuentes preparados. La segmentación se ejecuta desde el STL por su propia cola; este análisis no modifica la geometría ni su estado.'

    def plan_evidence(self,job):
        snapshot=self.db.one('SELECT feedback_ids FROM plan_context WHERE job_id=?',(job['id'],))
        ids=json.loads(snapshot['feedback_ids']) if snapshot else [r['id'] for r in self.db.rows("SELECT id FROM feedback WHERE case_id IN (?, 'general') AND created<=? ORDER BY created DESC",(job['target'],job['created']))]
        feedback={r['id']:r for r in self.db.feedback_rows() if r['case_id'] in {job['target'],'general'}}
        rows=[feedback[id] for id in ids if id in feedback]
        # Bound model context, while preserving the complete snapshot for audit/download.
        selected=[r for r in rows if r['case_id']==job['target']][:8]+[r for r in rows if r['case_id']=='general'][:2]
        evidence=[];seen=set()
        for row in selected:
            detail=self.db.one('SELECT source_id FROM feedback_details WHERE feedback_id=?',(row['id'],))
            source_id=detail['source_id'] if detail else None
            if not source_id:
                legacy=self.db.one('SELECT id FROM sources WHERE name=?',('Correccion laboratorio '+row['id'][:8],))
                source_id=legacy['id'] if legacy else None
            scope='Este caso' if row['case_id']==job['target'] else 'Criterio general'
            evidence.append({'source_id':source_id,'name':f"{scope} · {row['author']} · {time.strftime('%Y-%m-%d %H:%M',time.localtime(row['created']))}",'text':f"Estado: {row['status']}. {row['text']}",'kind':'correccion_tecnico','source_kind':'document','start':None,'end':None,'frame':None})
        for row in selected:
            for attachment in row['attachments']:
                if attachment['id'] in seen or len(seen)>=4:continue
                seen.add(attachment['id'])
                chunks=self.db.rows('SELECT c.*,s.name,s.kind AS source_kind FROM chunks c JOIN sources s ON s.id=c.source_id WHERE source_id=? ORDER BY c.id LIMIT 1',(attachment['id'],))
                if chunks:
                    chunk=chunks[0];chunk.pop('vector',None);evidence.append(chunk)
                else:
                    evidence.append({'source_id':attachment['id'],'name':attachment['name'],'text':'Adjunto registrado sin contenido textual consultable. Debe inspeccionarse directamente; no se puede inferir su geometría o instrucciones. Estado: '+attachment['status'],'kind':'adjunto_sin_texto','source_kind':'document','start':None,'end':None,'frame':None})
        history={'case_id':job['target'],'feedback':rows,'model_context_feedback_ids':[r['id'] for r in selected],'model_context_attachment_ids':list(seen),'limits':'Contexto del modelo: 8 revisiones del caso, 2 generales, 4 adjuntos (primer fragmento), 1100 caracteres por fuente. Historial completo conservado aquí.','geometry_modified':False}
        return evidence,history

    def segment(self,job):
        if self.s.agent_harness == 'codex':
            from .harness import SegmentHarness
            return SegmentHarness(self,job).run()
        return self.segment_fixed(job)

    def segment_fixed(self,job):
        case=self.db.one('SELECT * FROM cases WHERE id=?',(job['target'],))
        if not case:raise ValueError('Caso no encontrado')
        source=self.db.one('SELECT * FROM sources WHERE id=?',(case['source_id'],))
        if not self.s.geometry_python:raise ValueError('Python de geometria no configurado')
        run=self.s.data/'runs'/job['id'];log=self.s.data/'logs'/(job['id']+'.log')
        preparation=self.s.data/'profiles'/job['id'];preparation.mkdir(parents=True,exist_ok=False)
        profile=preparation/'Perfil_automatico.json'
        self.db.execute("UPDATE cases SET status='preparing' WHERE id=?",(case['id'],))
        try:
            workflow=lab_workflow.load_workflow(self.s.app)
            lab_workflow.snapshot(workflow,preparation/'Protocolo_obligatorio','fixed_engine_reference_only')
            self.db.update_job(job['id'],'running','Midiendo orientación, asientos y trazado sobre el STL original')
            evidence,history=self.plan_evidence(job)
            references=self.ingest.rag.search('patron laboratorio tubos conos trazado altura barra remesh seguridad cemento retenciones',limit=8,exclude_feedback=True,semantic=False)
            (preparation/'Historial_de_la_version.json').write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
            (preparation/'Referencias_consultadas.json').write_text(json.dumps(evidence+references,ensure_ascii=False,indent=2),encoding='utf-8')
            for name in ('prepare_profile.py','connections.py','lab_rules.py'):
                script=self.s.app/'engine'/name
                if script.is_file():shutil.copy2(script,preparation/name)
            (preparation/'engine').mkdir()
            for name in ('bar_height.py','bar_centering.py','shape_refinement.py','trace_support.py'):
                shutil.copy2(self.s.app/'engine/engine'/name,preparation/'engine'/name)
            command=[self.s.geometry_python,str(self.s.app/'engine/prepare_profile.py'),'--input',source['path'],'--name',case['name'],'--output',str(profile),'--history',str(preparation/'Historial_de_la_version.json')]
            with log.open('w',encoding='utf-8') as f:
                try:
                    subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600,**BACKGROUND_PROCESS)
                except subprocess.CalledProcessError as error:
                    f.flush()
                    lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
                    message=next((line.split(': ',1)[1] for line in reversed(lines) if line.startswith(('ValueError: ','RuntimeError: '))), 'No se ha completado la medición geométrica. Revisa el diagnóstico conservado.')
                    raise RuntimeError(message) from error
                report=json.loads(profile.with_suffix('.medidas.json').read_text(encoding='utf-8'))
                previous=self.db.one("SELECT id FROM jobs WHERE kind='segment' AND target=? AND status='done' AND created<? ORDER BY created DESC LIMIT 1",(case['id'],job['created']))
                comparison=None
                if previous:
                    previous_run=self.s.data/'runs'/previous['id']
                    previous_profile=previous_run/'perfil_ejecutado.json'
                    if previous_profile.is_file():
                        before=json.loads(previous_profile.read_text(encoding='utf-8'))
                        after=json.loads(profile.read_text(encoding='utf-8'))
                        comparison=compare_profiles(before,after)
                        comparison['previous_job_id']=previous['id']
                        comparison['engine_changed']=engine_digest(previous_run/'Codigo/engine')!=engine_digest(self.s.app/'engine/engine')
                        report['redesign_comparison']=comparison
                        profile.with_suffix('.medidas.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                        if not comparison['geometry_parameters_changed'] and not comparison['engine_changed']:
                            raise NoGeometryChange('Las indicaciones no producen cambios geométricos respecto a la versión anterior. No se ha repetido una segmentación idéntica. Consulta las correcciones pendientes; la versión anterior sigue disponible.')
                self.db.execute("UPDATE cases SET profile_path=?,status='generating' WHERE id=?",(str(profile),case['id']))
                command=[self.s.geometry_python,str(self.s.app/'engine/ejecutar.py'),'--input',source['path'],'--profile',str(profile),'--run-dir',str(run),'--blender',self.s.blender]
                if self.s.b4d_root:command+=['--b4d-root',self.s.b4d_root]
                if self.s.live_blender:command+=['--live-blender']
                process=subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT,**BACKGROUND_PROCESS)
                started=time.monotonic();last=''
                try:
                    while process.poll() is None:
                        if time.monotonic()-started>7200 or self.stop.is_set():
                            raise RuntimeError('La ejecución se interrumpió; etapas y diagnóstico conservados')
                        # The executor flushes ETAPA lines; reading the log avoids a blocked pipe.
                        lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
                        step=next((line for line in reversed(lines) if line.startswith('ETAPA ')),None)
                        if step and step!=last:
                            number=int(step.split()[1].split('/')[0])
                            stages=['Orientación del STL','Conexiones y ejes','Trazado y diseño de barra','Unión de barra y conos','Remallado, seguridad y cemento','Separación primaria y supra','Superficie para retenciones','Construcción de retenciones','Aplicación y protección de conexiones','Limpieza de malla','Medición y exportación','Escena y vista de la propuesta','Comprobación de archivos finales']
                            self.db.update_job(job['id'],'running',f'Paso {number}/13 · '+stages[number-1]);last=step
                        self.stop.wait(1)
                    if process.returncode:
                        f.write(f'\nEXECUTOR_EXIT_CODE {process.returncode}\n');f.flush()
                        progress_file=run/'outputs/Proceso/progreso.json'
                        progress=json.loads(progress_file.read_text(encoding='utf-8')) if progress_file.exists() else {}
                        number=progress.get('current_step')
                        detail='No se completó la propuesta'+(f' en el paso {number}' if number else '')+'. '
                        records=sorted((run/'logs').glob('[0-9][0-9]_*.py.log')) if (run/'logs').exists() else []
                        if progress.get('error') and not progress['error'].startswith('Command '):
                            detail+=progress['error']
                        elif records:
                            lines=records[-1].read_text(encoding='utf-8',errors='replace').splitlines()
                            detail+=next((line.split(': ',1)[-1] for line in reversed(lines) if line.startswith(('ValueError: ','RuntimeError: '))), 'Consulta la etapa y su diagnóstico en el visor.')
                        raise RuntimeError(detail)
                finally:
                    if process.poll() is None:
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False) if __import__('os').name=='nt' else process.terminate()
            state=json.loads((run/'Ejecucion.json').read_text())
            if state['status']!='GEOMETRY_PASS_DESIGN_REVIEW_PENDING':raise ValueError('No ha superado controles')
            report=json.loads(profile.with_suffix('.medidas.json').read_text(encoding='utf-8'))
            report['lab_workflow']=lab_workflow.receipt(workflow,'fixed_engine_reference_only')
            report.setdefault('corrections_pending',[]).append({'text':'Revisar el protocolo obligatorio del vídeo por etapas',
                'reason':'El motor fijo conserva la referencia, pero no interpreta la skill ni acredita su cumplimiento; usar el agente Codex para la planificación y revisión por etapas.'})
            profile.with_suffix('.medidas.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            if comparison:
                old_validation=previous_run/'outputs/Inferior_independiente/Validacion_PROPIA.json'
                new_validation=run/'outputs/Inferior_independiente/Validacion_PROPIA.json'
                if old_validation.is_file() and new_validation.is_file():
                    comparison['mesh_volumes']=compare_meshes(json.loads(old_validation.read_text(encoding='utf-8')),json.loads(new_validation.read_text(encoding='utf-8')))
                    report['redesign_comparison']=comparison
                    profile.with_suffix('.medidas.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            pending=len(report.get('corrections_pending',[]))
            review=['# Propuesta automática para revisión','',f"Conexiones medidas: {len(report['connections'])}.",'','Entrada geométrica: exclusivamente el STL original, identificado por su hash.','',*report['assumptions'],'','## Correcciones aplicadas',json.dumps(report['corrections_applied'],ensure_ascii=False,indent=2),'','## Indicaciones pendientes de interpretar',json.dumps(report['corrections_pending'],ensure_ascii=False,indent=2),'','Las fuentes recuperadas documentan el patrón y el historial. No se ejecuta código de documentos ni se importan sus geometrías. La recuperación de vídeos no modifica por sí sola los parámetros del motor.']
            (preparation/'Revision_de_la_propuesta.md').write_text('\n'.join(review),encoding='utf-8')
            self.db.execute("UPDATE cases SET status='review_pending' WHERE id=?",(case['id'],))
            return 'Propuesta generada desde el STL original; revisar diseño, altura y cobertura.'+(f' {pending} indicaciones requieren interpretación y están señaladas en el informe.' if pending else '')
        except NoGeometryChange as e:
            self.db.execute("UPDATE cases SET status='review_pending' WHERE id=?",(case['id'],))
            (preparation/'Diagnostico.txt').write_text(str(e),encoding='utf-8')
            raise
        except Exception as e:
            self.db.execute("UPDATE cases SET status='failed' WHERE id=?",(case['id'],))
            (preparation/'Diagnostico.txt').write_text(str(e)+'\n\n'+(log.read_text(encoding='utf-8',errors='replace')[-16000:] if log.exists() else ''),encoding='utf-8')
            raise
        finally:
            output=run/'outputs'/'Preparacion';output.mkdir(parents=True,exist_ok=True)
            for p in preparation.iterdir():
                if p.is_file():shutil.copy2(p,output/p.name)
                elif p.is_dir():shutil.copytree(p,output/p.name,dirs_exist_ok=True)
            if (run/'logs').exists():shutil.copytree(run/'logs',output/'Registros',dirs_exist_ok=True)
