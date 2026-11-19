"""Render the geometry that exists after a completed step, without changing it."""
import sys, os, json
from pathlib import Path
import bpy, numpy as np
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:];step=int(args[0]);destination=Path(args[1])
root=Path('work/inf_independiente')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('Proceso')
scene.world.color=(.035,.045,.065)
gold=(.78,.48,.13,1);white=(.82,.86,.92,1);red=(.95,.12,.22,1)
shown=[]
def add(name,color,shift=0):
    data=np.load(root/(name+'.npz'));v=data['vertices'];f=data['faces']
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update()
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.color=color
    obj.location.x=shift
    for face in mesh.polygons:face.use_smooth=True
    shown.extend((v+np.array([shift,0,0])).tolist())
    return obj
source=np.load(root/'entrada.npz')['vertices'];width=float(np.ptp(source[:,0]))
spacing=width*.6+2
if step<=2:
    add('entrada',white)
    if step==2:
        for c in json.loads((root/'conexiones.json').read_text()):
            center=Vector(c['center']);axis=Vector(c['normal'])
            curve=bpy.data.curves.new('Eje medido','CURVE');curve.dimensions='3D';curve.bevel_depth=.13
            line=curve.splines.new('POLY');line.points.add(1)
            for p,co in zip(line.points,[center-axis*2,center+axis*12]):p.co=(*co,1)
            obj=bpy.data.objects.new('Eje de chimenea',curve);scene.collection.objects.link(obj);obj.color=red
elif step in (3,4,5):
    add('entrada',white,-spacing)
    add({3:'core_trazado',4:'core_union',5:'core_remallado'}[step],gold,spacing)
    if step==3:
        for path in sorted(root.glob('Cone_*.npz')):add(path.stem,red,spacing)
    # The boolean tool extends below the anatomy. Show only its working section;
    # the saved geometry remains complete and unmodified.
    for obj in list(scene.objects):
        if obj.type=='MESH' and obj.name!='entrada':
            import bmesh
            bm=bmesh.new();bm.from_mesh(obj.data)
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,
                plane_co=(0,0,float(source[:,2].min())-.6),plane_no=(0,0,1),clear_inner=True)
            bm.to_mesh(obj.data);bm.free()
    bpy.context.view_layer.update()
    shown=[tuple(obj.matrix_world@v.co) for obj in scene.objects if obj.type=='MESH' for v in obj.data.vertices]
elif step in (6,9,10,11,13):
    primary='Primaria_sin_retenciones' if step==6 else 'Primaria_dual' if step==9 else 'Primaria_final'
    add(primary,gold,-spacing);add('Supra',white,spacing)
elif step==8:
    add('Primaria_sin_retenciones',gold);add('Retencion_dual_tool',red)
else:
    raise ValueError('Paso sin una vista geométrica definida')
bpy.context.view_layer.update()
points=np.array(shown);center=(points.min(0)+points.max(0))/2;extent=np.ptp(points,axis=0)
bpy.ops.object.camera_add(location=Vector(center)+Vector((0,-65,145)))
camera=bpy.context.object;camera.rotation_euler=(Vector(center)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=max(extent[0]*1.18,extent[1]*1.9,extent[2]*1.5,12)
scene.camera=camera;scene.render.resolution_x=1100;scene.render.resolution_y=680;scene.render.resolution_percentage=100
destination.parent.mkdir(parents=True,exist_ok=True)
temporary=destination.with_name(destination.stem+'.tmp.png')
scene.render.filepath=str(temporary);bpy.ops.render.render(write_still=True)
os.replace(temporary,destination)
