"""Codex plans/edits a case; a separate supervisor owns execution and acceptance.

Case geometry adapters never replace the installed application or its validators.
The source STL, connection measurements and tolerances are immutable to the agent.
"""
import ast
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import time

from .revisions import compare_profiles, compare_meshes, engine_digest
from . import lab_workflow
from .processes import owned_session,stop_owned_process

BACKGROUND = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
EDITABLE_CODE = {'shape_refinement.py', 'bar_height.py', 'case_geometry.py', 'occlusal_safety.py'}
EDITABLE_PROFILE = {'trace_xy', 'bar_top_z', 'bar_plane', 'cone_top_z',
                    'cone_top_overrides', 'anterior_raise_mm', 'shape_refinement',
                    'adaptation_notes','retention_mode'}
ALLOWED_IMPORTS = {'numpy', 'scipy', 'math', 'trimesh', 'manifold3d', 'bar_centering', 'bar_height',
                   'case_geometry', 'shape_refinement', 'design_checks', 'connection_protection', 'lateral_safety'}
FORBIDDEN_NAMES = {'eval', 'exec', 'compile', 'open', 'input', 'getattr', 'setattr',
                   'delattr', 'globals', 'locals', 'vars', 'dir', 'type', '__import__',
                   'breakpoint', 'help', 'memoryview'}
FORBIDDEN_ATTRS = {'load', 'save', 'savez', 'savez_compressed', 'loadtxt', 'savetxt',
                   'fromfile', 'tofile', 'memmap', 'ctypes', 'ctypeslib', 'f2py',
                   'lib', 'test', 'load_library', 'system', 'popen', 'read', 'write', 'export',
                   'load_mesh', 'load_path', 'load_scene', 'export_mesh'}

# Exact, reviewed migrations: contact repair and local shoulder measurement.
# Numerical case adapters keep their interface; the NEW immutable retention
# module and all current validators are installed in the next workspace.
RETENTION_CONTACT_MIGRATION = (
    'cdf05f73208c1e79666ab18442d0dfd0663fb29e71932f02d2da978e398f37ad',
    '1c458047bad655cde277305fbd15b888903b225ca5073aa653de78c9fbd3ea3c')
ADAPTER_COMPATIBLE_UPDATES = {'retention_safety.py':RETENTION_CONTACT_MIGRATION,
    'bar_centering.py':('d574dd002aa708b60dbf055fabcf63a08eda6f5ed7d308f800b37bf01777c52a',
                        'de84490226fa72cc9e574ea2929ba6416ab7703c2cb32b88502ff619aa246438')}
ORIENTED_MATERIAL_MIGRATION = (
    '2c1cfc37f68c901dfcafd9debbf0baddf809524b6255bede3da16f68e2c4debe',
    '3d7d4562925c8d20e176f02486b055a8821db9f7de34b7322542e7e58a72821b',
    'dcff4fb94f3ebba70dcdb211a2a71cee11bb1602f27f9debe7bec0cc047d5dd1')
RETENTION_MESH_MIGRATION = {
    '08_retenciones_duales.py':('6143b3d0740f83abf4315e06497849bdddfe31d8cc12f20102def4ec35e2c944',
                              '77e0dfb531a175ec4b6bf9c42c2e7de27526ffaf90903bddc31d72944bd55a7e'),
    '09_aplicar_retenciones.py':('960277d5f7fb96969f6a75d6c3a4b072bf47a5b9009d5459617743083467cc2f',
                               'c456cff53e385d78edebd3595a13d7a63f59a4a4bc2f36f8ce0e9b4c0251e783')}
RETENTION_MESH_HELPER = '1a9890c1882cb446ace39ba0cf4fab1aaa7fee42c1f5f4f03b702a4fdd72260f'
SUPRA_EXPORT_MIGRATION = {
    'mesh_export.py':('9ab65e79f7f6a07b774115df3f37d6328de47b1d5f91b814a157bd2c82682736',
                      'c1a85c9df52c7195c223d561c74263b78a3ead63e4dd142133a4ef3311a20e7d'),
    '10_limpieza_exportacion.py':('68d5f0c583eaaff1bc296f06b3eecff5cf7d814e3d732e8f173a76486278bef2',
                                 '275d2876a9d3df5ad8f3bfbcd6b126146bdc93c1b37d38bcf27f0db801724d60'),
    '11_validacion.py':('04bbcf35b2fd4c659848884715cea2bcaaee8249f72a7d36e8a25377b19e9eac',
                        'af3a244fd977e43af064930c56164676a3b2133d28141cad42b7b8a646276e0e'),
    '12_escena_final.py':('ad247ab4954efe7af289d70ab879b5b17bd9ead0714f6d17db96653b6400987e',
                         'e5c24be69ad481057ca2b647de3abd3dd8914318c0342c26be3517113762edcf')}


