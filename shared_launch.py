"""Armor-2 coincident launch-prefix evidence, never full-warhead certification.

The parent record remains multi-projectile. This module keeps a separate,
attributed ballistic prefix and admits historical data only as a hypothesis.
"""
import hashlib,json,math


def number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
def armor_second(mobile,shot):return mobile=='ARMOR' and isinstance(shot,int) and not isinstance(shot,bool) and shot==1
def _start(value):return isinstance(value,list) and len(value)==6 and all(number(v) for v in value)
def _hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _family(probe,release,state):
    from shot_attribution import identity
    if not isinstance(probe,dict) or not isinstance(release,dict) or not isinstance(state,dict):return None
    if not armor_second(probe.get('mobile'),release.get('shot')) or not armor_second(probe.get('mobile'),probe.get('shot')):return None
    if probe.get('clone_id','dragonbound')!='dragonbound' or release.get('item') or release.get('items'):return None
    if release.get('hero')!=state.get('heroId') or not number(release.get('power')) or not 1<=release['power']<=400:return None
    if not all(number(release.get(k)) for k in ('wind','windAngle')):return None
    raw=state.get('shots')
    if not isinstance(raw,list) or len(raw)>64 or any(not isinstance(s,dict) for s in raw):return None
    return [s for s in raw if identity(s) not in release.get('baseline',[])]


def _member(shot,release,state,explicit_owner=False):
    """A coherent early launch, before interpreting its trajectory mechanism."""
    from shot_attribution import attributed_start
    if shot.get('id') is None or isinstance(shot.get('id'),bool):return False
    if not _start(shot.get('start')) or not number(shot.get('elapsed')) or not 0<=shot['elapsed']<=600:return False
    if not number(shot.get('duration')) or not 0<shot['duration']<=20000 or shot['elapsed']>shot['duration']+1:return False
    if shot.get('auxiliary') or shot.get('delay'):return False
    if not isinstance(shot.get('shotType'),int) or isinstance(shot['shotType'],bool) or shot['shotType']!=1:return False
    metadata=shot.get('metadata') or {}
    if not isinstance(metadata,dict) or not isinstance(metadata.get('selectedShot',1),int) or isinstance(metadata.get('selectedShot',1),bool) or metadata.get('selectedShot',1)!=1:return False
    a,b=metadata.get('player_n'),metadata.get('player')
    if a is not None and b is not None and str(a)!=str(b):return False
    owner=a if a is not None else b
    if explicit_owner and (owner is None or isinstance(owner,bool) or str(owner)!=str(release.get('hero'))):return False
    attribution=attributed_start(state,shot,release)
    return bool(attribution and attribution.get('learnable') and attribution.get('shot')==1 and attribution.get('power')==release['power'])


def _modified(shot):
    return any(shot.get(k) for k in ('wave','orbit','path','change','jumps','unknown_mechanism','mechanism'))


def extract_prefix(probe,release,state,episode=None):
    """One fresh, own, item-free pair with exactly the same initial equation."""
    from shot_attribution import identity
    fresh=_family(probe,release,state)
    if fresh is None:return None
    if len(fresh)!=2 or any(s.get('id') is None or isinstance(s.get('id'),bool) for s in fresh) or str(fresh[0]['id'])==str(fresh[1]['id']):return None
    if any(not _member(shot,release,state) or _modified(shot) for shot in fresh):return None
    if fresh[0]['start']!=fresh[1]['start']:return None
    if episode is None:episode=release.get('episode')
    if episode is not None and (not isinstance(episode,str) or not episode or len(episode)>200):return None
    start=fresh[0]['start'];duration=min(s['duration'] for s in fresh)/1000
    members=sorted(_hash(identity(s)) for s in fresh)
    return {'id':'prefix:'+_hash([episode,members])[:32],'episode':episode,'source':'owned-coincident-prefix','mobile':'ARMOR','shot':1,'power':release['power'],'speed':start[3],'ax':start[4],'ay':start[5],'wind':release['wind'],'wind_angle':release['windAngle'],'heading':start[2],'origin':start[:2],'duration_s':duration,'prefix_duration_s':duration,'member_ids':members,'pair_count':2,'simple':True,'full_family_validated':False}


