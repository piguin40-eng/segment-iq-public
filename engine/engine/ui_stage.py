"""Execute one owned geometry script in a dedicated Blender UI instance."""
import bpy, os, runpy, sys, traceback, json
from pathlib import Path

script=Path(sys.argv[sys.argv.index('--')+1]).resolve()
receipt=Path('outputs/Proceso/Blender')/('etapa_'+os.environ['DENTAL_STEP']+'.json')
os.environ['DENTAL_UI_STAGE']='1'
# Loading a file inside an active temp_override invalidates the UI context.
# Load before returning to the event loop; enter the new context on the next tick.
if script.name=='05_remesh_gap.py':
    bpy.ops.wm.open_mainfile(filepath=str(Path('outputs/Inferior_independiente/03_Diseno_basico_propio.blend').resolve()),load_ui=False,use_scripts=False)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.view.show_splash=False

def run():
    result={'status':'FAILED','script':script.name}
    try:
        window=bpy.context.window or bpy.context.window_manager.windows[0]
        area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
        region=next(r for r in area.regions if r.type=='WINDOW')
        with bpy.context.temp_override(window=window,area=area,region=region):
            runpy.run_path(str(script),run_name='__main__')
        result['status']='PASS'
    except Exception as error:
        traceback.print_exc();result['error']=str(error)
    finally:
        receipt.parent.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        bpy.ops.wm.quit_blender()

bpy.app.timers.register(run,first_interval=2)
