import sys,json,hashlib
from pathlib import Path
import trimesh
path=Path(sys.argv[1]);m=trimesh.load(path,force='mesh')
report={'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'vertices':len(m.vertices),'faces':len(m.faces),'bounds_input_units':m.bounds.tolist(),'dimensions_input_units':m.extents.tolist(),'volume_input_units3':float(m.volume),'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),'interpretation':'STL no codifica unidades ni identidad anatomica; confirmar mm y orientacion. Estas medidas globales no determinan el perfil de barra.'}
Path(sys.argv[2]).write_text(json.dumps(report,indent=2),encoding='utf-8')
