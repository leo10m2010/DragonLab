"""Bounded launch correction for provisional practice, never held-out tests."""
import math


def corrected_hypothesis(model,record,episode,state,player):
    if not model or record.get('multi_projectile') or state.get('weather'):return None
    samples=record.get('samples',[])
    if not samples:return None
    sample=samples[-1]
    if sample.get('episode')!=episode or not sample.get('simple'):return None
    values=[sample.get(k) for k in ('power','speed','ax','ay','wind','wind_angle','raw_angle')]
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):return None
    if sample['power']<40 or abs(sample['raw_angle']-player['rawAngle'])>2:return None
    if sample.get('pose')!={k:player.get(k) for k in ('look','body','minAngle','maxAngle')}:return None
    if abs(sample['wind']-state['wind'])>1 or state['wind'] and abs((sample['wind_angle']-state['windAngle']+180)%360-180)>5:return None
    k=model['wind_scale']
    if k is None and state['wind']:return None
    r=math.radians(sample['wind_angle']);k=k or 0
    if math.hypot(sample['ax']-k*sample['wind']*math.cos(r),sample['ay']-(model['gravity']-k*sample['wind']*math.sin(r)))>5:return None
    # Infer gain from observed launch speed, not from an impact on a wall.
    scale=(sample['speed']-model['offset'])/sample['power']
    if not .85<=scale/model['scale']<=1.15:return None
    return {**model,'scale':scale,'source':'provisional-launch-feedback','feedback_id':sample.get('id')}
