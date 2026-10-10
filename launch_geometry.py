"""Transform native per-shot muzzle definitions to world coordinates."""
import math
from core import REVERSE

def muzzle_offset(player,mobile,shot):
    muzzles=player.get('muzzles',[])
    if not 0<=shot<len(muzzles):return None
    muzzle=muzzles[shot];angle=muzzle.get('angle');radius=muzzle.get('radius');body=player.get('body');look=player.get('look')
    if look not in (0,1) or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (angle,radius,body)) or not 0<radius<=200:return None
    face=look if mobile not in REVERSE else 1-look
    a=math.radians((angle if face else 180-angle)-body)
    return round(math.cos(a)*radius),-round(math.sin(a)*radius)
