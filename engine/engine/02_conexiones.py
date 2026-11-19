import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
import os,sys,json
sys.path.insert(0,os.environ.get('DENTAL_PYTHON_DEPS',os.path.abspath('work/mesh_packages')))
import numpy as np,trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
m=trimesh.load('work/inf_independiente/Entrada_orientada.stl',force='mesh');destination='work/inf_independiente/candidatos.json'
if C.get('connections'):
 selected=C['connections']
 if len(selected)!=C['expected_connections']:raise RuntimeError('Connection count mismatch')
 json.dump(selected,open('work/inf_independiente/conexiones.json','w'),indent=2)
 json.dump({'target_centers':[c['center'] for c in selected],'target_axes_occlusal':[c['normal'] for c in selected],'radii':[c['radius'] for c in selected]},open('work/inf_independiente/construccion_conexiones.json','w'),indent=2)
 print('MEASURED FROM HASH-BOUND INPUT',len(selected),flush=True)
 sys.exit(0)
v=np.array(m.vertices);cand=[]
for threshold in [.15,.25,.4,.6,.9]:
 edges=m.face_adjacency_edges[m.face_adjacency_angles>threshold]
 ids=np.unique(edges);lookup=np.full(len(v),-1);lookup[ids]=np.arange(len(ids));ee=lookup[edges]
 graph=coo_matrix((np.ones(len(ee)),(ee[:,0],ee[:,1])),shape=(len(ids),len(ids)))
 n,labels=connected_components(graph,directed=False)
 for lab in range(n):
  vv=v[ids[labels==lab]]
  if len(vv)<15:continue
  c=vv.mean(0);_,_,axes=np.linalg.svd(vv-c,full_matrices=False);p=(vv-c)@axes.T
  if abs(axes[2,2])<.5:continue
  plane=float(np.std(p[:,2]));A=np.column_stack([2*p[:,0],2*p[:,1],np.ones(len(p))]);b=(p[:,:2]**2).sum(1);fit=np.linalg.lstsq(A,b,rcond=None)[0]
  rad=np.sqrt(max(0,fit[2]+(fit[:2]**2).sum()));res=np.std(np.linalg.norm(p[:,:2]-fit[:2],axis=1))
  if .45<rad<3.7 and res<.1 and plane<.1:
   center=c+axes[:2].T@fit[:2];normal=axes[2];normal=normal if normal[2]>0 else -normal
   cand.append({'threshold':threshold,'vertices':len(vv),'center':center.tolist(),'normal':normal.tolist(),'radius':float(rad),'radial_std':float(res),'planar_std':plane})
json.dump(cand,open(destination,'w'),indent=2)
selected=[]
for c in sorted(cand,key=lambda c: c['radial_std']+c['planar_std']):
 if abs(c['radius']-C['connection_radius_mm'])<.002 and c['radial_std']<.001 and c['planar_std']<.001 and all(np.linalg.norm(np.array(c['center'])-np.array(d['center']))>.1 for d in selected):selected.append(c)
selected.sort(key=lambda c:np.arctan2(c['center'][0],C['trace_center_y']-c['center'][1]));json.dump(selected,open('work/inf_independiente/conexiones.json','w'),indent=2);print('DETECTED',len(selected),flush=True)

json.dump({'target_centers':[c['center'] for c in selected],'target_axes_occlusal':[c['normal'] for c in selected]},open('work/inf_independiente/construccion_conexiones.json','w'),indent=2)

if len(selected)!=C['expected_connections']:raise RuntimeError('Connection count mismatch: '+str(len(selected)))
