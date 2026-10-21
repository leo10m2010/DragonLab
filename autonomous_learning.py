"""Data-only launch learner. Does not import the Lab, its solver or its profiles."""
import json,math,statistics,time
from bisect import bisect_right
from pathlib import Path
from training_orientation import heading,raw_angle
from local_storage import atomic_write

def fit(samples,minimum=4):
    if len(samples)<minimum or len({s['power'] for s in samples})<(2 if minimum==2 else 3) or max(s['power'] for s in samples)-min(s['power'] for s in samples)<80:return None
    powers=[s['power'] for s in samples];speeds=[s['speed'] for s in samples];pbar=statistics.mean(powers);vbar=statistics.mean(speeds)
    denominator=sum((p-pbar)**2 for p in powers)
    scale=sum((p-pbar)*(v-vbar) for p,v in zip(powers,speeds))/denominator;offset=vbar-scale*pbar
    xs=[s['wind']*math.cos(math.radians(s['wind_angle'])) for s in samples];ys=[s['wind']*math.sin(math.radians(s['wind_angle'])) for s in samples]
    ybar=statistics.mean(ys);abar=statistics.mean(s['ay'] for s in samples)
    denominator=sum(x*x for x in xs)+sum((y-ybar)**2 for y in ys)
    coupling=(sum(x*s['ax'] for x,s in zip(xs,samples))-sum((y-ybar)*(s['ay']-abar) for y,s in zip(ys,samples)))/denominator if denominator>1e-6 else None
    gravity=abar+(coupling or 0)*ybar
    if not .01<scale<30 or not 0<gravity<10000 or coupling is not None and not 0<=coupling<100:return None
    model={'scale':scale,'offset':offset,'gravity':gravity,'wind_scale':coupling,'count':len(samples),'source':'observed-native-launches'}
    if max(error(model,s) for s in samples)>8:return None
    return model

def error(model,sample):
    if model['wind_scale'] is None and sample['wind']!=0:return math.inf
    k=model['wind_scale'] or 0;r=math.radians(sample['wind_angle'])
    return max(abs(model['scale']*sample['power']+model['offset']-sample['speed']),math.hypot(k*sample['wind']*math.cos(r)-sample['ax'],model['gravity']-k*sample['wind']*math.sin(r)-sample['ay']))

def flight_error(model,sample):
    duration=sample.get('duration_s');angle=sample.get('heading')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (duration,angle)) or not 0<duration<=20:return None
    if model['wind_scale'] is None and sample['wind']:return math.inf
    k=model['wind_scale'] or 0;r=math.radians(sample['wind_angle']);a=math.radians(angle)
    ds=model['scale']*sample['power']+model['offset']-sample['speed']
    dax=k*sample['wind']*math.cos(r)-sample['ax'];day=model['gravity']-k*sample['wind']*math.sin(r)-sample['ay']
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
    a=math.radians(world);w=math.radians(wind_angle);speed=model['scale']*power+model['offset'];k=model['wind_scale'] or 0
    vx=speed*math.cos(a);vy=-speed*math.sin(a);ax=k*wind*math.cos(w);ay=model['gravity']-k*wind*math.sin(w)
    count=max(2,min(500,math.ceil(duration/.04)))
    return [(origin[0]+vx*t+.5*ax*t*t,origin[1]+vy*t+.5*ay*t*t) for t in (duration*i/count for i in range(count+1))]

