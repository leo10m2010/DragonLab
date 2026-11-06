"""Bounded numeric training guides, with a pre-shot model kept apart from truth.

Stores no credentials, names, chats, screenshots or commands. SQLite commits
each confirmed case atomically; feedback can update it without appending a
second copy. Saving a guide never certifies its physical model.
"""
import hashlib,json,math,sqlite3,time
from contextlib import contextmanager
from pathlib import Path
from calibration_book import mobile_name

FILENAME='guias-entrenamiento.sqlite3'
MAX_PAYLOAD=32*1024

def number(value):
    try:return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
    except OverflowError:return False
def hashed(value):return hashlib.sha256(str(value).encode()).hexdigest()
def point(value):return list(value) if isinstance(value,(list,tuple)) and len(value)==2 and all(number(v) for v in value) else None
def numeric(row,keys):return {k:row[k] for k in keys if number(row.get(k))}

def pre_shot_path(plan,wind,angle):
    snapshot=plan.get('guide_prediction');origin=point(plan.get('origin'))
    if not isinstance(snapshot,dict) or not origin:return None
    model=snapshot.get('model');duration=snapshot.get('duration_s')
    if not isinstance(model,dict) or not all(number(model.get(k)) for k in ('scale','offset','gravity')) or not number(duration) or not 0<duration<=20:return None
    if model.get('wind_scale') is not None and not number(model['wind_scale']):return None
    if not all(number(v) for v in (plan.get('heading'),plan.get('power'),wind,angle)):return None
    if model.get('wind_mode') not in (None,'smooth','floor'):return None
    from wind_models import acceleration
    model={**model,'wind_mode':model.get('wind_mode') or 'smooth'}
    heading=math.radians(plan['heading']);speed=model['scale']*plan['power']+model['offset'];ax,ay=acceleration(model,wind,angle)
    points=[]
    for i in range(65):
        t=duration*i/64;points.append([origin[0]+speed*math.cos(heading)*t+.5*ax*t*t,origin[1]-speed*math.sin(heading)*t+.5*ay*t*t,t])
    if not all(number(v) for p in points for v in p):return None
    return {'source':'replayed-pre-shot-model','model':{**numeric(model,('scale','offset','gravity','wind_scale')),'wind_mode':model.get('wind_mode') or 'smooth'},'duration_s':duration,'path':points}

def native_path(shot,phase='initial'):
    start=shot.get('start');duration=shot.get('duration')
    if not isinstance(start,list) or len(start)!=6 or not all(number(v) for v in start) or not number(duration) or not 0<duration<=20000:return None
    from native_paths import position
    points=[]
    try:
        for i in range(65):
            t=duration/1000*i/64;x,y=position(shot,t)
            if not all(number(v) for v in (x,y)):return None
            points.append([x,y,t])
    except (TypeError,ValueError,KeyError,IndexError,OverflowError):return None
    return {'source':'native-path-reconstruction','phase':phase,'start':list(start),'duration_s':duration/1000,'delay_s':shot.get('delay',0)/1000 if number(shot.get('delay',0)) else 0,'path':points,
            'bullet_id':shot.get('bulletId') if number(shot.get('bulletId')) else None,'simple':not any(shot.get(k) for k in ('change','jumps','wave','orbit','path'))}

def comparison(prediction,native):
    if not prediction or len(native)!=1:return None
    from shot_review import interpolate
    horizon=min(prediction['duration_s'],native[0]['duration_s']);errors=[]
    for i in range(1,33):
        t=horizon*i/32;a=interpolate(prediction['path'],t);b=interpolate(native[0]['path'],t)
        if a and b:errors.append(math.dist(a,b))
    if not errors:return None
    return {'source':'pre-shot-model-vs-native-reconstruction','horizon_s':horizon,'mean_error_px':sum(errors)/len(errors),'max_error_px':max(errors),'certifies_aim':False}

