"""Exercise the real geometry pipeline using a synthetic, non-patient bridge."""
import argparse,json,subprocess,sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--blender',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--retentions',action='store_true')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    app=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(app/'engine'))
    import manifold3d as mf
    import trimesh
    from prepare_profile import prepare
    folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    body=mf.Manifold.cube([28,10,10]).translate([-14,-5,0])
    for x in (-8,8):
        cavity=mf.Manifold.cylinder(3.1,2.2,2.2,96).translate([x,0,-.1])
        cavity=cavity+mf.Manifold.cylinder(11,1.1,1.1,96).translate([x,0,-.1])
        body=body-cavity
    data=body.to_mesh64()
    mesh=trimesh.Trimesh(data.vert_properties[:,:3],data.tri_verts,process=True)
    source=folder/'synthetic-bridge.stl';mesh.export(source)
    profile,report=prepare(source,'24-25-26 synthetic bridge',{})
    if args.retentions:profile['retention_mode']='dual_required'
    profile_path=folder/'profile.json'
    profile_path.write_text(json.dumps(profile,indent=2),encoding='utf-8')
    (folder/'preparation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    command=[sys.executable,str(app/'engine/ejecutar.py'),'--input',str(source),
      '--profile',str(profile_path),'--run-dir',str(folder/'run'),'--blender',args.blender]
    if args.live:command.append('--live-blender')
    subprocess.run(command,check=True)
    state=json.loads((folder/'run/Ejecucion.json').read_text())
    assert state['status']=='GEOMETRY_PASS_DESIGN_REVIEW_PENDING',state['status']
    if args.retentions:
        stages=json.loads((folder/'run/outputs/Proceso/progreso.json').read_text())['stages']
        assert all(stages[i-1]['status']=='done' for i in (7,8,9))
    if args.live:
        capture=folder/'run/outputs/Proceso/Blender/ventana.json'
        frames=json.loads(capture.read_text())['frames']
        assert frames and all((folder/'run/outputs'/f['path']).is_file() for f in frames)
        assert {3,5,12}.issubset({f['step'] for f in frames})
    print('SYNTHETIC_NATIVE_GEOMETRY_PASS — design review remains pending')

if __name__=='__main__':main()
