"""Read completed snapshots only; a render in progress is never a video frame."""
import json
import re
from pathlib import Path
from functools import lru_cache


def result_file_groups(files, selected_attempt=None):
    """Show one proposal; preserve other attempts as explicitly named diagnostics."""
    previews=[f for f in files if f['name']=='Vista_propia.png']
    published=[f for f in previews if not f['path'].startswith('Intentos/')]
    attempts=[(int(m[1]),f) for f in previews
              if (m:=re.match(r'^Intentos/(\d+)/outputs/',f['path']))]
    if selected_attempt is not None:
        chosen=next((f for number,f in attempts if number==selected_attempt),None)
    else:
        chosen=published[0] if published else max(attempts,key=lambda item:item[0])[1] if attempts else None
    folder=chosen['path'].rsplit('/',1)[0]+'/' if chosen else None
    number=re.match(r'^Intentos/(\d+)/',chosen['path']) if chosen else None
    label=f'Propuesta del intento {int(number[1])} · pendiente de revisión' if number else 'Propuesta para revisión'
    result=[]
    for file in files:
        f=dict(file);f['display_group']='technical'
        selected=folder is not None and f['path'].rsplit('/',1)[0]+'/'==folder
        if chosen and f['path']==chosen['path']:
            f['display_group']='preview';f['proposal_label']=label
        elif selected and (re.match(r'^(Primaria|Supra)_.*_PROPIA\.stl$',f['name'],re.I) or re.match(r'^08_.*\.blend$',f['name'],re.I)):
            f['display_group']='principal'
        elif selected and f['name'].lower().endswith('.blend'):
            f['display_group']='stage'
        elif '/' not in f['path'] and f['name'].lower().endswith('.zip'):
            f['display_group']='principal'
        result.append(f)
    return result

def read_json(path, default):
    try:return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return default


@lru_cache(maxsize=32)
def _safety_snapshot(path, mtime_ns, size):
    """Keep raw point clouds in the downloadable report, not every live poll."""
    report=read_json(path,{})
    summary={key:report[key] for key in (
        'scope','global_minimum_verified','unresolved','stopped_reason',
        'extra_openings_resolved','supra_genus_after_lateral','roof_refinement'
    ) if key in report}
    summary['attempts']=[dict(
        {key:row[key] for key in ('attempt','phase','minimum_sampled_mm','sample_count') if key in row},
        thin_section_count=len(row.get('thin_sections',[])),
        unresolved_tangent_count=len(row.get('tangent_search_unresolved',[]))
    ) for row in report.get('attempts',[])]
    return summary


def safety_snapshot(path):
    try:
        stat=path.stat()
        return _safety_snapshot(path,stat.st_mtime_ns,stat.st_size)
    except OSError:return {}

def completed_frames(root, candidates):
    frames=[]
    for frame in candidates:
        path=(root/frame.get('path','')).resolve()
        if path.is_relative_to(root) and path.suffix=='.png' and path.is_file():
            frames.append({k:frame[k] for k in ('step','label','path','created','kind') if k in frame})
    return frames

def job_progress(data,job):
    root=(data/'runs'/job['id']/'outputs').resolve()
    agent=read_json(root/'Agente/Estado.json',{})
    prefix=agent.get('attempt_path','')
    attempt=(root/prefix).resolve()
    if prefix and attempt.is_relative_to(root) and prefix.startswith('Intentos/'):
        view_root=attempt
    else:
        view_root=root;prefix=''
    stored=read_json(view_root/'Proceso/progreso.json',{})
    frames=completed_frames(view_root,stored.get('frames',[]))
    window=read_json(view_root/'Proceso/Blender/ventana.json',{})
    window_frames=completed_frames(view_root,window.get('frames',[]))
    if prefix:
        for f in frames+window_frames:f['path']=prefix+'/'+f['path']
    capture_error=(view_root/'Proceso/Blender/captura_error.txt').is_file()
    report=read_json(data/'profiles'/job['id']/'Perfil_automatico.medidas.json',{})
    if not report:report=read_json(root/'Preparacion/Perfil_automatico.medidas.json',{})
    if not report and agent:report=read_json(data/'agent_work'/job['id']/'Perfil.medidas.json',{})
    # Frames and measurements must belong to the same active attempt. During
    # retries there may be no published result, or a stale report at root.
    b4d=read_json(view_root/'Inferior_independiente/B4D_ejecucion.json',None)
    validation=read_json(view_root/'Inferior_independiente/Validacion_PROPIA.json',{})
    safety=safety_snapshot(view_root/'Inferior_independiente/Seguridad_oclusal_local.json')
    # Once PLAN has replaced the parser's initial proposal, do not present the
    # old automatic height adjustments as the changes being built right now.
    current_plan=job['status']!='done' and isinstance(agent.get('proposed_changes'),list)
    changes=([{'changes':agent['proposed_changes'],'origin':'agent_plan'}] if current_plan
             else report.get('corrections_applied',[]))
    pending=([{'text':text,'reason':'Pendiente de resolver; borrador no aprobado' if job['status']=='needs_review'
               else 'Pendiente de comprobar o corregir sobre esta propuesta'} for text in agent.get('pending',[])]
             if current_plan or job['status']=='needs_review' else
             report.get('corrections_pending',[{'text':text,'reason':'Pendiente de resolver por el agente'} for text in agent.get('pending',[])]))
    default_engine='SEGMENT IQ · preparando el STL para Blender' if job['status'] in ('queued','running') else 'Blender · ejecución anterior sin registro visual por etapas'
    return {'job_id':job['id'],'case_id':job['target'],'status':job['status'],'detail':job['detail'],
            'engine':stored.get('engine',default_engine),'agent':agent,
            'stages':stored.get('stages',[]),'frames':frames,'current_step':stored.get('current_step'),
            'window_frames':window_frames,'window_capture_error':capture_error,
            'error':stored.get('error'),'b4d':b4d,'measured_sections':validation.get('design_sections'),
            'local_safety':safety,
            'extraction':read_json(view_root/'Inferior_independiente/Comprobacion_extraccion.json',None),
            'walls':({k:v for k,v in wall_report.items() if k not in ('walls','original_skin_clusters')}
                     if (wall_report:=read_json(view_root/'Inferior_independiente/Comprobacion_paredes.json',None)) else None),
            'shape_refinement':{} if current_plan else report.get('shape_refinement',{}),
            'shape_construction':read_json(view_root/'Inferior_independiente/Refinamiento_construccion.json',{}),
            'bar_centering':validation.get('bar_centering'),
            'retentions':read_json(view_root/'Inferior_independiente/Retenciones_medidas.json',{}),
            'redesign_comparison':report.get('redesign_comparison'),
            'corrections_applied':changes,
            'corrections_pending':pending,
            'preparation_pending':report.get('corrections_pending',[]),
            'design_constraints':report.get('design_constraints',{})}
