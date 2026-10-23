"""Wind features selected from measured launches, shared by fit and prediction."""
import math,statistics


def components(wind,angle,mode='smooth'):
    radians=math.radians(angle%360)
    x,y=wind*math.cos(radians),wind*math.sin(radians)
    if mode=='floor':return math.floor(x),math.floor(y)
    if mode!='smooth':raise ValueError('Modelo de viento desconocido')
    return x,y


def acceleration(model,wind,angle):
    x,y=components(wind,angle,model.get('wind_mode','smooth'))
    k=model.get('wind_scale') or 0
    return k*x,model['gravity']-k*y


def domain(samples,mode='smooth'):
    values=[components(s['wind'],s['wind_angle'],mode) for s in samples]
    return [min(p[0] for p in values),max(p[0] for p in values),min(p[1] for p in values),max(p[1] for p in values)] if values else None


def supported(model,wind,angle,margin=1):
    bounds=model.get('wind_domain')
    if not bounds:return False
    x,y=components(wind,angle,model.get('wind_mode','smooth'))
    return bounds[0]-margin<=x<=bounds[1]+margin and bounds[2]-margin<=y<=bounds[3]+margin


def fit_acceleration(samples,mode=None):
    if not samples:return None
    choices=[]
    for kind in ([mode] if mode else ['smooth','floor'] if len(samples)>=4 else ['smooth']):
        xy=[components(s['wind'],s['wind_angle'],kind) for s in samples]
        xs=[p[0] for p in xy];ys=[p[1] for p in xy]
        ybar=statistics.mean(ys);abar=statistics.mean(s['ay'] for s in samples)
        denominator=sum(x*x for x in xs)+sum((y-ybar)**2 for y in ys)
        coupling=(sum(x*s['ax'] for x,s in zip(xs,samples))-sum((y-ybar)*(s['ay']-abar) for y,s in zip(ys,samples)))/denominator if denominator>1e-6 else None
        if coupling is None and any(s['wind'] for s in samples):continue
        gravity=abar+(coupling or 0)*ybar
        if not 0<gravity<10000 or coupling is not None and not 0<=coupling<100:continue
        errors=[math.hypot((coupling or 0)*x-s['ax'],gravity-(coupling or 0)*y-s['ay']) for x,y,s in zip(xs,ys,samples)]
        choices.append({'gravity':gravity,'wind_scale':coupling,'wind_mode':kind,'wind_domain':domain(samples,kind),'acceleration_rmse':math.sqrt(statistics.mean(e*e for e in errors)),'acceleration_max_error':max(errors)})
    if not choices:return None
    smooth=next((c for c in choices if c['wind_mode']=='smooth'),None)
    floor=next((c for c in choices if c['wind_mode']=='floor'),None)
    if smooth and floor:
        return floor if floor['acceleration_rmse']+.15<.8*smooth['acceleration_rmse'] else smooth
    return choices[0]
