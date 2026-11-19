"""Measure a raw arch and propose a reproducible first design; no reference geometry input."""
import argparse, hashlib, json, re, sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.ndimage import gaussian_filter1d
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
sys.path.insert(0,str(Path(__file__).resolve().parent))
from connections import group_chimneys, orient_partial
from lab_rules import requested_rules,regional_and_thickness,observation_intents,effective_feedback,shape_rules
sys.path.insert(0,str(Path(__file__).resolve().parent/'engine'))
from bar_height import regional_weight,top_height
from bar_centering import centered_trace, trace_balance, axis_at_bar_top,coordinates,project
from shape_refinement import refine_trace
from trace_support import TraceSupportError,fit_trace_plane


def circular_edges(mesh):
    vertices = mesh.vertices
    candidates = []
    for threshold in (.15, .25, .4, .6, .9, 1.2, 1.45):
        edges = mesh.face_adjacency_edges[mesh.face_adjacency_angles > threshold]
        if not len(edges):
            continue
        ids = np.unique(edges)
        lookup = np.full(len(vertices), -1)
        lookup[ids] = np.arange(len(ids))
        ee = lookup[edges]
        count, labels = connected_components(coo_matrix((np.ones(len(ee)), (ee[:, 0], ee[:, 1])), shape=(len(ids), len(ids))), directed=False)
        for label in range(count):
            points = vertices[ids[labels == label]]
            if not 6 <= len(points) <= 10000:
                continue
            center = points.mean(0)
            _, _, axes = np.linalg.svd(points-center, full_matrices=False)
            local = (points-center) @ axes.T
            plane = float(local[:, 2].std())
            if plane > .002:
                continue
            matrix = np.column_stack((2*local[:, 0], 2*local[:, 1], np.ones(len(local))))
            fit = np.linalg.lstsq(matrix, (local[:, :2]**2).sum(1), rcond=None)[0]
            radius = float(np.sqrt(max(0, fit[2]+(fit[:2]**2).sum())))
            residual = float(np.linalg.norm(local[:, :2]-fit[:2], axis=1).std())
            center = center + axes[:2].T @ fit[:2]
            if not .5 < radius < 4.5 or residual > .002:
                continue
            if any(np.linalg.norm(center-np.array(c['center'])) < .03 and abs(radius-c['radius']) < .01 for c in candidates):
                continue
            candidates.append(dict(center=center.tolist(), normal=axes[2].tolist(), radius=radius,
                                   radial_std=residual, planar_std=plane, vertices=len(points)))
    return candidates


def orientation(mesh, seats):
    points = np.array([c['center'] for c in seats])
    normals = np.array([c['normal'] for c in seats])
    _, axes = np.linalg.eigh(normals.T @ normals)
    z = axes[:, -1]
    # Polarity is already measured together with each basal seat and its
    # axial protection. A second centroid heuristic can reverse only the
    # direction while leaving those measured features on the wrong side.
    if np.dot(z, normals.mean(0)) < 0:
        z = -z
    reference = np.eye(3)[np.argmin(abs(z))]
    x = np.cross(reference, z); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    q = points @ np.array([x, y, z]).T
    matrix = np.column_stack((2*q[:, 0], 2*q[:, 1], np.ones(len(q))))
    fit = np.linalg.lstsq(matrix, (q[:, :2]**2).sum(1), rcond=None)[0]
    angles = np.sort(np.arctan2(q[:, 1]-fit[1], q[:, 0]-fit[0]))
    gaps = np.diff(np.r_[angles, angles[0]+2*np.pi])
    i = np.argmax(gaps)
    opening = angles[i]+gaps[i]/2
    y = np.cos(opening)*x + np.sin(opening)*y
    x = np.cross(y, z)
    rotation = np.array([x, y, z])
    # Recover the fitted circle centre before rotating the opening towards +Y.
    base_x = np.cross(reference, z); base_x /= np.linalg.norm(base_x)
    base_y = np.cross(z, base_x)
    origin = fit[0]*base_x+fit[1]*base_y+np.median(q[:, 2])*z
    transform = np.eye(4); transform[:3, :3] = rotation; transform[:3, 3] = -rotation@origin
    transformed = []
    for seat in seats:
        c = dict(seat)
        c['center'] = (rotation@np.array(c['center'])+transform[:3, 3]).tolist()
        n = rotation@np.array(c['normal'])
        if n[2] <= 0:
            raise ValueError('Los ejes medidos no comparten una orientación de corona coherente; revisar la detección sin invertir las protecciones.')
        c['normal'] = n.tolist()
        transformed.append(c)
    transformed.sort(key=lambda c: np.arctan2(c['center'][0], -c['center'][1]))
    return transform, transformed


