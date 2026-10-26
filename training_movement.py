"""Short walking plans require continuous nearby terrain support."""
import math
from physics_extensions import solid

def walking_step(state,target_x,avoid=None,prefer='towards',distance=14,allow_shorter=False):
    """A supported world-pixel step, with three pixels of stopping clearance.

    The default remains an exact fourteen-pixel proposal. Adaptive callers may
    shorten a request at the last supported point, retaining the same margin.
    """
    hero=next((p for p in state.get('players',[]) if p.get('id')==state.get('heroId')),None)
    terrain=state.get('terrain')
    if terrain and 'surface' in terrain:terrain={**terrain,'heights':terrain['surface']}
    if not hero or not terrain or not all(isinstance(hero.get(k),(int,float)) and math.isfinite(hero[k]) for k in ('x','y')):return None
    if not isinstance(target_x,(int,float)) or isinstance(target_x,bool) or not math.isfinite(target_x) or not isinstance(distance,(int,float)) or isinstance(distance,bool) or not math.isfinite(distance) or not 2<=distance<=256:return None
    requested=math.floor(distance);margin=3
    x,y=hero['x'],hero['y']
    # Find the support level relative to the native vehicle anchor, then keep
    # every intermediate foot position close to that level. Reject holes/cliffs.
    support=next((dy for dy in range(-4,25) if solid(terrain,x,y+dy) and not solid(terrain,x,y+dy-1)),None)
    if support is None:return None
    towards=1 if target_x>x else -1
    for side in ((-towards,towards) if prefer=='away' else (towards,-towards)):
        direction='right' if side>0 else 'left'
        if direction==avoid:continue
        reference=y+support;grounds={}
        # Check every intermediate pixel, not only endpoints or even pixels.
        # The native key release can take another renderer tick to settle.
        for step in range(1,requested+margin+1):
            px=x+side*step
            ground=next((gy for gy in range(round(reference)-6,round(reference)+9) if solid(terrain,px,gy) and not solid(terrain,px,gy-1)),None)
            if ground is None or abs(ground-reference)>10:break
            grounds[step]=ground
        safe_distance=min(requested,len(grounds)-margin)
        if safe_distance>=2 and (allow_shorter or safe_distance==requested):
            ground=grounds[safe_distance]
            return {'direction':direction,'distance':safe_distance,'max_drop':14,'clearance_margin':margin,'distance_clamped':safe_distance<requested,'expected_to':[x+side*safe_distance,ground-support],'expected_body':math.degrees(math.atan2(ground-reference,side*safe_distance)) if side>0 else math.degrees(math.atan2(reference-ground,safe_distance))}
    return None

