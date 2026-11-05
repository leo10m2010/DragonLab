"""Target-specific empirical weapon choices; no invented damage tables."""
import math,statistics


def enemy_for(state,target=None):
    hero=next((p for p in state.get('players',[]) if str(p.get('id'))==str(state.get('heroId'))),None)
    if not hero:return None
    enemies=[p for p in state.get('players',[]) if str(p.get('id'))!=str(hero['id']) and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
    point=target or (hero['x'],hero['y'])
    return min(enemies,key=lambda p:math.hypot(p['x']-point[0],p['y']-point[1]),default=None)


def comparable(rows,episode,state,enemy):
    if not enemy:return []
    return [r for r in rows if r.get('episode')==episode and str(r.get('target_id'))==str(enemy['id'])
            and isinstance(r.get('wind'),(int,float)) and abs(r['wind']-state.get('wind',0))<=1
            and (not state.get('wind') or isinstance(r.get('wind_angle'),(int,float)) and abs((r['wind_angle']-state.get('windAngle',0)+180)%360-180)<=5)]


def damage_evidence(rows):
    values=[r['enemy_health_drop'] for r in rows if r.get('health_window_known') and isinstance(r.get('enemy_health_drop'),(int,float)) and not isinstance(r['enemy_health_drop'],bool) and math.isfinite(r['enemy_health_drop']) and r['enemy_health_drop']>=0]
    return statistics.mean(values) if len(values)>=3 else 0


def dual_decision(rows,remaining,enabled,shot,phase,*,under_pressure=False,trajectory_verified=False,verified_check_count=0):
    if not enabled:return False,'DD desactivado'
    if not isinstance(shot,int) or isinstance(shot,bool) or shot not in (0,1) or phase!='evaluation':return False,'DD requiere bala 1 o 2 con trayectoria comprobada'
    known_remaining=isinstance(remaining,(int,float)) and not isinstance(remaining,bool) and math.isfinite(remaining) and remaining>0
    damage=damage_evidence(rows)
    if known_remaining and damage>0 and remaining<=damage:return False,'Tiro normal suficiente según las mediciones'
    # A critical-life opportunity is distinct from a measured finishing claim.
    # The caller must establish low native HP and future native flight checks;
    # a catalog delay or damage range cannot satisfy either condition.
    checked=isinstance(verified_check_count,int) and not isinstance(verified_check_count,bool) and verified_check_count>=3
    if under_pressure is True and trajectory_verified is True and checked and known_remaining:
        return True,'DD de refuerzo: vida propia crítica y trayectoria comprobada; no garantiza remate'
    if not known_remaining:return False,'DD reservado: falta medir daño o vida'
    errors=[r['path_error_px'] for r in rows if isinstance(r.get('path_error_px'),(int,float)) and not isinstance(r['path_error_px'],bool) and math.isfinite(r['path_error_px'])]
    if len(errors)<5 or sum(e<=20 for e in errors)/len(errors)<.8:return False,'DD reservado: falta precisión comprobada'
    if damage<=0 or remaining is None:return False,'DD reservado: falta medir daño o vida'
    if remaining<=damage:return False,'Tiro normal suficiente según las mediciones'
    # A bounded opportunity to finish; this is a heuristic, not a damage guarantee.
    if remaining>damage*1.8:return False,'DD reservado: baja oportunidad de terminar el objetivo'
    return True,'DD: oportunidad de terminar el objetivo con precisión comprobada'
