"""Transfer attributable launch evidence to the manual guide, without game input.

Each match is fitted separately. A saved model is a bounded historical launch
certificate, not proof of a special weapon family or a new match's physics.
"""
import copy,hashlib,json,math,threading,time
from pathlib import Path
from autonomous_learning import fit,error,flight_error,special_continuation
from calibration_book import mobile_name
from local_launch_window import _rows,validated_window
from local_storage import atomic_write
from wind_models import domain,supported,components

MAX_FILE=64*1024*1024
MAX_PROFILES=6

def digest(value):return hashlib.sha256(str(value).encode()).hexdigest()
def number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
def valid_key(key):
    parts=key.split(':') if isinstance(key,str) else []
    return len(parts)==3 and parts[0]=='dragonbound' and mobile_name(parts[1])==parts[1] and parts[1]!='RANDOMIZER' and parts[2] in ('0','1','2')

def certificate(key,rows,episode):
    """Fit a past episode, then check strictly later, disjoint native launches."""
    if not valid_key(key) or special_continuation(key):return None
    rows=_rows({'samples':rows},episode)
    proof=None
    for cut in range(4,min(9,len(rows)-2)):
        training,future=rows[:cut],rows[cut:]
        if len(future)<3 or len({s['power'] for s in future})<2:continue
        model=fit(training)
        if not model or any(error(model,s)>5 or (flight_error(model,s) is None or flight_error(model,s)>12) for s in future):continue
        low=max(min(s['power'] for s in training),min(s['power'] for s in future))
        high=min(max(s['power'] for s in training),max(s['power'] for s in future))
        if high<=low:continue
        model={**model,'wind_domain':domain(future,model.get('wind_mode','smooth'))}
        proof={'model':model,'power_range':[low,high],'max_flight_seconds':min(s['duration_s'] for s in future),
               'training_ids':[s['id'] for s in training],'validation_ids':[s['id'] for s in future],
               'scope':'checked-launch-window','max_flight_error_px':max(flight_error(model,s) for s in future)}
        break
    if not proof and rows:
        last=rows[-1]
        proof=validated_window({'samples':rows},episode,last['wind'],last['wind_angle'])
    if not proof:return None
    model=proof['model'];ident=digest((key,episode,proof['training_ids'],proof['validation_ids']))
    return {'id':ident,'key':key,'episode_key':digest(episode),'sequence':int(episode) if episode.isdecimal() else 0,
            'fit':{'power_scale':model['scale'],'speed_offset':model['offset'],'gravity':model['gravity'],
                   'wind_scale':model['wind_scale'],'wind_mode':model.get('wind_mode','smooth'),
                   'wind_observed':model['wind_scale'] is not None,'wind_domain':model['wind_domain']},
            'power_range':proof['power_range'],'max_flight_seconds':proof['max_flight_seconds'],
            'wind_features':proof.get('uncertainty_wind_features'),
            'training_ids':[digest(i) for i in proof['training_ids']],
            'validation_ids':[digest(i) for i in proof['validation_ids']],
            'sample_count':len(rows),'scope':proof['scope'],'max_flight_error_px':proof['max_flight_error_px']}

