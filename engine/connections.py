"""Chimney axes and functional protection measured solely on the incoming mesh.

Interface brands and implant catalogues are deliberately not used: the finished
primary retains the incoming functional surface by exact solid intersection.
"""
import numpy as np
import trimesh


def frame(normal):
    z = np.asarray(normal, dtype=float); z /= np.linalg.norm(z)
    ref = np.eye(3)[np.argmin(abs(z))]
    x = np.cross(z, ref); x /= np.linalg.norm(x)
    return x, np.cross(z, x), z


def group_chimneys(mesh, candidates):
    groups = []
    for ring in sorted(candidates, key=lambda c: -c['vertices']):
        center = np.asarray(ring['center']); normal = np.asarray(ring['normal'])
        for group in groups:
            ref = group[0]; delta = center - ref['center']; axis = np.asarray(ref['normal'])
            if abs(normal @ axis) > .998 and np.linalg.norm(delta-axis*(delta@axis)) < .06:
                group.append(ring); break
        else:
            groups.append([ring])
    connections, diagnostics = [], []
    # A high anterior connection can lie above the whole-arch centroid. Using
    # that centroid separately for each socket reverses those axes and measures
    # the screw exit as the basal seat. Establish one coherent crown direction
    # for the candidate set, then retain each connection's own inclination.
    # Isolated circles are not chimney evidence. Letting their locations set
    # polarity can point all sockets toward the basal exterior of the arch.
    # Use only groups with the same axial evidence required below.
    axial_groups=[group for group in groups if len(group)>=2 and
        np.ptp(np.asarray([r['center'] for r in group])@np.asarray(group[0]['normal']))>=.1]
    ring_normals=np.asarray([r['normal'] for group in axial_groups for r in group])
    if not len(ring_normals):raise ValueError('No se han localizado anillos para orientar las conexiones.')
    _,vectors=np.linalg.eigh(ring_normals.T@ring_normals)
    crown_axis=vectors[:,-1]
    group_centers=np.asarray([np.mean([r['center'] for r in group],axis=0) for group in axial_groups])
    if crown_axis@(mesh.centroid-group_centers.mean(0))<0:crown_axis=-crown_axis
    for group in groups:
        c = np.mean([r['center'] for r in group], axis=0)
        normals = np.asarray([r['normal'] for r in group])
        _, vectors = np.linalg.eigh(normals.T @ normals); axis = vectors[:, -1]
        if axis @ crown_axis < 0: axis = -axis
        u, v, axis = frame(axis)
        heights = (np.asarray([r['center'] for r in group])-c) @ axis
        order = np.argsort(heights); group = [group[i] for i in order]; heights = heights[order]
        base = np.asarray(group[0]['center']); heights -= heights[0]
        span = float(heights[-1])
        if len(group) < 2 or span < .1:
            diagnostics.append({'center':c.tolist(),'reason':'Sin evidencia axial suficiente de chimenea'}); continue
        # Test the measured channel, not an infinite ray through the entire
        # arch. Beyond an open angled chimney the same line can hit another
        # tooth; that remote material does not close this connection.
        projected = (mesh.vertices-base) @ axis
        low, high = float(projected.min()-1), float(projected.max()+1)
        axial_origin = base+axis*low
        hits, _, _ = mesh.ray.intersects_location([axial_origin], [axis], multiple_hits=True)
        hit_heights=(np.asarray(hits).reshape(-1,3)-base)@axis
        if np.any((hit_heights>=-.05)&(hit_heights<=span+.05)):
            diagnostics.append({'center':c.tolist(),'reason':'El eje atraviesa material; no es una chimenea abierta'}); continue
        # Check circumferential inward walls at multiple levels, including the
        # gaps between sharp circular features. Noncircular/hex walls also pass.
        levels = np.linspace(.025, max(.05, span-.025), 9)
        angles = np.linspace(0,2*np.pi,48,endpoint=False)
        directions = np.cos(angles)[:,None]*u+np.sin(angles)[:,None]*v
        origins = np.repeat(base+levels[:,None]*axis, len(angles), axis=0)
        rays = np.tile(directions,(len(levels),1))
        xyz, ids, triangles = mesh.ray.intersects_location(origins,rays,multiple_hits=False)
        distances = np.full(len(origins),np.inf)
        distances[ids] = np.linalg.norm(xyz-origins[ids],axis=1)
        inward = np.zeros(len(origins),dtype=bool)
        inward[ids] = np.einsum('ij,ij->i',mesh.face_normals[triangles],rays[ids]) < -.2
        valid = (distances>.3)&(distances<5)&inward
        covered = valid.reshape(len(levels),len(angles)).mean(1)
        if np.count_nonzero(covered>.95) < 7:
            diagnostics.append({'center':c.tolist(),'reason':'Pared de chimenea no confirmada en varias alturas','coverage':covered.tolist()}); continue
        largest = max(r['radius'] for r in group)
        # First narrow ring above the basal connection bounds its upper neck.
        necks = [h for r,h in zip(group,heights) if h>.2 and r['radius']<.78*largest]
        neck = float(min(necks) if necks else span)
        # An annular step above the first narrow neck is still a measured
        # connection surface. A lone ring at the occlusal opening is not such
        # evidence and must not extend protection through the whole crown.
        shoulders=[float(h) for r,h in zip(group,heights)
                   if any(abs(h-other_h)<.002 and abs(r['radius']-other['radius'])>.05
                          for other,other_h in zip(group,heights))]
        functional_top=max([neck]+shoulders)
        basal = [r['radius'] for r,h in zip(group,heights) if h<=neck+.001]
        wall_radius = float(np.max(distances.reshape(len(levels),-1)[levels<=neck][np.isfinite(distances.reshape(len(levels),-1)[levels<=neck])]))
        perimeter = max(max(basal),wall_radius)
        # Measured noncircular internal features plus a construction margin.
        # This margin belongs to the protective tool, never to the connection.
        protective_radius = perimeter+.25
        q=mesh.vertices-base; radial=np.linalg.norm(q-np.outer(q@axis,axis),axis=1)
        local=q[radial<=protective_radius]@axis
        bottom=float(min(0,local.min())-.2)
        # Follow the measured internal wall above the basal perimeter instead
        # of protecting a full-width cylinder through the adjacent crown.
        # Dense first-hit rays cannot mistake an exterior undercut for the
        # connection wall behind it. Keep the basal circular features in full.
        dense_levels=np.linspace(.025,functional_top+.15,max(12,int(np.ceil((functional_top+.15)/.1))+1))
        dense_angles=np.linspace(0,2*np.pi,192,endpoint=False)
        dense_directions=np.cos(dense_angles)[:,None]*u+np.sin(dense_angles)[:,None]*v
        dense_origins=np.repeat(base+dense_levels[:,None]*axis,192,axis=0)
        dense_rays=np.tile(dense_directions,(len(dense_levels),1))
        local_coords=np.column_stack([q@u,q@v,q@axis])
        tri_coords=local_coords[mesh.faces]
        lower=np.array([-protective_radius-.2,-protective_radius-.2,-.25])
        upper=np.array([protective_radius+.2,protective_radius+.2,functional_top+.3])
        face_ids=np.flatnonzero(np.all(tri_coords.max(1)>=lower,axis=1)&np.all(tri_coords.min(1)<=upper,axis=1))
        local_mesh=trimesh.Trimesh(mesh.vertices,mesh.faces[face_ids],process=False)
        dense_xyz,dense_ids,dense_tri=local_mesh.ray.intersects_location(dense_origins,dense_rays,multiple_hits=False)
        dense_tri=face_ids[dense_tri]
        dense_dist=np.full(len(dense_origins),np.nan)
        wall_hit=np.einsum('ij,ij->i',mesh.face_normals[dense_tri],dense_rays[dense_ids])<-.2
        dense_dist[dense_ids[wall_hit]]=np.linalg.norm(dense_xyz[wall_hit]-dense_origins[dense_ids[wall_hit]],axis=1)
        dense_dist=dense_dist.reshape(-1,192)
        measured_envelope=[]
        if np.all(np.isfinite(dense_dist).mean(1)>.98):
            maxima=np.nanmax(dense_dist,axis=1)
            # Include neighboring slices, the full intersected wall triangles,
            # sharp basal rings and the 0.25 mm construction allowance.
            wall_vertices=mesh.vertices[np.unique(mesh.faces[np.unique(dense_tri[wall_hit])])]
            wall_q=wall_vertices-base;wall_h=wall_q@axis
            wall_r=np.linalg.norm(wall_q-np.outer(wall_h,axis),axis=1)
            for i,h in enumerate(dense_levels):
                nearby=abs(wall_h-h)<.16
                radius=max(maxima[max(0,i-1):min(len(maxima),i+2)])
                if nearby.any():radius=max(radius,float(wall_r[nearby].max()))
                for ring,rh in zip(group,heights):
                    if rh<.5 and h<=rh+.2:radius=max(radius,ring['radius'])
                    if abs(h-rh)<.16 and rh<=functional_top+.001:radius=max(radius,ring['radius'])
                measured_envelope.append({'height_mm':float(h),'radius_mm':float(min(protective_radius,radius+.25))})
            measured_envelope.insert(0,{'height_mm':bottom,'radius_mm':float(protective_radius)})
            # Connect every upper shoulder down to the basal support. Separate
            # shrinking/expanding slabs can preserve a rim as an isolated ring.
            # This conservative cone-like closure only adds protection; it
            # never removes measured functional surfaces or adds source metal.
            for i in range(len(measured_envelope)-2,-1,-1):
                measured_envelope[i]['radius_mm']=max(measured_envelope[i]['radius_mm'],measured_envelope[i+1]['radius_mm'])
        wall_vertex_ids=np.unique(mesh.faces[np.unique(dense_tri[wall_hit])])
        wall_vertex_ids=wall_vertex_ids[(projected[wall_vertex_ids]>=bottom)&(projected[wall_vertex_ids]<=functional_top+.15)]
        record=dict(group[0])
        record.update(center=base.tolist(),normal=axis.tolist(),
            detection='chimney_axis_and_circumferential_walls',
            connection_type='geometry_only_interface_or_direct',
            chimney_radius_mm=float(min(r['radius'] for r in group)),
            functional_perimeter_radius_mm=float(perimeter),
            protection_radius_mm=float(protective_radius),
            protection_bottom_mm=bottom,protection_top_mm=functional_top+.15,
            orientation_method='coherent_arch_crown_direction',
            measured_neck_mm=neck,measured_annular_shoulders_mm=sorted(set(shoulders)),
            protection_envelope_method='measured_walls_with_basal_support_closure',
            protection_envelope=measured_envelope,
            functional_wall_vertex_ids=wall_vertex_ids.tolist() if measured_envelope else [],
            chimney_axial_span_mm=span,wall_coverage=covered.tolist(),
            measured_features=[{'height_mm':float(h),'radius_mm':r['radius']} for r,h in zip(group,heights)])
        connections.append(record)
    if not connections:
        raise ValueError('No se ha localizado una chimenea abierta con paredes verificables. Diagnóstico geométrico conservado.')
    if len(connections)>16:
        raise ValueError('Detección ambigua: más de 16 ejes de chimenea. Requiere revisar el detector.')
    return connections, diagnostics


def orient_partial(mesh, connections):
    normals=np.asarray([c['normal'] for c in connections]);_,vectors=np.linalg.eigh(normals.T@normals)
    z=vectors[:,-1]
    if z@normals.mean(0)<0:z=-z
    centers=np.asarray([c['center'] for c in connections]);origin=centers.mean(0)
    points=centers-origin if len(connections)>1 else mesh.vertices-mesh.centroid
    points=points-np.outer(points@z,z);_,_,axes=np.linalg.svd(points,full_matrices=False)
    x=axes[0];y=np.cross(z,x);y/=np.linalg.norm(y);x=np.cross(y,z)
    rotation=np.asarray([x,y,z]);transform=np.eye(4)
    transform[:3,:3]=rotation;transform[:3,3]=-rotation@origin
    result=[]
    for item in connections:
        c=dict(item);c['center']=(rotation@item['center']+transform[:3,3]).tolist()
        c['normal']=(rotation@item['normal']).tolist();result.append(c)
    result.sort(key=lambda c:c['center'][0])
    return transform,result
