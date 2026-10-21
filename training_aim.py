"""Guided training uses the same solver and settings as the visible laboratory."""
from dataclasses import replace
import math,time
from core import solve

class NoAim(RuntimeError):
    def __init__(self,message,reposition=False):
        super().__init__(message);self.reposition=bool(reposition)

def terrain_solution(settings,result):
    power=result.get('guide_power')
    if not result.get('blocked') or not isinstance(power,(int,float)) or not math.isfinite(power) or not 1<=power<=settings.max_power:return None
    paths=result.get('preview_paths') or []
    if not paths or not paths[0]:return None
    end=paths[0][-1][:2]
    if len(end)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in end):return None
    origin=(settings.hero_x,settings.hero_y);target=(settings.target_x,settings.target_y)
    if math.dist(origin,end)<60 or math.dist(end,target)>=math.dist(origin,target)-10:return None
    return {**result,'power':power,'end':end,'training_action':'abrir paso','approximate':True}

def approximate_solution(settings,result):
    if result.get('blocked'):return terrain_solution(settings,result)
    power=result.get('power');end=result.get('end')
    if not isinstance(power,(int,float)) or not math.isfinite(power) or not 1<=power<=settings.max_power or not isinstance(end,(list,tuple)) or len(end)<2:return None
    end=end[:2]
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in end):return None
    origin=(settings.hero_x,settings.hero_y);target=(settings.target_x,settings.target_y)
    if math.dist(origin,end)<60 or math.dist(end,target)>=math.dist(origin,target)-10:return None
    return {**result,'end':end,'training_action':'aproximar','approximate':True}

def choose_aim(settings,preferred,limits=None,allow_blocked=False):
    angles=[preferred,35,45,55,65,75,25,80,settings.angle]
    if limits:angles=[max(limits[0],min(limits[1],a)) for a in angles]
    angles=list(dict.fromkeys(angles))
    blocked=[];deadline=time.monotonic()+1.5
    for angle in angles:
        if time.monotonic()>deadline:break
        snapshot=replace(settings,angle=angle,launch_offset=None);result=solve(snapshot)
        if result.get('reachable') and not result.get('blocked') and isinstance(result.get('power'),(int,float)) and 1<=result['power']<=settings.max_power:
            return angle,result
        if allow_blocked:
            candidate=approximate_solution(snapshot,result)
            if candidate:blocked.append((angle,candidate))
    if blocked:return min(blocked,key=lambda item:math.dist(item[1]['end'],(settings.target_x,settings.target_y)))
    raise NoAim('El Lab no encontró un tiro libre hacia el objetivo')

def actual_solution(settings,allow_blocked=False):
    result=solve(settings)
    if allow_blocked:
        candidate=approximate_solution(settings,result)
        if candidate:return candidate
    if not result.get('reachable') or result.get('blocked') or not isinstance(result.get('power'),(int,float)) or not math.isfinite(result['power']) or not 1<=result['power']<=settings.max_power:
        raise NoAim('El ángulo real no permite un tiro válido del Lab; no se carga')
    return result
