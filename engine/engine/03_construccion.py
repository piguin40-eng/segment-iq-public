import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
from bar_height import top_height
from shape_refinement import inset_contour
from live_window import checkpoint, empty_scene
import bpy,bmesh,os,json,numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
root=os.path.abspath('work/inf_independiente');out=os.path.abspath('outputs/Inferior_independiente');empty_scene();bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=.001
D=np.load(root+'/entrada.npz');vertices=D['vertices'];faces=D['faces'];tree=BVHTree.FromPolygons([Vector(p) for p in vertices],faces.tolist(),all_triangles=True)
def mesh(name,v,f=[],e=[]):
 me=bpy.data.meshes.new(name);me.from_pydata(np.array(v).tolist(),e,np.array(f).tolist());me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return o
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def dump(o,name):
 o.data.calc_loop_triangles();np.savez(root+'/'+name+'.npz',vertices=np.array([o.matrix_world@v.co for v in o.data.vertices]),faces=np.array([p.vertices[:] for p in o.data.loop_triangles]))
source=mesh('Entrada_STL_sin_segmentar',vertices,faces);cones=[]
checkpoint('STL original orientado · comienzo del diseño')
for i,c in enumerate(json.load(open(root+'/conexiones.json'))):
 center=Vector(c['center']);axis=Vector(c['normal']);distance=(C['cone_top_overrides'].get(str(i+1),C['cone_top_z'])-center.z)/axis.z;bottom=center-axis*2;top=center+axis*distance;mid=(bottom+top)/2
 bpy.ops.mesh.primitive_cone_add(vertices=96,radius1=c['radius']+.65,radius2=c['radius']+.25,depth=(top-bottom).length,location=mid);o=bpy.context.object;o.name=f'Cone_{i+1:02d}';o.rotation_euler=axis.to_track_quat('Z','Y').to_euler();bpy.context.view_layer.update();dump(o,o.name);cones.append(o)
 t=mesh(f'Tubes_{i+1:02d}',[center-axis*3,center,center+axis*(distance+3)],[],[(0,1),(1,2)]);mod=t.modifiers.new('Skin','SKIN');bpy.context.view_layer.update()
 for sv in t.data.skin_vertices[0].data:sv.radius=(c['radius'],c['radius'])
 t.data.skin_vertices[0].data[1].use_root=True;t.modifiers.new('Subdivision','SUBSURF');t.hide_render=True;t.hide_set(True)
 checkpoint('Conexión '+str(i+1)+' · cono construido sobre su eje medido')
bpy.ops.wm.save_as_mainfile(filepath=out+'/01_Tubos_y_conos_desde_STL.blend')
xy=np.load(root+'/trazado_xy.npz')['xy'];v=[]
for a,b in xy:
 hit=tree.ray_cast(Vector((a,b,-30)),Vector((0,0,1)))
 if hit[0] is None:hit=tree.find_nearest(Vector((a,b,-5)))
 v.append((a,b,hit[0].z))
line=mesh('Draw_Line_propia_76_puntos',v,[],[(i,(i+1)%len(v)) for i in range(len(v))]);line['origen']='Trazado calculado exclusivamente sobre el STL bruto por bandas radiales; ninguna plantilla geometrica de referencia.'
checkpoint('Trazado propio sobre el STL')
active(line);bm=bmesh.new();bm.from_mesh(line.data)
for k in range(3):bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=False)
# Follow the closed loop in topological order after subdivision.
bm.verts.ensure_lookup_table();start=bm.verts[0];ordered=[start];prev=None;cur=start
while True:
 nxt=next(e.other_vert(cur) for e in cur.link_edges if e.other_vert(cur)!=prev)
 if nxt==start:break
 ordered.append(nxt);prev,cur=cur,nxt
v=np.array([p.co[:] for p in ordered]);bm.free();line.hide_render=True
base=mesh('DrawingDone_propio',v,[],[(i,(i+1)%len(v)) for i in range(len(v))]);bpy.ops.wm.save_as_mainfile(filepath=out+'/02_Trazado_propio.blend')
N=len(v);allv=[];names=['MARGIN','Attach','INSIDE','Flat','Extrude','TOP']
for j in range(6):
 vv=v.copy()
 if j==0:vv[:,2]-=.25
 elif j==2:vv[:,2]+=.2
 elif j==3:vv[:,2]+=.4
 elif j==4:vv[:,2]+=.9
 elif j==5:vv[:,2]=top_height(vv[:,:2],C)
 bevel=C.get('shape_refinement',{}).get('cervical_bevel_mm',0.)
 if bevel and j>=2:vv[:,:2]=inset_contour(vv[:,:2],C,bevel)
 if bevel and j==2:vv[:,2]=v[:,2]+bevel
 allv.extend(vv.tolist())
f=[]
for j in range(5):
 for i in range(N):a=j*N+i;b=j*N+(i+1)%N;f.append((a,b,b+N,a+N))
f.append(tuple(range(5*N,6*N)));design=mesh('DESIGN_propio',allv,f)
checkpoint('Barra construida · seis perfiles de altura')
for j,name in enumerate(names):design.vertex_groups.new(name=name).add(list(range(j*N,(j+1)*N)),1,'REPLACE')
design['top_altura_marco_trabajo']=C['bar_top_z'];design['incremento_anterior_mm']=C.get('anterior_raise_mm',0);bpy.ops.wm.save_as_mainfile(filepath=out+'/03_Diseno_basico_propio.blend')
json.dump({'requested':C.get('shape_refinement',{}),'cervical_bevel_width_mm':bevel,'cervical_bevel_height_mm':bevel,
 'scope':'Bisel construido en los perfiles INSIDE y superiores; las conexiones se protegen de nuevo tras separar. La forma final requiere revisión.'},open(out+'/Refinamiento_construccion.json','w'),indent=2)
core=design.copy();core.data=design.data.copy();bpy.context.collection.objects.link(core);core.name='CORE_propio';bm=bmesh.new();bm.from_mesh(core.data);edges=[e for e in bm.edges if e.is_boundary];vv=list({v for e in edges for v in e.verts});new={v:bm.verts.new((v.co.x,v.co.y,-35)) for v in vv}
for e in edges:a,b=e.verts;bm.faces.new((a,b,new[b],new[a]))
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(core.data);bm.free();active(core);r=core.modifiers.new('Remesh_015','REMESH');r.mode='VOXEL';r.voxel_size=.15;bpy.ops.object.modifier_apply(modifier=r.name);dump(core,'core_trazado')
print('OWN DESIGN READY',N,flush=True)
checkpoint('Herramienta de barra remallada')
