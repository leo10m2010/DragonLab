"""Shadow launch fits, independent future observations and reversible promotion."""
import math,time,json,hashlib
from calibration_validation import current_fit

def sample_id(sample):
    return sample.get('sample_id') or hashlib.sha256(json.dumps(sample,sort_keys=True).encode()).hexdigest()[:24]

def errors(fit,sample):
    if not fit:return None
    k=fit.get('wind_scale')
    if sample['wind'] and (k is None or not fit.get('wind_observed')):return None
    k=k or 0;a=math.radians(sample['wind_angle'])
    speed=abs(math.hypot(sample['vx'],sample['vy'])-(fit['power_scale']*sample['power']+fit['speed_offset']))
    acceleration=math.hypot(sample['ax']-k*sample['wind']*math.cos(a),sample['ay']-(fit['gravity']-k*sample['wind']*math.sin(a)))
    return {'speed':speed,'acceleration':acceleration,'score':speed/5+acceleration/5}

def good(value):return value is not None and value['speed']<=5 and value['acceleration']<=5

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
                record['fit']=candidate['fit'];record['accepted_validation']=values;record.pop('candidate',None);record.pop('drift_pending',None);record['active_failures']=[]
                record['status']='Ajuste validado con tiros nuevos';return record['fit']
            record.pop('candidate',None);record['status']='Ajuste actual conservado' if active else 'Aprendiendo: prueba independiente fallida'
            return None
    if not record.get('candidate'):
        try:fit,cut=current_fit(record.get('samples',[]))
        except ValueError:return None
        if active and all(abs((fit.get(k) or 0)-(active.get(k) or 0))<1e-8 for k in ('power_scale','speed_offset','gravity','wind_scale')):return None
        training=record['samples'][cut:]
        record['candidate']={'fit':fit,'training_ids':[sample_id(x) for x in training],'validation':[],'created':time.time()}
        record['status']='Aprendiendo: comprobando ajuste nuevo'
    return None