def choose_reposition(state,target_x,reason,avoid=None,evaluate=None,visited=None,position_risk=None,movement_budget=None,time_left=None):
    """Try up to eight supported positions; risk only breaks equal-cost ties.

    movement_budget is remaining horizontal world pixels, never a native fuel
    bar. With no budget/time supplied, legacy fourteen-pixel choices remain.
    """
    import copy
    preferred='away' if reason=='terrain-blocked' else 'towards'
    adaptive=movement_budget is not None or time_left is not None
    limit=72
    for value in (movement_budget,time_left):
        if value is not None and (not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<0):return None
    if movement_budget is not None:limit=min(limit,math.floor(movement_budget))
    if time_left is not None:limit=min(limit,math.floor(max(0,time_left-6.5)*24))
    if limit<2:return None
    hero=next((p for p in state.get('players',[]) if p.get('id')==state.get('heroId')),None)
    if not hero or not all(isinstance(hero.get(k),(int,float)) and not isinstance(hero[k],bool) and math.isfinite(hero[k]) for k in ('x','y')):return None
    if not adaptive:distances=[14]
    elif reason=='terrain-blocked':distances=[min(8,limit),min(28,limit),limit]
    elif reason in ('unknown-weather','weather-column','weather-escape'):
        if not isinstance(target_x,(int,float)) or not math.isfinite(target_x):return None
        goal=max(2,math.ceil(abs(target_x-hero['x'])))
        distances=[min(goal,limit),min(max(8,goal+8),limit),limit]
    else:distances=[min(4,limit),min(16,limit),limit]
    distances=list(dict.fromkeys(distances));seen=set();fallback=None;failed={'left':0,'right':0}
    def assess(step):
        hypothetical=copy.deepcopy(state);candidate=next(p for p in hypothetical['players'] if p['id']==hypothetical['heroId'])
        candidate['x'],candidate['y']=step['expected_to'];candidate['body']=step['expected_body']
        return bool(evaluate(hypothetical,step))
    def refine(clear):
        # Use a measured blocked/clear bracket rather than committing to a tier.
        # Two clear directions receive the same refinement budget, so empirical
        # exposure can still break a tie without adding a longer walk.
        result=[];per_direction=1 if len(clear)>1 else 2
        for best in clear:
            low=failed[best['direction']];high=best['distance']
            for _ in range(per_direction):
                if high-low<=2:break
                mid=(low+high)//2
                trial=walking_step(state,target_x,avoid='left' if best['direction']=='right' else 'right',prefer=preferred,distance=mid,allow_shorter=True)
                if not trial or trial['distance']<=low or any(math.dist(trial['expected_to'],point)<min(7,max(1.5,trial['distance']/2)) for point in (visited or [])):break
                if assess(trial):best={**trial,'distance_refined':True};high=trial['distance']
                else:low=trial['distance']
            result.append(best)
        return result
    def select_clear(clear):
        # A learned preference must not turn a shorter solution into a longer
        # walk. Only equally short, already-clear alternatives are comparable.
        shortest=min(step['distance'] for step in clear)
        clear=[step for step in clear if step['distance']==shortest]
        if len(clear)==2 and position_risk:
            def evidence(step):
                try:row=position_risk(list(step['expected_to']))
                except (TypeError,ValueError,KeyError,RuntimeError,OSError,OverflowError):return None
                if not isinstance(row,dict):return None
                values=[row.get(k) for k in ('estimate','low','high')]
                if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values):return None
                estimate,low,high=values;samples=row.get('samples');episodes=row.get('episodes')
                if not 0<=low<=estimate<=high<=1 or not isinstance(samples,int) or isinstance(samples,bool) or samples<8 or not isinstance(episodes,int) or isinstance(episodes,bool) or not 2<=episodes<=samples:return None
                return {'estimate':estimate,'low':low,'high':high,'samples':min(samples,1000000),'episodes':min(episodes,1000000)}
            risks=[evidence(step) for step in clear]
            if all(risks):
                chosen=0 if risks[0]['high']<risks[1]['low'] else 1 if risks[1]['high']<risks[0]['low'] else None
                if chosen is not None:
                    return {**clear[chosen],'selection':'lower-observed-exposure','opponent_evidence':{'chosen':risks[chosen],'alternative':risks[1-chosen],'changed_preference':chosen!=0}}
        return {**clear[0],'selection':'predicted-clear-path'}
    for distance in distances:
        first=walking_step(state,target_x,avoid=avoid,prefer=preferred,distance=distance,allow_shorter=adaptive)
        if not first:continue
        alternatives=[first];other=walking_step(state,target_x,avoid=first['direction'],prefer=preferred,distance=distance,allow_shorter=adaptive)
        if other and other['direction']!=avoid:alternatives.append(other)
        clear=[]
        for step in alternatives:
            key=(step['direction'],tuple(step['expected_to']))
            radius=min(7,max(1.5,step['distance']/2))
            if key in seen or any(math.dist(step['expected_to'],point)<radius for point in (visited or [])):continue
            seen.add(key)
            if fallback is None:fallback=step
            if not evaluate:return step
            if assess(step):clear.append(step)
            else:failed[step['direction']]=max(failed[step['direction']],step['distance'])
        if clear:return select_clear(refine(clear) if adaptive else clear)
    return {**fallback,'selection':'retreat-from-obstruction' if preferred=='away' else 'supported-step'} if fallback else None
