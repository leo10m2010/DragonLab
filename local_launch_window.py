"""A current-match, closed force/time window, not a global launch model.

Short-range shots sometimes cannot produce a 40-point force span. A narrow
window is admitted only after separate later native checks and is never
extrapolated. The residual envelope includes one native speed/acceleration
unit for quantization; its guarantee is conditional on the tested affine
launch regime, not an assurance of impact, damage, or continued game physics.
"""
import ast,math,statistics
from wind_models import acceleration,components,domain,fit_acceleration,supported

MAX_ROWS=96
MAX_TRAINING=8
MIN_TRAINING_SPAN=12
MAX_PARAMETER_ERROR=2
MAX_FLIGHT_ERROR=5
OWN_SOURCES={'confirmed-release','owned-native','owned-native-launch'}
SPECIAL_FLAGS=('multi_projectile','variable_projectiles','special_continuation_pending',
               'intrinsic_pattern','patterns','observed_phases','prefix_only')


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def _native_identity(row):
    """Older own rows have no source field, but bind their native start tuple."""
    ident=row.get('id')
    if not isinstance(ident,str) or not ident or len(ident)>2048 or ident.startswith(('seed:','prefix:')):return False
    source=row.get('source')
    if source is not None:return source in OWN_SOURCES
    try:
        prefix,encoded=ident.split(':',1)
        if not prefix or prefix=='None':return False
        start=ast.literal_eval(encoded)
    except (ValueError,SyntaxError,TypeError,MemoryError,RecursionError):return False
    return (isinstance(start,list) and len(start)==6 and all(number(v) for v in start)
            and all(abs(start[index]-row[name])<=1e-7 for index,name in ((2,'heading'),(3,'speed'),(4,'ax'),(5,'ay'))))


def _eligible(row,episode):
    if not isinstance(row,dict) or row.get('episode')!=episode or row.get('simple') is not True:return False
    if not all(number(row.get(k)) for k in ('power','speed','ax','ay','wind','wind_angle','heading','duration_s')):return False
    if not 1<=row['power']<=400 or row['speed']<0 or not 0<row['duration_s']<=20 or not 0<=row['wind']<=100:return False
    return _native_identity(row)


def _rows(record,episode):
    raw=record.get('samples')
    if not isinstance(raw,list):return []
    unique={};rows=[]
    for row in raw[-MAX_ROWS:]:
        if not _eligible(row,episode):continue
        ident=row['id']
        if ident in unique:
            # A duplicate cannot supply another held-out check; contradictory
            # duplicates cannot be resolved by selecting the favorable copy.
            if any(row[k]!=unique[ident][k] for k in ('power','speed','ax','ay','wind','wind_angle','heading','duration_s')):return []
            continue
        unique[ident]=row;rows.append(row)
    return rows


def _training_model(training):
    powers=[s['power'] for s in training];pbar=statistics.mean(powers)
    sxx=sum((p-pbar)**2 for p in powers)
    if not sxx:return None
    vbar=statistics.mean(s['speed'] for s in training)
    scale=sum((s['power']-pbar)*(s['speed']-vbar) for s in training)/sxx
    offset=vbar-scale*pbar
    if not .01<scale<30:return None
    # Pick the wind representation using training rows only. Later checks
    # cannot select whichever representation happens to fit their outcomes.
    fits=[fit_acceleration(training,mode=m) for m in ('smooth','floor')]
    fits=[f for f in fits if f is not None]
    if not fits:return None
    fits.sort(key=lambda f:(f['acceleration_rmse'],f['wind_mode']!='smooth'))
    best=fits[0]
    model={'scale':scale,'offset':offset,**best,'count':len(training),'source':'owned-native-local-window'}
    if max(_parameter_error(model,s) for s in training)>MAX_PARAMETER_ERROR:return None
    return model


def _parameter_error(model,row):
    if model.get('wind_scale') is None and row['wind']:return math.inf
    ax,ay=acceleration(model,row['wind'],row['wind_angle'])
    return max(abs(model['scale']*row['power']+model['offset']-row['speed']),math.hypot(ax-row['ax'],ay-row['ay']))


def _flight_error(model,row):
    if model.get('wind_scale') is None and row['wind']:return math.inf
    ax,ay=acceleration(model,row['wind'],row['wind_angle']);angle=math.radians(row['heading'])
    ds=model['scale']*row['power']+model['offset']-row['speed']
    dx,dy=ax-row['ax'],ay-row['ay'];duration=row['duration_s']
    return max(math.hypot(ds*math.cos(angle)*t+.5*dx*t*t,-ds*math.sin(angle)*t+.5*dy*t*t) for t in (duration*i/8 for i in range(1,9)))


