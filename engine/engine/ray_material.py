"""Read-only intervals in positive oriented mesh volume; no mesh repair."""
import numpy as np


def first_material_exit(distances, normal_dots, epsilon=1e-6):
    """Return the first filled-to-empty crossing, not an internal overlap.

    Recover the oriented count at the origin from all crossings toward empty
    space at infinity. Stop before the first void, even when more material
    lies farther away. Outside, tangent or invalid rays have no valid exit.
    This interpretation does not repair or approve self-intersecting meshes.
    """
    distances=np.asarray(distances);normal_dots=np.asarray(normal_dots)
    valid=np.flatnonzero((distances>epsilon)&np.isfinite(distances))
    if not len(valid) or not np.isfinite(normal_dots[valid]).all():return None
    if np.any(abs(normal_dots[valid])<1e-8):return None
    order=valid[np.argsort(distances[valid])]
    signs=np.sign(normal_dots[order]).astype(int)
    level=int(signs.sum())
    if level<=0:return None
    for index,sign in zip(order,signs):
        level-=int(sign)
        if level==0:return int(index)
        if level<0:return None
    return None
