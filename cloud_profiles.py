"""Use a shared fit only when local observations identify a compatible regime."""
import math
def compatible_fit(profiles,book,clone,mobile,shot,wind):
    record=book.records.get(f'{clone}:{mobile}:{shot}',{})
    if record.get('drift_pending'):return None
    samples=[s for s in record.get('samples',[]) if s.get('wind')==0]
    if wind!=0 or not samples:return None
    recent=samples[-1]
    for profile in sorted(profiles,key=lambda p:p.get('id',0),reverse=True):
        fit=profile.get('fit',{})
        if fit.get('wind_mode','smooth') not in ('smooth','floor'):continue
        if (profile.get('clone'),profile.get('mobile'),profile.get('shot'))!=(clone,mobile,shot):continue
        if not all(isinstance(fit.get(k),(int,float)) and math.isfinite(fit[k]) for k in ('gravity','power_scale','speed_offset')):continue
        if abs(fit['gravity']-recent['ay'])>1:continue
        if abs(fit['power_scale']*recent['power']+fit['speed_offset']-math.hypot(recent['vx'],recent['vy']))>3:continue
        return fit
    return None
