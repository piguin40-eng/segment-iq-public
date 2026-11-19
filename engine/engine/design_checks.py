"""Measure local supra intervals along the actual separating surface normals."""
import numpy as np
from bar_height import regional_weight
from ray_material import first_material_exit

def vertical_hits(mesh,xy,z):
    points,ids,_=mesh.ray.intersects_location(np.column_stack((xy,np.full(len(xy),z))),np.tile([0,0,1],(len(xy),1)),multiple_hits=True)
    if not len(points):return [np.array([]) for _ in range(len(xy))]
    return [np.sort(points[ids==i,2]) for i in range(len(xy))]

def design_checks(source,primary,supra,config):
    trace=np.asarray(config.get('trace_xy',[]));n=len(trace)//2
    if not n:return {'scope':'No hay trazado medido para comprobar secciones','global_minimum_verified':False}
    left,right=trace[:n],trace[n:][::-1]
    xy=np.concatenate([left*f+right*(1-f) for f in (.25,.5,.75)])
    floor=float(source.bounds[0,2])-2
    sh,ph,uh=[vertical_hits(mesh,xy,floor) for mesh in (source,primary,supra)]
    # The working Z direction can leave through the side of an inclined screw
    # channel. Its very short chord is not the thickness above the separator.
    # Keep Z sections as evidence, but measure each new interface along its own
    # outward normal, within the same contiguous source material interval.
    points,ids,faces=primary.ray.intersects_location(np.column_stack((xy,np.full(len(xy),floor))),
        np.tile([0,0,1],(len(xy),1)),multiple_hits=True)
    normals={}
    for i in np.unique(ids):
        candidates=np.flatnonzero(ids==i)
        last=candidates[np.argmax(points[candidates,2])]
        normals[int(i)]=primary.face_normals[faces[last]]
    samples=[];unpaired=[];candidates=[];directions=[];origins=[]
    for i,(raw,p,u) in enumerate(zip(sh,ph,uh)):
        if not len(raw) or not len(p):continue
        # A ray can leave the original through a screw channel, then hit an
        # unrelated thin wall farther above. That is not a cement-facing roof.
        # Measure supra only in the original material interval containing the
        # primary's new separating surface; retain excluded evidence explicitly.
        if len(raw)%2:continue
        interval=next(((lo,hi) for lo,hi in raw.reshape(-1,2) if lo-1e-5<=p[-1]<hi-1e-5),None)
        if interval is None:
            unpaired.append({'xy':xy[i].tolist(),'primary_top_z':float(p[-1]),'source_z':raw.tolist(),
                'supra_z':u.tolist(),'reason':'Sin techo de separación en el mismo intervalo de material; el rayo termina en la superficie original o cruza una chimenea.'})
            continue
        above=u[(u>p[-1]+.001)&(u<=interval[1]+1e-5)]
        row={'xy':xy[i].tolist(),'primary_height_mm':float(p[-1]-raw[0]),
             'primary_top_z':float(p[-1]),'measurement_direction':normals[i].tolist(),
             'vertical_chord_mm':float(above[1]-above[0]) if len(above)>=2 else None}
        candidates.append(row);directions.append(normals[i]);origins.append([*xy[i],p[-1]])
    if candidates:
        origins=np.asarray(origins);directions=np.asarray(directions)
        start=origins+directions*1e-5
        source_points,source_ids,source_faces=source.ray.intersects_location(start,directions,multiple_hits=True)
        supra_points,supra_ids,supra_faces=supra.ray.intersects_location(start,directions,multiple_hits=True)
        entries=[];entry_directions=[];entry_rows=[]
        for i,row in enumerate(candidates):
            raw=source_points[source_ids==i] if len(source_points) else np.empty((0,3))
            material=supra_points[supra_ids==i] if len(supra_points) else np.empty((0,3))
            distances=(raw-origins[i])@directions[i]
            source_dots=source.face_normals[source_faces[source_ids==i]]@directions[i]
            source_exit=first_material_exit(distances,source_dots)
            end=float(distances[source_exit]) if source_exit is not None else 0.
            length=(material-origins[i])@directions[i]
            selected=np.flatnonzero((length>1e-6)&(length<=end+1e-5))
            selected=selected[np.argsort(length[selected])]
            if len(selected)>=2:
                a,b=selected[:2]
                face=int(supra_faces[supra_ids==i][a])
                inward=-np.asarray(supra.face_normals[face])
                row['primary_normal_chord_mm']=float(length[b]-length[a])
                row['primary_probe_direction']=directions[i].tolist()
                if float(inward@directions[i])>0:
                    row.update(measurement_direction=inward.tolist(),supra_entry_xyz=material[a].tolist())
                    entries.append(material[a]);entry_directions.append(inward);entry_rows.append(row)
                else:
                    row.update(supra_occlusal_mm=0.,supra_bottom_z=float(material[a,2]),
                        supra_top_z=float(material[a,2]),measurement_error='La primera cara no entra en la cavidad de supra.')
            else:
                # Do not silently exclude a new separator lacking a complete
                # supra interval in the original material: it must fail safety.
                row.update(supra_occlusal_mm=0.,supra_bottom_z=row['primary_top_z'],
                    supra_top_z=row['primary_top_z'],measurement_error='Sin intervalo completo de supra sobre la nueva separación.')
            samples.append(row)
        if entries:
            # A retention changes the metal normal but does not change the
            # opposing cavity. Measure thickness perpendicular to THAT cavity;
            # keep the oblique metal ray as a diagnostic, not as its thickness.
            entries=np.asarray(entries);inward=np.asarray(entry_directions)
            start=entries+inward*1e-5
            rp,ri,rf=source.ray.intersects_location(start,inward,multiple_hits=True)
            sp,si,sf=supra.ray.intersects_location(start,inward,multiple_hits=True)
            for i,row in enumerate(entry_rows):
                raw=rp[ri==i];material=sp[si==i];faces=sf[si==i]
                rd=(raw-entries[i])@inward[i];sd=(material-entries[i])@inward[i]
                source_dots=source.face_normals[rf[ri==i]]@inward[i]
                supra_dots=supra.face_normals[faces]@inward[i]
                raw_exit=first_material_exit(rd,source_dots)
                end=float(rd[raw_exit]) if raw_exit is not None else 0.
                j=first_material_exit(sd,supra_dots)
                row['source_oriented_crossings_at_entry']=int(np.sign(source_dots[rd>1e-6]).sum())
                row['supra_oriented_crossings_at_entry']=int(np.sign(supra_dots[sd>1e-6]).sum())
                row['source_internal_crossings_before_exit']=int(np.sum((rd>1e-6)&(rd<end-1e-6)))
                row['supra_bottom_z']=float(entries[i,2])
                if j is not None and sd[j]<=end+1e-5 and float(supra.face_normals[faces[j]]@inward[i])>0:
                    row.update(supra_occlusal_mm=float(sd[j]),supra_top_z=float(material[j,2]),
                        supra_exit_xyz=material[j].tolist(),first_original_exit_mm=end)
                else:
                    row.update(supra_occlusal_mm=0.,supra_top_z=float(entries[i,2]),
                        measurement_error='Sin salida de supra en su normal dentro del primer intervalo del original.')
    result={'scope':'Tres líneas interiores del trazado; espesor local en la normal a la separación, acotado al mismo intervalo de material original. No acredita mínimo global ni márgenes.',
            'measurement_method':'supra_cavity_normal',
            'material_interpretation':'Positive oriented material; first exit before any void. Internal overlapping surfaces are recorded, not repaired or approved.',
            'global_minimum_verified':False,'samples':samples,'sample_count':len(samples),
            'unpaired_source_sections':unpaired}
    if samples:
        thickness=np.array([x['supra_occlusal_mm'] for x in samples])
        result['minimum_sampled_occlusal_mm']=float(thickness.min())
        minimum=config.get('minimum_supra_mm')
        if minimum:
            result['occlusal_target_mm']=minimum;result['occlusal_target_pass']=bool(thickness.min()>=minimum-1e-5)
    if config.get('anterior_raise_mm') and samples:
        weights=regional_weight(np.array([x['xy'][1] for x in samples]),config['bar_y_bounds'])
        height=np.array([x['primary_height_mm'] for x in samples])
        a=height[weights>.8];p=height[weights<.2]
        result['regional_samples']={'anterior':len(a),'posterior':len(p)}
        if len(a)>=3 and len(p)>=3:
            result['anterior_height_median_mm']=float(np.median(a));result['posterior_height_median_mm']=float(np.median(p))
            result['anterior_higher_pass']=bool(np.median(a)>np.median(p)+.1)
        else:result['anterior_higher_pass']=False
    return result