def corrections(history):
    height, widening = 0., 0.
    applied, pending = [], []
    for row in effective_feedback(history):
        if row.get('status') not in {'correction', 'rejected'}: continue
        intents, unresolved = observation_intents(row['text'])
        changed = []
        if intents.get('protect_connections'):
            changed.append('Detectar chimeneas y proteger el perímetro funcional medido desde el STL; comprobar conservación después de exportar.')
        if intents.get('center_connections'):
            changed.append('Centrar el trazado de la barra sobre los ejes medidos de las conexiones, con espacio equilibrado a ambos lados; no mover los implantes.')
        for key,message in {
            'smooth_margin':'Proponer un contorno de terminación continuo y suavizado sobre el STL; comparar con las marcas de referencia.',
            'smooth_roof':'Reducir y redondear las crestas superiores del separador conservando la reserva de supra y las conexiones.',
            'cervical_bevel':'Construir un bisel cervical de apoyo propuesto de 0.20 mm, excluyendo las regiones funcionales protegidas.',
            'slimmer_bar':'Afinar el cuerpo de barra hasta 0.20 mm por lado, limitado por el soporte medido de las conexiones.'}.items():
            if intents.get(key):changed.append(message)
        if 'height' in intents:
            effective = float(np.clip(height + intents['height'], -2, 2)) - height
            height += effective
            if abs(effective) > 1e-8:
                changed.append(f'Altura de barra {effective:+.2f} mm respecto al diseño medido; sin recortar las regiones funcionales protegidas.')
            else:
                unresolved.append('La altura solicitada alcanza el límite acumulado de adaptación de ±2 mm; no se ha aplicado otra reducción/aumento.')
        if 'width' in intents:
            effective = float(np.clip(widening + intents['width'], -10, 10)) - widening
            widening += effective
            if abs(effective) > 1e-8: changed.append(f'Anchura del trazado {effective:+g} puntos percentiles por borde.')
            else: unresolved.append('La anchura solicitada alcanza el límite de adaptación; no se ha aplicado otra variación.')
        if changed: applied.append({'id':row['id'], 'changes':changed})
        for text in unresolved:
            pending.append({'id':row['id'], 'text':text, 'reason':'Indicación conservada para revisión: esta parte no se da por aplicada automáticamente.'})
    return height, widening, applied, pending


