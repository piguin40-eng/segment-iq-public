"""Fit a reference plane to continuous source material, without relaxing reserves."""
import numpy as np
from scipy.optimize import differential_evolution
from bar_height import regional_weight
from bar_centering import coordinates,project


class TraceSupportError(ValueError):
    pass


def fit_trace_plane(mesh,trace,connections,config,clearance,samples_at):
    partial=config['trace_mode']=='linear_bridge'
    trace=np.asarray(trace);n=len(trace)//2;theta=coordinates(trace[:n],partial)[0]
    grid=np.vstack([project(t,np.linspace(samples_at(t).min(),samples_at(t).max(),180),partial) for t in theta])
    points,ids,_=mesh.ray.intersects_location(np.c_[grid,np.full(len(grid),mesh.bounds[0,2]-2)],
                    np.tile([0,0,1],(len(grid),1)),multiple_hits=True)
    if not len(points):raise TraceSupportError('No hay intersecciones de material para ajustar el plano del trazado.')
    order=np.lexsort((points[:,2],ids));points=points[order];ids=ids[order]
    unique,starts,counts=np.unique(ids,return_index=True,return_counts=True)
    rows=[]
    for ray,start,count in zip(unique,starts,counts):
        z=np.unique(np.round(points[start:start+count,2],8))
        if len(z)%2:continue
        for lo,hi in z.reshape(-1,2):
            if hi-lo>1.2+clearance:rows.append([int(ray)//180,*grid[ray],lo+1.2,hi-clearance])
    rows=np.asarray(rows)
    if not len(rows) or len(np.unique(rows[:,0]))!=n:
        raise TraceSupportError('Hay una sección sin espesor continuo para la barra y la reserva de supra, incluso adaptando el plano.')
    group=rows[:,0].astype(int);x,y,lo,hi=rows[:,1:].T
    rise=config.get('anterior_raise_mm',0);weights=regional_weight(y,config.get('bar_y_bounds',[0,1]))
    centers=np.asarray([c['center'] for c in connections]);cw=regional_weight(centers[:,1],config.get('bar_y_bounds',[0,1]))
    base=np.asarray([*config.get('bar_plane',[0.,0.])[:2],config['bar_top_z']])
    def errors(plane):
        h=x*plane[0]+y*plane[1]+plane[2]+rise*weights
        delta=np.maximum(lo+.08-h,0)+np.maximum(h-hi+.08,0)
        error=np.full(n,np.inf);np.minimum.at(error,group,delta)
        seat=np.maximum(centers[:,2]+1-(centers[:,:2]@plane[:2]+plane[2]+rise*cw),0)
        return error,seat
    def objective(plane):
        error,seat=errors(plane)
        return 100*(np.sum(error**2)+np.sum(seat**2))+.0001*np.sum(((plane-base)*[20,20,1])**2)
    result=differential_evolution(objective,[(base[0]-.2,base[0]+.2),(base[1]-.2,base[1]+.2),
                    (base[2]-3,base[2]+3)],seed=42,popsize=10,maxiter=100,tol=1e-7,polish=True)
    error,seat=errors(result.x)
    if max(error.max(),seat.max())>1e-5:
        raise TraceSupportError('No se encuentra un plano continuo compatible con todas las secciones y conexiones; revisar el trazado del caso.')
    h=x*result.x[0]+y*result.x[1]+result.x[2]+rise*weights
    inner=[];outer=[]
    for i in range(n):
        valid=np.flatnonzero((group==i)&(h>lo)&(h<hi))
        if not len(valid):raise TraceSupportError('El plano ajustado no conserva la reserva en todas las secciones.')
        radius=y[valid] if partial else np.hypot(x[valid],y[valid])
        values=np.percentile(radius,config.get('trace_quantiles',[20,80]))
        a,b=[valid[np.argmin(abs(radius-q))] for q in values]
        inner.append(rows[a,1:3]);outer.append(rows[b,1:3])
    updated=dict(config,bar_plane=result.x.tolist(),bar_top_z=float(result.x[2]))
    return updated,np.vstack([outer,inner[::-1]]),{
        'method':'Ajuste de plano con intervalos continuos del STL y soporte local de conexiones',
        'initial_plane':base.tolist(),'final_plane':result.x.tolist(),'sections':n,
        'cervical_clearance_mm':1.2,'occlusal_clearance_mm':clearance,
        'source_geometry_changed':False,'constraints_relaxed':False}
