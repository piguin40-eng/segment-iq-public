import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dental_config import C
import sys,os
sys.path.insert(0,os.environ.get('DENTAL_PYTHON_DEPS',os.path.abspath('work/mesh_packages')))
import numpy as np,trimesh,manifold3d as mf
import io,json
from mesh_export import separate_export_contacts,prepare_indexed_export
from pathlib import Path
inverse=np.linalg.inv(np.asarray(json.load(open('work/inf_independiente/procedencia.json'))['raw_to_work']))
d=np.load('work/inf_independiente/Primaria_dual.npz');r=mf.Manifold(mf.Mesh64(d['vertices'].astype('float64'),d['faces'].astype('uint64')))
# A mesh-array round trip can expose coincident sheets of zero volume from
# Boolean contact faces. Remove only numerical zero-volume components; any
# second material component is a failed design, not something to hide.
parts=r.decompose();material=[part for part in parts if abs(part.volume())>1e-10]
if len(material)!=1:raise RuntimeError('La barra contiene varios componentes de metal después de serializar las retenciones.')
if len(parts)>1:print('ZERO_VOLUME_SHEETS',len(parts)-1,flush=True)
r=material[0]
for eps in [0,1e-7,1e-6]:
 a=r.simplify(eps) if eps else r
 candidate_parts=a.decompose();candidate_material=[part for part in candidate_parts if abs(part.volume())>1e-10]
 if len(candidate_material)!=1:continue
 a=candidate_material[0];me=a.to_mesh64()
 # Positional welding followed by deleting narrow triangles destroys the
 # closed topology supplied by the Boolean kernel. Preserve its vertex IDs.
 m=trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts,process=False)
 print(eps,m.is_watertight,m.euler_number,flush=True)
 expected=C.get('expected_euler_by_mesh',{}).get('primaria',C['expected_euler'])
 if expected is None:expected=2-2*r.genus()
 if m.is_watertight and m.euler_number==expected:
  m,contacts=separate_export_contacts(m,inverse)
  print('EXPORT_CONTACTS',contacts,m.euler_number,flush=True)
  # Validate serialization in the original coordinate frame before selecting
  # a cleanup candidate. Translation changes vertex welding at tiny slivers;
  # a closed mesh in work coordinates alone is insufficient.
  exported=m.copy();exported.apply_transform(inverse)
  payload=exported.export(file_type='stl_ascii').encode('utf-8')
  reloaded=trimesh.load(io.BytesIO(payload),file_type='stl',force='mesh')
  local_reload=trimesh.load(io.BytesIO(m.export(file_type='stl_ascii').encode('utf-8')),file_type='stl',force='mesh')
  if any(not item.is_watertight or not item.is_winding_consistent or item.euler_number!=m.euler_number for item in (reloaded,local_reload)):
   print('EXPORT_ROUNDTRIP_REJECTED',eps,flush=True);continue
  m.export('work/inf_independiente/Primaria_final.stl',file_type='stl_ascii');np.savez('work/inf_independiente/Primaria_final.npz',vertices=m.vertices,faces=m.faces)
  Path('outputs/Inferior_independiente/Limpieza_exportacion.json').write_text(json.dumps({'simplification_mm':eps,'zero_volume_components_removed':len(parts)-len(material),'vertex_contacts':contacts,'original_frame_roundtrip_closed':True,'euler':int(reloaded.euler_number)},indent=2),encoding='utf-8');break
else:raise RuntimeError('No valid mesh')

# Supra needs the same indexed-contact treatment as the primary. Reading its
# intermediate STL first would already have welded the distinct surface fans.
with np.load('work/inf_independiente/Supra.npz') as d:
 s=trimesh.Trimesh(d['vertices'],d['faces'],process=False)
expected=C.get('expected_euler_by_mesh',{}).get('supra',C['expected_euler'])
s,supra_report=prepare_indexed_export(s,inverse,expected_euler=expected)
s.export('work/inf_independiente/Supra_export.stl',file_type='stl_ascii')
np.savez('work/inf_independiente/Supra_export.npz',vertices=s.vertices,faces=s.faces)
Path('outputs/Inferior_independiente/Exportacion_supra.json').write_text(json.dumps(supra_report,indent=2),encoding='utf-8')
print('SUPRA_EXPORT_ROUNDTRIP_OK',supra_report,flush=True)
