"""Ejecutor aislado del prototipo dental; no ejecuta los historiales bpy originales."""
import argparse, hashlib, json, os, subprocess, sys, time, shutil
from pathlib import Path

STEPS=['01_entrada_trazado.py','02_conexiones.py','03_construccion.py','04_union.py','05_remesh_gap.py','06_separacion.py','07_superficie_retenciones.py','08_retenciones_duales.py','09_aplicar_retenciones.py','10_limpieza_exportacion.py','11_validacion.py','12_escena_final.py','13_comprobar_STL.py']
BLENDER_STEPS={3,5,7,8,12}
STAGE_LABELS=['Orientación del STL','Chimeneas y ejes medidos','Trazado y diseño de barra','Unión de barra y conos','Remallado y cemento','Separación primaria y supra','Superficie para retenciones','Construcción de retenciones','Retenciones y conexiones protegidas','Limpieza de malla','Medición y exportación','Vista de la propuesta','Comprobación de los STL']

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def stage_error(log_path):
 prefixes=('ValueError: ','RuntimeError: ','TypeError: ','IndexError: ','KeyError: ','AttributeError: ','AssertionError: ')
 if log_path.is_file():
  lines=log_path.read_text(encoding='utf-8',errors='replace').splitlines()
  for line in reversed(lines):
   if line.startswith(prefixes):return line[:1800]
 return 'No se completó la etapa; su registro contiene el diagnóstico.'

def validate_config(c,src):
 if c.get('retention_mode','dual_required') not in {'none','dual_optional','dual_required'}:raise ValueError('Modo de retenciones no reconocido.')
 required=['profile','source_sha256','arch','trace_center_y','trace_samples','trace_quantiles','connection_radius_mm','expected_connections','expected_euler','cone_top_z','cone_top_overrides','bar_top_z','cement_gap_mm','max_overlap_mm3','max_connection_error_mm','adaptation_notes']
 missing=[k for k in required if c.get(k) is None]
 if missing:raise ValueError('Faltan mediciones del caso: '+', '.join(missing))
 if digest(src)!=c['source_sha256']:raise ValueError('El perfil pertenece a otro STL. Medir el nuevo caso y crear su perfil; no cambiar solo el hash.')
 if c['arch'] not in ('SUP','INF','AUTO'):raise ValueError('Arcada invalida')
 for k in ['connection_radius_mm','expected_connections','trace_samples','cement_gap_mm','max_connection_error_mm']:
  if not isinstance(c[k],(int,float)) or c[k]<=0:raise ValueError('Parametro positivo requerido: '+k)
 if c['max_overlap_mm3']<0:raise ValueError('Tolerancia de solapamiento negativa')
 if c['raw_to_work'] is None and c['profile']!='INF-reference-independent-2026-09-07':raise ValueError('Un caso nuevo requiere matriz raw_to_work medida y documentada; PCA solo ensayado en la referencia.')
 if c['raw_to_work'] is not None:
  import numpy as np
  t=np.asarray(c['raw_to_work'],dtype=float)
  if t.shape!=(4,4) or not np.isfinite(t).all() or not np.allclose(t[3],[0,0,0,1]) or not np.allclose(t[:3,:3].T@t[:3,:3],np.eye(3),atol=1e-6):raise ValueError('La orientacion debe ser una transformacion rigida 4x4 sin escala.')