def classify_prefix(probe,release,state,episode=None):
    """Missing/stale observations are absence of proof, not a changed family.

    A conflict needs a complete fresh set with explicit coherent own metadata.
    Unknown or rival extras leave the observation inconclusive. No such frame
    adds validation evidence or revokes a previously checked initial flight.
    """
    sample=extract_prefix(probe,release,state,episode)
    if sample:return {'status':'matched','sample':sample,'reason':'coincident-pair'}
    fresh=_family(probe,release,state)
    inconclusive={'status':'inconclusive','sample':None,'reason':'incomplete-or-unattributed-observation'}
    if not fresh or len(fresh)<2:return inconclusive
    if any(not _member(shot,release,state,explicit_owner=True) for shot in fresh):return inconclusive
    if len({str(s['id']) for s in fresh})!=len(fresh):return inconclusive
    if len(fresh)>2:return {'status':'conflict','sample':None,'reason':'more-than-two-confirmed-own-projectiles'}
    if fresh[0]['start']!=fresh[1]['start']:return {'status':'conflict','sample':None,'reason':'confirmed-own-launch-spread'}
    if any(_modified(shot) for shot in fresh):return {'status':'conflict','sample':None,'reason':'confirmed-own-modified-path'}
    return inconclusive


def _fresh(row):
    if not isinstance(row,dict) or row.get('source')!='owned-coincident-prefix' or not armor_second(row.get('mobile'),row.get('shot')):return False
    if not isinstance(row.get('id'),str) or not row['id'].startswith('prefix:') or not isinstance(row.get('episode'),str) or not row['episode'] or len(row['episode'])>200:return False
    if row.get('pair_count')!=2 or row.get('simple') is not True or row.get('full_family_validated') is not False:return False
    if not all(number(row.get(k)) for k in ('power','speed','ax','ay','wind','wind_angle','heading','duration_s','prefix_duration_s')):return False
    if not 1<=row['power']<=400 or not 0<row['duration_s']<=20 or row['duration_s']!=row['prefix_duration_s']:return False
    members=row.get('member_ids')
    return isinstance(members,list) and len(members)==2 and members[0]!=members[1] and all(isinstance(v,str) and len(v)==64 for v in members)


def add_prefix_sample(record,sample,episode=None):
    """Only this nested record changes; raw family/pattern flags stay intact."""
    if not isinstance(record,dict) or not isinstance(sample,dict):return False
    sample=dict(sample)
    if sample.get('episode') is None and episode is not None:
        sample['episode']=episode;sample['id']='prefix:'+_hash([episode,sample.get('member_ids')])[:32]
    if not _fresh(sample):return False
    child=record.setdefault('launch_prefix',{'schema':1,'samples':[]})
    if not isinstance(child,dict) or child.get('schema')!=1 or not isinstance(child.get('samples'),list):return False
    if any(isinstance(s,dict) and s.get('id')==sample['id'] for s in child['samples']):return False
    child['samples']=(child['samples']+[sample])[-96:]
    return True


def _legacy_reference_samples(record):
    """Coincident historical starts suggest parameters, but never future checks."""
    if not isinstance(record,dict):return []
    raw=record.get('samples');patterns=record.get('patterns')
    if not isinstance(raw,list) or not isinstance(patterns,list):return []
    result=[];seen=set()
    for pattern in patterns[-32:]:
        if not isinstance(pattern,dict) or not number(pattern.get('power')) or not 1<=pattern['power']<=400:continue
        starts=pattern.get('starts')
        if not isinstance(starts,list) or len(starts)!=2 or not all(_start(s) for s in starts) or starts[0]!=starts[1]:continue
        start=starts[0]
        matches=[s for s in raw[-96:] if isinstance(s,dict) and all(number(s.get(k)) for k in ('power','speed','ax','ay','wind','wind_angle','heading')) and [s['power'],s['speed'],s['ax'],s['ay'],s['heading']]==[pattern['power'],start[3],start[4],start[5],start[2]]]
        regimes={(s['wind'],s['wind_angle'],str(s.get('episode','legacy'))) for s in matches}
        if len(regimes)!=1:continue
        sample=matches[-1];ident='seed:launch-prefix:'+_hash([pattern['power'],start,sample['wind'],sample['wind_angle']])[:32]
        if ident in seen:continue
        seen.add(ident)
        result.append({**{k:sample[k] for k in ('power','speed','ax','ay','wind','wind_angle','heading')},'id':ident,'episode':'legacy-prefix:'+str(sample.get('episode','legacy')),'source':'legacy-coincident-prefix-reference','simple':False,'validation_eligible':False,'reference_duration_s':sample.get('duration_s') if number(sample.get('duration_s')) and 0<sample['duration_s']<=20 else None})
    return result


