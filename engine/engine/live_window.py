"""Capture this worker's Blender window after real operations, never the desktop.

Only display settings change. Capture errors cannot turn a valid geometry step
into a failure. Long synchronous operators retain the previous frame.
"""
import json, os, time
from pathlib import Path

def empty_scene():
    import bpy
    if not os.environ.get('DENTAL_UI_STAGE'):
        bpy.ops.wm.read_factory_settings(use_empty=True)


def checkpoint(label):
    if not os.environ.get('DENTAL_LIVE_WINDOW'):
        return
    import bpy
    if bpy.app.background:
        return
    folder=Path('outputs/Proceso/Blender');folder.mkdir(parents=True,exist_ok=True)
    manifest=folder/'ventana.json'
    try:
        from mathutils import Quaternion
        window=bpy.context.window or bpy.context.window_manager.windows[0]
        area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
        region=next(r for r in area.regions if r.type=='WINDOW')
        with bpy.context.temp_override(window=window,area=area,region=region):
            space=area.spaces.active
            space.overlay.show_floor=False
            space.overlay.show_axis_x=False;space.overlay.show_axis_y=False
            space.region_3d.view_rotation=Quaternion((1,0,0,0))
            space.region_3d.view_perspective='ORTHO'
            space.shading.type='SOLID';space.shading.show_cavity=True
            bpy.context.view_layer.update()
            bpy.ops.view3d.view_all(center=False)
            area.header_text_set('SEGMENT IQ | '+label)
            try:
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP',iterations=2)
                records=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {'frames':[]}
                index=len(records['frames'])+1
                name=f'{index:04d}.png';temporary=folder/f'{index:04d}.tmp.png'
                bpy.ops.screen.screenshot(filepath=str(temporary.resolve()))
                if not temporary.is_file():raise RuntimeError('Blender no guardó la captura')
                os.replace(temporary,folder/name)
                records['frames'].append({'step':int(os.environ['DENTAL_STEP']), 'label':label,
                    'path':'Proceso/Blender/'+name,'created':time.time(),'kind':'blender_window'})
                records['capture']='Blender screen.screenshot · propia ventana · después de operaciones reales'
                temp_manifest=folder/'ventana.tmp'
                temp_manifest.write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
                os.replace(temp_manifest,manifest)
            finally:area.header_text_set(None)
    except Exception as error:
        (folder/'captura_error.txt').write_text(str(error),encoding='utf-8')
        print('BLENDER_WINDOW_ERROR',str(error),flush=True)
