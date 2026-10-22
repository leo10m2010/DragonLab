"""Short walking plans require continuous nearby terrain support."""
import math
from physics_extensions import solid

def walking_step(state,target_x,avoid=None,prefer='towards'):
    hero=next((p for p in state.get('players',[]) if p.get('id')==state.get('heroId')),None)
    terrain=state.get('terrain')
    if terrain and 'surface' in terrain:terrain={**terrain,'heights':terrain['surface']}
    if not hero or not terrain or not all(isinstance(hero.get(k),(int,float)) and math.isfinite(hero[k]) for k in ('x','y')):return None
    x,y=hero['x'],hero['y']
    # Find the support level relative to the native vehicle anchor, then keep
    # every intermediate foot position close to that level. Reject holes/cliffs.
    support=next((dy for dy in range(-4,25) if solid(terrain,x,y+dy) and not solid(terrain,x,y+dy-1)),None)
    if support is None:return None
    towards=1 if target_x>x else -1
    for side in ((-towards,towards) if prefer=='away' else (towards,-towards)):
        direction='right' if side>0 else 'left'
        if direction==avoid:continue
        safe=True;reference=y+support
        for step in range(2,15,2):
            px=x+side*step
            ground=next((gy for gy in range(round(reference)-6,round(reference)+9) if solid(terrain,px,gy) and not solid(terrain,px,gy-1)),None)
            if ground is None or abs(ground-(y+support))>10:safe=False;break
        if safe:return {'direction':direction,'distance':14,'max_drop':14,'expected_to':[x+side*14,ground-support],'expected_body':math.degrees(math.atan2(ground-(y+support),side*14)) if side>0 else math.degrees(math.atan2((y+support)-ground,14))}
    return None

def choose_reposition(state,target_x,reason,avoid=None,evaluate=None,visited=None):
    """Compare both supported directions; a blocked muzzle prefers retreat."""
    import copy
    preferred='away' if reason=='terrain-blocked' else 'towards'
    first=walking_step(state,target_x,avoid=avoid,prefer=preferred)
    if not first:return None
    alternatives=[first];other=walking_step(state,target_x,avoid=first['direction'],prefer=preferred)
    if other and other['direction']!=avoid:alternatives.append(other)
    alternatives=[step for step in alternatives if not any(math.dist(step['expected_to'],point)<7 for point in (visited or []))]
    if not alternatives:return None
    first=alternatives[0]
    if not evaluate:return first
    for step in alternatives:
        hypothetical=copy.deepcopy(state);hero=next(p for p in hypothetical['players'] if p['id']==hypothetical['heroId'])
        hero['x'],hero['y']=step['expected_to'];hero['body']=step['expected_body']
        if evaluate(hypothetical,step):return {**step,'selection':'predicted-clear-path'}
    return {**first,'selection':'retreat-from-obstruction' if preferred=='away' else 'supported-step'}
