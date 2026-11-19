"""Read-only surface sampling of actual supra cavity normals.

Unlike three trace lines, the sample covers separator side walls and ends.
This is a diagnostic: finite samples do not certify global wall thickness.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from engine.ray_material import first_material_exit

EPS = 1e-5
SOURCE_FACE_TOLERANCE = .003


def first_hit(mesh, origins, directions, batch=256, material_exit=False):
    points=np.full((len(origins),3),np.nan); faces=np.full(len(origins),-1,dtype=int)
    distances=np.full(len(origins),np.inf)
    for start in range(0,len(origins),batch):
        o=origins[start:start+batch]; n=directions[start:start+batch]
        loc,ray,tri=mesh.ray.intersects_location(o,n,multiple_hits=True)
        if not len(loc):continue
        d=np.einsum('ij,ij->i',loc-o[ray],n[ray])
        valid=d>EPS*.1;loc,ray,tri,d=loc[valid],ray[valid],tri[valid],d[valid]
        if material_exit:
            keep=[]
            dots=np.einsum('ij,ij->i',mesh.face_normals[tri],n[ray])
            for ray_id in np.unique(ray):
                local=np.flatnonzero(ray==ray_id)
                index=first_material_exit(d[local],dots[local],EPS*.1)
                if index is not None:keep.append(local[index])
            keep=np.asarray(keep,dtype=int)
        else:
            order=np.lexsort((d,ray));_,index=np.unique(ray[order],return_index=True);keep=order[index]
        ids=start+ray[keep];points[ids]=loc[keep];faces[ids]=tri[keep];distances[ids]=d[keep]
    return points,faces,distances


def sample(mesh, count, seed):
    rng=np.random.default_rng(seed)
    ids=rng.choice(len(mesh.faces),size=count,p=mesh.area_faces/mesh.area)
    uv=rng.random((count,2));uv[uv.sum(axis=1)>1]=1-uv[uv.sum(axis=1)>1]
    triangles=mesh.triangles[ids]
    points=triangles[:,0]+uv[:,0,None]*(triangles[:,1]-triangles[:,0])+uv[:,1,None]*(triangles[:,2]-triangles[:,0])
    return points,np.asarray(mesh.face_normals)[ids],ids


def protected(points, connections):
    """Diagnostic envelope label; it never permits cutting functional surfaces."""
    selected=np.zeros(len(points),dtype=bool)
    for c in connections:
        if 'protection_radius_mm' not in c:continue
        axis=np.asarray(c['normal'],dtype=float);axis/=np.linalg.norm(axis)
        delta=points-np.asarray(c['center']);height=delta@axis
        radial=np.linalg.norm(delta-height[:,None]*axis,axis=1)
        limit=np.full(len(points),c['protection_radius_mm'])
        env=c.get('protection_envelope',[])
        if len(env)>1:
            h=np.array([r['height_mm'] for r in env]);r=np.array([r['radius_mm'] for r in env])
            i=np.clip(np.searchsorted(h,height,side='right')-1,0,len(h)-2)
            limit=np.maximum(r[i],r[i+1])
        selected|=(height>=c['protection_bottom_mm'])&(height<=c['protection_top_mm'])&(radial<=limit/np.cos(np.pi/192)+EPS)
    return selected


def clusters(rows, field, limit=100, cell_mm=1.):
    result={}
    for row in sorted(rows,key=lambda r:r.get(field) if r.get(field) is not None else float('inf')):
        key=tuple(np.floor(np.asarray(row['primary_point_work'])/cell_mm).astype(int))
        result.setdefault(key,row)
    return list(result.values())[:limit]


def inspect(source, primary, supra, connections=(), minimum=.8, samples=12000, seed=170926):
    if not np.isfinite(minimum) or minimum<=0 or not 100<=samples<=100000:
        raise ValueError('Espesor positivo y entre 100 y 100000 muestras requeridos')
    for mesh in (source,primary,supra):
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
            raise ValueError('Se requieren mallas cerradas, orientadas y con volumen positivo')
    q,n,face=sample(primary,samples,seed)
    distance=np.empty(samples)
    for start in range(0,samples,256):
        distance[start:start+256]=trimesh.proximity.closest_point(source,q[start:start+256])[1]
    mask=distance>SOURCE_FACE_TOLERANCE
    original_rows=[{'primary_point_work':p.tolist(),'normal_work':v.tolist(),
                    'inside_functional_envelope':bool(b)}
                   for p,v,b in zip(q[~mask],n[~mask],protected(q[~mask],connections))]
    q,n,face=q[mask],n[mask],face[mask]
    origin=q+n*EPS
    _,source_face,source_exit=first_hit(source,origin,n,material_exit=True)
    entry,entry_face,entry_distance=first_hit(supra,origin,n)
    entering=np.zeros(len(q),dtype=bool)
    found=entry_face>=0
    entering[found]=np.einsum('ij,ij->i',supra.face_normals[entry_face[found]],n[found])<0
    valid=found&entering&np.isfinite(source_exit)&(entry_distance<source_exit-EPS)
    missing=[{'primary_point_work':p.tolist(),'normal_work':v.tolist(),
              'original_material_mm':float(d) if np.isfinite(d) else None,
              'inside_functional_envelope':bool(b)}
             for p,v,d,b in zip(q[~valid],n[~valid],source_exit[~valid],protected(q[~valid],connections))]
    q,n,face,entry,entry_face=q[valid],n[valid],face[valid],entry[valid],entry_face[valid]
    # The thickness ray follows the cavity's OWN normal, not a Z chord or
    # an unrelated normal of the metal/retention tool.
    inward=-np.asarray(supra.face_normals)[entry_face]
    _,exit_face,thickness=first_hit(supra,entry+inward*EPS,inward,material_exit=True)
    _,raw_face,raw_exit=first_hit(source,entry+inward*EPS,inward,material_exit=True)
    finite=np.isfinite(thickness)&np.isfinite(raw_exit)
    within=finite&(thickness<=raw_exit+.0001)
    exiting=np.zeros(len(q),dtype=bool)
    exiting[within]=np.einsum('ij,ij->i',supra.face_normals[exit_face[within]],inward[within])>0
    good=within&exiting
    rows=[]
    labels=protected(q,connections)
    for i in np.flatnonzero(good):
        rows.append({'primary_point_work':q[i].tolist(),'cavity_point_work':entry[i].tolist(),
            'normal_into_supra_work':inward[i].tolist(),'thickness_mm':float(thickness[i]+EPS),
            'first_original_exit_mm':float(raw_exit[i]+EPS),
            'primary_face':int(face[i]),'cavity_face':int(entry_face[i]),
            'supra_exit_face':int(exit_face[i]),'original_exit_face':int(raw_face[i]),
            'inside_functional_envelope':bool(labels[i])})
    thin=[row for row in rows if row['thickness_mm']<minimum-1e-5]
    return {'status':'WALL_DEFECTS_FOUND' if thin or missing else
                    ('INCOMPLETE_WALL_MEASUREMENTS' if (~good).any() else
                    ('NO_DEFECT_IN_SAMPLED_WALLS' if rows else 'NO_WALL_MEASUREMENTS')),
        'minimum_required_mm':minimum,'surface_samples':samples,'separator_samples':int(mask.sum()),
        'measured_wall_count':len(rows),'thin_wall_count':len(thin),'missing_cavity_count':len(missing),
        'invalid_wall_ray_count':int((~good).sum()),
        'minimum_sampled_wall_mm':min((r['thickness_mm'] for r in rows),default=None),
        'worst_wall_clusters':clusters(thin,'thickness_mm'),
        'missing_cavity_clusters':clusters(missing,'original_material_mm'),
        'walls':rows,'original_skin_clusters':clusters(original_rows,'unused',cell_mm=2.),
        'global_minimum_verified':False,'seed':seed,'source_face_classification_tolerance_mm':SOURCE_FACE_TOLERANCE,
        'material_interpretation':'Positive oriented material; first exit before a void. Internal overlapping surfaces are not repaired or approved.',
        'scope':'Muestreo de superficie de primaria, entrada en supra y espesor en la normal interior real de su cavidad. Cada rayo se limita al primer intervalo del original. No certifica espesor global, soporte, fabricación ni trayectoria.',
        'original_skin_note':'Las caras coincidentes con el original se registran aparte. Distinguir superficies cervicales o funcionales previstas de ventanas no deseadas según las capturas; su presencia no implica por sí sola un defecto.',
        'functional_note':'La etiqueta de envolvente es diagnóstica. No autoriza recortar conexiones; su conservación se comprueba externamente.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--samples',type=int,default=12000)
    args=parser.parse_args()
    def mesh(name):
        with np.load(args.run_dir/'work/inf_independiente'/name) as d:
            return trimesh.Trimesh(d['vertices'],d['faces'],process=False)
    profile=json.loads((args.run_dir/'perfil_ejecutado.json').read_text(encoding='utf-8-sig'))
    report=inspect(mesh('entrada.npz'),mesh('Primaria_final.npz'),mesh('Supra.npz'),
                   profile.get('connections',[]),profile.get('minimum_supra_mm',.8),args.samples)
    report.update(run_directory=str(args.run_dir.resolve()),coordinates='working')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','measured_wall_count','thin_wall_count','missing_cavity_count','minimum_sampled_wall_mm')}))


if __name__=='__main__':main()
