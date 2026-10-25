"""Data-only launch learner. Does not import the Lab, its solver or its profiles."""
import json,math,statistics,time
from bisect import bisect_right
from pathlib import Path
from training_orientation import heading,raw_angle
from local_storage import atomic_write
from wind_models import acceleration as wind_acceleration,fit_acceleration,components,domain as wind_domain,supported as wind_supported

def fit(samples,minimum=4,wind_mode=None):
    if len(samples)<minimum or len({s['power'] for s in samples})<(2 if minimum==2 else 3) or max(s['power'] for s in samples)-min(s['power'] for s in samples)<40:return None
    powers=[s['power'] for s in samples];speeds=[s['speed'] for s in samples];pbar=statistics.mean(powers);vbar=statistics.mean(speeds)
    denominator=sum((p-pbar)**2 for p in powers)
    scale=sum((p-pbar)*(v-vbar) for p,v in zip(powers,speeds))/denominator;offset=vbar-scale*pbar
    wind_fit=fit_acceleration(samples,mode=wind_mode)
    if not wind_fit or not .01<scale<30:return None
    model={'scale':scale,'offset':offset,**wind_fit,'count':len(samples),'source':'observed-native-launches'}
    if max(error(model,s) for s in samples)>8:return None
    return model

def error(model,sample):
    if model['wind_scale'] is None and sample['wind']!=0:return math.inf
    ax,ay=wind_acceleration(model,sample['wind'],sample['wind_angle'])
    return max(abs(model['scale']*sample['power']+model['offset']-sample['speed']),math.hypot(ax-sample['ax'],ay-sample['ay']))

def flight_error(model,sample):
    duration=sample.get('duration_s');angle=sample.get('heading')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (duration,angle)) or not 0<duration<=20:return None
    if model['wind_scale'] is None and sample['wind']:return math.inf
    ax,ay=wind_acceleration(model,sample['wind'],sample['wind_angle']);a=math.radians(angle)
    ds=model['scale']*sample['power']+model['offset']-sample['speed']
    dax=ax-sample['ax'];day=ay-sample['ay']
    return max(math.hypot(ds*math.cos(a)*t+.5*dax*t*t,-ds*math.sin(a)*t+.5*day*t*t) for t in (duration*i/8 for i in range(1,9)))

def occupied(terrain,x,y):
    if not terrain:return False
    x-=terrain.get('originX',0);y-=terrain.get('originY',0);ix=int(round(x));iy=int(round(y))
    heights=terrain.get('heights',terrain.get('surface'))
    if heights is not None:return 0<=ix<len(heights) and heights[ix] is not None and y>=heights[ix]
    rows=terrain.get('rows')
    if rows is None or not 0<=iy<len(rows) or not 0<=ix<terrain.get('width',0):return False
    return bisect_right(rows[iy],ix)%2==1

def predicted_path(model,origin,world,power,wind,wind_angle,duration):
    a=math.radians(world);speed=model['scale']*power+model['offset']
    vx=speed*math.cos(a);vy=-speed*math.sin(a);ax,ay=wind_acceleration(model,wind,wind_angle)
    travel_bound=abs(speed)*duration+.5*math.hypot(ax,ay)*duration*duration
    count=max(2,min(4000,max(math.ceil(duration/.04),math.ceil(travel_bound/3))))
    return [(origin[0]+vx*t+.5*ax*t*t,origin[1]+vy*t+.5*ay*t*t) for t in (duration*i/count for i in range(count+1))]

def launch_origin(hero,mobile,shot):
    """Native shot geometry first; retain old offsets for older game readers."""
    muzzles=hero.get('muzzles')
    if isinstance(muzzles,(list,tuple)) and isinstance(shot,int) and not isinstance(shot,bool) and 0<=shot<len(muzzles) and isinstance(muzzles[shot],dict):
        from launch_geometry import muzzle_offset
        offset=muzzle_offset(hero,mobile,shot)
        if offset is not None:return (hero['x']+offset[0],hero['y']+offset[1]),'native-shot-muzzle'
    offset=[hero.get('muzzleX'),hero.get('muzzleY')]
    if all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and abs(v)<200 for v in offset):
        return (hero['x']+offset[0],hero['y']+offset[1]),'legacy-muzzle-offset'
    return (hero['x'],hero['y']),'hero-center'


def special_continuation(key):
    """Keep known secondary mechanisms pending when ownership is uncertain."""
    parts=key.split(':')
    if len(parts)!=3:return False
    try:mode=int(parts[2])
    except ValueError:return False
    mechanisms={'NAK':{1,2},'KALSIDDON':{0,1,2},'TRICO':{1},'TURTLE':{1,2},
                'RAON':{0,1,2},'FROG':{0,1,2},'GRUB':{1,2},'ASATE':{0,1,2},
                'LIGHTNING':{0,1,2},'ADUKA':{1,2},'ARMOR':{1},'MAGE':{1},
                'BIGFOOT':{0,1,2},'BOOMER':{1}}
    return mode in mechanisms.get(parts[1],set())


def pattern_flag(record):
    return bool(record.get('patterns') or record.get('intrinsic_pattern') or record.get('special_continuation_pending') or any(p.get('verified') is True for p in record.get('observed_phases',[]) if isinstance(p,dict)))


