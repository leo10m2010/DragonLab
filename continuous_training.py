"""Finite evaluation blocks within one time-bounded continuous session."""
import copy,hashlib,json,math,os,re,time,uuid
from pathlib import Path
from local_storage import atomic_write

TOTAL_FIELDS=('calibration_shots','directed_test_shots','skipped_turns','near_target_shots','known_health_windows','health_drop_windows','weather_practice_shots','dual_uses','terrain_attempts','terrain_reserved_attempts','terrain_openings_observed')

class ObservationArchiveError(RuntimeError):pass

def transient_browser_error(error):
    """Only known lost CDP handles/contexts; never game or input failures."""
    message=str(error).strip().rstrip('.')
    return message in {
        'Cannot find context with specified id','Could not find object with given id',
        'Execution context was destroyed','Execution context was destroyed, most likely because of a navigation',
        'Inspected target navigated or closed','Target closed','Session closed. Most likely the target has been closed',
        'Session with given id not found','No target with given id found',
    } or bool(re.fullmatch(r'Cannot find execution context with id \d+',message))

def finite_number(value):
    try:return value if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else None
    except OverflowError:return None

class DeadlineCancel:
    """The normal stop signal, also checked inside every input preparation."""
    def __init__(self,event,deadline):self.event=event;self.deadline=deadline
    def is_set(self):return self.event.is_set() or time.monotonic()>=self.deadline
    def set(self):self.event.set()
    def clear(self):self.event.clear()
    def wait(self,timeout=None):
        remaining=max(0,self.deadline-time.monotonic())
        if remaining<=0:return True
        elapsed=self.event.wait(remaining if timeout is None else min(max(0,timeout),remaining))
        return bool(elapsed) or self.is_set()

