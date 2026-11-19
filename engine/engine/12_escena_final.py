import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
from live_window import checkpoint, empty_scene
import bpy,os,json,numpy as np
from mathutils import Vector,Matrix
root=os.path.abspath('work/inf_independiente');out=os.path.abspath('outputs/Inferior_independiente');empty_scene();bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene;s.name='01_Ensamblado_laboratorio';s.unit_settings.system='METRIC';s.unit_settings.scale_length=.001
transform=Matrix(np.linalg.inv(np.array(json.load(open(root+'/procedencia.json'))['raw_to_work'])).tolist());objs=[]
for name,file,color in [('Primaria_INF_PROPIA','Primaria_final',(.66,.43,.12,1)),('Supra_INF_PROPIA','Supra_export',(.82,.86,.9,1)),('Primaria_sin_retenciones','Primaria_sin_retenciones',(.6,.7,.8,1))]:
 name=name.replace('_INF_','_'+C['arch']+'_')
 d=np.load(root+'/'+file+'.npz');me=bpy.data.meshes.new(name);me.from_pydata(d['vertices'].tolist(),[],d['faces'].tolist());me.update();o=bpy.data.objects.new(name,me);s.collection.objects.link(o);o.color=color;o.matrix_world=transform
 for f in me.polygons:f.use_smooth=True
 if file=='Primaria_sin_retenciones':o.hide_set(True);o.hide_render=True
 else:objs.append(o)
t=bpy.data.texts.new('LEEME');t.write('Construccion propia desde el STL bruto: trazado medido, tubos/conos, seis perfiles, remallado, seguridad adaptada y retenciones duales. Cemento propuesto '+str(C['cement_gap_mm'])+' mm. '+C['adaptation_notes']+' Escena 01 y STL en coordenadas originales; escena 02 separada para inspeccion. Ver Perfil_automatico.medidas.json, Ejecucion.json y Resultado_controles.json. Requiere revision del laboratorio.')
bpy.ops.wm.save_as_mainfile(filepath=out+'/07b_Comparacion_antes_despues.blend')
checkpoint('Primaria y supra ensambladas · coordenadas del original')
p=bpy.data.scenes.new('02_Vista_separada');bpy.context.window.scene=p
extents=[np.ptp(np.array([v.co[:] for v in o.data.vertices]),axis=0) for o in objs]
width=max(e[0] for e in extents);spacing=width*.60+2
for o,x in zip(objs,[-spacing,spacing]):
 n=o.copy();n.data=o.data.copy();n.matrix_world=Matrix.Identity(4);p.collection.objects.link(n);v=np.array([v.co[:] for v in n.data.vertices]);center=(v.min(0)+v.max(0))/2;n.location=Vector((x,0,0))-Vector(center)
checkpoint('Propuesta separada · primaria y supra para revisión')
p.render.engine='BLENDER_WORKBENCH';p.display.shading.light='STUDIO';p.display.shading.color_type='OBJECT';p.display.shading.show_cavity=True;p.display.shading.cavity_type='BOTH';p.display.shading.background_type='WORLD';p.world=bpy.data.worlds.new('World');p.world.color=(.045,.055,.075)
bpy.ops.object.camera_add(location=(0,-65,145));c=bpy.context.object;c.rotation_euler=(-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=max((2*spacing+width)*1.12,max(e[1] for e in extents)*2.1);p.camera=c
p.render.resolution_x=1500;p.render.resolution_y=850;p.render.resolution_percentage=100;p.render.filepath=out+'/Vista_propia.png';bpy.ops.wm.save_as_mainfile(filepath=out+'/08_'+C['arch']+'_propia.blend');bpy.ops.render.render(write_still=True)
print('READY',flush=True)
