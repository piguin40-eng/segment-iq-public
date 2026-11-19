"""Measured learning assets, kept separate from executable case geometry."""
import json,os,shutil,subprocess
from pathlib import Path


def geometry_chunks(source,report):
    prefix=f"Referencia {source['name']}. Medición de aprendizaje; no es una nueva segmentación ni aprobación. "
    if report['format']=='STL':
        return [{'kind':'geometria_medida','text':prefix+json.dumps({k:v for k,v in report.items()
            if k not in {'source_sha256','provenance'}},ensure_ascii=False)}]
    chunks=[{'kind':'escena_blender_medida','text':prefix+f"Escena Blender: {report['object_count']} objetos. Unidades {report['unit_system']}, escala {report['unit_scale']}. Geometría almacenada antes de modificadores; scripts incrustados desactivados. Nombres: "+', '.join(o['name'] for o in report['objects'])}]
    for obj in report['objects']:
        if obj['type']!='MESH':continue
        fields={k:obj[k] for k in ('name','vertices','polygons','triangles','dimensions_world','signed_volume','non_two_face_edges','modifiers') if k in obj}
        chunks.append({'kind':'objeto_blender_medido','text':prefix+json.dumps(fields,ensure_ascii=False)})
    return chunks


def measure_geometry(settings,source,folder):
    folder.mkdir(parents=True,exist_ok=True);output=folder/'geometry.json'
    script=settings.app/'engine/inspect_learning_geometry.py';suffix=Path(source['path']).suffix.lower()
    args=['--input',source['path'],'--output',str(output)]
    if suffix in {'.blend','.blend1'}:
        if not settings.blender:raise ValueError('Blender no está configurado para leer la escena de aprendizaje')
        command=[settings.blender,'--background','--factory-startup','--disable-autoexec','--python',str(script),'--',*args]
    else:
        if not settings.geometry_python:raise ValueError('Python geométrico no está configurado')
        command=[settings.geometry_python,str(script),*args]
    output.unlink(missing_ok=True)
    with (folder/'geometry.log').open('w',encoding='utf8') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180,
            **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
    report=json.loads(output.read_text(encoding='utf8'))
    if report.get('source_sha256')!=source['sha256']:raise ValueError('La referencia ha cambiado durante su medición')
    return geometry_chunks(source,report)


def snapshot_case_learning(settings,db,history,case_id,workspace):
    """Pin explicitly attached examples independently of RAG top-k retrieval."""
    records=[];seen=set();folder=Path(workspace)/'aprendizajes_caso'
    for row in history.get('feedback',[]):
        if row.get('case_id')!=case_id:continue
        for attached in row.get('attachments',[]):
            sid=attached['id']
            if sid in seen or len(seen)>=20:continue
            seen.add(sid);source=db.one('SELECT * FROM sources WHERE id=?',(sid,))
            if not source:continue
            path=Path(source['path']).resolve()
            if not path.is_relative_to((settings.data/'originals').resolve()) or not path.is_file():continue
            folder.mkdir(parents=True,exist_ok=True)
            record={'source_id':sid,'name':source['name'],'sha256':source['sha256'],
                'original_read_only':str(path),'role':'Reference for measurements/comparison only; never import its finished geometry into the generated result.'}
            meta=settings.data/'derived'/sid/'geometry.json'
            if meta.is_file():
                report=json.loads(meta.read_text(encoding='utf8'))
                if report.get('source_sha256')==source['sha256']:
                    dest=folder/(sid+'.geometry.json');shutil.copy2(meta,dest)
                    record['local_measurements']=dest.relative_to(workspace).as_posix()
            if path.suffix.lower() in {'.txt','.md','.py','.json'} and path.stat().st_size<=2_000_000:
                dest=folder/(sid+'.reference.txt');shutil.copy2(path,dest)
                record['local_document']=dest.relative_to(workspace).as_posix()
            if path.suffix.lower() in {'.png','.jpg','.jpeg','.webp'}:
                dest=folder/(sid+path.suffix.lower());shutil.copy2(path,dest)
                record['local_image']=dest.relative_to(workspace).as_posix()
            records.append(record)
    if records:
        (Path(workspace)/'Aprendizajes_caso.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
    return records