class RollingEvaluation:
    """Retain raw block reports on disk, with bounded in-memory summaries."""
    def __init__(self,directory,learner,max_shots,allow_dual=False):
        from adaptive_training import AdaptiveTrial
        self.factory=AdaptiveTrial;self.learner=learner;self.max_shots=max_shots;self.allow_dual=allow_dual
        self.directory=Path(directory)/'evaluaciones-continuas'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
        self.block=1;self.completed_blocks=0;self.completed_shots=0;self.totals={key:0 for key in TOTAL_FIELDS};self.latest=[];self.observations=0
        self.current=self.create()
    def create(self):
        return self.factory(self.directory/f'bloque-{self.block:05d}'/'evaluacion-adaptativa.json',self.learner,self.max_shots,allow_dual=self.allow_dual)
    def rollover(self):
        # The controller settles pending health windows before changing callback.
        previous=self.current;previous.finish();summary=previous.summary()
        for key in TOTAL_FIELDS:self.totals[key]+=summary.get(key,0)
        self.completed_shots+=sum(summary.get(key,0) for key in ('calibration_shots','directed_test_shots','weather_practice_shots','dual_uses','terrain_attempts'))
        self.completed_blocks+=1;self.latest.append({'block':self.block,'summary':summary});self.latest=self.latest[-24:]
        self.block+=1;self.current=self.create()
        self.current.focus_mobile=previous.focus_mobile;self.current.focus_modes=dict(previous.focus_modes)
        for key,profile in previous.profiles.items():
            continued=self.current.profile(profile.mobile,profile.shot)
            for field in ('episode','warmups','frozen','context_candidate','baseline','prior','prior_training_ids','seen_episodes','phase','episode_calibration_count','directed_test_count'):
                setattr(continued,field,copy.deepcopy(getattr(profile,field)))
            continued.episode_calibration_count=max(continued.episode_calibration_count,sum(row.get('episode')==profile.episode for row in profile.calibration))
            continued.directed_test_count=max(continued.directed_test_count,len(profile.tests))
            continued.experience_tests=(getattr(profile,'experience_tests',[])+profile.tests)[-96:]
            continued.experience_calibration=(getattr(profile,'experience_calibration',[])+profile.calibration)[-96:]
        self.current.experience_weather_rows=(getattr(previous,'experience_weather_rows',[])+previous.weather_rows)[-192:]
        self.current.experience_recovery_rows=(getattr(previous,'experience_recovery_rows',[])+previous.recovery_rows)[-192:]
        self.current.experience_reserved_recoveries=(getattr(previous,'experience_reserved_recoveries',[])+getattr(previous,'reserved_recoveries',[]))[-192:]
        self.save();return self.current
    def report(self):
        current=self.current.summary()
        return {'block':self.block,'completed_blocks':self.completed_blocks,'completed_shots':self.completed_shots,'totals':{key:self.totals[key]+current.get(key,0) for key in TOTAL_FIELDS},'latest_blocks':list(self.latest),'archive':str(self.directory)}
    def save(self):atomic_write(self.directory/'sesion.json',json.dumps({'schema':1,**self.report()},allow_nan=False).encode())
    def record(self,probe,release,observation):
        """Append confirmed numeric evidence before bounded learner history rotates."""
        from calibration_book import mobile_name
        from shot_attribution import attributed_start,identity
        native=[];shots=observation.get('shots')
        for shot in shots[:512] if isinstance(shots,list) else []:
            if not isinstance(shot,dict):continue
            try:
                if identity(shot) in release.get('baseline',[]):continue
                attribution=attributed_start(observation,shot,release)
                if not attribution or not attribution.get('learnable'):continue
                start=[finite_number(value) for value in attribution['start']]
                if any(value is None for value in start):continue
                duration=finite_number(shot.get('duration'))
                native.append({'start':start,'duration':duration if duration is not None and 0<=duration<=120000 else None,'elapsed':finite_number(shot.get('elapsed')),'bulletId':finite_number(shot.get('bulletId')),'shotType':finite_number(shot.get('shotType'))})
                if len(native)>=64:break
            except (KeyError,TypeError,ValueError,IndexError,AttributeError,OverflowError):continue
        weather=[];zones=observation.get('weather')
        for zone in zones[:32] if isinstance(zones,list) else []:
            if not isinstance(zone,dict):continue
            row={key:finite_number(zone.get(key)) for key in ('typeId','resolvedTypeId','x','size')}
            if any(value is not None for value in row.values()):weather.append(row)
        plan=release.get('learner') if isinstance(release.get('learner'),dict) else {}
        phase=plan.get('evaluation_phase');mode=probe.get('shot')
        row={'schema':1,'sequence':self.observations+1,'block':self.block,'episode':hashlib.sha256(str(self.learner.episode).encode()).hexdigest()[:24],'clone':'dragonbound','mobile':mobile_name(probe.get('mobile')),'shot':mode if mode in (0,1,2) and not isinstance(mode,bool) else None,'phase':phase if phase in ('calibration','evaluation','weather','recovery') else None,'item':'dual' if release.get('item')=='dual' else None,'created':finite_number(time.time()),'native':native,'weather':weather}
        row.update({key:finite_number(release.get(key)) for key in ('hero','x','y','power','angle','wind','windAngle','turn_serial')})
        origin=plan.get('origin')
        if isinstance(origin,(list,tuple)) and len(origin)==2 and all(finite_number(v) is not None for v in origin):
            row['planned_origin']=list(origin)
            row['origin_source']=plan.get('origin_source') if plan.get('origin_source') in ('native-shot-muzzle','legacy-muzzle-offset','hero-center') else None
            row['origin_error_px']=math.dist(origin,native[0]['start'][:2]) if native else None
        raw=json.dumps(row,ensure_ascii=True,allow_nan=False,separators=(',',':'))+'\n'
        try:
            self.directory.mkdir(parents=True,exist_ok=True)
            with (self.directory/'observaciones-nativas.jsonl').open('a',encoding='utf-8',newline='\n') as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
        except OSError as error:raise ObservationArchiveError('No se pudieron guardar las mediciones nativas; entrenamiento detenido para conservar los datos') from error
        self.observations+=1
