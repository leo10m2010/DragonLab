"""Per-vehicle calibration from attributed native shot starts; never synthetic evidence."""
import math,json,pathlib,time
from core import PROFILES,fit_calibration
from calibration_validation import validated_fit,current_fit

def mobile_name(value):
    if isinstance(value,int) and 0<=value<len(PROFILES):return list(PROFILES)[value]
    return value.upper() if isinstance(value,str) and value.upper() in PROFILES else None

class CalibrationBook:
    def __init__(self,path):
        self.path=pathlib.Path(path);self.records={};self.seen=set();self.revision=0;self.message='Esperando tiros medibles'
        try:
            saved=json.loads(self.path.read_text(encoding='utf-8'))
            if saved.get('schema')==1:self.records=saved.get('records',{})
        except (OSError,ValueError,TypeError):pass
    def key(self,clone,mobile,shot):return f'{clone}:{mobile}:{shot}'
    def profile(self,clone,mobile,shot,wind):
        record=self.records.get(self.key(clone,mobile,shot),{})
        fit=record.get('fit')
        if record.get('drift_pending'):return None
        if not fit or (not fit.get('wind_observed') and wind!=0):return None
        return fit
    def confidence(self,clone,mobile,shot,wind):
        record=self.records.get(self.key(clone,mobile,shot),{});fit=self.profile(clone,mobile,shot,wind)
        count=len(record.get('samples',[]))
        if record.get('drift_pending'):return {'label':'Recalibrando','count':count,'level':'low'}
        if fit:return {'label':'Salida calibrada' if mobile in ('KALSIDDON','NAK','TRICO') else 'Calibrado','count':count,'level':'measured','residual':fit.get('holdout_speed_error')}
        return {'label':'Aproximado' if count else 'Faltan datos','count':count,'level':'low'}
    def provisional(self,clone,mobile,shot,wind,angle):
        record=self.records.get(self.key(clone,mobile,shot),{})
        if record.get('drift_pending'):return None
        matching=[m for m in record.get('samples',[]) if m.get('wind')==wind and (wind==0 or abs((m.get('wind_angle',999)-angle+180)%360-180)<1e-6)]
        if not matching:return None
        sample=matching[-1];g,w,p,*_=PROFILES[mobile]
        return {'gravity':max(1,sample['ay']+math.sin(math.radians(angle))*wind*w),'wind_scale':w,'power_scale':math.hypot(sample['vx'],sample['vy'])/sample['power'],'speed_offset':0,'provisional':True}
    def underground_gravity(self,clone):
        samples=self.records.get(self.key(clone,'NAK',1),{}).get('underground_samples',[])
        if len(samples)<3:return None
        import statistics
        return statistics.median(s['gravity'] for s in samples)
    def acceleration(self,clone,mobile,shot,wind,angle):
        record=self.records.get(self.key(clone,mobile,shot),{})
        if record.get('drift_pending'):return None
        matching=[m for m in record.get('samples',[]) if abs(m.get('wind',-1)-wind)<1e-6 and (wind==0 or abs((m.get('wind_angle',999)-angle+180)%360-180)<1e-6)]
        return [matching[-1]['ax'],matching[-1]['ay']] if matching else None
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);temp=self.path.with_suffix('.tmp')
        temp.write_text(json.dumps({'schema':1,'records':self.records},indent=2),encoding='utf-8');temp.replace(self.path)
        self.revision+=1
    def observe(self,state,clone='dragonbound'):
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
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (power,wind,angle)) or not 1<=power<=400:return []
        native=[s for s in state.get('shots',[]) if s.get('native') and not s.get('auxiliary') and not s.get('delay',0) and isinstance(s.get('start'),list) and len(s['start'])==6]
        accepted=[]
        # Multiple simultaneous bullets can have different speed offsets. Keep them
        # visible, but do not silently fit one as the primary projectile.
        starts={tuple(s['start']) for s in native}
        if len(starts)!=1 or len({s.get('id') for s in native})!=len(native):return []
        s=native[0];ident=(clone,str(s.get('id'))+':'+','.join(str(v) for v in s['start']))
        if ident in self.seen:return []
        self.seen.add(ident)
        if len(self.seen)>4096:self.seen={ident}
        start=s['start'];x,y,launch_angle,speed,ax,ay=start
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in start) or speed<=0:return []
        if not isinstance(s.get('elapsed'),(int,float)) or not 0<=s['elapsed']<=600:return []
        distances=sorted((math.hypot(p['x']-x,p['y']-y),p['id']) for p in players)
        if distances[0][1]!=hero['id'] or distances[0][0]>90 or (len(distances)>1 and distances[1][0]-distances[0][0]<60):return []
        # Identical ballistic starts (e.g. Armor's two bullets) share a speed.
        # Different offsets, delayed secondary projectiles and lightning do not.
        actual_type=s.get('shotType')
        if actual_type in (0,1,2):shot_type=actual_type
        r=math.radians(launch_angle)
        sample={'power':power,'vx':math.cos(r)*speed,'vy':-math.sin(r)*speed,'ax':ax,'ay':ay,'wind':wind,'wind_angle':angle,'source':'native-shot-start'}
        key=self.key(clone,name,shot_type);record=self.records.setdefault(key,{'samples':[]})
        sample['sample_id']=ident[1]
        if any(m.get('sample_id')==ident[1] for m in record.get('samples',[])):return []
        prior=record.get('fit')
        if prior:
            predicted=prior['power_scale']*power+prior['speed_offset']
            g=ay+(math.sin(math.radians(angle))*wind*prior['wind_scale'] if prior.get('wind_scale') is not None else 0)
            mismatch=abs(speed-predicted)>max(8,.02*speed) or abs(g-prior['gravity'])>max(12,.05*prior['gravity'])
            if mismatch:
                pending=record.setdefault('drift_pending',[]);pending.append(sample)
                record['status']='Recalibrando: cambiaron las mediciones';self.message=f'{name}: comprobando un cambio de física'
                if len(pending)<2:self.save();return []
                archives=record.setdefault('previous_regimes',[])
                archives.append({'samples':record['samples'],'fit':prior,'reason':'Two incompatible native starts','archived':time.time()})
                record['previous_regimes']=archives[-8:]
                record.pop('fit',None);record['samples']=pending[:-1];record.pop('drift_pending',None)
            else:record.pop('drift_pending',None)
        record['samples']=(record['samples']+[sample])[-48:];record['updated']=time.time()
        samples=record['samples'];powers=[v['power'] for v in samples]
        self.message=f'{name}: {len(samples)} tiros medidos'
        if len(samples)>=4 and len(set(powers))>=3 and max(powers)-min(powers)>=40:
            try:
                fit,cut=current_fit(samples)
                if cut:
                    archives=record.setdefault('previous_regimes',[])
                    archives.append({'samples':samples[:cut],'reason':'Recent contiguous observations pass independent validation','archived':time.time()})
                    record['previous_regimes']=archives[-8:];record['samples']=samples[cut:]
                record['fit']=fit;record['status']='Ajuste observado';self.message=f'{name}: ajuste guardado con {len(samples)} tiros'
                accepted.append((key,fit))
            except ValueError:
                if prior:
                    archives=record.setdefault('previous_regimes',[])
                    cohort=samples[:-1]
                    ids=[s.get('sample_id') for s in cohort]
                    if not any([s.get('sample_id') for s in a.get('samples',[])]==ids for a in archives):
                        archives.append({'samples':cohort,'fit':prior,'reason':'Prior validated fit preserved after a new observation failed validation','archived':time.time()})
                        record['previous_regimes']=archives[-8:]
                record.pop('fit',None);record['status']='Faltan datos compatibles o falló la validación independiente'
        self.save();return accepted
    def refit_measured(self):
        changed=0
        for record in self.records.values():
            if record.get('drift_pending'):continue
            samples=record.get('samples',[])
            if len(samples)<4:continue
            try:
                fit,cut=current_fit(samples)
                if cut:
                    record.setdefault('previous_regimes',[]).append({'samples':samples[:cut],'reason':'Recent contiguous observations pass independent validation','archived':time.time()})
                    record['previous_regimes']=record['previous_regimes'][-8:];record['samples']=samples[cut:]
                record['fit']=fit;record['status']='Ajuste observado';changed+=1
            except ValueError:
                record.pop('fit',None);record['status']='Faltan datos compatibles o falló la validación independiente'
        self.save();return changed
    def rows(self,clone='dragonbound'):
        rows=[]
        for name in PROFILES:
            modes=[self.records.get(self.key(clone,name,i),{}) for i in (0,1,2)]
            record=max(modes,key=lambda r:(bool(r.get('fit')),len(r.get('samples',[])),bool(r.get('muzzle'))));fit=record.get('fit');count=sum(len(r.get('samples',[])) for r in modes)
            status=('Ajuste observado' if fit and fit.get('wind_observed') else 'Ajuste sin viento' if fit else 'Midiendo' if count else 'Salida medida · fuerza base' if record.get('muzzle') else 'Perfil base · faltan tiros')
            if any(r.get('drift_pending') for r in modes):status='Revisando cambio de física'
            elif any(r.get('fit') for r in modes):
                status=' · '.join(f'{label}: '+('con viento' if r.get('fit',{}).get('wind_observed') else 'sin viento' if r.get('fit') else 'pendiente') for label,r in zip(('1','2','SS'),modes))
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