def quarantine_legacy_phases(key,record):
    """Preserve unproven children without poisoning an ordinary launch model."""
    if record.get('phase_schema')==2:return False
    phases=record.get('observed_phases',[])
    if not isinstance(phases,list):return False
    unverified=[p for p in phases if isinstance(p,dict) and p.get('verified') is not True]
    if not unverified:
        if record.get('multi_projectile') and not record.get('patterns') and not record.get('intrinsic_pattern') and not any(p.get('verified') is True for p in phases if isinstance(p,dict)):
            # Older builds persisted a flag without recording its cause. Keep
            # that fact, but it cannot indefinitely disable an ordinary shot.
            record['legacy_unverified_multi_projectile']=True
            record['special_continuation_pending']=special_continuation(key)
            record['multi_projectile']=pattern_flag(record);record['phase_schema']=2
            return True
        return False
    retained=[p for p in phases if isinstance(p,dict) and p.get('verified') is True]
    quarantined=record.setdefault('quarantined_phases',[])
    seen={p.get('id') for p in quarantined if isinstance(p,dict)}
    for phase in unverified:
        if phase.get('id') not in seen:
            quarantined.append({**phase,'reason':'legacy-continuation-without-owner-proof'});seen.add(phase.get('id'))
    pending=special_continuation(key)
    record['observed_phases']=retained+([{**p,'verified':False,'pending':True} for p in unverified] if pending else [])
    record['special_continuation_pending']=pending
    parents={p.get('parent') for p in unverified}
    for case in record.get('cases',[]):
        if case.get('id') in parents:case['continuation_unverified']=True
    record['multi_projectile']=pattern_flag(record);record['phase_schema']=2
    return True


def weather_training_case(shot,state,release,episode):
    """Keep native column paths as evidence, never as an aiming certificate."""
    from native_paths import position
    from weather_validation import crossing_evidence
    from shot_attribution import identity
    duration=shot.get('duration')
    if not isinstance(duration,(int,float)) or not math.isfinite(duration) or not 0<duration<=20000:return None
    duration/=1000;zones=[]
    for weather in state.get('weather',[])[:32]:
        kind=weather.get('resolvedTypeId')
        if kind is None:kind=weather.get('typeId')
        x=weather.get('x');size=weather.get('size')
        if kind not in (7,8) or not isinstance(x,(int,float)) or not math.isfinite(x):continue
        if kind==7 and size is None:size=0
        if not isinstance(size,(int,float)) or not math.isfinite(size) or size<0 or kind==8 and size==0:continue
        zones.append({'kind':'mirror' if kind==7 else 'tornado','type_id':kind,'x':x,'size':size})
    if not zones:return None
    count=max(32,min(112,math.ceil(duration/.04)+1));times={duration*i/(count-1) for i in range(count)}
    for jump in (shot.get('jumps') or [])[:16]:
        if not isinstance(jump,(list,tuple)) or not jump or not isinstance(jump[0],(int,float)) or not math.isfinite(jump[0]):continue
        at=jump[0]/1000
        for t in (at-.001,at,at+.001):
            if 0<t<duration:times.add(t)
    points=[]
    for t in sorted(times):
        try:x,y=position(shot,t)
        except (ValueError,TypeError,KeyError,IndexError):return None
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y)):return None
        points.append({'x':x,'y':y,'t':t})
    case={'id':identity(shot),'episode':episode,'shot':release['shot'],'power':release['power'],'wind':release['wind'],'wind_angle':release['windAngle'],'origin':shot['start'][:2],'duration_s':duration,'path':points,'zones':zones,'source':'owned-native-path-reconstruction','validated_for_aiming':False}
    case['crossings']=crossing_evidence(case)
    return case if any(e['crossed'] for e in case['crossings']) else None


def quarantine_legacy_column_checks(record):
    if record.get('column_evidence_schema')==2:return False
    effects=record.get('weather_effects') or {};changed=False
    for kind in ('7','8'):
        effect=effects.get(kind)
        if not isinstance(effect,dict):continue
        effect['legacy_unverified_checked']=effect.get('checked',0);effect['checked']=0
        effect['partial_checked']=0;changed=True
    if changed:record['column_evidence_schema']=2
    return changed


def near_weather_escape(hero,origin,proposals):
    """A small supported walk may leave a launch column; physics stays unknown."""
    choices=[]
    for proposal in proposals:
        for weather in proposal.get('weather_crossings',[]):
            kind=weather.get('resolvedTypeId')
            if kind is None:kind=weather.get('typeId')
            center=weather.get('x');size=weather.get('size')
            if kind not in (7,8) or not isinstance(center,(int,float)) or not math.isfinite(center):continue
            half=25 if kind==7 else size/4 if isinstance(size,(int,float)) and math.isfinite(size) and size>0 else None
            if half is None:continue
            lo,hi=center-half,center+half;x=origin[0]
            if lo<=x<=hi:
                destination=lo-1 if x-center<=0 else hi+1
                delta=destination-x
                if abs(delta)>28:continue
            elif min(abs(x-lo),abs(x-hi))<=28:
                delta=-14 if x<center else 14;destination=x+delta
            else:continue
            choices.append({'weather_escape_x':hero['x']+delta,'weather_escape_origin_x':destination,'weather_escape_distance':abs(delta),'weather_escape_kind':kind})
    return min(choices,key=lambda c:c['weather_escape_distance']) if choices else {}


