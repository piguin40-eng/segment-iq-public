import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
from retention_mesh import decimation_ratio
from live_window import checkpoint, empty_scene
import bpy,bmesh,os,json,numpy as np
from mathutils import Vector
root=os.path.abspath('work/inf_independiente');out=os.path.abspath('outputs/Inferior_independiente');os.makedirs(out,exist_ok=True)
empty_scene();bpy.context.preferences.filepaths.save_version=0
bpy.ops.preferences.addon_enable(module='mesh_tissue')
def imp(path,name):
 bpy.ops.import_mesh.stl(filepath=os.path.abspath(path));o=bpy.context.object;o.name=name;return o
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,mod):
 name=mod.name;active(o);bpy.ops.object.modifier_apply(modifier=name);checkpoint('Retenciones · '+name+' aplicado')
def dump(o,name):
 o.data.calc_loop_triangles();np.savez(root+'/'+name+'.npz',vertices=np.array([v.co[:] for v in o.data.vertices]),faces=np.array([p.vertices[:] for p in o.data.loop_triangles]))
target=imp('work/inf_independiente/Primaria_sin_retenciones.stl','iBar_No_Retention');target.hide_render=True
surface=imp(root+'/Superficie_segura.stl','surfaces');o=surface.copy();o.data=surface.data.copy();bpy.context.collection.objects.link(o);o.name='Retencion_Dual';surface.hide_render=True;surface.hide_set(True)
input_faces=len(o.data.polygons);ratio=decimation_ratio(input_faces)
mod=o.modifiers.new('Decimate_patron','DECIMATE');mod.ratio=ratio;apply(o,mod)
restored_surface=len(o.data.polygons)<min(32,input_faces)
if restored_surface:o.data=surface.data.copy();ratio=1.
preparation={'surface_faces':input_faces,'requested_decimate_ratio':.015,'applied_decimate_ratio':ratio,
 'decimated_faces':len(o.data.polygons),'minimum_face_target':32,'restored_surface':restored_surface,
 'scope':'Densidad de malla para construir la red dual; no acredita seguridad de las retenciones.'}
print('DECIMATE',len(o.data.polygons),flush=True)
active(o);bpy.ops.object.dual_mesh();o=bpy.context.object;print('DUAL',len(o.data.vertices),len(o.data.edges),flush=True)
preparation.update(dual_vertices=len(o.data.vertices),dual_edges=len(o.data.edges))
with open(out+'/Retenciones_preparacion.json','w',encoding='utf-8') as f:json.dump(preparation,f,indent=2)
if not len(o.data.vertices) or not len(o.data.edges):raise ValueError('La superficie segura no permite una red dual conectada; revisar la superficie de retenciones.')
checkpoint('Retenciones · malla dual creada con Tissue')
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.delete(bm,geom=list(bm.faces),context='FACES_ONLY');bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.001)
for v in list(bm.verts):
 if not v.link_edges:bm.verts.remove(v)
for i in range(2):bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=False)
bm.to_mesh(o.data);bm.free();o.data.update()
# Repeated surface projection as in the supplied history; offset taken from installed B4D script.
mod=o.modifiers.new('Shrinkwrap_surface','SHRINKWRAP');mod.target=target;mod.wrap_method='NEAREST_SURFACEPOINT';mod.wrap_mode='ABOVE_SURFACE';mod.offset=.1;apply(o,mod)
net=o.copy();net.data=o.data.copy();bpy.context.collection.objects.link(net);net.name='Red_dual_proyectada';net.hide_render=True;net.hide_set(True)
mod=o.modifiers.new('Skin','SKIN');bpy.context.view_layer.update()
for sv in o.data.skin_vertices[0].data:sv.radius=(.325,.325)
# Choose one root per connected component.
adj={v.index:[] for v in o.data.vertices}
for e in o.data.edges:
 a,b=e.vertices;adj[a].append(b);adj[b].append(a)
seen=set()
for start in adj:
 if start in seen:continue
 o.data.skin_vertices[0].data[start].use_root=True;todo=[start];seen.add(start)
 while todo:
  for w in adj[todo.pop()]:
   if w not in seen:seen.add(w);todo.append(w)
apply(o,mod);print('SKIN',len(o.data.polygons),flush=True)
mod=o.modifiers.new('Subdivision','SUBSURF');mod.levels=2;apply(o,mod)
for val in [.2,.1]:
 mod=o.modifiers.new('Remesh','REMESH');mod.mode='VOXEL';mod.voxel_size=val;apply(o,mod)
mod=o.modifiers.new('Smooth','SMOOTH');mod.iterations=5;mod.factor=.5;apply(o,mod)
o['radio_skin_mm']=.325;o['procedencia']='Radio explicitado para esta revision; el historial solo registra Skin sin radio. Topologia dual y secuencia proyectada segun historial. No valor original confirmado.'
dump(o,'Retencion_dual_tool');bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.001
bpy.ops.wm.save_as_mainfile(filepath=out+'/07a_Red_y_herramienta_dual_INF.blend');print('DUAL_TOOL_READY',flush=True)
checkpoint('Herramienta de retenciones terminada')
