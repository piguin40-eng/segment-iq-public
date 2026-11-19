"""Distinguish equal-volume shape changes from an identical exported proposal."""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf


def solid(path):
    mesh=trimesh.load(path,force='mesh')
    return mf.Manifold(mf.Mesh64(np.float64(mesh.vertices),np.uint64(mesh.faces)))


def compare(before,after):
    result={}
    for label,prefix in [('primaria','Primaria_'),('supra','Supra_')]:
        old=list(before.glob(prefix+'*_PROPIA.stl'))
        new=list(after.glob(prefix+'*_PROPIA.stl'))
        if len(old)!=1 or len(new)!=1:raise ValueError('Falta una pieza inequívoca para comparar')
        a,b=solid(old[0]),solid(new[0])
        result[label]={'symmetric_difference_mm3':float((a-b).volume()+(b-a).volume())}
    result['geometry_changed']=max(v['symmetric_difference_mm3'] for v in result.values())>1e-5
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('before',type=Path);parser.add_argument('after',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(compare(args.before,args.after),indent=2),encoding='utf-8')
