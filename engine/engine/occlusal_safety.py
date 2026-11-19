"""Locally lower the separating tool where a measured supra interval is too thin.

This is a sampled occlusal correction, not a global minimum wall-thickness claim.
The original mesh and protected connection volumes are never deformed.
"""
import numpy as np
import trimesh, manifold3d as mf
from design_checks import design_checks
from connection_protection import combined
from lateral_safety import exterior_islands

def mesh_of(solid):
    data=solid.to_mesh64()
    return trimesh.Trimesh(data.vert_properties[:,:3],data.tri_verts,process=False)

def height_limit(bounds,points,clearance,spacing=.25,slope=.8,lower=0):
    """Closed volume below a Lipschitz height field; only local depressions cut."""
    low,high=np.array(bounds,dtype=float)
    x=np.linspace(low[0]-1,high[0]+1,int(np.ceil((high[0]-low[0]+2)/spacing))+1)
    y=np.linspace(low[1]-1,high[1]+1,int(np.ceil((high[1]-low[1]+2)/spacing))+1)
    xx,yy=np.meshgrid(x,y);height=np.full(xx.shape,high[2]+10.)
    for row in points:
        distance=np.hypot(xx-row['xy'][0],yy-row['xy'][1])
        height=np.minimum(height,row['supra_top_z']-clearance-.20+slope*distance)
    # Correct interpolation error conservatively by one cell diagonal. Maintain
    # at least the configured gap normal to the steepest allowed slope.
    height-=slope*spacing*np.sqrt(2)+lower
    return height_solid(x,y,height,low[2]-50)