def propose_bar_height(xy, bottoms, tops, connections, rules, height_delta, partial):
    """Separate an inclined cervical reference from an added regional height.

    Recover an otherwise infeasible horizontal proposal from this STL's measured
    cervical samples. Never cap an excessive correction or move implant axes.
    The corridor and final geometry still have to pass the same checks.
    """
    xy=np.asarray(xy,dtype=float);bottoms=np.asarray(bottoms);tops=np.asarray(tops)
    bounds=np.percentile(xy[:,1],[10,90]).tolist()
    weights=regional_weight(xy[:,1],bounds)
    clearance=max(1.5,(rules['minimum_supra_mm'] or 0)+.3)
    regional=bool(rules['anterior_feedback_ids']) and not partial
    centers=np.asarray([c['center'] for c in connections])
    def proposal(slope):
        offset=xy@slope
        cervical=bottoms-offset;occlusal=tops-offset
        difference=float(np.median(cervical[weights>.8])-np.median(cervical[weights<.2])) if regional else 0.
        increase=max(rules['anterior_delta_mm'],rules['anterior_delta_mm']+difference) if regional else 0.
        top=float(min(np.median(cervical+.60*(tops-bottoms)),np.percentile(occlusal,10)-1.5)+height_delta)
        if regional:top=min(top,float(np.percentile(occlusal-increase*weights,10)-clearance))
        local=centers[:,:2]@slope+top+increase*regional_weight(centers[:,1],bounds)
        return top,increase,difference,float(np.min(local-centers[:,2]))
    slope=np.zeros(2);top,increase,difference,seat_clearance=proposal(slope)
    diagnostic={'method':'horizontal','horizontal_anterior_raise_mm':increase,
                'horizontal_cervical_difference_mm':difference,'reference_only':True}
    if not partial and (increase>3 or seat_clearance<1):
        # Robust linear fit prevents a few cusp-side trace tips from defining
        # the reference plane. Rank-deficient/invalid measurements stay errors.
        matrix=np.column_stack([xy,np.ones(len(xy))])
        if len(xy)<12 or not np.isfinite(np.r_[xy.ravel(),bottoms,tops]).all() or np.linalg.matrix_rank(matrix)<3:
            raise ValueError('No se puede medir un plano cervical fiable para adaptar la barra.')
        fit=np.linalg.lstsq(matrix,bottoms,rcond=None)[0]
        for _ in range(5):
            residual=bottoms-matrix@fit
            centered=residual-np.median(residual)
            selected=abs(centered)<=max(1.,2.5*np.median(abs(centered)))
            if selected.sum()<12 or np.linalg.matrix_rank(matrix[selected])<3:
                raise ValueError('Muestras cervicales insuficientes para adaptar el plano de la barra.')
            fit=np.linalg.lstsq(matrix[selected],bottoms[selected],rcond=None)[0]
        slope=fit[:2];top,increase,difference,seat_clearance=proposal(slope)
        diagnostic.update(method='measured_cervical_plane',cervical_fit=fit.tolist(),
                          samples_used=int(selected.sum()),total_samples=len(xy),
                          median_absolute_fit_error_mm=float(np.median(abs(bottoms-matrix@fit))),
                          residual_cervical_difference_mm=difference,
                          note='La inclinación del caso define el plano; no se suma como metal anterior. Conexiones y transformación originales conservadas.')
    if increase>3:
        raise ValueError(f'Incluso adaptando el plano cervical, el incremento anterior calculado es {increase:.2f} mm y supera 3 mm; revisar las secciones del caso.')
    if seat_clearance<1:
        raise ValueError('El espacio entre asientos y anatomía oclusal no permite proponer la barra con este detector. Diagnóstico conservado.')
    diagnostic.update(bar_plane=[*slope.tolist(),top],anterior_raise_mm=increase,
                      minimum_sampled_seat_clearance_mm=seat_clearance)
    return top,increase,bounds,[*slope.tolist(),top],diagnostic


