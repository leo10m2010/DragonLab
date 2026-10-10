"""Visual forecast learned from observed missile families, independent of aiming.

Similar flight time selects a shape. A rigid rotation and uniform scale maps
its guide-apex-to-impact vector to the current prediction. This is not a
validated homing law; weather, terrain and extreme arcs can change the result.
"""
import math
from kals_templates import FAMILIES

def forecast(mode,origin,end,split):
    dx=end[0]-origin[0];dy=end[1]-origin[1];length=math.hypot(dx,dy)
    remaining=end[2]-split
    candidates=[f for f in FAMILIES if f['mode']==mode]
    if not candidates or remaining<=.1 or length<1:return []
    family=min(candidates,key=lambda f:abs(math.log(remaining/f['remaining']))+abs(math.log(length/f['length']))*.25)
    time_scale=remaining/family['remaining']
    # Extrapolation is visible as an estimate, never a claim of calibrated hit.
    face=1 if dx>=0 else -1
    return [[(origin[0]+u*dx-v*face*dy,origin[1]+u*dy+v*face*dx,split+t*time_scale) for u,v,t in branch] for branch in family['branches']]
