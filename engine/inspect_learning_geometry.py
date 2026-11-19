"""Read geometry evidence without executing embedded code or exporting meshes."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np


def stored_matrix(obj,seen=None):
    """Hidden/unlinked objects can have an unevaluated zero matrix_world."""
    seen=set() if seen is None else set(seen)
    if id(obj) in seen or obj.constraints or (obj.parent and obj.parent_type!='OBJECT'):return None
    seen.add(id(obj));basis=np.asarray(obj.matrix_basis,dtype=float)
    if obj.parent:
        parent=stored_matrix(obj.parent,seen)
        return None if parent is None else parent@np.asarray(obj.matrix_parent_inverse,dtype=float)@basis
    return basis


def inspect_stl(path):
    import trimesh
    mesh=trimesh.load(path,force='mesh')
    return {'format':'STL','units':'input units; STL does not encode units',
        'vertices':len(mesh.vertices),'triangles':len(mesh.faces),
        'bounds':mesh.bounds.tolist(),'dimensions':mesh.extents.tolist(),
        'signed_volume':float(mesh.volume),'watertight':bool(mesh.is_watertight),
        'winding_consistent':bool(mesh.is_winding_consistent),'euler':int(mesh.euler_number),
        'component_count':len(mesh.split(only_watertight=False))}


def inspect_blend(path):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    rows=[]
    for obj in list(bpy.data.objects)[:256]:
        matrix=stored_matrix(obj)
        row={'name':obj.name,'type':obj.type,'matrix_world':matrix.tolist() if matrix is not None else None,
            'transform_method':'Stored basis and object parent chain' if matrix is not None else 'Unresolved constraints or non-object parenting; world dimensions omitted',
            'hidden_viewport':bool(obj.hide_viewport),'hidden_render':bool(obj.hide_render),
            'modifiers':[{'name':m.name,'type':m.type,**{k:getattr(m,k) for k in
                ('thickness','offset','voxel_size','levels','operation') if hasattr(m,k)}} for m in obj.modifiers]}
        if obj.type=='MESH':
            mesh=obj.data;verts=np.empty(len(mesh.vertices)*3,dtype=float)
            mesh.vertices.foreach_get('co',verts);verts=verts.reshape(-1,3)
            if len(verts) and matrix is not None:
                world=verts@matrix[:3,:3].T+matrix[:3,3]
                row.update(bounds_world=[world.min(0).tolist(),world.max(0).tolist()],dimensions_world=np.ptp(world,axis=0).tolist())
                if len(verts)<=100:row['small_control_mesh_vertices_world']=world.tolist()
            mesh.calc_loop_triangles();tri=np.empty(len(mesh.loop_triangles)*3,dtype=np.int32)
            mesh.loop_triangles.foreach_get('vertices',tri);tri=tri.reshape(-1,3)
            volume=float(np.einsum('ij,ij->i',verts[tri[:,0]],np.cross(verts[tri[:,1]],verts[tri[:,2]])).sum()/6*np.linalg.det(matrix[:3,:3])) if len(tri) and matrix is not None else None
            loop_edges=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('edge_index',loop_edges)
            uses=np.bincount(loop_edges,minlength=len(mesh.edges))
            row.update(vertices=len(verts),polygons=len(mesh.polygons),triangles=len(tri),
                signed_volume=volume,non_two_face_edges=int(np.count_nonzero(uses!=2)),
                vertex_groups=[g.name for g in obj.vertex_groups])
            if mesh.skin_vertices and len(verts)<=100:
                row['skin_radii']=[list(v.radius) for v in mesh.skin_vertices[0].data]
        rows.append(row)
    return {'format':'BLEND','reader_version':bpy.app.version_string,'file_version':list(bpy.data.version),
        'unit_system':bpy.context.scene.unit_settings.system,'unit_scale':bpy.context.scene.unit_settings.scale_length,
        'object_count':len(bpy.data.objects),'objects':rows,'objects_truncated':len(bpy.data.objects)>len(rows),
        'embedded_text_names':[t.name for t in bpy.data.texts],
        'measurement_scope':'Stored mesh data and object transforms, before evaluation of modifiers. Hidden meshes measured directly; embedded scripts disabled.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    path=Path(args.input)
    report=inspect_blend(path) if path.suffix.lower() in {'.blend','.blend1'} else inspect_stl(path)
    report.update(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        provenance='Measured reference evidence, not a generated segmentation or laboratory approval.',
        geometry_exported=False)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf8')
    print('GEOMETRY_EVIDENCE_SAVED',flush=True)


if __name__=='__main__':main()
