from pathlib import Path
project = Path(SPECPATH).parent
native = project / 'native' / 'bin'
a = Analysis([str(project / 'cloud_runtime.py')], pathex=[str(project)],
    binaries=[(str(native / name), 'native/bin') for name in ('dragonlab_core.dll','dragonlab_overlay.dll')],
    datas=[(str(project / 'viewer.html'),'.'),(str(native / 'native-manifest.json'),'native/bin')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['numpy','PIL.AvifImagePlugin','PIL._avif'], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,a.binaries,a.datas,[],name='DragonLab-Cloud',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    disable_windowed_traceback=False)