class AutonomousLearner:
    def __init__(self,path,seed_path=None):
        self.path=Path(path);self.records={};self.latest_plan={};self.pending={};self.episode=str(time.time_ns())
        try:
            saved=json.loads(self.path.read_text(encoding='utf-8'))
            if saved.get('schema')==1 and isinstance(saved.get('records'),dict):self.records=saved['records']
        except (OSError,ValueError,TypeError,AttributeError):pass
        if not self.records and seed_path:self.seed(seed_path)
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
        return {key:{'samples':r.get('samples',[]),'fit':r.get('model') if not r.get('drift') else None,'candidate':r.get('candidate') or {}} for key,r in self.records.items()}
    def progress(self):
        from training_progress import coverage_report
        records=list(self.records.values());cases=[c for r in records for c in r.get('cases',[])]
        aimed=[c for c in cases if c.get('stage') in ('apuntar con modelo propio','repetir experiencia real compatible','afinar con dos tiros reales','apuntar con ajuste local comprobado')]
        tested=[e for r in records for e in r.get('model_tests',[])]
        coverage=coverage_report(self.records);coverage.pop('modes')
        return {**coverage,'measured_launches':sum(sum(not str(s.get('id','')).startswith('seed:') for s in r.get('samples',[])) for r in records),
                'validated_launch_modes':sum(bool(r.get('model')) and not r.get('drift') for r in records),
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
        if not all(isinstance(sample.get(k),(int,float)) and math.isfinite(sample[k]) for k in ('power','speed','ax','ay','wind','wind_angle')) or not 1<=sample['power']<=400 or sample['speed']<=0 or not 0<=sample['wind']<=100:return False
        record=self.records.setdefault(key,{'samples':[]});samples=record['samples']
        if any(s['id']==sample['id'] for s in samples):return False
        candidate=record.get('candidate')
        if not seed and candidate:
            projected=flight_error(candidate['model'],sample)
            if error(candidate['model'],sample)<=8 and (projected is None or projected<=12):
                candidate.setdefault('validation',[]).append({'power':sample['power'],'id':sample['id']})
                if len(candidate['validation'])>=3:record['model']=candidate['model'];record['drift']=False;record.pop('candidate',None)
            else:record.pop('candidate',None)
        if not seed and record.get('model'):
            record['bad']=record.get('bad',0)+1 if error(record['model'],sample)>12 or (flight_error(record['model'],sample) or 0)>25 else 0
            if record['bad']>=3:record['drift']=True
        record['samples']=(samples+[sample])[-96:]
        if not record.get('candidate') and (not record.get('model') or record.get('drift')):
            model=fit(record['samples'])
            training=record['samples']
            if not model:
                fresh=[s for s in record['samples'] if not s['id'].startswith('seed:')]
                model=fit(fresh);training=fresh
                if not model:
                    for cut in range(1,max(1,len(fresh)-5)):
                        model=fit(fresh[cut:])
                        if model:training=fresh[cut:];break
            if model:record['candidate']={'model':model,'validation':[],'trained_ids':[s['id'] for s in training]}
        return True
    def observe(self,probe,release,state):
        from shot_attribution import attributed_start,identity
        owned=[s for s in state.get('shots',[]) if identity(s) not in release.get('baseline',[]) and (attributed_start(state,s,release) or {}).get('learnable')]
        if not owned:return False
        key=f"dragonbound:{probe['mobile']}:{release['shot']}";primary=owned[0];start=primary['start']
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
        record['last_direction']={'planned_heading':planned.get('heading'),'observed_heading':start[2],'initial_vx':start[3]*math.cos(math.radians(start[2])),'raw_angle':release.get('angle'),'pose':release.get('pose')}
        intrinsic=len(owned)>1 or bool(primary.get('wave') or primary.get('orbit'))
        record['multi_projectile']=bool(record.get('patterns') or record.get('observed_phases') or intrinsic)
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
        case={'power':release['power'],'angle':(release.get('learner') or {}).get('elevation'),'wind':release['wind'],'wind_angle':release['windAngle'],'weather':[{k:w.get(k) for k in ('typeId','resolvedTypeId','x','size')} for w in state.get('weather',[])[:32]],'ends':ends,'target':target,'origin':[release['x'],release['y']]}
        if target:
            distances=[]
            for shot in owned:
                try:distances.extend(math.dist(position(shot,shot['duration']/1000*i/64),target) for i in range(65))
                except (ValueError,TypeError,KeyError):pass
            case['path_miss_px']=min(distances,default=None)
        case['id']=identity(primary);case['episode']=self.episode;case['stage']=planned.get('stage','exploración anterior');case['miss_px']=min((math.dist(e,target) for e in ends),default=None) if target else None
        record['cases']=(record.get('cases',[])+[case])[-48:]
        try:self.pending[identity(primary)]={'key':key,'duration':primary['duration'],'end':position(primary,primary['duration']/1000),'created':time.monotonic()}
        except (ValueError,TypeError,KeyError):pass
        self.pending=dict(list(self.pending.items())[-4:])
        # Learn whether a crossed climate actually changes flight, using only
        # native decoded positions against its own measured initial conditions.
        if len(owned)==1 and not primary.get('wave') and not primary.get('orbit'):
            try:
                duration=primary['duration']/1000;angle=math.radians(start[2]);points=[];deviations=[]
                for i in range(1,9):
                    t=duration*i/10;point=position(primary,t);points.append(point)
                    expected=(start[0]+start[3]*math.cos(angle)*t+.5*start[4]*t*t,start[1]-start[3]*math.sin(angle)*t+.5*start[5]*t*t)
                    deviations.append(math.dist(point,expected))
                xmin=min(p[0] for p in points);xmax=max(p[0] for p in points)
                for weather in state.get('weather',[]):
                    x=weather.get('x');size=weather.get('size',0)
                    if not isinstance(x,(int,float)) or not isinstance(size,(int,float)) or not xmin<=x<=xmax:continue
                    kind=str(weather.get('resolvedTypeId') if weather.get('resolvedTypeId') is not None else weather.get('typeId'))
                    effect=record.setdefault('weather_effects',{}).setdefault(kind,{'checked':0,'altered':0})
                    effect['checked']=min(1000,effect['checked']+1);effect['altered']=min(1000,effect['altered']+int(max(deviations,default=0)>8))
            except (ValueError,TypeError,KeyError):pass
        self.save();return True
    def track(self,state):
        if state.get('status')!='live':self.pending.clear();return
        from shot_attribution import identity
        from native_paths import position
        changed=False
        for parent_id,parent in list(self.pending.items()):
            if time.monotonic()-parent['created']>30:self.pending.pop(parent_id,None);continue
            record=self.records[parent['key']]
            for shot in state.get('shots',[]):
                start=shot.get('start');delay=shot.get('delay',0)
                if not shot.get('native') or not isinstance(delay,(int,float)) or delay<=0 or abs(delay-parent['duration'])>1 or not isinstance(start,list) or len(start)!=6:continue
                if math.dist(start[:2],parent['end'])>60:continue
                ident=identity(shot);phases=record.setdefault('observed_phases',[])
                if any(p['id']==ident for p in phases):continue
                try:end=position(shot,shot['duration']/1000)
                except (ValueError,TypeError,KeyError):continue
                if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in end):continue
                phases.append({'id':ident,'parent':parent_id,'start':start,'delay':delay,'end':list(end)});record['observed_phases']=phases[-32:];record['multi_projectile']=True
                case=next((c for c in record.get('cases',[]) if c.get('id')==parent_id),None)
                if case:case['ends']=[list(end)];case['has_continuation']=True
                changed=True
        if changed:self.save()
    def applicable_model(self,record,wind,wind_angle):
        # A historical fit is not automatically valid for a new match/regime.
        local=[s for s in record.get('samples',[]) if s.get('episode')==self.episode and s.get('simple')]
        for cut in range(max(0,len(local)-12),max(0,len(local)-3)):
            rows=local[cut:];training=rows[:2];checks=rows[2:]
            if len(checks)<2 or len({s['power'] for s in checks})<2 or max(s['power'] for s in checks)-min(s['power'] for s in checks)<40:continue
            candidate=fit(training,minimum=2)
            if not candidate:continue
            if not min(s['wind'] for s in rows)<=wind<=max(s['wind'] for s in rows):continue
            if wind and any(abs((s['wind_angle']-wind_angle+180)%360-180)>5 for s in rows):continue
            if all(error(candidate,s)<=5 and flight_error(candidate,s) is not None and flight_error(candidate,s)<=12 for s in checks):
                return candidate,'apuntar con ajuste local comprobado'
        model=record.get('model') if not record.get('drift') else None
        if model and local:
            last=local[-1];projection=flight_error(model,last)
            if abs(last['wind']-wind)<=1 and (wind==0 or abs((last['wind_angle']-wind_angle+180)%360-180)<=5) and error(model,last)<=5 and projection is not None and projection<=12:return model,'apuntar con modelo propio'
        return None,'condiciones sin comprobar'
    def plan(self,state,player,probe,actual=False,previous=None,model_override=None,calibration_only=False):
        hero=next(p for p in state['players'] if str(p['id'])==str(state['heroId']))
        others=[p for p in state['players'] if str(p['id'])!=str(hero['id']) and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
        if not others:raise RuntimeError('Sin objetivo vivo')
        target=min(others,key=lambda p:math.hypot(p['x']-hero['x'],p['y']-hero['y']))
        key=f"dragonbound:{probe['mobile']}:{probe['shot']}";record=self.records.get(key,{})
        model,model_source=(model_override,'evaluación con modelo congelado') if model_override is not None else (None,'calibración controlada') if calibration_only else self.applicable_model(record,state['wind'],state['windAngle'])
        look=player['look'];body=player.get('body',0);right=target['x']>=hero['x']
        low,high=player['minAngle'],player['maxAngle']
        offsets=[hero.get('muzzleX'),hero.get('muzzleY')]
        origin=(hero['x']+offsets[0],hero['y']+offsets[1]) if all(isinstance(v,(int,float)) and math.isfinite(v) and abs(v)<200 for v in offsets) else (hero['x'],hero['y'])
        target_xy=(target['x'],target['y'])
        candidates=[player['rawAngle']] if actual else [max(low,min(high,raw_angle(a,body,look,right))) for a in [probe['angle'],35,55,75,25,65]]
        weather=state.get('weather') or []
        # Nearby repeated native outcomes can be reused without assuming the
        # weather or a multi-projectile pattern follows a ballistic formula.
        remembered=self.remembered(record,hero,target_xy,state,player,probe,actual) if model_override is None and not calibration_only else None
        if remembered:self.latest_plan=remembered;return remembered
        bracket=self.bracketed(record,hero,target_xy,state,player,actual) if model_override is None and not calibration_only else None
        if bracket:self.latest_plan=bracket;return bracket
        effects=record.get('weather_effects',{});blocked=False
        for raw in candidates:
            world=heading(raw,body,look)
            # Before future validation there are no calibrated aiming defaults.
            if model and not record.get('multi_projectile'):
                solved=self.solve_observed(model,origin,target_xy,world,state['wind'],state['windAngle'],details=True)
                if solved is not None:
                    power,duration=solved;path=predicted_path(model,origin,world,power,state['wind'],state['windAngle'],duration)
                    xmin=min(p[0] for p in path);xmax=max(p[0] for p in path)
                    crossed=[w for w in weather if isinstance(w.get('x'),(int,float)) and xmin-w.get('size',0)/2<=w['x']<=xmax+w.get('size',0)/2]
                    known=all((effects.get(str(w.get('resolvedTypeId') if w.get('resolvedTypeId') is not None else w.get('typeId'))) or {}).get('checked',0)>=3 and (effects.get(str(w.get('resolvedTypeId') if w.get('resolvedTypeId') is not None else w.get('typeId'))) or {}).get('altered',0)==0 for w in crossed)
                    if not known:continue
                    if any(occupied(state.get('terrain'),*p) and math.dist(p,target_xy)>20 for p in path[2:]):blocked=True;continue
                    result={'power':power,'raw_angle':raw,'heading':world,'elevation':world if right else 180-world,'target':list(target_xy),'stage':model_source,'model_samples':len(record.get('samples',[])),'approximate':True}
                    self.latest_plan=result;return result
        raw=candidates[0];world=heading(raw,body,look)
        recent=record.get('cases',[])[-1:];needs_move=blocked or bool(recent and recent[0].get('ends') and all(math.dist(e,(hero['x'],hero['y']))<60 for e in recent[0]['ends']))
        result={'power':previous['power'] if actual and previous else probe['power'],'raw_angle':raw,'heading':world,'elevation':world if right else 180-world,'target':list(target_xy),'stage':'calibración controlada' if calibration_only else 'medir clima/patrón' if weather or record.get('multi_projectile') else 'comprobar modelo propio' if record.get('candidate') else 'explorar fuerzas y ángulos','model_samples':len(record.get('samples',[])),'approximate':True,'needs_move':needs_move}
        self.latest_plan=result;return result
    def remembered(self,record,hero,target,state,player,probe,actual):
        def signature(weathers):return sorted(str(w.get('resolvedTypeId') if w.get('resolvedTypeId') is not None else w.get('typeId')) for w in weathers)
        choices=[];right=target[0]>=hero['x'];current_weather=state.get('weather') or []
        for case in record.get('cases',[]):
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
        k=model['wind_scale'] or 0;r=math.radians(wind_angle);ax=k*wind*math.cos(r);ay=model['gravity']-k*wind*math.sin(r)
        direction=(math.cos(math.radians(world)),-math.sin(math.radians(world)));dx=target[0]-origin[0];dy=target[1]-origin[1]
        denominator=ax*direction[1]-ay*direction[0];numerator=2*(dx*direction[1]-dy*direction[0])
        if abs(denominator)<1e-9 or numerator/denominator<=0:return None
        duration=math.sqrt(numerator/denominator)
        if duration>20:return None
        speed=(dx/duration-.5*ax*duration)*direction[0]+(dy/duration-.5*ay*duration)*direction[1]
        power=(speed-model['offset'])/model['scale']
        if not 1<=power<=400:return None
        return (round(power),duration) if details else round(power)
