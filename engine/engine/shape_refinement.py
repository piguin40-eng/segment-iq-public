"""Measured contour, cervical bevel and roof refinements for the current STL."""
import numpy as np
from bar_centering import coordinates,project,axis_at_bar_top


def refine_trace(trace,connections,config):
    from scipy.ndimage import gaussian_filter1d
    shape=config.get('shape_refinement',{})
    if not (shape.get('smooth_margin') or shape.get('bar_narrowing_per_side_mm')):
        return np.asarray(trace),{}
    partial=config['trace_mode']=='linear_bridge'
    xy=np.asarray(trace);n=len(xy)//2
    t,outer=coordinates(xy[:n],partial);_,inner=coordinates(xy[n:][::-1],partial)
    anchors=np.array([axis_at_bar_top(c,config)[:2] for c in connections])
    at,ar=coordinates(anchors,partial)
    tt=np.unique(np.r_[np.linspace(t[0],t[-1],max(n,100)),at])
    center=np.interp(tt,t,(outer+inner)/2);before=np.interp(tt,t,(outer-inner)/2)
    if partial and len(at)>1:
        order=np.argsort(at);inside=(tt>=at.min())&(tt<=at.max())
        center[inside]=np.interp(tt[inside],at[order],ar[order])
    width=before.copy();reduction=shape.get('bar_narrowing_per_side_mm',0.)
    if shape.get('smooth_margin'):width=np.minimum(width,gaussian_filter1d(width,2,mode='nearest'))
    width=np.maximum(.5,width-reduction)
    # Retain shoulders outside each measured functional perimeter. A request
    # to slim the body must not consume the implant support or move its axis.
    floor=np.zeros(len(tt))
    for connection,a in zip(connections,at):
        radius=connection.get('functional_perimeter_radius_mm',connection['radius'])+.3+shape.get('cervical_bevel_mm',0.)
        distance=abs(tt-a) if partial else abs(tt-a)*np.linalg.norm(connection['center'][:2])
        floor=np.maximum(floor,np.sqrt(np.maximum(0,radius*radius-distance*distance)))
    width=np.minimum(before,np.maximum(width,floor))
    result=np.vstack([project(tt,center+width,partial),project(tt,center-width,partial)[::-1]])
    return result,{'proposed_reduction_per_side_mm':reduction,
        'median_total_width_reduction_mm':float(np.median(2*(before-width))),
        'maximum_total_width_reduction_mm':float(np.max(2*(before-width))),
        'connection_support_limited_samples':int(np.sum(floor>before-reduction)),
        'contour_samples_per_side':len(tt),'smooth_margin_requested':bool(shape.get('smooth_margin'))}


def inset_contour(xy,config,distance):
    """Offset toward the locally paired midline, preserving measured axes."""
    partial=config['trace_mode']=='linear_bridge';trace=np.asarray(config['trace_xy']);n=len(trace)//2
    t,outer=coordinates(trace[:n],partial);_,inner=coordinates(trace[n:][::-1],partial)
    tt,r=coordinates(np.asarray(xy),partial);center=np.interp(tt,t,(outer+inner)/2)
    return project(tt,r-np.sign(r-center)*np.minimum(distance,abs(r-center)*.2),partial)


def smooth_lower_height(height,spacing,radius=.6):
    """Smooth only by lowering; never consume a previously reserved supra wall."""
    from scipy.ndimage import gaussian_filter,minimum_filter
    cells=max(1,int(np.ceil(radius/spacing)))
    lowered=minimum_filter(height,size=2*cells+1,mode='nearest')
    smooth=gaussian_filter(lowered,sigma=max(.5,cells/3),radius=cells,mode='nearest')
    # Every point in a smoothing window has seen this point in its minimum
    # window, so its weighted average cannot exceed the original height.
    return np.minimum(height,smooth)


def lower_convex_profile(t,z):
    """Bridge local peaks between neighbouring valleys without raising them."""
    hull=[]
    for i in range(len(t)):
        while len(hull)>1:
            a,b=hull[-2:]
            if (t[b]-t[a])*(z[i]-z[b])-(z[b]-z[a])*(t[i]-t[b])>0:break
            hull.pop()
        hull.append(i)
    return np.minimum(z,np.interp(t,np.asarray(t)[hull],np.asarray(z)[hull]))


def rounded_roof(primary,config,spacing=.35,radius=1.25):
    """Lower peaks on the actual generated roof, without raising valleys."""
    from scipy.ndimage import distance_transform_edt,gaussian_filter
    from bar_height import top_height
    low,high=primary.bounds
    x=np.linspace(low[0]-1,high[0]+1,int(np.ceil((high[0]-low[0]+2)/spacing))+1)
    y=np.linspace(low[1]-1,high[1]+1,int(np.ceil((high[1]-low[1]+2)/spacing))+1)
    xx,yy=np.meshgrid(x,y);xy=np.column_stack([xx.ravel(),yy.ravel()])
    points,ids,faces=primary.ray.intersects_location(np.column_stack([xy,np.full(len(xy),high[2]+2)]),np.tile([0,0,-1],(len(xy),1)),multiple_hits=False)
    partial=config['trace_mode']=='linear_bridge';trace=np.asarray(config['trace_xy']);n=len(trace)//2
    t,outer=coordinates(trace[:n],partial);_,inner=coordinates(trace[n:][::-1],partial)
    tt,rr=coordinates(points[:,:2],partial);middle=np.interp(tt,t,(outer+inner)/2);width=np.interp(tt,t,(outer-inner)/2)
    nominal=top_height(points[:,:2],config)
    valid=(primary.face_normals[faces,2]>.35)&(tt>=t[0])&(tt<=t[-1])&(abs(rr-middle)<width*.70)
    # Only the upper construction layer defines roof finishing. Low original
    # cervical faces and previous safety cuts must not seed a global valley.
    valid &= abs(points[:,2]-nominal)<.6
    valid &= points[:,2]>min(c['center'][2] for c in config['connections'])+.8
    points,ids=points[valid],ids[valid]
    heights=np.full(len(xy),np.nan);heights[ids]=points[:,2];heights=heights.reshape(xx.shape)
    missing=~np.isfinite(heights)
    if missing.all():raise RuntimeError('No se puede medir la superficie superior para suavizar sus crestas.')
    nearest=distance_transform_edt(missing,return_distances=False,return_indices=True)
    field=top_height(xy,config).reshape(xx.shape)
    residual=heights-field
    filled_residual=residual[tuple(nearest)]
    smooth=gaussian_filter(filled_residual,sigma=max(.5,radius/spacing),mode='nearest')
    # Smooth deviations from the tilted field, not the tilt itself. The cap
    # finishes remesh crests with a bounded allowance; it cannot raise metal
    # because the caller intersects it with the existing, safety-cut tool.
    allowance=float(config.get('shape_refinement',{}).get('roof_finish_allowance_mm',.20))
    finish=np.clip(smooth-allowance,-.45,-.10)
    smoothed=field+finish
    filled=heights[tuple(nearest)]
    reduction=filled-smoothed
    return x,y,smoothed,{'method':'Acabado del residuo respecto al campo inclinado; interseccion conserva recortes previos y protecciones.',
        'radius_mm':radius,'sample_count':len(ids),'maximum_roof_reduction_mm':float(reduction[~missing].max()),
        'median_roof_reduction_mm':float(np.median(reduction[~missing])),
        'nominal_finish_offset_range_mm':[float(finish.min()),float(finish.max())],
        'scope':'Propuesta de acabado; no acredita rectitud, soporte ni paredes del resultado.'}