def gate(folder,c):
 report=json.loads((folder/'Validacion_PROPIA.json').read_text())
 reloaded=json.loads((folder/'Comprobacion_STL.json').read_text())
 errors=[]
 for name,m in report['meshes'].items():
  if not m['watertight'] or not m['winding_consistent'] or m['components']!=1 or m['volume_mm3']<=0:errors.append(name+': malla invalida')
  expected=c.get('expected_euler_by_mesh',{}).get(name,c['expected_euler'])
  if expected is not None and 2-2*m['genus']!=expected:errors.append(name+': topologia no prevista')
 for name,m in reloaded.items():
  key='primaria' if name.lower().startswith('primaria') else 'supra'
  measured=2-2*report['meshes'][key]['genus']
  if not m['closed'] or not m['consistent_winding'] or m['volume_mm3']<=0 or m['euler']!=measured:errors.append(name+': exportacion invalida')
 if abs(report['overlap_mm3'])>c['max_overlap_mm3']:errors.append('Solapamiento entre piezas')
 if c.get('prevent_extra_supra_openings') and report['meshes']['supra']['genus']>c['max_supra_genus']:
  errors.append('La separación ha creado aberturas adicionales en la supra; revisar protección y reserva lateral')
 if c.get('max_primary_genus') is not None and report['meshes']['primaria']['genus']>c['max_primary_genus']:
  errors.append('La barra tiene aberturas adicionales respecto al STL; revisar la seguridad y las retenciones')
 if len(report['connection_rings'])!=c['expected_connections']:errors.append('Numero de conexiones')
 if any(r['max_distance_to_primary_mm']>c['max_connection_error_mm'] for r in report['connection_rings']):errors.append('Alteracion de asientos muestreados')
 sections=report.get('design_sections',{})
 if c.get('center_connections'):
  centered=report.get('bar_centering') or {}
  if not centered.get('all_bilateral') or centered.get('max_center_offset_mm',float('inf'))>c['max_bar_center_offset_mm']:
   errors.append('La barra final no ha quedado equilibrada a ambos lados de las conexiones en las secciones medidas')
 if c.get('require_anterior_higher',bool(c.get('anterior_raise_mm'))) and not sections.get('anterior_higher_pass'):errors.append('No se ha conseguido más altura anterior que posterior en las secciones medidas')
 if c.get('minimum_supra_mm') and (sections.get('sample_count',0)<10 or not sections.get('occlusal_target_pass')):errors.append('El espesor oclusal muestreado no alcanza el mínimo de supra solicitado; revisar la zona de seguridad')
 protected=[r for r in c.get('connections',[]) if 'protection_radius_mm' in r]
 measures=report.get('functional_connection_protection',[])
 exported=reloaded['Primaria_'+c['arch']+'_PROPIA.stl'].get('functional_connection_protection',[])
 for checks in (measures,exported):
  if len(checks)!=len(protected):errors.append('Falta comprobar el perímetro completo antes/después de exportar')
  for m in checks:
   if m['protected_source_volume_mm3']<=0 or m['missing_volume_mm3']>c.get('max_protected_volume_loss_mm3',.0001):errors.append('Pérdida de volumen en perímetro funcional')
   if not m['source_vertices_checked'] or m['max_surface_distance_mm']>c['max_connection_error_mm']:errors.append('Alteración de superficie de conexión')
   if m['chimney_axis_material_hits']:errors.append('Chimenea obstruida')
 if errors:raise RuntimeError('; '.join(errors))
 return {'geometry_checks':'PASS','design_review':'PENDING','functional_connections_checked':len(measures),'limitations':['No comprueba espesor minimo global ni trayectoria de insercion.','La región funcional protegida se mide desde chimeneas y perímetros del STL; requiere confirmar que incluye todos los detalles de la interfase o conexión directa.','Comprobar altura, profundidad y cobertura anatomica distal en las escenas.','Control de seguridad adaptado; no macro literal B4D.']}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--input',required=True);p.add_argument('--profile',required=True);p.add_argument('--run-dir',required=True)
 p.add_argument('--blender',required=True);p.add_argument('--python-deps');p.add_argument('--check',action='store_true')
 p.add_argument('--until',type=int,choices=range(1,14),default=13)
 p.add_argument('--b4d-root',help='Instalación local licenciada; usa la herramienta real de cemento de iBar')
 p.add_argument('--live-blender',action='store_true',help='Capturar la ventana propia de Blender después de operaciones reales')
 a=p.parse_args();src=Path(a.input).resolve();profile=Path(a.profile).resolve();blender=Path(a.blender).resolve()
 if a.python_deps:sys.path.insert(0,str(Path(a.python_deps).resolve()))
 import numpy,scipy,trimesh,manifold3d,networkx,rtree
 c=json.loads(profile.read_text(encoding='utf-8-sig'));validate_config(c,src)
 if not blender.is_file():raise FileNotFoundError(blender)
 probe="import bpy; assert bpy.app.version[:2]==(3,6), 'Requiere Blender 3.6; adaptar API para otras versiones'; bpy.ops.preferences.addon_enable(module='mesh_tissue'); assert hasattr(bpy.ops.object,'dual_mesh'); print('DENTAL_PREFLIGHT_OK')"
 subprocess.run([str(blender),'--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python-expr',probe],check=True)
 if a.check:print('PREFLIGHT OK: entrada, perfil, librerias, Blender y Tissue. No se ha generado geometria.');return
 run=Path(a.run_dir).resolve();run.mkdir(parents=True,exist_ok=False)
 logs=run/'logs';logs.mkdir();c['input']=str(src)
 cfg=run/'perfil_ejecutado.json';cfg.write_text(json.dumps(c,indent=2),encoding='utf-8')
 env=os.environ.copy();env['DENTAL_CONFIG']=str(cfg);env['PYTHONUNBUFFERED']='1'
 if a.python_deps:env['DENTAL_PYTHON_DEPS']=str(Path(a.python_deps).resolve())
 if a.b4d_root:env['DENTAL_B4D_ROOT']=str(Path(a.b4d_root).resolve())
 if a.live_blender:env['DENTAL_LIVE_WINDOW']='1'
 source_engine=Path(__file__).resolve().parent/'engine'
 engine=run/'Codigo/engine'
 shutil.copytree(source_engine,engine,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 shutil.copy2(Path(__file__).resolve(),run/'Codigo/ejecutar.py')
 provenance={'source':str(src),'source_sha256':digest(src),'only_geometry_input':'raw STL','profile':c,'scripts_sha256':{f.name:digest(f) for f in engine.glob('*.py')},'steps':[],'status':'RUNNING'}
 state=run/'Ejecucion.json'
 progress_folder=run/'outputs/Proceso';progress_folder.mkdir(parents=True)
 progress={'stages':[{'step':i,'label':label,'status':'pending'} for i,label in enumerate(STAGE_LABELS,1)],'frames':[],
   'engine':'SEGMENT IQ · Blender'+(' · cemento con Blender for Dental' if a.b4d_root else ''),'status':'RUNNING'}
 def save():
  state.write_text(json.dumps(provenance,indent=2),encoding='utf-8')
  temporary=progress_folder/'progreso.tmp'
  temporary.write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
  os.replace(temporary,progress_folder/'progreso.json')
 save()
 try:
  for i,name in enumerate(STEPS[:a.until],1):
   print(f'ETAPA {i}/13 {name}',flush=True);started=time.time()
   progress['current_step']=i;progress['stages'][i-1].update(status='running',started=started);save()
   if i in {7,8} and c.get('retention_mode','dual_required')=='none':
    reason='Sin retenciones añadidas según el diseño; opcionales en el protocolo del vídeo.'
    progress['stages'][i-1].update(status='skipped',seconds=0,detail=reason)
    provenance['steps'].append({'step':i,'script':name,'status':'skipped','reason':reason,'seconds':0})
    save();continue
   cmd=[str(blender),'--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(engine/name)] if i in BLENDER_STEPS else [sys.executable,str(engine/name)]
   startup=None
   env['DENTAL_STEP']=str(i)
   if a.live_blender and i in BLENDER_STEPS:
    cmd=[str(blender),'--factory-startup','--disable-autoexec','--window-geometry','0','0','1280','760','--python-exit-code','1','--python',str(engine/'ui_stage.py'),'--',str(engine/name)]
   if i==5 and a.b4d_root:
    cmd=[str(blender),'--disable-autoexec','--window-geometry','0','0','1280','760','--python-exit-code','1','--python',str(engine/'b4d_stage.py')]
   if os.name=='nt' and ((a.live_blender and i in BLENDER_STEPS) or (i==5 and a.b4d_root)):
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
   with open(logs/(name+'.log'),'w',encoding='utf-8') as log:
    subprocess.run(cmd,cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,startupinfo=startup,timeout=1800)
   if a.live_blender and i in BLENDER_STEPS and not (i==5 and a.b4d_root):
    receipt=progress_folder/'Blender'/f'etapa_{i}.json'
    result=json.loads(receipt.read_text(encoding='utf-8')) if receipt.is_file() else {}
    if result.get('status')!='PASS':raise RuntimeError(result.get('error','Blender no confirmó la finalización de esta etapa.'))
   if i==5 and a.b4d_root:
    receipt=run/'outputs/Inferior_independiente/B4D_ejecucion.json'
    if not receipt.is_file() or json.loads(receipt.read_text())['status']!='PASS':raise RuntimeError('Blender for Dental no confirmó la herramienta de cemento; revisar su diagnóstico.')
   progress['stages'][i-1].update(status='done',seconds=round(time.time()-started,2))
   provenance['steps'].append({'step':i,'script':name,'seconds':round(time.time()-started,2)});save()
   if i in {1,2,3,5,6,8,9,12}:
    frame=progress_folder/f'{i:02d}.png'
    try:
     if i==12:shutil.copy2(run/'outputs/Inferior_independiente/Vista_propia.png',frame)
     else:
      cmd=[str(blender),'--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(engine/'progress_render.py'),'--',str(i),str(frame)]
      with open(logs/f'vista_{i:02d}.log','w',encoding='utf-8') as log:subprocess.run(cmd,cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
     progress['frames'].append({'step':i,'label':STAGE_LABELS[i-1],'path':f'Proceso/{i:02d}.png','created':time.time()})
    except Exception as preview_error:
     progress['stages'][i-1]['preview_error']='No se pudo renderizar esta etapa; su geometría y registro se conservan.'
     print('VISTA_ERROR',i,str(preview_error),flush=True)
    save()
  folder=run/'outputs/Inferior_independiente'
  if a.until==13:
   result=gate(folder,c);(folder/'Resultado_controles.json').write_text(json.dumps(result,indent=2),encoding='utf-8');provenance['status']='GEOMETRY_PASS_DESIGN_REVIEW_PENDING'
  else:provenance['status']='INTERMEDIATE_ONLY'
  progress['status']=provenance['status'];save();shutil.copy2(state,folder/'Ejecucion.json');print(str(folder),flush=True)
 except Exception as e:
  provenance['status']='FAILED';provenance['error']=str(e)
  progress['status']='FAILED';progress['error']=str(e)
  if isinstance(e,subprocess.CalledProcessError):
   failed_log=logs/(STEPS[progress['current_step']-1]+'.log')
   progress['error']=stage_error(failed_log);provenance['error']=progress['error']
  if progress.get('current_step'):progress['stages'][progress['current_step']-1]['status']='failed'
  save()
  if isinstance(e,subprocess.CalledProcessError):raise RuntimeError(progress['error']) from e
  raise

if __name__=='__main__':main()
