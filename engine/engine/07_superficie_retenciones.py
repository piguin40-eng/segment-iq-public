import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
from live_window import checkpoint, empty_scene
import bpy,bmesh,os,numpy as np,json
from mathutils.bvhtree import BVHTree
from mathutils import Vector
root='work/inf_independiente';d=np.load('work/inf_independiente/entrada.npz');source=BVHTree.FromPolygons([Vector(v) for v in d['vertices']],d['faces'].tolist(),all_triangles=True)
empty_scene();bpy.ops.import_mesh.stl(filepath=os.path.abspath(root+'/Primaria_sin_retenciones.stl'));o=bpy.context.object;bm=bmesh.new();bm.from_mesh(o.data);tree=BVHTree.FromBMesh(bm);D=json.load(open('work/inf_independiente/construccion_conexiones.json'));remove=[]
checkpoint('Primaria separada · cálculo de superficie para retenciones')
for f in bm.faces:
 c=f.calc_center_median();n=f.normal;near=source.find_nearest(c);hit=tree.ray_cast(c-n*.02,-n);bad=near[3]<.045 or n.z<.6 or hit[0] is None or hit[3]<.9
 if not bad:
  for i,(center,axis) in enumerate(zip(D['target_centers'],D['target_axes_occlusal'])):
   q=c-Vector(center);axis=Vector(axis)
   if (q-axis*q.dot(axis)).length<D.get('radii',[C['connection_radius_mm']]*len(D['target_centers']))[i]+.9:bad=True;break
 if bad:remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(o.data);bm.free();bpy.ops.export_mesh.stl(filepath=os.path.abspath(root+'/Superficie_segura.stl'),use_selection=True);print('SURFACE',len(o.data.polygons),flush=True)
checkpoint('Superficie de retenciones · zonas de conexión excluidas')
