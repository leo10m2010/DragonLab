"""Randomizer observations are projectile variants, never one fixed vehicle fit."""
import math

def record_variant(record,shot,release):
    start=shot.get('start');bullet=shot.get('bulletId')
    if not isinstance(start,list) or len(start)!=6 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in start):return False
    record['variable_projectiles']=True
    variants=record.setdefault('projectile_variants',{});key=str(bullet) if isinstance(bullet,(int,float)) else 'unidentified'
    rows=variants.setdefault(key,[]);ident=str(shot.get('id'))+':'+str(start)
    if any(row['id']==ident for row in rows):return False
    rows.append({'id':ident,'bullet_id':bullet,'power':release.get('power'),'start':start,'wind':release.get('wind'),'wind_angle':release.get('windAngle'),'identity_timing':'after-release','predictable_before_release':False})
    variants[key]=rows[-48:];record['status']='Arma variable: proyectil previo al tiro sin identificar'
    return True
