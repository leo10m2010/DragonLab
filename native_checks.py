"""Packaged runtime check: no window, game connection, capture or input."""
import ctypes,io,json,pathlib
from core import Settings
from native_solver import NativeSolver,library_path

def run(destination):
    from PIL import Image
    report={'schema':1,'native':{},'image_formats':[]}
    native=NativeSolver();result=native.solve(Settings(angle=60,hero_x=150,hero_y=400,target_x=700,target_y=400,gravity=396,power_scale=2.45,muzzle=False,environment={'terrain':{'polygon':[[0,450],[1200,450],[1200,900],[0,900]]},'hitTolerance':18}))
    if not result.get('reachable') or result.get('power')!=205:raise RuntimeError('La regresión nativa empaquetada falló')
    report['native']['core']={'available':True,'power':result['power']}
    dll=ctypes.CDLL(str(library_path('dragonlab_overlay').resolve()))
    dll.dl_overlay_status.argtypes=[];dll.dl_overlay_status.restype=ctypes.c_uint32
    report['native']['overlay']={'available':True,'status':dll.dl_overlay_status()}
    for format_name in ('PNG','JPEG','BMP'):
        output=io.BytesIO();Image.new('RGB',(8,8),(77,245,156)).save(output,format_name);output.seek(0)
        with Image.open(output) as image:
            image.load()
            if image.size!=(8,8):raise RuntimeError('Codec de imagen inválido')
        report['image_formats'].append(format_name)
    from mascot import mascot_source
    from icons import ICON_NAMES,icon_pixels
    artwork=mascot_source()
    for name in ICON_NAMES:
        if icon_pixels(name,16,'#BAFF00').getchannel('A').getbbox() is None:raise RuntimeError('Icono vacío')
    report['assets']={'dragon_size':list(artwork.size),'tabler_icons':len(ICON_NAMES)}
    pathlib.Path(destination).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
