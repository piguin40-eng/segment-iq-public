import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
import sys,os,json
sys.path.insert(0,os.environ.get('DENTAL_PYTHON_DEPS',os.path.abspath('work/mesh_packages')))
from pathlib import Path
import numpy as np,manifold3d as mf,trimesh
root=Path('work/inf_independiente')
def man(p):
 d=np.load(p);m=trimesh.Trimesh(d['vertices'],d['faces'],process=True);return mf.Manifold(mf.Mesh64(m.vertices.astype('float64'),m.faces.astype('uint64')))
r=man(root/'core_trazado.npz')
for p in root.glob('Cone_*.npz'):r=r+man(p)
me=r.to_mesh64();np.savez(root/'core_union.npz',vertices=me.vert_properties[:,:3],faces=me.tri_verts);body=man(root/'entrada.npz')
for n,a in [('primary',body^r),('supra',body-r)]:print(n,a.volume(),a.genus(),[(p.volume(),p.genus()) for p in a.decompose()],flush=True)
