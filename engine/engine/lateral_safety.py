"""Reserve material around isolated exterior breakthroughs of the separator.

This detects additional openings relative to the raw topology. It does not
certify a global wall thickness; all changes remain inside the original STL.
"""
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def exterior_islands(source,supra):
    centers=source.triangles_center;distances=[]
    for start in range(0,len(centers),4000):
        distances.extend(trimesh.proximity.closest_point(supra,centers[start:start+4000])[1])
    selected=np.asarray(distances)>.01
    ids=np.flatnonzero(selected)
    if not len(ids):return []
    lookup=np.full(len(centers),-1);lookup[ids]=np.arange(len(ids))
    edges=source.face_adjacency[np.all(selected[source.face_adjacency],axis=1)];edges=lookup[edges]
    count,labels=connected_components(coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(ids),len(ids))),directed=False)
    groups=[ids[labels==i] for i in range(count)]
    groups.sort(key=lambda ix:-source.area_faces[ix].sum())
    return [{'points':centers[ix], 'area_mm2':float(source.area_faces[ix].sum())} for ix in groups[1:] if source.area_faces[ix].sum()>.005]
