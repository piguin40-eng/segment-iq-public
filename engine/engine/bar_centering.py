"""Anchor the bar to measured connection axes; never translate an implant."""
import numpy as np
from bar_height import top_height


def axis_at_height(connection, height):
    base = np.asarray(connection['center'], dtype=float)
    axis = np.asarray(connection['normal'], dtype=float)
    if abs(axis[2]) < .5:
        raise ValueError('Eje demasiado inclinado para centrar el trazado con este método.')
    return base + axis * ((height - base[2]) / axis[2])


def axis_at_bar_top(connection, config):
    """Intersect the measured axis with the same height field used by TOP."""
    base=np.asarray(connection['center'],dtype=float)
    height=float(top_height(base[:2],config))
    for _ in range(40):
        point=axis_at_height(connection,height)
        target=float(top_height(point[:2],config))
        if abs(target-height)<1e-7:return point
        height=target
    raise ValueError('El eje de la conexión no converge sobre el plano de barra medido.')


def coordinates(xy, partial):
    return (xy[:, 0], xy[:, 1]) if partial else (np.arctan2(xy[:, 0], -xy[:, 1]), np.linalg.norm(xy, axis=1))


def project(t, r, partial):
    return np.column_stack([np.broadcast_to(t, np.shape(r)), r]) if partial else np.column_stack([r*np.sin(t), -r*np.cos(t)])


def trace_balance(config):
    trace = np.asarray(config['trace_xy']); n = len(trace)//2
    partial = config['trace_mode'] == 'linear_bridge'
    t, outer = coordinates(trace[:n], partial)
    _, inner = coordinates(trace[n:][::-1], partial)
    rows = []
    for i, c in enumerate(config['connections'], 1):
        q = axis_at_bar_top(c,config)
        at, ar = coordinates(q[None, :2], partial); at, ar = at[0], ar[0]
        left, right = np.interp(at,t,inner), np.interp(at,t,outer)
        rows.append({'connection':i, 'axis_xy':q[:2].tolist(), 'inner_space_mm':float(ar-left),
                     'outer_space_mm':float(right-ar), 'center_offset_mm':float(abs((left+right)/2-ar)),
                     'covered':bool(t[0]<=at<=t[-1] and left<ar<right)})
    return rows


def centered_trace(mesh, trace, connections, config, clearance):
    partial = config['trace_mode'] == 'linear_bridge'
    trace = np.asarray(trace); n = len(trace)//2
    t, outer = coordinates(trace[:n], partial)
    _, inner = coordinates(trace[n:][::-1], partial)
    natural = (outer+inner)/2
    anchors = np.array([axis_at_bar_top(c,config)[:2] for c in connections])
    at, ar = coordinates(anchors, partial)
    order = np.argsort(at); at,ar = at[order],ar[order]
    if at[0]<t[0] or at[-1]>t[-1]:
        raise ValueError('Una conexión queda fuera del corredor; no se entregará una barra sin cubrirla.')
    if len(at)>1 and np.any(np.diff(at)<1e-5):
        raise ValueError('Conexiones superpuestas en el trazado: requiere adaptar el marco del caso.')
    # Exact anchor samples avoid interpolation moving a connection off the midline.
    sample_t = np.unique(np.r_[t,at])
    shifts = ar-np.interp(at,t,natural)
    control_t = np.r_[t[0],at,t[-1]]
    control_shift = np.r_[0.,shifts,0.]
    centers = np.interp(sample_t,t,natural)+np.interp(sample_t,control_t,control_shift)
    if partial and len(at)>1:
        inside=(sample_t>=at[0])&(sample_t<=at[-1])
        centers[inside]=np.interp(sample_t[inside],at,ar)
    widths = np.interp(sample_t,t,(outer-inner)/2)
    left=[];right=[];omitted=[];anatomical_fallback=[]
    for s, center, width in zip(sample_t,centers,widths):
        # Search paired borders symmetrically. Do not independently shift one
        # unsupported side, which would recreate the original lateral bias.
        candidates=np.linspace(width,.45,100) if width>.45 else np.array([width])
        a=project(s,center-candidates,partial); b=project(s,center+candidates,partial)
        xy=np.vstack([a,b]); floor=mesh.bounds[0,2]-2
        points,ids,_=mesh.ray.intersects_location(np.column_stack([xy,np.full(len(xy),floor)]),np.tile([0,0,1],(len(xy),1)),multiple_hits=True)
        bottoms=np.full(len(xy),np.inf);tops=np.full(len(xy),-np.inf)
        np.minimum.at(bottoms,ids,points[:,2]);np.maximum.at(tops,ids,points[:,2])
        heights=top_height(xy,config)
        valid=(bottoms<heights-1.2)&(tops>heights+clearance)
        valid=valid[:len(a)]&valid[len(a):]
        matches=np.flatnonzero(valid)
        if not len(matches):
            if not partial and np.min(abs(at-s))>1e-6:
                # Between implant anchors the arch still follows its own
                # anatomy. Reuse this case's measured supported borders when
                # a symmetric offset would leave the crown; never move an axis.
                left.append(project(s,np.array([np.interp(s,t,inner)]),partial)[0])
                right.append(project(s,np.array([np.interp(s,t,outer)]),partial)[0])
                anatomical_fallback.append(float(s));continue
            if at[0] <= s <= at[-1]:
                raise ValueError('No hay espacio bilateral para centrar la barra y reservar supra; diagnóstico conservado sin desplazar las conexiones.')
            omitted.append(float(s));continue
        k=matches[0];left.append(a[k]);right.append(b[k])
    result=np.vstack([right,left[::-1]])
    checked=trace_balance(dict(config,trace_xy=result.tolist(),connections=connections))
    if not all(r['covered'] and r['center_offset_mm']<.05 for r in checked):
        raise ValueError('El trazado no ha quedado centrado sobre todas las conexiones.')
    return result, {'connections':checked,'distal_samples_omitted':omitted,'anatomical_samples_between_anchors':anatomical_fallback,
                    'method':'Bordes simétricos alrededor del eje medido; ajustados al soporte y reserva oclusal del STL.'}