def valid_profile(row):
    if not isinstance(row,dict) or not valid_key(row.get('key')) or special_continuation(row['key']):return False
    f=row.get('fit') or {};bounds=row.get('power_range');horizon=row.get('max_flight_seconds')
    if not all(number(f.get(k)) for k in ('power_scale','speed_offset','gravity')):return False
    if not .01<f['power_scale']<30 or not 0<f['gravity']<10000 or f.get('wind_mode') not in ('smooth','floor'):return False
    if f.get('wind_scale') is not None and not (number(f['wind_scale']) and 0<=f['wind_scale']<100):return False
    if not isinstance(bounds,list) or len(bounds)!=2 or not all(number(v) for v in bounds) or not 1<=bounds[0]<bounds[1]<=400:return False
    if not number(horizon) or not 0<horizon<=20:return False
    wind=f.get('wind_domain')
    if not isinstance(wind,list) or len(wind)!=4 or not all(number(v) for v in wind):return False
    def hashed(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
    training=row.get('training_ids');checks=row.get('validation_ids')
    if not isinstance(training,list) or not isinstance(checks,list) or not 3<=len(training)<=96 or not 3<=len(checks)<=96 or not all(hashed(v) for v in training+checks):return False
    if len(set(training))<3 or len(set(checks))<3 or set(training)&set(checks):return False
    sequence=row.get('sequence');features=row.get('wind_features')
    if not isinstance(sequence,int) or isinstance(sequence,bool) or not 0<=sequence<=10**22:return False
    if features is not None and (not isinstance(features,list) or len(features)!=2 or not all(number(v) for v in features)):return False
    if row.get('scope') not in ('checked-launch-window','local-power-flight-window'):return False
    if not isinstance(row.get('sample_count'),int) or not 6<=row['sample_count']<=96:return False
    return hashed(row.get('id')) and hashed(row.get('episode_key'))

class LearnedLaunchLibrary:
    def __init__(self,directory):
        self.directory=Path(directory);self.path=self.directory/'perfiles-aprendidos.json';self.profiles={};self.manual={};self.coverage={}
        self.lock=threading.RLock();self.stamps=None;self.error='';self.episode=None;self.in_game=False;self.live={};self.revision=0
        try:
            if self.path.stat().st_size>8*1024*1024:raise ValueError('Oversized library')
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('schema')!=1:raise ValueError('Unknown library schema')
            self.profiles={k:[r for r in rows[-MAX_PROFILES:] if valid_profile(r) and r['key']==k] for k,rows in data.get('profiles',{}).items() if valid_key(k) and isinstance(rows,list)}
            self.manual={k:{'samples':v['samples'][-96:]} for k,v in data.get('manual',{}).items() if valid_key(k) and isinstance(v,dict) and isinstance(v.get('samples'),list)}
            self.coverage=data.get('coverage',{})
        except FileNotFoundError:pass
        except (OSError,ValueError,TypeError,AttributeError):self.error='No se pudo leer el aprendizaje guardado'
    def sources(self):
        return [self.directory/'aprendizaje-autonomo.json',*(self.directory/f'entrenamiento-paralelo/sesion-{i}/aprendizaje-autonomo.json' for i in (1,2))]
    def save(self):
        atomic_write(self.path,json.dumps({'schema':1,'profiles':self.profiles,'manual':self.manual,'coverage':self.coverage},allow_nan=False).encode())
    def retain(self,profile):
        if not profile or not valid_profile(profile):return False
        key=profile['key'];old=self.profiles.get(key,[])
        if any(r['id']==profile['id'] for r in old):return False
        same=[r for r in old if r['episode_key']==profile['episode_key']]
        if same and max(r['sample_count'] for r in same)>profile['sample_count']:return False
        old=[r for r in old if r['episode_key']!=profile['episode_key']]
        self.profiles[key]=sorted(old+[profile],key=lambda r:r.get('sequence',0))[-MAX_PROFILES:];self.revision+=1;return True
    def refresh(self):
        """Read fixed numeric data files only; unchanged sources cost three stats."""
        paths=self.sources();stamps=[]
        for p in paths:
            try:s=p.stat();stamps.append((str(p),s.st_mtime_ns,s.st_size))
            except FileNotFoundError:stamps.append((str(p),None,None))
        if stamps==self.stamps:return False
        proposed=[];coverage={};failed=False
        for p,(_,stamp,size) in zip(paths,stamps):
            if stamp is None:continue
            try:
                if size>MAX_FILE:raise ValueError('Oversized observations')
                data=json.loads(p.read_text(encoding='utf-8'))
                if data.get('schema')!=1 or not isinstance(data.get('records'),dict):raise ValueError('Invalid observations')
                for key,record in data['records'].items():
                    if not valid_key(key) or not isinstance(record,dict):continue
                    groups={}
                    for row in record.get('samples',[])[-96:]:
                        if isinstance(row,dict) and isinstance(row.get('episode'),str):groups.setdefault(row['episode'],[]).append(row)
                    count=sum(1 for rows in groups.values() for s in rows if not str(s.get('id','')).startswith('seed:') and all(number(s.get(k)) for k in ('power','speed','ax','ay','wind','wind_angle')))
                    previous=coverage.get(key,{});coverage[key]={'samples':max(previous.get('samples',0),count),'special':special_continuation(key) or bool(record.get('multi_projectile') or record.get('variable_projectiles'))}
                    if coverage[key]['special']:continue
                    for episode,rows in groups.items():
                        proof=certificate(key,rows,episode)
                        if proof:proposed.append(proof)
            except (OSError,ValueError,TypeError,KeyError,OverflowError):failed=True
        with self.lock:
            changed=any([self.retain(p) for p in proposed])
            self.coverage=coverage or self.coverage
            self.error='Una fuente de mediciones no pudo leerse; se conserva el aprendizaje anterior' if failed else ''
            self.stamps=None if failed else stamps
            self.save()
        return changed
    def profile(self,key,wind,angle):
        if not number(wind) or not 0<=wind<=100 or not number(angle):return None
        with self.lock:
            options=[]
            for row in self.profiles.get(key,[]):
                fit=row['fit'];model={**fit,'scale':fit['power_scale'],'offset':fit['speed_offset']}
                if not supported(fit,wind,angle,margin=0):continue
                features=row.get('wind_features')
                if features is not None and any(abs(a-b)>1e-7 for a,b in zip(features,components(wind,angle,fit['wind_mode']))):continue
                if any(error(model,s)>5 or flight_error(model,s) is None or flight_error(model,s)>12 for s in self.live.get(key,[])):continue
                options.append(row)
            if not options:return None
            best=max(options,key=lambda r:(r.get('sequence',0),len(r['validation_ids'])))
            metadata={k:copy.deepcopy(best[k]) for k in ('id','key','power_range','max_flight_seconds','scope')}
            metadata.update(checks=len(best['validation_ids']),samples=best['sample_count'],current_match_checked=bool(self.live.get(key)))
            return {**copy.deepcopy(best['fit']),'learned_launch':metadata}
    def observe(self,state,release=None):
        """Learn from normal manual shots; never sends or schedules an action."""
        if state.get('status')!='live' or state.get('over'):
            self.in_game=False;return False
        if release and release.get('item'):return False
        if not self.in_game:
            self.in_game=True;self.episode=str(time.time_ns());self.live={}
        from shot_attribution import attributed_start,identity
        hero=next((p for p in state.get('players',[]) if p.get('id')==state.get('heroId')),None)
        name=mobile_name(hero.get('mobile')) if hero else None
        if not name:return False
        candidates=[]
        for shot in state.get('shots',[]):
            a=attributed_start(state,shot,release)
            if a and a.get('learnable'):candidates.append((shot,a))
        if len(candidates)!=1:return False
        shot,a=candidates[0];mode=a['shot'];key=f'dragonbound:{name}:{mode}'
        if not valid_key(key) or special_continuation(key) or any(shot.get(k) for k in ('change','jumps','wave','orbit','path')):return False
        start=shot['start'];duration=shot.get('duration')
        if not number(duration) or not 0<duration<=20000:return False
        row={'id':identity(shot),'episode':self.episode,'simple':True,'source':'owned-native-launch',
             'power':a['power'],'speed':start[3],'heading':start[2],'ax':start[4],'ay':start[5],
             'wind':a['wind'],'wind_angle':a['windAngle'],'duration_s':duration/1000}
        if not _rows({'samples':[row]},self.episode):return False
        with self.lock:
            live=self.live.setdefault(key,[])
            if any(s['id']==row['id'] for s in live):return False
            live.append(row);self.live[key]=live[-24:]
            record=self.manual.setdefault(key,{'samples':[]});record['samples']=(record['samples']+[row])[-96:]
            proof=certificate(key,self.live[key],self.episode);self.retain(proof);self.revision+=1;self.save()
        return True
    def summary(self):
        with self.lock:return {'available_modes':sum(bool(v) for v in self.profiles.values()),'profiles':sum(len(v) for v in self.profiles.values()),'error':self.error}
    def rows(self):
        from core import PROFILES
        result=[]
        for name in PROFILES:
            labels=[];count=0
            for mode,label in enumerate(('1','2','SS')):
                key=f'dragonbound:{name}:{mode}';profiles=self.profiles.get(key,[]);c=self.coverage.get(key,{})
                count+=c.get('samples',0)
                value='proyectil variable' if name=='RANDOMIZER' else 'aprendida' if profiles else 'mecanismo pendiente' if c.get('special') or special_continuation(key) else 'faltan comprobaciones' if c.get('samples') else 'sin tiros útiles'
                labels.append(label+': '+value)
            result.append((name,' · '.join(labels),count))
        return result
