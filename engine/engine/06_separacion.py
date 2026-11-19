import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
import sys,os
sys.path.insert(0,os.environ.get('DENTAL_PYTHON_DEPS',os.path.abspath('work/mesh_packages')))
import numpy as np,trimesh,manifold3d as mf
from occlusal_safety import separate_with_safety
import json
from pathlib import Path
root=Path('work/inf_independiente')
def man(name):
 d=np.load(root/(name+'.npz'));m=trimesh.Trimesh(d['vertices'],d['faces'],process=True);return mf.Manifold(mf.Mesh64(m.vertices.astype('float64'),m.faces.astype('uint64')))
body=man('entrada')
inner,outer=man('Core_inner'),man('Core_outer')
primary,supra,correction=separate_with_safety(body,inner,outer,C)
Path('outputs/Inferior_independiente/Seguridad_oclusal_local.json').write_text(json.dumps(correction,ensure_ascii=False,indent=2),encoding='utf-8')
for name,r in [('Primaria_sin_retenciones',primary),('Supra',supra)]:
 print(name,r.volume(),r.genus(),len(r.decompose()),flush=True);me=r.to_mesh64();np.savez(root/(name+'.npz'),vertices=me.vert_properties[:,:3],faces=me.tri_verts);trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts,process=False).export(root/(name+'.stl'),file_type='stl_ascii')
