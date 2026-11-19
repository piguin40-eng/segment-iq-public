import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
import sys,os,json
sys.path.insert(0,os.environ.get('DENTAL_PYTHON_DEPS',os.path.abspath('work/mesh_packages')))
import trimesh,numpy as np,manifold3d as mf
from connection_protection import connection_checks
from pathlib import Path
out=Path('outputs/Inferior_independiente');r={};meshes=[]
transform=np.asarray(json.load(open('work/inf_independiente/procedencia.json'))['raw_to_work'])
for name in ['Primaria_'+C['arch']+'_PROPIA.stl','Supra_'+C['arch']+'_PROPIA.stl']:
 m=trimesh.load(out/name,force='mesh');r[name]={'closed':bool(m.is_watertight),'consistent_winding':bool(m.is_winding_consistent),'volume_mm3':m.volume,'euler':m.euler_number};print(name,r[name],flush=True)
 m.apply_transform(transform);meshes.append(m)
if any('protection_radius_mm' in c for c in C.get('connections',[])):
 d=np.load('work/inf_independiente/entrada.npz');source=trimesh.Trimesh(d['vertices'],d['faces'],process=False)
 r['Primaria_'+C['arch']+'_PROPIA.stl']['functional_connection_protection']=connection_checks(source,*meshes,C['connections'])
json.dump(r,open(out/'Comprobacion_STL.json','w'),indent=2)
