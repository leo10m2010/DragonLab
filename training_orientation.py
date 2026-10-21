"""Direction from observed native angle ranges, without vehicle-specific physics."""
import math

def heading(raw,body,look):return raw-body if look==1 else 180-raw-body
def raw_angle(elevation,body,look,target_right):
    world=elevation if target_right else 180-elevation
    return world+body if look==1 else 180-world-body
def desired_look(player,target_right):
    low=player.get('baseMinAngle',player.get('minAngle',player.get('rawAngle')))
    high=player.get('baseMaxAngle',player.get('maxAngle',player.get('rawAngle')))
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (low,high)):raise RuntimeError('Sin rango nativo para orientar el carro')
    middle=(low+high)/2;body=player.get('body',0);direction=1 if target_right else -1
    return max((0,1),key=lambda look:direction*math.cos(math.radians(heading(middle,body,look))))

def up_increases_raw(player):
    low=player.get('baseMinAngle',player.get('minAngle',player.get('rawAngle')))
    high=player.get('baseMaxAngle',player.get('maxAngle',player.get('rawAngle')))
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (low,high)):raise RuntimeError('Sin lectura del rango de ángulo')
    return math.cos(math.radians((low+high)/2))>=0