def primary_balance(primary, config):
    """Measure outer metal borders in horizontal sections below the bar top.

    This is a design centering measurement, not a strength or fit certificate.
    """
    import trimesh
    from connection_protection import protection
    partial=config.get('trace_mode')=='linear_bridge'; rows=[]
    for i,c in enumerate(config.get('connections',[]),1):
        top=float(axis_at_bar_top(c,config)[2])
        protected_mesh=None
        if c.get('protection_envelope'):
            solid=protection(c)
            if solid is not None:
                raw=solid.to_mesh64()
                protected_mesh=trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False)
        def shoulder_limits(z):
            if protected_mesh is None:
                minimum=c.get('functional_perimeter_radius_mm',0)+.05
                return minimum,minimum
            q=axis_at_height(c,z)
            direction=np.array([0.,1.,0.]) if partial else np.r_[q[:2]/np.linalg.norm(q[:2]),0.]
            hits=protected_mesh.ray.intersects_location([q-direction*100],[direction],multiple_hits=True)[0]
            if not len(hits):return None
            signed=np.sort((hits-q)@direction)
            signed=signed[np.r_[True,np.diff(signed)>1e-7]]
            if len(signed)%2:return None
            intervals=signed.reshape(-1,2)
            around=intervals[(intervals[:,0]<0)&(intervals[:,1]>0)]
            if not len(around):return None
            return float(-around[0,0]+.05),float(around[0,1]+.05)
        def section(z):
            q=axis_at_height(c,z)
            direction=np.array([0.,1.,0.]) if partial else np.r_[q[:2]/np.linalg.norm(q[:2]),0.]
            hits=primary.ray.intersects_location([q-direction*100],[direction],multiple_hits=True)[0]
            if not len(hits):return None
            signed=np.sort((hits-q)@direction)
            # Pair the material intervals along this closed mesh. The farthest
            # intersections can belong to the OTHER arm of a full arch.
            signed=signed[np.r_[True,np.diff(signed)>1e-7]]
            if len(signed)%2:return None
            intervals=signed.reshape(-1,2)
            through=intervals[(intervals[:,0]<=0)&(intervals[:,1]>=0)]
            if len(through):return -through[0,0],through[0,1]
            negative=intervals[intervals[:,1]<0];positive=intervals[intervals[:,0]>0]
            if not len(negative) or not len(positive):return None
            a,b=negative[-1],positive[0]
            gap=max(c.get('functional_perimeter_radius_mm',0),c.get('protection_radius_mm',0),c.get('radius',0))+.1
            if -a[1]>gap or b[0]>gap:return None
            return -a[0],b[1]
        # Find actual bar shoulders after local safety relief, not just the
        # narrower circular neck left above them. With a measured taper, compare
        # against the actual protected envelope in THIS horizontal section,
        # not the wider basal diameter projected up the whole neck. Protection
        # volume itself is unchanged and independently checked after export.
        def has_shoulders(z):
            pair=section(z);limits=shoulder_limits(z)
            return pair is not None and limits is not None and all(a>b for a,b in zip(pair,limits))
        levels=np.arange(top-.4,c['center'][2]+.8,-.2)
        z=next((float(z) for z in levels if has_shoulders(z)),None)
        if z is None:
            rows.append({'connection':i,'bilateral':False,'reason':'Sin hombros de barra a ambos lados más allá del perímetro funcional.'});continue
        for level in (z,z-.4):
            pair=section(level);limits=shoulder_limits(level)
            if not has_shoulders(level):
                rows.append({'connection':i,'section_z':level,'bilateral':False});continue
            left,right=pair
            rows.append({'connection':i,'depth_below_top_mm':top-level,'section_z':level,'bilateral':True,
                         'inner_space_mm':float(left),'outer_space_mm':float(right),
                         'required_inner_space_mm':float(limits[0]),'required_outer_space_mm':float(limits[1]),
                         'support_reference':'local_protected_envelope' if protected_mesh is not None else 'legacy_basal_perimeter',
                         'center_offset_mm':float(abs(left-right)/2)})
    return {'scope':'Dos secciones por conexión sobre los hombros reales de barra, tras la seguridad local y más allá del perímetro funcional; no acredita resistencia.',
            'samples':rows,'max_center_offset_mm':max((r['center_offset_mm'] for r in rows),default=None) if all(r['bilateral'] for r in rows) else None,
            'all_bilateral':bool(rows) and all(r['bilateral'] for r in rows)}
