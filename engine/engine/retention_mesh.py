"""Mesh preparation rules shared by Blender and the retention boolean stage."""
import math
import numpy as np


def decimation_ratio(face_count, requested=.015, minimum_faces=32):
    if face_count < 1:
        raise ValueError('No queda superficie segura para construir la red de retenciones; revisar el cuerpo de la barra.')
    if not math.isfinite(requested) or not 0 < requested <= 1 or minimum_faces < 3:
        raise ValueError('Parametros de simplificacion de retenciones invalidos')
    # One spare face avoids float32 rounding below the target in Blender.
    return min(1., max(float(requested), (minimum_faces + 1.) / face_count))


def triangle_arrays(vertices, faces):
    """Normalize an empty tool or validate a nonempty one without repairing it."""
    vertices=np.asarray(vertices,dtype=np.float64);faces=np.asarray(faces)
    if vertices.size==0 and faces.size==0:
        return np.empty((0,3),dtype=np.float64),np.empty((0,3),dtype=np.uint64)
    if vertices.ndim!=2 or vertices.shape[1]!=3 or faces.ndim!=2 or faces.shape[1]!=3:
        raise ValueError('La herramienta de retenciones no contiene vertices y triangulos validos')
    if not np.isfinite(vertices).all() or not np.issubdtype(faces.dtype,np.integer):
        raise ValueError('La herramienta de retenciones contiene coordenadas o indices invalidos')
    if not len(vertices) or not len(faces) or np.any(faces<0) or np.any(faces>=len(vertices)):
        raise ValueError('La herramienta de retenciones contiene triangulos incompletos')
    return np.ascontiguousarray(vertices),np.ascontiguousarray(faces,dtype=np.uint64)
