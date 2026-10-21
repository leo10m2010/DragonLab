"""Small active-learning curriculum; never treats attempts as validated fits."""
import math
from calibration_book import mobile_name
POWERS=(100,300,180,360,120,320,220)
ANGLES=(55,35,75)

def wind_bin(wind):
    if not isinstance(wind,(int,float)) or not math.isfinite(wind) or wind<0:raise ValueError('Viento inválido')
    return min(10,int(wind//10))

def next_probe(records,mobile,wind,attempts=0,available=(0,1,2)):
    mobile=mobile_name(mobile)
    if not mobile:raise ValueError('Carro sin identificar')
    if not available:raise ValueError('No hay tiros disponibles')
    band=wind_bin(wind)
    def score(mode):
        r=records.get(f'dragonbound:{mobile}:{mode}',{})
        validation=r.get('candidate',{}).get('validation',[])
        samples=validation if r.get('candidate') else r.get('samples',[])+r.get('training_patterns',[])
        # Future validation gets priority; measured modes still need wind coverage.
        coverage=sum(wind_bin(s.get('wind',wind))==band for s in r.get('samples',[])+r.get('training_patterns',[]))
        return (0 if r.get('candidate') else 1 if not r.get('fit') else 2,coverage,len(samples),mode)
    mode=min(available,key=score);r=records.get(f'dragonbound:{mobile}:{mode}',{})
    seen=[s.get('power') for s in r.get('candidate',{}).get('validation',[]) or r.get('samples',[])+r.get('training_patterns',[])]
    power=min(POWERS,key=lambda p:(sum(abs(p-q)<=12 for q in seen),-min((abs(p-q) for q in seen),default=400),(POWERS.index(p)-attempts)%len(POWERS))) if seen else POWERS[attempts%len(POWERS)]
    return {'mobile':mobile,'shot':mode,'power':power,'angle':ANGLES[attempts%len(ANGLES)],'wind_band':band,'purpose':'validación independiente' if r.get('candidate') else 'ampliar viento' if r.get('fit') else 'medir salida'}

def next_mobile(options,attempted):
    options=[o for o in options if mobile_name(o.get('name')) and o.get('name')!='Random']
    return min(options,key=lambda o:(attempted.get(mobile_name(o['name']),0),o.get('id',999))) if options else None
