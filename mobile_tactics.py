"""Reference roles and measured terrain context, never firing authorization.

Mechanics/delays: https://dragonbound.net/guide/mobiles
These descriptions do not supply force, gravity, damage or a completed model.
"""
import math
from calibration_book import mobile_name
from physics_extensions import solid

GUIDE_URL='https://dragonbound.net/guide/mobiles'

# role, normal tactical purpose, reference shot delay, special mechanism, dig use
ROLES={
    'ARMOR':(
        ('direct-impact','attack',250,False,True),
        ('two-warheads','attack',430,True,False),
        ('time-expanding-shell','attack',800,True,False)),
    'NAK':(
        ('direct-impact','clear-line',250,False,False),
        ('underground-return','underground-attack',400,True,False),
        ('terrain-ignoring','piercing-attack',800,True,False)),
    'ADUKA':(
        ('direct-electric','quick-attack',250,False,False),
        ('thor-tracers','charge-thor',400,True,False),
        ('terrain-ignoring-thor','thor-penetration',800,True,False)),
    'TRICO':(
        ('direct-impact','attack',250,False,True),
        ('orbiting-triple','grouped-impact',400,True,False),
        ('explosive-impact','remove-support',800,True,True)),
    'KALSIDDON':(
        ('flight-transformation','transform-in-flight',None,True,False),
        ('flight-transformation','transform-in-flight',None,True,False),
        ('flight-transformation','transform-in-flight',None,True,False)),
}


def number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def terrain_vulnerability(state,target):
    """Read nearby support. Thin-ground/ledge signals do not predict a fall.

    A height-only surface has no lower boundary, so its thickness stays unknown.
    Sampling is bounded and uses world coordinates, independent of the camera.
    """
    unknown={'support_known':False,'weak_support':False,'reason':'unknown-support','thickness_px':None,'near_ledge_px':None}
    if not isinstance(state,dict) or not isinstance(target,dict) or not all(number(target.get(k)) for k in ('x','y')):return unknown
    terrain=state.get('terrain')
    if not isinstance(terrain,dict):return unknown
    if 'surface' in terrain and 'heights' not in terrain:terrain={**terrain,'heights':terrain['surface']}
    x,y=target['x'],target['y'];uncertain=[False]
    def occupied(px,py):
        try:return bool(solid(terrain,px,py))
        except (TypeError,ValueError,IndexError,KeyError,AttributeError,OverflowError):uncertain[0]=True;return None
    def support(px,base,reach=32):
        for offset in range(-6,reach+1):
            level=round(base)+offset;here=occupied(px,level);above=occupied(px,level-1)
            if here is None or above is None:return None
            if here and not above:return level
        return None
    center=support(x,y)
    if center is None:return unknown
    explicit_volume='heights' not in terrain and any(terrain.get(k) is not None for k in ('rows','runs','pixels','mask','polygon'))
    thickness=[]
    if explicit_volume:
        for offset in (-6,0,6):
            top=support(x+offset,y)
            if top is None:continue
            depth=0
            while depth<64:
                value=occupied(x+offset,top+depth)
                if value is None:return unknown
                if not value:break
                depth+=1
            # Reaching the cap is a lower bound, not a measured thin layer.
            if depth<64:thickness.append(depth)
    nearest=None
    for side in (-1,1):
        for distance in range(1,33):
            # Require support near the same foot level; a large drop is a ledge
            # observation, not a claim that the entire column is empty.
            if support(x+side*distance,center,8) is None:
                nearest=distance if nearest is None else min(nearest,distance);break
    if uncertain[0]:return unknown
    thin=min(thickness) if thickness else None
    weak=thin is not None and thin<=18 or nearest is not None and nearest<=12
    reason='thin-support' if thin is not None and thin<=18 else 'near-ledge' if nearest is not None and nearest<=12 else 'support-present'
    return {'support_known':True,'weak_support':bool(weak),'reason':reason,'support_y':center,'thickness_px':thin,'near_ledge_px':nearest,'thickness_source':'observed-volume' if thin is not None else 'unknown-or-deeper-than-scan'}


def _target(state,plan):
    players=state.get('players')
    if not isinstance(players,(list,tuple)):return None
    valid=[p for p in players if isinstance(p,dict) and all(number(p.get(k)) for k in ('x','y'))]
    hero=next((p for p in valid if str(p.get('id'))==str(state.get('heroId'))),None)
    if not hero:return None
    enemies=[p for p in valid if str(p.get('id'))!=str(hero.get('id')) and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
    if plan.get('target_id') is not None:return next((p for p in enemies if str(p.get('id'))==str(plan['target_id'])),None)
    target=plan.get('target');point=target if isinstance(target,(list,tuple)) and len(target)==2 and all(number(v) for v in target) else (hero['x'],hero['y'])
    return min(enemies,key=lambda p:math.dist((p['x'],p['y']),point),default=None)


def mobile_intent(mobile,shot,state=None,plan=None):
    """Explain a role/opportunity without making a shot legal or changing aim."""
    name=mobile_name(mobile);valid=isinstance(shot,int) and not isinstance(shot,bool) and shot in (0,1,2)
    row=ROLES.get(name,())[shot] if valid and name in ROLES else None
    if row is None:return {'mobile':name,'shot':shot if valid else None,'role':'unknown','intent':'needs-observation','reference_delay':None,'mechanism_pending':True,'authorizes_action':False,'source':GUIDE_URL}
    role,intent,delay,special,dig=row;state=state if isinstance(state,dict) else {};plan=plan if isinstance(plan,dict) else {}
    terrain=terrain_vulnerability(state,_target(state,plan));action=plan.get('action')
    if action=='abrir paso':intent='clear-line'
    elif action=='bunge' and terrain['weak_support']:intent='remove-support'
    return {'mobile':name,'shot':shot,'role':role,'intent':intent,'reference_delay':delay,'quick_reference':delay==250,'mechanism_pending':special,'candidate_goal':'bunge' if dig and terrain['weak_support'] else None,'terrain':terrain,'authorizes_action':False,'source':GUIDE_URL}
