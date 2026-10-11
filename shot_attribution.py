"""Reject ambiguous shooters and stale power from another player's turn."""
import math

def identity(shot):return str(shot.get('id'))+':'+str(shot.get('start'))

def attributed_start(state,shot,release=None):
    start=shot.get('start');elapsed=shot.get('elapsed')
    if not shot.get('native') or shot.get('auxiliary') or shot.get('delay',0):return None
    if not isinstance(start,list) or len(start)!=6 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in start):return None
    if not isinstance(elapsed,(int,float)) or not 0<=elapsed<=600:return None
    hero=next((p for p in state.get('players',[]) if p.get('id')==state.get('heroId')),None)
    if not hero:return None
    metadata=shot.get('metadata') or {};owner=metadata.get('player_n',metadata.get('player'))
    if owner is not None and str(owner)!=str(hero['id']):return None
    players=[p for p in state.get('players',[]) if all(isinstance(p.get(k),(int,float)) and math.isfinite(p[k]) for k in ('x','y'))]
    distances=sorted((math.hypot(p['x']-start[0],p['y']-start[1]),str(p['id'])) for p in players)
    if not distances or math.hypot(hero['x']-start[0],hero['y']-start[1])>90:return None
    if owner is None and (distances[0][1]!=str(hero['id']) or len(distances)>1 and distances[1][0]-distances[0][0]<60):return None
    if metadata.get('mobile') is not None and str(metadata['mobile'])!=str(hero.get('mobile')):return None
    explicit=release and release.get('hero')==hero['id'] and identity(shot) not in release.get('baseline',[]) and math.dist((release['x'],release['y']),(hero['x'],hero['y']))<1
    if explicit and release.get('projectile') is not None and release['projectile']!=identity(shot):explicit=False
    own_turn=str(state.get('activePlayer'))==str(hero['id'])
    power=metadata.get('power') if owner is not None else None
    if power is None:power=release.get('power') if explicit else state.get('currentPower') if own_turn else None
    kind=shot.get('shotType')
    if kind not in (0,1,2):kind=release.get('shot') if explicit else state.get('selectedShot') if own_turn else None
    if not isinstance(power,(int,float)) or not math.isfinite(power) or not 1<=power<=400 or kind not in (0,1,2):return None
    return {'hero':hero,'power':power,'shot':kind,'start':start,'wind':release.get('wind') if explicit else state.get('wind'),'windAngle':release.get('windAngle') if explicit else state.get('windAngle'),'learnable':bool(explicit or own_turn),'source':'confirmed-release' if explicit else 'native-metadata' if owner is not None and metadata.get('power') is not None else 'own-turn-ui'}