def prefix_record(record):
    """Separate view for ordinary fit helpers, with no family outcome reuse."""
    child=record.get('launch_prefix') if isinstance(record,dict) else None
    current=[dict(s) for s in child.get('samples',[]) if _fresh(s)] if isinstance(child,dict) and child.get('schema')==1 and isinstance(child.get('samples'),list) else []
    legacy=_legacy_reference_samples(record);old_durations=[s['reference_duration_s'] for s in legacy if s['reference_duration_s'] is not None]
    horizon=max(s['prefix_duration_s'] for s in current) if current else min(old_durations) if old_durations else 0
    reference_durations=old_durations+[s['prefix_duration_s'] for s in current]
    return {'samples':legacy+current,'model':None,'cases':[],'patterns':[],'observed_phases':[],'multi_projectile':False,'prefix_only':True,'scope':'shared-launch-prefix','full_family_validated':False,'weather_effects':{},'prefix_horizon_s':horizon,'prefix_horizon_source':'owned-pair-prefix' if current else 'historical-primary-hypothesis-only' if old_durations else 'unmeasured','reference_max_primary_seconds':max(reference_durations) if reference_durations else 0,'reference_horizon_validated':False,'blocked_episode':child.get('blocked_episode') if isinstance(child,dict) and isinstance(child.get('blocked_episode'),str) else None}


def reference_model(record):
    from training_evaluation import measured_prior
    view=prefix_record(record);samples=view['samples'];model=measured_prior(samples)
    if not model:return None
    return {'model':model,'training_ids':[s['id'] for s in samples],'scope':'shared-launch-prefix','source':'shared-prefix-reference-unvalidated','eligible_for_aiming':False,'full_family_validated':False,'prefix_horizon_s':view['prefix_horizon_s'],'prefix_horizon_source':view['prefix_horizon_source'],'reference_max_primary_seconds':view['reference_max_primary_seconds'],'reference_horizon_validated':False}


def can_prefix(mobile,shot,record):
    return bool(armor_second(mobile,shot) and reference_model(record))


def validated_prefix(record,episode,wind,wind_angle):
    """Two fitted own launches, then two different future force checks."""
    from autonomous_learning import fit,error,flight_error
    from training_evaluation import current_checks,varied_checks
    from wind_models import domain,supported
    if not isinstance(episode,str) or not number(wind) or not number(wind_angle):return None
    child=record.get('launch_prefix') if isinstance(record,dict) else None
    if isinstance(child,dict) and child.get('blocked_episode')==episode:return None
    rows=[s for s in prefix_record(record)['samples'] if _fresh(s) and s['episode']==episode]
    reference=reference_model(record);mode=(reference or {}).get('model',{}).get('wind_mode')
    for cut in range(max(0,len(rows)-12),max(0,len(rows)-3)):
        training=rows[cut:cut+2];future=rows[cut+2:]
        if len(training)!=2 or len(future)<2:continue
        model=fit(training,minimum=2,wind_mode=mode)
        if not model:continue
        checks=current_checks(future,wind,wind_angle,model)
        if not varied_checks(checks):continue
        if any(error(model,s)>5 or flight_error(model,s) is None or flight_error(model,s)>12 for s in checks):continue
        if not set(s['id'] for s in training).isdisjoint(s['id'] for s in checks):continue
        checked=training+checks;model={**model,'wind_domain':domain(checked,model.get('wind_mode','smooth'))}
        if not supported(model,wind,wind_angle):continue
        horizon=min(s['prefix_duration_s'] for s in checks)
        return {'model':model,'training_ids':[s['id'] for s in training],'validation_ids':[s['id'] for s in checks],'power_range':[min(s['power'] for s in checks),max(s['power'] for s in checks)],'max_prefix_seconds':horizon,'prefix_horizon_s':horizon,'scope':'shared-launch-prefix','full_family_validated':False}
    return None
