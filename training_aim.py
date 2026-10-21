"""Guided training uses the same solver and settings as the visible laboratory."""
from dataclasses import replace
import math
from core import solve

class NoAim(RuntimeError):pass

def choose_aim(settings,preferred,limits=None):
    angles=[preferred,35,45,55,65,75,25,80,settings.angle]
    if limits:angles=[max(limits[0],min(limits[1],a)) for a in angles]
    angles=list(dict.fromkeys(angles))
    for angle in angles:
        result=solve(replace(settings,angle=angle,launch_offset=None))
        if result.get('reachable') and not result.get('blocked') and isinstance(result.get('power'),(int,float)) and 1<=result['power']<=settings.max_power:
            return angle,result
    raise NoAim('El Lab no encontró un tiro libre hacia el objetivo')

def actual_solution(settings):
    result=solve(settings)
    if not result.get('reachable') or result.get('blocked') or not isinstance(result.get('power'),(int,float)) or not math.isfinite(result['power']) or not 1<=result['power']<=settings.max_power:
        raise NoAim('El ángulo real no permite un tiro válido del Lab; no se carga')
    return result
