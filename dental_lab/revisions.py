"""Make unchanged redesigns explicit, and compare each output with its predecessor."""
import hashlib
import json


GEOMETRY_KEYS=('source_sha256','arch','raw_to_work','trace_xy','trace_samples','trace_quantiles',
               'connections','cone_top_z','cone_top_overrides','bar_top_z','bar_plane',
               'anterior_raise_mm','bar_y_bounds','minimum_supra_mm','cement_gap_mm','center_connections',
               'prevent_extra_supra_openings','shape_refinement','retention_mode')


def stable(value):
    if isinstance(value,float):return round(value,6)
    if isinstance(value,list):return [stable(x) for x in value]
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items()}
    return value


def compare_profiles(before,after):
    changed=[k for k in GEOMETRY_KEYS if stable(before.get(k))!=stable(after.get(k))]
    return {'parameters_changed':changed,'bar_top_change_mm':after['bar_top_z']-before['bar_top_z'],
            'geometry_parameters_changed':bool(changed)}


def engine_digest(folder):
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.py')}


def compare_meshes(before,after):
    return {key:{'before_mm3':before['meshes'][key]['volume_mm3'],
                 'after_mm3':after['meshes'][key]['volume_mm3'],
                 'change_mm3':after['meshes'][key]['volume_mm3']-before['meshes'][key]['volume_mm3']}
            for key in ('primaria','supra')}