def supported_trace(mesh,trace,config,clearance,samples_at):
    """Recheck refined borders; interpolation must not enter a chimney or void."""
    trace=np.array(trace,dtype=float,copy=True);partial=config['trace_mode']=='linear_bridge'
    def support(xy):
        heights=top_height(xy,config)
        points,ids,_=mesh.ray.intersects_location(np.column_stack([xy,np.full(len(xy),mesh.bounds[0,2]-2)]),
                    np.tile([0,0,1],(len(xy),1)),multiple_hits=True)
        valid=np.zeros(len(xy),dtype=bool);bottom=np.full(len(xy),np.inf);top=np.full(len(xy),-np.inf)
        if not len(points):return valid,bottom,top
        for i in range(len(xy)):
            z=np.unique(np.round(points[ids==i,2],8))
            if len(z):bottom[i]=z[0];top[i]=z[-1]
            if len(z)%2:continue
            valid[i]=any(lo<heights[i]-1.2 and hi>heights[i]+clearance for lo,hi in z.reshape(-1,2))
        return valid,bottom,top
    valid,_,_=support(trace);changes=[]
    for i in np.flatnonzero(~valid):
        t,r=coordinates(trace[i:i+1],partial);t=float(t[0])
        measured=samples_at(t)
        candidates=project(t,np.linspace(measured.min(),measured.max(),200),partial)
        supported,_,_=support(candidates)
        candidates=candidates[supported]
        if not len(candidates):raise TraceSupportError(f'No hay material continuo para apoyar el trazado refinado en la sección {t:.4f}.')
        target=candidates[np.argmin(np.linalg.norm(candidates-trace[i],axis=1))]
        changes.append({'point':int(i),'before_xy':trace[i].tolist(),'after_xy':target.tolist(),
                        'distance_mm':float(np.linalg.norm(target-trace[i]))})
        trace[i]=target
    n=len(trace)//2;_,outer=coordinates(trace[:n],partial);_,inner=coordinates(trace[n:][::-1],partial)
    if np.any(outer-inner<=.05):raise TraceSupportError('El trazado refinado se cruza al buscar material continuo; revisar su anchura.')
    valid,bottom,top=support(trace)
    if not valid.all():raise ValueError('Un borde refinado sigue sin reserva cervical u oclusal.')
    return trace,bottom,top,{'method':'Proyección radial tras el afinado, sobre un intervalo continuo del STL; no se omiten secciones.',
                           'adjustments':changes,'all_supported':True,'cervical_clearance_mm':1.2,'occlusal_clearance_mm':clearance}


def initial_centering(mesh, xy, connections, config, clearance):
    """Return a supported seed for planning when the nominal field cannot center.

    This never clears center_connections: the final mesh still must satisfy the
    executor's bilateral shoulder check. A planning estimate is not a result.
    """
    before=trace_balance(dict(config,trace_xy=np.asarray(xy).tolist(),connections=connections))
    try:
        result,report=centered_trace(mesh,xy,connections,config,clearance)
    except ValueError as error:
        if 'No hay espacio bilateral' not in str(error):
            raise
        return np.asarray(xy).copy(),{'status':'pending_agent_redesign',
            'reason':str(error),'before':before,
            'scope':'Semilla medida sin centrado resuelto; el agente debe replantear el campo y el cuerpo. El control final bilateral permanece obligatorio.'}
    return result,dict(report,before=before,status='proposed_trace_only')


