"""Shadow launch fits, independent future observations and reversible promotion."""
import math,time,json,hashlib
from calibration_validation import current_fit
from wind_models import acceleration as wind_acceleration

def sample_id(sample):
    return sample.get('sample_id') or hashlib.sha256(json.dumps(sample,sort_keys=True).encode()).hexdigest()[:24]

def errors(fit,sample):
    if not fit:return None
    k=fit.get('wind_scale')
    if sample['wind'] and (k is None or not fit.get('wind_observed')):return None
    ax,ay=wind_acceleration(fit,sample['wind'],sample['wind_angle'])
    speed=abs(math.hypot(sample['vx'],sample['vy'])-(fit['power_scale']*sample['power']+fit['speed_offset']))
    acceleration=math.hypot(sample['ax']-ax,sample['ay']-ay)
    path_error=None;duration=sample.get('duration_s')
    if sample.get('simple_trajectory') and isinstance(duration,(int,float)) and math.isfinite(duration) and 0<duration<=20:
        angle=math.atan2(-sample['vy'],sample['vx']);ds=fit['power_scale']*sample['power']+fit['speed_offset']-math.hypot(sample['vx'],sample['vy'])
        dax=ax-sample['ax'];day=ay-sample['ay']
        path_error=max(math.hypot(ds*math.cos(angle)*t+.5*dax*t*t,-ds*math.sin(angle)*t+.5*day*t*t) for t in (duration*i/8 for i in range(1,9)))
    return {'speed':speed,'acceleration':acceleration,'trajectory':path_error,'score':speed/5+acceleration/5+(path_error/12 if path_error is not None else 0)}

def good(value):return value is not None and value['speed']<=5 and value['acceleration']<=5 and (value.get('trajectory') is None or value['trajectory']<=12)

def update(record,sample):
    """Return an activated fit, or None. Training never counts as future evidence."""
    ident=sample_id(sample);active=record.get('fit');e=errors(active,sample)
    if active and e is not None:
        failures=record.setdefault('active_failures',[])
        if good(e):failures.clear();record.pop('drift_pending',None)
        elif not any(x['id']==ident for x in failures):
            failures.append({'id':ident,'sample':sample,'error':e});record['active_failures']=failures[-3:]
            if len(failures)>=3:
                fallback=record.get('rollback_fit')
                if fallback and all(good(errors(fallback,x['sample'])) for x in failures):
                    record['fit']=fallback;record.pop('rollback_fit',None);record.pop('candidate',None);record.pop('drift_pending',None);record['active_failures']=[]
                    record['status']='Ajuste anterior recuperado';return fallback
                record['drift_pending']=[x['sample'] for x in failures[-3:]]
    candidate=record.get('candidate')
    if candidate and ident not in candidate['training_ids'] and not any(x['id']==ident for x in candidate['validation']):
        candidate_error=errors(candidate['fit'],sample)
        if candidate_error is not None:
            candidate['validation'].append({'id':ident,'power':sample['power'],'candidate':candidate_error,'baseline':errors(active,sample)})
            candidate['validation']=candidate['validation'][-8:]
        values=candidate['validation'];powers=[x['power'] for x in values]
        if len(values)>=3 and len(set(powers))>=2 and max(powers)-min(powers)>=40:
            passed=all(good(x['candidate']) for x in values)
            comparable=all(x['baseline'] is not None for x in values)
            improvement=not active or comparable and sum(x['candidate']['score'] for x in values)+.05<.95*sum(x['baseline']['score'] for x in values)
            if passed and improvement:
                if active:
                    record['rollback_fit']=dict(active)
                    archive=record.setdefault('previous_regimes',[])
                    archive.append({'fit':dict(active),'reason':'Replaced after independent future validation','archived':time.time()});record['previous_regimes']=archive[-8:]
                checked_ids=set(candidate['training_ids'])|{x['id'] for x in values}
                checked=[x for x in record.get('samples',[]) if sample_id(x) in checked_ids]
                if checked:
                    candidate['fit']['wind_range']=[min(x['wind'] for x in checked),max(x['wind'] for x in checked)]
                    candidate['fit']['power_range']=[min(x['power'] for x in checked),max(x['power'] for x in checked)]
                    candidate['fit']['validation_count']=len(values)
                record['fit']=candidate['fit'];record['accepted_validation']=values;record.pop('candidate',None);record.pop('drift_pending',None);record['active_failures']=[]
                record['status']='Ajuste validado con tiros nuevos';return record['fit']
            record.pop('candidate',None);record['status']='Ajuste actual conservado' if active else 'Aprendiendo: prueba independiente fallida'
            return None
    if not record.get('candidate'):
        try:fit,cut=current_fit(record.get('samples',[]))
        except ValueError:return None
        if active and fit.get('wind_mode','smooth')==active.get('wind_mode','smooth') and all(abs((fit.get(k) or 0)-(active.get(k) or 0))<1e-8 for k in ('power_scale','speed_offset','gravity','wind_scale')):return None
        training=record['samples'][cut:]
        record['candidate']={'fit':fit,'training_ids':[sample_id(x) for x in training],'validation':[],'created':time.time()}
        record['status']='Aprendiendo: comprobando ajuste nuevo'
    return None
