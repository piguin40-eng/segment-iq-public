import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
import sys,os,json,hashlib
sys.path.insert(0,os.environ.get('DENTAL_PYTHON_DEPS',os.path.abspath('work/mesh_packages')))
from pathlib import Path
import trimesh,numpy as np
root=Path('work/inf_independiente');root.mkdir(parents=True,exist_ok=True);Path('outputs/Inferior_independiente').mkdir(parents=True,exist_ok=True);src=Path(C['input'])
m=trimesh.load(src,force='mesh');center=m.vertices.mean(0);val,axes=np.linalg.eigh(np.cov((m.vertices-center).T));T=np.eye(4);T[:3,:3]=axes[:,[2,1,0]].T
if np.linalg.det(T[:3,:3])<0:T[0,:3]*=-1
T[:3,3]=-T[:3,:3]@center;T=np.diag([1,1,-1,1])@T
if C['raw_to_work'] is not None:T=np.array(C['raw_to_work'],dtype=float)
m.apply_transform(T);m.export(root/'Entrada_orientada.stl');np.savez(root/'entrada.npz',vertices=m.vertices,faces=m.faces)
json.dump({'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'raw_to_work':T.tolist(),'volume_mm3':m.volume,'geometry_sources':[str(src)],'reference_geometry_imported':False},open(root/'procedencia.json','w'),indent=2)
# A measured profile already has both borders, including linear short bridges.
if C.get('trace_xy'):
 np.savez(root/'trazado_xy.npz',xy=np.asarray(C['trace_xy'],dtype=float))
 print('INPUT',m.volume,m.bounds,'measured trace',len(C['trace_xy']),flush=True)
 sys.exit(0)
# Trace two anatomical borders independently from radial bands of the raw arch.
v=m.vertices;angle=np.arctan2(v[:,0],C['trace_center_y']-v[:,1]);radius=np.sqrt(v[:,0]**2+(C['trace_center_y']-v[:,1])**2)
lo,hi=np.percentile(angle,[1.2,98.8]);theta=np.linspace(lo+.015,hi-.015,C['trace_samples']);rows=[]
for t in theta:
 rr=radius[np.abs(angle-t)<.055];q=np.percentile(rr,C['trace_quantiles']);rows.append(q)
r=np.array(rows)
from scipy.ndimage import gaussian_filter1d
r=gaussian_filter1d(r,1.0,axis=0);outer=np.column_stack([r[:,1]*np.sin(theta),C['trace_center_y']-r[:,1]*np.cos(theta)]);inner=np.column_stack([r[:,0]*np.sin(theta),C['trace_center_y']-r[:,0]*np.cos(theta)]);contour=np.concatenate([outer,inner[::-1]])
if C.get('trace_xy'):contour=np.array(C['trace_xy'],dtype=float)
np.savez(root/'trazado_xy.npz',xy=contour,theta=theta,radii=r);print('INPUT',m.volume,m.bounds,'trace',contour.shape,flush=True)
