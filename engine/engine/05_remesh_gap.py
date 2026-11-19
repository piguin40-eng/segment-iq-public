import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
from live_window import checkpoint
import bpy,os,numpy as np,json,hashlib
from pathlib import Path
root=os.path.abspath('work/inf_independiente');out=os.path.abspath('outputs/Inferior_independiente')
if not os.environ.get('DENTAL_B4D_ROOT') and not os.environ.get('DENTAL_UI_STAGE'):bpy.ops.wm.open_mainfile(filepath=out+'/03_Diseno_basico_propio.blend',load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
for o in bpy.data.objects:o.hide_set(True);o.hide_render=True
D=np.load(root+'/core_union.npz');me=bpy.data.meshes.new('CUTTER_propio');me.from_pydata(D['vertices'].tolist(),[],D['faces'].tolist());me.update();o=bpy.data.objects.new('CUTTER_propio',me);bpy.context.collection.objects.link(o);o.select_set(True);bpy.context.view_layer.objects.active=o
r=o.modifiers.new('Remesh_015','REMESH');r.mode='VOXEL';r.voxel_size=.15;bpy.ops.object.modifier_apply(modifier=r.name);sm=o.modifiers.new('Smooth_10','SMOOTH');sm.factor=.5;sm.iterations=10;bpy.ops.object.modifier_apply(modifier=sm.name)
bpy.ops.wm.save_as_mainfile(filepath=out+'/04_Remallado_propio.blend')
checkpoint('Herramienta de corte · remallado y suavizado')
if os.environ.get('DENTAL_B4D_ROOT'):
 from pie_menu_editor.ui_utils import execute_script
 for name in ('Hybrid','CUTTER'):
  if name not in bpy.data.collections:bpy.context.scene.collection.children.link(bpy.data.collections.new(name))
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.hide_render=False;o.select_set(True);bpy.context.view_layer.objects.active=o;o.name='CUTTER'
 script=Path(os.environ['DENTAL_B4D_ROOT'])/'IBar3/scripts/gEZ7hsvkEM.py'
 if not script.is_file():raise RuntimeError('No está la herramienta de cemento de Blender for Dental')
 execute_script(str(script))
 checkpoint('Blender for Dental · herramienta de espacio de cemento ejecutada')
 o=bpy.data.objects.get('CuttingTool')
 if o is None or 'Solidify' not in o.modifiers:raise RuntimeError('iBar no creó CuttingTool con espacio de cemento')
 gap=o.modifiers['Solidify'];gap.thickness=C['cement_gap_mm'];gap.offset=0
 if gap.type!='SOLIDIFY':raise RuntimeError('Modificador de cemento inesperado')
 gap.name='C_Solidify';me=o.data
 receipt={'status':'PASS','tool':'Blender for Dental · iBar · Ajustar espacio de cemento','script_name':script.name,
  'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'blender':bpy.app.version_string,
  'cement_gap_mm':gap.thickness,'offset':gap.offset,'scope':'Herramienta de cemento ejecutada desde instalación local; otras etapas utilizan el motor SEGMENT IQ.',
  'vertices':len(me.vertices),'faces':len(me.polygons)}
 Path(out+'/B4D_ejecucion.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
 bpy.ops.wm.save_as_mainfile(filepath=out+'/06_Cemento_B4D.blend')
 checkpoint('Blender for Dental · gap ajustado a '+str(C['cement_gap_mm'])+' mm')
me.calc_loop_triangles();f=np.array([p.vertices[:] for p in me.loop_triangles]);v=np.array([v.co[:] for v in me.vertices]);np.savez(root+'/core_remallado.npz',vertices=v,faces=f)
for name,offset in [('Core_inner',-C['cement_gap_mm']/2),('Core_outer',C['cement_gap_mm']/2)]:np.savez(root+'/'+name+'.npz',vertices=np.array([v.co+v.normal*offset for v in me.vertices]),faces=f)
o['control_seguridad']='Comprobar localmente cobertura de supra y conexiones mediante resultados booleanos; no importar herramientas de referencia.'
bpy.ops.wm.save_as_mainfile(filepath=out+'/05_Control_geometrico.blend');r=o.modifiers.get('C_Solidify') or o.modifiers.new('C_Solidify','SOLIDIFY');r.thickness=C['cement_gap_mm'];r.offset=0;bpy.ops.wm.save_as_mainfile(filepath=out+'/06_Cemento_014.blend');print('CORE GAP READY',flush=True)