def adapter_engine_compatible(previous, current):
    if previous==current:return True
    if not previous:return False
    # Export-only migration: validation and scene use the same checked supra.
    # Copy current immutable code; inherit only validated numerical adapters.
    if all((previous.get(name),current.get(name))==pair for name,pair in SUPRA_EXPORT_MIGRATION.items()):
        comparable=dict(current)
        comparable.update({name:pair[0] for name,pair in SUPRA_EXPORT_MIGRATION.items()})
        return adapter_engine_compatible(previous,comparable)
    if set(previous)!=set(current):
        if (set(current)-set(previous)=={'retention_mesh.py'} and not set(previous)-set(current)
                and current.get('retention_mesh.py')==RETENTION_MESH_HELPER
                and all((previous.get(name),current.get(name))==pair
                        for name,pair in RETENTION_MESH_MIGRATION.items())):
            comparable=dict(current);comparable.pop('retention_mesh.py')
            comparable.update({name:pair[0] for name,pair in RETENTION_MESH_MIGRATION.items()})
            return adapter_engine_compatible(previous,comparable)
        old,new,helper=ORIENTED_MATERIAL_MIGRATION
        # Exact measurement-only update. Recover editable recipes, never old
        # validators or approval; every new execution uses current checks.
        if (set(current)-set(previous)=={'ray_material.py'} and not set(previous)-set(current)
                and previous.get('design_checks.py')==old
                and current.get('design_checks.py')==new
                and current.get('ray_material.py')==helper):
            comparable=dict(current);comparable.pop('ray_material.py')
            comparable['design_checks.py']=old
            return adapter_engine_compatible(previous,comparable)
        return False
    changed={name for name in previous if previous[name]!=current[name]}
    return all(name in ADAPTER_COMPATIBLE_UPDATES and
        (previous[name],current[name])==ADAPTER_COMPATIBLE_UPDATES[name] for name in changed)


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(tmp, path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


class AgentServiceBusy(RuntimeError):
    """Explicit transient capacity rejection from Codex, not a geometry error."""


class AdapterValidationError(ValueError):
    """An editable numerical adapter needs repair before it can execute."""


def cli_error_message(log):
    for line in reversed(Path(log).read_text(encoding='utf-8',errors='replace').splitlines()):
        try: event=json.loads(line)
        except ValueError: continue
        if not isinstance(event,dict): continue
        if event.get('type')=='turn.failed':
            failure=event.get('error',{})
            message=failure.get('message','') if isinstance(failure,dict) else ''
        elif event.get('type')=='error': message=event.get('message','')
        else: continue
        if isinstance(message,str) and message: return message[:1400]
    return ''


def tool_error_summary(log):
    """Keep the full traceback in the log, a readable cause in the case viewer."""
    lines=Path(log).read_text(encoding='utf-8',errors='replace').splitlines()
    for line in reversed(lines):
        match=re.match(r'^(?:ValueError|TypeError|SyntaxError|ImportError|ModuleNotFoundError|RuntimeError|FileNotFoundError|OSError|MemoryError):\s*(.+)',line)
        if match:return 'No se completó la etapa. '+match[1][:1200]+' Registro completo conservado.'
    message=cli_error_message(log)
    if message:return 'Codex no pudo continuar: '+message+' Registro: '+Path(log).name
    return 'La herramienta terminó con error. Consulta el registro '+Path(log).name+' del intento para ver el diagnóstico completo.'


def find_codex(settings):
    if settings.codex_executable and Path(settings.codex_executable).is_file():
        return settings.codex_executable
    found = shutil.which('codex')
    if found:
        return found
    from .platform_paths import codex_candidates
    candidates = [p for p in codex_candidates() if p.is_file()]
    return str(max(candidates, key=lambda p: p.stat().st_mtime)) if candidates else None


def validate_adapter(path):
    """Restrict case adapters to numerical geometry, not file/process automation.

    This check is an additional policy, not a general Python security sandbox.
    Codex itself runs with its workspace-write sandbox, never full-access.
    """
    try:
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    except SyntaxError as error:
        raise AdapterValidationError(f'Sintaxis inválida en {path.name}, línea {error.lineno}: {error.msg}') from error
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module or '']
            if any(name.split('.')[0] not in ALLOWED_IMPORTS for name in names) or getattr(node, 'level', 0):
                raise AdapterValidationError('El adaptador solo admite bibliotecas de geometría: '+path.name+': '+', '.join(names))
            if any(part in FORBIDDEN_ATTRS or part.startswith('_') for name in names for part in name.split('.')):
                raise AdapterValidationError('Import no numérico en '+path.name+': '+', '.join(names))
            if isinstance(node,ast.ImportFrom) and any(n.name in FORBIDDEN_ATTRS or n.name.startswith('_') or n.name=='*' for n in node.names):
                raise AdapterValidationError('Import no numérico en '+path.name+': '+', '.join(n.name for n in node.names))
        if isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or node.id.startswith('__')):
            raise AdapterValidationError('Operación ajena a la geometría en '+path.name+': '+node.id)
        if isinstance(node, ast.Attribute) and (node.attr.startswith('_') or node.attr in FORBIDDEN_ATTRS):
            raise AdapterValidationError('Acceso ajeno a la geometría en '+path.name+': '+node.attr)


def validate_candidate(base, candidate, engine, manifest):
    changed = {k for k in set(base)|set(candidate) if base.get(k) != candidate.get(k)}
    if changed - EDITABLE_PROFILE:
        raise ValueError('Se intentaron cambiar medidas o controles protegidos: '+', '.join(sorted(changed-EDITABLE_PROFILE)))
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Parámetro no finito')
        if isinstance(value, list):
            for v in value: finite(v)
        if isinstance(value, dict):
            for v in value.values(): finite(v)
    finite(candidate)
    if candidate.get('retention_mode','dual_required') not in {'none','dual_optional','dual_required'}:
        raise ValueError('Modo de retenciones no reconocido')
    for key in ('bar_top_z', 'cone_top_z'):
        if abs(candidate[key]-base[key]) > 2:
            raise ValueError('Cambio de altura mayor de 2 mm por intento; requiere una adaptación específica')
    shape = candidate.get('shape_refinement', {})
    if not 0 <= shape.get('cervical_bevel_mm', 0) <= .5:
        raise ValueError('Bisel fuera del intervalo de propuestas ensayable (0–0,5 mm)')
    if not 0 <= shape.get('bar_narrowing_per_side_mm', 0) <= .8:
        raise ValueError('Afinado fuera del intervalo ensayable')
    if not isinstance(candidate['trace_xy'], list) or not 6 <= len(candidate['trace_xy']) <= 4000:
        raise ValueError('Trazado inválido')
    if any(not isinstance(p, list) or len(p)!=2 or any(not isinstance(v,(int,float)) for v in p) for p in candidate['trace_xy']):
        raise ValueError('El trazado requiere coordenadas XY finitas')
    current = engine_digest(engine)
    for name in set(manifest)|set(current):
        if manifest.get(name) != current.get(name):
            if name not in EDITABLE_CODE or name not in current:
                raise ValueError('El agente cambió una etapa o un verificador protegido: '+name)
            validate_adapter(engine/name)
    return sorted(changed)


def response_schema():
    props = {'decision': {'type':'string','enum':['run','accept','retry','unchanged','blocked']},
             'summary': {'type':'string'}, 'changes': {'type':'array','items':{'type':'string'}},
             'pending': {'type':'array','items':{'type':'string'}},
             'resolved_pending': {'type':'array','items':{'type':'string'}},
             'evidence': {'type':'array','items':{'type':'string'}},
             'lab_workflow': lab_workflow.answer_schema()}
    return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}


def remaining_pending(base_report,review):
    resolved=set(review.get('resolved_pending',[]))
    result=[]
    for row in base_report.get('corrections_pending',[]):
        text=row.get('text','')
        protected=bool(re.search(r'romp|fractur|resisten|inserci|fragil|frágil|rotura|espesor|grosor',text,re.I))
        if text not in resolved or protected: result.append(row)
    seen={r['text'] for r in result}
    for text in review.get('pending',[]):
        if text not in seen:
            result.append({'text':text,'reason':'Pendiente tras revisión del agente'});seen.add(text)
    return result


def result_evidence(root):
    """Locate the actual previous proposal, not just its profile or failed retries."""
    root=Path(root)
    return {'job_id':root.name,
            'reports_read_only':[str(p.resolve()) for p in sorted((root/'outputs/Inferior_independiente').glob('*.json')) if p.is_file()],
            'meshes_read_only':[str(p.resolve()) for p in sorted((root/'outputs/Inferior_independiente').glob('*.stl')) if p.is_file()],
            'working_meshes_read_only':[str(p.resolve()) for name in ('Primaria_final.npz','Supra.npz')
                                       if (p:=root/'work/inf_independiente'/name).is_file()],
            'coordinate_note':'Los STL exportados están en coordenadas originales; las mallas NPZ están en coordenadas de trabajo. Usar raw_to_work antes de comparar secciones.'}