class TrainingGuideStore:
    def __init__(self,directory,per_mode=16,limit=816):
        self.path=Path(directory)/FILENAME;self.per_mode=max(1,min(per_mode,32));self.limit=max(1,min(limit,1632));self.pending={};self.error='';self.saved=0
    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        connection=sqlite3.connect(self.path,timeout=.3)
        try:
            with connection:
                connection.execute('PRAGMA max_page_count=12288')
                connection.execute('CREATE TABLE IF NOT EXISTS guides (id TEXT PRIMARY KEY, profile TEXT NOT NULL, episode TEXT NOT NULL, game TEXT, created REAL NOT NULL, payload TEXT NOT NULL)')
                connection.execute('CREATE INDEX IF NOT EXISTS guide_profile ON guides(profile,created)')
                yield connection
        finally:connection.close()
    def record(self,token,probe,release,state,episode,game=None):
        try:return self._record(token,probe,release,state,episode,game)
        except (sqlite3.Error,OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError,IndexError):self.error='No se pudo guardar la guía del entrenamiento';return False
    def _record(self,token,probe,release,state,episode,game):
        if not isinstance(token,str) or not token or not isinstance(release,dict) or release.get('hero')!=state.get('heroId'):return False
        mobile=mobile_name(probe.get('mobile'));mode=release.get('shot')
        if not mobile or not isinstance(mode,int) or isinstance(mode,bool) or mode not in (0,1,2) or not number(release.get('power')) or not 1<=release['power']<=400:return False
        from shot_attribution import attributed_start,identity
        native=[];parents=[]
        for shot in state.get('shots',[])[:64]:
            if not isinstance(shot,dict) or identity(shot) in release.get('baseline',[]):continue
            attribution=attributed_start(state,shot,release)
            if not attribution or not attribution.get('learnable') or attribution['shot']!=mode:continue
            actual=native_path(shot)
            if actual:native.append(actual);parents.append(identity(shot))
            if len(native)>=8:break
        if not native:return False
        key=f'dragonbound:{mobile}:{mode}';plan=release.get('learner') or release.get('lab') or {}
        if not isinstance(plan,dict):plan={}
        wind,angle=release.get('wind'),release.get('windAngle')
        if not all(number(v) for v in (wind,angle)):return False
        phase=plan.get('evaluation_phase');phase=phase if phase in ('calibration','evaluation','weather','recovery') else 'unknown'
        scope='initial-launch-only' if plan.get('prefix_only') or plan.get('full_family_validated') is False else 'planned-flight'
        row={'schema':1,'profile':key,'phase':phase,'scope':scope,'physics_approved_by_archive':False,'item':'dual' if release.get('item')=='dual' else None,
             'planned':{**numeric(plan,('power','raw_angle','heading','elevation')),'origin':point(plan.get('origin')),'target':point(plan.get('target'))},
             'actual':{**numeric(release,('power','angle')),'wind':wind,'wind_angle':angle},'prediction':pre_shot_path(plan,wind,angle),'native':native,
             'weather':[numeric(w,('typeId','resolvedTypeId','x','size')) for w in state.get('weather',[])[:32] if isinstance(w,dict)],'health':None,'outcome':'unknown'}
        row['comparison']=comparison(row['prediction'],native)
        simple=len(native)==1 and native[0]['simple'] and release.get('item') is None
        row['launch_samples']=[{'id':hashed((episode,ident)),'episode':str(episode)[:200],'simple':simple,'source':'owned-native-launch','power':release['power'],'speed':n['start'][3],'heading':n['start'][2],'ax':n['start'][4],'ay':n['start'][5],'wind':wind,'wind_angle':angle,'duration_s':n['duration_s']} for ident,n in zip(parents,native)]
        raw=json.dumps(row,allow_nan=False,separators=(',',':'))
        if len(raw.encode())>MAX_PAYLOAD-512:
            row['native']=native[:2];row['launch_samples']=row['launch_samples'][:2];row['truncated']=True
            # A clipped family cannot later be mistaken for a simple shot.
            for sample in row['launch_samples']:sample['simple']=False
            raw=json.dumps(row,allow_nan=False,separators=(',',':'))
            if len(raw.encode())>MAX_PAYLOAD-512:return False
        ident=hashed(token)
        with self.connect() as connection:
            if connection.execute('SELECT 1 FROM guides WHERE id=?',(ident,)).fetchone():return False
            connection.execute('INSERT INTO guides VALUES (?,?,?,?,?,?)',(ident,key,str(episode)[:200],hashed(game) if game else None,time.time(),raw))
            connection.execute('DELETE FROM guides WHERE profile=? AND id NOT IN (SELECT id FROM guides WHERE profile=? ORDER BY created DESC,id DESC LIMIT ?)',(key,key,self.per_mode))
            connection.execute('DELETE FROM guides WHERE id NOT IN (SELECT id FROM guides ORDER BY created DESC,id DESC LIMIT ?)',(self.limit,))
        self.pending[ident]={'token':token,'profile':key,'parents':parents,'at':time.monotonic()};self.pending=dict(list(self.pending.items())[-32:]);self.saved+=1;self.error='';return True
    def update_health(self,row):
        keys=('known','enemy_health_drop','own_health_drop','reward_eligible','terrain_opened')
        result={k:v for k,v in row.items() if k in keys and (v is None or isinstance(v,bool) or number(v))}
        if not self.path.exists():return False
        try:
            with self.connect() as connection:
                found=connection.execute('SELECT payload FROM guides WHERE id=?',(hashed(row.get('token')),)).fetchone()
                if not found:return False
                data=json.loads(found[0]);data['health']=result
                connection.execute('UPDATE guides SET payload=?,game=COALESCE(game,?) WHERE id=?',(json.dumps(data,allow_nan=False,separators=(',',':')),hashed(row['game']) if row.get('game') else None,hashed(row.get('token'))))
            return True
        except (sqlite3.Error,OSError,ValueError,TypeError):self.error='No se pudo guardar el resultado de la guía';return False
    def update_outcome(self,row):
        if not self.path.exists() or not row.get('id'):return False
        known=row.get('outcome_known') is True and row.get('source')=='native-survival-at-gameover' and row.get('outcome') in ('win','loss')
        try:
            with self.connect() as connection:
                rows=connection.execute('SELECT id,payload FROM guides WHERE game=?',(hashed(row['id']),)).fetchall()
                for ident,raw in rows:
                    data=json.loads(raw)
                    if known:data['outcome']=row['outcome']
                    elif data.get('outcome') not in ('win','loss'):data['outcome']='unknown'
                    connection.execute('UPDATE guides SET payload=? WHERE id=?',(json.dumps(data,separators=(',',':')),ident))
            return bool(rows)
        except (sqlite3.Error,OSError,ValueError,TypeError):self.error='No se pudo guardar el cierre de las guías';return False
    def follow(self,state,learner):
        """Append only continuations whose owner was proved by the learner."""
        if not self.pending or not learner:return
        from shot_attribution import identity
        shots={identity(s):s for s in state.get('shots',[]) if isinstance(s,dict)}
        for ident,pending in list(self.pending.items()):
            if time.monotonic()-pending['at']>25:self.pending.pop(ident,None);continue
            continued=pending.setdefault('continued',set())
            phases=learner.records.get(pending['profile'],{}).get('observed_phases',[])
            additions=[(p,shots[p['id']]) for p in phases if isinstance(p,dict) and p.get('verified') is True and p.get('parent') in pending['parents'] and p.get('id') in shots and p['id'] not in continued]
            if not additions:continue
            try:
                with self.connect() as connection:
                    found=connection.execute('SELECT payload FROM guides WHERE id=?',(ident,)).fetchone()
                    if not found:continue
                    data=json.loads(found[0]);seen=set(data.get('continuations',[]))
                    for phase,shot in additions:
                        key=hashed(phase['id'])
                        if key in seen:continue
                        path=native_path(shot,'verified-continuation')
                        if path and len(data['native'])<8:data['native'].append(path);seen.add(key)
                    data['continuations']=sorted(seen)
                    if seen:
                        for sample in data['launch_samples']:sample['simple']=False
                    raw=json.dumps(data,allow_nan=False,separators=(',',':'))
                    if len(raw.encode())<=MAX_PAYLOAD-512:
                        connection.execute('UPDATE guides SET payload=? WHERE id=?',(raw,ident))
                        continued.update(phase['id'] for phase,shot in additions if hashed(phase['id']) in seen)
            except (sqlite3.Error,OSError,ValueError,TypeError,KeyError):self.error='No se pudo completar el recorrido guardado'
    def summary(self):
        return {'saved_this_run':self.saved,'error':self.error,'per_mode_limit':self.per_mode,'total_limit':self.limit}
    @staticmethod
    def read_records(path):
        path=Path(path)
        if not path.exists():return {},0
        connection=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.2)
        try:
            records={};count=0
            for profile,payload in connection.execute('SELECT profile,payload FROM guides ORDER BY created LIMIT 1632'):
                if len(payload)>MAX_PAYLOAD:continue
                case=json.loads(payload);record=records.setdefault(profile,{'samples':[]})
                record['samples'].extend(case.get('launch_samples',[]));count+=1
                if len(case.get('native',[]))>1 or case.get('continuations') or case.get('scope')=='initial-launch-only':record['multi_projectile']=True
            # Preserve source episodes; the manual library fits each separately.
            for record in records.values():record['samples']=record['samples'][-384:]
            return records,count
        finally:connection.close()