def _uncertainty(model,training,power_range,wind,angle,horizon):
    """Deterministic OLS sensitivity to bounded per-observation quantization.

    An affine least-squares speed at p is a weighted sum of observed speeds.
    Sum(abs(weights)) therefore bounds propagation of each speed-unit error.
    Acceleration has the analogous one-coupling/intercept sensitivity. We
    include observed training residuals in addition to one native unit.
    """
    n=len(training);pbar=statistics.mean(s['power'] for s in training)
    sxx=sum((s['power']-pbar)**2 for s in training)
    residual=max(abs(model['scale']*s['power']+model['offset']-s['speed']) for s in training)
    speed_bound=(1+residual)*max(sum(abs(1/n+(p-pbar)*(s['power']-pbar)/sxx) for s in training) for p in power_range)
    xy=[components(s['wind'],s['wind_angle'],model['wind_mode']) for s in training]
    ybar=statistics.mean(y for _,y in xy);denominator=sum(x*x+(y-ybar)**2 for x,y in xy)
    residual_a=max(max(abs(a-b) for a,b in zip(acceleration(model,s['wind'],s['wind_angle']),(s['ax'],s['ay']))) for s in training)
    quantum=1+residual_a;x,y=components(wind,angle,model['wind_mode'])
    if denominator<=1e-6:
        if x or y:return None
        accel_bound=quantum
    else:
        coupling_bound=quantum*sum(abs(x0)+abs(y0-ybar) for x0,y0 in xy)/denominator
        accel_bound=math.hypot(abs(x)*coupling_bound,quantum+abs(ybar-y)*coupling_bound)
    flight_bound=speed_bound*horizon+.5*accel_bound*horizon*horizon
    return speed_bound,accel_bound,flight_bound


def validated_window(record,episode,wind,wind_angle):
    """Return a strictly local proof after >=3 training and >=3 future shots."""
    if not isinstance(record,dict) or any(record.get(k) for k in SPECIAL_FLAGS):return None
    if not isinstance(episode,str) or not episode or not number(wind) or not 0<=wind<=100 or not number(wind_angle):return None
    rows=_rows(record,episode)
    if len(rows)<6:return None
    # A later coherent regime may replace an earlier one only after its own
    # new future checks. At most 24 recent rows and eight training rows fit.
    for start in range(max(0,len(rows)-24),len(rows)-5):
        end=next((cut for cut in range(start+3,min(start+MAX_TRAINING,len(rows)-3)+1)
                  if len({s['power'] for s in rows[start:cut]})>=3
                  and max(s['power'] for s in rows[start:cut])-min(s['power'] for s in rows[start:cut])>=MIN_TRAINING_SPAN),None)
        if end is None:continue
        training=rows[start:end];future=rows[end:]
        if len(future)<3 or len({s['power'] for s in future})<2:continue
        model=_training_model(training)
        if not model:continue
        if any(_parameter_error(model,s)>MAX_PARAMETER_ERROR or _flight_error(model,s)>MAX_FLIGHT_ERROR for s in future):continue
        power_range=[min(s['power'] for s in future),max(s['power'] for s in future)]
        train_range=[min(s['power'] for s in training),max(s['power'] for s in training)]
        if not train_range[0]<=power_range[0]<=power_range[1]<=train_range[1]:continue
        # Domain belongs to later checks, not to an untested historical fit.
        model={**model,'wind_domain':domain(future,model['wind_mode'])}
        if not supported(model,wind,wind_angle,margin=0):continue
        horizon=min(s['duration_s'] for s in future)
        uncertainty=_uncertainty(model,training,power_range,wind,wind_angle,horizon)
        if uncertainty is None or uncertainty[0]>MAX_PARAMETER_ERROR or uncertainty[2]>MAX_FLIGHT_ERROR:continue
        return {'model':model,'episode':episode,'limited':True,'scope':'local-power-flight-window',
                'training_ids':[s['id'] for s in training],'validation_ids':[s['id'] for s in future],
                'power_range':power_range,'training_power_range':train_range,
                'max_flight_seconds':horizon,'max_flight_error_px':max(_flight_error(model,s) for s in future),
                'max_parameter_error':max(_parameter_error(model,s) for s in future),
                'speed_uncertainty_bound':uncertainty[0],'acceleration_uncertainty_bound':uncertainty[1],
                'uncertainty_wind_features':list(components(wind,wind_angle,model['wind_mode'])),
                'flight_uncertainty_bound_px':uncertainty[2],'full_autonomy_proven':False,
                'source':'current-episode-independent-native-checks'}
    return None


def supports_window(proof,power,duration,wind,wind_angle,episode=None):
    """Caller-side force/time/domain check: closed interval, no extrapolation."""
    if not isinstance(proof,dict) or proof.get('limited') is not True or proof.get('scope')!='local-power-flight-window':return False
    if episode is not None and proof.get('episode')!=episode:return False
    if not all(number(v) for v in (power,duration,wind,wind_angle)) or duration<=0:return False
    bounds=proof.get('power_range');horizon=proof.get('max_flight_seconds')
    if not isinstance(bounds,list) or len(bounds)!=2 or not all(number(v) for v in bounds) or not number(horizon):return False
    if not bounds[0]<=power<=bounds[1] or duration>horizon:return False
    try:
        features=components(wind,wind_angle,proof['model']['wind_mode'])
        evaluated=proof.get('uncertainty_wind_features')
        if not isinstance(evaluated,list) or len(evaluated)!=2 or any(abs(a-b)>1e-7 for a,b in zip(features,evaluated)):return False
        return supported(proof['model'],wind,wind_angle,margin=0)
    except (KeyError,TypeError,ValueError,OverflowError):return False
