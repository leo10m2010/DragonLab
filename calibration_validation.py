"""Independent leave-one-out validation for measured launch parameters."""
import math
from physics_extensions import fit_calibration

def validated_fit(samples):
    for s in samples:
        if not isinstance(s,dict) or not all(isinstance(s.get(k),(int,float)) and math.isfinite(s[k]) for k in ('power','vx','vy','ax','ay','wind','wind_angle')):raise ValueError('Muestra incompleta o no finita')
        if not 1<=s['power']<=400 or not 0<=s['wind']<=100:raise ValueError('Fuerza o viento fuera de rango')
    powers=[s['power'] for s in samples]
    if len(samples)<4 or len(set(powers))<3 or max(powers)-min(powers)<40:raise ValueError('Faltan tiros con fuerzas suficientemente distintas')
    fit=fit_calibration(samples);speeds=[];accelerations=[]
    for i,measurement in enumerate(samples):
        training=samples[:i]+samples[i+1:]
        try:trial=fit_calibration(training)
        except ValueError:continue
        speeds.append(abs(math.hypot(measurement['vx'],measurement['vy'])-(trial['power_scale']*measurement['power']+trial['speed_offset'])))
        wx=measurement['wind']*math.cos(math.radians(measurement['wind_angle']));wy=measurement['wind']*math.sin(math.radians(measurement['wind_angle']))
        if trial['wind_scale'] is not None or measurement['wind']==0:
            k=trial['wind_scale'] or 0;accelerations.append(math.hypot(measurement['ax']-k*wx,measurement['ay']-(trial['gravity']-k*wy)))
    fit['holdout_speed_error']=max(speeds) if speeds else None
    fit['holdout_acceleration_error']=max(accelerations) if accelerations else None
    if fit['speed_rmse']>3 or fit['acceleration_max_error']>5 or (speeds and max(speeds)>5) or (accelerations and max(accelerations)>5):raise ValueError('Las muestras no pasan la comprobación independiente de velocidad y viento')
    return fit

def current_fit(samples):
    """Recover from older regimes only after six contiguous validated shots.

    No individual outlier is discarded: only an entire historical prefix may
    be archived. Choose the longest consistent recent suffix, preserving it
    for validation and retaining the excluded observations in the book.
    """
    try:return validated_fit(samples),0
    except ValueError as original:
        for cut in range(1,len(samples)-5):
            try:return validated_fit(samples[cut:]),cut
            except ValueError:continue
        raise original
