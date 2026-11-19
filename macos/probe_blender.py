"""Run with the configured local Blender; never claim B4D without its receipt."""
import json,sys
from pathlib import Path
import bpy

report={'version':bpy.app.version_string,'platform':sys.platform,
        'stl_import':hasattr(bpy.ops.import_mesh,'stl'),'tissue':False,'b4d_available':False}
try:
    bpy.ops.preferences.addon_enable(module='mesh_tissue')
    report['tissue']='mesh_tissue' in bpy.context.preferences.addons
except Exception as error:report['tissue_error']=str(error)
addon=bpy.context.preferences.addons.get('pie_menu_editor')
report['b4d_available']=bool(addon and hasattr(addon.preferences,'pie_menus') and
                           any('ibar' in menu.name.lower() for menu in addon.preferences.pie_menus))
if '--' in sys.argv:
    output=Path(sys.argv[sys.argv.index('--')+1]);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
if bpy.app.version[:2]!=(3,6) or not report['stl_import'] or not report['tissue']:
    raise RuntimeError('El motor actual requiere Blender 3.6 y Tissue. No se ha cambiado el motor por otro incompatible.')
