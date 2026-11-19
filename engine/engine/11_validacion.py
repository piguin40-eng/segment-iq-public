import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
import sys,os,json
sys.path.insert(0,os.environ.get('DENTAL_PYTHON_DEPS',os.path.abspath('work/mesh_packages')))
import numpy as np,trimesh,manifold3d as mf
from connection_protection import connection_checks
from design_checks import design_checks
from bar_centering import primary_balance
root='work/inf_independiente';out='outputs/Inferior_independiente'
p=trimesh.load(root+'/Primaria_final.stl',force='mesh');s=trimesh.load(root+'/Supra_export.stl',force='mesh');d=np.load(root+'/entrada.npz');source=trimesh.Trimesh(d['vertices'],d['faces'],process=False)
def man(m):return mf.Manifold(mf.Mesh64(np.float64(m.vertices),np.uint64(m.faces)))
report={'status':'Revision de diseno; no validado para fabricacion','meshes':{}}
for name,m in [('primaria',p),('supra',s)]:
 r=man(m);report['meshes'][name]={'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),'volume_mm3':float(m.volume),'triangles':len(m.faces),'components':len(r.decompose()),'genus':r.genus()}
report['overlap_mm3']=(man(p)^man(s)).volume()
construction=json.load(open(root+'/construccion_conexiones.json'));checks=[]
for i,(center,axis) in enumerate(zip(construction['target_centers'],construction['target_axes_occlusal'])):
 c=np.array(center);n=np.array(axis);u=np.cross(n,[1,0,0]);u/=np.linalg.norm(u);v=np.cross(n,u);theta=np.linspace(0,2*np.pi,128,endpoint=False);radius=construction.get('radii',[C['connection_radius_mm']]*len(construction['target_centers']))[i];ring=c+radius*(np.cos(theta)[:,None]*u+np.sin(theta)[:,None]*v)
 original=trimesh.proximity.closest_point(source,ring)[0];dist=trimesh.proximity.closest_point(p,original)[1];checks.append({'connection':i+1,'max_distance_to_primary_mm':float(dist.max()),'sample_count':len(dist)})
report['connection_rings']=checks
report['functional_connection_protection']=connection_checks(source,p,s,C.get('connections',[]))
report['design_sections']=design_checks(source,p,s,C)
report['bar_centering']=primary_balance(p,C) if C.get('center_connections') else None
for name,m,other in [('primaria',p,s),('supra',s,p)]:
 points,_=trimesh.sample.sample_surface(m,10000,seed=20260907);ds=trimesh.proximity.closest_point(source,points)[1];points=points[ds>.02];dist=trimesh.proximity.closest_point(other,points)[1]
 report['meshes'][name]['interface_distances_sampled_mm']={'samples':len(dist),'min':float(dist.min()),'median':float(np.median(dist)),'p95':float(np.percentile(dist,95)),'max':float(dist.max())}
inverse=np.linalg.inv(np.array(json.load(open(root+'/procedencia.json'))['raw_to_work']))
for name,m in [('Primaria_'+C['arch']+'_PROPIA.stl',p),('Supra_'+C['arch']+'_PROPIA.stl',s)]:
 m=m.copy();m.apply_transform(inverse);m.export(out+'/'+name, file_type='stl_ascii')
report['working_to_original']=inverse.tolist();json.dump(report,open(out+'/Validacion_PROPIA.json','w'),indent=2);print(json.dumps(report,indent=2),flush=True)