def resumable_draft(root, source_hash, manifest):
    """Recover editable work, never approval, from a measured but unapproved attempt."""
    root=Path(root)
    metadata=root/'outputs/Agente'
    baseline=read(metadata/'Perfil_base.json',{})
    if not baseline or baseline.get('source_sha256')!=source_hash:
        return None
    if not adapter_engine_compatible(read(metadata/'Motor_instalado.json',{}),manifest):
        return None
    for attempt in sorted((root/'outputs/Intentos').glob('[0-9][0-9]'),reverse=True):
        output=attempt/'outputs/Inferior_independiente'
        execution=read(attempt/'Ejecucion.json',{})
        profile=read(attempt/'perfil_ejecutado.json',{})
        controls=read(output/'Resultado_controles.json',{})
        if execution.get('status')!='GEOMETRY_PASS_DESIGN_REVIEW_PENDING': continue
        if execution.get('source_sha256')!=source_hash or profile.get('source_sha256')!=source_hash: continue
        if controls.get('geometry_checks')!='PASS': continue
        if not read(output/'Validacion_PROPIA.json',{}): continue
        if not (attempt/'Codigo/engine').is_dir(): continue
        arch=profile.get('arch',baseline.get('arch','SUP'))
        if arch not in {'SUP','INF'} or ('arch' in baseline and arch!=baseline['arch']): continue
        names=(f'Primaria_{arch}_PROPIA.stl',f'Supra_{arch}_PROPIA.stl','Vista_propia.png')
        if not all((output/name).is_file() for name in names): continue
        review=read(metadata/(attempt.name+'_review.json'),{})
        return {'root':attempt,'metadata_root':root,'job_id':root.name,'attempt':int(attempt.name),
                'approval':'draft_needs_review','review':review}
    return None


def planning_evidence(directory, workspace, source_hash, manifest, baseline=None):
    """Expose interrupted measurements for review, never inherit executable work."""
    directory=Path(directory); workspace=Path(workspace)
    previous=read(directory/'Perfil_base.json',{})
    if previous.get('source_sha256')!=source_hash:
        return None
    if baseline is not None and any(previous.get(key)!=baseline.get(key) for key in
            ('connections','raw_to_work','expected_connections','expected_euler','minimum_supra_mm')):
        return None
    if read(directory/'Motor_instalado.json',{})!=manifest:
        return None
    if not (workspace/'original.stl').is_file() or digest(workspace/'original.stl')!=source_hash:
        return None
    files=sorted({p for pattern in ('Medicion_plan*.json','Trazado_propuesto.json','Cambios_plan.json','plan_*.py')
                  for p in workspace.glob(pattern) if p.is_file() and p.stat().st_size<=2_000_000})[:20]
    if not files: return None
    return {'files_read_only':[str(p.resolve()) for p in files],
            'scope':'Mediciones y propuestas de PLAN sin construir ni aprobar. Revisar contra el perfil actual; no ejecutar scripts ni heredar trazados automáticamente.'}


def planning_log_summary(log):
    """Bound the context of a timed out CLI run; omit raw command output."""
    log=Path(log)
    if not log.is_file(): return []
    with log.open('rb') as stream:
        stream.seek(max(0,log.stat().st_size-256_000))
        lines=stream.read().decode('utf-8',errors='replace').splitlines()
    result=[]
    for line in lines:
        try: event=json.loads(line)
        except ValueError: continue
        item=event.get('item',{})
        if item.get('type')=='agent_message' and item.get('text'):
            result.append(item['text'][:1400])
        elif event.get('type')=='item.completed' and item.get('type')=='command_execution' and item.get('exit_code'):
            result.append('Comando fallido: '+item.get('command','')[:400])
    return result[-6:]


def recoverable_plan(directory, workspace, baseline, manifest, workflow_hash, feedback):
    """Recover a saved numerical recipe, never approval or old immutable code."""
    directory=Path(directory);workspace=Path(workspace)
    interrupted=any(read(p,{}).get('phase')=='plan' for p in directory.glob('*_Interrupcion.json'))
    planned=any(read(p,{}).get('decision')=='run' for p in directory.glob('[0-9][0-9]_plan.json'))
    if not (interrupted or planned):return None
    previous=read(directory/'Perfil_base.json',{})
    # New measurements or corrections always require a new PLAN.
    comparable=lambda p:{k:v for k,v in p.items() if k!='input'}
    if not previous or comparable(previous)!=comparable(baseline):return None
    old_manifest=read(directory/'Motor_instalado.json',{})
    if not adapter_engine_compatible(old_manifest,manifest):return None
    if read(directory/'Estado.json',{}).get('lab_workflow',{}).get('sha256')!=workflow_hash:return None
    if read(directory/'Historial_de_la_version.json',{}).get('feedback')!=feedback:return None
    original=workspace/'original.stl'
    if not original.is_file() or digest(original)!=baseline.get('source_sha256'):return None
    candidate=read(workspace/'Perfil.json',{})
    try:
        changed=validate_candidate(previous,candidate,workspace/'engine/engine',old_manifest)
    except (ValueError,SyntaxError,OSError,TypeError):return None
    if not (set(changed)-{'adaptation_notes'}) and engine_digest(workspace/'engine/engine')==old_manifest:return None
    return {'workspace':workspace,'profile':candidate,'job_id':directory.parent.parent.name,
            'approval':'NONE','origin':'interrupted_agent_candidate' if interrupted else 'saved_agent_candidate'}


