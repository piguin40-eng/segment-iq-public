"""Keep actual dual-mesh grooves only where they preserve primary topology."""
import manifold3d as mf
import numpy as np


MODES={'none','dual_optional','dual_required'}


def retention_mode(config):
    mode=config.get('retention_mode','dual_required')
    if mode not in MODES:raise ValueError('Modo de retenciones no reconocido.')
    return mode


def apply_retention_policy(base,tool,config):
    mode=retention_mode(config)
    material=[p for p in base.decompose() if abs(p.volume())>1e-10]
    if len(material)!=1:
        raise RuntimeError('La primaria ya contiene fragmentos antes de las retenciones; corregir la separación y las conexiones.')
    base=material[0]
    if mode=='none':
        return base,mf.Manifold(),{'mode':mode,'status':'not_applied_by_design','accepted':[],'rejected':[],
            'reason':'Sin retenciones añadidas: opcionales en LAB-VIDEO-BARRAS-20260916; se conserva la barra para revisar inserción y espesor.'}
    result,removed,report=apply_safe_retention(base,tool)
    applied=base.volume()-result.volume()>1e-8
    report.update(mode=mode,status='applied' if applied else 'no_safe_grooves')
    if not applied and mode=='dual_required':
        raise RuntimeError('No quedan surcos de retención seguros después de proteger la barra; revisar la red dual.')
    return result,removed,report


def apply_safe_retention(base,tool):
    cuts=sorted((base^tool).decompose(),key=lambda part:-part.volume())
    result=base;accepted=[];rejected=[]
    for cut in cuts:
        if cut.volume()<=1e-10:continue
        # Do not subtract the intersection already clipped to the primary.
        # Its new faces coincide exactly with the bar and can create inverted
        # contact sheets after serialization. Use the original protected tool
        # in a slightly padded local box; padding selects tool only, never adds
        # material to it or invades an excluded functional region.
        bounds=np.asarray(cut.bounding_box());low=bounds[:3]-1e-4;high=bounds[3:]+1e-4
        local_tool=tool^mf.Manifold.cube(high-low).translate(low)
        trial=result-local_tool
        # Detect unstable surface contacts before acceptance, with the same
        # indexed round trip used downstream. Any resulting metal fragment or
        # new opening still rejects the groove; no threshold is relaxed.
        trial=mf.Manifold(trial.to_mesh64()).simplify(1e-7)
        parts=trial.decompose()
        # Boolean operations can emit coincident sheets with numerical zero
        # volume. They are not pieces of metal and must not distort genus or
        # reject a safe groove. Keep the same bound as final export cleanup.
        material=[part for part in parts if abs(part.volume())>1e-10]
        row={'volume_mm3':cut.volume(),'bounds':list(cut.bounding_box())}
        if len(material)!=1 or material[0].genus()>base.genus() or material[0].volume()<=0:
            rejected.append(dict(row,reason='El surco abre un paso adicional o separa metal.'))
        else:
            row['zero_volume_sheets_removed']=len(parts)-len(material)
            row['actual_removed_mm3']=result.volume()-material[0].volume()
            accepted.append(row);result=material[0]
    return result,base-result,{'accepted':accepted,'rejected':rejected,
                             'rule':'Se conservan los surcos de la red dual que no perforan ni desconectan la barra.',
                             'subtraction_method':'protected_original_tool_in_local_box',
                             'tool_selection_padding_mm':1e-4,'contact_regularization_mm':1e-7}
