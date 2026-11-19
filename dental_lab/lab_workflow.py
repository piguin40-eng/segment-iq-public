"""Versioned lab instructions supplied independently of RAG ranking.

Receipts prove which context was supplied and answered, not geometric compliance.
"""
import hashlib
import json
from pathlib import Path

SKILL = 'blender-barras-video'
VERSION = '1.1.0'
REFERENCE = 'LAB-VIDEO-BARRAS-20260916'
VIDEO_SHA256 = '903f28d96f9d1ed324a45bfb805db5e0fc941953a0eaf1439334e6e43d6c489f'
FILES = ('SKILL.md', 'references/procedimiento.md', 'references/evidencia.md',
         'complemento_retenciones.md')
CHECKS = ('orientacion', 'tubos_conos', 'mascara_trazado', 'plano_barra',
          'remesh_cuter', 'afinamiento', 'seguridad', 'cemento_separacion',
          'retenciones', 'comprobacion_exportacion')


def load_workflow(app):
    folder = Path(app)/'openclaw/skills'/SKILL
    files = {}
    for name in FILES:
        try:
            value = (folder/name).read_text(encoding='utf-8-sig').strip()
        except OSError as error:
            raise RuntimeError('Falta el protocolo obligatorio de barras: '+name+
                               '. Repara la instalación de SEGMENT IQ; no hace falta un JSON del caso.') from error
        if not value:
            raise RuntimeError('El protocolo obligatorio de barras está vacío: '+name)
        files[name] = value
    canonical = json.dumps({'version':VERSION, 'files':files, 'checks':CHECKS},
                           ensure_ascii=False, sort_keys=True).encode('utf-8')
    return {'id':REFERENCE, 'skill':SKILL, 'version':VERSION,
            'sha256':hashlib.sha256(canonical).hexdigest(), 'checks':list(CHECKS), 'files':files}


def receipt(workflow, mode):
    return {**{key:workflow[key] for key in ('id','skill','version','sha256','checks')},
            'status':'required_context_loaded', 'mode':mode,
            'scope':'Consulta y respuesta por etapa; no certifica ejecución B4D ni cumplimiento geométrico.'}


def snapshot(workflow, destination, mode):
    destination = Path(destination)
    for name, text in workflow['files'].items():
        path = destination/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text+'\n', encoding='utf-8')
    (destination/'Protocolo.json').write_text(json.dumps(receipt(workflow,mode), ensure_ascii=False, indent=2), encoding='utf-8')


def prompt(workflow):
    header = ('PROTOCOLO OBLIGATORIO DEL LABORATORIO. Considera todas sus etapas en este caso. '
              'Las correcciones posteriores del técnico prevalecen. Devuelve lab_workflow con el SHA-256 '
              f'{workflow["sha256"]} y una entrada para CADA etapa: '+', '.join(CHECKS)+'. '
              'PLAN admite planned/pending/not_applicable; REVIEW admite verified/pending/not_applicable. '
              'not_applicable solo se admite para retenciones opcionales y necesita motivo. '
              'Cada verified requiere evidencia del resultado de este caso; citar la skill no verifica una malla. '
              'Los pasos no comprobados quedan pending con causa concreta. No declares que el vídeo ejecutó una etapa.\n\n')
    return header+'\n\n'.join('### '+name+'\n'+text for name,text in workflow['files'].items())


def answer_schema():
    item = {'type':'object', 'properties':{
        'step':{'type':'string','enum':list(CHECKS)},
        'status':{'type':'string','enum':['planned','verified','pending','not_applicable']},
        'detail':{'type':'string'}, 'evidence':{'type':'array','items':{'type':'string'}}},
        'required':['step','status','detail','evidence'], 'additionalProperties':False}
    return {'type':'object','properties':{'sha256':{'type':'string'},
            'checks':{'type':'array','items':item}},'required':['sha256','checks'],'additionalProperties':False}


def validate_answer(workflow, answer, phase):
    supplied = answer.get('lab_workflow', {})
    if not isinstance(supplied, dict) or supplied.get('sha256') != workflow['sha256']:
        raise ValueError('El agente no ha reconocido la versión del protocolo obligatorio de barras')
    rows = supplied.get('checks')
    if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):
        raise ValueError('Falta la revisión de etapas del protocolo de barras')
    if len(rows)!=len(CHECKS) or {row.get('step') for row in rows}!=set(CHECKS):
        raise ValueError('El agente ha omitido o repetido etapas del protocolo de barras')
    allowed = {'planned','pending','not_applicable'} if phase=='plan' else {'verified','pending','not_applicable'}
    for row in rows:
        if row.get('status') not in allowed or not isinstance(row.get('detail'),str) or not row['detail'].strip():
            raise ValueError('Estado o explicación inválidos para '+row['step'])
        evidence = row.get('evidence')
        if not isinstance(evidence,list) or any(not isinstance(e,str) or not e.strip() for e in evidence):
            raise ValueError('Evidencia inválida para '+row['step'])
        if row['status']=='verified' and not evidence:
            raise ValueError('Falta evidencia para la etapa comprobada '+row['step'])
        if row['status']=='not_applicable' and row['step']!='retenciones':
            raise ValueError('Una etapa obligatoria no puede omitirse: '+row['step'])
    return [f"Protocolo · {row['step']}: {row['detail']}" for row in rows if row['status']=='pending']


def status(app, mode):
    try:
        result = receipt(load_workflow(app),mode)
        result['available'] = True
        return result
    except RuntimeError as error:
        return {'id':REFERENCE, 'skill':SKILL, 'version':VERSION, 'available':False,
                'status':'missing', 'error':str(error), 'mode':mode}