class SegmentHarness:
    def __init__(self, worker, job):
        self.w=worker; self.s=worker.s; self.db=worker.db; self.job=job
        self.root=self.s.data/'runs'/job['id']
        self.out=self.root/'outputs/Agente'
        self.workspace=self.s.data/'agent_work'/job['id']
        self.state={'provider':'Codex','status':'preparing','attempt':0,'events':[],
                    'max_attempts':min(3,max(1,self.s.agent_max_attempts)),
                    'design_review':'PENDING'}

    def event(self, text, status=None):
        if status: self.state['status']=status
        self.state['detail']=text
        self.state['events'].append({'time':time.time(),'text':text})
        self.state['events']=self.state['events'][-40:]
        write(self.out/'Estado.json',self.state)
        self.db.update_job(self.job['id'],'needs_review' if status=='needs_review' else 'running',text)

    def process(self, command, log, timeout, cwd=None, prompt=None, env=None, events=False):
        started=time.monotonic()
        env=dict(os.environ if env is None else env)
        env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        with log.open('w',encoding='utf-8') as stream:
            process=subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.PIPE if prompt else subprocess.DEVNULL,
                                     stdout=stream,stderr=subprocess.STDOUT,**BACKGROUND,**owned_session())
            try:
                if prompt:
                    process.stdin.write(prompt.encode('utf-8')); process.stdin.close()
                offset=0
                while process.poll() is None:
                    if self.w.stop.is_set():
                        raise InterruptedError('Ejecución detenida; diagnóstico conservado en '+log.name)
                    if time.monotonic()-started>timeout:
                        raise TimeoutError(f'{log.name}: se agotó el límite de {timeout} segundos; archivos y diagnóstico conservados')
                    if events:
                        with log.open(encoding='utf-8',errors='replace') as incoming:
                            incoming.seek(offset)
                            for line in iter(incoming.readline, ''):
                                try: item=json.loads(line).get('item',{})
                                except ValueError: continue
                                if item.get('type')=='agent_message' and item.get('text'):
                                    message=item['text'].strip()
                                    if not message.startswith('{'): self.event(message[:1400])
                            offset=incoming.tell()
                    self.w.stop.wait(1)
                if process.returncode:
                    message=cli_error_message(log) if events else ''
                    if re.search(r'model is at capacity|model.*temporarily unavailable|service.*overloaded',message,re.I):
                        raise AgentServiceBusy('El modelo de Codex está temporalmente saturado. Registro: '+log.name)
                    raise RuntimeError(tool_error_summary(log))
            finally:
                if process.poll() is None:
                    stop_owned_process(process)

    def think(self, phase, extra, images=()):
        codex=find_codex(self.s)
        if not codex: raise RuntimeError('Codex no está instalado. No se ha sustituido silenciosamente por el motor de reglas.')
        tag=f'{self.state["attempt"]:02d}_{phase}'
        command=[codex,'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check',
                 '--sandbox','read-only' if phase=='review' else 'workspace-write','-c','approval_policy="never"','--json',
                 '-C',str(self.workspace),'--output-schema',str(self.workspace/'Respuesta.schema.json')]
        if os.name=='nt': command+=['-c','windows.sandbox="elevated"']
        for path in images[:5]: command+=['--image',str(path)]
        prompt=(self.s.app/'docs/HARNESS_PROMPT.md').read_text(encoding='utf-8')+'\n\n'+lab_workflow.prompt(self.workflow)+'\n\n'+extra
        timeout=min(1800,max(60,self.s.agent_timeout_seconds))
        if phase=='repair':timeout=min(timeout,240)
        # One bounded recovery in the SAME workspace. Do not discard useful
        # measurements or consume a Blender attempt for an interrupted PLAN.
        for recovery in range(2 if phase=='plan' else 1):
            if self.w.stop.is_set(): raise InterruptedError('Ejecución detenida antes de iniciar Codex')
            call_tag=tag+(f'_recuperacion{recovery}' if recovery else '')
            result=self.workspace/(call_tag+'.json')
            log=self.out/(call_tag+'.jsonl')
            limit=min(timeout,240) if recovery else timeout
            write(self.workspace/'Presupuesto_fase.json',{'phase':phase,'recovery':recovery,
                'deadline_unix':time.time()+limit,'timeout_seconds':limit,
                'initial_measurement_target_seconds':min(180,limit),
                'instruction':'PLAN acotado: comprobar secciones representativas, guardar cambios y devolver run para medir el resultado real en Blender. No repetir un barrido denso antes de construir.'})
            try:
                call_started=time.monotonic()
                for busy_retry in range(3):
                    busy_tag=call_tag+(f'_ocupado{busy_retry}' if busy_retry else '')
                    result=self.workspace/(busy_tag+'.json');log=self.out/(busy_tag+'.jsonl')
                    remaining=math.ceil(limit-(time.monotonic()-call_started))
                    if remaining<=0:raise TimeoutError('Se agotó el presupuesto de la fase '+phase)
                    try:
                        self.process(command+['-o',str(result),'-'],log,remaining,
                                     cwd=self.workspace,prompt=prompt,events=True)
                        break
                    except AgentServiceBusy:
                        if busy_retry==2:raise
                        delay=(10,30)[busy_retry]
                        self.event(f'Codex está temporalmente saturado; se conserva el trabajo y se reintentará en {delay} segundos ({busy_retry+1}/2)',
                                    'reviewing' if phase=='review' else 'planning')
                        if self.w.stop.wait(delay):raise InterruptedError('Ejecución detenida mientras esperaba a Codex')
                break
            except TimeoutError:
                checkpoint={'phase':phase,'attempt':self.state['attempt'],'log':log.name,
                    'messages':planning_log_summary(log),'geometry_launched':phase=='review',
                    'approval':'NONE','workspace_preserved':True}
                write(self.out/(call_tag+'_Interrupcion.json'),checkpoint)
                if phase!='plan' or recovery: raise
                write(self.workspace/'Plan_interrumpido.json',checkpoint)
                self.event('Agente · recuperando el plan guardado tras agotar el tiempo; aún no se ha construido la segmentación','planning')
                prompt+='\n\nRECUPERACIÓN DE PLAN: consulta Plan_interrumpido.json y Presupuesto_fase.json. '+\
                    'Los procesos de la llamada anterior ya se han detenido. Los archivos medidos siguen aquí. '+\
                    'Revisa lo conservado y termina el plan sin repetir barridos densos. Usa secciones representativas por lotes pequeños. '+\
                    'No reconstruyas antes de devolver run. Si los datos indispensables siguen faltando, devuelve blocked con la causa concreta; nunca inventes un PASS.'
        answer=read(result)
        if not isinstance(answer,dict) or answer.get('decision') not in response_schema()['properties']['decision']['enum']:
            raise ValueError('Codex no devolvió una decisión válida')
        for key in ('changes','pending','evidence','resolved_pending'):
            if not isinstance(answer.get(key),list) or not all(isinstance(x,str) for x in answer[key]):
                raise ValueError('Respuesta incompleta del agente: '+key)
        if not isinstance(answer.get('summary'),str): raise ValueError('Falta el resumen del agente')
        pending=lab_workflow.validate_answer(self.workflow,answer,'plan' if phase=='repair' else phase)
        answer['pending']=list(dict.fromkeys(answer['pending']+pending))
        write(self.out/(tag+'.json'),answer)
        self.event(answer['summary'])
        return answer

    def execute_attempt(self, command, run, log):
        """Return failed measurements to PLAN as well as successful ones to REVIEW."""
        try:
            build_error=None
            try:
                self.process(command,log,7200,cwd=self.workspace)
            except (InterruptedError,TimeoutError):
                raise
            except Exception as error:
                build_error=error
            completed_geometry=(run/'outputs/Inferior_independiente/Validacion_PROPIA.json').is_file()
            if (build_error is None or completed_geometry) and all((run/'work/inf_independiente'/name).is_file() for name in ('Primaria_final.npz','Supra.npz')):
                inspector=self.trusted/'inspect_insertion.py'
                if inspector.is_file():
                    try:
                        self.process([self.s.geometry_python,str(inspector),'--run-dir',str(run),
                            '--output',str(run/'outputs/Inferior_independiente/Comprobacion_extraccion.json')],
                            self.out/(run.name+'_Extraccion.log'),300,cwd=self.workspace)
                    except (InterruptedError,TimeoutError):raise
                    except Exception:
                        if build_error is None:raise
                walls=self.trusted/'inspect_walls.py'
                if walls.is_file() and (run/'work/inf_independiente/entrada.npz').is_file():
                    self.event('Agente · comprobando paredes laterales y extremos de la supra', 'executing')
                    try:
                        self.process([self.s.geometry_python,str(walls),'--run-dir',str(run),
                            '--output',str(run/'outputs/Inferior_independiente/Comprobacion_paredes.json')],
                            self.out/(run.name+'_Paredes.log'),900,cwd=self.workspace)
                    except (InterruptedError,TimeoutError):raise
                    except Exception:
                        if build_error is None:raise
            if build_error is not None:raise build_error
        finally:
            self.capture_attempt(run,log)

    def capture_attempt(self, run, log):
        destination=self.workspace/'Evidencia_intentos'/run.name
        destination.mkdir(parents=True,exist_ok=True)
        files=[]
        reports=[run/'Ejecucion.json',run/'perfil_ejecutado.json']
        output=run/'outputs/Inferior_independiente'
        reports+=sorted(output.glob('*.json'))
        reports+=[output/'Vista_propia.png',run/'outputs/Proceso/progreso.json']
        for source in reports:
            if not source.is_file(): continue
            target=destination/source.relative_to(run)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
            files.append(target.relative_to(self.workspace).as_posix())
        # Keep mesh paths for read-only measurements without duplicating large
        # artifacts or allowing a failed attempt to become the final result.
        meshes=[str(p.resolve()) for folder in (output,run/'work/inf_independiente')
                for p in sorted(folder.glob('*')) if p.is_file() and p.suffix.lower() in {'.stl','.npz'}]
        execution=read(run/'Ejecucion.json',{})
        evidence={'attempt':run.name,'execution_status':execution.get('status','INCOMPLETE'),
                  'execution_error':execution.get('error'),'reports':files,'meshes_read_only':meshes,
                  'code_directory_read_only':str((run/'Codigo').resolve()),
                  'scope':'Evidencia del intento, incluso fallido; no es una propuesta aprobada.'}
        if log.is_file():
            evidence['supervisor_log_tail']=log.read_text(encoding='utf-8',errors='replace')[-7000:]
        write(self.workspace/'Ultimo_intento.json',evidence)
        write(self.out/(run.name+'_Evidencia.json'),evidence)

    def prepare(self):
        self.workspace.mkdir(parents=True,exist_ok=False); self.out.mkdir(parents=True,exist_ok=True)
        options=self.db.one('SELECT fresh_start FROM segment_options WHERE job_id=?',(self.job['id'],)) or {}
        self.fresh_start=bool(options.get('fresh_start'))
        self.state['start_mode']='fresh_from_original' if self.fresh_start else 'continue_measured'
        self.workflow=lab_workflow.load_workflow(self.s.app)
        lab_workflow.snapshot(self.workflow,self.out/'Protocolo_obligatorio','codex')
        lab_workflow.snapshot(self.workflow,self.workspace/'protocolo_obligatorio','codex')
        self.state['lab_workflow']=lab_workflow.receipt(self.workflow,'codex')
        self.case=self.db.one('SELECT * FROM cases WHERE id=?',(self.job['target'],))
        self.source=self.db.one('SELECT * FROM sources WHERE id=?',(self.case['source_id'],))
        if not self.s.geometry_python: raise ValueError('Python de geometría no configurado')
        self.db.execute("UPDATE cases SET status='preparing' WHERE id=?",(self.case['id'],))
        evidence,self.history=self.w.plan_evidence(self.job)
        from .learning_geometry import snapshot_case_learning
        learning=snapshot_case_learning(self.s,self.db,self.history,self.case['id'],self.workspace)
        query=' '.join(r['text'][:500] for r in self.history['feedback'][:3]) or 'patron laboratorio barra seguridad cemento retenciones'
        refs=self.w.ingest.rag.search(query,limit=8,exclude_feedback=True,semantic=False)
        visual_count=0
        for ref in refs:
            if not ref.get('frame') or visual_count>=4: continue
            frame=(self.s.data/ref['frame']).resolve()
            if frame.is_relative_to(self.s.data.resolve()) and frame.is_file() and frame.suffix.lower() in {'.png','.jpg','.jpeg','.webp'}:
                visual_count+=1
                dest=self.workspace/f'referencia_video_{visual_count}{frame.suffix.lower()}'
                shutil.copy2(frame,dest);ref['local_frame']=dest.name
        write(self.out/'Historial_de_la_version.json',self.history)
        write(self.out/'Referencias_consultadas.json',evidence+refs)
        shutil.copy2(self.source['path'],self.workspace/'original.stl')
        self.raw_hash=digest(self.workspace/'original.stl')
        self.attempt_signatures=set()
        self.event('Agente · midiendo el STL y recuperando correcciones y referencias')
        self.profile=self.workspace/'Perfil.json'
        self.process([self.s.geometry_python,str(self.s.app/'engine/prepare_profile.py'),'--input',
                      str(self.workspace/'original.stl'),'--name',self.case['name'],'--output',str(self.profile),
                      '--history',str(self.out/'Historial_de_la_version.json')],
                     self.out/'Preparacion.log',600)
        self.base=read(self.profile); self.base_report=read(self.profile.with_suffix('.medidas.json'))
        write(self.out/'Perfil_base.json',self.base)
        self.previous=self.db.one("SELECT id,created FROM jobs WHERE kind='segment' AND target=? AND status='done' AND created<? ORDER BY created DESC LIMIT 1",(self.case['id'],self.job['created']))
        self.previous_root=self.s.data/'runs'/self.previous['id'] if self.previous else None
        self.previous_metadata_root=self.previous_root
        self.previous_draft=None
        self.previous_plan=None
        self.engine=self.workspace/'engine'
        self.trusted=self.out/'Motor_base'
        shutil.copytree(self.s.app/'engine',self.trusted,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(self.trusted,self.engine)
        self.manifest=engine_digest(self.trusted/'engine')
        # A first case may have no accepted proposal. Preserve useful numerical
        # work from a rejected design, with its rejection visible to the agent.
        failed=self.db.rows("SELECT id,created FROM jobs WHERE kind='segment' AND target=? AND status IN ('failed','interrupted','needs_review') AND created<? ORDER BY created DESC LIMIT 5",(self.case['id'],self.job['created']))
        if not self.previous:
            for job in failed:
                draft=resumable_draft(self.s.data/'runs'/job['id'],self.raw_hash,self.manifest)
                if draft:
                    self.previous_draft=draft
                    self.previous={'id':job['id'],'created':job['created'],'approval':'draft_needs_review'}
                    self.previous_root=draft['root'];self.previous_metadata_root=draft['metadata_root']
                    write(self.workspace/'Ultima_revision.json',{'job_id':job['id'],'attempt':draft['attempt'],
                        'approval':'draft_needs_review','review':draft['review']})
                    self.event('Agente · consultando el borrador anterior solo como referencia para la nueva construcción' if self.fresh_start else
                               'Agente · recuperando ajustes de una propuesta medida; su acabado sigue pendiente de revisión')
                    break
        self.previous_profile=read(self.previous_root/'perfil_ejecutado.json',{}) if self.previous else {}
        self.previous_validation=read(self.previous_root/'outputs/Inferior_independiente/Validacion_PROPIA.json',{}) if self.previous else {}
        # Keep accepted case adapters and parameters across corrections, while a
        # newly changed measured baseline wins over inherited automatic values.
        if self.previous_root and not self.fresh_start:
            old_base=read(self.previous_metadata_root/'outputs/Agente/Perfil_base.json',{})
            old_manifest=read(self.previous_metadata_root/'outputs/Agente/Motor_instalado.json',{})
            if old_base and adapter_engine_compatible(old_manifest,self.manifest):
                merged=dict(self.base)
                for key in EDITABLE_PROFILE:
                    if self.base.get(key)==old_base.get(key) and key in self.previous_profile:
                        merged[key]=self.previous_profile[key]
                write(self.profile,merged)
                for name in EDITABLE_CODE:
                    source=self.previous_root/'Codigo/engine'/name
                    if source.is_file(): shutil.copy2(source,self.engine/'engine'/name)
        if not self.fresh_start:
            for job in failed:
                # The latest saved recipe wins over an older geometry draft.
                # Keep that draft only as comparison evidence for the new PLAN.
                if self.previous and job['created']<=self.previous['created']:break
                recovered=recoverable_plan(self.s.data/'runs'/job['id']/'outputs/Agente',
                    self.s.data/'agent_work'/job['id'],self.base,self.manifest,self.workflow['sha256'],self.history['feedback'])
                if not recovered:continue
                merged=dict(self.base)
                for key in EDITABLE_PROFILE:
                    if key in recovered['profile']:merged[key]=recovered['profile'][key]
                write(self.profile,merged)
                for name in EDITABLE_CODE:
                    source=recovered['workspace']/'engine/engine'/name
                    if source.is_file():shutil.copy2(source,self.engine/'engine'/name)
                self.previous_plan={'job_id':job['id'],'approval':'NONE','origin':recovered['origin']}
                self.event('Agente · recuperando los últimos ajustes guardados para construirlos y medirlos; no están aprobados')
                break
        write(self.out/'Motor_instalado.json',self.manifest)
        write(self.workspace/'Respuesta.schema.json',response_schema())
        shutil.copytree(self.s.app/'docs',self.workspace/'documentacion')
        skill=self.s.app/'openclaw/skills/blender-dental-lab'
        if skill.is_dir():
            shutil.copytree(skill,self.workspace/'skill')
            entry=self.workspace/'skill/SKILL.md'
            entry.write_text(entry.read_text(encoding='utf-8').replace('../../../docs/','../documentacion/').replace('../blender-barras-video/','../protocolo_obligatorio/'),encoding='utf-8')
        self.images=[]
        for row in self.history['feedback'][:10]:
            for attachment in row.get('attachments',[]):
                source=self.db.one('SELECT path FROM sources WHERE id=?',(attachment['id'],))
                if source and Path(source['path']).suffix.lower() in {'.png','.jpg','.jpeg','.webp'}:
                    dest=self.workspace/('anotacion_'+attachment['id']+Path(source['path']).suffix.lower())
                    if dest not in self.images and len(self.images)<4:
                        shutil.copy2(source['path'],dest); self.images.append(dest)
        if self.previous_root:
            preview=self.previous_root/'outputs/Inferior_independiente/Vista_propia.png'
            if preview.is_file():
                dest=self.workspace/'Version_anterior.png';shutil.copy2(preview,dest);self.images.append(dest)
        context={'case_id':self.case['id'],'feedback':self.history['feedback'],
                 'start_mode':self.state['start_mode'],
                 'recovered_interrupted_plan':self.previous_plan,
                 'current_engine_scripts':self.manifest,
                 'lab_workflow':lab_workflow.receipt(self.workflow,'codex'),
                 'references':evidence+refs,'measures':self.base_report,
                 'case_learning_assets':learning,
                 'previous_profile':self.previous_profile,'previous_validation':self.previous_validation,
                 'images':[p.name for p in self.images],
                 'editable_code':sorted(EDITABLE_CODE),'editable_profile':sorted(EDITABLE_PROFILE),
                 'geometry_python':self.s.geometry_python,'blender':self.s.blender}
        context['previous_result']=result_evidence(self.previous_root) if self.previous_root else None
        if self.previous_draft:
            context['previous_result'].update(job_id=self.previous['id'],attempt=self.previous_draft['attempt'],
                approval='draft_needs_review',review=self.previous_draft['review'],
                continuation='Solo se recuperan parámetros y adaptadores permitidos. Reconstruir desde original.stl; no copiar estas mallas ni presentar este borrador como aprobado.')
        if self.fresh_start:
            if context['previous_result']:
                context['previous_result']['continuation']='Solo comparación: no se han heredado parámetros ni adaptadores de esta versión.'
            self.event('Agente · construcción nueva desde el STL original, con las correcciones y referencias del laboratorio')
        context['previous_failed_attempts']=[]
        failed=self.db.rows("SELECT id,detail FROM jobs WHERE kind='segment' AND target=? AND status IN ('failed','interrupted','needs_review') AND created<? ORDER BY created DESC LIMIT 2",(self.case['id'],self.job['created']))
        for item in failed:
            directory=self.s.data/'runs'/item['id']/'outputs/Agente'
            if not directory.is_dir(): continue
            reviews=sorted(directory.glob('*_review.json'))[-2:]
            plans=sorted(directory.glob('*_plan.json'))[-1:]
            record={'job_id':item['id'],'diagnostic':item['detail'][:4000],
                    'reviews':[read(p) for p in reviews],'last_plan':[read(p) for p in plans]}
            old_manifest=read(directory/'Motor_instalado.json',{})
            record['engine_changes_since_failure']=[name for name in sorted(set(old_manifest)|set(self.manifest))
                if old_manifest.get(name)!=self.manifest.get(name)] if old_manifest else None
            old_base=read(directory/'Perfil_base.json',{})
            record['preparation_changes_since_failure']=[key for key in
                ('connections','raw_to_work','expected_connections','expected_euler','minimum_supra_mm')
                if old_base.get(key)!=self.base.get(key)] if old_base else None
            record['scope']='Evidencia histórica: no atribuir fragmentos ni fallos al motor actual sin volver a medir su geometría.'
            snapshots=sorted(directory.glob('*_Evidencia.json'))
            if snapshots:
                snapshot=read(snapshots[-1],{})
                old_workspace=self.s.data/'agent_work'/item['id']
                record['attempt_evidence']={
                    'execution_status':snapshot.get('execution_status'),
                    'execution_error':snapshot.get('execution_error'),
                    'reports_read_only':[str(old_workspace/path) for path in snapshot.get('reports',[])],
                    'code_directory_read_only':snapshot.get('code_directory_read_only'),
                    'meshes_read_only':snapshot.get('meshes_read_only',[])}
            planning=planning_evidence(directory,self.s.data/'agent_work'/item['id'],self.raw_hash,self.manifest,self.base)
            if planning: record['planning_evidence']=planning
            # Prior failed geometry is evidence; never auto-select it as a result.
            context['previous_failed_attempts'].append(record)
        write(self.workspace/'Contexto.json',context)
        write(self.workspace/'Perfil_medido.json',self.base)
        write(self.out/'Contexto_del_agente.json',context)

    def validate(self):
        if digest(self.workspace/'original.stl')!=self.raw_hash or digest(self.source['path'])!=self.raw_hash:
            raise ValueError('El STL original cambió durante el intento')
        # The executable and every non-adapter script must be the installed code.
        for source in self.trusted.rglob('*.py'):
            relative=source.relative_to(self.trusted)
            if relative.as_posix() in {'engine/'+name for name in EDITABLE_CODE}: continue
            dest=self.engine/relative
            if not dest.is_file() or digest(dest)!=digest(source):
                raise ValueError('Código protegido modificado: '+str(relative))
        allowed={p.relative_to(self.trusted).as_posix() for p in self.trusted.rglob('*.py')}
        allowed.add('engine/case_geometry.py')
        if any(p.relative_to(self.engine).as_posix() not in allowed for p in self.engine.rglob('*.py')):
            raise ValueError('Módulo ejecutable fuera de los adaptadores permitidos')
        candidate=read(self.profile)
        validate_candidate(self.base,candidate,self.engine/'engine',self.manifest)
        return candidate

    def candidate_plan(self, reason):
        """Advance a changed, valid recipe to the existing strict build gates."""
        candidate=self.validate_for_execution()
        changed=[key for key in EDITABLE_PROFILE-{'adaptation_notes'} if candidate.get(key)!=self.base.get(key)]
        adapters=engine_digest(self.engine/'engine')!=self.manifest
        if not changed and not adapters:
            raise TimeoutError('El PLAN no dejó un candidato modificado para construir; '+reason)
        plan={'decision':'run','origin':'supervisor_recovery',
              'summary':'El supervisor construirá el candidato guardado por el agente para medirlo; el PLAN interrumpido no constituye una aprobación.',
              'changes':['Recuperados los ajustes de forma guardados por el agente; pendientes de comprobar en Blender.'],
              'pending':['Construcción, controles geométricos y revisión del agente todavía pendientes.'],
              'evidence':['Perfil.json','Plan_interrumpido.json' if (self.workspace/'Plan_interrumpido.json').is_file() else 'Contexto.recovered_interrupted_plan'],
              'resolved_pending':[],'recovery_reason':reason,
              'recovered_from':getattr(self,'previous_plan',None),
              'workflow_receipt':lab_workflow.receipt(self.workflow,'supervisor_recovery')}
        write(self.out/f'{self.state["attempt"]:02d}_plan.json',plan)
        self.event(plan['summary'],'planning')
        return plan

    def validate_for_execution(self):
        """Return one adapter error to the agent without consuming a build.

        Source, protected code and profile violations still stop immediately.
        A repair does not change the allowlist or replace any geometry gate.
        """
        try:
            return self.validate()
        except AdapterValidationError as error:
            write(self.workspace/'Correccion_adaptador.json',{'error':str(error),
                'attempt':self.state['attempt'],'geometry_launched':False,
                'editable_modules':sorted(EDITABLE_CODE),'approval':'NONE'})
            self.event('Agente · corrigiendo el adaptador antes de construir: '+str(error),'planning')
            answer=self.think('repair',
                'FASE REPARACIÓN DE CÓDIGO, máximo 240 segundos. Lee Correccion_adaptador.json. '+
                'Corrige únicamente el defecto indicado en los adaptadores permitidos, conservando la propuesta geométrica. '+
                'No repitas mediciones, no construyas y no cambies original, controles ni umbrales. '+
                'Los imports de nombres privados con guion bajo están prohibidos: si el helper matemático es propio de un adaptador editable, '+
                'dale un nombre público en su definición y referencias, conservando su cálculo. Nunca cambies un módulo protegido. '+
                'Devuelve run o retry tras reparar; blocked si no puedes. Todas las etapas geométricas siguen planned o pending. '+
                'Fallo exacto: '+str(error))
            if answer['decision'] not in {'run','retry'}:
                raise AdapterValidationError('El adaptador sigue pendiente: '+answer['summary'])
            return self.validate()

    def defer_draft(self, problem):
        """Expose an unapproved checkpoint without converting it to an acceptance."""
        if digest(self.workspace/'original.stl')!=self.raw_hash or digest(self.source['path'])!=self.raw_hash:
            return False
        draft=resumable_draft(self.root,self.raw_hash,self.manifest)
        if not draft:return False
        base=read(self.out/'Perfil_base.json');candidate=read(draft['root']/'perfil_ejecutado.json')
        execution=read(draft['root']/'Ejecucion.json',{})
        # The executor records its resolved input path in the executed profile.
        # It is provenance, not an editable field added by the planning agent.
        if 'input' not in base and candidate.get('input')==execution.get('source'):
            candidate={key:value for key,value in candidate.items() if key!='input'}
        validate_candidate(base,candidate,draft['root']/'Codigo/engine',self.manifest)
        write(self.out/'Estado_antes_del_borrador.json',self.state)
        self.state.update(draft_attempt=draft['attempt'],attempt_path=f'Intentos/{draft["attempt"]:02d}/outputs',
            design_review='NOT_ACCEPTED',pending=draft['review'].get('pending',self.state.get('pending',[])))
        write(self.out/'Borrador_no_aprobado.json',{'attempt':draft['attempt'],'approval':'NOT_ACCEPTED',
            'geometry_checks':'PASS','source_sha256':self.raw_hash,'stopped_reason':problem,
            'review':draft['review'],'scope':'Borrador para continuar correcciones; no es una propuesta aceptada ni una aprobación del laboratorio.'})
        self.db.execute("UPDATE cases SET status='needs_review' WHERE id=?",(self.job['target'],))
        self.event('Borrador generado; necesita ajustes de diseño. '+problem[:1800],'needs_review')
        return True

    def run(self):
        from .worker import NoGeometryChange,DraftNeedsReview
        try:
            self.prepare()
            problem=('El técnico solicita una construcción NUEVA desde original.stl. No se han heredado adaptadores ni parámetros del borrador. Conserva el conocimiento, las correcciones y las protecciones; usa las versiones anteriores solo para comparar. Replantea el cuerpo continuo y el trazado antes de ajustar paredes; no repitas el recorte acumulativo que separó los tramos.' if self.fresh_start else
                     'Continúa el acabado de la propuesta NO aprobada recuperada. Consulta Ultima_revision.json y Contexto.previous_result; conserva las mejoras medidas.' if self.previous_draft else '')
            for attempt in range(1,self.state['max_attempts']+1):
                self.state['attempt']=attempt
                self.event(f'Agente · interpretando y preparando el intento {attempt}', 'planning')
                if attempt==1 and self.previous_plan:
                    plan=self.candidate_plan('Continuación del candidato del plan interrumpido '+self.previous_plan['job_id'])
                else:
                    try:
                        plan=self.think('plan',
                            'FASE PLAN. Lee Contexto.json, Perfil.json, la skill y los módulos necesarios. '+
                            'Interpreta por separado las correcciones más recientes, consulta las imágenes adjuntas y las medidas. '+
                            'Edita Perfil.json o los adaptadores permitidos si hace falta. No ejecutes la segmentación: la ejecutará el supervisor al devolver run. '+
                            'No cambies nada solo para forzar una versión distinta. Si lo pedido ya está en la versión anterior, devuelve unchanged. '+
                            'Los cambios base del parser también pueden requerir run aunque tú no edites ningún archivo. '+
                            ('El intento anterior falló o necesita ajuste: '+problem if problem else ''),self.images)
                    except TimeoutError as error:
                        plan=self.candidate_plan(str(error))
                self.state['pending']=plan['pending']
                self.state['proposed_changes']=plan['changes']
                write(self.out/'Estado.json',self.state)
                if plan['decision']=='unchanged':
                    if not self.previous or self.previous_draft:
                        raise RuntimeError('El agente no ha construido una propuesta para este caso. '+plan['summary'])
                    raise NoGeometryChange(plan['summary'])
                if plan['decision'] not in {'run','retry'}:
                    if self.defer_draft(plan['summary']):raise DraftNeedsReview(self.state['detail'])
                    raise RuntimeError('El agente necesita revisión: '+plan['summary'])
                try:
                    candidate=self.validate_for_execution()
                    signature=json.dumps([candidate,engine_digest(self.engine/'engine')],sort_keys=True)
                    if signature in self.attempt_signatures:
                        raise RuntimeError('El agente repitió el mismo código y parámetros del intento fallido; debe corregir la causa antes de ejecutar otra vez')
                    self.attempt_signatures.add(signature)
                    comparison=compare_profiles(self.previous_profile,candidate) if self.previous_profile else None
                    code_changed=bool(self.previous_root and engine_digest(self.previous_root/'Codigo/engine')!=engine_digest(self.engine/'engine'))
                    if comparison and not comparison['geometry_parameters_changed'] and not code_changed and not self.previous_draft:
                        raise NoGeometryChange('El agente no ha producido un cambio de parámetros ni de geometría ejecutable. '+plan['summary'])
                    run=self.root/'outputs/Intentos'/f'{attempt:02d}'
                    self.state['attempt_path']=f'Intentos/{attempt:02d}/outputs'
                    self.event(f'Agente · ejecutando Blender y comprobaciones, intento {attempt}', 'executing')
                    self.db.execute("UPDATE cases SET status='generating' WHERE id=?",(self.case['id'],))
                    command=[self.s.geometry_python,str(self.engine/'ejecutar.py'),'--input',str(self.workspace/'original.stl'),
                             '--profile',str(self.profile),'--run-dir',str(run),'--blender',self.s.blender]
                    if self.s.b4d_root: command+=['--b4d-root',self.s.b4d_root]
                    if self.s.live_blender: command+=['--live-blender']
                    self.execute_attempt(command,run,self.out/f'{attempt:02d}_Blender.log')
                    state=read(run/'Ejecucion.json',{})
                    if state.get('status')!='GEOMETRY_PASS_DESIGN_REVIEW_PENDING':
                        raise RuntimeError('La geometría no ha superado los verificadores')
                    self.validate()  # check the agent-owned code/profile again after execution
                    validation=read(run/'outputs/Inferior_independiente/Validacion_PROPIA.json')
                    volumes=compare_meshes(self.previous_validation,validation) if self.previous_validation else None
                    if volumes and not self.previous_draft and max(abs(v['change_mm3']) for v in volumes.values())<1e-6:
                        geometric=self.out/f'{attempt:02d}_Diferencia_geometrica.json'
                        self.process([self.s.geometry_python,str(self.s.app/'engine/compare_results.py'),
                                      str(self.previous_root/'outputs/Inferior_independiente'),
                                      str(run/'outputs/Inferior_independiente'),str(geometric)],
                                     self.out/f'{attempt:02d}_Comparacion.log',300)
                        if not read(geometric,{}).get('geometry_changed'):
                            raise NoGeometryChange('Las piezas coinciden geométricamente con la versión anterior; no se presenta como una corrección.')
                    for name in ('Validacion_PROPIA.json','Resultado_controles.json','Seguridad_oclusal_local.json','Retenciones_medidas.json'):
                        path=run/'outputs/Inferior_independiente'/name
                        if path.is_file(): shutil.copy2(path,self.workspace/name)
                    view=self.workspace/'Resultado_actual.png'
                    shutil.copy2(run/'outputs/Inferior_independiente/Vista_propia.png',view)
                    write(self.workspace/'Comparacion.json',{'profiles':comparison,'volumes':volumes})
                    code_before=engine_digest(self.engine/'engine'); profile_before=digest(self.profile)
                    self.event('Agente · revisando las medidas y la vista del resultado', 'reviewing')
                    review=self.think('review',
                        'FASE REVISIÓN. No edites archivos. Inspecciona Resultado_actual.png, las anotaciones, '+
                        'Version_anterior.png si existe, Comparacion.json y los informes recién medidos. '+
                        'Decide accept solo si la propuesta mejora lo solicitado con evidencia; retry si hace falta otro ajuste. '+
                        'Una malla válida no acredita el espesor global ni resistencia. Deja esos extremos pendientes. '+
                        'Describe únicamente cambios comprobados; distingue intención de medida. Plan del intento: '+json.dumps(plan,ensure_ascii=False),
                        [view]+self.images[:4])
                    if code_before!=engine_digest(self.engine/'engine') or profile_before!=digest(self.profile):
                        raise ValueError('El agente editó la propuesta durante la revisión; hay que reconstruir y medir esos cambios')
                    if review['decision']!='accept':
                        self.state['pending']=review['pending']
                        write(self.workspace/'Ultima_revision.json',{'attempt':attempt,'review':review})
                        problem=review['summary']+' Consulta Ultima_revision.json y Ultimo_intento.json para sus medidas, imágenes y requisitos pendientes.'
                        write(self.out/f'{attempt:02d}_Pendiente.json',review); continue
                    if not review['evidence'] or not review['changes']:
                        raise ValueError('La revisión no acredita cambios con evidencia del resultado')
                    self.publish(run,candidate,validation,volumes,comparison,plan,review)
                    return 'Propuesta construida y revisada por el agente Codex con Blender; revisión del laboratorio pendiente.'
                except NoGeometryChange:
                    raise
                except InterruptedError:
                    raise
                except Exception as error:
                    problem=str(error)[-7000:]
                    if (self.workspace/'Ultimo_intento.json').is_file():
                        problem+=' Consulta Ultimo_intento.json: contiene los informes, la vista y las mallas reales del último intento. Localiza la causa medida antes de ajustar.'
                    write(self.out/f'{attempt:02d}_Diagnostico.json',{'error':problem})
                    self.event('Agente · analizando el error para corregir el siguiente intento', 'retrying')
            if self.defer_draft(problem):raise DraftNeedsReview(self.state['detail'])
            raise RuntimeError('El agente agotó sus intentos sin una propuesta aceptable. '+problem)
        except DraftNeedsReview:
            raise
        except NoGeometryChange as error:
            self.event(str(error),'unchanged')
            self.db.execute("UPDATE cases SET status='review_pending' WHERE id=?",(self.job['target'],))
            raise
        except Exception as error:
            self.event(str(error)[:3000],'failed')
            write(self.out/'Diagnostico.json',{'error':str(error)})
            self.db.execute("UPDATE cases SET status='failed' WHERE id=?",(self.job['target'],))
            raise

    def publish(self,run,candidate,validation,volumes,comparison,plan,review):
        # Only the supervisor exposes a winning attempt. Earlier files stay intact.
        shutil.copytree(run/'outputs',self.root/'outputs',dirs_exist_ok=True)
        for name in ('Ejecucion.json','perfil_ejecutado.json'):
            shutil.copy2(run/name,self.root/name)
        shutil.copytree(run/'Codigo',self.root/'Codigo')
        preparation=self.root/'outputs/Preparacion';preparation.mkdir(exist_ok=True)
        report=dict(self.base_report)
        if comparison:
            comparison.update(previous_job_id=self.previous['id'],engine_changed=engine_digest(self.previous_root/'Codigo/engine')!=engine_digest(run/'Codigo/engine'),mesh_volumes=volumes)
            if self.previous_draft:
                comparison.update(previous_attempt=self.previous_draft['attempt'],previous_approval='draft_needs_review')
            report['redesign_comparison']=comparison
        # Parser labels are proposals, not proof: the model's review is displayed
        # separately and original pending requirements are never silently removed.
        report['agent_review']=review
        report['lab_workflow']=review['lab_workflow']
        report['corrections_applied']=[{'changes':review['changes'],'origin':'agent_review'}]
        report['corrections_pending']=remaining_pending(self.base_report,review)
        write(preparation/'Perfil_automatico.medidas.json',report)
        write(preparation/'Perfil_automatico.json',candidate)
        for name in ('Historial_de_la_version.json','Referencias_consultadas.json'):
            shutil.copy2(self.out/name,preparation/name)
        write(self.out/'Revision_final.json',review)
        write(self.out/'Plan_final.json',plan)
        self.state.update(winning_attempt=self.state['attempt'],changes=review['changes'],pending=review['pending'])
        self.state.pop('attempt_path',None)
        self.db.execute("UPDATE cases SET profile_path=?,status='review_pending' WHERE id=?",(str(preparation/'Perfil_automatico.json'),self.case['id']))
        self.event('Agente · propuesta generada, medidas comprobadas y vista revisada; pendiente del laboratorio','done')
