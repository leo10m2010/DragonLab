"""Per-vehicle calibration from attributed native shot starts; never synthetic evidence."""
import math,json,pathlib,time
from core import PROFILES,fit_calibration
from calibration_validation import validated_fit,current_fit

def mobile_name(value):
    if isinstance(value,int) and 0<=value<len(PROFILES):return list(PROFILES)[value]
    if isinstance(value,str):
        name=value.upper().replace('.','').replace(' ','')
        name={'JFROG':'FROG','RAONLAUNCHER':'RAON','CAMALEON':'RANDOMIZER','CHAMELEON':'RANDOMIZER'}.get(name,name)
        return name if name in PROFILES else None
    return None

class CalibrationBook:
    def __init__(self,path):
        self.path=pathlib.Path(path);self.records={};self.seen=set();self.release=None;self.revision=0;self.message='Esperando tiros medibles'
        try:
            saved=json.loads(self.path.read_text(encoding='utf-8'))
            if saved.get('schema')==1:self.records=saved.get('records',{})
        except (OSError,ValueError,TypeError):pass
    def key(self,clone,mobile,shot):return f'{clone}:{mobile}:{shot}'
    def profile(self,clone,mobile,shot,wind):
        if mobile=='RANDOMIZER':return None
        record=self.records.get(self.key(clone,mobile,shot),{})
        fit=record.get('fit')
        if record.get('drift_pending'):return None
        if not fit or (not fit.get('wind_observed') and wind!=0):return None
        return fit
    def confidence(self,clone,mobile,shot,wind):
        if mobile=='RANDOMIZER':return {'label':'Arma variable · falta identificar proyectil','count':0,'level':'low'}
        record=self.records.get(self.key(clone,mobile,shot),{});fit=self.profile(clone,mobile,shot,wind)
        count=len(record.get('samples',[]))
        if record.get('drift_pending'):return {'label':'Recalibrando','count':count,'level':'low'}
        if record.get('candidate'):return {'label':'Comprobando mejora','count':count,'level':'learning'}
        if fit:return {'label':'Salida calibrada' if mobile in ('KALSIDDON','NAK','TRICO') else 'Calibrado','count':count,'level':'measured','residual':fit.get('holdout_speed_error')}
        return {'label':'Aproximado' if count else 'Faltan datos','count':count,'level':'low'}
    def provisional(self,clone,mobile,shot,wind,angle):
        # A single unvalidated measurement must never override a saved fit.
        return None
    def note_release(self,release):
        self.release={**release,'expires':time.monotonic()+2}
    def underground_gravity(self,clone):
        samples=self.records.get(self.key(clone,'NAK',1),{}).get('underground_samples',[])
        if len(samples)<3:return None
        import statistics
        return statistics.median(s['gravity'] for s in samples)
    def acceleration(self,clone,mobile,shot,wind,angle):
        if mobile=='RANDOMIZER':return None
        return None
    def save(self):
        from local_storage import atomic_write
        atomic_write(self.path,json.dumps({'schema':1,'records':self.records},indent=2).encode())
        self.revision+=1
    def observe(self,state,clone='dragonbound'):
        if clone=='gunbound-world':return self.observe_gunbound(state.get('measurements',[]))
        if state.get('status')!='live':return []
        shots=state.get('shots',[])
        for child in shots:
            if child.get('bulletId')!=36 or not child.get('native'):continue
            parent=next((p for p in shots if p.get('bulletId')==35 and p.get('duration')==child.get('delay')),None)
            if not parent:continue
            a=parent.get('start',[]);b=child.get('start',[])
            if len(a)!=6 or len(b)!=6 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in a+b):continue
            t=parent['duration']/1000;vx=a[3]*math.cos(math.radians(a[2]))+a[4]*t;vy=-a[3]*math.sin(math.radians(a[2]))+a[5]*t
            if math.dist((vx,vy),(b[3]*math.cos(math.radians(b[2])),-b[3]*math.sin(math.radians(b[2]))))>2 or abs(b[4])>1 or not 500<=-b[5]<=4000:continue
            record=self.records.setdefault(self.key(clone,'NAK',1),{'samples':[]});samples=record.setdefault('underground_samples',[]);ident=str(child['id'])+':'+str(b)
            if not any(s['id']==ident for s in samples):
                samples.append({'id':ident,'gravity':-b[5],'source':'native-shot-continuation'});record['underground_samples']=samples[-32:];self.save()
        players=[p for p in state.get('players',[]) if all(isinstance(p.get(k),(int,float)) for k in ('x','y'))]
        muzzle_changed=False
        for player in players:
            vehicle=mobile_name(player.get('mobile'))
            if not vehicle:continue
            for index,muzzle in enumerate(player.get('muzzles',[])):
                if all(isinstance(muzzle.get(k),(int,float)) and math.isfinite(muzzle[k]) for k in ('angle','radius')) and 0<muzzle['radius']<=200:
                    record=self.records.setdefault(self.key(clone,vehicle,index),{'samples':[]})
                    if record.get('muzzle')!=muzzle:record['muzzle']=muzzle;record['muzzle_source']='native-player-aim';muzzle_changed=True
        if muzzle_changed:self.save()
        hero=next((p for p in players if p.get('isHero') or p.get('id')==state.get('heroId')),None)
        if not hero:return []
        name=mobile_name(hero.get('mobile'));shot_type=state.get('selectedShot')
        power=state.get('currentPower');wind=state.get('wind');angle=state.get('windAngle')
        if not name or shot_type not in (0,1,2):return []
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (wind,angle)):return []
        native=[s for s in state.get('shots',[]) if s.get('native') and not s.get('auxiliary') and not s.get('delay',0) and isinstance(s.get('start'),list) and len(s['start'])==6]
        accepted=[]
        # Multiple simultaneous bullets can have different speed offsets. Keep them
        # visible, but do not silently fit one as the primary projectile.
        starts={tuple(s['start']) for s in native}
        if len(starts)!=1 or len({s.get('id') for s in native})!=len(native):return []
        s=native[0]
        release=self.release if self.release and time.monotonic()<self.release['expires'] else None
        scope=(release or {}).get('measurement_session')
        prefix=''
        if isinstance(scope,str) and scope:
            import hashlib
            prefix=hashlib.sha256(scope.encode()).hexdigest()[:24]+':'
        ident=(clone,prefix+str(s.get('id'))+':'+','.join(str(v) for v in s['start']))
        if ident in self.seen:return []
        start=s['start'];x,y,launch_angle,speed,ax,ay=start
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in start) or speed<=0:return []
        if not isinstance(s.get('elapsed'),(int,float)) or not 0<=s['elapsed']<=600:return []
        from shot_attribution import attributed_start
        release=self.release if self.release and time.monotonic()<self.release['expires'] else None
        attribution=attributed_start(state,s,release)
        if not attribution or not attribution['learnable']:return []
        power=attribution['power'];shot_type=attribution['shot'];wind=attribution['wind'];angle=attribution['windAngle']
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (wind,angle)):return []
        self.seen.add(ident)
        if len(self.seen)>4096:self.seen={ident}
        r=math.radians(launch_angle)
        sample={'power':power,'vx':math.cos(r)*speed,'vy':-math.sin(r)*speed,'ax':ax,'ay':ay,'wind':wind,'wind_angle':angle,'source':'native-shot-start','duration_s':s.get('duration',0)/1000,'simple_trajectory':not any(s.get(k) for k in ('change','jumps','wave','orbit','path'))}
        key=self.key(clone,name,shot_type);record=self.records.setdefault(key,{'samples':[]})
        if name=='RANDOMIZER':
            from variable_projectiles import record_variant
            record_variant(record,s,{'power':power,'wind':wind,'windAngle':angle});self.message=record['status'];self.save();return []
        sample['sample_id']=ident[1]
        if prefix:sample['measurement_session']=prefix[:-1]
        if any(m.get('sample_id')==ident[1] for m in record.get('samples',[])):return []
        record['samples']=(record['samples']+[sample])[-48:];record['updated']=time.time()
        from learning_guard import update
        activated=update(record,sample)
        self.message=f"{name}: {record.get('status','Aprendiendo')}"
        if activated:accepted.append((key,activated))
        self.save();return accepted
    def observe_gunbound(self,measurements):
        accepted=[]
        from learning_guard import update
        for sample in measurements[:24]:
            if sample.get('source')!='gunbound-own-shot-path':continue
            name=mobile_name(sample.get('mobile'));shot=sample.get('selected_shot');ident=sample.get('sample_id')
            if not name or shot not in (0,1,2) or not ident:continue
            if not all(isinstance(sample.get(k),(int,float)) and math.isfinite(sample[k]) for k in ('power','vx','vy','ax','ay','wind','wind_angle')):continue
            if not 1<=sample['power']<=100 or not 0<=sample['wind']<=100:continue
            key=self.key('gunbound-world',name,shot);record=self.records.setdefault(key,{'samples':[]})
            if any(m.get('sample_id')==ident for m in record['samples']):continue
            record['samples']=(record['samples']+[sample])[-48:];record['updated']=time.time()
            activated=update(record,sample)
            if record.get('candidate'):record['candidate']['fit']['native_euler_step']=.05
            if activated:
                activated['native_euler_step']=.05;accepted.append((key,activated))
            self.message=f"{name} · {('1','2','SS')[shot]}: {record.get('status','Midiendo')} · {len(record['samples'])} tiros"
            self.save()
        return accepted

    def observe_training(self,state,release):
        if not isinstance(state,dict) or not isinstance(release,dict) or release.get('item'):return []
        self.note_release(release)
        from shot_attribution import attributed_start,identity
        import hashlib
        starts=[]
        for shot in state.get('shots',[]):
            a=attributed_start(state,shot,release)
            if a and a['learnable']:starts.append(shot)
        if len({tuple(s['start']) for s in starts})>1:
            hero=next((p for p in state.get('players',[]) if p.get('id')==state.get('heroId')),None)
            name=mobile_name(hero.get('mobile')) if hero else None
            if name and release.get('shot') in (0,1,2):
                key=self.key('dragonbound',name,release['shot']);record=self.records.setdefault(key,{'samples':[]})
                launches=[{'bullet':s.get('bulletId'),'start':s['start']} for s in starts[:16]]
                source=release.get('measurement_session','')
                ident=hashlib.sha256((str(source)+str([(s.get('id'),s['start']) for s in starts])).encode()).hexdigest()[:24]
                groups=record.setdefault('training_patterns',[])
                if not any(g['id']==ident for g in groups):
                    groups.append({'id':ident,'power':release['power'],'wind':release.get('wind'),'wind_angle':release.get('windAngle'),'launches':launches,'source':'attributed-native-group'})
                    record['training_patterns']=groups[-48:];record['pattern_status']='Salida múltiple: modelo específico pendiente';self.save()
        return self.observe(state,'dragonbound')

    def refit_measured(self):
        # Historical observations can prepare a challenger but are not new
        # independent evidence for replacing a running calibration.
        from learning_guard import update
        before=sum(bool(r.get('candidate')) for r in self.records.values())
        for key,record in self.records.items():
            if ':RANDOMIZER:' in key:continue
            samples=record.get('samples',[])
            if samples:update(record,samples[-1])
        self.save()
        return max(0,sum(bool(r.get('candidate')) for r in self.records.values())-before)
    def rows(self,clone='dragonbound'):
        rows=[]
        for name in PROFILES:
            modes=[self.records.get(self.key(clone,name,i),{}) for i in (0,1,2)]
            record=max(modes,key=lambda r:(bool(r.get('fit')),len(r.get('samples',[])),bool(r.get('muzzle'))));fit=record.get('fit');count=sum(len(r.get('samples',[])) for r in modes)
            status=('Ajuste observado' if fit and fit.get('wind_observed') else 'Ajuste sin viento' if fit else 'Midiendo' if count else 'Salida medida · fuerza base' if record.get('muzzle') else 'Perfil base · faltan tiros')
            if any(r.get('drift_pending') for r in modes):status='Revisando cambio de física'
            elif any(r.get('fit') for r in modes):
                status=' · '.join(f'{label}: '+('con viento' if r.get('fit',{}).get('wind_observed') else 'sin viento' if r.get('fit') else 'pendiente') for label,r in zip(('1','2','SS'),modes))
            if name=='RANDOMIZER':status='Arma variable · variantes por proyectil'
            rows.append((name,status,count))
        return rows
    def import_samples(self,data,clone='dragonbound'):
        # Import only explicit measurements with vehicle and shot attribution.
        if not isinstance(data,list):raise ValueError('Se requiere una lista de muestras')
        groups={}
        for sample in data:
            name=mobile_name(sample.get('mobile'));shot=sample.get('selected_shot',0)
            if name is None or shot not in (0,1,2):raise ValueError('Muestra sin vehículo o tiro válido')
            groups.setdefault(self.key(clone,name,shot),[]).append({k:sample[k] for k in ('power','vx','vy','ax','ay','wind','wind_angle')})
        fitted={key:validated_fit(values) for key,values in groups.items()}
        for key,values in groups.items():self.records[key]={'samples':values[-48:],'fit':fitted[key],'status':'Ajuste importado','updated':time.time()}
        self.save();return len(groups)
