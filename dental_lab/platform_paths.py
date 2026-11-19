"""Platform paths shared by the local installers and the server."""
import os
import sys
from pathlib import Path


def install_root(platform=None, home=None):
    platform=platform or sys.platform;home=Path.home() if home is None else Path(home)
    return home/'Library/Application Support/SEGMENT IQ' if platform=='darwin' else home/'Documents/DentalLabAgent'


def environment_python(root, name='python', platform=None):
    platform=platform or sys.platform
    return Path(root)/'runtime'/name/('Scripts/python.exe' if platform=='win32' else 'bin/python')


def blender_default(platform=None, home=None):
    platform=platform or sys.platform
    if platform=='darwin':
        return str(install_root(platform,home)/'runtime/Blender.app/Contents/MacOS/Blender')
    if platform=='win32':return r'C:\Program Files\Blender Foundation\Blender 3.6\blender.exe'
    return 'blender'


def codex_candidates(home=None, platform=None):
    home=Path.home() if home is None else Path(home);platform=platform or sys.platform
    if platform=='darwin':
        return [install_root(platform,home)/'runtime/codex/codex',
                Path('/opt/homebrew/bin/codex'),Path('/usr/local/bin/codex'),
                home/'.local/bin/codex',Path('/Applications/Codex.app/Contents/Resources/codex')]
    if platform=='win32':return list((home/'AppData/Local/OpenAI/Codex/bin').glob('*/codex.exe'))
    return [home/'.local/bin/codex']
