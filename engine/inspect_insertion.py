"""Read-only collision sampling for an explicitly identified extraction direction.

Discrete free positions do not certify the continuous path or choose a clinical
insertion axis. A measured collision is evidence to investigate, not an approval.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf


def direction_for(profile, explicit=None):
    if explicit is not None:return explicit,'explicit_test_direction'
    proposal=profile.get('shape_refinement',{}).get('proposed_insertion_direction_work')
    return (proposal,'profile_proposal_not_approved') if proposal is not None else ([0,0,1],'provisional_working_Z')


def inspect(primary, supra, direction=(0, 0, 1), step=.125):
    axis=np.asarray(direction,dtype=float)
    if axis.shape!=(3,) or not np.isfinite(axis).all() or np.linalg.norm(axis)<1e-8:
        raise ValueError('La dirección de extracción debe ser un vector finito no nulo')
    if not np.isfinite(step) or step<=0:
        raise ValueError('El paso debe ser positivo y finito')
    axis/=np.linalg.norm(axis)
    for mesh in (primary,supra):
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
            raise ValueError('La comprobación requiere dos mallas cerradas y orientadas')
    clearance=max(0.,float((primary.vertices@axis).max()-(supra.vertices@axis).min()))+step
    count=int(np.ceil(clearance/step))+1
    if count>500:raise ValueError('Más de 500 posiciones: comprobar unidades y paso de muestreo')
    def solid(mesh):return mf.Manifold(mf.Mesh64(np.float64(mesh.vertices),np.uint64(mesh.faces)))
    fixed=solid(primary);moving=solid(supra)
    rows=[]
    for distance in np.linspace(0,clearance,count):
        collision=fixed ^ moving.translate(tuple(axis*distance))
        rows.append({'distance_mm':float(distance),'collision_volume_mm3':float(collision.volume())})
    maximum=max(row['collision_volume_mm3'] for row in rows)
    return {'status':'COLLISION_DETECTED' if maximum>1e-5 else 'NO_COLLISION_IN_SAMPLED_POSITIONS',
            'direction_work':axis.tolist(),'requested_step_mm':float(step),'sample_count':count,
            'maximum_collision_mm3':maximum,'samples':rows,'continuous_path_verified':False,
            'scope':'Traslaciones discretas de supra respecto a primaria. No certifica trayectoria continua, paredes, resistencia ni elección clínica del eje.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--direction',type=float,nargs=3)
    parser.add_argument('--step',type=float,default=.125)
    args=parser.parse_args()
    def mesh(name):
        with np.load(args.run_dir/'work/inf_independiente'/name) as data:
            return trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    profile=json.loads((args.run_dir/'perfil_ejecutado.json').read_text(encoding='utf-8-sig'))
    direction,origin=direction_for(profile,args.direction)
    report=inspect(mesh('Primaria_final.npz'),mesh('Supra.npz'),direction,args.step)
    report.update(run_directory=str(args.run_dir.resolve()),coordinates='working',
        axis_origin=origin,axis_selection='Dirección de ensayo explícita o propuesta del perfil; Z de trabajo por defecto. No equivale al eje de cada implante ni a un eje de inserción aprobado.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','sample_count','maximum_collision_mm3')},ensure_ascii=False))


if __name__=='__main__':main()