def weather_interval(weather):
    """Column bounds match the native path evidence and piecewise engine."""
    x=weather.get('x');size=weather.get('size',0);kind=weather.get('resolvedTypeId')
    if kind is None:kind=weather.get('typeId')
    if not isinstance(x,(int,float)) or not math.isfinite(x):return None
    if kind==7:half=25
    elif not isinstance(size,(int,float)) or not math.isfinite(size):return None
    elif kind==8:
        if size<=0:return None
        half=max(1,size*.25)
    else:half=max(0,size)/2
    return x-half,x+half

class AutonomousLearner:
    def __init__(self,path,seed_path=None):
        self.path=Path(path);self.records={};self.latest_plan={};self.pending={};self.episode=str(time.time_ns())
        try:
            saved=json.loads(self.path.read_text(encoding='utf-8'))
            if saved.get('schema')==1 and isinstance(saved.get('records'),dict):self.records=saved['records']
        except (OSError,ValueError,TypeError,AttributeError):pass
        self.wind_mode_hints={};repaired=False
        for key,record in self.records.items():
            repaired=quarantine_legacy_phases(key,record) or repaired
            repaired=quarantine_legacy_column_checks(record) or repaired
            if key.startswith('dragonbound:RANDOMIZER:'):record['variable_projectiles']=True
            groups={}
            for sample in record.get('samples',[]):
                if sample.get('simple'):groups.setdefault(sample.get('episode','legacy'),[]).append(sample)
            for group in reversed(list(groups.values())):
                if len(group)<4:continue
                hint=fit_acceleration(group)
                if hint and hint['acceleration_max_error']<=2:self.wind_mode_hints[key]=hint['wind_mode'];break
        if not self.records and seed_path:self.seed(seed_path)
        if repaired:self.save()
    def seed(self,path):
        # Import raw attributed measurements only. Never copy a fit or prediction.
        try:records=json.loads(Path(path).read_text(encoding='utf-8')).get('records',{})
        except (OSError,ValueError,AttributeError):return
        if not isinstance(records,dict):return
        for key,record in records.items():
            if not key.startswith('dragonbound:') or not isinstance(record,dict):continue
            for s in record.get('samples',[])[-96:]:
                if s.get('source')!='native-shot-start':continue
                try:sample={'id':'seed:'+str(s['sample_id']),'power':s['power'],'speed':math.hypot(s['vx'],s['vy']),'ax':s['ax'],'ay':s['ay'],'wind':s['wind'],'wind_angle':s['wind_angle']}
                except (KeyError,TypeError,ValueError):continue
                if all(isinstance(sample[k],(int,float)) and math.isfinite(sample[k]) for k in ('power','speed','ax','ay','wind','wind_angle')):self.add(key,sample,seed=True)
        if self.records:self.save()
    def save(self):atomic_write(self.path,json.dumps({'schema':1,'records':self.records},allow_nan=False).encode())
    def curriculum_records(self):
        return {key:{'samples':r.get('samples',[]),'fit':r.get('model') if not r.get('drift') and not r.get('variable_projectiles') else None,'candidate':r.get('candidate') or {}} for key,r in self.records.items()}
    def progress(self):
        from training_progress import coverage_report
        records=list(self.records.values());cases=[c for r in records for c in r.get('cases',[])]
        aimed=[c for c in cases if c.get('stage') in ('apuntar con modelo propio','repetir experiencia real compatible','afinar con dos tiros reales','apuntar con ajuste local comprobado','evaluación con modelo congelado')]
        tested=[e for r in records for e in r.get('model_tests',[])]
        coverage=coverage_report(self.records);coverage.pop('modes')
        local=[r['last_local_validation'] for r in records if (r.get('last_local_validation') or {}).get('episode')==self.episode]
        return {**coverage,'current_match_validated_modes':len(local),'median_local_flight_error_px':round(statistics.median(r['median_flight_error_px'] for r in local),3) if local else None,'measured_launches':sum(sum(not str(s.get('id','')).startswith('seed:') for s in r.get('samples',[])) for r in records),
                'validated_launch_modes':sum(bool(r.get('model')) and not r.get('drift') and not r.get('variable_projectiles') for r in records),
                'candidate_modes':sum(bool(r.get('candidate')) for r in records),
                'retained_aimed_shots':len(aimed),'retained_exploration_shots':len(cases)-len(aimed),
                'future_model_checks':len(tested),'median_launch_error':round(statistics.median(e['error'] for e in tested),3) if tested else None,
                'accuracy_improvement_proven':False}
    def choose_mobile(self,options,attempted):
        from calibration_book import mobile_name
        from training_policy import next_mobile
        valid=[o for o in options if mobile_name(o.get('name')) and o.get('name')!='Random']
        focus=getattr(self,'focus_mobile',None)
        if focus:
            item=next((o for o in valid if mobile_name(o['name'])==focus),None)
            attempts=attempted.get(focus,0)-getattr(self,'focus_started',0)
            complete=all(self.records.get(f'dragonbound:{focus}:{mode}',{}).get('model') and not self.records.get(f'dragonbound:{focus}:{mode}',{}).get('drift') for mode in (0,1,2))
            if item and attempts<3 and not complete:return item
        item=next_mobile(valid,attempted)
        if item:self.focus_mobile=mobile_name(item['name']);self.focus_started=attempted.get(self.focus_mobile,0)
        return item
    def choose_probe(self,mobile,wind,attempts,available):
        from training_policy import next_probe
        # Establish one ordinary launch model before scattering all measurements.
        pending=[mode for mode in available if not self.records.get(f'dragonbound:{mobile}:{mode}',{}).get('model') or self.records.get(f'dragonbound:{mobile}:{mode}',{}).get('drift')]
        ready=[mode for mode in available if mode not in pending and not self.records.get(f'dragonbound:{mobile}:{mode}',{}).get('multi_projectile')]
        records=self.curriculum_records()
        for mode in available:
            key=f'dragonbound:{mobile}:{mode}';record=records.setdefault(key,{})
            record['samples']=[s for s in record.get('samples',[]) if s.get('episode')==self.episode]
            if record.get('candidate'):
                ids={s['id'] for s in record['samples']}
                record['candidate']={**record['candidate'],'validation':[v for v in record['candidate'].get('validation',[]) if v.get('id') in ids]}
        first=next(iter(available));first_rows=records[f'dragonbound:{mobile}:{first}']['samples']
        modes=[first] if len(first_rows)<4 else ready if ready and attempts%3!=0 else pending[:1] or available
        probe=next_probe(records,mobile,wind,attempts,modes)
        cases=[c for c in self.records.get(f"dragonbound:{mobile}:{probe['shot']}",{}).get('cases',[]) if c.get('episode')==self.episode]
        # Hold the elevation for a block so measured outcomes become comparable.
        probe['angle']=(55,35,75)[(len(cases)//6)%3]
        return probe
    def add(self,key,sample,seed=False):
        if key.startswith('dragonbound:RANDOMIZER:'):return False
        if not all(isinstance(sample.get(k),(int,float)) and math.isfinite(sample[k]) for k in ('power','speed','ax','ay','wind','wind_angle')) or not 1<=sample['power']<=400 or sample['speed']<=0 or not 0<=sample['wind']<=100:return False
        record=self.records.setdefault(key,{'samples':[]});samples=record['samples']
        if any(s['id']==sample['id'] for s in samples):return False
        candidate=record.get('candidate')
        if candidate and candidate.get('episode')!=sample.get('episode'):record.pop('candidate',None);candidate=None
        if not seed and candidate:
            projected=flight_error(candidate['model'],sample)
            if error(candidate['model'],sample)<=5 and (projected is None or projected<=12):
                candidate.setdefault('validation',[]).append({'power':sample['power'],'id':sample['id']})
                checks=candidate['validation'];powers=[c['power'] for c in checks]
                if len(checks)>=3 and len(set(powers))>=2 and max(powers)-min(powers)>=40:
                    checked_ids=set(candidate['trained_ids'])|{c['id'] for c in checks}
                    checked=[s for s in samples+[sample] if s['id'] in checked_ids]
                    candidate['model']['wind_domain']=wind_domain(checked,candidate['model'].get('wind_mode','smooth'))
                    record['model']=candidate['model'];record['drift']=False;record.pop('candidate',None)
            else:record.pop('candidate',None)
        if not seed and record.get('model'):
            record['bad']=record.get('bad',0)+1 if error(record['model'],sample)>12 or (flight_error(record['model'],sample) or 0)>25 else 0
            if record['bad']>=3:record['drift']=True
        record['samples']=(samples+[sample])[-96:]
        if not record.get('candidate') and (not record.get('model') or record.get('drift')):
            training=[s for s in record['samples'] if s.get('episode')==sample.get('episode') and s.get('simple',True) and (seed or not str(s['id']).startswith('seed:'))]
            model=fit(training)
            if model:record['candidate']={'model':model,'episode':sample.get('episode'),'validation':[],'trained_ids':[s['id'] for s in training]}
        return True
    def observe(self,probe,release,state):
        from shot_attribution import attributed_start,identity
        owned=[s for s in state.get('shots',[]) if identity(s) not in release.get('baseline',[]) and (attributed_start(state,s,release) or {}).get('learnable')]
        if not owned:return False
        key=f"dragonbound:{probe['mobile']}:{release['shot']}";primary=owned[0];start=primary['start']
        if probe['mobile']=='RANDOMIZER':
            from variable_projectiles import record_variant
            record=self.records.setdefault(key,{'samples':[]})
            for shot in owned:record_variant(record,shot,release)
            self.save();return True
        sample={'id':identity(primary),'power':release['power'],'speed':start[3],'ax':start[4],'ay':start[5],'wind':release['wind'],'wind_angle':release['windAngle']}
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for k,v in sample.items() if k!='id') or not 1<=sample['power']<=400:return False
        sample['episode']=self.episode;sample['duration_s']=primary.get('duration',0)/1000;sample['simple']=len(owned)==1 and not any(primary.get(k) for k in ('change','wave','orbit','path','jumps'))
        sample['heading']=start[2];sample['raw_angle']=release.get('angle');sample['pose']=release.get('pose')
        existing=self.records.get(key,{})
        tested_error=error(existing['model'],sample) if existing.get('model') and not existing.get('drift') else None
        if not self.add(key,sample):return False
        if tested_error is not None and math.isfinite(tested_error):self.records[key]['model_tests']=(self.records[key].get('model_tests',[])+[{'id':sample['id'],'error':tested_error}])[-96:]
        record=self.records[key]
        planned=release.get('learner') or {}
        planned_origin=planned.get('origin')
        if isinstance(planned_origin,(list,tuple)) and len(planned_origin)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in planned_origin):
            record['last_launch_geometry']={'planned_origin':list(planned_origin),'origin_source':planned.get('origin_source'),'native_origin':start[:2],'origin_error_px':math.dist(planned_origin,start[:2])}
        record['last_direction']={'planned_heading':planned.get('heading'),'observed_heading':start[2],'initial_vx':start[3]*math.cos(math.radians(start[2])),'raw_angle':release.get('angle'),'pose':release.get('pose')}
        intrinsic=len(owned)>1 or bool(primary.get('wave') or primary.get('orbit'))
        if intrinsic:record['intrinsic_pattern']=True
        record['multi_projectile']=pattern_flag(record)
        record['weather_modified_last_shot']=bool(primary.get('change') or primary.get('jumps'))
        # Store the real pattern instead of declaring the primary a full model.
        if len(owned)>1:record['patterns']=(record.get('patterns',[])+[{'power':release['power'],'starts':[s['start'] for s in owned[:16]]}])[-32:]
        from native_paths import position
        ends=[]
        for shot in owned:
            try:
                end=position(shot,shot['duration']/1000)
                if all(isinstance(v,(int,float)) and math.isfinite(v) for v in end):ends.append(end)
            except (ValueError,TypeError,KeyError):pass
        target=(release.get('learner') or {}).get('target')
        case={'action':planned.get('action','apuntar'),'power':release['power'],'angle':(release.get('learner') or {}).get('elevation'),'wind':release['wind'],'wind_angle':release['windAngle'],'weather':[{k:w.get(k) for k in ('typeId','resolvedTypeId','x','size')} for w in state.get('weather',[])[:32]],'ends':ends,'target':target,'origin':[release['x'],release['y']]}
        if target:
            distances=[]
            for shot in owned:
                try:distances.extend(math.dist(position(shot,shot['duration']/1000*i/64),target) for i in range(65))
                except (ValueError,TypeError,KeyError):pass
            case['path_miss_px']=min(distances,default=None)
        case['id']=identity(primary);case['episode']=self.episode;case['stage']=planned.get('stage','exploración anterior');case['miss_px']=min((math.dist(e,target) for e in ends),default=None) if target else None
        record['cases']=(record.get('cases',[])+[case])[-48:]
        training_case=None
        if len(owned)==1:
            training_case=weather_training_case(primary,state,release,self.episode)
            if training_case:record['weather_training']=(record.get('weather_training',[])+[training_case])[-32:]
        try:self.pending[identity(primary)]={'key':key,'duration':primary['duration'],'end':position(primary,primary['duration']/1000),'created':time.monotonic(),'hero':release['hero'],'mobile':probe['mobile'],'shot':release['shot'],'episode':self.episode,'baseline':list(release.get('baseline',[]))}
        except (ValueError,TypeError,KeyError):pass
        self.pending=dict(list(self.pending.items())[-4:])
        # Learn whether a crossed climate actually changes flight, using only
        # native decoded positions against its own measured initial conditions.
        if len(owned)==1 and not primary.get('wave') and not primary.get('orbit'):
            try:
                duration=primary['duration']/1000;angle=math.radians(start[2]);points=[];deviations=[]
                for i in range(33):
                    t=duration*i/32;point=position(primary,t);points.append(point)
                    expected=(start[0]+start[3]*math.cos(angle)*t+.5*start[4]*t*t,start[1]-start[3]*math.sin(angle)*t+.5*start[5]*t*t)
                    deviations.append(math.dist(point,expected))
                xmin=min(p[0] for p in points);xmax=max(p[0] for p in points)
                for weather in state.get('weather',[]):
                    x=weather.get('x');size=weather.get('size',0)
                    if not isinstance(x,(int,float)) or not isinstance(size,(int,float)) or not all(math.isfinite(v) for v in (x,size)) or x+max(0,size)/2<xmin or x-max(0,size)/2>xmax:continue
                    kind=str(weather.get('resolvedTypeId') if weather.get('resolvedTypeId') is not None else weather.get('typeId'))
                    effect=record.setdefault('weather_effects',{}).setdefault(kind,{'checked':0,'altered':0})
                    if kind in ('7','8'):
                        record['column_evidence_schema']=2
                        evidence=next((e for e in (training_case or {}).get('crossings',[]) if e['kind']==('mirror' if kind=='7' else 'tornado') and e['center']==x),None)
                        if not evidence or evidence['status']!='complete-crossing':
                            effect['partial_checked']=min(1000,effect.get('partial_checked',0)+1)
                            effect['altered']=min(1000,effect['altered']+int(max(deviations,default=0)>8));continue
                    effect['checked']=min(1000,effect['checked']+1);effect['altered']=min(1000,effect['altered']+int(max(deviations,default=0)>8))
            except (ValueError,TypeError,KeyError):pass
        self.save();return True
    def track(self,state):
        if state.get('status')!='live':self.pending.clear();return
        from shot_attribution import identity
        from native_paths import position
        changed=False
        for parent_id,parent in list(self.pending.items()):
            if time.monotonic()-parent['created']>30 or parent.get('episode')!=self.episode:self.pending.pop(parent_id,None);continue
            record=self.records[parent['key']]
            for shot in state.get('shots',[]):
                start=shot.get('start');delay=shot.get('delay',0)
                if not shot.get('native') or shot.get('auxiliary') or not isinstance(delay,(int,float)) or isinstance(delay,bool) or not math.isfinite(delay) or delay<=0 or abs(delay-parent['duration'])>1 or not isinstance(start,list) or len(start)!=6:continue
                if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in start):continue
                if start[3]==0 and start[4]==0 and start[5]==0 and not any(shot.get(k) for k in ('path','wave','orbit','jumps')):continue
                if math.dist(start[:2],parent['end'])>60:continue
                ident=identity(shot)
                if ident in parent.get('baseline',[]) or ident==parent_id:continue
                metadata=shot.get('metadata') or {}
                if not isinstance(metadata,dict):continue
                owner=metadata.get('player_n',metadata.get('player'))
                if owner is not None and str(owner)!=str(parent.get('hero')):continue
                from calibration_book import mobile_name
                mobile=metadata.get('mobile')
                if mobile is not None and mobile_name(mobile)!=parent.get('mobile'):continue
                mode=shot.get('shotType')
                if mode is None:mode=metadata.get('selectedShot')
                if isinstance(mode,bool):continue
                if mode is not None and mode!=parent.get('shot'):continue
                verified=owner is not None and str(owner)==str(parent.get('hero')) and (mode==parent.get('shot') or mobile is not None and mobile_name(mobile)==parent.get('mobile'))
                phases=record.setdefault('observed_phases',[]);quarantined=record.setdefault('quarantined_phases',[])
                if any(p.get('id')==ident and p.get('verified') is True for p in phases):continue
                if not verified and any(p.get('id')==ident for p in phases+quarantined):continue
                try:end=position(shot,shot['duration']/1000)
                except (ValueError,TypeError,KeyError):continue
                if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in end):continue
                phase={'id':ident,'parent':parent_id,'start':start,'delay':delay,'end':list(end),'verified':verified,'owner':owner,'shot':mode,'bullet_id':shot.get('bulletId'),'episode':self.episode}
                if verified:
                    phases[:]=[p for p in phases if p.get('id')!=ident]
                    for prior in quarantined:
                        if prior.get('id')==ident:prior['resolved_with_owner_proof']=True
                    phases.append(phase);record['observed_phases']=phases[-32:]
                    record['special_continuation_pending']=any(p.get('pending') for p in phases)
                else:
                    quarantined.append({**phase,'reason':'continuation-without-owner-proof'});record['quarantined_phases']=quarantined[-96:]
                    if special_continuation(parent['key']):
                        phases.append({**phase,'pending':True});record['observed_phases']=phases[-32:];record['special_continuation_pending']=True
                record['multi_projectile']=pattern_flag(record);record['phase_schema']=2
                case=next((c for c in record.get('cases',[]) if c.get('id')==parent_id),None)
                if case:
                    if verified:case['ends']=[list(end)];case['has_continuation']=True;case['continuation_verified']=True;case['continuation_unverified']=False
                    elif special_continuation(parent['key']):case['has_continuation']=True;case['continuation_unverified']=True
                changed=True
        if changed:self.save()
    def applicable_model(self,record,wind,wind_angle):
        if record.get('variable_projectiles'):return None,'proyectil variable sin identificar antes del tiro'
        # A historical fit is not automatically valid for a new match/regime.
        local=[s for s in record.get('samples',[]) if s.get('episode')==self.episode and s.get('simple')]
        for cut in range(max(0,len(local)-12),max(0,len(local)-3)):
            rows=local[cut:];training=rows[:2];checks=rows[2:]
            if len(checks)<2 or len({s['power'] for s in checks})<2 or max(s['power'] for s in checks)-min(s['power'] for s in checks)<40:continue
            mode=self.wind_mode_hints.get(next((k for k,v in self.records.items() if v is record),''),(record.get('model') or {}).get('wind_mode'))
            candidate=fit(training,minimum=2,wind_mode=mode)
            if not candidate:continue
            candidate['wind_domain']=wind_domain(rows,candidate.get('wind_mode','smooth'))
            if candidate.get('wind_mode')=='floor':
                if not wind_supported(candidate,wind,wind_angle):continue
            else:
                if not min(s['wind'] for s in rows)<=wind<=max(s['wind'] for s in rows):continue
                if wind and any(abs((s['wind_angle']-wind_angle+180)%360-180)>5 for s in rows):continue
            if all(error(candidate,s)<=5 and flight_error(candidate,s) is not None and flight_error(candidate,s)<=12 for s in checks):
                record['last_local_validation']={'episode':self.episode,'training_ids':[s['id'] for s in training],'validation_ids':[s['id'] for s in checks],'model':dict(candidate),'median_flight_error_px':statistics.median(flight_error(candidate,s) for s in checks)}
                return candidate,'apuntar con ajuste local comprobado'
        model=record.get('model') if not record.get('drift') else None
        if model and local:
            last=local[-1];projection=flight_error(model,last)
            if abs(last['wind']-wind)<=1 and (wind==0 or abs((last['wind_angle']-wind_angle+180)%360-180)<=5) and error(model,last)<=5 and projection is not None and projection<=12:return model,'apuntar con modelo propio'
        return None,'condiciones sin comprobar'
    def plan(self,state,player,probe,actual=False,previous=None,model_override=None,calibration_only=False):
        hero=next(p for p in state['players'] if str(p['id'])==str(state['heroId']))
        # PowerReader confirms the final pose after turning or walking. The
        # serialized sample also supplies the per-shot native muzzle definitions.
        hero={**hero,**{k:player[k] for k in ('x','y','look','body','muzzles','muzzleX','muzzleY') if player.get(k) is not None}}
        others=[p for p in state['players'] if str(p['id'])!=str(hero['id']) and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
        if not others:raise RuntimeError('Sin objetivo vivo')
        target=min(others,key=lambda p:math.hypot(p['x']-hero['x'],p['y']-hero['y']))
        key=f"dragonbound:{probe['mobile']}:{probe['shot']}";record=self.records.get(key,{})
        model,model_source=(model_override,'evaluación con modelo congelado') if model_override is not None else (None,'calibración controlada') if calibration_only else self.applicable_model(record,state['wind'],state['windAngle'])
        look=player['look'];body=player.get('body',0);right=target['x']>=hero['x']
        low,high=player['minAngle'],player['maxAngle']
        origin,origin_source=launch_origin(hero,probe['mobile'],probe['shot'])
        geometry={'origin':list(origin),'origin_source':origin_source}
        target_xy=(target['x'],target['y'])
        candidates=[player['rawAngle']] if actual else [max(low,min(high,raw_angle(a,body,look,right))) for a in [probe['angle'],35,55,75,25,65]]
        if not actual and probe.get('prefer_current_angle'):candidates=list(dict.fromkeys([player['rawAngle']]+candidates))
        if not actual:
            candidates=list(dict.fromkeys(candidates+list(range(math.ceil(low),math.floor(high)+1,4))+[high]))
        weather=state.get('weather') or []
        # Nearby repeated native outcomes can be reused without assuming the
        # weather or a multi-projectile pattern follows a ballistic formula.
        remembered=self.remembered(record,hero,target_xy,state,player,probe,actual) if model_override is None and not calibration_only else None
        if remembered:
            remembered={**remembered,**geometry};self.latest_plan=remembered;return remembered
        bracket=self.bracketed(record,hero,target_xy,state,player,actual) if model_override is None and not calibration_only else None
        if bracket:
            bracket={**bracket,**geometry};self.latest_plan=bracket;return bracket
        effects=record.get('weather_effects',{});blocked=False;unsupported_weather=False;obstructions=[];weather_probes=[]
        for raw in candidates:
            world=heading(raw,body,look)
            # Before future validation there are no calibrated aiming defaults.
            if model and not record.get('multi_projectile'):
                solved=self.solve_observed(model,origin,target_xy,world,state['wind'],state['windAngle'],details=True)
                if solved is not None:
                    power,duration=solved;path=predicted_path(model,origin,world,power,state['wind'],state['windAngle'],duration)
                    hit=next((i for i,p in enumerate(path[1:],1) if occupied(state.get('terrain'),*p) and math.dist(p,target_xy)>20),None)
                    reachable_path=path[:hit+1] if hit is not None else path
                    xmin=min(p[0] for p in reachable_path);xmax=max(p[0] for p in reachable_path)
                    crossed=[w for w in weather if weather_interval(w) is not None and xmin<=weather_interval(w)[1] and xmax>=weather_interval(w)[0]]
                    known=all((effects.get(str(w.get('resolvedTypeId') if w.get('resolvedTypeId') is not None else w.get('typeId'))) or {}).get('checked',0)>=3 and (effects.get(str(w.get('resolvedTypeId') if w.get('resolvedTypeId') is not None else w.get('typeId'))) or {}).get('altered',0)==0 for w in crossed)
                    if hit is not None:
                        blocked=True
                        if known:obstructions.append({**geometry,'power':power,'raw_angle':raw,'heading':world,'elevation':world if right else 180-world,'target':list(target_xy),'impact':list(path[hit]),'clearance':math.dist(path[hit],(hero['x'],hero['y']))})
                        continue
                    if not known:
                        unsupported_weather=True
                        weather_probes.append({**geometry,'power':power,'raw_angle':raw,'heading':world,'elevation':world if right else 180-world,'target':list(target_xy),'weather_crossings':crossed})
                        continue
                    result={**geometry,'power':power,'raw_angle':raw,'heading':world,'elevation':world if right else 180-world,'target':list(target_xy),'stage':model_source,'model_samples':len(record.get('samples',[])),'approximate':True}
                    self.latest_plan=result;return result
        raw=candidates[0];world=heading(raw,body,look)
        recent=record.get('cases',[])[-1:];needs_move=blocked or bool(recent and recent[0].get('ends') and all(math.dist(e,(hero['x'],hero['y']))<60 for e in recent[0]['ends']))
        escape=near_weather_escape(hero,origin,weather_probes) if unsupported_weather else {}
        result={**geometry,**escape,'power':previous['power'] if actual and previous else probe['power'],'raw_angle':raw,'heading':world,'elevation':world if right else 180-world,'target':list(target_xy),'stage':'calibración controlada' if calibration_only else 'medir clima/patrón' if weather or record.get('multi_projectile') else 'comprobar modelo propio' if record.get('candidate') else 'explorar fuerzas y ángulos','model_samples':len(record.get('samples',[])),'approximate':True,'needs_move':needs_move,'unavailable_reason':'missing-model' if not model else 'unsupported-pattern' if record.get('multi_projectile') else 'unknown-weather' if unsupported_weather else 'terrain-blocked' if blocked else 'unmeasured-wind' if model.get('wind_scale') is None and state['wind'] else 'terrain-blocked' if blocked else 'angle-unavailable','blocked_plans':obstructions,'weather_probes':weather_probes,'reposition_allowed':bool(model and not record.get('multi_projectile') and (blocked or not unsupported_weather or escape) and (model.get('wind_scale') is not None or not state['wind']))}
        self.latest_plan=result;return result
    def remembered(self,record,hero,target,state,player,probe,actual):
        def signature(weathers):return sorted(str(w.get('resolvedTypeId') if w.get('resolvedTypeId') is not None else w.get('typeId')) for w in weathers)
        choices=[];right=target[0]>=hero['x'];current_weather=state.get('weather') or []
        for case in record.get('cases',[]):
            if case.get('action')=='abrir paso':continue
            if case.get('continuation_unverified'):continue
            if case.get('episode')!=self.episode:continue
            if not case.get('target') or not case.get('ends') or case.get('angle') is None:continue
            if (case['target'][0]>=case['origin'][0])!=right or math.dist(case['origin'],(hero['x'],hero['y']))>40:continue
            if abs(case['wind']-state['wind'])>3 or abs((case['wind_angle']-state['windAngle']+180)%360-180)>15 or signature(case['weather'])!=signature(current_weather):continue
            if any(not any(abs(w.get('x',1e9)-old.get('x',-1e9))<40 for old in case['weather']) for w in current_weather):continue
            raw=max(player['minAngle'],min(player['maxAngle'],raw_angle(case['angle'],player.get('body',0),player['look'],right)))
            effective=heading(player['rawAngle'] if actual else raw,player.get('body',0),player['look']);elevation=effective if right else 180-effective
            if abs(elevation-case['angle'])>2:continue
            translated=[(e[0]-case['origin'][0]+hero['x'],e[1]-case['origin'][1]+hero['y']) for e in case['ends']]
            miss=min(math.dist(e,target) for e in translated)
            if miss<=35:choices.append((miss,raw,case))
        if len(choices)<2:return None
        _,raw,case=min(choices,key=lambda c:c[0])
        return {'power':case['power'],'raw_angle':raw,'heading':heading(raw,player.get('body',0),player['look']),'elevation':case['angle'],'target':list(target),'stage':'repetir experiencia real compatible','model_samples':len(record.get('samples',[])),'approximate':True}
    def bracketed(self,record,hero,target,state,player,actual):
        # A bounded interpolation between comparable real short/long outcomes.
        # Do not extrapolate, merge climates, or assume a multiple projectile is one.
        if record.get('multi_projectile') or state.get('weather'):return None
        right=target[0]>=hero['x'];sign=1 if right else -1;choices=[]
        for case in record.get('cases',[]):
            if case.get('action')=='abrir paso':continue
            if case.get('episode')!=self.episode:continue
            if case.get('weather') or case.get('has_continuation') or len(case.get('ends',[]))!=1 or case.get('angle') is None:continue
            if not case.get('target') or math.dist(case['origin'],(hero['x'],hero['y']))>20:continue
            if (case['target'][0]>=case['origin'][0])!=right:continue
            if abs(case['wind']-state['wind'])>2 or abs((case['wind_angle']-state['windAngle']+180)%360-180)>10:continue
            end=case['ends'][0];offset=(end[0]-case['origin'][0],end[1]-case['origin'][1])
            if abs(offset[1]-(target[1]-hero['y']))>25:continue
            raw=max(player['minAngle'],min(player['maxAngle'],raw_angle(case['angle'],player.get('body',0),player['look'],right)))
            world=heading(player['rawAngle'] if actual else raw,player.get('body',0),player['look']);elevation=world if right else 180-world
            if abs(elevation-case['angle'])>2:continue
            choices.append((case,raw,sign*(offset[0]-(target[0]-hero['x']))))
        for a,raw,short in reversed(choices):
            if short>=0:continue
            for b,_,long in reversed(choices):
                if long<=0 or b['power']-a['power']<40 or abs(a['angle']-b['angle'])>1:continue
                if math.dist(a['origin'],b['origin'])>10 or abs(a['wind']-b['wind'])>1 or abs((a['wind_angle']-b['wind_angle']+180)%360-180)>5:continue
                power=round(a['power']+(b['power']-a['power'])*(-short)/(long-short))
                return {'power':power,'raw_angle':raw,'heading':heading(player['rawAngle'] if actual else raw,player.get('body',0),player['look']),'elevation':a['angle'],'target':list(target),'stage':'afinar con dos tiros reales','supporting_cases':[a.get('id'),b.get('id')],'approximate':True,'model_samples':len(record.get('samples',[]))}
        return None
    @staticmethod
    def solve_observed(model,origin,target,world,wind,wind_angle,details=False):
        if model['wind_scale'] is None and wind:return None
        ax,ay=wind_acceleration(model,wind,wind_angle)
        direction=(math.cos(math.radians(world)),-math.sin(math.radians(world)));dx=target[0]-origin[0];dy=target[1]-origin[1]
        denominator=ax*direction[1]-ay*direction[0];numerator=2*(dx*direction[1]-dy*direction[0])
        if abs(denominator)<1e-9 or numerator/denominator<=0:return None
        duration=math.sqrt(numerator/denominator)
        if duration>20:return None
        speed=(dx/duration-.5*ax*duration)*direction[0]+(dy/duration-.5*ay*duration)*direction[1]
        power=(speed-model['offset'])/model['scale']
        if not 1<=power<=400:return None
        return (round(power),duration) if details else round(power)
