# Reproducible Windows package; build native/build_native.ps1 first.
from pathlib import Path
project = Path(SPECPATH).parent
native = project / 'native' / 'bin'
a = Analysis([str(project / 'launcher.py')], pathex=[str(project)],
    binaries=[(str(native / name), 'native/bin') for name in ('dragonlab_core.dll','dragonlab_overlay.dll')],
    datas=[(str(project / 'viewer.html'),'.'),(str(native / 'native-manifest.json'),'native/bin')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['numpy','PIL.AvifImagePlugin','PIL._avif'], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,a.binaries,a.datas,[],name='DragonLab-Launcher',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    manifest=str(project / 'native' / 'windows.manifest'),disable_windowed_traceback=False)
