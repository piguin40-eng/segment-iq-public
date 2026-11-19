"""Exact protection solids; no imported implant or interface geometry."""
import numpy as np
import manifold3d as mf


def protection(connection, extra=0.):
    if 'protection_radius_mm' not in connection:
        return None
    axis=np.asarray(connection['normal'],dtype=float);axis/=np.linalg.norm(axis)
    ref=np.eye(3)[np.argmin(abs(axis))]
    u=np.cross(axis,ref);u/=np.linalg.norm(u);v=np.cross(axis,u)
    bottom=connection['protection_bottom_mm']-extra
    top=connection['protection_top_mm']+extra
    center=np.asarray(connection['center'])+axis*(top+bottom)/2
    envelope=connection.get('protection_envelope')
    if envelope:
        # Stepwise conservative envelope: every slab uses the larger adjacent
        # measured radius, rather than tapering through a sharp shoulder.
        heights=[r['height_mm'] for r in envelope]
        radii=[r['radius_mm'] for r in envelope]
        contours=[]
        for i in range(len(heights)-1):
            lo=heights[i]-extra;hi=heights[i+1]+extra
            radius=(max(radii[i:i+2])+extra)/np.cos(np.pi/192)
            contours.append(np.array([[0.,lo],[radius,lo],[radius,hi],[0.,hi]]))
        # Union the section in 2D before revolving it. Stacking independently
        # transformed cylinders creates coincident internal faces and zero-
        # volume sheets at the joins of slightly inclined axes.
        section=mf.CrossSection(contours)
        return mf.Manifold.revolve(section,192).transform(np.column_stack([u,v,axis,np.asarray(connection['center'])]))
    # Circumscribe the requested radius: polygon chords cannot clip a perimeter.
    radius=(connection['protection_radius_mm']+extra)/np.cos(np.pi/192)
    return mf.Manifold.cylinder(top-bottom,radius,radius,192,True).transform(np.column_stack([u,v,axis,center]))


def combined(connections, extra=0.):
    result=None
    for c in connections:
        piece=protection(c,extra)
        if piece is not None:result=piece if result is None else result+piece
    return result


def chimney_axis_check(source,parts,connection):
    """Keep local and newly created obstructions; identify unchanged remote anatomy."""
    base=np.asarray(connection['center']);axis=np.asarray(connection['normal'],dtype=float)
    axis=axis/np.linalg.norm(axis)
    low=min(float(np.min((m.vertices-base)@axis)) for m in (source,*parts))-1
    start=base+axis*low
    def crossings(mesh):
        points,_,faces=mesh.ray.intersects_location([start],[axis],multiple_hits=True)
        heights=(np.asarray(points).reshape(-1,3)-base)@axis
        order=np.argsort(heights)
        return heights[order],(mesh.face_normals[np.asarray(faces,dtype=int)]@axis)[order]
    original,dots=crossings(source)
    span=connection.get('chimney_axial_span_mm')
    if span is None:
        hits=sum(len(crossings(m)[0]) for m in parts)
        return {'chimney_axis_material_hits':hits,'axis_check_method':'legacy_entire_axis'}
    # Source intersections occur beyond the opening for some angled channels.
    # Record those intervals, while rejecting new material even outside the
    # measured channel. A remote roof is not permission to cap the opening.
    intervals=[];level=0;begin=None;ambiguous=False
    for h,dot in zip(original,dots):
        if abs(dot)<1e-8:
            ambiguous=True;continue
        before=level;level-=int(np.sign(dot))
        if before<=0 and level>0:begin=h
        if before>0 and level==0 and begin is not None:intervals.append((begin,h))
        if level<0:ambiguous=True
    if level!=0:ambiguous=True
    local=[];added=[];remote=[]
    for mesh in parts:
        heights,_=crossings(mesh)
        for h in heights:
            if -.05<=h<=float(span)+.05:local.append(float(h))
            elif not ambiguous and any(a-1e-5<=h<=b+1e-5 for a,b in intervals):remote.append(float(h))
            else:added.append(float(h))
    return {'chimney_axis_material_hits':len(local)+len(added),
            'axis_check_method':'measured_channel_and_new_material_against_source',
            'measured_channel_axial_range_mm':[-.05,float(span)+.05],
            'local_axis_material_hits_mm':local,'new_remote_axis_hits_mm':added,
            'unchanged_remote_anatomy_hits_mm':remote,
            'source_axis_intervals_mm':[[float(a),float(b)] for a,b in intervals],
            'source_axis_interpretation_ambiguous':ambiguous,
            'axis_scope':'Canal medido y material nuevo frente al original; no certifica acceso instrumental ni trayectoria clínica.'}


def connection_checks(source,primary,supra,connections):
    import trimesh
    def man(m):return mf.Manifold(mf.Mesh64(np.array(m.vertices,dtype=np.float64,order='C',copy=True),np.array(m.faces,dtype=np.uint64,order='C',copy=True)))
    source_solid,primary_solid=man(source),man(primary)
    checks=[]
    for i,c in enumerate(connections):
        mask=protection(c)
        if mask is None:continue
        original=source_solid^mask
        missing=(original-primary_solid).volume()
        base=np.asarray(c['center']);axis=np.asarray(c['normal']);q=source.vertices-base
        axial=q@axis;radial=np.linalg.norm(q-np.outer(axial,axis),axis=1)
        envelope=c.get('protection_envelope')
        limit=np.full(len(axial),c['protection_radius_mm'])
        if envelope:
            h=np.array([r['height_mm'] for r in envelope]);r=np.array([r['radius_mm'] for r in envelope])
            intervals=np.clip(np.searchsorted(h,axial,side='right')-1,0,len(h)-2)
            limit=np.maximum(r[intervals],r[intervals+1])
        selected=(radial<limit-.001)&(axial>c['protection_bottom_mm'])&(axial<c['protection_top_mm'])
        wall_ids=c.get('functional_wall_vertex_ids',[])
        if wall_ids:
            selected[np.asarray(wall_ids,dtype=int)]=True
        points=source.vertices[selected]
        distances=trimesh.proximity.closest_point(primary,points)[1] if len(points) else np.array([np.inf])
        axis_report=chimney_axis_check(source,(primary,supra),c)
        checks.append({'connection':i+1,'protected_source_volume_mm3':original.volume(),
            'missing_volume_mm3':float(max(0,missing)),'source_vertices_checked':int(len(points)),
            'max_surface_distance_mm':float(distances.max()),**axis_report,
            'protected_radius_mm':c['protection_radius_mm'],
            'protected_axial_range_mm':[c['protection_bottom_mm'],c['protection_top_mm']]})
    return checks
