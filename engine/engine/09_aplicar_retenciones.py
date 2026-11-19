import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
import sys,os,json
sys.path.insert(0,os.environ.get('DENTAL_PYTHON_DEPS',os.path.abspath('work/mesh_packages')))
import numpy as np,trimesh,manifold3d as mf
from connection_protection import combined
from retention_safety import apply_retention_policy,retention_mode
from retention_mesh import triangle_arrays
root='work/inf_independiente'
def from_stl(p):
 m=trimesh.load(p,force='mesh');return mf.Manifold(mf.Mesh64(np.float64(m.vertices),np.uint64(m.faces)))
base=from_stl('work/inf_independiente/Primaria_sin_retenciones.stl');tool=mf.Manifold()
if retention_mode(C)!='none':
 with np.load(root+'/Retencion_dual_tool.npz') as d:vertices,faces=triangle_arrays(d['vertices'],d['faces'])
 if len(faces):tool=mf.Manifold(mf.Mesh64(vertices,faces))
print('tool',tool.status(),tool.volume(),flush=True)
D=json.load(open('work/inf_independiente/construccion_conexiones.json'))
for i,(c,n) in enumerate(zip(D['target_centers'],D['target_axes_occlusal'])):
 c=np.array(c);n=np.array(n);u=np.cross(n,[1,0,0]);u/=np.linalg.norm(u);v=np.cross(n,u)
 radius=D.get('radii',[C['connection_radius_mm']]*len(D['target_centers']))[i]+.8
 protect=mf.Manifold.cylinder(60,radius,radius,64,True).transform(np.column_stack([u,v,n,c]))
 tool=tool-protect
functional=combined(C.get('connections',[]))
if functional is not None:tool=tool-functional
result,tool,retention_safety=apply_retention_policy(base,tool,C)
print('result',result.status(),result.volume(),result.genus(),len(result.decompose()),flush=True)
for name,r in [('Primaria_dual',result),('Herramienta_protegida',tool)]:
 if r.is_empty():continue
 me=r.to_mesh64();np.savez(root+'/'+name+'.npz',vertices=me.vert_properties[:,:3],faces=me.tri_verts);trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts,process=False).export(root+'/'+name+'.stl',file_type='stl_ascii')
parameters={'skin_radius_mm':.325,'shrinkwrap_offset_mm':.1,'decimate_ratio':.015} if retention_mode(C)!='none' else {}
json.dump({'base_volume':base.volume(),'final_volume':result.volume(),'removed_mm3':base.volume()-result.volume(),'genus':result.genus(),'parts':len(result.decompose()),'mode':retention_mode(C),**parameters,'parameters_status':'Sin retenciones por criterio de diseño; parámetros de red no aplicados.' if retention_mode(C)=='none' else 'sequence from user history; explicit settings from installed script or current adaptation, not all original settings recovered'},open(root+'/retention_report.json','w'),indent=2)
from pathlib import Path
retention_safety.update(removed_mm3=base.volume()-result.volume(),genus_before=base.genus(),genus_after=result.genus())
Path('outputs/Inferior_independiente/Retenciones_medidas.json').write_text(json.dumps(retention_safety,ensure_ascii=False,indent=2),encoding='utf-8')
