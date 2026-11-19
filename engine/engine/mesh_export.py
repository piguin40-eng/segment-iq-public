"""Separate coincident vertex fans without simplifying functional surfaces."""
import io
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def prepare_indexed_export(mesh,transform,expected_euler=None):
    """Preserve Boolean topology in both STL coordinate frames, or fail closed.

    This only separates coincident indexed vertices by at most 1e-6 mm. It
    does not close holes, simplify, remove components or accept a design.
    """
    if (not len(mesh.faces) or not np.isfinite(mesh.vertices).all()
            or not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0):
        raise RuntimeError('La malla indexada no es un volumen cerrado orientado; revisar la separacion antes de exportar.')
    if expected_euler is not None and mesh.euler_number!=expected_euler:
        raise RuntimeError('La malla indexada tiene una topologia no prevista; no se reparara durante la exportacion.')
    result,contacts=separate_export_contacts(mesh,transform)
    if contacts['maximum_shift_mm']>1.000001e-6:
        raise RuntimeError('La separacion de contactos supera el limite numerico de exportacion.')
    frames={}
    for name,matrix in [('work',np.eye(4)),('original',transform)]:
        exported=result.copy();exported.apply_transform(matrix)
        reloaded=trimesh.load(io.BytesIO(exported.export(file_type='stl_ascii').encode('utf-8')),
                              file_type='stl',force='mesh')
        if (not reloaded.is_watertight or not reloaded.is_winding_consistent
                or reloaded.euler_number!=mesh.euler_number or reloaded.volume<=0):
            raise RuntimeError('La malla no conserva su topologia al reimportar el STL en coordenadas '+name+'.')
        frames[name]={'closed':True,'consistent_winding':True,'euler':int(reloaded.euler_number),
                      'volume_mm3':float(reloaded.volume)}
    return result,{'vertex_contacts':contacts,'roundtrip':frames,
                   'volume_change_mm3':float(result.volume-mesh.volume),
                   'scope':'Serializacion comprobada; no acredita espesores, insercion ni aprobacion de diseno.'}


def separate_export_contacts(mesh,transform,epsilon=1e-6):
    """Keep indexed topology while separating positions that STL would weld.

    Boolean meshes already distinguish touching surface fans by vertex index.
    Preserve that information before any positional merge loses it. The bound
    applies in mesh coordinates; final functional checks still apply normally.
    """
    original=mesh.vertices.copy();vertices=original.copy();moved=set()
    # Distinct deterministic directions for vertices in a coincident cluster.
    # Repeat only if rounding in either coordinate frame still merges points.
    for attempt in range(3):
        grouped=[]
        for coordinates in (vertices,trimesh.transform_points(vertices,transform)):
            _,labels,counts=np.unique(np.round(coordinates,8),axis=0,return_inverse=True,return_counts=True)
            for label in np.flatnonzero(counts>1):grouped.append(np.flatnonzero(labels==label))
        if not grouped:break
        for ids in grouped:
            count=len(ids);i=np.arange(count);z=1-2*(i+.5)/count
            angle=i*(np.pi*(3-np.sqrt(5)))+attempt*.7
            directions=np.column_stack([np.sqrt(1-z*z)*np.cos(angle),np.sqrt(1-z*z)*np.sin(angle),z])
            vertices[ids]=original[ids]+epsilon*directions;moved.update(ids.tolist())
    result=trimesh.Trimesh(vertices,mesh.faces.copy(),process=False)
    maximum=float(np.linalg.norm(vertices-original,axis=1).max(initial=0.))
    return result,{'separated_vertices':len(moved),'maximum_shift_mm':maximum,
                  'method':'Preserve indexed Boolean topology before STL coordinate welding.'}


def separate_vertex_contacts(mesh,epsilon=1e-6):
    faces=mesh.faces;adj=mesh.face_adjacency;edges=mesh.face_adjacency_edges
    a=[];b=[]
    for j in (0,1):
        a.append(adj[:,0]*3+np.argmax(faces[adj[:,0]]==edges[:,j,None],axis=1))
        b.append(adj[:,1]*3+np.argmax(faces[adj[:,1]]==edges[:,j,None],axis=1))
    a=np.concatenate(a);b=np.concatenate(b)
    count,labels=connected_components(coo_matrix((np.ones(len(a)),(a,b)),shape=(faces.size,faces.size)),directed=False)
    _,first=np.unique(labels,return_index=True)
    original_ids=faces.ravel()[first]
    multiplicity=np.bincount(original_ids,minlength=len(mesh.vertices))
    split=np.flatnonzero(multiplicity[original_ids]>1)
    if not len(split):return mesh,{'separated_fans':0,'maximum_shift_mm':0.}
    vertices=mesh.vertices[original_ids].copy()
    normals=np.zeros((count,3));weighted=np.repeat(mesh.face_normals*mesh.area_faces[:,None],3,axis=0)
    np.add.at(normals,labels,weighted)
    lengths=np.linalg.norm(normals[split],axis=1)
    if np.any(lengths<1e-15):raise RuntimeError('Contacto singular sin una dirección de separación verificable.')
    vertices[split]-=epsilon*normals[split]/lengths[:,None]
    result=trimesh.Trimesh(vertices,labels.reshape(-1,3),process=False)
    return result,{'separated_fans':len(split),'maximum_shift_mm':epsilon}