def height_solid(x,y,height,bottom_z):
    xx,yy=np.meshgrid(x,y)
    vertices=np.column_stack([xx.ravel(),yy.ravel(),height.ravel()])
    bottom=vertices.copy();bottom[:,2]=bottom_z
    n=len(vertices);nx=len(x);ny=len(y);faces=[]
    for j in range(ny-1):
        for i in range(nx-1):
            a=j*nx+i;b=a+1;c=a+nx+1;d=a+nx
            faces.extend([(a,b,c),(a,c,d),(n+a,n+c,n+b),(n+a,n+d,n+c)])
    boundary=list(range(nx))+[j*nx+nx-1 for j in range(1,ny)]+list(range((ny-1)*nx+nx-2,(ny-1)*nx-1,-1))+[j*nx for j in range(ny-2,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.extend([(a,n+a,n+b),(a,n+b,b)])
    mesh=trimesh.Trimesh(np.vstack([vertices,bottom]),faces,process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent:raise RuntimeError('La zona local de seguridad no forma un volumen cerrado')
    solid=mf.Manifold(mf.Mesh64(np.array(mesh.vertices,dtype=np.float64),np.array(mesh.faces,dtype=np.uint64)))
    if solid.is_empty() or solid.volume()<=0:raise RuntimeError('Zona de seguridad local inválida')
    return solid

def separate_with_safety(body,inner,outer,config):
    protected=combined(config.get('connections',[]))
    outer_protected=combined(config.get('connections',[]),config['cement_gap_mm']) if protected is not None else None
    def pieces(a,b):
        if protected is not None:a=a+protected;b=b+outer_protected
        return body^a,body-b
    primary,supra=pieces(inner,outer)
    minimum=config.get('minimum_supra_mm')
    report={'scope':'Corrección local de intervalos oclusales medidos; mínimo global pendiente','attempts':[],'global_minimum_verified':False}
    report['continuity_guard']=[]
    def keeps_continuity(candidate,stage):
        parts=[float(part.volume()) for part in candidate.decompose()]
        accepted=len(parts)==1 and parts[0]>0
        report['continuity_guard'].append({'stage':stage,'components_candidate_mm3':parts,'accepted':accepted})
        if not accepted:
            report['unresolved']=True
            report['continuity_conflict']='Recorte rechazado porque fragmenta o vacía la primaria. El defecto de pared sigue pendiente; replantear el cuerpo.'
        return accepted
    if config.get('prevent_extra_supra_openings'):
        source=mesh_of(body);lateral=[]
        for attempt in range(3):
            if supra.genus()<=body.genus():break
            islands=exterior_islands(source,mesh_of(supra))
            lateral.append({'attempt':attempt,'supra_genus':supra.genus(),'source_genus':body.genus(),
                            'exterior_island_areas_mm2':[r['area_mm2'] for r in islands]})
            if not islands:break
            points=np.vstack([r['points'] for r in islands])
            reserve=minimum or .8
            if config.get('center_connections'):
                # Balance local relief across the measured bar midline. A
                # one-sided relief can leave the connection on a raised edge.
                from bar_centering import coordinates,project
                trace=np.asarray(config['trace_xy']);n=len(trace)//2
                partial=config['trace_mode']=='linear_bridge'
                t,ra=coordinates(trace[:n],partial);_,rb=coordinates(trace[n:][::-1],partial)
                pt,pr=coordinates(points[:,:2],partial)
                reflected=project(pt,2*np.interp(pt,t,(ra+rb)/2)-pr,partial)
                points=np.vstack([points,np.column_stack([reflected,points[:,2]])])
            _,ids=np.unique(np.round(points/.2).astype(int),axis=0,return_index=True)
            caps=[{'xy':point[:2].tolist(),'supra_top_z':float(point[2])} for point in points[ids]]
            bounds=mesh_of(outer).bounds
            next_inner=inner^height_limit(bounds,caps,reserve,lower=config['cement_gap_mm']*np.sqrt(1+.8**2)+.02)
            next_outer=outer^height_limit(bounds,caps,reserve)
            next_primary,next_supra=pieces(next_inner,next_outer)
            if not keeps_continuity(next_primary,'lateral_'+str(attempt)):break
            inner,outer=next_inner,next_outer
            primary,supra=next_primary,next_supra
        report['lateral_repairs']=lateral
        report['supra_genus_after_lateral']=supra.genus()
        report['extra_openings_resolved']=bool(supra.genus()<=body.genus())
    if config.get('shape_refinement',{}).get('smooth_roof'):
        from shape_refinement import rounded_roof
        before=primary.volume();x,y,z,refinement=rounded_roof(mesh_of(primary),config)
        limit=height_solid(x,y,z,mesh_of(body).bounds[0,2]-50)
        next_inner=inner^limit
        # Retain a vertical allowance above the new roof in addition to the
        # existing lateral cement volume. Functional protection is reapplied.
        next_outer=outer^limit.translate([0,0,config['cement_gap_mm']*np.sqrt(2)+.02])
        next_primary,next_supra=pieces(next_inner,next_outer)
        if keeps_continuity(next_primary,'roof'):
            inner,outer=next_inner,next_outer
            primary,supra=next_primary,next_supra
        refinement['metal_removed_mm3']=before-primary.volume()
        refinement['connections_reprotected']=len(config.get('connections',[]))
        report['roof_refinement']=refinement
    if not minimum:return primary,supra,report
    source=mesh_of(body);caps=[];previous=None
    for attempt in range(4):
        checks=design_checks(source,mesh_of(primary),mesh_of(supra),config)
        thin=[row for row in checks.get('samples',[]) if row['supra_occlusal_mm']<minimum-1e-5]
        report['attempts'].append({'attempt':attempt,'minimum_sampled_mm':checks.get('minimum_sampled_occlusal_mm'),
            'sample_count':checks['sample_count'],'thin_sections':thin,
            'unpaired_source_sections':checks.get('unpaired_source_sections',[])})
        if not thin:return primary,supra,report
        if attempt==3:break
        current=checks['minimum_sampled_occlusal_mm']
        if previous is not None and current<=previous+1e-5:
            report['stopped_reason']='La corrección local no mejora el mínimo medido; conservar geometría y diagnóstico para revisar la zona.'
            break
        previous=current;caps.extend(thin)
        bounds=mesh_of(outer).bounds
        limit=height_limit(bounds,caps,minimum)
        inner_limit=height_limit(bounds,caps,minimum,lower=config['cement_gap_mm']*np.sqrt(1+.8**2)+.02)
        next_primary,next_supra=pieces(inner^inner_limit,outer^limit)
        if not keeps_continuity(next_primary,'occlusal_'+str(attempt)):break
        primary,supra=next_primary,next_supra
    report['unresolved']=True
    return primary,supra,report
