"""Passive confirmation after release; never retries or injects an input."""
import math,time
from shot_attribution import identity,attributed_start

def wait_for_shot(reader,plan,result,cancel,timeout=2.5):
    baseline={identity(s) for s in reader.initial.get('shots',[])};deadline=time.monotonic()+timeout
    release={'hero':plan['hero'],'x':plan['heroState']['x'],'y':plan['heroState']['y'],'power':result['power'],'shot':plan['shot'],'wind':plan.get('wind'),'windAngle':plan.get('windAngle'),'baseline':list(baseline)}
    while time.monotonic()<deadline and not cancel.is_set():
        state=reader.client.sample()
        candidates=[]
        for shot in state.get('shots',[]):
            if identity(shot) in baseline:continue
            attribution=attributed_start(state,shot,release)
            if attribution and attribution['shot']==plan['shot']:candidates.append((shot,attribution))
        if candidates:
            starts={tuple(s['start']) for s,a in candidates}
            if len(starts)!=1:return {'status':'ambiguous','reason':'Varios proyectiles distintos; fuerza no atribuida'}
            shot,a=candidates[0]
            # Native metadata has precedence. The UI is meaningful only while
            # this player still owns the turn; otherwise keep it unconfirmed.
            native_power=(shot.get('metadata') or {}).get('power')
            measured=native_power if native_power is not None else state.get('currentPower') if str(state.get('activePlayer'))==str(plan['hero']) else None
            if not isinstance(measured,(int,float)) or not math.isfinite(measured):
                return {'status':'observed','projectile':identity(shot),'reason':'Proyectil observado; fuerza final no disponible'}
            expected_speed=plan.get('expectedSpeed');launch_consistent=isinstance(expected_speed,(int,float)) and abs(shot['start'][3]-expected_speed)<=5
            if native_power is None and measured==result['power']==plan['power'] and not launch_consistent:
                return {'status':'observed','projectile':identity(shot),'observedPower':measured,'reason':'Barra confirmada y proyectil observado; falta una salida calibrada para contrastar su fuerza'}
            status='confirmed' if measured==result['power']==plan['power'] else 'mismatch'
            release['projectile']=identity(shot)
            return {'status':status,'evidence':'native-power' if native_power is not None else 'bar-and-measured-launch' if launch_consistent else 'bar-mismatch','requestedPower':plan['power'],'releasedPower':result['power'],'actualPower':measured,'projectile':identity(shot),'start':shot['start'],'shot':a['shot'],'release':release}
        time.sleep(.06)
    return {'status':'unconfirmed','reason':'No se pudo observar un proyectil atribuible; no se repite el tiro'}
