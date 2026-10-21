"""Short walking plans require continuous nearby terrain support."""
import math
from physics_extensions import solid

def walking_step(state,target_x,avoid=None):
    hero=next((p for p in state.get('players',[]) if p.get('id')==state.get('heroId')),None)
    terrain=state.get('terrain')
    if terrain and 'surface' in terrain:terrain={**terrain,'heights':terrain['surface']}
    if not hero or not terrain or not all(isinstance(hero.get(k),(int,float)) and math.isfinite(hero[k]) for k in ('x','y')):return None
    x,y=hero['x'],hero['y']
    # Find the support level relative to the native vehicle anchor, then keep
    # every intermediate foot position close to that level. Reject holes/cliffs.
    support=next((dy for dy in range(-4,25) if solid(terrain,x,y+dy)),None)
    if support is None:return None
    towards=1 if target_x>x else -1
    for side in (towards,-towards):
        direction='right' if side>0 else 'left'
        if direction==avoid:continue
        safe=True;reference=y+support
        for step in range(2,15,2):
            px=x+side*step
            ground=next((gy for gy in range(round(reference)-6,round(reference)+9) if solid(terrain,px,gy)),None)
            if ground is None or abs(ground-(y+support))>10:safe=False;break
        if safe:return {'direction':direction,'distance':14,'max_drop':14}
    return None