def prepare(source, name, history):
    mesh = trimesh.load(source, force='mesh')
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError('El STL de entrada necesita reparación de malla; no se generará una falsa segmentación.')
    if not 3 < max(mesh.extents) < 160:
        raise ValueError('Las dimensiones no corresponden al intervalo de una arcada en milímetros; se conserva la entrada sin escalar.')
    candidates = circular_edges(mesh)
    detected, detection_notes = group_chimneys(mesh, candidates)
    partial_transform, partial_connections = orient_partial(mesh,detected)
    centers=np.asarray([c['center'] for c in partial_connections])
    spread=np.linalg.svd(centers[:,:2]-centers[:,:2].mean(0),compute_uv=False)
    # NumPy comparisons produce np.bool_, which json cannot serialize. Three
    # aligned implants take this branch; two implants short-circuit to bool.
    partial=bool(len(detected)<=2 or spread[1]<.1*spread[0])
    transform,connections=(partial_transform,partial_connections) if partial else orientation(mesh,detected)
    mesh.apply_transform(transform)
    height_delta, widening, applied, pending = corrections(history)
    rules=requested_rules(history)
    shape=shape_rules(history)
    center_connections=partial or any(observation_intents(r['text'])[0].get('center_connections') for r in history.get('feedback',[]) if r.get('status') in {'correction','rejected'})
    v = mesh.vertices
    angle = v[:,0] if partial else np.arctan2(v[:, 0], -v[:, 1])
    radius = v[:,1] if partial else np.linalg.norm(v[:, :2], axis=1)
    band=max(float(np.ptp(angle))/100,.1) if partial else .06
    def xy_at(t,r):
        return np.column_stack((np.full_like(r,t),r)) if partial else np.column_stack((r*np.sin(t),-r*np.cos(t)))
    sections={}
    def samples_at(t):
        if partial:
            if float(t) not in sections:
                lines=trimesh.intersections.mesh_plane(mesh,[1,0,0],[t,0,0])
                sections[float(t)]=lines.reshape(-1,3)[:,1]
            result=sections[float(t)]
        else:
            result=radius[abs(angle-t)<band]
            if len(result)<5:result=radius[abs(angle-t)<2*band]
        if not len(result):raise ValueError('Sección del trazado sin anatomía; diagnóstico conservado para revisar la geometría.')
        return result
    lo, hi = np.percentile(angle, [.15, 99.85])
    if not partial and (hi-lo > 5 or hi-lo < 1):
        raise ValueError('La abertura de la arcada no se ha identificado con confianza suficiente. Diagnóstico conservado para adaptar el trazado.')
    theta = np.linspace(lo+.004, hi-.004, 48)
    quantiles = [20-widening, 80+widening]
    rows = []
    for t in theta:
        selection = samples_at(t)
        rows.append(np.percentile(selection, quantiles))
    radii = gaussian_filter1d(np.array(rows), .8, axis=0)
    outer = np.column_stack((theta,radii[:,1])) if partial else np.column_stack((radii[:,1]*np.sin(theta),-radii[:,1]*np.cos(theta)))
    inner = np.column_stack((theta,radii[:,0])) if partial else np.column_stack((radii[:,0]*np.sin(theta),-radii[:,0]*np.cos(theta)))
    xy = np.concatenate((outer,inner[::-1]))
    # Smooth vertex percentiles can overshoot a narrow distal end. Move only
    # unsupported samples onto measured vertical intersections at the same angle.
    shifts = []
    for i in range(len(xy)):
        origin = np.r_[xy[i],mesh.bounds[0,2]-10]
        if mesh.ray.intersects_any([origin],[[0,0,1]])[0]: continue
        t = theta[i] if i<len(theta) else theta[2*len(theta)-1-i]
        rr = samples_at(t)
        sample_r = np.linspace(rr.min(),rr.max(),100)
        sample_xy = xy_at(t,sample_r)
        candidates_xyz = np.column_stack((sample_xy,np.full(len(sample_xy),mesh.bounds[0,2]-10)))
        supported = mesh.ray.intersects_any(candidates_xyz,np.tile([0,0,1],(len(sample_xy),1)))
        if not supported.any():
            raise ValueError('No se pudo apoyar el extremo del trazado sobre el STL. Se conserva el diagnóstico para mejorar el detector.')
        valid = sample_xy[supported]
        nearest = valid[np.argmin(np.linalg.norm(valid-xy[i],axis=1))]
        shifts.append({'point':i,'distance_mm':float(np.linalg.norm(nearest-xy[i]))})
        xy[i] = nearest
    origins = np.column_stack((xy,np.full(len(xy),mesh.bounds[0,2]-10)))
    points, ray_ids, _ = mesh.ray.intersects_location(origins,np.tile([0,0,1],(len(xy),1)),multiple_hits=True)
    bottoms, tops = [], []
    for i in range(len(xy)):
        zs=points[ray_ids==i,2]
        if not len(zs): raise ValueError('Un borde del trazado sale de la anatomía. Se requiere ajustar el trazado automático, sin pedir un perfil al usuario.')
        bottoms.append(zs.min());tops.append(zs.max())
    bottoms,tops=np.array(bottoms),np.array(tops)
    thickness=tops-bottoms
    top,anterior_raise,y_bounds,plane,height_reference=propose_bar_height(
        xy,bottoms,tops,connections,rules,height_delta,partial)
    trace_config={'trace_mode':'linear_bridge' if partial else 'radial_arch',
                  'bar_top_z':top,'bar_plane':plane,'anterior_raise_mm':anterior_raise,'bar_y_bounds':y_bounds,
                  'trace_quantiles':quantiles}
    # Measure a corridor with anatomy both below and above the proposed top.
    # This prevents an occlusal overhang from becoming a cervical trace and
    # cutting a crown off the supra at a narrow end.
    grid=[]
    for t in theta:
        rr=samples_at(t)
        grid.extend(xy_at(t,np.linspace(rr.min(),rr.max(),100)).tolist())
    grid=np.array(grid)
    pp,ii,_=mesh.ray.intersects_location(np.column_stack((grid,np.full(len(grid),mesh.bounds[0,2]-10))),np.tile([0,0,1],(len(grid),1)),multiple_hits=True)
    gb=np.full(len(grid),np.inf);gt=np.full(len(grid),-np.inf)
    np.minimum.at(gb,ii,pp[:,2]);np.maximum.at(gt,ii,pp[:,2])
    grid_top=top_height(grid,trace_config)
    occlusal_clearance=max(1.5,(rules['minimum_supra_mm'] or 0)+.3)
    valid=(gb<grid_top-1.2)&(gt>grid_top+occlusal_clearance)
    usable=valid.reshape(len(theta),100).any(1)
    indices=np.flatnonzero(usable)
    if len(indices)<30 or not usable[indices[0]:indices[-1]+1].all():
        raise ValueError('No se encuentra un corredor continuo para la barra con espesor de supra. Diagnóstico conservado.')
    outer=[];inner=[];bo=[];bi=[];to=[];ti=[]
    for i in indices:
        candidates=np.flatnonzero(valid[i*100:(i+1)*100])+i*100
        ri=grid[candidates,1] if partial else np.linalg.norm(grid[candidates],axis=1)
        values=np.percentile(ri,quantiles)
        a,b=[candidates[np.argmin(abs(ri-value))] for value in values]
        inner.append(grid[a]);outer.append(grid[b]);bi.append(gb[a]);bo.append(gb[b]);ti.append(gt[a]);to.append(gt[b])
    xy=np.concatenate((outer,inner[::-1]));bottoms=np.r_[bo,bi[::-1]];tops=np.r_[to,ti[::-1]];thickness=tops-bottoms
    centering=None
    if center_connections:
        xy,centering=initial_centering(mesh,xy,connections,trace_config,occlusal_clearance)
        xy,shape_trace=refine_trace(xy,connections,dict(trace_config,shape_refinement=shape))
        outer=xy[:len(xy)//2];inner=xy[len(xy)//2:][::-1]
        pp,ii,_=mesh.ray.intersects_location(np.column_stack([xy,np.full(len(xy),mesh.bounds[0,2]-2)]),np.tile([0,0,1],(len(xy),1)),multiple_hits=True)
        bottoms=np.full(len(xy),np.inf);tops=np.full(len(xy),-np.inf)
        np.minimum.at(bottoms,ii,pp[:,2]);np.maximum.at(tops,ii,pp[:,2]);thickness=tops-bottoms
    if not center_connections:
        xy,shape_trace=refine_trace(xy,connections,dict(trace_config,shape_refinement=shape))
        outer=xy[:len(xy)//2];inner=xy[len(xy)//2:][::-1]
    try:
        xy,bottoms,tops,refined_support=supported_trace(mesh,xy,trace_config,occlusal_clearance,samples_at)
    except TraceSupportError as initial_error:
        trace_config,xy,plane_fit=fit_trace_plane(mesh,xy,connections,trace_config,occlusal_clearance,samples_at)
        top=trace_config['bar_top_z'];plane=trace_config['bar_plane']
        xy,shape_trace=refine_trace(xy,connections,dict(trace_config,shape_refinement=shape))
        xy,bottoms,tops,refined_support=supported_trace(mesh,xy,trace_config,occlusal_clearance,samples_at)
        height_reference['corridor_plane_adjustment']=dict(plane_fit,initial_error=str(initial_error))
        height_reference['bar_plane']=plane
    thickness=tops-bottoms;outer=xy[:len(xy)//2];inner=xy[len(xy)//2:][::-1]
    if center_connections:
        checked=trace_balance(dict(trace_config,trace_xy=xy.tolist(),connections=connections))
        if not all(r['covered'] and r['center_offset_mm']<.05 for r in checked):
            centering.update(status='pending_agent_redesign',final_trace=checked,
                reason='El corredor medido no conserva el centrado de todas las conexiones; replantear trazado, campo y cuerpo antes de aceptar la barra.')
        if centering.get('status')=='pending_agent_redesign':
            pending.append({'id':'automatic_centering','text':'Conexiones por el medio de la barra con hombros bilaterales equilibrados.',
                'reason':centering['reason']+' El control final sigue obligatorio.'})
    arch_numbers=re.findall(r'(?<!\d)([1-4][1-8])(?!\d)',name)
    upper=sum(int(t)<30 for t in arch_numbers);lower=len(arch_numbers)-upper
    arch='SUP' if upper>lower else 'INF' if lower else 'AUTO'
    posterior_only=bool(arch_numbers) and all(int(n)%10>=4 for n in arch_numbers)
    regional_ids=set(rules['anterior_feedback_ids'])
    resolved_ids=regional_ids if not partial or posterior_only else set()
    pending=[row for row in pending if not (row['id'] in resolved_ids and 'anterior' in row['text'].lower() and not re.search(r'\b(pieza|distal|izquierda|derecha)\b',row['text'],re.I))]
    for id in resolved_ids:
        applied.append({'id':id,'changes':[
            f"Propuesta de altura anterior: incremento gradual de {anterior_raise:.2f} mm sobre el plano de referencia medido; objetivo de {rules['anterior_delta_mm']:.2f} mm de altura adicional de inserción, pendiente de comprobar tras separar." if not partial else
            'Criterio de altura anterior: no corresponde a este puente, cuyo nombre identifica solo piezas posteriores. Se mantiene la barra posterior medida.']})
    if rules['minimum_supra_mm'] is not None:
        minimum=rules['minimum_supra_mm']
        pending=[row for row in pending if regional_and_thickness(row['text'])[1] is None]
        applied.append({'id':rules['minimum_feedback_ids'][-1],'changes':[f'Reserva oclusal medida de {occlusal_clearance:.2f} mm para proteger la supra; se comprobará el objetivo de {minimum:.2f} mm después de separar.']})
        pending.append({'id':rules['minimum_feedback_ids'][-1],'text':f'Grosor mínimo de supra {minimum:.2f} mm en toda la superficie.',
                        'reason':'La reserva oclusal se aplica y se mide, pero no acredita por sí sola el mínimo en paredes laterales y márgenes. Ese control completo sigue pendiente.'})
    source_hash=hashlib.sha256(Path(source).read_bytes()).hexdigest()
    profile=dict(profile='measured-auto-v2-chimneys',source_sha256=source_hash,arch=arch,raw_to_work=transform.tolist(),
      trace_mode='linear_bridge' if partial else 'radial_arch',
      trace_center_y=0.,trace_samples=len(xy)//2,trace_quantiles=quantiles,trace_xy=xy.tolist(),
      center_connections=center_connections,max_bar_center_offset_mm=.35,
      retention_mode='none',
      shape_refinement={k:v for k,v in shape.items() if k!='feedback_ids'},
      prevent_extra_supra_openings=True,max_supra_genus=int((2-mesh.euler_number)//2),max_primary_genus=int((2-mesh.euler_number)//2),
      connection_radius_mm=float(np.median([c['radius'] for c in connections])),connections=connections,
      expected_connections=len(connections),expected_euler=2-2*len(connections),
      expected_euler_by_mesh={'primaria':None,'supra':None},
      cone_top_z=top,cone_top_overrides={},bar_top_z=top,bar_plane=plane,
      anterior_raise_mm=anterior_raise,bar_y_bounds=y_bounds,minimum_supra_mm=rules['minimum_supra_mm'],
      require_anterior_higher=bool(rules['anterior_feedback_ids']) and not partial,
      height_goal=rules.get('height_goal'),
      cement_gap_mm=.15 if arch=='SUP' else .14,max_overlap_mm3=.0001,max_connection_error_mm=.001,
      max_protected_volume_loss_mm3=.0001,
      auto_prepared=True,bar_height_delta_mm=height_delta,
      adaptation_notes='Propuesta automática desde el STL: orientación por anillos y apertura del arco; altura según espesor muestreado y límite oclusal; trazado sobre corredor con anatomía a ambos lados de TOP. Cemento inicial según referencia SUP/INF. El trazado puede acortarse en extremos finos; revisar cobertura distal. Seguridad adaptada y diseño pendientes de revisión. Sin importar geometría de ejemplos.')
    report=dict(source_sha256=source_hash,geometry_source='STL bruto exclusivamente',connections=connections,
      connection_detection_notes=detection_notes,trace_mode=profile['trace_mode'],
      input_euler=int(mesh.euler_number),dimensions_mm=mesh.extents.tolist(),raw_to_work=transform.tolist(),
      trace_bottom_z=bottoms.tolist(),trace_occlusal_z=tops.tolist(),sampled_thickness_mm=thickness.tolist(),
      bar_top_z_proposed=top,trace_width_mm=np.linalg.norm(np.array(outer)-inner,axis=1).tolist(),
      assumptions=['STL interpretado en milímetros, sin escala.','Altura basada en espesor y límite oclusal; anchura percentiles 20–80 del corredor. Propuesta inicial para revisar.','La seguridad geométrica propia no reproduce todas las selecciones históricas de B4D.','Revisar cobertura distal: los extremos finos pueden quedar fuera de la barra; el detector no identifica cada pieza dental.','Euler se registra y se compara antes/después de exportar, pero no se predice solo a partir de conexiones: el STL puede tener otras asas.'],
      corrections_applied=applied,corrections_pending=pending)
    report['design_constraints']={'anterior_raise_mm':anterior_raise,'minimum_supra_mm':rules['minimum_supra_mm'],
      'occlusal_reserve_mm':occlusal_clearance,'global_minimum_verified':False,'bar_height_delta_mm':height_delta,
      'center_connections':center_connections,'bar_centering':centering}
    report['height_reference']=height_reference
    height_reference['minimum_sampled_seat_clearance_mm']=float(min(
        axis_at_bar_top(c,profile)[2]-c['center'][2] for c in connections))
    report['refined_trace_support']=refined_support
    report['shape_refinement']=dict(shape,trace=shape_trace)
    for i,connection in enumerate(connections,1):
        profile['cone_top_overrides'][str(i)]=float(axis_at_bar_top(connection,profile)[2])
    report['trace_projection_adjustments']=shifts
    report['corridor_clearance_mm']={'cervical':1.2,'occlusal':occlusal_clearance}
    report['trace_angles_retained']=theta[indices].tolist()
    report['trace_distal_samples_omitted_for_clearance']=int(len(theta)-len(indices))
    report['top_rule']='En el plano de referencia medido: menor entre mediana(bottom+60% de espesor) y percentil 10 oclusal menos 1,5 mm, más la corrección explícita. Incremento regional separado de la inclinación cervical; propuesta para revisar.'
    return profile,report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--name',default='');p.add_argument('--output',required=True);p.add_argument('--history');a=p.parse_args()
    history=json.loads(Path(a.history).read_text(encoding='utf-8')) if a.history else {}
    profile,report=prepare(a.input,a.name,history)
    target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
    target.with_suffix('.medidas.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'arch':profile['arch'],'connections':profile['expected_connections'],'bar_top_z':profile['bar_top_z'],'thickness_range':np.percentile(report['sampled_thickness_mm'],[0,50,100]).tolist(),'profile':str(target)},ensure_ascii=False))
