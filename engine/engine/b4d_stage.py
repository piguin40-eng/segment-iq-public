"""Run the installed iBar tool in a real Blender UI context. No vendor code bundled."""
import bpy, os, sys, json, traceback, runpy
from pathlib import Path
bpy.context.preferences.view.show_splash=False

def run():
    receipt=Path('outputs/Inferior_independiente/B4D_ejecucion.json')
    try:
        addon=bpy.context.preferences.addons.get('pie_menu_editor')
        if not addon or not hasattr(addon.preferences,'pie_menus'):
            raise RuntimeError('Blender for Dental no ha cargado sus menús. Reparar su instalación local.')
        if not any('ibar' in menu.name.lower() for menu in addon.preferences.pie_menus):
            raise RuntimeError('Los menús licenciados de iBar no están disponibles en esta instalación.')
        area=next(a for a in bpy.context.window.screen.areas if a.type=='VIEW_3D')
        region=next(r for r in area.regions if r.type=='WINDOW')
        with bpy.context.temp_override(area=area,region=region):
            runpy.run_path(str(Path(__file__).with_name('05_remesh_gap.py')),run_name='__main__')
        print('B4D_STAGE_COMPLETE',flush=True)
    except Exception as error:
        traceback.print_exc();receipt.parent.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps({'status':'FAILED','error':str(error)},ensure_ascii=False),encoding='utf-8')
    finally:bpy.ops.wm.quit_blender()

def load_scene():
    bpy.ops.wm.open_mainfile(filepath=str(Path('outputs/Inferior_independiente/03_Diseno_basico_propio.blend').resolve()),load_ui=False,use_scripts=False)
    bpy.app.timers.register(run,first_interval=2)
bpy.app.timers.register(load_scene,first_interval=5)
